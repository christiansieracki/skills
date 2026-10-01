"""Baut einen kuenstlichen Arbeitsordner im Temp-Verzeichnis.

Die Tests pruefen Linter und Suche so, wie die Skills sie aufrufen: ueber die
Kommandozeile, in aller Regel mit `--wurzel` auf diesen Ordner. Die Skripte
nehmen den Wurzelpfad schon als Argument entgegen, der Fixture ist also ohne
eine Zeile Produktionscode injizierbar. Die echte Bibliothek wird dabei nie
angefasst.

Der Ordner ist absichtlich klein: Wurzeldatei, eine Schwerpunktliste und eine
Handvoll Karten, die genau die geprueften Faelle abdecken. Wer einen weiteren
Fall braucht, legt eine Karte dazu, statt eine bestehende umzubiegen. Sonst
zieht eine Aenderung Tests mit, die von ihr nichts wissen wollen.

Die IDs gehoeren dem Fixture. Wer hier ue-000005 liest, liest nicht die Karte
ue-000005 aus der echten Bibliothek.
"""

from __future__ import annotations

import os
import re
import shutil
import socket
import subprocess
import sys
import tempfile
import textwrap
import zlib
from dataclasses import dataclass
from pathlib import Path

SKRIPTE = Path(__file__).resolve().parent.parent / "scripts"

WURZELDATEI = "trainingsplanung-root.yml"

# EXIF-Tag 0x0112, dieselbe Zahl, die bilder_aufbereiten.py ORIENTIERUNG nennt.
# Sie steht hier noch einmal, weil die Tests die Skripte ueber die
# Kommandozeile aufrufen und nicht importieren. Zweimal ausgeschrieben waere
# sie zweimal zu raten.
ORIENTIERUNG = 274

ROOT_YML = """\
# Wurzeldatei eines kuenstlichen Arbeitsordners fuer die Tests.
#
# finde_wurzel() erkennt den Ordner an ihrem Namen, und die naechste ID liest
# hier, welcher Trainer an diesem Rechner sitzt. Mehr lesen die Skripte nicht
# aus ihr, deshalb steht hier nur das Noetigste. Was ein echter Arbeitsordner
# mitbringt, legt init_struktur.py an.

version: 1
verein: "Testverein"
saison: "2025/26"
"""

# Der Trainer des Fixtures. Er sitzt an dem Rechner, auf dem der Test laeuft,
# und hat die Nummer 00, wie alle Karten in STANDARDKARTEN.
TRAINER = {"test": {"nummer": "00", "rechner": [socket.gethostname()]}}

SCHWERPUNKTE_MD = """\
# Schwerpunkte

Kurzfassung fuer die Tests. Die Kennungen stammen aus der Startfassung des
Plugins, damit hier keine Sprache erfunden wird, die es im Verein nicht gibt.

Eine Ausnahme ist `nur-beach`. Eine rein beachspezifische Kennung gibt es in
der echten Liste noch nicht, weil die erst aus echtem Importmaterial entsteht
und nach Freigabe eingetragen wird. Fuer die Mismatch-Pruefung braucht es sie,
und der Name sagt, dass sie dem Fixture gehoert, genau wie die IDs.

Die Steuerungsschwerpunkte tragen keine Disziplinspalte, so wie in der echten
Datei. Der Parser darf sie deshalb nicht verlieren.

## Inhaltliche Schwerpunkte

| Kennung | Klartext | Disziplin |
|---|---|---|
| `ballkontrolle` | Sauberer Kontakt in Bagger und Pritschen, ohne Spielsituation | beide |
| `annahme` | Annahme als Technikelement | beide |
| `sideout-sicherheit` | Den eigenen Aufschlagball sicher zurueckgewinnen | beide |
| `laufwege-rotation` | Positionen, Rotation, Wechsel zwischen 5-1, 6-2 und situativ | halle |
| `nur-beach` | Nur im Sand, es gibt sie allein fuer diesen Fixture | beach |

## Steuerungsschwerpunkte

| Kennung | Klartext |
|---|---|
| `standortbestimmung` | Technik-Checks und Tests, um den Ausgangspunkt zu kennen |
"""

RUMPF = """\

# {titel}

## Ziel

Karte aus dem kuenstlichen Arbeitsordner. Steht hier, damit die Tests etwas zu
lesen haben.

## Ablauf

Siehe Frontmatter.

## Variationen

-
"""

# Pflichtfelder in der Reihenfolge aus DATENMODELL.md. Eine Karte im
# Arbeitsordner gibt nur an, was fuer ihren Fall wichtig ist, der Rest kommt
# von hier.
KARTE = {
    "id": "ue-000000",
    "titel": "Ohne Titel",
    "typ": "uebung",
    "disziplin": ["halle"],
    "element": ["ballkontrolle"],
    "spielphase": "keine",
    "form": "technik",
    "schwerpunkt": ["ballkontrolle"],
    "level_min": "einsteiger",
    "level_max": "ambitioniert",
    "spieler_min": 2,
    "spieler_max": None,
    "dauer_min": 10,
    "dauer_max": 15,
    "spielflaechen": 1,
    "netz": False,
    "erwachsenenbelastung": False,
    "belastungshinweis": "",
    "material": ["baelle"],
    "schaubild": None,
    "quelle": "Testbestand",
    "quelldatei": None,
    "variante_von": None,
    "autor": "test",
    "angelegt": "2026-01-01",
}

STANDARDKARTEN = [
    # Braucht wenige Spieler und eine Spielflaeche.
    {
        "id": "ue-000001",
        "titel": "Annahme im Halbfeld",
        "element": ["annahme"],
        "spielphase": "sideout",
        "form": "komplex",
        "schwerpunkt": ["annahme"],
        "spieler_min": 4,
        "spieler_max": 8,
        "dauer_min": 15,
        "dauer_max": 20,
        "netz": True,
    },
    # Die Karte mit der niedrigsten Obergrenze. Bei mehr Anwesenden wird daraus
    # eine zweite Gruppe, kein Ausschluss.
    {
        "id": "ue-000002",
        "titel": "Zonenbaggern im Paar",
        "spieler_min": 2,
        "spieler_max": 4,
        "dauer_min": 8,
        "dauer_max": 8,
    },
    # Die einzige Karte, die zwei Spielflaechen braucht.
    {
        "id": "ue-000003",
        "titel": "Sideout-Serie über zwei Spielflächen",
        "element": ["annahme", "angriff"],
        "spielphase": "sideout",
        "form": "spielform",
        "schwerpunkt": ["sideout-sicherheit"],
        "spieler_min": 12,
        "spieler_max": 16,
        "dauer_min": 20,
        "dauer_max": 25,
        "spielflaechen": 2,
        "netz": True,
    },
    # Die einzige reine Beachkarte. Sie darf in der Hallensuche nicht
    # auftauchen und in der ungefilterten Suche sehr wohl.
    {
        "id": "ue-000004",
        "titel": "Annahme zu zweit im Sand",
        "disziplin": ["beach"],
        "element": ["annahme"],
        "spielphase": "sideout",
        "schwerpunkt": ["annahme"],
        "spieler_min": 2,
        "spieler_max": 4,
        "dauer_min": 10,
        "dauer_max": 15,
        "netz": True,
    },
    # Laeuft drinnen wie draussen. Sie steht in beiden Disziplinfiltern, das
    # ist der Fall, den eine Karte mit Einzelwert nicht abbilden koennte.
    {
        "id": "ue-000005",
        "titel": "Zwei gegen Zwei auf dem Kleinfeld",
        "disziplin": ["halle", "beach"],
        "element": ["annahme", "angriff"],
        "spielphase": "sideout",
        "form": "spielform",
        "schwerpunkt": ["sideout-sicherheit"],
        "spieler_min": 4,
        "spieler_max": 8,
        "dauer_min": 15,
        "dauer_max": 20,
        "netz": True,
    },
]

# Platzhalter fuer ein Feld, das auf dieser Karte gar nicht stehen soll.
# `disziplin=None` waere etwas anderes: dann stuende `disziplin: null` auf der
# Karte. Fuer den Fall "Feld fehlt" braucht es deshalb einen eigenen Wert.
OHNE = object()

UMLAUTE = str.maketrans({"ä": "ae", "ö": "oe", "ü": "ue", "ß": "ss"})


def auffaelligkeiten(ausgabe: str) -> list[str]:
    """Zieht die gemeldeten Zeilen aus der Ausgabe von index.py.

    Jede Auffaelligkeit steht in einer eigenen Zeile mit fuehrendem "  - ".
    Mehr Struktur hat die Ausgabe des Linters heute nicht. Die Funktion steht
    hier, weil nicht nur der Test des Linters nach ihm fragt: auch nach einem
    Sammelimport soll er nichts melden.
    """
    return [zeile[4:] for zeile in ausgabe.splitlines() if zeile.startswith("  - ")]


def _slug(titel: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", titel.lower().translate(UMLAUTE)).strip("-")


def _yaml(wert) -> str:
    """Schreibt einen Wert so, wie lies_frontmatter() ihn wieder einliest.

    Die Umkehrung des Parsers steht hier nach, weil es im Plugin keinen
    Schreiber gibt. Dass beide Seiten zusammenpassen, haelt der Test fest, der
    die Felder eines Treffers einzeln nachmisst. Driftet der Parser weg, faellt
    dieser Test.
    """
    if wert is None:
        return "null"
    if isinstance(wert, bool):
        return "true" if wert else "false"
    if isinstance(wert, int):
        return str(wert)
    if isinstance(wert, list):
        return "[" + ", ".join(_yaml(x) for x in wert) + "]"
    text = str(wert)
    # Kennungen stehen unquotiert auf den echten Karten, alles andere in
    # Anfuehrungszeichen. Ein '#' im Text gilt sonst als Kommentar.
    return text if re.fullmatch(r"[a-z0-9._/-]+", text) else f'"{text}"'


def _als_karte(felder: dict) -> str:
    frontmatter = "\n".join(f"{k}: {_yaml(v)}" for k, v in felder.items())
    return f"---\n{frontmatter}\n---\n" + RUMPF.format(titel=felder["titel"])


def _als_wurzeldatei(trainer: dict | None) -> str:
    """Die Wurzeldatei, mit dem Abschnitt `trainer:` in der Form aus DATENMODELL.md.

    `None` laesst den Abschnitt weg, so wie in jedem Arbeitsordner vor 3.0.0.
    """
    if trainer is None:
        return ROOT_YML
    zeilen = ["", "trainer:"]
    for name, eintrag in trainer.items():
        zeilen += [f"  {name}:",
                   f'    nummer: "{eintrag["nummer"]}"',
                   f"    rechner: [{', '.join(eintrag['rechner'])}]"]
    return ROOT_YML + "\n".join(zeilen) + "\n"


def _vierstellig(uid: str) -> str:
    """Eine ID des Fixtures so, wie sie vor 3.0.0 hiess: `ue-000042` wird `ue-0042`."""
    return uid[:len("ue-")] + uid[len("ue-00"):]


# Die Spalten der Uebersicht in sammelimport.md, in der Reihenfolge aus #29.
UEBERSICHT_SPALTEN = ["Kandidat", "Dateien", "Was es ist", "Ergebnis", "Status", "Karte", "Notiz"]

ABSPRACHEN = """\
Absprache aus dem kuenstlichen Arbeitsordner: `quelle` nennt das Heft und die
Seite. Steht hier, damit der Test sie im Auftrag wiederfindet.
"""


def _als_sammelimport(kandidaten: list[dict], freigegeben: str | None,
                      je_durchgang: int, absprachen: str, einstellungen: dict) -> str:
    zeilen = ["| " + " | ".join(UEBERSICHT_SPALTEN) + " |",
              "|" + "---|" * len(UEBERSICHT_SPALTEN)]
    for k in kandidaten:
        dateien = ", ".join(f"`{d}`" for d in k["dateien"])
        zellen = [str(k["kandidat"]), dateien, k.get("was", "Übung aus dem Test"),
                  k.get("ergebnis", "uebung"), k.get("status", "offen"),
                  k.get("karte", ""), k.get("notiz", "")]
        zeilen.append("| " + " | ".join(zellen) + " |")
    return (
        "---\n"
        f"kandidaten_je_durchgang: {je_durchgang}\n"
        f"plan_freigegeben: {_yaml(freigegeben)}\n"
        + "".join(f"{name}: {_yaml(wert)}\n" for name, wert in einstellungen.items())
        + "---\n\n"
        "# Sammelimport\n\n"
        "## Absprachen\n\n"
        f"{absprachen}\n"
        "## Übersicht\n\n"
        + "\n".join(zeilen) + "\n"
    )


def _als_freigabe(vorschlaege: list[str], rueckfragen: list[str]) -> str:
    """Der Abschnitt `## Freigabe` am Ende eines Kartenentwurfs, Form aus #29.

    Eine leere Liste heisst dort "keine", beide Listen stehen immer da.
    """
    teile = ["## Freigabe", ""]
    if vorschlaege:
        teile += ["Vorschläge:", *(f"- {v}" for v in vorschlaege)]
    else:
        teile += ["Vorschläge: keine"]
    teile.append("")
    if rueckfragen:
        teile += ["Rückfragen:", *(f"{i}. {r}" for i, r in enumerate(rueckfragen, 1))]
    else:
        teile += ["Rückfragen: keine"]
    return "\n".join(teile) + "\n"


def _pdf_zeichenkette(text: str) -> bytes:
    """Ein Text als PDF-Zeichenkette in runden Klammern, kodiert wie die Schrift."""
    roh = text.encode("cp1252")
    return b"(" + roh.replace(b"\\", b"\\\\").replace(b"(", b"\\(").replace(b")", b"\\)") + b")"


def _pdf_strom(daten: bytes, eintraege: str = "") -> bytes:
    """Ein Strom-Objekt. `eintraege` kommen zu `/Length` ins Woerterbuch, fuer ein Bild etwa
    `/Type /XObject /Subtype /Image` mit Breite, Hoehe und Maske."""
    return (f"<< /Length {len(daten)} {eintraege}>>\nstream\n".encode()
            + daten + b"\nendstream")


def _pdf_datei(objekte: list[bytes]) -> bytes:
    """Setzt eine PDF-Datei aus ihren Objekten zusammen. Objekt 1 ist der Katalog.

    Dazu gehoert die Querverweistabelle mit der Lage jedes Objekts in Bytes.
    Ein Leser, der sie nicht findet, repariert die Datei still, und ein Test,
    der erst an der reparierten Datei gruen wird, prueft zu wenig.
    """
    datei = bytearray(b"%PDF-1.4\n%\xe2\xe3\xcf\xd3\n")
    lagen = []
    for nummer, objekt in enumerate(objekte, 1):
        lagen.append(len(datei))
        datei += f"{nummer} 0 obj\n".encode() + objekt + b"\nendobj\n"
    tabelle = len(datei)
    datei += f"xref\n0 {len(objekte) + 1}\n0000000000 65535 f \n".encode()
    datei += b"".join(f"{lage:010d} 00000 n \n".encode() for lage in lagen)
    datei += (f"trailer\n<< /Size {len(objekte) + 1} /Root 1 0 R >>\n"
              f"startxref\n{tabelle}\n%%EOF\n").encode()
    return bytes(datei)


@dataclass
class PdfBild:
    """Ein Bild fuer ein Test-PDF, mit Transparenzmaske, so wie PlayDrill sein Feldbild einbettet.

    Deckend ist nur das Rechteck `deckend`: links, oben, rechts, unten in
    Pixeln, rechts und unten ausschliesslich. Darum herum ist das Bild
    durchsichtig. Was beim Ausschneiden uebrig bleiben muss, steht damit im
    Test und nicht in einer zweiten Rechnung.

    `kaputt` schreibt statt der Pixel Bytes, die sich nicht entpacken lassen.
    """

    breite: int
    hoehe: int
    deckend: tuple[int, int, int, int]
    kaputt: bool = False

    def objekte(self, nummer: int, farbprofil: int) -> list[bytes]:
        """Das Bild als Objekt `nummer` und seine Maske gleich dahinter.

        Der Farbraum ist ein Verweis auf ein ICC-Profil, wie in jedem
        PlayDrill-PDF, und nicht das einfachere /DeviceRGB.
        """
        links, oben, rechts, unten = self.deckend
        maske = bytearray(self.breite * self.hoehe)
        for zeile in range(oben, unten):
            anfang = zeile * self.breite
            maske[anfang + links:anfang + rechts] = b"\xff" * (rechts - links)
        pixel = b"kein Bild" if self.kaputt else zlib.compress(
            bytes([30, 120, 200]) * (self.breite * self.hoehe))
        groesse = f"/Type /XObject /Subtype /Image /Width {self.breite} /Height {self.hoehe} "
        return [
            _pdf_strom(pixel, f"{groesse}/ColorSpace [/ICCBased {farbprofil} 0 R] "
                              f"/BitsPerComponent 8 /Filter /FlateDecode /SMask {nummer + 1} 0 R "),
            _pdf_strom(zlib.compress(bytes(maske)),
                       f"{groesse}/ColorSpace /DeviceGray /BitsPerComponent 8 /Filter /FlateDecode "),
        ]


def _pdf_mit_text(seiten: list[list[str]], bilder: list[PdfBild]) -> bytes:
    """Ein PDF mit Textebene, je Seite eine Liste von Zeilen, die Bilder auf der ersten.

    Die Schrift ist Helvetica, eine der vierzehn, die jeder PDF-Leser ohne
    Einbettung kennt. Mit WinAnsiEncoding kommen Umlaute durch, und nur dann
    zeigt der Test, dass pdftotext sie als UTF-8 herausgibt.

    Die Objekte stehen in fester Folge: 1 Katalog, 2 Seitenbaum, 3 Schrift.
    Mit Bildern folgt das Farbprofil, das sie sich teilen, dann je Bild das
    Bild und seine Maske. Zuletzt je Seite ihr Inhalt und die Seite selbst.
    """
    objekte = [b"", b"",
               b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica "
               b"/Encoding /WinAnsiEncoding >>"]
    xobjekte, zeichnen = [], b""
    if bilder:
        objekte.append(_pdf_strom(b"kein echtes Farbprofil", "/N 3 "))
        farbprofil = len(objekte)
    for i, bild in enumerate(bilder, 1):
        nummer = len(objekte) + 1
        objekte += bild.objekte(nummer, farbprofil)
        xobjekte.append(f"/Im{i} {nummer} 0 R")
        zeichnen += f"q {bild.breite} 0 0 {bild.hoehe} 50 {100 * i} cm /Im{i} Do Q\n".encode()
    kinder = []
    for seite, zeilen in enumerate(seiten or [[]]):
        inhalt = (b"BT /F1 10 Tf 12 TL 50 800 Td\n"
                  + b"".join(_pdf_zeichenkette(z) + b" Tj T*\n" for z in zeilen)
                  + b"ET")
        ressourcen = "/Font << /F1 3 0 R >>"
        if seite == 0 and xobjekte:
            inhalt = zeichnen + inhalt
            ressourcen += f" /XObject << {' '.join(xobjekte)} >>"
        objekte.append(_pdf_strom(inhalt))
        objekte.append(f"<< /Type /Page /Parent 2 0 R /Resources << {ressourcen} >> "
                       f"/Contents {len(objekte)} 0 R >>".encode())
        kinder.append(f"{len(objekte)} 0 R")
    objekte[0] = b"<< /Type /Catalog /Pages 2 0 R >>"
    objekte[1] = (f"<< /Type /Pages /Kids [{' '.join(kinder)}] /Count {len(kinder)} "
                  f"/MediaBox [0 0 595 842] >>").encode()
    return _pdf_datei(objekte)


class Arbeitsordner:
    """Ein kuenstlicher Arbeitsordner, der sich wieder wegraeumen laesst.

    `vor_der_umstellung=True` baut ihn so, wie er unter 2.5.1 aussah: die
    Standardkarten mit vierstelliger ID und ohne `trainer:` in der
    Wurzeldatei. Das ist der Ordner, den `ids_umstellen.py` vorfindet.
    """

    def __init__(self, vor_der_umstellung: bool = False) -> None:
        self.pfad = Path(tempfile.mkdtemp(prefix="trainingsplanung-test-"))
        self.ids: list[str] = []
        self.entwurfsordner: Path | None = None
        self.setze_trainer(None if vor_der_umstellung else TRAINER)
        (self.pfad / "schwerpunkte.md").write_text(SCHWERPUNKTE_MD, encoding="utf-8")
        (self.pfad / "uebungen").mkdir()
        for felder in STANDARDKARTEN:
            if vor_der_umstellung:
                felder = {**felder, "id": _vierstellig(felder["id"])}
            self.lege_karte_an(**felder)

    def setze_trainer(self, trainer: dict | None) -> None:
        """Schreibt die Wurzeldatei neu, mit diesen Trainern unter `trainer:`.

        Je Trainer `nummer` und `rechner`, wie in TRAINER. `None` laesst den
        Abschnitt ganz weg.
        """
        (self.pfad / WURZELDATEI).write_text(_als_wurzeldatei(trainer), encoding="utf-8")

    def lege_trainingsplan_an(self, name: str, *ids: str) -> Path:
        """Legt unter `trainings/` einen Trainingsplan an, der diese IDs nennt.

        `name` ist der Pfad unter `trainings/`, etwa `gruppe/2026-09-15.md`.
        Jede ID steht in einer eigenen Zeile der Ablauftabelle, in der Spalte
        ID, so wie die Vorlage es vorsieht.
        """
        zeilen = ["| Zeit | Teil | Übung | ID | Anpassung | Warum hier |",
                  "|---|---|---|---|---|---|"]
        zeilen += [f"| 18:00 | Hauptteil | Übung aus dem Test | {uid} | | |" for uid in ids]
        datei = self.pfad / "trainings" / name
        datei.parent.mkdir(parents=True, exist_ok=True)
        datei.write_text(
            f"---\ndatum: {Path(name).stem}\ngruppe: gruppe\nstatus: geplant\n---\n\n"
            "# Training\n\n## Ablauf\n\n" + "\n".join(zeilen) + "\n",
            encoding="utf-8",
        )
        return datei

    def ergaenze_schwerpunkt(self, kennung: str, disziplin: str) -> None:
        """Haengt eine Zeile an die Tabelle der inhaltlichen Schwerpunkte.

        Fuer Zeilen, die der Fixture nicht dauerhaft tragen soll, etwa eine mit
        einem vertippten Disziplinwert. `disziplin` geht so in die Zelle, wie
        es hier steht, auch leer.
        """
        datei = self.pfad / "schwerpunkte.md"
        zeile = f"| `{kennung}` | Zeile aus einem Test | {disziplin} |"
        datei.write_text(
            datei.read_text(encoding="utf-8").replace(
                "\n\n## Steuerungsschwerpunkte", f"\n{zeile}\n\n## Steuerungsschwerpunkte"
            ),
            encoding="utf-8",
        )

    def lege_schaubild_an(self, name: str) -> Path:
        """Legt eine Datei unter schaubilder/ ab.

        Was drinsteht, zaehlt nicht: der Linter schaut nur nach, ob es die
        Datei gibt. Den Ordner legt erst dieser Aufruf an, damit ein
        Arbeitsordner ohne Schaubilder auch keinen hat.
        """
        ordner = self.pfad / "schaubilder"
        ordner.mkdir(exist_ok=True)
        datei = ordner / name
        datei.write_text('<svg xmlns="http://www.w3.org/2000/svg"></svg>', encoding="utf-8")
        return datei

    def lege_szene_an(self, name: str, text: str) -> Path:
        """Legt eine Szenendatei unter schaubilder/ ab.

        Der Name ist der Basisname ohne Endung, so wie ihn auch das Skript
        entgegennimmt. Den Ordner legt erst dieser Aufruf an, damit ein
        Arbeitsordner ohne Schaubilder auch keinen hat.
        """
        ordner = self.pfad / "schaubilder"
        ordner.mkdir(exist_ok=True)
        datei = ordner / f"{name}.szene.yml"
        datei.write_text(textwrap.dedent(text).strip() + "\n", encoding="utf-8")
        return datei

    def lege_entwurfsordner_an(self) -> Path:
        """Ein Ordner neben dem Arbeitsordner, ohne Wurzeldatei ueber sich.

        Das Gegenstueck zum Arbeitsordner: hier laesst sich pruefen, was ein
        Skript tut, wenn es von einem fremden Fleck aus gerufen wird. Er
        entsteht beim ersten Aufruf und wird mit weggeraeumt.
        """
        if self.entwurfsordner is None:
            self.entwurfsordner = Path(tempfile.mkdtemp(prefix="trainingsplanung-entwurf-"))
        return self.entwurfsordner

    def lege_entwurf_an(self, name: str, text: str) -> Path:
        """Legt eine Szenendatei ausserhalb des Arbeitsordners ab.

        Dafuer, dass eine Szene auch neben dem Arbeitsordner rendert: der
        Skill volleyball-schaubild zeichnet Runde um Runde im
        Temp-Verzeichnis, und nach schaubilder/ kommt erst, was der Trainer
        freigegeben hat.
        """
        datei = self.lege_entwurfsordner_an() / f"{name}.szene.yml"
        datei.write_text(textwrap.dedent(text).strip() + "\n", encoding="utf-8")
        return datei

    def lege_karte_an(self, **felder) -> None:
        """Legt eine Uebungskarte an.

        Nicht genannte Felder kommen aus KARTE. Ein Feld auf `OHNE` gesetzt
        fehlt auf der Karte ganz.
        """
        karte = {k: v for k, v in {**KARTE, **felder}.items() if v is not OHNE}
        datei = self.pfad / "uebungen" / f"{karte['id']}-{_slug(karte['titel'])}.md"
        datei.write_text(_als_karte(karte), encoding="utf-8")
        self.ids.append(karte["id"])

    def lege_quelldatei_an(self, name: str, inhalt: bytes) -> Path:
        """Legt eine Datei in `quellen/` ab, Byte fuer Byte wie angegeben.

        Fuer die Faelle, in denen es auf den Inhalt gar nicht ankommt: eine
        Datei, die nur schwer genug sein muss, damit die Bildaufbereitung sie
        in die Liste nimmt. Ein echtes Bild dafuer zu erzeugen braeuchte
        Pillow, und der Test, der ohne Pillow laeuft, bekaeme es nicht.
        """
        datei = self.pfad / "quellen" / name
        datei.parent.mkdir(parents=True, exist_ok=True)
        datei.write_bytes(inhalt)
        return datei

    def lege_quell_pdf_an(self, name: str, *seiten: list[str],
                          bilder: list[PdfBild] | None = None) -> Path:
        """Legt ein PDF mit Textebene in `quellen/` ab, je Seite eine Liste von Zeilen.

        Gebaut wird es zur Laufzeit mit der Standardbibliothek, so wie
        `lege_quellbild_an` sein Foto baut. Kein Binaermaterial im Repo, und
        was im PDF steht, steht hier im Test. `bilder` kommen auf die erste
        Seite, in der genannten Reihenfolge.
        """
        return self.lege_quelldatei_an(name, _pdf_mit_text(list(seiten), bilder or []))

    def lege_quellenordner_an(self, ordner: str, kandidaten: list[dict],
                              freigegeben: str | None = "2026-09-30",
                              je_durchgang: int = 30,
                              absprachen: str = ABSPRACHEN,
                              **einstellungen) -> Path:
        """Legt einen Quellenordner mit `sammelimport.md` und Quelldateien an.

        `kandidaten` sind die Zeilen der Uebersicht. Jede nennt `kandidat` und
        `dateien`, relativ zum Quellenordner. Die uebrigen Spalten haben einen
        Standard: eine offene Uebung ohne Karte und Notiz. Jede genannte Datei
        entsteht leer unter `quellen/<ordner>/`. Wer ihren Inhalt braucht,
        etwa den Text eines PDF, legt sie danach mit `lege_quell_pdf_an`
        neu an.

        `freigegeben=None` ist der Plan, den der Trainer noch nicht
        freigegeben hat. Weitere Einstellungen, etwa `textmarke`, kommen
        als Schluesselwort und stehen dann so im Frontmatter.
        """
        for k in kandidaten:
            for datei in k["dateien"]:
                self.lege_quelldatei_an(f"{ordner}/{datei}", b"")
        datei = self.pfad / "quellen" / ordner / "sammelimport.md"
        datei.parent.mkdir(parents=True, exist_ok=True)
        datei.write_text(
            _als_sammelimport(kandidaten, freigegeben, je_durchgang, absprachen, einstellungen),
            encoding="utf-8",
        )
        return datei

    def lege_kartenentwurf_an(self, ordner: str, kandidat: int,
                              vorschlaege: list[str] | None = None,
                              rueckfragen: list[str] | None = None,
                              freigabe: str | None = None,
                              **felder) -> Path:
        """Legt einen Kartenentwurf so ab, wie der Agent ihn schreibt.

        Das Frontmatter ist das der Karte ohne `id`, mit den Standardwerten
        aus KARTE. Eine `id` steht nur darin, wenn der Test sie nennt.
        `quelldatei` nennt ohne Angabe die Dateien des Kandidaten
        laut Uebersicht, so wie der Auftrag sie vorgibt. Die Uebersicht muss
        dafuer schon da sein, wie im Betrieb: Der Agent entwirft nach dem
        freigegebenen Plan.

        Am Ende steht `## Freigabe` mit beiden Listen. `freigabe` ersetzt
        diesen Abschnitt woertlich, fuer die Entwuerfe, deren Form nicht
        stimmen soll. `freigabe=""` laesst ihn weg.
        """
        if "quelldatei" not in felder:
            felder["quelldatei"] = self._quelldatei_laut_plan(ordner, kandidat)
        karte = {k: v for k, v in {**KARTE, "id": OHNE, **felder}.items() if v is not OHNE}
        text = _als_karte(karte)
        if freigabe is None:
            freigabe = _als_freigabe(vorschlaege or [], rueckfragen or [])
        if freigabe:
            text += "\n" + freigabe
        datei = self.pfad / "kartenentwuerfe" / ordner / f"{kandidat}.md"
        datei.parent.mkdir(parents=True, exist_ok=True)
        datei.write_text(text, encoding="utf-8")
        return datei

    def _quelldatei_laut_plan(self, ordner: str, kandidat: int) -> str | None:
        """Die Dateien eines Kandidaten als Wert fuer `quelldatei:`, relativ zu quellen/.

        Ohne Uebersicht oder ohne Zeile fuer den Kandidaten None. Dann
        steht `quelldatei: null` im Entwurf, und `pruefen` weist ihn ab.
        """
        if not (self.pfad / "quellen" / ordner / "sammelimport.md").is_file():
            return None
        zeile = self.uebersicht(ordner).get(str(kandidat))
        if zeile is None:
            return None
        return ", ".join(f"{ordner}/{d}" for d in re.findall(r"`([^`]+)`", zeile["Dateien"]))

    def uebersicht(self, ordner: str) -> dict[str, dict[str, str]]:
        """Liest die Uebersicht aus `sammelimport.md`, je Kandidat eine Zeile.

        Der Schluessel ist die Nummer des Kandidaten als Text, so wie sie in
        der Tabelle steht. Die Zellen kommen ohne Rand-Leerzeichen zurueck.
        """
        text = (self.pfad / "quellen" / ordner / "sammelimport.md").read_text(encoding="utf-8")
        zeilen = {}
        for zeile in text.split("## Übersicht", 1)[1].splitlines():
            if not zeile.startswith("|") or zeile.startswith("|---"):
                continue
            zellen = [z.strip() for z in zeile.strip().strip("|").split("|")]
            if zellen[0] == UEBERSICHT_SPALTEN[0]:
                continue
            zeilen[zellen[0]] = dict(zip(UEBERSICHT_SPALTEN, zellen))
        return zeilen

    def lege_quellbild_an(self, name: str, groesse: tuple[int, int],
                          orientierung: int | None = None) -> Path:
        """Erzeugt ein Bild in `quellen/` zur Laufzeit. Braucht Pillow.

        Das Bild ist Rauschen, und das mit Absicht: nur unkomprimierbarer
        Inhalt bringt eine Datei zuverlaessig ueber die Schwelle von 2 MB,
        ohne dass hier eine Dateigroesse geraten werden muss. Die Alternative
        waere ein eingechecktes Foto. Das hiesse Binaermaterial im Repo,
        dessen Bedingung niemand mehr ansieht.

        `orientierung` schreibt den EXIF-Eintrag 0x0112. 6 heisst "fuer die
        Anzeige um 90 Grad drehen", der Wert, den die Magazinseiten tragen.
        """
        from PIL import Image  # nur hier noetig, der Rest der Suite laeuft ohne

        breite, hoehe = groesse
        bild = Image.frombytes("RGB", groesse, os.urandom(breite * hoehe * 3))
        datei = self.pfad / "quellen" / name
        datei.parent.mkdir(parents=True, exist_ok=True)
        if datei.suffix.lower() == ".png":
            bild.save(datei, "PNG")
            return datei
        exif = Image.Exif()
        if orientierung is not None:
            exif[ORIENTIERUNG] = orientierung
        bild.save(datei, "JPEG", quality=95, exif=exif)
        return datei

    def starte(self, skript: str, *argumente: str,
               eingabe: str | None = None,
               umgebung: dict[str, str] | None = None,
               mit_wurzel: bool = True,
               verzeichnis: Path | None = None) -> subprocess.CompletedProcess:
        """Ruft ein Skript so auf, wie die Skills es tun: ueber die Kommandozeile.

        Der Interpreter ist der, unter dem die Tests laufen. Damit stimmt er
        auf jedem Rechner, ohne dass hier zwischen `python` und `python3`
        entschieden werden muss.

        Ohne `eingabe` haengt stdin am Nullgeraet. Ein Skript, das eine
        Rueckfrage stellt, bekommt damit sofort ein EOF statt auf eine Eingabe
        zu warten, die nie kommt. Ohne das bliebe die Suite an der Rueckfrage
        der Bildaufbereitung haengen, sobald sie aus einem Terminal laeuft.

        `eingabe` beantwortet die Rueckfrage. Nur so ist der Ja-Zweig
        pruefbar, und er ist der, hinter dem das Ersetzen der Originale
        haengt.

        `umgebung` legt sich ueber die Umgebungsvariablen des Testlaufs, statt
        sie zu ersetzen. Damit laesst sich eine Bibliothek ausblenden, ohne
        dem Skript dafuer einen Schalter zu geben, den es im Betrieb nicht
        braucht.

        `mit_wurzel=False` laesst `--wurzel` weg und `verzeichnis` sagt, wo
        der Aufruf steht. Beide zusammen sind der Aufruf von Hand: dann sucht
        das Skript den Arbeitsordner selbst, ab dem angegebenen Verzeichnis
        aufwaerts, und findet neben dem Arbeitsordner keinen. Ohne die beiden
        liefe jeder Aufruf mit `--wurzel` und im Verzeichnis des Testlaufs,
        und die Suche waere nie gepruefter Code.
        """
        # subprocess.run nimmt `input` und `stdin` nicht zusammen entgegen.
        strom = ({"input": eingabe} if eingabe is not None
                 else {"stdin": subprocess.DEVNULL})
        wurzel = ["--wurzel", str(self.pfad)] if mit_wurzel else []
        return subprocess.run(
            [sys.executable, str(SKRIPTE / skript), *wurzel, *argumente],
            capture_output=True, text=True, encoding="utf-8", errors="replace",
            env={**os.environ, **(umgebung or {})},
            cwd=str(verzeichnis) if verzeichnis is not None else None,
            check=False, **strom,
        )

    def raeume_auf(self) -> None:
        """Loescht den Ordner und die index.json, die die Skripte angelegt haben.

        Die index.json landet im Cache des Rechners, unter einem Namen, der
        aus dem Wurzelpfad abgeleitet ist. Das Loeschen des Ordners allein
        laesst sie also liegen. Wo sie steht, verraet `index.py --still`. Danach zu fragen ist billiger, als
        die Ableitung hier nachzubauen und bei ihrem naechsten Umbau still
        danebenzugreifen. Jeder Testlauf legt einen neuen Wurzelpfad an, ohne
        Aufraeumen wuechse der Cache also mit jedem Lauf.
        """
        fertig = self.starte("index.py", "--still")
        if fertig.returncode == 0 and fertig.stdout.strip():
            try:
                Path(fertig.stdout.strip()).unlink()
            except OSError:
                pass
        shutil.rmtree(self.pfad, ignore_errors=True)
        if self.entwurfsordner is not None:
            shutil.rmtree(self.entwurfsordner, ignore_errors=True)
