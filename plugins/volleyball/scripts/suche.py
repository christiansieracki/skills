#!/usr/bin/env python3
"""Sucht Übungen in der Bibliothek.

    <python> suche.py --element annahme --spieler 14 --spielflaechen 2
    <python> suche.py --schwerpunkt sideout-sicherheit --level fortgeschritten
    <python> suche.py --disziplin beach   # Beachübungen und die für beides
    <python> suche.py --form spielform --dauer 20 --lang
    <python> suche.py --id ue-0042
    <python> suche.py --nie-benutzt
    <python> suche.py --seit 180          # seit über 180 Tagen nicht eingesetzt

Der Index wird vor jeder Suche neu gebaut, die Treffer sind also immer aktuell.
`--spieler 14` heißt "heute sind 14 da", nicht "nimm genau 14". Eine Übung
für 8 läuft bei 14 Leuten in zwei Gruppen, das zeigt die Trefferliste an.
`--dauer 20` heißt entsprechend "der Teil hat 20 Minuten", kürzeres passt auch.
Wer es strikt will, nimmt `--genau`.

`--disziplin beach` zeigt die Beachübungen und die, die für beides taugen,
`--disziplin halle` spiegelbildlich dasselbe. Ohne das Flag wird nicht
gefiltert, es kommt alles. Ein Pflichtflag bestrafte jeden schnellen Blick
in die Bibliothek. Damit die Mischung sichtbar bleibt, steht die Disziplin
in jeder Trefferzeile.

Mehrere Filter werden mit UND verknüpft. `--json` gibt die Treffer maschinell
lesbar aus, für den Fall dass ein Skill sie weiterverarbeitet.

Wichtig: `--jugend` blendet Übungen mit Erwachsenenbelastung NICHT aus. Es
markiert sie und zeigt den Hinweis, damit du entscheiden kannst, ob und wie du
sie anpasst.
"""

from __future__ import annotations

import argparse
import json
import sys
from datetime import date, datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from tpdaten import (  # noqa: E402
    DISZIPLINEN, LEVEL, disziplin_text, finde_wurzel, hole_index,
    interpreter, konsole_vorbereiten,
)


def gruppen(hi, anwesend):
    """Wie viele Gruppen braucht es, damit alle beschäftigt sind?"""
    if not isinstance(hi, int) or not isinstance(anwesend, int) or hi <= 0:
        return 1
    return max(1, -(-anwesend // hi))


def passt_spieler(e, anwesend, genau: bool) -> bool:
    """`--spieler 14` heißt: heute sind 14 da, was geht?

    Nicht: welche Übung nimmt genau 14. Eine Übung für 8 läuft bei 14 Leuten
    in zwei Gruppen, genau so lief die Annahme-Challenge am 15.09. mit 16
    Leuten an zwei Netzen. Deshalb zählt nur die Untergrenze, und die
    Obergrenze wird zur Gruppenzahl.
    """
    if anwesend is None:
        return True
    lo, hi = e.get("spieler_min"), e.get("spieler_max")
    if genau:
        if lo is not None and anwesend < lo:
            return False
        if hi is not None and anwesend > hi:
            return False
        return True
    return not (lo is not None and anwesend < lo)


def passt_dauer(e, minuten, genau: bool) -> bool:
    """`--dauer 20` heißt: der Teil hat 20 Minuten. Kürzeres passt auch rein."""
    if minuten is None:
        return True
    lo, hi = e.get("dauer_min"), e.get("dauer_max")
    if genau:
        if lo is not None and minuten < lo:
            return False
        if hi is not None and minuten > hi:
            return False
        return True
    return not (lo is not None and minuten < lo)


def tage_her(datum: str | None) -> int | None:
    if not datum:
        return None
    try:
        return (date.today() - datetime.strptime(datum, "%Y-%m-%d").date()).days
    except ValueError:
        return None


def filtere(eintraege, a):
    treffer = []
    for e in eintraege:
        if a.id and e["id"] != a.id:
            continue
        if a.typ and e.get("typ") != a.typ:
            continue
        if a.disziplin and not set(a.disziplin) & set(e.get("disziplin") or []):
            continue
        if a.element and not set(a.element) & set(e.get("element") or []):
            continue
        if a.schwerpunkt and not set(a.schwerpunkt) & set(e.get("schwerpunkt") or []):
            continue
        if a.form and e.get("form") != a.form:
            continue
        if a.spielphase and e.get("spielphase") != a.spielphase:
            continue
        if a.netz is not None and bool(e.get("netz")) != a.netz:
            continue
        if a.spielflaechen is not None and (e.get("spielflaechen") or 1) > a.spielflaechen:
            continue
        if not passt_spieler(e, a.spieler, a.genau):
            continue
        if not passt_dauer(e, a.dauer, a.genau):
            continue
        if a.level:
            lo, hi = e.get("level_min"), e.get("level_max")
            if lo in LEVEL and hi in LEVEL:
                if not (LEVEL.index(lo) <= LEVEL.index(a.level) <= LEVEL.index(hi)):
                    continue
        if a.text:
            n = a.text.lower()
            if n not in (e.get("titel") or "").lower() and n not in e["id"]:
                continue
        if a.nie_benutzt and e.get("zuletzt"):
            continue
        if a.seit is not None:
            d = tage_her(e.get("zuletzt"))
            if d is not None and d < a.seit:
                continue
        treffer.append(e)
    return treffer


def zeige(e, lang: bool, anwesend=None):
    warn = " ⚠" if e.get("erwachsenenbelastung") else ""
    art = " (Folge)" if e.get("typ") == "folge" else ""
    g = gruppen(e.get("spieler_max"), anwesend)
    parallel = f"  [{g} Gruppen parallel]" if g > 1 else ""
    # Die Disziplin steht in jeder Trefferzeile, auch in der kurzen Liste.
    # Sonst entgeht bei einer ungefilterten Suche, dass da eine Beachübung
    # zwischen den Hallenübungen liegt. Wie sie geschrieben wird, steht in
    # `disziplin_text()`, damit `index.md` dasselbe zeigt.
    disziplin = disziplin_text(e)
    print(f"{e['id']}  {e['titel']}{art}{warn}  [{disziplin}]{parallel}")
    if not lang:
        return
    def s(lo, hi, u=""):
        if lo is None and hi is None:
            return "?"
        if hi is None:
            return f"ab {lo}{u}"
        return f"{lo}–{hi}{u}" if lo != hi else f"{hi}{u}"
    print(f"    Disziplin    {disziplin}")
    print(f"    Element      {', '.join(e.get('element') or []) or '—'}")
    print(f"    Schwerpunkt  {', '.join(e.get('schwerpunkt') or []) or '—'}")
    print(f"    Form         {e.get('form') or '—'} · Spielphase {e.get('spielphase') or '—'}")
    print(f"    Level        {s(e.get('level_min'), e.get('level_max'))}")
    print(f"    Spieler      {s(e.get('spieler_min'), e.get('spieler_max'))}"
          f" · Dauer {s(e.get('dauer_min'), e.get('dauer_max'), ' min')}"
          f" · Spielflächen {e.get('spielflaechen') or '?'}"
          f" · Netz {'ja' if e.get('netz') else 'nein'}")
    if e.get("material"):
        print(f"    Material     {', '.join(e['material'])}")
    if e.get("erwachsenenbelastung"):
        print(f"    Belastung    {e.get('belastungshinweis') or 'Erwachsenenbelastung, Hinweis fehlt'}")
    if e.get("variante_von"):
        print(f"    Variante von {e['variante_von']}")
    if e.get("schaubild"):
        print(f"    Schaubild    schaubilder/{e['schaubild']}")
    if e.get("quelle"):
        print(f"    Quelle       {e['quelle']}")
    if e.get("quelldatei"):
        # Das Feld ist freier Text und nennt bei einer Übung, die über zwei
        # Seiten läuft, beide (DATENMODELL.md). Ein vorangestelltes `quellen/`
        # säße dann nur vor der ersten und ließe die zweite aussehen, als läge
        # sie woanders. Deshalb steht der Ordner einmal davor und die Angabe
        # dahinter so, wie sie auf der Karte steht.
        #
        # Sie in Dateinamen zu zerlegen hieße raten: mal trennt ein Komma die
        # beiden Seiten, mal ein „und", hinter dem Namen steht oft noch eine
        # Seitenzahl, und ein Dateiname darf Komma und Leerzeichen enthalten.
        # Jede Regel dafür trifft irgendeine Schreibweise still falsch.
        #
        # Die Zeile darüber nennt `schaubilder/` dagegen als Teil des Pfades.
        # Dort steht laut DATENMODELL.md ein einzelner Dateiname, und der
        # ergibt mit dem Ordner davor einen Pfad, den man kopieren kann.
        print(f"    Quelldatei   in quellen/ · {e['quelldatei']}")
    d = tage_her(e.get("zuletzt"))
    hist = f"{e.get('zuletzt')} ({d} Tage her)" if d is not None else (e.get("zuletzt") or "noch nie")
    print(f"    Zuletzt      {hist} · insgesamt {e.get('anzahl_einsaetze', 0)}x")
    print(f"    Datei        {e['datei']}")
    print()


def main() -> int:
    konsole_vorbereiten()
    ap = argparse.ArgumentParser(description="Übungen in der Bibliothek suchen")
    ap.add_argument("--wurzel", type=Path, default=None)
    ap.add_argument("--id")
    ap.add_argument("--text", help="Teilstring im Titel")
    ap.add_argument("--disziplin", nargs="+", choices=sorted(DISZIPLINEN),
                    help="halle, beach oder beides; ohne das Flag kommt alles")
    ap.add_argument("--element", nargs="+")
    ap.add_argument("--schwerpunkt", nargs="+")
    ap.add_argument("--form")
    ap.add_argument("--spielphase")
    ap.add_argument("--typ", choices=["uebung", "folge"])
    ap.add_argument("--level", choices=LEVEL)
    ap.add_argument("--spieler", type=int, help="so viele sind heute da")
    ap.add_argument("--dauer", type=int, help="so viele Minuten hat der Teil")
    ap.add_argument("--genau", action="store_true",
                    help="Spieler und Dauer exakt treffen statt Gruppen bilden zu dürfen")
    ap.add_argument("--spielflaechen", type=int, help="so viele stehen zur Verfügung")
    ap.add_argument("--netz", dest="netz", action="store_true", default=None)
    ap.add_argument("--ohne-netz", dest="netz", action="store_false")
    ap.add_argument("--nie-benutzt", action="store_true")
    ap.add_argument("--seit", type=int, metavar="TAGE")
    ap.add_argument("--jugend", action="store_true",
                    help="Übungen mit Erwachsenenbelastung deutlich markieren, nicht ausblenden")
    ap.add_argument("--lang", action="store_true", help="alle Felder zeigen")
    ap.add_argument("--json", action="store_true")
    a = ap.parse_args()

    wurzel = a.wurzel.resolve() if a.wurzel else finde_wurzel()
    daten = hole_index(wurzel)
    treffer = filtere(daten["uebungen"], a)

    if a.json:
        print(json.dumps(treffer, ensure_ascii=False, indent=1))
        return 0

    if not treffer:
        print("Keine Übung passt. Filter lockern, oder es ist Zeit für einen Import.")
        return 1

    print(f"{len(treffer)} von {daten['anzahl']} Übungen:\n")
    for e in sorted(treffer, key=lambda x: x["id"]):
        zeige(e, a.lang or len(treffer) <= 3, a.spieler)

    if a.jugend:
        heikel = [e for e in treffer if e.get("erwachsenenbelastung")]
        if heikel:
            print("Mit Erwachsenenbelastung, anpassen statt streichen:")
            for e in heikel:
                print(f"  {e['id']}  {e.get('belastungshinweis') or '(Hinweis fehlt)'}")
            print()

    if daten["warnungen"]:
        print(f"Hinweis: {len(daten['warnungen'])} Auffälligkeiten in der Bibliothek, "
              f"'{interpreter()} index.py' zeigt sie.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
