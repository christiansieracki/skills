#!/usr/bin/env python3
"""Zeichnet aus einer Szene ein Schaubild als SVG.

    <python> schaubild.py ue-0042                       # schaubilder/ue-0042.szene.yml
    <python> schaubild.py schaubilder/ue-0042.szene.yml
    <python> schaubild.py ue-0042 --wurzel <pfad>

Die Szene ist die Quelle, das SVG ist das Erzeugnis (ADR-0004). Beide liegen
unter demselben Basisnamen in `schaubilder/`, damit eine Korrektur ein halbes
Jahr spaeter drei Zeilen kostet statt einer Neuzeichnung. Wer in das SVG
tippt, verliert es beim naechsten Erzeugen, genau wie bei der Leseansicht.

Gerechnet wird in der Szene durchgehend in Metern. Die Umrechnung in
Zeichenkoordinaten passiert allein hier, an einer Stelle: nur so stimmt ein
eingezeichneter Abstand mit dem ueberein, was in der Halle abgeschritten wird.

Geschrieben wird erst, wenn das ganze Bild steht. Eine Szene, die nicht
aufgeht, hinterlaesst deshalb kein halbes SVG, sondern eine Meldung und die
Datei von vorher.

Nur Standardbibliothek, wie alles im Plugin ausser der Bildaufbereitung.
"""

from __future__ import annotations

import argparse
import html
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from szene import Ort, Szene, SzeneFehler, Weg, lies_szene, scheitel  # noqa: E402
from tpdaten import finde_wurzel, konsole_vorbereiten  # noqa: E402

# Zeicheneinheiten je Meter. Die Zahl steht genau einmal im Plugin; alles
# andere rechnet in Metern und geht durch Blatt.
MASSSTAB = 30.0

# Mindestrand um das Feld, in Metern. Darin steht, was neben dem Feld liegt:
# Netzpfosten, Beschriftungen, spaeter Titel und Legende.
RAND = 1.5

# Luft um einen Punkt ausserhalb des Feldes. Ein Aufschlagspieler hinter der
# Grundlinie soll ganz im Bild stehen, nicht halb angeschnitten.
LUFT = 0.8

# Radius eines Spielermarkers in Metern. Knapp ein Meter Durchmesser: so gross
# wie ein Mensch von oben Platz braucht, und damit massstaeblich statt geraten.
MARKER = 0.45

# Die Farben. Zwei Saetze derselben Namen, einer je Schema, damit das Bild in
# einer hellen wie in einer dunklen Leseansicht lesbar bleibt. Die Werte sind
# die aus leseansicht.py, damit Schaubild und Blatt nicht zwei Handschriften
# haben.
HELL = {
    "papier": "#fbfaf8",
    "feld": "#ffffff",
    "strich": "#1c1a17",
    "gedaempft": "#6b6560",
    "laufweg": "#8a5a2b",
    "ballweg": "#2b5a8a",
}
DUNKEL = {
    "papier": "#171614",
    "feld": "#201e1b",
    "strich": "#ece8e2",
    "gedaempft": "#9a938c",
    "laufweg": "#d6a36b",
    "ballweg": "#7fb0dd",
}


# --------------------------------------------------------------------------
# Vom Meter zur Zeicheneinheit
# --------------------------------------------------------------------------

class Blatt:
    """Rechnet Meter in Zeichenkoordinaten um.

    Die Szene sieht das Feld von oben: x waechst nach rechts, y zur Gegenseite
    hin. Im SVG waechst y nach unten, deshalb wird es hier gespiegelt. Wer
    diesen Umstand vergisst, zeichnet ein Bild, in dem die Aufschlagposition
    vorn am Netz steht.
    """

    def __init__(self, links: float, unten: float, rechts: float, oben: float) -> None:
        self._links, self._oben = links, oben
        self.breite = (rechts - links) * MASSSTAB
        self.hoehe = (oben - unten) * MASSSTAB

    def x(self, meter: float) -> float:
        return (meter - self._links) * MASSSTAB

    def y(self, meter: float) -> float:
        return (self._oben - meter) * MASSSTAB

    def laenge(self, meter: float) -> float:
        return meter * MASSSTAB


def grenzen(s: Szene) -> tuple[float, float, float, float]:
    """Der Ausschnitt in Metern: das Feld mit Rand, erweitert um alles Weitere."""
    xs = [-RAND, s.vorlage.breite + RAND]
    ys = [-RAND, s.vorlage.laenge + RAND]
    for x, y in s.punkte():
        xs += [x - LUFT, x + LUFT]
        ys += [y - LUFT, y + LUFT]
    return min(xs), min(ys), max(xs), max(ys)


def koord(wert: float) -> str:
    """Eine Zeichenkoordinate so kurz wie moeglich, ohne Genauigkeit zu verlieren."""
    text = f"{wert:.2f}".rstrip("0").rstrip(".")
    return "0" if text in ("", "-0") else text


# --------------------------------------------------------------------------
# Die Teile des Bildes
# --------------------------------------------------------------------------

def farbblock(auswahl: dict[str, str]) -> str:
    return "svg{" + "".join(f"--{k}:{v};" for k, v in auswahl.items()).rstrip(";") + "}"


def stil() -> str:
    """Das Stylesheet des Bildes, mit beiden Farbschemata.

    Die Farben stehen als Variablen da und nicht an den Formen, damit ein
    zweites Schema nichts kostet ausser sechs Zeilen. `currentColor` waere die
    andere Moeglichkeit, taugt hier aber nicht: die Leseansicht bettet das Bild
    als `<img>` ein, und darin gibt es keine Elternfarbe, die faerben koennte.
    """
    return (
        farbblock(HELL)
        + "@media (prefers-color-scheme:dark){" + farbblock(DUNKEL) + "}"
        + ".papier{fill:var(--papier)}"
        + ".feld{fill:var(--feld);stroke:var(--strich);stroke-width:2.4}"
        + ".linie{fill:none;stroke:var(--strich);stroke-width:1.4}"
        + ".netz{fill:none;stroke:var(--gedaempft);stroke-width:1.4;stroke-dasharray:7 5}"
        + ".marker{fill:var(--feld);stroke:var(--strich);stroke-width:1.8}"
        + ".beschriftung{fill:var(--strich);font-family:"
          "-apple-system,BlinkMacSystemFont,'Segoe UI',Roboto,sans-serif;"
          "font-weight:600;text-anchor:middle;dominant-baseline:central}"
        + ".weg{fill:none;stroke-width:2.6;stroke-linecap:round}"
        + ".laufweg{stroke:var(--laufweg)}"
        + ".ballweg{stroke:var(--ballweg);stroke-dasharray:9 6}"
    )


def spitzen() -> str:
    """Je Wegart eine Pfeilspitze.

    Zwei statt einer, weil eine SVG-Markierung die Strichfarbe ihres Pfades
    nicht erbt. Eine gemeinsame Spitze haette am Ballweg die Farbe des
    Laufwegs.
    """
    teile = ["<defs>"]
    for art in ("laufweg", "ballweg"):
        teile.append(
            f'<marker id="spitze-{art}" viewBox="0 0 10 10" refX="9" refY="5" '
            f'markerWidth="4.5" markerHeight="4.5" orient="auto-start-reverse">'
            f'<path d="M0 0 L10 5 L0 10 Z" fill="var(--{art})"/></marker>'
        )
    teile.append("</defs>")
    return "".join(teile)


def feld(s: Szene, blatt: Blatt) -> str:
    """Die Feldvorlage: Rand, Mittellinie, Angriffslinien, Netz.

    Gezeichnet wird nur, was die Vorlage kennt. Im Sand gibt es weder
    Angriffs- noch Mittellinie, und eine Linie im Bild, die es draussen nicht
    gibt, ist eine Ansage, die niemand einhalten kann.
    """
    v = s.vorlage
    teile = [f'<g class="feldvorlage {v.name}">']
    teile.append(
        f'<rect class="feld" x="{koord(blatt.x(0))}" y="{koord(blatt.y(v.laenge))}" '
        f'width="{koord(blatt.laenge(v.breite))}" height="{koord(blatt.laenge(v.laenge))}"/>'
    )

    def quer(klasse: str, bei: float) -> str:
        return (f'<line class="{klasse}" x1="{koord(blatt.x(0))}" y1="{koord(blatt.y(bei))}" '
                f'x2="{koord(blatt.x(v.breite))}" y2="{koord(blatt.y(bei))}"/>')

    if v.mittellinie:
        teile.append(quer("linie mittellinie", v.netz))
    for bei in v.angriffslinien_bei:
        teile.append(quer("linie angriffslinie", bei))

    # Das Netz ist ein Band um die Mittellinie herum, keine Linie darauf. So
    # bleibt in der Halle die Mittellinie darunter sichtbar, und im Sand sieht
    # man auf einen Blick, dass da keine ist.
    band = 0.3
    teile.append(
        f'<rect class="netz" x="{koord(blatt.x(0))}" y="{koord(blatt.y(v.netz + band / 2))}" '
        f'width="{koord(blatt.laenge(v.breite))}" height="{koord(blatt.laenge(band))}"/>'
    )
    teile.append("</g>")
    return "".join(teile)


def steuerpunkt(von: Ort, nach: Ort, bogen: float) -> Ort | None:
    """Der Steuerpunkt der Kurve, oder None fuer einen geraden Weg.

    Er liegt doppelt so weit neben der Mitte der Sehne wie der Scheitel, denn
    eine quadratische Bezierkurve kommt ihrem Steuerpunkt nur halb entgegen.
    Wo der Scheitel liegt, sagt die Szene; wer den Faktor hier weglaesst,
    zeichnet einen Bogen von halber Hoehe, und dann stimmt am Bild etwas nicht,
    was niemand benennen kann.
    """
    if not bogen:
        return None
    sx, sy = scheitel(von, nach, bogen)
    return (2 * sx - (von[0] + nach[0]) / 2, 2 * sy - (von[1] + nach[1]) / 2)


def _geschoben(punkt: Ort, ziel: Ort, strecke: float) -> Ort:
    """Schiebt `punkt` um `strecke` Meter auf `ziel` zu."""
    dx, dy = ziel[0] - punkt[0], ziel[1] - punkt[1]
    laenge = (dx * dx + dy * dy) ** 0.5
    if laenge == 0:
        return punkt
    return (punkt[0] + dx / laenge * strecke, punkt[1] + dy / laenge * strecke)


def enden(weg: Weg, besetzt: list[Ort]) -> tuple[Ort, Ort, Ort | None]:
    """Laesst einen Weg am Rand eines Markers anfangen und aufhoeren.

    Ein Pfeil, der in der Mitte eines Spielers endet, verliert seine Spitze
    unter dessen Marker, und damit das Einzige, was die Richtung zeigt. Also
    hoert der Weg am Kreisrand auf, mit etwas Luft davor.

    Gekuerzt wird entlang der Tangente, bei einer Kurve also zum Steuerpunkt
    hin. Zur Sehne hin gekuerzt rutschte der Anfang eines stark gebogenen Weges
    sichtbar neben die Kurve.

    Der Steuerpunkt wird danach neu gesetzt, aus den gekuerzten Enden. Bliebe
    der alte stehen, waere die Pfeilhoehe des gezeichneten Bogens eine andere
    als die angesagte, sobald ein Ende auf einem Spieler liegt. `bogen` ist ein
    Mass und muss auch dann nachmessbar bleiben.
    """
    von, nach = weg.von, weg.nach
    steuer = steuerpunkt(von, nach, weg.bogen)
    dx, dy = nach[0] - von[0], nach[1] - von[1]
    # Nie mehr als ein Drittel je Seite: ein kurzer Weg zwischen zwei
    # Nachbarpositionen soll schrumpfen, nicht sich umdrehen.
    strecke = min(MARKER + 0.15, (dx * dx + dy * dy) ** 0.5 / 3)
    if any(trifft(von, p) for p in besetzt):
        von = _geschoben(von, steuer or nach, strecke)
    if any(trifft(nach, p) for p in besetzt):
        nach = _geschoben(nach, steuer or von, strecke)
    return von, nach, steuerpunkt(von, nach, weg.bogen)


def trifft(a: Ort, b: Ort) -> bool:
    """Ob zwei Punkte derselbe Ort sind, auf fuenf Zentimeter genau."""
    return abs(a[0] - b[0]) < 0.05 and abs(a[1] - b[1]) < 0.05


def pfad(weg: Weg, blatt: Blatt, besetzt: list[Ort]) -> str:
    """Ein Weg, gerade oder gekruemmt, mit Pfeilspitze am Ende."""
    (x0, y0), (x1, y1), steuer = enden(weg, besetzt)
    anfang = f"M{koord(blatt.x(x0))} {koord(blatt.y(y0))}"
    if steuer:
        mitte = f"Q{koord(blatt.x(steuer[0]))} {koord(blatt.y(steuer[1]))} "
    else:
        mitte = "L"
    ende = f"{koord(blatt.x(x1))} {koord(blatt.y(y1))}"
    return (f'<path class="weg {weg.art}" d="{anfang} {mitte}{ende}" '
            f'marker-end="url(#spitze-{weg.art})"/>')


def marker(s: Szene, blatt: Blatt) -> str:
    """Die Spielermarker samt Beschriftung.

    Die Schrift schrumpft, sobald mehr als zwei Zeichen im Kreis stehen. Ein
    Kuerzel, das ueber den Rand laeuft, ist schlechter zu lesen als ein
    kleiner gesetztes.
    """
    teile = []
    for spieler in s.spieler:
        mx, my = blatt.x(spieler.x), blatt.y(spieler.y)
        teile.append('<g class="spieler">')
        teile.append(f'<circle class="marker" cx="{koord(mx)}" cy="{koord(my)}" '
                     f'r="{koord(blatt.laenge(MARKER))}"/>')
        if spieler.text:
            groesse = 15 if len(spieler.text) <= 2 else 11
            teile.append(f'<text class="beschriftung" x="{koord(mx)}" y="{koord(my)}" '
                         f'font-size="{groesse}">{html.escape(spieler.text)}</text>')
        teile.append("</g>")
    return "".join(teile)


def zeichne(s: Szene) -> str:
    """Das ganze Bild als SVG-Text, in einem Stueck."""
    blatt = Blatt(*grenzen(s))
    teile = [
        f'<svg xmlns="http://www.w3.org/2000/svg" '
        f'viewBox="0 0 {koord(blatt.breite)} {koord(blatt.hoehe)}" '
        f'width="{koord(blatt.breite)}" height="{koord(blatt.hoehe)}" role="img">',
        f"<style>{stil()}</style>",
        spitzen(),
        '<rect class="papier" x="0" y="0" width="100%" height="100%"/>',
        feld(s, blatt),
    ]
    # Wege unter die Marker: ein Pfeil, der einen Spieler streift, soll nicht
    # quer durch sein Kuerzel laufen. Wer auf einem Spieler anfaengt oder
    # aufhoert, wird dafuer bis an dessen Kreisrand gekuerzt.
    besetzt = [(spieler.x, spieler.y) for spieler in s.spieler]
    teile.extend(pfad(weg, blatt, besetzt) for weg in s.wege)
    teile.append(marker(s, blatt))
    teile.append("</svg>")
    return "".join(teile) + "\n"


# --------------------------------------------------------------------------
# Die Dateien
# --------------------------------------------------------------------------

ENDUNG = ".szene.yml"


def finde_szene(angabe: str, wurzel: Path) -> Path:
    """Findet die Szenendatei zu dem, was auf der Kommandozeile stand.

    Erlaubt ist beides: der Pfad zur Datei und der blosse Basisname, wie er
    auch im Feld `schaubild:` steht. Der Basisname ist der haeufigere Fall,
    weil der Zeichen-Skill von einer Uebungs-ID kommt.
    """
    kandidat = Path(angabe)
    if kandidat.suffix not in (".yml", ".yaml"):
        kandidat = kandidat.with_name(kandidat.name + ENDUNG)
    if kandidat.is_absolute():
        return kandidat
    # Ein blosser Name ohne Ordner meint schaubilder/, dort gehoeren Szenen hin.
    if kandidat.parent == Path("."):
        kandidat = Path("schaubilder") / kandidat
    return wurzel / kandidat


def ziel(quelle: Path) -> Path:
    """Das SVG liegt neben der Szene, unter demselben Basisnamen.

    Der Basisname ist der Dateiname ohne `.yml` beziehungsweise `.yaml` und
    ohne das `.szene` davor. Eine Regel statt einer Liste von Schreibweisen:
    `ue-0042.szene.yml` und `ue-0042.szene.yaml` ergeben beide `ue-0042.svg`.
    """
    stamm = quelle.with_suffix("").name
    if stamm.endswith(".szene"):
        stamm = stamm[: -len(".szene")]
    return quelle.with_name(stamm + ".svg")


def main() -> int:
    konsole_vorbereiten()
    ap = argparse.ArgumentParser(
        description="Aus einer Szene ein Schaubild als SVG zeichnen")
    ap.add_argument("szene",
                    help="Szenendatei oder Basisname, dann unter schaubilder/ "
                         "gesucht (etwa ue-0042)")
    ap.add_argument("--wurzel", type=Path, default=None)
    a = ap.parse_args()

    wurzel = a.wurzel.resolve() if a.wurzel else finde_wurzel()
    quelle = finde_szene(a.szene, wurzel)
    if not quelle.is_file():
        print(f"Keine Szene unter {quelle}")
        print("Eine Szene heisst <basisname>.szene.yml und liegt in schaubilder/,")
        print("neben dem Bild, das aus ihr entsteht.")
        return 1

    try:
        bild = zeichne(lies_szene(quelle.read_text(encoding="utf-8")))
    except SzeneFehler as fehler:
        # Erst rendern, dann schreiben: eine Szene, die nicht aufgeht, laesst
        # das Bild von vorher heil liegen, statt es halb zu ersetzen.
        print(f"{quelle.name}: {fehler}")
        print("Es wurde nichts geschrieben.")
        return 1

    datei = ziel(quelle)
    datei.parent.mkdir(parents=True, exist_ok=True)
    datei.write_text(bild, encoding="utf-8")
    print(f"Geschrieben: {datei}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
