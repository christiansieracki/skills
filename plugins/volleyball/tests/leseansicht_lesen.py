"""Liest eine erzeugte Leseansicht in eine einfache Form zurueck.

Die Tests der Leseansicht pruefen, was ein Trainer in ihr findet, und nicht,
in welchem Markup es steht. Das Markup kennt nur dieser Helfer (#50, Testing
Decisions). Aendert sich die Gestaltung, wird er nachgezogen, und die Tests
bleiben, wie sie sind.

Gelesen wird mit html.parser aus der Standardbibliothek in einen kleinen
Baum. Darauf suchen die Funktionen unten nach den Klassen, die leseansicht.py
vergibt. Was der Trainer sieht, kommt als Text zurueck, mit einfachen
Leerzeichen, so wie es im Browser dasteht.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from html.parser import HTMLParser

# Elemente ohne schliessendes Tag.
LEERE_ELEMENTE = {"area", "base", "br", "col", "embed", "hr", "img", "input", "link",
                  "meta", "source", "track", "wbr"}

# Elemente mitten im Satz. Zwischen allen anderen steht beim Lesen ein
# Leerzeichen, wie der Browser sie untereinander setzt.
IM_SATZ = {"a", "abbr", "b", "code", "em", "i", "small", "span", "strong"}

# Was aufgeklappt in einem Programmpunkt stehen kann, nach der Klasse im Markup.
TEILE = {
    "heute": "Heute",
    "schaubild": "Schaubild der Karte",
    "karte": "Quelle und ID",
    "warum": "Warum hier?",
}


class Knoten:
    """Ein Element der Seite mit seinen Kindern, Elementen und Text in ihrer Folge."""

    def __init__(self, tag: str, attribute: dict[str, str | None]) -> None:
        self.tag = tag
        self.attribute = attribute
        self.kinder: list[Knoten | str] = []

    @property
    def klassen(self) -> set[str]:
        return set((self.attribute.get("class") or "").split())

    def text(self) -> str:
        """Der Text, den der Browser zeigt. Skript und Stil gehoeren nicht dazu."""
        stuecke: list[str] = []

        def sammle(knoten: Knoten) -> None:
            for kind in knoten.kinder:
                if isinstance(kind, str):
                    stuecke.append(kind)
                elif kind.tag not in ("script", "style"):
                    trenner = "" if kind.tag in IM_SATZ else " "
                    stuecke.append(trenner)
                    sammle(kind)
                    stuecke.append(trenner)

        sammle(self)
        return " ".join("".join(stuecke).split())

    def alle(self, tag: str | None = None, klasse: str | None = None) -> list[Knoten]:
        """Jeder Nachfahre mit diesem Tag und dieser Klasse, in der Folge der Seite."""
        gefunden = []
        for kind in self.kinder:
            if isinstance(kind, str):
                continue
            if (tag is None or kind.tag == tag) and (klasse is None or klasse in kind.klassen):
                gefunden.append(kind)
            gefunden += kind.alle(tag, klasse)
        return gefunden

    def erstes(self, tag: str | None = None, klasse: str | None = None) -> Knoten | None:
        treffer = self.alle(tag, klasse)
        return treffer[0] if treffer else None

    def elemente(self) -> list[Knoten]:
        """Die direkten Kinder, die Elemente sind."""
        return [kind for kind in self.kinder if isinstance(kind, Knoten)]


class _Baumbauer(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.dokument = Knoten("#dokument", {})
        self.stapel = [self.dokument]

    def handle_starttag(self, tag, attrs) -> None:
        knoten = Knoten(tag, dict(attrs))
        self.stapel[-1].kinder.append(knoten)
        if tag not in LEERE_ELEMENTE:
            self.stapel.append(knoten)

    def handle_startendtag(self, tag, attrs) -> None:
        self.stapel[-1].kinder.append(Knoten(tag, dict(attrs)))

    def handle_endtag(self, tag) -> None:
        for tiefe in range(len(self.stapel) - 1, 0, -1):
            if self.stapel[tiefe].tag == tag:
                del self.stapel[tiefe:]
                return

    def handle_data(self, data) -> None:
        self.stapel[-1].kinder.append(data)


def baum(html: str) -> Knoten:
    bauer = _Baumbauer()
    bauer.feed(html)
    bauer.close()
    return bauer.dokument


@dataclass
class Schaubild:
    datei: str
    """Was im Bild als Quelle steht: ein Pfad, oder beim Einbetten die Daten."""
    beschriftung: str
    """"Schaubild 1 von 2" und weiter. Bei einem einzelnen Bild leer."""


@dataclass
class Programmpunkt:
    zeit: str
    dauer: int | None
    name: str
    uebung: str
    heute: str | None
    schaubilder: list[Schaubild]
    quelle: str | None
    id: str | None
    warum: str | None
    teile: list[str]
    """Was aufgeklappt untereinander steht, in dieser Folge, benannt wie in TEILE."""
    zugeklappt: bool
    warum_zugeklappt: bool
    gedaempft: bool


@dataclass
class Abschnitt:
    ueberschrift: str
    text: str
    zugeklappt: bool


@dataclass
class Umschalter:
    wahl: list[str]
    """Was man waehlen kann, in der Folge der Seite."""
    voreingestellt: str | None
    sichtbar: bool
    """Ob er ohne Skript zu sehen ist."""


@dataclass
class Leseansicht:
    ablauf: str
    """Die Zeile ueber dem Ablauf, etwa "Ablauf · 3 Programmpunkte · Minuten ab Beginn"."""
    knoepfe: list[str]
    """Die Knoepfe ueber dem Ablauf, die zu etwas auf der Seite fuehren."""
    programmpunkte: list[Programmpunkt]
    vorbereitung: list[Abschnitt]
    text: str
    """Aller Text der Seite ausserhalb von Skript und Stil."""
    skripte: list[str]
    """Je Skript sein Inhalt oder seine Quelle."""
    ereignisse: list[str]
    """Skript an Elementen: Attribute wie onclick und Links auf javascript:."""
    umschalter: Umschalter | None
    """Der Umschalter Hell, Dunkel, System."""
    farbschema: dict[str, str]
    """Das Farbschema ohne Skript, je Bedingung einer Media-Query, "" ohne Bedingung."""


def _text(knoten: Knoten | None) -> str | None:
    return knoten.text() if knoten is not None else None


def _programmpunkt(knoten: Knoten) -> Programmpunkt:
    kopf = knoten.erstes("summary")
    inhalt = knoten.erstes(klasse="inhalt")
    dauer = _text(kopf.erstes(klasse="dauer"))
    heute = inhalt.erstes(klasse="heute")
    warum = inhalt.erstes(klasse="warum")
    schaubilder = []
    for bild in inhalt.alle("figure"):
        unterschrift = bild.erstes("figcaption")
        schaubilder.append(Schaubild(bild.erstes("img").attribute.get("src") or "",
                                     _text(unterschrift) or ""))
    teile = [TEILE[k] for kind in inhalt.elemente() for k in sorted(kind.klassen) if k in TEILE]
    return Programmpunkt(
        zeit=_text(kopf.erstes(klasse="zeit")) or "",
        dauer=int(re.search(r"\d+", dauer).group()) if dauer else None,
        name=_text(kopf.erstes(klasse="name")) or "",
        uebung=_text(kopf.erstes(klasse="uebung")) or "",
        heute=_text(heute.erstes("p")) if heute is not None else None,
        schaubilder=schaubilder,
        quelle=_text(inhalt.erstes(klasse="quelle")),
        id=_text(inhalt.erstes(klasse="id")),
        warum=_text(warum.erstes(klasse="rich")) if warum is not None else None,
        teile=teile,
        zugeklappt="open" not in knoten.attribute,
        warum_zugeklappt=warum is not None and "open" not in warum.attribute,
        gedaempft="gedaempft" in knoten.klassen,
    )


def _abschnitt(knoten: Knoten) -> Abschnitt:
    return Abschnitt(ueberschrift=_text(knoten.erstes("summary")) or "",
                     text=_text(knoten.erstes(klasse="rich")) or "",
                     zugeklappt="open" not in knoten.attribute)


def _knoepfe(seite: Knoten) -> list[str]:
    """Die Knoepfe ueber dem Ablauf, deren Ziel es auf der Seite gibt."""
    ziele = {k.attribute.get("id") for k in seite.alle() if k.attribute.get("id")}
    leiste = seite.erstes(klasse="knoepfe")
    if leiste is None:
        return []
    return [a.text() for a in leiste.alle("a")
            if (a.attribute.get("href") or "").startswith("#")
            and a.attribute["href"][1:] in ziele]


def _ereignisse(seite: Knoten) -> list[str]:
    gefunden = []
    for knoten in seite.alle():
        for name, wert in knoten.attribute.items():
            if name.startswith("on"):
                gefunden.append(f"{knoten.tag} {name}")
            elif (wert or "").strip().lower().startswith("javascript:"):
                gefunden.append(f"{knoten.tag} {name}={wert}")
    return gefunden


def _umschalter(seite: Knoten) -> Umschalter | None:
    feld = seite.erstes(klasse="darstellung")
    if feld is None:
        return None
    wahl = [(label.text(), "checked" in label.erstes("input").attribute)
            for label in feld.alle("label")]
    return Umschalter(wahl=[name for name, _ in wahl],
                      voreingestellt=next((name for name, an in wahl if an), None),
                      sichtbar="hidden" not in feld.attribute)


def _regeln(stil: str) -> list[tuple[str, str, str]]:
    """Je Regel im Stil ihre Media-Query ohne Leerzeichen, ihr Selektor und ihre Deklarationen."""
    regeln, offen = [], []
    for m in re.finditer(r"([^{}]*)([{}])", stil):
        davor = m.group(1).strip()
        if m.group(2) == "{":
            offen.append(davor)
        elif offen:
            selektor = offen.pop()
            if not selektor.startswith("@"):
                media = "".join(o.removeprefix("@media") for o in offen)
                regeln.append(("".join(media.split()), selektor, davor))
    return regeln


# Ein Selektor fuer das Wurzelelement, mit Bedingungen an seine Attribute.
WURZEL = re.compile(r":root((?::not\()?\[[\w-]+(?:=[^\]]*)?\]\)?)*")
BEDINGUNG = re.compile(r"(:not\()?\[([\w-]+)(?:=\"?([^\]\"]*)\"?)?\]")


def _trifft_wurzel(selektor: str, wurzel: Knoten) -> bool:
    """Ob der Selektor das Wurzelelement trifft, wie es im HTML steht, ohne Skript."""
    if not WURZEL.fullmatch(selektor.strip()):
        return False
    for nicht, name, wert in BEDINGUNG.findall(selektor):
        hat = name in wurzel.attribute and wert in ("", wurzel.attribute[name])
        if hat == bool(nicht):
            return False
    return True


def _farbschema(seite: Knoten) -> dict[str, str]:
    """Welches color-scheme ohne Skript am Wurzelelement gilt, je Media-Query."""
    wurzel = seite.erstes("html")
    stil = "".join(k for s in seite.alle("style") for k in s.kinder if isinstance(k, str))
    schema = {}
    for media, selektor, deklarationen in _regeln(stil):
        m = re.search(r"color-scheme:\s*([\w ]+)", deklarationen)
        if m and any(_trifft_wurzel(s, wurzel) for s in selektor.split(",")):
            schema[media] = m.group(1).strip()
    return schema


def lies_leseansicht(html: str) -> Leseansicht:
    seite = baum(html)
    kopf = seite.erstes(klasse="ablauf-kopf")
    vorbereitung = seite.erstes(klasse="vorbereitung")
    return Leseansicht(
        ablauf=" · ".join(k.text() for k in kopf.elemente()) if kopf is not None else "",
        knoepfe=_knoepfe(seite),
        programmpunkte=[_programmpunkt(k) for k in seite.alle("details", "programmpunkt")],
        vorbereitung=([_abschnitt(k) for k in vorbereitung.alle("details", "abschnitt")]
                      if vorbereitung is not None else []),
        text=seite.text(),
        skripte=[s.attribute.get("src") or "".join(k for k in s.kinder if isinstance(k, str))
                 for s in seite.alle("script")],
        ereignisse=_ereignisse(seite),
        umschalter=_umschalter(seite),
        farbschema=_farbschema(seite),
    )
