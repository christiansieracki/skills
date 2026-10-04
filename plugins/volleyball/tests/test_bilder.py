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

Fuer HEIC gilt dasselbe mit pillow-heif: Die Pruefung, die ein HEIC baut und
aufbereitet, wird uebersprungen, wo das Paket fehlt.
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

try:
    import pillow_heif  # noqa: F401
    HAT_PILLOW_HEIF = HAT_PILLOW
except ImportError:  # pragma: no cover - haengt an der Installation, nicht am Code
    HAT_PILLOW_HEIF = False

BRAUCHT_PILLOW = unittest.skipUnless(HAT_PILLOW, "Pillow ist nicht installiert")
BRAUCHT_PILLOW_HEIF = unittest.skipUnless(HAT_PILLOW_HEIF, "pillow-heif ist nicht installiert")


def blende_aus(test: unittest.TestCase, modul: str) -> dict[str, str]:
    """Die Umgebung fuer einen Aufruf, in dem sich `modul` nicht importieren laesst.

    Ein `<modul>.py`, das beim Import abbricht, verdeckt das echte Paket: der
    PYTHONPATH kommt vor den site-packages. Das Skript sieht damit denselben
    ImportError, den es auf einer Installation ohne das Paket saehe, und es
    muss dafuer nichts deinstalliert werden.
    """
    schatten = Path(tempfile.mkdtemp(prefix=f"ohne-{modul}-"))
    test.addCleanup(shutil.rmtree, schatten, True)
    (schatten / f"{modul}.py").write_text(
        f'raise ImportError("{modul} ist fuer diesen Test ausgeblendet")\n',
        encoding="utf-8",
    )
    return {"PYTHONPATH": str(schatten)}

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
        # Laeuft auch dort, wo Pillow installiert ist, siehe blende_aus().
        datei = self.ordner.lege_quelldatei_an("seite-01.jpg", ZU_SCHWER)

        fertig = self.ordner.starte(
            "bilder_aufbereiten.py", "--ja", umgebung=blende_aus(self, "PIL"))

        self.assertNotEqual(fertig.returncode, 0)
        self.assertIn("Pillow", fertig.stdout)
        self.assertIn("pip install Pillow", fertig.stdout)
        self.assertEqual(datei.read_bytes(), ZU_SCHWER)


class FremdeFormateTest(unittest.TestCase):
    """TIFF und HEIC werden zu JPEG, auch unter der Schwelle.

    Das Lesewerkzeug des Agenten zeigt nur PNG und JPEG. Ein TIFF oder HEIC
    bliebe ohne Aufbereitung unlesbar, egal wie klein es ist.
    """

    def setUp(self) -> None:
        self.ordner = Arbeitsordner()
        self.addCleanup(self.ordner.raeume_auf)
        self.quellen = self.ordner.pfad / "quellen"

    def starte(self, umgebung: dict[str, str] | None = None):
        """Ruft die Aufbereitung mit `--ja` auf. Wie der Lauf ausgeht, prueft der Test."""
        return self.ordner.starte("bilder_aufbereiten.py", "--ja", umgebung=umgebung)

    def pruefe_jpeg(self, datei: Path, groesse: tuple[int, int]) -> None:
        with Image.open(datei) as bild:
            self.assertEqual(bild.format, "JPEG")
            self.assertEqual(bild.size, groesse)

    def lege_tiff_an(self, name: str, bild) -> Path:
        """Legt ein TIFF in `quellen/` ab, ohne Kompression wie vom Scanner."""
        datei = self.quellen / name
        datei.parent.mkdir(parents=True, exist_ok=True)
        bild.save(datei, "TIFF")
        return datei

    @BRAUCHT_PILLOW
    def test_ein_tiff_unter_der_schwelle_wird_zu_jpeg_mit_der_endung_jpg(self) -> None:
        tiff = self.ordner.lege_quellbild_an("scans/scan.tif", (400, 300))
        self.assertLess(tiff.stat().st_size, 2 * 1024 * 1024)

        fertig = self.starte()

        self.assertEqual(fertig.returncode, 0, fertig.stdout + fertig.stderr)
        self.assertEqual([p.name for p in (self.quellen / "scans").iterdir()], ["scan.jpg"],
                         "das Original ist weg, und es entsteht nichts daneben")
        self.pruefe_jpeg(self.quellen / "scans" / "scan.jpg", (400, 300))

    @BRAUCHT_PILLOW
    def test_ein_schweres_tiff_wird_dabei_verkleinert(self) -> None:
        self.ordner.lege_quellbild_an("scan.tiff", (3000, 2250))

        fertig = self.starte()

        self.assertEqual(fertig.returncode, 0, fertig.stdout + fertig.stderr)
        self.assertFalse((self.quellen / "scan.tiff").exists())
        self.pruefe_jpeg(self.quellen / "scan.jpg", (2000, 1500))

    @BRAUCHT_PILLOW
    def test_ein_graues_tiff_ohne_kompression_ist_danach_weg(self) -> None:
        # So scannt ein Buerogeraet eine Textseite. Pillow bildet ein solches
        # TIFF in den Speicher ab, statt es zu lesen. Haelt das Bild die Datei
        # offen, laesst Windows sie nicht loeschen, und neben dem JPEG bliebe
        # das Original liegen.
        tiff = self.lege_tiff_an("grau.tif", Image.new("L", (400, 300), 128))

        fertig = self.starte()

        self.assertEqual(fertig.returncode, 0, fertig.stdout + fertig.stderr)
        self.assertFalse(tiff.exists())
        self.pruefe_jpeg(self.quellen / "grau.jpg", (400, 300))

    @BRAUCHT_PILLOW
    def test_ein_tiff_mit_16_bit_graustufen_bleibt_grau(self) -> None:
        # Ein JPEG fasst 8 Bit je Pixel. Schnitte die Umwandlung alles ueber
        # 255 ab, kaeme der Scan fast weiss heraus, und das Original waere weg.
        self.lege_tiff_an("tief.tif", Image.new("I;16", (400, 300), 20000))

        fertig = self.starte()

        self.assertEqual(fertig.returncode, 0, fertig.stdout + fertig.stderr)
        with Image.open(self.quellen / "tief.jpg") as jpeg:
            grau = jpeg.convert("L").getpixel((200, 150))
        self.assertAlmostEqual(grau, 20000 // 256, delta=3)

    @BRAUCHT_PILLOW
    def test_ein_tiff_in_cmyk_wird_ein_jpeg_in_rgb(self) -> None:
        # Ein JPEG in CMYK zeigt mancher Betrachter falsch oder gar nicht.
        self.lege_tiff_an("druck.tif", Image.new("CMYK", (400, 300), (0, 0, 0, 0)))

        fertig = self.starte()

        self.assertEqual(fertig.returncode, 0, fertig.stdout + fertig.stderr)
        with Image.open(self.quellen / "druck.jpg") as jpeg:
            self.assertEqual(jpeg.mode, "RGB")

    @BRAUCHT_PILLOW_HEIF
    def test_ein_heic_wird_mit_pillow_heif_zu_jpeg(self) -> None:
        # So kommt ein Foto vom iPhone.
        self.ordner.lege_quellbild_an("IMG_0001.HEIC", (400, 300))

        fertig = self.starte()

        self.assertEqual(fertig.returncode, 0, fertig.stdout + fertig.stderr)
        self.assertEqual([p.name for p in self.quellen.iterdir()], ["IMG_0001.jpg"])
        self.pruefe_jpeg(self.quellen / "IMG_0001.jpg", (400, 300))

    @BRAUCHT_PILLOW
    def test_ohne_pillow_heif_bleibt_das_heic_liegen_und_der_rest_wird_aufbereitet(self) -> None:
        # Laeuft auch dort, wo pillow-heif installiert ist, siehe blende_aus().
        # Das HEIC muss dafuer nicht echt sein, geoeffnet wird es nicht.
        heic = self.ordner.lege_quelldatei_an("IMG_0001.heic", b"kein echtes HEIC")
        tiff = self.ordner.lege_quellbild_an("scan.tif", (400, 300))

        fertig = self.starte(umgebung=blende_aus(self, "pillow_heif"))

        self.assertNotEqual(fertig.returncode, 0,
                            "das HEIC bleibt unlesbar, gruen waere geschoent")
        self.assertIn("IMG_0001.heic", fertig.stdout)
        self.assertIn("pip install pillow-heif", fertig.stdout)
        self.assertEqual(heic.read_bytes(), b"kein echtes HEIC")
        self.assertFalse(tiff.exists())
        self.pruefe_jpeg(self.quellen / "scan.jpg", (400, 300))

    @BRAUCHT_PILLOW
    def test_eine_datei_auf_die_eine_karte_zeigt_bleibt_liegen(self) -> None:
        # Als .jpg braeche der Verweis. Die Angabe ist freier Text, hier mit
        # Seitenzahl dahinter.
        self.ordner.lege_karte_an(id="ue-000006", titel="Aus dem Scan",
                                  quelldatei="magazin/scan.tif, S. 12")
        tiff = self.ordner.lege_quellbild_an("magazin/scan.tif", (400, 300))
        vorher = tiff.read_bytes()

        fertig = self.starte()

        self.assertEqual(fertig.returncode, 0, fertig.stdout + fertig.stderr)
        self.assertEqual(tiff.read_bytes(), vorher)
        self.assertFalse((self.quellen / "magazin" / "scan.jpg").exists())
        self.assertIn("magazin/scan.tif", fertig.stdout)
        self.assertIn("ue-000006", fertig.stdout)

    @BRAUCHT_PILLOW
    def test_ein_heic_mit_karte_nennt_die_karte_auch_ohne_pillow_heif(self) -> None:
        # Mit dem Paket bliebe es genauso liegen. Der Hinweis gehoert der
        # Karte, und der Lauf ist gruen.
        self.ordner.lege_karte_an(id="ue-000006", titel="Vom iPhone",
                                  quelldatei="IMG_0001.heic")
        self.ordner.lege_quelldatei_an("IMG_0001.heic", b"kein echtes HEIC")

        fertig = self.starte(umgebung=blende_aus(self, "pillow_heif"))

        self.assertEqual(fertig.returncode, 0, fertig.stdout + fertig.stderr)
        self.assertIn("ue-000006", fertig.stdout)
        self.assertNotIn("pillow-heif", fertig.stdout)

    @BRAUCHT_PILLOW
    def test_ein_jpeg_auf_das_eine_karte_zeigt_wird_trotzdem_verkleinert(self) -> None:
        # Sein Name bleibt, der Verweis also auch.
        self.ordner.lege_karte_an(id="ue-000006", titel="Von der Seite",
                                  quelldatei="seite-01.jpg")
        datei = self.ordner.lege_quellbild_an("seite-01.jpg", (3000, 2250))

        fertig = self.starte()

        self.assertEqual(fertig.returncode, 0, fertig.stdout + fertig.stderr)
        with Image.open(datei) as bild:
            self.assertEqual(max(bild.size), 2000)

    @BRAUCHT_PILLOW
    def test_ein_tiff_neben_einem_jpeg_gleichen_namens_bleibt_liegen(self) -> None:
        # Das JPEG aus dem TIFF ueberschriebe das, das schon da liegt.
        tiff = self.ordner.lege_quellbild_an("scan.tif", (400, 300))
        jpeg = self.ordner.lege_quellbild_an("scan.jpg", (200, 100))
        vorher = jpeg.read_bytes()

        fertig = self.starte()

        self.assertNotEqual(fertig.returncode, 0, "das TIFF bleibt unlesbar")
        self.assertTrue(tiff.exists())
        self.assertEqual(jpeg.read_bytes(), vorher)
        self.assertIn("scan.tif", fertig.stdout)

    @BRAUCHT_PILLOW
    def test_ein_mehrseitiges_tiff_bleibt_liegen(self) -> None:
        # Ein JPEG fasst eine Seite. Ab der zweiten ginge alles verloren.
        tiff = self.quellen / "zwei-seiten.tif"
        tiff.parent.mkdir(parents=True, exist_ok=True)
        seite = Image.new("RGB", (400, 300), "white")
        seite.save(tiff, "TIFF", save_all=True, append_images=[seite.copy()])
        vorher = tiff.read_bytes()

        fertig = self.starte()

        self.assertNotEqual(fertig.returncode, 0)
        self.assertIn("FEHLER", fertig.stdout)
        self.assertEqual(tiff.read_bytes(), vorher)
        self.assertFalse((self.quellen / "zwei-seiten.jpg").exists())

    @BRAUCHT_PILLOW
    def test_die_rueckfrage_nennt_die_neue_endung(self) -> None:
        # Wer zustimmt, soll wissen, dass aus scan.tif ein scan.jpg wird.
        tiff = self.ordner.lege_quellbild_an("scan.tif", (400, 300))

        fertig = self.ordner.starte("bilder_aufbereiten.py")

        self.assertEqual(fertig.stdout.count("Weiter? [j/N]"), 1)
        self.assertIn("als JPEG mit .jpg", fertig.stdout)
        self.assertTrue(tiff.exists(), "ohne Zustimmung bleibt das Original")


if __name__ == "__main__":
    unittest.main()
