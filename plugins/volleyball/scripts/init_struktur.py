#!/usr/bin/env python3
"""Legt einen neuen Trainingsplanungs-Ordner an.

    <python> init_struktur.py ~/Nextcloud/Training/trainingsplanung
    <python> init_struktur.py <ordner> --gruppe h1-h2 --teams herren-1 herren-2

Vorhandene Dateien werden nie überschrieben. Das Skript kann also gefahrlos ein
zweites Mal laufen, wenn nachträglich etwas fehlt.
"""

from __future__ import annotations

import argparse
import shutil
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from tpdaten import konsole_vorbereiten  # noqa: E402

START = Path(__file__).resolve().parent.parent / "referenzen" / "start"

ORDNER = ["uebungen", "quellen", "schaubilder", "teams", "trainings"]

ROOT_YML = """\
# Wurzeldatei der Trainingsplanung.
#
# Die volleyball-Skills suchen ab dem geoeffneten Ordner aufwaerts nach dieser
# Datei. Solange sie mitwandert, darf der Ordner heissen und liegen, wo er will.

version: 1
verein: "{verein}"
saison: "{saison}"

# --- Trainingsgruppen -------------------------------------------------------
# Eine Gruppe ist, wer zusammen in der Halle steht. Daran haengen die
# Trainingseinheiten. Ein Team ist die Wettkampfmannschaft mit Saisonplan.

gruppen:
  {gruppe}:
    name: "{gruppe_name}"
    teams: [{teams_liste}]
    leitteam: {leitteam}
    zeiten: ""
    trainer: []
    hinweis: ""

# --- Teams ------------------------------------------------------------------

teams:
{teams_block}
# --- Ordner -----------------------------------------------------------------

ordner:
  uebungen: uebungen/
  quellen: quellen/
  schaubilder: schaubilder/
  trainings: trainings/
  teams: teams/

dateien:
  schwerpunkte: schwerpunkte.md
  glossar: glossary.md
  index: index.md

# --- Regeln fuer die Skills -------------------------------------------------

regeln:
  index_json_in_nextcloud: false
  index_md_automatisch: false
  leseansicht_automatisch: false
"""

TEAM_BLOCK = """\
  {team}:
    name: "{name}"
    ordner: teams/{team}/
    saisonplan: {saisonplan}
    mesozyklen: {mesozyklen}
"""

README = """\
# Trainingsplanung

Hier liegen die Übungsbibliothek, die Saisonpläne und alle Trainingseinheiten.
Alles ist einfacher Text im Markdown-Format, jede Datei lässt sich mit jedem
Editor öffnen, auch ohne Claude.

| Ordner | Inhalt |
|---|---|
| `uebungen/` | Die Übungsbibliothek. Eine Datei je Übung. |
| `quellen/` | Originaldokumente, aus denen Übungen stammen. |
| `schaubilder/` | Aufbauskizzen, die zu einer Übung gehören. |
| `teams/<team>/` | Team-Profil, Saisonplan und Mesozyklen. |
| `trainings/<gruppe>/` | Die Trainingseinheiten, benannt nach Datum. |
| `glossary.md` | Wie wir Begriffe benutzen. Bitte einmal lesen. |
| `schwerpunkte.md` | Die verbindliche Liste der Schwerpunkte. |

`trainingsplanung-root.yml` ist die Wurzeldatei. Daran erkennen die Skills den
Ordner. Bitte nicht verschieben oder umbenennen.

## Die wichtigste Regel: korrigieren ja, umschreiben nein

Die Bibliothek gehört allen.

**Immer erlaubt:** Tippfehler beheben, fehlende Felder nachtragen, eine
Beschreibung klarer formulieren, ein Schaubild ergänzen.

**Bitte nicht:** eine fremde Karte auf dein Niveau oder deine Altersklasse
umschreiben. Alle anderen, die per ID auf diese Übung verweisen, bekommen sonst
eine andere Übung.

**Stattdessen:** Anpassungen gehören in den Abschnitt „Variationen" der Karte.
Ändern sie den Charakter der Übung, leg eine eigene Karte an und trag
`variante_von: ue-0042` ein.

## Claude einrichten

```
/plugin marketplace add christiansieracki/skills
/plugin install volleyball@christiansieracki-skills
```

Danach den Ordner, in dem diese Datei liegt, in der Claude-App als Ordner
verbinden.
"""


def schreibe(pfad: Path, inhalt: str, angelegt: list, uebersprungen: list):
    if pfad.exists():
        uebersprungen.append(pfad.name)
        return
    pfad.parent.mkdir(parents=True, exist_ok=True)
    pfad.write_text(inhalt, encoding="utf-8")
    angelegt.append(str(pfad))


def main() -> int:
    konsole_vorbereiten()
    ap = argparse.ArgumentParser(description="Trainingsplanungs-Ordner anlegen")
    ap.add_argument("ordner", type=Path)
    ap.add_argument("--verein", default="TODO Vereinsnamen eintragen")
    ap.add_argument("--saison", default="")
    ap.add_argument("--gruppe", default="gruppe-1")
    ap.add_argument("--teams", nargs="+", default=["team-1"])
    a = ap.parse_args()

    wurzel = a.ordner.expanduser().resolve()
    angelegt: list[str] = []
    uebersprungen: list[str] = []

    for name in ORDNER:
        (wurzel / name).mkdir(parents=True, exist_ok=True)
    (wurzel / "trainings" / a.gruppe).mkdir(parents=True, exist_ok=True)

    leitteam = a.teams[0]
    block = "".join(
        TEAM_BLOCK.format(
            team=t, name=t.replace("-", " ").title(),
            saisonplan=f"teams/{t}/saisonplan.md" if t == leitteam else "null",
            mesozyklen=f"teams/{t}/mesozyklen/" if t == leitteam else "null",
        )
        for t in a.teams
    )
    schreibe(
        wurzel / "trainingsplanung-root.yml",
        ROOT_YML.format(
            verein=a.verein, saison=a.saison, gruppe=a.gruppe,
            gruppe_name=" + ".join(t.replace("-", " ").title() for t in a.teams),
            teams_liste=", ".join(a.teams), leitteam=leitteam, teams_block=block,
        ),
        angelegt, uebersprungen,
    )
    schreibe(wurzel / "README.md", README, angelegt, uebersprungen)

    for name, ziel in (("glossary.md", wurzel / "glossary.md"),
                       ("schwerpunkte.md", wurzel / "schwerpunkte.md"),
                       ("_vorlage.md", wurzel / "trainings" / a.gruppe / "_vorlage.md")):
        quelle = START / name
        if ziel.exists():
            uebersprungen.append(ziel.name)
        elif quelle.is_file():
            shutil.copyfile(quelle, ziel)
            angelegt.append(str(ziel))

    for t in a.teams:
        (wurzel / "teams" / t).mkdir(parents=True, exist_ok=True)
        if t == leitteam:
            (wurzel / "teams" / t / "mesozyklen").mkdir(exist_ok=True)

    print(f"Wurzel: {wurzel}\n")
    for p in angelegt:
        print(f"  angelegt      {p}")
    for p in uebersprungen:
        print(f"  war schon da  {p}")

    print("\nAls Nächstes:")
    print("  1. Vereinsnamen und Saison in trainingsplanung-root.yml eintragen")
    print("  2. Team-Profile anlegen, am einfachsten mit volleyball-saisonplaner")
    print("  3. Erste Übungen holen, am einfachsten mit volleyball-uebungsimport")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
