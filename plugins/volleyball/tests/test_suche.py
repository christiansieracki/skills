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


if __name__ == "__main__":
    unittest.main()
