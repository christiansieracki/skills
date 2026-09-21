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

import os
import re
import shutil
import subprocess
import sys
import tempfile
import textwrap
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
               umgebung: dict[str, str] | None = None) -> subprocess.CompletedProcess:
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
        """
        # subprocess.run nimmt `input` und `stdin` nicht zusammen entgegen.
        strom = ({"input": eingabe} if eingabe is not None
                 else {"stdin": subprocess.DEVNULL})
        return subprocess.run(
            [sys.executable, str(SKRIPTE / skript), "--wurzel", str(self.pfad), *argumente],
            capture_output=True, text=True, encoding="utf-8", errors="replace",
            env={**os.environ, **(umgebung or {})},
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
