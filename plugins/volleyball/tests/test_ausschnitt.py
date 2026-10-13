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

import unittest

from arbeitsordner import Arbeitsordner

try:
    from PIL import Image
    HAT_PILLOW = True
except ImportError:  # pragma: no cover - haengt an der Installation, nicht am Code
    HAT_PILLOW = False

BRAUCHT_PILLOW = unittest.skipUnless(HAT_PILLOW, "Pillow ist nicht installiert")

ROT = (200, 30, 30)


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


if __name__ == "__main__":
    unittest.main()
