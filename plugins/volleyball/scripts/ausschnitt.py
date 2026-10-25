#!/usr/bin/env python3
"""Schneidet eine Quellgrafik als Ausschnitt aus einer Seite (ADR-0013).

    <python> ausschnitt.py <foto> --rechteck 8 42 94 88 <ziel.jpg>
    <python> ausschnitt.py <pdf> --seite 3 --rechteck 5 20 95 61 <ziel.png>

Die Quelle ist ein Foto (JPEG, PNG) oder ein PDF, bei einem PDF mit der Seite,
ab 1 gezählt. Das Rechteck sind vier ganze Zahlen in Prozent der Seite: links,
oben, rechts, unten, gemessen an der Seite, wie sie aufrecht steht. So nennt
der Kartenentwurf seinen Ausschnitt, und so sieht ihn der Trainer bei der
Freigabe.

Ein Foto wird nach seiner EXIF-Orientierung gerade gestellt und mit Pillow
ausgeschnitten. Das Ergebnis ist ein JPEG mit derselben Qualität wie in der
Bildaufbereitung. Eine PDF-Seite zeichnet `pypdfium2` so, dass ihre lange
Kante so lang ist wie das Zielmaß der Bildaufbereitung, 2000 Pixel. Pillow
schneidet aus, das Ergebnis ist ein PNG. Die Endung des Ziels folgt deshalb
der Quelle: `.jpg` beim Foto, `.png` beim PDF. Ein Ziel, das schon da ist,
wird überschrieben, denn `sammelimport.py pruefen` schneidet nach jeder
Korrektur neu aus.

Am Ende nennt das Skript das Maß des Ausschnitts in Pixeln. Stimmt etwas
nicht, sagt es, was, endet mit Exitcode 1 und schreibt nichts.

Pillow braucht jeder Ausschnitt, `pypdfium2` nur einer aus einem PDF. Beide
sind freiwillig (ADR-0005, ADR-0013): Fehlt eins, nennt das Skript den Befehl
zum Installieren. Geholt werden sie erst, wenn geschnitten wird, so bekommt
ein Skript, das dieses importiert, keine neue Voraussetzung.

Der Sammelimport schneidet über dieselbe Funktion, `schneide_aus()`. Mit
`zeichne_seiten()` legt er dem Agenten die Seiten eines PDF als Bild hin,
gezeichnet wie zum Schneiden. Das Skript ist nur die Kommandozeile darum.
"""

from __future__ import annotations

import argparse
import io
import math
import sys
from collections.abc import Callable, Iterable
from dataclasses import dataclass
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from bilder_aufbereiten import QUALITAET, ZIELKANTE, fuer_jpeg  # noqa: E402
from tpdaten import interpreter, konsole_vorbereiten  # noqa: E402

FOTO_ENDUNGEN = {".jpg", ".jpeg", ".png"}


@dataclass(frozen=True)
class Bildformat:
    """Als was ein Ausschnitt geschrieben wird: die Endung seiner Datei und das Format für Pillow."""

    endung: str
    name: str


# Was aus welcher Quelle wird: aus einem Foto ein JPEG, aus einer PDF-Seite ein PNG.
AUS_DEM_FOTO = Bildformat(".jpg", "JPEG")
AUS_DEM_PDF = Bildformat(".png", "PNG")

RECHTECK = ("links", "oben", "rechts", "unten")


class KeinAusschnitt(Exception):
    """Der Ausschnitt lässt sich so nicht schneiden. Der Text sagt einem Trainer, warum.

    Eine Zeile, denn `sammelimport.py pruefen` schreibt ihn als Notiz in die
    Übersicht und weist den Entwurf damit ab.
    """


class BibliothekFehlt(Exception):
    """Pillow fehlt, oder bei einem PDF `pypdfium2`. Der Text nennt den Befehl zum Installieren.

    Eine eigene Ausnahme, weil das kein Fehler des Ausschnitts ist: Der
    Sammelimport bricht dann ab, statt den Entwurf abzuweisen.
    """


def verlange_bibliotheken(pdf: bool) -> None:
    """Wirft BibliothekFehlt, wenn eine Bibliothek fehlt, die der Ausschnitt braucht.

    Gefragt wird vor dem ersten Lesen und Schreiben, damit nichts halb
    geschrieben liegen bleibt. `pypdfium2` braucht nur ein PDF (ADR-0013),
    ein Foto geht ohne.
    """
    try:
        # Geholt wird beides, was der Ausschnitt braucht. Eine halbe
        # Installation fiele sonst erst beim Schneiden auf.
        from PIL import Image, ImageOps  # noqa: F401  Der Import ist die Prüfung.
    except ImportError:
        raise BibliothekFehlt(
            f"Für den Ausschnitt fehlt Pillow.\n\n"
            f"Installieren mit:\n  {interpreter()} -m pip install Pillow") from None
    if pdf:
        try:
            import pypdfium2  # noqa: F401  Der Import ist die Prüfung.
        except ImportError:
            raise BibliothekFehlt(
                f"Für einen Ausschnitt aus einem PDF fehlt pypdfium2.\n\n"
                f"Installieren mit:\n  {interpreter()} -m pip install pypdfium2\n\n"
                f"Ein Ausschnitt aus einem Foto geht auch ohne.") from None


# --------------------------------------------------------------------------
# Prüfen, bevor gelesen wird
# --------------------------------------------------------------------------

def bildformat(quelle: Path) -> Bildformat:
    """Das Bildformat des Ausschnitts aus dieser Quelle: JPEG beim Foto, PNG beim PDF.

    Erkannt wird die Quelle an ihrer Endung. Was weder Foto noch PDF ist,
    wirft KeinAusschnitt.
    """
    endung = quelle.suffix.lower()
    if endung == ".pdf":
        return AUS_DEM_PDF
    if endung in FOTO_ENDUNGEN:
        return AUS_DEM_FOTO
    raise KeinAusschnitt(
        f"{quelle.name} ist weder ein Foto (JPEG, PNG) noch ein PDF. "
        f"Ausschnitte gibt es nur aus diesen.")


def pruefe_rechteck(rechteck: tuple[int, int, int, int]) -> None:
    """Wirft KeinAusschnitt, wenn das Rechteck nicht den Regeln folgt.

    Vier ganze Zahlen von 0 bis 100, links kleiner als rechts, oben kleiner
    als unten. Ein Rechteck ohne Fläche ergäbe kein Bild.
    """
    for name, wert in zip(RECHTECK, rechteck):
        if not isinstance(wert, int) or not 0 <= wert <= 100:
            raise KeinAusschnitt(
                f"Das Rechteck stimmt nicht: {name} ist {wert}. Jede Zahl ist "
                f"eine ganze Zahl von 0 bis 100, in Prozent der Seite.")
    links, oben, rechts, unten = rechteck
    if links >= rechts:
        raise KeinAusschnitt(
            f"Das Rechteck stimmt nicht: links ({links}) muss kleiner sein als rechts ({rechts}).")
    if oben >= unten:
        raise KeinAusschnitt(
            f"Das Rechteck stimmt nicht: oben ({oben}) muss kleiner sein als unten ({unten}).")


def _pruefe_aufruf(quelle: Path, ziel: Path, rechteck: tuple[int, int, int, int],
                   seite: int | None) -> Bildformat:
    """Prüft alles, was sich ohne Bibliothek und ohne die Quelle zu lesen prüfen lässt.

    Gibt das Bildformat des Ausschnitts zurück.
    """
    if not quelle.is_file():
        raise KeinAusschnitt(f"Die Quelle {quelle} gibt es nicht.")
    art = bildformat(quelle)
    if ziel.suffix.lower() != art.endung:
        aus = "einem PDF" if art is AUS_DEM_PDF else "einem Foto"
        raise KeinAusschnitt(
            f"Aus {aus} wird ein {art.name}, das Ziel muss deshalb auf {art.endung} enden, "
            f"nicht {ziel.name}.")
    # Ein Tippfehler im Aufruf, und die Quelle wäre durch ihren eigenen
    # Ausschnitt ersetzt. Sie ist das Einzige, was sich nicht neu schneiden
    # lässt.
    if ziel.resolve() == quelle.resolve():
        raise KeinAusschnitt(f"Das Ziel ist die Quelle selbst: {quelle.name}.")
    if not ziel.parent.is_dir():
        raise KeinAusschnitt(f"Den Ordner für das Ziel gibt es nicht: {ziel.parent}")
    if art is AUS_DEM_PDF and seite is None:
        raise KeinAusschnitt(
            f"{quelle.name} ist ein PDF, und es fehlt, welche Seite. Gezählt wird ab 1.")
    if art is AUS_DEM_FOTO and seite is not None:
        raise KeinAusschnitt(
            f"Ein Foto hat keine Seiten, eine Seite gibt es nur bei einem PDF: {quelle.name}.")
    pruefe_rechteck(rechteck)
    return art


# --------------------------------------------------------------------------
# Lesen und Schneiden
# --------------------------------------------------------------------------

def _foto(quelle: Path):
    """Das Foto, nach seiner EXIF-Orientierung gerade gestellt.

    Gelesen wird aus dem Speicher, wie in der Bildaufbereitung: Solange ein
    Bild lebt, das Pillow aus der Datei liest, lässt Windows sie nicht
    überschreiben.
    """
    from PIL import Image, ImageOps

    try:
        with Image.open(io.BytesIO(quelle.read_bytes())) as bild:
            return ImageOps.exif_transpose(bild)
    except (OSError, ValueError, Image.DecompressionBombError):
        raise KeinAusschnitt(f"{quelle.name} lässt sich nicht als Bild öffnen.") from None


def _oeffne_pdf(quelle: Path):
    """Das PDF, geöffnet mit `pypdfium2`. Wer es öffnet, schließt es auch."""
    import pypdfium2

    try:
        return pypdfium2.PdfDocument(quelle.read_bytes())
    except pypdfium2.PdfiumError:
        raise KeinAusschnitt(f"{quelle.name} lässt sich nicht als PDF öffnen.") from None


def _zeichne(pdf, quelle: Path, seite: int):
    """Die Seite des offenen PDF als Bild, ihre lange Kante ZIELKANTE Pixel lang.

    Gezeichnet wird die Seite, wie sie aufrecht steht: Breite und Höhe, die
    `pypdfium2` nennt, rechnen eine Drehung der Seite schon ein.

    `pypdfium2` rundet die Kanten auf. Ein Faktor, der knapp über dem
    genauen liegt, ergäbe 2001 Pixel, etwa bei einer Folie im Format 16:9.
    Er wird deshalb so weit verkleinert, bis die lange Kante genau
    ZIELKANTE misst.
    """
    if not 1 <= seite <= len(pdf):
        seiten = "eine Seite" if len(pdf) == 1 else f"{len(pdf)} Seiten"
        raise KeinAusschnitt(
            f"{quelle.name} hat {seiten}, eine Seite {seite} gibt es nicht. "
            f"Gezählt wird ab 1.")
    blatt = pdf[seite - 1]
    lang = max(blatt.get_size())
    faktor = ZIELKANTE / lang
    while math.ceil(lang * faktor) > ZIELKANTE:
        faktor = math.nextafter(faktor, 0)
    return blatt.render(scale=faktor).to_pil()


def _pdf_seite(quelle: Path, seite: int):
    """Die Seite des PDF als Bild, gezeichnet wie in `_zeichne`."""
    pdf = _oeffne_pdf(quelle)
    try:
        return _zeichne(pdf, quelle, seite)
    finally:
        pdf.close()


def zeichne_seiten(quelle: Path, ziel: Callable[[int], Path],
                   seiten: Iterable[int] | None = None) -> list[tuple[int, Path]]:
    """Schreibt Seiten des PDF als PNG, so wie `schneide_aus` sie vor dem Schneiden zeichnet.

    `seiten` zählt ab 1, ohne Angabe sind es alle Seiten. `ziel(seite)` sagt,
    wohin eine Seite kommt. Zurück kommt je Seite ihre Zahl und ihr Pfad.

    Der Sammelimport legt sie neben den Auftrag (#65). Der Agent schätzt
    die Prozente eines Ausschnitts an der Seite, und das Werkzeug, mit dem
    er liest, zeichnet PDF-Seiten mit `pdftoppm`. Das fehlt unter Windows,
    wie ADR-0013 sagt. Mit diesen Bildern sieht er die Seite ohne, und
    genau so, wie `pruefen` sie schneidet.

    Wirft KeinAusschnitt, wenn sich das PDF nicht öffnen lässt oder es eine
    Seite nicht gibt, und BibliothekFehlt ohne Pillow oder `pypdfium2`. Was
    bis dahin geschrieben war, bleibt dann liegen.
    """
    verlange_bibliotheken(pdf=True)
    pdf = _oeffne_pdf(quelle)
    try:
        geschrieben: list[tuple[int, Path]] = []
        for seite in seiten if seiten is not None else range(1, len(pdf) + 1):
            puffer = io.BytesIO()
            _zeichne(pdf, quelle, seite).save(puffer, AUS_DEM_PDF.name)
            pfad = ziel(seite)
            pfad.write_bytes(puffer.getvalue())
            geschrieben.append((seite, pfad))
        return geschrieben
    finally:
        pdf.close()


def _schneide(bild, rechteck: tuple[int, int, int, int]):
    """Schneidet das Rechteck in Prozent aus dem aufrechten Bild."""
    links, oben, rechts, unten = rechteck
    breite, hoehe = bild.size
    return bild.crop((round(links * breite / 100), round(oben * hoehe / 100),
                      round(rechts * breite / 100), round(unten * hoehe / 100)))


def schneide_aus(quelle: Path, ziel: Path, rechteck: tuple[int, int, int, int],
                 seite: int | None = None) -> tuple[int, int]:
    """Schneidet den Ausschnitt aus der Quelle und schreibt ihn nach `ziel`.

    `seite` zählt ab 1 und gehört nur zu einem PDF. Gibt Breite und Höhe des
    Ausschnitts in Pixeln zurück.

    Wirft KeinAusschnitt, wenn etwas am Aufruf oder an der Quelle nicht
    stimmt, und BibliothekFehlt, wenn Pillow oder bei einem PDF `pypdfium2`
    fehlt. In beiden Fällen ist nichts geschrieben: Kodiert wird in den
    Speicher, erst das fertige Bild kommt auf die Platte. Ein Ziel, das schon
    da ist, bleibt dann, wie es war.
    """
    art = _pruefe_aufruf(quelle, ziel, rechteck, seite)
    verlange_bibliotheken(art is AUS_DEM_PDF)
    if art is AUS_DEM_PDF:
        ausschnitt, optionen = _schneide(_pdf_seite(quelle, seite), rechteck), {}
    else:
        ausschnitt = fuer_jpeg(_schneide(_foto(quelle), rechteck))
        optionen = {"quality": QUALITAET}
    puffer = io.BytesIO()
    ausschnitt.save(puffer, art.name, **optionen)
    ziel.write_bytes(puffer.getvalue())
    return ausschnitt.size


# --------------------------------------------------------------------------

def main() -> int:
    konsole_vorbereiten()
    ap = argparse.ArgumentParser(
        description="Eine Quellgrafik als Ausschnitt aus einem Foto oder einer "
                    "PDF-Seite schneiden")
    ap.add_argument("quelle", type=Path, help="das Foto (JPEG, PNG) oder das PDF")
    ap.add_argument("ziel", type=Path,
                    help="wohin der Ausschnitt kommt: .jpg beim Foto, .png beim PDF")
    ap.add_argument("--seite", type=int, default=None,
                    help="bei einem PDF die Seite, ab 1 gezählt")
    ap.add_argument("--rechteck", type=int, nargs=4, required=True,
                    metavar=("LINKS", "OBEN", "RECHTS", "UNTEN"),
                    help="in Prozent der aufrechten Seite, ganze Zahlen von 0 bis 100")
    a = ap.parse_args()

    try:
        breite, hoehe = schneide_aus(a.quelle, a.ziel, tuple(a.rechteck), a.seite)
    except (KeinAusschnitt, BibliothekFehlt) as fehler:
        print(f"{fehler}\n\nEs ist kein Ausschnitt geschrieben.")
        return 1
    print(f"Ausschnitt: {a.ziel}, {breite} × {hoehe} Pixel")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
