"""Prueft die Leseansicht eines Trainingsplans gegen einen kuenstlichen Arbeitsordner.

    <python> -m unittest discover -s plugins/volleyball/tests

Erzeugt wird ueber die Kommandozeile, wie der Skill es tut, und gelesen wird
die HTML-Datei, die dabei neben dem Plan entsteht. `leseansicht.py` nimmt kein
`--wurzel`, es findet den Arbeitsordner ueber den Pfad des Plans.

Die Bilder kommen hier als Verweis statt eingebettet. Dann steht der Name
jeder Datei im HTML, und ihre Reihenfolge laesst sich ablesen. Welche Datei
gezeigt wird, entscheidet dieselbe Stelle wie beim Einbetten.
"""

from __future__ import annotations

import re
import unittest

from arbeitsordner import Arbeitsordner

PLAN = "gruppe/2026-09-15.md"


class SchaubildTest(unittest.TestCase):
    def setUp(self) -> None:
        self.ordner = Arbeitsordner()
        self.addCleanup(self.ordner.raeume_auf)

    def bilder(self, *ids: str) -> list[str]:
        """Erzeugt die Leseansicht eines Plans mit diesen IDs. Gibt die Bilder in ihrer Folge zurueck.

        Je Bild der Dateiname, auf den es verweist.
        """
        plan = self.ordner.lege_trainingsplan_an(PLAN, *ids)
        fertig = self.ordner.starte("leseansicht.py", str(plan), "--bilder", "verweis",
                                    mit_wurzel=False)
        self.assertEqual(fertig.returncode, 0, fertig.stdout + fertig.stderr)
        html = plan.with_suffix(".html").read_text(encoding="utf-8")
        return [quelle.rsplit("/", 1)[-1] for quelle in re.findall(r'<img src="([^"]+)"', html)]

    def test_ein_einzelnes_schaubild_steht_bei_seiner_uebung(self) -> None:
        self.ordner.lege_schaubild_an("ue-000030-aufbau.svg")
        self.ordner.lege_karte_an(id="ue-000030", titel="Mit einem Bild",
                                  schaubild="ue-000030-aufbau.svg")

        self.assertEqual(self.bilder("ue-000030"), ["ue-000030-aufbau.svg"])

    def test_eine_liste_zeigt_alle_bilder_in_ihrer_reihenfolge(self) -> None:
        # Absichtlich nicht alphabetisch: Die Folge kommt von der Karte, bei
        # einem Zirkel das Uebersichtsblatt vorn (#39).
        namen = ["ue-000031-uebersicht.png", "ue-000031-station-2.png",
                 "ue-000031-station-1.png"]
        for name in namen:
            self.ordner.lege_schaubild_an(name)
        self.ordner.lege_karte_an(id="ue-000031", titel="Zirkel mit drei Bildern",
                                  schaubild=namen)

        self.assertEqual(self.bilder("ue-000031"), namen)

    def test_fehlt_ein_bild_der_liste_faellt_nur_dieses_weg(self) -> None:
        # Wie bei einem einzelnen Bild: Eine Leseansicht ohne ein Bild ist
        # brauchbar, eine mit totem Verweis nicht. Den Verweis meldet der
        # Linter.
        for name in ("ue-000032-zirkel-1.png", "ue-000032-zirkel-3.png"):
            self.ordner.lege_schaubild_an(name)
        self.ordner.lege_karte_an(
            id="ue-000032", titel="Zirkel mit einem fehlenden Bild",
            schaubild=["ue-000032-zirkel-1.png", "ue-000032-zirkel-2.png",
                       "ue-000032-zirkel-3.png"])

        self.assertEqual(self.bilder("ue-000032"),
                         ["ue-000032-zirkel-1.png", "ue-000032-zirkel-3.png"])


if __name__ == "__main__":
    unittest.main()
