# Schaubilder: die Szene ist die Quelle

Ein Schaubild entsteht aus einer **Szene**: einer kurzen Beschreibung in
YAML, die in Metern rechnet (ADR-0004). Von Hand gezeichnetes SVG gibt es
nicht mehr. Szene und Bild liegen nebeneinander in `schaubilder/`, unter
demselben Basisnamen:

```
schaubilder/ue-000042.szene.yml    die Quelle, hier wird geändert
schaubilder/ue-000042.svg          das Erzeugnis, wird überschrieben
```

Dasselbe Muster wie bei Trainingsplan und Leseansicht: Wer in das SVG tippt,
verliert es beim nächsten Erzeugen. So bleibt ein Bild änderbar. Eine Korrektur
ein halbes Jahr später kostet drei Zeilen in der Szene statt einer
Neuzeichnung.

Erzeugt wird mit:

```
<python> ${CLAUDE_PLUGIN_ROOT}/scripts/schaubild.py ue-000042
<python> ${CLAUDE_PLUGIN_ROOT}/scripts/schaubild.py ue-000042 --wurzel <pfad>
```

Das Argument ist der Basisname (dann wird unter `schaubilder/` gesucht) oder
der Pfad zur Szenendatei. Geschrieben wird erst, wenn das ganze Bild steht:
Eine Szene, die nicht aufgeht, hinterlässt eine Meldung und das Bild von
vorher, nie ein halbes.

Auf der Übungskarte steht anschließend der Dateiname des Bildes:
`schaubild: ue-000042.svg`. `index.py` meldet, wenn er ins Leere zeigt.

## Der Aufbau einer Szene

```yaml
titel: Annahme-Zielzone
untertitel: Aufschlag von hinten, Annahme auf die Position 3
form: halle

legende:
  - ueberschrift: Aufschlagseite
    zeilen:
      - AS schlägt von hinter der Grundlinie
      - flach und lang, wechselnde Ziele
  - ueberschrift: Wertung
    zeilen:
      - 3 Punkte in der Zielzone
      - 1 Punkt spielbar daneben

zonen:
  - text: Zielzone
    form: rechteck
    bei: [4.5, 7.5]
    groesse: [3.0, 3.0]

spieler:
  - bei: 5
    text: AA
  - bei: 6
    text: L
  - bei: 3
    text: Z
  - bei: [4.5, 16.5]
    text: A

wege:
  - art: ballweg
    von: [4.5, 16.5]
    nach: 6
    bogen: 1.4
  - art: laufweg
    von: 1
    nach: [6.5, 7.2]

fusszeile: "Quelle: Volleyball-Magazin 09/2026, Seite 12"
```

Auf oberster Ebene gibt es zwölf Schlüssel, mehr nicht:

| Schlüssel | Wofür |
|---|---|
| `form` | die Grundform: `halle`, `beach` oder `frei` |
| `groesse` | die Maße der freien Leinwand, nur bei `form: frei` |
| `titel` | die Überschrift über dem Bild |
| `untertitel` | die zweite Zeile darunter, ohne `titel` die erste |
| `legende` | die Legendenspalte neben dem Bild, in Legendenblöcken |
| `fusszeile` | die Zeilen unter dem Bild: Zeichenerklärung und Quelle |
| `spieler` | Marker mit Beschriftung |
| `wege` | Lauf- und Ballwege |
| `zonen` | Flächen, die etwas bedeuten: Zielzone, Aufschlagbereich |
| `stellen` | Orte, an denen nichts steht und die einen Namen brauchen: Feldmitte, Netz |
| `geraete` | Kasten, Ballwagen, Zielmatte und was sonst im Weg steht |
| `abstaende` | Maßketten und beschriftete Pfeile |

Ein Schlüssel, den es nicht gibt, wird gemeldet statt übergangen. Ein
vertipptes `spiler:` ergäbe sonst ein leeres Feld, und das sieht fertig aus.

### Gerechnet wird in Metern

Durchgehend. Der Ursprung liegt in der **linken unteren Ecke** des Feldes, `x`
wächst nach rechts, `y` zur Gegenseite hin. Das Netz liegt auf halber Länge,
in der Halle also bei 9 m, im Sand bei 8 m.

Gesehen wird von oben, und die eigene Mannschaft steht **unten** und schaut zum
Netz. Ihre rechte Seite ist damit auch die rechte Seite des Bildes.

Die Umrechnung in Zeichenkoordinaten macht das Skript. In der Szene steht nie
eine Pixelzahl, und im Bild nie ein Meter. Nur so stimmt ein eingezeichneter
Abstand mit dem überein, was in der Halle abgeschritten wird.

Die Zeichenfläche wächst um das herum, was neben dem Feld steht. Ein
Aufschlagspieler bei `[4.5, -1.5]` steht ganz im Bild, statt angeschnitten zu
werden.

### `form`: die Grundform

| Wert | Fläche | Was darauf gezeichnet wird |
|---|---|---|
| `halle` | 9 × 18 m | Rand, Mittellinie, beide Angriffslinien (3 m vom Netz), Netzband |
| `beach` | 8 × 16 m | Rand, Netzband, sonst nichts |
| `frei` | aus `groesse` | nichts, nur die Fläche |

**Im Sand gibt es weder Angriffs- noch Mittellinie.** Eine Linie im Bild, die
es draußen nicht gibt, ist eine Ansage an Spieler, die niemand einhalten kann.
Das Netz steht in beiden Feldvorlagen als Band um die Feldmitte; in der Halle
bleibt die Mittellinie darunter sichtbar, im Sand sieht man auf einen Blick,
dass da keine ist.

Eine Grundform, die es nicht gibt, bricht mit einer Meldung ab.

### `frei`: die freie Leinwand

Für das, was auf kein Spielfeld passt: ein Stationsbetrieb quer durch die
Halle, ein Aufbau im Gang, eine Ecke mit drei Kästen. Die Leinwand ist ein
Stück Boden mit angesagtem Maß:

```yaml
form: frei
groesse: [12.0, 9.0]    # Breite und Länge in Metern
```

Gerechnet wird wie auf dem Feld: Ursprung in der linken unteren Ecke, `x` nach
rechts, `y` nach oben. Derselbe Aufbau misst hier also dasselbe wie dort, und
der Wechsel zwischen beiden Grundformen kostet eine Zeile.

**Was aufs Feld passt, gehört aufs Feld.** Dort ist der Maßstab geschenkt. Die
Leinwand ist für den Rest da.

Die Fläche bekommt keine Linie am Rand und kein Netz. Dass sie trotzdem
dasteht, sagt in der Halle, wie viel Boden der Aufbau braucht.

Ohne `groesse:` bricht die Szene ab. Eine Feldvorlage nimmt umgekehrt kein
`groesse:` entgegen: das Hallenfeld misst 9 × 18 m, und eine zweite Zahl
daneben wäre entweder wirkungslos oder falsch.

### `bei`, `von`, `nach`: wo etwas ist

Es gibt genau einen Weg, einen Ort zu nennen, und er sieht überall gleich aus.
Welche der drei Formen erlaubt ist, hängt an der Grundform:

| Geschrieben als | Bedeutet | Erlaubt in |
|---|---|---|
| `bei: 4` | Positionsnummer 1 bis 6 | nur `halle` |
| `bei: block` | eine Rolle | nur `beach` |
| `bei: [3.0, 12.5]` | Meter, x und y | überall |

Auf der freien Leinwand gibt es weder Nummern noch Rollen. Beide beziehen sich
auf ein Feld, und ohne Feld gibt es nichts, worauf. Dort stehen Orte in Metern
da.

**Positionsnummern in der Halle.** Die sechs Drittelflächen der eigenen
Hälfte, nach Volleyballkonvention: hinten 1/6/5, vorne 2/3/4, Position 1 ist
die Aufschlagposition rechts hinten. Ein Marker liegt jeweils in der Mitte
seiner Fläche.

**Rollen im Sand.** Dort gibt es keine Rotation, auf die sich eine Nummer
beziehen könnte, also heißt ein Platz nach dem, was der Spieler dort tut. Dafür
steht das Wort, das im Datenmodell schon dafür da ist: `block`, `abwehr`,
`annahme` und `aufschlag` sind Elemente einer Übungskarte. Die Annahme braucht
zwei Plätze und bekommt dafür eine Seitenangabe. `block` ist auch hier das
Technikelement und kein Zeitabschnitt.

| Rolle | Wo | Kürzel im Marker |
|---|---|---|
| `block` | am Netz, Feldmitte | BL |
| `abwehr` | hinten, Feldmitte | AB |
| `annahme-links` | linke Hälfte, mittlere Tiefe | AL |
| `annahme-rechts` | rechte Hälfte, mittlere Tiefe | AR |
| `aufschlag` | hinter der Grundlinie | AS |

Eine Positionsnummer im Sand und eine Rolle in der Halle brechen beide mit
einer Meldung ab, statt still auf irgendetwas zurückzufallen.

Alles andere steht in Metern da, auch die Gegenseite. Für die gibt es keine
Positionsnamen.

### `spieler`

```yaml
spieler:
  - bei: 3
    text: Z
    hervorgehoben: true
  - bei: [4.5, 16.5]
```

| Schlüssel | Bedeutung |
|---|---|
| `bei` | wo der Spieler steht, in den drei Formen von oben |
| `text` | die Beschriftung im Marker, optional |
| `hervorgehoben` | `true` für einen Spieler mit Sonderrolle, optional |

`text` ist die Beschriftung im Marker, kurz gehalten: eine Positionsnummer, ein
Kürzel wie Z, D, AA, MB, L. Fehlt `text`, beschriftet sich eine Position mit
ihrer Nummer und eine Rolle mit ihrem Kürzel; ein freier Punkt bleibt leer,
statt einen Namen zu bekommen, den niemand vergeben hat.

Der Marker ist maßstäblich: knapp ein Meter Durchmesser, so viel wie ein Mensch
von oben braucht.

**Hervorgehoben** wird ein Spieler, der in der Übung eine Sonderrolle hat: der
Zuspieler, der nicht mitrotiert, oder der Angreifer auf der Kiste, der die
Bälle bringt. Sein Marker ist in Strichfarbe gefüllt, das Kürzel darin steht in
Feldfarbe, und der Rand bleibt, wie er ist. Alle anderen bleiben Umriss. Worin
die Sonderrolle besteht, sagt die Legende; der gefüllte Marker zeigt nur, wer
sie hat.

Gefüllt und Umriss unterscheiden sich in der Helligkeit und bleiben damit auch
im Graustufendruck auseinander. Eine Farbe steht dafür nicht in der Szene:
`hervorgehoben` nimmt `true` oder `false`, sonst nichts.
Ohne den Schlüssel gilt `false`. `ja`, eine Zahl oder `"true"` in
Anführungszeichen brechen mit einer Meldung ab, statt still als wahr oder
falsch gelesen zu werden.

### `wege`

```yaml
wege:
  - art: laufweg
    von: 4
    nach: [3.0, 8.4]
  - art: ballweg
    von: [4.5, 16.5]
    nach: 6
    bogen: 1.4
```

| Schlüssel | Bedeutung |
|---|---|
| `art` | `laufweg` (durchgezogen) oder `ballweg` (gestrichelt) |
| `von`, `nach` | ein Ort, in den drei Formen von oben |
| `bogen` | Pfeilhöhe der Krümmung in Metern, optional |

Unterschieden wird über die **Strichart**, nicht allein über die Farbe. Das
bleibt für den lesbar, der Farben schlecht auseinanderhält, und im Ausdruck in
Graustufen. Jede Wegart hat ihre eigene Pfeilspitze.

`bogen` ist der größte Abstand der Kurve von der Geraden zwischen `von` und
`nach`, in Metern. Ein positiver Wert biegt nach **links**, vom Gang `von` →
`nach` aus gesehen, ein negativer nach rechts. Ohne `bogen` wird gerade
gezeichnet.

Fängt ein Weg auf einem Spieler an oder hört auf ihm auf, endet er am Rand des
Markers. Sonst verschwände die Pfeilspitze unter dem Kreis, und mit ihr das
Einzige, was die Richtung zeigt. An einer Stelle endet er genauso, am Rand
ihres Wortes.

### `zonen`

```yaml
zonen:
  - text: Zielzone
    form: rechteck
    bei: [4.5, 7.5]
    groesse: [3.0, 3.0]
  - text: Ziel
    form: kreis
    bei: [2.0, 3.0]
    groesse: 2.0
```

Eine **Zone** ist eine Fläche im Schaubild, die etwas bedeutet: die Zielzone
einer Annahme, der Bereich, in den aufgeschlagen wird, das Stück Feld, das ein
Blockspieler abdeckt. Sie besteht aus einer einzigen Grundform, hat einen Rand
und eine Beschriftung und ist maßstäblich wie alles andere in einer Szene.

| Schlüssel | Bedeutung |
|---|---|
| `text` | die Beschriftung, **Pflicht** |
| `form` | `rechteck` oder `kreis`, wie beim Gerät |
| `bei` | der Mittelpunkt, in den drei Formen von oben |
| `groesse` | `[breite, laenge]` in Metern, beim Kreis der Durchmesser |

**Eine Zone ist kein Gerät.** Ein Rechteck als Gerät zeichnet ebenfalls eine
Fläche mit Rand und Beschriftung, und man könnte eine Zielzone als Kasten
hinstellen. Das wäre aber eine falsche Ansage: Ein Gerät ist ein Gegenstand,
den jemand in die Halle stellt, eine Zone ist eine Absprache. Wer den
Unterschied im Bild nicht sieht, räumt in der Halle einen Kasten weg, wo nie
einer stand. Beide sehen deshalb verschieden aus:

| | Gerät | Zone |
|---|---|---|
| ist | ein Gegenstand | eine Absprache |
| Rand | durchgezogen | gestrichelt |
| Füllung | `--geraet` | `--zone`, näher am Boden |
| Beschriftung | darunter, gedämpft, freiwillig | darin oben, in Strichfarbe, Pflicht |
| besteht aus | einem Teil oder mehreren | einer Grundform |

Unterschieden wird über die **Strichart**, nicht allein über die Farbe, genau
wie bei Lauf- und Ballweg. Das bleibt im Graustufendruck stehen.

**Die Füllung bleibt zurückhaltend.** Über einer Zone stehen Marker und laufen
Wege, und eine Fläche, die kräftig genug ist, um aufzufallen, ist auch kräftig
genug, um das zu verdecken, worum es geht. Aus demselben Grund liegt die Zone
unter den Linien des Feldes: Eine Zielzone löscht nicht die Angriffslinie, an
der sie in der Halle abgemessen wird.

Die Beschriftung steht **in** der Zone. Ein Rechteck trägt sie an seiner
Oberkante, weil in der Mitte einer Zone meist jemand steht. Ein Kreis trägt sie
in der Mitte: oben ist er schmal, und das Wort stünde zu beiden Seiten daneben.

Gezeichnet wird sie als Letztes, über allem, was in der Zone steht. Ein Marker
deckt einen ganzen Meter ab, und mit der Fläche zusammen unten wäre das Wort
weg, sobald jemand darauf steht. Eine Zone ohne lesbares Wort ist aber nur noch
ein Farbfleck, der aussieht wie ein Gerät. Aus demselben Grund bricht eine Zone
ohne `text:` ab. Jeder Buchstabe hat einen schmalen Hof in Zonenfarbe. So
bleibt das Wort auch über einem hervorgehobenen Marker lesbar, der in
Strichfarbe gefüllt ist.

**Passt das Wort nicht hinein, sagt das Skript es.** Es vergleicht beim
Schreiben die geschätzte Breite des Wortes mit der Breite der Zone, beim Kreis
mit dem Durchmesser. Ist das Wort breiter, bricht das Skript nicht ab. Es
schreibt das Bild und sagt darunter, welche Zone es ist und was hilft. Hieße
der Kreis im Beispiel oben „Aufschlagziel" statt „Ziel", stünde da:

```
Zone 2 "Aufschlagziel": das Wort ist breiter als die Zone.
Ein kuerzeres Wort hilft, oder eine breitere Zone.
```

Die Schrift bleibt dabei so groß wie bei allen anderen Beschriftungen. Ein
einzelnes kleiner gesetztes Wort machte das Bild uneinheitlich. Meist ist das
kürzere Wort der bessere Ausweg: Die Zone ist maßstäblich, und wer sie
verbreitert, ändert die Absprache in der Halle.

Die Breite des Wortes ist eine Schätzung. Die Schrift steht erst im Betrachter
fest, und erst dort ließe sie sich messen. Passt ein Wort nur knapp oder knapp
nicht, zählt deshalb, was die Vorschau zeigt. Aus demselben Grund nennt der
Hinweis kein Maß, das reichen würde.

Zwei Flächen unter einem Wort gibt es nicht. Das wäre eine Absprache an zwei
Orten, und die schreibt man als zwei Zonen hin.

Zonen gibt es auf dem Feld und auf der freien Leinwand.

### `stellen`

```yaml
stellen:
  - bei: [4.5, 4.5]
    text: Feldmitte
  - bei: [9.8, 9.0]
    text: Netz
```

Eine **Stelle** ist ein Ort im Schaubild, der einen Namen braucht, ohne dass
dort etwas steht: die Feldmitte, zu der gespielt wird, der Startpunkt eines
Laufwegs, eine Linie des Feldes. Gezeichnet wird nur das Wort, zentriert auf
den Ort, in Kleinschrift und Strichfarbe. Es gibt keinen Punkt, keinen Rand
und keine Fläche.

| Schlüssel | Bedeutung |
|---|---|
| `bei` | der Ort, in den drei Formen von oben, **Pflicht** |
| `text` | das Wort, **Pflicht** |

Eine Stelle ist nur ein Wort. Ohne `text` bliebe nichts von ihr, was im Bild
stünde, und die Szene bricht ab. Ohne `bei` bricht sie ebenso ab, wie bei
jedem anderen Ort. Andere Schlüssel gibt es nicht.

**Zone oder Stelle?** Eine Zone ist eine Absprache über ein Stück Boden und
hat eine Fläche. Eine Stelle ist nur der Name eines Ortes, an dem nichts
steht. Die Feldmitte, zu der ein Abwehrball gespielt wird, ist kein Stück
Boden mit einem Maß, und ein Rand darum wäre eine Ansage, die es in der Halle
nicht gibt: Wer ihn sieht, sperrt etwas ab. Das Netz ist eine Linie.

| | Zone | Stelle |
|---|---|---|
| ist | eine Absprache über ein Stück Boden | der Name eines Ortes |
| im Bild | Fläche, gestrichelter Rand, Wort darin | nur das Wort |
| Maß | `groesse`, Pflicht | keins |

Steht an dem Ort jemand oder etwas, trägt dessen Marker oder Gerät den Namen,
und es braucht keine Stelle. Geprüft wird das nicht.

**Ein Weg hört vor dem Wort auf.** Beginnt oder endet ein Weg am Ort einer
Stelle, endet er am Rand ihres Wortes, so wie am Rand eines Markers. Das gilt
auch für einen Weg mit `bogen`. Dafür muss in `von` oder `nach` derselbe Ort
stehen wie in `bei`, auf fünf Zentimeter genau. Einen Namen, über den ein Weg
die Stelle findet, gibt es nicht. Waagerecht ist ein Wort breiter als
senkrecht, und ein langes Wort hält einen Weg weiter von seinem Ort fern als
ein kurzes. Mehr als zwei Drittel eines Weges fallen dabei nie weg. Ist er
dafür zu kurz, ragt die Spitze ins Wort; dann hilft ein kürzeres Wort oder ein
längerer Weg.

Das Wort steht **über allem**, auch über den Wörtern der Zonen und über den
Markern, denn außer dem Wort hat eine Stelle nichts.

Eine Linie des Feldes benennt man neben dem Feld auf ihrer Höhe, wie das Netz
oben. Auf der Linie selbst liefe sie mitten durch das Wort. Neben dem Feld
wächst das Blatt mit, statt das Wort anzuschneiden.

Stellen gibt es auf dem Feld und auf der freien Leinwand. Eine
Positionsnummer im Sand und eine Rolle in der Halle brechen auch hier ab.

### `geraete`

```yaml
geraete:
  - text: Kasten mit Ballwagen
    teile:
      - form: rechteck
        bei: [2.0, 7.0]
        groesse: [1.6, 0.8]
      - form: kreis
        bei: [2.0, 7.0]
        groesse: 0.6
  - text: Zielmatte
    teile:
      - form: rechteck
        bei: [9.5, 6.5]
        groesse: [2.0, 1.0]
```

Ein Gerät wird aus Grundformen zusammengesetzt. Es gibt zwei:

| `form` | `bei` | `groesse` |
|---|---|---|
| `rechteck` | Mittelpunkt | `[breite, laenge]` in Metern |
| `kreis` | Mittelpunkt | Durchmesser in Metern, eine Zahl |

Zusammengesetzt statt aufgezählt, weil eine feste Liste von Geräten immer das
eine nicht kennt, das dieser Aufbau braucht. Zwei Grundformen tragen weit: der
Ballwagen auf dem Kasten ist ein Rechteck mit einem Kreis darauf, die
Zielmatte ist ein Rechteck, ein Hütchen ist ein kleiner Kreis.

Alle Teile eines Eintrags gehören zu einem Gerät und bekommen zusammen einen
Namen. `text` steht **unter** dem Gerät, mittig. Ein Wort wie „Ballwagen" passt
in keinen Ballwagen. Wer darunter noch eine Maßkette legt, gibt ihr mit
`versatz` etwas mehr Abstand.

Auch ein Gerät ist maßstäblich. Ein Kasten von 1,6 × 0,8 m ist im Bild so
lang wie ein Sechstel der Feldbreite.

### `abstaende`

```yaml
abstaende:
  - art: masskette
    von: [6.0, 2.0]
    nach: [9.0, 2.0]
    versatz: -0.9
  - art: pfeil
    von: 4
    nach: [1.5, 12.0]
    text: gut 4 m
```

| Schlüssel | Bedeutung |
|---|---|
| `art` | `masskette` (Linie mit Maßstrichen) oder `pfeil` (Linie mit Spitzen an beiden Enden) |
| `von`, `nach` | die beiden Orte, deren Abstand gemeint ist, in den drei Formen von oben |
| `versatz` | wie weit die Linie danebengerückt wird, in Metern, optional |
| `text` | die Beschriftung, optional |

**Maßstäblich ist beides.** Maßkette und Pfeil zeichnen dieselbe Strecke und
unterscheiden sich allein an den Enden. Welche der beiden übersichtlicher ist,
hängt am Anwendungsfall. Der Pfeil trägt an beiden Enden eine Spitze; einfach
bepfeilt läse er sich als Weg.

Ohne `text` steht da, was gemessen wurde: `6 m`, `4,5 m`. Wer selbst etwas
hinschreibt, verantwortet es. Gezeichnet wird in beiden Fällen die Strecke
zwischen `von` und `nach`.

`versatz` rückt die Linie zur Seite, ohne sie zu kürzen. Positiv heißt nach
**links**, vom Gang `von` → `nach` aus gesehen, genau wie bei `bogen`. Zwei
gestrichelte Maßhilfslinien halten die verschobene Linie an dem fest, was sie
misst. Das braucht man, sobald eine Kette sonst quer durch die Marker liefe,
deren Abstand sie angibt.

### `titel`, `untertitel`, `legende`, `fusszeile`

Das Textwerk neben dem Bild. Es macht aus einer Skizze eine Anleitung: Das Feld
zeigt, wo jemand steht, das Textwerk sagt, worum es geht, was die Zeichen
bedeuten und woher die Übung kommt.

```yaml
titel: Annahme-Zielzone
untertitel: Aufschlag von hinten, Annahme auf die Position 3

legende:
  - ueberschrift: Aufschlagseite
    zeilen:
      - AS schlägt von hinter der Grundlinie
      - flach und lang, wechselnde Ziele
  - ueberschrift: Wertung
    zeilen:
      - 3 Punkte in der Zielzone
      - 1 Punkt spielbar daneben

fusszeile:
  - Durchgezogen ist ein Laufweg, gestrichelt ein Ballweg
  - "Quelle: Volleyball-Magazin 09/2026, Seite 12"
```

Alle vier sind freiwillig. Die meisten Schaubilder tragen keinen Titel, eine
Aufstellung erklärt sich oft von selbst.

Ein Text mit Doppelpunkt darin gehört in Anführungszeichen, wie die Quelle
oben. Ohne sie läse YAML `Quelle:` als Schlüssel, und die Szene bricht ab.

**Wo was steht.** Titel und Untertitel stehen über dem Bild, die Legende als
Spalte rechts daneben, die Fußzeile darunter. Steht kein `titel` da, rückt der
Untertitel an dessen Platz, dazu weiter unten mehr. Titel und Fußzeile sitzen
auf derselben linken Kante wie die Grundform, damit das Textwerk nicht wie ein
zweites Blatt hinter dem ersten aussieht. Die Legendenspalte beginnt oben auf
Höhe der Grundform. Steht jemand hinter der Grundlinie, fängt sie also unter
diesem Marker an.

**Die Legende steht in Legendenblöcken.** Sie ist selten eine einzige
Aufzählung, meist sind es mehrere: die Aufschlagseite, die Annahmeseite, das
Zuspielziel, die Wertung. Jeder Legendenblock braucht eine `ueberschrift` und
mindestens eine Zeile unter `zeilen`. Fehlt eines von beidem, bricht die Szene
ab: ohne Überschrift steht da eine Liste, von der niemand weiß, wovon sie
handelt, und eine Überschrift ohne Zeilen erklärt nichts und nimmt trotzdem
Platz neben dem Feld weg.

**Die Fußzeile trägt Zeichenerklärung und Quelle.** Was die Zeichen im Bild
bedeuten und woher die Übung kommt, steht unter dem Bild. Wer in der Übung
welche Aufgabe hat, die Besetzung, gehört in die Legende: Sie sagt, was im Bild
geschieht, die Fußzeile, wie man es liest. `fusszeile` nimmt eine einzelne
Zeile oder eine Liste von Zeilen, jede mit Strich. Die Zeilen stehen
untereinander, in der Reihenfolge der Szene. Leere Einträge fallen weg, wie in
einem Legendenblock. Stehen unter `fusszeile` Schlüssel mit Werten oder eine
Liste in der Liste, bricht die Szene ab, statt deren Schreibweise ins Bild zu
setzen.

**Das Blatt wächst mit.** Eine lange Zeile macht das Bild breiter, eine lange
Spalte oder eine Fußzeile aus mehreren Zeilen macht es höher. Abgeschnitten
wird nichts. Dass die halbe Erklärung fehlt, sieht man dem Bild sonst nicht
an, es wirkt fertig. Gebrochen wird eine Zeile trotzdem nicht: Wo ein Umbruch
hingehört, entscheidet, wer sie schreibt. In der Fußzeile heißt das zwei
Einträge statt einer langen Zeile, damit kein Umbruch mitten in einer
Quellenangabe landet. Kurz halten lohnt sich also. Im vorhandenen
`2026-09-15-annahme-zielzone.svg` nimmt die Legendenspalte mehr Platz ein als
das Feld.

**Ein `untertitel` ohne `titel` rückt nach oben.** Er bekommt den Platz und die
Schrift des Titels. Eine einzelne Zeile über dem Feld ist eine Überschrift,
gleich unter welchem Schlüssel sie in der Szene steht. Ein Abbruch kostete das
ganze Bild und eine Runde der Vorschau-Schleife, und das für eine Kleinigkeit.

Das Skript sagt beim Schreiben, dass es das getan hat, und schlägt einen
`titel:` vor: den der Übungskarte, deren ID der Basisname der Szene ist.
`schaubilder/ue-000042.szene.yml` gehört zu `uebungen/ue-000042-*.md`, und dort
steht der Titel schon. Übernehmen kostet eine Zeile. Ist der Basisname keine
Übungs-ID, gibt es die Karte nicht oder trägt sie keinen Titel, steht der
Hinweis ohne Wortlaut da. Geraten wird nichts.

In der Szene ändert sich nichts. Der Text steht weiter unter `untertitel:`,
verschoben wird die Zeile allein im Satz.

Die oberste Zeile wird zugleich der Name des Bildes, im SVG als `<title>`.
Das ist der `titel:`, und ohne ihn der Untertitel, der dann dort oben steht.
Es trägt, wo das Bild für sich steht, etwa in der Vorschau beim Zeichnen. In
der Leseansicht steckt es als `<img>` mit eigenem `alt`, dort zählt das.

## Farben

Das Bild bringt beide Farbschemata mit und schaltet mit dem Gerät um, genau wie
die Leseansicht, in der es steckt. Die Farben stehen als CSS-Variablen im Bild:
`--papier`, `--feld`, `--strich`, `--gedaempft`, `--laufweg`, `--ballweg`,
`--geraet`, `--zone`.

In der Szene stehen keine Farben. Wer eine braucht, ändert die Palette in
`scripts/schaubild.py`. Dann ändern sich alle Bilder mit, und so ist es
gedacht.

`currentColor` wird bewusst nicht benutzt: Die Leseansicht bettet das Schaubild
als `<img>` ein, und darin gibt es keine Elternfarbe, die färben könnte.

## Wann welches Schaubild

- **Aufstellung/Rotation:** ein Feld, die beteiligten Positionen, bei Bedarf
  Laufwege für die Rotation.
- **Annahme- und Angriffssystem:** Lauf- und Ballwege auf einer Feldhälfte, die
  Gegenseite nur so weit, wie sie gebraucht wird. Wohin der Ball soll, ist eine
  Zone, und ohne Maß eine Stelle, etwa die Feldmitte.
- **Beach:** dieselbe Szene mit `form: beach`; Plätze über Rollen statt über
  Nummern.
- **Stationsbetrieb:** aufs Feld, solange er hineinpasst. Sonst `form: frei`
  mit dem Maß des Hallenteils, Geräte für den Aufbau und Maßketten für die
  Abstände, die in der Halle abgeschritten werden.

Beschriftungen kurz halten. Das Schaubild ergänzt den Text der Übungskarte, es
ersetzt ihn nicht.
