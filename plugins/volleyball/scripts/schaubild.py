#!/usr/bin/env python3
"""Zeichnet aus einer Szene ein Schaubild als SVG.

    <python> schaubild.py ue-000042                       # schaubilder/ue-000042.szene.yml
    <python> schaubild.py schaubilder/ue-000042.szene.yml
    <python> schaubild.py ue-000042 --wurzel <pfad>
    <python> schaubild.py ue-000042 --png                 # dazu eine Ansicht als PNG

Die Szene ist die Quelle, das SVG ist das Erzeugnis (ADR-0004). Beide liegen
unter demselben Basisnamen in `schaubilder/`, damit eine Korrektur ein halbes
Jahr spaeter drei Zeilen kostet statt einer Neuzeichnung. Wer in das SVG
tippt, verliert es beim naechsten Erzeugen, genau wie bei der Leseansicht.

Gerechnet wird in der Szene durchgehend in Metern. Die Umrechnung in
Zeichenkoordinaten passiert allein hier und nirgends sonst: nur so stimmt ein
eingezeichneter Abstand mit dem ueberein, was in der Halle abgeschritten wird.

Geschrieben wird erst, wenn das ganze Bild steht. Eine Szene, die nicht
aufgeht, hinterlaesst deshalb kein halbes SVG, sondern eine Meldung und die
Datei von vorher.

`--png` nimmt das fertige SVG zusaetzlich mit Edge oder Chrome als PNG auf,
fuer eine Vorschau, die ein SVG nicht als Bild zeigt. Die Ansicht als PNG
liegt im Temp-Verzeichnis und nie im Arbeitsordner.

Nur Standardbibliothek. Allein `--png` braucht dazu Edge oder Chrome. Fehlt
der Browser, entsteht das SVG trotzdem, und die Meldung sagt, dass die Ansicht
als PNG fehlt.
"""

from __future__ import annotations

import argparse
import html
import math
import re
import sys
import tempfile
import xml.etree.ElementTree as ET
from dataclasses import dataclass, replace
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from browser import Browser, BrowserFehler, finde_browser  # noqa: E402
from szene import (NAMENSABSTAND, Feldvorlage, Flaeche,  # noqa: E402
                   Geraet, Legendenblock, Ort, Spieler, Szene, SzeneFehler,
                   Weg, lies_szene, normale, scheitel)
from tpdaten import (ID_MUSTER, finde_wurzel,  # noqa: E402
                     konsole_vorbereiten, lies_frontmatter, suche_wurzel)

# Zeicheneinheiten je Meter. Die Zahl steht genau einmal im Plugin; alles
# andere rechnet in Metern und geht durch Blatt.
MASSSTAB = 30.0

# Mindestrand um das Feld, in Metern. Darin steht, was neben dem Feld liegt:
# Netzpfosten, Beschriftungen, spaeter Titel und Legende.
RAND = 1.5

# Luft um einen Punkt ausserhalb des Feldes. Ein Aufschlagspieler hinter der
# Grundlinie soll ganz im Bild stehen, nicht halb angeschnitten.
LUFT = 0.8

# Die Gasse vor der Legendenspalte, in Metern. So breit wie der Rand um das
# Feld: neben einem Marker, einem Wort oder einem Geraet ausserhalb des
# Feldes steht die Spalte so weit ab wie neben dem Feld selbst. Mit weniger
# Luft liest sich ein Wort davor wie der Anfang der Legendenzeile daneben.
GASSE = RAND

# Radius eines Spielermarkers in Metern. Knapp ein Meter Durchmesser: so gross
# wie ein Mensch von oben Platz braucht, und damit massstaeblich statt geraten.
MARKER = 0.45

# Wie weit der Rahmen um einen Spieler auf einem Geraet ueber dessen Marker
# hinausreicht, in Metern. Genug, dass um einen gefuellten Marker ein Rand in
# Geraetefarbe stehen bleibt; wenig genug, dass der Rahmen nicht nach einem
# zweiten Gegenstand neben dem Spieler aussieht.
UEBERSTAND = 0.2

# Die Luft zwischen dem Ende eines Weges und dem Marker oder Wort, an dem er
# aufhoert, in Metern. Genug, dass die Pfeilspitze frei steht.
WEGABSTAND = 0.15

# Die Strichbreite eines Weges, in Zeicheneinheiten.
WEGSTRICH = 2.6

# Wie gross eine Pfeilspitze ist, als Vielfaches der Strichbreite ihres
# Pfades. So misst SVG eine Markierung am Ende eines Pfades: ein breiterer
# Strich bekommt eine groessere Spitze.
SPITZE = 4.5

# Wie weit die Spitze eines Weges von seinem Ende zurueckreicht, in Metern.
# Gerechnet wird die ganze Markierung, auch das Zehntel, das ueber das Ende
# hinausragt: eher ein Finger zu lang als eine Spitze im Wort.
SPITZENLAENGE = SPITZE * WEGSTRICH / MASSSTAB

# Laenge eines Massstrichs quer zur Masslinie, in Metern. Ein Strich, kein
# Balken: er markiert das Ende einer Masskette, ohne mit dem Aufbau um
# Aufmerksamkeit zu streiten.
MASSSTRICH = 0.5

# Schriftgroesse der kleinen Beschriftungen an Geraeten und Abstaenden, in
# Zeicheneinheiten. Sie steht einmal da und geht von hier sowohl ins Stylesheet
# als auch in die Rechnung, wie viel Platz ein Wort neben dem Aufbau braucht.
KLEINSCHRIFT = 13

# Wie breit ein Zeichen im Verhaeltnis zu seiner Hoehe ungefaehr ist. Geschaetzt
# und eher zu breit: ein angeschnittenes Wort ist schlimmer als ein Finger Luft
# zu viel.
ZEICHENBREITE = 0.6

# Der Hof um ein Wort im Feld, als Strichbreite in Zeicheneinheiten. Er liegt
# hinter den Buchstaben, in der Farbe dessen, worauf das Wort steht, und
# unterbricht so eine Linie oder einen Weg darunter, statt sie zwischen den
# Buchstaben durchscheinen zu lassen.
HOF = 3

# Die Farben, die unter dem Wort einer Stelle zu sehen sein koennen, siehe
# grund().
GRUENDE = ("feld", "papier", "zone")

# Die Schriftgroessen des Textwerks, in Zeicheneinheiten. Sie stehen
# beieinander, weil ihr Verhaeltnis die Rangfolge macht: der Titel vor dem
# Untertitel, die Ueberschrift eines Legendenblocks vor seinen Zeilen, die
# Fusszeile zuletzt. Wer eine davon anfasst, sieht hier, wogegen.
SCHRIFT = {
    "titel": 22,
    "untertitel": 15,
    "legendenkopf": 14,
    "legendenzeile": KLEINSCHRIFT,
    "fusszeile": 12,
}

# Die Hoehe einer Textzeile als Vielfaches ihrer Schriftgroesse.
ZEILENABSTAND = 1.5

# Die Luft zwischen zwei Legendenbloecken, in Zeicheneinheiten. Eine halbe
# Zeile: genug, dass die Bloecke auseinanderfallen, wenig genug, dass sie eine
# Spalte bleiben.
BLOCKABSTAND = KLEINSCHRIFT * ZEILENABSTAND / 2

# Der Rand des Blattes um das Textwerk, in Zeicheneinheiten. Derselbe wie der
# Rand um das Feld, damit Titel, Legende und Fusszeile auf denselben Kanten
# sitzen wie das Bild und nicht auf zweiten daneben.
SEITENRAND = RAND * MASSSTAB

# Die Farben. Zwei Saetze derselben Namen, einer je Schema, damit das Bild in
# einer hellen wie in einer dunklen Leseansicht lesbar bleibt. Die Werte sind
# die aus leseansicht.py, damit Schaubild und Blatt nicht zwei Handschriften
# haben.
HELL = {
    "papier": "#fbfaf8",
    "feld": "#ffffff",
    "strich": "#1c1a17",
    "gedaempft": "#6b6560",
    "laufweg": "#8a5a2b",
    "ballweg": "#2b5a8a",
    "geraet": "#efebe4",
    # Die Zone liegt naeher am Boden als das Geraet. Ueber ihr stehen Marker
    # und laufen Wege, und eine Flaeche, die kraeftig genug ist, um
    # aufzufallen, ist auch kraeftig genug, um das zu verdecken, worum es geht.
    "zone": "#f6f3ed",
}
DUNKEL = {
    "papier": "#171614",
    "feld": "#201e1b",
    "strich": "#ece8e2",
    "gedaempft": "#9a938c",
    "laufweg": "#d6a36b",
    "ballweg": "#7fb0dd",
    "geraet": "#2e2a25",
    "zone": "#272421",
}


# --------------------------------------------------------------------------
# Vom Meter zur Zeicheneinheit
# --------------------------------------------------------------------------

class Blatt:
    """Rechnet Meter in Zeichenkoordinaten um.

    Die Szene sieht das Feld von oben: x waechst nach rechts, y zur Gegenseite
    hin. Im SVG waechst y nach unten, deshalb wird es hier gespiegelt. Wer
    diesen Umstand vergisst, zeichnet ein Bild, in dem die Aufschlagposition
    vorn am Netz steht.

    `kopf` ist die Hoehe des Textwerks ueber dem Bild. Das Bild rueckt darum
    nach unten, ohne dass sich an seinem Massstab etwas aendert: ein Titel
    verschiebt das Feld, er verzerrt es nicht.
    """

    def __init__(self, links: float, unten: float, rechts: float, oben: float,
                 kopf: float = 0.0) -> None:
        self._links, self._oben, self._kopf = links, oben, kopf
        self.breite = (rechts - links) * MASSSTAB
        self.hoehe = (oben - unten) * MASSSTAB

    def x(self, meter: float) -> float:
        return (meter - self._links) * MASSSTAB

    def y(self, meter: float) -> float:
        return self._kopf + (self._oben - meter) * MASSSTAB

    def laenge(self, meter: float) -> float:
        return meter * MASSSTAB


def grenzen(s: Szene) -> tuple[float, float, float, float]:
    """Der Ausschnitt in Metern: die Grundform mit Rand, erweitert um alles Weitere."""
    xs = [-RAND, s.grundform.breite + RAND]
    ys = [-RAND, s.grundform.laenge + RAND]
    for x, y in s.punkte():
        xs += [x - LUFT, x + LUFT]
        ys += [y - LUFT, y + LUFT]
    # Eine Beschriftung braucht Platz nach ihrer Laenge und nicht nach LUFT.
    for text, bei in s.beschriftungen(wortbreite):
        links, unten, rechts, oben = wortflaeche(text, bei).rahmen
        xs += [links, rechts]
        ys += [unten, oben]
    return min(xs), min(ys), max(xs), max(ys)


def rechte_kante(s: Szene) -> float:
    """Wie weit das Gezeichnete nach rechts reicht, in Metern.

    Die Kante selbst, ohne die Luft, die grenzen() um einen Punkt legt: ein
    Marker reicht um seinen Radius ueber seinen Ort hinaus, ein Wort um seine
    halbe Breite. Davor haelt die Legendenspalte ihre Gasse.
    """
    kanten = [s.grundform.breite]
    kanten += [x for x, _ in s.punkte()]
    kanten += [spieler.x + MARKER for spieler in s.spieler]
    kanten += [bei[0] + wortbreite(text) / 2
               for text, bei in s.beschriftungen(wortbreite)]
    return max(kanten)


def wortbreite(text: str) -> float:
    """Wie breit eine Beschriftung im Feld ungefaehr wird, in Metern."""
    return textbreite(text, KLEINSCHRIFT) / MASSSTAB


def wortflaeche(text: str, bei: Ort) -> Flaeche:
    """Der Platz, den eine Beschriftung im Feld um ihren Ort einnimmt, in Metern.

    Geschaetzt, siehe textbreite(). Dieselbe Rechnung laesst das Blatt um ein
    Wort wachsen, einen Weg vor dem Wort einer Stelle und vor dem Namen eines
    Geraets aufhoeren, rueckt die Zahl eines Abstands neben ihre Linie und
    sagt, ob das Wort einer Zone in die Zone passt. Zwei Schaetzungen liefen
    auseinander, und dann stuende ein Wort im Bild, das der Weg fuer kleiner
    haelt.
    """
    return Flaeche("rechteck", bei, wortbreite(text), KLEINSCHRIFT / MASSSTAB)


def textbreite(text: str, groesse: float) -> float:
    """Wie breit ein Text in dieser Schriftgroesse ungefaehr wird.

    Geschaetzt aus der Zeichenzahl. Genau messen koennte nur, wer die
    Schriftdatei kennt, und die steht erst im Betrachter fest. Geschaetzt wird
    deshalb eher zu breit: ein Finger Luft zu viel ist besser als ein
    abgeschnittenes Wort.
    """
    return len(text) * groesse * ZEICHENBREITE


def zeilenhoehe(sorte: str) -> float:
    """Wie viel Blatt eine Zeile dieser Sorte in der Hoehe braucht."""
    return SCHRIFT[sorte] * ZEILENABSTAND


def koord(wert: float) -> str:
    """Eine Zeichenkoordinate so kurz wie moeglich, ohne Genauigkeit zu verlieren."""
    text = f"{wert:.2f}".rstrip("0").rstrip(".")
    return "0" if text in ("", "-0") else text


# Eine gesetzte Zeile des Textwerks: ihre Sorte, ihr Text, ihre Oberkante in
# Zeicheneinheiten. Wo sie steht, entscheidet der Satzspiegel; was in ihr
# steht, die Szene.
Zeile = tuple[str, str, float]


def zeilensatz(eintraege: list[tuple[str, str]],
               oben: float) -> tuple[list[Zeile], float]:
    """Setzt Zeilen untereinander ab `oben` und gibt sie samt Unterkante zurueck.

    Jede Zeile des Textwerks geht hier durch, und zwar einmal: gesetzt wird
    beim Bemessen des Blattes, gelesen wird danach beim Zeichnen. Zwei
    getrennte Rechnungen liefen frueher oder spaeter auseinander, und dann
    stuende eine Zeile halb ausserhalb des Bildes oder das Feld im Titel.
    """
    satz: list[Zeile] = []
    y = oben
    for sorte, text in eintraege:
        satz.append((sorte, text, y))
        y += zeilenhoehe(sorte)
    return satz, y


def legendensatz(bloecke: list[Legendenblock],
                 oben: float) -> tuple[list[list[Zeile]], float]:
    """Setzt die Legendenspalte und gibt sie samt ihrer Unterkante zurueck."""
    satz: list[list[Zeile]] = []
    y = oben
    for block in bloecke:
        if satz:
            y += BLOCKABSTAND
        zeilen, y = zeilensatz(
            [("legendenkopf", block.ueberschrift)]
            + [("legendenzeile", text) for text in block.zeilen], y)
        satz.append(zeilen)
    return satz, y


def zeichenerklaerung(s: Szene) -> str:
    """Die Zeile, die sagt, wie man die Wege und Abstaende im Bild liest.

    Genannt wird genau, was in der Szene vorkommt. Bei der Abnahme von 1c
    (#28) entstand die Zeile zweimal von Hand, und beim zweiten Bild musste
    man daran denken, den Laufweg wegzulassen. Der Wortlaut ist der von
    damals: "Durchgezogen ist ein Laufweg, gestrichelt ein Ballweg."

    Massketten und Pfeile sind beide ein Abstand und teilen sich deshalb einen
    Satzteil. Ohne Wege und Abstaende gibt es nichts zu erklaeren, und es kommt
    eine leere Zeichenkette zurueck.
    """
    wegarten = {weg.art for weg in s.wege}
    satzteile = [(merkmal, bedeutung) for art, merkmal, bedeutung in (
        ("laufweg", "durchgezogen", "ein Laufweg"),
        ("ballweg", "gestrichelt", "ein Ballweg"),
    ) if art in wegarten]
    abstandsarten = {abstand.art for abstand in s.abstaende}
    enden = [ende for art, ende in (("masskette", "Maßstrichen"),
                                    ("pfeil", "zwei Spitzen"))
             if art in abstandsarten]
    if enden:
        satzteile.append(("mit " + " oder ".join(enden), "ein Abstand"))
    if not satzteile:
        return ""
    (merkmal, bedeutung), *weitere = satzteile
    satz = f"{merkmal} ist {bedeutung}" + "".join(f", {m} {b}" for m, b in weitere)
    return satz[0].upper() + satz[1:] + "."


# Woran eine geschriebene Zeichenerklaerung in der Fusszeile zu erkennen ist:
# an " = " wie in "Gestrichelter Pfeil = Ballweg", oder daran, dass sie einen
# Laufweg, Ballweg oder Abstand nennt, auch in der Mehrzahl. Die Zeile, die
# zeichenerklaerung() setzt, nennt immer eines davon. Wer sie aus dem Bild in
# die Szene uebernimmt, um sie umzuformulieren, bekommt keine zweite dazu.
GESCHRIEBENE_ERKLAERUNG = re.compile(r" = |laufweg|ballweg|abst[aä]nd", re.IGNORECASE)


def fusszeile(s: Szene) -> list[str]:
    """Die Zeilen unter dem Bild, notfalls mit der Zeichenerklaerung vorneweg.

    Hat die Szene eine geschriebene Zeichenerklaerung, bleibt die Fusszeile,
    wie sie ist. Sonst setzt das Skript seine als erste Zeile, und die Quelle
    rueckt darunter. In der Szene aendert sich nichts.
    """
    zeilen = s.textwerk.fusszeile
    if any(GESCHRIEBENE_ERKLAERUNG.search(zeile) for zeile in zeilen):
        return zeilen
    erklaerung = zeichenerklaerung(s)
    return [erklaerung, *zeilen] if erklaerung else zeilen


class Satzspiegel:
    """Wo auf dem Blatt das Bild steht und wo das Textwerk daneben.

    Das Bild rechnet in Metern, das Textwerk in Zeilen. Beide treffen sich
    hier: der Satzspiegel schiebt das Bild unter den Titel, setzt die Legende
    daneben und die Fusszeile darunter und sagt am Ende, wie gross das Blatt
    dafuer sein muss.

    Gross genug ist es immer. Ein Blatt, das nach dem Feld bemessen waere,
    schnitte eine lange Legende ab, und dass die halbe Erklaerung fehlt, sieht
    man dem Bild nicht an: es wirkt fertig.

    `breite` und `hoehe` sind das ganze Blatt. Der Bildblock darin misst
    `blatt.breite` und `blatt.hoehe`; `textkante` und `spaltenkante` sind die
    beiden linken Kanten, an denen das Textwerk anfaengt.
    """

    def __init__(self, s: Szene) -> None:
        self.werk = s.textwerk
        # Ohne Titel bekommt der Untertitel dessen Platz und dessen Schrift.
        # Verschoben wird die Zeile allein hier im Satz: in der Szene steht sie
        # weiter unter `untertitel:`, so wie der Trainer sie geschrieben hat.
        kopf = [("titel", self.werk.oberste_zeile)]
        if not self.werk.untertitel_steht_oben:
            kopf.append(("untertitel", self.werk.untertitel))
        self.kopfzeilen, unterkante = zeilensatz(
            [(sorte, text) for sorte, text in kopf if text], SEITENRAND)
        self.kopf = unterkante if self.kopfzeilen else 0.0
        self.blatt = Blatt(*grenzen(s), kopf=self.kopf)

        # Titel und Fusszeile sitzen auf der linken Kante der Grundform, nicht
        # auf der des Blattes. Die waechst mit, sobald neben dem Feld jemand
        # steht, und ein Titel, der sich danach richtet, spraenge von Bild zu
        # Bild woandershin.
        self.textkante = self.blatt.x(0)

        # Die Legende faengt eine Gasse weit rechts von dem an, was am
        # weitesten rechts steht, gleich ob das Feld, ein Marker oder ein
        # Wort. Der rechte Rand des Bildblocks taugt dafuer nicht: ein Wort
        # schiebt ihn genau bis an seine geschaetzte Breite und keinen
        # Millimeter weiter, und die Spalte stiesse an das Wort. Oben steht
        # sie mit der Grundform auf einer Hoehe.
        self.spaltenkante = self.blatt.x(rechte_kante(s) + GASSE)
        self.legende, spaltenende = legendensatz(
            self.werk.legende, self.blatt.y(s.grundform.laenge))

        unten = self.kopf + self.blatt.hoehe
        if self.legende:
            unten = max(unten, spaltenende + SEITENRAND)
        self.fusszeilen, unten = zeilensatz(
            [("fusszeile", zeile) for zeile in fusszeile(s)], unten)
        self.hoehe = unten + (SEITENRAND if self.fusszeilen else 0.0)

        # Breit genug fuer alles, was rechts am weitesten hinausragt: der
        # Bildblock, die laengste Legendenzeile, der laengste Text darunter
        # oder darueber.
        kanten = [self.blatt.breite]
        kanten += [self.spaltenkante + textbreite(text, SCHRIFT[sorte]) + SEITENRAND
                   for block in self.legende for sorte, text, _ in block]
        kanten += [self.textkante + textbreite(text, SCHRIFT[sorte]) + SEITENRAND
                   for sorte, text, _ in self.kopfzeilen + self.fusszeilen]
        self.breite = max(kanten)


# --------------------------------------------------------------------------
# Die Teile des Bildes
# --------------------------------------------------------------------------

def schriftangabe(groesse: float) -> str:
    """Eine Schriftgroesse als Angabe im Stylesheet, mit Einheit.

    Ohne `px` ist die Zahl dort ungueltig. Der Betrachter verwirft sie und
    setzt den Text in seine Grundschrift, 16 Pixel: der Titel so gross wie
    die Fusszeile, und die Schaetzung der Textbreite rechnete mit einer
    anderen Groesse als der, die im Bild steht. Im Attribut `font-size` am
    Marker ist die blosse Zahl erlaubt, im Stylesheet nicht.
    """
    return f"font-size:{koord(groesse)}px"


def farbblock(auswahl: dict[str, str]) -> str:
    return "svg{" + "".join(f"--{k}:{v};" for k, v in auswahl.items()).rstrip(";") + "}"


def hof() -> str:
    """Der Hof eines Wortes im Stylesheet, ohne seine Farbe.

    Die Farbe setzt, wer den Hof traegt: das Zonenwort die der Zone, die
    Stelle die ihres Grundes.
    """
    return f"stroke-width:{koord(HOF)};stroke-linejoin:round;paint-order:stroke"


def stil() -> str:
    """Das Stylesheet des Bildes, mit beiden Farbschemata.

    Die Farben stehen als Variablen da und nicht an den Formen, damit ein
    zweites Schema nichts kostet ausser sechs Zeilen. `currentColor` waere die
    andere Moeglichkeit, taugt hier aber nicht: die Leseansicht bettet das Bild
    als `<img>` ein, und darin gibt es keine Elternfarbe, die faerben koennte.
    """
    return (
        farbblock(HELL)
        + "@media (prefers-color-scheme:dark){" + farbblock(DUNKEL) + "}"
        + ".papier{fill:var(--papier)}"
        + ".feld{fill:var(--feld);stroke:var(--strich);stroke-width:2.4}"
        # Die Leinwand bekommt keinen Rand. Sie ist ein Stueck Boden und kein
        # Feld; eine Linie im Bild, die es in der Halle nicht gibt, ist eine
        # Ansage, die niemand einhalten kann.
        + ".leinwand{fill:var(--feld)}"
        + ".linie{fill:none;stroke:var(--strich);stroke-width:1.4}"
        + ".netz{fill:none;stroke:var(--gedaempft);stroke-width:1.4;stroke-dasharray:7 5}"
        + ".marker{fill:var(--feld);stroke:var(--strich);stroke-width:1.8}"
        + ".teil{fill:var(--geraet);stroke:var(--gedaempft);stroke-width:1.6}"
        # Eine Zone ist kein Geraet: ein Geraet ist ein Gegenstand, eine Zone
        # eine Absprache. Unterschieden wird ueber die Strichart und nicht
        # allein ueber die Farbe, damit der Unterschied im Graustufendruck
        # stehen bleibt und fuer den lesbar ist, der Farben schlecht
        # auseinanderhaelt.
        + ".zonenflaeche{fill:var(--zone);stroke:var(--gedaempft);"
          "stroke-width:1.6;stroke-dasharray:8 5}"
        + "text{font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',Roboto,"
          "sans-serif;font-weight:600;text-anchor:middle;dominant-baseline:central}"
        + ".beschriftung{fill:var(--strich)}"
        # Ein hervorgehobener Spieler ist gefuellt, die anderen bleiben Umriss.
        # Das faellt auf einen Blick auf und haengt nicht an der Farbe: Strich-
        # und Feldfarbe liegen auch im Graustufendruck weit auseinander. Das
        # Kuerzel tauscht dafuer die Farbe mit der Flaeche. Beides sind Farben,
        # die es schon gibt; eine eigene braeuchte ein zweites Paar, das in
        # beiden Schemata lesbar bleiben muesste.
        + ".hervorgehoben .marker{fill:var(--strich)}"
        + ".hervorgehoben .beschriftung{fill:var(--feld)}"
        + f".geraetname{{fill:var(--gedaempft);{schriftangabe(KLEINSCHRIFT)}}}"
        # Der Name der Zone steht voll da, der des Geraetes gedaempft. Was ein
        # Kasten ist, sieht man ihm an; was auf einer Flaeche gilt, sagt allein
        # ihr Wort.
        #
        # Jeder Buchstabe bringt einen Hof in Zonenfarbe mit, hinter sich
        # gemalt. Auf der Zone faellt er nicht auf; ueber einem hervorgehobenen
        # Marker, der in Strichfarbe gefuellt ist, traegt er das Wort.
        + f".zonenname{{fill:var(--strich);{schriftangabe(KLEINSCHRIFT)};"
          f"stroke:var(--zone);{hof()}}}"
        # Eine Stelle ist nur ihr Wort, voll und so gross wie das einer Zone.
        # Auch sie bringt einen Hof mit, in der Farbe ihres Grundes, siehe
        # grund(). Ein Weg, der nur vorbeilaeuft, schiene sonst zwischen den
        # Buchstaben durch, und eine Linie des Feldes strich das Wort durch.
        # Ein Hof in einer einzigen Farbe schimmerte neben dem Feld im
        # dunklen Schema um die Buchstaben.
        + f".stelle{{fill:var(--strich);{schriftangabe(KLEINSCHRIFT)};{hof()}}}"
        + "".join(f".stelle.grund-{farbe}{{stroke:var(--{farbe})}}"
                  for farbe in GRUENDE)
        + f".weg{{fill:none;stroke-width:{koord(WEGSTRICH)};stroke-linecap:round}}"
        + ".laufweg{stroke:var(--laufweg)}"
        + ".ballweg{stroke:var(--ballweg);stroke-dasharray:9 6}"
        # Die Linie einer Abstandsangabe tritt zurueck, die Zahl nicht:
        # gelesen wird die Zahl, die Linie sagt nur, wozu sie gehoert.
        + ".masslinie{fill:none;stroke:var(--gedaempft);stroke-width:1.4}"
        + ".massstrich{stroke:var(--gedaempft);stroke-width:1.8}"
        + ".masshilfslinie{stroke:var(--gedaempft);stroke-width:1;"
          "stroke-dasharray:4 4}"
        + f".massbeschriftung{{fill:var(--strich);{schriftangabe(KLEINSCHRIFT)}}}"
        # Das Textwerk steht auf dem Papier und liest sich von links. Eine
        # Beschriftung im Feld steht um ihren Punkt herum und deshalb mittig;
        # eine Legendenzeile faengt an einer Kante an wie jeder andere Satz.
        + ".textwerk text{text-anchor:start}"
        + f".titel{{fill:var(--strich);{schriftangabe(SCHRIFT['titel'])};"
          "font-weight:700}"
        + f".untertitel{{fill:var(--gedaempft);{schriftangabe(SCHRIFT['untertitel'])};"
          "font-weight:400}"
        + f".legendenkopf{{fill:var(--strich);{schriftangabe(SCHRIFT['legendenkopf'])}}}"
        # Die Zeilen stehen leichter da als die Ueberschrift darueber. Sonst
        # stuende eine Wand aus Fettschrift neben dem Feld, und die zoege den
        # Blick von dem weg, was sie erklaeren soll.
        + f".legendenzeile{{fill:var(--strich);"
          f"{schriftangabe(SCHRIFT['legendenzeile'])};font-weight:400}}"
        + f".fusszeile{{fill:var(--gedaempft);{schriftangabe(SCHRIFT['fusszeile'])};"
          "font-weight:400}"
    )


def spitzen() -> str:
    """Je Sorte Pfeil eine Spitze.

    Eine je Sorte statt einer gemeinsamen, weil eine SVG-Markierung die
    Strichfarbe ihres Pfades nicht erbt. Eine gemeinsame Spitze haette am
    Ballweg die Farbe des Laufwegs und am Abstandspfeil ebenfalls.
    """
    teile = ["<defs>"]
    for art, farbe in (("laufweg", "laufweg"), ("ballweg", "ballweg"),
                       ("mass", "gedaempft")):
        teile.append(
            f'<marker id="spitze-{art}" viewBox="0 0 10 10" refX="9" refY="5" '
            f'markerWidth="{koord(SPITZE)}" markerHeight="{koord(SPITZE)}" '
            f'orient="auto-start-reverse">'
            f'<path d="M0 0 L10 5 L0 10 Z" fill="var(--{farbe})"/></marker>'
        )
    teile.append("</defs>")
    return "".join(teile)


def untergrund(s: Szene, blatt: Blatt) -> str:
    """Was unter dem Aufbau liegt: der Boden, die Zonenflaechen, die Linien.

    Der Boden ist ein Spielfeld oder die freie Leinwand. Die Zonen liegen
    darauf und unter den Feldlinien: eine Zielzone verdeckt damit nicht die
    Angriffslinie, an der sie in der Halle abgemessen wird. Eine Linie des
    Feldes gehoert zum Boden und nicht zum Aufbau.

    Die Beschriftungen der Zonen kommen erst ganz zuletzt dazu, siehe
    zonennamen().
    """
    if isinstance(s.grundform, Feldvorlage):
        boden, linien = feldboden(s, blatt), feldlinien(s, blatt)
    else:
        boden, linien = leinwand(s, blatt), ""
    return (f'<g class="untergrund {s.grundform.name}">'
            f'{boden}{zonenflaechen(s, blatt)}{linien}</g>')


def leinwand(s: Szene, blatt: Blatt) -> str:
    """Die freie Leinwand: die Flaeche in der angesagten Groesse, sonst nichts.

    Keine Linie am Rand und kein Netz. Dass die Flaeche trotzdem dasteht, sagt
    dem Trainer, wie viel Boden der Aufbau braucht, und dem Bild seinen
    Massstab.
    """
    g = s.grundform
    return (f'<rect class="leinwand" x="{koord(blatt.x(0))}" '
            f'y="{koord(blatt.y(g.laenge))}" '
            f'width="{koord(blatt.laenge(g.breite))}" '
            f'height="{koord(blatt.laenge(g.laenge))}"/>')


def feldboden(s: Szene, blatt: Blatt) -> str:
    """Die Flaeche der Feldvorlage, ohne die Linien darauf."""
    v = s.grundform
    return (f'<rect class="feld" x="{koord(blatt.x(0))}" '
            f'y="{koord(blatt.y(v.laenge))}" '
            f'width="{koord(blatt.laenge(v.breite))}" '
            f'height="{koord(blatt.laenge(v.laenge))}"/>')


def feldlinien(s: Szene, blatt: Blatt) -> str:
    """Mittellinie, Angriffslinien und Netz der Feldvorlage.

    Getrennt von der Flaeche, weil dazwischen die Zonen liegen. Gezeichnet
    wird nur, was die Vorlage kennt: im Sand gibt es weder Angriffs- noch
    Mittellinie, und eine Linie im Bild, die es draussen nicht gibt, ist eine
    Ansage, die niemand einhalten kann.
    """
    v = s.grundform
    teile = []

    def quer(klasse: str, bei: float) -> str:
        return (f'<line class="{klasse}" x1="{koord(blatt.x(0))}" y1="{koord(blatt.y(bei))}" '
                f'x2="{koord(blatt.x(v.breite))}" y2="{koord(blatt.y(bei))}"/>')

    if v.mittellinie:
        teile.append(quer("linie mittellinie", v.netz))
    for bei in v.angriffslinien_bei:
        teile.append(quer("linie angriffslinie", bei))

    # Das Netz ist ein Band um die Mittellinie herum, keine Linie darauf. So
    # bleibt in der Halle die Mittellinie darunter sichtbar, und im Sand sieht
    # man auf einen Blick, dass da keine ist.
    band = 0.3
    teile.append(
        f'<rect class="netz" x="{koord(blatt.x(0))}" y="{koord(blatt.y(v.netz + band / 2))}" '
        f'width="{koord(blatt.laenge(v.breite))}" height="{koord(blatt.laenge(band))}"/>'
    )
    return "".join(teile)


def steuerpunkt(von: Ort, nach: Ort, bogen: float) -> Ort | None:
    """Der Steuerpunkt der Kurve, oder None fuer einen geraden Weg.

    Er liegt doppelt so weit neben der Mitte der Sehne wie der Scheitel, denn
    eine quadratische Bezierkurve kommt ihrem Steuerpunkt nur halb entgegen.
    Wo der Scheitel liegt, sagt die Szene; wer den Faktor hier weglaesst,
    zeichnet einen Bogen von halber Hoehe, und dann stimmt am Bild etwas nicht,
    was niemand benennen kann.
    """
    if not bogen:
        return None
    sx, sy = scheitel(von, nach, bogen)
    return (2 * sx - (von[0] + nach[0]) / 2, 2 * sy - (von[1] + nach[1]) / 2)


# Was ein Weg an einem Ende auslaesst: der Ort, auf dem das Ende dafuer liegen
# muss, und die Flaeche, an deren Rand der Weg dann aufhoert. Meist ist der
# Ort die Mitte der Flaeche. Beim Rahmen um einen Spieler am Rand eines
# Kastens ist er es nicht.
Aussparung = tuple[Ort, Flaeche]


def aussparungen(s: Szene) -> list[Aussparung]:
    """Was ein Weg an seinem Ende auslaesst: Marker, Rahmen und die Woerter der Stellen.

    Ein Pfeil, der in der Mitte eines Spielers oder im Wort einer Stelle
    endet, verliert seine Spitze darunter, und damit das Einzige, was die
    Richtung zeigt. Beide nehmen einen Platz um ihren Ort ein, der Marker einen
    Kreis, das Wort ein Rechteck, und an dessen Rand hoert der Weg auf.

    Steht ein Spieler auf einem Geraet, hoert der Weg erst am Rahmen um ihn
    auf. Am Marker finge er mitten im Geraet an und kreuzte dessen Rand.
    Gemessen wird vom Spieler aus, der Rahmen steht nicht immer mittig um ihn.

    `s` ist die Szene, wie sie gezeichnet wird, siehe szene_mit_rahmen().
    """
    marker = [((spieler.x, spieler.y),
               Flaeche("kreis", (spieler.x, spieler.y), 2 * MARKER, 2 * MARKER))
              for spieler in s.spieler]
    rahmen = [((geraet.spieler.x, geraet.spieler.y), geraet.teile[0])
              for geraet in s.geraete if isinstance(geraet, GeraetUnterSpieler)]
    woerter = [(stelle.bei, wortflaeche(stelle.text, stelle.bei))
               for stelle in s.stellen]
    return marker + rahmen + woerter


def geraetnamen(s: Szene) -> list[Flaeche]:
    """Der Platz, den die Namen der Geraete einnehmen, siehe durch_den_namen()."""
    return [wortflaeche(geraet.text, geraet.name_bei)
            for geraet in s.geraete if geraet.text]


def durch_den_namen(ende: Ort, richtung: Ort, name: Flaeche) -> float | None:
    """Wie weit ein Weg von seinem Ende aus laeuft, bis er einen Namen verlaesst.

    In Metern, entlang `richtung`, also vom Ende in den Weg hinein. None, wenn
    das Ende nicht in den Namen reicht.

    Als Ende zaehlt nicht nur der letzte Punkt, sondern das Stueck, auf dem
    die Spitze sitzt. Im Referenzbild endet der Annahmepfeil an der Unterkante
    der Zielmatte, knapp ueber ihrem Namen: der letzte Punkt liegt ausserhalb
    des Wortes, die Spitze dahinter mitten darauf. Am Anfang eines Weges gilt
    dasselbe Stueck, so wie Marker und Stellen an beiden Enden zaehlen.

    Ein Marker und das Wort einer Stelle zaehlen dagegen nur, wenn das Ende
    auf ihrem Ort liegt: dorthin zeigt, wer sie meint. Auf den Ort eines
    Namens zeigt niemand, er steht unter seinem Geraet. Getroffen wird er von
    einem Weg, der auf das Geraet zeigt und dabei mit der Spitze hineinreicht.
    """
    ein, aus = -math.inf, math.inf
    links, unten, rechts, oben = name.rahmen
    for punkt, schritt, anfang, schluss in ((ende[0], richtung[0], links, rechts),
                                            (ende[1], richtung[1], unten, oben)):
        if not schritt:
            if not anfang <= punkt <= schluss:
                return None
            continue
        a, b = (anfang - punkt) / schritt, (schluss - punkt) / schritt
        ein, aus = max(ein, min(a, b)), min(aus, max(a, b))
    if ein > aus or aus < 0 or ein > SPITZENLAENGE:
        return None
    return aus


def _kuerzung(ende: Ort, hin: Ort, ausgespart: list[Aussparung],
              namen: list[Flaeche]) -> tuple[Ort, float]:
    """In welche Richtung und wie weit ein Ende des Weges auf `hin` zu rueckt.

    Steht an dem Ende nichts, rueckt es nicht. Stehen dort ein Marker und ein
    Wort, zaehlt das, was weiter reicht, ebenso bei Marker und Rahmen. Ein
    Marker, ein Rahmen und das Wort einer Stelle zaehlen auf ihrem Ort, der
    Name eines Geraets, sobald das Ende in ihn hineinreicht.
    """
    dx, dy = hin[0] - ende[0], hin[1] - ende[1]
    laenge = (dx * dx + dy * dy) ** 0.5
    if laenge == 0:
        return (0.0, 0.0), 0.0
    richtung = (dx / laenge, dy / laenge)
    raender = [flaeche.rand(richtung, ab=ort)
               for ort, flaeche in ausgespart if trifft(ende, ort)]
    raender += [weit for name in namen
                if (weit := durch_den_namen(ende, richtung, name)) is not None]
    return richtung, (max(raender) + WEGABSTAND if raender else 0.0)


def enden(weg: Weg, ausgespart: list[Aussparung],
          namen: list[Flaeche]) -> tuple[Ort, Ort, Ort | None]:
    """Laesst einen Weg am Rand eines Markers, Rahmens oder Wortes anfangen und aufhoeren.

    Gekuerzt wird entlang der Tangente, bei einer Kurve also zum Steuerpunkt
    hin. Zur Sehne hin gekuerzt rutschte der Anfang eines stark gebogenen Weges
    sichtbar neben die Kurve.

    Der Steuerpunkt wird danach neu gesetzt, aus den gekuerzten Enden. Bliebe
    der alte stehen, waere die Pfeilhoehe des gezeichneten Bogens eine andere
    als die angesagte, sobald ein Ende auf einem Spieler oder an einer Stelle
    liegt. `bogen` ist ein Mass und muss auch dann nachmessbar bleiben.
    """
    von, nach = weg.von, weg.nach
    steuer = steuerpunkt(von, nach, weg.bogen)
    richtung_von, weit_von = _kuerzung(von, steuer or nach, ausgespart, namen)
    richtung_nach, weit_nach = _kuerzung(nach, steuer or von, ausgespart, namen)
    # Beide Enden zusammen nie mehr als zwei Drittel: ein kurzer Weg zwischen
    # zwei Nachbarpositionen soll schrumpfen, nicht sich umdrehen. Die Grenze
    # gilt fuer beide zusammen und nicht je Seite, damit ein breites Wort am
    # einen Ende den Platz bekommt, den am anderen niemand braucht.
    dx, dy = nach[0] - von[0], nach[1] - von[1]
    hoechstens = (dx * dx + dy * dy) ** 0.5 * 2 / 3
    if weit_von + weit_nach > hoechstens:
        faktor = hoechstens / (weit_von + weit_nach)
        weit_von, weit_nach = weit_von * faktor, weit_nach * faktor
    von = (von[0] + richtung_von[0] * weit_von, von[1] + richtung_von[1] * weit_von)
    nach = (nach[0] + richtung_nach[0] * weit_nach,
            nach[1] + richtung_nach[1] * weit_nach)
    return von, nach, steuerpunkt(von, nach, weg.bogen)


def trifft(a: Ort, b: Ort) -> bool:
    """Ob zwei Punkte derselbe Ort sind, auf fuenf Zentimeter genau."""
    return abs(a[0] - b[0]) < 0.05 and abs(a[1] - b[1]) < 0.05


def pfad(weg: Weg, blatt: Blatt, ausgespart: list[Aussparung],
         namen: list[Flaeche]) -> str:
    """Ein Weg, gerade oder gekruemmt, mit Pfeilspitze am Ende."""
    (x0, y0), (x1, y1), steuer = enden(weg, ausgespart, namen)
    anfang = f"M{koord(blatt.x(x0))} {koord(blatt.y(y0))}"
    if steuer:
        mitte = f"Q{koord(blatt.x(steuer[0]))} {koord(blatt.y(steuer[1]))} "
    else:
        mitte = "L"
    ende = f"{koord(blatt.x(x1))} {koord(blatt.y(y1))}"
    return (f'<path class="weg {weg.art}" d="{anfang} {mitte}{ende}" '
            f'marker-end="url(#spitze-{weg.art})"/>')


def flaeche(klasse: str, was: Flaeche, blatt: Blatt) -> str:
    """Eine Grundform als SVG: ein Kreis oder ein Rechteck um seinen Mittelpunkt.

    Dieselbe Rechnung fuer Geraeteteil und Zone. Was die beiden bedeuten und
    wie sie aussehen, steht in `klasse` und im Stylesheet. Ihr Mass steht
    hier, und es ist dasselbe.
    """
    x, y = was.bei
    if was.form == "kreis":
        return (f'<circle class="{klasse}" cx="{koord(blatt.x(x))}" '
                f'cy="{koord(blatt.y(y))}" '
                f'r="{koord(blatt.laenge(was.breite / 2))}"/>')
    return (f'<rect class="{klasse}" x="{koord(blatt.x(x - was.breite / 2))}" '
            f'y="{koord(blatt.y(y + was.laenge / 2))}" '
            f'width="{koord(blatt.laenge(was.breite))}" '
            f'height="{koord(blatt.laenge(was.laenge))}"/>')


def beschriftung(klasse: str, text: str, bei: Ort, blatt: Blatt) -> str:
    """Ein Wort an einem Ort in Metern, mittig um ihn herum gesetzt."""
    x, y = bei
    return (f'<text class="{klasse}" x="{koord(blatt.x(x))}" '
            f'y="{koord(blatt.y(y))}">{html.escape(text)}</text>')


def zonenflaechen(s: Szene, blatt: Blatt) -> str:
    """Die Flaechen der Zonen, jede mit gestricheltem Rand.

    Ohne ihre Beschriftung: die Flaeche liegt unter dem Aufbau, das Wort
    darueber. Warum die beiden auseinanderliegen, steht bei zonennamen().
    """
    return "".join(flaeche("zonenflaeche", zone, blatt) for zone in s.zonen)


def zonennamen(s: Szene, blatt: Blatt) -> str:
    """Die Beschriftungen der Zonen, ueber allem, was in ihnen steht.

    Die Flaeche einer Zone gehoert unter den Aufbau, ihr Wort nicht. Ein
    Marker deckt einen ganzen Meter ab; stuende das Wort mit seiner Flaeche
    unten, waere es weg, sobald jemand darauf steht. Eine Zone ohne lesbares
    Wort ist aber nur noch ein Farbfleck, der aussieht wie ein Geraet.
    """
    return "".join(beschriftung("zonenname", zone.text, zone.name_bei, blatt)
                   for zone in s.zonen)


def zonenhinweise(s: Szene) -> list[str]:
    """Je Zone, deren Wort breiter ist als sie selbst, ein Hinweis samt Ausweg.

    Gezeichnet wird trotzdem, in derselben Schrift wie alle anderen
    Beschriftungen. Ein kleiner gesetztes Wort machte das Bild uneinheitlich,
    und ein Abbruch kostete eine Runde der Schleife fuer eine Kleinigkeit.
    Aendern kann es nur der Trainer: mit einem kuerzeren Wort oder einer
    breiteren Zone.

    Verglichen wird mit der Breite der Zone, beim Kreis mit dem Durchmesser:
    dort steht sein Wort, in der Mitte. Ein Mass, das reichen wuerde, nennt
    der Hinweis nicht. Die Breite des Wortes ist geschaetzt, und eine Zahl
    auf zehn Zentimeter taete so, als waere sie gemessen.

    Genannt wird die Zone mit ihrer Nummer, wie in den Meldungen beim Lesen
    der Szene, und mit ihrem Wort, an dem der Trainer sie im Bild findet.
    """
    hinweise = []
    for nummer, zone in enumerate(s.zonen, 1):
        if wortbreite(zone.text) <= zone.breite:
            continue
        hinweise.append(
            f'Zone {nummer} "{zone.text}": das Wort ist breiter als die Zone.\n'
            "Ein kuerzeres Wort hilft, oder eine breitere Zone.")
    return hinweise


def grund(s: Szene, bei: Ort) -> str:
    """Welche Farbe an diesem Ort unter einem Wort zu sehen ist, aus GRUENDE.

    Eine Zone, sonst die Grundform, sonst das Papier daneben. Feld und
    Leinwand tragen beide die Feldfarbe. Was auf dem Boden steht, ein Geraet
    oder ein Marker, zaehlt nicht: steht dort etwas, traegt es selbst den
    Namen, und es braucht keine Stelle (ADR-0007).

    Gemessen wird an der Mitte des Wortes. Ragt es ueber den Rand des Feldes,
    gilt, worauf seine Mitte steht.
    """
    if any(zone.enthaelt(bei) for zone in s.zonen):
        return "zone"
    form = s.grundform
    if 0 <= bei[0] <= form.breite and 0 <= bei[1] <= form.laenge:
        return "feld"
    return "papier"


def stellen(s: Szene, blatt: Blatt) -> str:
    """Die Woerter der Stellen, jedes zentriert auf seinen Ort.

    Nur das Wort. Ein Punkt darunter liesse sich an einer Linie des Feldes
    nicht setzen, und ein Rand oder eine Flaeche machten aus der Stelle eine
    Zone (ADR-0007). Der Hof um die Buchstaben ist kein Rand: er hat die Farbe
    dessen, worauf das Wort steht, und faellt dort nicht auf.
    """
    return "".join(beschriftung(f"stelle grund-{grund(s, stelle.bei)}",
                                stelle.text, stelle.bei, blatt)
                   for stelle in s.stellen)


def spieler_auf(geraet: Geraet, s: Szene) -> Spieler | None:
    """Der Spieler, der auf diesem Geraet steht, oder None.

    Ein Geraet liegt unter einem Spieler, wenn seine Mitte in dessen Marker
    liegt. In der Szene steht dafuer nichts: Geraet und Spieler stehen am
    selben Ort, und erst hier faellt auf, dass sie uebereinanderliegen.

    Liegt die Mitte in zwei Markern, steht er auf dem, dessen Mitte naeher
    liegt. Auf die Reihenfolge in der Szene kommt es nicht an.
    """
    links, unten, rechts, oben = geraet.rahmen
    mitte = ((links + rechts) / 2, (unten + oben) / 2)

    def abstand(spieler: Spieler) -> float:
        return math.dist(mitte, (spieler.x, spieler.y))

    naechster = min(s.spieler, key=abstand, default=None)
    if naechster is None or abstand(naechster) > MARKER:
        return None
    return naechster


def rahmen_um(geraet: Geraet, spieler: Spieler) -> Flaeche:
    """Der Rahmen, als der ein Geraet unter einem Spieler gezeichnet wird.

    Er umfasst das Geraet und den Marker samt UEBERSTAND. Eine Kiste, die
    kleiner ist als der Marker, steht damit mittig um den Spieler, 0,2 m ueber
    den Marker hinaus. Ein Kasten von 1,6 m Breite behaelt seine Breite und
    waechst nur in der Tiefe, die unter dem Marker verschwaende. Steht der
    Spieler am Rand des Kastens, waechst der Rahmen nur auf dieser Seite. Um
    den Spieler gespiegelt, waere der Kasten breiter gezeichnet, als er ist.

    Ein Geraet nur aus Kreisen, etwa ein Huetchen, bekommt einen runden
    Rahmen um den Spieler. Ein eckiger saehe aus wie eine Kiste, auf der
    jemand steht.

    `geraet.rahmen` ist etwas anderes: der Kasten um alle Teile des Geraets,
    aus dem dieser Rahmen entsteht.
    """
    bei = (spieler.x, spieler.y)
    reicht = MARKER + UEBERSTAND
    if all(teil.form == "kreis" for teil in geraet.teile):
        radius = max([reicht] + [math.dist(teil.bei, bei) + teil.breite / 2
                                 for teil in geraet.teile])
        return Flaeche("kreis", bei, 2 * radius, 2 * radius)
    links, unten, rechts, oben = geraet.rahmen
    links, unten = min(links, spieler.x - reicht), min(unten, spieler.y - reicht)
    rechts, oben = max(rechts, spieler.x + reicht), max(oben, spieler.y + reicht)
    return Flaeche("rechteck", ((links + rechts) / 2, (unten + oben) / 2),
                   rechts - links, oben - unten)


def jenseits_des_netzes(s: Szene, spieler: Spieler) -> bool:
    """Ob der Spieler auf der Seite des Feldes steht, die im Bild oben liegt.

    Auf der freien Leinwand gibt es kein Netz und damit kein Jenseits.
    """
    return isinstance(s.grundform, Feldvorlage) and spieler.y > s.grundform.netz


@dataclass
class GeraetUnterSpieler(Geraet):
    """Ein Geraet unter einem Spieler, wie es gezeichnet wird.

    In der Szene stehen nur Geraet und Spieler am selben Ort. Was im Bild
    daraus wird, entscheidet der Zeichner und haelt es hier fest: der Rahmen
    als einziges Teil, der Spieler, von dem aus ein Weg bis an den Rahmen
    gekuerzt wird, und die Seite, auf der der Name steht.
    """

    spieler: Spieler
    name_oben: bool

    @property
    def name_bei(self) -> Ort:
        """Wo der Name steht: auf der Seite, die vom Netz weg zeigt.

        Unter dem Geraet stuende er zum Netz hin, und vom Angreifer auf der
        Kiste, einen Meter vor dem Netz, landete er auf dem Netzband.
        Jenseits des Netzes steht er deshalb im selben Abstand darueber.
        """
        if not self.name_oben:
            return super().name_bei
        links, _, rechts, oben = self.rahmen
        return ((links + rechts) / 2, oben + NAMENSABSTAND)


def szene_mit_rahmen(s: Szene) -> Szene:
    """Die Szene, wie sie gezeichnet wird: jedes Geraet unter einem Spieler als Rahmen.

    Eine Kiste unter dem Angreifer ist kleiner als sein Marker und waere
    darunter verschwunden. Als Rahmen um ihn steht sie etwas groesser da, in
    der Darstellung eines Geraets.

    Die Szene selbst bleibt, wie sie ist. Zurueck kommt eine neue, und alles,
    was danach Platz bemisst oder zeichnet, liest den Rahmen statt des
    Geraets.
    """
    geraete: list[Geraet] = []
    for geraet in s.geraete:
        spieler = spieler_auf(geraet, s)
        if spieler is not None:
            geraet = GeraetUnterSpieler(
                teile=[rahmen_um(geraet, spieler)], text=geraet.text,
                spieler=spieler, name_oben=jenseits_des_netzes(s, spieler))
        geraete.append(geraet)
    return replace(s, geraete=geraete)


def geraete(s: Szene, blatt: Blatt) -> str:
    """Die Geraete, jedes aus seinen Teilen und mit seinem Namen.

    Der Name steht darunter, bei einem Rahmen jenseits des Netzes darueber,
    siehe GeraetUnterSpieler.

    Die Teile stehen in derselben Gruppe, damit ein Ballwagen auf einem Kasten
    ein Geraet ist und nicht zwei Formen mit einem Namen dazwischen.
    """
    stuecke = []
    for geraet in s.geraete:
        stuecke.append('<g class="geraet">')
        stuecke.extend(flaeche("teil", teil, blatt) for teil in geraet.teile)
        if geraet.text:
            stuecke.append(
                beschriftung("geraetname", geraet.text, geraet.name_bei, blatt))
        stuecke.append("</g>")
    return "".join(stuecke)


def strecke(klasse: str, blatt: Blatt, von: Ort, nach: Ort, zusatz: str = "") -> str:
    """Eine gerade Linie zwischen zwei Orten in Metern."""
    return (f'<line class="{klasse}" x1="{koord(blatt.x(von[0]))}" '
            f'y1="{koord(blatt.y(von[1]))}" x2="{koord(blatt.x(nach[0]))}" '
            f'y2="{koord(blatt.y(nach[1]))}"{zusatz}/>')


def abstaende(s: Szene, blatt: Blatt) -> str:
    """Die Abstandsangaben: Massketten und beschriftete Pfeile.

    Beide zeichnen dieselbe Strecke und unterscheiden sich allein an den
    Enden. Dass ein Abstand massstaeblich stimmt, ist damit keine Frage der
    Sorgfalt, sondern eine Folge des Aufbaus: die Laenge entsteht in einer
    Rechnung, und die ist fuer beide Darstellungen dieselbe.

    Der Pfeil traegt an beiden Enden eine Spitze. Einfach bepfeilt laese er
    sich als Weg, und dann stuende eine Bewegung im Bild, die niemand gemeint
    hat.
    """
    stuecke = []
    for abstand in s.abstaende:
        a, b = abstand.enden
        nx, ny = normale(abstand.von, abstand.nach)
        stuecke.append(f'<g class="abstand {abstand.art}">')
        if abstand.versatz:
            # Die Masshilfslinien halten die verschobene Linie an dem fest,
            # was sie misst. Ohne sie schwebte eine Zahl neben dem Aufbau.
            stuecke.append(strecke("masshilfslinie", blatt, abstand.von, a))
            stuecke.append(strecke("masshilfslinie", blatt, abstand.nach, b))
        if abstand.art == "masskette":
            for punkt in (a, b):
                stuecke.append(strecke(
                    "massstrich", blatt,
                    (punkt[0] - nx * MASSSTRICH / 2, punkt[1] - ny * MASSSTRICH / 2),
                    (punkt[0] + nx * MASSSTRICH / 2, punkt[1] + ny * MASSSTRICH / 2)))
            enden = ""
        else:
            enden = (' marker-start="url(#spitze-mass)"'
                     ' marker-end="url(#spitze-mass)"')
        stuecke.append(strecke("masslinie", blatt, a, b, enden))
        stuecke.append(beschriftung("massbeschriftung", abstand.text,
                                    abstand.text_bei(wortbreite(abstand.text)),
                                    blatt))
        stuecke.append("</g>")
    return "".join(stuecke)


def marker(s: Szene, blatt: Blatt) -> str:
    """Die Spielermarker samt Beschriftung.

    Die Schrift schrumpft, sobald mehr als zwei Zeichen im Kreis stehen. Ein
    Kuerzel, das ueber den Rand laeuft, ist schlechter zu lesen als ein
    kleiner gesetztes.
    """
    teile = []
    for spieler in s.spieler:
        mx, my = blatt.x(spieler.x), blatt.y(spieler.y)
        klasse = "spieler hervorgehoben" if spieler.hervorgehoben else "spieler"
        teile.append(f'<g class="{klasse}">')
        teile.append(f'<circle class="marker" cx="{koord(mx)}" cy="{koord(my)}" '
                     f'r="{koord(blatt.laenge(MARKER))}"/>')
        if spieler.text:
            groesse = 15 if len(spieler.text) <= 2 else 11
            teile.append(f'<text class="beschriftung" x="{koord(mx)}" y="{koord(my)}" '
                         f'font-size="{groesse}">{html.escape(spieler.text)}</text>')
        teile.append("</g>")
    return "".join(teile)


def textzeile(x: float, zeile: Zeile) -> str:
    """Eine gesetzte Zeile als SVG, in ihrer Zeilenhoehe senkrecht zentriert.

    Gesetzt wird zur Mitte und nicht zur Grundlinie, weil das Stylesheet
    `dominant-baseline` schon auf die Mitte stellt. So braucht hier nichts die
    Kennwerte der Schrift zu kennen, die erst im Betrachter feststehen.
    """
    sorte, text, oben = zeile
    y = oben + zeilenhoehe(sorte) / 2
    return (f'<text class="{sorte}" x="{koord(x)}" y="{koord(y)}">'
            f'{html.escape(text)}</text>')


def textwerk(spiegel: Satzspiegel) -> str:
    """Titel und Untertitel oben, die Legende daneben, die Fusszeile darunter."""
    teile = [textzeile(spiegel.textkante, zeile) for zeile in spiegel.kopfzeilen]
    for block in spiegel.legende:
        # Je Legendenblock eine Gruppe: eine Ueberschrift mit ihren Zeilen ist
        # ein Gedanke und nicht eine Handvoll Texte, die zufaellig
        # untereinander stehen.
        teile.append('<g class="legendenblock">')
        teile.extend(textzeile(spiegel.spaltenkante, zeile) for zeile in block)
        teile.append("</g>")
    teile += [textzeile(spiegel.textkante, zeile) for zeile in spiegel.fusszeilen]
    return f'<g class="textwerk">{"".join(teile)}</g>' if teile else ""


def zeichne(s: Szene) -> str:
    """Das ganze Bild als SVG-Text, in einem Stueck."""
    s = szene_mit_rahmen(s)
    spiegel = Satzspiegel(s)
    blatt = spiegel.blatt
    teile = [
        f'<svg xmlns="http://www.w3.org/2000/svg" '
        f'viewBox="0 0 {koord(spiegel.breite)} {koord(spiegel.hoehe)}" '
        f'width="{koord(spiegel.breite)}" height="{koord(spiegel.hoehe)}" '
        f'role="img">',
    ]
    # Die oberste Zeile ist zugleich der Name des Bildes. Das traegt ueberall
    # dort, wo das SVG fuer sich steht, etwa in der Vorschau beim Zeichnen:
    # `role` allein sagt einer Vorlesehilfe nur "Grafik". In der Leseansicht
    # steckt das Bild als `<img>` mit eigenem `alt`, dort zaehlt das. Steht
    # oben ein Untertitel, benennt er das Bild genauso: er steht dort in jeder
    # Hinsicht als Titel und nicht nur in dessen Schrift.
    if s.textwerk.oberste_zeile:
        teile.append(f"<title>{html.escape(s.textwerk.oberste_zeile)}</title>")
    teile += [
        f"<style>{stil()}</style>",
        spitzen(),
        '<rect class="papier" x="0" y="0" width="100%" height="100%"/>',
        untergrund(s, blatt),
        # Geraete unter die Abstandsangaben, die Abstandsangaben unter die
        # Wege: von unten nach oben wird das Bild von dem, was steht, zu dem,
        # was passiert. Was zuletzt kommt, bleibt sichtbar.
        geraete(s, blatt),
        abstaende(s, blatt),
    ]
    # Wege unter die Marker: ein Pfeil, der einen Spieler streift, soll nicht
    # quer durch sein Kuerzel laufen. Wer auf einem Spieler oder an einer
    # Stelle anfaengt oder aufhoert, wird dafuer bis an den Rand des Markers,
    # seines Rahmens oder des Wortes gekuerzt, und wer in den Namen eines
    # Geraets reicht, bis an den Rand des Namens.
    ausgespart, namen = aussparungen(s), geraetnamen(s)
    teile.extend(pfad(weg, blatt, ausgespart, namen) for weg in s.wege)
    teile.append(marker(s, blatt))
    # Die Zonennamen ueber den Aufbau. Die Flaechen liegen ganz unten, ihre
    # Woerter ganz oben: was eine Zone bedeutet, soll nicht unter dem
    # verschwinden, was in ihr steht.
    teile.append(zonennamen(s, blatt))
    # Die Stellen noch darueber. Eine Stelle hat nichts als ihr Wort; liegt
    # etwas darueber, ist sie weg.
    teile.append(stellen(s, blatt))
    # Das Textwerk zuletzt. Es steht zwar neben dem Bild und nicht darin, aber
    # was erklaert, soll von nichts verdeckt werden, was spaeter dazukommt.
    teile.append(textwerk(spiegel))
    teile.append("</svg>")
    return "".join(teile) + "\n"


# --------------------------------------------------------------------------
# Die Dateien
# --------------------------------------------------------------------------

ENDUNG = ".szene.yml"


def finde_szene(angabe: str, wurzel: Path | None) -> Path:
    """Findet die Szenendatei zu dem, was auf der Kommandozeile stand.

    Erlaubt ist beides: der Pfad zur Datei und der blosse Basisname, wie er
    auch im Feld `schaubild:` steht. Der Basisname ist der haeufigere Fall,
    weil der Zeichen-Skill von einer Uebungs-ID kommt.

    `wurzel` ist der Arbeitsordner, sofern einer angegeben wurde. Gebraucht
    wird er allein in der letzten Zeile, wo aus einem relativen Pfad ein
    vollstaendiger wird, und erst dort wird er notfalls gesucht. Ein absoluter
    Pfad sagt schon allein, wo die Szene liegt, und rendert deshalb auch
    ausserhalb eines Arbeitsordners.
    """
    kandidat = Path(angabe)
    if kandidat.suffix not in (".yml", ".yaml"):
        kandidat = kandidat.with_name(kandidat.name + ENDUNG)
    if kandidat.is_absolute():
        return kandidat
    # Ein blosser Name ohne Ordner meint schaubilder/, dort gehoeren Szenen hin.
    if kandidat.parent == Path("."):
        kandidat = Path("schaubilder") / kandidat
    return (wurzel or finde_wurzel()) / kandidat


def ziel(quelle: Path) -> Path:
    """Das SVG liegt neben der Szene, unter demselben Basisnamen.

    Der Basisname ist der Dateiname ohne `.yml` beziehungsweise `.yaml` und
    ohne das `.szene` davor. Eine Regel statt einer Liste von Schreibweisen:
    `ue-000042.szene.yml` und `ue-000042.szene.yaml` ergeben beide `ue-000042.svg`.
    """
    stamm = quelle.with_suffix("").name
    if stamm.endswith(".szene"):
        stamm = stamm[: -len(".szene")]
    return quelle.with_name(stamm + ".svg")


def kartentitel(basisname: str, wurzel: Path | None) -> str:
    """Der `titel:` der Uebungskarte, deren ID dieser Basisname ist.

    `schaubilder/ue-000042.szene.yml` gehoert zu `uebungen/ue-000042-*.md`, und
    dort steht der Titel schon. Gesucht wird darum eine einzige Datei und nicht
    die ganze Bibliothek: das Skript braucht den Titel nur, um ihn
    vorzuschlagen, und dafuer lohnt kein Index.

    Ein zweites Bild derselben Karte traegt eine Nummer hinter der ID, etwa
    `ue-000042-2` (#39). Auch das ist die Karte ue-000042.

    Geraten wird nichts. Kein Arbeitsordner, ein Basisname, der keine
    Uebungs-ID ist, eine ID ohne Karte, eine Karte ohne `titel:`: in allen vier
    Faellen kommt eine leere Zeichenkette zurueck, und der Hinweis steht dann
    ohne Wortlaut da.
    """
    treffer = re.fullmatch(rf"({ID_MUSTER})(-\d+)?", basisname)
    if wurzel is None or not treffer:
        return ""
    karten = sorted((wurzel / "uebungen").glob(f"{treffer.group(1)}-*.md"))
    if not karten:
        return ""
    frontmatter, _ = lies_frontmatter(karten[0])
    return str(frontmatter.get("titel") or "")


# Der Ordner im Temp-Verzeichnis, in dem die Ansichten als PNG liegen. Nie
# neben dem SVG: bei der Abnahme von 1c (#28) landete eine PNG neben dem SVG
# im Arbeitsordner und ueberschrieb dort eine andere Datei.
PNG_ORDNER = "volleyball-schaubild"


def ansicht_als_png(svg: Path) -> str:
    """Nimmt das fertige Bild als PNG auf und sagt, wo es liegt oder warum nicht.

    Die Ansicht ist so gross, wie das SVG selbst sagt, auf ganze Pixel
    aufgerundet. Sie traegt den Basisnamen des Bildes, eine neue Runde
    ueberschreibt also die Ansicht der vorigen und keine fremde Datei.
    """
    programm = finde_browser()
    if programm is None:
        return "Die Ansicht als PNG fehlt: weder Edge noch Chrome gefunden."
    wurzel = ET.parse(svg).getroot()
    breite = math.ceil(float(wurzel.get("width")))
    hoehe = math.ceil(float(wurzel.get("height")))
    png = Path(tempfile.gettempdir()) / PNG_ORDNER / (svg.stem + ".png")
    try:
        png.parent.mkdir(parents=True, exist_ok=True)
        with Browser(programm) as browser:
            browser.nimm_auf(svg, png, breite, hoehe)
    except (OSError, BrowserFehler) as fehler:
        return f"Die Ansicht als PNG fehlt: {fehler}"
    return f"Ansicht als PNG: {png}"


def main() -> int:
    konsole_vorbereiten()
    ap = argparse.ArgumentParser(
        description="Aus einer Szene ein Schaubild als SVG zeichnen")
    ap.add_argument("szene",
                    help="Szenendatei oder Basisname, dann unter schaubilder/ "
                         "gesucht (etwa ue-000042)")
    ap.add_argument("--wurzel", type=Path, default=None)
    ap.add_argument("--png", action="store_true",
                    help="dazu eine Ansicht als PNG im Temp-Verzeichnis, fuer "
                         "eine Vorschau, die ein SVG nicht als Bild zeigt")
    a = ap.parse_args()

    # Gesucht wird der Arbeitsordner erst dort, wo er gebraucht wird: beim
    # relativen Szenenpfad, und beim Nachschlagen des Kartentitels. Ein
    # absoluter Pfad kommt ohne ihn aus und rendert deshalb auch aus einem
    # Verzeichnis heraus, ueber dem keine Wurzeldatei steht.
    angegebene_wurzel = a.wurzel.resolve() if a.wurzel else None
    quelle = finde_szene(a.szene, angegebene_wurzel)
    if not quelle.is_file():
        print(f"Keine Szene unter {quelle}")
        print("Eine Szene heisst <basisname>.szene.yml und liegt in schaubilder/,")
        print("neben dem Bild, das aus ihr entsteht.")
        return 1

    try:
        s = lies_szene(quelle.read_text(encoding="utf-8"))
        bild = zeichne(s)
    except SzeneFehler as fehler:
        # Erst rendern, dann schreiben: eine Szene, die nicht aufgeht, laesst
        # das Bild von vorher heil liegen, statt es halb zu ersetzen.
        print(f"{quelle.name}: {fehler}")
        print("Es wurde nichts geschrieben.")
        return 1

    datei = ziel(quelle)
    datei.parent.mkdir(parents=True, exist_ok=True)
    datei.write_text(bild, encoding="utf-8")
    print(f"Geschrieben: {datei}")
    # Fehlt die Ansicht als PNG, steht das Bild trotzdem, und der Lauf ist
    # gelungen. Wer sie nicht sehen kann, oeffnet das SVG, so wie ohne `--png`.
    if a.png:
        print(ansicht_als_png(datei))
    # Gesagt wird es trotzdem: das Bild ist fertig, aber der Trainer soll
    # wissen, dass seine Zeile oben in der Titelschrift steht, und mit einem
    # Wort daraus einen `titel:` machen koennen, wenn er will.
    if s.textwerk.untertitel_steht_oben:
        print("Ohne `titel:` steht der Untertitel oben, in der Schrift des Titels.")
        # `ziel()` hat den Basisnamen schon freigelegt. Gehoert die Szene zu
        # einer Uebung, ist er deren ID.
        #
        # Gesucht wird der Arbeitsordner zuerst ueber der Szene: dieselbe ID
        # gibt es in jeder Bibliothek, und gemeint ist die, zu der die Szene
        # gehoert, nicht die, in der der Aufruf zufaellig steht. Der Rueckfall
        # auf das Verzeichnis des Aufrufs ist die Vorschau-Schleife von
        # volleyball-schaubild: ein Entwurf im Temp-Verzeichnis hat keine
        # Wurzel ueber sich, und ohne den Rueckfall verloere er seinen
        # Vorschlag.
        vorschlag = kartentitel(
            datei.stem,
            angegebene_wurzel or suche_wurzel(quelle.parent) or suche_wurzel())
        if vorschlag:
            # In Anfuehrungszeichen, und zwar immer: ein Doppelpunkt im Titel
            # laese sich sonst als zweiter Schluessel, eine Raute als
            # Kommentar. Der Vorschlag soll eine Zeile sein, die der Trainer
            # uebernehmen kann, ohne sie nachzubessern.
            print(f'Auf der Uebungskarte steht dazu: titel: "{vorschlag}"')
    # Ebenso ein Zonenwort, das nicht in seine Zone passt: das Bild steht,
    # und der Trainer erfaehrt es in der Vorschau statt erst in der Halle.
    for hinweis in zonenhinweise(s):
        print(hinweis)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
