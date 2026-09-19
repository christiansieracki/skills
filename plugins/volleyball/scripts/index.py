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
Sie wird nur mit --md geschrieben, also auf ausdrueckliche Ansage.
"""

from __future__ import annotations

import argparse
import sys
from collections import defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from tpdaten import (  # noqa: E402
    cache_pfad, disziplin_text, finde_wurzel, hole_index,
    konsole_vorbereiten,
)

ELEMENT_TITEL = {
    "annahme": "Annahme", "zuspiel": "Zuspiel", "angriff": "Angriff",
    "block": "Block", "abwehr": "Abwehr", "aufschlag": "Aufschlag",
    "ballkontrolle": "Ballkontrolle", "athletik": "Athletik",
    "koordination": "Koordination",
}


def spanne(lo, hi, einheit=""):
    if lo is None and hi is None:
        return "?"
    if hi is None:
        return f"ab {lo}{einheit}"
    if lo is None or lo == hi:
        return f"{hi}{einheit}"
    return f"{lo}–{hi}{einheit}"


def schreibe_md(wurzel: Path, daten: dict) -> Path:
    nach_element = defaultdict(list)
    for e in daten["uebungen"]:
        for el in e.get("element") or ["ohne"]:
            nach_element[el].append(e)

    z = [
        "# Übungsindex",
        "",
        f"{daten['anzahl']} Übungen. Erzeugt von `index.py`, nicht von Hand ändern.",
        "Was hier steht, kommt aus dem Frontmatter der Karten in `uebungen/`.",
        "",
    ]

    for el in sorted(nach_element, key=lambda x: ELEMENT_TITEL.get(x, x)):
        z += [f"## {ELEMENT_TITEL.get(el, el)}", "",
              "| Übung | Disziplin | Level | Spieler | Dauer | Zuletzt |",
              "|---|---|---|---|---|---|"]
        for e in sorted(nach_element[el], key=lambda x: x["id"]):
            titel = f"[{e['titel']}]({e['datei']})"
            if e.get("typ") == "folge":
                titel += " *(Folge)*"
            if e.get("erwachsenenbelastung"):
                titel += " ⚠"
            z.append(
                f"| {titel} | {disziplin_text(e)} "
                f"| {spanne(e.get('level_min'), e.get('level_max'))} "
                f"| {spanne(e.get('spieler_min'), e.get('spieler_max'))} "
                f"| {spanne(e.get('dauer_min'), e.get('dauer_max'), ' min')} "
                f"| {e.get('zuletzt') or '—'} |"
            )
        z.append("")

    lange_her = [e for e in daten["uebungen"] if not e.get("zuletzt")]
    if lange_her:
        z += ["## Noch nie eingesetzt", ""]
        z += [f"- [{e['titel']}]({e['datei']})" for e in sorted(lange_her, key=lambda x: x["id"])]
        z.append("")

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
