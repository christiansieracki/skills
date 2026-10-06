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

import base64
import re
from dataclasses import dataclass, field
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import unquote

# Elemente ohne schliessendes Tag.
LEERE_ELEMENTE = {"area", "base", "br", "col", "embed", "hr", "img", "input", "link",
                  "meta", "source", "track", "wbr"}

# Elemente mitten im Satz. Zwischen allen anderen steht beim Lesen ein
# Leerzeichen, wie der Browser sie untereinander setzt.
IM_SATZ = {"a", "abbr", "b", "code", "em", "i", "small", "span", "strong"}

# Was aufgeklappt in einem Programmpunkt stehen kann, nach der Klasse im Markup.
TEILE = {
    "heute": "Heute",
    "planabschnitt": "Abschnitt",
    "schaubild": "Schaubild der Karte",
    "karte": "Quelle und ID",
    "verweise": "Verweise",
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
class Link:
    text: str
    adresse: str
    reiter: str | None
    """Der Name des Reiters unter Nachschlagen, zu dem der Link fuehrt, sonst None."""


@dataclass
class Programmpunkt:
    zeit: str
    dauer: int | None
    name: str
    hallenteil: str
    """Der Hallenteil, wie der Generator ihn im Namen findet, "A". Ohne ihn leer."""
    uebung: str
    heute: str | None
    abschnitte: list[Abschnitt]
    """Die Abschnitte des Plans, die zu diesem Programmpunkt gehoeren, in ihrer Folge."""
    schaubilder: list[Schaubild]
    quelle: str | None
    id: str | None
    warum: str | None
    teile: list[str]
    """Was aufgeklappt untereinander steht, in dieser Folge, benannt wie in TEILE."""
    zugeklappt: bool
    warum_zugeklappt: bool
    gedaempft: bool
    verweise: list[str]
    """Die Knoepfe zum Nachschlagen, je der Name des Reiters, den er oeffnet."""
    links: list[Link]
    """Jeder Link im Text des Programmpunkts, ohne die Verweise."""


@dataclass
class Eintrag:
    """Ein Eintrag einer Liste zum Aufklappen, aus einer Zeile einer Tabelle mit `Nr | Übung`."""
    titel: str
    """"Nr. Übung", wie es zugeklappt dasteht."""
    heute: str | None
    """Was darunter steht, aus der Spalte Heute. Ohne die Spalte None."""
    inhalt: list[tuple[str, str]]
    """Was aufgeklappt dasteht, je Spalte Beschriftung und Text. Ohne Beschriftung ""."""
    zugeklappt: bool


@dataclass
class Abschnitt:
    ueberschrift: str
    """In einem Programmpunkt leer, wenn die Ueberschrift weggefallen ist."""
    text: str
    zugeklappt: bool
    listen: list[list[Eintrag]] = field(default_factory=list)
    """Jede Liste zum Aufklappen im Abschnitt, in der Folge des Plans."""
    tabellen: list[list[list[str]]] = field(default_factory=list)
    """Jede Tabelle, die eine Tabelle blieb: je Zeile ihre Zellen, die Kopfzeile vorn."""


@dataclass
class Reiter:
    name: str
    text: str


@dataclass
class Nachschlagen:
    vorweg: str
    """Der Text ueber den Reitern."""
    reiter: list[Reiter]


@dataclass
class Kopf:
    titel: str
    """Die Ueberschrift der Seite, der Kurztitel."""
    angaben: list[str]
    """Was darunter steht, je Angabe ihr Text, in der Folge der Seite."""
    zeilen: list[str]
    """Dieselben Angaben, wie sie dastehen: je Zeile ihr Text mit den Trennzeichen."""


@dataclass
class Umschalter:
    wahl: list[str]
    """Was man waehlen kann, in der Folge der Seite."""
    voreingestellt: str | None
    sichtbar: bool
    """Ob er ohne Skript zu sehen ist."""


@dataclass
class Leseansicht:
    kopf: Kopf
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
    nachschlagen: Nachschlagen | None = None
    nachgeladen: list[str] = field(default_factory=list)
    """Was die Seite von anderswo holt: Skripte und Stile mit eigener Quelle,
    jede Adresse ins Netz in einem Skript oder Stil."""
    vergroessern: list[str] = field(default_factory=list)
    """Was ohne Skript zu sehen ist und zum Vergroessern einlaedt, je sein Text."""


def _text(knoten: Knoten | None) -> str | None:
    return knoten.text() if knoten is not None else None


def _ziel(a: Knoten) -> str:
    """Die Stelle, auf die ein Link auf dieser Seite zeigt, wie der Browser sie sucht.

    Fuer einen Link woandershin leer.
    """
    adresse = a.attribute.get("href") or ""
    return unquote(adresse[1:]) if adresse.startswith("#") else ""


def _programmpunkt(knoten: Knoten, reiter: dict[str, str]) -> Programmpunkt:
    """`reiter` sind die Namen der Reiter unter Nachschlagen nach ihrem Anker."""
    kopf = knoten.erstes("summary")
    inhalt = knoten.erstes(klasse="inhalt")
    verweise = inhalt.erstes(klasse="verweise")
    knoepfe = verweise.alle("a") if verweise is not None else []
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
        hallenteil=knoten.attribute.get("data-hallenteil") or "",
        uebung=_text(kopf.erstes(klasse="uebung")) or "",
        heute=_text(heute.erstes("p")) if heute is not None else None,
        abschnitte=[_planabschnitt(k) for k in inhalt.alle(klasse="planabschnitt")],
        schaubilder=schaubilder,
        quelle=_text(inhalt.erstes(klasse="quelle")),
        id=_text(inhalt.erstes(klasse="id")),
        warum=_text(warum.erstes(klasse="rich")) if warum is not None else None,
        teile=teile,
        zugeklappt="open" not in knoten.attribute,
        warum_zugeklappt=warum is not None and "open" not in warum.attribute,
        gedaempft="gedaempft" in knoten.klassen,
        verweise=[reiter.get(_ziel(a), a.attribute.get("href") or "") for a in knoepfe],
        links=[Link(a.text(), a.attribute.get("href") or "", reiter.get(_ziel(a)))
               for a in inhalt.alle("a") if a not in knoepfe],
    )


def _kopf(seite: Knoten) -> Kopf:
    """Der Kopf ueber dem Ablauf. Jede Zeile ist ein Absatz, jede Angabe darin markiert."""
    kopf = seite.erstes(klasse="kopf")
    if kopf is None:
        return Kopf("", [], [])
    return Kopf(titel=_text(kopf.erstes("h1")) or "",
                angaben=[k.text() for k in kopf.alle(klasse="angabe")],
                zeilen=[p.text() for p in kopf.alle("p")])


def _eintrag(knoten: Knoten) -> Eintrag:
    kopf = knoten.erstes("summary")
    inhalt, beschriftung = [], ""
    for kind in knoten.erstes(klasse="eintrag-text").alle():
        if kind.tag == "dt":
            beschriftung = kind.text()
        elif kind.tag in ("dd", "p"):
            inhalt.append((beschriftung, kind.text()))
            beschriftung = ""
    return Eintrag(titel=_text(kopf.erstes(klasse="nr-uebung")) or "",
                   heute=_text(kopf.erstes(klasse="dosierung")),
                   inhalt=inhalt,
                   zugeklappt="open" not in knoten.attribute)


def _listen(knoten: Knoten) -> list[list[Eintrag]]:
    """Die Listen zum Aufklappen unter diesem Knoten, je Liste ihre Eintraege."""
    return [[_eintrag(e) for e in liste.alle("details", "eintrag")]
            for liste in knoten.alle(klasse="liste")]


def _tabellen(knoten: Knoten) -> list[list[list[str]]]:
    """Die Tabellen unter diesem Knoten, je Zeile die Texte ihrer Zellen."""
    return [[[zelle.text() for zelle in zeile.elemente() if zelle.tag in ("th", "td")]
             for zeile in tabelle.alle("tr")]
            for tabelle in knoten.alle("table")]


def _abschnitt(knoten: Knoten) -> Abschnitt:
    return Abschnitt(ueberschrift=_text(knoten.erstes("summary")) or "",
                     text=_text(knoten.erstes(klasse="rich")) or "",
                     zugeklappt="open" not in knoten.attribute,
                     listen=_listen(knoten),
                     tabellen=_tabellen(knoten))


def _planabschnitt(knoten: Knoten) -> Abschnitt:
    """Ein Abschnitt im Programmpunkt, mit seiner Ueberschrift, wenn er eine hat."""
    kopf = next((k for k in knoten.elemente() if k.tag == "h3"), None)
    return Abschnitt(ueberschrift=_text(kopf) or "",
                     text=_text(knoten.erstes(klasse="rich")) or "",
                     zugeklappt=False,
                     listen=_listen(knoten),
                     tabellen=_tabellen(knoten))


def _nachschlagen(knoten: Knoten | None) -> Nachschlagen | None:
    if knoten is None:
        return None
    return Nachschlagen(
        vorweg=_text(knoten.erstes(klasse="vorweg")) or "",
        reiter=[Reiter(_text(r.erstes("h3")) or "", _text(r.erstes(klasse="rich")) or "")
                for r in knoten.alle(klasse="reiter")])


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


def _nachgeladen(seite: Knoten) -> list[str]:
    gefunden = [f"script src={k.attribute['src']}" for k in seite.alle("script")
                if k.attribute.get("src")]
    gefunden += [f"link href={k.attribute.get('href')}" for k in seite.alle("link")]
    for k in seite.alle("script") + seite.alle("style"):
        text = "".join(kind for kind in k.kinder if isinstance(kind, str))
        gefunden += re.findall(r"https?://\S+|@import\b", text)
    return gefunden


def _vergroessern(seite: Knoten) -> list[str]:
    """Jeder Knopf, der ohne Skript zu sehen ist, und jeder Link, der "vergrößern" verspricht.

    Ein `<button>` tut ohne Skript nichts, auf dieser Seite gibt es kein
    Formular. Verborgen ist, was `hidden` traegt oder in einem `<dialog>`
    steht, der erst durch Skript aufgeht.
    """
    gefunden = []

    def suche(knoten: Knoten) -> None:
        for kind in knoten.elemente():
            if kind.tag in ("script", "style", "template", "dialog") or "hidden" in kind.attribute:
                continue
            text = kind.text() or kind.attribute.get("aria-label") or ""
            if (kind.tag == "button" or kind.attribute.get("role") == "button"
                    or (kind.tag == "a" and "vergrößer" in text.casefold())):
                gefunden.append(text)
            else:
                suche(kind)

    suche(seite)
    return gefunden


def wie_oft_eingebettet(html: str, datei: Path) -> int:
    """Wie oft der Inhalt dieser Datei in der Leseansicht steht.

    Eingebettet wird ein Bild als Data-URI, sein Inhalt steht darin in Base64.
    """
    return html.count(base64.b64encode(datei.read_bytes()).decode("ascii"))


def lies_leseansicht(html: str) -> Leseansicht:
    seite = baum(html)
    kopf = seite.erstes(klasse="ablauf-kopf")
    vorbereitung = seite.erstes(klasse="vorbereitung")
    nachschlagen = seite.erstes(klasse="nachschlagen")
    reiter = ({r.attribute.get("id"): _text(r.erstes("h3"))
               for r in nachschlagen.alle(klasse="reiter")} if nachschlagen is not None else {})
    return Leseansicht(
        kopf=_kopf(seite),
        ablauf=" · ".join(k.text() for k in kopf.elemente()) if kopf is not None else "",
        knoepfe=_knoepfe(seite),
        programmpunkte=[_programmpunkt(k, reiter) for k in seite.alle("details", "programmpunkt")],
        vorbereitung=([_abschnitt(k) for k in vorbereitung.alle("details", "abschnitt")]
                      if vorbereitung is not None else []),
        text=seite.text(),
        skripte=[s.attribute.get("src") or "".join(k for k in s.kinder if isinstance(k, str))
                 for s in seite.alle("script")],
        ereignisse=_ereignisse(seite),
        umschalter=_umschalter(seite),
        farbschema=_farbschema(seite),
        nachschlagen=_nachschlagen(nachschlagen),
        nachgeladen=_nachgeladen(seite),
        vergroessern=_vergroessern(seite),
    )
