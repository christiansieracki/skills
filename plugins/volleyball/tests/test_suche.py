"""Prueft die Suche gegen einen kuenstlichen Arbeitsordner.

    <python> -m unittest discover -s plugins/volleyball/tests

Gesucht wird ueber die Kommandozeile und mit `--json`, so wie ein Skill es
tut, der die Treffer weiterverarbeitet. Die Zusagen, die hier festgehalten
werden, sind die beiden, die sich am leichtesten unbemerkt verlieren: dass
`--spieler` die Anwesenden meint und keine Obergrenze, und dass zu wenige
Spielflaechen eine Uebung wirklich herausfallen lassen.
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


if __name__ == "__main__":
    unittest.main()
