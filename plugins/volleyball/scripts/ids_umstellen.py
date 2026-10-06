#!/usr/bin/env python3
"""Stellt einen Arbeitsordner auf sechsstellige IDs um (ADR-0011).

    <python> ids_umstellen.py --trainer christian               # zeigt nur
    <python> ids_umstellen.py --trainer christian --schreiben
    <python> ids_umstellen.py --wurzel <pfad> --trainer christian --schreiben

Bis 2.5.1 waren IDs vierstellig. Seit 3.0.0 tragen sie vorn zwei Ziffern für
die Nummer des Trainers. Die bisherigen Karten bekommen `00`: `ue-0042` wird
`ue-000042`. Damit wird die Regel „Eine vergebene ID wird nie wieder geändert“
ein einziges Mal gebrochen, und zwar überall zugleich, damit kein Verweis ins
Leere zeigt.

- Jede vierstellige ID als ganzes Wort in den `.md`- und `.yml`-Dateien des
  Arbeitsordners wird sechsstellig. Das gilt auch unter `quellen/`, etwa in
  den PlayDrill-Logs und in der Übersicht eines Sammelimports.
- Karten in `uebungen/` und Dateien in `schaubilder/`, deren Name mit einer
  vierstelligen ID beginnt, werden umbenannt: die Karte, ihr Bild, ihre Szene.
- Hat die Wurzeldatei unter `trainer:` noch niemanden, kommt der genannte
  Trainer hinein, mit der Nummer 00 und diesem Rechner. Ist dort schon jemand
  eingetragen, bleibt der Abschnitt, wie er ist. Gehört dieser Rechner dann
  zu keinem Trainer, sagt das Skript es.

Erzeugtes schreibt das Skript nicht um. `index.md` und die Leseansichten
entstehen danach neu aus den umgestellten Dateien, das Skript sagt am Ende,
womit.

Ohne `--schreiben` zeigt es jede Änderung und schreibt nichts. Ist ein neuer
Dateiname schon belegt, schreibt es auch mit `--schreiben` nichts. Ein zweiter
Lauf findet nichts mehr zu tun: Das Muster für eine vierstellige ID trifft
eine sechsstellige nicht.
"""

from __future__ import annotations

import argparse
import os
import re
import sys
from dataclasses import dataclass, field
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from tpdaten import (  # noqa: E402
    ALTE_ID_MUSTER, EINTRAGSNAME, MARKER, TRAINER_ABSCHNITT, KeineId, finde_wurzel,
    interpreter, konsole_vorbereiten, lies_trainer, rechnername, trainernummer,
)

VIERSTELLIG = re.compile(rf"\b{ALTE_ID_MUSTER}\b")
TEXTDATEIEN = {".md", ".yml", ".yaml"}
UMBENENNEN_IN = ("uebungen", "schaubilder")

# Steht über dem Abschnitt, wenn das Skript ihn anlegt. Ohne Umlaute, wie der
# Rest der Wurzeldatei aus init_struktur.py.
KOPF_TRAINER = [
    "# --- Trainer ----------------------------------------------------------------",
    "# Jeder Trainer, der Uebungen anlegt, hat eine Nummer. Sie steht vorn in jeder",
    "# ID, die er vergibt (ADR-0011). Dazu die Rechner, an denen er importiert.",
]


def sechsstellig(id_oder_name: str) -> str:
    """`ue-0042` wird `ue-000042`, auch am Anfang eines Dateinamens."""
    return "ue-00" + id_oder_name[len("ue-"):]


@dataclass
class Plan:
    """Was die Umstellung ändern würde. Pfade relativ zum Arbeitsordner."""

    wurzel: Path
    texte: dict[str, str] = field(default_factory=dict)
    zeilen: list[tuple[str, int, list[str]]] = field(default_factory=list)
    umbenennen: list[tuple[str, str]] = field(default_factory=list)
    belegt: list[str] = field(default_factory=list)
    nicht_lesbar: list[str] = field(default_factory=list)
    trainer: str | None = None
    hinweis: str | None = None

    @property
    def leer(self) -> bool:
        return not (self.texte or self.umbenennen or self.trainer)


def textdateien(wurzel: Path):
    """Jede `.md` und `.yml` im Arbeitsordner, außer `index.md` in der Wurzel.

    `index.md` ist erzeugt und wird danach neu gebaut. Ordner und Dateien mit
    einem Punkt vorn gehören dem Sync oder dem Editor, nicht der
    Trainingsplanung.
    """
    for ordner, unterordner, dateien in os.walk(wurzel):
        unterordner[:] = sorted(d for d in unterordner if not d.startswith("."))
        for name in sorted(dateien):
            pfad = Path(ordner) / name
            if (pfad.suffix.lower() in TEXTDATEIEN and not name.startswith(".")
                    and pfad != wurzel / "index.md"):
                yield pfad


def mit_trainer(text: str, name: str) -> str | None:
    """Der Text der Wurzeldatei mit dem Trainer als 00 an diesem Rechner.

    Fehlt der Abschnitt, kommt er ans Ende. Steht `trainer:` schon da, ohne
    Eintrag, wie in der Vorlage aus init_struktur.py, kommt der Trainer direkt
    darunter. Die Zeilenenden der Datei bleiben, wie sie sind.
    """
    nl = "\r\n" if "\r\n" in text else "\n"
    eintrag = [f"  {name}:", '    nummer: "00"', f"    rechner: [{rechnername()}]"]
    zeilen = text.splitlines(keepends=True)
    for i, zeile in enumerate(zeilen):
        if TRAINER_ABSCHNITT.match(zeile.rstrip("\r\n")):
            if not zeile.endswith("\n"):
                zeilen[i] += nl
            zeilen[i + 1:i + 1] = [z + nl for z in eintrag]
            return "".join(zeilen)
    if text and not text.endswith("\n"):
        text += nl
    return text + nl.join(["", *KOPF_TRAINER, "", "trainer:", *eintrag]) + nl


def plane(wurzel: Path, trainer: str) -> Plan:
    plan = Plan(wurzel)
    for pfad in textdateien(wurzel):
        name = pfad.relative_to(wurzel).as_posix()
        roh = pfad.read_bytes()
        try:
            text = roh.decode("utf-8")
        except UnicodeDecodeError:
            if re.search(rb"\b" + ALTE_ID_MUSTER.encode() + rb"\b", roh):
                plan.nicht_lesbar.append(name)
            continue
        if not VIERSTELLIG.search(text):
            continue
        plan.texte[name] = VIERSTELLIG.sub(lambda m: sechsstellig(m.group()), text)
        for nummer, zeile in enumerate(text.splitlines(), 1):
            gefunden = VIERSTELLIG.findall(zeile)
            if gefunden:
                plan.zeilen.append((name, nummer, gefunden))

    for ordner in UMBENENNEN_IN:
        if not (wurzel / ordner).is_dir():
            continue
        for pfad in sorted((wurzel / ordner).iterdir()):
            if pfad.is_file() and re.match(rf"{ALTE_ID_MUSTER}\b", pfad.name):
                ziel = pfad.with_name(sechsstellig(pfad.name))
                plan.umbenennen.append((f"{ordner}/{pfad.name}", f"{ordner}/{ziel.name}"))
                if ziel.exists():
                    plan.belegt.append(f"{ordner}/{ziel.name}")

    if not lies_trainer(wurzel):
        plan.trainer = trainer
    else:
        # Den Abschnitt pflegt der Import-Skill nach Rückfrage, hier wird
        # keiner umgeschrieben. Still übergangen wäre --trainer aber auch
        # nicht recht: Danach bekäme dieser Rechner keine ID, und niemand
        # hätte es gesagt.
        try:
            trainernummer(wurzel)
        except KeineId as fehler:
            plan.hinweis = (f"Unter trainer: steht schon jemand. Der Abschnitt bleibt, wie er "
                            f"ist, und {trainer} bekommt dort keinen Eintrag.\n{fehler}")
    return plan


def zeige(plan: Plan) -> None:
    if plan.umbenennen:
        print("Umbenennen:")
        for alt, neu in plan.umbenennen:
            print(f"  {alt} → {neu}")
        print()
    if plan.zeilen:
        print("IDs im Text:")
        for name, nummer, gefunden in plan.zeilen:
            ids = ", ".join(f"{uid} → {sechsstellig(uid)}" for uid in gefunden)
            print(f"  {name}:{nummer}  {ids}")
        print()
    if plan.trainer:
        print(f"{MARKER} bekommt unter trainer: {plan.trainer} mit der Nummer 00 "
              f"und diesem Rechner, {rechnername()}.")
        print()
    if plan.nicht_lesbar:
        print("Nicht als UTF-8 lesbar, mit vierstelliger ID darin. Bitte von Hand umstellen:")
        for name in plan.nicht_lesbar:
            print(f"  {name}")
        print()
    if plan.hinweis:
        print(plan.hinweis)
        print()


def schreibe(plan: Plan) -> None:
    """Erst die Texte, dann die Namen, zuletzt die Wurzeldatei.

    Bricht der Lauf dazwischen ab, findet der nächste, was noch fehlt: Jeder
    Schritt sucht nach dem, was er noch nicht getan hat. Die Bytes außerhalb
    der IDs bleiben, wie sie waren, auch die Zeilenenden.
    """
    for name, text in plan.texte.items():
        (plan.wurzel / name).write_bytes(text.encode("utf-8"))
    for alt, neu in plan.umbenennen:
        (plan.wurzel / alt).rename(plan.wurzel / neu)
    if plan.trainer:
        datei = plan.wurzel / MARKER
        text = datei.read_bytes().decode("utf-8")
        datei.write_bytes(mit_trainer(text, plan.trainer).encode("utf-8"))


def neu_zu_bauen(wurzel: Path) -> list[str]:
    """Die Aufrufe, die das Erzeugte aus den umgestellten Dateien neu bauen."""
    python = interpreter()
    aufrufe = []
    if (wurzel / "index.md").is_file():
        aufrufe.append(f"{python} index.py --md")
    if (wurzel / "trainings").is_dir():
        for html in sorted((wurzel / "trainings").rglob("*.html")):
            if html.with_suffix(".md").is_file():
                plan = html.with_suffix(".md").relative_to(wurzel).as_posix()
                aufrufe.append(f"{python} leseansicht.py {plan}")
    return aufrufe


def main() -> int:
    konsole_vorbereiten()
    ap = argparse.ArgumentParser(description="Arbeitsordner auf sechsstellige IDs umstellen")
    ap.add_argument("--wurzel", type=Path, default=None)
    ap.add_argument("--trainer", required=True,
                    help="wer die Nummer 00 bekommt, so wie er unter gruppen.<gruppe>.trainer heißt")
    ap.add_argument("--schreiben", action="store_true",
                    help="umstellen, statt nur zu zeigen, was sich ändert")
    a = ap.parse_args()

    if not re.fullmatch(EINTRAGSNAME, a.trainer):
        print(f"--trainer {a.trainer!r}: ein Name ohne Leerzeichen, Doppelpunkt und #, "
              f"so wie unter gruppen.<gruppe>.trainer.")
        return 1
    wurzel = a.wurzel.resolve() if a.wurzel else finde_wurzel()
    plan = plane(wurzel, a.trainer)
    print(f"Arbeitsordner: {wurzel}\n")
    if plan.leer:
        print("Nichts zu tun: Keine vierstellige ID mehr, und unter trainer: steht schon jemand.")
        if plan.hinweis:
            print(f"\n{plan.hinweis}")
        return 0

    zeige(plan)
    print(f"{len(plan.umbenennen)} Dateien umzubenennen, {len(plan.zeilen)} Zeilen mit "
          f"vierstelligen IDs in {len(plan.texte)} Dateien.")
    if plan.belegt:
        print("\nDiese Namen gibt es schon, deshalb wird nichts umgestellt:")
        for name in plan.belegt:
            print(f"  {name}")
        return 1
    if a.schreiben:
        schreibe(plan)
        print("Umgestellt.")
    else:
        print("Nichts geschrieben. Mit --schreiben wird umgestellt.")

    aufrufe = neu_zu_bauen(wurzel)
    if aufrufe:
        print(f"\n{'Jetzt' if a.schreiben else 'Danach'} aus dem Arbeitsordner heraus neu bauen, "
              f"was aus den Karten erzeugt wird:")
        for aufruf in aufrufe:
            print(f"  {aufruf}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
