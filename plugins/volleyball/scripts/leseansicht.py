#!/usr/bin/env python3
"""Macht aus einem Trainingsplan die Leseansicht fuers Handy.

    <python> leseansicht.py trainings/h1-h2/2026-09-15.md

Erzeugt die .html neben der .md, eine einzige Datei, die auch ohne
JavaScript lesbar ist. Die Ablauftabelle wird dabei bewusst NICHT als Tabelle
gezeigt: sechs Spalten sind auf einem Handy in der Halle unlesbar. Jede Zeile
wird ein Programmpunkt, der zugeklappt Zeitangabe, Dauer, Name und Uebung
zeigt und sich mit dem Daumen aufklappen laesst. `## Zum Nachschlagen` steht
am Ende fuer sich, jede `###` darin ein Reiter. Alle anderen Abschnitte des
Plans stehen am Ende unter Vorbereitung. Ein kurzes eingebettetes Skript
macht aus Nachschlagen und Vorbereitung Ansichten, die sich ueber dem Ablauf
oeffnen. Gestaltet ist die Seite nach der Vorlage unter
docs/gestaltung/leseansicht/, hell oder dunkel nach dem Geraet (ADR-0012).

Erzeugt wird in zwei Schritten. `gliedere` zerlegt den Plan in eine
Gliederung: die Rohdaten fuer den Kopf, die Programmpunkte, die Vorbereitung
und die Meldungen. `schreibe` macht daraus das HTML. Die Gestaltung steckt nur
im zweiten Schritt.

Hat eine Uebung im Ablauf ein Schaubild auf ihrer Karte, steht es bei ihr,
bei einer Liste alle in ihrer Reihenfolge. Standardmaessig als Data-URI
eingebettet, damit die Datei allein lauffaehig ist und auch dann noch Bilder
zeigt, wenn man sie sich aufs Handy schickt. Das macht sie gross. Wer sie
klein braucht, nimmt --bilder verweis, dann steht ein relativer Pfad nach
schaubilder/ drin.

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
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from urllib.parse import unquote

sys.path.insert(0, str(Path(__file__).resolve().parent))
from tpdaten import (  # noqa: E402
    finde_wurzel, konsole_vorbereiten, lies_frontmatter, lies_uebungen, schaubilder,
)

# --------------------------------------------------------------------------
# Die Gliederung
# --------------------------------------------------------------------------

# Eine Zeitangabe: von-bis in ganzen Minuten ab Beginn, mit Halbgeviertstrich
# oder Bindestrich, so wie in der Spalte Zeit (Glossar).
ZEITANGABE = re.compile(r"(\d+)\s*[–-]\s*(\d+)")

# Ein Markdown-Link auf eine Stelle im Plan: [Text](#anker).
LINK_AUF_STELLE = re.compile(r"\[[^\]]+\]\(#([^)\s]+)\)")

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
    in der .md und in der Leseansicht zur selben Stelle.
    """
    return re.sub(r"[^\w\- ]", "", ueberschrift.strip().lower()).replace(" ", "-")


def zeitangabe(text: str) -> tuple[int, int] | None:
    """Von und bis, wenn der Text eine Zeitangabe ist, sonst None."""
    m = ZEITANGABE.fullmatch(text.strip())
    if not m:
        return None
    von, bis = int(m.group(1)), int(m.group(2))
    return (von, bis) if von < bis else None


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
    """

    zeit: str
    name: str
    uebung: str
    id: str
    heute: str
    warum: str
    karte: Karte | None = None
    verweise: list[Abschnitt] = field(default_factory=list)
    """Die Reiter unter Nachschlagen, auf die der Programmpunkt verweist, jeder einmal."""

    def texte(self) -> list[str]:
        """Was der Plan zu diesem Programmpunkt schreibt, in der Folge der Leseansicht.

        Aus diesen Texten kommen seine Verweise: "Heute", die Abschnitte, die
        ihm gehoeren, und "Warum hier".
        """
        return [self.heute, self.warum]

    @property
    def dauer(self) -> int | None:
        """Die Minuten aus der Zeitangabe. Steht etwas anderes in der Spalte Zeit, None."""
        von_bis = zeitangabe(self.zeit)
        return von_bis[1] - von_bis[0] if von_bis else None

    @property
    def pause_oder_umbau(self) -> bool:
        return self.name.lower().startswith(("pause", "umbau"))


@dataclass
class Kopf:
    """Die Rohdaten fuer den Kopf: die `#`-Ueberschrift und das Frontmatter."""

    titel: str
    felder: dict


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
    """`## Zum Nachschlagen`, wenn es ihn gibt und er nicht leer ist. Die `###` sind die Reiter."""


def _ist_zaun(zeile: str) -> bool:
    return zeile.strip().startswith("```")


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
    im_code = False
    for zeile in rumpf.splitlines():
        if _ist_zaun(zeile):
            im_code = not im_code
        elif not im_code:
            m = re.match(r"^(#{1,3})\s+(.*)$", zeile)
            stufe = len(m.group(1)) if m else 0
            if stufe == 1 and titel is None:
                titel = m.group(2).strip()
                continue
            if stufe == 2:
                oben = Abschnitt(2, m.group(2).strip())
                abschnitte.append(oben)
                ziel = oben.zeilen
                continue
            if stufe == 3:
                unten = Abschnitt(3, m.group(2).strip())
                oben.unterabschnitte.append(unten)
                ziel = unten.zeilen
                continue
        ziel.append(zeile)
    return titel, abschnitte


def _ist_trennzeile(zeile: str) -> bool:
    return set(zeile.replace("|", "").strip()) <= set("-: ")


def _zellen(zeile: str) -> list[str]:
    return [z.strip() for z in zeile.strip().strip("|").split("|")]


def nimm_tabelle(zeilen: list[str]) -> list[str]:
    """Nimmt die erste Tabelle aus den Zeilen heraus und gibt sie zurueck.

    Was davor und danach steht, bleibt in `zeilen`. Ohne Tabelle eine leere
    Liste. Eine Zeile mit `|` in einem Codeblock gehoert zu keiner Tabelle.
    """
    im_code = False
    for anfang, zeile in enumerate(zeilen):
        if _ist_zaun(zeile):
            im_code = not im_code
        elif not im_code and zeile.strip().startswith("|"):
            ende = anfang
            while ende < len(zeilen) and zeilen[ende].strip().startswith("|"):
                ende += 1
            tabelle = zeilen[anfang:ende]
            del zeilen[anfang:ende]
            return tabelle
    return []


def _ohne_strich(text: str) -> str:
    return "" if text in ("", "—") else text


def programmpunkte(tabelle: list[str]) -> list[Programmpunkt]:
    """Je Zeile der Ablauftabelle ein Programmpunkt, in ihrer Reihenfolge."""
    reihen = [_zellen(z) for z in tabelle if not _ist_trennzeile(z)]
    if not reihen:
        return []
    kopf = [k.lower() for k in reihen[0]]
    stelle = {feld: next((kopf.index(n) for n in namen if n in kopf), None)
              for feld, namen in SPALTEN.items()}
    punkte = []
    for reihe in reihen[1:]:
        def zelle(feld: str) -> str:
            i = stelle[feld]
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
        for ziel in LINK_AUF_STELLE.findall(text):
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


def gliedere(plan: Path, wurzel: Path | None) -> Gliederung:
    """Zerlegt den Plan in die Gliederung der Leseansicht.

    Die erste Tabelle unter `## Ablauf` ist die Ablauftabelle. Was dort
    daneben steht, bleibt im Abschnitt Ablauf und kommt mit ihm unter
    Vorbereitung. `## Zum Nachschlagen` steht fuer sich, nicht unter
    Vorbereitung.
    """
    felder, rumpf = lies_frontmatter(plan)
    titel, abschnitte = zerlege(rumpf)
    titel = titel or plan.stem
    abschnitte[0].ueberschrift = titel
    nachschlagen = next((a for a in abschnitte if a.ist_nachschlagen), None)
    if nachschlagen is not None:
        abschnitte.remove(nachschlagen)
        nachschlagen.unterabschnitte = [r for r in nachschlagen.unterabschnitte if not r.leer]
    punkte = []
    for abschnitt in abschnitte:
        if abschnitt.ist_ablauf:
            punkte += programmpunkte(nimm_tabelle(abschnitt.zeilen))
    karten = lies_karten(wurzel)
    for punkt in punkte:
        punkt.karte = karten.get(punkt.id)
    if nachschlagen is not None and nachschlagen.leer:
        nachschlagen = None
    reiter = nachschlagen.unterabschnitte if nachschlagen else []
    for punkt in punkte:
        punkt.verweise = verweise(punkt.texte(), reiter)
    return Gliederung(kopf=Kopf(titel, felder), programmpunkte=punkte,
                      vorbereitung=[a for a in abschnitte if not a.leer],
                      nachschlagen=nachschlagen)


# --------------------------------------------------------------------------
# Das HTML
# --------------------------------------------------------------------------

# Die Farben der Vorlage, je Schema ein Satz derselben Namen. Schaubilder
# liegen auch im Dunkeln auf hellem Grund, sonst verschwinden Linien und
# Beschriftung.
HELL = {
    "papier": "#f3f6f0", "flaeche": "#e5ece0", "tinte": "#243d32", "gedaempft": "#58705e",
    "akzent": "#356548", "linie": "#c7d6c6", "heute": "#e5ece0", "heute-marke": "#243d32",
    "knopf": "transparent", "knopf-rand": "#c7d6c6", "offen": "#243d32",
    "bildgrund": "#e5ece0", "bildrand": "#c7d6c6", "bild": "transparent",
    "schleier": "#192c2ba6", "schatten": "#1e30252b",
}
DUNKEL = {
    "papier": "#14241e", "flaeche": "#21382c", "tinte": "#e6eee3", "gedaempft": "#a9beab",
    "akzent": "#b3d5a0", "linie": "#3b5141", "heute": "#233a2b", "heute-marke": "#b3d5a0",
    "knopf": "#1a2d23", "knopf-rand": "#45604b", "offen": "#d9edca",
    "bildgrund": "#dce4d7", "bildrand": "#82997d", "bild": "#edf1e8",
    "schleier": "#08140dd1", "schatten": "#07110ccc",
}


def farben(palette: dict[str, str], schema: str) -> str:
    """Eine Palette als CSS-Variablen, fuer einen Block um `:root`."""
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
h1{font-size:24px;line-height:1.2;letter-spacing:-.5px;padding-top:22px}
.meta{color:var(--gedaempft);font-size:12px;margin-top:3px;padding-bottom:16px;
border-bottom:1px solid var(--linie)}
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
.programmpunkt>summary::-webkit-details-marker{display:none}
.programmpunkt>summary::after{content:"+";font-size:23px;color:var(--akzent)}
.programmpunkt[open]>summary::after{content:"−"}
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
.inhalt h3,.rich h3{font-size:18px;line-height:1.4;margin:24px 0 10px}
.rich h4{font-size:16px;margin:20px 0 8px}
.schaubild figure{margin:16px 0;padding:10px;background:var(--bildgrund);
border:1px solid var(--bildrand);color:#243d32;color-scheme:light}
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
.vorbereitung{margin-top:40px}
.vorbereitung h2{font-size:22px;line-height:1.25;padding-bottom:8px;
border-bottom:2px solid var(--akzent)}
.abschnitt{border-bottom:1px solid var(--linie)}
.abschnitt>summary{font-weight:700;padding:12px 0}
.abschnitt>.rich{padding-bottom:16px;overflow-wrap:anywhere}
.nachschlagen{margin-top:40px}
.nachschlagen>h2{font-size:22px;line-height:1.25;padding-bottom:8px;
border-bottom:2px solid var(--akzent)}
.reiterleiste,.verweise{display:flex;gap:8px;flex-wrap:wrap}
.reiterleiste{padding-top:16px;margin-bottom:20px}
.verweise{margin-top:24px}
.reiterleiste a,.verweise a,.ansicht-kopf button{display:flex;align-items:center;min-height:44px;
padding:10px 14px;font:inherit;font-size:13px;color:inherit;text-decoration:none;cursor:pointer;
background:var(--knopf);border:1px solid var(--knopf-rand);border-radius:7px}
.reiterleiste a:hover,.verweise a:hover,.ansicht-kopf button:hover{background:var(--flaeche)}
.verweise a::after{content:"\\2009↗"}
.reiterleiste a[aria-current]{background:var(--akzent);color:var(--papier);
border-color:var(--akzent)}
.reiter>h3{font-size:18px;line-height:1.4;margin:24px 0 10px}
.ansicht .reiter>h3{font-size:22px;line-height:1.25;margin-top:8px}
.ansicht{padding:0;max-height:90vh;max-height:90dvh;width:calc(100% - 24px);max-width:760px;
margin:auto;background:var(--papier);color:var(--tinte);border:1px solid var(--linie);
border-radius:16px;box-shadow:0 20px 70px var(--schatten);overscroll-behavior:contain}
.ansicht::backdrop{background:var(--schleier,#192c2ba6)}
.ansicht-kopf{display:flex;justify-content:space-between;align-items:center;gap:12px;
padding:18px 20px;background:var(--papier);position:sticky;top:0;z-index:2;
border-bottom:1px solid var(--linie)}
.ansicht-kopf h2{font-size:19px;line-height:1.25}
.ansicht-kopf button{flex-shrink:0}
.ansicht-inhalt{padding:4px 20px 28px;overflow-wrap:anywhere}
.ansicht-inhalt>section{margin:0}
@media (prefers-reduced-motion:no-preference){.ansicht[open]{animation:aufgehen .15s ease-out}}
@keyframes aufgehen{from{opacity:0;transform:translateY(12px)}to{opacity:1;transform:none}}
.fuss{font-size:11px;color:var(--gedaempft);border-top:1px solid var(--linie);
padding-top:16px;margin-top:30px}
@media (min-width:900px){.seite{padding:0 36px 48px}h1{padding-top:32px}}
""")

# Die Ansichten (#56). Ohne Skript, oder wo der Browser kein <dialog> kennt,
# stehen Nachschlagen und Vorbereitung am Ende der Seite, und Knoepfe und
# Verweise springen dorthin. Mit Skript wird jeder Abschnitt mit
# data-zurueck eine Ansicht: ein <dialog>, der sich mit dem Zurueck-Knopf,
# einem Tipp daneben und, wo der Browser es weitergibt, mit Escape oder der
# Zurueck-Geste schliesst. Ein Link auf eine Stelle darin oeffnet die
# Ansicht, ein Link auf einen Reiter zeigt ihn. Der Ablauf bleibt dabei, wie
# er ist, offene Programmpunkte bleiben offen.
#
# `ansicht(titel, zurueck)` baut eine leere Ansicht. Was sie zeigt, kommt in
# ihr Feld .ansicht-inhalt, hier ein Abschnitt der Seite, beim Vergroessern
# ein Bild.
SKRIPT_ANSICHTEN = """
(function () {
  "use strict";
  if (typeof HTMLDialogElement !== "function"
      || typeof HTMLDialogElement.prototype.showModal !== "function") return;

  function ansicht(titel, zurueck) {
    var dialog = document.createElement("dialog");
    dialog.className = "ansicht";
    dialog.setAttribute("aria-label", titel.textContent);
    var kopf = document.createElement("div");
    kopf.className = "ansicht-kopf";
    var knopf = document.createElement("button");
    knopf.type = "button";
    knopf.textContent = zurueck;
    knopf.addEventListener("click", function () { dialog.close(); });
    kopf.append(titel, knopf);
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

  // Die Stelle, auf die ein Link zeigt, so wie der Browser sie sucht.
  function stelle(link) {
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
      if (stelle(a) === reiter) a.setAttribute("aria-current", "true");
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
    var ziel = link && stelle(link);
    var dialog = ziel && ziel.closest("dialog.ansicht");
    if (!dialog) return;
    e.preventDefault();
    zeigeReiter(ziel.closest(".reiter") || dialog.querySelector(".reiter"));
    oeffne(dialog);
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


def nach_html(zeilen: list[str]) -> str:
    """Das Markdown eines Abschnitts als HTML.

    Der Umfang ist der der frueheren Leseansicht: Absaetze, Listen, Tabellen,
    Codebloecke, Trennlinien, dazu fett, kursiv, Code und Links im Text.
    `##` und `###` sind hier schon herausgeloest, eine tiefere Ueberschrift
    wird eine kleine.
    """
    raus, i = [], 0
    liste = None
    in_code = False
    code: list[str] = []

    def liste_zu():
        nonlocal liste
        if liste:
            raus.append(f"</{liste}>")
            liste = None

    while i < len(zeilen):
        z = zeilen[i]

        if _ist_zaun(z):
            if in_code:
                raus.append("<pre>" + html.escape("\n".join(code)) + "</pre>")
                code, in_code = [], False
            else:
                liste_zu()
                in_code = True
            i += 1
            continue
        if in_code:
            code.append(z)
            i += 1
            continue

        if z.strip().startswith("|"):
            block = []
            while i < len(zeilen) and zeilen[i].strip().startswith("|"):
                block.append(zeilen[i])
                i += 1
            liste_zu()
            raus.append("<table>")
            for n, zz in enumerate(block):
                if _ist_trennzeile(zz):
                    continue
                tag = "th" if n == 0 else "td"
                raus.append("<tr>" + "".join(f"<{tag}>{inline(f)}</{tag}>"
                                             for f in _zellen(zz)) + "</tr>")
            raus.append("</table>")
            continue

        m = re.match(r"^#{1,4}\s+(.*)$", z)
        if m:
            liste_zu()
            raus.append(f"<h4>{inline(m.group(1).strip())}</h4>")
            i += 1
            continue

        m = re.match(r"^\s*[-*]\s+(.*)$", z)
        if m:
            if liste != "ul":
                liste_zu()
                raus.append("<ul>")
                liste = "ul"
            raus.append(f"<li>{inline(m.group(1))}</li>")
            i += 1
            continue

        m = re.match(r"^\s*(\d+)\.\s+(.*)$", z)
        if m:
            if liste != "ol":
                liste_zu()
                raus.append("<ol>")
                liste = "ol"
            raus.append(f"<li>{inline(m.group(2))}</li>")
            i += 1
            continue

        if z.strip() in ("---", "___"):
            liste_zu()
            raus.append("<hr>")
            i += 1
            continue

        if z.strip():
            liste_zu()
            raus.append(f"<p>{inline(z.strip())}</p>")
        i += 1

    if in_code:
        raus.append("<pre>" + html.escape("\n".join(code)) + "</pre>")
    liste_zu()
    return "\n".join(raus)


def abschnitt_html(abschnitt: Abschnitt) -> str:
    """Der Text eines Abschnitts, seine Unterabschnitte mit ihrer Ueberschrift darin."""
    teile = [nach_html(abschnitt.zeilen)]
    for unter in abschnitt.unterabschnitte:
        teile += [f"<h3>{inline(unter.ueberschrift)}</h3>", nach_html(unter.zeilen)]
    return "\n".join(t for t in teile if t)


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
        wann.append(f'<span class="dauer">{punkt.dauer} min</span>')
    was = [f'<span class="name">{inline(punkt.name)}</span>'] if punkt.name else []
    if punkt.uebung:
        was.append(f'<strong class="uebung">{inline(punkt.uebung)}</strong>')
    inhalt = []
    if punkt.heute:
        inhalt.append(f'<div class="heute"><b>Heute</b><p>{inline(punkt.heute)}</p></div>')
    inhalt += karte_html(punkt, adresse)
    if punkt.verweise:
        inhalt.append('<nav class="verweise" aria-label="Nachschlagen">'
                      + "".join(map(link_auf_reiter, punkt.verweise)) + "</nav>")
    if punkt.warum:
        inhalt.append('<details class="warum"><summary>Warum hier?</summary>'
                      f'<div class="rich"><p>{inline(punkt.warum)}</p></div></details>')
    klassen = "programmpunkt gedaempft" if punkt.pause_oder_umbau else "programmpunkt"
    return (f'<details class="{klassen}">'
            f'<summary><span class="wann">{"".join(wann)}</span>'
            f'<span class="was">{"".join(was)}</span></summary>\n'
            f'<div class="inhalt">\n' + "\n".join(inhalt) + "\n</div></details>")


def kopf_html(kopf: Kopf) -> str:
    meta = []
    for schl, beschriftung in (("gruppe", ""), ("teilnehmer", "Teilnehmer"),
                               ("dauer", "Minuten"), ("spielflaechen", "Spielflächen")):
        if kopf.felder.get(schl) is not None:
            meta.append(f"{kopf.felder[schl]} {beschriftung}".strip())
    return (f"<h1>{html.escape(kopf.titel)}</h1>\n"
            f'<div class="meta">{html.escape(" · ".join(meta))}</div>')


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
<title>{html.escape(gliederung.kopf.titel)}</title><style>{CSS}</style></head><body>
<main class="seite">
{kopf_html(gliederung.kopf)}
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
<script>{SKRIPT_ANSICHTEN}</script>
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
    ziel.write_text(schreibe(gliederung, baue_adresse(ziel, a.bilder), plan.name, erzeugt),
                    encoding="utf-8")
    print(f"Leseansicht: {ziel}")
    for meldung in gliederung.meldungen:
        print(meldung)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
