"""Prueft die Aufbereitung der Quellbilder gegen einen kuenstlichen Arbeitsordner.

    <python> -m unittest discover -s plugins/volleyball/tests

Aufgerufen wird ueber die Kommandozeile mit `--wurzel`, wie bei Linter und
Suche. Gemessen wird am Ergebnis auf der Platte: Kantenlaenge, EXIF-Eintrag,
Dateiname, Bytes. Das ist der Teil, an dem haengt, ob eine abfotografierte
Magazinseite sich hinterher oeffnen laesst.

Zwei Festlegungen:

Die Pruefungen, die ein Bild erzeugen, werden **uebersprungen, wenn Pillow
fehlt**. Ein rotes Testergebnis, das auf einer normalen Installation die Norm
waere, liest bald niemand mehr. Fuer alles andere soll die
Standardbibliothek reichen.

Das Testfoto entsteht **zur Laufzeit**, nicht als eingecheckte Datei. Wenn
diese Pruefungen ueberhaupt laufen, ist Pillow da; also baut der Aufbau das
JPEG mit EXIF-Orientierung 6 selbst. Kein Binaermaterial im Repo, und die
Bedingung des Tests steht als Code da, statt in einer Datei versteckt zu sein.
"""

from __future__ import annotations

import os
import shutil
import tempfile
import unittest
from pathlib import Path

from arbeitsordner import ORIENTIERUNG, Arbeitsordner

try:
    from PIL import Image
    HAT_PILLOW = True
except ImportError:  # pragma: no cover - haengt an der Installation, nicht am Code
    HAT_PILLOW = False

BRAUCHT_PILLOW = unittest.skipUnless(HAT_PILLOW, "Pillow ist nicht installiert")

# Reicht ueber die Schwelle von 2 MB, ohne dass ein Bild dafuer noetig waere.
# Zufallsbytes, weil eine Datei aus Nullen je nach Dateisystem gar nicht so
# viel Platz belegt, wie sie behauptet.
ZU_SCHWER = os.urandom(3 * 1024 * 1024)


class BilderTest(unittest.TestCase):
    def setUp(self) -> None:
        self.ordner = Arbeitsordner()
        self.addCleanup(self.ordner.raeume_auf)

    def bereite_auf(self, *argumente: str):
        fertig = self.ordner.starte("bilder_aufbereiten.py", "--ja", *argumente)
        self.assertEqual(fertig.returncode, 0, fertig.stdout + fertig.stderr)
        return fertig

    @BRAUCHT_PILLOW
    def test_ein_bild_ueber_der_schwelle_wird_verkleinert(self) -> None:
        datei = self.ordner.lege_quellbild_an("seite-01.jpg", (3000, 2250))

        self.bereite_auf()

        with Image.open(datei) as bild:
            self.assertEqual(max(bild.size), 2000)
        self.assertLess(datei.stat().st_size, 2 * 1024 * 1024)

    @BRAUCHT_PILLOW
    def test_ein_bild_unter_der_schwelle_bleibt_byte_identisch(self) -> None:
        # Die Aufbereitung soll nichts verschlechtern, was schon in Ordnung
        # war. Ein kleines Foto wird deshalb nicht einmal neu kodiert.
        datei = self.ordner.lege_quellbild_an("klein.jpg", (400, 300))
        vorher = datei.read_bytes()

        self.bereite_auf()

        self.assertEqual(datei.read_bytes(), vorher)

    @BRAUCHT_PILLOW
    def test_orientierung_sechs_steht_danach_aufrecht(self) -> None:
        # So liegen alle fuenfzehn Magazinseiten vor: quer aufgenommen, mit
        # der Anweisung im EXIF, sie fuer die Anzeige zu drehen.
        datei = self.ordner.lege_quellbild_an("quer.jpg", (3000, 2250), orientierung=6)

        self.bereite_auf()

        with Image.open(datei) as bild:
            breite, hoehe = bild.size
            self.assertLess(breite, hoehe, "das Bild liegt immer noch quer")
            self.assertEqual(max(bild.size), 2000)
            # Zurueckgesetzt, sonst dreht der naechste Betrachter ein zweites Mal.
            self.assertIn(bild.getexif().get(ORIENTIERUNG, 1), (0, 1))

    @BRAUCHT_PILLOW
    def test_der_dateiname_bleibt_und_es_entsteht_nichts_daneben(self) -> None:
        # Daran haengen die `quelldatei:`-Verweise auf den Karten.
        self.ordner.lege_quellbild_an("seite-01.jpg", (3000, 2250))

        self.bereite_auf()

        quellen = self.ordner.pfad / "quellen"
        self.assertEqual([p.name for p in sorted(quellen.iterdir())], ["seite-01.jpg"])

    @BRAUCHT_PILLOW
    def test_ein_png_ueber_der_schwelle_wird_ebenfalls_verkleinert(self) -> None:
        # Ein grosser Screenshot macht dasselbe Problem wie ein grosses Foto.
        datei = self.ordner.lege_quellbild_an("screenshot.png", (2400, 1800))
        vorher = datei.stat().st_size

        self.bereite_auf()

        with Image.open(datei) as bild:
            self.assertEqual(max(bild.size), 2000)
        self.assertLess(datei.stat().st_size, vorher)

    @BRAUCHT_PILLOW
    def test_die_bilanz_nennt_dateien_und_gesparten_platz(self) -> None:
        self.ordner.lege_quellbild_an("seite-01.jpg", (3000, 2250))
        self.ordner.lege_quellbild_an("seite-02.jpg", (3000, 2250))

        fertig = self.bereite_auf()

        self.assertIn("2 von 2 aufbereitet", fertig.stdout)
        self.assertRegex(fertig.stdout, r"\d+,\d MB gespart")

    @BRAUCHT_PILLOW
    def test_ein_quer_liegendes_kleines_bild_wird_gemeldet_statt_angefasst(self) -> None:
        # Die Schwelle entscheidet, nicht die Orientierung: das kleine Bild
        # bleibt byte-identisch. Damit es deswegen nicht still quer liegen
        # bleibt, nennt die Bilanz es beim Namen.
        klein = self.ordner.lege_quellbild_an("klein-quer.jpg", (400, 300), orientierung=6)
        vorher = klein.read_bytes()
        self.ordner.lege_quellbild_an("seite-01.jpg", (3000, 2250))

        fertig = self.bereite_auf()

        self.assertEqual(klein.read_bytes(), vorher)
        self.assertIn("Quer, aber unter der Schwelle", fertig.stdout)
        self.assertIn("klein-quer.jpg", fertig.stdout)

    @BRAUCHT_PILLOW
    def test_eine_kaputte_datei_haelt_den_stapel_nicht_an_faerbt_ihn_aber_rot(self) -> None:
        # Zufallsbytes unter einem .jpg-Namen: die Datei kommt ueber die
        # Schwelle und in die Liste, scheitert aber beim Oeffnen.
        self.ordner.lege_quelldatei_an("kaputt.jpg", ZU_SCHWER)
        gut = self.ordner.lege_quellbild_an("seite-01.jpg", (3000, 2250))

        fertig = self.ordner.starte("bilder_aufbereiten.py", "--ja")

        self.assertNotEqual(fertig.returncode, 0, "ein Fehlschlag darf nicht gruen sein")
        self.assertIn("FEHLER", fertig.stdout)
        with Image.open(gut) as bild:
            self.assertEqual(max(bild.size), 2000, "der Rest des Stapels lief weiter")

    @BRAUCHT_PILLOW
    def test_ein_ja_auf_die_rueckfrage_bearbeitet_den_ganzen_stapel(self) -> None:
        # Der Zweig, hinter dem das Ersetzen der Originale haengt. Ohne `--ja`
        # gibt es nur diesen einen Weg dorthin.
        self.ordner.lege_quellbild_an("seite-01.jpg", (3000, 2250))
        self.ordner.lege_quellbild_an("seite-02.jpg", (3000, 2250))

        fertig = self.ordner.starte("bilder_aufbereiten.py", eingabe="ja\n")

        self.assertEqual(fertig.returncode, 0, fertig.stdout + fertig.stderr)
        self.assertEqual(fertig.stdout.count("Weiter? [j/N]"), 1,
                         "einmal fuer den ganzen Stapel, nicht je Datei")
        self.assertIn("2 von 2 aufbereitet", fertig.stdout)

    @BRAUCHT_PILLOW
    def test_ohne_zustimmung_wird_einmal_gefragt_und_nichts_geschrieben(self) -> None:
        # Ohne `--ja` stellt das Skript die Rueckfrage. stdin haengt im Test am
        # Nullgeraet, die Antwort ist damit ein EOF und gilt als Nein. Genau
        # das soll das Original heil lassen.
        datei = self.ordner.lege_quelldatei_an("seite-01.jpg", ZU_SCHWER)

        fertig = self.ordner.starte("bilder_aufbereiten.py")

        self.assertNotEqual(fertig.returncode, 0)
        self.assertEqual(fertig.stdout.count("Weiter? [j/N]"), 1,
                         "einmal fuer den ganzen Stapel, nicht je Datei")
        self.assertEqual(datei.read_bytes(), ZU_SCHWER)

    def test_ohne_pillow_bricht_es_mit_installationshinweis_ab(self) -> None:
        # Laeuft auch dort, wo Pillow installiert ist. Ein `PIL.py`, das beim
        # Import abbricht, verdeckt das echte Paket: der PYTHONPATH kommt vor
        # den site-packages. Das Skript sieht damit denselben ImportError, den
        # es auf einer Installation ohne Pillow saehe, und es muss dafuer
        # nichts deinstalliert werden.
        schatten = Path(tempfile.mkdtemp(prefix="ohne-pillow-"))
        self.addCleanup(shutil.rmtree, schatten, True)
        (schatten / "PIL.py").write_text(
            'raise ImportError("Pillow ist fuer diesen Test ausgeblendet")\n',
            encoding="utf-8",
        )
        datei = self.ordner.lege_quelldatei_an("seite-01.jpg", ZU_SCHWER)

        fertig = self.ordner.starte(
            "bilder_aufbereiten.py", "--ja", umgebung={"PYTHONPATH": str(schatten)})

        self.assertNotEqual(fertig.returncode, 0)
        self.assertIn("Pillow", fertig.stdout)
        self.assertIn("pip install Pillow", fertig.stdout)
        self.assertEqual(datei.read_bytes(), ZU_SCHWER)


if __name__ == "__main__":
    unittest.main()
