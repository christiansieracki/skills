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
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from bilder_aufbereiten import QUALITAET  # noqa: E402
from tpdaten import konsole_vorbereiten  # noqa: E402


def _foto(quelle: Path):
    """Das Foto, nach seiner EXIF-Orientierung gerade gestellt.

    Gelesen wird aus dem Speicher, wie in der Bildaufbereitung: Solange ein
    Bild lebt, das Pillow aus der Datei liest, lässt Windows sie nicht
    überschreiben.
    """
    from PIL import Image, ImageOps

    with Image.open(io.BytesIO(quelle.read_bytes())) as bild:
        return ImageOps.exif_transpose(bild)


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
    ap.add_argument("--rechteck", type=int, nargs=4, required=True,
                    metavar=("LINKS", "OBEN", "RECHTS", "UNTEN"),
                    help="in Prozent der aufrechten Seite, ganze Zahlen von 0 bis 100")
    a = ap.parse_args()

    breite, hoehe = schneide_aus(a.quelle, a.ziel, tuple(a.rechteck))
    print(f"Ausschnitt: {a.ziel}, {breite} × {hoehe} Pixel")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
