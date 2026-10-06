#!/usr/bin/env python3
"""Macht aus einem Trainingsplan die Leseansicht fuers Handy.

    <python> leseansicht.py trainings/h1-h2/2026-09-15.md

Erzeugt die .html neben der .md, eine einzige Datei, die auch ohne
JavaScript lesbar ist. Die Ablauftabelle wird dabei bewusst NICHT als Tabelle
gezeigt: sechs Spalten sind auf einem Handy in der Halle unlesbar. Jede Zeile
wird ein Programmpunkt, der zugeklappt Zeitangabe, Dauer, Name und Uebung
zeigt und sich mit dem Daumen aufklappen laesst. Beginnt die Ueberschrift
eines Abschnitts mit einer Zeitangabe, steht er aufgeklappt in diesem
Programmpunkt (Glossar). `## Zum Nachschlagen` steht am Ende fuer sich, jede
`###` darin ein Reiter. Alle anderen Abschnitte des Plans stehen am Ende unter
Vorbereitung, auch einer, dessen Zeitangabe auf keinen Programmpunkt passt.
Den nennt das Skript auf der Konsole. Ein kurzes eingebettetes Skript macht
aus Nachschlagen und Vorbereitung Ansichten, die sich ueber dem Ablauf
oeffnen. Gestaltet ist die Seite nach der Vorlage unter
docs/gestaltung/leseansicht/, hell oder dunkel nach dem Geraet. Wo
JavaScript laeuft, waehlt der Trainer Hell, Dunkel oder System selbst
(ADR-0012).

Erzeugt wird in zwei Schritten. `gliedere` zerlegt den Plan in eine
Gliederung: die Rohdaten fuer den Kopf, die Programmpunkte, Nachschlagen, die
Vorbereitung und die Meldungen. `schreibe` macht daraus das HTML. Die
Gestaltung steckt nur im zweiten Schritt.

Hat eine Uebung im Ablauf ein Schaubild auf ihrer Karte, steht es bei ihr,
bei einer Liste alle in ihrer Reihenfolge. Standardmaessig als Data-URI
eingebettet, damit die Datei allein lauffaehig ist und auch dann noch Bilder
zeigt, wenn man sie sich aufs Handy schickt. Das macht sie gross. Wer sie
klein braucht, nimmt --bilder verweis, dann steht ein relativer Pfad nach
schaubilder/ drin. Mit Skript laesst sich jedes Schaubild, wie jede
Hallenskizze, in einer Ansicht vergroessern. Die nimmt das Bild beim Oeffnen
aus dem Programmpunkt, eingebettet steht es nur einmal in der Datei.

Der Trainingsplan bleibt die Quelle. Die Leseansicht traegt unten das Datum
ihrer Erzeugung, damit man sieht, ob sie zur aktuellen Fassung passt. Wer in
die HTML tippt, verliert es beim naechsten Erzeugen.
"""

from __future__ import annotations

import argparse
import base64
import html
import mimetypes
import os
import re
import sys
from collections.abc import Iterator
from dataclasses import dataclass, field, replace
from datetime import date, datetime
from pathlib import Path
from typing import NamedTuple
from urllib.parse import unquote

sys.path.insert(0, str(Path(__file__).resolve().parent))
from tpdaten import (  # noqa: E402
    finde_wurzel, konsole_vorbereiten, lies_frontmatter, lies_gruppen, lies_uebungen, schaubilder,
    tabellenzellen,
)

# --------------------------------------------------------------------------
# Die Gliederung
# --------------------------------------------------------------------------

# Eine Zeitangabe: von-bis in ganzen Minuten ab Beginn, mit Halbgeviertstrich
# oder Bindestrich, so wie in der Spalte Zeit (Glossar).
ZEITANGABE = re.compile(r"(\d+)\s*[–-]\s*(\d+)")

# Ein Markdown-Link auf eine Ueberschrift im Plan: [Text](#anker).
LINK_AUF_UEBERSCHRIFT = re.compile(r"\[[^\]]+\]\(#([^)\s]+)\)")

# Die Spalten der Ablauftabelle und unter welchen Ueberschriften sie stehen
# koennen, kleingeschrieben. Die zweite hiess bis zur Welle zur Leseansicht
# "Teil", davor "Block". Alte Plaene gelten weiter.
SPALTEN = {
    "zeit": ("zeit",),
    "name": ("programmpunkt", "teil", "block"),
    "uebung": ("übung", "uebung"),
    "id": ("id",),
    "heute": ("anpassung heute", "anpassung"),
    "warum": ("warum hier", "begründung", "warum"),
}


def anker(ueberschrift: str) -> str:
    """Der Anker einer Ueberschrift, wie GitHub ihn bildet.

    Klein geschrieben, Satzzeichen fallen weg, jedes Leerzeichen wird ein
    Bindestrich. Umlaute bleiben. So fuehrt ein Link wie `[…](#die-läufer)`
    in der .md und in der Leseansicht zur selben Ueberschrift.
    """
    return re.sub(r"[^\w\- ]", "", ueberschrift.strip().lower()).replace(" ", "-")


class Zeitangabe(NamedTuple):
    """Von und bis in ganzen Minuten ab Beginn. Wie sie geschrieben ist, zaehlt nicht."""

    von: int
    bis: int

    @property
    def minuten(self) -> int:
        return self.bis - self.von


def zeitangabe(text: str) -> Zeitangabe | None:
    """Die Zeitangabe, wenn der Text eine ist, sonst None."""
    m = ZEITANGABE.fullmatch(text.strip())
    if not m:
        return None
    von, bis = int(m.group(1)), int(m.group(2))
    return Zeitangabe(von, bis) if von < bis else None


# Eine Ueberschrift, die mit einer Zeitangabe beginnt: "46–93 Drei Sechser".
# Was danach steht, ist der Rest der Ueberschrift. "18:00 Aufwaermen" beginnt
# mit keiner.
VORN_ZEITANGABE = re.compile(r"(\d+\s*[–-]\s*\d+)(?!\d|[:.]\d)[\s:,·–—-]*(.*)")

# Der Hallenteil, im Namen eines Programmpunkts ("Zuspiel, Hallenteil A") wie
# in einer Ueberschrift gleich hinter der Zeitangabe ("Hallenteil A: Skizze").
# Seine Kennung ist ein einzelner Buchstabe oder eine Ziffer. "Hallenteil
# wechseln" nennt keinen, das ist Text.
HALLENTEIL = re.compile(r"\bHallenteil\s+([^\W_])(?!\w)", re.IGNORECASE)


@dataclass
class Zuordnung:
    """Was eine Ueberschrift ueber ihren Programmpunkt sagt: "69–89 Hallenteil A: Hallenskizze"."""

    zeit: str
    """Die Zeitangabe, wie sie in der Ueberschrift steht."""
    zeitangabe: Zeitangabe
    hallenteil: str
    """Leer, wenn keiner dabeisteht. Dann gilt der Abschnitt fuer jeden Programmpunkt zu der Zeit."""
    rest: str
    """Die Ueberschrift ohne Zeitangabe und Hallenteil."""


def zuordnung(ueberschrift: str) -> Zuordnung | None:
    """Wozu die Ueberschrift gehoert, wenn sie mit einer Zeitangabe beginnt. Sonst None."""
    m = VORN_ZEITANGABE.match(ueberschrift.strip())
    von_bis = zeitangabe(m.group(1)) if m else None
    if von_bis is None:
        return None
    zeit, rest = m.group(1), m.group(2).strip()
    kennung = HALLENTEIL.match(rest)
    if kennung:
        return Zuordnung(zeit, von_bis, kennung.group(1),
                         rest[kennung.end():].lstrip(" :,·–—-"))
    return Zuordnung(zeit, von_bis, "", rest)


@dataclass
class Abschnitt:
    """Ein Stueck des Plans unter einer Ueberschrift, `##` oder `###`.

    `zeilen` ist das Markdown unter der Ueberschrift bis zum ersten
    Unterabschnitt. Die `###` eines `##` stehen fuer sich in
    `unterabschnitte`, jeder mit seiner Ueberschrift.

    Stufe 1 ist der Text zwischen dem Titel und dem ersten `##`. Er traegt
    den Titel als Ueberschrift.
    """

    stufe: int
    ueberschrift: str
    zeilen: list[str] = field(default_factory=list)
    unterabschnitte: list[Abschnitt] = field(default_factory=list)

    @property
    def leer(self) -> bool:
        return (not any(z.strip() for z in self.zeilen)
                and all(u.leer for u in self.unterabschnitte))

    @property
    def ist_ablauf(self) -> bool:
        return self.stufe == 2 and self.ueberschrift.lower().startswith("ablauf")

    @property
    def ist_nachschlagen(self) -> bool:
        return self.stufe == 2 and self.ueberschrift.lower() == "zum nachschlagen"


@dataclass
class Karte:
    """Was die Leseansicht von einer Uebungskarte braucht.

    `schaubilder` sind die Dateien unter schaubilder/, in der Reihenfolge der
    Karte. Fehlt eine, faellt nur sie weg. Eine Leseansicht ohne Bild ist
    brauchbar, eine mit totem Bildverweis nicht.
    """

    titel: str
    quelle: str
    schaubilder: list[Path]


@dataclass
class Programmpunkt:
    """Eine Zeile der Ablauftabelle. Die Texte als Markdown, wie sie im Plan stehen.

    `id`, `heute` und `warum` sind leer, wenn die Zelle leer ist oder "—" heisst.
    `abschnitte` sind die Abschnitte des Plans, die ueber ihre Zeitangabe zu
    ihm gehoeren, in der Reihenfolge des Plans, jeder mit der Ueberschrift,
    die hier steht.
    """

    zeit: str
    name: str
    uebung: str
    id: str
    heute: str
    warum: str
    karte: Karte | None = None
    abschnitte: list[Abschnitt] = field(default_factory=list)
    verweise: list[Abschnitt] = field(default_factory=list)
    """Die Reiter unter Nachschlagen, auf die der Programmpunkt verweist, jeder einmal."""

    def texte(self) -> list[str]:
        """Was der Plan zu diesem Programmpunkt schreibt, in der Folge der Leseansicht.

        Aus diesen Texten kommen seine Verweise: "Heute", die Abschnitte, die
        ihm gehoeren, je einer mit seinen Unterabschnitten, und "Warum hier".
        """
        abschnitte = []
        for abschnitt in self.abschnitte:
            zeilen = [abschnitt.ueberschrift, *abschnitt.zeilen]
            for unter in abschnitt.unterabschnitte:
                zeilen += [unter.ueberschrift, *unter.zeilen]
            abschnitte.append("\n".join(zeilen))
        return [self.heute, *abschnitte, self.warum]

    @property
    def dauer(self) -> str | None:
        """Die Minuten aus der Zeitangabe, wie beim Kopf als Text: "47 min".

        Steht etwas anderes in der Spalte Zeit, None.
        """
        von_bis = zeitangabe(self.zeit)
        return f"{von_bis.minuten} min" if von_bis else None

    @property
    def pause_oder_umbau(self) -> bool:
        return self.name.lower().startswith(("pause", "umbau"))

    @property
    def hallenteil(self) -> str:
        """Der Hallenteil aus dem Namen, "Zuspiel, Hallenteil A". Ohne ihn leer."""
        m = HALLENTEIL.search(self.name)
        return m.group(1) if m else ""

    def gehoert_dazu(self, zu: Zuordnung) -> bool:
        """Ob ein Abschnitt mit dieser Zeitangabe und diesem Hallenteil hierher gehoert.

        Ein Programmpunkt mit "18:00" in der Spalte Zeit bekommt keinen.
        """
        if zeitangabe(self.zeit) != zu.zeitangabe:
            return False
        return not zu.hallenteil or zu.hallenteil.casefold() == self.hallenteil.casefold()


# Der Gedankenstrich zwischen Datum und Kurztitel in der `#`-Ueberschrift:
# "Training 01.10.2026 — Drei Sechser". Ein Halbgeviertstrich zaehlt nur mit
# Leerzeichen, ohne ist er eine Spanne wie 18–20.
GEDANKENSTRICH = re.compile(r"\s*—\s*|\s+–\s+")

# Die Wochentage kurz, ab Montag wie date.weekday(). Nicht aus der Locale des
# Rechners, die ist unter Windows oft englisch.
WOCHENTAGE = ("Mo", "Di", "Mi", "Do", "Fr", "Sa", "So")


@dataclass
class Kopf:
    """Die Rohdaten fuer den Kopf: die `#`-Ueberschrift und das Frontmatter.

    `gruppenname` ist der Name der Gruppe aus der Wurzeldatei, unter
    `gruppen.<gruppe>.name`. Ausserhalb eines Arbeitsordners oder ohne Namen
    dort ist er None.

    Die Angaben darunter kommen als Text ohne Markup, so wie sie im Kopf
    stehen. Fehlt ein Feld im Frontmatter oder ist es leer, ist die Angabe
    None.
    """

    titel: str
    felder: dict
    gruppenname: str | None = None

    @property
    def kurztitel(self) -> str:
        """Was in der Ueberschrift nach dem Gedankenstrich steht. Ohne ihn die ganze."""
        teile = GEDANKENSTRICH.split(self.titel, maxsplit=1)
        return teile[1] if len(teile) == 2 and teile[1] else self.titel

    @property
    def datum(self) -> str | None:
        """Wochentag und Datum aus `datum`: "Do, 01.10.2026". Was kein Datum ist, bleibt stehen."""
        wert = self.felder.get("datum")
        if wert is None:
            return None
        try:
            tag = date.fromisoformat(str(wert))
        except ValueError:
            return str(wert)
        return f"{WOCHENTAGE[tag.weekday()]}, {tag:%d.%m.%Y}"

    @property
    def gruppe(self) -> str | None:
        """Der Name der Gruppe, sonst ihr Kuerzel aus `gruppe`."""
        kuerzel = self.felder.get("gruppe")
        return self.gruppenname or (str(kuerzel) if kuerzel is not None else None)

    @property
    def teilnehmer(self) -> str | None:
        """Die Zahl aus `teilnehmer`: "18 Teilnehmer"."""
        wert = self.felder.get("teilnehmer")
        return f"{wert} Teilnehmer" if wert is not None else None

    @property
    def dauer(self) -> str | None:
        """Die Minuten aus `dauer`: "120 min". Steht dort mehr als eine Zahl, bleibt es stehen."""
        wert = self.felder.get("dauer")
        if wert is None:
            return None
        return f"{wert} min" if isinstance(wert, int) else str(wert)

    @property
    def hallenteile(self) -> str | None:
        """Die Zahl der Hallenteile aus `spielflaechen`: "1 Hallenteil", "2 Hallenteile"."""
        wert = self.felder.get("spielflaechen")
        if wert is None:
            return None
        return "1 Hallenteil" if wert == 1 else f"{wert} Hallenteile"


@dataclass
class Gliederung:
    """Der Plan, zerlegt in das, was die Leseansicht zeigt. Noch ohne jedes Markup."""

    kopf: Kopf
    programmpunkte: list[Programmpunkt]
    vorbereitung: list[Abschnitt]
    """Jeder Abschnitt, der nicht leer ist, in der Reihenfolge des Plans."""
    meldungen: list[str] = field(default_factory=list)
    """Was der Trainer auf der Konsole lesen soll, eine Zeile je Meldung."""
    nachschlagen: Abschnitt | None = None
    """`## Zum Nachschlagen`, wenn es ihn mit Text oder `###` gibt. Jede `###` ist ein Reiter."""


def _ist_zaun(zeile: str) -> bool:
    return zeile.strip().startswith("```")


def _ist_tabellenzeile(zeile: str) -> bool:
    return zeile.strip().startswith("|")


def _bloecke(zeilen: list[str]) -> Iterator[tuple[str, int, int]]:
    """Die Zeilen in Bloecken, je Block seine Art, sein Anfang und sein Ende.

    Die Art ist "code", "tabelle" oder "zeile". Ein Codeblock reicht von Zaun
    zu Zaun, beide eingeschlossen, ohne schliessenden Zaun bis zum Schluss.
    Darin ist nichts Markdown, kein `#` und kein `|`. Eine Tabelle sind
    aufeinanderfolgende Zeilen mit `|` vorn. Jede andere Zeile ist ein Block
    fuer sich. Das Ende gehoert nicht mehr zum Block.
    """
    i = 0
    while i < len(zeilen):
        anfang = i
        if _ist_zaun(zeilen[i]):
            i += 1
            while i < len(zeilen) and not _ist_zaun(zeilen[i]):
                i += 1
            i = min(i + 1, len(zeilen))
            yield "code", anfang, i
        elif _ist_tabellenzeile(zeilen[i]):
            while i < len(zeilen) and _ist_tabellenzeile(zeilen[i]):
                i += 1
            yield "tabelle", anfang, i
        else:
            i += 1
            yield "zeile", anfang, i


def zerlege(rumpf: str) -> tuple[str | None, list[Abschnitt]]:
    """Teilt den Rumpf des Plans an seinen Ueberschriften.

    Zurueck kommen der Titel aus der ersten `#`-Ueberschrift und die
    Abschnitte in der Reihenfolge des Plans. Vorn steht immer der Abschnitt
    der Stufe 1, auch wenn er leer ist, noch ohne Ueberschrift. Eine
    Ueberschrift in einem Codeblock zaehlt nicht, eine Hallenskizze darf mit
    `#` zeichnen.
    """
    titel = None
    vorab = Abschnitt(1, "")
    abschnitte = [vorab]
    oben = vorab
    ziel = vorab.zeilen
    zeilen = rumpf.splitlines()
    for art, anfang, ende in _bloecke(zeilen):
        m = re.match(r"^(#{1,3})\s+(.*)$", zeilen[anfang]) if art == "zeile" else None
        stufe = len(m.group(1)) if m else 0
        if stufe == 1 and titel is None:
            titel = m.group(2).strip()
        elif stufe == 2:
            oben = Abschnitt(2, m.group(2).strip())
            abschnitte.append(oben)
            ziel = oben.zeilen
        elif stufe == 3:
            unten = Abschnitt(3, m.group(2).strip())
            oben.unterabschnitte.append(unten)
            ziel = unten.zeilen
        else:
            ziel.extend(zeilen[anfang:ende])
    return titel, abschnitte


def _ist_trennzeile(zeile: str) -> bool:
    return set(zeile.replace("|", "").strip()) <= set("-: ")


def nimm_tabelle(zeilen: list[str]) -> list[str]:
    """Nimmt die erste Tabelle aus den Zeilen heraus und gibt sie zurueck.

    Was davor und danach steht, bleibt in `zeilen`. Ohne Tabelle eine leere
    Liste. Eine Zeile mit `|` in einem Codeblock gehoert zu keiner Tabelle.
    """
    for art, anfang, ende in _bloecke(zeilen):
        if art == "tabelle":
            tabelle = zeilen[anfang:ende]
            del zeilen[anfang:ende]
            return tabelle
    return []


def _ohne_strich(text: str) -> str:
    return "" if text in ("", "—") else text


def programmpunkte(tabelle: list[str]) -> list[Programmpunkt]:
    """Je Zeile der Ablauftabelle ein Programmpunkt, in ihrer Reihenfolge."""
    reihen = [tabellenzellen(z) for z in tabelle if not _ist_trennzeile(z)]
    if not reihen:
        return []
    kopf = [k.lower() for k in reihen[0]]
    spalte = {feld: next((kopf.index(n) for n in namen if n in kopf), None)
              for feld, namen in SPALTEN.items()}
    punkte = []
    for reihe in reihen[1:]:
        def zelle(feld: str) -> str:
            i = spalte[feld]
            return reihe[i] if i is not None and i < len(reihe) else ""
        punkte.append(Programmpunkt(
            zeit=zelle("zeit"), name=zelle("name"), uebung=zelle("uebung"),
            id=_ohne_strich(zelle("id").strip("`")),
            heute=_ohne_strich(zelle("heute")), warum=_ohne_strich(zelle("warum")),
        ))
    return punkte


def verweise(texte: list[str], reiter: list[Abschnitt]) -> list[Abschnitt]:
    """Die Reiter, auf die ein Link in diesen Texten zeigt, jeder einmal, in der Folge der Links."""
    nach_anker = {anker(r.ueberschrift): r for r in reiter}
    gefunden: list[Abschnitt] = []
    for text in texte:
        for ziel in LINK_AUF_UEBERSCHRIFT.findall(text):
            r = nach_anker.get(unquote(ziel))
            if r is not None and all(r is not g for g in gefunden):
                gefunden.append(r)
    return gefunden


def lies_karten(wurzel: Path | None) -> dict[str, Karte]:
    """Die Karten der Bibliothek nach ID. Ausserhalb eines Arbeitsordners keine."""
    if wurzel is None:
        return {}
    karten = {}
    for karte in lies_uebungen(wurzel):
        dateien = [wurzel / "schaubilder" / name for name in schaubilder(karte.get("schaubild"))]
        karten[karte["id"]] = Karte(titel=karte.get("titel") or karte["id"],
                                    quelle=karte.get("quelle") or "",
                                    schaubilder=[d for d in dateien if d.is_file()])
    return karten


def lies_gruppenname(wurzel: Path | None, kuerzel) -> str | None:
    """Der Name der Gruppe aus der Wurzeldatei. Ausserhalb eines Arbeitsordners None."""
    if wurzel is None or kuerzel is None:
        return None
    name = ((lies_gruppen(wurzel) or {}).get(str(kuerzel)) or {}).get("name")
    return str(name) if name not in (None, "") else None


def _gleich(a: str, b: str) -> bool:
    return " ".join(a.split()).casefold() == " ".join(b.split()).casefold()


def _im_programmpunkt(abschnitt: Abschnitt, punkt: Programmpunkt) -> Abschnitt:
    """Der Abschnitt, wie er im Programmpunkt steht.

    Zeitangabe und Hallenteil fallen aus der Ueberschrift, auch aus der eines
    mitgenommenen Unterabschnitts, wenn sie auf diesen Programmpunkt zeigen.
    Gleicht der Rest dem Namen der Uebung, faellt die Ueberschrift ganz weg,
    oben wie in einem Unterabschnitt.
    """
    def gekuerzt(ueberschrift: str) -> str:
        zu = zuordnung(ueberschrift)
        rest = zu.rest if zu and punkt.gehoert_dazu(zu) else ueberschrift
        return "" if _gleich(rest, punkt.uebung) else rest

    return replace(abschnitt, ueberschrift=gekuerzt(abschnitt.ueberschrift),
                   unterabschnitte=[replace(u, ueberschrift=gekuerzt(u.ueberschrift))
                                    for u in abschnitt.unterabschnitte])


def _ziele(abschnitt: Abschnitt, punkte: list[Programmpunkt]) -> list[Programmpunkt] | None:
    """Die Programmpunkte, zu denen der Abschnitt ueber seine Zeitangabe gehoert.

    None, wenn seine Ueberschrift mit keiner beginnt. Passt sie auf keinen
    Programmpunkt, eine leere Liste.
    """
    zu = zuordnung(abschnitt.ueberschrift)
    return None if zu is None else [p for p in punkte if p.gehoert_dazu(zu)]


def _meldung(abschnitt: Abschnitt) -> str:
    """Was der Trainer liest, wenn die Zeitangabe des Abschnitts auf keinen Programmpunkt passt.

    Damit findet er den Tippfehler oder die verschobene Zeit.
    """
    zu = zuordnung(abschnitt.ueberschrift)
    wo = f" in Hallenteil {zu.hallenteil}" if zu.hallenteil else ""
    return (f"Kein Programmpunkt mit der Zeitangabe {zu.zeit}{wo} für den "
            f"Abschnitt „{abschnitt.ueberschrift}“. Er steht unter Vorbereitung.")


def _ist_ziel(punkt: Programmpunkt, ziele: list[Programmpunkt] | None) -> bool:
    return any(p is punkt for p in ziele or [])


def verteile(abschnitte: list[Abschnitt],
             punkte: list[Programmpunkt]) -> tuple[list[Abschnitt], list[str]]:
    """Gibt jedem Programmpunkt die Abschnitte, deren Ueberschrift mit seiner Zeitangabe beginnt.

    Ein `###` mit eigener Zeitangabe entscheidet selbst, auch unter einem `##`
    mit Zeitangabe. Ein `###` ohne folgt seinem `##`. So steht unter
    `## 69–89 Zuspiel` jede Hallenskizze nur bei ihrem Hallenteil. Geht ein
    `###` zu einem Programmpunkt, zu dem auch sein `##` geht, steht er dort in
    ihm, sonst fuer sich.

    Zurueck kommen die Abschnitte, die bleiben, in der Reihenfolge des Plans,
    und die Meldungen. Ein `##`, der gewandert ist, bleibt nur mit den `###`,
    deren Zeitangabe auf keinen Programmpunkt passt. Die Abschnitte, die
    hereinkommen, bleiben, wie sie sind.
    """
    bleiben, meldungen = [], []
    for abschnitt in abschnitte:
        oben = _ziele(abschnitt, punkte) if abschnitt.stufe > 1 else None
        unten = [(u, _ziele(u, punkte)) for u in abschnitt.unterabschnitte]
        meldungen += [_meldung(a) for a, ziele in [(abschnitt, oben), *unten] if ziele == []]
        for punkt in oben or []:
            mit = [u for u, ziele in unten if ziele is None or _ist_ziel(punkt, ziele)]
            punkt.abschnitte.append(
                _im_programmpunkt(replace(abschnitt, unterabschnitte=mit), punkt))
        for u, ziele in unten:
            for punkt in ziele or []:
                if not _ist_ziel(punkt, oben):
                    punkt.abschnitte.append(_im_programmpunkt(u, punkt))
        if oben:
            rest = [u for u, ziele in unten if ziele == []]
            if rest:
                bleiben.append(replace(abschnitt, zeilen=[], unterabschnitte=rest))
        else:
            bleiben.append(replace(abschnitt,
                                   unterabschnitte=[u for u, ziele in unten if not ziele]))
    return bleiben, meldungen


def gliedere(plan: Path, wurzel: Path | None) -> Gliederung:
    """Zerlegt den Plan in die Gliederung der Leseansicht.

    Die erste Tabelle unter `## Ablauf` ist die Ablauftabelle. Was dort
    daneben steht, bleibt im Abschnitt Ablauf und kommt mit ihm unter
    Vorbereitung, unter der Ueberschrift "Ablauf", auch wenn der Plan etwa
    `## Ablauf (90 min)` schreibt. `## Zum Nachschlagen` steht fuer sich,
    nicht unter Vorbereitung.
    """
    felder, rumpf = lies_frontmatter(plan)
    titel, abschnitte = zerlege(rumpf)
    titel = titel or plan.stem
    abschnitte[0].ueberschrift = titel
    nachschlagen = next((a for a in abschnitte if a.ist_nachschlagen), None)
    if nachschlagen is not None:
        abschnitte.remove(nachschlagen)
        # Jede `###` ist ein Reiter, auch ohne Text, sonst fuehrte ein Verweis
        # darauf ins Leere. Ohne Text und ohne `###` gibt es nichts nachzuschlagen.
        if nachschlagen.leer and not nachschlagen.unterabschnitte:
            nachschlagen = None
    punkte = []
    for abschnitt in abschnitte:
        if abschnitt.ist_ablauf:
            punkte += programmpunkte(nimm_tabelle(abschnitt.zeilen))
            abschnitt.ueberschrift = "Ablauf"
    karten = lies_karten(wurzel)
    for punkt in punkte:
        punkt.karte = karten.get(punkt.id)
    abschnitte, meldungen = verteile(abschnitte, punkte)
    reiter =nachschlagen.unterabschnitte if nachschlagen else []
    for punkt in punkte:
        punkt.verweise = verweise(punkt.texte(), reiter)
    return Gliederung(kopf=Kopf(titel, felder, lies_gruppenname(wurzel, felder.get("gruppe"))),
                      programmpunkte=punkte,
                      vorbereitung=[a for a in abschnitte if not a.leer],
                      nachschlagen=nachschlagen,
                      meldungen=meldungen)


# --------------------------------------------------------------------------
# Das HTML
# --------------------------------------------------------------------------

# Die Farben der Vorlage, je Schema ein Satz derselben Namen. Schaubilder
# liegen auch im Dunkeln auf hellem Grund, sonst verschwinden Linien und
# Beschriftung. Darum ist auch die Schrift daneben, die Bildtinte, in beiden
# Schemata dunkel. Der helle Schleier steht im Stil noch einmal als Rueckfall
# fuer ::backdrop, dem aeltere Browser die Variablen nicht weitergeben.
HELL = {
    "papier": "#f3f6f0", "flaeche": "#e5ece0", "tinte": "#243d32", "gedaempft": "#58705e",
    "akzent": "#356548", "linie": "#c7d6c6", "heute": "#e5ece0", "heute-marke": "#243d32",
    "knopf": "transparent", "knopf-rand": "#c7d6c6", "offen": "#243d32",
    "bildgrund": "#e5ece0", "bildrand": "#c7d6c6", "bild": "transparent", "bildtinte": "#243d32",
    "schleier": "#192c2ba6", "schatten": "#1e30252b",
}
DUNKEL = {
    "papier": "#14241e", "flaeche": "#21382c", "tinte": "#e6eee3", "gedaempft": "#a9beab",
    "akzent": "#b3d5a0", "linie": "#3b5141", "heute": "#233a2b", "heute-marke": "#b3d5a0",
    "knopf": "#1a2d23", "knopf-rand": "#45604b", "offen": "#d9edca",
    "bildgrund": "#dce4d7", "bildrand": "#82997d", "bild": "#edf1e8", "bildtinte": "#243d32",
    "schleier": "#08140dd1", "schatten": "#07110ccc",
}


def farben(palette: dict[str, str], schema: str) -> str:
    """Eine Palette als CSS-Variablen, die Deklarationen einer Regel fuer `:root`."""
    return "".join(f"--{name}:{wert};" for name, wert in palette.items()) + f"color-scheme:{schema}"


CSS = (":root{" + farben(HELL, "light") + "}"
       "@media (prefers-color-scheme:dark){:root{" + farben(DUNKEL, "dark") + "}}" + """
*,*::before,*::after{box-sizing:border-box}
html{-webkit-text-size-adjust:100%}
body{margin:0;background:var(--papier);color:var(--tinte);
font:16px/1.55 "Trebuchet MS",Verdana,sans-serif}
.seite{max-width:760px;margin:auto;padding:0 20px 36px}
h1,h2,h3,p{margin:0}
a{color:var(--akzent)}
:focus-visible{outline:3px solid var(--akzent);outline-offset:3px}
summary{cursor:pointer;min-height:44px}
.kopf{padding:22px 0 16px;border-bottom:1px solid var(--linie)}
h1{font-size:24px;line-height:1.2;letter-spacing:-.5px}
.leiste{display:flex;justify-content:space-between;align-items:center;gap:12px;margin-top:12px}
.kopf .datum{font-weight:700;font-size:19px;letter-spacing:-.4px}
.kopf .angaben{color:var(--gedaempft);font-size:12px;margin-top:3px}
.umfang{margin-left:auto;text-align:right}
.minuten{font:700 15px ui-monospace,monospace}
.umfang .angaben{font-size:11px;margin-top:0}
.knoepfe{display:flex;gap:8px;flex-wrap:wrap;margin:16px 0 0}
.knoepfe a{flex:1;display:flex;align-items:center;justify-content:center;min-height:44px;
padding:10px 14px;font-size:13px;color:inherit;text-decoration:none;background:var(--knopf);
border:1px solid var(--knopf-rand);border-radius:7px}
.knoepfe a:hover{background:var(--flaeche)}
.ablauf-kopf{display:flex;justify-content:space-between;align-items:baseline;gap:12px;
margin:25px 0 12px}
.ablauf-kopf h2{font-size:29px;line-height:1.15;letter-spacing:-1px}
.ablauf-kopf span{font-size:11px;text-transform:uppercase;letter-spacing:1.3px;
color:var(--gedaempft);text-align:right}
.ablauf{border-top:2px solid var(--akzent)}
.programmpunkt{border-bottom:1px solid var(--linie)}
.programmpunkt[open]{border-left:3px solid var(--akzent);padding-left:14px;margin-left:-17px}
.programmpunkt>summary{display:grid;grid-template-columns:57px 1fr 20px;gap:12px;
padding:17px 0;align-items:center;list-style:none}
.programmpunkt>summary::-webkit-details-marker,.eintrag>summary::-webkit-details-marker{
display:none}
.programmpunkt>summary::after,.eintrag>summary::after{content:"+";font-size:23px;flex-shrink:0;
color:var(--akzent)}
.programmpunkt[open]>summary::after,.eintrag[open]>summary::after{content:"−"}
.wann{align-self:start;padding-top:3px;font:700 13px ui-monospace,monospace;
font-variant-numeric:tabular-nums}
.zeit,.dauer{display:block}
.dauer{color:var(--gedaempft);font:400 11px "Trebuchet MS",sans-serif;margin-top:3px}
.name{display:block;font-size:11px;letter-spacing:.7px;text-transform:uppercase;
color:var(--gedaempft)}
.uebung{display:block;font-size:16px;line-height:1.3;margin-top:4px}
.name:only-child{font-size:16px;letter-spacing:0;text-transform:none;color:inherit;font-weight:700}
.programmpunkt[open] .uebung,.programmpunkt[open] .name:only-child{color:var(--offen)}
.gedaempft .uebung,.gedaempft .name:only-child{font-size:14px;font-weight:400;
color:var(--gedaempft)}
.inhalt{padding:8px 0 20px;overflow-wrap:anywhere}
.heute{background:var(--heute);border-left:3px solid var(--akzent);padding:14px 16px;
margin:10px 0 22px}
.heute b{display:block;font-size:11px;letter-spacing:1px;text-transform:uppercase;
margin-bottom:6px;color:var(--heute-marke)}
.inhalt h3,.rich h3,.reiter>h3{font-size:18px;line-height:1.4;margin:24px 0 10px}
.rich h4{font-size:16px;margin:20px 0 8px}
.schaubild figure{margin:16px 0;padding:10px;background:var(--bildgrund);
border:1px solid var(--bildrand);color:var(--bildtinte);color-scheme:light}
.schaubild img{display:block;width:100%;height:auto;border-radius:4px;background:var(--bild)}
.schaubild figcaption{text-align:center;font-size:12px;margin-top:8px}
.karte{color:var(--gedaempft);font-size:12px;margin-top:3px}
.warum{margin-top:24px;border-top:1px solid var(--linie)}
.warum>summary{color:var(--gedaempft);font-size:13px;padding-top:10px}
.warum .rich p{font-size:14px;color:var(--gedaempft)}
.rich p{margin:12px 0}
.rich ul,.rich ol{padding-left:22px;margin:14px 0}
.rich li{padding-left:3px;margin:10px 0}
.rich pre{background:var(--flaeche);padding:14px;overflow:auto;
font:11px/1.5 ui-monospace,monospace;border-radius:6px}
.rich table{display:block;overflow-x:auto;border-collapse:collapse;width:100%;margin:18px 0;
font-size:13px}
.rich th,.rich td{border:1px solid var(--linie);padding:9px 11px;text-align:left;
vertical-align:top;min-width:65px}
.rich th{background:var(--flaeche)}
.rich code{font-family:ui-monospace,monospace;font-size:.85em;overflow-wrap:anywhere}
.rich hr{border:0;border-top:1px solid var(--linie);margin:28px 0}
.liste{margin:14px 0;border-top:1px solid var(--linie)}
.eintrag{border-bottom:1px solid var(--linie)}
.eintrag>summary{display:flex;gap:12px;justify-content:space-between;align-items:center;
padding:13px 0;list-style:none}
.eintrag>summary::after{font-size:22px}
.nr-uebung,.dosierung{display:block}
.nr-uebung{font-size:14px}
.dosierung{color:var(--gedaempft);font:12px ui-monospace,monospace;margin-top:4px}
.eintrag-text{padding:0 0 18px}
.eintrag-text p,.eintrag-text dl,.eintrag-text dd{margin:0}
.eintrag-text dt{font-size:11px;letter-spacing:.7px;text-transform:uppercase;
color:var(--gedaempft);margin-top:10px}
.eintrag-text dt:first-child{margin-top:0}
.vorbereitung,.nachschlagen{margin-top:40px}
.vorbereitung>h2,.nachschlagen>h2{font-size:22px;line-height:1.25;padding-bottom:8px;
border-bottom:2px solid var(--akzent)}
.abschnitt{border-bottom:1px solid var(--linie)}
.abschnitt>summary{font-weight:700;padding:12px 0}
.abschnitt>.rich{padding-bottom:16px;overflow-wrap:anywhere}
.reiterleiste,.verweise{display:flex;gap:8px;flex-wrap:wrap}
.reiterleiste{padding-top:16px;margin-bottom:20px}
.verweise{margin-top:24px}
.reiterleiste a,.verweise a,.ansicht-kopf button,.vergroessern{display:flex;align-items:center;
min-height:44px;padding:10px 14px;font:inherit;font-size:13px;color:inherit;text-decoration:none;
cursor:pointer;background:var(--knopf);border:1px solid var(--knopf-rand);border-radius:7px}
.reiterleiste a:hover,.verweise a:hover,.ansicht-kopf button:hover,.vergroessern:hover{
background:var(--flaeche)}
.verweise a::after{content:"\\2009↗"}
.reiterleiste a[aria-current]{background:var(--akzent);color:var(--papier);
border-color:var(--akzent)}
.ansicht .reiter>h3{font-size:22px;line-height:1.25;margin-top:8px}
.ansicht{padding:0;max-height:90vh;max-height:90dvh;width:calc(100% - 24px);max-width:760px;
margin:auto;background:var(--papier);color:var(--tinte);border:1px solid var(--linie);
border-radius:16px;box-shadow:0 20px 70px var(--schatten);overscroll-behavior:contain}
.ansicht::backdrop{background:var(--schleier,""" + HELL["schleier"] + """)}
.ansicht-kopf{display:flex;justify-content:space-between;align-items:center;gap:12px;
padding:18px 20px;background:var(--papier);position:sticky;top:0;z-index:2;
border-bottom:1px solid var(--linie)}
.ansicht-kopf h2{font-size:19px;line-height:1.25}
.ansicht-kopf button{flex-shrink:0}
.ansicht-inhalt{padding:4px 20px 28px;overflow-wrap:anywhere}
.ansicht-inhalt>section{margin:0}
.bildknopf{display:block;width:100%;padding:0;font:inherit;color:inherit;background:none;
border:0;cursor:zoom-in}
.bildknopf span{display:block;text-align:center;font-size:12px;margin-top:8px}
.vergroesserung .vergroessern{margin-top:16px}
.vergroesserung pre{margin:16px 0 0;padding:20px;overflow:auto;background:var(--flaeche);
border-radius:6px;font:14px/1.7 ui-monospace,monospace}
.bildflaeche{margin-top:16px;padding:10px;overflow:auto;background:var(--bildgrund);
border:1px solid var(--bildrand);border-radius:4px}
.bildflaeche img{display:block;width:100%;max-width:none;height:auto;background:var(--bild)}
.bildflaeche.doppelt img{width:200%}
@media (prefers-reduced-motion:no-preference){.ansicht[open]{animation:aufgehen .15s ease-out}}
@keyframes aufgehen{from{opacity:0;transform:translateY(12px)}to{opacity:1;transform:none}}
.fuss{font-size:11px;color:var(--gedaempft);border-top:1px solid var(--linie);
padding-top:16px;margin-top:30px}
@media (min-width:900px){.seite{padding:0 36px 48px}.kopf{padding-top:32px}}
""")

# Der Umschalter Hell, Dunkel, System. Ohne Skript bleibt er verborgen, und
# das Farbschema folgt dem Geraet wie oben. Das Skript zeigt ihn und setzt die
# Wahl als data-darstellung am Wurzelelement. Bei "system" gilt weiter die
# Media-Query, bei "hell" und "dunkel" die Palette hier, gleich wie das Geraet
# eingestellt ist.
UMSCHALTER_HTML = (
    '<fieldset class="darstellung" aria-describedby="darstellung-hinweis" hidden>'
    '<legend>Darstellung</legend><div class="wahl">'
    + "".join(f'<label><input type="radio" name="darstellung" value="{wert}" autocomplete="off"'
              f'{" checked" if wert == "system" else ""}><span>{name}</span></label>'
              for wert, name in (("hell", "Hell"), ("dunkel", "Dunkel"), ("system", "System")))
    + '</div><p class="hinweis" id="darstellung-hinweis"></p></fieldset>')

UMSCHALTER_CSS = (":root[data-darstellung=hell]{" + farben(HELL, "light") + "}"
                  ":root[data-darstellung=dunkel]{" + farben(DUNKEL, "dark") + "}" + """
.darstellung{margin:16px 0 0;border:0;padding:0;min-width:0}
.darstellung legend{padding:0;margin-bottom:7px;font-size:11px;letter-spacing:.7px;
text-transform:uppercase;color:var(--gedaempft)}
.darstellung .wahl{display:flex;gap:3px;padding:3px;background:var(--papier);
border:1px solid var(--linie);border-radius:7px}
.darstellung label{flex:1;display:flex;position:relative;cursor:pointer;font-size:13px}
.darstellung input{position:absolute;opacity:0;width:1px;height:1px;margin:0}
.darstellung span{flex:1;display:flex;align-items:center;justify-content:center;
min-height:44px;border-radius:4px}
.darstellung input:checked+span{background:var(--flaeche);color:var(--akzent);font-weight:700}
.darstellung input:focus-visible+span{outline:3px solid var(--akzent);outline-offset:2px}
.darstellung .hinweis{margin-top:5px;font-size:11px;color:var(--gedaempft)}
""")

# Steht im Kopf der Seite, damit eine gemerkte Wahl gilt, bevor etwas zu sehen
# ist. Den Umschalter zeigt es erst, wenn alles andere geklappt hat. Ohne
# Speicher gilt die Wahl fuer diesen Besuch. Kommt die Wahl aus einem anderen
# Tab, wird sie uebernommen.
UMSCHALTER_SKRIPT = """(function () {
  var schluessel = "volleyball-leseansicht-darstellung";
  var geraet = window.matchMedia && window.matchMedia("(prefers-color-scheme: dark)");
  var wahl = gemerkt();

  function gemerkt() {
    try {
      var wert = window.localStorage.getItem(schluessel);
      if (wert === "hell" || wert === "dunkel" || wert === "system") return wert;
    } catch (e) { /* kein Speicher, etwa bei einer lokalen Datei */ }
    return "system";
  }

  function zeige() {
    document.documentElement.setAttribute("data-darstellung", wahl);
    var feld = document.querySelector(".darstellung");
    if (!feld) return;
    feld.querySelector('input[value="' + wahl + '"]').checked = true;
    feld.querySelector(".hinweis").textContent = wahl !== "system" ? "Manuell gewählt"
      : "Folgt deiner Geräteeinstellung · " + (geraet && geraet.matches ? "dunkel" : "hell");
    feld.hidden = false;
  }

  zeige();
  document.addEventListener("DOMContentLoaded", function () {
    zeige();
    document.querySelector(".darstellung").addEventListener("change", function (ereignis) {
      wahl = ereignis.target.value;
      try { window.localStorage.setItem(schluessel, wahl); }
      catch (e) { /* dann gilt sie fuer diesen Besuch */ }
      zeige();
    });
  });
  if (geraet && geraet.addEventListener) geraet.addEventListener("change", zeige);
  else if (geraet && geraet.addListener) geraet.addListener(zeige);
  window.addEventListener("storage", function (ereignis) {
    if (ereignis.key === schluessel || ereignis.key === null) {
      wahl = gemerkt();
      zeige();
    }
  });
})();"""

# Die Ansichten (#56). Ohne Skript, oder wo der Browser kein <dialog> kennt,
# stehen Nachschlagen und Vorbereitung am Ende der Seite, und Knoepfe und
# Verweise springen dorthin. Mit Skript wird jeder Abschnitt mit
# data-zurueck eine Ansicht: ein <dialog>, der sich mit dem Zurueck-Knopf,
# einem Tipp daneben und, wo der Browser es weitergibt, mit Escape oder der
# Zurueck-Geste schliesst. Ein Link auf etwas darin oeffnet die Ansicht,
# ein Link auf einen Reiter zeigt ihn. Der Ablauf bleibt dabei, wie
# er ist, offene Programmpunkte bleiben offen.
#
# `ansicht(titel, zurueck)` baut eine leere Ansicht. Was sie zeigt, kommt in
# ihr Feld .ansicht-inhalt, hier ein Abschnitt der Seite, beim Vergroessern
# eine Hallenskizze in groesserer Schrift oder ein Schaubild in voller
# Breite, das sich auf doppelte Breite stellen laesst. Die Knoepfe dazu
# entstehen erst hier. Ohne Skript stehen Skizze und Bild im Programmpunkt,
# und der Browser zoomt wie gewohnt.
ANSICHTEN_SKRIPT = """
(function () {
  "use strict";
  if (typeof HTMLDialogElement !== "function"
      || typeof HTMLDialogElement.prototype.showModal !== "function") return;

  // Ein Knopf tut nur mit Skript etwas, darum entsteht jeder erst hier.
  function knopf(klasse, text, beiKlick) {
    var k = document.createElement("button");
    k.type = "button";
    if (klasse) k.className = klasse;
    k.textContent = text;
    k.addEventListener("click", beiKlick);
    return k;
  }

  function ansicht(titel, zurueck) {
    var dialog = document.createElement("dialog");
    dialog.className = "ansicht";
    dialog.setAttribute("aria-label", titel.textContent);
    var kopf = document.createElement("div");
    kopf.className = "ansicht-kopf";
    kopf.append(titel, knopf("", zurueck, function () { dialog.close(); }));
    var inhalt = document.createElement("div");
    inhalt.className = "ansicht-inhalt";
    dialog.append(kopf, inhalt);
    dialog.addEventListener("click", function (e) {
      if (e.target !== dialog) return;
      var r = dialog.getBoundingClientRect();
      if (e.clientX < r.left || e.clientX > r.right
          || e.clientY < r.top || e.clientY > r.bottom) dialog.close();
    });
    return dialog;
  }

  function oeffne(dialog) {
    if (!dialog.open) dialog.showModal();
    dialog.scrollTop = 0;
  }

  // Das Element, zu dem ein Link springt, so wie der Browser es sucht.
  function sprungziel(link) {
    var anker = link.getAttribute("href").slice(1);
    var ziel = document.getElementById(anker);
    if (!ziel) {
      try { ziel = document.getElementById(decodeURIComponent(anker)); } catch (e) {}
    }
    return ziel;
  }

  // Zeigt von den Reitern seines Abschnitts nur diesen.
  function zeigeReiter(reiter) {
    if (!reiter) return;
    var abschnitt = reiter.parentNode;
    abschnitt.querySelectorAll(":scope > .reiter").forEach(function (r) {
      r.hidden = r !== reiter;
    });
    abschnitt.querySelectorAll(".reiterleiste a").forEach(function (a) {
      if (sprungziel(a) === reiter) a.setAttribute("aria-current", "true");
      else a.removeAttribute("aria-current");
    });
  }

  document.querySelectorAll("section[data-zurueck]").forEach(function (abschnitt) {
    var dialog = ansicht(abschnitt.querySelector(":scope > h2"),
                         abschnitt.getAttribute("data-zurueck"));
    abschnitt.before(dialog);
    dialog.querySelector(".ansicht-inhalt").append(abschnitt);
    zeigeReiter(abschnitt.querySelector(":scope > .reiter"));
  });

  document.addEventListener("click", function (e) {
    var link = e.target.closest('a[href^="#"]');
    var ziel = link && sprungziel(link);
    var dialog = ziel && ziel.closest("dialog.ansicht");
    if (!dialog) return;
    e.preventDefault();
    zeigeReiter(ziel.closest(".reiter") || dialog.querySelector(".reiter"));
    oeffne(dialog);
  });

  // Vergroessern (#57). Die Ansicht entsteht beim Oeffnen und verschwindet
  // beim Schliessen wieder.
  function vergroessere(titel, inhalt) {
    var kopf = document.createElement("h2");
    kopf.textContent = titel;
    var dialog = ansicht(kopf, "Zurück");
    dialog.classList.add("vergroesserung");
    inhalt.forEach(function (stueck) { dialog.querySelector(".ansicht-inhalt").append(stueck); });
    dialog.addEventListener("close", function () { dialog.remove(); });
    document.body.append(dialog);
    oeffne(dialog);
  }

  // Unter jedem Codeblock im Ablauf, also jeder Hallenskizze, ein Knopf.
  document.querySelectorAll(".programmpunkt pre").forEach(function (skizze) {
    skizze.after(knopf("vergroessern", "Skizze vergrößern", function () {
      var gross = document.createElement("pre");
      gross.textContent = skizze.textContent;
      vergroessere("Hallenskizze", [gross]);
    }));
  });

  // Jedes Schaubild der Karte wird selbst ein Knopf. Die Ansicht nimmt das
  // Bild beim Oeffnen von ihm, eingebettet steht es nur einmal in der Datei.
  document.querySelectorAll(".programmpunkt .schaubild img").forEach(function (bild) {
    var k = knopf("bildknopf", "", function () {
      var flaeche = document.createElement("div");
      flaeche.className = "bildflaeche";
      var gross = document.createElement("img");
      gross.src = bild.src;
      gross.alt = bild.alt;
      flaeche.append(gross);
      var breite = knopf("vergroessern", "2× vergrößern", function () {
        var doppelt = flaeche.classList.toggle("doppelt");
        breite.textContent = doppelt ? "Gesamtansicht" : "2× vergrößern";
      });
      vergroessere(bild.alt, [breite, flaeche]);
    });
    k.setAttribute("aria-label", bild.alt + ", vergrößern");
    var hinweis = document.createElement("span");
    hinweis.textContent = "Schaubild vergrößern ↗";
    bild.before(k);
    k.append(bild, hinweis);
  });
})();
"""


def baue_adresse(ziel: Path, modus: str):
    """Gibt eine Funktion Bilddatei -> Adresse im HTML zurueck, bei `aus` None."""
    if modus == "aus":
        return None

    def adresse(datei: Path) -> str:
        if modus == "einbetten":
            typ = mimetypes.guess_type(datei.name)[0] or "image/png"
            roh = base64.b64encode(datei.read_bytes()).decode("ascii")
            return f"data:{typ};base64,{roh}"
        return Path(os.path.relpath(datei, ziel.parent)).as_posix()

    return adresse


def inline(t: str) -> str:
    t = html.escape(t)
    t = re.sub(r"`([^`]+)`", r"<code>\1</code>", t)
    t = re.sub(r"\*\*([^*]+)\*\*", r"<strong>\1</strong>", t)
    t = re.sub(r"(?<!\*)\*([^*]+)\*(?!\*)", r"<em>\1</em>", t)
    t = re.sub(r"\[([^\]]+)\]\(([^)]+)\)", r'<a href="\2">\1</a>', t)
    return t.replace("&lt;br&gt;", "<br>")


def ist_liste_zum_aufklappen(tabelle: list[str]) -> bool:
    """Ob die ersten beiden Spalten der Tabelle `Nr` und `Übung` heissen."""
    kopf = [k.lower() for k in tabellenzellen(tabelle[0])]
    return len(kopf) >= 2 and kopf[0] == "nr" and kopf[1] in SPALTEN["uebung"]


def liste_html(tabelle: list[str]) -> str:
    """Eine Tabelle mit `Nr | Übung` als Liste zum Aufklappen, je Zeile ein Eintrag.

    Vier Spalten sind auf dem Handy unlesbar, darum steht zugeklappt nur
    "Nr. Übung" und darunter die Spalte `Heute`, die Dosierung dieses Abends.
    Die uebrigen Spalten stehen im aufgeklappten Eintrag, eine einzelne ohne
    Beschriftung, mehrere jeweils unter ihrer Spaltenueberschrift.
    """
    kopf, *reihen = [tabellenzellen(z) for z in tabelle if not _ist_trennzeile(z)]
    namen = [k.lower() for k in kopf]
    heute = namen.index("heute") if "heute" in namen else None
    uebrige = [i for i in range(2, len(kopf)) if i != heute]
    eintraege = []
    for reihe in reihen:
        reihe += [""] * (len(kopf) - len(reihe))
        dosierung = (f' <span class="dosierung">{inline(reihe[heute])}</span>'
                     if heute is not None and reihe[heute] else "")
        if len(uebrige) <= 1:
            text = "".join(f"<p>{inline(reihe[i])}</p>" for i in uebrige if reihe[i])
        else:
            text = "<dl>" + "".join(f"<dt>{inline(kopf[i])}</dt><dd>{inline(reihe[i])}</dd>"
                                    for i in uebrige if reihe[i]) + "</dl>"
        eintraege.append(
            f'<details class="eintrag"><summary><span>'
            f'<span class="nr-uebung">{inline(reihe[0])}. {inline(reihe[1])}</span>{dosierung}'
            f'</span></summary><div class="eintrag-text">{text}</div></details>')
    return '<div class="liste">\n' + "\n".join(eintraege) + "\n</div>"


def tabelle_html(tabelle: list[str]) -> str:
    """Eine Tabelle aus dem Plan. Beginnt sie mit `Nr | Übung`, eine Liste zum Aufklappen."""
    if ist_liste_zum_aufklappen(tabelle):
        return liste_html(tabelle)
    reihen = []
    for n, zeile in enumerate(tabelle):
        if not _ist_trennzeile(zeile):
            tag = "th" if n == 0 else "td"
            reihen.append("<tr>" + "".join(f"<{tag}>{inline(f)}</{tag}>"
                                           for f in tabellenzellen(zeile)) + "</tr>")
    return "\n".join(["<table>", *reihen, "</table>"])


def nach_html(zeilen: list[str]) -> str:
    """Das Markdown eines Abschnitts als HTML.

    Der Umfang ist der der frueheren Leseansicht: Absaetze, Listen, Tabellen,
    Codebloecke, Trennlinien, dazu fett, kursiv, Code und Links im Text.
    `##` und `###` sind hier schon herausgeloest, eine tiefere Ueberschrift
    wird eine kleine.
    """
    raus = []
    liste = None

    def liste_zu():
        nonlocal liste
        if liste:
            raus.append(f"</{liste}>")
            liste = None

    for art, anfang, ende in _bloecke(zeilen):
        if art == "code":
            liste_zu()
            code = zeilen[anfang + 1:ende]
            if code and ende - anfang > 1 and _ist_zaun(code[-1]):
                code = code[:-1]
            raus.append("<pre>" + html.escape("\n".join(code)) + "</pre>")
            continue

        if art == "tabelle":
            liste_zu()
            raus.append(tabelle_html(zeilen[anfang:ende]))
            continue

        z = zeilen[anfang]
        m = re.match(r"^#{1,4}\s+(.*)$", z)
        if m:
            liste_zu()
            raus.append(f"<h4>{inline(m.group(1).strip())}</h4>")
            continue

        m = re.match(r"^\s*[-*]\s+(.*)$", z)
        if m:
            if liste != "ul":
                liste_zu()
                raus.append("<ul>")
                liste = "ul"
            raus.append(f"<li>{inline(m.group(1))}</li>")
            continue

        m = re.match(r"^\s*(\d+)\.\s+(.*)$", z)
        if m:
            if liste != "ol":
                liste_zu()
                raus.append("<ol>")
                liste = "ol"
            raus.append(f"<li>{inline(m.group(2))}</li>")
            continue

        if z.strip() in ("---", "___"):
            liste_zu()
            raus.append("<hr>")
            continue

        if z.strip():
            liste_zu()
            raus.append(f"<p>{inline(z.strip())}</p>")

    liste_zu()
    return "\n".join(raus)


def abschnitt_html(abschnitt: Abschnitt, unter_tag: str = "h3") -> str:
    """Der Text eines Abschnitts, seine Unterabschnitte mit ihrer Ueberschrift darin.

    Ist die Ueberschrift eines Unterabschnitts weggefallen, steht sein Text ohne sie.
    """
    teile = [nach_html(abschnitt.zeilen)]
    for unter in abschnitt.unterabschnitte:
        if unter.ueberschrift:
            teile.append(f"<{unter_tag}>{inline(unter.ueberschrift)}</{unter_tag}>")
        teile.append(nach_html(unter.zeilen))
    return "\n".join(t for t in teile if t)


def planabschnitt_html(abschnitt: Abschnitt) -> str:
    """Ein Abschnitt im Programmpunkt. Ist seine Ueberschrift weggefallen, ohne sie.

    Die Ueberschrift steht eine Stufe tiefer als die des Programmpunkts, die
    seiner Unterabschnitte noch eine darunter.
    """
    kopf = f"<h3>{inline(abschnitt.ueberschrift)}</h3>" if abschnitt.ueberschrift else ""
    return (f'<section class="planabschnitt">{kopf}<div class="rich">\n'
            f"{abschnitt_html(abschnitt, 'h4')}\n</div></section>")


def vorbereitung_html(abschnitte: list[Abschnitt]) -> str:
    if not abschnitte:
        return ""
    return ('<section class="vorbereitung" id="vorbereitung" data-zurueck="Zurück zum Ablauf">'
            '<h2>Vorbereitung</h2>\n'
            + "\n".join(f'<details class="abschnitt"><summary>{inline(a.ueberschrift)}</summary>'
                        f'<div class="rich">\n{abschnitt_html(a)}\n</div></details>'
                        for a in abschnitte)
            + "\n</section>")


def link_auf_reiter(reiter: Abschnitt) -> str:
    """Ohne Skript ein Sprung zum Reiter am Ende der Seite, mit Skript oeffnet er ihn."""
    return f'<a href="#{html.escape(anker(reiter.ueberschrift))}">{inline(reiter.ueberschrift)}</a>'


def nachschlagen_html(abschnitt: Abschnitt | None) -> str:
    """Zum Nachschlagen, ein Reiter je `###`, der Text davor ueber den Reitern.

    Ohne Skript stehen die Reiter untereinander, und die Leiste darueber
    springt zu jedem. Mit Skript zeigt die Ansicht einen Reiter auf einmal.
    """
    if abschnitt is None:
        return ""
    teile = ['<section class="nachschlagen" id="nachschlagen" data-zurueck="Zurück zur Übung">'
             '<h2>Nachschlagen</h2>']
    vorweg = nach_html(abschnitt.zeilen)
    if vorweg:
        teile.append(f'<div class="rich vorweg">\n{vorweg}\n</div>')
    reiter = abschnitt.unterabschnitte
    if reiter:
        teile.append('<nav class="reiterleiste" aria-label="Themen">'
                     + "".join(map(link_auf_reiter, reiter)) + "</nav>")
    teile += [f'<section class="reiter" id="{html.escape(anker(r.ueberschrift))}">'
              f'<h3>{inline(r.ueberschrift)}</h3>'
              f'<div class="rich">\n{nach_html(r.zeilen)}\n</div></section>' for r in reiter]
    return "\n".join(teile) + "\n</section>"


def karte_html(punkt: Programmpunkt, adresse) -> list[str]:
    """Das Schaubild der Karte und darunter ihre Quelle und ID.

    Ohne Bild bleiben Quelle und ID, damit man die Karte findet.
    """
    if not punkt.id:
        return []
    karte = punkt.karte
    teile = []
    bilder = karte.schaubilder if karte and adresse else []
    if bilder:
        figuren = []
        for nr, datei in enumerate(bilder, 1):
            zaehler = f"Schaubild {nr} von {len(bilder)}" if len(bilder) > 1 else ""
            alt = html.escape(f"{zaehler or 'Schaubild'}: {karte.titel}")
            unterschrift = f"<figcaption>{zaehler}</figcaption>" if zaehler else ""
            figuren.append(f'<figure><img src="{html.escape(adresse(datei))}" alt="{alt}" '
                           f'loading="lazy">{unterschrift}</figure>')
        teile.append('<section class="schaubild"><h3>Schaubild der Karte</h3>'
                     + "".join(figuren) + "</section>")
    quelle = (f'<span class="quelle">{html.escape(karte.quelle)}</span> · '
              if karte and karte.quelle else "")
    teile.append(f'<p class="karte">{quelle}<span class="id">{html.escape(punkt.id)}</span></p>')
    return teile


def programmpunkt_html(punkt: Programmpunkt, adresse) -> str:
    wann = [f'<span class="zeit">{inline(punkt.zeit)}</span>'] if punkt.zeit else []
    if punkt.dauer is not None:
        wann.append(f'<span class="dauer">{punkt.dauer}</span>')
    was = [f'<span class="name">{inline(punkt.name)}</span>'] if punkt.name else []
    if punkt.uebung:
        was.append(f'<strong class="uebung">{inline(punkt.uebung)}</strong>')
    inhalt = []
    if punkt.heute:
        inhalt.append(f'<div class="heute"><b>Heute</b><p>{inline(punkt.heute)}</p></div>')
    inhalt += [planabschnitt_html(a) for a in punkt.abschnitte]
    inhalt += karte_html(punkt, adresse)
    if punkt.verweise:
        inhalt.append('<nav class="verweise" aria-label="Nachschlagen">'
                      + "".join(map(link_auf_reiter, punkt.verweise)) + "</nav>")
    if punkt.warum:
        inhalt.append('<details class="warum"><summary>Warum hier?</summary>'
                      f'<div class="rich"><p>{inline(punkt.warum)}</p></div></details>')
    klassen = "programmpunkt gedaempft" if punkt.pause_oder_umbau else "programmpunkt"
    # Zu sehen ist der Hallenteil im Namen. Das Attribut sagt, welchen der
    # Generator dort gefunden hat.
    hallenteil = (f' data-hallenteil="{html.escape(punkt.hallenteil)}"'
                  if punkt.hallenteil else "")
    return (f'<details class="{klassen}"{hallenteil}>'
            f'<summary><span class="wann">{"".join(wann)}</span>'
            f'<span class="was">{"".join(was)}</span></summary>\n'
            f'<div class="inhalt">\n' + "\n".join(inhalt) + "\n</div></details>")


def kopf_html(kopf: Kopf) -> str:
    """Der Kurztitel, darunter wie in der Vorlage links Datum, Gruppe und
    Teilnehmer, rechts Dauer und Hallenteile.

    Jede Zeile traegt nur die Angaben, die es gibt, und nur zwischen ihnen
    steht ein Trennzeichen. Eine Zeile ohne Angabe faellt weg, eine Seite
    ohne Zeile auch.
    """
    def zeile(klasse: str, *angaben: str | None) -> str:
        da = [f'<span class="angabe">{html.escape(a)}</span>' for a in angaben if a]
        return f'<p class="{klasse}">{" · ".join(da)}</p>' if da else ""

    def seite(klasse: str, *zeilen: str) -> str:
        inhalt = "".join(zeilen)
        return f'<div class="{klasse}">{inhalt}</div>' if inhalt else ""

    leiste = (seite("wer", zeile("datum", kopf.datum),
                    zeile("angaben", kopf.gruppe, kopf.teilnehmer))
              + seite("umfang", zeile("minuten", kopf.dauer), zeile("angaben", kopf.hallenteile)))
    return (f'<header class="kopf"><h1>{html.escape(kopf.kurztitel)}</h1>'
            + (f'<div class="leiste">{leiste}</div>' if leiste else "") + "</header>")


def schreibe(gliederung: Gliederung, adresse, quelle: str, erzeugt: str) -> str:
    """Die Leseansicht als HTML. `adresse` kommt aus baue_adresse."""
    punkte = "\n".join(programmpunkt_html(p, adresse) for p in gliederung.programmpunkte)
    zahl = len(gliederung.programmpunkte)
    zahl = f"{zahl} Programmpunkt" if zahl == 1 else f"{zahl} Programmpunkte"
    # Ohne JavaScript ein Sprung ans Ende der Seite, mit Skript oeffnet der
    # Knopf eine Ansicht. Einen Knopf ohne Ziel gibt es nicht.
    knoepfe = "".join(f'<a href="#{ziel}">{name}</a>' for ziel, name, da in (
        ("nachschlagen", "Nachschlagen", gliederung.nachschlagen),
        ("vorbereitung", "Vorbereitung", gliederung.vorbereitung)) if da)
    if knoepfe:
        knoepfe = f'<nav class="knoepfe" aria-label="Trainingsunterlagen">{knoepfe}</nav>'
    return f"""<!DOCTYPE html>
<html lang="de"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<meta name="color-scheme" content="light dark">
<title>{html.escape(gliederung.kopf.titel)}</title><style>{CSS}{UMSCHALTER_CSS}</style>
<script>{UMSCHALTER_SKRIPT}</script></head><body>
<main class="seite">
{kopf_html(gliederung.kopf)}
{UMSCHALTER_HTML}
{knoepfe}
<div class="ablauf-kopf"><h2>Ablauf</h2><span>{zahl} · Minuten ab Beginn</span></div>
<div class="ablauf">
{punkte}
</div>
{nachschlagen_html(gliederung.nachschlagen)}
{vorbereitung_html(gliederung.vorbereitung)}
<div class="fuss">Leseansicht, erzeugt am {erzeugt} aus <code>{html.escape(quelle)}</code>.<br>
Änderungen gehören in die Markdown-Datei, hier gehen sie beim nächsten Erzeugen verloren.</div>
</main>
<script>{ANSICHTEN_SKRIPT}</script>
</body></html>"""


def main() -> int:
    konsole_vorbereiten()
    ap = argparse.ArgumentParser(description="Leseansicht eines Trainingsplans erzeugen")
    ap.add_argument("plan", type=Path, help="Pfad zur Trainings-.md")
    ap.add_argument("--out", type=Path, default=None)
    ap.add_argument("--bilder", choices=["einbetten", "verweis", "aus"],
                    default="einbetten",
                    help="Schaubilder der Uebungen einbetten (Standard, die HTML "
                         "laeuft dann allein), als relativen Verweis setzen, oder "
                         "weglassen")
    a = ap.parse_args()

    plan = a.plan.resolve()
    if not plan.is_file():
        raise SystemExit(f"Nicht gefunden: {plan}")

    ziel = a.out or plan.with_suffix(".html")
    try:
        wurzel = finde_wurzel(plan.parent)
    except SystemExit:
        # Leseansicht soll auch fuer eine .md ausserhalb der Bibliothek laufen,
        # dann eben ohne Schaubilder.
        wurzel = None

    gliederung = gliedere(plan, wurzel)
    erzeugt = datetime.now().strftime("%d.%m.%Y %H:%M")
    seite = schreibe(gliederung, baue_adresse(ziel, a.bilder), plan.name, erzeugt)
    try:
        ziel.write_text(seite, encoding="utf-8")
        gesperrt = False
    except PermissionError:
        gesperrt = True
    if not gesperrt:
        print(f"Leseansicht: {ziel}")
    # Die Meldungen gelten dem Plan, nicht der Datei. Sie kommen auch, wenn
    # die Datei gesperrt ist, und vor deren Meldung.
    for meldung in gliederung.meldungen:
        print(meldung)
    if gesperrt:
        # Die Rechte der Datei fasst das Skript nicht an (#75). Geoeffnet wird
        # sie erst, wenn das HTML fertig ist, eine alte bleibt also unberuehrt.
        sys.stdout.flush()
        print(f"Leseansicht nicht geschrieben: {ziel}\n"
              "Die Datei ist gesperrt oder schreibgeschützt. Häufige Ursache: Der "
              "Nextcloud-Client hat sie gesperrt, weil sie auf dem Server kein "
              "Schreibrecht hat. Eine Leseansicht, die dort schon liegt, bleibt, "
              "wie sie war, ohne die Änderungen im Plan.", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
