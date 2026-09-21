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
    """Eine Grundform: Masse in Metern und die Linien, die es darauf gibt.

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


@dataclass
class Szene:
    vorlage: Feldvorlage
    spieler: list[Spieler] = field(default_factory=list)
    wege: list[Weg] = field(default_factory=list)

    def punkte(self) -> list[Ort]:
        """Alles, was auf dem Blatt Platz braucht, in Metern.

        Damit waechst die Zeichenflaeche um das herum, was ausserhalb des
        Feldes steht, etwa ein Aufschlagspieler hinter der Grundlinie. Ihn
        abzuschneiden waere die stillste aller Fehlermeldungen.
        """
        gesammelt = [(s.x, s.y) for s in self.spieler]
        for weg in self.wege:
            gesammelt.extend([weg.von, weg.nach, scheitel(weg.von, weg.nach, weg.bogen)])
        return gesammelt


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

SZENE_SCHLUESSEL = {"form", "spieler", "wege"}
SPIELER_SCHLUESSEL = {"bei", "text"}
WEG_SCHLUESSEL = {"art", "von", "nach", "bogen"}
WEGARTEN = ("laufweg", "ballweg")


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


def ort(wert, vorlage: Feldvorlage, wo: str) -> Ort:
    """Loest `bei:`, `von:` und `nach:` zu einem Punkt in Metern auf.

    Es gibt genau einen Weg, einen Ort zu nennen, und er sieht ueberall gleich
    aus: eine Zahl ist eine Positionsnummer, ein Wort ist eine Rolle, ein Paar
    in eckigen Klammern sind Meter. Welche der drei Formen erlaubt ist, sagt
    die Grundform. Nummern gibt es nur in der Halle, Rollen nur im Sand.
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
        if not vorlage.positionen:
            raise SzeneFehler(
                f"{wo}: Positionsnummern gibt es auf dem Feld {vorlage.name!r} "
                f"nicht. Im Sand wird nicht rotiert, also bezieht sich keine "
                f"Nummer auf etwas. Einen Platz hier ueber eine Rolle nennen "
                f"({', '.join(sorted(vorlage.rollen))}) oder ueber [x, y] in Metern."
            )
        if nummer != wert or nummer not in vorlage.positionen:
            raise SzeneFehler(
                f"{wo}: {wert!r} ist keine Position. Es gibt die Positionen "
                f"{', '.join(str(p) for p in sorted(vorlage.positionen))}."
            )
        return vorlage.positionen[nummer]

    name = str(wert)
    if not vorlage.rollen:
        hinweis = (f"Einen Platz hier ueber eine Positionsnummer nennen "
                   f"({', '.join(str(p) for p in sorted(vorlage.positionen))}) "
                   f"oder ueber [x, y] in Metern.")
        if name.isdigit():
            raise SzeneFehler(f"{wo}: {name!r} steht in Anfuehrungszeichen und gilt "
                              f"damit als Rolle. Als Position ohne sie schreiben.")
        raise SzeneFehler(
            f"{wo}: Rollen benennen Plaetze nur im Sand, nicht auf dem Feld "
            f"{vorlage.name!r}. {hinweis}"
        )
    if name not in vorlage.rollen:
        raise SzeneFehler(
            f"{wo}: die Rolle {name!r} gibt es nicht. Es gibt "
            f"{', '.join(sorted(vorlage.rollen))}."
        )
    return vorlage.rollen[name]


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


def lies_szene(text: str) -> Szene:
    """Macht aus dem Text einer Szenendatei eine gepruefte Szene."""
    roh = lies_yaml(text)
    _pruefe_schluessel(roh, SZENE_SCHLUESSEL, "Die Szene")

    name = roh.get("form")
    if name is None:
        raise SzeneFehler(
            f"Der Szene fehlt die Grundform. `form:` nennt eine von "
            f"{', '.join(sorted(FELDVORLAGEN))}."
        )
    if name not in FELDVORLAGEN:
        raise SzeneFehler(
            f"Die Grundform {name!r} gibt es nicht. Es gibt "
            f"{', '.join(sorted(FELDVORLAGEN))}."
        )
    vorlage = FELDVORLAGEN[name]

    spieler = []
    for nummer, eintrag in enumerate(_als_liste(roh.get("spieler"), "spieler"), 1):
        wo = f"Spieler {nummer}"
        eintrag = _als_abbildung(eintrag, wo)
        _pruefe_schluessel(eintrag, SPIELER_SCHLUESSEL, wo)
        bei = eintrag.get("bei")
        x, y = ort(bei, vorlage, wo)
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
            von=ort(eintrag.get("von"), vorlage, f"{wo}, von"),
            nach=ort(eintrag.get("nach"), vorlage, f"{wo}, nach"),
            bogen=float(bogen),
        )
        normale(weg.von, weg.nach)  # meldet einen Weg der Laenge null
        wege.append(weg)

    return Szene(vorlage=vorlage, spieler=spieler, wege=wege)
