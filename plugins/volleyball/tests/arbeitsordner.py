"""Baut einen kuenstlichen Arbeitsordner im Temp-Verzeichnis.

Die Tests pruefen Linter und Suche so, wie die Skills sie aufrufen: ueber die
Kommandozeile, mit `--wurzel` auf diesen Ordner. Beide Skripte nehmen den
Wurzelpfad schon als Argument entgegen, der Fixture ist also ohne eine Zeile
Produktionscode injizierbar. Die echte Bibliothek wird dabei nie angefasst.

Der Ordner ist absichtlich klein: Wurzeldatei, eine Schwerpunktliste und eine
Handvoll Karten, die genau die geprueften Faelle abdecken. Wer einen weiteren
Fall braucht, legt eine Karte dazu, statt eine bestehende umzubiegen. Sonst
zieht eine Aenderung Tests mit, die von ihr nichts wissen wollen.

Die IDs gehoeren dem Fixture. Wer hier ue-0005 liest, liest nicht die Karte
ue-0005 aus der echten Bibliothek.
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

Eine Ausnahme ist `nur-beach`. Eine rein beachspezifische Kennung gibt es in
der echten Liste noch nicht, weil die erst aus echtem Importmaterial entsteht
und ein Mensch sie eintraegt. Fuer die Mismatch-Pruefung braucht es sie aber,
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
    "id": "ue-0000",
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
    # Die einzige Karte, die zwei Spielflaechen braucht.
    {
        "id": "ue-0003",
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
        "id": "ue-0004",
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
        "id": "ue-0005",
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

    def lege_karte_an(self, **felder) -> None:
        """Legt eine Uebungskarte an.

        Nicht genannte Felder kommen aus KARTE. Ein Feld auf `OHNE` gesetzt
        fehlt auf der Karte ganz.
        """
        karte = {k: v for k, v in {**KARTE, **felder}.items() if v is not OHNE}
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
