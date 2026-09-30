# Offene Punkte

Was bei der Arbeit aufgefallen ist und noch kein Ticket hat. Der Tracker sind
die GitHub-Issues in `christiansieracki/skills`, siehe
`docs/agents/issue-tracker.md`. Diese Datei ist die Stufe davor: hier steht,
was jemand beim nächsten Schnitt aufgreifen soll, mit genug Zusammenhang, um
daraus ein Ticket zu machen.

Ein Punkt verschwindet hier, sobald er ein Ticket hat oder erledigt ist.

## Aus der Abnahme am Volleyball-Magazin (#18)

Die Abnahme von Welle 1b ist durch. Fünf Dinge sind dabei liegen geblieben.
Die vier zum Schaubild sind inzwischen Welle 1c (#23), übrig ist eins.

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

Seit dem PlayDrill-Import (siehe unten) drängt die Frage. Jede PlayDrill-Karte
hat genau eine Quelldatei und zeigt damit genau die Zeile ohne kopierbaren
Pfad. Schreibt ein automatischer Lauf die übrigen rund 335 Karten, bevor das
entschieden ist, geht die Umstellung über rund 370 Karten statt über 34. Die
Frage gehört deshalb vor den Massenimport, nicht erst in die Wissenskarte.

## Im Arbeitsordner, nicht im Plugin

Betrifft `Nextcloud/_Training/trainingsplanung` und keinen Code.

### `schaubilder/2026-09-15-annahme-zielzone.png` ist überschrieben

Die PNG war die Ansicht des handgezeichneten SVG von vor der Abnahme von Welle
1b und damit das Einzige, was zeigte, wie diese Fassung aussah. Bei der
Abnahme von Welle 1c (#28) hat der Agent sie am 30.09.2026 überschrieben. Er
wollte das erzeugte SVG ansehen, und sein Hilfsskript legte die Ansicht als
PNG neben das SVG, also genau auf diese Datei. Jetzt zeigt sie das erzeugte
Bild vor den Stellen.

Eine lokale Kopie gibt es nicht. Nextcloud hält die Vorversion auf dem Server,
im Webinterface lässt sie sich unter „Versionen" wiederherstellen.

Keine Karte verweist auf die PNG, der Linter schaut sie nicht an. Offen bleibt
wie vorher, was mit ihr geschieht. Sie kann wiederhergestellt als Beleg liegen
bleiben, neu erzeugt werden oder wegkommen.

### Aus dem Warm-up Teil 4 fehlen Übung 3 und 4

Die Praxiseinheit auf den Magazinseiten 28 und 29 fängt mit dem Warm-up aus
Teil 4 der Reihe „Warm-up mit Plan" im selben Heft an. Das hat vier Übungen.
In der Bibliothek stehen davon Übung 1 und 2 (`ue-0019`, `ue-0020`). Es
fehlen Übung 3, Steigerungsläufe und kurze Sprints, und Übung 4, Zwei gegen
Zwei mit höchstens drei Armkontakten. Beide stehen auf den Seiten 24 und 25
(`vm_09_2026/20260918_130305.jpg` und `20260918_130310.jpg`). Ob sie damals
bewusst weggelassen wurden, ist nicht vermerkt.

Übung 4 ist die Spielform, mit der das Warm-up endet, und liegt nah an
`ue-0041` „Ein Arm erlaubt". Beim Import wäre zu prüfen, ob sie eine eigene
Karte wird oder unter die Variationen von `ue-0041` kommt.

## Neu seit der Abnahme

Aufgefallen am 28.09.2026.

### `export_pdf.py` endet mit Exitcode 0, auch wenn nichts exportiert ist

Nach „Fertig: 0/7 exportiert." gibt das Skript 0 zurück. Ob der Export
geklappt hat, steht damit nur in der Ausgabe, nicht im Rückgabewert.
Aufgefallen bei der Diagnose des Edge-Fehlers: Die Schleife musste deshalb die
PDFs zählen, statt den Exitcode zu lesen. Saisonplaner und Trainingsdesign
rufen das Skript auf und sehen einen Fehlschlag nur, wenn sie die Ausgabe
lesen.

### Ein PDF über Edge dauert zehn bis zwanzig Sekunden

Jede Datei bekommt einen eigenen, frischen Profilordner, und so lange braucht
Edge damit. Die sieben Trainings unter `trainings/h1-h2` dauern zusammen gut
zwei Minuten. `--no-first-run`, `--disable-extensions` und
`--disable-component-update` haben nichts Messbares gebracht. Naheliegend wäre
ein Profil für den ganzen Lauf statt eines je Datei. Ob Edge damit schneller
ist, ist nicht gemessen.

### Den PlayDrill-Import automatisieren

Unter `quellen/playdrill/` liegen 343 PDFs, eine Übung je Datei. Davon sind 8
Karte. Der Ablauf steht in `PLAYDRILL_IMPORT_LOG.md` im Arbeitsordner: eine
Übung je Sitzung, die Zeile übernehmen und die Karten-ID mit einer Sperrdatei
reservieren, damit parallele Sitzungen nicht dieselbe Nummer nehmen. So dauert
der Rest über dreihundert Sitzungen. Gewünscht ist ein Lauf, der jede Übung in
einem eigenen Subagenten bearbeitet, wenig Tokens braucht und nichts erfindet.

Was dafür schon feststeht:

- Die PDFs haben eine Textebene, und `pdftotext` ist installiert. Den Text
  kann ein Skript ziehen, ohne Modell. Nur das Feldbild braucht ein Modell,
  das Bilder liest.
- Der größte Posten sind die festen Kosten je Übung. Import-Skill,
  `DATENMODELL.md`, `SPRACHE.md` und `glossary.md` sind zusammen etwa 33 KB,
  geschätzt 9 000 bis 10 000 Tokens, bevor die Quelle gelesen ist. Über 335
  Übungen sind das rund drei Millionen Tokens nur für die Regeln. Der
  Orchestrator fällt daneben kaum ins Gewicht.
- Ein Subagent kann nicht nachfragen. Das Log verlangt aber je Übung
  Rückfragen: die Lesart des Feldbilds, wenn unter „Ausführung" nur der
  Platzhalter steht, dazu `spieler_min` und einen Vorschlag für `level_max`.
  Die Rückfragen müssen also gesammelt statt gestellt werden, mit dem
  ausgeschnittenen Feldbild daneben, wie es die Absprache vom 26.09.2026
  verlangt.
- Die 8 fertigen Karten sind ein Maßstab gegen Erfundenes: ein Probelauf über
  Nr. 1 bis 8, verglichen mit dem, was schon abgenommen ist.
- Das Szenen-Vokabular spielt keine Rolle. Laut Absprache vom 26.09.2026
  bekommt jede PlayDrill-Karte das ausgeschnittene PlayDrill-Bild, gezeichnet
  wird nichts.

Zu entscheiden:

- Das Agent-Tool aus einer Sitzung heraus oder ein Skript, das `claude -p` je
  PDF startet. Im zweiten Fall sammelt kein Orchestrator Kontext an, und ein
  abgebrochener Lauf macht bei der ersten offenen Zeile weiter.
- Welches Modell die Subagenten nehmen.
- Was als belegt gilt: aus dem Text, aus einer Regel zum Dateinamen, oder es
  wird eine Rückfrage.
- Welche Status das Log dazubekommt, etwa `entwurf` oder `rückfrage`.
- Ob der Ablauf ins Plugin gehört oder in den Arbeitsordner.
- Ob `quelldatei:` vorher eine Liste wird, siehe oben.

Zwei Fragen beantwortet erst ein Probelauf: was eine Übung wirklich kostet,
und ob Text und Feldbild reichen, ohne dass etwas erfunden wird. Dafür reicht
ein `/prototype` über etwa fünf Übungen, eine davon mit Platzhaltertext.

### Die Zeichenerklärung könnte das Skript selbst setzen

Die Fußzeile eines Schaubilds trägt Zeichenerklärung und Quelle. Die
Zeichenerklärung schreibt bisher, wer die Szene schreibt, etwa „gestrichelter
Pfeil = Ballweg". Dabei weiß `schaubild.py`, welche Wegarten und Abstandsarten
in der Szene vorkommen, und könnte die Zeile selbst setzen. Einen Vorläufer
gibt es schon: Eine Maßkette ohne `text:` schreibt die gemessene Zahl hin.

Beim Zuschnitt der Welle zum Szenen-Vokabular bewusst draußen gelassen. Es ist
neues Verhalten und keine Lücke im Vokabular. Zu entscheiden wäre, ob die
selbst gesetzte Zeile eine geschriebene ersetzt oder nur einspringt, wenn keine
dasteht.

Bei der Abnahme (#28) ist die Zeile zweimal von Hand entstanden, für
`ue-0037` mit Laufweg und Ballweg, für `ue-0039` nur mit Ballweg. Beim zweiten
Bild musste man darauf achten, den Laufweg wegzulassen.

### Ein Weg quer durch das Wort einer Stelle

Aufgefallen am 30.09.2026 bei #26. Das Wort einer Stelle steht über allem,
aber ohne Hof. Beginnt oder endet ein Weg an der Stelle, hört er vor dem Wort
auf. Läuft er nur hindurch, scheint er zwischen den Buchstaben durch. Dasselbe
passiert, wenn eine Stelle direkt auf einer Linie des Feldes sitzt; die
Referenz rät deshalb, eine Linie neben dem Feld zu benennen.

Das Zonenwort hat für den ähnlichen Fall seit 2.3.0 einen Hof in Zonenfarbe.
Für die Stelle ginge er in Feldfarbe. Neben dem Feld stünde er dann auf dem
Papier, und im dunklen Schema sähe man ihn als Schimmer um die Buchstaben. #26
schließt Rand und Fläche aus, einen Hof hat es nicht erwogen.

Die Abnahme (#28) sollte zeigen, ob es ihn braucht. Im Referenzbild stehen
„Netz" und „3-m-Linie" neben dem Feld, dort läuft nichts hindurch. In
`ue-0037` lief im ersten Entwurf der Laufweg des Verteidigers quer durch
„Feldmitte", weil die Stelle genau dort lag, wo er nach vorn startet.
Freigegeben ist das Bild mit der Stelle 0,4 m zur Seite gerückt. Der Fall
kommt also vor, sobald eine Stelle mitten im Feld steht und jemand an ihr
vorbei nach vorn läuft. In der Szene lässt er sich umgehen. Ob der Hof
trotzdem kommt, ist zu entscheiden.

## Aus der Abnahme von Welle 1c (#28)

Aufgefallen am 30.09.2026 beim Zeichnen des Referenzbilds und der beiden
Bilder auf `beach`, `ue-0037` und `ue-0039`. Alle betreffen den Zeichner, also
`schaubild.py` und `szene.py`. Bei den ersten vier weichen die freigegebenen
Bilder in der Szene aus oder nehmen die Schwäche hin.

### Das Wort einer Stelle neben dem Feld stößt an die Legendenspalte

Die Legendenspalte fängt am rechten Rand des Bildblocks an. Laut Kommentar
in `Satzspiegel.__init__` liegt der „einen Feldrand weit neben allem, was
gezeichnet ist". Für Marker stimmt das, sie bekommen `LUFT`. Das Wort einer
Stelle rückt den Rand aber genau bis an seine geschätzte Breite und keinen
Millimeter weiter. Im Referenzbild steht „3-m-Linie" bei `[10.4, 6.0]` mit
rund 7 Zeicheneinheiten Luft vor „Der Ball muss von oben hineinfallen." und
liest sich wie deren Anfang.

Der Trainer hat das Bild trotzdem so freigegeben. Abhilfe wäre eine Gasse vor
der Spalte, die unabhängig davon gilt, was am weitesten rechts steht. Das gilt
dann auch für Zonen- und Gerätenamen am Rand.

### Die Beschriftung eines senkrechten Abstands liegt auf ihrer Linie

`Abstand.text_bei` rückt die Zahl `TEXTABSTAND`, also 0,45 m, von der Linie
weg, quer zu ihr und gleich, wie breit das Wort ist. Bei einer waagerechten
Linie reicht das, das Wort steht darüber oder darunter. Bei einer
senkrechten Linie steht es daneben und ist breiter als 0,45 m, also läuft die
Linie hindurch. In `ue-0039` sollte ein Pfeil vom Angreifer zum Verteidiger
„5 bis 6 m" zeigen, und die Linie strich „bis" durch. Freigegeben ist das Bild
ohne Pfeil, die Entfernung steht in der Legende.

Abhilfe wäre, den Abstand nach der halben Wortbreite zu bemessen, sobald die
Linie eher senkrecht als waagerecht verläuft.

### Ein Gerät unter einem Spieler verschwindet

Der Angreifer auf der Kiste ist in allen vier Übungen der Praxiseinheit, die
eine Kiste brauchen, die Hauptfigur. Als Gerät unter seinem Marker ist die
Kiste nicht zu sehen, denn der Marker misst knapp einen Meter und die Kiste
weniger. Ihr Name steht unter dem Gerät, also zum Netz hin, und landet am Netz
auf dem Netzband. Freigegeben ist beides ohne Kiste. Dass er darauf steht,
sagt die Legende.

Ob ein Spieler auf einem Gerät eine eigene Darstellung braucht, etwa das
Gerät als Rahmen um den Marker, oder ob die Legende dafür reicht, ist offen.

### Ein Pfeil endet auf dem Namen eines Geräts

Im Referenzbild endet der Annahmepfeil von 6 an der Unterkante der Zielmatte,
und dort steht ihr Name. Die Pfeilspitze sitzt auf „Zielmatte". Das war im
erzeugten Bild vor der Abnahme schon so und ist so freigegeben.

Ein Weg hört am Rand eines Markers und am Wort einer Stelle auf, am Namen
eines Geräts aber nicht. Ob er das auch soll, oder ob der Name eines Geräts
einem Pfeil ausweicht, ist offen. In der Szene hilft nur ein anderes Ende des
Pfeils. Hier ist dafür wenig Platz: Das Wort ist fast so breit wie die Matte,
und rechts daneben steht Z.

### Ein SVG ansehen, wenn die Umgebung es nicht zeigt

Der Skill `volleyball-schaubild` verlangt, dass das Bild im Dialog beurteilt
wird, und sagt, im Markup stehe nicht, ob ein Marker ein Wort verdeckt. Das
Lesewerkzeug des Agenten zeigt PNG und JPG als Bild, bei einem SVG gibt es nur
das Markup zurück. Bei der Abnahme hat der Agent deshalb jedes Bild über Edge
im Headless-Modus zu PNG gemacht, mit einem Hilfsskript im Temp-Verzeichnis
der Sitzung. Beim ersten Aufruf lag die PNG neben dem SVG im Arbeitsordner und
hat die alte Ansicht überschrieben, siehe oben.

`export_pdf.py` ruft Edge schon genauso auf. Ein `schaubild.py --png`, das die
Ansicht immer ins Temp-Verzeichnis legt, nähme dem Agenten das Basteln ab und
schlösse aus, dass sie im Arbeitsordner landet.

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

Die Reihenfolge stammt aus #10 und ist dort begründet. Den PlayDrill-Import
kannte #10 noch nicht. Wo er sich einreiht, ist nicht entschieden. Die Welle
zum Szenen-Vokabular ist als Welle 1c (#23) mit der Abnahme (#28) durch.

### Der PlayDrill-Import als Lauf

Siehe oben unter *Neu seit der Abnahme*. Braucht ein Interview, einen
Probelauf und eine eigene Spec.

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
