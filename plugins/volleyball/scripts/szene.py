"""Liest eine Szene und loest sie zu Punkten in Metern auf.

Die Szene ist die Quelle, das SVG ist das Erzeugnis (ADR-0004). Dieses Modul
kennt die Quelle: es liest die YAML-Teilmenge, in der eine Szene geschrieben
ist, prueft sie und gibt Punkte in **Metern** zurueck. Wie daraus
Zeichenkoordinaten werden, weiss allein schaubild.py.

Die Trennung liegt genau hier, weil die beiden Seiten verschiedene Einheiten
sprechen. Alles, was ein Mensch in eine Szene schreibt, steht in Metern; alles,
was im SVG steht, in Zeicheneinheiten. Eine Zahl, die in beiden Welten
vorkommt, ist ein Fehler, der sich nicht ansieht.

Geprueft wird streng und frueh: eine unbekannte Grundform, ein unbekannter
Schluessel, eine Positionsnummer im Sand. Eine Szene, die nicht aufgeht, wirft
SzeneFehler, und der Aufrufer schreibt dann keine Datei. Ein stilles Weglassen
waere hier das Schlimmste: das Bild sieht fertig aus, und dass der halbe Aufbau
fehlt, merkt der Trainer erst in der Halle.

Nur Standardbibliothek, wie alles im Plugin ausser der Bildaufbereitung.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field


class SzeneFehler(Exception):
    """Die Szene geht nicht auf. Der Text ist fuer den Trainer geschrieben."""


# Ein Ort auf dem Feld, in Metern. Der Name steht in jeder Signatur, die einen
# weitergibt: die Verwechslung mit Zeichenkoordinaten ist der eine Fehler, den
# man diesem Modul nicht ansieht.
Ort = tuple[float, float]


# --------------------------------------------------------------------------
# Die YAML-Teilmenge
# --------------------------------------------------------------------------
#
# PyYAML waere eine Abhaengigkeit, und das Plugin hat sich auf die
# Standardbibliothek festgelegt. Gebraucht wird ohnehin nur ein kleiner Teil
# der Sprache: Abbildungen, Folgen von Abbildungen, Skalare und Listen in
# eckigen Klammern. Genau das kann der Parser hier, und alles andere meldet er,
# statt es zu raten.

_ZAHL = re.compile(r"-?\d+(\.\d+)?")


def _skalar(roh: str):
    """Macht aus dem Text hinter dem Doppelpunkt einen Wert.

    Kommentare am Zeilenende fallen weg, ausser der Wert steht in
    Anfuehrungszeichen. Sonst verlaere `text: "3 # 4"` seine Raute.
    """
    roh = roh.strip()
    if roh and roh[0] not in "\"'" and "#" in roh:
        roh = roh.split("#", 1)[0].strip()
    if roh in ("", "null", "~"):
        return None
    if roh in ("true", "false"):
        return roh == "true"
    if roh.startswith("[") and roh.endswith("]"):
        inner = roh[1:-1].strip()
        return [_skalar(t) for t in inner.split(",")] if inner else []
    if len(roh) >= 2 and roh[0] == roh[-1] and roh[0] in "\"'":
        return roh[1:-1]
    if _ZAHL.fullmatch(roh):
        return float(roh) if "." in roh else int(roh)
    return roh


def _zeilen(text: str) -> list[tuple[int, str, int]]:
    """Zerlegt den Text in (Einrueckung, Inhalt, Zeilennummer).

    Leerzeilen und ganze Kommentarzeilen fallen weg; sie tragen keine
    Struktur. Ein Tabulator in der Einrueckung wird gemeldet statt still als
    ein Zeichen gezaehlt: die Datei saehe im Editor richtig aus und ergaebe
    trotzdem eine andere Schachtelung.
    """
    zeilen = []
    for nummer, roh in enumerate(text.splitlines(), 1):
        if not roh.strip() or roh.lstrip().startswith("#"):
            continue
        einzug = len(roh) - len(roh.lstrip())
        if "\t" in roh[:einzug]:
            raise SzeneFehler(
                f"Zeile {nummer}: Tabulator in der Einrueckung. "
                f"Eine Szene wird mit Leerzeichen eingerueckt."
            )
        zeilen.append((einzug, roh.strip(), nummer))
    return zeilen


def _teil(zeilen, i: int, einzug: int):
    if zeilen[i][1].startswith("-"):
        return _folge(zeilen, i, einzug)
    return _abbildung(zeilen, i, einzug)


def _abbildung(zeilen, i: int, einzug: int) -> tuple[dict, int]:
    werte: dict = {}
    while i < len(zeilen) and zeilen[i][0] == einzug and not zeilen[i][1].startswith("-"):
        _, inhalt, nummer = zeilen[i]
        if ":" not in inhalt:
            raise SzeneFehler(
                f"Zeile {nummer}: {inhalt!r} ist kein Schluessel mit Doppelpunkt."
            )
        schluessel, rest = inhalt.split(":", 1)
        schluessel, rest = schluessel.strip(), rest.strip()
        i += 1
        if rest:
            werte[schluessel] = _skalar(rest)
            continue
        # Leer hinter dem Doppelpunkt: der Wert steht darunter. Eine Folge darf
        # dabei auf derselben Hoehe stehen wie ihr Schluessel, so wie YAML es
        # erlaubt und wie man es schreibt.
        tiefer = (i < len(zeilen) and (zeilen[i][0] > einzug or (
            zeilen[i][0] == einzug and zeilen[i][1].startswith("-"))))
        if tiefer:
            werte[schluessel], i = _teil(zeilen, i, zeilen[i][0])
        else:
            werte[schluessel] = None
    return werte, i


def _folge(zeilen, i: int, einzug: int) -> tuple[list, int]:
    eintraege: list = []
    while i < len(zeilen) and zeilen[i][0] == einzug and zeilen[i][1].startswith("-"):
        _, inhalt, nummer = zeilen[i]
        rest = inhalt[1:].strip()
        ende = i + 1
        while ende < len(zeilen) and zeilen[ende][0] > einzug:
            ende += 1
        unter = zeilen[i + 1:ende]
        if unter:
            # Der Text hinter dem Strich ist die erste Zeile des Eintrags. Er
            # beginnt in der Spalte, in der auch die Folgezeilen stehen, also
            # bekommt er deren Einrueckung.
            basis = unter[0][0]
            block = ([(basis, rest, nummer)] if rest else []) + list(unter)
            wert, _ = _teil(block, 0, basis)
        elif not rest or rest[0] in "[\"'" or ":" not in rest:
            wert = _skalar(rest)
        else:
            wert, _ = _abbildung([(einzug + 2, rest, nummer)], 0, einzug + 2)
        eintraege.append(wert)
        i = ende
    return eintraege, i


def lies_yaml(text: str) -> dict:
    """Liest die Teilmenge von YAML, in der eine Szene geschrieben ist."""
    zeilen = _zeilen(text)
    if not zeilen:
        raise SzeneFehler("Die Szene ist leer.")
    if zeilen[0][0] != 0:
        raise SzeneFehler(f"Zeile {zeilen[0][2]}: die Szene beginnt eingerueckt.")
    wert, i = _teil(zeilen, 0, 0)
    if i < len(zeilen):
        raise SzeneFehler(
            f"Zeile {zeilen[i][2]}: {zeilen[i][1]!r} steht schiefer als die "
            f"Zeilen darueber."
        )
    if not isinstance(wert, dict):
        raise SzeneFehler("Die Szene beginnt mit einer Liste statt mit Schluesseln.")
    return wert


# --------------------------------------------------------------------------
# Die Feldvorlagen
# --------------------------------------------------------------------------

# Die sechs Positionen der Halle, jeweils die Mitte ihrer Drittelflaeche auf
# der nahen Haelfte. Gesehen wird von oben, die nahe Mannschaft steht unten und
# schaut zum Netz: ihre rechte Seite ist damit auch die rechte Seite des
# Bildes. Position 1 ist die Aufschlagposition rechts hinten.
POSITIONEN = {
    1: (7.5, 1.5),
    2: (7.5, 7.5),
    3: (4.5, 7.5),
    4: (1.5, 7.5),
    5: (1.5, 1.5),
    6: (4.5, 1.5),
}

# Im Sand gibt es keine Rotation, auf die sich eine Nummer beziehen koennte.
# Ein Platz heisst deshalb nach dem, was der Spieler dort tut, und zwar mit dem
# Wort, das im Datenmodell schon dafuer steht: block, abwehr, annahme und
# aufschlag sind Elemente einer Uebungskarte. Die Annahme braucht zwei Plaetze
# und bekommt dafuer eine Seitenangabe.
ROLLEN = {
    "block": (4.0, 6.5),
    "abwehr": (4.0, 3.0),
    "annahme-links": (2.0, 4.5),
    "annahme-rechts": (6.0, 4.5),
    "aufschlag": (4.0, -1.0),
}

ROLLEN_KUERZEL = {
    "block": "BL",
    "abwehr": "AB",
    "annahme-links": "AL",
    "annahme-rechts": "AR",
    "aufschlag": "AS",
}


@dataclass(frozen=True)
class Feldvorlage:
    """Ein Spielfeld: Masse in Metern und die Linien, die es darauf gibt.

    Der Ursprung liegt in der linken unteren Ecke des Feldes. x waechst nach
    rechts, y zur Gegenseite hin. Das Netz liegt auf halber Laenge.
    """

    name: str
    breite: float
    laenge: float
    angriffslinien: bool
    mittellinie: bool
    positionen: dict[int, Ort]
    rollen: dict[str, Ort]

    @property
    def netz(self) -> float:
        return self.laenge / 2

    @property
    def angriffslinien_bei(self) -> tuple[float, ...]:
        """Drei Meter vor und hinter dem Netz, wenn es sie gibt."""
        if not self.angriffslinien:
            return ()
        return (self.netz - 3.0, self.netz + 3.0)


FELDVORLAGEN = {
    "halle": Feldvorlage(
        name="halle", breite=9.0, laenge=18.0,
        angriffslinien=True, mittellinie=True,
        positionen=POSITIONEN, rollen={},
    ),
    # Im Sand gibt es weder Angriffs- noch Mittellinie. Was nicht auf dem Platz
    # ist, wird auch nicht gezeichnet: eine Linie im Bild, die es draussen
    # nicht gibt, ist eine Ansage an Spieler, die niemand einhalten kann.
    "beach": Feldvorlage(
        name="beach", breite=8.0, laenge=16.0,
        angriffslinien=False, mittellinie=False,
        positionen={}, rollen=ROLLEN,
    ),
}

# Der Name der freien Leinwand in `form:`. Sie steht neben den Feldvorlagen
# und nicht darunter: eine Feldvorlage ist eine Grundform unter anderen, kein
# Normalfall mit einer Ausnahme daneben.
FREI = "frei"


@dataclass(frozen=True)
class Leinwand:
    """Eine freie Flaeche in Metern, ohne Spielfeld darauf.

    Fuer das, was auf kein Feld passt: ein Stationsbetrieb quer durch die
    Halle, ein Aufbau im Gang, eine Ecke mit drei Kaesten. Der Ursprung liegt
    wie beim Feld in der linken unteren Ecke, x waechst nach rechts, y nach
    oben. Damit misst derselbe Aufbau hier dasselbe wie dort, und der Wechsel
    zwischen beiden Grundformen kostet eine Zeile.

    Was aufs Feld passt, gehoert aufs Feld: dort ist der Massstab geschenkt.
    Die Leinwand ist der Ausnahmefall, nicht der bequemere Weg.

    Positionsnummern und Rollen gibt es hier nicht. Beide beziehen sich auf ein
    Feld, und ohne Feld gibt es nichts, worauf. Sie stehen trotzdem als leere
    Abbildungen da, damit `ort()` beide Grundformen gleich behandelt.
    """

    breite: float
    laenge: float
    name: str = FREI

    @property
    def positionen(self) -> dict[int, Ort]:
        return {}

    @property
    def rollen(self) -> dict[str, Ort]:
        return {}


# Die Grundform einer Szene: ein Spielfeld oder die freie Leinwand. Beide
# tragen name, breite, laenge, positionen und rollen; mehr braucht weder das
# Einlesen noch das Zeichnen von einer Grundform zu wissen.
Grundform = Feldvorlage | Leinwand


# --------------------------------------------------------------------------
# Was in einer Szene steht
# --------------------------------------------------------------------------

@dataclass
class Spieler:
    x: float
    y: float
    text: str


@dataclass
class Weg:
    art: str      # laufweg | ballweg
    von: Ort
    nach: Ort
    bogen: float  # Pfeilhoehe in Metern, 0 heisst gerade


# Der Abstand der Geraetebeschriftung unter dem Geraet, in Metern.
NAMENSABSTAND = 0.55

# Der Abstand der Massbeschriftung neben ihrer Linie, in Metern.
TEXTABSTAND = 0.45

TEILFORMEN = ("rechteck", "kreis")


@dataclass
class Teil:
    """Eine Grundform eines Geraetes, in Metern: Mittelpunkt und Masse.

    Ein Kreis traegt seinen Durchmesser in beiden Massen. Das spart die zweite
    Sorte Teil und kostet nichts: wer `breite` liest, bekommt bei beiden
    Formen die Ausdehnung in x.
    """

    form: str     # rechteck | kreis
    bei: Ort
    breite: float
    laenge: float

    @property
    def rahmen(self) -> tuple[float, float, float, float]:
        """Links, unten, rechts, oben in Metern."""
        x, y = self.bei
        return (x - self.breite / 2, y - self.laenge / 2,
                x + self.breite / 2, y + self.laenge / 2)


@dataclass
class Geraet:
    """Ein Kasten, ein Ballwagen, eine Zielmatte: Teile mit einem Namen.

    Zusammengesetzt statt aufgezaehlt, weil eine feste Liste von Geraeten
    immer das eine nicht kennt, das dieser Aufbau braucht. Zwei Grundformen
    tragen weit: der Ballwagen auf dem Kasten ist ein Rechteck mit einem Kreis
    darauf, und die Zielmatte ist ein Rechteck.
    """

    teile: list[Teil]
    text: str

    @property
    def rahmen(self) -> tuple[float, float, float, float]:
        """Der Kasten um alle Teile, links, unten, rechts, oben in Metern."""
        ecken = [teil.rahmen for teil in self.teile]
        return (min(e[0] for e in ecken), min(e[1] for e in ecken),
                max(e[2] for e in ecken), max(e[3] for e in ecken))

    @property
    def name_bei(self) -> Ort:
        """Wo die Beschriftung steht: mittig unter dem Geraet.

        Unter dem Geraet und nicht darin. Ein Wort wie "Ballwagen" passt in
        keinen Ballwagen, und halb verdeckt ist es schlechter zu lesen als
        daneben. Wer dieselbe Regel fuer alle Geraete nimmt, bekommt ausserdem
        ein Bild, in dem die Namen auf einer Hoehe stehen statt jeder woanders.
        """
        links, unten, rechts, _ = self.rahmen
        return ((links + rechts) / 2, unten - NAMENSABSTAND)

    def punkte(self) -> list[Ort]:
        links, unten, rechts, oben = self.rahmen
        return [(links, unten), (rechts, oben)]


@dataclass
class Abstand:
    """Eine Abstandsangabe zwischen zwei Orten, in Metern.

    `von` und `nach` sind die Orte, deren Abstand gemeint ist. Die Enden der
    gezeichneten Linie liegen um `versatz` daneben, damit eine Kette nicht quer
    durch die Marker laeuft, deren Abstand sie angibt. Gemessen und beschriftet
    wird trotzdem die Strecke zwischen `von` und `nach`: ein Schaubild, dessen
    Abstaende luegen, ist schlimmer als eines ohne Abstaende.
    """

    art: str       # masskette | pfeil
    von: Ort
    nach: Ort
    versatz: float  # Meter nach links, vom Gang von -> nach aus gesehen
    text: str

    @property
    def enden(self) -> tuple[Ort, Ort]:
        """Die beiden Enden der gezeichneten Linie, um den Versatz verschoben."""
        nx, ny = normale(self.von, self.nach)
        return ((self.von[0] + nx * self.versatz, self.von[1] + ny * self.versatz),
                (self.nach[0] + nx * self.versatz, self.nach[1] + ny * self.versatz))

    @property
    def text_bei(self) -> Ort:
        """Wo die Zahl steht: neben der Mitte der Linie.

        Auf der Seite, auf die auch der Versatz zeigt. Sonst landete die Zahl
        zwischen der Linie und dem, was sie misst, also genau dort, wo schon
        etwas steht.
        """
        (ax, ay), (bx, by) = self.enden
        nx, ny = normale(self.von, self.nach)
        weite = TEXTABSTAND if self.versatz >= 0 else -TEXTABSTAND
        return ((ax + bx) / 2 + nx * weite, (ay + by) / 2 + ny * weite)

    def punkte(self) -> list[Ort]:
        return [self.von, self.nach, *self.enden]


def meterangabe(laenge: float) -> str:
    """Eine Laenge als Text, wie sie in der Halle gesagt wird: "6 m", "4,5 m"."""
    gerundet = round(laenge, 1)
    zahl = f"{gerundet:g}".replace(".", ",")
    return f"{zahl} m"


@dataclass
class Szene:
    grundform: Grundform
    spieler: list[Spieler] = field(default_factory=list)
    wege: list[Weg] = field(default_factory=list)
    geraete: list[Geraet] = field(default_factory=list)
    abstaende: list[Abstand] = field(default_factory=list)

    def punkte(self) -> list[Ort]:
        """Alles, was auf dem Blatt Platz braucht, in Metern.

        Damit waechst die Zeichenflaeche um das herum, was ausserhalb des
        Feldes steht, etwa ein Aufschlagspieler hinter der Grundlinie, ein
        Kasten neben der Seitenlinie oder die Zahl einer Masskette. Etwas
        davon abzuschneiden waere die stillste aller Fehlermeldungen.
        """
        gesammelt = [(s.x, s.y) for s in self.spieler]
        for weg in self.wege:
            gesammelt.extend([weg.von, weg.nach, scheitel(weg.von, weg.nach, weg.bogen)])
        for geraet in self.geraete:
            gesammelt.extend(geraet.punkte())
        for abstand in self.abstaende:
            gesammelt.extend(abstand.punkte())
        return gesammelt

    def beschriftungen(self) -> list[tuple[str, Ort]]:
        """Die Texte neben dem Aufbau, je mit dem Ort, an dem sie stehen.

        Auch sie brauchen Platz im Bild, und wie viel, haengt an der
        Schriftgroesse. Die kennt schaubild.py. Hier steht deshalb nur, was wo
        steht; wie breit es wird, rechnet der Zeichner aus.
        """
        texte = [(g.text, g.name_bei) for g in self.geraete if g.text]
        return texte + [(a.text, a.text_bei) for a in self.abstaende if a.text]


def scheitel(von: Ort, nach: Ort, bogen: float) -> Ort:
    """Der am weitesten von der Geraden entfernte Punkt eines Weges.

    Das ist die Bedeutung von `bogen`, und sie steht nur hier. Bei einem
    geraden Weg ist es die Mitte der Sehne, bei einem gekruemmten liegt der
    Punkt um die Pfeilhoehe daneben, links vom Gang `von` -> `nach`. Wer die
    Kurve zeichnet, rechnet von diesem Punkt aus, statt die Formel ein zweites
    Mal hinzuschreiben.
    """
    mitte = ((von[0] + nach[0]) / 2, (von[1] + nach[1]) / 2)
    if not bogen:
        return mitte
    nx, ny = normale(von, nach)
    return (mitte[0] + nx * bogen, mitte[1] + ny * bogen)


def normale(von: Ort, nach: Ort) -> Ort:
    """Die Einheitsnormale nach links, vom Gang `von` -> `nach` aus gesehen."""
    dx, dy = nach[0] - von[0], nach[1] - von[1]
    laenge = (dx * dx + dy * dy) ** 0.5
    if laenge == 0:
        raise SzeneFehler("Ein Weg faengt dort an, wo er aufhoert.")
    return (-dy / laenge, dx / laenge)


# --------------------------------------------------------------------------
# Einlesen
# --------------------------------------------------------------------------

SZENE_SCHLUESSEL = {"form", "groesse", "spieler", "wege", "geraete", "abstaende"}
SPIELER_SCHLUESSEL = {"bei", "text"}
WEG_SCHLUESSEL = {"art", "von", "nach", "bogen"}
WEGARTEN = ("laufweg", "ballweg")
GERAET_SCHLUESSEL = {"text", "teile"}
TEIL_SCHLUESSEL = {"form", "bei", "groesse"}
ABSTAND_SCHLUESSEL = {"art", "von", "nach", "versatz", "text"}
ABSTANDSARTEN = ("masskette", "pfeil")


def _pruefe_schluessel(werte: dict, erlaubt: set[str], wo: str) -> None:
    """Meldet einen Schluessel, den es nicht gibt.

    Ein Tippfehler waere sonst die stillste Art, das halbe Bild zu verlieren:
    `spiler:` statt `spieler:` ergaebe ein leeres Feld, und das sieht fertig
    aus.
    """
    for schluessel in werte:
        if schluessel not in erlaubt:
            raise SzeneFehler(
                f"{wo}: {schluessel!r} gibt es nicht. "
                f"Moeglich ist: {', '.join(sorted(erlaubt))}."
            )


def _als_abbildung(wert, wo: str) -> dict:
    if not isinstance(wert, dict):
        raise SzeneFehler(f"{wo}: hier stehen Schluessel und Werte, nicht {wert!r}.")
    return wert


def _als_liste(wert, wo: str) -> list:
    if wert is None:
        return []
    if not isinstance(wert, list):
        raise SzeneFehler(f"{wo}: hier steht eine Liste mit Strichen, nicht {wert!r}.")
    return wert


def _als_zahl(wert, wo: str, was: str) -> float:
    """Eine Zahl in Metern. `bool` ist in Python eine Zahl, hier aber keine."""
    if not isinstance(wert, (int, float)) or isinstance(wert, bool):
        raise SzeneFehler(f"{wo}: {wert!r} ist {was}.")
    return float(wert)


def _masse(wert, wo: str) -> tuple[float, float]:
    """Ein Paar `[breite, laenge]` in Metern, beides groesser als null."""
    if not isinstance(wert, list) or len(wert) != 2:
        raise SzeneFehler(
            f"{wo}: {wert!r} sind keine Masse. Erwartet wird [breite, laenge] "
            f"in Metern."
        )
    breite = _als_zahl(wert[0], wo, "keine Breite in Metern")
    laenge = _als_zahl(wert[1], wo, "keine Laenge in Metern")
    if breite <= 0 or laenge <= 0:
        raise SzeneFehler(
            f"{wo}: [{breite:g}, {laenge:g}] misst nichts. Breite und Laenge "
            f"sind groesser als null."
        )
    return breite, laenge


def grundformen() -> list[str]:
    """Alles, was in `form:` stehen darf."""
    return sorted([*FELDVORLAGEN, FREI])


def lies_grundform(name, groesse) -> Grundform:
    """Loest `form:` und `groesse:` zur Grundform der Szene auf.

    Die beiden Schluessel gehoeren zusammen und werden deshalb zusammen
    geprueft. Ein Mass neben einer Feldvorlage waere entweder wirkungslos oder
    falsch, und beides faellt niemandem auf; eine Leinwand ohne Mass haette
    keinen Massstab, den man ihr ansehen koennte.
    """
    if name == FREI:
        if groesse is None:
            raise SzeneFehler(
                f"Die freie Leinwand braucht ein Mass: `groesse: [breite, "
                f"laenge]` in Metern. Ohne das waere der Massstab geraten, und "
                f"ein Schaubild, dessen Abstaende luegen, ist schlimmer als "
                f"eines ohne Abstaende."
            )
        return Leinwand(*_masse(groesse, "Die Leinwand"))

    if name not in FELDVORLAGEN:
        raise SzeneFehler(
            f"Die Grundform {name!r} gibt es nicht. Es gibt "
            f"{', '.join(grundformen())}."
        )
    vorlage = FELDVORLAGEN[name]
    if groesse is not None:
        raise SzeneFehler(
            f"Das Feld {name!r} misst {vorlage.breite:g} x {vorlage.laenge:g} m. "
            f"`groesse:` gibt es nur bei der freien Leinwand ({FREI!r}), die "
            f"kein Feld unter sich hat."
        )
    return vorlage


def _ortsformen(grundform: Grundform) -> str:
    """Wie ein Ort in dieser Grundform genannt werden darf.

    Zusammengesetzt aus dem, was die Grundform hergibt, statt je Fall
    ausgeschrieben. Sonst stuende in der Meldung zur freien Leinwand ein
    Hinweis auf Positionsnummern, die es dort gerade nicht gibt.
    """
    formen = []
    if grundform.positionen:
        formen.append("eine Positionsnummer ("
                      + ", ".join(str(p) for p in sorted(grundform.positionen)) + ")")
    if grundform.rollen:
        formen.append("eine Rolle (" + ", ".join(sorted(grundform.rollen)) + ")")
    formen.append("[x, y] in Metern")
    return "Moeglich ist: " + ", ".join(formen) + "."


def ort(wert, grundform: Grundform, wo: str) -> Ort:
    """Loest `bei:`, `von:` und `nach:` zu einem Punkt in Metern auf.

    Es gibt genau einen Weg, einen Ort zu nennen, und er sieht ueberall gleich
    aus: eine Zahl ist eine Positionsnummer, ein Wort ist eine Rolle, ein Paar
    in eckigen Klammern sind Meter. Welche der drei Formen erlaubt ist, sagt
    die Grundform. Nummern gibt es nur in der Halle, Rollen nur im Sand, und
    auf der freien Leinwand gibt es weder das eine noch das andere.
    """
    if wert is None:
        raise SzeneFehler(f"{wo}: es fehlt die Angabe, wo das ist.")

    if isinstance(wert, list):
        if len(wert) != 2 or not all(isinstance(z, (int, float)) for z in wert):
            raise SzeneFehler(
                f"{wo}: {wert!r} sind keine Meter. Erwartet wird [x, y], "
                f"beides Zahlen."
            )
        return (float(wert[0]), float(wert[1]))

    if isinstance(wert, bool):  # bool ist in Python eine Zahl, hier aber keine
        raise SzeneFehler(f"{wo}: {wert!r} ist kein Ort.")

    if isinstance(wert, (int, float)):
        nummer = int(wert)
        if not grundform.positionen:
            grund = ("Im Sand wird nicht rotiert, also bezieht sich keine Nummer "
                     "auf etwas." if grundform.rollen else
                     "Ohne Feld gibt es nichts, worauf sich eine Nummer beziehen "
                     "koennte.")
            raise SzeneFehler(
                f"{wo}: Positionsnummern gibt es in der Grundform "
                f"{grundform.name!r} nicht. {grund} {_ortsformen(grundform)}"
            )
        if nummer != wert or nummer not in grundform.positionen:
            raise SzeneFehler(
                f"{wo}: {wert!r} ist keine Position. Es gibt die Positionen "
                f"{', '.join(str(p) for p in sorted(grundform.positionen))}."
            )
        return grundform.positionen[nummer]

    name = str(wert)
    if not grundform.rollen:
        if name.isdigit() and grundform.positionen:
            raise SzeneFehler(f"{wo}: {name!r} steht in Anfuehrungszeichen und gilt "
                              f"damit als Rolle. Als Position ohne sie schreiben.")
        # Warum es sie nicht gibt, haengt an der Grundform. Auf der Leinwand
        # traegt gar kein Platz einen Namen, und ein Hinweis auf den Sand
        # schickte den Leser in die falsche Richtung.
        grund = ("Rollen benennen Plaetze nur im Sand." if grundform.positionen
                 else "Ohne Feld traegt kein Platz einen Namen.")
        raise SzeneFehler(
            f"{wo}: In der Grundform {grundform.name!r} gibt es keine Rollen. "
            f"{grund} {_ortsformen(grundform)}"
        )
    if name not in grundform.rollen:
        raise SzeneFehler(
            f"{wo}: die Rolle {name!r} gibt es nicht. Es gibt "
            f"{', '.join(sorted(grundform.rollen))}."
        )
    return grundform.rollen[name]


def _beschriftung(wert, bei) -> str:
    """Was im Marker steht, wenn die Szene nichts sagt.

    Eine Positionsnummer beschriftet sich selbst, eine Rolle ueber ihr
    Kuerzel. Ein Punkt in Metern hat keinen Namen und bleibt leer, statt einen
    zu bekommen, den niemand vergeben hat.
    """
    if wert is not None:
        return str(wert)
    if isinstance(bei, (int, float)) and not isinstance(bei, bool):
        return str(int(bei))
    if isinstance(bei, str):
        return ROLLEN_KUERZEL.get(bei, bei)
    return ""


def _lies_teil(eintrag, grundform: Grundform, wo: str) -> Teil:
    """Eine Grundform eines Geraetes.

    Ein Kreis bekommt eine Zahl als `groesse`, sein Durchmesser; ein Rechteck
    ein Paar. Zwei Schreibweisen fuer denselben Schluessel, weil ein Kreis mit
    zwei Massen eine Ellipse waere, und die gibt es hier nicht.
    """
    eintrag = _als_abbildung(eintrag, wo)
    _pruefe_schluessel(eintrag, TEIL_SCHLUESSEL, wo)
    art = eintrag.get("form")
    if art not in TEILFORMEN:
        raise SzeneFehler(
            f"{wo}: {art!r} ist keine Grundform fuer ein Geraeteteil. Es gibt "
            f"{', '.join(TEILFORMEN)}."
        )
    bei = ort(eintrag.get("bei"), grundform, f"{wo}, bei")
    groesse = eintrag.get("groesse")
    if art == "kreis":
        durchmesser = _als_zahl(groesse, wo, "kein Durchmesser in Metern")
        if durchmesser <= 0:
            raise SzeneFehler(f"{wo}: ein Kreis mit dem Durchmesser "
                              f"{durchmesser:g} misst nichts.")
        return Teil(art, bei, durchmesser, durchmesser)
    return Teil(art, bei, *_masse(groesse, wo))


def _lies_geraet(eintrag, grundform: Grundform, wo: str) -> Geraet:
    eintrag = _als_abbildung(eintrag, wo)
    _pruefe_schluessel(eintrag, GERAET_SCHLUESSEL, wo)
    teile = [_lies_teil(t, grundform, f"{wo}, Teil {n}")
             for n, t in enumerate(_als_liste(eintrag.get("teile"), f"{wo}, teile"), 1)]
    if not teile:
        raise SzeneFehler(
            f"{wo}: ein Geraet besteht aus mindestens einem Teil. Unter `teile:` "
            f"steht, woraus: {', '.join(TEILFORMEN)}."
        )
    return Geraet(teile=teile, text=str(eintrag.get("text") or ""))


def _lies_abstand(eintrag, grundform: Grundform, wo: str) -> Abstand:
    eintrag = _als_abbildung(eintrag, wo)
    _pruefe_schluessel(eintrag, ABSTAND_SCHLUESSEL, wo)
    art = eintrag.get("art")
    if art not in ABSTANDSARTEN:
        raise SzeneFehler(
            f"{wo}: {art!r} ist keine Art von Abstandsangabe. Es gibt "
            f"{', '.join(ABSTANDSARTEN)}."
        )
    von = ort(eintrag.get("von"), grundform, f"{wo}, von")
    nach = ort(eintrag.get("nach"), grundform, f"{wo}, nach")
    laenge = ((nach[0] - von[0]) ** 2 + (nach[1] - von[1]) ** 2) ** 0.5
    if not laenge:
        raise SzeneFehler(
            f"{wo}: `von` und `nach` sind derselbe Ort. Zwischen einem Ort und "
            f"sich selbst gibt es keinen Abstand einzuzeichnen."
        )
    # `or 0` waere hier falsch: es machte aus `versatz: false` still eine Null
    # und nicht die Meldung, die _als_zahl fuer einen Wahrheitswert bereithaelt.
    versatz = eintrag.get("versatz")
    # Ohne eigenen Text steht da, was gemessen wurde. Wer selbst etwas
    # hinschreibt, verantwortet es: gezeichnet wird in beiden Faellen die
    # Strecke zwischen `von` und `nach`.
    return Abstand(
        art=art,
        von=von,
        nach=nach,
        versatz=_als_zahl(0 if versatz is None else versatz, wo,
                          "kein Versatz in Metern"),
        text=str(eintrag.get("text") or meterangabe(laenge)),
    )


def lies_szene(text: str) -> Szene:
    """Macht aus dem Text einer Szenendatei eine gepruefte Szene."""
    roh = lies_yaml(text)
    _pruefe_schluessel(roh, SZENE_SCHLUESSEL, "Die Szene")

    name = roh.get("form")
    if name is None:
        raise SzeneFehler(
            f"Der Szene fehlt die Grundform. `form:` nennt eine von "
            f"{', '.join(grundformen())}."
        )
    form = lies_grundform(name, roh.get("groesse"))

    spieler = []
    for nummer, eintrag in enumerate(_als_liste(roh.get("spieler"), "spieler"), 1):
        wo = f"Spieler {nummer}"
        eintrag = _als_abbildung(eintrag, wo)
        _pruefe_schluessel(eintrag, SPIELER_SCHLUESSEL, wo)
        bei = eintrag.get("bei")
        x, y = ort(bei, form, wo)
        spieler.append(Spieler(x, y, _beschriftung(eintrag.get("text"), bei)))

    wege = []
    for nummer, eintrag in enumerate(_als_liste(roh.get("wege"), "wege"), 1):
        wo = f"Weg {nummer}"
        eintrag = _als_abbildung(eintrag, wo)
        _pruefe_schluessel(eintrag, WEG_SCHLUESSEL, wo)
        art = eintrag.get("art")
        if art not in WEGARTEN:
            raise SzeneFehler(
                f"{wo}: {art!r} ist keine Wegart. Es gibt "
                f"{', '.join(WEGARTEN)}."
            )
        bogen = eintrag.get("bogen") or 0
        if not isinstance(bogen, (int, float)) or isinstance(bogen, bool):
            raise SzeneFehler(f"{wo}: bogen {bogen!r} ist keine Pfeilhoehe in Metern.")
        weg = Weg(
            art=art,
            von=ort(eintrag.get("von"), form, f"{wo}, von"),
            nach=ort(eintrag.get("nach"), form, f"{wo}, nach"),
            bogen=float(bogen),
        )
        normale(weg.von, weg.nach)  # meldet einen Weg der Laenge null
        wege.append(weg)

    geraete = [_lies_geraet(eintrag, form, f"Geraet {nummer}")
               for nummer, eintrag
               in enumerate(_als_liste(roh.get("geraete"), "geraete"), 1)]

    abstaende = [_lies_abstand(eintrag, form, f"Abstand {nummer}")
                 for nummer, eintrag
                 in enumerate(_als_liste(roh.get("abstaende"), "abstaende"), 1)]

    return Szene(grundform=form, spieler=spieler, wege=wege,
                 geraete=geraete, abstaende=abstaende)
