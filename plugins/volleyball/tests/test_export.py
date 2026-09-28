"""Prueft den PDF-Export ueber den Browser.

    <python> -m unittest discover -s plugins/volleyball/tests

Aufgerufen wird ueber die Kommandozeile, wie die Skills es tun. Gemessen wird
am Ergebnis auf der Platte: liegt das PDF da, wenn das Skript fertig ist.

Der Test laeuft nur, wo das Skript den Weg ueber Edge oder Chrome waehlt. Auf
einem Rechner mit pandoc und einer PDF-Maschine wird er uebersprungen, denn
dort gibt es den Fehler nicht, den er festhaelt. Welcher Weg es ist, sagt die
erste Zeile der Ausgabe. Danach zu fragen ist billiger, als die Wahl hier
nachzubauen.

Ein Druck ueber Edge dauert zehn bis zwanzig Sekunden. Deshalb nur eine Datei.
"""

from __future__ import annotations

import unittest

from arbeitsordner import Arbeitsordner

TRAINING = """\
# Training 01.01.2026

Kurz, damit der Druck schnell geht.
"""


class ExportUeberBrowserTest(unittest.TestCase):
    def setUp(self) -> None:
        self.ordner = Arbeitsordner()
        self.addCleanup(self.ordner.raeume_auf)

    def test_das_pdf_liegt_da_auch_mit_kompatibilitaetsschicht(self) -> None:
        # Windows setzt __COMPAT_LAYER fuer Prozesse, die aus manchen
        # Anwendungen heraus starten, etwa aus der Claude-App. Edge startet
        # sich dann ohne die Variable neu und der erste Prozess kehrt sofort
        # zurueck, lange bevor das PDF geschrieben ist.
        quelle = self.ordner.pfad / "trainings" / "gruppe"
        quelle.mkdir(parents=True)
        (quelle / "2026-01-01.md").write_text(TRAINING, encoding="utf-8")
        ausgabe = self.ordner.pfad / "pdf"

        fertig = self.ordner.starte(
            "export_pdf.py", str(quelle), "-o", str(ausgabe),
            mit_wurzel=False,
            umgebung={"__COMPAT_LAYER": "DetectorsAppHealth"},
        )

        if "Druckmodus" not in fertig.stdout.split("\n", 1)[0]:
            self.skipTest("dieser Rechner druckt nicht ueber den Browser")
        self.assertEqual(fertig.returncode, 0, fertig.stdout + fertig.stderr)
        self.assertIn("Fertig: 1/1", fertig.stdout, fertig.stdout)
        self.assertTrue((ausgabe / "2026-01-01.pdf").is_file(), fertig.stdout)


if __name__ == "__main__":
    unittest.main()
