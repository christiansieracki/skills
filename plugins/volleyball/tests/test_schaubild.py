"""Prueft das Zeichnen einer Szene gegen einen kuenstlichen Arbeitsordner.

    <python> -m unittest discover -s plugins/volleyball/tests

Aufgerufen wird ueber die Kommandozeile mit `--wurzel`, wie bei Linter, Suche
und Bildaufbereitung. Gemessen wird an der **Geometrie** des geparsten SVG und
nicht an seinem Markup (ADR-0004): hat das Beachfeld 8x16 und nicht
Hallenproportionen, liegt ein Marker fuer Position 4 im richtigen Drittel,
weicht ein gekruemmter Weg um genau die angegebene Pfeilhoehe von der Geraden
ab.

Goldene Referenzdateien waeren das Gegenteil davon. Sie faerbten jede
Farbkorrektur rot und hoeben damit genau die Aenderbarkeit auf, fuer die die
Trennung von Szene und Bild ueberhaupt da ist.

Alle Masse hier werden aus dem Feldrechteck zurueckgerechnet, nicht aus einem
Massstab, der im Skript steht. Damit prueft der Test das Verhaeltnis, das er
zusichern will, und nicht die Zahl, mit der es zustande kam.
"""

from __future__ import annotations

import re
import unittest
import xml.etree.ElementTree as ET
from pathlib import Path

from arbeitsordner import Arbeitsordner

SVG = "{http://www.w3.org/2000/svg}"

HALLE = (9.0, 18.0)
BEACH = (8.0, 16.0)


# --------------------------------------------------------------------------
# Das erzeugte Bild lesen
# --------------------------------------------------------------------------

def mit_klasse(baum, klasse: str) -> list[ET.Element]:
    """Alle Elemente, die diese Klasse tragen — auch neben anderen Klassen."""
    return [e for e in baum.iter() if klasse in (e.get("class") or "").split()]


def zahlen(text: str) -> list[float]:
    return [float(t) for t in re.findall(r"-?\d+(?:\.\d+)?", text)]


class Feldmass:
    """Rechnet Zeichenkoordinaten zurueck in Meter.

    Die Umrechnung haengt allein am Feldrechteck im Bild und an den Massen, die
    das Feld laut Regelwerk hat. Der Massstab des Skripts kommt darin nicht vor:
    verdoppelte er sich morgen, blieben diese Pruefungen gruen, und das ist
    genau richtig.
    """

    def __init__(self, baum, masse: tuple[float, float]) -> None:
        rechtecke = mit_klasse(baum, "feld")
        assert len(rechtecke) == 1, f"{len(rechtecke)} Feldrechtecke im Bild"
        r = rechtecke[0]
        self.x = float(r.get("x"))
        self.y = float(r.get("y"))
        self.breite = float(r.get("width"))
        self.hoehe = float(r.get("height"))
        self.breite_m, self.laenge_m = masse

    @property
    def verhaeltnis(self) -> float:
        return self.breite / self.hoehe

    def meter(self, sx: float, sy: float) -> tuple[float, float]:
        """Ein Punkt im Bild, ausgedrueckt in Metern auf dem Feld."""
        return (
            (sx - self.x) / self.breite * self.breite_m,
            (self.y + self.hoehe - sy) / self.hoehe * self.laenge_m,
        )

    def strecke(self, laenge: float) -> float:
        """Eine Laenge im Bild, ausgedrueckt in Metern."""
        return laenge / self.hoehe * self.laenge_m


def pfeilhoehe(feld: "Feldmass", d: str) -> float:
    """Wie weit der gezeichnete Bogen von seiner Sehne abweicht, in Metern.

    Der Mittelpunkt einer quadratischen Bezierkurve liegt bei t=0.5, also bei
    (P0 + 2C + P1) / 4. Gemessen wird gegen die Sehne zwischen den Enden, die
    im Bild wirklich stehen — das ist die Strecke, die ein Leser mit dem Bogen
    vergleicht.
    """
    x0, y0, sx, sy, x1, y1 = zahlen(d)
    mitte = feld.meter((x0 + 2 * sx + x1) / 4, (y0 + 2 * sy + y1) / 4)
    sehne = feld.meter((x0 + x1) / 2, (y0 + y1) / 2)
    return ((mitte[0] - sehne[0]) ** 2 + (mitte[1] - sehne[1]) ** 2) ** 0.5


def kontrast(vorne: str, hinten: str) -> float:
    """Das Kontrastverhaeltnis zweier Farben nach WCAG, von 1 bis 21."""
    def helligkeit(farbe: str) -> float:
        roh = farbe.lstrip("#")
        kanaele = [int(roh[i:i + 2], 16) / 255 for i in (0, 2, 4)]
        linear = [k / 12.92 if k <= 0.03928 else ((k + 0.055) / 1.055) ** 2.4
                  for k in kanaele]
        return 0.2126 * linear[0] + 0.7152 * linear[1] + 0.0722 * linear[2]

    hell, dunkel = sorted((helligkeit(vorne), helligkeit(hinten)), reverse=True)
    return (hell + 0.05) / (dunkel + 0.05)


# --------------------------------------------------------------------------

class SchaubildTest(unittest.TestCase):
    def setUp(self) -> None:
        self.ordner = Arbeitsordner()
        self.addCleanup(self.ordner.raeume_auf)

    def zeichne(self, name: str, szene: str) -> ET.Element:
        """Legt die Szene ab, zeichnet sie und gibt das geparste SVG zurueck."""
        self.ordner.lege_szene_an(name, szene)
        fertig = self.ordner.starte("schaubild.py", name)
        self.assertEqual(fertig.returncode, 0, fertig.stdout + fertig.stderr)
        return ET.fromstring(self.bild(name).read_text(encoding="utf-8"))

    def bild(self, name: str) -> Path:
        return self.ordner.pfad / "schaubilder" / f"{name}.svg"

    def scheitert(self, name: str, szene: str):
        """Zeichnet eine Szene, die nicht aufgehen darf, und gibt den Lauf zurueck."""
        self.ordner.lege_szene_an(name, szene)
        fertig = self.ordner.starte("schaubild.py", name)
        self.assertNotEqual(fertig.returncode, 0,
                            "eine Szene, die nicht aufgeht, darf nicht gruen sein")
        return fertig

    # -- Szene und Bild ---------------------------------------------------

    def test_szene_und_bild_liegen_unter_demselben_basisnamen(self) -> None:
        # Daran haengt, dass eine Korrektur ein halbes Jahr spaeter drei Zeilen
        # kostet: wer das Bild sieht, findet seine Quelle ohne zu suchen.
        self.zeichne("ue-0042", """
            form: halle
            spieler:
              - bei: 3
        """)

        namen = sorted(p.name for p in (self.ordner.pfad / "schaubilder").iterdir())
        self.assertEqual(namen, ["ue-0042.svg", "ue-0042.szene.yml"])

    def test_eine_unbekannte_form_bricht_ab_und_schreibt_keine_datei(self) -> None:
        fertig = self.scheitert("ue-0043", """
            form: turnhalle
            spieler:
              - bei: 3
        """)

        self.assertIn("turnhalle", fertig.stdout)
        self.assertIn("halle", fertig.stdout, "die Meldung nennt, was es gibt")
        self.assertFalse(self.bild("ue-0043").exists(),
                         "eine Szene, die nicht aufgeht, hinterlaesst kein halbes Bild")

    def test_ein_vertippter_schluessel_wird_gemeldet(self) -> None:
        # Sonst waere der Tippfehler die stillste Art, das halbe Bild zu
        # verlieren: `spiler:` ergaebe ein leeres Feld, und das sieht fertig aus.
        fertig = self.scheitert("ue-0044", """
            form: halle
            spiler:
              - bei: 3
        """)

        self.assertIn("spiler", fertig.stdout)
        self.assertFalse(self.bild("ue-0044").exists())

    # -- Die beiden Feldvorlagen -------------------------------------------

    def test_das_hallenfeld_misst_neun_zu_achtzehn(self) -> None:
        baum = self.zeichne("halle", "form: halle")

        feld = Feldmass(baum, HALLE)
        self.assertAlmostEqual(feld.verhaeltnis, 9 / 18, places=3)

    def test_das_hallenfeld_traegt_beide_angriffslinien(self) -> None:
        baum = self.zeichne("halle", "form: halle")

        feld = Feldmass(baum, HALLE)
        bei = sorted(feld.meter(float(e.get("x1")), float(e.get("y1")))[1]
                     for e in mit_klasse(baum, "angriffslinie"))
        self.assertEqual(len(bei), 2, "je Haelfte eine")
        # Drei Meter vor und hinter dem Netz, das auf halber Laenge liegt.
        self.assertAlmostEqual(bei[0], 6.0, places=2)
        self.assertAlmostEqual(bei[1], 12.0, places=2)

    def test_das_beachfeld_misst_acht_zu_sechzehn(self) -> None:
        baum = self.zeichne("beach", "form: beach")

        feld = Feldmass(baum, BEACH)
        self.assertAlmostEqual(feld.verhaeltnis, 8 / 16, places=3)

    def test_im_sand_gibt_es_weder_angriffs_noch_mittellinie(self) -> None:
        # Eine Linie im Bild, die es draussen nicht gibt, ist eine Ansage, die
        # niemand einhalten kann.
        baum = self.zeichne("beach", "form: beach")

        self.assertEqual(mit_klasse(baum, "angriffslinie"), [])
        self.assertEqual(mit_klasse(baum, "mittellinie"), [])
        self.assertEqual(len(mit_klasse(baum, "netz")), 1, "das Netz steht trotzdem da")

    def test_in_der_halle_gibt_es_die_mittellinie(self) -> None:
        baum = self.zeichne("halle", "form: halle")

        feld = Feldmass(baum, HALLE)
        linien = mit_klasse(baum, "mittellinie")
        self.assertEqual(len(linien), 1)
        _, bei = feld.meter(float(linien[0].get("x1")), float(linien[0].get("y1")))
        self.assertAlmostEqual(bei, 9.0, places=2)

    # -- Wo jemand steht ---------------------------------------------------

    def test_position_vier_liegt_in_der_vorderen_linken_drittelflaeche(self) -> None:
        baum = self.zeichne("halle", """
            form: halle
            spieler:
              - bei: 4
                text: AA
        """)

        feld = Feldmass(baum, HALLE)
        kreise = mit_klasse(baum, "marker")
        self.assertEqual(len(kreise), 1)
        x, y = feld.meter(float(kreise[0].get("cx")), float(kreise[0].get("cy")))
        # Linkes Drittel der Breite, vorderstes Drittel der eigenen Haelfte:
        # die Drittelflaeche, die im Feld die Nummer 4 traegt.
        self.assertTrue(0 < x < 3, f"x liegt bei {x:.2f} m statt im linken Drittel")
        self.assertTrue(6 < y < 9, f"y liegt bei {y:.2f} m statt vorn am Netz")

    def test_ein_marker_traegt_seine_beschriftung(self) -> None:
        baum = self.zeichne("halle", """
            form: halle
            spieler:
              - bei: 3
                text: Z
        """)

        self.assertEqual([e.text for e in mit_klasse(baum, "beschriftung")], ["Z"])

    def test_im_sand_wird_ein_platz_ueber_seine_rolle_benannt(self) -> None:
        baum = self.zeichne("beach", """
            form: beach
            spieler:
              - bei: block
              - bei: abwehr
        """)

        feld = Feldmass(baum, BEACH)
        orte = {e.text: feld.meter(float(k.get("cx")), float(k.get("cy")))
                for e, k in zip(mit_klasse(baum, "beschriftung"),
                                mit_klasse(baum, "marker"))}
        self.assertEqual(sorted(orte), ["AB", "BL"])
        # Der Blockspieler steht am Netz, der Abwehrspieler dahinter. Ohne das
        # waeren es zwei Kreise mit Kuerzeln statt zwei Plaetzen.
        self.assertGreater(orte["BL"][1], orte["AB"][1])
        self.assertLess(orte["BL"][1], 8.0, "und auf der eigenen Haelfte")

    def test_im_sand_gibt_es_keine_positionsnummern(self) -> None:
        # Es gibt dort keine Rotation, auf die sich eine Nummer beziehen
        # koennte. Still auf eine Hallenposition zurueckzufallen hiesse, eine
        # Aufstellung zu zeichnen, die es im Sand nicht gibt.
        fertig = self.scheitert("sand", """
            form: beach
            spieler:
              - bei: 4
        """)

        self.assertIn("Positionsnummern", fertig.stdout)
        self.assertIn("block", fertig.stdout, "die Meldung nennt die Rollen")

    def test_in_der_halle_gibt_es_keine_rollen(self) -> None:
        fertig = self.scheitert("drinnen", """
            form: halle
            spieler:
              - bei: block
        """)

        self.assertIn("Rollen", fertig.stdout)
        self.assertFalse(self.bild("drinnen").exists())

    def test_freie_koordinaten_stehen_in_metern_da(self) -> None:
        baum = self.zeichne("frei", """
            form: halle
            spieler:
              - bei: [3.0, 12.5]
                text: A
        """)

        feld = Feldmass(baum, HALLE)
        kreis = mit_klasse(baum, "marker")[0]
        x, y = feld.meter(float(kreis.get("cx")), float(kreis.get("cy")))
        self.assertAlmostEqual(x, 3.0, places=2)
        self.assertAlmostEqual(y, 12.5, places=2)

    # -- Wege --------------------------------------------------------------

    def test_laufweg_und_ballweg_sind_unterscheidbar(self) -> None:
        baum = self.zeichne("wege", """
            form: halle
            wege:
              - art: laufweg
                von: 4
                nach: 3
              - art: ballweg
                von: 3
                nach: 4
        """)

        wege = mit_klasse(baum, "weg")
        self.assertEqual(len(wege), 2)
        lauf, ball = mit_klasse(baum, "laufweg")[0], mit_klasse(baum, "ballweg")[0]
        # Unterschieden wird ueber die Strichart, nicht allein ueber die Farbe:
        # das bleibt auch fuer den lesbar, der Farben schlecht auseinanderhaelt,
        # und im Ausdruck in Graustufen.
        stil = ET.fromstring(
            self.bild("wege").read_text(encoding="utf-8")).find(SVG + "style").text
        self.assertIn(".ballweg{", stil)
        self.assertRegex(stil, r"\.ballweg\{[^}]*stroke-dasharray")
        self.assertNotRegex(stil, r"\.laufweg\{[^}]*stroke-dasharray")
        # Und jeder traegt eine eigene Pfeilspitze, sonst haette der Ballweg die
        # Farbe des Laufwegs.
        self.assertNotEqual(lauf.get("marker-end"), ball.get("marker-end"))

    def test_ein_gerader_weg_hat_keine_kruemmung(self) -> None:
        baum = self.zeichne("gerade", """
            form: halle
            wege:
              - art: laufweg
                von: [1.5, 7.5]
                nach: [4.5, 7.5]
        """)

        self.assertNotIn("Q", mit_klasse(baum, "weg")[0].get("d"))

    def test_ein_gekruemmter_weg_weicht_um_die_pfeilhoehe_von_der_geraden_ab(self) -> None:
        # Der Bogen ist kein Gefuehl, sondern ein Mass: was in der Szene steht,
        # muss im Bild nachmessbar sein. Sonst zeichnete eine spaetere Aenderung
        # am Renderer einen halb so hohen Bogen, und niemand koennte es benennen.
        baum = self.zeichne("bogen", """
            form: halle
            wege:
              - art: ballweg
                von: [1.5, 4.5]
                nach: [1.5, 13.5]
                bogen: 1.5
        """)

        feld = Feldmass(baum, HALLE)
        d = mit_klasse(baum, "weg")[0].get("d")
        self.assertIn("Q", d, "ein Bogen wird als Kurve gezeichnet")
        self.assertAlmostEqual(pfeilhoehe(feld, d), 1.5, places=2)

    def test_die_pfeilhoehe_stimmt_auch_zwischen_zwei_spielern(self) -> None:
        # Ein Weg zwischen zwei Markern wird an beiden Enden gekuerzt. Bliebe
        # der Steuerpunkt dabei stehen, wuerde ein anderer Bogen gezeichnet als
        # angesagt — und zwar genau im haeufigsten Fall, dem Ball von einem
        # Spieler zum naechsten.
        baum = self.zeichne("bogen-gekuerzt", """
            form: halle
            spieler:
              - bei: 5
              - bei: 4
            wege:
              - art: ballweg
                von: 5
                nach: 4
                bogen: 1.5
        """)

        feld = Feldmass(baum, HALLE)
        d = mit_klasse(baum, "weg")[0].get("d")
        self.assertIn("Q", d)
        self.assertAlmostEqual(pfeilhoehe(feld, d), 1.5, places=2)

    def test_ein_weg_darf_auf_positionen_zeigen(self) -> None:
        baum = self.zeichne("zeigt", """
            form: halle
            wege:
              - art: laufweg
                von: 5
                nach: 4
        """)

        feld = Feldmass(baum, HALLE)
        x0, y0, x1, y1 = zahlen(mit_klasse(baum, "weg")[0].get("d"))
        self.assertEqual(
            [tuple(round(w, 1) for w in feld.meter(x0, y0)),
             tuple(round(w, 1) for w in feld.meter(x1, y1))],
            [(1.5, 1.5), (1.5, 7.5)],
        )

    def test_ein_weg_auf_einen_spieler_endet_vor_dessen_marker(self) -> None:
        # Sonst verschwaende die Pfeilspitze unter dem Kreis, und mit ihr das
        # Einzige, was die Richtung des Weges zeigt.
        baum = self.zeichne("trifft", """
            form: halle
            spieler:
              - bei: 4
              - bei: 3
            wege:
              - art: ballweg
                von: 4
                nach: 3
        """)

        feld = Feldmass(baum, HALLE)
        kreis = mit_klasse(baum, "marker")[0]
        radius = feld.strecke(float(kreis.get("r")))
        x0, y0, x1, y1 = zahlen(mit_klasse(baum, "weg")[0].get("d"))
        for punkt, mitte in ((feld.meter(x0, y0), (1.5, 7.5)),
                             (feld.meter(x1, y1), (4.5, 7.5))):
            abstand = ((punkt[0] - mitte[0]) ** 2 + (punkt[1] - mitte[1]) ** 2) ** 0.5
            self.assertGreater(abstand, radius,
                               "der Weg reicht bis in den Marker hinein")

    # -- Lesbarkeit ---------------------------------------------------------

    def test_das_bild_bleibt_in_hellem_und_dunklem_farbschema_lesbar(self) -> None:
        # Die Leseansicht schaltet mit dem Geraet um, und das Schaubild steckt
        # als Bild darin. Ein Feld in Papierweiss auf dunklem Grund ist nicht
        # falsch, aber ein schwarzer Strich auf schwarzem Grund ist weg.
        baum = self.zeichne("halle", "form: halle")

        stil = baum.find(SVG + "style").text
        hell = dict(re.findall(r"--([a-z]+):(#[0-9a-f]{6})",
                               re.search(r"^svg\{([^}]*)\}", stil).group(1)))
        dunkel = dict(re.findall(
            r"--([a-z]+):(#[0-9a-f]{6})",
            re.search(r"prefers-color-scheme:dark\)\{svg\{([^}]*)\}", stil).group(1)))

        self.assertEqual(sorted(hell), sorted(dunkel),
                         "beide Schemata setzen dieselben Farben")
        self.assertNotEqual(hell, dunkel, "sonst waere das zweite Schema Zierrat")
        for name, farben in (("hell", hell), ("dunkel", dunkel)):
            for vorne in ("strich", "gedaempft", "laufweg", "ballweg"):
                with self.subTest(schema=name, farbe=vorne):
                    self.assertGreaterEqual(
                        kontrast(farben[vorne], farben["feld"]), 4.5,
                        f"{vorne} hebt sich im Schema {name} zu wenig vom Feld ab")
            self.assertGreaterEqual(kontrast(farben["strich"], farben["papier"]), 4.5)

    def test_jede_feldvorlage_ergibt_wohlgeformtes_xml(self) -> None:
        # Rauchtest ueber beide Grundformen mit allem, was das Vokabular hergibt.
        for form, wo in (("halle", "3"), ("beach", "block")):
            with self.subTest(form=form):
                baum = self.zeichne(f"rauch-{form}", f"""
                    form: {form}
                    spieler:
                      - bei: {wo}
                        text: "Z & A"
                      - bei: [2.0, 2.0]
                    wege:
                      - art: laufweg
                        von: {wo}
                        nach: [2.0, 2.0]
                      - art: ballweg
                        von: [2.0, 2.0]
                        nach: {wo}
                        bogen: -1.0
                """)
                self.assertTrue(baum.tag.endswith("svg"))
                self.assertEqual(len(mit_klasse(baum, "marker")), 2)
                self.assertEqual(len(mit_klasse(baum, "weg")), 2)

    def test_ein_punkt_ausserhalb_des_feldes_bleibt_im_bild(self) -> None:
        # Ein Aufschlagspieler steht hinter der Grundlinie. Ihn abzuschneiden
        # waere die stillste aller Fehlermeldungen.
        baum = self.zeichne("hinten", """
            form: halle
            spieler:
              - bei: [4.5, -1.5]
                text: A
        """)

        breite, hoehe = zahlen(baum.get("viewBox"))[2:]
        kreis = mit_klasse(baum, "marker")[0]
        unterkante = float(kreis.get("cy")) + float(kreis.get("r"))
        self.assertLess(unterkante, hoehe, "der Marker liegt ganz im Bild")
        self.assertGreater(breite, 0)


if __name__ == "__main__":
    unittest.main()
