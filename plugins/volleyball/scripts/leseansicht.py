#!/usr/bin/env python3
"""Macht aus einem Trainingsplan die Leseansicht fuers Handy.

    <python> leseansicht.py trainings/h1-h2/2026-09-15.md

Erzeugt die .html neben der .md. Die Ablauftabelle wird dabei bewusst NICHT
als Tabelle gerendert: sechs Spalten sind auf einem Handy in der Halle
unlesbar. Jede Zeile wird ein Block, den man mit dem Daumen abhaken kann.

Hat eine Uebung im Ablauf ein Schaubild auf ihrer Karte, landet es mit im
Block. Standardmaessig als Data-URI eingebettet, damit die Datei allein
lauffaehig ist und auch dann noch Bilder zeigt, wenn man sie sich aufs Handy
schickt. Das macht sie gross. Wer sie klein braucht, nimmt --bilder verweis,
dann steht ein relativer Pfad nach schaubilder/ drin.

Der Trainingsplan bleibt die Quelle. Die Leseansicht traegt oben das Datum
ihrer Erzeugung, damit man sieht, ob sie zur aktuellen Fassung passt. Wer in
die HTML tippt, verliert es beim naechsten Erzeugen.
"""

from __future__ import annotations

import argparse
import base64
import html
import mimetypes
import os
import re
import sys
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from tpdaten import (  # noqa: E402
    finde_wurzel, konsole_vorbereiten, lies_frontmatter, lies_uebungen,
)

CSS = """
:root{--bg:#fbfaf8;--fg:#1c1a17;--muted:#6b6560;--line:#e2ddd6;--akzent:#8a5a2b;
--karte:#fff;--warn:#8a2b2b}
@media (prefers-color-scheme:dark){:root{--bg:#171614;--fg:#ece8e2;--muted:#9a938c;
--line:#332f2a;--akzent:#d6a36b;--karte:#201e1b;--warn:#e08a8a}}
*{box-sizing:border-box}
body{margin:0;padding:16px;background:var(--bg);color:var(--fg);
font:17px/1.55 -apple-system,BlinkMacSystemFont,"Segoe UI",Roboto,sans-serif;
max-width:720px;margin-inline:auto;-webkit-text-size-adjust:100%}
h1{font-size:1.5rem;line-height:1.25;margin:0 0 4px}
h2{font-size:1.15rem;margin:32px 0 12px;padding-bottom:6px;border-bottom:1px solid var(--line)}
h3{font-size:1rem;margin:20px 0 8px}
.meta{color:var(--muted);font-size:.85rem;margin-bottom:24px}
.teil{background:var(--karte);border:1px solid var(--line);border-radius:12px;
padding:14px 16px;margin:10px 0}
.teil.an{border-left:4px solid var(--akzent)}
.kopf{display:flex;gap:10px;align-items:baseline;flex-wrap:wrap;margin-bottom:6px}
.zeit{font-variant-numeric:tabular-nums;font-weight:700;color:var(--akzent);white-space:nowrap}
.phase{color:var(--muted);font-size:.8rem;text-transform:uppercase;letter-spacing:.06em}
.name{font-weight:600;font-size:1.05rem;width:100%}
.id{font:.75rem ui-monospace,SFMono-Regular,Menlo,monospace;color:var(--muted)}
.zeile{margin-top:8px;font-size:.92rem}
.zeile b{color:var(--muted);font-weight:600;font-size:.78rem;text-transform:uppercase;
letter-spacing:.05em;display:block}
.warum{color:var(--muted);font-size:.88rem;font-style:italic}
.bild{margin-top:10px}
.bild img{display:block;width:100%;height:auto;border:1px solid var(--line);
border-radius:8px;background:#fff}
ul,ol{padding-left:22px}
li{margin:4px 0}
table{width:100%;border-collapse:collapse;font-size:.9rem;margin:12px 0;display:block;
overflow-x:auto}
th,td{border:1px solid var(--line);padding:7px 9px;text-align:left;vertical-align:top}
th{background:var(--karte)}
pre{background:var(--karte);border:1px solid var(--line);border-radius:8px;padding:12px;
overflow-x:auto;font-size:.78rem;line-height:1.35}
code{font-family:ui-monospace,SFMono-Regular,Menlo,monospace;font-size:.88em}
hr{border:0;border-top:1px solid var(--line);margin:28px 0}
.fuss{margin-top:40px;padding-top:12px;border-top:1px solid var(--line);
color:var(--muted);font-size:.8rem}
"""


def kein_bild(_uid: str) -> str:
    return ""


def baue_bildaufloeser(wurzel, ziel: Path, modus: str):
    """Gibt eine Funktion uid -> HTML-Schnipsel fuer das Schaubild zurueck.

    Faellt auf "kein Bild" zurueck, wenn die Karte keins traegt oder die Datei
    unter schaubilder/ fehlt. Eine Leseansicht ohne Bild ist brauchbar, eine
    mit totem Bildverweis nicht.
    """
    if modus == "aus" or wurzel is None:
        return kein_bild

    nach_id = {k["id"]: k for k in lies_uebungen(wurzel) if k.get("id")}

    def aufloesen(uid: str) -> str:
        karte = nach_id.get(uid)
        if not karte or not karte.get("schaubild"):
            return ""
        datei = wurzel / "schaubilder" / str(karte["schaubild"])
        if not datei.is_file():
            return ""
        if modus == "einbetten":
            typ = mimetypes.guess_type(datei.name)[0] or "image/png"
            roh = base64.b64encode(datei.read_bytes()).decode("ascii")
            quelle = f"data:{typ};base64,{roh}"
        else:
            quelle = Path(os.path.relpath(datei, ziel.parent)).as_posix()
        beschriftung = html.escape(f"Schaubild: {karte.get('titel') or uid}")
        return (f'<div class="bild"><img src="{quelle}" alt="{beschriftung}" '
                f'loading="lazy"></div>')

    return aufloesen


def inline(t: str) -> str:
    t = html.escape(t)
    t = re.sub(r"`([^`]+)`", r"<code>\1</code>", t)
    t = re.sub(r"\*\*([^*]+)\*\*", r"<strong>\1</strong>", t)
    t = re.sub(r"(?<!\*)\*([^*]+)\*(?!\*)", r"<em>\1</em>", t)
    t = re.sub(r"\[([^\]]+)\]\(([^)]+)\)", r'<a href="\2">\1</a>', t)
    return t.replace("&lt;br&gt;", "<br>")


def ablauf_bloecke(zeilen: list[str], bild=kein_bild) -> str:
    """Rendert die Ablauftabelle als Bloecke statt als breite Tabelle."""
    reihen = []
    for z in zeilen:
        if set(z.replace("|", "").strip()) <= set("-: "):
            continue
        felder = [f.strip() for f in z.strip().strip("|").split("|")]
        reihen.append(felder)
    if not reihen:
        return ""
    kopf = [k.lower() for k in reihen[0]]
    def idx(*namen):
        for n in namen:
            if n in kopf:
                return kopf.index(n)
        return None
    i_zeit, i_teil = idx("zeit"), idx("teil", "block")
    i_ue, i_id = idx("übung", "uebung"), idx("id")
    i_anp = idx("anpassung heute", "anpassung")
    i_warum = idx("warum hier", "begründung", "warum")

    raus = []
    for r in reihen[1:]:
        g = lambda i: r[i] if i is not None and i < len(r) else ""
        anp = g(i_anp).strip()
        uid = g(i_id).strip().strip("`")
        raus.append(f'<div class="teil{" an" if anp and anp != "—" else ""}">')
        raus.append('<div class="kopf">')
        if g(i_zeit):
            raus.append(f'<span class="zeit">{inline(g(i_zeit))}</span>')
        if g(i_teil):
            raus.append(f'<span class="phase">{inline(g(i_teil))}</span>')
        if g(i_ue):
            extra = f' <span class="id">{html.escape(uid)}</span>' if uid and uid != "—" else ""
            raus.append(f'<span class="name">{inline(g(i_ue))}{extra}</span>')
        raus.append("</div>")
        if anp and anp != "—":
            raus.append(f'<div class="zeile"><b>Heute</b>{inline(anp)}</div>')
        if g(i_warum).strip():
            raus.append(f'<div class="zeile warum">{inline(g(i_warum))}</div>')
        if uid and uid != "—":
            schnipsel = bild(uid)
            if schnipsel:
                raus.append(schnipsel)
        raus.append("</div>")
    return "\n".join(raus)


def nach_html(rumpf: str, bild=kein_bild) -> str:
    zeilen = rumpf.splitlines()
    raus, i = [], 0
    liste = None
    in_code = False
    code: list[str] = []
    in_ablauf = False

    def liste_zu():
        nonlocal liste
        if liste:
            raus.append(f"</{liste}>")
            liste = None

    while i < len(zeilen):
        z = zeilen[i]

        if z.strip().startswith("```"):
            if in_code:
                raus.append("<pre>" + html.escape("\n".join(code)) + "</pre>")
                code, in_code = [], False
            else:
                liste_zu()
                in_code = True
            i += 1
            continue
        if in_code:
            code.append(z)
            i += 1
            continue

        if z.strip().startswith("|"):
            block = []
            while i < len(zeilen) and zeilen[i].strip().startswith("|"):
                block.append(zeilen[i])
                i += 1
            liste_zu()
            if in_ablauf:
                raus.append(ablauf_bloecke(block, bild))
                in_ablauf = False
            else:
                raus.append("<table>")
                for n, zz in enumerate(block):
                    if set(zz.replace("|", "").strip()) <= set("-: "):
                        continue
                    tag = "th" if n == 0 else "td"
                    felder = [f.strip() for f in zz.strip().strip("|").split("|")]
                    raus.append("<tr>" + "".join(f"<{tag}>{inline(f)}</{tag}>" for f in felder) + "</tr>")
                raus.append("</table>")
            continue

        m = re.match(r"^(#{1,4})\s+(.*)$", z)
        if m:
            liste_zu()
            stufe = len(m.group(1))
            titel = m.group(2).strip()
            in_ablauf = stufe == 2 and titel.lower().startswith("ablauf")
            if stufe > 1:
                raus.append(f"<h{stufe}>{inline(titel)}</h{stufe}>")
            i += 1
            continue

        m = re.match(r"^\s*[-*]\s+(.*)$", z)
        if m:
            if liste != "ul":
                liste_zu()
                raus.append("<ul>")
                liste = "ul"
            raus.append(f"<li>{inline(m.group(1))}</li>")
            i += 1
            continue

        m = re.match(r"^\s*(\d+)\.\s+(.*)$", z)
        if m:
            if liste != "ol":
                liste_zu()
                raus.append("<ol>")
                liste = "ol"
            raus.append(f"<li>{inline(m.group(2))}</li>")
            i += 1
            continue

        if z.strip() in ("---", "___"):
            liste_zu()
            raus.append("<hr>")
            i += 1
            continue

        if z.strip():
            liste_zu()
            raus.append(f"<p>{inline(z.strip())}</p>")
        i += 1

    liste_zu()
    return "\n".join(raus)


def main() -> int:
    konsole_vorbereiten()
    ap = argparse.ArgumentParser(description="Leseansicht eines Trainingsplans erzeugen")
    ap.add_argument("plan", type=Path, help="Pfad zur Trainings-.md")
    ap.add_argument("--out", type=Path, default=None)
    ap.add_argument("--bilder", choices=["einbetten", "verweis", "aus"],
                    default="einbetten",
                    help="Schaubilder der Uebungen einbetten (Standard, die HTML "
                         "laeuft dann allein), als relativen Verweis setzen, oder "
                         "weglassen")
    a = ap.parse_args()

    plan = a.plan.resolve()
    if not plan.is_file():
        raise SystemExit(f"Nicht gefunden: {plan}")

    ziel = a.out or plan.with_suffix(".html")
    try:
        wurzel = finde_wurzel(plan.parent)
    except SystemExit:
        # Leseansicht soll auch fuer eine .md ausserhalb der Bibliothek laufen,
        # dann eben ohne Schaubilder.
        wurzel = None
    bild = baue_bildaufloeser(wurzel, ziel, a.bilder)

    fm, rumpf = lies_frontmatter(plan)
    titel = next((z[2:].strip() for z in rumpf.splitlines() if z.startswith("# ")), plan.stem)

    meta = []
    for schl, beschriftung in (("gruppe", ""), ("teilnehmer", "Teilnehmer"),
                               ("dauer", "Minuten"), ("spielflaechen", "Spielflächen")):
        if fm.get(schl) is not None:
            meta.append(f"{fm[schl]} {beschriftung}".strip())
    erzeugt = datetime.now().strftime("%d.%m.%Y %H:%M")

    doc = f"""<!DOCTYPE html>
<html lang="de"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>{html.escape(titel)}</title><style>{CSS}</style></head><body>
<h1>{html.escape(titel)}</h1>
<div class="meta">{html.escape(" · ".join(meta))}</div>
{nach_html(rumpf, bild)}
<div class="fuss">Leseansicht, erzeugt am {erzeugt} aus <code>{html.escape(plan.name)}</code>.<br>
Änderungen gehören in die Markdown-Datei, hier gehen sie beim nächsten Erzeugen verloren.</div>
</body></html>"""

    ziel.write_text(doc, encoding="utf-8")
    print(f"Leseansicht: {ziel}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
