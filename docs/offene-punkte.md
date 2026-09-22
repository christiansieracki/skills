# Offene Punkte

Was bei der Arbeit aufgefallen ist und noch kein Ticket hat. Der Tracker sind
die GitHub-Issues in `christiansieracki/skills`, siehe
`docs/agents/issue-tracker.md`. Diese Datei ist die Stufe davor: hier steht,
was jemand beim nächsten Schnitt aufgreifen soll, mit genug Zusammenhang, um
daraus ein Ticket zu machen.

Ein Punkt verschwindet hier, sobald er ein Ticket hat oder erledigt ist.

## Aus der Abnahme am Volleyball-Magazin (#18)

Die Abnahme von Welle 1b ist durch. Fünf Dinge sind dabei liegen geblieben.

### Das Szenen-Vokabular kennt keine Beschriftung am Feld

Das handgezeichnete `2026-09-15-annahme-zielzone.svg` beschriftete zwei Linien
mit „Netz" und „3-m-Linie". Die Nachbildung aus einer Szene kann das nicht:
Text trägt nur, wer eine Fläche hat (eine Zone) oder ein Gegenstand ist (ein
Gerät). Ein Wort an eine Stelle des Feldes zu setzen geht nicht.

Für die beiden genannten Linien ist das verschmerzbar, das Netzband und die
Angriffslinie erkennt ein Trainer. Es fehlt aber überall dort, wo eine Stelle
einen Namen braucht, ohne dass dort etwas steht: der Punkt, an dem der Trainer
anwirft, die Ecke, in die aufgeschlagen wird.

Zu entscheiden wäre, ob es dafür einen zwölften Schlüssel gibt oder ob eine
Zone ohne Füllung reicht.

### `fusszeile` trägt eine Zeile, das Original hatte drei

Die Fußzeile des Referenzbildes bestand aus drei Sätzen: der Zeichenerklärung
und zwei Zeilen zur Besetzung. In der Szene ist `fusszeile` eine einzelne
Zeile. Bei der Nachbildung ist die Zeichenerklärung Fußzeile geblieben, die
beiden Besetzungszeilen sind ein sechster Legendenblock geworden.

Das Ergebnis liest sich gut, verschiebt aber Inhalt von unten nach rechts. Zu
entscheiden wäre, ob `fusszeile` eine Liste von Zeilen annimmt, so wie
`legende` es mit `zeilen` schon tut.

### Ein Marker lässt sich nicht hervorheben

Im Referenzbild ist der Zuspieler als gefüllter dunkler Kreis gezeichnet, alle
anderen Spieler als Umriss. Auf einen Blick sieht man damit, wer die Sonderrolle
hat. Die Szene zeichnet jeden Marker gleich, der Unterschied liegt allein in der
Beschriftung.

### Die Zonenbeschriftung kann aus einer schmalen Zone herausragen

`textbreite()` in `schaubild.py` schätzt die Breite eines Wortes aus der
Zeichenzahl. Die Schätzung ist bewusst großzügig, trifft bei kurzen Wörtern in
schmalen Zonen aber trotzdem daneben: „Ziel" in einer Zone von 1,28 m Breite
ragt im fertigen Bild ein Stück über den gestrichelten Rand hinaus.

Kosmetisch, und die Zone bleibt lesbar. Auffallen würde es bei einer Zone, die
ein längeres Wort trägt.

### Die Trefferzeile zeigt Schaubild und Quelldatei verschieden

`suche.py --lang` druckt zwei benachbarte Zeilen für zwei Dateien im
Arbeitsordner, und sie sehen verschieden aus:

```
    Schaubild    schaubilder/ue-0020.svg
    Quelldatei   in quellen/ · volleyballmagazin/vm_09_2026/20260918_130257.jpg
```

Der Grund steht im Kommentar an der Stelle: `schaubild:` trägt laut
`DATENMODELL.md` einen einzelnen Dateinamen und ergibt mit dem Ordner davor
einen Pfad, den man kopieren kann. `quelldatei:` ist freier Text und nennt bei
einer Übung über zwei Seiten beide. Ein Präfix säße dort nur vor der ersten.

Der Preis ist, dass die häufige Angabe mit einer einzigen Datei ihre kopierbare
Pfadzeile verloren hat. Beides ginge wieder, wenn `quelldatei:` im Schema eine
Liste würde statt freier Text. Das wäre eine Schemaänderung und bricht
bestehende Karten, gehört also in eine Welle, die ohnehin am Datenmodell
arbeitet.

## Im Arbeitsordner, nicht im Plugin

Zwei Dinge betreffen `Nextcloud/_Training/trainingsplanung` und keinen Code.

### `schaubilder/2026-09-15-annahme-zielzone.png` ist veraltet

Die PNG ist die Ansicht des handgezeichneten SVG von vor der Abnahme. Seit der
Abnahme entsteht das SVG daneben aus einer Szene und sieht an drei Stellen
anders aus. Keine Karte verweist auf die PNG, der Linter schaut sie nicht an.

Sie ist damit zugleich das Einzige, was zeigt, wie die handgezeichnete Fassung
aussah. Entweder bleibt sie als dieser Beleg liegen, oder sie wird neu erzeugt,
oder sie wird weggeräumt. Eine Entscheidung steht aus.

### `index.md` kennt 18 Übungen, die Bibliothek hat 20

Die Lesebrille wird nur auf ausdrückliche Ansage neu gebaut, so steht es in
`trainingsplanung-root.yml` unter `index_md_automatisch: false`. Seit dem
Import von `ue-0019` und `ue-0020` ist sie veraltet.

```
<python> scripts/index.py --wurzel <pfad> --md
```

### Die Seiten 28 und 29 des Magazins sind noch nicht importiert

Das Volleyball-Magazin 09/2026 trägt auf diesen beiden Seiten eine
Praxiseinheit „Grundfertigkeiten der einarmigen Abwehr" mit sechs nummerierten
Übungen. Mehrere davon sind räumlich und damit Kandidaten für ein Schaubild:
ein Angreifer steht auf einer Kiste am Netz und spielt Shots in vorher
festgelegte Zonen.

Die beiden Seiten sind aufbereitet und lesbar. Aus dem Artikel auf den Seiten
22 bis 25 sind bisher zwei von vier Übungen importiert; die Seiten 30 bis 36
sind Theorie und Diagnostik ohne Übungen.

## Aus Welle 1b bewusst ausgelassen

Steht so in #10 unter *Out of Scope* und gilt weiter.

- Die vier bestehenden PNG-Schaubilder als Szene nachbauen. Sie bleiben PNG.
- `leseansicht.py` umbauen. Sie tut bereits das Richtige.
- Die Szene im Linter prüfen. Das Rendern prüft sie.
- Den Stationsbetrieb als zweite Geometrie behandeln.
- Mehrere Schaubilder je Karte. `schaubild:` bleibt ein einzelner Dateiname.
- HEIC und TIFF aufbereiten.
- Ein Beach-Team anlegen, solange es keins gibt.

## Was als Nächstes ansteht

Die Reihenfolge stammt aus #10 und ist dort begründet.

### Der zweite Ast von Welle 1b: die Wissenskarte

Die Wissenskarte als eigene Kartensorte mit eigenem Ordner und Schema
(ADR-0002), und damit der Import der Theorie- und Ratgeberseiten des
Volleyball-Magazins. Braucht eine eigene Spec. Die Bildaufbereitung aus Welle
1b war die Vorbedingung dafür und ist erledigt.

### Welle 2

Das Trainingsdesign auf Disziplin umstellen. Der Zugriff auf Wissenskarten über
die Suche und über die Trainingsplanung.

In Welle 1b wurde am Trainingsdesign nur der Abschnitt zum Schaubild angefasst,
der Rest des Skills blieb liegen und gehört hierher.

### Welle 3

Die Saisonfrage. Hallenjahr und Beachsommer passen nicht in das eine
`saison`-Feld der Wurzeldatei.

## Altlast aus Welle 1a

Die Zahl paralleler Gruppen wird nirgends gegen die verfügbaren Spielflächen
geprüft. `suche.py` zeigt „3 Gruppen parallel" an, auch wenn nur eine Fläche da
ist.
