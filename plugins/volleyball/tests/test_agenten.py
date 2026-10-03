"""Prueft die Agentendefinitionen des Sammelimports gegen das Datenmodell.

    <python> -m unittest discover -s plugins/volleyball/tests

Die beiden Agenten unter `agents/` haben keine Kommandozeile, also gibt es
nichts zu starten. Ihr Prompt schreibt die kontrollierten Werte und die Felder
der Karte aus, weil der Agent nur `Read` und `Write` hat und `tpdaten.py` nicht
fragen kann (ADR-0009). Ausgeschrieben laufen sie dem Datenmodell still
hinterher: Kommt in `tpdaten.py` ein Element dazu, entwirft der Agent weiter
ohne, und `pruefen` weist ab, was er nach seiner alten Liste schreibt.

Deshalb ist das der einzige Test, der `tpdaten` importiert statt ein Skript zu
starten. Er liest die Definitionen als Text und vergleicht.
"""

from __future__ import annotations

import re
import sys
import unittest
from pathlib import Path

PLUGIN = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PLUGIN / "scripts"))

import tpdaten  # noqa: E402

AGENTEN = ["volleyball-kartenentwurf", "volleyball-zerlegungsplan"]

# Je Feld die Werte aus tpdaten.py. Die Level stehen als Liste, ihre
# Reihenfolge zaehlt: level_min darf nicht ueber level_max liegen.
KONTROLLIERT = {
    "typ": tpdaten.TYPEN,
    "disziplin": tpdaten.DISZIPLINEN,
    "element": tpdaten.ELEMENTE,
    "spielphase": tpdaten.SPIELPHASEN,
    "form": tpdaten.FORMEN,
    "level_min": tpdaten.LEVEL,
    "level_max": tpdaten.LEVEL,
}


def definition(name: str) -> Path:
    return PLUGIN / "agents" / f"{name}.md"


def abschnitt(text: str, titel: str) -> list[str]:
    """Die Zeilen unter `## <titel>` bis zur naechsten Ueberschrift dieser Ebene.

    Eine Ueberschrift in einem Codeblock zaehlt nicht: Das Schema des
    Entwurfs zeigt die Abschnitte der Karte.
    """
    zeilen = text.splitlines()
    anfang = zeilen.index(f"## {titel}")
    im_codeblock = False
    for i in range(anfang + 1, len(zeilen)):
        if zeilen[i].startswith("```"):
            im_codeblock = not im_codeblock
        elif not im_codeblock and zeilen[i].startswith(("# ", "## ")):
            return zeilen[anfang + 1:i]
    return zeilen[anfang + 1:]


def kontrollierte_werte(text: str) -> dict[str, list[str]]:
    """Je Feld die Werte aus `## Kontrollierte Werte`, in ihrer Reihenfolge.

    Ein Punkt sieht so aus: ``- `form`: `technik`, `komplex` ``. Vor dem
    Doppelpunkt stehen die Felder in Backticks, dahinter die Werte. Zwei
    Felder mit denselben Werten teilen sich einen Punkt. Eine eingerueckte
    Zeile setzt den Punkt davor fort.
    """
    punkte: list[str] = []
    for zeile in abschnitt(text, "Kontrollierte Werte"):
        if zeile.startswith("- "):
            punkte.append(zeile)
        elif punkte and zeile.startswith(" ") and zeile.strip():
            punkte[-1] += " " + zeile.strip()
        elif punkte:
            break
    werte: dict[str, list[str]] = {}
    for punkt in punkte:
        felder, _, rest = punkt.partition(":")
        for feld in re.findall(r"`([a-z_]+)`", felder):
            werte[feld] = re.findall(r"`([^`]+)`", rest)
    return werte


def entwurfsfelder(text: str) -> list[str]:
    """Die Felder im Frontmatter des Schemas, das der Agent schreiben soll.

    Das Schema ist der erste Codeblock unter `## Der Entwurf`, das Frontmatter
    darin steht zwischen zwei Zeilen `---`.
    """
    zeilen = abschnitt(text, "Der Entwurf")
    block = next(i for i, z in enumerate(zeilen) if z.startswith("```"))
    anfang = zeilen.index("---", block)
    ende = zeilen.index("---", anfang + 1)
    return [m.group(1) for z in zeilen[anfang + 1:ende]
            if (m := re.match(r"([a-z_]+):", z))]


class AgentenTest(unittest.TestCase):
    def kopf(self, name: str) -> dict:
        felder, _ = tpdaten.lies_frontmatter(definition(name))
        return felder

    def test_beide_agenten_liegen_im_plugin_mit_name_und_beschreibung(self) -> None:
        for name in AGENTEN:
            with self.subTest(name):
                self.assertTrue(definition(name).is_file(), definition(name))
                kopf = self.kopf(name)
                self.assertEqual(kopf.get("name"), name)
                self.assertTrue(kopf.get("description"))

    def test_das_modell_ist_sonnet(self) -> None:
        # Haiku hat im Probelauf in 13 von 20 Entwuerfen erfunden (ADR-0009).
        for name in AGENTEN:
            with self.subTest(name):
                self.assertEqual(self.kopf(name).get("model"), "sonnet")

    def test_die_werkzeuge_sind_genau_read_und_write(self) -> None:
        # Ein Agent mit Bash oder Edit koennte die Uebersicht anfassen, und die
        # schreibt nach der Freigabe des Plans nur sammelimport.py.
        for name in AGENTEN:
            with self.subTest(name):
                werkzeuge = [w.strip() for w in str(self.kopf(name).get("tools")).split(",")]
                self.assertEqual(sorted(werkzeuge), ["Read", "Write"])

    def test_die_kontrollierten_werte_stimmen_genau_mit_tpdaten(self) -> None:
        # Sortiert verglichen faellt auch ein Wert auf, der doppelt dasteht.
        for name in AGENTEN:
            with self.subTest(name):
                werte = kontrollierte_werte(definition(name).read_text(encoding="utf-8"))
                self.assertEqual(sorted(werte), sorted(KONTROLLIERT))
                for feld, erwartet in KONTROLLIERT.items():
                    if isinstance(erwartet, list):
                        self.assertEqual(werte[feld], erwartet, feld)
                    else:
                        self.assertEqual(sorted(werte[feld]), sorted(erwartet), feld)

    def test_der_kartenentwurf_traegt_jedes_feld_der_karte_ausser_id_und_angelegt(self) -> None:
        # pruefen verlangt jedes dieser Felder, auch die mit null. Ein Feld,
        # das im Schema fehlt, fehlt in jedem Entwurf, und jeder neue Aufruf
        # kostet rund 91 000 Tokens.
        text = definition("volleyball-kartenentwurf").read_text(encoding="utf-8")
        erwartet = [f for f in tpdaten.KARTENFELDER if f not in ("id", "angelegt")]
        self.assertEqual(entwurfsfelder(text), erwartet)


if __name__ == "__main__":
    unittest.main()
