#!/usr/bin/env python3
"""Führt einen Sammelimport über einen Quellenordner, Kandidat für Kandidat.

    <python> sammelimport.py vorbereiten --plan <ordner>
    <python> sammelimport.py vorbereiten <ordner> [--trotzdem]
    <python> sammelimport.py pruefen <ordner> [--json]
    <python> sammelimport.py uebernehmen <ordner> --kandidat 3 "Notiz" ...
                 --uebersprungen 4 "Grund" ... --ergaenzt 5 ue-000027 ...

`<ordner>` ist der Quellenordner, relativ zu `quellen/`. In ihm liegt die
`sammelimport.md` mit den Einstellungen im Frontmatter, den Absprachen und der
Übersicht, dem freigegebenen Zerlegungsplan mit dem Stand je Kandidat.

`vorbereiten --plan` legt vor dem Zerlegungsplan die Planeingabe an: jede
Datei, die noch in keiner Zeile der Übersicht steht und die `ohne:` nicht
auslässt, bei PDFs ihr Text, dazu die nächste freie Kandidatennummer und die
Bibliotheksliste. Ein zweiter Lauf über denselben Ordner nimmt so nur, was neu
ist, und zählt weiter. Den Text liest `pdftotext`, wenn es da ist (ADR-0008).

`vorbereiten` legt unter `kartenentwuerfe/<ordner>/` die Aufträge für die
nächsten offenen Kandidaten an, mit dem Text jedes PDF und der Angabe, ob der
Ablauf aus dem Bild kommt, und trägt in `in_arbeit` ein, welcher Trainer
daran arbeitet. Arbeitet laut Eintrag ein anderer daran, geht es nur mit
`--trotzdem` weiter. Wenn die Einstellungen es wollen, schneidet es
daneben aus jedem PDF mit Bild die Quellgrafik aus, dafür braucht es Pillow
(ADR-0005). `pruefen` setzt den Status aus den Kartenentwürfen, die dort auf
der Platte liegen, und weist ab, was das Datenmodell bricht oder die Form der
Freigabe nicht einhält. Mit `--json` gibt es aus, was die Freigabe im Chat
braucht. `uebernehmen` macht aus freigegebenen Entwürfen Karten in `uebungen/`,
erst jetzt mit ID (ADR-0010), und legt die Quellgrafiken als ihre Schaubilder ab.
Ein freigegebener Entwurf, der die Prüfung nicht besteht, bleibt mit seinem
Status stehen. Gestrichene und ergänzende Kandidaten bekommen nur ihren Status.
Ist nichts mehr offen, löscht es `in_arbeit`.

Nach der Freigabe des Plans schreibt nur noch dieses Skript in die Übersicht.
Mehrere Agenten entwerfen parallel, und keiner von ihnen fasst sie an.
"""

from __future__ import annotations

import argparse
import io
import json
import os
import re
import shutil
import subprocess
import sys
import unicodedata
import zlib
from dataclasses import dataclass, field
from datetime import date
from functools import cache, cached_property
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from bilder_aufbereiten import SCHWELLE, bilder, menschenmass  # noqa: E402
from bilder_aufbereiten import kandidaten as bilder_nach_gewicht  # noqa: E402
from tpdaten import (  # noqa: E402
    DISZIPLIN_SPALTE, KARTENFELDER, TYPEN, KeineId, finde_wurzel, hole_index, interpreter,
    konsole_vorbereiten, lies_frontmatter, lies_schwerpunkt_zeilen, lies_schwerpunkte,
    lies_uebungen, naechste_id, pruefe_felder, schaubilder, trainer_dieses_rechners,
)

SAMMELIMPORT = "sammelimport.md"
ENTWUERFE = "kartenentwuerfe"
PLANEINGABE = "planeingabe.md"
JE_DURCHGANG = 30

# Bis hierhin kommt der Text aller PDFs ganz in die Planeingabe, gezählt in
# Zeichen, rund 100 000 Tokens. So viel liest der Agent für den Zerlegungsplan
# in einem Aufruf, neben Bibliotheksliste und Regeln. Der ganze Ordner
# quellen/playdrill hat 310 000 Zeichen in 343 PDFs, gemessen am 30.09.2026,
# und passt. Darüber bekommt jede Datei nur ihre ersten Zeilen, bis
# ERSTE_ZEILEN_BIS Zeichen. 400 Zeichen haben im Probelauf für die Gruppierung
# gereicht. Warum mehr als die ersten Zeilen: Nachtrag zu ADR-0008.
GANZER_TEXT_BIS = 400_000
ERSTE_ZEILEN_BIS = 400

# Weniger Zeichen Ablauf als hier, und der Ablauf kommt aus dem Bild (#29).
# Was als Ablauf zählt, sagt ablauftext().
WENIG_TEXT = 150

# Der Anfang der Zeile im Auftrag, die `pruefen` wieder liest.
AUS_DEM_BILD = "Ablauf aus dem Bild"

# Die Anfänge der Zeilen im Auftrag, die ein PDF nennen, aus dem sich keine
# Quellgrafik ausschneiden ließ. Auch die liest `pruefen` wieder.
KEINE_AUSGESCHNITTEN = "- Quellgrafik: keine ausgeschnitten,"
KEINE_QUELLGRAFIK_AUS = "- Keine Quellgrafik aus"

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


@dataclass
class InArbeit:
    """Wer gerade am Quellenordner arbeitet, aus `in_arbeit: christian, 2026-10-02`."""

    trainer: str
    seit: str

    def ist_von(self, trainer: str) -> bool:
        """Steht dieser Trainer im Eintrag? Von Hand geschrieben auch groß."""
        return self.trainer.casefold() == trainer.casefold()


class Sammelimport:
    """Die `sammelimport.md` eines Quellenordners.

    Gelesen werden die Einstellungen und die Übersicht. Geschrieben werden nur
    die Zeilen der Übersicht und die Einstellung `in_arbeit`, alles andere in
    der Datei bleibt, wie es ist: Die Absprachen gehören dem Trainer.
    """

    def __init__(self, wurzel: Path, ordner: str) -> None:
        self.wurzel = wurzel
        self.ordner = ordner
        self.datei = self.quellordner / SAMMELIMPORT
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

    def verlange_aktuelle_einstellungen(self) -> None:
        """Bricht ab, wenn eine Einstellung noch unter ihrem alten Namen steht.

        Bis zum 02.10.2026 hieß die Einstellung zum Ausschneiden anders (#49).
        Ginge `vorbereiten` über den alten Namen hinweg, schnitte es still
        nichts aus, und die Karten kämen ohne Bild heraus.
        """
        if "feldbild_ausschneiden" in self.einstellungen:
            raise Abbruch(f"In quellen/{self.ordner}/{SAMMELIMPORT} steht noch "
                          f"feldbild_ausschneiden. Die Einstellung heißt jetzt "
                          f"quellgrafik_ausschneiden, benenn sie um.\n"
                          f"Es ist noch kein Auftrag geschrieben.")

    @property
    def in_arbeit(self) -> InArbeit | None:
        """Wer laut Einstellungen gerade am Quellenordner arbeitet, oder None (#40)."""
        wert = self.einstellungen.get("in_arbeit")
        if wert is None:
            return None
        trainer, _, seit = str(wert).partition(",")
        return InArbeit(trainer.strip(), seit.strip() or "unbekannt")

    # `setze_in_arbeit` und `loesche_in_arbeit` ändern die Zeile im
    # Frontmatter, geschrieben wird erst mit `speichere`. Die Zeile steht über
    # der Übersicht, deren Grenzen rücken also mit.

    def setze_in_arbeit(self, trainer: str) -> None:
        """Trägt den Trainer mit dem Datum von heute in `in_arbeit` ein."""
        wert = f"{trainer}, {date.today().isoformat()}"
        alt = self._einstellungszeile("in_arbeit")
        if alt is not None:
            self.zeilen[alt] = f"in_arbeit: {wert}"
        else:
            ende = _frontmatter_ende(self.zeilen)
            if ende is None:
                raise Abbruch(f"quellen/{self.ordner}/{SAMMELIMPORT} hat kein Frontmatter.\n"
                              f"Es ist noch kein Auftrag geschrieben.")
            self.zeilen.insert(ende, f"in_arbeit: {wert}")
            self.anfang, self.ende = self.anfang + 1, self.ende + 1
        self.einstellungen["in_arbeit"] = wert

    def loesche_in_arbeit(self) -> None:
        """Nimmt `in_arbeit` aus den Einstellungen."""
        alt = self._einstellungszeile("in_arbeit")
        if alt is not None:
            del self.zeilen[alt]
            self.anfang, self.ende = self.anfang - 1, self.ende - 1
        self.einstellungen["in_arbeit"] = None

    def _einstellungszeile(self, name: str) -> int | None:
        """Die Zeile im Frontmatter, auf der `name:` steht, oder None."""
        ende = _frontmatter_ende(self.zeilen) or 0
        return next((i for i in range(1, ende) if re.match(rf"{name}\s*:", self.zeilen[i])),
                    None)

    def speichere(self) -> None:
        """Schreibt die geänderten Zeilen der Übersicht zurück, dazu `in_arbeit`, sonst nichts.

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

    def _text_einstellung(self, name: str) -> str | None:
        wert = self.einstellungen.get(name)
        if wert is None:
            return None
        return str(wert).strip() or None

    @property
    def quellgrafik_ausschneiden(self) -> bool:
        wert = self.einstellungen.get("quellgrafik_ausschneiden")
        if wert is None:
            return False
        if not isinstance(wert, bool):
            raise Abbruch(f"quellgrafik_ausschneiden in quellen/{self.ordner}/{SAMMELIMPORT} "
                          f"ist {wert!r}, erwartet ist true oder false.")
        return wert

    @property
    def textmarke(self) -> str | None:
        """Ab hier beschreibt eine Quelle ihren Ablauf, bei PlayDrill `Ausführung:`."""
        return self._text_einstellung("textmarke")

    @property
    def platzhalter(self) -> str | None:
        """Was eine Quelle hinschreibt, wenn sie keinen Ablauf hat."""
        return self._text_einstellung("platzhalter")

    @cached_property
    def ohne(self) -> list[str]:
        """Was `vorbereiten --plan` im Quellenordner auslässt, relativ zu ihm (#40).

        Ein Ordner gilt mit allem darunter. Verglichen wird in einer
        Unicode-Form, aus demselben Grund wie in `neue_dateien`.

        Die Liste steht in eckigen Klammern. Eine aus `- `-Zeilen liest der
        Parser als leer, und still übergangen käme jede ausgelassene Datei
        wieder in die Planeingabe. Deshalb bricht das Skript dann ab.
        """
        wert = self.einstellungen.get("ohne")
        if wert is None:
            if self._blockliste("ohne"):
                raise Abbruch(f"ohne in quellen/{self.ordner}/{SAMMELIMPORT} steht als Liste "
                              f"aus `- `-Zeilen. Schreib sie in eckigen Klammern, etwa "
                              f"ohne: [Aufst_Pos_D, PLAYDRILL_IMPORT_LOG.md].")
            return []
        pfade = wert if isinstance(wert, list) else [wert]
        if not all(isinstance(p, str) for p in pfade):
            raise Abbruch(f"ohne in quellen/{self.ordner}/{SAMMELIMPORT} ist {wert!r}, "
                          f"erwartet ist eine Liste von Pfaden relativ zum Quellenordner.")
        return [_nfc(p.replace("\\", "/").strip("/")) for p in pfade if p.strip("/")]

    def _blockliste(self, name: str) -> bool:
        """Folgt im Frontmatter auf `name:` eine Zeile mit `- `?"""
        zeile = self._einstellungszeile(name)
        if zeile is None:
            return False
        folgende = [z.strip() for z in self.zeilen[zeile + 1:_frontmatter_ende(self.zeilen)]
                    if z.strip()]
        return bool(folgende) and folgende[0].startswith("- ")

    def ausgelassen(self, name: str) -> bool:
        """Lässt `ohne:` die Datei `name` aus, relativ zum Quellenordner und in NFC?"""
        return any(name == pfad or name.startswith(pfad + "/") for pfad in self.ohne)

    @property
    def absprachen(self) -> str:
        return "\n".join(_abschnitt(self.zeilen, "Absprachen") or []).strip()

    @property
    def quellordner(self) -> Path:
        return self.wurzel / "quellen" / self.ordner

    @property
    def entwurfsordner(self) -> Path:
        return self.wurzel / ENTWUERFE / self.ordner

    def entwurf(self, k: Kandidat) -> Path:
        return self.entwurfsordner / f"{k.nummer}.md"

    def auftrag(self, k: Kandidat) -> Path:
        return self.entwurfsordner / f"{k.nummer}.auftrag.md"

    def quellgrafik(self, k: Kandidat, nr: int | None = None) -> Path:
        """Wo eine Quellgrafik des Kandidaten liegt.

        Ohne Nummer die einzige, `17.quellgrafik.png`. Hat der Kandidat
        mehrere, etwa ein Zirkel mit einem Bild je Blatt, heißen sie
        `17.quellgrafik-1.png`, `17.quellgrafik-2.png` und so weiter (#39).
        """
        endung = "" if nr is None else f"-{nr}"
        return self.entwurfsordner / f"{k.nummer}.quellgrafik{endung}.png"

    def ist_quellgrafik_von(self, k: Kandidat, name: str) -> bool:
        """Ist `name` eine Quellgrafik dieses Kandidaten, einzeln oder mit Nummer?"""
        muster = rf"{re.escape(k.nummer)}\.quellgrafik(-[1-9]\d*)?\.png"
        return re.fullmatch(muster, name) is not None

    def quellgrafiken(self, k: Kandidat) -> list[Path]:
        """Die Quellgrafiken des Kandidaten, die neben dem Entwurf liegen."""
        if not self.entwurfsordner.is_dir():
            return []
        return sorted(p for p in self.entwurfsordner.iterdir()
                      if self.ist_quellgrafik_von(k, p.name))

    # Was die Prüfung eines Entwurfs aus dem Arbeitsordner braucht. Gelesen
    # wird einmal je Aufruf, nicht je Entwurf: Ein Durchgang hat 30, die
    # Bibliothek bei PlayDrill über 300 Karten.

    @cached_property
    def schwerpunkte(self) -> dict[str, set[str]]:
        """Je Kennung aus `schwerpunkte.md` die Disziplinen, für die sie gilt."""
        return lies_schwerpunkte(self.wurzel)[0]

    @cached_property
    def bekannt(self) -> set[str]:
        """Die IDs der Karten in `uebungen/`, für `variante_von` und `--ergaenzt`.

        Eine Karte, die `uebernehmen` schreibt, trägt `uebernimm` hier nach.
        """
        return {str(karte["id"]) for karte in lies_uebungen(self.wurzel)}


# --------------------------------------------------------------------------
# Der Kartenentwurf
# --------------------------------------------------------------------------

class Formfehler(Exception):
    """Ein Kartenentwurf, der nicht Karte werden kann. Der Text ist der Grund in der Notiz."""


# Damit endet jede Rückfrage, dahinter die Vermutung oder `keine`.
VERMUTUNG = "Vermutung im Entwurf:"

# Was ein Kartenentwurf im Frontmatter tragen muss: alles von der Karte, nur
# `id` und `angelegt` nicht. Die setzt `uebernehmen` bei der Freigabe.
ENTWURFSFELDER = [f for f in KARTENFELDER if f not in ("id", "angelegt")]


@dataclass
class Rueckfrage:
    """Eine Rückfrage aus `## Freigabe`. Ohne Vermutung ist `vermutung` None."""

    nr: int
    frage: str
    vermutung: str | None


@dataclass
class Vorschlag:
    """Ein Vorschlag aus `## Freigabe`: zu einem Feld oder zu einer Stelle im Text.

    `ziel` ist das Feld, oder bei einer Textstelle die Überschrift ihres
    Abschnitts samt `##`. `wo` sagt, wo im Abschnitt, etwa „Schritt 2“, und
    ist bei einem Feld leer. `text` ist die Begründung.
    """

    ziel: str
    wo: str
    text: str

    @property
    def zur_textstelle(self) -> bool:
        return self.ziel.startswith("#")


@dataclass
class Befund:
    """Was die Prüfung eines Kartenentwurfs ergeben hat.

    Besteht er nicht, steht in `fehler` der Grund, und der Rest bleibt leer.
    Sonst trägt der Befund, was die Freigabe im Chat braucht.
    """

    fehler: str | None = None
    felder: dict = field(default_factory=dict)
    vorschlaege: list[Vorschlag] = field(default_factory=list)
    rueckfragen: list[Rueckfrage] = field(default_factory=list)
    aus_dem_bild: bool = False

    @property
    def mit_vermutung(self) -> list[Rueckfrage]:
        return [r for r in self.rueckfragen if r.vermutung is not None]

    @property
    def ohne_vermutung(self) -> list[Rueckfrage]:
        return [r for r in self.rueckfragen if r.vermutung is None]


_LISTENKOPF = re.compile(r"^(Vorschläge|Rückfragen):\s*(.*)$")
_PUNKT = re.compile(r"^(?:-|\d+\.)\s+(.*)$")
_ZIEL = re.compile(r"`([^`]+)`(.*)")


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


_AUS_DEM_BILD_JA = re.compile(rf"^- {AUS_DEM_BILD}: ja\b", re.MULTILINE)


def _auftragstext(auftrag: Path) -> str:
    """Der Text eines Auftrags, leer, wenn es ihn nicht gibt oder er sich nicht lesen lässt."""
    try:
        return auftrag.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError):
        return ""


def laut_auftrag_aus_dem_bild(auftrag: Path) -> bool:
    """Hat `vorbereiten` in den Auftrag geschrieben, dass der Ablauf aus dem Bild kommt?

    Gelesen wird der Auftrag und nicht noch einmal die Quelle: Die Regel hat
    gegolten, als der Agent den Entwurf schrieb, und pdftotext muss für
    `pruefen` nicht da sein.
    """
    return bool(_AUS_DEM_BILD_JA.search(_auftragstext(auftrag)))


def laut_auftrag_ohne_quellgrafik(auftrag: Path, k: Kandidat) -> list[str]:
    """Die PDFs des Kandidaten, aus denen sich laut Auftrag keine Quellgrafik ausschneiden ließ.

    Gelesen wird der Auftrag, wie bei `laut_auftrag_aus_dem_bild`: Die
    Ausgabe von `vorbereiten` ist nach einem Abbruch weg, der Auftrag liegt
    bis zum Übernehmen da (#36). Ein PDF steht dort als `` `<datei>`: <grund> ``,
    siehe `lege_quellgrafiken_an`. Gesucht wird nach den Dateien des
    Kandidaten, in der Reihenfolge der Spalte Dateien, denn ein Dateiname
    kann selbst ein Komma oder einen Doppelpunkt tragen.
    """
    zeilen = [z for z in _auftragstext(auftrag).splitlines()
              if z.startswith((KEINE_AUSGESCHNITTEN, KEINE_QUELLGRAFIK_AUS))]
    return [d for d in k.dateien if _ist_pdf(d) and any(f"`{d}`: " in z for z in zeilen)]


def _unter_quellen(quellen: Path, wert: str) -> bool:
    """Ist `wert` eine Datei unter `quellen/`, auch nach dem Auflösen von `..`?"""
    pfad = quellen / wert
    return pfad.is_file() and pfad.resolve().is_relative_to(quellen.resolve())


def quelldateien(quellen: Path, wert: str) -> list[tuple[str, bool]]:
    """Die Dateien in `quelldatei:`, jede mit der Angabe, ob es sie unter quellen/ gibt.

    Getrennt wird am Komma. Danach werden benachbarte Teile wieder
    zusammengefügt, bis jedes Stück eine vorhandene Datei nennt, denn auch
    ein Dateiname kann ein Komma tragen (#40). Geht das nicht auf, gilt die
    Zerlegung mit den wenigsten Teilen ohne Datei, und Teile ohne Datei, die
    nebeneinander stehen, kommen wieder zusammen. Fehlt genau eine Datei,
    nennt eine Meldung so genau sie, mit Komma oder ohne, und nicht ein
    Bruchstück.
    """
    teile = wert.split(",")

    @cache
    def zerlege_ab(i: int) -> tuple[int, tuple[tuple[int, int, bool], ...]]:
        """Ab Teil `i`: wie viele Teile ohne Datei bleiben, und die Stücke als Bereiche."""
        if i == len(teile):
            return 0, ()
        moeglich = []
        for j in range(i + 1, len(teile) + 1):
            if _unter_quellen(quellen, ",".join(teile[i:j]).strip()):
                fehlend, rest = zerlege_ab(j)
                moeglich.append((fehlend, ((i, j, True), *rest)))
        # Teil `i` allein und ohne Datei. Ein leerer Teil, etwa hinter einem
        # Komma am Ende, zählt nicht.
        fehlend, rest = zerlege_ab(i + 1)
        moeglich.append((fehlend + 1, ((i, i + 1, False), *rest)) if teile[i].strip()
                        else (fehlend, rest))
        return min(moeglich, key=lambda m: m[0])

    bereiche: list[tuple[int, int, bool]] = []
    for i, j, da in zerlege_ab(0)[1]:
        if not da and bereiche and not bereiche[-1][2]:
            bereiche[-1] = (bereiche[-1][0], j, False)
        else:
            bereiche.append((i, j, da))
    return [(",".join(teile[i:j]).strip(), da) for i, j, da in bereiche]


def pruefe_quelldatei(wurzel: Path, wert: object) -> None:
    """Bricht mit Formfehler ab, wenn `quelldatei:` nicht auf Dateien unter quellen/ zeigt.

    Der Wert steht relativ zu quellen/, damit er auf jedem Rechner stimmt,
    egal wo dort der Arbeitsordner liegt. Ein absoluter Pfad wird abgewiesen,
    auch wenn er hier eine Datei trifft. Geprüft wird `anchor` und nicht
    `is_absolute()`, aus demselben Grund wie in `suche.py`.

    Bei zwei Seiten nennt der Wert beide, durch Komma getrennt. Wie er sich
    in Dateien zerlegt, sagt `quelldateien`. Der Wert bleibt ein Text.
    """
    if not wert:
        raise Formfehler("quelldatei fehlt")
    if not isinstance(wert, str):
        raise Formfehler(f"quelldatei {wert!r} ist kein Text, zwei Dateien stehen durch "
                         f"Komma getrennt")
    for datei, da in quelldateien(wurzel / "quellen", wert):
        if Path(datei).anchor:
            raise Formfehler(f"quelldatei {datei} ist absolut, erwartet ist ein Pfad "
                             f"relativ zu quellen/")
        if not da:
            raise Formfehler(f"quelldatei {datei} gibt es unter quellen/ nicht")


def pruefe_frontmatter(sammelimport: Sammelimport, k: Kandidat, felder: dict) -> None:
    """Bricht mit Formfehler ab, wenn das Frontmatter eines Entwurfs keine Karte ergibt.

    Die Felder prüft `pruefe_felder` aus tpdaten.py, dieselben Regeln wie
    der Linter. Eine Karte aus einem Entwurf, der hier besteht, hat dem
    Linter an ihren Feldern nichts zu melden. Gemeldet wird der erste
    Fehler, denn neu entworfen wird ohnehin der ganze Entwurf.
    """
    if "id" in felder:
        raise Formfehler(f"Entwurf trägt id: {felder['id']}, die ID vergibt erst uebernehmen")
    fehlend = [f for f in ENTWURFSFELDER if f not in felder]
    if fehlend:
        raise Formfehler(f"Frontmatter ohne {', '.join(fehlend)}")
    if not felder.get("titel"):
        raise Formfehler("titel ist leer")
    befunde = pruefe_felder(felder, sammelimport.schwerpunkte, sammelimport.bekannt)
    if befunde:
        raise Formfehler(befunde[0])
    pruefe_quelldatei(sammelimport.wurzel, felder.get("quelldatei"))
    # Im Entwurf nennt `schaubild:` die Quellgrafiken neben ihm, einzeln oder als
    # Liste, und nur die eigenen: `uebernehmen` trägt sie nach schaubilder/,
    # unter den Namen der Karte. Ein fremdes fehlte danach seinem Kandidaten,
    # und ein doppeltes ließe sich nur einmal verschieben.
    gesehen: set[str] = set()
    for name in schaubilder(felder.get("schaubild")):
        if not sammelimport.ist_quellgrafik_von(k, name):
            raise Formfehler(
                f"schaubild: nennt {name}, das ist keine Quellgrafik dieses Kandidaten "
                f"({sammelimport.quellgrafik(k).name}, bei mehreren "
                f"{sammelimport.quellgrafik(k, 1).name} und weiter)")
        if name in gesehen:
            raise Formfehler(f"schaubild: nennt {name} zweimal")
        gesehen.add(name)
        if not (sammelimport.entwurfsordner / name).is_file():
            raise Formfehler(f"Quellgrafik {name} liegt nicht neben dem Entwurf")


def lies_vorschlag(nr: int, text: str, felder: dict, ueberschriften: set[str]) -> Vorschlag:
    """Ein Vorschlag, getrennt nach Feld oder Textstelle, an seinem Ziel in Backticks.

    Die Form steht in DATENMODELL.md: `` `level_max`: Begründung `` oder
    `` `## Ablauf`, Schritt 2: Begründung ``. Ohne Ziel vorn fände der
    Vorschlag keine Spalte in der Tabelle. Ein Feld, das nicht im
    Frontmatter steht, auch nicht, und einen Abschnitt, den der Entwurf
    nicht hat, fände der Trainer nicht, wenn er nachsehen will.
    """
    treffer = _ZIEL.fullmatch(text)
    if not treffer:
        raise Formfehler(f"Vorschlag {nr} beginnt nicht mit einem Feld oder einer "
                         f"Überschrift in Backticks")
    ziel, rest = treffer.group(1).strip(), treffer.group(2).strip()
    if not ziel.startswith("#"):
        if ziel not in felder:
            raise Formfehler(f"Vorschlag {nr} nennt `{ziel}`, das steht nicht im Frontmatter")
        return Vorschlag(ziel, "", rest.lstrip(":,").strip())
    if ziel not in ueberschriften:
        raise Formfehler(f"Vorschlag {nr} nennt `{ziel}`, den Abschnitt hat der Entwurf nicht")
    rest = rest.lstrip(",").strip()
    wo, doppelpunkt, begruendung = rest.partition(":")
    if not doppelpunkt:
        wo, begruendung = "", rest
    return Vorschlag(ziel, wo.strip(), begruendung.strip())


def lies_rueckfrage(nr: int, text: str) -> Rueckfrage:
    """Eine Rückfrage, mit ihrer Vermutung oder ohne.

    Sie stellt genau eine Frage und endet auf `Vermutung im Entwurf: …`,
    oder auf `… keine`, wenn der Agent keine hat. Zwei Fragen in einer
    ließen sich in der Tabelle nicht mit einem Ja beantworten. Gezählt wird
    das Fragezeichen über die ganze Rückfrage, und es muss vor der Vermutung
    stehen.
    """
    frage, marke, vermutung = text.rpartition(VERMUTUNG)
    if not marke or not vermutung.strip():
        raise Formfehler(f"Rückfrage {nr} endet nicht auf „{VERMUTUNG} …“")
    fragezeichen = text.count("?")
    if fragezeichen != 1 or "?" not in frage:
        raise Formfehler(f"Rückfrage {nr} hat {fragezeichen} Fragezeichen, erlaubt ist "
                         f"genau eins, vor „{VERMUTUNG}“")
    vermutung = vermutung.strip()
    keine = re.fullmatch(r"keine\.?", vermutung, re.IGNORECASE)
    return Rueckfrage(nr, frage.strip(), None if keine else vermutung)


def lies_freigabe(rumpf: str, felder: dict) -> tuple[list[Vorschlag], list[Rueckfrage]]:
    """Die Listen unter `## Freigabe`, oder Formfehler, wenn ihre Form nicht stimmt."""
    zeilen = rumpf.splitlines()
    freigabe = _abschnitt(zeilen, "Freigabe")
    if freigabe is None:
        raise Formfehler("## Freigabe fehlt")
    listen = _listen(freigabe)
    for liste in ("Vorschläge", "Rückfragen"):
        if liste not in listen:
            raise Formfehler(f"## Freigabe ohne {liste}:")
    ueberschriften = {z.strip() for z in zeilen if z.startswith("#")}
    return ([lies_vorschlag(nr, v, felder, ueberschriften)
             for nr, v in enumerate(listen["Vorschläge"], 1)],
            [lies_rueckfrage(nr, r) for nr, r in enumerate(listen["Rückfragen"], 1)])


def pruefe_entwurf(sammelimport: Sammelimport, k: Kandidat) -> Befund:
    """Sagt, ob ein Kartenentwurf Karte werden kann, und wenn nicht, warum.

    Abgewiesen wird ein Entwurf, der das Datenmodell bricht oder die Form der
    Freigabe nicht einhält. Der Agent hat nicht nachfragen können, und was
    hier durchkäme, stünde nach der Freigabe so auf der Karte.
    """
    datei = sammelimport.entwurf(k)
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
    try:
        pruefe_frontmatter(sammelimport, k, felder)
        vorschlaege, rueckfragen = lies_freigabe(rumpf, felder)
    except Formfehler as fehler:
        return Befund(str(fehler))
    return Befund(felder=felder, vorschlaege=vorschlaege, rueckfragen=rueckfragen,
                  aus_dem_bild=laut_auftrag_aus_dem_bild(sammelimport.auftrag(k)))


# --------------------------------------------------------------------------
# vorbereiten --plan
# --------------------------------------------------------------------------

def vorhandener_sammelimport(wurzel: Path, ordner: str) -> Sammelimport | None:
    """Die `sammelimport.md` des Quellenordners, oder None beim ersten Lauf.

    Beim ersten Lauf gibt es noch keine Übersicht, vielleicht nicht einmal
    die `sammelimport.md`.
    """
    quellordner = wurzel / "quellen" / ordner
    if not quellordner.is_dir():
        raise Abbruch(f"Keinen Ordner quellen/{ordner}/.")
    if not (quellordner / SAMMELIMPORT).is_file():
        return None
    return Sammelimport(wurzel, ordner)


def neue_dateien(quellordner: Path, sammelimport: Sammelimport | None) -> dict[str, Path]:
    """Die Dateien des Quellenordners, die noch in keiner Zeile der Übersicht stehen.

    Der Schlüssel ist der Name relativ zum Quellenordner, so wie in der Spalte
    Dateien, samt Unterordnern. Ohne `sammelimport.md` ist jede Datei neu. Was `ohne:`
    auslässt, ist nie neu, und die `sammelimport.md` selbst ist nie eine
    Quelle.

    Verglichen wird in einer Unicode-Form. macOS schreibt ein Ü im Dateinamen
    als U mit zwei Punkten, Windows und die Übersicht als ein Zeichen, und
    jeder Übungsordner von PlayDrill heißt `Ü_…`. Geöffnet wird die Datei
    über ihren Pfad, wie er auf der Platte steht.
    """
    im_plan = ({_nfc(d) for k in sammelimport.kandidaten for d in k.dateien}
               if sammelimport else set())
    alle = {_nfc(p.relative_to(quellordner).as_posix()): p for p in quellordner.rglob("*")
            if p.is_file() and p.name != SAMMELIMPORT}
    return {name: alle[name] for name in sorted(alle)
            if name not in im_plan and not (sammelimport and sammelimport.ausgelassen(name))}


def naechste_kandidatennummer(sammelimport: Sammelimport | None) -> int:
    """Die höchste Nummer in der Übersicht plus eins, ohne Übersicht 1 (#40).

    Die Nummer eines Kandidaten bleibt. Ein zweiter Lauf zählt deshalb ab
    hier weiter, auch über Lücken hinweg, die beim Zusammenlegen entstehen.
    """
    if sammelimport is None:
        return 1
    return max((int(k.nummer) for k in sammelimport.kandidaten), default=0) + 1


def _nfc(text: str) -> str:
    return unicodedata.normalize("NFC", text)


def finde_pdftotext() -> str | None:
    """Wo `pdftotext` liegt, oder None (ADR-0008).

    Erst im PATH. Unter Windows danach neben `git.exe`: Git für Windows bringt
    Xpdf mit, in `…\\Git\\mingw64\\bin`, legt aber nur `…\\Git\\cmd` in den
    PATH von Windows. Je nach Installation steht dort `cmd\\git.exe`,
    `bin\\git.exe` oder `mingw64\\bin\\git.exe`, deshalb wird von `git.exe`
    aus drei Ebenen aufwärts nach `mingw64\\bin` geschaut.
    """
    gefunden = shutil.which("pdftotext")
    if gefunden or sys.platform != "win32":
        return gefunden
    git = shutil.which("git")
    if not git:
        return None
    for ordner in list(Path(git).resolve().parents)[:3]:
        exe = ordner / "mingw64" / "bin" / "pdftotext.exe"
        if exe.is_file():
            return str(exe)
    return None


def _ist_pdf(datei: str | Path) -> bool:
    return Path(datei).suffix.lower() == ".pdf"


def pdf_text(pdftotext: str, pdf: Path) -> str | None:
    """Der Text eines PDF, oder None, wenn pdftotext es nicht lesen kann.

    `-enc UTF-8`, weil Xpdf sonst Latin-1 schreibt und aus „Ausführung"
    „Ausf�hrung" wird. `-raw`, weil Xpdf ohne es die Zeilen eines Absatzes zu
    einer zusammenzieht: Aus den Kopfzeilen „Trainer/Ersteller", „ZEIT" und
    „Werkzeuge" eines PlayDrill-Blatts würde eine. Poppler zieht nichts
    zusammen, mit `-raw` lesen beide gleich. Leere Zeilen und Seitenwechsel
    fallen weg, sie kosten nur Platz.
    """
    try:
        lauf = subprocess.run([pdftotext, "-raw", "-enc", "UTF-8", str(pdf), "-"],
                              capture_output=True, timeout=60, check=False)
    except (OSError, subprocess.TimeoutExpired):
        return None
    if lauf.returncode != 0:
        return None
    zeilen = lauf.stdout.decode("utf-8", errors="replace").replace("\f", "\n").splitlines()
    return "\n".join(z.strip() for z in zeilen if z.strip())


def erste_zeilen(text: str) -> str:
    """Die ersten Zeilen eines Textes, ganze Zeilen, bis ERSTE_ZEILEN_BIS Zeichen erreicht sind."""
    zeilen: list[str] = []
    for zeile in text.splitlines():
        if sum(len(z) + 1 for z in zeilen) >= ERSTE_ZEILEN_BIS:
            break
        zeilen.append(zeile)
    return "\n".join(zeilen)


def _eingezaeunt(text: str) -> list[str]:
    """Ein Text als Codeblock, dessen Zaun länger ist als jede Backtick-Folge darin."""
    laengste = max((len(folge) for folge in re.findall(r"`+", text)), default=0)
    zaun = "`" * max(3, laengste + 1)
    return [f"{zaun}text", text, zaun]


def melde_ohne_pdftotext(wohin: str, wofuer: str) -> None:
    """Sagt einmal, dass pdftotext fehlt und wie es dazukommt.

    Abgebrochen wird nicht (ADR-0008). Ohne Text liest der Agent die PDFs
    selbst. Das kostet mehr, geht aber.
    """
    print(f"pdftotext fehlt, die PDFs kommen ohne Text in {wohin}.")
    print(f"Der Agent für {wofuer} liest sie dann selbst, das kostet mehr.\n")
    print("Installieren:")
    print("  Windows: kommt mit Git für Windows, …\\Git\\mingw64\\bin\\pdftotext.exe")
    print("  macOS:   brew install poppler")
    print("  Linux:   das Paket poppler-utils\n")


def aus_diesem_ordner(quelldatei: object, ordner: str) -> bool:
    """Liegt eine der Dateien in `quelldatei` in diesem Quellenordner?

    Bei zwei Seiten nennt `quelldatei` beide, durch Komma getrennt, und es
    reicht, wenn eine davon hier liegt. Verglichen wird mit dem Schrägstrich
    dahinter, sonst gälte `stapel-alt/…` als Datei aus `stapel`.
    """
    if not quelldatei:
        return False
    praefix = _nfc(ordner) + "/"
    return any(_nfc(teil.strip().replace("\\", "/")).startswith(praefix)
               for teil in str(quelldatei).split(","))


def bibliotheksliste(wurzel: Path, ordner: str) -> list[str]:
    """Jede Karte der Bibliothek als Tabelle, die aus diesem Quellenordner markiert.

    Daran erkennt der Agent für den Zerlegungsplan, was schon importiert ist,
    und führt es als `importiert` mit seiner ID. Titel und Element braucht er,
    um einen Verdacht auf ein Duplikat zu äußern.
    """
    zeilen = ["| ID | Titel | Element | quelldatei | Aus diesem Ordner |",
              "|---|---|---|---|---|"]
    for karte in sorted(lies_uebungen(wurzel), key=lambda k: str(k["id"])):
        element = karte.get("element") or []
        element = ", ".join(map(str, element)) if isinstance(element, list) else str(element)
        zellen = [karte["id"], karte.get("titel") or "", element, karte.get("quelldatei") or "",
                  "ja" if aus_diesem_ordner(karte.get("quelldatei"), ordner) else ""]
        zeilen.append("| " + " | ".join(_zelle(z) for z in zellen) + " |")
    return zeilen


def melde_schwere_fotos(ordner: str, quellordner: Path,
                        sammelimport: Sammelimport | None) -> None:
    """Nennt die Fotos im Quellenordner, die zu schwer zum Lesen sind.

    Schwelle und Endungen kommen aus `bilder_aufbereiten.py`, damit „zu
    schwer" hier dasselbe heißt wie dort, wo es behoben wird. Genannt werden
    alle Fotos des Ordners, nicht nur die neuen: Auch ein Foto, das schon im
    Plan steht, muss der Agent für den Entwurf öffnen können. Nur was `ohne:`
    auslässt, öffnet kein Agent, das fehlt hier.
    """
    schwer, _leicht = bilder_nach_gewicht(quellordner)
    namen = {pfad: _nfc(pfad.relative_to(quellordner).as_posix()) for pfad in schwer}
    schwer = [pfad for pfad in schwer
              if not (sammelimport and sammelimport.ausgelassen(namen[pfad]))]
    if not schwer:
        return
    print(f"{bilder(len(schwer))} über {menschenmass(SCHWELLE)}, zu schwer zum Lesen:")
    for pfad in schwer:
        print(f"  {namen[pfad]}  {menschenmass(pfad.stat().st_size)}")
    print(f"Vorher verkleinern, mit Rückfrage: "
          f"'{interpreter()} bilder_aufbereiten.py quellen/{ordner}'\n")


def _text_oder_grund(text: str | None, pdftotext: str | None) -> list[str]:
    """Was unter einem PDF steht: sein Text, oder warum keiner da ist.

    Ohne Text muss der Agent das PDF selbst lesen, und das soll er nicht aus
    einer leeren Stelle schließen müssen.
    """
    if text:
        return _eingezaeunt(text)
    if not pdftotext:
        grund = "Ohne Text, pdftotext fehlt."
    elif text is None:
        grund = "pdftotext konnte die Datei nicht lesen."
    else:
        grund = "Keine Textebene."
    return [f"{grund} Das PDF selbst lesen."]


def lege_planeingabe_an(wurzel: Path, ordner: str) -> int:
    """Legt die Eingabe für den Zerlegungsplan an.

    Der Agent liest sie in einem Aufruf: jede Datei, die noch in keiner Zeile
    der Übersicht steht, bei PDFs mit ihrem Text, und die Bibliotheksliste.
    Der Quellenordner steht einmal absolut im Kopf, denn Fotos und PDFs ohne
    Text öffnet der Agent selbst. Dazu die nächste freie Kandidatennummer, ab
    der er zählt.
    """
    sammelimport = vorhandener_sammelimport(wurzel, ordner)
    quellordner = wurzel / "quellen" / ordner
    dateien = neue_dateien(quellordner, sammelimport)
    melde_schwere_fotos(ordner, quellordner, sammelimport)
    if not dateien:
        wo = ("in der Übersicht oder unter ohne" if sammelimport and sammelimport.ohne
              else "in der Übersicht")
        print(f"Keine neuen Dateien in quellen/{ordner}/, jede steht schon {wo}.")
        return 0
    pdfs = {name for name in dateien if _ist_pdf(name)}
    pdftotext = finde_pdftotext() if pdfs else None
    if pdfs and not pdftotext:
        melde_ohne_pdftotext("die Planeingabe", "den Zerlegungsplan")
    texte = {name: pdf_text(pdftotext, dateien[name]) for name in pdfs} if pdftotext else {}

    zeichen = sum(len(t) for t in texte.values() if t)
    if not pdfs:
        textlage = []
    elif not pdftotext:
        textlage = ["Die PDFs stehen ohne Text da, pdftotext fehlt."]
    elif zeichen > GANZER_TEXT_BIS:
        texte = {name: erste_zeilen(t) if t else t for name, t in texte.items()}
        textlage = [f"Der Text aller PDFs hätte {zeichen} Zeichen, zu viel für einen Aufruf. "
                    f"Je PDF stehen die ersten Zeilen da, der ganze Text steht im PDF."]
        print(f"Der Text der PDFs hat {zeichen} Zeichen, mehr als {GANZER_TEXT_BIS}. "
              f"Die Planeingabe nennt je PDF die ersten Zeilen.")
    else:
        textlage = ["Je PDF steht sein ganzer Text da."]

    teile = [f"# Planeingabe für quellen/{ordner}/", "",
             f"Quellenordner: `{quellordner.as_posix()}/`", "",
             f"Nächste freie Kandidatennummer: {naechste_kandidatennummer(sammelimport)}", "",
             f"{len(dateien)} Dateien, die noch in keiner Zeile der Übersicht stehen, "
             f"relativ zum Quellenordner.", *textlage, "", "## Dateien", ""]
    for datei in dateien:
        teile += [f"### `{datei}`", ""]
        if datei in pdfs:
            teile += [*_text_oder_grund(texte.get(datei), pdftotext), ""]
    teile += ["## Bibliothek", "",
              "Jede Karte der Bibliothek. „ja“ heißt: Ihre `quelldatei` liegt in "
              "diesem Quellenordner, sie ist schon importiert.", "",
              *bibliotheksliste(wurzel, ordner), ""]
    ziel = wurzel / ENTWUERFE / ordner / PLANEINGABE
    ziel.parent.mkdir(parents=True, exist_ok=True)
    ziel.write_text("\n".join(teile), encoding="utf-8")
    print(f"Planeingabe für {len(dateien)} Dateien: {ziel.as_posix()}")
    return 0


# --------------------------------------------------------------------------
# Die Quellgrafik
# --------------------------------------------------------------------------

class KeineQuellgrafik(Exception):
    """Aus einem PDF ließ sich keine Quellgrafik ausschneiden. Der Text sagt, warum."""


class OhneBild(KeineQuellgrafik):
    """Das PDF bettet gar kein Bild ein. Dann kommt das nächste PDF des Kandidaten dran."""


# Je Nummer das Wörterbuch eines Objekts und, wenn es einen hat, sein Strom.
PdfObjekte = dict[int, tuple[bytes, bytes | None]]

_OBJEKT = re.compile(rb"(?<!\d)(\d+)\s+\d+\s+obj\b\s*")
_STROM = re.compile(rb"\s*stream\r?\n")


def _woerterbuch_ende(daten: bytes, anfang: int) -> int | None:
    """Wo das Wörterbuch endet, das bei `anfang` mit `<<` beginnt: gleich hinter seinem `>>`.

    Gezählt wird die Tiefe, denn ein Wörterbuch kann weitere enthalten.
    Zeichenketten werden übersprungen, `(…)` und `<…>`, weil eine
    Klammer oder ein `>` darin sonst mitzählte.
    """
    tiefe, i = 0, anfang
    while i < len(daten):
        if daten.startswith(b"<<", i):
            tiefe, i = tiefe + 1, i + 2
        elif daten.startswith(b">>", i):
            tiefe, i = tiefe - 1, i + 2
            if tiefe == 0:
                return i
        elif daten[i:i + 1] == b"<":
            i = daten.find(b">", i) + 1 or len(daten)
        elif daten[i:i + 1] == b"(":
            klammern = 0
            while i < len(daten):
                zeichen = daten[i:i + 1]
                if zeichen == b"\\":
                    i += 1
                elif zeichen == b"(":
                    klammern += 1
                elif zeichen == b")":
                    klammern -= 1
                    if klammern == 0:
                        break
                i += 1
            i += 1
        else:
            i += 1
    return None


def pdf_objekte(daten: bytes) -> PdfObjekte:
    """Die Objekte eines PDF, die ein Wörterbuch sind: je Nummer das Wörterbuch und der Strom.

    Gelesen wird der Reihe nach durch die Datei, ohne die Querverweistabelle.
    Den Inhalt eines Stroms überspringt die Suche, sonst fände sie darin
    zufällig ein `obj`. Die Länge eines Stroms steht in `/Length`, gilt aber
    nur, wenn dort auch `endstream` folgt. Sonst, etwa bei einer Länge als
    Verweis, endet er vor dem nächsten `endstream`. Kommt eine Nummer zweimal
    vor, gilt die spätere, so wie bei einer nachträglich geänderten Datei.

    Das Vorbild im PlayDrill-Log suchte mit einem einzigen Muster bis zum
    nächsten `stream` und griff bei einem Objekt ohne Strom in das nächste
    Objekt hinein.
    """
    objekte: PdfObjekte = {}
    pos = 0
    while (objekt := _OBJEKT.search(daten, pos)):
        pos = objekt.end()
        if not daten.startswith(b"<<", pos):
            continue
        ende = _woerterbuch_ende(daten, pos)
        if ende is None:
            break
        woerterbuch, pos = daten[pos:ende], ende
        strom = None
        kopf = _STROM.match(daten, pos)
        if kopf:
            anfang = kopf.end()
            laenge = _zahl(woerterbuch, b"Length")
            schluss = anfang + laenge if laenge is not None else -1
            if laenge is None or not re.match(rb"\s*endstream", daten[schluss:schluss + 20]):
                schluss = daten.find(b"endstream", anfang)
                if schluss < 0:
                    break
                schluss -= 2 if daten[schluss - 2:schluss] == b"\r\n" else 1
            strom, pos = daten[anfang:schluss], schluss
        objekte[int(objekt.group(1))] = (woerterbuch, strom)
    return objekte


def _zahl(woerterbuch: bytes, name: bytes) -> int | None:
    """Eine Zahl im Wörterbuch, aber kein Verweis wie `/Length 12 0 R`."""
    treffer = re.search(rb"/" + name + rb"\s+(\d+)\b(?!\s+\d+\s+R)", woerterbuch)
    return int(treffer.group(1)) if treffer else None


def _verweis(woerterbuch: bytes, name: bytes) -> int | None:
    """Die Nummer des Objekts, auf das ein Eintrag verweist, etwa `/SMask 7 0 R`."""
    treffer = re.search(rb"/" + name + rb"\s+(\d+)\s+\d+\s+R", woerterbuch)
    return int(treffer.group(1)) if treffer else None


def _farbmodus(objekte: PdfObjekte, woerterbuch: bytes) -> str:
    """Der Modus für Pillow aus dem Farbraum des Bildes.

    PlayDrill nennt den Farbraum über ein ICC-Profil, `[/ICCBased 6 0 R]`.
    Wie viele Farben ein Pixel hat, steht dann als `/N` beim Profil.
    """
    modi = {1: "L", 3: "RGB", 4: "CMYK"}
    treffer = re.search(rb"/ColorSpace\s*(/\w+|\[\s*/ICCBased\s+(\d+)\s+\d+\s+R\s*\])", woerterbuch)
    if treffer and treffer.group(2):
        profil = objekte.get(int(treffer.group(2)))
        farben = _zahl(profil[0], b"N") if profil else None
        if farben in modi:
            return modi[farben]
    elif treffer:
        farben = {b"/DeviceGray": 1, b"/DeviceRGB": 3, b"/DeviceCMYK": 4}.get(treffer.group(1))
        if farben:
            return modi[farben]
    raise KeineQuellgrafik("den Farbraum des Bildes liest das Skript nicht")


def _bild(objekte: PdfObjekte, nummer: int, als_maske: bool = False):
    """Ein eingebettetes Bild als Bild von Pillow, eine Maske als Graustufen.

    Gelesen werden die Bilder, wie PlayDrill sie einbettet: entpackt mit
    /FlateDecode, 8 Bit je Farbe. Dazu JPEG, /DCTDecode, das Pillow selbst
    öffnet. Alles andere meldet KeineQuellgrafik.
    """
    from PIL import Image  # erst hier, verlange_pillow() hat vorher geprüft

    woerterbuch, strom = objekte[nummer]
    breite, hoehe = _zahl(woerterbuch, b"Width"), _zahl(woerterbuch, b"Height")
    if not breite or not hoehe or strom is None:
        raise KeineQuellgrafik("das Bild hat keine lesbare Größe")
    gefiltert = re.search(rb"/Filter\s*(?:\[\s*)?(/\w+)\s*\]?", woerterbuch)
    filter_ = gefiltert.group(1).decode() if gefiltert else ""
    if filter_ == "/DCTDecode":
        bild = Image.open(io.BytesIO(strom))
        bild.load()
        return bild.convert("L" if als_maske else "RGB")
    if filter_ not in ("", "/FlateDecode") or re.search(rb"/Filter\s*\[[^\]]*/\w+[^\]]*/\w+",
                                                        woerterbuch):
        raise KeineQuellgrafik(f"das Bild ist mit {filter_} gepackt, das liest das Skript nicht")
    if (_zahl(woerterbuch, b"Predictor") or 1) > 1 or _zahl(woerterbuch, b"BitsPerComponent") != 8:
        raise KeineQuellgrafik("das Bild ist anders gepackt, als das Skript es liest")
    modus = "L" if als_maske else _farbmodus(objekte, woerterbuch)
    pixel = zlib.decompress(strom) if filter_ else strom
    return Image.frombytes(modus, (breite, hoehe), pixel).convert("L" if als_maske else "RGB")


def schneide_quellgrafik_aus(pdf: Path, ziel: Path) -> None:
    """Legt das größte eingebettete Bild eines PDF als PNG ab, ohne den durchsichtigen Rand.

    Das größte nach Pixeln, und nur unter den Bildern, die keine Maske eines
    anderen sind. PlayDrill bettet seine Quellgrafik mit 1920 × 1040 Pixeln
    ein, dazu eine Transparenzmaske. Was die Maske ganz durchsichtig lässt,
    wird abgeschnitten, wie im PlayDrill-Log. Eine Quellgrafik ohne Maske
    bleibt, wie sie ist.
    """
    try:
        objekte = pdf_objekte(pdf.read_bytes())
    except OSError as fehler:
        raise KeineQuellgrafik(f"die Datei lässt sich nicht lesen ({fehler})") from fehler
    bilder = {n: w for n, (w, strom) in objekte.items()
              if strom is not None and re.search(rb"/Subtype\s*/Image\b", w)}
    masken = {_verweis(w, name) for w in bilder.values() for name in (b"SMask", b"Mask")}
    kandidaten = [n for n in bilder if n not in masken]
    if not kandidaten:
        raise OhneBild("das PDF bettet kein Bild ein")
    nummer = max(kandidaten, key=lambda n: (_zahl(bilder[n], b"Width") or 0)
                 * (_zahl(bilder[n], b"Height") or 0))
    try:
        bild = _bild(objekte, nummer)
        maske = _verweis(bilder[nummer], b"SMask")
        if maske in bilder:
            alpha = _bild(objekte, maske, als_maske=True).resize(bild.size)
            rahmen = alpha.getbbox()
            if rahmen is None:
                raise KeineQuellgrafik("das Bild ist ganz durchsichtig")
            bild.putalpha(alpha)
            bild = bild.crop(rahmen)
    except (zlib.error, OSError, ValueError) as fehler:
        raise KeineQuellgrafik(f"das Bild lässt sich nicht lesen ({fehler})") from fehler
    bild.save(ziel, "PNG", optimize=True)


def verlange_pillow(sammelimport: Sammelimport) -> None:
    """Bricht ab, wenn die Quellgrafik ausgeschnitten werden soll und Pillow fehlt (ADR-0005).

    Vor dem ersten Auftrag, damit nichts geschrieben ist: Ein Durchgang ohne
    Quellgrafik ergäbe Karten ohne Bild, und Entwürfe, die der Agent ohne das
    Bild gelesen hat.
    """
    try:
        from PIL import Image  # noqa: F401  Der Import ist die Prüfung.
    except ImportError:
        raise Abbruch(
            f"Für das Ausschneiden der Quellgrafik fehlt Pillow. In quellen/"
            f"{sammelimport.ordner}/{SAMMELIMPORT} steht quellgrafik_ausschneiden: true.\n\n"
            f"Installieren mit:\n  {interpreter()} -m pip install Pillow\n\n"
            f"Es ist noch kein Auftrag geschrieben.") from None


def lege_quellgrafiken_an(sammelimport: Sammelimport, k: Kandidat) -> tuple[list[str], list[str]]:
    """Schneidet die Quellgrafiken eines Kandidaten aus, wenn die Einstellungen es wollen.

    Zurück kommen die Zeilen für den Auftrag und, was das Skript dazu sagt,
    wenn etwas nicht geklappt hat. Jedes PDF des Kandidaten, das ein Bild
    einbettet, gibt eine Quellgrafik, in der Reihenfolge der Spalte Dateien
    (#39). Bei einem Zirkel steht dort das Übersichtsblatt vorn (#35), sein
    Bild zeigt den ganzen Aufbau, und die Stationsblätter folgen.

    Lässt sich ein Bild nicht lesen, fehlt nur dieses, und die übrigen zählen
    ohne Lücke weiter. Das gilt auch für das Bild der Übersicht (entschieden
    am 02.10.2026): Die Stationen bekommen ihre Quellgrafiken trotzdem, und für
    die Übersicht lässt sich danach ein Schaubild zeichnen. Der Auftrag nennt
    das PDF, und der Agent sieht dort selbst nach. `pruefen` liest es dort
    wieder, siehe `laut_auftrag_ohne_quellgrafik`.
    """
    for altes in sammelimport.quellgrafiken(k):
        altes.unlink()
    if not sammelimport.quellgrafik_ausschneiden:
        return ["- Quellgrafik: wird bei dieser Quelle nicht ausgeschnitten."], []
    pdfs = [d for d in k.dateien if _ist_pdf(d)]
    if not pdfs:
        return ["- Quellgrafik: keine, der Kandidat hat kein PDF."], []
    ausgeschnitten: list[tuple[str, Path]] = []
    fehler: list[str] = []
    for datei in pdfs:
        ziel = sammelimport.quellgrafik(k, len(ausgeschnitten) + 1)
        try:
            schneide_quellgrafik_aus(sammelimport.quellordner / datei, ziel)
        except OhneBild:
            continue
        except KeineQuellgrafik as warum:
            fehler.append(f"`{datei}`: {warum}")
            continue
        ausgeschnitten.append((datei, ziel))

    if not ausgeschnitten:
        grund = "; ".join(fehler) or "kein PDF des Kandidaten bettet ein Bild ein"
        return ([f"{KEINE_AUSGESCHNITTEN} {grund}. Sieh dir das Bild im PDF selbst an."],
                [f"Keine Quellgrafik, {grund}."])
    if len(ausgeschnitten) == 1:
        # Eine einzelne Quellgrafik trägt keine Nummer, auf der Karte wird
        # sie ein einzelner Name.
        datei, ziel = ausgeschnitten[0]
        ziel = ziel.replace(sammelimport.quellgrafik(k))
        zeilen = [f"- Quellgrafik: `{ziel.as_posix()}`, aus `{datei}`. Trag sie im Entwurf "
                  f"als `schaubild: {ziel.name}` ein."]
    else:
        namen = ", ".join(ziel.name for _, ziel in ausgeschnitten)
        zeilen = [f"- Quellgrafiken: eine je PDF mit Bild, in der Reihenfolge der Dateien. "
                  f"Trag sie im Entwurf in dieser Reihenfolge ein, als `schaubild: [{namen}]`.",
                  *(f"  - `{ziel.as_posix()}`, aus `{datei}`" for datei, ziel in ausgeschnitten)]
    zeilen += [f"{KEINE_QUELLGRAFIK_AUS} {grund}. Sieh dir das Bild im PDF selbst an."
               for grund in fehler]
    return zeilen, [f"Keine Quellgrafik aus {grund}." for grund in fehler]


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


def _muster(text: str) -> re.Pattern[str]:
    """Ein Text als Suchmuster, gleich in welcher Schreibung und mit welchem Leerraum.

    Bei PlayDrill steht „hier Könnte ihr Text stehen“ mit großem K auf dem
    Blatt, im Log des Trainers mit kleinem. Und pdftotext bricht eine Zeile,
    wo das Blatt sie bricht.
    """
    return re.compile(r"\s+".join(re.escape(w) for w in _nfc(text).split()), re.IGNORECASE)


def ablauftext(text: str, textmarke: str | None, platzhalter: str | None) -> str:
    """Der Teil eines Texts, der den Ablauf beschreibt, ohne den Platzhalter.

    Das ist der Text nach dem ersten Vorkommen der Textmarke. Ohne Textmarke,
    oder wenn die Datei sie nicht trägt, ist es der ganze Text. PlayDrill
    schreibt auch „Ausführung(1) …“ oder „Ausführung 1“, mit vollem Ablauf
    dahinter. Leerraum zählt als ein Zeichen.
    """
    text = _nfc(text)
    if textmarke:
        marke = _muster(textmarke).search(text)
        if marke:
            text = text[marke.end():]
    if platzhalter:
        text = _muster(platzhalter).sub(" ", text)
    return " ".join(text.split())


def ablauf_aus_dem_bild(sammelimport: Sammelimport, texte: list[str | None]) -> str:
    """Die Zeile des Auftrags, ob der Ablauf aus dem Bild kommt (#29, Geschichte 44).

    `texte` hat je Datei des Kandidaten ihren Text, oder None, wenn sie
    keinen hat: ein Foto, ein PDF ohne Textebene, oder pdftotext fehlt.
    Unter WENIG_TEXT Zeichen Ablauf kommt er aus dem Bild. Fehlt einer Datei
    der Text, kann die Regel das nicht sagen, dann entscheidet der Agent.
    Genug Text ist aber genug, auch wenn daneben ein Foto liegt.

    `pruefen` liest die Zeile wieder, an ihrem Anfang, siehe AUS_DEM_BILD.
    """
    marke, platzhalter = sammelimport.textmarke, sammelimport.platzhalter
    zeichen = sum(len(ablauftext(t, marke, platzhalter)) for t in texte if t)
    gezaehlt = f"Nach „{marke}“" if marke else "Im ganzen Text"
    ohne_platzhalter = ", ohne den Platzhalter," if platzhalter else ""
    if zeichen >= WENIG_TEXT:
        return f"- {AUS_DEM_BILD}: nein. {gezaehlt} stehen{ohne_platzhalter} {zeichen} Zeichen."
    if not texte or not all(texte):
        return (f"- {AUS_DEM_BILD}: entscheidest du. Nicht jede Datei hat Text, die Regel "
                f"kann es nicht sagen.")
    return (f"- {AUS_DEM_BILD}: ja. {gezaehlt} stehen{ohne_platzhalter} nur {zeichen} Zeichen. "
            f"Den Ablauf liest du aus dem Bild, der Trainer prüft ihn einzeln.")


def schreibe_auftrag(sammelimport: Sammelimport, k: Kandidat, kennungen: list[str],
                     pdftotext: str | None, quellgrafikzeilen: list[str]) -> Path:
    """Legt den Auftrag für einen Kandidaten an, alles, was der Agent braucht.

    Die Pfade stehen absolut da, denn der Agent liest und schreibt mit ihnen.
    `quelldatei:` steht relativ zu `quellen/`, so wie auf der Karte, damit sie
    auf jedem Rechner stimmt, egal wo dort der Arbeitsordner liegt.

    Unter jedem PDF steht sein ganzer Text, anders als in der Planeingabe nie
    gekappt: Der Agent schreibt aus ihm die Karte. Ohne Text steht da, warum,
    und dass er das PDF selbst lesen muss.
    """
    relativ = [f"{sammelimport.ordner}/{d}" for d in k.dateien]
    dateien: list[str] = []
    texte: list[str | None] = []
    for d in k.dateien:
        pfad = sammelimport.quellordner / d
        dateien += [f"### `{d}`", "", f"`{pfad.as_posix()}`", ""]
        text = pdf_text(pdftotext, pfad) if pdftotext and _ist_pdf(d) else None
        texte.append(text)
        if _ist_pdf(d):
            dateien += [*_text_oder_grund(text, pdftotext), ""]
    teile = [
        f"# Auftrag für Kandidat {k.nummer}",
        "",
        f"- Quellenordner: `quellen/{sammelimport.ordner}/`",
        f"- Kandidat: {k.nummer}",
        f"- Was es ist: {k.was}",
        f"- Typ laut Zerlegungsplan: `{k.ergebnis}`",
        f"- `quelldatei:` `{', '.join(relativ)}`",
        ablauf_aus_dem_bild(sammelimport, texte),
        *quellgrafikzeilen,
        f"- Zielpfad des Entwurfs: `{sammelimport.entwurf(k).as_posix()}`",
        "",
        "## Dateien",
        "",
        *dateien,
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


def trainer_fuer_auftraege(wurzel: Path) -> str:
    """Der Trainer dieses Rechners, oder Abbruch, bevor ein Auftrag geschrieben ist.

    Ohne ihn ließe sich nicht eintragen, wer am Quellenordner arbeitet, und
    `uebernehmen` bekäme am Ende keine ID.
    """
    try:
        return trainer_dieses_rechners(wurzel)
    except KeineId as fehler:
        raise Abbruch(f"{fehler}\nEs ist noch kein Auftrag geschrieben.") from None


def verlange_freien_quellenordner(sammelimport: Sammelimport, trainer: str,
                                  trotzdem: bool) -> None:
    """Bricht ab, wenn laut `in_arbeit` ein anderer Trainer am Quellenordner arbeitet (#40).

    Zwei Trainer, die denselben Quellenordner zugleich importieren, entwürfen
    dieselben Kandidaten zweimal. Mit getrennten Nummernbereichen entstünden
    zwei Karten mit gleichem Inhalt und verschiedenen IDs, und der Linter
    merkte es nicht. `trotzdem` geht über einen fremden Eintrag hinweg, etwa
    einen von einem abgebrochenen Lauf. Der Skill fragt den Trainer vorher.

    Der Eintrag ist ein Hinweis und keine Sperre. Er liegt in derselben
    Nextcloud wie alles andere, und wer vor dem Abgleich anfängt, sieht ihn
    nicht. Aus diesem Grund vergibt ADR-0011 die IDs nicht über eine
    Reservierungsdatei. Hier reicht der Hinweis: Im schlimmsten Fall wird
    doppelt entworfen, und die Freigabe zeigt es.
    """
    eintrag = sammelimport.in_arbeit
    if eintrag and not eintrag.ist_von(trainer) and not trotzdem:
        raise Abbruch(
            f"An quellen/{sammelimport.ordner}/ arbeitet seit {eintrag.seit} {eintrag.trainer}, "
            f"so steht es unter in_arbeit in {SAMMELIMPORT}.\n"
            f"Stammt der Eintrag von einem abgebrochenen Lauf, geht es mit --trotzdem weiter.\n"
            f"Es ist noch kein Auftrag geschrieben.")


def vorbereiten(wurzel: Path, ordner: str, trotzdem: bool = False) -> int:
    """Legt die Aufträge für den nächsten Durchgang an.

    Gibt es welche, steht danach in `in_arbeit` der Trainer dieses Rechners.
    Arbeitete er schon daran, bleibt das Datum, seit wann. Ohne Auftrag wird
    nichts eingetragen, sonst bliebe der Eintrag stehen, bis `uebernehmen`
    ihn löscht, und das liefe vielleicht nie.
    """
    sammelimport = Sammelimport(wurzel, ordner)
    sammelimport.verlange_aktuelle_einstellungen()
    sammelimport.verlange_freigabe()
    trainer = trainer_fuer_auftraege(wurzel)
    verlange_freien_quellenordner(sammelimport, trainer, trotzdem)
    offen = [k for k in sammelimport.kandidaten
             if k.wartet and pruefe_entwurf(sammelimport, k).fehler]
    dran = offen[:sammelimport.je_durchgang]
    print(f"Aufträge für {len(dran)} von {len(offen)} offenen Kandidaten:")
    if not dran:
        return 0
    if sammelimport.quellgrafik_ausschneiden:
        verlange_pillow(sammelimport)
    pdftotext = None
    if any(_ist_pdf(d) for k in dran for d in k.dateien):
        pdftotext = finde_pdftotext()
        if not pdftotext:
            melde_ohne_pdftotext("die Aufträge", "den Kartenentwurf")
    eintrag = sammelimport.in_arbeit
    if eintrag is None or not eintrag.ist_von(trainer):
        sammelimport.setze_in_arbeit(trainer)
        sammelimport.speichere()
    sammelimport.entwurfsordner.mkdir(parents=True, exist_ok=True)
    kennungen = kennungstabelle(wurzel)
    for k in dran:
        quellgrafikzeilen, meldungen = lege_quellgrafiken_an(sammelimport, k)
        auftrag = schreibe_auftrag(sammelimport, k, kennungen, pdftotext, quellgrafikzeilen)
        print(f"  {k.nummer}  {auftrag.as_posix()}")
        for meldung in meldungen:
            print(f"      {meldung}")
    return 0


# --------------------------------------------------------------------------
# pruefen
# --------------------------------------------------------------------------

def setze_befund(k: Kandidat, befund: Befund) -> None:
    """Der Status eines Kandidaten, wie ihn sein Entwurf auf der Platte ergibt.

    `rückfrage` heißt: Hier muss einzeln gefragt werden. Entweder hat der
    Entwurf für mindestens eine Rückfrage keine Vermutung, oder der Ablauf
    kommt laut Auftrag aus dem Bild. Dann ist er als Ganzes eine Vermutung,
    und der Trainer prüft ihn mit der Quellgrafik vor sich. Eine Rückfrage mit
    Vermutung bestätigt er sonst in der Tabelle wie einen Vorschlag.
    """
    if befund.fehler:
        k.setze("offen", befund.fehler)
        return
    gruende = [AUS_DEM_BILD] if befund.aus_dem_bild else []
    if befund.ohne_vermutung:
        anzahl = len(befund.ohne_vermutung)
        gruende.append(f"{anzahl} Rückfrage{'n' if anzahl > 1 else ''} ohne Vermutung")
    k.setze("rückfrage" if gruende else "bereit", ", ".join(gruende))


def fuer_die_freigabe(sammelimport: Sammelimport, k: Kandidat, befund: Befund) -> dict:
    """Was der Skill für die Freigabe im Chat über einen Kandidaten braucht (#29).

    Einzeln fragt er die Rückfragen ohne Vermutung, mit den Quellgrafiken, und
    bei `ablauf_aus_dem_bild` den Ablauf. Alles andere kommt in eine Tabelle:
    die Felder in ihren Spalten, die Vorschläge zu Feldern daran, die
    Rückfragen mit Vermutung zum Bestätigen, und eine Spalte „aus dem
    Bild“ aus den Vorschlägen zu Textstellen. Ein abgewiesener Entwurf kommt
    nicht in die Freigabe, von ihm stehen nur Status und Notiz da.

    `quellgrafiken` sind die, die der Entwurf in `schaubild:` nennt, in seiner
    Reihenfolge, so wie sie auf die Karte kommen. Nennt er keine, ist die
    Liste leer. `quellgrafik_fehlt` nennt die PDFs, deren Bild sich nicht
    ausschneiden ließ, relativ zum Quellenordner wie `dateien`. Der Skill sagt
    es bei der Freigabe dazu und nennt am Ende des Durchgangs die Karten, denen
    deshalb eine Quellgrafik fehlt.

    Gefragt wird nur nach einem Kandidaten, dessen Entwurf auf der Platte
    liegt, siehe `pruefen`.
    """
    return {
        "kandidat": k.nummer,
        "was": k.was,
        "ergebnis": k.ergebnis,
        "dateien": k.dateien,
        "status": k.status,
        "notiz": k.notiz,
        "entwurf": sammelimport.entwurf(k).as_posix(),
        "quellgrafiken": [(sammelimport.entwurfsordner / name).as_posix()
                          for name in schaubilder(befund.felder.get("schaubild"))],
        "quellgrafik_fehlt": laut_auftrag_ohne_quellgrafik(sammelimport.auftrag(k), k),
        "ablauf_aus_dem_bild": befund.aus_dem_bild,
        "felder": befund.felder,
        "vorschlaege": {
            "felder": [{"feld": v.ziel, "text": v.text}
                       for v in befund.vorschlaege if not v.zur_textstelle],
            "textstellen": [{"abschnitt": v.ziel, "wo": v.wo, "text": v.text}
                            for v in befund.vorschlaege if v.zur_textstelle],
        },
        "rueckfragen": {
            "mit_vermutung": [{"nr": r.nr, "frage": r.frage, "vermutung": r.vermutung}
                              for r in befund.mit_vermutung],
            "ohne_vermutung": [{"nr": r.nr, "frage": r.frage} for r in befund.ohne_vermutung],
        },
    }


def pruefen(wurzel: Path, ordner: str, als_json: bool = False) -> int:
    """Setzt den Status jedes wartenden Kandidaten aus seinem Entwurf auf der Platte.

    Mit `als_json` kommt statt der Zeilen für den Trainer, was der Skill für
    die Freigabe braucht. Die Übersicht wird in beiden Fällen geschrieben.

    Ein Kandidat ohne Entwurf hat für die Freigabe nichts und fehlt im JSON
    (#36). Bei PlayDrill warten nach dem ersten Durchgang über 200 davon, und
    der Skill liest die Ausgabe in jedem Durchgang zweimal.
    """
    sammelimport = Sammelimport(wurzel, ordner)
    sammelimport.verlange_freigabe()
    stand: dict[str, int] = {}
    freigabe = []
    for k in sammelimport.kandidaten:
        if not k.wartet:
            continue
        befund = pruefe_entwurf(sammelimport, k)
        setze_befund(k, befund)
        stand[k.status] = stand.get(k.status, 0) + 1
        if sammelimport.entwurf(k).is_file():
            freigabe.append(fuer_die_freigabe(sammelimport, k, befund))
        if not als_json:
            print(f"  {k.nummer}  {k.status}{': ' + k.notiz if k.notiz else ''}")
    sammelimport.speichere()
    if als_json:
        print(json.dumps({"ordner": ordner, "kandidaten": freigabe}, ensure_ascii=False, indent=1))
    else:
        print(", ".join(f"{s} {stand.get(s, 0)}" for s in ("bereit", "rückfrage", "offen")))
    return 0


# --------------------------------------------------------------------------
# uebernehmen
# --------------------------------------------------------------------------

UMLAUTE = str.maketrans({"ä": "ae", "ö": "oe", "ü": "ue", "ß": "ss"})


def slug(titel: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", titel.lower().translate(UMLAUTE)).strip("-")


def _setze_feld(felder: list[str], name: str, wert: str) -> list[str]:
    """Die Zeilen des Frontmatters mit `name: wert`, ersetzt oder hinten angehängt."""
    zeile = f"{name}: {wert}"
    felder = [zeile if re.match(rf"{name}\s*:", z) else z for z in felder]
    return felder if zeile in felder else [*felder, zeile]


def als_karte(entwurf: str, uid: str, heute: str,
              schaubildnamen: list[str] | None = None) -> str:
    """Aus dem Text eines Kartenentwurfs der Text der Karte.

    `id` kommt als erstes Feld dazu, `angelegt` wird der Tag der Freigabe.
    `schaubildnamen`, wenn angegeben, ersetzt die Namen der Quellgrafiken neben
    dem Entwurf durch die in schaubilder/. Einer steht als Name da, mehrere als
    Liste. `## Freigabe` fällt weg: Vorschläge und Rückfragen sind mit dem Ja
    des Trainers erledigt und gehören nicht auf die Karte in der Halle. Dass
    das Frontmatter sauber schließt, hat `pruefe_entwurf` vorher festgestellt.
    """
    zeilen = entwurf.splitlines()
    ende = _frontmatter_ende(zeilen)
    if ende is None:
        raise ValueError("Kartenentwurf ohne geschlossenes Frontmatter")
    felder = [z for z in zeilen[1:ende] if not re.match(r"id\s*:", z)]
    felder = _setze_feld(felder, "angelegt", heute)
    if schaubildnamen:
        wert = (schaubildnamen[0] if len(schaubildnamen) == 1
                else f"[{', '.join(schaubildnamen)}]")
        felder = _setze_feld(felder, "schaubild", wert)

    rumpf = zeilen[ende + 1:]
    grenzen = _abschnitt_grenzen(rumpf, "Freigabe")
    if grenzen is not None:
        rumpf = rumpf[:grenzen[0]] + rumpf[grenzen[1]:]
    while rumpf and not rumpf[-1].strip():
        rumpf.pop()
    return "\n".join(["---", f"id: {uid}", *felder, "---", *rumpf]) + "\n"


def uebernimm(sammelimport: Sammelimport, k: Kandidat, notiz: str) -> str:
    """Schreibt die Karte eines freigegebenen Kandidaten. Gibt ihre ID zurück.

    Die Reihenfolge ist Absicht. Erst die Karte und ihr Schaubild, dann sofort
    die Übersicht, zuletzt aufräumen. Bricht der Lauf dazwischen ab, liegt
    höchstens ein Entwurf zu viel herum. Stünde die Übersicht zuletzt, fände
    der nächste Lauf einen offenen Kandidaten mit gültigem Entwurf und schriebe
    dieselbe Karte ein zweites Mal.

    Die Quellgrafik bekommt den Namen der Karte, wie jedes PlayDrill-Bild in
    schaubilder/. Mehrere bekommen ihn mit Nummer, in der Reihenfolge, in der
    der Entwurf sie nennt (#39). Liegt dort schon eine Datei unter einem
    dieser Namen, wird nichts geschrieben, auch die Karte nicht: Überschrieben
    wird in schaubilder/ nichts.
    """
    entwurf = sammelimport.entwurf(k)
    felder, _ = lies_frontmatter(entwurf)
    # Vor der Schleife in `uebernehmen` gab es schon eine. Scheitert sie hier,
    # ist der Bereich mitten im Durchgang voll geworden.
    try:
        uid = naechste_id(sammelimport.wurzel)
    except KeineId as fehler:
        raise NichtUebernommen(str(fehler)) from None
    name = f"{uid}-{slug(str(felder['titel']))}"
    ziel = sammelimport.wurzel / "uebungen" / f"{name}.md"
    # Welche Quellgrafiken, hat `pruefe_entwurf` sichergestellt: nur die
    # eigenen, jede einmal, und jede liegt da.
    quellgrafiken = [sammelimport.entwurfsordner / bild
                     for bild in schaubilder(felder.get("schaubild"))]
    nummern = ([f"-{nr}" for nr in range(1, len(quellgrafiken) + 1)]
               if len(quellgrafiken) > 1 else [""])
    verschoben = {quellgrafik: (sammelimport.wurzel / "schaubilder"
                                / f"{name}{nummer}{quellgrafik.suffix}")
                  for quellgrafik, nummer in zip(quellgrafiken, nummern)}
    belegt = [bild.name for bild in verschoben.values() if bild.exists()]
    if belegt:
        raise NichtUebernommen(f"schaubilder/{', schaubilder/'.join(belegt)} gibt es schon")
    text = als_karte(entwurf.read_text(encoding="utf-8"), uid, date.today().isoformat(),
                     [bild.name for bild in verschoben.values()])
    # "x" legt nur neu an. Eine Datei unter dieser ID gibt es laut
    # naechste_id() nicht, und falls doch, wird sie nicht überschrieben.
    with ziel.open("x", encoding="utf-8") as datei:
        datei.write(text)
    for quellgrafik, schaubild in verschoben.items():
        schaubild.parent.mkdir(exist_ok=True)
        shutil.move(quellgrafik, schaubild)
    sammelimport.bekannt.add(uid)
    schliesse_ab(sammelimport, k, "importiert", notiz, karte=uid)
    return uid


class NichtUebernommen(Exception):
    """Ein Kandidat, dessen Karte nicht geschrieben wurde. Der Text sagt, warum."""


def schliesse_ab(sammelimport: Sammelimport, k: Kandidat, status: str, notiz: str,
                 karte: str | None = None) -> None:
    """Trägt den Kandidaten als erledigt ein und löscht, was für ihn angelegt war.

    Erst die Übersicht, dann aufräumen. Bricht der Lauf dazwischen ab, liegt
    höchstens ein Entwurf zu viel herum, und kein erledigter Kandidat sieht
    wieder offen aus.

    Die Quellgrafiken verschwinden auch dann, wenn der Entwurf sie nicht
    eingetragen hat. Sie ließen sich jederzeit neu aus dem PDF schneiden.
    """
    k.setze(status, notiz, karte=karte)
    sammelimport.speichere()
    for datei in (sammelimport.entwurf(k), sammelimport.auftrag(k), *sammelimport.quellgrafiken(k)):
        datei.unlink(missing_ok=True)


def warum_nicht_wartend(k: Kandidat | None) -> str | None:
    """Warum ein genannter Kandidat nicht auf seine Karte wartet, oder None.

    Bei None, einer Nummer ohne Zeile in der Übersicht, gibt es immer einen
    Grund. Wer keinen bekommt, hat also einen Kandidaten in der Hand.
    """
    if k is None:
        return "steht nicht in der Übersicht"
    if not k.wartet:
        return f"ist {k.status}, nicht offen"
    return None


def pruefe_fuer_uebernahme(sammelimport: Sammelimport, k: Kandidat | None) -> str | None:
    """Warum ein Kandidat nicht übernommen werden kann, oder None.

    Prüft wie `pruefen`, setzt aber nichts (#40). Ein freigegebener Entwurf
    trägt die Antworten des Trainers. Ginge er zurück auf `offen`, entwürfe
    ihn der nächste Durchgang neu und überschriebe sie. Entwurf und Status
    bleiben also, wie sie sind, die Ausgabe nennt den Fehler, und der Skill
    bessert aus.
    """
    grund = warum_nicht_wartend(k)
    if grund or k is None:
        return grund
    return pruefe_entwurf(sammelimport, k).fehler


def uebernehmen(wurzel: Path, ordner: str, freigegeben: list[tuple[str, str]],
                uebersprungen: list[tuple[str, str]], ergaenzt: list[tuple[str, str]]) -> int:
    """Erledigt die Kandidaten, über die der Trainer bei der Freigabe entschieden hat.

    Freigegebene werden Karte. Gestrichene werden `übersprungen`, der Grund
    steht in der Notiz. Ein bestätigtes Duplikat hat der Skill schon in die
    bestehende Karte eingearbeitet, der Kandidat wird `ergänzt` und zeigt auf
    sie. Aus den beiden letzten entsteht keine Karte.

    Vor allem anderen muss der Quellenordner da sein (#40). Gleicht die
    Nextcloud eines Rechners quellen/ nicht ab, liegen dort die Entwürfe,
    aber weder Übersicht noch Quellen.
    """
    if not (wurzel / "quellen" / ordner).is_dir():
        raise Abbruch(f"Den Ordner quellen/{ordner}/ gibt es an diesem Rechner nicht. "
                      f"Gleicht die Nextcloud quellen/ hier ab?\nNichts übernommen.")
    sammelimport = Sammelimport(wurzel, ordner)
    sammelimport.verlange_freigabe()
    if not (freigegeben or uebersprungen or ergaenzt):
        raise Abbruch("Kein Kandidat genannt. Je Kandidat: --kandidat <nr> \"<notiz>\", "
                      "--uebersprungen <nr> \"<grund>\" oder --ergaenzt <nr> <id>")
    # Gibt es an diesem Rechner keine ID, dann für keinen Kandidaten. Das
    # steht einmal da, bevor irgendetwas geschrieben ist, statt je Kandidat.
    # Gestrichene und ergänzende Kandidaten brauchen keine ID.
    if freigegeben:
        try:
            naechste_id(wurzel)
        except KeineId as fehler:
            raise Abbruch(f"{fehler}\nNichts übernommen.") from None
    nach_nummer = {k.nummer: k for k in sammelimport.kandidaten}

    abgewiesen = 0
    for nummer, notiz in freigegeben:
        k = nach_nummer.get(nummer)
        grund = pruefe_fuer_uebernahme(sammelimport, k)
        if not grund and k is not None:
            try:
                print(f"  {nummer}  importiert als {uebernimm(sammelimport, k, notiz)}")
                continue
            except NichtUebernommen as fehler:
                grund = str(fehler)
        print(f"  {nummer}  nicht übernommen: {grund}")
        abgewiesen += 1

    # Je Kandidat ohne Karte: Status, Notiz, Karte, und was dagegen spricht.
    # `bekannt` kennt auch die Karten, die dieser Aufruf eben geschrieben
    # hat. Auch eine davon kann die ergänzte sein.
    ohne_karte = [
        (nummer, "übersprungen", grund.strip(), None, "" if grund.strip() else "ohne Grund")
        for nummer, grund in uebersprungen
    ] + [
        (nummer, "ergänzt", "", uid,
         "" if uid in sammelimport.bekannt else f"{uid} gibt es nicht in uebungen/")
        for nummer, uid in ergaenzt
    ]
    for nummer, status, notiz, karte, einwand in ohne_karte:
        k = nach_nummer.get(nummer)
        einwand = warum_nicht_wartend(k) or einwand
        if einwand:
            print(f"  {nummer}  nicht {status}: {einwand}")
            abgewiesen += 1
            continue
        schliesse_ab(sammelimport, k, status, notiz, karte=karte)
        print(f"  {nummer}  {status}: {notiz or karte}")

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
        if sammelimport.in_arbeit is not None:
            sammelimport.loesche_in_arbeit()
            sammelimport.speichere()
            print(f"in_arbeit in {SAMMELIMPORT} ist gelöscht.")
    return 1 if abgewiesen else 0


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
    vor.add_argument("--plan", action="store_true",
                     help="statt der Aufträge die Eingabe für den Zerlegungsplan anlegen")
    vor.add_argument("--trotzdem", action="store_true",
                     help="ohne --plan: weiter, auch wenn laut in_arbeit ein anderer Trainer "
                          "daran arbeitet")
    pr = befehle.add_parser("pruefen", help="den Status aus den Entwürfen auf der Platte setzen")
    pr.add_argument("ordner", type=quellenordner, help=hilfe)
    pr.add_argument("--json", action="store_true",
                    help="je Kandidat ausgeben, was die Freigabe im Chat braucht")
    ue = befehle.add_parser("uebernehmen", help="freigegebene Kandidaten als Karte übernehmen")
    ue.add_argument("ordner", type=quellenordner, help=hilfe)
    ue.add_argument("--kandidat", nargs=2, action="append", default=[],
                    metavar=("NR", "NOTIZ"),
                    help="ein freigegebener Kandidat und was der Trainer geändert hat")
    ue.add_argument("--uebersprungen", nargs=2, action="append", default=[],
                    metavar=("NR", "GRUND"),
                    help="ein Kandidat, den der Trainer gestrichen hat, und warum")
    ue.add_argument("--ergaenzt", nargs=2, action="append", default=[],
                    metavar=("NR", "ID"),
                    help="ein Kandidat, der als Duplikat eine bestehende Karte ergänzt hat")
    a = ap.parse_args()
    if a.befehl == "vorbereiten" and a.plan and a.trotzdem:
        ap.error("--trotzdem gilt nur ohne --plan, die Planeingabe trägt nicht ein, wer arbeitet")

    wurzel = a.wurzel.resolve() if a.wurzel else finde_wurzel()
    try:
        if a.befehl == "pruefen":
            return pruefen(wurzel, a.ordner, als_json=a.json)
        if a.befehl == "uebernehmen":
            return uebernehmen(wurzel, a.ordner, [tuple(p) for p in a.kandidat],
                               [tuple(p) for p in a.uebersprungen],
                               [tuple(p) for p in a.ergaenzt])
        if a.plan:
            return lege_planeingabe_an(wurzel, a.ordner)
        return vorbereiten(wurzel, a.ordner, trotzdem=a.trotzdem)
    except Abbruch as fehler:
        print(fehler)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
