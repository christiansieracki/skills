#!/usr/bin/env python3
"""Führt einen Sammelimport über einen Quellenordner, Kandidat für Kandidat.

    <python> sammelimport.py vorbereiten --plan <ordner> [--zurueckgestellte]
    <python> sammelimport.py vorbereiten <ordner> [--trotzdem]
    <python> sammelimport.py pruefen <ordner> [--json]
    <python> sammelimport.py uebernehmen <ordner> --kandidat 3 "Notiz" ...
                 --uebersprungen 4 "Grund" ... --zurueckgestellt 6 "Grund" ...
                 --ergaenzt 5 ue-000027 ...

`<ordner>` ist der Quellenordner, relativ zu `quellen/`. In ihm liegt die
`sammelimport.md` mit den Einstellungen im Frontmatter, den Absprachen und der
Übersicht, dem freigegebenen Zerlegungsplan mit dem Stand je Kandidat.

`vorbereiten --plan` legt vor dem Zerlegungsplan die Planeingabe an: jede
Datei, die noch in keiner Zeile der Übersicht steht und die `ohne:` nicht
auslässt, bei PDFs ihr Text mit einer Marke, wo jede Seite beginnt, dazu die
nächste freie Kandidatennummer und die Bibliotheksliste mit Übungs- und
Wissenskarten. Ein zweiter Lauf über denselben Ordner nimmt so nur, was neu
ist, und zählt weiter. Zurückgestellte Zeilen holt er nur mit
`--zurueckgestellte`. Den Text liest `pdftotext`, wenn es da ist (ADR-0008).

`vorbereiten` legt unter `kartenentwuerfe/<ordner>/` die Aufträge für die
nächsten offenen Kandidaten an, für Übungs- wie Wissenskarten, mit dem Text
jedes PDF, bei einem Seitenbereich nur dem dieser Seiten, bei einer Übung mit
der Angabe, ob der Ablauf aus dem Bild kommt, und trägt in `in_arbeit` ein,
welcher Trainer daran arbeitet. Arbeitet laut Eintrag ein anderer daran, geht
es nur mit `--trotzdem` weiter. Bei `quellgrafik: eingebettet` schneidet es
daneben für eine Übung aus jedem PDF mit Bild die Quellgrafik aus, dafür
braucht es Pillow (ADR-0005). Bei `quellgrafik: ausschnitt` schneidet es
nichts vorab, der Auftrag sagt, wie der Entwurf seine Ausschnitte nennt, eine
Übung in `schaubild:`, eine Wissenskarte als Bildverweis, und Pillow, bei
einem PDF auch `pypdfium2`, muss da sein (ADR-0013). `pruefen` setzt den Status aus
den Kartenentwürfen, die dort auf der Platte liegen, schneidet ihre
Ausschnitte neu aus und weist ab, was das Datenmodell bricht oder die Form der
Freigabe nicht einhält. Welche Sorte Karte ein Entwurf werden soll, sagt das
Ergebnis seiner Zeile. Mit `--json` gibt es aus, was die Freigabe im Chat
braucht. `uebernehmen` macht aus freigegebenen Entwürfen Karten in `uebungen/`
oder `wissen/`, erst jetzt mit ID (ADR-0010), je Sorte aus dem eigenen Zähler,
und legt die Quellgrafiken unter dem Namen der Karte in `schaubilder/` ab.
Nennt eine Wissenskarte unter `Übungen:` die Übungen aus demselben Beitrag,
trägt es deren IDs in ihre `uebungen` ein, gleich in welcher Reihenfolge beide
Karte werden.
Ein freigegebener Entwurf, der die Prüfung nicht besteht, bleibt mit seinem
Status stehen. Gestrichene, zurückgestellte und ergänzende Kandidaten
bekommen nur ihren Status.
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
from ausschnitt import BibliothekFehlt, KeinAusschnitt, schneide_aus, verlange_bibliotheken  # noqa: E402
from ausschnitt import FOTO as AUS_DEM_FOTO  # noqa: E402
from ausschnitt import PDF as AUS_DEM_PDF  # noqa: E402
from ausschnitt import ergebnis as ergebnis_des_ausschnitts  # noqa: E402
from bilder_aufbereiten import SCHWELLE, bilder, menschenmass  # noqa: E402
from bilder_aufbereiten import kandidaten as bilder_zum_aufbereiten  # noqa: E402
from tpdaten import (  # noqa: E402
    DISZIPLIN_SPALTE, ID_MUSTER, KARTENFELDER, SORTEN, UEBUNGSKARTE, WISSENSFELDER,
    WISSENSKARTE, Kartensorte, KeineId, als_liste, biege_bildverweise_um, bildverweise,
    finde_wurzel, hole_index, interpreter, konsole_vorbereiten, lies_frontmatter, lies_karten,
    lies_schwerpunkt_zeilen, lies_schwerpunkte, lies_uebungen, naechste_id, pruefe_felder,
    pruefe_wissensfelder, pruefe_wissensrumpf, schaubilder, tabellenzellen,
    trainer_dieses_rechners,
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

# Die Werte der Einstellung `quellgrafik:` (#63), siehe Sammelimport.art_der_quellgrafik.
QUELLGRAFIK = ("eingebettet", "ausschnitt", "keine")

SPALTEN = ["Kandidat", "Dateien", "Was es ist", "Ergebnis", "Status", "Karte", "Notiz"]

# Je Ergebnis, aus dem eine Karte wird, ihre Sorte (#69). Aus `uebung` und
# `folge` wird eine Übungskarte mit diesem `typ`, aus `wissen` eine
# Wissenskarte. `zurückgestellt` und `übersprungen` werden keine Karte.
SORTE_DES_ERGEBNISSES = {"uebung": UEBUNGSKARTE, "folge": UEBUNGSKARTE, "wissen": WISSENSKARTE}
ERGEBNISSE = {*SORTE_DES_ERGEBNISSES, "zurückgestellt", "übersprungen"}

# Die Sorten, für die es Auftrag, Agent und Prüfung gibt. Seit #70 sind es
# beide. Eine Sorte, die hier fehlt, wartet `offen`: Ein Durchgang legt ihr
# keinen Auftrag an, und `pruefen` lässt sie, wie sie ist.
ENTWORFENE_SORTEN = (UEBUNGSKARTE, WISSENSKARTE)

# Wie die Sorte in der Ausgabe von `vorbereiten` und in `pruefen --json`
# heißt. Daran wählt der Skill den Agenten, der den Entwurf schreibt, und die
# Tabelle, in der er ihn vorlegt.
SORTENNAME = {UEBUNGSKARTE: "uebungskarte", WISSENSKARTE: "wissenskarte"}

STATUS = {"offen", "bereit", "rückfrage", "importiert", "ergänzt", "übersprungen",
          "zurückgestellt"}

# Die Stände, in denen ein Kandidat noch auf seine Karte wartet. Alle anderen
# sind erledigt, und kein Aufruf fasst ihre Zeile mehr an.
NOCH_OFFEN = {"offen", "bereit", "rückfrage"}

# Die Stände, in denen ein Kandidat eine Karte hat, in der Spalte Karte: seine
# eigene, oder die, die er ergänzt hat.
MIT_KARTE = {"importiert", "ergänzt"}

# Damit beginnt am Ende von „Was es ist“ einer `wissen`-Zeile die Liste der
# Übungen aus demselben Beitrag, in der festen Form `Übungen: 13, 14, ue-000041`
# (#69): Kandidatennummern für Übungen dieses Plans, IDs für Übungen, die schon
# Karte sind.
UEBUNGEN_MARKE = "Übungen:"


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


# --------------------------------------------------------------------------
# Die Übersicht
# --------------------------------------------------------------------------

# Ein Seitenbereich, wie er in der Spalte Dateien hinter einem PDF steht:
# `S. 12–15` oder `S. 3`. Bindestrich und Halbgeviertstrich gelten beide, der
# Zerlegungsplan schreibt den Halbgeviertstrich, von Hand kommt oft der
# Bindestrich.
_SEITENBEREICH = re.compile(r"S\.\s*(\d+)(?:\s*[-–]\s*(\d+))?")

# Eine Datei in der Spalte Dateien: ihr Name in Backticks und, was bis zur
# nächsten Datei dahinter steht.
_DATEI_IN_DER_ZELLE = re.compile(r"`([^`]+)`([^`]*)")


@dataclass(frozen=True)
class Seitenbereich:
    """Die Seiten eines PDF, die zu einem Kandidaten gehören, beide Enden mitgezählt (#64)."""

    erste: int
    letzte: int

    def __str__(self) -> str:
        """So, wie der Bereich in der Übersicht und im Auftrag steht."""
        if self.erste == self.letzte:
            return f"S. {self.erste}"
        return f"S. {self.erste}–{self.letzte}"


def lies_seitenbereich(text: str) -> Seitenbereich:
    """Ein Seitenbereich aus seinem Text, oder ValueError mit dem Grund.

    Der ganze Text muss der Bereich sein. Aus „S. 3 bis 5“ nur Seite 3 zu
    lesen, gäbe dem Agenten still zu wenig. Den Text selbst nennt der Grund
    nicht, das tut, wer ihn gelesen hat, mit dem, was dazugehört.
    """
    treffer = _SEITENBEREICH.fullmatch(text.strip())
    if not treffer:
        raise ValueError("das ist kein Seitenbereich wie S. 12–15 oder S. 3")
    erste = int(treffer.group(1))
    letzte = int(treffer.group(2) or erste)
    if erste < 1:
        raise ValueError("der Bereich beginnt vor Seite 1")
    if letzte < erste:
        raise ValueError("der Bereich endet vor seiner ersten Seite")
    return Seitenbereich(erste, letzte)


@dataclass(frozen=True)
class Datei:
    """Eine Datei aus der Spalte Dateien, relativ zum Quellenordner.

    `angabe` ist, was in der Zelle hinter ihrem Namen steht, bei einem PDF
    der Seitenbereich (#64). Ohne Angabe gehört die ganze Datei zum
    Kandidaten, wie vor dem Seitenbereich. Ein Kandidat kann so aus einem
    langen PDF nur seine Seiten nehmen, und eine Datei kann mit
    verschiedenen Bereichen in mehreren Zeilen stehen.
    """

    name: str
    angabe: str = ""

    @property
    def seiten(self) -> Seitenbereich | None:
        """Der Seitenbereich, None für die ganze Datei.

        Lässt sich die Angabe nicht lesen, kommt ValueError. `vorbereiten`
        prüft das vor dem ersten Auftrag, siehe `pruefe_seitenbereiche`.
        """
        return lies_seitenbereich(self.angabe) if self.angabe else None

    def __str__(self) -> str:
        """So, wie die Datei in der Spalte Dateien steht."""
        return f"`{self.name}` {self.angabe}" if self.angabe else f"`{self.name}`"


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
    def sorte(self) -> Kartensorte | None:
        """Die Sorte der Karte, die aus dem Kandidaten wird, None, wenn keine wird."""
        return SORTE_DES_ERGEBNISSES.get(self.ergebnis)

    @property
    def wartet(self) -> bool:
        """Aus dem Kandidaten soll eine Karte werden, gleich welcher Sorte, und es gibt sie noch nicht.

        Solange einer wartet, ist im Quellenordner etwas offen, und
        `uebernehmen` räumt nicht auf.
        """
        return self.sorte is not None and self.status in NOCH_OFFEN

    @property
    def wartet_auf_entwurf(self) -> bool:
        """Er wartet, und für seine Sorte gibt es schon Auftrag und Prüfung.

        Nur diese Kandidaten nimmt ein Durchgang und prüft `pruefen`.
        """
        return self.wartet and self.sorte in ENTWORFENE_SORTEN

    @property
    def dateien(self) -> list[Datei]:
        """Die Dateien des Kandidaten, relativ zum Quellenordner, jede mit ihrer Angabe.

        In der Zelle steht jede in Backticks, weil Dateinamen Kommas tragen
        können, und dahinter, bei einem PDF, ein Seitenbereich. Das Komma vor
        der nächsten Datei gehört nicht zur Angabe. Eine von Hand
        geschriebene Zelle ohne Backticks wird an den Kommas getrennt, dann
        ohne Seitenbereich.
        """
        zelle = self.zellen["Dateien"]
        treffer = _DATEI_IN_DER_ZELLE.findall(zelle)
        if not treffer:
            return [Datei(d.strip()) for d in zelle.split(",") if d.strip()]
        return [Datei(name, angabe.strip().strip(",").strip()) for name, angabe in treffer]

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
        self.spalten = tabellenzellen(self.zeilen[kopf])
        fehlend = [s for s in SPALTEN if s not in self.spalten]
        if fehlend:
            raise self._abbruch(f"Es fehlen die Spalten {', '.join(fehlend)}.")
        self.anfang = self.ende = kopf + 2
        while self.ende < len(self.zeilen) and self.zeilen[self.ende].lstrip().startswith("|"):
            werte = tabellenzellen(self.zeilen[self.ende])
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
        nichts aus, und die Karten kämen ohne Bild heraus. Genannt wird der
        Name, den sie seit #63 hat. `quellgrafik_ausschneiden` dazwischen
        gilt weiter, siehe `art_der_quellgrafik`.
        """
        if "feldbild_ausschneiden" in self.einstellungen:
            raise Abbruch(f"In quellen/{self.ordner}/{SAMMELIMPORT} steht noch "
                          f"feldbild_ausschneiden. Die Einstellung heißt jetzt quellgrafik:\n"
                          f"aus feldbild_ausschneiden: true wird quellgrafik: eingebettet, "
                          f"aus false wird quellgrafik: keine.\n"
                          f"Es ist noch kein Auftrag geschrieben.")
        try:
            self.art_der_quellgrafik
        except Abbruch as fehler:
            raise Abbruch(f"{fehler}\nEs ist noch kein Auftrag geschrieben.") from None

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
    def art_der_quellgrafik(self) -> str:
        """Woher die Quellgrafik kommt: `eingebettet`, `ausschnitt` oder `keine` (#63).

        `eingebettet` ist das größte eingebettete Bild eines PDF, wie bei
        PlayDrill, `ausschnitt` heißt, der Entwurf nennt seine Ausschnitte.
        Bis #63 hieß die Einstellung `quellgrafik_ausschneiden`, und
        die `sammelimport.md` von PlayDrill trägt sie noch: `true` gilt als
        `eingebettet`, `false` als `keine`. Ohne Einstellung gilt `keine`, wie
        vorher. Stehen beide da, bricht das Skript ab, statt eine zu wählen.
        """
        datei = f"quellen/{self.ordner}/{SAMMELIMPORT}"
        alt = self.einstellungen.get("quellgrafik_ausschneiden")
        wert = self.einstellungen.get("quellgrafik")
        if wert is not None and alt is not None:
            raise Abbruch(f"In {datei} stehen quellgrafik und quellgrafik_ausschneiden. "
                          f"Es gilt quellgrafik, lösch quellgrafik_ausschneiden.")
        if wert is None:
            if alt is None:
                return "keine"
            if not isinstance(alt, bool):
                raise Abbruch(f"quellgrafik_ausschneiden in {datei} ist {alt!r}, erwartet ist "
                              f"true oder false. Es heißt jetzt quellgrafik, mit "
                              f"{', '.join(QUELLGRAFIK)}.")
            return "eingebettet" if alt else "keine"
        if wert not in QUELLGRAFIK:
            raise Abbruch(f"quellgrafik in {datei} ist {wert!r}, erwartet ist "
                          f"{', '.join(QUELLGRAFIK)}.")
        return wert

    @property
    def quellgrafik_angabe(self) -> str:
        """Die Einstellung zur Quellgrafik, so wie sie in der Datei steht, für eine Meldung."""
        alt = self.einstellungen.get("quellgrafik_ausschneiden")
        if self.einstellungen.get("quellgrafik") is None and alt is not None:
            return f"quellgrafik_ausschneiden: {'true' if alt else 'false'}"
        return f"quellgrafik: {self.art_der_quellgrafik}"

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

    def quellgrafik(self, k: Kandidat, nr: int | None = None, endung: str = ".png") -> Path:
        """Wo eine Quellgrafik des Kandidaten liegt.

        Ohne Nummer die einzige, `17.quellgrafik.png`. Hat der Kandidat
        mehrere, etwa ein Zirkel mit einem Bild je Blatt, heißen sie
        `17.quellgrafik-1.png`, `17.quellgrafik-2.png` und so weiter (#39).
        Ein Ausschnitt aus einem Foto ist ein JPEG und endet auf `.jpg` (#63).
        """
        nummer = "" if nr is None else f"-{nr}"
        return self.entwurfsordner / f"{k.nummer}.quellgrafik{nummer}{endung}"

    def ist_quellgrafik_von(self, k: Kandidat, name: str) -> bool:
        """Ist `name` eine Quellgrafik dieses Kandidaten, einzeln oder mit Nummer, PNG oder JPEG?"""
        muster = rf"{re.escape(k.nummer)}\.quellgrafik(-[1-9]\d*)?\.(png|jpg)"
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
# Die Übungen aus demselben Beitrag
# --------------------------------------------------------------------------

def _uebungen_angaben(k: Kandidat) -> list[str]:
    """Was hinter `Übungen:` in „Was es ist“ steht, je Angabe ein Text, ungeprüft.

    Die Liste hat nur eine `wissen`-Zeile, und sie steht am Ende, nach einem
    `ergänzt wi-######`. Ohne sie ist die Liste leer.
    """
    if k.sorte is not WISSENSKARTE:
        return []
    _, marke, liste = _nfc(k.was).rpartition(UEBUNGEN_MARKE)
    if not marke:
        return []
    return [angabe.strip() for angabe in liste.strip().rstrip(".").split(",") if angabe.strip()]


def uebungen_aus_dem_beitrag(sammelimport: Sammelimport,
                             k: Kandidat) -> tuple[list[Kandidat], list[str]]:
    """Die Übungen hinter `Übungen:`: die Zeilen der genannten Kandidaten und die IDs (#72).

    Eine Nummer muss eine Zeile der Übersicht sein, aus der eine Übung oder
    Folge wird, eine ID eine Karte in uebungen/. Sonst kommt ValueError mit
    der Angabe und dem Grund. Eine Zeile, die der Trainer bei der Freigabe
    gestrichen oder zurückgestellt hat, behält ihr Ergebnis und gilt weiter.
    Sie bringt nur nie eine ID mit.
    """
    nach_nummer = {z.nummer: z for z in sammelimport.kandidaten}
    zeilen: list[Kandidat] = []
    ids: list[str] = []
    for angabe in _uebungen_angaben(k):
        if angabe.isdigit():
            zeile = nach_nummer.get(angabe)
            if zeile is None:
                raise ValueError(f"{angabe}, das ist keine Zeile der Übersicht")
            if zeile.sorte is not UEBUNGSKARTE:
                raise ValueError(f"{angabe}, das ist keine Übung oder Folge, "
                                 f"sondern {zeile.ergebnis}")
            zeilen.append(zeile)
        elif re.fullmatch(ID_MUSTER, angabe):
            if angabe not in sammelimport.bekannt:
                raise ValueError(f"{angabe}, das gibt es nicht in uebungen/")
            ids.append(angabe)
        else:
            raise ValueError(f"„{angabe}“, das ist weder eine Kandidatennummer noch die ID "
                             f"einer Übung")
    return zeilen, ids


def ids_der_uebungen(sammelimport: Sammelimport, k: Kandidat) -> list[str]:
    """Die IDs, die laut `Übungen:` jetzt schon auf die Wissenskarte gehören, sortiert (#72).

    Das sind die genannten IDs und die Karten der genannten Kandidaten, die
    schon `importiert` oder `ergänzt` sind. Ein Kandidat, der noch wartet,
    bringt seine ID mit, wenn er Karte wird, siehe
    `trage_bei_wissenskarten_ein`. Einer, der übersprungen oder
    zurückgestellt ist, nie. ValueError wie bei `uebungen_aus_dem_beitrag`.
    """
    zeilen, ids = uebungen_aus_dem_beitrag(sammelimport, k)
    karten = [z.zellen["Karte"].strip() for z in zeilen if z.status in MIT_KARTE]
    return sorted({*ids, *(uid for uid in karten if re.fullmatch(ID_MUSTER, uid))})


def mit_uebungen(text: str, ids: list[str]) -> str:
    """Der Text einer Wissenskarte, in deren `uebungen` genau diese IDs stehen.

    Sonst bleibt der Text, wie er ist. Fehlt das Feld, etwa auf einer Karte
    von Hand, kommt es ans Ende des Frontmatters.
    """
    zeilen = text.splitlines()
    ende = _frontmatter_ende(zeilen)
    if ende is None:
        raise ValueError("Wissenskarte ohne geschlossenes Frontmatter")
    felder = _setze_feld(zeilen[1:ende], "uebungen", f"[{', '.join(ids)}]")
    return "\n".join(["---", *felder, "---", *zeilen[ende + 1:]]) + "\n"


def _ersetze(datei: Path, text: str) -> None:
    """Schreibt den Text erst daneben und benennt dann um, damit die Datei nie halb ist."""
    zwischen = datei.with_name(datei.name + ".neu")
    try:
        zwischen.write_text(text, encoding="utf-8")
        os.replace(zwischen, datei)
    finally:
        zwischen.unlink(missing_ok=True)


def trage_bei_wissenskarten_ein(sammelimport: Sammelimport, k: Kandidat, uid: str) -> list[str]:
    """Trägt eine Übung in jede schon übernommene Wissenskarte ein, die sie nennt (#72).

    Das Gegenstück zu `ids_der_uebungen`. Kommt die Wissenskarte vor ihren
    Übungen, fehlen ihr deren IDs noch, und jede Übung bringt ihre hier mit,
    ob sie Karte wird oder eine Karte ergänzt. So stimmt das Ergebnis in
    jeder Reihenfolge, auch in einem Aufruf, und keine ID steht doppelt.
    Zurück kommen die Zeilen für die Ausgabe.
    """
    if k.sorte is not UEBUNGSKARTE:
        return []
    wissenskarten = [w.zellen["Karte"].strip() for w in sammelimport.kandidaten
                     if w.status in MIT_KARTE and k.nummer in _uebungen_angaben(w)]
    if not wissenskarten:
        return []
    dateien = {str(karte["id"]): sammelimport.wurzel / karte["datei"]
               for karte in lies_karten(sammelimport.wurzel, WISSENSKARTE)}
    meldungen = []
    for wid in wissenskarten:
        datei = dateien.get(wid)
        if datei is None:
            meldungen.append(f"{wid} liegt nicht in wissen/, dort fehlt {uid} in uebungen")
            continue
        felder, _ = lies_frontmatter(datei)
        vorher = [str(u) for u in als_liste(felder.get("uebungen"))]
        if uid not in vorher:
            _ersetze(datei, mit_uebungen(datei.read_text(encoding="utf-8"),
                                         sorted({*vorher, uid})))
        meldungen.append(f"steht in uebungen von {wid}")
    return meldungen


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

# Dasselbe für den Entwurf einer Wissenskarte (#70). Auch `schwerpunkt` und
# `uebungen` stehen da, die auf der Karte freiwillig sind, dann als `[]`.
# Fehlte eins, wäre nicht zu unterscheiden, ob der Agent nichts gefunden oder
# das Feld vergessen hat.
WISSENSENTWURFSFELDER = [f for f in WISSENSFELDER if f not in ("id", "angelegt")]


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
class Ausschnitt:
    """Ein Ausschnitt aus `## Freigabe`: welche Quellgrafik woraus (#63).

    `datei` steht relativ zum Quellenordner wie in der Spalte Dateien,
    `seite` gibt es nur bei einem PDF und zählt dort ab 1. `rechteck` ist
    links, oben, rechts, unten in Prozent der aufrechten Seite, wie bei
    `ausschnitt.py`.
    """

    name: str
    datei: str
    seite: int | None
    rechteck: tuple[int, int, int, int]


@dataclass
class Befund:
    """Was die Prüfung eines Kartenentwurfs ergeben hat.

    Besteht er nicht, steht in `fehler` der Grund, und der Rest bleibt leer.
    Sonst trägt der Befund, was die Freigabe im Chat braucht. `quellgrafiken`
    sind die Namen der Quellgrafiken, die der Entwurf auf die Karte bringt,
    siehe `quellgrafiken_im_entwurf`.
    """

    fehler: str | None = None
    felder: dict = field(default_factory=dict)
    vorschlaege: list[Vorschlag] = field(default_factory=list)
    rueckfragen: list[Rueckfrage] = field(default_factory=list)
    aus_dem_bild: bool = False
    ausschnitte: list[Ausschnitt] = field(default_factory=list)
    quellgrafiken: list[str] = field(default_factory=list)

    @property
    def mit_vermutung(self) -> list[Rueckfrage]:
        return [r for r in self.rueckfragen if r.vermutung is not None]

    @property
    def ohne_vermutung(self) -> list[Rueckfrage]:
        return [r for r in self.rueckfragen if r.vermutung is None]


_LISTENKOPF = re.compile(r"^(Ausschnitte|Vorschläge|Rückfragen):\s*(.*)$")
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
    return [d.name for d in k.dateien
            if _ist_pdf(d.name) and any(f"`{d.name}`: " in z for z in zeilen)]


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
    # und ein doppeltes ließe sich nur einmal verschieben. Ob jede daneben
    # liegt, prüft `pruefe_quellgrafiken_daneben`, erst nach dem Schneiden der
    # Ausschnitte.
    gesehen: set[str] = set()
    for name in schaubilder(felder.get("schaubild")):
        if not sammelimport.ist_quellgrafik_von(k, name):
            raise Formfehler(f"schaubild: nennt {name}, das ist keine Quellgrafik dieses "
                             f"Kandidaten ({_namen_der_quellgrafiken(sammelimport, k)})")
        if name in gesehen:
            raise Formfehler(f"schaubild: nennt {name} zweimal")
        gesehen.add(name)


def _namen_der_quellgrafiken(sammelimport: Sammelimport, k: Kandidat) -> str:
    """Wie die Quellgrafiken eines Kandidaten heißen, für eine Meldung."""
    return (f"{sammelimport.quellgrafik(k).name}, bei mehreren "
            f"{sammelimport.quellgrafik(k, 1).name} und weiter, ein Ausschnitt aus einem Foto "
            f"auf .jpg")


def pruefe_quellgrafiken_daneben(sammelimport: Sammelimport, felder: dict) -> None:
    """Bricht mit Formfehler ab, wenn eine Quellgrafik aus `schaubild:` nicht neben dem Entwurf liegt.

    Etwa weil sie jemand beim Aufräumen gelöscht hat. Die Karte zeigte nach
    der Übernahme ins Leere.
    """
    for name in schaubilder(felder.get("schaubild")):
        if not (sammelimport.entwurfsordner / name).is_file():
            raise Formfehler(f"Quellgrafik {name} liegt nicht neben dem Entwurf")


def pruefe_wissensentwurf(sammelimport: Sammelimport, felder: dict) -> None:
    """Bricht mit Formfehler ab, wenn das Frontmatter einer Wissenskarte keine Karte ergibt (#70).

    Das Gegenstück zu `pruefe_frontmatter`, mit den Regeln, die der Linter
    an eine Wissenskarte legt, aus `pruefe_wissensfelder`. Den Text prüft
    `pruefe_wissenstext`, erst nach dem Schneiden der Ausschnitte. Eine
    Karte aus einem Entwurf, der beides besteht, hat dem Linter nichts zu
    melden. Gemeldet wird der erste Fehler, wie bei der Übungskarte.
    """
    if "id" in felder:
        raise Formfehler(f"Entwurf trägt id: {felder['id']}, die ID vergibt erst uebernehmen")
    fehlend = [f for f in WISSENSENTWURFSFELDER if f not in felder]
    if fehlend:
        raise Formfehler(f"Frontmatter ohne {', '.join(fehlend)}")
    befunde = pruefe_wissensfelder(felder, sammelimport.schwerpunkte, sammelimport.bekannt)
    if befunde:
        raise Formfehler(befunde[0])
    pruefe_quelldatei(sammelimport.wurzel, felder.get("quelldatei"))


def bildverweise_der_karte(rumpf: str) -> list[str]:
    """Die Bildverweise aus dem Text, der auf die Karte kommt, also ohne `## Freigabe`.

    `## Freigabe` fällt beim Übernehmen weg, siehe `als_karte`, und mit ihm
    jeder Verweis darin.
    """
    zeilen = rumpf.splitlines()
    grenzen = _abschnitt_grenzen(zeilen, "Freigabe")
    if grenzen is not None:
        zeilen = zeilen[:grenzen[0]] + zeilen[grenzen[1]:]
    return bildverweise("\n".join(zeilen))


def pruefe_bildverweise(ausschnitte: list[Ausschnitt], rumpf: str) -> None:
    """Bricht mit Formfehler ab, wenn ein Bildverweis im Entwurf einer Wissenskarte auf keinen Ausschnitt zeigt (#71).

    Eine Wissenskarte bekommt ihre Bilder nur als Ausschnitt. Neben dem
    Entwurf liegen nach `pruefen` genau die Ausschnitte aus seiner Liste, und
    nur sie trägt `uebernehmen` nach schaubilder/. Ein anderer Bildverweis
    zeigte auf der Karte ins Leere. Das gilt auch für einen gestrichenen
    Ausschnitt, dessen Datei noch vom letzten Lauf daneben liegt: Er soll
    nicht auf die Karte.
    """
    namen = {a.name for a in ausschnitte}
    for pfad in bildverweise_der_karte(rumpf):
        if pfad not in namen:
            raise Formfehler(f"Bildverweis {pfad} zeigt auf keine Quellgrafik neben dem Entwurf, "
                             f"nur ein Ausschnitt aus der Liste Ausschnitte: wird eine")


def pruefe_wissenstext(sammelimport: Sammelimport, rumpf: str) -> None:
    """Bricht mit Formfehler ab, wenn der Text einer Wissenskarte keine Karte ergibt (#70).

    Die beiden Abschnitte und die Bildverweise, mit `pruefe_wissensrumpf`
    wie im Linter, aufgelöst gegen den Ordner des Entwurfs. Deshalb erst,
    wenn die Ausschnitte geschnitten sind (#71).
    """
    befunde = pruefe_wissensrumpf(rumpf, sammelimport.entwurfsordner)
    if befunde:
        raise Formfehler(befunde[0])


def quellgrafiken_im_entwurf(k: Kandidat, felder: dict, rumpf: str) -> list[str]:
    """Die Namen der Quellgrafiken, die der Entwurf auf die Karte bringt, in ihrer Reihenfolge.

    Bei einer Übung die aus `schaubild:`, bei einer Wissenskarte die aus den
    Bildverweisen, in der Reihenfolge, in der sie im Text stehen, jede
    einmal (#71). So kommen sie auch nach schaubilder/: Auf der Karte liest
    man das erste Bild zuerst.
    """
    if k.sorte is WISSENSKARTE:
        return list(dict.fromkeys(bildverweise_der_karte(rumpf)))
    return schaubilder(felder.get("schaubild"))


# Ein Ausschnitt in `## Freigabe`, die Form ist die Entscheidung aus #61:
# `17.quellgrafik-2.png`: `Merkmale.pdf` S. 3, links 5, oben 20, rechts 95, unten 61
_AUSSCHNITT = re.compile(
    r"`(?P<name>[^`]+)`:\s*`(?P<datei>[^`]+)`(?:\s+S\.\s*(?P<seite>\d+))?\s*,\s*"
    r"links\s+(?P<links>\d+)\s*,\s*oben\s+(?P<oben>\d+)\s*,\s*"
    r"rechts\s+(?P<rechts>\d+)\s*,\s*unten\s+(?P<unten>\d+)\.?")


def lies_ausschnitte(rumpf: str) -> list[Ausschnitt]:
    """Die Liste `Ausschnitte:` unter `## Freigabe`, oder Formfehler, wenn ein Punkt sie verfehlt.

    Die Liste gibt es nur, wenn der Entwurf Ausschnitte hat (#63). Ohne sie,
    oder ohne `## Freigabe`, kommt eine leere Liste. Dass `## Freigabe`
    fehlt, meldet `lies_freigabe`.
    """
    freigabe = _abschnitt(rumpf.splitlines(), "Freigabe") or []
    ausschnitte = []
    for nr, text in enumerate(_listen(freigabe).get("Ausschnitte", []), 1):
        treffer = _AUSSCHNITT.fullmatch(text.strip())
        if not treffer:
            raise Formfehler(
                f"Ausschnitt {nr} hat nicht die feste Form `<name>`: `<datei>` S. <seite>, "
                f"links <zahl>, oben <zahl>, rechts <zahl>, unten <zahl>")
        seite = treffer.group("seite")
        ausschnitte.append(Ausschnitt(
            treffer.group("name").strip(), treffer.group("datei").strip(),
            int(seite) if seite else None,
            tuple(int(treffer.group(name)) for name in ("links", "oben", "rechts", "unten"))))
    return ausschnitte


def _bereiche(eintraege: list[Datei]) -> list[Seitenbereich] | None:
    """Die Seitenbereiche, mit denen eine Datei beim Kandidaten steht, None für die ganze Datei.

    Steht sie einmal ohne Bereich da, gehört sie ganz zum Kandidaten. Einen
    Bereich, den das Skript nicht lesen kann, hat `vorbereiten` schon
    abgewiesen. Hier schränkt er nichts ein.
    """
    bereiche = []
    for d in eintraege:
        try:
            bereich = d.seiten
        except ValueError:
            return None
        if bereich is None:
            return None
        bereiche.append(bereich)
    return bereiche


def pruefe_ausschnitte(sammelimport: Sammelimport, k: Kandidat, ausschnitte: list[Ausschnitt],
                       felder: dict, rumpf: str) -> None:
    """Bricht mit Formfehler ab, wenn ein Ausschnitt so nicht Quellgrafik werden kann (#63).

    Geprüft wird, was sich ohne Schneiden prüfen lässt. Der Name ist der
    einer Quellgrafik dieses Kandidaten und kommt einmal vor, sonst
    überschriebe ein Ausschnitt den anderen. Die Datei ist eine des
    Kandidaten, bei einem Seitenbereich auch die Seite. Die Endung passt zur
    Datei, wie bei `ausschnitt.py`. Und der Entwurf bringt den Ausschnitt auf
    die Karte: Bei einer Übung nennt ihn `schaubild:`, bei einer
    Wissenskarte ein Bildverweis im Text (#71). Was dort nicht steht, sähe
    der Trainer bei der Freigabe und vermisste es danach auf der Karte.
    """
    gesehen: set[str] = set()
    wissen = k.sorte is WISSENSKARTE
    eingetragen = set(quellgrafiken_im_entwurf(k, felder, rumpf))
    for a in ausschnitte:
        if not sammelimport.ist_quellgrafik_von(k, a.name):
            raise Formfehler(f"Ausschnitt {a.name} ist kein Name für eine Quellgrafik dieses "
                             f"Kandidaten ({_namen_der_quellgrafiken(sammelimport, k)})")
        if a.name in gesehen:
            raise Formfehler(f"Ausschnitt {a.name} steht zweimal da")
        gesehen.add(a.name)
        eintraege = [d for d in k.dateien if _nfc(d.name) == _nfc(a.datei)]
        if not eintraege:
            raise Formfehler(f"Ausschnitt {a.name} nennt {a.datei}, die Datei gehört nicht zu "
                             f"Kandidat {k.nummer}")
        try:
            endung, form = ergebnis_des_ausschnitts(Path(a.datei))
        except KeinAusschnitt as fehler:
            raise Formfehler(f"Ausschnitt {a.name}: {fehler}") from None
        if Path(a.name).suffix != endung:
            raise Formfehler(f"Ausschnitt {a.name}: aus {a.datei} wird ein {form}, der Name "
                             f"endet deshalb auf {endung}")
        bereiche = _bereiche(eintraege)
        if a.seite is not None and bereiche and not any(
                b.erste <= a.seite <= b.letzte for b in bereiche):
            raise Formfehler(f"Ausschnitt {a.name} nennt {a.datei} S. {a.seite}, zu Kandidat "
                             f"{k.nummer} gehört nur {', '.join(map(str, bereiche))}")
        if a.name not in eingetragen:
            raise Formfehler(f"Ausschnitt {a.name} steht in keinem Bildverweis im Text" if wissen
                             else f"Ausschnitt {a.name} fehlt in schaubild:")


def schneide_ausschnitte(sammelimport: Sammelimport, k: Kandidat,
                         ausschnitte: list[Ausschnitt]) -> None:
    """Schneidet jeden Ausschnitt neu aus und legt ihn neben den Entwurf (#63).

    Bei jedem Lauf, über dieselbe Funktion wie `ausschnitt.py`. Hat der
    Skill bei der Freigabe die Zahlen geändert, liegt danach der neue
    Ausschnitt da. Lässt sich einer nicht schneiden, etwa weil es die Seite
    nicht gibt, ist das ein Formfehler mit dem Grund aus `ausschnitt.py`.
    Fehlt eine Bibliothek, kommt BibliothekFehlt durch: Das ist kein Fehler
    des Entwurfs, und der Aufrufer bricht ab.
    """
    for a in ausschnitte:
        datei = next(d for d in k.dateien if _nfc(d.name) == _nfc(a.datei))
        try:
            schneide_aus(sammelimport.quellordner / datei.name,
                         sammelimport.entwurfsordner / a.name, a.rechteck, a.seite)
        except KeinAusschnitt as fehler:
            raise Formfehler(f"Ausschnitt {a.name}: {fehler}") from None


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

    Welche Sorte Karte der Entwurf werden soll, sagt das Ergebnis seiner
    Zeile, nicht der Entwurf selbst (#70). Ein Entwurf in der Form einer
    Übungskarte unter einer `wissen`-Zeile fällt so als Wissenskarte durch.
    Die Form der Freigabe ist für beide Sorten dieselbe. Aus dem Bild kommt
    nur der Ablauf einer Übung.

    Die Ausschnitte eines Entwurfs, der sonst besteht, werden dabei neu
    geschnitten, bei jedem Aufruf, der prüft: Was neben ihm liegt, folgt so
    immer den Zahlen in `## Freigabe`. Fehlt dafür eine Bibliothek, kommt
    BibliothekFehlt durch, siehe `schneide_ausschnitte`. Den Text einer
    Wissenskarte prüft es erst danach, denn ihre Bildverweise zeigen auf die
    Ausschnitte neben dem Entwurf (#71).
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
    wissen = k.sorte is WISSENSKARTE
    try:
        if wissen:
            pruefe_wissensentwurf(sammelimport, felder)
        else:
            pruefe_frontmatter(sammelimport, k, felder)
        vorschlaege, rueckfragen = lies_freigabe(rumpf, felder)
        ausschnitte = lies_ausschnitte(rumpf)
        pruefe_ausschnitte(sammelimport, k, ausschnitte, felder, rumpf)
        if wissen:
            pruefe_bildverweise(ausschnitte, rumpf)
        schneide_ausschnitte(sammelimport, k, ausschnitte)
        if wissen:
            pruefe_wissenstext(sammelimport, rumpf)
        else:
            pruefe_quellgrafiken_daneben(sammelimport, felder)
    except Formfehler as fehler:
        return Befund(str(fehler))
    aus_dem_bild = not wissen and laut_auftrag_aus_dem_bild(sammelimport.auftrag(k))
    return Befund(felder=felder, vorschlaege=vorschlaege, rueckfragen=rueckfragen,
                  aus_dem_bild=aus_dem_bild, ausschnitte=ausschnitte,
                  quellgrafiken=quellgrafiken_im_entwurf(k, felder, rumpf))


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
    Quelle. Ein PDF, das mit einem Seitenbereich in einer Zeile steht, ist
    auch nicht mehr neu, mit welchen Seiten auch immer (#64).

    Verglichen wird in einer Unicode-Form. macOS schreibt ein Ü im Dateinamen
    als U mit zwei Punkten, Windows und die Übersicht als ein Zeichen, und
    jeder Übungsordner von PlayDrill heißt `Ü_…`. Geöffnet wird die Datei
    über ihren Pfad, wie er auf der Platte steht.
    """
    im_plan = ({_nfc(d.name) for k in sammelimport.kandidaten for d in k.dateien}
               if sammelimport else set())
    alle = _auf_der_platte(quellordner)
    return {name: alle[name] for name in sorted(alle)
            if name not in im_plan and not (sammelimport and sammelimport.ausgelassen(name))}


def _auf_der_platte(quellordner: Path) -> dict[str, Path]:
    """Jede Datei des Quellenordners samt Unterordnern, außer der `sammelimport.md`.

    Der Schlüssel ist der Name relativ zum Quellenordner in NFC, der Wert der
    Pfad, wie er auf der Platte steht, siehe `neue_dateien`.
    """
    return {_nfc(p.relative_to(quellordner).as_posix()): p for p in quellordner.rglob("*")
            if p.is_file() and p.name != SAMMELIMPORT}


def zurueckgestellte_dateien(quellordner: Path, geholt: list[Kandidat]) -> dict[str, Path]:
    """Die Dateien der zurückgestellten Zeilen, die der Trainer holt (#69).

    Der Schlüssel ist der Name wie in `neue_dateien`. Fehlt eine Datei auf der
    Platte, steht sie trotzdem da, mit dem Pfad aus der Zeile. Der Agent
    merkt es beim Öffnen und sagt es im Plan.
    """
    alle = _auf_der_platte(quellordner)
    namen = {_nfc(d.name) for k in geholt for d in k.dateien}
    return {name: alle.get(name, quellordner / name) for name in sorted(namen)}


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


@cache
def pdf_seiten(pdftotext: str, pdf: Path) -> tuple[str, ...] | None:
    """Der Text eines PDF je Seite, oder None, wenn pdftotext es nicht lesen kann.

    `-enc UTF-8`, weil Xpdf sonst Latin-1 schreibt und aus „Ausführung"
    „Ausf�hrung" wird. `-raw`, weil Xpdf ohne es die Zeilen eines Absatzes zu
    einer zusammenzieht: Aus den Kopfzeilen „Trainer/Ersteller", „ZEIT" und
    „Werkzeuge" eines PlayDrill-Blatts würde eine. Poppler zieht nichts
    zusammen, mit `-raw` lesen beide gleich. Leere Zeilen fallen weg, sie
    kosten nur Platz.

    Geteilt wird am Seitenvorschub. Xpdf und Poppler schließen jede Seite
    damit ab, auch die letzte und eine ohne Text, die Zahl der Teile ist also
    die Zahl der Seiten (#64). Mit `-f` und `-l` ließe sich eine Seite nicht
    zählen: Hinter der letzten kommt dort nur nichts, ohne Fehler.

    Einmal je Aufruf und PDF: `vorbereiten` zählt erst die Seiten, dann
    schreibt es die Aufträge, und mehrere Kandidaten teilen sich ein Heft.
    """
    try:
        lauf = subprocess.run([pdftotext, "-raw", "-enc", "UTF-8", str(pdf), "-"],
                              capture_output=True, timeout=60, check=False)
    except (OSError, subprocess.TimeoutExpired):
        return None
    if lauf.returncode != 0:
        return None
    text = lauf.stdout.decode("utf-8", errors="replace").removesuffix("\f")
    return tuple("\n".join(z.strip() for z in seite.splitlines() if z.strip())
                 for seite in text.split("\f"))


def pdf_text(seiten: tuple[str, ...] | None) -> str | None:
    """Der Text von Seiten am Stück, leer, wenn keine Text hat, None bleibt None."""
    if seiten is None:
        return None
    return "\n".join(seite for seite in seiten if seite)


# Die Marke, mit der in der Planeingabe jede Seite eines PDF beginnt (#64).
SEITENMARKE = "=== Seite {} ==="


def mit_seitenmarken(seiten: tuple[str, ...] | None,
                     nur: set[int] | None = None) -> str | None:
    """Der Text eines PDF am Stück, vor jeder Seite ihre Marke, gezählt ab 1.

    Daran nennt der Zerlegungsplan Seitenbereiche. Auch eine Seite ohne Text
    bekommt ihre Marke, sonst verrutschte die Zählung danach. Hat keine Seite
    Text, bleibt es leer wie bei `pdf_text`: Marken allein wären kein Text,
    und der Agent soll lesen, dass er das PDF selbst öffnen muss.

    `nur` beschränkt den Text auf diese Seiten, etwa die einer
    zurückgestellten Zeile (#69). Ihre Marken tragen die Nummer im PDF.

    Im Auftrag stehen die Marken bei `quellgrafik: ausschnitt`, denn ein
    Ausschnitt nennt seine Seite (#63). Bei einem Seitenbereich ist `nur`
    der Bereich, und die Marken zählen auch dort wie im PDF.
    """
    if seiten is None:
        return None
    gewaehlt = [(nummer, seite) for nummer, seite in enumerate(seiten, 1)
                if nur is None or nummer in nur]
    if not any(seite for _, seite in gewaehlt):
        return ""
    zeilen: list[str] = []
    for nummer, seite in gewaehlt:
        zeilen += [SEITENMARKE.format(nummer), *([seite] if seite else [])]
    return "\n".join(zeilen)


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


def _als_text(wert: object) -> str:
    """Ein Feld einer Karte für eine Zelle, eine Liste durch Komma getrennt."""
    if isinstance(wert, list):
        return ", ".join(map(str, wert))
    return str(wert or "")


def bibliotheksliste(wurzel: Path, ordner: str) -> list[str]:
    """Jede Karte der Bibliothek als Tabelle je Sorte, die aus diesem Quellenordner markiert.

    Daran erkennt der Agent für den Zerlegungsplan, was schon importiert ist,
    und führt es als `importiert` mit seiner ID. Titel und Element einer
    Übungskarte braucht er, um einen Verdacht auf ein Duplikat zu äußern.
    Bei einer Wissenskarte sind es Frage und Thema, und dazu kommt der
    Verdacht, dass ein Beitrag die Fortsetzung einer Karte aus einem
    früheren Heft ist (#69).
    """
    teile = [(UEBUNGSKARTE, "Übungskarten", ["Titel", "Element"], ["titel", "element"]),
             (WISSENSKARTE, "Wissenskarten", ["Frage", "Thema"], ["titel", "thema"])]
    zeilen: list[str] = []
    for sorte, ueberschrift, spalten, felder in teile:
        kopf = ["ID", *spalten, "quelldatei", "Aus diesem Ordner"]
        zeilen += [f"### {ueberschrift}", "",
                   "| " + " | ".join(kopf) + " |", "|" + "---|" * len(kopf)]
        for karte in sorted(lies_karten(wurzel, sorte), key=lambda k: str(k["id"])):
            zellen = [karte["id"], *(_als_text(karte.get(f)) for f in felder),
                      _als_text(karte.get("quelldatei")),
                      "ja" if aus_diesem_ordner(karte.get("quelldatei"), ordner) else ""]
            zeilen.append("| " + " | ".join(_zelle(z) for z in zellen) + " |")
        zeilen.append("")
    return zeilen[:-1]


def melde_unlesbare_fotos(ordner: str, quellordner: Path,
                          sammelimport: Sammelimport | None) -> None:
    """Nennt die Fotos im Quellenordner, die der Agent so nicht lesen kann.

    Das sind die über der Schwelle und jedes TIFF und HEIC, auch ein kleines,
    denn das Lesewerkzeug zeigt nur JPEG und PNG. Welche das sind, sagt
    `bilder_aufbereiten.py`, damit es hier dasselbe heißt wie dort, wo es
    behoben wird. Genannt werden alle Fotos des Ordners, nicht nur die neuen:
    Auch ein Foto, das schon im Plan steht, muss der Agent für den Entwurf
    öffnen können. Nur was `ohne:` auslässt, öffnet kein Agent, das fehlt hier.
    """
    unlesbar, _lesbar = bilder_zum_aufbereiten(quellordner)
    namen = {pfad: _nfc(pfad.relative_to(quellordner).as_posix()) for pfad in unlesbar}
    unlesbar = [pfad for pfad in unlesbar
                if not (sammelimport and sammelimport.ausgelassen(namen[pfad]))]
    if not unlesbar:
        return
    print(f"{bilder(len(unlesbar))} so nicht lesbar, über {menschenmass(SCHWELLE)} "
          f"oder weder JPEG noch PNG:")
    for pfad in unlesbar:
        print(f"  {namen[pfad]}  {menschenmass(pfad.stat().st_size)}")
    print(f"Vorher aufbereiten, mit Rückfrage: "
          f"'{interpreter()} bilder_aufbereiten.py quellen/{ordner}'\n")


def _text_oder_grund(text: str | None, pdftotext: str | None,
                     seiten: Seitenbereich | None = None) -> list[str]:
    """Was unter einem PDF steht: sein Text, oder warum keiner da ist.

    Ohne Text muss der Agent das PDF selbst lesen, und das soll er nicht aus
    einer leeren Stelle schließen müssen. Gehören nur einige Seiten zum
    Kandidaten, liest er nur sie (#64).
    """
    if text:
        return _eingezaeunt(text)
    if not pdftotext:
        grund = "Ohne Text, pdftotext fehlt."
    elif text is None:
        grund = "pdftotext konnte die Datei nicht lesen."
    else:
        grund = "Keine Textebene."
    nur = f", nur {seiten}" if seiten else ""
    return [f"{grund} Das PDF selbst lesen{nur}."]


def seitenbereiche_der_zeilen(geholt: list[Kandidat]) -> dict[str, list[Seitenbereich]]:
    """Je Datei der geholten Zeilen die Seitenbereiche, die sie nennen (#69).

    Der Rest eines aufgeteilten PDF steht schon in anderen Zeilen. Käme er
    wieder, plante der Agent ihn ein zweites Mal. Nennt eine der Zeilen die
    Datei ohne Bereich, oder mit einem, der sich nicht lesen lässt, gehört
    sie ganz dazu und fehlt hier. Den Bereich, so wie er dasteht, sieht der
    Agent dann unter „Zurückgestellt“.
    """
    ganz: set[str] = set()
    bereiche: dict[str, set[Seitenbereich]] = {}
    for k in geholt:
        for d in k.dateien:
            try:
                bereich = d.seiten
            except ValueError:
                bereich = None
            if bereich is None:
                ganz.add(_nfc(d.name))
            else:
                bereiche.setdefault(_nfc(d.name), set()).add(bereich)
    return {name: sorted(menge, key=lambda b: (b.erste, b.letzte))
            for name, menge in bereiche.items() if name not in ganz}


def zurueckgestellt_teil(geholt: list[Kandidat]) -> list[str]:
    """Der Abschnitt der Planeingabe mit den zurückgestellten Zeilen, die der Trainer holt.

    Je Zeile Nummer, Dateien, „Was es ist“ und Notiz (#69). Daraus weiß der
    Agent, was ein früherer Lauf über die Dateien schon gesagt hat, und
    welche Nummer seine erste Zeile daraus trägt.
    """
    zeilen = ["## Zurückgestellt", "",
              "Diese Zeilen der Übersicht sind zurückgestellt, und der Trainer holt sie "
              "jetzt. Ihre Dateien stehen unter „Dateien“.", "",
              "| Kandidat | Dateien | Was es ist | Notiz |", "|---|---|---|---|"]
    for k in geholt:
        zellen = [k.nummer, ", ".join(map(str, k.dateien)), k.was, k.notiz]
        zeilen.append("| " + " | ".join(_zelle(z) for z in zellen) + " |")
    return [*zeilen, ""]


def lege_planeingabe_an(wurzel: Path, ordner: str, zurueckgestellte: bool = False) -> int:
    """Legt die Eingabe für den Zerlegungsplan an.

    Der Agent liest sie in einem Aufruf: jede Datei, die noch in keiner Zeile
    der Übersicht steht, bei PDFs mit ihrem Text und den Seitenmarken, und
    die Bibliotheksliste.
    Der Quellenordner steht einmal absolut im Kopf, denn Fotos und PDFs ohne
    Text öffnet der Agent selbst. Dazu die nächste freie Kandidatennummer, ab
    der er zählt.

    Mit `zurueckgestellte` holt der Trainer die zurückgestellten Zeilen
    (#69): Ihre Dateien kommen zu den neuen, und die Zeilen selbst stehen
    unter „Zurückgestellt“. Ohne den Schalter kommt keine wieder, auch nicht
    eine, die der Trainer bewusst zurückgestellt hat.
    """
    sammelimport = vorhandener_sammelimport(wurzel, ordner)
    quellordner = wurzel / "quellen" / ordner
    neu = neue_dateien(quellordner, sammelimport)
    geholt = ([k for k in sammelimport.kandidaten if k.status == "zurückgestellt"]
              if zurueckgestellte and sammelimport else [])
    aus_geholten = zurueckgestellte_dateien(quellordner, geholt)
    dateien = dict(sorted({**neu, **aus_geholten}.items()))
    melde_unlesbare_fotos(ordner, quellordner, sammelimport)
    if not dateien:
        wo = ("in der Übersicht oder unter ohne" if sammelimport and sammelimport.ohne
              else "in der Übersicht")
        keine = ", und keine Zeile ist zurückgestellt" if zurueckgestellte else ""
        print(f"Keine neuen Dateien in quellen/{ordner}/, jede steht schon {wo}{keine}.")
        return 0
    pdfs = {name for name in dateien if _ist_pdf(name)}
    pdftotext = finde_pdftotext() if pdfs else None
    if pdfs and not pdftotext:
        melde_ohne_pdftotext("die Planeingabe", "den Zerlegungsplan")
    nur = seitenbereiche_der_zeilen(geholt)
    seiten_von = {name: {n for b in bereiche for n in range(b.erste, b.letzte + 1)}
                  for name, bereiche in nur.items()}
    texte = ({name: mit_seitenmarken(pdf_seiten(pdftotext, dateien[name]), seiten_von.get(name))
              for name in pdfs}
             if pdftotext else {})

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
             f"{len(neu)} Dateien, die noch in keiner Zeile der Übersicht stehen, "
             f"relativ zum Quellenordner.",
             *([f"Dazu {len(aus_geholten)} Dateien aus {len(geholt)} zurückgestellten "
                f"Zeilen, siehe „Zurückgestellt“."] if geholt else []),
             *textlage, "",
             *(zurueckgestellt_teil(geholt) if geholt else []),
             "## Dateien", ""]
    for datei in dateien:
        teile += [f"### `{datei}`", ""]
        if datei in pdfs and datei in nur:
            teile += [f"Nur {', '.join(map(str, nur[datei]))}, aus den zurückgestellten Zeilen. "
                      f"Die übrigen Seiten stehen schon in anderen Zeilen.", ""]
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
            f"{sammelimport.ordner}/{SAMMELIMPORT} steht {sammelimport.quellgrafik_angabe}.\n\n"
            f"Installieren mit:\n  {interpreter()} -m pip install Pillow\n\n"
            f"Es ist noch kein Auftrag geschrieben.") from None


def verlange_bibliotheken_fuer_ausschnitte(sammelimport: Sammelimport,
                                           dran: list[Kandidat]) -> None:
    """Bricht ab, wenn den Ausschnitten des Durchgangs eine Bibliothek fehlt (ADR-0013).

    Pillow braucht jeder Ausschnitt, `pypdfium2` nur einer aus einem PDF.
    Gefragt wird deshalb nach `pypdfium2` nur, wenn ein Kandidat des
    Durchgangs ein PDF hat. Vor dem ersten Auftrag, aus demselben Grund wie
    bei `verlange_pillow`: Sonst kämen Entwürfe mit Ausschnitten, die
    `pruefen` nicht schneiden kann.
    """
    try:
        verlange_bibliotheken(any(_ist_pdf(d.name) for k in dran for d in k.dateien))
    except BibliothekFehlt as fehler:
        raise Abbruch(f"In quellen/{sammelimport.ordner}/{SAMMELIMPORT} steht "
                      f"{sammelimport.quellgrafik_angabe}.\n{fehler}\n\n"
                      f"Es ist noch kein Auftrag geschrieben.") from None


def lege_quellgrafiken_an(sammelimport: Sammelimport, k: Kandidat) -> tuple[list[str], list[str]]:
    """Schneidet die Quellgrafiken eines Kandidaten aus, bei `quellgrafik: eingebettet`.

    Alte Quellgrafiken neben dem Entwurf räumt es vorher in jedem Fall weg,
    auch Ausschnitte. Bei `ausschnitt` schneidet es nichts, die Zeile im
    Auftrag verweist auf `## Ausschnitte`, siehe `ausschnitte_im_auftrag`.

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
    # Eine Wissenskarte hat kein `schaubild:`. Ihre Bilder stehen als Verweis
    # im Text, an der Kernaussage, die sie zeigen, und kommen nur als
    # Ausschnitt (#71). Das größte eingebettete Bild eines PDF zeigt bei
    # Theorie selten, was eine Kernaussage erklärt (#61).
    if k.sorte is WISSENSKARTE:
        if sammelimport.art_der_quellgrafik == "ausschnitt":
            return ["- Bilder: als Ausschnitt mit Bildverweis, wenn die Quelle ein Bild zeigt, "
                    "das eine Kernaussage erklärt, siehe `## Ausschnitte`."], []
        return ["- Bilder: keine. Setz keinen Bildverweis in den Entwurf."], []
    if sammelimport.art_der_quellgrafik == "ausschnitt":
        # Vorab geschnitten wird nichts, der Entwurf nennt seine Ausschnitte,
        # und `pruefen` schneidet sie (#63).
        return ["- Quellgrafik: als Ausschnitt, wenn die Quelle ein Bild der Übung zeigt, "
                "siehe `## Ausschnitte`."], []
    if sammelimport.art_der_quellgrafik != "eingebettet":
        return ["- Quellgrafik: wird bei dieser Quelle nicht ausgeschnitten."], []
    pdfs = [d.name for d in k.dateien if _ist_pdf(d.name)]
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


def dateien_im_auftrag(sammelimport: Sammelimport, k: Kandidat,
                       pdftotext: str | None) -> tuple[list[str], list[str | None]]:
    """Der Abschnitt `## Dateien` eines Auftrags, und je Datei ihr Text.

    Je Datei steht ihr Pfad absolut da, denn der Agent öffnet sie damit.
    Unter jedem PDF steht sein Text, anders als in der Planeingabe nie
    gekappt: Der Agent schreibt aus ihm die Karte. Ohne Text steht da, warum,
    und dass er das PDF selbst lesen muss.

    Nennt der Kandidat Seiten, steht nur deren Text da, und der Abschnitt
    sagt, welche Seiten der Agent im PDF öffnet (#64). Der Text je Datei geht
    an die Regel „wenig Text“, None bei einem Foto oder ohne Text.

    Bei `quellgrafik: ausschnitt` steht vor jeder Seite ihre Marke, gezählt
    wie im PDF, auch bei einem Seitenbereich. Ein Ausschnitt nennt seine
    Seite, und ab 1 gezählt träfe er bei einem Bereich die falsche.
    """
    marken = sammelimport.art_der_quellgrafik == "ausschnitt"
    zeilen: list[str] = []
    texte: list[str | None] = []
    for d in k.dateien:
        pfad = sammelimport.quellordner / d.name
        zeilen += [f"### `{d.name}`", "", f"`{pfad.as_posix()}`", ""]
        if not _ist_pdf(d.name):
            texte.append(None)
            continue
        bereich = d.seiten
        if bereich:
            zeilen += [f"Zu diesem Kandidaten gehören nur {bereich}. Öffnest du das PDF, "
                       f"lies nur diese Seiten.", ""]
        alle = pdf_seiten(pdftotext, pfad) if pdftotext else None
        seiten = alle
        if bereich and alle is not None:
            seiten = alle[bereich.erste - 1:bereich.letzte]
        text = pdf_text(seiten)
        texte.append(text)
        if marken and text:
            text = mit_seitenmarken(
                alle, set(range(bereich.erste, bereich.letzte + 1)) if bereich else None)
        zeilen += [*_text_oder_grund(text, pdftotext, bereich), ""]
    return zeilen, texte


def endung_des_ausschnitts(datei: str) -> str | None:
    """Die Endung eines Ausschnitts aus dieser Datei: `.jpg` beim Foto, `.png` beim PDF.

    None für eine Datei, aus der `ausschnitt.py` nichts schneidet, etwa ein
    TIFF, das noch nicht aufbereitet ist.
    """
    try:
        return ergebnis_des_ausschnitts(Path(datei))[0]
    except KeinAusschnitt:
        return None


def ausschnitte_im_auftrag(sammelimport: Sammelimport, k: Kandidat) -> list[str]:
    """Der Abschnitt `## Ausschnitte` eines Auftrags bei `quellgrafik: ausschnitt` (#63).

    Er sagt dem Agenten, in welcher Form der Entwurf seine Ausschnitte nennt
    und wie sie heißen, mit einer Datei dieses Kandidaten als Beispiel. Die
    Endung folgt der Quelle, wie bei `ausschnitt.py`: aus einer PDF-Seite ein
    PNG, aus einem Foto ein JPEG. Genannt werden nur die Endungen, die bei
    diesem Kandidaten vorkommen. Die Seite eines PDF zählt wie die Marken im
    Text, bei einem Seitenbereich ist das Beispiel seine erste Seite.

    Eine Übung trägt ihre Ausschnitte in `schaubild:`, eine Wissenskarte
    setzt jeden als Bildverweis an die Kernaussage, die er zeigt (#71). Nur
    darin unterscheidet sich der Abschnitt für die beiden Sorten.
    """
    wissen = k.sorte is WISSENSKARTE
    moeglich = [(d, endung) for d in k.dateien if (endung := endung_des_ausschnitts(d.name))]
    if not moeglich:
        ohne = ("der Entwurf hat keinen Bildverweis" if wissen else "`schaubild:` ist `null`")
        return ["## Ausschnitte", "",
                f"Aus keiner Datei dieses Kandidaten lässt sich ein Ausschnitt schneiden, nur aus "
                f"einem Foto (JPEG, PNG) oder einem PDF. Es gibt keinen, und {ohne}.", ""]
    datei, endung = moeglich[0]
    pdf, foto = AUS_DEM_PDF[0], AUS_DEM_FOTO[0]
    seite = f" S. {datei.seiten.erste if datei.seiten else 1}" if endung == pdf else ""
    einzeln = sammelimport.quellgrafik(k, endung=endung).name
    mehrere = [sammelimport.quellgrafik(k, nr, endung).name for nr in (1, 2)]
    endungen = {e for _, e in moeglich}
    regeln = {pdf: (f"`{pdf}` aus einer PDF-Seite",
                    "Bei einem PDF steht dahinter die Seite, gezählt im PDF ab 1 wie in den "
                    "Marken `=== Seite 1 ===` im Text, nicht die Seitenzahl, die auf der Seite "
                    "gedruckt ist."),
              foto: (f"`{foto}` aus einem Foto", "Bei einem Foto steht keine Seite.")}
    gilt = [regeln[e] for e in (pdf, foto) if e in endungen]
    if wissen:
        wozu = [
            "Zeigt die Quelle ein Bild, das eine Kernaussage erklärt, etwa eine Bildreihe oder "
            "eine Kurve, nennst du es als Ausschnitt: unter `## Freigabe` in einer eigenen Liste "
            "vor den Vorschlägen, ein Punkt je Ausschnitt. Dazu setzt du jeden Ausschnitt als "
            "Bildverweis an die Kernaussage, die er zeigt, mit seinem Namen als Pfad. Hat die "
            "Quelle kein Bild, das etwas erklärt, gibt es keinen Ausschnitt, keine Liste und "
            "keinen Bildverweis.", "",
            "```markdown",
            "Ausschnitte:",
            f"- `{einzeln}`: `{datei.name}`{seite}, links 8, oben 42, rechts 94, unten 88",
            "```", "",
            f"- Bildverweis: `![Bildreihe oberes Zuspiel]({einzeln})`, in einer eigenen Zeile "
            f"unter der Kernaussage. Jeder Ausschnitt steht in einem Bildverweis, und jeder "
            f"Bildverweis nennt einen Ausschnitt aus der Liste.",
        ]
        reihenfolge = "im Bildverweis genau mit diesem Namen"
    else:
        wozu = [
            "Zeigt die Quelle ein Bild der Übung, nennst du es als Ausschnitt: unter "
            "`## Freigabe` in einer eigenen Liste vor den Vorschlägen, ein Punkt je Ausschnitt, "
            "und `schaubild:` trägt seinen Namen. Hat die Quelle kein Bild der Übung, gibt es "
            "keinen Ausschnitt und keine Liste, und `schaubild:` ist `null`.", "",
            "```markdown",
            "Ausschnitte:",
            f"- `{einzeln}`: `{datei.name}`{seite}, links 8, oben 42, rechts 94, unten 88",
            "```", "",
        ]
        reihenfolge = "in `schaubild:` als Liste in derselben Reihenfolge"
    return [
        "## Ausschnitte", "",
        *wozu,
        f"- Name: ein einzelner Ausschnitt heißt `{einzeln}`, mehrere `{mehrere[0]}`, "
        f"`{mehrere[1]}` und weiter, {reihenfolge}. "
        f"Die Endung ist {', '.join(e for e, _ in gilt)}.",
        f"- Datei: wie unter `## Dateien`, relativ zum Quellenordner. "
        f"{' '.join(regel for _, regel in gilt)}",
        "- Rechteck: links, oben, rechts, unten in ganzen Prozent der Seite, wie sie aufrecht "
        "steht. Links ist kleiner als rechts, oben kleiner als unten.", "",
    ]


def uebungen_im_auftrag(sammelimport: Sammelimport, k: Kandidat) -> str:
    """Die Zeile im Auftrag einer Wissenskarte mit den Übungen aus demselben Beitrag (#72).

    Mit ID genannt werden die, die schon Karte sind. Die trägt der Agent in
    `uebungen` ein, die Bibliothek kennt er sonst nicht. Ein Kandidat, der
    noch wartet, hat keine ID. Er steht nur mit seiner Nummer da, damit der
    Agent sie nicht für eine ID hält, und `uebernehmen` trägt ihn nach.
    Dass sich `Übungen:` lesen lässt, hat `vorbereiten` vorher geprüft.
    """
    zeilen, _ = uebungen_aus_dem_beitrag(sammelimport, k)
    ids = ids_der_uebungen(sammelimport, k)
    if ids:
        text = f"{', '.join(ids)}. Trag genau diese in `uebungen` ein."
    elif _uebungen_angaben(k):
        text = "noch keine ist Karte. `uebungen` bleibt `[]`."
    else:
        text = "keine. `uebungen` bleibt `[]`."
    wartend = [z.nummer for z in zeilen if z.wartet]
    if wartend:
        text += (f" Noch ohne Karte und ohne ID: Kandidat {', '.join(wartend)}. Das trägt "
                 f"`uebernehmen` nach.")
    return f"- Übungen aus demselben Beitrag: {text}"


def schreibe_auftrag(sammelimport: Sammelimport, k: Kandidat, kennungen: list[str],
                     pdftotext: str | None, quellgrafikzeilen: list[str]) -> Path:
    """Legt den Auftrag für einen Kandidaten an, alles, was der Agent braucht.

    Die Pfade stehen absolut da, denn der Agent liest und schreibt mit ihnen.
    `quelldatei:` steht relativ zu `quellen/`, so wie auf der Karte, damit sie
    auf jedem Rechner stimmt, egal wo dort der Arbeitsordner liegt. Sie nennt
    die Dateien ohne Seitenbereich, die Seiten kommen in `quelle` (#64).

    Der Auftrag einer Wissenskarte hat dieselbe Form, nur ohne die Zeile
    „Ablauf aus dem Bild“ (#70): Eine Wissenskarte hat keinen Ablauf, den die
    Regel „wenig Text“ zählen könnte. Die Kennungen kommen für beide Sorten
    samt den Steuerungsschwerpunkten. Die stehen auf keiner Übungskarte, auf
    einer Wissenskarte schon. Dafür nennt er die Übungen aus demselben
    Beitrag, die schon Karte sind (#72).
    """
    relativ = [f"{sammelimport.ordner}/{d.name}" for d in k.dateien]
    dateien, texte = dateien_im_auftrag(sammelimport, k, pdftotext)
    ablauf = [ablauf_aus_dem_bild(sammelimport, texte)] if k.sorte is UEBUNGSKARTE else []
    uebungen = [uebungen_im_auftrag(sammelimport, k)] if k.sorte is WISSENSKARTE else []
    # Bei `ausschnitt` nennt der Entwurf beider Sorten seine Ausschnitte (#71).
    ausschnitte = (ausschnitte_im_auftrag(sammelimport, k)
                   if sammelimport.art_der_quellgrafik == "ausschnitt" else [])
    teile = [
        f"# Auftrag für Kandidat {k.nummer}",
        "",
        f"- Quellenordner: `quellen/{sammelimport.ordner}/`",
        f"- Kandidat: {k.nummer}",
        f"- Was es ist: {k.was}",
        f"- Typ laut Zerlegungsplan: `{k.ergebnis}`",
        f"- `quelldatei:` `{', '.join(relativ)}`",
        *ablauf,
        *uebungen,
        *quellgrafikzeilen,
        f"- Zielpfad des Entwurfs: `{sammelimport.entwurf(k).as_posix()}`",
        "",
        "## Dateien",
        "",
        *dateien,
        *ausschnitte,
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


def pruefe_seitenbereiche(sammelimport: Sammelimport, dran: list[Kandidat],
                          pdftotext: str | None) -> None:
    """Bricht ab, wenn ein Kandidat des Durchgangs Seiten nennt, die es so nicht gibt (#64).

    Vor dem ersten Auftrag, wie bei anderen Fehlern in der Übersicht, und
    die Meldung nennt die Zeile. Ein Seitenbereich steht nur hinter einem
    PDF, ein Foto ist eine Seite. Ob er über die letzte Seite hinausgeht,
    sagt die Zahl der Seiten aus pdftotext. Ohne pdftotext, oder wenn es
    das PDF nicht lesen kann, bleibt das offen, und der Agent, der die Seiten
    dann selbst liest, merkt es.
    """
    for k in dran:
        for d in k.dateien:
            try:
                bereich = d.seiten
            except ValueError as fehler:
                grund = str(fehler)
            else:
                if bereich is None:
                    continue
                if not _ist_pdf(d.name):
                    grund = "einen Seitenbereich gibt es nur bei einem PDF"
                else:
                    seiten = (pdf_seiten(pdftotext, sammelimport.quellordner / d.name)
                              if pdftotext else None)
                    if seiten is None or bereich.letzte <= len(seiten):
                        continue
                    grund = f"das PDF hat {len(seiten)} Seiten"
            raise sammelimport._abbruch(f"Kandidat {k.nummer} nennt {d}, {grund}.\n"
                                        f"Es ist noch kein Auftrag geschrieben.")


def pruefe_uebungen_aus_dem_beitrag(sammelimport: Sammelimport, dran: list[Kandidat]) -> None:
    """Bricht ab, wenn eine Wissenskarte des Durchgangs unter `Übungen:` keine Übung nennt (#72).

    Vor dem ersten Auftrag, wie beim Seitenbereich, und die Meldung nennt
    die Zeile. Still übergangen, fehlte die Übung später auf der Karte, und
    eine ID, die es nicht gibt, schriebe der Agent laut Auftrag in den
    Entwurf, den `pruefen` dann abweist, Durchgang für Durchgang.
    """
    for k in dran:
        try:
            uebungen_aus_dem_beitrag(sammelimport, k)
        except ValueError as fehler:
            raise sammelimport._abbruch(
                f"Bei Kandidat {k.nummer} steht hinter {UEBUNGEN_MARKE} {fehler}.\n"
                f"Es ist noch kein Auftrag geschrieben.") from None


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
    try:
        offen = [k for k in sammelimport.kandidaten
                 if k.wartet_auf_entwurf and pruefe_entwurf(sammelimport, k).fehler]
    except BibliothekFehlt as fehler:
        raise Abbruch(f"Ein Entwurf nennt einen Ausschnitt.\n{fehler}\n\n"
                      f"Es ist noch kein Auftrag geschrieben.") from None
    dran = offen[:sammelimport.je_durchgang]
    print(f"Aufträge für {len(dran)} von {len(offen)} offenen Kandidaten:")
    if not dran:
        return 0
    # Eingebettet bekommt nur eine Übung ihre Quellgrafik, als Ausschnitt
    # beide Sorten (#71). Ein Durchgang nur mit Wissenskarten schneidet bei
    # `eingebettet` nichts und braucht kein Pillow.
    if sammelimport.art_der_quellgrafik == "eingebettet":
        if any(k.sorte is UEBUNGSKARTE for k in dran):
            verlange_pillow(sammelimport)
    elif sammelimport.art_der_quellgrafik == "ausschnitt":
        verlange_bibliotheken_fuer_ausschnitte(sammelimport, dran)
    pdftotext = None
    if any(_ist_pdf(d.name) for k in dran for d in k.dateien):
        pdftotext = finde_pdftotext()
        if not pdftotext:
            melde_ohne_pdftotext("die Aufträge", "den Kartenentwurf")
    pruefe_seitenbereiche(sammelimport, dran, pdftotext)
    pruefe_uebungen_aus_dem_beitrag(sammelimport, dran)
    eintrag = sammelimport.in_arbeit
    if eintrag is None or not eintrag.ist_von(trainer):
        sammelimport.setze_in_arbeit(trainer)
        sammelimport.speichere()
    sammelimport.entwurfsordner.mkdir(parents=True, exist_ok=True)
    kennungen = kennungstabelle(wurzel)
    for k in dran:
        quellgrafikzeilen, meldungen = lege_quellgrafiken_an(sammelimport, k)
        auftrag = schreibe_auftrag(sammelimport, k, kennungen, pdftotext, quellgrafikzeilen)
        print(f"  {k.nummer}  {SORTENNAME[k.sorte]}  {auftrag.as_posix()}")
        for meldung in meldungen:
            print(f"      {meldung}")
    return 0


# --------------------------------------------------------------------------
# pruefen
# --------------------------------------------------------------------------

def setze_befund(k: Kandidat, befund: Befund) -> None:
    """Der Status eines Kandidaten, wie ihn sein Entwurf auf der Platte ergibt.

    `rückfrage` heißt: Hier muss der Trainer eine Frage beantworten, bevor er
    freigibt. Entweder hat der Entwurf für mindestens eine Rückfrage keine
    Vermutung, oder der Ablauf kommt laut Auftrag aus dem Bild. Dann ist er
    als Ganzes eine Vermutung, und der Trainer prüft ihn mit der Quellgrafik
    vor sich. Eine Rückfrage mit Vermutung bestätigt er sonst in der Tabelle
    wie einen Vorschlag.
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
    Reihenfolge, so wie sie auf die Karte kommen, bei einer Wissenskarte die
    aus ihren Bildverweisen in der Reihenfolge des Texts (#71). Nennt er
    keine, ist die Liste leer. `quellgrafik_fehlt` nennt die PDFs, deren Bild sich nicht
    ausschneiden ließ, relativ zum Quellenordner wie `dateien`. Der Skill sagt
    es bei der Freigabe dazu und nennt am Ende des Durchgangs die Karten, denen
    deshalb eine Quellgrafik fehlt.

    `ausschnitte` nennt jeden Ausschnitt aus `## Freigabe` mit dem Pfad, unter
    dem `pruefen` ihn eben geschnitten hat, dazu Datei, Seite und Rechteck
    (#63). Der Skill zeigt jeden im Chat, und korrigiert der Trainer ihn, ändert
    der Skill die Zahlen im Entwurf.

    Gefragt wird nur nach einem Kandidaten, dessen Entwurf auf der Platte
    liegt, siehe `pruefen`.
    """
    return {
        "kandidat": k.nummer,
        "was": k.was,
        "ergebnis": k.ergebnis,
        "sorte": SORTENNAME[k.sorte],
        "dateien": [d.name for d in k.dateien],
        "status": k.status,
        "notiz": k.notiz,
        "entwurf": sammelimport.entwurf(k).as_posix(),
        "quellgrafiken": [(sammelimport.entwurfsordner / name).as_posix()
                          for name in befund.quellgrafiken],
        "quellgrafik_fehlt": laut_auftrag_ohne_quellgrafik(sammelimport.auftrag(k), k),
        "ausschnitte": [{"name": a.name,
                         "pfad": (sammelimport.entwurfsordner / a.name).as_posix(),
                         "datei": a.datei, "seite": a.seite,
                         "rechteck": dict(zip(("links", "oben", "rechts", "unten"), a.rechteck))}
                        for a in befund.ausschnitte],
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
        if not k.wartet_auf_entwurf:
            continue
        try:
            befund = pruefe_entwurf(sammelimport, k)
        except BibliothekFehlt as fehler:
            # Kein Fehler des Entwurfs. Abgewiesen ginge er auf `offen` und
            # würde neu entworfen, mit demselben Ergebnis.
            raise Abbruch(f"Der Entwurf von Kandidat {k.nummer} nennt einen Ausschnitt.\n"
                          f"{fehler}\n\nDie Übersicht ist nicht geändert.") from None
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
              schaubildnamen: list[str] | None = None,
              bildverweise_neu: dict[str, str] | None = None) -> str:
    """Aus dem Text eines Kartenentwurfs der Text der Karte.

    `id` kommt als erstes Feld dazu, `angelegt` wird der Tag der Freigabe.
    `schaubildnamen`, wenn angegeben, ersetzt die Namen der Quellgrafiken neben
    dem Entwurf durch die in schaubilder/. Einer steht als Name da, mehrere als
    Liste. Bei einer Wissenskarte biegt `bildverweise_neu` stattdessen die
    Bildverweise im Text um, je Quellgrafik neben dem Entwurf auf ihren Weg
    von wissen/ aus (#71). `## Freigabe` fällt weg: Vorschläge und
    Rückfragen sind mit dem Ja des Trainers erledigt und gehören nicht auf
    die Karte in der Halle. Dass das Frontmatter sauber schließt, hat
    `pruefe_entwurf` vorher festgestellt.
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
    if bildverweise_neu:
        rumpf = biege_bildverweise_um("\n".join(rumpf), bildverweise_neu).split("\n")
    return "\n".join(["---", f"id: {uid}", *felder, "---", *rumpf]) + "\n"


def uebernimm(sammelimport: Sammelimport, k: Kandidat, notiz: str) -> str:
    """Schreibt die Karte eines freigegebenen Kandidaten. Gibt ihre ID zurück.

    Die Reihenfolge ist Absicht. Erst die Karte und ihr Schaubild, dann sofort
    die Übersicht, zuletzt aufräumen. Bricht der Lauf dazwischen ab, liegt
    höchstens ein Entwurf zu viel herum. Stünde die Übersicht zuletzt, fände
    der nächste Lauf einen offenen Kandidaten mit gültigem Entwurf und schriebe
    dieselbe Karte ein zweites Mal.

    Die Quellgrafik bekommt den Namen der Karte, wie jedes PlayDrill-Bild in
    schaubilder/, mit ihrer Endung, ein Ausschnitt aus einem Foto also `.jpg`
    (#63). Mehrere bekommen ihn mit Nummer, in der Reihenfolge, in der
    der Entwurf sie nennt (#39). Liegt dort schon eine Datei unter einem
    dieser Namen, wird nichts geschrieben, auch die Karte nicht: Überschrieben
    wird in schaubilder/ nichts.

    Ordner und ID kommen aus der Sorte des Kandidaten (#70). Eine
    Wissenskarte kommt nach wissen/, mit der nächsten freien `wi`-ID aus dem
    eigenen Zähler, so zählen Übungen und Wissenskarten auch in einem Aufruf
    getrennt. Den Ordner legt erst sie an, ein Arbeitsordner von vor der
    Wissenskarte hat keinen. Der Slug kommt aus der Frage, das Fragezeichen
    fällt dabei weg. Die Quellgrafiken einer Wissenskarte sind die aus ihren
    Bildverweisen, nummeriert in der Reihenfolge des Texts, und die Verweise
    zeigen danach von wissen/ aus auf `../schaubilder/<datei>` (#71).
    """
    entwurf = sammelimport.entwurf(k)
    felder, rumpf = lies_frontmatter(entwurf)
    sorte = k.sorte
    # Vor der Schleife in `uebernehmen` gab es schon eine. Scheitert sie hier,
    # ist der Bereich mitten im Durchgang voll geworden.
    try:
        uid = naechste_id(sammelimport.wurzel, sorte)
    except KeineId as fehler:
        raise NichtUebernommen(str(fehler)) from None
    name = f"{uid}-{slug(str(felder['titel']))}"
    ziel = sammelimport.wurzel / sorte.ordner / f"{name}.md"
    # Welche Quellgrafiken, hat `pruefe_entwurf` sichergestellt: nur die
    # eigenen, jede einmal, und jede liegt da.
    quellgrafiken = [sammelimport.entwurfsordner / bild
                     for bild in quellgrafiken_im_entwurf(k, felder, rumpf)]
    nummern = ([f"-{nr}" for nr in range(1, len(quellgrafiken) + 1)]
               if len(quellgrafiken) > 1 else [""])
    verschoben = {quellgrafik: (sammelimport.wurzel / "schaubilder"
                                / f"{name}{nummer}{quellgrafik.suffix}")
                  for quellgrafik, nummer in zip(quellgrafiken, nummern)}
    belegt = [bild.name for bild in verschoben.values() if bild.exists()]
    if belegt:
        raise NichtUebernommen(f"schaubilder/{', schaubilder/'.join(belegt)} gibt es schon")
    if sorte is WISSENSKARTE:
        schaubildnamen = None
        bildverweise_neu = {alt.name: f"../schaubilder/{neu.name}"
                            for alt, neu in verschoben.items()}
    else:
        schaubildnamen = [bild.name for bild in verschoben.values()]
        bildverweise_neu = None
    text = als_karte(entwurf.read_text(encoding="utf-8"), uid, date.today().isoformat(),
                     schaubildnamen, bildverweise_neu)
    if sorte is WISSENSKARTE:
        # Zu den Übungen aus dem Entwurf die aus demselben Beitrag, die schon
        # Karte sind (#72). Die übrigen bringen ihre ID mit, wenn sie Karte
        # werden. Dass sich `Übungen:` lesen lässt, hat
        # `pruefe_fuer_uebernahme` vorher festgestellt.
        text = mit_uebungen(text, sorted({*map(str, als_liste(felder.get("uebungen"))),
                                          *ids_der_uebungen(sammelimport, k)}))
    # "x" legt nur neu an. Eine Datei unter dieser ID gibt es laut
    # naechste_id() nicht, und falls doch, wird sie nicht überschrieben.
    ziel.parent.mkdir(exist_ok=True)
    with ziel.open("x", encoding="utf-8") as datei:
        datei.write(text)
    for quellgrafik, schaubild in verschoben.items():
        schaubild.parent.mkdir(exist_ok=True)
        shutil.move(quellgrafik, schaubild)
    # `bekannt` sind die IDs in uebungen/, eine Wissenskarte gehört nicht dazu.
    if sorte is UEBUNGSKARTE:
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
    eingetragen hat. Sie ließen sich jederzeit neu aus dem PDF schneiden, ein
    Ausschnitt aus Foto oder PDF-Seite ebenso.
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
    try:
        grund = pruefe_entwurf(sammelimport, k).fehler
    except BibliothekFehlt as fehler:
        # Für den Ausschnitt fehlt eine Bibliothek. Die übrigen Kandidaten
        # gehen trotzdem durch, die Meldung steht in einer Zeile.
        return " ".join(str(fehler).split())
    if grund:
        return grund
    # Die Übungen aus demselben Beitrag kommen beim Übernehmen auf die
    # Wissenskarte (#72). `vorbereiten` hat sie vor dem Auftrag geprüft,
    # aber die Zeile kann seitdem von Hand geändert sein.
    try:
        uebungen_aus_dem_beitrag(sammelimport, k)
    except ValueError as fehler:
        return f"hinter {UEBUNGEN_MARKE} steht {fehler}"
    return None


def uebernehmen(wurzel: Path, ordner: str, freigegeben: list[tuple[str, str]],
                uebersprungen: list[tuple[str, str]], ergaenzt: list[tuple[str, str]],
                zurueckgestellt: list[tuple[str, str]] = ()) -> int:
    """Erledigt die Kandidaten, über die der Trainer bei der Freigabe entschieden hat.

    Freigegebene werden Karte. Gestrichene werden `übersprungen`, der Grund
    steht in der Notiz. Zurückgestellte werden `zurückgestellt`, auch mit
    Grund, und kommen wieder, wenn der Trainer sie holt (#69). Ein
    bestätigtes Duplikat hat der Skill schon in die bestehende Karte
    eingearbeitet, der Kandidat wird `ergänzt` und zeigt auf sie. Aus den
    drei letzten entsteht keine Karte.

    Vor allem anderen muss der Quellenordner da sein (#40). Gleicht die
    Nextcloud eines Rechners quellen/ nicht ab, liegen dort die Entwürfe,
    aber weder Übersicht noch Quellen.
    """
    if not (wurzel / "quellen" / ordner).is_dir():
        raise Abbruch(f"Den Ordner quellen/{ordner}/ gibt es an diesem Rechner nicht. "
                      f"Gleicht die Nextcloud quellen/ hier ab?\nNichts übernommen.")
    sammelimport = Sammelimport(wurzel, ordner)
    sammelimport.verlange_freigabe()
    if not (freigegeben or uebersprungen or ergaenzt or zurueckgestellt):
        raise Abbruch("Kein Kandidat genannt. Je Kandidat: --kandidat <nr> \"<notiz>\", "
                      "--uebersprungen <nr> \"<grund>\", --zurueckgestellt <nr> \"<grund>\" "
                      "oder --ergaenzt <nr> <id>")
    nach_nummer = {k.nummer: k for k in sammelimport.kandidaten}
    # Gibt es an diesem Rechner keine ID, dann für keinen Kandidaten. Das
    # steht einmal da, bevor irgendetwas geschrieben ist, statt je Kandidat.
    # Gestrichene und ergänzende Kandidaten brauchen keine ID. Gefragt wird
    # je Sorte, die freigegeben ist: Eine vierstellige ID in uebungen/ hält
    # keine Wissenskarte auf. Nennt der Aufruf nur Nummern ohne Zeile, wird
    # gefragt wie vor der Wissenskarte, nach einer Übung.
    if freigegeben:
        genannt = [nach_nummer.get(nummer) for nummer, _ in freigegeben]
        sorten = [s for s in SORTEN if any(k is not None and k.sorte is s for k in genannt)]
        for sorte in sorten or [UEBUNGSKARTE]:
            try:
                naechste_id(wurzel, sorte)
            except KeineId as fehler:
                raise Abbruch(f"{fehler}\nNichts übernommen.") from None

    abgewiesen = 0
    for nummer, notiz in freigegeben:
        k = nach_nummer.get(nummer)
        grund = pruefe_fuer_uebernahme(sammelimport, k)
        if not grund and k is not None:
            try:
                uid = uebernimm(sammelimport, k, notiz)
            except NichtUebernommen as fehler:
                grund = str(fehler)
            else:
                print(f"  {nummer}  importiert als {uid}")
                for meldung in trage_bei_wissenskarten_ein(sammelimport, k, uid):
                    print(f"      {meldung}")
                continue
        print(f"  {nummer}  nicht übernommen: {grund}")
        abgewiesen += 1

    # Je Kandidat ohne Karte: Status, Notiz, Karte, und was dagegen spricht.
    # `bekannt` kennt auch die Karten, die dieser Aufruf eben geschrieben
    # hat. Auch eine davon kann die ergänzte sein.
    ohne_karte = [
        (nummer, status, grund.strip(), None, "" if grund.strip() else "ohne Grund")
        for status, mit_grund in (("übersprungen", uebersprungen),
                                  ("zurückgestellt", zurueckgestellt))
        for nummer, grund in mit_grund
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
        # Auch eine Übung, die eine Karte ergänzt, gehört auf die
        # Wissenskarte ihres Beitrags, mit der ID der ergänzten (#72).
        for meldung in trage_bei_wissenskarten_ein(sammelimport, k, karte) if karte else []:
            print(f"      {meldung}")

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
    vor.add_argument("--zurueckgestellte", action="store_true",
                     help="mit --plan: dazu die Dateien der zurückgestellten Zeilen, die der "
                          "Trainer jetzt holt")
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
    ue.add_argument("--zurueckgestellt", nargs=2, action="append", default=[],
                    metavar=("NR", "GRUND"),
                    help="ein Kandidat, den der Trainer später holen will, und warum")
    ue.add_argument("--ergaenzt", nargs=2, action="append", default=[],
                    metavar=("NR", "ID"),
                    help="ein Kandidat, der als Duplikat eine bestehende Karte ergänzt hat")
    a = ap.parse_args()
    if a.befehl == "vorbereiten" and a.plan and a.trotzdem:
        ap.error("--trotzdem gilt nur ohne --plan, die Planeingabe trägt nicht ein, wer arbeitet")
    if a.befehl == "vorbereiten" and a.zurueckgestellte and not a.plan:
        ap.error("--zurueckgestellte gilt nur mit --plan, geholt wird in den Zerlegungsplan")

    wurzel = a.wurzel.resolve() if a.wurzel else finde_wurzel()
    try:
        if a.befehl == "pruefen":
            return pruefen(wurzel, a.ordner, als_json=a.json)
        if a.befehl == "uebernehmen":
            return uebernehmen(wurzel, a.ordner, [tuple(p) for p in a.kandidat],
                               [tuple(p) for p in a.uebersprungen],
                               [tuple(p) for p in a.ergaenzt],
                               [tuple(p) for p in a.zurueckgestellt])
        if a.plan:
            return lege_planeingabe_an(wurzel, a.ordner, zurueckgestellte=a.zurueckgestellte)
        return vorbereiten(wurzel, a.ordner, trotzdem=a.trotzdem)
    except Abbruch as fehler:
        print(fehler)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
