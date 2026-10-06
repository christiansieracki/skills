"""Prueft, dass die Vorlagen des Trainingsplans das Geruest tragen, das die Leseansicht versteht.

    <python> -m unittest discover -s plugins/volleyball/tests

Das Geruest steht zweimal: als Saat-Vorlage `referenzen/start/_vorlage.md`, die
init_struktur.py in jeden neuen Arbeitsordner kopiert, und in `VORLAGEN.md`,
nach dem der Skill Trainingsdesign neue Plaene schreibt. Beide sagen dasselbe
(#50, #59).

Wer eine Vorlage ausfuellt, ohne ihre Ueberschriften anzufassen, bekommt eine
Leseansicht ohne Meldung: Jeder Abschnitt mit Zeitangabe steht bei seinem
Programmpunkt. Geprueft wird wie in test_leseansicht.py ueber die
Kommandozeile, gelesen mit leseansicht_lesen.py.
"""

from __future__ import annotations

import re
import shutil
import tempfile
import unittest
from dataclasses import dataclass
from pathlib import Path

from arbeitsordner import SKRIPTE, Arbeitsordner
from leseansicht_lesen import Leseansicht, lies_leseansicht

REFERENZEN = SKRIPTE.parent / "referenzen"

# Die Kopfzeile der Ablauftabelle, wie die Spec sie festlegt (#50).
KOPFZEILE = "| Zeit | Programmpunkt | Übung | ID | Anpassung heute | Warum hier |"


def geruest_aus_vorlagen_md() -> str:
    """Das Geruest des Trainingsplans aus VORLAGEN.md, der Codeblock unter seiner Ueberschrift."""
    text = (REFERENZEN / "VORLAGEN.md").read_text(encoding="utf-8")
    ab = text.index("## trainings/&lt;gruppe&gt;/JJJJ-MM-TT.md")
    # Der Zaun ist laenger als drei Zeichen, weil die Hallenskizze im Geruest
    # selbst ein Codeblock ist.
    m = re.compile(r"^(`{3,})markdown\n(.*?)^\1[ \t]*$", re.M | re.S).search(text, ab)
    return m.group(2)


def _zellen(zeile: str) -> list[str]:
    return [z.strip() for z in zeile.strip().strip("|").split("|")]


def gliederung(markdown: str) -> list[str]:
    """Das Geruest einer Vorlage ohne Frontmatter: Ueberschriften und Tabellen, in ihrer Folge.

    Je Ueberschrift ihre Zeile, je Tabelle ihre Kopfzeile, aus der
    Ablauftabelle dazu je Programmpunkt Zeit und Name. Was in einem Codeblock
    steht, zaehlt nicht. Der Text auch nicht, den darf jede Vorlage auf ihre
    Art erklaeren.
    """
    zeilen, im_code, ablauf, davor = [], False, False, ""
    for zeile in markdown.split("\n---\n", 1)[1].splitlines():
        if zeile.startswith("```"):
            im_code = not im_code
        elif im_code:
            pass
        elif zeile.startswith("#"):
            zeilen.append(zeile.strip())
        elif zeile.startswith("|") and not davor.startswith("|"):
            zeilen.append("| " + " | ".join(_zellen(zeile)) + " |")
            ablauf = _zellen(zeile)[0] == "Zeit"
        elif zeile.startswith("|") and ablauf and set(zeile.strip()) - set("|-: "):
            zeit, name = _zellen(zeile)[:2]
            zeilen.append(f"| {zeit} | {name} |")
        davor = zeile
    return zeilen


@dataclass
class Lauf:
    """Was beim Erzeugen der Leseansicht aus einer Vorlage herauskam."""

    exitcode: int
    konsole: list[str]
    """Was auf der Konsole stand, eine Zeile je Eintrag."""
    ansicht: Leseansicht | None


class VorlageTest(unittest.TestCase):
    """Beide Vorlagen, unveraendert als Plan in einen neuen Arbeitsordner gelegt.

    Die Leseansichten entstehen einmal fuer die ganze Klasse, die Tests lesen
    nur. Jeder Test prueft beide Vorlagen.
    """

    @classmethod
    def setUpClass(cls) -> None:
        cls.ordner = Arbeitsordner()
        cls.addClassCleanup(cls.ordner.raeume_auf)
        cls.neu = Path(tempfile.mkdtemp(prefix="trainingsplanung-vorlage-"))
        cls.addClassCleanup(shutil.rmtree, cls.neu, True)
        angelegt = cls.ordner.starte("init_struktur.py", str(cls.neu), "--gruppe", "gruppe",
                                     mit_wurzel=False)
        if angelegt.returncode != 0:
            raise AssertionError(angelegt.stdout + angelegt.stderr)
        cls.saat = (cls.neu / "trainings" / "gruppe" / "_vorlage.md").read_text(encoding="utf-8")
        cls.laeufe = {"_vorlage.md": cls.erzeuge("2026-10-01.md", cls.saat),
                      "VORLAGEN.md": cls.erzeuge("2026-10-02.md", geruest_aus_vorlagen_md())}

    @classmethod
    def erzeuge(cls, name: str, markdown: str) -> Lauf:
        """Erzeugt die Leseansicht eines Plans, der genau so aussieht wie die Vorlage.

        Der Plan liegt im neuen Arbeitsordner unter trainings/, wie einer, den
        ein Trainer aus der Vorlage kopiert hat.
        """
        plan = cls.neu / "trainings" / "gruppe" / name
        plan.write_text(markdown, encoding="utf-8")
        fertig = cls.ordner.starte("leseansicht.py", str(plan), mit_wurzel=False)
        html = plan.with_suffix(".html")
        return Lauf(fertig.returncode, (fertig.stdout + fertig.stderr).splitlines(),
                    lies_leseansicht(html.read_text(encoding="utf-8")) if html.is_file() else None)

    def ansicht(self, lauf: Lauf) -> Leseansicht:
        self.assertEqual(lauf.exitcode, 0, lauf.konsole)
        return lauf.ansicht

    def test_die_leseansicht_aus_einer_vorlage_meldet_nichts(self) -> None:
        # Gemeldet wird eine Zeitangabe, die auf keinen Programmpunkt passt.
        # Ausser der Zeile, wo die Datei liegt, steht dann nichts da.
        for name, lauf in self.laeufe.items():
            with self.subTest(vorlage=name):
                self.assertEqual(lauf.exitcode, 0, lauf.konsole)
                self.assertEqual([z for z in lauf.konsole if not z.startswith("Leseansicht:")], [])

    def test_jeder_abschnitt_mit_zeitangabe_steht_bei_seinem_programmpunkt(self) -> None:
        # Das Beispiel fuer einen ausgeschriebenen Programmpunkt mit seiner
        # Hallenskizze, die Athletik als Liste zum Aufklappen, ein Verweis auf
        # ein Thema unter Zum Nachschlagen. Unter Vorbereitung bleibt keine
        # Ueberschrift mit Zeitangabe.
        for name, lauf in self.laeufe.items():
            with self.subTest(vorlage=name):
                ansicht = self.ansicht(lauf)

                abschnitte = [a for p in ansicht.programmpunkte for a in p.abschnitte]
                text = " ".join(f"{a.ueberschrift} {a.text}" for a in abschnitte)
                self.assertIn("Hallenskizze", text)
                self.assertTrue(any(a.listen for a in abschnitte), "keine Athletik als Liste")
                self.assertTrue(ansicht.nachschlagen and ansicht.nachschlagen.reiter, "kein Thema")
                self.assertTrue(any(p.verweise for p in ansicht.programmpunkte), "kein Verweis")
                self.assertEqual([a.ueberschrift for a in ansicht.vorbereitung
                                  if re.match(r"\d+\s*[–-]\s*\d+", a.ueberschrift)], [])

    def test_der_kurztitel_steht_nach_dem_gedankenstrich(self) -> None:
        for name, lauf in self.laeufe.items():
            with self.subTest(vorlage=name):
                self.assertEqual(self.ansicht(lauf).kopf.titel, "Kurztitel")

    def test_beide_vorlagen_zeigen_dasselbe_geruest(self) -> None:
        # Dieselben Ueberschriften in derselben Folge und dieselben Tabellen.
        # Der Text darunter darf sich unterscheiden: Die Saat-Vorlage erklaert
        # mehr, sie fuellt auch jemand ohne Claude aus.
        saat, vorlagen_md = gliederung(self.saat), gliederung(geruest_aus_vorlagen_md())

        self.assertIn(KOPFZEILE, saat)
        self.assertEqual(vorlagen_md, saat)


if __name__ == "__main__":
    unittest.main()
