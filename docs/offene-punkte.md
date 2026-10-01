# Offene Punkte

Was bei der Arbeit aufgefallen ist und noch kein Ticket hat. Der Tracker sind
die GitHub-Issues in `christiansieracki/skills`, siehe
`docs/agents/issue-tracker.md`. Diese Datei ist die Stufe davor: hier steht,
was jemand beim nächsten Schnitt aufgreifen soll, mit genug Zusammenhang, um
daraus ein Ticket zu machen.

Ein Punkt verschwindet hier, sobald er ein Ticket hat oder erledigt ist.

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

## Aus dem Interview zum Sammelimport

Aufgefallen am 30.09.2026.

### Zwei Rechner vergeben dieselbe ID

Die nächste freie ID ist die höchste in `uebungen/` plus eins, gelesen aus der
lokalen Kopie. Geben zwei Trainer am selben Abend auf zwei Rechnern Karten frei,
sehen beide dieselbe höchste Nummer, solange Nextcloud noch nicht abgeglichen
hat. Dann schreiben beide `ue-0291`. `index.py` meldet die doppelte ID, aber
erst hinterher, und ein Trainingsplan kann schon auf eine der beiden zeigen.

Die Sperrdatei aus dem PlayDrill-Log half dagegen nicht, sie liegt im
Temp-Ordner des einen Rechners. Das Risiko hat jeder Import. Mit dem
Sammelimport, der dreißig Karten auf einmal freigibt, wird es wahrscheinlicher.
Bewusst nicht in der Welle zum Sammelimport, weil es jeden Import betrifft.

## Aus Welle 1d

Aufgefallen am 30.09.2026 bei #31.

### Zwei Quelldateien, von denen eine ein Komma im Namen trägt

`quelldatei:` nennt bei zwei Seiten beide Dateien, getrennt durch Komma, so
steht es im Datenmodell. Die Übersicht in `sammelimport.md` setzt jede Datei in
Backticks und kommt deshalb mit Kommas im Dateinamen klar. `quelldatei:` auf
der Karte nicht.

Seit #34 nimmt `sammelimport.py pruefen` zuerst den ganzen Wert als eine Datei
und trennt erst sonst am Komma. Eine einzelne Datei mit Komma im Namen besteht
damit, und das ist der Fall bei PlayDrill, eine Übung je Datei. Nennt ein
Kandidat zwei Dateien und eine davon trägt ein Komma, etwa
`stapel/a, b.pdf, stapel/c.pdf`, weist `pruefen` den Entwurf mit „quelldatei
stapel/a gibt es unter quellen/ nicht" ab, und jeder neue Entwurf scheitert
genauso. `quelldatei:` als Liste ist in #29 ausdrücklich draußen.

Aufgefallen am 01.10.2026 bei #32.

### Die Planeingabe heißt `vorbereiten --plan`

#29 und #36 nennen für die Eingabe des Zerlegungsplans nur `vorbereiten`.
Umgesetzt ist sie als `vorbereiten --plan`. Nach der Freigabe lässt sich ein
zweiter Lauf über neue Dateien am Stand nicht von einem Durchgang
unterscheiden, `plan_freigegeben` ist in beiden Fällen gesetzt. Ohne `--plan`
legt `vorbereiten` wie bisher Aufträge an.

Der Skill (#36) ruft beim Einstieg `--plan` und im Durchgang `vorbereiten`
ohne. Der Agent (#35) liest `kartenentwuerfe/<ordner>/planeingabe.md`. Gibt es
keine neuen Dateien, schreibt `--plan` nichts und sagt „Keine neuen Dateien".
Eine ältere Planeingabe bleibt dann liegen. Der Skill richtet sich nach der
Ausgabe und startet keinen Agenten.

### Eine Datei ohne Zeile in der Übersicht kommt bei jedem Lauf wieder

`--plan` nimmt jede Datei, die in keiner Zeile der Übersicht steht. Macht der
Plan aus einer Datei keinen Kandidaten, steht sie beim nächsten Lauf wieder als
neu da. Das betrifft einen bloßen Verweis, einen Ordner, den der Trainer aus
dem Plan streicht, und die `.DS_Store` eines Mac. Naheliegend wäre, dass jede
Datei eine Zeile bekommt, notfalls `übersprungen` mit Grund. Das gehört in die
Regeln des Agenten (#35) und in die Freigabe im Skill (#36).

### Beim zweiten Lauf zählt der Plan die Kandidaten weiter

Kandidaten sind je Quellenordner fortlaufend nummeriert, und die Nummer bleibt.
Die Planeingabe nennt die höchste schon vergebene Nummer nicht. Beim zweiten
Lauf finge der Agent sonst wieder bei 1 an. Entweder nennt die Planeingabe die
nächste freie Nummer, oder der Skill (#36) nummeriert beim Schreiben der
Übersicht.

### Der Zerlegungsplan über PlayDrill kostet mehr als geschätzt

#29 rechnet für PlayDrill mit rund 40 000 Tokens Text. Gemessen hat der ganze
Ordner `quellen/playdrill` 310 000 Zeichen in 343 PDFs, eher 80 000 bis 100 000
Tokens. Die Planeingabe ist 350 KB groß. Der Agent liest sie in mehreren
Stücken, weil `Read` je Aufruf begrenzt ist. Ob die Schwelle von 400 000
Zeichen trägt, zeigt die Abnahme (#37). Liegt sie zu hoch, bekommt jede Datei
nur ihre ersten Zeilen, und Übersichtsblätter verlieren ihre Stationsliste.

Aufgefallen am 01.10.2026 bei #33.

### „Wenig Text“ trifft bei PlayDrill 15 Blätter, nicht 40

ADR-0008 rechnet mit 40 von 258 PlayDrill-PDFs, die zu wenig Ausführungstext
haben, 27 davon nur mit dem Platzhalter. Gemessen mit `textmarke: "Ausführung:"`
und dem Platzhalter aus dem Log trifft die Regel 15 von 260 PDFs in den
Übungsordnern. Den Platzhalter „hier Könnte ihr Text stehen“ trägt auf seiner
Textebene nur ein einziges Blatt, `Ü_Abwehr/#12P+_Kat1_Abwehr_Bewegung-Reaktion.pdf`.
Sechs der 15 sind Stationsblätter aus `Ü_Zirkelübung`. Als Teil einer Folge
kann ihr Text zusammen über 150 Zeichen kommen, denn gezählt wird über alle
Dateien eines Kandidaten.

Woher die 27 kommen, ist nicht geklärt. Die Abnahme (#37) zeigt, ob die Regel
die Blätter findet, deren Ablauf wirklich im Bild steht. Dabei auch die
Feldbilder ansehen: Ausgeschnitten sind alle 343. Drei davon sind byte-gleich
mit `ue-0022`, `ue-0023` und `ue-0042` geprüft, eines mit dem Auge.

### Wie der Agent sagt, dass der Ablauf aus dem Bild kommt

Hat eine Datei keinen Text, etwa ein Foto, steht im Auftrag „Ablauf aus dem
Bild: entscheidest du“. Laut #29 entscheidet der Agent dann „und sagt es“. Wie,
steht nirgends. `pruefen` erkennt den Ablauf aus dem Bild nur am Auftrag.
Schreibt der Agent dazu eine Rückfrage mit Vermutung, landet der Kandidat in
der Tabelle statt in der Einzelfrage. Die Regeln des Kartenentwurfs (#35)
sollten für diesen Fall eine Rückfrage ohne Vermutung verlangen, oder eine
feste Form, die `pruefen` erkennt.

### Bei einer Folge steht das Übersichtsblatt vorn

Das Feldbild kommt aus dem ersten PDF eines Kandidaten, das ein Bild
einbettet, in der Reihenfolge der Spalte Dateien. Entschieden am 01.10.2026.
Bei einem Zirkel soll das das Übersichtsblatt sein. Die Regeln des
Zerlegungsplans (#35) müssen es deshalb an die erste Stelle setzen.

Aufgefallen am 01.10.2026 bei #34.

### Was `pruefen` vom Kartenentwurf wörtlich verlangt

Ein abgewiesener Entwurf kostet einen neuen Aufruf des Agenten, im Probelauf
rund 91 000 Tokens. Die Regeln des Kartenentwurfs (#35) sollten deshalb die
Formen ausschreiben, an denen `pruefen` hängt:

- Eine Rückfrage ohne Vermutung endet genau auf `Vermutung im Entwurf: keine`.
  „keine Vermutung“ oder „keine, weil …“ gilt als Vermutung, und die Rückfrage
  landet in der Tabelle statt in der Einzelfrage. Abweisen lässt sich das
  nicht, „keine Pause“ kann eine echte Vermutung sein.
- Ein Fragezeichen steht nur in der Frage, nicht in der Vermutung.
- Ein Vorschlag zu einer Textstelle nennt den Abschnitt mit `##`, also
  `` `## Ablauf` ``. `` `Ablauf` `` gilt als Feld, das es nicht gibt.
- Das Frontmatter trägt jedes Feld der Karte außer `id` und `angelegt`, auch
  die mit `null`.

Der Test der Agentendefinitionen gegen `tpdaten.py` (#35) könnte neben den
kontrollierten Werten auch die Felder gegen `KARTENFELDER` prüfen. Die Liste
steht sonst dreimal da, in `DATENMODELL.md`, in `tpdaten.py` und im Agenten.

### Eine Freigabe geht verloren, wenn die Prüfung beim Übernehmen scheitert

`uebernehmen` prüft jeden freigegebenen Entwurf noch einmal. Besteht er nicht,
geht der Kandidat auf `offen`, und der nächste Durchgang lässt ihn neu
entwerfen. Der neue Entwurf überschreibt den alten, samt dem, was der Skill
aus den Antworten des Trainers eingearbeitet hat. Der Trainer gibt denselben
Kandidaten dann ein zweites Mal frei.

Treffen kann das vor allem `quelldatei`: Auf einem Rechner, dessen Nextcloud
`quellen/` nicht synchronisiert, fehlt jede Quelldatei, und jeder Kandidat
fiele beim Übernehmen durch. Solange der Sammelimport auf dem Rechner läuft,
der die Quellen hat, kommt das nicht vor. Offen ist, ob ein freigegebener
Entwurf vor dem Neuentwerfen geschützt sein soll. Den Stand „freigegeben“
kennt die Übersicht bisher nicht.

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

Die Reihenfolge stammt aus #10 und ist dort begründet. Den Sammelimport kannte
#10 noch nicht. Er kommt als Nächstes, vor der Wissenskarte, entschieden am
30.09.2026, und ist jetzt Welle 1d (#29) mit den Slices #30 bis #37. Die
PlayDrill-Bibliothek braucht die Wissenskarte nicht, und die Wissenskarte kann
danach den Sammelimport um ihre Kartensorte erweitern. Die Welle zum
Szenen-Vokabular ist als Welle 1c (#23) mit der Abnahme (#28) durch.

### Der zweite Ast von Welle 1b: die Wissenskarte

Die Wissenskarte als eigene Kartensorte mit eigenem Ordner und Schema
(ADR-0002), und damit der Import der Theorie- und Ratgeberseiten des
Volleyball-Magazins. Braucht eine eigene Spec. Die Bildaufbereitung aus Welle
1b war die Vorbedingung dafür und ist erledigt.

Kommt nach dem Sammelimport (#29) und erweitert ihn um die Wissenskarte. Was ein
Sammelimport als Theorie zurückgestellt hat, steht in der Übersicht seiner
`sammelimport.md` und wird von dort geholt.

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
