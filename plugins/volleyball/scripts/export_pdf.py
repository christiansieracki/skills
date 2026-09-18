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

Benoetigt pandoc ODER wkhtmltopdf. Fehlt beides, gibt das Skript einen
Hinweis mit Installationsbefehl aus.
"""

import argparse
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from tpdaten import finde_wurzel, konsole_vorbereiten  # noqa: E402

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
"""


def find_tool():
    for tool in ("pandoc", "wkhtmltopdf"):
        if shutil.which(tool):
            return tool
    return None


def md_to_pdf(src: Path, dest: Path, tool: str) -> bool:
    dest.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile("w", suffix=".css", delete=False, encoding="utf-8") as f:
        f.write(CSS)
        css_path = f.name

    try:
        if tool == "pandoc":
            cmd = [
                "pandoc", str(src), "-o", str(dest),
                "--from", "markdown+pipe_tables+yaml_metadata_block+hard_line_breaks",
                "--pdf-engine", "wkhtmltopdf" if shutil.which("wkhtmltopdf") else "weasyprint",
                "--css", css_path,
            ]
        else:
            import markdown  # nur im Fallback noetig
            html_body = markdown.markdown(
                src.read_text(encoding="utf-8"), extensions=["tables", "fenced_code"]
            )
            html = f"<html><head><meta charset='utf-8'><style>{CSS}</style></head><body>{html_body}</body></html>"
            with tempfile.NamedTemporaryFile("w", suffix=".html", delete=False, encoding="utf-8") as hf:
                hf.write(html)
                html_path = hf.name
            cmd = ["wkhtmltopdf", "--quiet", "--encoding", "utf-8", html_path, str(dest)]

        result = subprocess.run(cmd, capture_output=True, text=True)
        if result.returncode != 0:
            print(f"  FEHLER bei {src.name}: {result.stderr.strip()[:200]}")
            return False
        return True
    except Exception as exc:  # noqa: BLE001
        print(f"  FEHLER bei {src.name}: {exc}")
        return False
    finally:
        Path(css_path).unlink(missing_ok=True)


def main():
    konsole_vorbereiten()
    parser = argparse.ArgumentParser(description="Markdown-Trainingsdokumente als PDF exportieren")
    parser.add_argument("pfad", nargs="?", default=None,
                        help="Datei oder Ordner (Standard: die Wurzel der Trainingsplanung)")
    parser.add_argument("-o", "--ausgabe", default=None, help="Ausgabeordner")
    args = parser.parse_args()

    tool = find_tool()
    if not tool:
        print("Weder pandoc noch wkhtmltopdf gefunden.")
        print("Installieren mit z.B.:  sudo apt install pandoc wkhtmltopdf")
        print("                 oder:  brew install pandoc wkhtmltopdf")
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

    print(f"Werkzeug: {tool} | {len(dateien)} Dokument(e) -> {ausgabe}/")
    ok = 0
    for src in dateien:
        rel = src.relative_to(basis) if src.is_relative_to(basis) else Path(src.name)
        dest = ausgabe / rel.with_suffix(".pdf")
        if md_to_pdf(src, dest, tool):
            print(f"  ok: {rel.with_suffix('.pdf')}")
            ok += 1
    print(f"Fertig: {ok}/{len(dateien)} exportiert.")


if __name__ == "__main__":
    main()
