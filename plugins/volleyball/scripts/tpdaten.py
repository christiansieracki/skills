"""Gemeinsame Bausteine fuer index.py, suche.py und leseansicht.py.

Nur Standardbibliothek, damit die Skripte ueberall laufen, wo Python 3 da ist.
Das Frontmatter wird mit einem kleinen eigenen Parser gelesen statt mit PyYAML,
weil das Format bewusst schmal gehalten ist: Schluessel, einfache Werte,
Listen in eckigen Klammern.
"""

from __future__ import annotations

import json
import os
import re
import socket
import sys
from dataclasses import dataclass
from pathlib import Path

from szene import ENDUNG as SZENE_ENDUNG
from szene import SzeneFehler, bild_zur_szene, lies_szene

MARKER = "trainingsplanung-root.yml"

ELEMENTE = {
    "annahme", "zuspiel", "angriff", "block", "abwehr", "aufschlag",
    "ballkontrolle", "athletik", "koordination",
}
DISZIPLINEN = {"halle", "beach"}

# Was in der Disziplinspalte von schwerpunkte.md stehen darf, und wofuer es
# steht. `beide` gibt es nur hier: auf der Karte ist die Disziplin eine Liste,
# in einer Tabellenzelle waere eine Liste unlesbar.
DISZIPLIN_SPALTE = {
    "halle": {"halle"},
    "beach": {"beach"},
    "beide": set(DISZIPLINEN),
}
SPIELPHASEN = {"sideout", "break", "keine"}
FORMEN = {"erwaermung", "technik", "komplex", "spielform", "station", "abschluss"}
LEVEL = ["einsteiger", "fortgeschritten", "ambitioniert"]
TYPEN = {"uebung", "folge"}

# Die Felder im Frontmatter einer Uebungskarte, in der Reihenfolge aus
# DATENMODELL.md. Der Linter verlangt sie nicht alle, der Sammelimport von
# jedem Kartenentwurf schon, ausser `id` und `angelegt`: die setzt erst die
# Freigabe.
KARTENFELDER = [
    "id", "titel", "typ", "disziplin", "element", "spielphase", "form", "schwerpunkt",
    "level_min", "level_max", "spieler_min", "spieler_max", "dauer_min", "dauer_max",
    "spielflaechen", "netz", "erwachsenenbelastung", "belastungshinweis", "material",
    "schaubild", "quelle", "quelldatei", "variante_von", "autor", "angelegt",
]

# Das Muster einer Uebungs-ID, wie DATENMODELL.md es festlegt: zwei Ziffern fuer
# die Nummer des Trainers, vier laufend (ADR-0011). Es steht einmal da, weil
# mehrere Stellen danach fragen: der Linter, die Suche nach Verweisen im Text,
# das Schaubild, das zu einem Basisnamen die Karte sucht, und die naechste ID.
ID_MUSTER = r"ue-\d{6}"

# Eine ID, wie sie bis 2.5.1 vergeben wurde. Gilt nicht mehr: der Linter meldet
# sie, die naechste ID verweigert sich, solange es sie gibt, und
# ids_umstellen.py macht aus ihr eine sechsstellige. Mit `\b` auf beiden
# Seiten trifft es `ue-000042` nicht, sonst fuehrte ein zweiter Lauf des
# Umstellens die Nullen ein zweites Mal ein.
ALTE_ID_MUSTER = r"ue-\d{4}"

# Was in jeder Meldung zu einer vierstelligen ID steht.
HINWEIS_UMSTELLEN = "ids_umstellen.py stellt den Arbeitsordner auf sechs Stellen um"


@dataclass(frozen=True)
class Kartensorte:
    """Eine Sorte Karte in der Bibliothek: Uebungskarte oder Wissenskarte (ADR-0002).

    Jede Sorte liegt flach in ihrem eigenen Ordner, ihre ID hat ein eigenes
    Praefix vor denselben sechs Ziffern, und gezaehlt wird je Sorte getrennt
    (ADR-0011, Nachtrag zu ADR-0002). Wer Karten einliest, eine ID vergibt
    oder eine Karte prueft, bekommt die Sorte als Angabe, statt Ordner und
    Muster selbst zu kennen.

    `alte_muster` ist das Muster einer vierstelligen ID von vor 3.0.0. Die gab
    es nur bei Uebungen.
    """

    ordner: str
    praefix: str
    muster: str
    felder: tuple[str, ...]
    alte_muster: str | None = None


UEBUNGSKARTE = Kartensorte("uebungen", "ue", ID_MUSTER, tuple(KARTENFELDER), ALTE_ID_MUSTER)

# Die Wissenskarte (ADR-0002 mit Nachtrag, #61): Hintergrund aus einer
# Fremdquelle, eine Frage je Karte, und die Frage ist ihr Titel. Ihre Felder in
# der Reihenfolge aus DATENMODELL.md. Pflicht sind titel, thema, disziplin und
# quelle; schwerpunkt und uebungen sind freiwillig. Bilder stehen als Verweis
# im Text, ein Feld `schaubild` gibt es nicht, eines fuer Alter oder Level auch
# nicht.
WISSENSFELDER = [
    "id", "titel", "thema", "schwerpunkt", "disziplin", "uebungen",
    "quelle", "quelldatei", "autor", "angelegt",
]

# Die Werte von `thema`, fest im Datenmodell wie `element`. Kein Trainer
# erweitert sie selbst. Technik und Taktik kamen im Nachtrag zu ADR-0002
# dazu, sonst haetten die Merkmale des oberen Zuspiels kein Thema.
THEMEN = {
    "trainingslehre", "methodik", "psychologie", "physiologie",
    "ernaehrung", "regelkunde", "technik", "taktik",
}

# Die beiden Abschnitte, die jede Wissenskarte hat, als `## <Titel>`.
WISSENSABSCHNITTE = ["Kernaussagen", "Was das fürs Training heißt"]

# Wie ID_MUSTER, mit dem Praefix der Wissenskarte. Der Bereich ist derselbe,
# der Zaehler ein eigener.
WISSEN_ID_MUSTER = r"wi-\d{6}"

WISSENSKARTE = Kartensorte("wissen", "wi", WISSEN_ID_MUSTER, tuple(WISSENSFELDER))

SORTEN = (UEBUNGSKARTE, WISSENSKARTE)


def sorte_der_id(uid) -> Kartensorte | None:
    """Die Sorte, zu deren Muster eine ID passt, oder None.

    Eine vierstellige ID von vor 3.0.0 gehoert zu ihrer Sorte, auch wenn sie
    nicht mehr gilt.
    """
    for sorte in SORTEN:
        for muster in (sorte.muster, sorte.alte_muster):
            if muster and re.fullmatch(muster, str(uid)):
                return sorte
    return None


def disziplin_text(eintrag: dict) -> str:
    """Die Disziplin einer Karte, wie ein Mensch sie zu sehen bekommt.

    Die Trefferliste der Suche und die Lesebrille `index.md` zeigen dasselbe,
    damit eine Beachuebung in beiden Ansichten gleich aussieht. Fehlt das Feld,
    steht hier ein Strich. Der Linter meldet so eine Karte ohnehin, daran soll
    die Ausgabe nicht scheitern.
    """
    return ", ".join(eintrag.get("disziplin") or []) or "—"


def als_liste(wert) -> list:
    """Ein Listenfeld als Liste, auch wenn die eckigen Klammern fehlen.

    Ohne sie liest der Parser einen Text. Der Linter meldet das. Wer das Feld
    nur anzeigt, `index.md` oder die Suche, soll daran nicht jeden Buchstaben
    als eigenen Wert aufzaehlen. Fehlt das Feld, ist die Liste leer.
    """
    if wert is None or wert == "":
        return []
    return wert if isinstance(wert, list) else [wert]


def schaubilder(wert) -> list[str]:
    """Die Dateinamen in `schaubild:`, in ihrer Reihenfolge.

    Das Feld traegt einen Namen oder eine Liste davon, etwa bei einem Zirkel
    aus Uebersichtsblatt und Stationsblaettern je Blatt ein Bild (#39). Wer
    es liest, der Linter, die Leseansicht, die Suche und der Sammelimport,
    bekommt hier immer eine Liste. Leer ist sie, wenn das Feld fehlt oder
    `null` ist.
    """
    if wert is None or wert == "":
        return []
    if isinstance(wert, list):
        return [str(name) for name in wert if name not in (None, "")]
    return [str(wert)]


# --------------------------------------------------------------------------
# Konsole
# --------------------------------------------------------------------------

def konsole_vorbereiten() -> None:
    """Sorgt dafuer, dass die Ausgabe auch auf Windows-Konsolen durchkommt.

    Die Skripte schreiben Umlaute, Halbgeviertstriche und das Warnzeichen fuer
    Uebungen mit Erwachsenenbelastung. Unter Windows steht stdout haeufig auf
    cp1252, und das Warnzeichen laesst sich dort nicht kodieren: jeder Aufruf,
    der eine solche Uebung anzeigt, stirbt sonst mit UnicodeEncodeError.
    Deshalb hier auf UTF-8 umstellen, mit errors="replace" als Netz fuer
    Konsolen, die auch damit nicht klarkommen.
    """
    for strom in (sys.stdout, sys.stderr):
        try:
            strom.reconfigure(encoding="utf-8", errors="replace")
        except (AttributeError, ValueError, OSError):
            pass


def interpreter() -> str:
    """Nennt den Aufruf, mit dem dieses Skript gerade laeuft.

    Unter Windows kommt `python` heraus, sonst `python3` oder die genaue
    Fassung wie `python3.12`. Hinweise in der Ausgabe nehmen diesen Namen,
    damit der Leser ihn kopieren kann: `python3` zeigt unter Windows auf den
    Platzhalter aus dem Microsoft Store und bricht ab, bevor ein Skript
    startet.
    """
    return Path(sys.executable).stem or "python3"


# --------------------------------------------------------------------------
# Wurzel finden
# --------------------------------------------------------------------------

def suche_wurzel(start: Path | None = None) -> Path | None:
    """Sucht ab `start` aufwaerts nach der Markerdatei, ohne abzubrechen.

    Damit ist es egal, wie der Ordner heisst und wo er liegt, solange
    trainingsplanung-root.yml mitwandert.

    Fuer die Stellen, an denen ein fehlender Arbeitsordner kein Fehler ist,
    sondern nur heisst, dass es hier nichts nachzuschlagen gibt. Wer ihn
    wirklich braucht, nimmt `finde_wurzel()` und bekommt die Meldung.
    """
    p = (start or Path.cwd()).resolve()
    for kandidat in [p, *p.parents]:
        if (kandidat / MARKER).is_file():
            return kandidat
    return None


def finde_wurzel(start: Path | None = None) -> Path:
    """Sucht den Arbeitsordner und bricht ab, wenn keiner da ist."""
    wurzel = suche_wurzel(start)
    if wurzel is None:
        raise SystemExit(
            f"Keine {MARKER} gefunden. Das Skript aus dem Trainingsplanungs-Ordner\n"
            f"heraus starten oder den Pfad mit --wurzel angeben."
        )
    return wurzel


# --------------------------------------------------------------------------
# Frontmatter
# --------------------------------------------------------------------------

_SKALAR = re.compile(r"^(?P<key>[a-z_]+):\s*(?P<val>.*)$")


def _wert(roh: str):
    roh = roh.strip()
    if "#" in roh and not roh.startswith(('"', "'")):
        roh = roh.split("#", 1)[0].strip()
    if roh in ("", "null", "~"):
        return None
    if roh in ("true", "false"):
        return roh == "true"
    if roh.startswith("[") and roh.endswith("]"):
        inner = roh[1:-1].strip()
        if not inner:
            return []
        return [_wert(t) for t in inner.split(",")]
    if len(roh) >= 2 and roh[0] == roh[-1] and roh[0] in "\"'":
        return roh[1:-1]
    if re.fullmatch(r"-?\d+", roh):
        return int(roh)
    return roh


def lies_frontmatter(pfad: Path) -> tuple[dict, str]:
    """Gibt (frontmatter, rumpf) zurueck. Ohne Frontmatter: ({}, ganzer Text)."""
    text = pfad.read_text(encoding="utf-8")
    if not text.startswith("---"):
        return {}, text
    teile = text.split("---", 2)
    if len(teile) < 3:
        return {}, text
    fm: dict = {}
    for zeile in teile[1].splitlines():
        if not zeile.strip() or zeile.lstrip().startswith("#"):
            continue
        m = _SKALAR.match(zeile.strip())
        if m:
            fm[m.group("key")] = _wert(m.group("val"))
    return fm, teile[2]


def tabellenzellen(zeile: str) -> list[str]:
    """Die Zellen einer Zeile aus einer Markdown-Tabelle, ohne Leerraum drumherum.

    Wie bei GitHub trennt ein `\\|` keine Zellen, in der Zelle steht dann `|`.
    """
    innen = zeile.strip()
    innen = innen[1:] if innen.startswith("|") else innen
    innen = innen[:-1] if innen.endswith("|") and not innen.endswith("\\|") else innen
    return [z.strip().replace("\\|", "|") for z in re.split(r"(?<!\\)\|", innen)]


# --------------------------------------------------------------------------
# Einlesen
# --------------------------------------------------------------------------

# Die Marken, mit denen der Nextcloud-Client eine Konfliktkopie benennt,
# nachgesehen am 03.10.2026 in src/common/utility.cpp des Clients. Die Marke
# steht vor der letzten Endung: aus `plan.md` wird
# `plan (conflicted copy 2026-10-03 101500).md`, mit dem Namen des Nutzers vor
# dem Datum, wenn der Client ihn kennt. Klammern in diesem Namen ersetzt der
# Client, die Marke endet also an der ersten schliessenden Klammer. Aeltere
# Clients schrieben `plan_conflict-20261003-101500.md`. `(case clash from ...)`
# bekommt eine Datei, die neben einer zweiten mit demselben Namen in anderer
# Schreibung keinen Platz hat, etwa unter Windows.
KONFLIKTMARKE = re.compile(
    r" \((?:conflicted copy|case clash from) [^()]*\)|_conflict-\d{8}-\d{6}")


def ausgelassen(pfad: Path) -> bool:
    """Eine Datei unter uebungen/ oder trainings/, die keine Karte und kein Plan ist.

    Eine Vorlage mit `_` vorn, die README und eine Konfliktkopie. Die
    Konfliktkopie meldet der Linter, gelesen wird sie nicht: Sonst stuende
    eine Uebung zweimal in der Suche, und ein Training zaehlte doppelt.
    """
    return (pfad.name.startswith("_") or pfad.name.upper() == "README.MD"
            or KONFLIKTMARKE.search(pfad.name) is not None)


_KENNUNG = re.compile(r"`([a-z0-9-]+)`")


def lies_schwerpunkte(wurzel: Path) -> tuple[dict[str, set[str]], list[str]]:
    """Zieht aus schwerpunkte.md, welche Kennung fuer welche Disziplin gilt.

    Zurueck kommt die Zuordnung und nicht mehr nur die Menge der Kennungen:
    die Pruefung auf eine Hallenkarte mit einem Beachschwerpunkt braucht zu
    jeder Kennung die Disziplinen, fuer die sie gedacht ist. Dazu die
    Auffaelligkeiten der Datei selbst.

    Eine leere dritte Spalte gilt fuer beide Disziplinen, schraenkt also keine
    Karte ein. Das trifft die Steuerungsschwerpunkte, die die Spalte nicht
    fuehren, und eine von Hand nachgetragene Zeile, die sie vergessen hat.
    Beide sollen erlaubt bleiben, statt als unbekannte Kennung zu gelten.

    Ein Wert, den es nicht gibt, ist etwas anderes und wird gemeldet. Sonst
    schaltete ein Tippfehler in der von Hand gepflegten Datei still genau die
    Pruefung ab, fuer die die Spalte da ist.
    """
    gefunden: dict[str, set[str]] = {}
    warnungen: list[str] = []
    for kennung, _klartext, disziplin_angabe in lies_schwerpunkt_zeilen(wurzel):
        if disziplin_angabe and disziplin_angabe not in DISZIPLIN_SPALTE:
            warnungen.append(
                f"schwerpunkte.md: {kennung} traegt die Disziplin "
                f"{disziplin_angabe!r}, die es nicht gibt"
            )
        gefunden[kennung] = DISZIPLIN_SPALTE.get(disziplin_angabe, set(DISZIPLINEN))
    return gefunden, warnungen


def lies_schwerpunkt_zeilen(wurzel: Path) -> list[tuple[str, str, str]]:
    """Die Zeilen aus schwerpunkte.md: Kennung, Klartext, Disziplinspalte.

    Die Spalten kommen so, wie sie in der Datei stehen, die Disziplin also noch
    nicht aufgeloest und auch leer. Was sie bedeutet, sagt `lies_schwerpunkte`.
    Der Klartext ist fuer den, der eine Kennung waehlen muss, ohne die Datei
    vor sich zu haben: den Agenten im Sammelimport.
    """
    datei = wurzel / "schwerpunkte.md"
    if not datei.is_file():
        return []
    zeilen: list[tuple[str, str, str]] = []
    for zeile in datei.read_text(encoding="utf-8").splitlines():
        if not zeile.strip().startswith("|"):
            continue
        spalten = [s.strip() for s in zeile.strip().strip("|").split("|")]
        m = _KENNUNG.fullmatch(spalten[0])
        if not m:
            continue
        klartext = spalten[1] if len(spalten) > 1 else ""
        disziplin_angabe = spalten[2] if len(spalten) > 2 else ""
        zeilen.append((m.group(1), klartext, disziplin_angabe))
    return zeilen


def lies_uebungen(wurzel: Path) -> list[dict]:
    """Die Uebungskarten aus uebungen/, wie `lies_karten` sie liest."""
    return lies_karten(wurzel, UEBUNGSKARTE)


def lies_karten(wurzel: Path, sorte: Kartensorte) -> list[dict]:
    """Die Karten einer Sorte aus ihrem Ordner, je Karte ihr Frontmatter.

    Dazu `datei`, der Pfad relativ zur Wurzel, und `_rumpf`, der Text unter
    dem Frontmatter. Eine Karte ohne `id` faellt weg, ebenso eine Vorlage, die
    README und eine Konfliktkopie. Fehlt der Ordner, gibt es keine Karte: Ein
    Arbeitsordner aus der Zeit vor der Wissenskarte hat kein wissen/.
    """
    karten = []
    ordner = wurzel / sorte.ordner
    if not ordner.is_dir():
        return karten
    for pfad in sorted(ordner.glob("*.md")):
        if ausgelassen(pfad):
            continue
        fm, rumpf = lies_frontmatter(pfad)
        if not fm.get("id"):
            continue
        fm["datei"] = pfad.relative_to(wurzel).as_posix()
        fm["_rumpf"] = rumpf
        karten.append(fm)
    return karten


# --------------------------------------------------------------------------
# Die naechste ID
# --------------------------------------------------------------------------

class KeineId(Exception):
    """Fuer diesen Rechner gibt es keine ID. Der Text sagt, warum."""


def rechnername() -> str:
    """Der Name, unter dem dieser Rechner in `trainer:` steht.

    Unter Windows ist das der Geraetename. Auf dem Rechner selbst wird nichts
    gespeichert: Wer welche Nummer hat, steht fuer alle sichtbar in der
    Wurzeldatei.
    """
    return socket.gethostname()


# Der Name eines Eintrags in der Wurzeldatei: eines Trainers unter
# `trainer:` oder das Kuerzel einer Gruppe unter `gruppen:`, etwa `h1-h2`.
# Dazu die Zeilen, mit denen die beiden Abschnitte beginnen.
# ids_umstellen.py schreibt einen Trainer mit seinem Abschnitt, deshalb stehen
# die Muster einmal hier.
EINTRAGSNAME = r"[^\s:#]+"
TRAINER_ABSCHNITT = re.compile(r"trainer:\s*(#.*)?$")
GRUPPEN_ABSCHNITT = re.compile(r"gruppen:\s*(#.*)?$")
_EINTRAGSZEILE = re.compile(rf"(?P<name>{EINTRAGSNAME}):\s*(#.*)?$")


def _lies_eintraege(wurzel: Path, abschnitt: re.Pattern) -> dict[str, dict] | None:
    """Ein Abschnitt der Wurzeldatei aus benannten Eintraegen, je Eintrag seine Felder.

    None, wenn es den Abschnitt nicht gibt. Ein Abschnitt ohne Eintrag ergibt
    ein leeres Woerterbuch.

    Gelesen wird nur dieser eine Abschnitt, mit dem schmalen Parser des
    Frontmatters: Er beginnt mit der Zeile, auf die `abschnitt` passt, am
    Zeilenanfang und endet an der naechsten Zeile, die wieder dort beginnt.
    Eine Liste steht in eckigen Klammern, eine aus `- ` Zeilen wird auch
    verstanden, weil die Wurzeldatei von Hand gepflegt wird.
    """
    datei = wurzel / MARKER
    if not datei.is_file():
        return None
    zeilen = datei.read_text(encoding="utf-8").splitlines()
    anfang = next((i for i, z in enumerate(zeilen) if abschnitt.match(z)), None)
    if anfang is None:
        return None
    eintraege: dict[str, dict] = {}
    eintrag: dict | None = None
    feld = ""
    einzug_der_namen = None
    for zeile in zeilen[anfang + 1:]:
        inhalt = zeile.strip()
        if not inhalt or inhalt.startswith("#"):
            continue
        einzug = len(zeile) - len(zeile.lstrip())
        if einzug == 0:
            break
        einzug_der_namen = einzug_der_namen or einzug
        if einzug == einzug_der_namen:
            m = _EINTRAGSZEILE.match(inhalt)
            eintrag = eintraege.setdefault(m.group("name"), {}) if m else None
            continue
        if eintrag is None:
            continue
        if inhalt.startswith("- ") and feld:
            if not isinstance(eintrag.get(feld), list):
                eintrag[feld] = []
            eintrag[feld].append(_wert(inhalt[2:]))
            continue
        m = _SKALAR.match(inhalt)
        if m:
            feld = m.group("key")
            eintrag[feld] = _wert(m.group("val"))
    return eintraege


def lies_trainer(wurzel: Path) -> dict[str, dict] | None:
    """Der Abschnitt `trainer:` der Wurzeldatei: je Trainer `nummer` und `rechner`.

    None, wenn es den Abschnitt nicht gibt. Ein Abschnitt ohne Eintrag, wie
    ihn init_struktur.py anlegt, ergibt ein leeres Woerterbuch. `rechner`
    steht in eckigen Klammern oder als Liste aus `- ` Zeilen.
    """
    return _lies_eintraege(wurzel, TRAINER_ABSCHNITT)


def lies_gruppen(wurzel: Path) -> dict[str, dict] | None:
    """Der Abschnitt `gruppen:` der Wurzeldatei: je Gruppe nach Kuerzel ihre Felder.

    Gebraucht wird bisher nur `name`, den die Leseansicht statt des Kuerzels
    zeigt. Gelesen wird wie `trainer:`, mit demselben schmalen Parser. None,
    wenn es den Abschnitt nicht gibt.
    """
    return _lies_eintraege(wurzel, GRUPPEN_ABSCHNITT)


def _nummer(wert) -> str | None:
    """Die Nummer eines Trainers als zwei Ziffern, oder None, wenn sie keine ist.

    Ohne Anfuehrungszeichen liest der Parser `00` als Zahl 0. Auch das ist
    gemeint, die fuehrende Null kommt hier wieder dazu.
    """
    if isinstance(wert, int) and not isinstance(wert, bool) and 0 <= wert <= 99:
        return f"{wert:02d}"
    if isinstance(wert, str) and re.fullmatch(r"\d{2}", wert):
        return wert
    return None


def _rechner(eintrag: dict) -> set[str]:
    """Die Rechner eines Trainers, klein geschrieben. Ein einzelner Wert zaehlt als Liste."""
    rechner = eintrag.get("rechner")
    if not isinstance(rechner, list):
        rechner = [rechner] if rechner else []
    return {str(r).lower() for r in rechner if r}


def trainer_dieses_rechners(wurzel: Path) -> str:
    """Der Name, unter dem der Trainer dieses Rechners unter `trainer:` steht.

    Erkannt wird der Rechner an seinem Namen, ohne Ruecksicht auf Gross- und
    Kleinschreibung. Steht er bei keinem Trainer oder bei mehreren, gibt es
    keinen, und damit auch keine ID: KeineId.

    Die Meldung nennt den Rechner, die eingetragenen Trainer und die Nummer,
    die ein neuer bekaeme. Damit kann der Import-Skill fragen, wer da sitzt.
    """
    rechner = rechnername()
    abschnitt = lies_trainer(wurzel)
    trainer = abschnitt or {}
    treffer = [name for name, e in trainer.items() if rechner.lower() in _rechner(e)]
    if not treffer:
        nummern = {name: _nummer(e.get("nummer")) for name, e in trainer.items()}
        vergeben = [int(n) for n in nummern.values() if n is not None]
        neue = f"{max(vergeben) + 1:02d}" if vergeben else "00"
        eingetragen = ", ".join(f"{name} ({nummern[name] or '?'})" for name in trainer)
        grund = (f"In {MARKER} fehlt der Abschnitt trainer:." if abschnitt is None
                 else f"Unter trainer: in {MARKER} steht er bei niemandem.")
        raise KeineId(
            f"Der Rechner {rechner} gehoert zu keinem Trainer. {grund}\n"
            f"Eingetragen: {eingetragen or 'niemand'}. "
            f"Ein neuer Trainer bekaeme die Nummer {neue}."
        )
    if len(treffer) > 1:
        raise KeineId(f"Der Rechner {rechner} steht bei mehreren Trainern unter trainer: "
                      f"in {MARKER}: {', '.join(treffer)}.")
    return treffer[0]


def trainernummer(wurzel: Path) -> str:
    """Die Nummer des Trainers, der an diesem Rechner sitzt.

    Gibt es keinen Trainer dieses Rechners, oder teilt sich sein Trainer die
    Nummer mit einem anderen, gibt es keine: dann vergaeben zwei Rechner aus
    demselben Bereich, und genau das soll die Nummer verhindern.
    """
    name = trainer_dieses_rechners(wurzel)
    trainer = lies_trainer(wurzel) or {}
    nummern = {anderer: _nummer(e.get("nummer")) for anderer, e in trainer.items()}
    nummer = nummern[name]
    if nummer is None:
        raise KeineId(f"Die Nummer von {name} unter trainer: in {MARKER} ist keine "
                      f"zweistellige Zahl: {trainer[name].get('nummer')!r}.")
    gleiche = [anderer for anderer, seine in nummern.items()
               if seine == nummer and anderer != name]
    if gleiche:
        raise KeineId(f"Die Nummer {nummer} tragen unter trainer: in {MARKER} "
                      f"{name} und {', '.join(gleiche)}. Jeder Trainer braucht seine eigene.")
    return nummer


def naechste_id(wurzel: Path, sorte: Kartensorte = UEBUNGSKARTE) -> str:
    """Die naechste ID fuer den Trainer dieses Rechners: die hoechste in seinem Bereich plus eins.

    Der Bereich sind die IDs mit seiner Nummer vorn. Zwei Trainer vergeben so
    nie dieselbe ID, auch wenn Nextcloud ihre Rechner noch nicht abgeglichen
    hat (ADR-0011). Gezaehlt wird je Sorte fuer sich, im Ordner der Sorte und
    nur IDs mit ihrem Praefix: `wi-000001` ist die erste Wissenskarte und
    nicht irgendeine Nummer nach den Uebungen.

    Gelesen wird bei jedem Aufruf neu, unmittelbar vor dem Schreiben. Hat
    Nextcloud inzwischen eine Karte von einem anderen Rechner desselben
    Trainers gebracht, zaehlt sie schon mit. Gezaehlt werden Dateiname und
    `id:`, denn der Linter meldet eine Karte, bei der beide auseinanderlaufen,
    und bis dahin soll keine der beiden Nummern ein zweites Mal vergeben werden.

    Steht in `uebungen/` noch eine vierstellige ID, gibt es keine neue Uebung.
    Sonst bekaeme eine neue Karte `ue-000042`, und `ue-0042` wuerde beim
    Umstellen zu derselben. Wissenskarten gab es vierstellig nie, ihre
    Nummern kann das Umstellen nicht treffen.
    """
    vergeben: set[str] = set()
    vierstellig: list[str] = []
    for pfad in sorted((wurzel / sorte.ordner).glob("*.md")):
        kennungen = [pfad.name]
        try:
            felder, _ = lies_frontmatter(pfad)
            kennungen.append(str(felder.get("id") or ""))
        except (OSError, UnicodeDecodeError):
            pass
        for text in kennungen:
            if sorte.alte_muster and re.match(rf"{sorte.alte_muster}\b", text):
                vierstellig.append(pfad.name)
            m = re.match(rf"{sorte.muster}\b", text)
            if m:
                vergeben.add(m.group())
    if vierstellig:
        raise KeineId(f"{sorte.ordner}/ hat noch vierstellige IDs, etwa {vierstellig[0]}. "
                      f"Erst umstellen: {HINWEIS_UMSTELLEN}. Steht unter trainer: "
                      f"noch niemand, traegt es dabei diesen Rechner ein, {rechnername()}.")
    nummer = trainernummer(wurzel)
    # Die Nummer des Trainers steht direkt hinter Praefix und Strich.
    vorn = len(sorte.praefix) + 1
    laufend = [int(uid[-4:]) for uid in vergeben if uid[vorn:vorn + 2] == nummer]
    hoechste = max(laufend, default=0)
    if hoechste >= 9999:
        raise KeineId(f"Im Bereich {nummer} ist keine Nummer mehr frei.")
    return f"{sorte.praefix}-{nummer}{hoechste + 1:04d}"


def lies_trainings(wurzel: Path) -> list[dict]:
    einheiten = []
    ordner = wurzel / "trainings"
    if not ordner.is_dir():
        return einheiten
    for pfad in sorted(ordner.rglob("*.md")):
        if ausgelassen(pfad):
            continue
        fm, rumpf = lies_frontmatter(pfad)
        fm["datei"] = pfad.relative_to(wurzel).as_posix()
        fm["verwendet"] = sorted(set(re.findall(rf"\b{ID_MUSTER}\b", rumpf)))
        fm["vierstellig"] = sorted(set(re.findall(rf"\b{ALTE_ID_MUSTER}\b", rumpf)))
        einheiten.append(fm)
    return einheiten


# --------------------------------------------------------------------------
# Index bauen
# --------------------------------------------------------------------------

SCHLANK = [
    "id", "titel", "typ", "disziplin", "element", "spielphase", "form", "schwerpunkt",
    "level_min", "level_max", "spieler_min", "spieler_max",
    "dauer_min", "dauer_max", "spielflaechen", "netz",
    "erwachsenenbelastung", "belastungshinweis", "material",
    "variante_von", "schaubild", "quelle", "quelldatei", "autor", "datei",
]

# Was der Index von einer Wissenskarte fuehrt, wie SCHLANK von der Uebung:
# das Frontmatter ohne `angelegt`, dazu die Datei. Der Text bleibt auf der
# Karte.
SCHLANK_WISSEN = [
    "id", "titel", "thema", "schwerpunkt", "disziplin", "uebungen",
    "quelle", "quelldatei", "autor", "datei",
]


def baue_index(wurzel: Path) -> dict:
    """Der Index: die Uebungen mit ihrem Einsatz, die Wissenskarten und was der Linter meldet.

    Die Wissenskarten stehen unter `wissen`, getrennt von den Uebungen. Jede
    Uebung traegt unter `hintergrund` die IDs der Wissenskarten, deren
    `uebungen` sie nennen. Diese Gegenrichtung pflegt niemand auf der
    Uebungskarte (#61), sie entsteht hier bei jedem Bau neu.
    """
    karten = lies_uebungen(wurzel)
    wissenskarten = lies_karten(wurzel, WISSENSKARTE)
    trainings = lies_trainings(wurzel)
    schwerpunkte, schwerpunkt_warnungen = lies_schwerpunkte(wurzel)

    # Einsatzhistorie aus den Trainingsplaenen, statt sie auf den Karten zu pflegen.
    # Dieselbe Schleife merkt sich, welche Plaene eine Karte nennen: Welche
    # Leseansicht ein neues Bild veraltet, entscheidet dieselbe Regel wie der
    # Einsatz (#76), und eine zweite soll nicht neben ihr entstehen.
    einsaetze: dict[str, list[str]] = {}
    plaene: dict[str, list[str]] = {}
    for t in trainings:
        datum = str(t.get("datum") or "")
        for uid in t.get("verwendet", []):
            einsaetze.setdefault(uid, []).append(datum)
            plaene.setdefault(uid, []).append(t["datei"])

    # Ohne eckige Klammern ist `uebungen` ein Text. Das meldet der Linter,
    # hier zaehlt so eine Karte bei keiner Uebung mit.
    hintergrund: dict[str, set[str]] = {}
    for wk in wissenskarten:
        uebungen = wk.get("uebungen")
        for uid in uebungen if isinstance(uebungen, list) else []:
            hintergrund.setdefault(str(uid), set()).add(str(wk["id"]))

    bekannt = {k["id"] for k in karten}
    eintraege = []
    for k in karten:
        e = {f: k.get(f) for f in SCHLANK}
        hist = sorted(x for x in einsaetze.get(k["id"], []) if x)
        e["eingesetzt"] = hist
        e["zuletzt"] = hist[-1] if hist else None
        e["anzahl_einsaetze"] = len(hist)
        e["plaene"] = sorted(plaene.get(k["id"], []))
        e["hintergrund"] = sorted(hintergrund.get(str(k["id"]), ()))
        eintraege.append(e)

    warnungen = schwerpunkt_warnungen + pruefe(
        wurzel, karten, wissenskarten, trainings, schwerpunkte, bekannt
    )
    return {
        "wurzel": str(wurzel),
        "anzahl": len(eintraege),
        "uebungen": eintraege,
        "wissen": [{f: wk.get(f) for f in SCHLANK_WISSEN} for wk in wissenskarten],
        "warnungen": warnungen,
    }


def pruefe(wurzel: Path, karten, wissenskarten, trainings, schwerpunkte, bekannt) -> list[str]:
    """Der Linter: was an den Karten beider Sorten und an den Plaenen nicht stimmt.

    `bekannt` sind die IDs in uebungen/. Auf sie duerfen Plaene, `variante_von`
    und die `uebungen` einer Wissenskarte zeigen.
    """
    w: list[str] = []
    gesehen: dict[str, str] = {}

    for k in karten:
        befunde, am_platz = _pruefe_id(k, UEBUNGSKARTE, gesehen)
        if am_platz:
            befunde += pruefe_felder(k, schwerpunkte, bekannt)
            # Ein toter Bildverweis faellt sonst nirgends auf: die Leseansicht
            # laesst das Bild still weg, und gemerkt wird es erst in der Halle am
            # Blatt ohne Bild. Bei einer Liste steht jedes fehlende Bild einzeln
            # da, denn jedes fehlt fuer sich.
            for bild in schaubilder(k.get("schaubild")):
                if not (wurzel / "schaubilder" / bild).is_file():
                    befunde.append(f"schaubild zeigt auf {bild}, das es unter schaubilder/ nicht gibt")
        w += [f"{k['datei']}: {befund}" for befund in befunde]

    for k in wissenskarten:
        befunde, am_platz = _pruefe_id(k, WISSENSKARTE, gesehen)
        if am_platz:
            befunde += pruefe_wissensfelder(k, schwerpunkte, bekannt)
            befunde += pruefe_wissensrumpf(k["_rumpf"], wurzel / Path(k["datei"]).parent)
        w += [f"{k['datei']}: {befund}" for befund in befunde]

    for t in trainings:
        for uid in t.get("verwendet", []):
            if uid not in bekannt:
                w.append(f"{t['datei']}: verweist auf {uid}, das es in uebungen/ nicht gibt")
        # Eine Zeile je Plan und nicht je ID: vor dem Umstellen nennt jeder
        # Plan mehrere, und alle haben dieselbe Ursache.
        if t.get("vierstellig"):
            w.append(f"{t['datei']}: nennt noch vierstellige IDs "
                     f"({', '.join(t['vierstellig'])}), {HINWEIS_UMSTELLEN}")

    w += pruefe_szenen(wurzel)
    w += pruefe_konfliktkopien(wurzel)
    return w


def _pruefe_id(k: dict, sorte: Kartensorte, gesehen: dict[str, str]) -> tuple[list[str], bool]:
    """Was an der ID einer Karte nicht stimmt, und ob die Karte im Ordner ihrer Sorte liegt.

    `gesehen` merkt sich ueber beide Sorten, in welcher Datei eine ID schon
    stand. Traegt die Karte die ID der anderen Sorte, bleibt es bei dieser
    einen Meldung: Mit den Regeln des falschen Ordners geprueft, meldete sie
    jedes Feld, das die andere Sorte nicht hat.
    """
    kid, datei = k["id"], k["datei"]
    w: list[str] = []
    if kid in gesehen:
        w.append(f"id {kid} gibt es schon in {gesehen[kid]}")
    gesehen[kid] = datei

    andere = sorte_der_id(kid)
    if andere is not None and andere is not sorte:
        w.append(f"id {kid} hat das Muster {andere.praefix}-######, "
                 f"die Karte gehoert nach {andere.ordner}/")
        return w, False
    if sorte.alte_muster and re.fullmatch(sorte.alte_muster, str(kid)):
        w.append(f"id {kid} ist noch vierstellig, {HINWEIS_UMSTELLEN}")
    elif not re.fullmatch(sorte.muster, str(kid)):
        w.append(f"id {kid} passt nicht zum Muster {sorte.praefix}-######")
    if not str(Path(datei).name).startswith(str(kid)):
        w.append(f"Dateiname beginnt nicht mit der id {kid}")
    return w, True


def pruefe_szenen(wurzel: Path) -> list[str]:
    """Was an den Szenen in schaubilder/ nicht stimmt.

    Gelesen wird jede Szene, gezeichnet keine. Mit mehreren Trainern aendert
    einer die Szene, und keiner zeichnet neu (#47). Dass sie nicht mehr
    aufgeht, faellt sonst erst dem auf, der das naechste Mal zeichnen will.
    """
    w: list[str] = []
    for szene in sorted((wurzel / "schaubilder").glob(f"*{SZENE_ENDUNG}")):
        datei = szene.relative_to(wurzel).as_posix()
        try:
            lies_szene(szene.read_text(encoding="utf-8"))
        except SzeneFehler as fehler:
            w.append(f"{datei}: {fehler}")
            continue
        bild = bild_zur_szene(szene)
        aufruf = f"{interpreter()} schaubild.py {bild.stem}"
        if not bild.is_file():
            w.append(f"{datei}: {bild.name} fehlt, zeichnen mit {aufruf}")
        # Nextcloud gibt einer Datei beim Abgleich die Zeit mit, zu der sie
        # geschrieben wurde. Was ein anderer Trainer an der Szene geaendert
        # hat, ist darum auch hier juenger als das Bild aus der Zeit davor.
        elif bild.stat().st_mtime < szene.stat().st_mtime:
            w.append(f"{datei}: {bild.name} ist aelter als die Szene, "
                     f"neu zeichnen mit {aufruf}")
    return w


def pruefe_konfliktkopien(wurzel: Path) -> list[str]:
    """Jede Konfliktkopie im Arbeitsordner, auch unter quellen/.

    Aendern zwei Trainer dieselbe Datei, behaelt der Server eine Fassung unter
    dem alten Namen und der Client legt die andere daneben (#47). Gemerkt
    wird das sonst nie: Was in der Kopie steht, liest kein Skript.
    """
    w: list[str] = []
    for pfad in sorted(wurzel.rglob("*")):
        # Eine Kopie einer Kopie traegt zwei Marken. Wie der Client selbst
        # zaehlt die hintere, uebrig bleibt dann die erste Kopie.
        marken = list(KONFLIKTMARKE.finditer(pfad.name))
        if not marken or not pfad.is_file():
            continue
        marke = marken[-1]
        original = pfad.name[:marke.start()] + pfad.name[marke.end():]
        datei = pfad.relative_to(wurzel).as_posix()
        # Bei einem case clash sind es zwei Dateien und nicht zwei Fassungen
        # einer Datei. Zusammenzufuehren ist da nichts.
        if marke.group().startswith(" (case clash"):
            w.append(f"{datei}: auf dem Server liegt daneben {original} in anderer "
                     f"Gross- und Kleinschreibung, eine der beiden umbenennen")
        else:
            w.append(f"{datei}: Konfliktkopie von Nextcloud zu {original}, "
                     f"beide zusammenfuehren und die Kopie loeschen")
    return w


def pruefe_felder(k: dict, schwerpunkte: dict[str, set[str]], bekannt: set[str]) -> list[str]:
    """Was an den Feldern einer Karte nicht stimmt, ohne die Datei davor.

    Die kontrollierten Werte aus DATENMODELL.md und was sich sonst an den
    Feldern einer einzelnen Karte ablesen laesst. Was den Ort der Karte
    braucht, ihren Dateinamen oder ihr Schaubild in schaubilder/, prueft
    `pruefe` selbst.

    Der Linter setzt die Datei davor. `sammelimport.py pruefen` prueft damit
    einen Kartenentwurf, bevor er Karte wird, mit denselben Regeln. Was die
    Pruefung dort besteht, hat dem Linter an seinen Feldern nichts zu melden.
    """
    w: list[str] = []
    if k.get("typ") not in TYPEN:
        w.append(f"typ {k.get('typ')!r} ist weder uebung noch folge")

    # Pflichtfeld ohne stillen Default: faellt es weg, muss es auffallen.
    # Ein Default legte eine beim Import vergessene Beachuebung wortlos
    # unter Halle ab, und dort findet sie nie wieder jemand.
    befunde, gueltige_disziplinen = _pruefe_pflichtliste(k, "disziplin", DISZIPLINEN)
    w += befunde

    w += _ohne_klammern(k, "element", "schwerpunkt")
    element = k.get("element")
    for el in element if isinstance(element, list) else []:
        if el not in ELEMENTE:
            w.append(f"element {el!r} steht nicht in der Liste")
    if k.get("spielphase") not in SPIELPHASEN:
        w.append(f"spielphase {k.get('spielphase')!r} ist unbekannt")
    if k.get("form") not in FORMEN:
        w.append(f"form {k.get('form')!r} ist unbekannt")

    w += _pruefe_schwerpunkte(k, schwerpunkte, gueltige_disziplinen)

    for feld in ("level_min", "level_max"):
        v = k.get(feld)
        if v is None:
            w.append(f"{feld} ist leer")
        elif v not in LEVEL:
            w.append(f"{feld} {v!r} ist kein gueltiges Level")

    lo, hi = k.get("spieler_min"), k.get("spieler_max")
    if isinstance(lo, int) and isinstance(hi, int) and lo > hi:
        w.append(f"spieler_min {lo} ist groesser als spieler_max {hi}")
    lo, hi = k.get("dauer_min"), k.get("dauer_max")
    if isinstance(lo, int) and isinstance(hi, int) and lo > hi:
        w.append(f"dauer_min {lo} ist groesser als dauer_max {hi}")

    if k.get("erwachsenenbelastung") and not (k.get("belastungshinweis") or "").strip():
        w.append("erwachsenenbelastung ist gesetzt, aber belastungshinweis ist leer")

    vv = k.get("variante_von")
    if vv and vv not in bekannt:
        w.append(f"variante_von zeigt auf {vv}, das es nicht gibt")
    if not k.get("quelle"):
        w.append("quelle fehlt")
    return w


def pruefe_wissensfelder(k: dict, schwerpunkte: dict[str, set[str]],
                         bekannt: set[str]) -> list[str]:
    """Was am Frontmatter einer Wissenskarte nicht stimmt, ohne die Datei davor.

    Das Gegenstueck zu `pruefe_felder` fuer die zweite Sorte. Was den Ort der
    Karte braucht, ID und Dateiname, prueft `pruefe` selbst, den Text
    `pruefe_wissensrumpf`. `bekannt` sind die IDs in uebungen/.

    Der Linter setzt die Datei davor. Der Sammelimport prueft damit den
    Entwurf einer Wissenskarte, bevor er Karte wird, mit denselben Regeln.
    """
    w: list[str] = []
    titel = str(k.get("titel") or "").strip()
    if not titel:
        w.append("titel fehlt")
    elif not titel.endswith("?"):
        # Die Karte beantwortet eine Frage, und die Frage ist ihr Titel.
        w.append(f"titel {titel!r} endet nicht auf ein Fragezeichen")
    w += _pruefe_pflichtliste(k, "thema", THEMEN)[0]
    befunde, gueltige_disziplinen = _pruefe_pflichtliste(k, "disziplin", DISZIPLINEN)
    w += befunde
    # Ein Steuerungsschwerpunkt hat in schwerpunkte.md keine Disziplinspalte
    # und gilt damit fuer beide. Auf der Wissenskarte ist er erlaubt, mit ihm
    # findet der Saisonplaner sie zu einem Trainingsblock (ADR-0002).
    w += _ohne_klammern(k, "schwerpunkt", "uebungen")
    w += _pruefe_schwerpunkte(k, schwerpunkte, gueltige_disziplinen)

    # Die Gegenrichtung, welche Wissenskarten auf eine Uebung zeigen, pflegt
    # niemand auf der Uebungskarte. Sie stimmt nur, solange jede ID hier eine
    # Uebung trifft.
    uebungen = k.get("uebungen")
    for uid in uebungen if isinstance(uebungen, list) else []:
        if uid not in bekannt:
            w.append(f"uebungen nennt {uid}, das es in uebungen/ nicht gibt")
    if not str(k.get("quelle") or "").strip():
        w.append("quelle fehlt oder ist leer")
    return w


# Ein Bildverweis in Markdown: `![Text](pfad)`, auch `![Text](<pfad mit leerzeichen>)`
# und mit Titel dahinter, `![Text](pfad "Titel")`.
_BILDVERWEIS = re.compile(
    r"!\[[^\]]*\]\(\s*(?:<(?P<spitz>[^>]*)>|(?P<pfad>[^)\s]+))(?:\s+(?:\"[^\"]*\"|'[^']*'))?\s*\)")

# Eine Adresse im Netz statt einer Datei, etwa `https:`. Mindestens zwei
# Zeichen vor dem Doppelpunkt, sonst gaelte das Laufwerk `C:` als eine.
_ADRESSE = re.compile(r"[a-z][a-z0-9+.-]+:", re.I)


def bildverweise(rumpf: str) -> list[str]:
    """Die Pfade der Bildverweise im Text einer Karte, in ihrer Reihenfolge.

    So, wie Markdown sie aufloest: relativ zum Ordner der Karte, `%20` als
    Leerzeichen. Auf einer Wissenskarte in wissen/ heisst das
    `../schaubilder/<datei>`, im Entwurf der Name der Quellgrafik daneben.
    """
    from urllib.parse import unquote
    return [unquote(m.group("spitz") if m.group("spitz") is not None else m.group("pfad"))
            for m in _BILDVERWEIS.finditer(rumpf)]


def pruefe_wissensrumpf(rumpf: str, ordner: Path) -> list[str]:
    """Was am Text einer Wissenskarte nicht stimmt: die beiden Abschnitte und die Bilder.

    `ordner` ist der Ordner, in dem die Karte liegt, gegen ihn wird ein
    Bildverweis aufgeloest wie in jeder Markdown-Ansicht. Im Linter ist es
    wissen/, im Sammelimport der Ordner des Entwurfs. Eine Adresse im Netz
    ist keine Datei und wird nicht nachgesehen.
    """
    w = [f"Abschnitt ## {titel} fehlt" for titel in WISSENSABSCHNITTE
         if not re.search(rf"^##[ \t]+{re.escape(titel)}[ \t]*$", rumpf, re.M)]
    # Ein toter Bildverweis faellt sonst nirgends auf: Die Markdown-Ansicht
    # zeigt an seiner Stelle nichts oder nur den Text in den Klammern.
    for pfad in bildverweise(rumpf):
        if not _ADRESSE.match(pfad) and not (ordner / pfad).is_file():
            w.append(f"Bildverweis {pfad} zeigt auf eine Datei, die es nicht gibt")
    return w


def _ohne_klammern(k: dict, *felder: str) -> list[str]:
    """Ein Listenfeld, das ohne eckige Klammern dasteht.

    Der Parser liest dann einen Text. Darueber zu laufen hiesse, jeden
    Buchstaben als Element oder Kennung zu melden.
    """
    return [f"{feld} {k[feld]!r} steht nicht in eckigen Klammern"
            for feld in felder if k.get(feld) and not isinstance(k[feld], list)]


def _pruefe_schwerpunkte(k: dict, schwerpunkte: dict[str, set[str]],
                         gueltige_disziplinen: set[str]) -> list[str]:
    """Die Kennungen in `schwerpunkt`: aus schwerpunkte.md, und passend zur Disziplin der Karte.

    Fuer beide Sorten gleich. Ohne schwerpunkte.md gibt es nichts zu
    vergleichen, ohne eckige Klammern meldet das `_ohne_klammern`.
    """
    w: list[str] = []
    schwerpunkt = k.get("schwerpunkt")
    if not schwerpunkte or not isinstance(schwerpunkt, list):
        return w
    for s in schwerpunkt:
        if s not in schwerpunkte:
            w.append(f"schwerpunkt {s!r} steht nicht in schwerpunkte.md")
            continue
        # Eine Disziplin der Karte reicht: eine Karte fuer beides darf
        # einen Schwerpunkt tragen, den es nur in einer Disziplin gibt.
        # Traegt die Karte gar keine gueltige Disziplin, steht das
        # schon oben, und zweimal dasselbe zu melden hilft niemandem.
        if gueltige_disziplinen and not (schwerpunkte[s] & gueltige_disziplinen):
            w.append(
                f"schwerpunkt {s!r} gilt nur fuer "
                f"{', '.join(sorted(schwerpunkte[s]))}, die Karte fuer "
                f"{', '.join(sorted(gueltige_disziplinen))}"
            )
    return w


def _pruefe_pflichtliste(k: dict, feld: str, erlaubt: set[str]) -> tuple[list[str], set[str]]:
    """Ein Pflichtfeld, das eine Liste aus festen Werten traegt: Befunde und die gueltigen Werte.

    Ohne stillen Default: faellt das Feld weg, muss es auffallen. Ohne
    eckige Klammern liest der Parser einen Text, darueber zu laufen hiesse,
    jeden Buchstaben als Wert zu melden. Die gueltigen Werte braucht, wer
    weiter mit ihnen prueft, etwa die Schwerpunkte gegen die Disziplin.
    """
    wert = k.get(feld)
    if not wert:
        return [f"{feld} fehlt oder ist leer"], set()
    if not isinstance(wert, list):
        return [f"{feld} {wert!r} steht nicht in eckigen Klammern"], set()
    befunde = [f"{feld} {x!r} steht nicht in der Liste" for x in wert if x not in erlaubt]
    return befunde, {x for x in wert if x in erlaubt}


def cache_pfad(wurzel: Path) -> Path:
    """index.json liegt bewusst NICHT in Nextcloud.

    Sonst schreibt bei mehreren Trainern jeder Lauf dieselbe Datei neu und der
    Sync legt Konfliktkopien an. Der Index ist jederzeit neu baubar.
    """
    import hashlib
    import tempfile
    kennung = hashlib.sha1(str(wurzel).encode("utf-8")).hexdigest()[:10]
    ordner = Path(tempfile.gettempdir()) / "trainingsplanung-index"
    ordner.mkdir(parents=True, exist_ok=True)
    return ordner / f"index-{kennung}.json"


def hole_index(wurzel: Path) -> dict:
    daten = baue_index(wurzel)
    cache_pfad(wurzel).write_text(
        json.dumps(daten, ensure_ascii=False, indent=1), encoding="utf-8"
    )
    return daten
