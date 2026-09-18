"""Prueft den Linter gegen einen kuenstlichen Arbeitsordner.

    <python> -m unittest discover -s plugins/volleyball/tests

Der Linter ist `index.py`. Geprueft wird, was auf der Konsole ankommt: das ist
es, was ein Skill und ein Mensch zu sehen bekommen, und damit der Vertrag.
Eine interne Pruefroutine direkt aufzurufen hiesse, ihre Verdrahtung
nachzubauen. Der Test braeche dann beim ersten Umbau, ohne dass sich das
Verhalten geaendert haette.
"""

from __future__ import annotations

import unittest

from arbeitsordner import OHNE, Arbeitsordner


def auffaelligkeiten(ausgabe: str) -> list[str]:
    """Zieht die gemeldeten Zeilen aus der Ausgabe von index.py.

    Jede Auffaelligkeit steht in einer eigenen Zeile mit fuehrendem "  - ".
    Mehr Struktur hat die Ausgabe des Linters heute nicht.
    """
    return [zeile[4:] for zeile in ausgabe.splitlines() if zeile.startswith("  - ")]


class LinterTest(unittest.TestCase):
    def setUp(self) -> None:
        self.ordner = Arbeitsordner()
        self.addCleanup(self.ordner.raeume_auf)

    def test_sauberer_arbeitsordner_meldet_nichts(self) -> None:
        fertig = self.ordner.starte("index.py")

        self.assertEqual(fertig.returncode, 0, fertig.stderr)
        # Zeigt zugleich, dass der Fixture ueberhaupt gelesen wurde: ein leerer
        # Ordner waere ebenfalls ohne Auffaelligkeit.
        self.assertIn(f"Übungen: {len(self.ordner.ids)}", fertig.stdout)
        self.assertEqual(auffaelligkeiten(fertig.stdout), [])
        self.assertIn("Keine Auffälligkeiten", fertig.stdout)

    def test_unbekannter_schwerpunkt_wird_gemeldet(self) -> None:
        self.ordner.lege_karte_an(
            id="ue-0009",
            titel="Karte mit erfundenem Schwerpunkt",
            schwerpunkt=["gibt-es-nicht"],
        )

        fertig = self.ordner.starte("index.py")

        gemeldet = auffaelligkeiten(fertig.stdout)
        self.assertEqual(len(gemeldet), 1, fertig.stdout)
        self.assertIn("ue-0009", gemeldet[0])
        self.assertIn("gibt-es-nicht", gemeldet[0])

    def test_fehlende_disziplin_wird_gemeldet(self) -> None:
        # Das ist der Fall, fuer den es keinen stillen Default gibt: eine Karte,
        # bei der das Feld beim Import vergessen wurde.
        self.ordner.lege_karte_an(
            id="ue-0010", titel="Karte ganz ohne Disziplin", disziplin=OHNE,
        )

        gemeldet = auffaelligkeiten(self.ordner.starte("index.py").stdout)

        self.assertEqual(len(gemeldet), 1, gemeldet)
        self.assertIn("ue-0010", gemeldet[0])
        self.assertIn("disziplin", gemeldet[0])

    def test_leere_disziplin_wird_gemeldet(self) -> None:
        self.ordner.lege_karte_an(
            id="ue-0011", titel="Karte mit leerer Disziplinliste", disziplin=[],
        )

        gemeldet = auffaelligkeiten(self.ordner.starte("index.py").stdout)

        self.assertEqual(len(gemeldet), 1, gemeldet)
        self.assertIn("ue-0011", gemeldet[0])
        self.assertIn("disziplin", gemeldet[0])

    def test_unbekannte_disziplin_wird_gemeldet(self) -> None:
        # Ein Tippfehler macht die Karte sonst unauffindbar: kein Filter trifft
        # sie mehr.
        self.ordner.lege_karte_an(
            id="ue-0012", titel="Karte mit erfundener Disziplin", disziplin=["strand"],
        )

        gemeldet = auffaelligkeiten(self.ordner.starte("index.py").stdout)

        self.assertEqual(len(gemeldet), 1, gemeldet)
        self.assertIn("ue-0012", gemeldet[0])
        self.assertIn("strand", gemeldet[0])

    def test_disziplin_als_einzelwert_wird_gemeldet(self) -> None:
        # `disziplin: halle` statt `disziplin: [halle]`. Ohne eigene Pruefung
        # liefe die Wertepruefung ueber die Buchstaben und meldete fuenfmal.
        self.ordner.lege_karte_an(
            id="ue-0013", titel="Karte mit Disziplin ohne Klammern", disziplin="halle",
        )

        gemeldet = auffaelligkeiten(self.ordner.starte("index.py").stdout)

        self.assertEqual(len(gemeldet), 1, gemeldet)
        self.assertIn("ue-0013", gemeldet[0])
        self.assertIn("disziplin", gemeldet[0])

    def test_karte_fuer_halle_und_beach_meldet_nichts(self) -> None:
        self.ordner.lege_karte_an(
            id="ue-0014", titel="Karte für beide Disziplinen", disziplin=["halle", "beach"],
        )

        fertig = self.ordner.starte("index.py")

        self.assertEqual(auffaelligkeiten(fertig.stdout), [])


if __name__ == "__main__":
    unittest.main()
