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
import sys
from pathlib import Path

MARKER = "trainingsplanung-root.yml"

ELEMENTE = {
    "annahme", "zuspiel", "angriff", "block", "abwehr", "aufschlag",
    "ballkontrolle", "athletik", "koordination",
}
SPIELPHASEN = {"sideout", "break", "keine"}
FORMEN = {"erwaermung", "technik", "komplex", "spielform", "station", "abschluss"}
LEVEL = ["einsteiger", "fortgeschritten", "ambitioniert"]
TYPEN = {"uebung", "folge"}


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

def finde_wurzel(start: Path | None = None) -> Path:
    """Sucht ab `start` aufwaerts nach der Markerdatei.

    Damit ist es egal, wie der Ordner heisst und wo er liegt, solange
    trainingsplanung-root.yml mitwandert.
    """
    p = (start or Path.cwd()).resolve()
    for kandidat in [p, *p.parents]:
        if (kandidat / MARKER).is_file():
            return kandidat
    raise SystemExit(
        f"Keine {MARKER} gefunden. Das Skript aus dem Trainingsplanungs-Ordner\n"
        f"heraus starten oder den Pfad mit --wurzel angeben."
    )


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


# --------------------------------------------------------------------------
# Einlesen
# --------------------------------------------------------------------------

def lies_schwerpunkte(wurzel: Path) -> set[str]:
    """Zieht die erlaubten Kennungen aus den Tabellen in schwerpunkte.md."""
    datei = wurzel / "schwerpunkte.md"
    if not datei.is_file():
        return set()
    return set(re.findall(r"^\|\s*`([a-z0-9-]+)`\s*\|", datei.read_text(encoding="utf-8"), re.M))


def lies_uebungen(wurzel: Path) -> list[dict]:
    karten = []
    ordner = wurzel / "uebungen"
    if not ordner.is_dir():
        return karten
    for pfad in sorted(ordner.glob("*.md")):
        if pfad.name.startswith("_") or pfad.name.upper() == "README.MD":
            continue
        fm, rumpf = lies_frontmatter(pfad)
        if not fm.get("id"):
            continue
        fm["datei"] = pfad.relative_to(wurzel).as_posix()
        fm["_rumpf"] = rumpf
        karten.append(fm)
    return karten


def lies_trainings(wurzel: Path) -> list[dict]:
    einheiten = []
    ordner = wurzel / "trainings"
    if not ordner.is_dir():
        return einheiten
    for pfad in sorted(ordner.rglob("*.md")):
        if pfad.name.startswith("_") or pfad.name.upper() == "README.MD":
            continue
        fm, rumpf = lies_frontmatter(pfad)
        fm["datei"] = pfad.relative_to(wurzel).as_posix()
        fm["verwendet"] = sorted(set(re.findall(r"\bue-\d{4}\b", rumpf)))
        einheiten.append(fm)
    return einheiten


# --------------------------------------------------------------------------
# Index bauen
# --------------------------------------------------------------------------

SCHLANK = [
    "id", "titel", "typ", "element", "spielphase", "form", "schwerpunkt",
    "level_min", "level_max", "spieler_min", "spieler_max",
    "dauer_min", "dauer_max", "spielflaechen", "netz",
    "erwachsenenbelastung", "belastungshinweis", "material",
    "variante_von", "schaubild", "quelle", "quelldatei", "autor", "datei",
]


def baue_index(wurzel: Path) -> dict:
    karten = lies_uebungen(wurzel)
    trainings = lies_trainings(wurzel)
    erlaubt = lies_schwerpunkte(wurzel)

    # Einsatzhistorie aus den Trainingsplaenen, statt sie auf den Karten zu pflegen
    einsaetze: dict[str, list[str]] = {}
    for t in trainings:
        datum = str(t.get("datum") or "")
        for uid in t.get("verwendet", []):
            einsaetze.setdefault(uid, []).append(datum)

    bekannt = {k["id"] for k in karten}
    eintraege = []
    for k in karten:
        e = {f: k.get(f) for f in SCHLANK}
        hist = sorted(x for x in einsaetze.get(k["id"], []) if x)
        e["eingesetzt"] = hist
        e["zuletzt"] = hist[-1] if hist else None
        e["anzahl_einsaetze"] = len(hist)
        eintraege.append(e)

    return {
        "wurzel": str(wurzel),
        "anzahl": len(eintraege),
        "uebungen": eintraege,
        "warnungen": pruefe(karten, trainings, erlaubt, bekannt),
    }


def pruefe(karten, trainings, erlaubt, bekannt) -> list[str]:
    w: list[str] = []
    gesehen: dict[str, str] = {}

    for k in karten:
        kid, datei = k["id"], k["datei"]
        if kid in gesehen:
            w.append(f"{datei}: id {kid} gibt es schon in {gesehen[kid]}")
        gesehen[kid] = datei

        if not re.fullmatch(r"ue-\d{4}", str(kid)):
            w.append(f"{datei}: id {kid} passt nicht zum Muster ue-####")
        if not str(Path(datei).name).startswith(str(kid)):
            w.append(f"{datei}: Dateiname beginnt nicht mit der id {kid}")
        if k.get("typ") not in TYPEN:
            w.append(f"{datei}: typ {k.get('typ')!r} ist weder uebung noch folge")

        for el in k.get("element") or []:
            if el not in ELEMENTE:
                w.append(f"{datei}: element {el!r} steht nicht in der Liste")
        if k.get("spielphase") not in SPIELPHASEN:
            w.append(f"{datei}: spielphase {k.get('spielphase')!r} ist unbekannt")
        if k.get("form") not in FORMEN:
            w.append(f"{datei}: form {k.get('form')!r} ist unbekannt")

        if erlaubt:
            for s in k.get("schwerpunkt") or []:
                if s not in erlaubt:
                    w.append(f"{datei}: schwerpunkt {s!r} steht nicht in schwerpunkte.md")

        for feld in ("level_min", "level_max"):
            v = k.get(feld)
            if v is None:
                w.append(f"{datei}: {feld} ist leer")
            elif v not in LEVEL:
                w.append(f"{datei}: {feld} {v!r} ist kein gueltiges Level")

        lo, hi = k.get("spieler_min"), k.get("spieler_max")
        if isinstance(lo, int) and isinstance(hi, int) and lo > hi:
            w.append(f"{datei}: spieler_min {lo} ist groesser als spieler_max {hi}")
        lo, hi = k.get("dauer_min"), k.get("dauer_max")
        if isinstance(lo, int) and isinstance(hi, int) and lo > hi:
            w.append(f"{datei}: dauer_min {lo} ist groesser als dauer_max {hi}")

        if k.get("erwachsenenbelastung") and not (k.get("belastungshinweis") or "").strip():
            w.append(f"{datei}: erwachsenenbelastung ist gesetzt, aber belastungshinweis ist leer")

        vv = k.get("variante_von")
        if vv and vv not in bekannt:
            w.append(f"{datei}: variante_von zeigt auf {vv}, das es nicht gibt")
        if not k.get("quelle"):
            w.append(f"{datei}: quelle fehlt")

    for t in trainings:
        for uid in t.get("verwendet", []):
            if uid not in bekannt:
                w.append(f"{t['datei']}: verweist auf {uid}, das es in uebungen/ nicht gibt")

    return w


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
