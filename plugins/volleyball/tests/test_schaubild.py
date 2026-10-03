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

import math
import re
import shutil
import struct
import subprocess
import tempfile
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

# Der Zuspieler mit Sonderrolle, daneben zwei ohne: einer ohne den Schluessel
# und einer mit `false`. Beide sollen aussehen wie vor der Hervorhebung.
SONDERROLLE = """
form: halle
spieler:
  - bei: 3
    text: Z
    hervorgehoben: true
  - bei: 4
    text: AA
  - bei: 2
    text: D
    hervorgehoben: false
"""

# Ein Legendenblock mit der Zeile aus dem Referenzbild, vor der "3-m-Linie"
# stand und sich wie deren Anfang las. Vor ihm wird die Gasse gemessen.
ZUSPIELZIEL = """
legende:
  - ueberschrift: Zuspielziel Position 4
    zeilen:
      - Der Ball muss von oben hineinfallen.
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


def farbschemata(baum) -> dict[str, dict[str, str]]:
    """Die Farbvariablen des Bildes, je Schema: {"hell": {...}, "dunkel": {...}}."""
    stil = baum.find(SVG + "style").text

    def farben(block: str) -> dict[str, str]:
        return dict(re.findall(r"--([a-z]+):(#[0-9a-f]{6})",
                               re.search(block, stil).group(1)))

    return {"hell": farben(r"^svg\{([^}]*)\}"),
            "dunkel": farben(r"prefers-color-scheme:dark\)\{svg\{([^}]*)\}")}


def _passt_glied(glied: str, element: ET.Element) -> bool:
    """Ob ein Glied eines Selektors, etwa `text` oder `.a.b`, auf das Element passt."""
    name, *klassen = glied.split(".")
    return ((not name or element.tag == SVG + name)
            and set(klassen) <= set((element.get("class") or "").split()))


def stilwert(baum, element: ET.Element, eigenschaft: str) -> str | None:
    """Welchen Wert eine Eigenschaft an diesem Element aus dem Stylesheet bekommt.

    Gelesen wird das Stylesheet im Bild, so wie ein Betrachter es anwendet:
    von allen Regeln, deren Selektor passt, gewinnt die spezifischste, bei
    Gleichstand die spaetere. Damit prueft ein Test, wie ein Teil aussieht, und
    nicht, an welcher Klasse oder in welcher Regel das steht.

    Verstanden wird die Teilmenge, die das Skript schreibt: Elementnamen,
    Klassen und Nachfahren.
    """
    eltern = {kind: e for e in baum.iter() for kind in e}
    kette = [element]
    while kette[-1] in eltern:
        kette.append(eltern[kette[-1]])

    wert, bester = None, (-1, -1)
    for selektor, erklaerungen in re.findall(r"([^{}]+)\{([^{}]*)\}",
                                             baum.find(SVG + "style").text):
        werte = dict(teil.split(":", 1) for teil in erklaerungen.split(";")
                     if ":" in teil)
        if eigenschaft not in werte:
            continue
        glieder = selektor.split()
        if not glieder or not _passt_glied(glieder[-1], kette[0]):
            continue
        vorfahren = iter(kette[1:])
        if not all(any(_passt_glied(g, e) for e in vorfahren)
                   for g in reversed(glieder[:-1])):
            continue
        gewicht = (sum(g.count(".") for g in glieder),
                   sum(1 for g in glieder if not g.startswith(".")))
        if gewicht >= bester:
            wert, bester = werte[eigenschaft], gewicht
    return wert


def farbvariable(baum, element: ET.Element, eigenschaft: str) -> str:
    """Welche Farbvariable eine Eigenschaft an diesem Element bekommt, ohne `--`."""
    wert = stilwert(baum, element, eigenschaft)
    treffer = re.fullmatch(r"var\(--([a-z]+)\)", wert or "")
    assert treffer, f"{eigenschaft} ist {wert!r} und keine Farbvariable"
    return treffer.group(1)


# Die Schriftgroesse eines Betrachters, wenn nichts anderes gilt: `medium` in
# CSS, und das sind in jedem Browser 16 Pixel.
GRUNDSCHRIFT = 16.0


def schriftgroesse(baum, element: ET.Element) -> float:
    """Wie gross ein Text im Betrachter steht, in Zeicheneinheiten.

    So, wie ein Betrachter die Groesse findet. Im Stylesheet gilt sie nur mit
    Einheit: eine blosse Zahl ist dort ungueltig und faellt weg, anders als im
    Attribut `font-size`, wo sie erlaubt ist. Bleibt nichts, steht der Text in
    der Grundschrift des Betrachters. Wer die Zahl aus dem Stylesheet einfach
    liest, sieht eine Rangfolge, die im Bild nicht ankommt.

    Verstanden werden Pixel, die einzige Einheit, die das Skript schreibt.
    """
    wert = (stilwert(baum, element, "font-size") or "").strip()
    treffer = re.fullmatch(r"(\d+(?:\.\d+)?)px", wert)
    if treffer:
        return float(treffer.group(1))
    if element.get("font-size"):
        return float(element.get("font-size"))
    return GRUNDSCHRIFT


# Wie breit ein Zeichen mindestens ist, als Anteil seiner Schriftgroesse.
# Knapp geschaetzt: ein Wort aus gewoehnlichen Buchstaben ist in einer
# serifenlosen Schrift breiter. Ragt ein Weg schon in diesen Kasten hinein,
# ragt er sicher ins Wort; ragt schon der Kasten ueber das Blatt, ragt das Wort
# erst recht. Die Zahl ist eine Annahme ueber Schrift; das Skript rechnet
# mit seiner eigenen.
MINDESTBREITE = 0.5


def wortkasten(baum, wort: ET.Element) -> tuple[float, float]:
    """Wie weit ein Wort mindestens von seiner Mitte reicht, in Zeicheneinheiten.

    Halbe Breite und halbe Hoehe, in der Schriftgroesse, die der Betrachter
    anwendet, siehe schriftgroesse().
    """
    groesse = schriftgroesse(baum, wort)
    return len(wort.text) * groesse * MINDESTBREITE / 2, groesse / 2


def marker_nach_beschriftung(baum) -> dict[str, tuple[ET.Element, ET.Element]]:
    """Jeder beschriftete Spielermarker samt Beschriftung, nach deren Text.

    Zusammengefunden wird ueber den Ort: die Beschriftung steht in der Mitte
    ihres Markers. Wie die beiden im Markup beieinanderstehen, spielt keine
    Rolle. Ein Marker ohne Beschriftung hat keinen Text, unter dem er stuende,
    und fehlt deshalb.
    """
    texte = {(float(t.get("x")), float(t.get("y"))): t
             for t in mit_klasse(baum, "beschriftung")}
    paare = {}
    for kreis in mit_klasse(baum, "marker"):
        text = texte.get((float(kreis.get("cx")), float(kreis.get("cy"))))
        if text is not None:
            paare[text.text] = (kreis, text)
    return paare


# --------------------------------------------------------------------------

class SchaubildTest(unittest.TestCase):
    def setUp(self) -> None:
        self.ordner = Arbeitsordner()
        self.addCleanup(self.ordner.raeume_auf)

    def zeichne(self, name: str, szene: str) -> ET.Element:
        """Legt die Szene ab, zeichnet sie und gibt das geparste SVG zurueck."""
        self.laufe(name, szene)
        return ET.fromstring(self.bild(name).read_text(encoding="utf-8"))

    def laufe(self, name: str, szene: str) -> subprocess.CompletedProcess:
        """Zeichnet eine Szene und gibt den Lauf samt seinen Meldungen zurueck.

        Fuer die Faelle, in denen nicht nur das Bild zaehlt, sondern auch, was
        das Skript dem Trainer dazu sagt.
        """
        self.ordner.lege_szene_an(name, szene)
        fertig = self.ordner.starte("schaubild.py", name)
        self.assertEqual(fertig.returncode, 0, fertig.stdout + fertig.stderr)
        return fertig

    def bild(self, name: str) -> Path:
        return self.ordner.pfad / "schaubilder" / f"{name}.svg"

    def scheitert(self, name: str, szene: str):
        """Zeichnet eine Szene, die nicht aufgehen darf, und gibt den Lauf zurueck."""
        self.ordner.lege_szene_an(name, szene)
        fertig = self.ordner.starte("schaubild.py", name)
        self.assertNotEqual(fertig.returncode, 0,
                            "eine Szene, die nicht aufgeht, darf nicht gruen sein")
        return fertig

    def zonenwort_mindestens(self, name: str, text: str) -> float:
        """Wie breit das Wort einer Zone im gezeichneten Hallenbild mindestens ist, in Metern.

        Geschaetzt mit dem knappen Wortkasten und umgerechnet ueber das Feld,
        nicht mit der Schaetzung des Skripts. So steht fest, dass das Wort
        wirklich breiter ist als seine Zone, bevor ein Test den Hinweis
        darauf verlangt.
        """
        baum = ET.fromstring(self.bild(name).read_text(encoding="utf-8"))
        wort = next(w for w in mit_klasse(baum, "zonenname") if w.text == text)
        halbe_breite, _ = wortkasten(baum, wort)
        return Feldmass(baum, HALLE).strecke(2 * halbe_breite)

    # -- Szene und Bild ---------------------------------------------------

    def test_szene_und_bild_liegen_unter_demselben_basisnamen(self) -> None:
        # Daran haengt, dass eine Korrektur ein halbes Jahr spaeter drei Zeilen
        # kostet: wer das Bild sieht, findet seine Quelle ohne zu suchen.
        self.zeichne("ue-000042", """
            form: halle
            spieler:
              - bei: 3
        """)

        namen = sorted(p.name for p in (self.ordner.pfad / "schaubilder").iterdir())
        self.assertEqual(namen, ["ue-000042.svg", "ue-000042.szene.yml"])

    def test_eine_szene_ausserhalb_des_ordners_laesst_schaubilder_unberuehrt(self) -> None:
        # Daran haengt die Vorschau-Schleife von volleyball-schaubild: gerendert
        # wird Runde um Runde neben dem Entwurf im Temp-Verzeichnis, und nach
        # schaubilder/ kommt erst, was der Trainer freigegeben hat.
        entwurf = self.ordner.lege_entwurf_an("ue-000042", """
            form: halle
            spieler:
              - bei: 3
        """)

        fertig = self.ordner.starte("schaubild.py", str(entwurf))

        self.assertEqual(fertig.returncode, 0, fertig.stdout + fertig.stderr)
        self.assertTrue((entwurf.parent / "ue-000042.svg").is_file(),
                        "das Bild entsteht neben seiner Szene")
        self.assertFalse((self.ordner.pfad / "schaubilder").exists(),
                         "vor der Freigabe steht in schaubilder/ nichts")

    def test_eine_unbekannte_form_bricht_ab_und_schreibt_keine_datei(self) -> None:
        fertig = self.scheitert("ue-000043", """
            form: turnhalle
            spieler:
              - bei: 3
        """)

        self.assertIn("turnhalle", fertig.stdout)
        self.assertIn("halle", fertig.stdout, "die Meldung nennt, was es gibt")
        self.assertFalse(self.bild("ue-000043").exists(),
                         "eine Szene, die nicht aufgeht, hinterlaesst kein halbes Bild")

    def test_ein_vertippter_schluessel_wird_gemeldet(self) -> None:
        # Sonst waere der Tippfehler die stillste Art, das halbe Bild zu
        # verlieren: `spiler:` ergaebe ein leeres Feld, und das sieht fertig aus.
        fertig = self.scheitert("ue-000044", """
            form: halle
            spiler:
              - bei: 3
        """)

        self.assertIn("spiler", fertig.stdout)
        self.assertFalse(self.bild("ue-000044").exists())

    # -- Der Weg zur Szene -------------------------------------------------

    def test_ein_absoluter_pfad_rendert_auch_ohne_arbeitsordner(self) -> None:
        # Der Pfad sagt schon allein, wo die Szene liegt. Wer so eine Szene von
        # Hand zeichnet, soll das aus jedem Verzeichnis heraus koennen, auch
        # aus einem, ueber dem keine Wurzeldatei steht. Eine Suche vorweg
        # verlangte etwas, das dieser Lauf gar nicht braucht.
        entwurf = self.ordner.lege_entwurf_an("ue-000042", """
            form: halle
            spieler:
              - bei: 3
        """)

        fertig = self.ordner.starte("schaubild.py", str(entwurf),
                                    mit_wurzel=False, verzeichnis=entwurf.parent)

        self.assertEqual(fertig.returncode, 0, fertig.stdout + fertig.stderr)
        self.assertTrue((entwurf.parent / "ue-000042.svg").is_file(),
                        "das Bild entsteht neben seiner Szene")

    def test_ohne_arbeitsordner_steht_der_hinweis_ohne_wortlaut(self) -> None:
        # Der Titelvorschlag kommt von einer Uebungskarte, und ohne
        # Arbeitsordner gibt es keine. Geraten wird deshalb nichts, und
        # abgebrochen erst recht nicht: das Bild steht zu dem Zeitpunkt schon.
        entwurf = self.ordner.lege_entwurf_an("ue-000001", """
            form: halle
            untertitel: ohne etwas darueber
        """)

        fertig = self.ordner.starte("schaubild.py", str(entwurf),
                                    mit_wurzel=False, verzeichnis=entwurf.parent)

        self.assertEqual(fertig.returncode, 0, fertig.stdout + fertig.stderr)
        self.assertTrue((entwurf.parent / "ue-000001.svg").is_file())
        self.assertIn("titel:", fertig.stdout, "der Hinweis steht da")
        self.assertNotIn("Uebungskarte", fertig.stdout, "nur ohne Wortlaut")

    def test_der_titelvorschlag_kommt_aus_dem_ordner_der_szene(self) -> None:
        # Dieselbe Uebungs-ID gibt es in jedem Arbeitsordner. Gemeint ist die
        # Karte aus der Bibliothek, zu der die Szene gehoert, und nicht die
        # aus der, in der der Aufruf zufaellig steht.
        fremd = Arbeitsordner()
        self.addCleanup(fremd.raeume_auf)
        self.ordner.lege_karte_an(id="ue-000042", titel="Zielzone im eigenen Ordner")
        fremd.lege_karte_an(id="ue-000042", titel="Zielzone im fremden Ordner")
        szene = self.ordner.lege_szene_an("ue-000042", """
            form: halle
            untertitel: ohne etwas darueber
        """)

        fertig = self.ordner.starte("schaubild.py", str(szene),
                                    mit_wurzel=False, verzeichnis=fremd.pfad)

        self.assertEqual(fertig.returncode, 0, fertig.stdout + fertig.stderr)
        self.assertIn("Zielzone im eigenen Ordner", fertig.stdout,
                      "der Titel kommt aus der Bibliothek neben der Szene")
        self.assertNotIn("Zielzone im fremden Ordner", fertig.stdout,
                         "und nicht aus der, in der der Aufruf steht")

    def test_ein_entwurf_ohne_wurzel_nimmt_den_ordner_des_aufrufs(self) -> None:
        # Der Rueckfall, und die Vorschau-Schleife von volleyball-schaubild
        # besteht ganz aus ihm: der Entwurf liegt im Temp-Verzeichnis, ueber
        # dem keine Wurzel steht, und der Aufruf steht im Arbeitsordner.
        entwurf = self.ordner.lege_entwurf_an("ue-000001", """
            form: halle
            untertitel: ohne etwas darueber
        """)

        fertig = self.ordner.starte("schaubild.py", str(entwurf),
                                    mit_wurzel=False, verzeichnis=self.ordner.pfad)

        self.assertEqual(fertig.returncode, 0, fertig.stdout + fertig.stderr)
        self.assertIn("Annahme im Halbfeld", fertig.stdout,
                      "ohne Wurzel ueber der Szene zaehlt die ueber dem Aufruf")

    def test_die_angegebene_wurzel_sticht_den_ordner_der_szene(self) -> None:
        # Wer `--wurzel` nennt, sagt damit, welche Bibliothek gilt. Weder der
        # Ordner der Szene noch der des Aufrufs redet dann noch mit.
        fremd = Arbeitsordner()
        self.addCleanup(fremd.raeume_auf)
        self.ordner.lege_karte_an(id="ue-000042", titel="Zielzone aus der genannten Wurzel")
        fremd.lege_karte_an(id="ue-000042", titel="Zielzone neben der Szene")
        szene = fremd.lege_szene_an("ue-000042", """
            form: halle
            untertitel: ohne etwas darueber
        """)

        fertig = self.ordner.starte("schaubild.py", str(szene), verzeichnis=fremd.pfad)

        self.assertEqual(fertig.returncode, 0, fertig.stdout + fertig.stderr)
        self.assertIn("Zielzone aus der genannten Wurzel", fertig.stdout,
                      "der Titel kommt aus der genannten Wurzel")
        self.assertNotIn("Zielzone neben der Szene", fertig.stdout,
                         "Szene und Aufruf stehen beide im fremden Ordner "
                         "und reden trotzdem nicht mit")

    def test_ein_basisname_ohne_wurzel_bricht_ab_und_sagt_warum(self) -> None:
        # Die Gegenprobe: ein blosser Name sagt nicht, wo die Szene liegt.
        # Dafuer braucht es den Arbeitsordner wirklich, und die Meldung bleibt
        # die alte.
        daneben = self.ordner.lege_entwurfsordner_an()

        fertig = self.ordner.starte("schaubild.py", "ue-000042",
                                    mit_wurzel=False, verzeichnis=daneben)

        gesagt = fertig.stdout + fertig.stderr
        self.assertNotEqual(fertig.returncode, 0)
        self.assertIn("trainingsplanung-root.yml", gesagt)
        self.assertIn("--wurzel", gesagt, "die Meldung nennt den Ausweg")

    def test_ein_relativer_pfad_zaehlt_ab_der_wurzel(self) -> None:
        # Die dritte Form, und die einzige, bei der beides im Spiel ist:
        # Wurzel und Pfad. Gerufen wird von woanders, damit der Test wirklich
        # die Wurzel misst und nicht das Verzeichnis des Testlaufs.
        self.ordner.lege_szene_an("ue-000042", """
            form: halle
            spieler:
              - bei: 3
        """)
        daneben = self.ordner.lege_entwurfsordner_an()

        fertig = self.ordner.starte("schaubild.py", "schaubilder/ue-000042.szene.yml",
                                    verzeichnis=daneben)

        self.assertEqual(fertig.returncode, 0, fertig.stdout + fertig.stderr)
        self.assertTrue(self.bild("ue-000042").is_file(),
                        "das Bild steht in schaubilder/, nicht im Verzeichnis des Aufrufs")

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

    # -- Der hervorgehobene Spieler ------------------------------------------

    def test_ein_hervorgehobener_spieler_ist_gefuellt_die_uebrigen_umriss(self) -> None:
        # Im Referenzbild ist der Zuspieler gefuellt gezeichnet und alle anderen
        # als Umriss: auf einen Blick sieht man, wer nicht mitrotiert.
        baum = self.zeichne("sonderrolle", SONDERROLLE)

        marker = marker_nach_beschriftung(baum)
        self.assertEqual(sorted(marker), ["AA", "D", "Z"])
        # Gefuellt in Strichfarbe, das Kuerzel darin in Feldfarbe.
        kreis, kuerzel = marker["Z"]
        self.assertEqual(farbvariable(baum, kreis, "fill"), "strich")
        self.assertEqual(farbvariable(baum, kuerzel, "fill"), "feld")
        # Ohne den Schluessel und mit `false` wie bisher: Umriss auf Feldfarbe,
        # das Kuerzel in Strichfarbe.
        for ohne in ("AA", "D"):
            with self.subTest(spieler=ohne):
                kreis, kuerzel = marker[ohne]
                self.assertEqual(farbvariable(baum, kreis, "fill"), "feld")
                self.assertEqual(farbvariable(baum, kuerzel, "fill"), "strich")
        # Der Rand bleibt bei allen, wie er war.
        self.assertEqual({farbvariable(baum, kreis, "stroke")
                          for kreis, _ in marker.values()}, {"strich"})

    def test_das_kuerzel_im_gefuellten_marker_ist_in_beiden_farbschemata_lesbar(
            self) -> None:
        baum = self.zeichne("sonderrolle", SONDERROLLE)

        kreis, kuerzel = marker_nach_beschriftung(baum)["Z"]
        for name, farben in farbschemata(baum).items():
            with self.subTest(schema=name):
                self.assertGreaterEqual(
                    kontrast(farben[farbvariable(baum, kuerzel, "fill")],
                             farben[farbvariable(baum, kreis, "fill")]), 4.5)

    def test_gefuellt_und_umriss_unterscheiden_sich_auch_in_graustufen(self) -> None:
        # Das Kontrastverhaeltnis rechnet allein mit der Helligkeit, und genau
        # die bleibt im Graustufendruck uebrig. 3 ist das, was WCAG fuer
        # Grafik verlangt, die man erkennen muss.
        baum = self.zeichne("sonderrolle", SONDERROLLE)

        marker = marker_nach_beschriftung(baum)
        gefuellt = farbvariable(baum, marker["Z"][0], "fill")
        umriss = farbvariable(baum, marker["AA"][0], "fill")
        for name, farben in farbschemata(baum).items():
            with self.subTest(schema=name):
                self.assertGreaterEqual(kontrast(farben[gefuellt], farben[umriss]), 3)

    def test_hervorgehoben_nimmt_nur_einen_wahrheitswert(self) -> None:
        # `ja` ist in dieser Szene ein Wort und `1` eine Zahl. Still als wahr
        # oder falsch gelesen, stuende ein Marker anders im Bild, als der
        # Trainer meint, und das sieht man ihm nicht an. `"true"` in
        # Anfuehrungszeichen ist ebenfalls ein Wort; die Meldung sagt dann,
        # woran es liegt.
        for name, wert in (("ja", "ja"), ("zahl", "1"), ("zitat", '"true"')):
            with self.subTest(wert=wert):
                fertig = self.scheitert(f"sonderrolle-{name}", f"""
                    form: halle
                    spieler:
                      - bei: 4
                      - bei: 3
                        text: Z
                        hervorgehoben: {wert}
                """)

                self.assertIn("Spieler 2", fertig.stdout)
                self.assertIn("hervorgehoben", fertig.stdout)
                self.assertIn("true oder false", fertig.stdout)
                self.assertFalse(self.bild(f"sonderrolle-{name}").exists())
                if name == "zitat":
                    self.assertIn("Anfuehrungszeichen", fertig.stdout)

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
        # einen Kasten weg, wo nie einer stand.
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

        def rang(klasse: str) -> int:
            return reihenfolge.index(mit_klasse(baum, klasse)[0])

        zone = rang("zonenflaeche")
        # Ueber einer Zone stehen Marker und laufen Wege. Eine Flaeche, die
        # kraeftig genug waere, um aufzufallen, verdeckte sonst, worum es geht.
        self.assertLess(zone, rang("marker"))
        self.assertLess(zone, rang("weg"))
        # Die Angriffslinie gehoert zum Boden und nicht zum Aufbau. Eine
        # Zielzone darueber loeschte die Linie, an der sie abgemessen wird.
        self.assertLess(zone, rang("angriffslinie"))

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

        def rang(klasse: str) -> int:
            return reihenfolge.index(mit_klasse(baum, klasse)[0])

        # Der Marker liegt wirklich auf dem Wort: sonst pruefte der Test die
        # Reihenfolge an einem Fall, in dem sie egal waere.
        feld = Feldmass(baum, HALLE)
        name = mit_klasse(baum, "zonenname")[0]
        kreis = mit_klasse(baum, "marker")[0]
        abstand = abs(float(name.get("y")) - float(kreis.get("cy")))
        self.assertLess(abstand, float(kreis.get("r")))

        self.assertGreater(rang("zonenname"), rang("marker"))
        self.assertLess(rang("zonenflaeche"), rang("marker"),
                        "die Flaeche bleibt trotzdem unten")
        # Und massstaeblich steht das Wort weiter da, wo es hingehoert.
        self.assertAlmostEqual(feld.meter(float(name.get("x")), 0.0)[0], 4.5,
                               places=2)

    def test_das_wort_einer_zone_bleibt_auch_ueber_einem_gefuellten_marker_lesbar(
            self) -> None:
        # Ein hervorgehobener Marker ist in Strichfarbe gefuellt, und in der
        # steht auch das Wort der Zone. Wo beide sich kreuzen, stuende Strich
        # auf Strich. Lesbar bleibt das Wort, weil jeder Buchstabe einen Hof
        # in einer Farbe mitbringt, von der er sich abhebt.
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
                hervorgehoben: true
        """)

        name = mit_klasse(baum, "zonenname")[0]
        kreis = mit_klasse(baum, "marker")[0]
        self.assertLess(abs(float(name.get("y")) - float(kreis.get("cy"))),
                        float(kreis.get("r")), "das Wort liegt auf dem Marker")

        schrift = farbvariable(baum, name, "fill")
        hof = farbvariable(baum, name, "stroke")
        self.assertEqual(stilwert(baum, name, "paint-order"), "stroke",
                         "der Hof liegt hinter den Buchstaben, nicht darauf")
        self.assertGreater(float(stilwert(baum, name, "stroke-width")), 0)
        for schema, farben in farbschemata(baum).items():
            with self.subTest(schema=schema):
                self.assertGreaterEqual(kontrast(farben[schrift], farben[hof]), 4.5)

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

    def test_ein_zonenwort_breiter_als_die_zone_wird_gemeldet(self) -> None:
        # Die erste Zone passt und bleibt ungenannt. Genannt wird die, um die
        # es geht, und mit ihr der Ausweg.
        fertig = self.laufe("schmal", """
            form: halle
            zonen:
              - text: Ziel
                form: rechteck
                bei: [4.5, 3.0]
                groesse: [3.0, 2.0]
              - text: Zielzone Position 4
                form: rechteck
                bei: [1.5, 6.0]
                groesse: [1.5, 2.0]
        """)

        self.assertGreater(self.zonenwort_mindestens("schmal", "Zielzone Position 4"),
                           1.5, "das Wort ragt im Bild wirklich ueber die Zone")
        self.assertIn("Zone 2", fertig.stdout)
        self.assertIn("Zielzone Position 4", fertig.stdout)
        self.assertNotIn("Zone 1", fertig.stdout)
        self.assertIn("kuerzeres Wort", fertig.stdout)
        self.assertIn("breitere Zone", fertig.stdout)
        # Eine Kleinigkeit kostet keine Runde der Schleife: das Bild steht da.
        self.assertTrue(self.bild("schmal").exists())

    def test_ein_zonenwort_das_passt_bleibt_ohne_hinweis(self) -> None:
        # Die Zielzone des Referenzbildes, 1,28 m breit: „Ziel" steht dort im
        # Bild innerhalb des Randes. Daneben eine flache Zone, in der das Wort
        # zwar hoeher ist als die Zone, aber schmaler, und ein Kreis. Ein
        # Hinweis, der hier anschluege, lehrte den Trainer, ihn zu ueberlesen.
        fertig = self.laufe("passt", """
            form: halle
            zonen:
              - text: Ziel
                form: rechteck
                bei: [0.79, 7.43]
                groesse: [1.28, 2.85]
              - text: Zielzone
                form: rechteck
                bei: [4.5, 3.0]
                groesse: [4.0, 0.3]
              - text: Ziel
                form: kreis
                bei: [6.0, 6.0]
                groesse: 1.5
        """)

        self.assertEqual(len(fertig.stdout.strip().splitlines()), 1,
                         f"gesagt wird nur, dass geschrieben ist:\n{fertig.stdout}")

    def test_ein_kreis_misst_sein_wort_am_durchmesser(self) -> None:
        # Beim Kreis steht das Wort in der Mitte, wo er am breitesten ist.
        # Derselbe Kreis mit doppeltem Durchmesser traegt das Wort.
        szene = """
            form: halle
            zonen:
              - text: Aufschlagziel
                form: kreis
                bei: [4.5, 3.0]
                groesse: {groesse}
        """
        eng = self.laufe("eng", szene.format(groesse=2.0))

        self.assertGreater(self.zonenwort_mindestens("eng", "Aufschlagziel"), 2.0,
                           "das Wort ragt im Bild wirklich ueber den Kreis")
        self.assertIn("Zone 1", eng.stdout)
        self.assertIn("Aufschlagziel", eng.stdout)
        self.assertTrue(self.bild("eng").exists())

        weit = self.laufe("weit", szene.format(groesse=4.0))
        self.assertEqual(len(weit.stdout.strip().splitlines()), 1,
                         f"gesagt wird nur, dass geschrieben ist:\n{weit.stdout}")

    def test_ein_zu_breites_zonenwort_bleibt_so_gross_wie_die_uebrigen(self) -> None:
        # Gemeldet wird, verkleinert nicht. Ein Wort in kleinerer Schrift
        # machte das Bild uneinheitlich, und ueber den Hinweis haette der
        # Trainer nichts mehr, was er aendern koennte.
        baum = self.zeichne("gleich", """
            form: halle
            zonen:
              - text: Ziel
                form: rechteck
                bei: [4.5, 3.0]
                groesse: [3.0, 2.0]
              - text: Zielzone Position 4
                form: rechteck
                bei: [1.5, 6.0]
                groesse: [1.5, 2.0]
            geraete:
              - text: Kasten
                teile:
                  - form: rechteck
                    bei: [7.0, 12.0]
                    groesse: [1.6, 0.8]
            stellen:
              - bei: [4.5, 14.0]
                text: Feldmitte
        """)

        passt, zu_breit = mit_klasse(baum, "zonenname")
        self.assertEqual(zu_breit.text, "Zielzone Position 4")
        groesse = schriftgroesse(baum, zu_breit)
        for andere in (passt, mit_klasse(baum, "geraetname")[0],
                       mit_klasse(baum, "stelle")[0]):
            with self.subTest(klasse=andere.get("class")):
                self.assertEqual(schriftgroesse(baum, andere), groesse)

    # -- Stellen -----------------------------------------------------------

    def test_eine_stelle_steht_an_ihrem_ort(self) -> None:
        # In denselben drei Formen wie alles andere, damit es keine zweite
        # Schreibweise zu lernen gibt, und auf jeder Grundform, die sie
        # hergibt. Geprueft wird der Ort in Metern, mit etwas Spielraum, wo die
        # Angabe eine Flaeche meint und keinen Punkt.
        for name, kopf, bei, masse, klasse, (links, rechts, unten, oben) in (
            ("meter", "form: halle", "[3.0, 12.5]", HALLE, "feld",
             (2.99, 3.01, 12.49, 12.51)),
            # Die Drittelflaeche, die im Feld die Nummer 4 traegt.
            ("position", "form: halle", "4", HALLE, "feld", (0, 3, 6, 9)),
            # Am Netz und in der Mitte der Breite, dort, wo geblockt wird.
            ("rolle", "form: beach", "block", BEACH, "feld",
             (8 / 3, 16 / 3, 16 / 3, 8)),
            ("leinwand", "form: frei\ngroesse: [12.0, 9.0]", "[3.0, 7.5]",
             LEINWAND, "leinwand", (2.99, 3.01, 7.49, 7.51)),
        ):
            with self.subTest(ort=name):
                baum = self.zeichne(f"stelle-{name}", kopf + f"""
stellen:
  - bei: {bei}
    text: Feldmitte
""")

                bezug = Feldmass(baum, masse, klasse)
                woerter = mit_klasse(baum, "stelle")
                self.assertEqual([e.text for e in woerter], ["Feldmitte"])
                x, y = bezug.meter(float(woerter[0].get("x")),
                                   float(woerter[0].get("y")))
                self.assertTrue(links < x < rechts, f"x liegt bei {x:.2f} m")
                self.assertTrue(unten < y < oben, f"y liegt bei {y:.2f} m")

    def test_auch_eine_stelle_nimmt_nur_die_orte_ihrer_grundform(self) -> None:
        # So wie ueberall sonst. Still auf eine Hallenposition zurueckzufallen
        # hiesse, ein Wort an einen Ort zu setzen, den es im Sand nicht gibt.
        for name, form, bei, wort in (("sand", "beach", "4", "Positionsnummern"),
                                      ("halle", "halle", "block", "Rollen")):
            with self.subTest(form=form):
                fertig = self.scheitert(f"stelle-{name}", f"""
                    form: {form}
                    stellen:
                      - bei: {bei}
                        text: Feldmitte
                """)

                self.assertIn("Stelle 1", fertig.stdout)
                self.assertIn(wort, fertig.stdout)
                self.assertFalse(self.bild(f"stelle-{name}").exists())

    def test_eine_stelle_ohne_wort_ohne_ort_oder_mit_vertipptem_schluessel_bricht_ab(
            self) -> None:
        # Eine Stelle ist nur ein Wort. Ohne es stuende in der Szene etwas,
        # das nach fertig aussieht und im Bild nicht vorkommt. Ein vertippter
        # Schluessel waere die stillste Art, das Wort zu verlieren.
        for name, eintrag, gesucht in (
            ("ohne-text", "- bei: [4.5, 4.5]", ["text", "Wort"]),
            ("leerer-text", '- bei: [4.5, 4.5]\n    text: ""', ["text", "Wort"]),
            ("ohne-bei", "- text: Feldmitte", ["bei"]),
            ("vertippt", "- bei: [4.5, 4.5]\n    txt: Feldmitte", ["txt"]),
        ):
            with self.subTest(fall=name):
                fertig = self.scheitert(f"stelle-{name}",
                                        "form: halle\nstellen:\n  " + eintrag)

                self.assertIn("Stelle 1", fertig.stdout)
                for wort in gesucht:
                    self.assertIn(wort, fertig.stdout)
                self.assertFalse(self.bild(f"stelle-{name}").exists())

    def test_eine_stelle_zeichnet_nur_ihr_wort(self) -> None:
        # Keinen Punkt, keinen Rand, keine Flaeche. Mit einem Rand saehe sie
        # aus wie eine Zone, und die Spieler sperrten in der Halle etwas ab,
        # das es nicht gibt (ADR-0007).
        # Die Zone steht in beiden Szenen, damit es ein Wort gibt, mit dessen
        # Schrift sich die der Stelle vergleichen laesst.
        zone = """
form: halle
zonen:
  - text: Zielzone
    form: rechteck
    bei: [4.5, 14.0]
    groesse: [3.0, 2.0]
"""
        ohne = self.zeichne("ohne-stelle", zone)
        mit = self.zeichne("mit-stelle", zone + """
stellen:
  - bei: [4.5, 4.5]
    text: Feldmitte
""")

        def formen(baum) -> list[tuple[str, str]]:
            umrisse = {SVG + t for t in ("rect", "circle", "ellipse", "line",
                                         "path", "polygon", "polyline")}
            return sorted((e.tag, e.get("class") or "") for e in baum.iter()
                          if e.tag in umrisse)

        self.assertEqual(formen(mit), formen(ohne),
                         "zum Bild kommt nichts dazu, was eine Form haette")
        wort = mit_klasse(mit, "stelle")[0]
        # Einen Hof hat das Wort, einen sichtbaren Rand nicht: der Hof hat die
        # Farbe des Feldes, auf dem das Wort steht, und hebt sich davon nicht ab.
        self.assertEqual(farbvariable(mit, wort, "stroke"), "feld",
                         "der Hof hebt sich vom Feld darunter ab")
        # In Strichfarbe und so gross wie das Wort einer Zone. Eine Stelle ist
        # eine Beschriftung im Feld wie jede andere, nur ohne etwas darunter.
        self.assertEqual(farbvariable(mit, wort, "fill"), "strich")
        self.assertEqual(schriftgroesse(mit, wort),
                         schriftgroesse(mit, mit_klasse(mit, "zonenname")[0]))

    def test_das_wort_einer_stelle_steht_ueber_allem_im_bild(self) -> None:
        # Auch ueber den Zonenwoertern und den Markern. Eine Stelle hat nichts
        # als ihr Wort; liegt etwas darueber, ist sie weg.
        baum = self.zeichne("obenauf", """
            form: halle
            zonen:
              - text: Zielzone
                form: rechteck
                bei: [4.5, 6.0]
                groesse: [3.0, 2.0]
            geraete:
              - text: Kasten
                teile:
                  - form: rechteck
                    bei: [7.0, 3.0]
                    groesse: [1.6, 0.8]
            abstaende:
              - art: masskette
                von: [1.0, 2.0]
                nach: [7.0, 2.0]
            spieler:
              - bei: 3
                text: Z
                hervorgehoben: true
            wege:
              - art: ballweg
                von: 3
                nach: [4.5, 4.5]
            stellen:
              - bei: [4.5, 4.5]
                text: Feldmitte
        """)

        reihenfolge = list(baum.iter())
        wort = reihenfolge.index(mit_klasse(baum, "stelle")[0])
        for klasse in ("zonenname", "marker", "beschriftung", "weg", "teil",
                       "geraetname", "masslinie", "massbeschriftung", "netz"):
            with self.subTest(unter=klasse):
                self.assertGreater(wort, reihenfolge.index(mit_klasse(baum, klasse)[-1]))

    def test_das_wort_einer_stelle_hat_einen_hof_in_der_farbe_seines_grundes(
            self) -> None:
        # Ohne Hof scheint ein Weg, der nur vorbeilaeuft, zwischen den
        # Buchstaben durch, und eine Stelle auf einer Linie des Feldes wird
        # von ihr durchgestrichen. Der Hof hat die Farbe dessen, was unter
        # dem Wort zu sehen ist. Neben dem Feld ist das das Papier: ein Hof in
        # Feldfarbe schimmerte dort im dunklen Schema um die Buchstaben.
        for name, kopf, bei, grund in (
            ("im-feld", "form: halle", "[4.5, 3.0]", "feld"),
            # Auf der Angriffslinie, drei Meter vor dem Netz.
            ("auf-der-linie", "form: halle", "[4.5, 6.0]", "feld"),
            ("neben-dem-feld", "form: halle", "[10.4, 6.0]", "papier"),
            ("in-der-zone", "form: halle", "[4.5, 14.0]", "zone"),
            ("im-kreis", "form: halle", "[7.0, 3.0]", "zone"),
            # In der Ecke des Quadrats um den Kreis, aber nicht im Kreis.
            ("neben-dem-kreis", "form: halle", "[7.8, 3.8]", "feld"),
            ("auf-der-leinwand", "form: frei\ngroesse: [12.0, 9.0]",
             "[3.0, 7.5]", "feld"),
            ("neben-der-leinwand", "form: frei\ngroesse: [12.0, 9.0]",
             "[13.5, 4.0]", "papier"),
        ):
            with self.subTest(ort=name):
                baum = self.zeichne(f"hof-{name}", kopf + f"""
zonen:
  - text: Ziel
    form: rechteck
    bei: [4.5, 14.0]
    groesse: [3.0, 2.0]
  - text: Ziel
    form: kreis
    bei: [7.0, 3.0]
    groesse: 2.0
stellen:
  - bei: {bei}
    text: Feldmitte
""")

                wort = mit_klasse(baum, "stelle")[0]
                self.assertEqual(farbvariable(baum, wort, "stroke"), grund)
                self.assertEqual(stilwert(baum, wort, "paint-order"), "stroke",
                                 "der Hof liegt hinter den Buchstaben, nicht darauf")
                self.assertGreater(float(stilwert(baum, wort, "stroke-width")), 0)

    def test_eine_stelle_neben_dem_feld_bleibt_ganz_im_bild(self) -> None:
        # Rechts neben dem Feld auf Hoehe des Netzes, wo der Pfosten steht.
        # Ein angeschnittenes Wort ist die stillste aller Fehlermeldungen.
        def mit(text: str) -> ET.Element:
            return self.zeichne(f"pfosten-{len(text)}", f"""
                form: halle
                stellen:
                  - bei: [10.0, 9.0]
                    text: {text}
            """)

        kurz, lang = mit("Pfosten"), mit("Netzpfosten")

        wort = mit_klasse(lang, "stelle")[0]
        halb, _ = wortkasten(lang, wort)
        self.assertLessEqual(float(wort.get("x")) + halb, zahlen(lang.get("viewBox"))[2],
                             "das Wort steht ganz im Bild")
        self.assertGreater(zahlen(lang.get("viewBox"))[2],
                           zahlen(kurz.get("viewBox"))[2],
                           "das laengere Wort braucht mehr Blatt")
        self.assertAlmostEqual(Feldmass(kurz, HALLE).breite,
                               Feldmass(lang, HALLE).breite, places=2,
                               msg="gewachsen ist das Blatt, nicht das Feld")

    def pruefe_vor_dem_wort(self, baum, punkt: tuple[float, float]) -> None:
        """Der Punkt liegt ausserhalb des Kastens um das Wort der ersten Stelle."""
        wort = mit_klasse(baum, "stelle")[0]
        breit, hoch = wortkasten(baum, wort)
        dx = abs(punkt[0] - float(wort.get("x")))
        dy = abs(punkt[1] - float(wort.get("y")))
        self.assertTrue(dx >= breit or dy >= hoch,
                        f"der Weg reicht ins Wort: {dx:.1f} von {breit:.1f} "
                        f"waagerecht, {dy:.1f} von {hoch:.1f} senkrecht")

    def test_ein_gerader_weg_an_einer_stelle_hoert_vor_dem_wort_auf(self) -> None:
        # Sonst liefe die Pfeilspitze durch das Wort, und beide waeren
        # schlecht zu lesen. Das gilt am Ende eines Weges wie an seinem
        # Anfang.
        baum = self.zeichne("zur-mitte", """
            form: halle
            stellen:
              - bei: [5.0, 5.0]
                text: Feldmitte
            wege:
              - art: ballweg
                von: [0.5, 5.0]
                nach: [5.0, 5.0]
              - art: laufweg
                von: [5.0, 5.0]
                nach: [5.0, 1.0]
        """)

        feld = Feldmass(baum, HALLE)
        ball, lauf = (zahlen(mit_klasse(baum, art)[0].get("d"))
                      for art in ("ballweg", "laufweg"))
        self.pruefe_vor_dem_wort(baum, (ball[2], ball[3]))
        self.pruefe_vor_dem_wort(baum, (lauf[0], lauf[1]))
        # Das andere Ende bleibt, wo es angesagt ist.
        self.assertEqual(tuple(round(w, 2) for w in feld.meter(ball[0], ball[1])),
                         (0.5, 5.0))
        self.assertEqual(tuple(round(w, 2) for w in feld.meter(lauf[2], lauf[3])),
                         (5.0, 1.0))
        # Und gekuerzt wird um einen Kasten und nicht um einen Kreis: das Wort
        # ist breiter als hoch, also bleibt waagerecht mehr Weg weg.
        waagerecht = feld.strecke(abs(ball[2] - ball[0]))
        senkrecht = feld.strecke(abs(lauf[3] - lauf[1]))
        self.assertLess(waagerecht, senkrecht,
                        "beide Wege sind ungekuerzt 4,5 und 4 m lang")

    def test_ein_gekruemmter_weg_an_einer_stelle_hoert_vor_dem_wort_auf(self) -> None:
        # `bogen` soll keine Ausnahme sein: gekuerzt wird wie am Marker, und
        # die Pfeilhoehe bleibt dabei die angesagte.
        baum = self.zeichne("bogen-zur-mitte", """
            form: halle
            stellen:
              - bei: [5.0, 5.0]
                text: Feldmitte
            wege:
              - art: ballweg
                von: [1.0, 1.0]
                nach: [5.0, 5.0]
                bogen: 1.5
              - art: laufweg
                von: [5.0, 5.0]
                nach: [8.0, 1.0]
                bogen: -1.0
        """)

        feld = Feldmass(baum, HALLE)
        ball, lauf = (mit_klasse(baum, art)[0].get("d")
                      for art in ("ballweg", "laufweg"))
        self.assertIn("Q", ball)
        self.assertIn("Q", lauf)
        self.pruefe_vor_dem_wort(baum, tuple(zahlen(ball)[4:]))
        self.pruefe_vor_dem_wort(baum, tuple(zahlen(lauf)[:2]))
        self.assertAlmostEqual(pfeilhoehe(feld, ball), 1.5, places=2)
        self.assertAlmostEqual(pfeilhoehe(feld, lauf), 1.0, places=2)

    def test_auch_ein_kurzer_weg_hoert_vor_dem_wort_auf(self) -> None:
        # Ein Wort reicht waagerecht weiter als ein Marker. Ein Weg von zweieinhalb
        # Metern ist kurz, aber nicht so kurz, dass er vor "Feldmitte" nicht mehr
        # Platz haette.
        baum = self.zeichne("kurz-zur-mitte", """
            form: halle
            stellen:
              - bei: [5.0, 5.0]
                text: Feldmitte
            wege:
              - art: ballweg
                von: [2.5, 5.0]
                nach: [5.0, 5.0]
        """)

        feld = Feldmass(baum, HALLE)
        d = zahlen(mit_klasse(baum, "weg")[0].get("d"))
        self.pruefe_vor_dem_wort(baum, (d[2], d[3]))
        self.assertEqual(tuple(round(w, 2) for w in feld.meter(d[0], d[1])),
                         (2.5, 5.0), "der Anfang bleibt, wo er angesagt ist")

    def name_in_metern(self, baum, feld: Feldmass) -> tuple[float, float, float, float]:
        """Der Kasten um den Namen des ersten Geraets: links, unten, rechts, oben in Metern."""
        wort = mit_klasse(baum, "geraetname")[0]
        breit, hoch = wortkasten(baum, wort)
        x, y = feld.meter(float(wort.get("x")), float(wort.get("y")))
        return (x - feld.strecke(breit), y - feld.strecke(hoch),
                x + feld.strecke(breit), y + feld.strecke(hoch))

    def test_die_spitze_eines_weges_sitzt_nicht_auf_dem_namen_eines_geraets(
            self) -> None:
        # Der Annahmepfeil aus dem Referenzbild: Er endet an der Unterkante
        # der Zielmatte, und gleich darunter steht ihr Name. Das Ende selbst
        # liegt knapp ueber dem Wort, die Spitze dahinter aber sass auf
        # „Zielmatte". Der Weg hoert jetzt vor dem Namen auf, auf der Seite,
        # von der er kommt.
        baum = self.zeichne("zielmatte", """
            form: halle
            geraete:
              - text: Zielmatte
                teile:
                  - form: rechteck
                    bei: [5.55, 7.88]
                    groesse: [2.85, 1.35]
            wege:
              - art: ballweg
                von: [4.5, 1.8]
                nach: [6.08, 7.05]
                bogen: -0.6
        """)

        feld = Feldmass(baum, HALLE)
        d = zahlen(mit_klasse(baum, "weg")[0].get("d"))
        _, unten, _, _ = self.name_in_metern(baum, feld)
        _, ende = feld.meter(d[4], d[5])
        self.assertLess(ende, unten, "der Weg endet unter dem Namen")
        self.assertLess(unten - ende, 0.5, "und nicht weit davor")
        self.assertEqual(tuple(round(w, 2) for w in feld.meter(d[0], d[1])),
                         (4.5, 1.8), "der Anfang bleibt, wo er angesagt ist")

    def test_ein_weg_im_namen_eines_geraets_beginnt_und_endet_an_dessen_rand(
            self) -> None:
        # Wie am Wort einer Stelle, an beiden Enden des Weges.
        baum = self.zeichne("im-namen", """
            form: halle
            geraete:
              - text: Zielmatte
                teile:
                  - form: rechteck
                    bei: [4.5, 8.0]
                    groesse: [2.0, 1.0]
            wege:
              - art: ballweg
                von: [0.5, 6.95]
                nach: [4.5, 6.95]
              - art: laufweg
                von: [4.5, 6.95]
                nach: [4.5, 2.0]
        """)

        feld = Feldmass(baum, HALLE)
        links, unten, _, _ = self.name_in_metern(baum, feld)
        ball, lauf = (zahlen(mit_klasse(baum, art)[0].get("d"))
                      for art in ("ballweg", "laufweg"))
        self.assertLess(feld.meter(ball[2], ball[3])[0], links,
                        "der Ballweg endet links vor dem Namen")
        self.assertLess(feld.meter(lauf[0], lauf[1])[1], unten,
                        "der Laufweg beginnt unter dem Namen")
        self.assertEqual(tuple(round(w, 2) for w in feld.meter(ball[0], ball[1])),
                         (0.5, 6.95))
        self.assertEqual(tuple(round(w, 2) for w in feld.meter(lauf[2], lauf[3])),
                         (4.5, 2.0))

    def test_ein_weg_der_den_namen_eines_geraets_nicht_erreicht_bleibt_ganz(
            self) -> None:
        # Gekuerzt wird nur, wo die Spitze im Namen saesse. Ein Weg, der kurz
        # vor dem Namen aufhoert, einer, der von oben auf das Geraet zeigt,
        # einer, der seitlich neben dem Namen endet, und einer, der von unten
        # durch den Namen bis in die Mitte des Geraets laeuft, bleiben, wie
        # sie angesagt sind. Der letzte zeigt auf das Geraet und nicht auf
        # seinen Namen; vor dem Namen gekuerzt, zeigte er auf nichts mehr.
        baum = self.zeichne("vor-dem-namen", """
            form: halle
            geraete:
              - text: Zielmatte
                teile:
                  - form: rechteck
                    bei: [5.55, 7.88]
                    groesse: [2.85, 1.35]
            wege:
              - art: ballweg
                von: [5.55, 1.8]
                nach: [5.55, 6.0]
              - art: ballweg
                von: [5.55, 15.0]
                nach: [5.55, 8.6]
              - art: laufweg
                von: [8.5, 6.65]
                nach: [7.2, 6.65]
              - art: laufweg
                von: [5.0, 1.8]
                nach: [5.0, 7.88]
        """)

        feld = Feldmass(baum, HALLE)
        _, unten, rechts, oben = self.name_in_metern(baum, feld)
        self.assertLess(6.0, unten, "der erste Weg endet wirklich vor dem Namen")
        self.assertLess(rechts, 7.2, "der dritte wirklich rechts daneben")
        self.assertLess(oben, 7.88, "und der vierte laeuft wirklich hindurch")
        enden = [tuple(round(w, 2) for w in feld.meter(*zahlen(e.get("d"))[2:4]))
                 for e in mit_klasse(baum, "weg")]
        self.assertEqual(enden, [(5.55, 6.0), (5.55, 8.6), (7.2, 6.65), (5.0, 7.88)])

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

    def pruefe_neben_der_linie(self, baum, gruppe: ET.Element) -> None:
        """Die Zahl einer Abstandsangabe steht neben ihrer Linie und nicht darauf.

        Gemessen wird quer zur Linie: wie weit die Mitte des Wortes von ihr
        weg ist, und wie weit der Kasten um das Wort in diese Richtung
        reicht. Reicht der Kasten weiter, laeuft die Linie durch das Wort.
        """
        linie = mit_klasse(gruppe, "masslinie")[0]
        wort = mit_klasse(gruppe, "massbeschriftung")[0]
        x1, y1, x2, y2 = (float(linie.get(a)) for a in ("x1", "y1", "x2", "y2"))
        laenge = math.hypot(x2 - x1, y2 - y1)
        nx, ny = -(y2 - y1) / laenge, (x2 - x1) / laenge
        quer = abs((float(wort.get("x")) - x1) * nx + (float(wort.get("y")) - y1) * ny)
        breit, hoch = wortkasten(baum, wort)
        self.assertGreater(quer, breit * abs(nx) + hoch * abs(ny),
                           f"die Linie laeuft durch {wort.text!r}")

    def test_die_zahl_eines_senkrechten_abstands_steht_neben_ihrer_linie(self) -> None:
        # In ue-0039 sollte ein Pfeil vom Angreifer zum Verteidiger "5 bis 6 m"
        # zeigen, und die Linie strich "bis" durch. Neben einer senkrechten
        # Linie steht das Wort mit seiner ganzen Breite quer zu ihr, auf
        # beiden Seiten, die der Versatz waehlen kann.
        baum = self.zeichne("senkrecht", """
            form: beach
            abstaende:
              - art: pfeil
                von: [4.0, 9.0]
                nach: [4.0, 3.5]
                text: 5 bis 6 m
              - art: masskette
                von: [1.0, 2.0]
                nach: [1.0, 6.0]
                versatz: -0.5
                text: gut 4 m bis zur Linie
        """)

        for gruppe in mit_klasse(baum, "abstand"):
            with self.subTest(wort=mit_klasse(gruppe, "massbeschriftung")[0].text):
                self.pruefe_neben_der_linie(baum, gruppe)
                # Neben der Mitte der Linie, nicht hoeher oder tiefer.
                linie = mit_klasse(gruppe, "masslinie")[0]
                self.assertAlmostEqual(
                    float(mit_klasse(gruppe, "massbeschriftung")[0].get("y")),
                    (float(linie.get("y1")) + float(linie.get("y2"))) / 2, places=1)

    def test_ueber_einer_waagerechten_linie_steht_jede_zahl_gleich_weit_weg(
            self) -> None:
        # Ueber einer waagerechten Linie ist die Breite des Wortes gleich: es
        # steht mittig darueber, so weit weg wie jedes andere, ob kurz oder
        # lang.
        baum = self.zeichne("waagerecht", """
            form: halle
            abstaende:
              - art: masskette
                von: [1.5, 2.0]
                nach: [7.5, 2.0]
              - art: masskette
                von: [1.5, 5.0]
                nach: [7.5, 5.0]
                text: sechs Meter von Linie zu Linie
        """)

        ueber_der_linie = []
        for gruppe in mit_klasse(baum, "abstand"):
            linie = mit_klasse(gruppe, "masslinie")[0]
            wort = mit_klasse(gruppe, "massbeschriftung")[0]
            with self.subTest(wort=wort.text):
                self.pruefe_neben_der_linie(baum, gruppe)
                self.assertAlmostEqual(
                    float(wort.get("x")),
                    (float(linie.get("x1")) + float(linie.get("x2"))) / 2, places=1)
            ueber_der_linie.append(float(linie.get("y1")) - float(wort.get("y")))
        kurz, lang = ueber_der_linie
        self.assertGreater(kurz, 0, "die Zahl steht ueber der Linie")
        self.assertAlmostEqual(kurz, lang, places=2)

    def test_auch_neben_einer_schraegen_linie_steht_die_zahl_frei(self) -> None:
        # Zwischen waagerecht und senkrecht gibt es keine Stufe, an der ein
        # langes Wort ploetzlich wieder auf seine Linie rutscht. Die eine
        # Linie ist eher waagerecht, die andere eher senkrecht.
        baum = self.zeichne("schraeg", """
            form: halle
            abstaende:
              - art: pfeil
                von: [1.0, 2.0]
                nach: [5.0, 5.0]
                text: gut 5 m bis zum Netz
              - art: pfeil
                von: [6.0, 2.0]
                nach: [8.0, 6.0]
                versatz: -0.5
                text: gut 4 m bis zur Linie
        """)

        for gruppe in mit_klasse(baum, "abstand"):
            with self.subTest(wort=mit_klasse(gruppe, "massbeschriftung")[0].text):
                self.pruefe_neben_der_linie(baum, gruppe)

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

    def test_die_schrift_steht_im_bild_in_ihrer_rangfolge(self) -> None:
        # Der Titel vor dem Untertitel, die Ueberschrift eines Legendenblocks
        # vor seinen Zeilen, die Fusszeile zuletzt, und die Woerter im Feld
        # klein. Gemessen wird die Groesse, die ein Betrachter anwendet: eine,
        # die er verwirft, steht in seiner Grundschrift da, und dann sieht
        # alles gleich aus.
        baum = self.zeichne("rangfolge", """
            form: halle
            titel: Annahme-Zielzone
            untertitel: Aufschlag von hinten
            legende:
              - ueberschrift: Wertung
                zeilen:
                  - 3 Punkte in der Zielzone
            fusszeile: "Quelle: Volleyball-Magazin 09/2026"
            zonen:
              - text: Zielzone
                form: rechteck
                bei: [4.5, 6.0]
                groesse: [3.0, 2.0]
            geraete:
              - text: Kasten
                teile:
                  - form: rechteck
                    bei: [7.0, 12.0]
                    groesse: [1.6, 0.8]
            stellen:
              - bei: [4.5, 14.0]
                text: Feldmitte
            abstaende:
              - art: masskette
                von: [1.0, 2.0]
                nach: [1.0, 5.0]
        """)

        def groesse(klasse: str) -> float:
            return schriftgroesse(baum, mit_klasse(baum, klasse)[0])

        stufen = [groesse(klasse) for klasse in
                  ("titel", "untertitel", "legendenkopf", "legendenzeile",
                   "fusszeile")]
        self.assertEqual(stufen, sorted(set(stufen), reverse=True),
                         "jede Stufe kleiner als die davor")

        im_feld = {klasse: groesse(klasse) for klasse in
                   ("zonenname", "geraetname", "stelle", "massbeschriftung")}
        self.assertEqual(len(set(im_feld.values())), 1,
                         f"die Woerter im Feld stehen in einer Schrift: {im_feld}")
        self.assertLess(im_feld["zonenname"], groesse("titel"))

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

    def test_ein_untertitel_ohne_titel_steht_oben_in_der_schrift_des_titels(self) -> None:
        # Abzubrechen hiesse, dem Trainer wegen einer Kleinigkeit das ganze
        # Bild vorzuenthalten. Eine einzelne Zeile ueber dem Feld ist ein
        # Titel, gleich unter welchem Schluessel sie in der Szene steht.
        baum = self.zeichne("ue-000001", """
            form: halle
            untertitel: ohne etwas darueber
        """)

        self.assertEqual([e.text for e in mit_klasse(baum, "titel")],
                         ["ohne etwas darueber"])
        self.assertEqual(mit_klasse(baum, "untertitel"), [],
                         "keine zweite Zeile, die kleiner gesetzt waere")
        zeile, feld = mit_klasse(baum, "titel")[0], mit_klasse(baum, "feld")[0]
        self.assertLess(float(zeile.get("y")), float(feld.get("y")),
                        "die Zeile steht ueber dem Feld")
        self.assertEqual(baum.find(SVG + "title").text, "ohne etwas darueber",
                         "und ist damit auch der Name des Bildes")

        # Dieselbe Zeile als `titel:` geschrieben schiebt das Feld genauso weit
        # nach unten. Gemessen ist damit die Schrift und nicht nur die Klasse:
        # eine kleiner gesetzte Zeile braeuchte weniger Platz.
        als_titel = self.zeichne("mit-titel", """
            form: halle
            titel: ohne etwas darueber
        """)
        self.assertAlmostEqual(float(feld.get("y")),
                               float(mit_klasse(als_titel, "feld")[0].get("y")),
                               2, "der Kopf ist so hoch wie mit einem echten Titel")

    def test_ohne_titel_wird_der_titel_der_uebungskarte_vorgeschlagen(self) -> None:
        # Der Basisname der Szene ist die Uebungs-ID, und auf der Karte steht
        # der Titel schon. Der Trainer uebernimmt ihn mit einer Zeile oder
        # laesst es.
        fertig = self.laufe("ue-000001", """
            form: halle
            untertitel: ohne etwas darueber
        """)

        self.assertIn("titel:", fertig.stdout,
                      "das Skript meldet, was es getan hat")
        self.assertIn("Annahme im Halbfeld", fertig.stdout,
                      "und nennt den Titel der Karte ue-000001 als Vorschlag")

    def test_ein_zweites_bild_mit_nummer_bekommt_denselben_vorschlag(self) -> None:
        # Kommt zu einer Karte mit Szene ein Bild dazu, heisst es nach der ID
        # mit Nummer dahinter (#39). Gemeint ist dieselbe Karte.
        fertig = self.laufe("ue-000001-2", """
            form: halle
            untertitel: ohne etwas darueber
        """)

        self.assertIn("Annahme im Halbfeld", fertig.stdout)

    def test_ohne_passende_uebungskarte_steht_der_hinweis_ohne_wortlaut(self) -> None:
        # Drei Wege, auf denen kein Vorschlag zustande kommt. Geraten wird auf
        # keinem davon, und das Bild entsteht auf allen dreien.
        (self.ordner.pfad / "uebungen" / "ue-000009-ohne-titel.md").write_text(
            "---\nid: ue-000009\n---\n", encoding="utf-8")

        for name, warum in (("aufstellung", "keine Uebungs-ID"),
                            ("ue-009999", "eine ID ohne Karte"),
                            ("ue-000009", "eine Karte ohne Titel")):
            with self.subTest(warum=warum):
                fertig = self.laufe(name, """
                    form: halle
                    untertitel: ohne etwas darueber
                """)

                self.assertTrue(self.bild(name).exists(),
                                "geschrieben wird trotzdem")
                self.assertIn("titel:", fertig.stdout, "der Hinweis steht da")
                self.assertNotIn("Uebungskarte", fertig.stdout,
                                 "nur ohne Wortlaut")

    def test_die_szene_bleibt_stehen_wie_sie_geschrieben_ist(self) -> None:
        # Wer die Szene liest, soll nicht suchen muessen, welche Zeile das
        # Skript wohin geschoben hat.
        datei = self.ordner.lege_szene_an("ue-000001", """
            form: halle
            untertitel: ohne etwas darueber
        """)
        vorher = datei.read_text(encoding="utf-8")

        self.ordner.starte("schaubild.py", "ue-000001")

        self.assertEqual(datei.read_text(encoding="utf-8"), vorher)
        self.assertIn("untertitel: ohne etwas darueber", vorher)

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

    def gasse(self, baum, kante: float) -> float:
        """Wie weit rechts von dieser Kante die Legendenspalte anfaengt, in Metern.

        `kante` ist eine x-Koordinate im Bild. Gemessen wird bis zur linken
        Kante der Spalte, an der jede ihrer Zeilen anfaengt.
        """
        spalte = min(float(e.get("x")) for e in mit_klasse(baum, "legendenkopf")
                     + mit_klasse(baum, "legendenzeile"))
        return Feldmass(baum, HALLE).strecke(spalte - kante)

    def gasse_neben_dem_feld(self) -> float:
        """Die Gasse vor der Legendenspalte, wenn rechts nichts als das Feld steht."""
        baum = self.zeichne("gasse-feld", "form: halle" + ZUSPIELZIEL)
        feld = mit_klasse(baum, "feld")[0]
        return self.gasse(baum, float(feld.get("x")) + float(feld.get("width")))

    def pruefe_gasse_vor_dem_wort(self, baum, klasse: str, soll: float) -> None:
        """Vor dem Wort dieser Klasse bleibt die Gasse `soll`, in Metern.

        Gemessen wird am knappen Wortkasten. Das Wort im Bild ist breiter,
        die Gasse davor also schmaler: ist sie hier schon zu schmal, ist sie
        es im Bild erst recht. Breiter als ein halbes Wort darueber wird sie
        aber auch nicht, sonst stuende die Spalte vor einem Wort weiter weg
        als vor dem Feld.
        """
        wort = mit_klasse(baum, klasse)[0]
        halb, _ = wortkasten(baum, wort)
        gasse = self.gasse(baum, float(wort.get("x")) + halb)
        self.assertGreaterEqual(gasse, soll, f"zu schmal vor {wort.text!r}")
        self.assertLess(gasse, soll + Feldmass(baum, HALLE).strecke(halb),
                        f"zu breit vor {wort.text!r}")

    def test_vor_dem_wort_einer_stelle_bleibt_dieselbe_gasse_wie_vor_einem_marker(
            self) -> None:
        # Im Referenzbild steht "3-m-Linie" rechts neben dem Feld, und die
        # Spalte rueckte bis an das Wort heran. Es las sich wie der Anfang der
        # Legendenzeile daneben. Die Gasse vor der Spalte ist immer dieselbe,
        # gleich was am weitesten rechts steht: das Feld, ein Marker, ein Wort.
        neben_dem_feld = self.gasse_neben_dem_feld()
        marker = self.zeichne("gasse-marker", "form: halle" + ZUSPIELZIEL + """
spieler:
  - bei: [10.0, 6.0]
    text: Z
""")
        stelle = self.zeichne("gasse-stelle", "form: halle" + ZUSPIELZIEL + """
stellen:
  - bei: [10.4, 6.0]
    text: 3-m-Linie
""")

        kreis = mit_klasse(marker, "marker")[0]
        vor_dem_marker = self.gasse(marker,
                                    float(kreis.get("cx")) + float(kreis.get("r")))
        self.assertAlmostEqual(vor_dem_marker, neben_dem_feld, places=2)
        self.pruefe_gasse_vor_dem_wort(stelle, "stelle", neben_dem_feld)

    def test_vor_dem_namen_einer_zone_oder_eines_geraets_bleibt_die_gasse(self) -> None:
        # Dasselbe Wort, nur an etwas anderem: eine Zone traegt ihren Namen in
        # sich, ein Geraet unter sich. Ragt er rechts am weitesten hinaus,
        # haelt die Spalte vor ihm dieselbe Gasse.
        neben_dem_feld = self.gasse_neben_dem_feld()
        for klasse, aufbau in (
            ("zonenname", """
zonen:
  - text: Ablage
    form: rechteck
    bei: [10.0, 4.0]
    groesse: [1.2, 2.0]
"""),
            ("geraetname", """
geraete:
  - text: Ballwagen
    teile:
      - form: rechteck
        bei: [10.0, 6.0]
        groesse: [0.8, 0.5]
"""),
        ):
            with self.subTest(wort=klasse):
                baum = self.zeichne(f"gasse-{klasse}",
                                    "form: halle" + ZUSPIELZIEL + aufbau)

                self.pruefe_gasse_vor_dem_wort(baum, klasse, neben_dem_feld)

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

    def test_eine_liste_unter_fusszeile_ergibt_eine_zeile_je_eintrag(self) -> None:
        # Ein Schaubild aus einer Magazinquelle traegt darunter zwei Zeilen:
        # was die Zeichen bedeuten und woher die Uebung kommt.
        baum = self.zeichne("fuss-liste", """
            form: halle
            titel: Einarmige Abwehr
            fusszeile:
              - "Zeichen: Kreis Spieler, gestrichelt Ballweg"
              - "Quelle: Volleyball-Magazin 09/2026, Seite 28"
        """)

        zeilen = mit_klasse(baum, "fusszeile")
        self.assertEqual([e.text for e in zeilen],
                         ["Zeichen: Kreis Spieler, gestrichelt Ballweg",
                          "Quelle: Volleyball-Magazin 09/2026, Seite 28"])
        feld = mit_klasse(baum, "feld")[0]
        unterkante = float(feld.get("y")) + float(feld.get("height"))
        oben, unten = (float(e.get("y")) for e in zeilen)
        self.assertGreater(oben, unterkante, "beide stehen unter dem Bild")
        self.assertGreater(unten, oben, "in der Reihenfolge der Szene untereinander")
        for e in zeilen + mit_klasse(baum, "titel"):
            with self.subTest(zeile=e.text):
                self.assertAlmostEqual(float(e.get("x")), float(feld.get("x")),
                                       places=2)

    def test_jede_zeile_der_fusszeile_laesst_das_blatt_mitwachsen(self) -> None:
        # Abgeschnitten wird nichts, auch nicht die zweite Zeile. Dass die
        # Quelle fehlt, saehe man dem Bild nicht an.
        def mit(name: str, *zeilen: str) -> ET.Element:
            return self.zeichne(name, "form: halle\nfusszeile:\n" + "".join(
                f'  - "{zeile}"\n' for zeile in zeilen))

        eine = mit("fuss-eine", "Quelle: Magazin")
        zwei = mit("fuss-zwei", "Zeichen: Kreis Spieler", "Quelle: Magazin")
        # Eine einzelne Zeile ist eine Liste mit einem Eintrag, und so
        # geschrieben ergibt sie dasselbe Blatt wie ohne Strich.
        ohne_strich = self.zeichne("fuss-ohne-strich",
                                   'form: halle\nfusszeile: "Quelle: Magazin"')
        self.assertEqual(zahlen(ohne_strich.get("viewBox")), zahlen(eine.get("viewBox")))
        self.assertEqual([e.text for e in mit_klasse(ohne_strich, "fusszeile")],
                         ["Quelle: Magazin"])
        lang = mit("fuss-lang", "Zeichen: Kreis Spieler",
                   "Quelle: Volleyball-Magazin 09/2026, Praxiseinheit "
                   "Grundfertigkeiten der einarmigen Abwehr, Seite 28 und 29")

        _, _, breite_zwei, hoehe_zwei = zahlen(zwei.get("viewBox"))
        _, _, breite_lang, _ = zahlen(lang.get("viewBox"))
        self.assertGreater(hoehe_zwei, zahlen(eine.get("viewBox"))[3],
                           "die zweite Zeile braucht mehr Blatt nach unten")
        self.assertLess(max(float(e.get("y")) for e in mit_klasse(zwei, "fusszeile")),
                        hoehe_zwei, "die letzte Zeile steht noch im Bild")
        self.assertGreater(breite_lang, breite_zwei,
                           "eine lange zweite Zeile macht das Blatt breiter")
        # Gewachsen ist das Blatt, das Feld darauf bleibt, wie es war.
        self.assertAlmostEqual(Feldmass(zwei, HALLE).breite,
                               Feldmass(lang, HALLE).breite, places=2)

    def test_leere_eintraege_der_fusszeile_fallen_weg(self) -> None:
        # So wie in einem Legendenblock. Eine leere Zeile unter dem Bild ist
        # nur ein Loch, das nach vergessenem Text aussieht.
        mit_leeren = self.zeichne("fuss-leer", """
            form: halle
            fusszeile:
              - "Zeichen: Kreis Spieler"
              -
              - ""
              - "Quelle: Magazin"
        """)
        ohne = self.zeichne("fuss-ohne-leere", """
            form: halle
            fusszeile:
              - "Zeichen: Kreis Spieler"
              - "Quelle: Magazin"
        """)

        self.assertEqual([e.text for e in mit_klasse(mit_leeren, "fusszeile")],
                         ["Zeichen: Kreis Spieler", "Quelle: Magazin"])
        self.assertEqual(zahlen(mit_leeren.get("viewBox")),
                         zahlen(ohne.get("viewBox")),
                         "und nehmen auch keinen Platz weg")

    def test_eine_abbildung_oder_verschachtelte_liste_in_der_fusszeile_bricht_ab(
            self) -> None:
        # Sonst stuende ihre Python-Schreibweise im Bild, und das sieht man
        # erst dort. Am haeufigsten ist die Abbildung als Eintrag: eine
        # Quellenangabe mit Doppelpunkt, aber ohne Anfuehrungszeichen.
        for name, fuss, gesucht in (
            ("fuss-abbildung", "fusszeile:\n  quelle: Magazin",
             ["fusszeile", "Liste", "Anfuehrungszeichen"]),
            ("fuss-eintrag",
             'fusszeile:\n  - "Zeichen: Kreis Spieler"\n'
             "  - Quelle: Volleyball-Magazin 09/2026",
             ["fusszeile, Zeile 2", "Anfuehrungszeichen"]),
            ("fuss-verschachtelt",
             'fusszeile:\n  - "Quelle: Magazin"\n  - [Zeichen, Quelle]',
             ["fusszeile, Zeile 2"]),
        ):
            with self.subTest(fall=name):
                fertig = self.scheitert(name, "form: halle\n" + fuss)

                for wort in gesucht:
                    self.assertIn(wort, fertig.stdout)
                self.assertFalse(self.bild(name).exists())

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

        schemata = farbschemata(baum)
        hell, dunkel = schemata["hell"], schemata["dunkel"]
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
    hervorgehoben: true
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
  - art: ballweg
    von: {wo}
    nach: [4.5, 1.0]
stellen:
  - bei: [4.5, 1.0]
    text: Mitte & Ziel
""")
                self.assertTrue(baum.tag.endswith("svg"))
                self.assertEqual(len(mit_klasse(baum, "marker")), 2)
                self.assertEqual(
                    [text for text, (kreis, _) in marker_nach_beschriftung(baum).items()
                     if farbvariable(baum, kreis, "fill") == "strich"], ["Z & A"])
                self.assertEqual(len(mit_klasse(baum, "weg")), 3)
                self.assertEqual([e.text for e in mit_klasse(baum, "stelle")],
                                 ["Mitte & Ziel"])
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


# Was schaubild.py sagt, wenn es keinen Browser findet, der die Ansicht
# aufnimmt. Danach zu fragen ist billiger, als die Suche hier nachzubauen.
KEIN_BROWSER = "weder Edge noch Chrome"


class AnsichtAlsPngTest(unittest.TestCase):
    """`--png` legt zusaetzlich zum SVG eine Ansicht als PNG an, fuer die Vorschau.

    Das Lesewerkzeug des Agenten zeigt bei einem SVG nur das Markup, beurteilt
    wird das Bild aber im Dialog. Die Ansicht nimmt Edge oder Chrome auf. Wo
    keiner von beiden da ist, wird uebersprungen, was eine Ansicht braucht.

    Gezeichnet wird hier die freigegebene Szene unter schaubilder/. Dort hat
    bei der Abnahme von 1c eine PNG neben dem SVG eine andere Datei
    ueberschrieben.
    """

    SZENE = """
        form: halle
        spieler:
          - bei: 3
    """

    def setUp(self) -> None:
        self.ordner = Arbeitsordner()
        self.addCleanup(self.ordner.raeume_auf)
        self.ordner.lege_szene_an("ue-000042", self.SZENE)

    def ansicht(self, fertig: subprocess.CompletedProcess) -> Path:
        """Der Pfad, den das Skript fuer die Ansicht nennt.

        Uebersprungen wird nur, wenn das Skript sagt, dass es keinen Browser
        gefunden hat. Scheitert ein Browser, der da ist, faellt der Test.
        """
        if KEIN_BROWSER in fertig.stdout:
            self.skipTest("auf diesem Rechner gibt es weder Edge noch Chrome")
        treffer = re.search(r"^Ansicht als PNG: (.+)$", fertig.stdout, re.MULTILINE)
        self.assertIsNotNone(treffer, fertig.stdout + fertig.stderr)
        pfad = Path(treffer.group(1).strip())
        self.addCleanup(pfad.unlink, missing_ok=True)
        return pfad

    def test_die_ansicht_liegt_im_temp_verzeichnis_und_nie_im_arbeitsordner(self) -> None:
        fertig = self.ordner.starte("schaubild.py", "ue-000042", "--png")

        self.assertEqual(fertig.returncode, 0, fertig.stdout + fertig.stderr)
        png = self.ansicht(fertig)
        self.assertTrue(png.is_file(), fertig.stdout)
        self.assertTrue(png.is_relative_to(Path(tempfile.gettempdir()).resolve()), png)
        self.assertEqual(list(self.ordner.pfad.rglob("*.png")), [],
                         "im Arbeitsordner entsteht keine PNG")
        self.assertTrue((self.ordner.pfad / "schaubilder" / "ue-000042.svg").is_file())

    def test_die_ansicht_zeigt_das_ganze_bild(self) -> None:
        # Das SVG nennt seine Groesse selbst. Die Ansicht hat genau diese
        # Groesse, auf ganze Pixel aufgerundet: nichts ist abgeschnitten, und
        # es steht kein leerer Rand daneben.
        fertig = self.ordner.starte("schaubild.py", "ue-000042", "--png")

        png = self.ansicht(fertig)
        daten = png.read_bytes()
        self.assertEqual(daten[:8], b"\x89PNG\r\n\x1a\n", "die Ansicht ist eine PNG")
        breite, hoehe = struct.unpack(">II", daten[16:24])
        svg = ET.parse(self.ordner.pfad / "schaubilder" / "ue-000042.svg").getroot()
        self.assertEqual((breite, hoehe), (math.ceil(float(svg.get("width"))),
                                           math.ceil(float(svg.get("height")))))

    def test_ohne_browser_entsteht_das_svg_und_die_meldung_sagt_dass_die_ansicht_fehlt(
            self) -> None:
        # Ausgeblendet wird der Browser ueber die Umgebung: ein leerer PATH und
        # leere Ordner dort, wo unter Windows Edge und Chrome installiert sind.
        # Unter macOS stehen sie an festen Pfaden, die sich so nicht
        # ausblenden lassen. Dort entsteht die Ansicht eben, und der Test
        # wird uebersprungen.
        leer = Path(tempfile.mkdtemp(prefix="ohne-browser-"))
        self.addCleanup(shutil.rmtree, leer, ignore_errors=True)
        ohne_browser = {name: str(leer) for name in
                        ("PATH", "ProgramFiles", "ProgramFiles(x86)", "LOCALAPPDATA")}

        fertig = self.ordner.starte("schaubild.py", "ue-000042", "--png",
                                    umgebung=ohne_browser)

        if re.search(r"^Ansicht als PNG: ", fertig.stdout, re.MULTILINE):
            self.skipTest("der Browser laesst sich auf diesem Rechner nicht ausblenden")
        self.assertEqual(fertig.returncode, 0, fertig.stdout + fertig.stderr)
        self.assertTrue((self.ordner.pfad / "schaubilder" / "ue-000042.svg").is_file())
        self.assertRegex(fertig.stdout, r"(?m)^.*Ansicht.*fehlt.*$")
        self.assertIn(KEIN_BROWSER, fertig.stdout)


if __name__ == "__main__":
    unittest.main()
