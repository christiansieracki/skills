#!/usr/bin/env python3
"""Führt einen Sammelimport über einen Quellenordner, Kandidat für Kandidat.

    <python> sammelimport.py vorbereiten <ordner>
    <python> sammelimport.py pruefen <ordner>
    <python> sammelimport.py uebernehmen <ordner> --kandidat 3 "Notiz" ...

`<ordner>` ist der Quellenordner, relativ zu `quellen/`. In ihm liegt die
`sammelimport.md` mit den Einstellungen im Frontmatter, den Absprachen und der
Übersicht, dem freigegebenen Zerlegungsplan mit dem Stand je Kandidat.

`vorbereiten` legt unter `kartenentwuerfe/<ordner>/` die Aufträge für die
nächsten offenen Kandidaten an. `pruefen` setzt den Status aus den
Kartenentwürfen, die dort auf der Platte liegen. `uebernehmen` macht aus
freigegebenen Entwürfen Karten in `uebungen/`, erst jetzt mit ID (ADR-0010).

Nach der Freigabe des Plans schreibt nur noch dieses Skript in die Übersicht.
Mehrere Agenten entwerfen parallel, und keiner von ihnen fasst sie an.
"""

from __future__ import annotations

import argparse
import os
import re
import shutil
import sys
from dataclasses import dataclass
from datetime import date
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from tpdaten import (  # noqa: E402
    DISZIPLIN_SPALTE, ID_MUSTER, TYPEN, finde_wurzel, hole_index,
    konsole_vorbereiten, lies_frontmatter, lies_schwerpunkt_zeilen,
)

SAMMELIMPORT = "sammelimport.md"
ENTWUERFE = "kartenentwuerfe"
JE_DURCHGANG = 30

SPALTEN = ["Kandidat", "Dateien", "Was es ist", "Ergebnis", "Status", "Karte", "Notiz"]
ERGEBNISSE = {"uebung", "folge", "zurückgestellt", "übersprungen"}
STATUS = {"offen", "bereit", "rückfrage", "importiert", "ergänzt", "übersprungen",
          "zurückgestellt"}

# Die Stände, in denen ein Kandidat noch auf seine Karte wartet. Alle anderen
# sind erledigt, und kein Aufruf fasst ihre Zeile mehr an.
NOCH_OFFEN = {"offen", "bereit", "rückfrage"}


class Abbruch(Exception):
    """Ein Fehler, nach dem das Skript nichts geschrieben hat."""


# --------------------------------------------------------------------------
# Markdown
# --------------------------------------------------------------------------

def _abschnitt_grenzen(zeilen: list[str], titel: str) -> tuple[int, int] | None:
    """Die Zeile mit `## <titel>` und die, auf der die nächste Überschrift steht."""
    for i, zeile in enumerate(zeilen):
        if zeile.strip() == f"## {titel}":
            ende = next((j for j in range(i + 1, len(zeilen))
                         if zeilen[j].startswith(("# ", "## "))), len(zeilen))
            return i, ende
    return None


def _abschnitt(zeilen: list[str], titel: str) -> list[str] | None:
    """Die Zeilen unter `## <titel>` bis zur nächsten Überschrift."""
    grenzen = _abschnitt_grenzen(zeilen, titel)
    return None if grenzen is None else zeilen[grenzen[0] + 1:grenzen[1]]


def _frontmatter_ende(zeilen: list[str]) -> int | None:
    """Die Zeile `---`, die das Frontmatter schließt, oder None."""
    if not zeilen or zeilen[0].strip() != "---":
        return None
    return next((i for i in range(1, len(zeilen)) if zeilen[i].strip() == "---"), None)


def _zelle(wert: str) -> str:
    """Ein Wert so, dass er in einer Zelle bleibt: ohne Zeilenumbruch, `|` maskiert."""
    return " ".join(str(wert).split()).replace("|", "\\|")


def _zellen(zeile: str) -> list[str]:
    innen = zeile.strip()
    innen = innen[1:] if innen.startswith("|") else innen
    innen = innen[:-1] if innen.endswith("|") and not innen.endswith("\\|") else innen
    return [z.strip().replace("\\|", "|") for z in re.split(r"(?<!\\)\|", innen)]


# --------------------------------------------------------------------------
# Die Übersicht
# --------------------------------------------------------------------------

@dataclass
class Kandidat:
    """Eine Zeile der Übersicht.

    `zeile` ist der Text, wie er in der Datei steht. Solange der Kandidat nicht
    geändert wird, geht genau dieser Text zurück in die Datei. So bleibt eine
    erledigte Zeile zeichengenau stehen, auch wenn sie von Hand geschrieben ist
    und sich nicht sauber in Zellen zerlegen lässt.
    """

    zeile: str
    zellen: dict[str, str]
    geaendert: bool = False

    @property
    def nummer(self) -> str:
        return self.zellen["Kandidat"]

    @property
    def was(self) -> str:
        return self.zellen["Was es ist"]

    @property
    def ergebnis(self) -> str:
        return self.zellen["Ergebnis"]

    @property
    def status(self) -> str:
        return self.zellen["Status"]

    @property
    def notiz(self) -> str:
        return self.zellen["Notiz"]

    @property
    def wartet(self) -> bool:
        """Aus dem Kandidaten soll eine Karte werden, und es gibt sie noch nicht."""
        return self.ergebnis in TYPEN and self.status in NOCH_OFFEN

    @property
    def dateien(self) -> list[str]:
        """Die Dateien des Kandidaten, relativ zum Quellenordner.

        In der Zelle steht jede in Backticks, weil Dateinamen Kommas tragen
        können. Eine von Hand geschriebene Zelle ohne Backticks wird an den
        Kommas getrennt.
        """
        zelle = self.zellen["Dateien"]
        return re.findall(r"`([^`]+)`", zelle) or [d.strip() for d in zelle.split(",") if d.strip()]

    def setze(self, status: str, notiz: str = "", karte: str | None = None) -> None:
        self.zellen.update(Status=status, Notiz=notiz)
        if karte is not None:
            self.zellen["Karte"] = karte
        self.geaendert = True


class Sammelimport:
    """Die `sammelimport.md` eines Quellenordners.

    Gelesen werden die Einstellungen und die Übersicht. Geschrieben werden nur
    die Zeilen der Übersicht, alles andere in der Datei bleibt, wie es ist:
    Die Absprachen gehören dem Trainer.
    """

    def __init__(self, wurzel: Path, ordner: str) -> None:
        self.wurzel = wurzel
        self.ordner = ordner
        self.datei = wurzel / "quellen" / ordner / SAMMELIMPORT
        if not self.datei.is_file():
            raise Abbruch(f"Keine {SAMMELIMPORT} in quellen/{ordner}/.")
        self.einstellungen, _ = lies_frontmatter(self.datei)
        self.zeilen = self.datei.read_text(encoding="utf-8").splitlines()
        self._lies_uebersicht()

    def _abbruch(self, text: str) -> Abbruch:
        return Abbruch(f"In der Übersicht von quellen/{self.ordner}/{SAMMELIMPORT}: {text}")

    def _lies_uebersicht(self) -> None:
        self.kandidaten: list[Kandidat] = []
        self.spalten = list(SPALTEN)
        self.anfang = self.ende = len(self.zeilen)
        grenzen = _abschnitt_grenzen(self.zeilen, "Übersicht")
        if grenzen is None:
            return
        kopf = next((i for i in range(grenzen[0] + 1, grenzen[1])
                     if self.zeilen[i].lstrip().startswith("|")), None)
        if kopf is None:
            return
        self.spalten = _zellen(self.zeilen[kopf])
        fehlend = [s for s in SPALTEN if s not in self.spalten]
        if fehlend:
            raise self._abbruch(f"Es fehlen die Spalten {', '.join(fehlend)}.")
        self.anfang = self.ende = kopf + 2
        while self.ende < len(self.zeilen) and self.zeilen[self.ende].lstrip().startswith("|"):
            werte = _zellen(self.zeilen[self.ende])
            werte += [""] * (len(self.spalten) - len(werte))
            self._nimm_auf(Kandidat(self.zeilen[self.ende], dict(zip(self.spalten, werte))))
            self.ende += 1

    def _nimm_auf(self, k: Kandidat) -> None:
        """Nimmt eine Zeile auf, wenn sie sich lesen lässt, und bricht sonst ab.

        Abgebrochen wird lieber als geraten. Die Nummer benennt Entwurf und
        Auftrag: Doppelt teilten sich zwei Kandidaten eine Datei, und etwas
        anderes als eine Zahl, etwa ein Pfad, legte eine Datei außerhalb von
        `kartenentwuerfe/` ab. Ein vertippter Status gälte als erledigt, der
        Kandidat bekäme nie einen Auftrag, und am Ende verschwände der
        Entwurfsordner, obwohl aus ihm nie eine Karte wurde.
        """
        if not k.nummer.isdigit():
            raise self._abbruch(f"Der Kandidat {k.nummer!r} ist keine Nummer.")
        if any(k.nummer == anderer.nummer for anderer in self.kandidaten):
            raise self._abbruch(f"Der Kandidat {k.nummer} steht zweimal da.")
        if k.ergebnis not in ERGEBNISSE:
            raise self._abbruch(
                f"Kandidat {k.nummer} hat das Ergebnis {k.ergebnis!r}. "
                f"Erlaubt sind {', '.join(sorted(ERGEBNISSE))}.")
        if k.status not in STATUS:
            raise self._abbruch(
                f"Kandidat {k.nummer} hat den Status {k.status!r}. "
                f"Erlaubt sind {', '.join(sorted(STATUS))}.")
        self.kandidaten.append(k)

    def verlange_freigabe(self) -> None:
        """Bricht ab, solange der Trainer den Zerlegungsplan nicht freigegeben hat.

        Vor der Freigabe steht der Zuschnitt noch nicht fest, und die Übersicht
        gehört dem Skill, der den Plan mit dem Trainer bespricht. Erst danach
        schreibt nur noch dieses Skript hinein.
        """
        if not self.einstellungen.get("plan_freigegeben"):
            raise Abbruch(
                f"Der Zerlegungsplan in quellen/{self.ordner}/{SAMMELIMPORT} ist noch "
                f"nicht freigegeben.\nErst mit dem Datum in plan_freigegeben gibt es "
                f"Aufträge, Prüfung und Übernahme."
            )

    def speichere(self) -> None:
        """Schreibt die geänderten Zeilen der Übersicht zurück, sonst nichts.

        Erst daneben, dann umbenennen: Die Datei ist der Stand des ganzen
        Sammelimports, und ein Abbruch mitten im Schreiben soll sie heil
        lassen statt halb.
        """
        neu = [("| " + " | ".join(_zelle(k.zellen.get(s, "")) for s in self.spalten) + " |")
               if k.geaendert else k.zeile
               for k in self.kandidaten]
        self.zeilen[self.anfang:self.ende] = neu
        self.ende = self.anfang + len(neu)
        zwischen = self.datei.with_name(self.datei.name + ".neu")
        try:
            zwischen.write_text("\n".join(self.zeilen) + "\n", encoding="utf-8")
            os.replace(zwischen, self.datei)
        finally:
            zwischen.unlink(missing_ok=True)

    @property
    def je_durchgang(self) -> int:
        zahl = self.einstellungen.get("kandidaten_je_durchgang", JE_DURCHGANG)
        if zahl is None:
            return JE_DURCHGANG
        if not isinstance(zahl, int) or zahl < 1:
            raise Abbruch(f"kandidaten_je_durchgang in quellen/{self.ordner}/{SAMMELIMPORT} "
                          f"ist {zahl!r}, erwartet ist eine Zahl ab 1.")
        return zahl

    @property
    def absprachen(self) -> str:
        return "\n".join(_abschnitt(self.zeilen, "Absprachen") or []).strip()

    @property
    def entwurfsordner(self) -> Path:
        return self.wurzel / ENTWUERFE / self.ordner

    def entwurf(self, k: Kandidat) -> Path:
        return self.entwurfsordner / f"{k.nummer}.md"

    def auftrag(self, k: Kandidat) -> Path:
        return self.entwurfsordner / f"{k.nummer}.auftrag.md"


# --------------------------------------------------------------------------
# Der Kartenentwurf
# --------------------------------------------------------------------------

@dataclass
class Befund:
    fehler: str | None = None
    ohne_vermutung: int = 0


_LISTENKOPF = re.compile(r"^(Vorschläge|Rückfragen):\s*(.*)$")
_PUNKT = re.compile(r"^(?:-|\d+\.)\s+(.*)$")
_OHNE_VERMUTUNG = re.compile(r"Vermutung im Entwurf:\s*keine\.?\s*$")


def _listen(freigabe: list[str]) -> dict[str, list[str]]:
    """Die Listen unter `## Freigabe`, je Kopfzeile ihre Punkte.

    Eine Kopfzeile mit `keine` dahinter ist eine leere Liste. Ein Punkt, der
    über mehrere Zeilen läuft, wird zu einer Zeile zusammengezogen, damit das
    Ende einer Rückfrage auch ihr Ende ist.
    """
    listen: dict[str, list[str]] = {}
    aktuell: list[str] | None = None
    for zeile in freigabe:
        text = zeile.strip()
        kopf = _LISTENKOPF.match(text)
        if kopf:
            aktuell = listen.setdefault(kopf.group(1), [])
            continue
        if aktuell is None or not text:
            continue
        punkt = _PUNKT.match(text)
        if punkt:
            aktuell.append(punkt.group(1))
        elif aktuell:
            aktuell[-1] += " " + text
    return listen


def pruefe_entwurf(datei: Path) -> Befund:
    """Sagt, ob ein Kartenentwurf Karte werden kann, und wenn nicht, warum."""
    if not datei.is_file():
        return Befund("kein Entwurf")
    try:
        felder, rumpf = lies_frontmatter(datei)
        zeilen = datei.read_text(encoding="utf-8").splitlines()
    except UnicodeDecodeError:
        return Befund("Entwurf ist nicht als UTF-8 lesbar")
    # Die Karte entsteht zeilenweise aus dem Entwurf, das Frontmatter muss
    # also auf einer eigenen Zeile `---` enden, nicht nur irgendwo.
    if not felder or _frontmatter_ende(zeilen) is None:
        return Befund("kein lesbares Frontmatter")
    if not felder.get("titel"):
        return Befund("Frontmatter ohne titel")
    freigabe = _abschnitt(rumpf.splitlines(), "Freigabe")
    if freigabe is None:
        return Befund("## Freigabe fehlt")
    listen = _listen(freigabe)
    for liste in ("Vorschläge", "Rückfragen"):
        if liste not in listen:
            return Befund(f"## Freigabe ohne {liste}:")
    ohne = [r for r in listen["Rückfragen"] if _OHNE_VERMUTUNG.search(r)]
    return Befund(ohne_vermutung=len(ohne))


# --------------------------------------------------------------------------
# vorbereiten
# --------------------------------------------------------------------------

def kennungstabelle(wurzel: Path) -> list[str]:
    """Die Schwerpunkt-Kennungen des Arbeitsordners als Tabelle für den Auftrag.

    Die Disziplin steht so da, wie der Linter sie liest: Eine leere oder
    unbekannte Spalte heißt `beide`, siehe `lies_schwerpunkte`. So muss der
    Agent die Regel dafür nicht kennen.
    """
    zeilen = ["| Kennung | Klartext | Disziplin |", "|---|---|---|"]
    gesehen: set[str] = set()
    for kennung, klartext, angabe in lies_schwerpunkt_zeilen(wurzel):
        if kennung in gesehen:
            continue
        gesehen.add(kennung)
        spalte = angabe if angabe in DISZIPLIN_SPALTE else "beide"
        zeilen.append(f"| `{kennung}` | {klartext} | {spalte} |")
    return zeilen


def schreibe_auftrag(sammelimport: Sammelimport, k: Kandidat, kennungen: list[str]) -> Path:
    """Legt den Auftrag für einen Kandidaten an, alles, was der Agent braucht.

    Die Pfade stehen absolut da, denn der Agent liest und schreibt mit ihnen.
    `quelldatei:` steht relativ zu `quellen/`, so wie auf der Karte, damit sie
    auf jedem Rechner stimmt, egal wo dort der Arbeitsordner liegt.
    """
    quellen = sammelimport.wurzel / "quellen"
    relativ = [f"{sammelimport.ordner}/{d}" for d in k.dateien]
    teile = [
        f"# Auftrag für Kandidat {k.nummer}",
        "",
        f"- Quellenordner: `quellen/{sammelimport.ordner}/`",
        f"- Kandidat: {k.nummer}",
        f"- Was es ist: {k.was}",
        f"- Typ laut Zerlegungsplan: `{k.ergebnis}`",
        f"- `quelldatei:` `{', '.join(relativ)}`",
        f"- Zielpfad des Entwurfs: `{sammelimport.entwurf(k).as_posix()}`",
        "",
        "## Dateien",
        "",
        *(f"- `{(quellen / r).as_posix()}`" for r in relativ),
        "",
        "## Absprachen",
        "",
        sammelimport.absprachen or "Keine.",
        "",
        "## Schwerpunkt-Kennungen",
        "",
        *kennungen,
        "",
    ]
    ziel = sammelimport.auftrag(k)
    ziel.write_text("\n".join(teile), encoding="utf-8")
    return ziel


def vorbereiten(wurzel: Path, ordner: str) -> int:
    sammelimport = Sammelimport(wurzel, ordner)
    sammelimport.verlange_freigabe()
    offen = [k for k in sammelimport.kandidaten
             if k.wartet and pruefe_entwurf(sammelimport.entwurf(k)).fehler]
    dran = offen[:sammelimport.je_durchgang]
    print(f"Aufträge für {len(dran)} von {len(offen)} offenen Kandidaten:")
    if not dran:
        return 0
    sammelimport.entwurfsordner.mkdir(parents=True, exist_ok=True)
    kennungen = kennungstabelle(wurzel)
    for k in dran:
        print(f"  {k.nummer}  {schreibe_auftrag(sammelimport, k, kennungen).as_posix()}")
    return 0


# --------------------------------------------------------------------------
# pruefen
# --------------------------------------------------------------------------

def setze_befund(k: Kandidat, befund: Befund) -> None:
    """Der Status eines Kandidaten, wie ihn sein Entwurf auf der Platte ergibt.

    `rückfrage` heißt: Hier muss einzeln gefragt werden, weil der Entwurf für
    mindestens eine Rückfrage keine Vermutung hat. Eine Rückfrage mit Vermutung
    bestätigt der Trainer in der Tabelle wie einen Vorschlag.
    """
    if befund.fehler:
        k.setze("offen", befund.fehler)
    elif befund.ohne_vermutung:
        anzahl = befund.ohne_vermutung
        k.setze("rückfrage", f"{anzahl} Rückfrage{'n' if anzahl > 1 else ''} ohne Vermutung")
    else:
        k.setze("bereit")


def pruefen(wurzel: Path, ordner: str) -> int:
    sammelimport = Sammelimport(wurzel, ordner)
    sammelimport.verlange_freigabe()
    stand: dict[str, int] = {}
    for k in sammelimport.kandidaten:
        if not k.wartet:
            continue
        setze_befund(k, pruefe_entwurf(sammelimport.entwurf(k)))
        stand[k.status] = stand.get(k.status, 0) + 1
        print(f"  {k.nummer}  {k.status}{': ' + k.notiz if k.notiz else ''}")
    sammelimport.speichere()
    print(", ".join(f"{s} {stand.get(s, 0)}" for s in ("bereit", "rückfrage", "offen")))
    return 0


# --------------------------------------------------------------------------
# uebernehmen
# --------------------------------------------------------------------------

UMLAUTE = str.maketrans({"ä": "ae", "ö": "oe", "ü": "ue", "ß": "ss"})


def slug(titel: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", titel.lower().translate(UMLAUTE)).strip("-")


def naechste_id(wurzel: Path) -> str:
    """Die höchste ID in `uebungen/` plus eins, so wie das Datenmodell es sagt.

    Gelesen wird bei jedem Aufruf neu, unmittelbar vor dem Schreiben. Hat
    Nextcloud inzwischen eine Karte von einem anderen Rechner gebracht, zählt
    sie schon mit. Gezählt werden Dateiname und `id:`, denn der Linter meldet
    eine Karte, bei der beide auseinanderlaufen, und bis dahin soll keine der
    beiden Nummern ein zweites Mal vergeben werden.
    """
    hoechste = 0
    for pfad in (wurzel / "uebungen").glob("*.md"):
        nummern = [pfad.name]
        try:
            felder, _ = lies_frontmatter(pfad)
            nummern.append(str(felder.get("id") or ""))
        except (OSError, UnicodeDecodeError):
            pass
        for text in nummern:
            m = re.match(ID_MUSTER, text)
            if m:
                hoechste = max(hoechste, int(m.group()[len("ue-"):]))
    return f"ue-{hoechste + 1:04d}"


def als_karte(entwurf: str, uid: str, heute: str) -> str:
    """Aus dem Text eines Kartenentwurfs der Text der Karte.

    `id` kommt als erstes Feld dazu, `angelegt` wird der Tag der Freigabe.
    `## Freigabe` fällt weg: Vorschläge und Rückfragen sind mit dem Ja des
    Trainers erledigt und gehören nicht auf die Karte in der Halle. Dass das
    Frontmatter sauber schließt, hat `pruefe_entwurf` vorher festgestellt.
    """
    zeilen = entwurf.splitlines()
    ende = _frontmatter_ende(zeilen)
    if ende is None:
        raise ValueError("Kartenentwurf ohne geschlossenes Frontmatter")
    felder = [z for z in zeilen[1:ende] if not re.match(r"id\s*:", z)]
    datum = f"angelegt: {heute}"
    felder = [datum if re.match(r"angelegt\s*:", z) else z for z in felder]
    if datum not in felder:
        felder.append(datum)

    rumpf = zeilen[ende + 1:]
    grenzen = _abschnitt_grenzen(rumpf, "Freigabe")
    if grenzen is not None:
        rumpf = rumpf[:grenzen[0]] + rumpf[grenzen[1]:]
    while rumpf and not rumpf[-1].strip():
        rumpf.pop()
    return "\n".join(["---", f"id: {uid}", *felder, "---", *rumpf]) + "\n"


def uebernimm(sammelimport: Sammelimport, k: Kandidat, notiz: str) -> str:
    """Schreibt die Karte eines freigegebenen Kandidaten. Gibt ihre ID zurück.

    Die Reihenfolge ist Absicht. Erst die Karte, dann sofort die Übersicht,
    zuletzt Entwurf und Auftrag löschen. Bricht der Lauf dazwischen ab, liegt
    höchstens ein Entwurf zu viel herum. Stünde die Übersicht zuletzt, fände
    der nächste Lauf einen offenen Kandidaten mit gültigem Entwurf und schriebe
    dieselbe Karte ein zweites Mal.
    """
    entwurf = sammelimport.entwurf(k)
    felder, _ = lies_frontmatter(entwurf)
    uid = naechste_id(sammelimport.wurzel)
    ziel = sammelimport.wurzel / "uebungen" / f"{uid}-{slug(str(felder['titel']))}.md"
    text = als_karte(entwurf.read_text(encoding="utf-8"), uid, date.today().isoformat())
    # "x" legt nur neu an. Eine Datei unter dieser ID gibt es laut
    # naechste_id() nicht, und falls doch, wird sie nicht überschrieben.
    with ziel.open("x", encoding="utf-8") as datei:
        datei.write(text)
    k.setze("importiert", notiz, karte=uid)
    sammelimport.speichere()
    entwurf.unlink()
    sammelimport.auftrag(k).unlink(missing_ok=True)
    return uid


def pruefe_fuer_uebernahme(sammelimport: Sammelimport, k: Kandidat | None) -> str | None:
    """Warum ein Kandidat nicht übernommen werden kann, oder None.

    Prüft wie `pruefen` und setzt auch wie `pruefen`: Ein Entwurf, der die
    Prüfung nicht mehr besteht, geht zurück auf `offen`, mit dem Grund in der
    Notiz. Dann entwirft ihn der nächste Durchgang neu.
    """
    if k is None:
        return "steht nicht in der Übersicht"
    if not k.wartet:
        return f"ist {k.status}, nicht offen"
    befund = pruefe_entwurf(sammelimport.entwurf(k))
    if befund.fehler:
        setze_befund(k, befund)
        sammelimport.speichere()
    return befund.fehler


def uebernehmen(wurzel: Path, ordner: str, freigegeben: list[tuple[str, str]]) -> int:
    sammelimport = Sammelimport(wurzel, ordner)
    sammelimport.verlange_freigabe()
    if not freigegeben:
        raise Abbruch("Kein Kandidat genannt. Je Kandidat: --kandidat <nr> \"<notiz>\"")
    nach_nummer = {k.nummer: k for k in sammelimport.kandidaten}

    nicht_uebernommen = 0
    for nummer, notiz in freigegeben:
        k = nach_nummer.get(nummer)
        grund = pruefe_fuer_uebernahme(sammelimport, k)
        if grund or k is None:
            print(f"  {nummer}  nicht übernommen: {grund}")
            nicht_uebernommen += 1
            continue
        print(f"  {nummer}  importiert als {uebernimm(sammelimport, k, notiz)}")

    # Der Linter prüft die ganze Bibliothek, nicht nur die neuen Karten. Was
    # er meldet, steht damit vor dem Trainer, solange der Durchgang frisch ist.
    print()
    warnungen = hole_index(wurzel)["warnungen"]
    if warnungen:
        print(f"{len(warnungen)} Auffälligkeit(en) im Linter:")
        for zeile in warnungen:
            print(f"  - {zeile}")
    else:
        print("Linter: Keine Auffälligkeiten.")

    if not any(k.wartet for k in sammelimport.kandidaten):
        raeume_entwurfsordner_weg(sammelimport)
        print(f"Nichts mehr offen, {ENTWUERFE}/{ordner}/ ist weg.")
    return 1 if nicht_uebernommen else 0


def raeume_entwurfsordner_weg(sammelimport: Sammelimport) -> None:
    """Löscht `kartenentwuerfe/<ordner>/`, dazu leer gewordene Ordner darüber.

    `kartenentwuerfe/` selbst bleibt. Er ist leer, solange kein Sammelimport
    läuft (ADR-0010).
    """
    ordner = sammelimport.entwurfsordner
    shutil.rmtree(ordner, ignore_errors=True)
    oben = sammelimport.wurzel / ENTWUERFE
    ordner = ordner.parent
    while ordner != oben and ordner.is_dir() and not any(ordner.iterdir()):
        ordner.rmdir()
        ordner = ordner.parent


def quellenordner(angabe: str) -> str:
    """Der Quellenordner relativ zu `quellen/`, auch wenn er mit `quellen/` davor kommt.

    So nennt ihn der Trainer: „Sammelimport über quellen/playdrill". Gemeint
    ist derselbe Ordner wie mit `playdrill`.
    """
    ordner = Path(angabe).as_posix().strip("/")
    return ordner[len("quellen/"):] if ordner.startswith("quellen/") else ordner


def main() -> int:
    konsole_vorbereiten()
    ap = argparse.ArgumentParser(description="Sammelimport über einen Quellenordner")
    ap.add_argument("--wurzel", type=Path, default=None)
    befehle = ap.add_subparsers(dest="befehl", required=True)
    hilfe = "der Quellenordner, relativ zu quellen/"
    vor = befehle.add_parser("vorbereiten", help="Aufträge für die nächsten Kandidaten anlegen")
    vor.add_argument("ordner", type=quellenordner, help=hilfe)
    pr = befehle.add_parser("pruefen", help="den Status aus den Entwürfen auf der Platte setzen")
    pr.add_argument("ordner", type=quellenordner, help=hilfe)
    ue = befehle.add_parser("uebernehmen", help="freigegebene Kandidaten als Karte übernehmen")
    ue.add_argument("ordner", type=quellenordner, help=hilfe)
    ue.add_argument("--kandidat", nargs=2, action="append", default=[],
                    metavar=("NR", "NOTIZ"),
                    help="ein freigegebener Kandidat und was der Trainer geändert hat")
    a = ap.parse_args()

    wurzel = a.wurzel.resolve() if a.wurzel else finde_wurzel()
    try:
        if a.befehl == "pruefen":
            return pruefen(wurzel, a.ordner)
        if a.befehl == "uebernehmen":
            return uebernehmen(wurzel, a.ordner, [tuple(p) for p in a.kandidat])
        return vorbereiten(wurzel, a.ordner)
    except Abbruch as fehler:
        print(fehler)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
