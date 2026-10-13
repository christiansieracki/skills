#!/usr/bin/env python3
"""Schneidet eine Quellgrafik als Ausschnitt aus einer Seite (ADR-0013).

    <python> ausschnitt.py <foto> --rechteck 8 42 94 88 <ziel.jpg>
    <python> ausschnitt.py <pdf> --seite 3 --rechteck 5 20 95 61 <ziel.png>

Die Quelle ist ein Foto (JPEG, PNG) oder ein PDF. Das Rechteck sind vier ganze
Zahlen in Prozent der Seite: links, oben, rechts, unten, gemessen an der Seite,
wie sie aufrecht steht. So nennt der Kartenentwurf seinen Ausschnitt, und so
sieht ihn der Trainer bei der Freigabe.

Ein Foto wird nach seiner EXIF-Orientierung gerade gestellt und mit Pillow
ausgeschnitten. Das Ergebnis ist ein JPEG mit derselben Qualität wie in der
Bildaufbereitung.

Am Ende nennt das Skript das Maß des Ausschnitts in Pixeln.

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
from bilder_aufbereiten import QUALITAET, ZIELKANTE  # noqa: E402
from tpdaten import interpreter, konsole_vorbereiten  # noqa: E402


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


def _foto(quelle: Path):
    """Das Foto, nach seiner EXIF-Orientierung gerade gestellt.

    Gelesen wird aus dem Speicher, wie in der Bildaufbereitung: Solange ein
    Bild lebt, das Pillow aus der Datei liest, lässt Windows sie nicht
    überschreiben.
    """
    from PIL import Image, ImageOps

    with Image.open(io.BytesIO(quelle.read_bytes())) as bild:
        return ImageOps.exif_transpose(bild)


def _pdf_seite(quelle: Path, seite: int):
    """Die Seite des PDF als Bild, ihre lange Kante ZIELKANTE Pixel lang.

    Gezeichnet wird die Seite, wie sie aufrecht steht: Breite und Höhe, die
    `pypdfium2` nennt, rechnen eine Drehung der Seite schon ein.

    `pypdfium2` rundet die Kanten auf. Ein Faktor, der knapp über dem
    genauen liegt, ergäbe 2001 Pixel. Er wird deshalb so weit verkleinert,
    bis die lange Kante genau ZIELKANTE misst.
    """
    import pypdfium2

    pdf = pypdfium2.PdfDocument(quelle.read_bytes())
    try:
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

    Gibt Breite und Höhe des Ausschnitts in Pixeln zurück.
    """
    pdf = quelle.suffix.lower() == ".pdf"
    verlange_bibliotheken(pdf)
    if pdf:
        ausschnitt = _schneide(_pdf_seite(quelle, seite), rechteck)
        ausschnitt.save(ziel, "PNG")
        return ausschnitt.size
    ausschnitt = _schneide(_foto(quelle), rechteck)
    if ausschnitt.mode not in ("RGB", "L"):
        ausschnitt = ausschnitt.convert("RGB")
    ausschnitt.save(ziel, "JPEG", quality=QUALITAET)
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
    except BibliothekFehlt as fehlt:
        print(f"{fehlt}\n\nEs ist kein Ausschnitt geschrieben.")
        return 1
    print(f"Ausschnitt: {a.ziel}, {breite} × {hoehe} Pixel")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
