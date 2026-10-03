"""Prueft `ids_umstellen.py` gegen einen kuenstlichen Arbeitsordner von vor 3.0.0.

    <python> -m unittest discover -s plugins/volleyball/tests

Das Skript bricht die Regel, dass eine vergebene ID sich nie aendert, ein
einziges Mal (ADR-0011). Darum muss es ueberall zugleich umstellen, wo eine ID
steht: Ein Verweis, der vierstellig bleibt, zeigt danach ins Leere. Geprueft
wird ueber die Kommandozeile und an den Dateien danach. Was das Skript sagt,
ist der eine Teil des Vertrags, was auf der Platte liegt, der andere.
"""

from __future__ import annotations

import re
import shutil
import socket
import tempfile
import unittest
from pathlib import Path

from arbeitsordner import Arbeitsordner, auffaelligkeiten

PLAN = "gruppe/2026-09-15.md"
VIERSTELLIG = re.compile(r"\bue-\d{4}\b")


class IdsUmstellenTest(unittest.TestCase):
    def setUp(self) -> None:
        # Ein Arbeitsordner, wie 2.5.1 ihn hinterlaesst, mit einer ID an jeder
        # Stelle, an der eine stehen kann.
        self.ordner = Arbeitsordner(vor_der_umstellung=True)
        self.addCleanup(self.ordner.raeume_auf)
        self.ordner.lege_schaubild_an("ue-0006-aufbau.png")
        # Erst die Szene, dann das Bild aus ihr: Ein Bild, das aelter ist als
        # seine Szene, meldet der Linter (#47).
        self.ordner.lege_szene_an("ue-0006", """
            form: halle
            titel: Variante mit Schaubild
        """)
        self.ordner.lege_schaubild_an("ue-0006.svg")
        self.ordner.lege_karte_an(id="ue-0006", titel="Variante mit Schaubild",
                                  schaubild="ue-0006-aufbau.png", variante_von="ue-0002")
        plan = self.ordner.lege_trainingsplan_an(PLAN, "ue-0001", "ue-0006")
        plan.with_suffix(".html").write_text("<p>ue-0001 Annahme im Halbfeld</p>\n",
                                             encoding="utf-8")
        self.ordner.lege_quellenordner_an("playdrill", [
            {"kandidat": 1, "dateien": ["a.pdf"], "status": "importiert", "karte": "ue-0003"},
        ])
        self.ordner.lege_quelldatei_an("playdrill/log.md", "ue-0004 von Hand importiert\n".encode())
        (self.ordner.pfad / "index.md").write_text("| ue-0001 | Annahme im Halbfeld |\n",
                                                   encoding="utf-8")

    def stelle_um(self, *argumente: str):
        return self.ordner.starte("ids_umstellen.py", "--trainer", "christian", *argumente)

    def stand(self) -> dict[str, bytes]:
        """Jede Datei im Arbeitsordner mit ihrem Inhalt, Byte fuer Byte."""
        return {p.relative_to(self.ordner.pfad).as_posix(): p.read_bytes()
                for p in sorted(self.ordner.pfad.rglob("*")) if p.is_file()}

    def lies(self, pfad: str) -> str:
        return (self.ordner.pfad / pfad).read_text(encoding="utf-8")

    def test_ohne_schreiben_zeigt_es_jede_aenderung_und_schreibt_nichts(self) -> None:
        vorher = self.stand()

        fertig = self.stelle_um()

        self.assertEqual(fertig.returncode, 0, fertig.stdout + fertig.stderr)
        self.assertEqual(self.stand(), vorher)
        for erwartet in (
            "uebungen/ue-000001-annahme-im-halbfeld.md",
            "schaubilder/ue-000006-aufbau.png",
            "schaubilder/ue-000006.svg",
            "schaubilder/ue-000006.szene.yml",
            f"trainings/{PLAN}",
            "quellen/playdrill/sammelimport.md",
            "quellen/playdrill/log.md",
            "trainer:",
        ):
            self.assertIn(erwartet, fertig.stdout)

    def test_mit_schreiben_heisst_jede_id_sechsstellig(self) -> None:
        fertig = self.stelle_um("--schreiben")

        self.assertEqual(fertig.returncode, 0, fertig.stdout + fertig.stderr)
        karten = sorted(p.name for p in (self.ordner.pfad / "uebungen").glob("*.md"))
        self.assertEqual([name[:len("ue-000000")] for name in karten],
                         [f"ue-00000{n}" for n in range(1, 7)])
        self.assertEqual(
            sorted(p.name for p in (self.ordner.pfad / "schaubilder").iterdir()),
            ["ue-000006-aufbau.png", "ue-000006.svg", "ue-000006.szene.yml"])
        karte = self.lies("uebungen/ue-000006-variante-mit-schaubild.md")
        self.assertIn("\nid: ue-000006\n", karte)
        self.assertIn("\nschaubild: ue-000006-aufbau.png\n", karte)
        self.assertIn("\nvariante_von: ue-000002\n", karte)
        plan = self.lies(f"trainings/{PLAN}")
        self.assertIn("| ue-000001 |", plan)
        self.assertIn("| ue-000006 |", plan)
        self.assertEqual(self.ordner.uebersicht("playdrill")["1"]["Karte"], "ue-000003")
        self.assertIn("ue-000004", self.lies("quellen/playdrill/log.md"))
        for pfad, inhalt in self.stand().items():
            if pfad.endswith((".md", ".yml")) and pfad != "index.md":
                self.assertIsNone(VIERSTELLIG.search(inhalt.decode("utf-8")), pfad)

    def test_danach_vergibt_dieser_rechner_als_trainer_00(self) -> None:
        self.stelle_um("--schreiben")

        fertig = self.ordner.starte("suche.py", "--naechste-id")

        self.assertEqual(fertig.returncode, 0, fertig.stderr)
        self.assertEqual(fertig.stdout.strip(), "ue-000007")
        wurzeldatei = self.lies("trainingsplanung-root.yml")
        self.assertIn("christian:", wurzeldatei)
        self.assertIn(socket.gethostname(), wurzeldatei)

    def test_erzeugtes_bleibt_und_das_skript_sagt_womit_es_neu_entsteht(self) -> None:
        vorher = self.stand()

        fertig = self.stelle_um("--schreiben")

        nachher = self.stand()
        self.assertEqual(nachher["index.md"], vorher["index.md"])
        html = f"trainings/{PLAN[:-len('.md')]}.html"
        self.assertEqual(nachher[html], vorher[html])
        self.assertIn("index.py --md", fertig.stdout)
        self.assertIn(f"leseansicht.py trainings/{PLAN}", fertig.stdout)

    def test_danach_meldet_der_linter_nichts(self) -> None:
        vorher = auffaelligkeiten(self.ordner.starte("index.py").stdout)
        self.assertTrue(vorher, "vor dem Umstellen muss der Linter etwas finden")

        self.stelle_um("--schreiben")

        fertig = self.ordner.starte("index.py")
        self.assertEqual(auffaelligkeiten(fertig.stdout), [], fertig.stdout)

    def test_ein_zweiter_lauf_aendert_nichts(self) -> None:
        self.stelle_um("--schreiben")
        vorher = self.stand()

        fertig = self.stelle_um("--schreiben")

        self.assertEqual(fertig.returncode, 0, fertig.stdout + fertig.stderr)
        self.assertEqual(self.stand(), vorher)
        self.assertIn("Nichts zu tun", fertig.stdout)

    def test_ein_belegter_zielname_bricht_ab_bevor_etwas_geschrieben_ist(self) -> None:
        # Kaeme sonst die halbe Umstellung durch, zeigten Verweise schon auf
        # sechsstellige IDs, deren Karten noch vierstellig heissen.
        self.ordner.lege_karte_an(id="ue-000001", titel="Annahme im Halbfeld")
        vorher = self.stand()

        fertig = self.stelle_um("--schreiben")

        self.assertNotEqual(fertig.returncode, 0, fertig.stdout)
        self.assertEqual(self.stand(), vorher)
        self.assertIn("uebungen/ue-000001-annahme-im-halbfeld.md", fertig.stdout)

    def test_ein_eingetragener_trainer_bleibt_wie_er_ist(self) -> None:
        # Den Abschnitt pflegt sonst der Import-Skill, nach Rueckfrage. Das
        # Skript legt ihn nur an, es schreibt keinen um.
        self.ordner.setze_trainer({"anna": {"nummer": "00", "rechner": ["ANNAS-RECHNER"]}})
        vorher = self.lies("trainingsplanung-root.yml")

        fertig = self.stelle_um("--schreiben")

        self.assertEqual(self.lies("trainingsplanung-root.yml"), vorher)
        # Still uebergangen waere --trainer aber auch nicht recht: Danach
        # bekaeme dieser Rechner keine ID, ohne dass es jemand gesagt hat.
        self.assertIn("bleibt, wie er ist", fertig.stdout)
        self.assertIn(socket.gethostname(), fertig.stdout)


class VorlageTest(unittest.TestCase):
    """Die Wurzeldatei aus init_struktur.py hat `trainer:` schon, ohne Eintrag."""

    def test_der_leere_abschnitt_aus_der_vorlage_bekommt_den_trainer(self) -> None:
        ordner = Arbeitsordner()
        self.addCleanup(ordner.raeume_auf)
        neu = Path(tempfile.mkdtemp(prefix="trainingsplanung-vorlage-"))
        self.addCleanup(shutil.rmtree, neu, True)
        angelegt = ordner.starte("init_struktur.py", str(neu), mit_wurzel=False)
        self.assertEqual(angelegt.returncode, 0, angelegt.stdout + angelegt.stderr)
        ohne = ordner.starte("suche.py", "--wurzel", str(neu), "--naechste-id", mit_wurzel=False)
        self.assertNotEqual(ohne.returncode, 0, "die Vorlage traegt noch keinen Trainer")

        umgestellt = ordner.starte("ids_umstellen.py", "--wurzel", str(neu),
                                   "--trainer", "christian", "--schreiben", mit_wurzel=False)
        fertig = ordner.starte("suche.py", "--wurzel", str(neu), "--naechste-id", mit_wurzel=False)

        self.assertEqual(umgestellt.returncode, 0, umgestellt.stdout + umgestellt.stderr)
        self.assertEqual(fertig.returncode, 0, fertig.stderr)
        self.assertEqual(fertig.stdout.strip(), "ue-000001")
        # Der Kommentar mit dem Beispiel bleibt Kommentar, und der Abschnitt
        # steht einmal da.
        wurzeldatei = (neu / "trainingsplanung-root.yml").read_text(encoding="utf-8")
        self.assertEqual(len(re.findall(r"^trainer:", wurzeldatei, re.M)), 1)


if __name__ == "__main__":
    unittest.main()
