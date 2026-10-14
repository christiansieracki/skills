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

Der Sammelimport schneidet über dieselbe Funktion, `schneide_aus()`. Das
Skript ist nur die Kommandozeile darum.
"""

from __future__ import annotations

import argparse
import io
import math
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from bilder_aufbereiten import QUALITAET, ZIELKANTE, fuer_jpeg  # noqa: E402
from tpdaten import interpreter, konsole_vorbereiten  # noqa: E402

FOTO_ENDUNGEN = {".jpg", ".jpeg", ".png"}

# Was aus welcher Quelle wird, Endung und Format des Ausschnitts.
FOTO, PDF = (".jpg", "JPEG"), (".png", "PNG")

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

def ergebnis(quelle: Path) -> tuple[str, str]:
    """Endung und Format des Ausschnitts aus dieser Quelle: JPEG beim Foto, PNG beim PDF.

    Erkannt wird die Quelle an ihrer Endung. Was weder Foto noch PDF ist,
    wirft KeinAusschnitt.
    """
    endung = quelle.suffix.lower()
    if endung == ".pdf":
        return PDF
    if endung in FOTO_ENDUNGEN:
        return FOTO
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
                   seite: int | None) -> tuple[str, str]:
    """Prüft alles, was sich ohne Bibliothek und ohne die Quelle zu lesen prüfen lässt.

    Gibt Endung und Format des Ausschnitts zurück.
    """
    if not quelle.is_file():
        raise KeinAusschnitt(f"Die Quelle {quelle} gibt es nicht.")
    art = ergebnis(quelle)
    endung = art[0]
    if ziel.suffix.lower() != endung:
        aus = "einem PDF wird ein PNG" if art == PDF else "einem Foto wird ein JPEG"
        raise KeinAusschnitt(
            f"Aus {aus}, das Ziel muss deshalb auf {endung} enden, nicht {ziel.name}.")
    # Ein Tippfehler im Aufruf, und die Quelle wäre durch ihren eigenen
    # Ausschnitt ersetzt. Sie ist das Einzige, was sich nicht neu schneiden
    # lässt.
    if ziel.resolve() == quelle.resolve():
        raise KeinAusschnitt(f"Das Ziel ist die Quelle selbst: {quelle.name}.")
    if not ziel.parent.is_dir():
        raise KeinAusschnitt(f"Den Ordner für das Ziel gibt es nicht: {ziel.parent}")
    if art == PDF and seite is None:
        raise KeinAusschnitt(
            f"{quelle.name} ist ein PDF, und es fehlt, welche Seite. Gezählt wird ab 1.")
    if art == FOTO and seite is not None:
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


def _pdf_seite(quelle: Path, seite: int):
    """Die Seite des PDF als Bild, ihre lange Kante ZIELKANTE Pixel lang.

    Gezeichnet wird die Seite, wie sie aufrecht steht: Breite und Höhe, die
    `pypdfium2` nennt, rechnen eine Drehung der Seite schon ein.

    `pypdfium2` rundet die Kanten auf. Ein Faktor, der knapp über dem
    genauen liegt, ergäbe 2001 Pixel, etwa bei einer Folie im Format 16:9.
    Er wird deshalb so weit verkleinert, bis die lange Kante genau
    ZIELKANTE misst.
    """
    import pypdfium2

    try:
        pdf = pypdfium2.PdfDocument(quelle.read_bytes())
    except pypdfium2.PdfiumError:
        raise KeinAusschnitt(f"{quelle.name} lässt sich nicht als PDF öffnen.") from None
    try:
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
    verlange_bibliotheken(art == PDF)
    if art == PDF:
        ausschnitt = _schneide(_pdf_seite(quelle, seite), rechteck)
    else:
        ausschnitt = fuer_jpeg(_schneide(_foto(quelle), rechteck))
    puffer = io.BytesIO()
    if art == PDF:
        ausschnitt.save(puffer, "PNG")
    else:
        ausschnitt.save(puffer, "JPEG", quality=QUALITAET)
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
