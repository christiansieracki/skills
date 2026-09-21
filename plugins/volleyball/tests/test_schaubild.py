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
# Die Leinwand der Stationstests: ein Hallenteil, auf den kein ganzes Feld
# passt. Die Masse stehen in der Szene und hier, sonst gaebe es nichts, wogegen
# das Bild gemessen wuerde.
LEINWAND = (12.0, 9.0)

# Ein Stationsaufbau, wortgleich fuer beide Grundformen. Er steht einmal da,
# damit der Vergleich zwischen Feld und Leinwand wirklich derselbe Aufbau ist
# und nicht zwei aehnliche.
STATION = """
geraete:
  - text: Kasten
    teile:
      - form: rechteck
        bei: [3.0, 4.0]
        groesse: [1.6, 0.8]
abstaende:
  - art: masskette
    von: [3.0, 2.0]
    nach: [3.0, 5.0]
spieler:
  - bei: [1.0, 2.0]
    text: A
"""


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

    Die Umrechnung haengt allein am Rechteck der Grundform im Bild und an den
    Massen, die sie in Metern hat. Der Massstab des Skripts kommt darin nicht
    vor: verdoppelte er sich morgen, blieben diese Pruefungen gruen, und das ist
    genau richtig.

    `klasse` nennt das Rechteck, an dem gemessen wird: das Feld oder die freie
    Leinwand. Beide tragen ihre Masse in Metern, also misst derselbe Helfer in
    beiden Bildern. Genau das ist die Zusicherung, dass ein Aufbau auf der
    Leinwand denselben Massstab bekommt wie auf dem Feld.
    """

    def __init__(self, baum, masse: tuple[float, float],
                 klasse: str = "feld") -> None:
        rechtecke = mit_klasse(baum, klasse)
        assert len(rechtecke) == 1, (
            f"{len(rechtecke)} Rechtecke der Klasse {klasse!r} im Bild")
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


def laenge_im_bild(linie: ET.Element) -> float:
    """Die gezeichnete Laenge einer Linie, in Zeicheneinheiten.

    Gemessen wird an den Enden, die im Bild wirklich stehen. Ob eine
    Abstandsangabe massstaeblich ist, entscheidet sich genau hier und nicht an
    der Zahl, die danebensteht.
    """
    dx = float(linie.get("x2")) - float(linie.get("x1"))
    dy = float(linie.get("y2")) - float(linie.get("y1"))
    return (dx * dx + dy * dy) ** 0.5


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

    # -- Die freie Leinwand ------------------------------------------------

    def test_eine_freie_leinwand_rendert_ohne_feld_in_der_angegebenen_groesse(self) -> None:
        # Was auf kein Spielfeld passt, bekommt eine Flaeche mit angesagtem
        # Mass. Ein Feld darunter waere eine Ansage, die es in dem Hallenteil
        # nicht gibt.
        baum = self.zeichne("station", """
            form: frei
            groesse: [12.0, 9.0]
            spieler:
              - bei: [1.0, 2.0]
                text: A
        """)

        self.assertEqual(mit_klasse(baum, "feld"), [], "kein Spielfeld darunter")
        self.assertEqual(mit_klasse(baum, "netz"), [], "und kein Netz")
        flaeche = Feldmass(baum, LEINWAND, "leinwand")
        self.assertAlmostEqual(flaeche.verhaeltnis, 12 / 9, places=3)

    def test_auf_der_leinwand_steht_ein_punkt_da_wo_er_angesagt_ist(self) -> None:
        # Der Ursprung liegt auch hier in der linken unteren Ecke. Ohne das
        # haette die Leinwand ihren eigenen Massstab, und derselbe Aufbau waere
        # auf dem Feld ein anderer.
        baum = self.zeichne("punkt", """
            form: frei
            groesse: [12.0, 9.0]
            spieler:
              - bei: [3.0, 7.5]
                text: A
        """)

        flaeche = Feldmass(baum, LEINWAND, "leinwand")
        kreis = mit_klasse(baum, "marker")[0]
        x, y = flaeche.meter(float(kreis.get("cx")), float(kreis.get("cy")))
        self.assertAlmostEqual(x, 3.0, places=2)
        self.assertAlmostEqual(y, 7.5, places=2)

    def test_die_freie_leinwand_braucht_ein_mass(self) -> None:
        # Ohne Mass waere der Massstab geraten, und ein Schaubild, dessen
        # Abstaende luegen, ist schlimmer als eines ohne Abstaende.
        fertig = self.scheitert("ohne-mass", """
            form: frei
            spieler:
              - bei: [1.0, 1.0]
        """)

        self.assertIn("groesse", fertig.stdout)
        self.assertFalse(self.bild("ohne-mass").exists())

    def test_eine_feldvorlage_nimmt_keine_groesse_entgegen(self) -> None:
        # Das Hallenfeld misst 9x18 m. Eine zweite Zahl daneben waere entweder
        # wirkungslos oder falsch, und beides faellt niemandem auf.
        fertig = self.scheitert("zu-viel", """
            form: halle
            groesse: [12.0, 9.0]
        """)

        self.assertIn("groesse", fertig.stdout)
        self.assertIn("frei", fertig.stdout, "die Meldung nennt, wo es sie gibt")

    def test_auf_der_leinwand_gibt_es_weder_positionsnummern_noch_rollen(self) -> None:
        # Beide beziehen sich auf ein Feld. Ohne Feld gibt es nichts, worauf.
        for name, wo, wort in (("nummer", "4", "Positionsnummern"),
                               ("rolle", "block", "Rollen")):
            with self.subTest(ort=name):
                fertig = self.scheitert(f"leer-{name}", f"""
                    form: frei
                    groesse: [12.0, 9.0]
                    spieler:
                      - bei: {wo}
                """)

                self.assertIn(wort, fertig.stdout)
                self.assertIn("[x, y]", fertig.stdout, "die Meldung nennt den Ausweg")
                self.assertNotIn("Sand", fertig.stdout,
                                 "auf der Leinwand hilft der Hinweis auf Beach nicht")

    # -- Geraete -----------------------------------------------------------

    def test_ein_geraet_wird_aus_grundformen_zusammengesetzt_und_beschriftet(self) -> None:
        baum = self.zeichne("kasten", """
            form: halle
            geraete:
              - text: Kasten mit Ballwagen
                teile:
                  - form: rechteck
                    bei: [4.5, 6.0]
                    groesse: [1.6, 0.8]
                  - form: kreis
                    bei: [4.5, 6.0]
                    groesse: 0.6
        """)

        feld = Feldmass(baum, HALLE)
        gruppen = mit_klasse(baum, "geraet")
        self.assertEqual(len(gruppen), 1, "ein Geraet, nicht zwei Formen")
        kasten, wagen = mit_klasse(gruppen[0], "teil")
        # Beide Teile stehen massstaeblich da, sonst waere der Kasten eine
        # Kiste unbekannter Groesse.
        self.assertAlmostEqual(feld.strecke(float(kasten.get("width"))), 1.6, places=2)
        self.assertAlmostEqual(feld.strecke(float(kasten.get("height"))), 0.8, places=2)
        self.assertAlmostEqual(feld.strecke(float(wagen.get("r"))) * 2, 0.6, places=2)
        mitte = feld.meter(float(wagen.get("cx")), float(wagen.get("cy")))
        self.assertEqual(tuple(round(w, 2) for w in mitte), (4.5, 6.0))

        beschriftung = mit_klasse(gruppen[0], "geraetname")[0]
        self.assertEqual(beschriftung.text, "Kasten mit Ballwagen")
        # Sie steht unter dem Geraet. Ein Wort wie "Ballwagen" passt in keinen
        # Ballwagen, und halb verdeckt ist es schlechter als daneben.
        _, unter = feld.meter(float(beschriftung.get("x")),
                            float(beschriftung.get("y")))
        self.assertLess(unter, 6.0 - 0.4, "die Beschriftung liegt im Geraet")

    def test_eine_unbekannte_grundform_eines_geraetes_bricht_ab(self) -> None:
        fertig = self.scheitert("dreieck", """
            form: halle
            geraete:
              - text: Kasten
                teile:
                  - form: dreieck
                    bei: [4.5, 6.0]
                    groesse: [1.0, 1.0]
        """)

        self.assertIn("dreieck", fertig.stdout)
        self.assertIn("rechteck", fertig.stdout, "die Meldung nennt, was es gibt")
        self.assertFalse(self.bild("dreieck").exists())

    # -- Zonen -------------------------------------------------------------

    def test_eine_zone_ist_eine_massstaebliche_flaeche_mit_beschriftung(self) -> None:
        baum = self.zeichne("zielzone", """
            form: halle
            zonen:
              - text: Zielzone
                form: rechteck
                bei: [4.5, 6.0]
                groesse: [3.0, 2.0]
        """)

        feld = Feldmass(baum, HALLE)
        flaechen = mit_klasse(baum, "zonenflaeche")
        self.assertEqual(len(flaechen), 1)
        flaeche = flaechen[0]
        self.assertAlmostEqual(feld.strecke(float(flaeche.get("width"))), 3.0, places=2)
        self.assertAlmostEqual(feld.strecke(float(flaeche.get("height"))), 2.0, places=2)
        # Um ihren Mittelpunkt herum, wie jede Flaeche in einer Szene.
        links, oben = feld.meter(float(flaeche.get("x")), float(flaeche.get("y")))
        self.assertAlmostEqual(links, 3.0, places=2)
        self.assertAlmostEqual(oben, 7.0, places=2)

        # Die Beschriftung steht in der Zone. Eine Flaeche ist gross genug fuer
        # ihr Wort, und darin steht es bei dem, was es benennt.
        name = mit_klasse(baum, "zonenname")[0]
        self.assertEqual(name.text, "Zielzone")
        x, y = feld.meter(float(name.get("x")), float(name.get("y")))
        self.assertAlmostEqual(x, 4.5, places=2)
        self.assertTrue(5.0 < y < 7.0, f"die Beschriftung liegt bei {y:.2f} m")

    def test_eine_runde_zone_traegt_ihren_durchmesser(self) -> None:
        baum = self.zeichne("kreiszone", """
            form: halle
            zonen:
              - text: Aufschlagziel
                form: kreis
                bei: [4.5, 3.0]
                groesse: 2.0
        """)

        feld = Feldmass(baum, HALLE)
        kreis = mit_klasse(baum, "zonenflaeche")[0]
        self.assertAlmostEqual(feld.strecke(float(kreis.get("r"))) * 2, 2.0, places=2)

        # Und ihr Wort in der Mitte, wo sie am breitesten ist. An der
        # Oberkante ist ein Kreis schmal, und das Wort stuende zu beiden
        # Seiten daneben statt darin.
        name = mit_klasse(baum, "zonenname")[0]
        x, y = feld.meter(float(name.get("x")), float(name.get("y")))
        self.assertAlmostEqual(x, 4.5, places=2)
        self.assertAlmostEqual(y, 3.0, places=2)

    def test_eine_zone_ist_im_bild_von_einem_geraet_unterscheidbar(self) -> None:
        # Ein Geraet ist ein Gegenstand, den jemand in die Halle stellt, eine
        # Zone eine Absprache. Wer den Unterschied im Bild nicht sieht, raeumt
        # einen Kasten von einer Stelle weg, an der nie einer stand.
        baum = self.zeichne("beides", """
            form: halle
            zonen:
              - text: Zielzone
                form: rechteck
                bei: [2.5, 6.0]
                groesse: [3.0, 2.0]
            geraete:
              - text: Kasten
                teile:
                  - form: rechteck
                    bei: [7.0, 6.0]
                    groesse: [1.6, 0.8]
        """)

        feld = Feldmass(baum, HALLE)
        self.assertEqual(len(mit_klasse(baum, "zonenflaeche")), 1)
        self.assertEqual(len(mit_klasse(baum, "teil")), 1)

        stil = baum.find(SVG + "style").text
        zone = re.search(r"\.zonenflaeche\{([^}]*)\}", stil).group(1)
        teil = re.search(r"\.teil\{([^}]*)\}", stil).group(1)
        # Unterschieden wird ueber die Strichart und nicht allein ueber die
        # Farbe: so bleibt der Unterschied im Graustufendruck stehen und fuer
        # den lesbar, der Farben schlecht auseinanderhaelt.
        self.assertIn("stroke-dasharray", zone, "die Zone hat einen eigenen Rand")
        self.assertNotIn("stroke-dasharray", teil, "das Geraet steht durchgezogen da")
        self.assertNotEqual(re.search(r"fill:var\(--(\w+)\)", zone).group(1),
                            re.search(r"fill:var\(--(\w+)\)", teil).group(1))

        # Und an der Beschriftung: die der Zone steht in ihr, die des Geraetes
        # darunter.
        _, in_der_zone = feld.meter(
            0.0, float(mit_klasse(baum, "zonenname")[0].get("y")))
        _, unter_dem_geraet = feld.meter(
            0.0, float(mit_klasse(baum, "geraetname")[0].get("y")))
        self.assertGreater(in_der_zone, 5.0, "die Zone reicht von 5 bis 7 m")
        self.assertLess(unter_dem_geraet, 5.6, "der Kasten reicht bis 5,6 m")

    def test_eine_zone_liegt_unter_dem_aufbau_und_unter_den_feldlinien(self) -> None:
        baum = self.zeichne("darunter", """
            form: halle
            zonen:
              - text: Zielzone
                form: rechteck
                bei: [4.5, 6.0]
                groesse: [6.0, 4.0]
            spieler:
              - bei: 3
            wege:
              - art: ballweg
                von: [4.5, 1.0]
                nach: 3
        """)

        reihenfolge = list(baum.iter())

        def stelle(klasse: str) -> int:
            return reihenfolge.index(mit_klasse(baum, klasse)[0])

        zone = stelle("zonenflaeche")
        # Ueber einer Zone stehen Marker und laufen Wege. Eine Flaeche, die
        # kraeftig genug waere, um aufzufallen, verdeckte sonst, worum es geht.
        self.assertLess(zone, stelle("marker"))
        self.assertLess(zone, stelle("weg"))
        # Die Angriffslinie gehoert zum Boden und nicht zum Aufbau. Eine
        # Zielzone darueber loeschte die Linie, an der sie abgemessen wird.
        self.assertLess(zone, stelle("angriffslinie"))

    def test_das_wort_einer_zone_bleibt_unter_einem_marker_lesbar(self) -> None:
        # Die Flaeche einer Zone gehoert unter den Aufbau, ihr Wort nicht. Ein
        # Marker deckt einen ganzen Meter ab. Stuende das Wort mit seiner
        # Flaeche unten, waere es weg, sobald jemand darauf steht, und eine
        # Zone ohne lesbares Wort ist nur noch ein Farbfleck.
        baum = self.zeichne("beschriftet", """
            form: halle
            zonen:
              - text: Zielzone
                form: rechteck
                bei: [4.5, 6.0]
                groesse: [3.0, 1.2]
            spieler:
              - bei: [4.5, 6.0]
                text: Z
        """)

        reihenfolge = list(baum.iter())

        def stelle(klasse: str) -> int:
            return reihenfolge.index(mit_klasse(baum, klasse)[0])

        # Der Marker liegt wirklich auf dem Wort: sonst pruefte der Test die
        # Reihenfolge an einem Fall, in dem sie egal waere.
        feld = Feldmass(baum, HALLE)
        name = mit_klasse(baum, "zonenname")[0]
        kreis = mit_klasse(baum, "marker")[0]
        abstand = abs(float(name.get("y")) - float(kreis.get("cy")))
        self.assertLess(abstand, float(kreis.get("r")))

        self.assertGreater(stelle("zonenname"), stelle("marker"))
        self.assertLess(stelle("zonenflaeche"), stelle("marker"),
                        "die Flaeche bleibt trotzdem unten")
        # Und massstaeblich steht das Wort weiter da, wo es hingehoert.
        self.assertAlmostEqual(feld.meter(float(name.get("x")), 0.0)[0], 4.5,
                               places=2)

    def test_eine_zone_laesst_sich_auf_der_freien_leinwand_zeichnen(self) -> None:
        baum = self.zeichne("zone-leinwand", """
            form: frei
            groesse: [12.0, 9.0]
            zonen:
              - text: Wartebereich
                form: rechteck
                bei: [3.0, 4.0]
                groesse: [2.0, 3.0]
        """)

        bezug = Feldmass(baum, LEINWAND, "leinwand")
        flaeche = mit_klasse(baum, "zonenflaeche")[0]
        self.assertAlmostEqual(bezug.strecke(float(flaeche.get("width"))), 2.0, places=2)
        self.assertAlmostEqual(bezug.strecke(float(flaeche.get("height"))), 3.0, places=2)
        links, oben = bezug.meter(float(flaeche.get("x")), float(flaeche.get("y")))
        self.assertAlmostEqual(links, 2.0, places=2)
        self.assertAlmostEqual(oben, 5.5, places=2)

    def test_eine_zone_ohne_beschriftung_bricht_ab(self) -> None:
        # Eine Zone ist eine Absprache. Ohne Wort steht da eine Flaeche, von
        # der niemand weiss, was auf ihr gilt, und die aussieht wie ein Geraet.
        fertig = self.scheitert("stumm", """
            form: halle
            zonen:
              - form: rechteck
                bei: [4.5, 6.0]
                groesse: [3.0, 2.0]
        """)

        self.assertIn("Beschriftung", fertig.stdout)
        self.assertFalse(self.bild("stumm").exists())

    def test_eine_zone_ohne_mass_bricht_ab(self) -> None:
        fertig = self.scheitert("masslos", """
            form: halle
            zonen:
              - text: Zielzone
                form: rechteck
                bei: [4.5, 6.0]
        """)

        self.assertIn("Zone 1", fertig.stdout)
        self.assertFalse(self.bild("masslos").exists())

    def test_eine_unbekannte_grundform_einer_zone_bricht_ab(self) -> None:
        fertig = self.scheitert("sechseck", """
            form: halle
            zonen:
              - text: Zielzone
                form: sechseck
                bei: [4.5, 6.0]
                groesse: [3.0, 2.0]
        """)

        self.assertIn("sechseck", fertig.stdout)
        self.assertIn("rechteck", fertig.stdout, "die Meldung nennt, was es gibt")
        self.assertFalse(self.bild("sechseck").exists())

    def test_eine_zone_neben_dem_feld_bleibt_ganz_im_bild(self) -> None:
        baum = self.zeichne("danebenzone", """
            form: halle
            zonen:
              - text: Ablage
                form: rechteck
                bei: [11.0, 9.0]
                groesse: [2.0, 3.0]
        """)

        breite, hoehe = zahlen(baum.get("viewBox"))[2:]
        flaeche = mit_klasse(baum, "zonenflaeche")[0]
        rechts = float(flaeche.get("x")) + float(flaeche.get("width"))
        self.assertLess(rechts, breite, "die Zone liegt ganz im Bild")
        self.assertGreater(hoehe, 0)

    # -- Abstandsangaben ---------------------------------------------------

    def test_eine_masskette_ueber_sechs_meter_ist_ein_drittel_der_feldlaenge(self) -> None:
        # Der Massstab einer Abstandsangabe ist derselbe wie der des Feldes.
        # Sonst saehen zwei Strecken gleich aus und bedeuteten Verschiedenes.
        baum = self.zeichne("kette", """
            form: halle
            abstaende:
              - art: masskette
                von: [1.5, 2.0]
                nach: [7.5, 2.0]
        """)

        feld = Feldmass(baum, HALLE)
        linie = mit_klasse(baum, "masslinie")[0]
        self.assertAlmostEqual(laenge_im_bild(linie) / feld.hoehe, 1 / 3, places=3)

    def test_ein_beschrifteter_pfeil_ist_genauso_massstaeblich_wie_eine_masskette(self) -> None:
        # Welche der beiden Darstellungen uebersichtlicher ist, haengt am
        # Anwendungsfall. Am Massstab haengt es nicht.
        baum = self.zeichne("beides", """
            form: halle
            abstaende:
              - art: masskette
                von: [1.5, 2.0]
                nach: [7.5, 2.0]
              - art: pfeil
                von: [1.5, 4.0]
                nach: [7.5, 4.0]
        """)

        feld = Feldmass(baum, HALLE)
        kette, pfeil = mit_klasse(baum, "masskette")[0], mit_klasse(baum, "pfeil")[0]
        for art, gruppe in (("masskette", kette), ("pfeil", pfeil)):
            with self.subTest(art=art):
                linie = mit_klasse(gruppe, "masslinie")[0]
                self.assertAlmostEqual(feld.strecke(laenge_im_bild(linie)), 6.0,
                                       places=2)

        # Unterschieden wird an den Enden: die Kette bekommt Massstriche, der
        # Pfeil Spitzen an beiden Enden. Einfach bepfeilt laese er sich als Weg.
        self.assertEqual(len(mit_klasse(kette, "massstrich")), 2)
        self.assertEqual(len(mit_klasse(pfeil, "massstrich")), 0)
        spitzen = mit_klasse(pfeil, "masslinie")[0]
        self.assertTrue(spitzen.get("marker-start") and spitzen.get("marker-end"))
        self.assertIsNone(mit_klasse(kette, "masslinie")[0].get("marker-end"))

    def test_eine_abstandsangabe_beschriftet_sich_mit_der_gemessenen_laenge(self) -> None:
        # Die Zahl wird gemessen und nicht abgeschrieben. Wer etwas anderes
        # hinschreiben will, schreibt es hin und verantwortet es.
        baum = self.zeichne("zahlen", """
            form: halle
            abstaende:
              - art: masskette
                von: [1.0, 2.0]
                nach: [7.0, 2.0]
              - art: pfeil
                von: [1.0, 4.0]
                nach: [5.5, 4.0]
              - art: masskette
                von: [1.0, 6.0]
                nach: [7.0, 6.0]
                text: je 2 m
        """)

        self.assertEqual([e.text for e in mit_klasse(baum, "massbeschriftung")],
                         ["6 m", "4,5 m", "je 2 m"])

    def test_der_versatz_rueckt_die_masslinie_zur_seite_ohne_sie_zu_kuerzen(self) -> None:
        # Eine Kette quer durch die Marker, deren Abstand sie angibt, liest
        # niemand. Verschoben wird sie, verkuerzt nicht.
        baum = self.zeichne("versatz", """
            form: halle
            abstaende:
              - art: masskette
                von: [1.5, 2.0]
                nach: [7.5, 2.0]
                versatz: 1.0
        """)

        feld = Feldmass(baum, HALLE)
        linie = mit_klasse(baum, "masslinie")[0]
        self.assertAlmostEqual(feld.strecke(laenge_im_bild(linie)), 6.0, places=2)
        _, neben = feld.meter(float(linie.get("x1")), float(linie.get("y1")))
        self.assertAlmostEqual(neben, 3.0, places=2, msg="einen Meter nach links")
        # Zwei Masshilfslinien halten die Kette an dem fest, was sie misst.
        self.assertEqual(len(mit_klasse(baum, "masshilfslinie")), 2)

    def test_ein_abstand_zwischen_einem_ort_und_sich_selbst_bricht_ab(self) -> None:
        # Und meldet sich als Abstand. Eine Meldung ueber einen Weg schickte den
        # Leser in die Zeilen, in denen gar nichts steht.
        fertig = self.scheitert("null", """
            form: halle
            abstaende:
              - art: masskette
                von: 4
                nach: 4
        """)

        self.assertIn("Abstand 1", fertig.stdout)
        self.assertNotIn("Weg", fertig.stdout)
        self.assertFalse(self.bild("null").exists())

    def test_ein_wahrheitswert_als_versatz_wird_gemeldet(self) -> None:
        # `false` ist in Python eine Null, in einer Szene aber keine Angabe in
        # Metern. Still als "nicht verschoben" durchzugehen waere die Art
        # Fehler, die man dem fertigen Bild nicht ansieht.
        fertig = self.scheitert("wahrheitswert", """
            form: halle
            abstaende:
              - art: masskette
                von: [1.0, 2.0]
                nach: [7.0, 2.0]
                versatz: false
        """)

        self.assertIn("Versatz", fertig.stdout)
        self.assertFalse(self.bild("wahrheitswert").exists())

    # -- Der Stationsaufbau -------------------------------------------------

    def test_derselbe_stationsaufbau_geht_aufs_feld_und_auf_die_leinwand(self) -> None:
        # Was aufs Feld passt, wird aufs Feld gezeichnet und hat seinen
        # Massstab geschenkt. Die freie Leinwand ist der Ausnahmefall, und sie
        # misst denselben Kasten genauso.
        auf_feld = self.zeichne("station-feld", "form: halle" + STATION)
        auf_leinwand = self.zeichne("station-leinwand",
                                    "form: frei\ngroesse: [12.0, 9.0]" + STATION)

        gemessen = []
        for baum, masse, klasse in ((auf_feld, HALLE, "feld"),
                                    (auf_leinwand, LEINWAND, "leinwand")):
            bezug = Feldmass(baum, masse, klasse)
            kasten = mit_klasse(baum, "teil")[0]
            kette = mit_klasse(baum, "masslinie")[0]
            gemessen.append((round(bezug.strecke(float(kasten.get("width"))), 2),
                             round(bezug.strecke(laenge_im_bild(kette)), 2)))

        self.assertEqual(gemessen, [(1.6, 3.0), (1.6, 3.0)],
                         "derselbe Aufbau misst auf beiden Grundformen dasselbe")
        self.assertEqual(mit_klasse(auf_leinwand, "feld"), [])

    # -- Titel, Legende und Fusszeile --------------------------------------

    def test_eine_szene_traegt_titel_und_untertitel_ueber_dem_bild(self) -> None:
        baum = self.zeichne("kopf", """
            form: halle
            titel: Annahme-Zielzone
            untertitel: Aufschlag von hinten, Annahme auf die Drei
            spieler:
              - bei: 3
        """)

        self.assertEqual([e.text for e in mit_klasse(baum, "titel")],
                         ["Annahme-Zielzone"])
        self.assertEqual([e.text for e in mit_klasse(baum, "untertitel")],
                         ["Aufschlag von hinten, Annahme auf die Drei"])
        titel, unter = mit_klasse(baum, "titel")[0], mit_klasse(baum, "untertitel")[0]
        feld = mit_klasse(baum, "feld")[0]
        self.assertLess(float(titel.get("y")), float(unter.get("y")),
                        "der Untertitel steht unter dem Titel")
        self.assertLess(float(unter.get("y")), float(feld.get("y")),
                        "und beide ueber dem Feld")

    def test_der_titel_ist_zugleich_der_name_des_bildes(self) -> None:
        # Sonst hat `role="img"` nichts zu melden, und eine Vorlesehilfe sagt
        # ueber das ganze Schaubild nur "Grafik".
        baum = self.zeichne("name", """
            form: halle
            titel: Annahme-Zielzone
        """)

        self.assertEqual(baum.find(SVG + "title").text, "Annahme-Zielzone")

    def test_titel_und_fusszeile_sitzen_auf_derselben_kante_wie_das_bild(self) -> None:
        # Ein Titel, der zwei Finger neben dem Feld anfaengt, liest sich wie
        # ein zweites Blatt hinter dem ersten.
        baum = self.zeichne("kante", """
            form: halle
            titel: Annahme-Zielzone
            fusszeile: "Quelle: Volleyball-Magazin 09/2026"
        """)

        feld = mit_klasse(baum, "feld")[0]
        for klasse in ("titel", "fusszeile"):
            with self.subTest(klasse=klasse):
                self.assertAlmostEqual(float(mit_klasse(baum, klasse)[0].get("x")),
                                       float(feld.get("x")), places=2)

    def test_ein_untertitel_ohne_titel_bricht_ab(self) -> None:
        # Eine zweite Zeile unter nichts liest sich wie ein angefangener Satz.
        fertig = self.scheitert("nur-unter", """
            form: halle
            untertitel: ohne etwas darueber
        """)

        self.assertIn("Titel", fertig.stdout)
        self.assertFalse(self.bild("nur-unter").exists())

    def test_die_legende_steht_in_bloecken_aus_ueberschrift_und_zeilen(self) -> None:
        baum = self.zeichne("legende", """
            form: halle
            legende:
              - ueberschrift: Aufschlagseite
                zeilen:
                  - AS schlaegt von Position 1
                  - flach ueber das Netz
              - ueberschrift: Wertung
                zeilen:
                  - 3 Punkte in der Zielzone
        """)

        bloecke = mit_klasse(baum, "legendenblock")
        self.assertEqual(len(bloecke), 2, "zwei Legendenbloecke, nicht eine lange Liste")
        self.assertEqual([[e.text for e in mit_klasse(b, "legendenkopf")]
                          for b in bloecke],
                         [["Aufschlagseite"], ["Wertung"]])
        self.assertEqual([[e.text for e in mit_klasse(b, "legendenzeile")]
                          for b in bloecke],
                         [["AS schlaegt von Position 1", "flach ueber das Netz"],
                          ["3 Punkte in der Zielzone"]])
        # Gelesen wird von oben nach unten: erst die Ueberschrift, dann ihre
        # Zeilen, dann der naechste Block.
        hoehen = [float(e.get("y")) for b in bloecke for e in b]
        self.assertEqual(hoehen, sorted(hoehen))

    def test_die_legendenspalte_steht_neben_dem_feld_und_nicht_darauf(self) -> None:
        # Sie erklaert das Bild. Eine Erklaerung, die das Erklaerte verdeckt,
        # ist keine.
        baum = self.zeichne("neben", """
            form: halle
            legende:
              - ueberschrift: Wertung
                zeilen:
                  - 3 Punkte in der Zielzone
        """)

        feld = mit_klasse(baum, "feld")[0]
        rechts = float(feld.get("x")) + float(feld.get("width"))
        for e in mit_klasse(baum, "legendenkopf") + mit_klasse(baum, "legendenzeile"):
            self.assertGreater(float(e.get("x")), rechts, f"{e.text!r} liegt im Feld")

    def test_ein_legendenblock_ohne_ueberschrift_oder_ohne_zeilen_bricht_ab(self) -> None:
        # Ein Block ohne Ueberschrift ist eine Liste, von der niemand weiss,
        # wovon sie handelt; eine Ueberschrift ohne Zeilen erklaert nichts.
        for name, block in (("ohne-kopf", "- zeilen:\n    - eine Zeile"),
                            ("ohne-zeilen", "- ueberschrift: Wertung")):
            with self.subTest(fall=name):
                fertig = self.scheitert(name, "form: halle\nlegende:\n  " + block)

                self.assertIn("Legendenblock 1", fertig.stdout)
                self.assertFalse(self.bild(name).exists())

    def test_die_fusszeile_steht_unter_dem_bild(self) -> None:
        baum = self.zeichne("fuss", """
            form: halle
            fusszeile: "Quelle: Volleyball-Magazin 09/2026, Seite 12"
        """)

        self.assertEqual([e.text for e in mit_klasse(baum, "fusszeile")],
                         ["Quelle: Volleyball-Magazin 09/2026, Seite 12"])
        feld = mit_klasse(baum, "feld")[0]
        unterkante = float(feld.get("y")) + float(feld.get("height"))
        self.assertGreater(float(mit_klasse(baum, "fusszeile")[0].get("y")), unterkante)

    def test_das_feld_bleibt_massstaeblich_neben_dem_textwerk(self) -> None:
        # Das Textwerk rueckt das Bild, es verzerrt es nicht. Ohne diese
        # Zusicherung stuende derselbe Spieler mit Titel woanders als ohne.
        baum = self.zeichne("beides", """
            form: halle
            titel: Annahme-Zielzone
            untertitel: mit Legende daneben
            fusszeile: aus dem Magazin
            legende:
              - ueberschrift: Wertung
                zeilen:
                  - 3 Punkte in der Zielzone
            spieler:
              - bei: [3.0, 12.5]
                text: A
        """)

        feld = Feldmass(baum, HALLE)
        self.assertAlmostEqual(feld.verhaeltnis, 9 / 18, places=3)
        kreis = mit_klasse(baum, "marker")[0]
        x, y = feld.meter(float(kreis.get("cx")), float(kreis.get("cy")))
        self.assertAlmostEqual(x, 3.0, places=2)
        self.assertAlmostEqual(y, 12.5, places=2)

    def test_eine_lange_zeile_macht_das_blatt_breiter_statt_abgeschnitten(self) -> None:
        # Eine halb abgeschnittene Legende ist die stillste aller
        # Fehlermeldungen: das Bild sieht fertig aus.
        def mit(zeile: str) -> ET.Element:
            return self.zeichne(f"breite-{len(zeile)}", f"""
                form: halle
                legende:
                  - ueberschrift: Wertung
                    zeilen:
                      - {zeile}
            """)

        kurz = mit("drei Punkte")
        lang = mit("drei Punkte fuer jeden Ball, der in der Zielzone aufkommt")

        self.assertGreater(zahlen(lang.get("viewBox"))[2],
                           zahlen(kurz.get("viewBox"))[2],
                           "die laengere Zeile braucht mehr Blatt")
        for e in mit_klasse(lang, "legendenzeile"):
            self.assertLess(float(e.get("x")), zahlen(lang.get("viewBox"))[2])
        # Das Feld darunter bleibt, wie es war: gewachsen ist das Blatt.
        self.assertAlmostEqual(Feldmass(kurz, HALLE).breite,
                               Feldmass(lang, HALLE).breite, places=2)

    def test_eine_legende_laenger_als_das_feld_waechst_ins_blatt_hinein(self) -> None:
        def mit(bloecke: int) -> ET.Element:
            szene = "form: halle\nlegende:\n" + "".join(
                f"  - ueberschrift: Abschnitt {n}\n    zeilen:\n"
                f"      - eine Zeile\n      - noch eine\n"
                for n in range(1, bloecke + 1))
            return self.zeichne(f"spalte-{bloecke}", szene)

        kurz, lang = mit(1), mit(14)

        self.assertGreater(zahlen(lang.get("viewBox"))[3],
                           zahlen(kurz.get("viewBox"))[3])
        letzte = max(float(e.get("y")) for e in mit_klasse(lang, "legendenzeile"))
        self.assertLess(letzte, zahlen(lang.get("viewBox"))[3],
                        "die letzte Zeile steht noch im Bild")
        self.assertAlmostEqual(Feldmass(kurz, HALLE).hoehe,
                               Feldmass(lang, HALLE).hoehe, places=2)

    def test_das_textwerk_nimmt_nur_farben_die_auf_dem_papier_stehen(self) -> None:
        # Titel, Legende und Fusszeile stehen auf dem Papier und nicht auf dem
        # Feld. Gegen das Papier geprueft sind --strich und --gedaempft.
        baum = self.zeichne("farben", """
            form: halle
            titel: Annahme-Zielzone
            untertitel: mit Legende daneben
            fusszeile: aus dem Magazin
            legende:
              - ueberschrift: Wertung
                zeilen:
                  - 3 Punkte in der Zielzone
        """)

        stil = baum.find(SVG + "style").text
        for klasse in ("titel", "untertitel", "legendenkopf", "legendenzeile",
                       "fusszeile"):
            with self.subTest(klasse=klasse):
                farbe = re.search(rf"\.{klasse}\{{[^}}]*fill:var\(--(\w+)\)", stil)
                self.assertIsNotNone(farbe, f".{klasse} setzt keine Farbe")
                self.assertIn(farbe.group(1), ("strich", "gedaempft"))

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
                for grund in ("feld", "zone"):
                    with self.subTest(schema=name, farbe=vorne, grund=grund):
                        # Auch ueber einer Zone: dort stehen Marker und laufen
                        # Wege, und eine Flaeche, die das verdeckt, verdeckt
                        # genau das, worum es geht.
                        self.assertGreaterEqual(
                            kontrast(farben[vorne], farben[grund]), 4.5,
                            f"{vorne} hebt sich im Schema {name} zu wenig "
                            f"vom {grund} ab")
            # Auf dem Papier steht das Textwerk: Titel und Legende in
            # --strich, Untertitel und Fusszeile in --gedaempft. Beide muessen
            # sich davon abheben, sonst ist die Erklaerung zum Bild weg.
            self.assertGreaterEqual(kontrast(farben["strich"], farben["papier"]), 4.5)
            self.assertGreaterEqual(kontrast(farben["gedaempft"], farben["papier"]),
                                    4.5)
            # Ein Geraet ist eine Flaeche mit Rand. Faellt der Rand in die
            # Flaeche, steht ein Farbfleck im Bild statt eines Kastens.
            self.assertGreaterEqual(kontrast(farben["gedaempft"], farben["geraet"]),
                                    4.5)
            # Die Zone ist zurueckhaltender als das Geraet: ihre Fuellung
            # liegt naeher am Boden. Sonst stuende eine Absprache so kraeftig
            # im Bild wie ein Kasten.
            self.assertLess(abs(1 - kontrast(farben["zone"], farben["feld"])),
                            abs(1 - kontrast(farben["geraet"], farben["feld"])))

    def test_jede_grundform_ergibt_wohlgeformtes_xml(self) -> None:
        # Rauchtest ueber alle Grundformen mit allem, was das Vokabular hergibt.
        # Der Kopf steht je Grundform buendig da, weil die Leinwand eine zweite
        # Zeile braucht und eine eingerueckte Zeile keine Szene mehr waere.
        for name, kopf, wo in (
            ("halle", "form: halle", "3"),
            ("beach", "form: beach", "block"),
            ("frei", "form: frei\ngroesse: [10.0, 6.0]", "[5.0, 4.0]"),
        ):
            with self.subTest(form=name):
                baum = self.zeichne(f"rauch-{name}", kopf + f"""
titel: Aufbau & Ablauf
untertitel: mit allem, was das Vokabular hergibt
fusszeile: "Quelle: Magazin & Co."
legende:
  - ueberschrift: Wertung & Punkte
    zeilen:
      - drei Punkte in der Zielzone
      - ein Punkt daneben
spieler:
  - bei: {wo}
    text: "Z & A"
  - bei: [2.0, 2.0]
zonen:
  - text: Zielzone & Rand
    form: rechteck
    bei: [4.0, 4.0]
    groesse: [3.0, 2.0]
geraete:
  - text: Kasten & Wagen
    teile:
      - form: rechteck
        bei: [3.0, 3.0]
        groesse: [1.6, 0.8]
      - form: kreis
        bei: [3.0, 3.0]
        groesse: 0.5
abstaende:
  - art: masskette
    von: [2.0, 2.0]
    nach: [3.0, 3.0]
  - art: pfeil
    von: [2.0, 2.0]
    nach: {wo}
    versatz: -0.8
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
                self.assertEqual(len(mit_klasse(baum, "geraet")), 1)
                self.assertEqual(len(mit_klasse(baum, "zonenflaeche")), 1)
                self.assertEqual(len(mit_klasse(baum, "zonenname")), 1)
                self.assertEqual(len(mit_klasse(baum, "abstand")), 2)
                self.assertEqual(len(mit_klasse(baum, "legendenblock")), 1)

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
