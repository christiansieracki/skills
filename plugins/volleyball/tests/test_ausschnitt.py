"""Prueft `ausschnitt.py` gegen einen kuenstlichen Arbeitsordner.

    <python> -m unittest discover -s plugins/volleyball/tests

Der Ausschnitt ist die Quellgrafik, die aus einer Seite geschnitten wird: aus
einem Foto oder aus einer PDF-Seite, an einem Rechteck in Prozent der Seite
(ADR-0013). Aufgerufen wird ueber die Kommandozeile, wie die Skills es tun,
und gemessen wird am Bild, das danach auf der Platte liegt: Format, Mass in
Pixeln, Farbe an der Stelle. Dazu Ausgabe und Exitcode.

Foto und PDF entstehen zur Laufzeit, wie in test_bilder.py und
test_sammelimport.py. Das PDF traegt eine gezeichnete Flaeche in bekannter
Farbe an bekannter Stelle. Trifft der Ausschnitt sie, stimmen Seite, Mass und
Richtung, ohne dass der Test das Rechnen des Skripts nachrechnet.

Pruefungen, die Pillow oder `pypdfium2` brauchen, werden uebersprungen, wo
die Bibliothek fehlt. Das Fehlen selbst simuliert ein Schattenmodul im
PYTHONPATH, wie bei Pillow in test_bilder.py.
"""

from __future__ import annotations

import shutil
import tempfile
import unittest
from pathlib import Path

from arbeitsordner import A4, FOLIE, Arbeitsordner, PdfFlaeche

try:
    from PIL import Image
    HAT_PILLOW = True
except ImportError:  # pragma: no cover - haengt an der Installation, nicht am Code
    HAT_PILLOW = False

try:
    import pypdfium2  # noqa: F401
    HAT_PYPDFIUM2 = True
except ImportError:  # pragma: no cover - haengt an der Installation, nicht am Code
    HAT_PYPDFIUM2 = False

BRAUCHT_PILLOW = unittest.skipUnless(HAT_PILLOW, "Pillow ist nicht installiert")
BRAUCHT_PYPDFIUM2 = unittest.skipUnless(HAT_PYPDFIUM2, "pypdfium2 ist nicht installiert")

ROT = (200, 30, 30)
BLAU = (30, 120, 200)


def blende_aus(test: unittest.TestCase, modul: str) -> dict[str, str]:
    """Die Umgebung fuer einen Aufruf, in dem sich `modul` nicht importieren laesst.

    Wie in test_bilder.py: Ein `<modul>.py`, das beim Import abbricht,
    verdeckt das echte Paket, denn der PYTHONPATH kommt vor den
    site-packages. Deinstalliert werden muss dafuer nichts.
    """
    schatten = Path(tempfile.mkdtemp(prefix=f"ohne-{modul}-"))
    test.addCleanup(shutil.rmtree, schatten, True)
    (schatten / f"{modul}.py").write_text(
        f'raise ImportError("{modul} ist fuer diesen Test ausgeblendet")\n',
        encoding="utf-8",
    )
    return {"PYTHONPATH": str(schatten)}


def anteil_in_farbe(bild, farbe: tuple[int, int, int], toleranz: int = 24) -> float:
    """Welcher Anteil der Pixel in `farbe` ist, je Kanal bis auf `toleranz`.

    Die Toleranz faengt ab, was JPEG an einer einfarbigen Flaeche verschiebt.
    Rauschen trifft sie nur selten: ein Pixel in drei Kanaelen zugleich.
    """
    roh = bild.convert("RGB").tobytes()
    pixel = [roh[i:i + 3] for i in range(0, len(roh), 3)]
    treffer = sum(all(abs(wert - soll) <= toleranz for wert, soll in zip(p, farbe))
                  for p in pixel)
    return treffer / len(pixel)


class AusschnittTest(unittest.TestCase):
    def setUp(self) -> None:
        self.ordner = Arbeitsordner()
        self.addCleanup(self.ordner.raeume_auf)
        # Im Betrieb liegt das Ziel neben dem Kartenentwurf.
        self.entwuerfe = self.ordner.pfad / "kartenentwuerfe" / "stapel"
        self.entwuerfe.mkdir(parents=True)

    def schneide(self, quelle, ziel, *argumente: str, umgebung=None):
        """Ruft das Skript auf, wie ein Skill es tut. Einen Arbeitsordner braucht es nicht."""
        return self.ordner.starte("ausschnitt.py", str(quelle), *argumente, str(ziel),
                                  umgebung=umgebung, mit_wurzel=False)

    @BRAUCHT_PILLOW
    def test_ein_ausschnitt_aus_einem_foto_hat_das_erwartete_mass_und_ist_ein_jpeg(self) -> None:
        # Eine abfotografierte Magazinseite, ein JPEG wie aus dem Handy, und
        # ein Screenshot als PNG. Beide werden ein JPEG wie in der
        # Bildaufbereitung, und das Mass nennt die Ausgabe.
        for name in ("seite-26.jpg", "screenshot.png"):
            with self.subTest(name):
                quelle = self.ordner.lege_quellbild_an(name, (1000, 800))
                ziel = self.entwuerfe / f"{name}.quellgrafik.jpg"

                fertig = self.schneide(quelle, ziel, "--rechteck", "10", "20", "60", "70")

                self.assertEqual(fertig.returncode, 0, fertig.stdout + fertig.stderr)
                with Image.open(ziel) as bild:
                    self.assertEqual(bild.format, "JPEG")
                    self.assertEqual(bild.size, (500, 400))
                self.assertIn("500 × 400 Pixel", fertig.stdout)

    @BRAUCHT_PILLOW
    def test_bei_orientierung_sechs_meint_das_rechteck_die_aufrechte_seite(self) -> None:
        # So liegen die abfotografierten Magazinseiten vor: quer gespeichert,
        # mit der Anweisung im EXIF, sie fuer die Anzeige zu drehen. Der Agent
        # sieht die Seite aufrecht und nennt sein Rechteck an ihr. Die rote
        # Flaeche steht unten links auf der aufrechten Seite.
        quelle = self.ordner.lege_quellbild_an(
            "seite-26.jpg", (1000, 800), orientierung=6,
            flaeche=(ROT, (10, 60, 40, 90)))
        ziel = self.entwuerfe / "17.quellgrafik.jpg"

        fertig = self.schneide(quelle, ziel, "--rechteck", "15", "65", "35", "85")

        self.assertEqual(fertig.returncode, 0, fertig.stdout + fertig.stderr)
        with Image.open(ziel) as bild:
            # Aufrecht ist die Seite 800 breit und 1000 hoch.
            self.assertEqual(bild.size, (160, 200))
            self.assertGreater(anteil_in_farbe(bild, ROT), 0.95)

    def lege_merkmale_an(self):
        """Ein PDF mit zwei Seiten wie aus dem Lehrgang. Auf Seite 2 ist eine
        Grafik gezeichnet, eine blaue Flaeche bei links 20, oben 30, rechts
        60, unten 50. Seite 1 hat an derselben Stelle nichts."""
        return self.ordner.lege_quell_pdf_an(
            "Merkmale.pdf",
            ["Oberes Zuspiel", "Merkmale"],
            ["Bildreihe oberes Zuspiel", "Seite zwei"],
            flaechen=[PdfFlaeche(seite=2, farbe=BLAU, rechteck=(20, 30, 60, 50))])

    @BRAUCHT_PILLOW
    @BRAUCHT_PYPDFIUM2
    def test_ein_ausschnitt_aus_der_zweiten_seite_trifft_die_dort_gezeichnete_flaeche(self) -> None:
        # In den PDFs aus dem Lehrgang ist die Grafik oft gezeichnet und kein
        # eingebettetes Bild (ADR-0013). Der Ausschnitt liegt innerhalb der
        # Flaeche. Er trifft sie nur, wenn Seite, Richtung und Mass stimmen.
        quelle = self.lege_merkmale_an()
        ziel = self.entwuerfe / "17.quellgrafik.png"

        fertig = self.schneide(quelle, ziel, "--seite", "2",
                               "--rechteck", "25", "35", "55", "45")

        self.assertEqual(fertig.returncode, 0, fertig.stdout + fertig.stderr)
        with Image.open(ziel) as bild:
            self.assertEqual(bild.format, "PNG")
            self.assertGreater(anteil_in_farbe(bild, BLAU, toleranz=3), 0.95)

    @BRAUCHT_PILLOW
    @BRAUCHT_PYPDFIUM2
    def test_die_ganze_seite_hat_eine_lange_kante_von_2000_pixeln(self) -> None:
        # Das Zielmass der Bildaufbereitung. Die Folie im Format 16:9, wie
        # PowerPoint sie ausgibt, liegt quer, und ihre lange Kante kaeme ohne
        # Vorsicht auf 2001 Pixel.
        for name, seitenmass in (("a4.pdf", A4), ("folie.pdf", FOLIE)):
            with self.subTest(name):
                quelle = self.ordner.lege_quell_pdf_an(name, ["Seite eins"],
                                                       seitenmass=seitenmass)
                ziel = self.entwuerfe / f"{name}.png"

                fertig = self.schneide(quelle, ziel, "--seite", "1",
                                       "--rechteck", "0", "0", "100", "100")

                self.assertEqual(fertig.returncode, 0, fertig.stdout + fertig.stderr)
                with Image.open(ziel) as bild:
                    self.assertEqual(max(bild.size), 2000)

    @BRAUCHT_PILLOW
    def test_ohne_pypdfium2_endet_ein_pdf_mit_hinweis_und_ein_foto_geht_weiter(self) -> None:
        # pypdfium2 ist freiwillig wie Pillow (ADR-0013). Auf dem Rechner des
        # Trainers fehlt es, und ein Foto soll trotzdem gehen.
        ohne = blende_aus(self, "pypdfium2")
        pdf = self.lege_merkmale_an()
        foto = self.ordner.lege_quellbild_an("seite-26.jpg", (1000, 800))

        fertig = self.schneide(pdf, self.entwuerfe / "17.quellgrafik.png", "--seite", "2",
                               "--rechteck", "25", "35", "55", "45", umgebung=ohne)

        self.assertNotEqual(fertig.returncode, 0, fertig.stdout)
        self.assertIn("pip install pypdfium2", fertig.stdout)
        self.assertEqual(list(self.entwuerfe.iterdir()), [])

        fertig = self.schneide(foto, self.entwuerfe / "18.quellgrafik.jpg",
                               "--rechteck", "10", "20", "60", "70", umgebung=ohne)

        self.assertEqual(fertig.returncode, 0, fertig.stdout + fertig.stderr)
        self.assertTrue((self.entwuerfe / "18.quellgrafik.jpg").is_file())

    def test_ohne_pillow_endet_es_mit_hinweis(self) -> None:
        # Ohne Pillow geht kein Ausschnitt, weder aus dem Foto noch aus dem
        # PDF. Die Quelle muss dafuer kein Bild sein: Gefragt wird, bevor sie
        # gelesen wird. So laeuft der Test auch dort, wo Pillow fehlt.
        quelle = self.ordner.lege_quelldatei_an("seite-26.jpg", b"kein Bild")

        fertig = self.schneide(quelle, self.entwuerfe / "17.quellgrafik.jpg",
                               "--rechteck", "10", "20", "60", "70",
                               umgebung=blende_aus(self, "PIL"))

        self.assertNotEqual(fertig.returncode, 0, fertig.stdout)
        self.assertIn("pip install Pillow", fertig.stdout)
        self.assertEqual(list(self.entwuerfe.iterdir()), [])


if __name__ == "__main__":
    unittest.main()
