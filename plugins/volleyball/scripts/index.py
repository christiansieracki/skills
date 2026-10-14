#!/usr/bin/env python3
"""Baut den Uebungsindex neu und meldet, was in der Bibliothek nicht stimmt.

    <python> index.py                 # Index bauen, Warnungen zeigen
    <python> index.py --md            # zusaetzlich index.md in der Wurzel schreiben
    <python> index.py --wurzel PFAD   # Wurzel vorgeben statt suchen
    <python> index.py --still         # nur der Pfad zur index.json

Der Index wird bei jedem Aufruf komplett neu aus den Karten gebaut, deshalb
kann er nicht veralten. Die index.json landet im Cache des Rechners, nicht in
Nextcloud: sonst schreibt bei mehreren Trainern jeder Lauf dieselbe Datei neu
und der Sync legt Konfliktkopien an.

index.md dagegen ist die Lesebrille fuer Menschen und gehoert in die Wurzel.
Sie wird nur mit --md geschrieben, also auf ausdrueckliche Ansage. Sie zeigt
die Uebungen nach Element und, wo es welche gibt, die Wissenskarten nach
Thema. Zeigt eine Wissenskarte auf eine Uebung, steht ihre ID dort unter
"Hintergrund".
"""

from __future__ import annotations

import argparse
import sys
from collections import defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from tpdaten import (  # noqa: E402
    als_liste, cache_pfad, disziplin_text, finde_wurzel, hole_index,
    konsole_vorbereiten,
)

ELEMENT_TITEL = {
    "annahme": "Annahme", "zuspiel": "Zuspiel", "angriff": "Angriff",
    "block": "Block", "abwehr": "Abwehr", "aufschlag": "Aufschlag",
    "ballkontrolle": "Ballkontrolle", "athletik": "Athletik",
    "koordination": "Koordination",
}

THEMA_TITEL = {
    "trainingslehre": "Trainingslehre", "methodik": "Methodik",
    "psychologie": "Psychologie", "physiologie": "Physiologie",
    "ernaehrung": "Ernährung", "regelkunde": "Regelkunde",
    "technik": "Technik", "taktik": "Taktik",
}


def spanne(lo, hi, einheit=""):
    if lo is None and hi is None:
        return "?"
    if hi is None:
        return f"ab {lo}{einheit}"
    if lo is None or lo == hi:
        return f"{hi}{einheit}"
    return f"{lo}–{hi}{einheit}"


def wissenskarten_md(wissen: list[dict]) -> list[str]:
    """Der Abschnitt "Wissenskarten" von index.md, nach Thema gegliedert.

    Eine Karte mit zwei Themen steht unter beiden, denn gesucht wird sie
    unter jedem. Je Karte die Frage mit dem Weg zur Datei, die ID und die IDs
    ihrer Uebungen. Ohne Wissenskarten gibt es den Abschnitt nicht, und
    index.md bleibt, wie es vor ihnen war.
    """
    if not wissen:
        return []
    nach_thema = defaultdict(list)
    for k in wissen:
        # Ein Thema, das zweimal dasteht, ist eines.
        for thema in dict.fromkeys(als_liste(k.get("thema"))) or ["ohne"]:
            nach_thema[thema].append(k)

    z = ["## Wissenskarten", ""]
    # Ein Wert, den es nicht gibt, steht unter sich selbst, wie ein
    # unbekanntes Element. Der Linter meldet ihn, die Lesebrille soll an ihm
    # nicht scheitern, auch nicht an einer Zahl oder einem leeren Eintrag.
    for thema in sorted(nach_thema, key=lambda x: str(THEMA_TITEL.get(x, x))):
        z += [f"### {THEMA_TITEL.get(thema, thema)}", "",
              "| Frage | ID | Übungen |",
              "|---|---|---|"]
        for k in sorted(nach_thema[thema], key=lambda x: str(x["id"])):
            uebungen = ", ".join(str(u) for u in als_liste(k.get("uebungen"))) or "—"
            z.append(f"| [{k.get('titel')}]({k['datei']}) | {k['id']} | {uebungen} |")
        z.append("")
    return z


def schreibe_md(wurzel: Path, daten: dict) -> Path:
    nach_element = defaultdict(list)
    for e in daten["uebungen"]:
        for el in e.get("element") or ["ohne"]:
            nach_element[el].append(e)

    # Ohne Wissenskarten bleiben Kopf und Tabellen, wie sie vor ihnen waren.
    wissen = daten["wissen"]
    anzahl = f"{daten['anzahl']} Übungen"
    ordner = "`uebungen/`"
    if wissen:
        anzahl += f", {len(wissen)} {'Wissenskarte' if len(wissen) == 1 else 'Wissenskarten'}"
        ordner += " und `wissen/`"
    z = [
        "# Übungsindex",
        "",
        f"{anzahl}. Erzeugt von `index.py`, nicht von Hand ändern.",
        f"Was hier steht, kommt aus dem Frontmatter der Karten in {ordner}.",
        "",
    ]

    # Die Spalte "Hintergrund" nennt die Wissenskarten, die auf die Uebung
    # zeigen. Es gibt sie nur, wenn das eine tut: Leer staende sie sonst in
    # jeder Tabelle.
    mit_hintergrund = any(e.get("hintergrund") for e in daten["uebungen"])
    kopf = "| Übung | Disziplin | Level | Spieler | Dauer | Zuletzt |"
    trenner = "|---|---|---|---|---|---|"
    if mit_hintergrund:
        kopf += " Hintergrund |"
        trenner += "---|"

    for el in sorted(nach_element, key=lambda x: ELEMENT_TITEL.get(x, x)):
        z += [f"## {ELEMENT_TITEL.get(el, el)}", "", kopf, trenner]
        for e in sorted(nach_element[el], key=lambda x: x["id"]):
            titel = f"[{e['titel']}]({e['datei']})"
            if e.get("typ") == "folge":
                titel += " *(Folge)*"
            if e.get("erwachsenenbelastung"):
                titel += " ⚠"
            zeile = (
                f"| {titel} | {disziplin_text(e)} "
                f"| {spanne(e.get('level_min'), e.get('level_max'))} "
                f"| {spanne(e.get('spieler_min'), e.get('spieler_max'))} "
                f"| {spanne(e.get('dauer_min'), e.get('dauer_max'), ' min')} "
                f"| {e.get('zuletzt') or '—'} |"
            )
            if mit_hintergrund:
                zeile += f" {', '.join(e.get('hintergrund') or [])} |"
            z.append(zeile)
        z.append("")

    lange_her = [e for e in daten["uebungen"] if not e.get("zuletzt")]
    if lange_her:
        z += ["## Noch nie eingesetzt", ""]
        z += [f"- [{e['titel']}]({e['datei']})" for e in sorted(lange_her, key=lambda x: x["id"])]
        z.append("")

    z += wissenskarten_md(wissen)

    z += ["---", "", "⚠ heißt: die Übung hat Erwachsenenbelastung. Sie wird nicht",
          "ausgeblendet, der Hinweis steht auf der Karte und du entscheidest.", ""]

    ziel = wurzel / "index.md"
    ziel.write_text("\n".join(z), encoding="utf-8")
    return ziel


def main() -> int:
    konsole_vorbereiten()
    ap = argparse.ArgumentParser(description="Übungsindex neu bauen")
    ap.add_argument("--wurzel", type=Path, default=None)
    ap.add_argument("--md", action="store_true", help="index.md in der Wurzel neu schreiben")
    ap.add_argument("--still", action="store_true", help="nur den Pfad zur index.json ausgeben")
    a = ap.parse_args()

    wurzel = a.wurzel.resolve() if a.wurzel else finde_wurzel()
    daten = hole_index(wurzel)
    pfad = cache_pfad(wurzel)

    if a.still:
        print(pfad)
        return 0

    print(f"Wurzel:  {wurzel}")
    print(f"Übungen: {daten['anzahl']}")
    print(f"Wissenskarten: {len(daten['wissen'])}")
    print(f"Index:   {pfad}")

    if a.md:
        print(f"Index.md {schreibe_md(wurzel, daten)}")

    w = daten["warnungen"]
    if not w:
        print("\nKeine Auffälligkeiten.")
        return 0

    print(f"\n{len(w)} Auffälligkeit(en):")
    for zeile in w:
        print(f"  - {zeile}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
