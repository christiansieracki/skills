#!/usr/bin/env python3
"""
Exportiert die Markdown-Dokumente der Volleyball-Trainingsplanung als PDF.

Nutzung:
    <python> export_pdf.py                      # alles in der Trainingsplanung
    <python> export_pdf.py <pfad>               # einzelne Datei oder Ordner
    <python> export_pdf.py <pfad> -o <ausgabe>  # eigener Ausgabeordner

Ohne Pfad wird die Wurzel ueber trainingsplanung-root.yml gesucht, genau wie
bei den anderen Skripten. Die PDFs landen in <wurzel>/pdf/ und spiegeln die
Ordnerstruktur. Bestehende PDFs werden ueberschrieben.

Gedruckt wird mit dem, was auf dem Rechner schon da ist. Erste Wahl ist pandoc
mit einer PDF-Maschine wie wkhtmltopdf oder weasyprint. Fehlt die Maschine,
druckt Edge oder Chrome die HTML-Fassung, und dafuer muss niemand etwas
nachinstallieren. Fehlt auch das, sagt das Skript, was zu holen waere.
"""

import argparse
import importlib.util
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from tpdaten import finde_wurzel, konsole_vorbereiten  # noqa: E402

VON = "markdown+pipe_tables+yaml_metadata_block+hard_line_breaks"

# PDF-Maschinen, die pandoc ansteuern kann. Die beiden HTML-Maschinen stehen
# vorn, weil das CSS unten fuer sie gebaut ist. Der LaTeX-Zweig kommt danach:
# er ignoriert das CSS, liefert aber immer noch ein brauchbares PDF.
PDF_MASCHINEN = ("wkhtmltopdf", "weasyprint", "prince", "pagedjs-cli",
                 "typst", "xelatex", "lualatex", "pdflatex", "tectonic")

BROWSER_NAMEN = ("msedge", "microsoft-edge", "google-chrome",
                 "google-chrome-stable", "chromium", "chromium-browser")

CSS = """
@page { size: A4; margin: 16mm 14mm; }
body {
  font-family: -apple-system, "Helvetica Neue", Arial, sans-serif;
  font-size: 11.5pt; line-height: 1.5; color: #1a1a1a; max-width: 100%;
}
h1 { font-size: 20pt; margin: 0 0 4pt; border-bottom: 2px solid #333; padding-bottom: 4pt; }
h2 { font-size: 14pt; margin: 16pt 0 4pt; }
h3 { font-size: 12pt; margin: 12pt 0 3pt; }
table { border-collapse: collapse; width: 100%; margin: 8pt 0; font-size: 10pt; }
th, td { border: 1px solid #bbb; padding: 4pt 6pt; text-align: left; vertical-align: top; }
th { background: #eee; }
tr { page-break-inside: avoid; }
code { background: #f2f2f2; padding: 1pt 3pt; font-size: 10pt; }
blockquote { border-left: 3px solid #ccc; margin-left: 0; padding-left: 10pt; color: #444; }
ul, ol { margin: 4pt 0; padding-left: 18pt; }
h1, h2, h3 { page-break-after: avoid; }
img { max-width: 100%; }
"""


# --------------------------------------------------------------------------
# Was auf diesem Rechner da ist
# --------------------------------------------------------------------------

def pdf_maschine() -> str | None:
    """Die erste PDF-Maschine, die pandoc hier benutzen kann."""
    for name in PDF_MASCHINEN:
        if shutil.which(name):
            return name
    return None


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


def browser() -> str | None:
    """Ein Browser, der eine HTML-Datei drucken kann."""
    for name in BROWSER_NAMEN:
        pfad = shutil.which(name)
        if pfad:
            return pfad
    for pfad in browser_orte():
        if pfad.exists():
            return str(pfad)
    return None


def hat_markdown() -> bool:
    """Das Python-Paket markdown, der Ersatz fuer pandoc beim HTML-Bauen."""
    return importlib.util.find_spec("markdown") is not None


def waehle_weg() -> tuple[str, str] | None:
    """Sucht den Weg vom Markdown zum PDF, der auf diesem Rechner geht."""
    maschine = pdf_maschine()
    if shutil.which("pandoc") and maschine:
        return ("pandoc", maschine)

    nach_html = shutil.which("pandoc") or hat_markdown()
    gefunden = browser()
    if gefunden and nach_html:
        return ("browser", gefunden)

    if shutil.which("wkhtmltopdf") and hat_markdown():
        return ("wkhtmltopdf", "wkhtmltopdf")
    return None


def beschreibe(weg: tuple[str, str]) -> str:
    art, werkzeug = weg
    if art == "pandoc":
        return f"pandoc mit {werkzeug}"
    if art == "browser":
        return f"{Path(werkzeug).stem} im Druckmodus"
    return "wkhtmltopdf"


# --------------------------------------------------------------------------
# Umwandeln
# --------------------------------------------------------------------------

def baue_html(src: Path, css_pfad: Path, ziel: Path) -> None:
    """Macht aus der .md eine HTML-Datei, die alles Noetige eingebettet hat.

    Eingebettet heisst: die Schaubilder wandern als Data-URI mit hinein. Sonst
    zeigten die relativen Bildpfade aus dem Temp-Ordner heraus ins Leere.
    """
    if shutil.which("pandoc"):
        ergebnis = subprocess.run(
            ["pandoc", str(src), "-o", str(ziel), "--standalone",
             "--embed-resources", "--from", VON, "--css", str(css_pfad),
             "--resource-path", str(src.parent),
             "--metadata", f"title={src.stem}"],
            capture_output=True, text=True, timeout=180,
        )
        if ergebnis.returncode != 0:
            raise RuntimeError(ergebnis.stderr.strip()[:200])
        return

    import markdown  # nur ohne pandoc noetig
    rumpf = markdown.markdown(
        src.read_text(encoding="utf-8"), extensions=["tables", "fenced_code"]
    )
    ziel.write_text(
        '<html><head><meta charset="utf-8"><style>' + CSS + "</style></head>"
        "<body>" + rumpf + "</body></html>",
        encoding="utf-8",
    )


def md_to_pdf(src: Path, dest: Path, weg: tuple[str, str]) -> bool:
    dest.parent.mkdir(parents=True, exist_ok=True)
    art, werkzeug = weg

    with tempfile.TemporaryDirectory() as tmp:
        css_pfad = Path(tmp) / "druck.css"
        css_pfad.write_text(CSS, encoding="utf-8")
        try:
            if art == "pandoc":
                cmd = ["pandoc", str(src), "-o", str(dest), "--from", VON,
                       "--pdf-engine", werkzeug, "--css", str(css_pfad),
                       "--resource-path", str(src.parent)]
            else:
                html = Path(tmp) / "druck.html"
                baue_html(src, css_pfad, html)
                if art == "browser":
                    cmd = [werkzeug, "--headless", "--disable-gpu",
                           "--no-pdf-header-footer",
                           "--user-data-dir=" + str(Path(tmp) / "profil"),
                           "--print-to-pdf=" + str(dest), html.as_uri()]
                else:
                    cmd = ["wkhtmltopdf", "--quiet", "--encoding", "utf-8",
                           str(html), str(dest)]

            ergebnis = subprocess.run(cmd, capture_output=True, text=True, timeout=180)
            if ergebnis.returncode != 0:
                print(f"  FEHLER bei {src.name}: {ergebnis.stderr.strip()[:200]}")
                return False
            if not dest.exists():
                # Der Browser meldet auch dann Erfolg, wenn nichts entstanden ist.
                print(f"  FEHLER bei {src.name}: es ist kein PDF entstanden")
                return False
            return True
        except Exception as exc:  # noqa: BLE001
            print(f"  FEHLER bei {src.name}: {exc}")
            return False


def main():
    konsole_vorbereiten()
    parser = argparse.ArgumentParser(description="Markdown-Trainingsdokumente als PDF exportieren")
    parser.add_argument("pfad", nargs="?", default=None,
                        help="Datei oder Ordner (Standard: die Wurzel der Trainingsplanung)")
    parser.add_argument("-o", "--ausgabe", default=None, help="Ausgabeordner")
    args = parser.parse_args()

    weg = waehle_weg()
    if not weg:
        print("Kein Weg zum PDF gefunden.")
        print("Fuer den Schritt nach HTML braucht es pandoc, zum Drucken eine")
        print("PDF-Maschine wie wkhtmltopdf oder einen Browser (Edge, Chrome).")
        print("Installieren mit z.B.:  winget install --id JohnMacFarlane.Pandoc")
        print("                 oder:  brew install pandoc wkhtmltopdf")
        print("                 oder:  sudo apt install pandoc wkhtmltopdf")
        sys.exit(1)

    quelle = Path(args.pfad) if args.pfad else finde_wurzel()
    if not quelle.exists():
        print(f"Pfad nicht gefunden: {quelle}")
        sys.exit(1)

    basis = quelle if quelle.is_dir() else quelle.parent
    ausgabe = Path(args.ausgabe) if args.ausgabe else basis / "pdf"

    dateien = [quelle] if quelle.is_file() else sorted(
        p for p in quelle.rglob("*.md") if "pdf" not in p.parts
    )
    if not dateien:
        print(f"Keine .md-Dateien unter {quelle} gefunden.")
        sys.exit(0)

    print(f"Weg: {beschreibe(weg)} | {len(dateien)} Dokument(e) -> {ausgabe}/")
    ok = 0
    for src in dateien:
        rel = src.relative_to(basis) if src.is_relative_to(basis) else Path(src.name)
        dest = ausgabe / rel.with_suffix(".pdf")
        if md_to_pdf(src, dest, weg):
            print(f"  ok: {rel.with_suffix('.pdf')}")
            ok += 1
    print(f"Fertig: {ok}/{len(dateien)} exportiert.")


if __name__ == "__main__":
    main()
