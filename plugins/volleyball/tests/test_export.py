"""Prueft den PDF-Export: ueber den Browser, und was ein Fehlschlag zurueckgibt.

    <python> -m unittest discover -s plugins/volleyball/tests

Aufgerufen wird ueber die Kommandozeile, wie die Skills es tun. Gemessen wird
am Ergebnis auf der Platte: liegt das PDF da, wenn das Skript fertig ist.

Der Test des Browsers laeuft nur, wo das Skript den Weg ueber Edge oder Chrome
waehlt. Auf einem Rechner mit pandoc und einer PDF-Maschine wird er
uebersprungen, denn dort gibt es den Fehler nicht, den er festhaelt. Welcher
Weg es ist, sagt die erste Zeile der Ausgabe. Danach zu fragen ist billiger,
als die Wahl hier nachzubauen.

Ein Druck ueber Edge dauert einige Sekunden. Deshalb druckt der Test des
Browsers nur zwei Dateien, so wenige, wie es braucht, damit sich zwei Drucke
einen Profilordner teilen.
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

    def test_die_pdfs_liegen_da_auch_mit_kompatibilitaetsschicht(self) -> None:
        # Windows setzt __COMPAT_LAYER fuer Prozesse, die aus manchen
        # Anwendungen heraus starten, etwa aus der Claude-App. Edge startet
        # sich dann ohne die Variable neu und der erste Prozess kehrt sofort
        # zurueck, lange bevor das PDF geschrieben ist.
        #
        # Zwei Plaene, weil sich alle Drucke eines Laufs einen Profilordner
        # teilen. Der zweite Druck darf nicht an einen Browser geraten, der
        # den Ordner vom ersten noch haelt, und dort verloren gehen.
        quelle = self.ordner.pfad / "trainings" / "gruppe"
        quelle.mkdir(parents=True)
        for datum in ("2026-01-01", "2026-01-02"):
            (quelle / f"{datum}.md").write_text(TRAINING, encoding="utf-8")
        ausgabe = self.ordner.pfad / "pdf"

        fertig = self.ordner.starte(
            "export_pdf.py", str(quelle), "-o", str(ausgabe),
            mit_wurzel=False,
            umgebung={"__COMPAT_LAYER": "DetectorsAppHealth"},
        )

        if "Druckmodus" not in fertig.stdout.split("\n", 1)[0]:
            self.skipTest("dieser Rechner druckt nicht ueber den Browser")
        self.assertEqual(fertig.returncode, 0, fertig.stdout + fertig.stderr)
        self.assertIn("Fertig: 2/2", fertig.stdout, fertig.stdout)
        for datum in ("2026-01-01", "2026-01-02"):
            self.assertTrue((ausgabe / f"{datum}.pdf").is_file(), fertig.stdout)


class FehlschlagTest(unittest.TestCase):
    """Ein Fehlschlag zeigt sich am Rueckgabewert, nicht erst in der Ausgabe.

    Saisonplaner und Trainingsdesign rufen das Skript auf und lesen den
    Rueckgabewert. Dafuer muss eine einzige fehlende Datei reichen, nicht erst
    ein Lauf, in dem gar nichts entstanden ist.

    Die zweite Datei scheitert, weil an der Stelle ihres Ordners in der
    Ausgabe schon eine Datei liegt. Das geht auf jedem Weg zum PDF schief, auch
    ohne Browser.
    """

    def setUp(self) -> None:
        self.ordner = Arbeitsordner()
        self.addCleanup(self.ordner.raeume_auf)

    def test_eine_fehlende_datei_endet_mit_einem_fehler(self) -> None:
        quelle = self.ordner.pfad / "trainings"
        for gruppe in ("a", "b"):
            (quelle / gruppe).mkdir(parents=True)
            (quelle / gruppe / "2026-01-01.md").write_text(TRAINING, encoding="utf-8")
        ausgabe = self.ordner.pfad / "pdf"
        ausgabe.mkdir()
        (ausgabe / "b").write_text("versperrt den Ordner b", encoding="utf-8")

        fertig = self.ordner.starte(
            "export_pdf.py", str(quelle), "-o", str(ausgabe), mit_wurzel=False)

        if "Kein Weg zum PDF" in fertig.stdout:
            self.skipTest("dieser Rechner kann kein PDF erzeugen")
        self.assertIn("Fertig: 1/2", fertig.stdout, fertig.stdout + fertig.stderr)
        self.assertNotEqual(fertig.returncode, 0, fertig.stdout)


if __name__ == "__main__":
    unittest.main()
