# Die Szene ist die Quelle, das SVG ist das Erzeugnis

Schaubilder entstehen nicht mehr freihändig als SVG-Markup, sondern aus einer
**Szenenbeschreibung** in YAML, die ein Skript zu SVG rendert. Die Szene wird
neben dem Bild abgelegt, unter demselben Basisnamen: `ue-0042.szene.yml` und
`ue-0042.svg`. Die Szene rechnet durchgehend **in Metern**; eine Feldvorlage
(Halle 9×18, Beach 8×16) ist dabei nur eine mögliche Grundform unter anderen,
kein Sonderfall.

Ausschlaggebend war die Vorschau-Schleife, für die dieser Ast gebaut wird: Der
Trainer sieht das erzeugte Bild im Dialog und schärft es sprachlich nach. Das
verlangt eine Darstellung, die man *ändern* kann. Ein Aufruf mit
Kommandozeilenflags ist zustandslos und muss jede Runde neu zusammengesetzt
werden; eine Szenendatei wird an drei Zeilen angefasst und neu gerendert — auch
noch in einer späteren Sitzung, Monate danach.

Der Ordner kennt dieses Muster bereits: die Markdown-Datei ist die Quelle, die
Leseansicht wird beim nächsten Mal überschrieben. Das Schaubild reiht sich
darin ein.

## Considered Options

- **Schmales Vokabular aus Kommandozeilenflags** (`--spieler`, `--ballweg`).
  Verworfen am Bestand: das vorhandene Schaubild `2026-09-15-annahme-zielzone.svg`
  enthält Bézier-Ballwege, einen frei gezeichneten Ballwagen auf dem Kasten und
  eine Legendenspalte mit vier Blöcken. Ein Flag-Vokabular hätte dieses Bild nicht
  erzeugen können — und es ist der Qualitätsstand, der schon erreicht ist.
- **Zwei getrennte Modi**, einer fürs Feld und einer für freie Formen. Verworfen,
  weil beide dieselben Formen zweimal beschrieben hätten. Der Stationsbetrieb
  braucht keine zweite Geometrie: er wird, wo er hineinpasst, in ein volles Feld
  gezeichnet, und der Maßstab ergibt sich dann von selbst.
- **Weiter freihändig zeichnen.** Verworfen, weil das Ergebnis pro Lauf anders
  ausfällt und sich der Prüfvertrag aus Welle 1a — „was auf der Kommandozeile
  grün ist, gilt" — nicht darauf anwenden lässt.

## Consequences

Geprüft wird die **Geometrie**, nicht das Markup: das erzeugte SVG wird mit
`xml.etree` geparst und auf Verhältnisse zugesichert (hat das Beachfeld 8×16 und
nicht Hallenproportionen, liegt ein Marker für Position 4 im richtigen Drittel,
ist eine 6-Meter-Maßkette ein Drittel der Feldlänge lang). Goldene Referenzdateien
wären das Gegenteil davon: sie würden jede Farbkorrektur rot färben und damit
genau die Änderbarkeit aufheben, für die die Trennung da ist.

Ob ein Abstand als Maßkette oder als beschrifteter Pfeil erscheint, bleibt eine
Darstellungsentscheidung pro Bild. Beides steht im Vokabular; welches
übersichtlicher ist, hängt am Anwendungsfall und wird nicht im Datenmodell
vorentschieden.
