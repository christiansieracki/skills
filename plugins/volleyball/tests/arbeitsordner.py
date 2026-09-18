"""Baut einen kuenstlichen Arbeitsordner im Temp-Verzeichnis.

Die Tests pruefen Linter und Suche so, wie die Skills sie aufrufen: ueber die
Kommandozeile, mit `--wurzel` auf diesen Ordner. Beide Skripte nehmen den
Wurzelpfad schon als Argument entgegen, der Fixture ist also ohne eine Zeile
Produktionscode injizierbar. Die echte Bibliothek wird dabei nie angefasst.

Der Ordner ist absichtlich klein: Wurzeldatei, eine Schwerpunktliste und eine
Handvoll Karten, die genau die geprueften Faelle abdecken. Wer einen weiteren
Fall braucht, legt eine Karte dazu, statt eine bestehende umzubiegen. Sonst
zieht eine Aenderung Tests mit, die von ihr nichts wissen wollen.
"""

from __future__ import annotations

import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

SKRIPTE = Path(__file__).resolve().parent.parent / "scripts"

WURZELDATEI = "trainingsplanung-root.yml"

ROOT_YML = """\
# Wurzeldatei eines kuenstlichen Arbeitsordners fuer die Tests.
#
# Heute zaehlt nur, dass es sie gibt: finde_wurzel() erkennt den Ordner an
# ihrem Namen. Gelesen wird sie von index.py und suche.py nicht, deshalb steht
# hier nur das Noetigste. Was ein echter Arbeitsordner mitbringt, legt
# init_struktur.py an.

version: 1
verein: "Testverein"
saison: "2025/26"
"""

SCHWERPUNKTE_MD = """\
# Schwerpunkte

Kurzfassung fuer die Tests. Die Kennungen stammen aus der Startfassung des
Plugins, damit hier keine Sprache erfunden wird, die es im Verein nicht gibt.

## Inhaltliche Schwerpunkte

| Kennung | Klartext |
|---|---|
| `ballkontrolle` | Sauberer Kontakt in Bagger und Pritschen, ohne Spielsituation |
| `annahme` | Annahme als Technikelement |
| `sideout-sicherheit` | Den eigenen Aufschlagball sicher zurueckgewinnen |
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
    "id": "ue-0000",
    "titel": "Ohne Titel",
    "typ": "uebung",
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
    "hallenteile": 1,
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
    # Braucht wenige Spieler und ein Hallenteil.
    {
        "id": "ue-0001",
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
        "id": "ue-0002",
        "titel": "Zonenbaggern im Paar",
        "spieler_min": 2,
        "spieler_max": 4,
        "dauer_min": 8,
        "dauer_max": 8,
    },
    # Die einzige Karte, die zwei Hallenteile braucht.
    {
        "id": "ue-0003",
        "titel": "Sideout-Serie über zwei Hallenteile",
        "element": ["annahme", "angriff"],
        "spielphase": "sideout",
        "form": "spielform",
        "schwerpunkt": ["sideout-sicherheit"],
        "spieler_min": 12,
        "spieler_max": 16,
        "dauer_min": 20,
        "dauer_max": 25,
        "hallenteile": 2,
        "netz": True,
    },
]

UMLAUTE = str.maketrans({"ä": "ae", "ö": "oe", "ü": "ue", "ß": "ss"})


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


class Arbeitsordner:
    """Ein kuenstlicher Arbeitsordner, der sich wieder wegraeumen laesst."""

    def __init__(self) -> None:
        self.pfad = Path(tempfile.mkdtemp(prefix="trainingsplanung-test-"))
        self.ids: list[str] = []
        (self.pfad / WURZELDATEI).write_text(ROOT_YML, encoding="utf-8")
        (self.pfad / "schwerpunkte.md").write_text(SCHWERPUNKTE_MD, encoding="utf-8")
        (self.pfad / "uebungen").mkdir()
        for felder in STANDARDKARTEN:
            self.lege_karte_an(**felder)

    def lege_karte_an(self, **felder) -> None:
        """Legt eine Uebungskarte an. Nicht genannte Felder kommen aus KARTE."""
        karte = {**KARTE, **felder}
        datei = self.pfad / "uebungen" / f"{karte['id']}-{_slug(karte['titel'])}.md"
        datei.write_text(_als_karte(karte), encoding="utf-8")
        self.ids.append(karte["id"])

    def starte(self, skript: str, *argumente: str) -> subprocess.CompletedProcess:
        """Ruft ein Skript so auf, wie die Skills es tun: ueber die Kommandozeile.

        Der Interpreter ist der, unter dem die Tests laufen. Damit stimmt er
        auf jedem Rechner, ohne dass hier zwischen `python` und `python3`
        entschieden werden muss.
        """
        return subprocess.run(
            [sys.executable, str(SKRIPTE / skript), "--wurzel", str(self.pfad), *argumente],
            capture_output=True, text=True, encoding="utf-8", errors="replace",
            check=False,
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
