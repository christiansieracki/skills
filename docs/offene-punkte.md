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
Pfadzeile verloren hat.

Entschieden am 30.09.2026 beim Interview zum Sammelimport: `suche.py` prüft, ob
der **ganze** Wert eine Datei unter `quellen/` ist. Dann druckt es
`quellen/<wert>` als Pfad, sonst die Zeile wie bisher. Geraten wird dabei
nichts, die Datei gibt es oder nicht. Auf einem Rechner, der `quellen/` nicht
synchronisiert, sieht die Zeile aus wie heute.

Eine Liste in `quelldatei:` braucht es dafür nicht, das Schema bleibt. Die
frühere Begründung, die Umstellung müsse vor den PlayDrill-Import, trägt auch
nicht. Eine PlayDrill-Karte nennt genau eine Datei, und aus `"x"` ein `["x"]`
zu machen geht über 370 Karten so mechanisch wie über 34. Die Prüfung kommt als
kleiner eigener Punkt in die Welle zum Sammelimport.

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
30.09.2026. Die PlayDrill-Bibliothek braucht die Wissenskarte nicht, und die
Wissenskarte kann danach den Sammelimport um ihre Kartensorte erweitern. Die
Welle zum Szenen-Vokabular ist als Welle 1c (#23) mit der Abnahme (#28) durch.

### Der Sammelimport

Aus dem PlayDrill-Import ist beim Interview am 30.09.2026 ein allgemeiner
Sammelimport im Plugin geworden. Er soll auch einen Stapel abfotografierter
Magazinseiten zusammen verarbeiten und sich wiederholen lassen. Die Begriffe
stehen im Saat-Glossar unter „Sammelimport", die Gründe für drei Entscheidungen
in ADR-0008 bis ADR-0010. Der Probelauf ist am 30.09.2026 als Prototyp vor
der Spec gelaufen und hat das Modell entschieden, siehe unten. Als Nächstes
kommt die Spec.

Der Anlass: Unter `quellen/playdrill/` liegen 343 PDFs, eine Übung je Datei.
10 davon sind Karte, 258 in den Übungsordnern offen, 75 zurückgestellt. Von
Hand ist das eine Übung je Sitzung, der Rest also über 250 Sitzungen. Import-
Skill, `DATENMODELL.md`, `SPRACHE.md` und `glossary.md` kosten zusammen rund
10 000 Tokens je Sitzung, bevor die Quelle gelesen ist.

Entschieden:

- **Aufbau.** Ein fünfter Skill `volleyball-sammelimport`. Er startet je
  Kandidat den Plugin-Agenten `volleyball-kartenentwurf` über das Agent-Tool,
  vier parallel, mit Sonnet 5.5 (ADR-0009). Der Agent hat nur `Read` und `Write`, sein Prompt
  ist ein knapper Auszug der Regeln. Ein Test im Repo prüft dessen
  kontrollierte Werte gegen `tpdaten.py`. Der Import-Skill bietet den
  Sammelimport an, wenn das Material ein Ordner mit mehr als etwa zehn Dateien
  ist.
- **Ablauf.** Erst ein Zerlegungsplan über den ganzen Quellenordner, den der
  Trainer freigibt. Dann ein Kartenentwurf je Kandidat, etwa 30 Kandidaten auf
  einmal. Die Zahl steht in `sammelimport.md` und lässt sich ändern. Dann die
  Freigabe im Chat. Einzeln, mit dem Feldbild, kommen die Rückfragen ohne
  Vermutung und die Rückfrage, ob ein aus dem Bild gelesener Ablauf stimmt,
  auch wenn sie eine Vermutung hat. Das sind etwa 1,3 je Kandidat. Alles
  andere steht in einer Tabelle, pauschal oder zeilenweise freizugeben: die
  Vorschläge zu Feldern in ihren Spalten, die Rückfragen mit Vermutung wie ein
  Vorschlag, und eine Spalte „aus dem Bild", die nur nennt, welche Stellen im
  Text aus dem Bild gelesen sind. Wer sie prüfen will, öffnet den Entwurf.
  `übernehmen` vergibt danach die IDs, schreibt die Karten, benennt das
  Feldbild nach der Karte, setzt `angelegt` auf den Tag der Freigabe und lässt
  `index.py` laufen. Freigabeform und die 30 auf einmal kommen aus dem
  Probelauf, vorher hieß es: alle Rückfragen einzeln, eine Sitzung je
  Unterordner.
- **Kartenentwurf.** Markdown, damit man ihn auch in Nextcloud lesen kann. Am
  Ende steht `## Freigabe` mit den Listen `Vorschläge:` und `Rückfragen:`. Jede
  Rückfrage stellt genau eine Frage und endet auf `Vermutung im Entwurf: …`
  oder `Vermutung im Entwurf: keine`. Das Prüfskript weist einen Entwurf ab,
  der das nicht einhält. `übernehmen` nimmt `## Freigabe` aus der Karte, was
  der Trainer geändert hat, kommt in die Notiz der Übersicht.
- **Status aus den Dateien.** Das Prüfskript setzt den Status in der Übersicht
  aus den Entwürfen auf der Platte: kein oder ein fehlerhafter Entwurf bleibt
  `offen`, einer mit mindestens einer Rückfrage ohne Vermutung wird
  `rückfrage`, der Rest `bereit`. Die Rückmeldung des Agenten zeigt nur den
  Fortschritt. Weitermachen nach einem Abbruch heißt: prüfen, dann beim
  ersten offenen Kandidaten weiter. Im Probelauf hatten sechs Aufrufe ihren
  Entwurf geschrieben und brachen erst bei der Rückmeldung ab.
- **Nichts erfinden.** Jedes Feld ist belegt, ein Vorschlag mit Begründung oder
  eine Rückfrage. Belegt sind `quelle`, `quelldatei`, `schaubild`, `level_min`
  aus der Kategorie, `dauer`, `autor` und `angelegt`, dazu Ziel, Ablauf und
  Variationen, wenn die Quelle sie beschreibt. Vorschläge sind `titel`,
  `element`, `form`, `spielphase`, `schwerpunkt` (nur vorhandene), `disziplin`,
  `spieler_min`, `spieler_max`, `level_max`, `material` und `netz`. Eine
  Rückfrage wird es bei einem Ablauf, der bei weniger als 150 Zeichen Text aus
  dem Bild gelesen ist, bei einer neuen Kennung, bei einem Duplikatverdacht,
  bei einem Widerspruch in der Quelle und wenn unklar ist, ob Übung oder
  Folge. Für PlayDrill werden damit `spieler_min` und `level_max` aus den
  Absprachen vom 26.09.2026 zu Vorschlägen.
- **Kandidaten.** Der Zerlegungsplan fasst zusammen, was zusammengehört, auch
  über Ordner hinweg. Ein Zirkel mit Übersichtsblatt wird eine Folge mit dem
  Bild der Übersicht, die Stationsblätter gehen in den Ablauf. Nummerierte
  Technikreihen wie UZ1 bis UZ10 werden Einzelübungen. Theorie bekommt
  `zurückgestellt`, bis es die Wissenskarte gibt. Der Plan bekommt den vollen
  Text jeder Datei, wenn alles in einen Aufruf passt, bei PlayDrill rund
  40 000 Tokens, sonst die ersten Zeilen.
- **Ablage.** Je Quellenordner eine `sammelimport.md` mit den Absprachen für
  alle Karten daraus und der Übersicht mit dem Status je Kandidat: `offen`,
  `bereit`, `rückfrage`, `importiert`, `ergänzt`, `übersprungen`,
  `zurückgestellt`, dazu eine Spalte Gruppe. Die Kartenentwürfe liegen in
  `kartenentwuerfe/<ordner>/`, haben keine ID und verschwinden bei der
  Freigabe (ADR-0010).
- **Lesen.** `pdftotext` ist optional (ADR-0008). Pillow schneidet das Feldbild
  aus.
- **Bibliothek im Zerlegungsplan.** Die Vorstufe gibt dem Zerlegungsplan eine
  knappe Liste der Bibliothek mit, je Karte ID, Titel, Element und
  `quelldatei`. Was mit seiner `quelldatei` schon in diesem Quellenordner
  liegt, steht im Plan gleich als `importiert` mit ID. So läuft ein
  Sammelimport ein zweites Mal über denselben Ordner, und bei `vm_09_2026`
  werden Übung 1 und 2 des Warm-ups nicht noch einmal Kandidat. Einen
  Duplikatverdacht gegen die Bibliothek oder innerhalb des Ordners schreibt
  der Plan als Rückfrage, etwa Nr. 254 in `Ü_Zirkelübung` gegen `ue-0027`.
  `ergänzt` entsteht erst bei der Freigabe. Der Agent für die Entwürfe
  bekommt die Liste nicht. Ersetzt die frühere Absicht, je Kandidat mit
  `suche.py` zu suchen: Die Suche filtert nach `element`, das erst der Entwurf
  vorschlägt, und der Agent kann mit `Read` und `Write` kein Skript starten.
- **PlayDrill.** `PLAYDRILL_IMPORT_LOG.md` wird zu
  `quellen/playdrill/sammelimport.md`, die zehn fertigen Zeilen behalten ihre
  IDs, und `pd_nehmen.py` fällt weg. Der Sammelimport nimmt die Übungsordner
  ohne `Ü_FV-Prüfungsfolien`, das ist ein Trainingsabend, und ohne
  `Ü_In Bearbeitung`, das ist in PlayDrill selbst unfertig.
- **Probelauf.** Gelaufen am 30.09.2026 als Wegwerf-Prototyp vor der Spec,
  ohne Plugin-Code und ohne etwas im Arbeitsordner zu schreiben. Die zehn
  fertigen PlayDrill-Übungen blind, dazu der Sprungkraftzirkel, aus dem
  Volleyball-Magazin 09/2026 die sieben Übungen mit Karte und Übung 3 und 4
  des Warm-ups (siehe *Aus dem Warm-up Teil 4 fehlen Übung 3 und 4*). Je
  einmal mit Haiku 4.5 und Sonnet 5.5 über das Agent-Tool, dazu Zerlegungspläne
  über `vm_09_2026` und `Ü_Zirkelübung`. Bericht, Regelauszug, Aufträge und
  die 40 Entwürfe liegen auf dem lokalen Branch `prototyp/sammelimport-probelauf`
  unter `plugins/volleyball/prototyp-sammelimport/`. Der Branch wird nicht
  gepusht, die Entwürfe geben Vereins- und Magazinmaterial wieder.
  - **Modell: Sonnet 5.5.** Die Regel war: Haiku, wenn es nichts erfindet.
    Haiku erfindet. In 13 von 20 Entwürfen steht etwas, das die Quelle nicht
    sagt oder verdreht, 14 haben keine Rückfrage. Sonnet hält sich an die
    Quelle, und seine Rückfragen treffen die Stellen, die beim Import von Hand
    abgestimmt wurden, meist mit derselben Vermutung.
  - **Zerlegungsplan.** Sonnet zerlegt die 15 Fotos von `vm_09_2026` in einem
    Aufruf richtig, samt Übungen über zwei Seiten, Verweis und Theorie. Die
    Form des Plans bleibt. Haiku zerlegt falsch.
  - **Kosten.** Das Agent-Tool meldet je Aufruf die Tokens. Ein Kartenentwurf
    kostet mit Sonnet im Median 91 000, mit Haiku 54 000. Das ist eine
    Obergrenze, gelaufen ist ein allgemeiner Subagent statt des Plugin-Agenten.
    Nach 44 Aufrufen war das Sitzungslimit des Abos erreicht. Daher die 30
    Kandidaten auf einmal. Der Nachtrag in ADR-0009 hält das fest, der größte
    Unterordner hat 59 Kandidaten.
  - **Freigabe.** Ein Sonnet-Entwurf trägt im Schnitt 16 Vorschläge und 3,6
    Rückfragen, 2,5 davon mit Vermutung. Über 258 Kandidaten wären das rund
    930 Rückfragen einzeln. Daher die Form oben.
  - **Vorstufe.** Übersichtsblätter bekommen den vollen Text. Die ersten
    Zeilen schneiden die Stationsliste ab.
  - **Regelauszug.** Der Entwurf aus dem Probelauf ist die Vorlage für die
    Agentendefinition. „In eigenen Worten" braucht dort mehr Gewicht, bei
    Magazintexten bleibt Sonnet stellenweise nah am Wortlaut.
  - **Nicht geprüft:** Duplikate, der Plugin-Agent mit nur `Read` und
    `Write`, `übernehmen` und die Freigabe im Chat. Das prüft der erste Schnitt
    der Spec.
- **Trefferzeile.** Die Pfadzeile für `quelldatei:` aus dem ersten Abschnitt
  dieser Datei kommt als kleiner eigener Punkt dazu.
- **Glossar im Arbeitsordner.** Die lebende `glossary.md` bekommt die neuen
  Begriffe nicht von selbst, `init_struktur.py` kopiert die Saat nur beim
  Anlegen. Beim ersten Start in einem Arbeitsordner schaut der Skill, ob der
  Abschnitt „Sammelimport" dasteht. Fehlt er, bietet er an, ihn aus der Saat
  einzufügen, und wartet auf das Ja.
- **Version.** 2.6.0. Alles kommt dazu, nichts bricht einen bestehenden
  Arbeitsordner.

### Der zweite Ast von Welle 1b: die Wissenskarte

Die Wissenskarte als eigene Kartensorte mit eigenem Ordner und Schema
(ADR-0002), und damit der Import der Theorie- und Ratgeberseiten des
Volleyball-Magazins. Braucht eine eigene Spec. Die Bildaufbereitung aus Welle
1b war die Vorbedingung dafür und ist erledigt.

Kommt nach dem Sammelimport und erweitert ihn um die Wissenskarte. Was ein
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
