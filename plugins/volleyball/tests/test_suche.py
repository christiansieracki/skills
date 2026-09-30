"""Prueft die Suche gegen einen kuenstlichen Arbeitsordner.

    <python> -m unittest discover -s plugins/volleyball/tests

Gesucht wird ueber die Kommandozeile und mit `--json`, so wie ein Skill es
tut, der die Treffer weiterverarbeitet. Die Zusagen, die hier festgehalten
werden, sind die, die sich am leichtesten unbemerkt verlieren: dass
`--spieler` die Anwesenden meint und keine Obergrenze, dass zu wenige
Spielflaechen eine Uebung wirklich herausfallen lassen, und was der
Disziplinfilter durchlaesst. Am letzten haengt, ob beim Planen einer
Beacheinheit eine Hallenuebung im Ergebnis steht.
"""

from __future__ import annotations

import json
import unittest

from arbeitsordner import Arbeitsordner


class SucheTest(unittest.TestCase):
    def setUp(self) -> None:
        self.ordner = Arbeitsordner()
        self.addCleanup(self.ordner.raeume_auf)

    def treffer(self, *argumente: str) -> list[dict]:
        """Sucht und gibt die maschinenlesbare Ausgabe zurueck.

        `json.loads` ist hier die eigentliche Zusicherung: die Ausgabe laesst
        sich ohne Textparserei auswerten.
        """
        fertig = self.ordner.starte("suche.py", "--json", *argumente)
        self.assertEqual(fertig.returncode, 0, fertig.stderr)
        return json.loads(fertig.stdout)

    def quelldateizeile(self, uid: str, *vorhanden: str, **felder) -> str:
        """Legt eine Karte an und gibt ihre Quelldatei-Zeile zurueck.

        Die Faelle weiter unten unterscheiden sich darin, wie die
        `quelldatei:` auf der Karte geschrieben ist und welche Dateien unter
        `quellen/` liegen, und pruefen alle dieselbe eine Zeile. `vorhanden`
        nennt diese Dateien relativ zu `quellen/`. Ihr Inhalt zaehlt nicht,
        nur dass es sie gibt.
        """
        for name in vorhanden:
            self.ordner.lege_quelldatei_an(name, b"")
        self.ordner.lege_karte_an(id=uid, **felder)
        fertig = self.ordner.starte("suche.py", "--id", uid, "--lang")
        self.assertEqual(fertig.returncode, 0, fertig.stderr)
        zeilen = [z for z in fertig.stdout.splitlines() if "Quelldatei" in z]
        self.assertEqual(1, len(zeilen), f"keine Quelldatei-Zeile:\n{fertig.stdout}")
        return zeilen[0]

    def test_ohne_filter_kommen_alle_uebungen_zurueck(self) -> None:
        # Der Fixture traegt Karten beider Disziplinen. Der Test haelt damit
        # auch fest, dass ohne Disziplinfilter alles zurueckkommt.
        gefunden = self.treffer()

        self.assertEqual(sorted(e["id"] for e in gefunden), sorted(self.ordner.ids))

    def test_jeder_treffer_traegt_die_felder_seiner_karte(self) -> None:
        (gefunden,) = self.treffer("--id", "ue-0003")

        self.assertEqual(gefunden["titel"], "Sideout-Serie über zwei Spielflächen")
        self.assertEqual(gefunden["element"], ["annahme", "angriff"])
        # Steht `disziplin` nicht in der Index-Projektion, erreicht das Feld die
        # Suche gar nicht, egal wie sauber es auf der Karte gepflegt ist.
        self.assertEqual(gefunden["disziplin"], ["halle"])
        self.assertEqual(gefunden["spielflaechen"], 2)
        self.assertEqual(gefunden["spieler_max"], 16)
        self.assertIs(gefunden["netz"], True)

    def test_zu_wenige_spielflaechen_lassen_die_uebung_herausfallen(self) -> None:
        gefunden = [e["id"] for e in self.treffer("--spielflaechen", "1")]

        self.assertNotIn("ue-0003", gefunden)  # braucht zwei
        self.assertIn("ue-0002", gefunden)     # kommt mit einem aus

    def test_mehr_anwesende_als_die_obergrenze_bleiben_ein_treffer(self) -> None:
        # ue-0002 ist fuer hoechstens vier Spieler gedacht. Bei zwoelf
        # Anwesenden laeuft sie in drei Gruppen, sie faellt nicht heraus.
        gefunden = [e["id"] for e in self.treffer("--spieler", "12")]

        self.assertIn("ue-0002", gefunden)

    def test_die_trefferzeile_nennt_spielflaechen_und_gruppen(self) -> None:
        # Die lesbare Ausgabe zeigt zwei Dinge, die die JSON-Fassung nicht
        # hergibt: die Beschriftung des Spielflaechenfeldes und die Zahl der
        # Gruppen, in denen die Uebung bei so vielen Anwesenden laeuft.
        fertig = self.ordner.starte("suche.py", "--id", "ue-0002", "--spieler", "12", "--lang")

        self.assertEqual(fertig.returncode, 0, fertig.stderr)
        self.assertIn("[3 Gruppen parallel]", fertig.stdout)
        self.assertIn("Spielflächen 1", fertig.stdout)

    def test_mit_genau_zaehlt_die_obergrenze_dann_doch(self) -> None:
        gefunden = [e["id"] for e in self.treffer("--spieler", "12", "--genau")]

        self.assertNotIn("ue-0002", gefunden)  # Obergrenze 4
        self.assertIn("ue-0003", gefunden)     # 12 bis 16

    def test_der_disziplinfilter_beach_laesst_die_hallenkarte_draussen(self) -> None:
        gefunden = [e["id"] for e in self.treffer("--disziplin", "beach")]

        self.assertIn("ue-0004", gefunden)     # nur beach
        self.assertIn("ue-0005", gefunden)     # halle und beach
        self.assertNotIn("ue-0001", gefunden)  # nur halle

    def test_der_disziplinfilter_halle_laesst_die_beachkarte_draussen(self) -> None:
        gefunden = [e["id"] for e in self.treffer("--disziplin", "halle")]

        self.assertIn("ue-0001", gefunden)
        self.assertIn("ue-0005", gefunden)
        self.assertNotIn("ue-0004", gefunden)

    def test_beide_werte_zusammen_treffen_jede_disziplin(self) -> None:
        # Mehrere Werte sind erlaubt und werden als Mengenschnitt gegen die
        # Liste auf der Karte verknuepft, genau wie beim Element.
        gefunden = [e["id"] for e in self.treffer("--disziplin", "halle", "beach")]

        self.assertIn("ue-0001", gefunden)  # nur halle
        self.assertIn("ue-0004", gefunden)  # nur beach
        self.assertIn("ue-0005", gefunden)  # beides

    def test_auch_die_kurze_trefferliste_nennt_die_disziplin(self) -> None:
        # Ab vier Treffern faellt die ausfuehrliche Darstellung weg. Gerade
        # dann soll auffallen, dass da eine Beachkarte zwischen den
        # Hallenkarten steht.
        fertig = self.ordner.starte("suche.py")

        self.assertEqual(fertig.returncode, 0, fertig.stderr)
        zeile = next(z for z in fertig.stdout.splitlines() if z.startswith("ue-0004"))
        self.assertIn("beach", zeile)

    def test_die_ausfuehrliche_ausgabe_beschriftet_die_disziplin(self) -> None:
        fertig = self.ordner.starte("suche.py", "--id", "ue-0005", "--lang")

        self.assertEqual(fertig.returncode, 0, fertig.stderr)
        self.assertIn("Disziplin    halle, beach", fertig.stdout)

    def test_eine_vorhandene_einzelne_datei_wird_zu_einem_pfad(self) -> None:
        # Der haeufigste Fall: jede PlayDrill-Karte nennt genau eine Datei.
        # Liegt sie unter quellen/, steht dort ein Pfad, den man kopieren
        # kann, so wie `schaubilder/<datei>` in der Zeile darueber.
        zeile = self.quelldateizeile(
            "ue-0013", "playdrill/Annahme Diagonal.pdf",
            titel="Annahme diagonal",
            quelldatei="playdrill/Annahme Diagonal.pdf")

        self.assertEqual(
            "    Quelldatei   quellen/playdrill/Annahme Diagonal.pdf", zeile)

    def test_eine_fehlende_datei_wird_nicht_zu_einem_pfad(self) -> None:
        # Ein Mittrainer, dessen Nextcloud quellen/ nicht synchronisiert, hat
        # die Datei nicht. Die Zeile sieht bei ihm aus wie bisher, statt ihm
        # einen Pfad zu zeigen, unter dem nichts liegt.
        zeile = self.quelldateizeile(
            "ue-0014", titel="Annahme diagonal, ohne Quellen",
            quelldatei="playdrill/Annahme Diagonal.pdf")

        self.assertEqual(
            "    Quelldatei   in quellen/ · playdrill/Annahme Diagonal.pdf", zeile)

    def test_ein_absoluter_pfad_bekommt_kein_quellen_davor(self) -> None:
        # `quelldatei:` steht relativ zu quellen/, damit sie auf jedem Rechner
        # stimmt. Steht dort doch ein absoluter Pfad, zeigt er auf eine Datei,
        # die es gibt, und `quellen/` davor ergaebe trotzdem keinen Pfad.
        datei = self.ordner.lege_quelldatei_an("playdrill/Annahme Diagonal.pdf", b"")
        zeile = self.quelldateizeile(
            "ue-0016", titel="Annahme diagonal, absolut verwiesen",
            quelldatei=datei.as_posix())

        self.assertEqual(
            f"    Quelldatei   in quellen/ · {datei.as_posix()}", zeile)

    def test_eine_liste_statt_freiem_text_laesst_die_suche_nicht_abbrechen(self) -> None:
        # Das Feld ist freier Text, aber wer zwei Seiten in eckige Klammern
        # setzt, bekommt vom Parser eine Liste. Die ist kein Pfad, und die
        # Suche darf an ihr nicht scheitern.
        zeile = self.quelldateizeile(
            "ue-0015", "magazin/seite-04.jpg", "magazin/seite-05.jpg",
            titel="Abwehr über zwei Seiten, als Liste",
            quelldatei=["magazin/seite-04.jpg", "magazin/seite-05.jpg"])

        self.assertIn("in quellen/", zeile)
        self.assertEqual(1, zeile.count("quellen/"))

    def test_eine_uebung_ueber_zwei_seiten_nennt_beide_seiten(self) -> None:
        # Eine Uebung hoert selten da auf, wo die Seite aufhoert. Laeuft sie
        # ueber zwei Fotos, nennt `quelldatei:` laut DATENMODELL.md beide, und
        # beide liegen unter quellen/. Ein Praefix am Anfang der Angabe saesse
        # nur vor der ersten.
        zeile = self.quelldateizeile(
            "ue-0010", "magazin/seite-04.jpg", "magazin/seite-05.jpg",
            titel="Abwehr über zwei Seiten",
            quelldatei="magazin/seite-04.jpg, magazin/seite-05.jpg")

        self.assertIn("in quellen/", zeile)
        self.assertIn("magazin/seite-04.jpg, magazin/seite-05.jpg", zeile)
        self.assertEqual(1, zeile.count("quellen/"))

    def test_zwei_seiten_mit_und_getrennt_werden_genauso_gezeigt(self) -> None:
        # Das Feld ist freier Text, und wer zwei Seiten nennt, trennt sie mal
        # mit einem Komma und mal mit einem "und". An der Schreibweise darf
        # die Ausgabe nicht haengen: die zweite Seite soll in beiden Faellen
        # genauso dastehen wie die erste.
        zeile = self.quelldateizeile(
            "ue-0011", "magazin/seite-04.jpg", "magazin/seite-05.jpg",
            titel="Abwehr über zwei Seiten, anders geschrieben",
            quelldatei="magazin/seite-04.jpg und magazin/seite-05.jpg")

        self.assertIn("in quellen/", zeile)
        self.assertIn("magazin/seite-04.jpg und magazin/seite-05.jpg", zeile)
        self.assertEqual(1, zeile.count("quellen/"))

    def test_was_keine_datei_ist_wird_nicht_zu_einem_pfad(self) -> None:
        # Hinter dem Dateinamen steht oft eine Seitenzahl, und der Bestand
        # fuehrt Namen mit Leerzeichen darin. Nichts davon ist ein eigener
        # Pfad: `quellen/S. 1` gibt es nicht. Die Datei selbst liegt da, aber
        # der Wert ist mehr als ihr Name.
        zeile = self.quelldateizeile(
            "ue-0012", "unsortiert/Vorschlag Dienstag 14.09.23 _ H1.pdf",
            titel="Vorschlag aus der Sammlung",
            quelldatei="unsortiert/Vorschlag Dienstag 14.09.23 _ H1.pdf, S. 1")

        self.assertIn(
            "in quellen/ · unsortiert/Vorschlag Dienstag 14.09.23 _ H1.pdf, S. 1",
            zeile)
        self.assertEqual(1, zeile.count("quellen/"))


if __name__ == "__main__":
    unittest.main()
