#!/usr/bin/env python3
"""Edge oder Chrome ohne Fenster: eine Seite als PDF drucken oder als PNG aufnehmen.

Gesucht und aufgerufen wird der Browser hier und nirgends sonst.
`export_pdf.py` druckt damit Trainingsplaene, wenn pandoc keine PDF-Maschine
findet, und `schaubild.py --png` nimmt ein Schaubild auf, fuer eine Vorschau,
die ein SVG nicht als Bild zeigt. Beide brauchen dieselben Kniffe: die festen
Installationsorte unter Windows, die Umgebung ohne `__COMPAT_LAYER` und den
Blick auf die Platte, ob die Datei wirklich entstanden ist.

Nur Standardbibliothek. Gibt es keinen Browser, liefert `finde_browser()`
None, und der Aufrufer sagt, was dann fehlt.
"""

from __future__ import annotations

import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

BROWSER_NAMEN = ("msedge", "microsoft-edge", "google-chrome",
                 "google-chrome-stable", "chromium", "chromium-browser")


class BrowserFehler(Exception):
    """Der Browser hat die Datei nicht geliefert. Die Meldung sagt, warum."""


def browser_orte() -> list[Path]:
    """Die ueblichen Installationsorte von Edge und Chrome.

    Unter Windows steht keiner der beiden im PATH, deshalb die festen Pfade.
    """
    if sys.platform == "win32":
        ordner = [os.environ.get("ProgramFiles"),
                  os.environ.get("ProgramFiles(x86)"),
                  os.environ.get("LOCALAPPDATA")]
        return [Path(o) / rest
                for o in ordner if o
                for rest in (r"Microsoft\Edge\Application\msedge.exe",
                             r"Google\Chrome\Application\chrome.exe")]
    if sys.platform == "darwin":
        return [Path("/Applications/Microsoft Edge.app/Contents/MacOS/Microsoft Edge"),
                Path("/Applications/Google Chrome.app/Contents/MacOS/Google Chrome")]
    return []


def finde_browser() -> str | None:
    """Edge oder Chrome, wie es auf diesem Rechner aufzurufen ist."""
    for name in BROWSER_NAMEN:
        pfad = shutil.which(name)
        if pfad:
            return pfad
    for pfad in browser_orte():
        if pfad.exists():
            return str(pfad)
    return None


def ohne_kompatibilitaetsschicht() -> dict[str, str]:
    """Die Umgebung ohne __COMPAT_LAYER, fuer den Aufruf des Browsers.

    Windows setzt die Variable fuer Prozesse, die aus manchen Anwendungen
    heraus starten, etwa `DetectorsAppHealth` aus der Claude-App. Edge startet
    sich dann ohne sie neu, und der Prozess, auf den das Skript wartet, kehrt
    sofort zurueck. Die Datei kommt Sekunden spaeter, wenn der Temp-Ordner mit
    der Seite schon weg ist. Ohne die Variable bleibt Edge ein einziger
    Prozess und kehrt erst zurueck, wenn die Datei geschrieben ist.
    """
    return {k: v for k, v in os.environ.items() if k.upper() != "__COMPAT_LAYER"}


class Browser:
    """Ein Browser ohne Fenster, mit einem Profilordner fuer alle seine Aufrufe.

    Als Kontextmanager gedacht: am Ende wird der Profilordner weggeraeumt.
    Haelt der Browser ihn dann noch, bleibt er eben liegen, statt dass das
    Aufraeumen den Lauf abbricht.
    """

    def __init__(self, programm: str) -> None:
        self.programm = programm
        self._ordner = tempfile.TemporaryDirectory(
            prefix="volleyball-browser-", ignore_cleanup_errors=True)

    def __enter__(self) -> Browser:
        return self

    def __exit__(self, *_) -> None:
        self._ordner.cleanup()

    def drucke(self, seite: Path, pdf: Path) -> None:
        """Druckt die Seite als PDF, ohne Kopf- und Fusszeile des Browsers."""
        self._starte(pdf, "--no-pdf-header-footer",
                     "--print-to-pdf=" + str(pdf), seite.as_uri())

    def nimm_auf(self, seite: Path, png: Path, breite: int, hoehe: int) -> None:
        """Nimmt die Seite als PNG auf, so gross wie ein Fenster von breite x hoehe Pixeln."""
        self._starte(png, "--hide-scrollbars", f"--window-size={breite},{hoehe}",
                     "--screenshot=" + str(png), seite.as_uri())

    def _starte(self, ziel: Path, *argumente: str) -> None:
        # Der Browser meldet auch dann Erfolg, wenn nichts entstanden ist. Ob es
        # geklappt hat, zeigt allein die Datei, und eine vom letzten Lauf darf
        # dabei nicht fuer eine neue durchgehen.
        try:
            ziel.unlink(missing_ok=True)
            ergebnis = subprocess.run(
                [self.programm, "--headless", "--disable-gpu",
                 "--user-data-dir=" + str(Path(self._ordner.name) / "profil"),
                 *argumente],
                capture_output=True, text=True, timeout=180,
                env=ohne_kompatibilitaetsschicht(),
            )
        except (OSError, subprocess.TimeoutExpired) as fehler:
            raise BrowserFehler(str(fehler)) from fehler
        if ergebnis.returncode != 0:
            raise BrowserFehler(ergebnis.stderr.strip()[:200])
        if not ziel.exists():
            raise BrowserFehler(f"es ist kein {ziel.suffix[1:].upper()} entstanden")
