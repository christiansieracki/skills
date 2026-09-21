---
name: volleyball-schaubild
description: Zeichnet ein Schaubild zu einer Volleyball-Übung. Aus einer Szene in YAML entsteht ein SVG, das der Trainer ansieht, mit einem Satz nachschärft und freigibt; erst dann wird es geschrieben. Findet die Karten ohne Bild selbst. Use when the user wants a Schaubild, Feldskizze or diagram for a volleyball drill, wants an existing one corrected or redrawn, or asks which Übungskarten still have no picture. Companion zu volleyball-uebungsimport und volleyball-trainingsdesign.
---

# Schaubild

Ein Bild entsteht in Runden: rendern, zeigen, nachschärfen, freigeben. Nach
`schaubilder/` geschrieben wird erst, was der Trainer freigegeben hat.

Beurteilt wird das Bild im Dialog. `schaubild.py` gibt SVG zurück, und im
Markup steht nicht, ob ein Marker das Wort einer Zone verdeckt.

## Zuerst

`<python>` heißt `python3`, unter Windows `python`. Schlägt der eine fehl,
nimm den anderen.

1. `<python> ${CLAUDE_PLUGIN_ROOT}/scripts/index.py`. Das gibt die Wurzel und
   alles, was in der Bibliothek gerade nicht stimmt. Findet es keine
   `trainingsplanung-root.yml`, fragen wo der Ordner liegt.
2. `${CLAUDE_PLUGIN_ROOT}/referenzen/SCHAUBILDER.md` lesen. Dort steht, wie
   eine Szene aufgebaut ist: die elf Schlüssel, die drei Grundformen, wie ein
   Ort angegeben wird. Was dort nicht steht, gibt es nicht.
3. Aus `${CLAUDE_PLUGIN_ROOT}/referenzen/DATENMODELL.md` den Abschnitt über
   Schaubild und Szene lesen. Dort steht, was am Ende auf der Karte landet.
4. `${CLAUDE_PLUGIN_ROOT}/referenzen/SPRACHE.md` und die `glossary.md` der
   Wurzel lesen, bevor Titel, Legende und Fußzeile entstehen. Auch die paar
   Zeilen neben dem Feld sind Text im Ordner.

Alle Aufrufe hier laufen aus dem Arbeitsordner heraus. Von woanders aus
bekommt jedes Skript die Wurzel als `--wurzel <pfad>` mit, auch wenn die Szene
selbst mit vollem Pfad dasteht.

## Wofür ein Bild entsteht

| Der Trainer nennt | Vorgehen |
|---|---|
| eine Übungskarte, etwa `ue-0042` | `<python> ${CLAUDE_PLUGIN_ROOT}/scripts/suche.py --id ue-0042 --lang` |
| eine Übung ohne ID | mit `suche.py --text <stück des titels>` finden, bei mehreren Treffern fragen |
| nichts Bestimmtes | Kandidaten suchen, siehe unten |

Der Ablauf steht in der Kartendatei und nicht in der Trefferzeile. Wo sie
liegt, sagt `suche.py --lang` in der Zeile `Datei`.

## Kandidaten finden

```
<python> ${CLAUDE_PLUGIN_ROOT}/scripts/suche.py --json
```

Kandidat ist eine Karte, deren `schaubild` leer ist und deren Ablauf räumlich
ist: eine Aufstellung, Laufwege, eine Zielzone, ein Stationsaufbau.

Vorsortiert wird an den Feldern, die schon im JSON stehen: `form: station` und
`form: spielform`, ein gefülltes `material`, Elemente wie annahme, block oder
angriff. Ob der Ablauf wirklich räumlich ist, steht in der Kartendatei, und
die liest du für die, die danach übrig bleiben. `datei` sagt, wo sie liegt.

Die Liste entsteht bei jedem Lauf neu und wird nirgends mitgeschrieben. So
weiß auch eine frische Sitzung, was offen ist, selbst wenn in der Zwischenzeit
jemand von Hand ein Bild ergänzt hat.

Vorgelegt wird eine Zeile je Kandidat:

| ID | Titel | Was das Bild zeigen würde |
|---|---|---|
| ue-0042 | Annahme-Zielzone | Aufschlagrichtung, Zielzone, die drei Annahmespieler |

Der Trainer wählt aus, womit angefangen wird.

## Die Szene entwerfen

Die Szene kommt aus der Karte. Was dort nicht steht, wird gefragt. Ein Spieler
an einer geratenen Stelle steht in der Halle falsch.

| Auf der Karte | In der Szene |
|---|---|
| `disziplin` | `form: halle` oder `form: beach` |
| im Ablauf: wer wo steht | `spieler` |
| im Ablauf: wer wohin läuft, wohin der Ball geht | `wege` |
| im Ablauf: wohin gezielt wird | `zonen` |
| im Ablauf: Abstände, die in der Halle abgeschritten werden | `abstaende` |
| `material` | `geraete` |
| `titel` der Karte | `titel`, wo das Bild für sich steht |
| Ziel und Wertung, in kurzen Zeilen | `legende` |
| `quelle` | `fusszeile` |

Trägt die Karte `[halle, beach]`, fragen, für welches Feld das Bild gilt. Ein
Bild zeigt ein Feld.

Der Entwurf liegt im Temp-Verzeichnis der Sitzung, außerhalb des
Arbeitsordners, und trägt schon den Basisnamen, den er später tragen soll:
`ue-0042.szene.yml`. Die Freigabe kostet damit ein Kopieren.

## Die Schleife

Eine Runde hat vier Schritte. Sie ist vorbei, wenn der Trainer freigibt oder
sagt, was anders soll.

**Rendern.**

```
<python> ${CLAUDE_PLUGIN_ROOT}/scripts/schaubild.py <entwurf>.szene.yml
```

Der Pfad zur Entwurfsszene, ganz ausgeschrieben. Das Bild entsteht daneben,
unter demselben Basisnamen.

Geht die Szene nicht auf, steht der Grund in der Meldung. Die genannte Zeile
ändern und neu rendern. Gezeigt wird das Bild, das aus der geänderten Szene
entstanden ist.

**Zeigen.** Mit dem, was die Umgebung hergibt: eine Bildvorschau, ein
Werkzeug, das Dateien anzeigt, ein Fenster. Dazu zwei, drei Zeilen, was in
dieser Runde drinsteht oder sich geändert hat.

Zeigt die Umgebung nichts an, den Pfad zur SVG-Datei nennen und weitermachen.
Der Trainer öffnet sie selbst, die Schleife läuft genauso.

**Nachschärfen.** Der Satz des Trainers ändert die Szene, an den Zeilen, um
die es geht: ein Spieler zu weit links sind zwei Zahlen, eine fehlende
Erklärung ist eine Zeile mehr in der Legende. Die Entwurfsdatei bleibt
dieselbe. Wer sie neu schreibt, nimmt alles andere mit, und die Runde davor
war umsonst.

Passt der Wunsch in keinen Schlüssel aus `SCHAUBILDER.md`, sag das und schlag
vor, was das Vokabular hergibt. Ein erfundener Schlüssel bricht beim Rendern
ohnehin ab.

Danach zurück zum Rendern.

**Freigeben.** Der Trainer sagt, dass das Bild passt.

## Freigeben und nachtragen

Vier Schritte, in dieser Reihenfolge:

1. Die Entwurfsszene nach `schaubilder/<basisname>.szene.yml` schreiben.
2. `<python> ${CLAUDE_PLUGIN_ROOT}/scripts/schaubild.py <basisname>`. Jetzt
   liegt das Bild in `schaubilder/`, neben seiner Szene.
3. Auf der Karte `schaubild: <basisname>.svg` eintragen. Dort steht der
   Dateiname des Bildes, nicht der Szene.
4. `<python> ${CLAUDE_PLUGIN_ROOT}/scripts/index.py` laufen lassen. Zeigt der
   Verweis ins Leere, meldet er ihn.

Gehört das Bild zu einem Trainingsabend und zu keiner Übung, heißt es nach
Datum und Thema, etwa `2026-09-15-annahme-zielzone`, und Schritt 3 entfällt.

## Eine Karte, die schon ein Bild hat

Liegt neben dem Bild eine `<basisname>.szene.yml`, ist sie der Anfang des
Entwurfs: kopieren, die paar Zeilen ändern, damit in die Schleife. Genau dafür
liegt sie da.

Gibt es keine Szene, ist das Bild älter als die Szenen oder aus einer Quelle
ausgeschnitten. Es bleibt liegen, solange der Trainer es nicht ausdrücklich
neu haben will. Will er es, sag vorher, dass ein neues Bild an seine Stelle
tritt und dabei auf der Karte der Dateiname wechselt.

## Mehrere Bilder

Eins nach dem anderen, jedes durch die ganze Schleife. Das nächste fängt nach
einer Freigabe an. Nach jedem Bild sagen, wie viele der gewählten Karten noch
offen sind.

Fünfzehn Bilder sind eine Sitzung für sich, und die kann eng werden. Dann die
IDs der offenen Karten nennen und Schluss machen. Die nächste Sitzung findet
sie über dieselbe Suche wieder, weil auf ihnen noch kein `schaubild:` steht.

## Was der Trainer am Ende hört

Welche Bilder entstanden sind und unter welchen Dateinamen, auf welchen Karten
`schaubild:` jetzt steht, und was du aus dem Ablauf gedeutet hast, wo er nicht
eindeutig war. Dazu die Karten, die offen geblieben sind.
