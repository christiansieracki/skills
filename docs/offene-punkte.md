# Offene Punkte

Was bei der Arbeit aufgefallen ist und noch kein Ticket hat. Der Tracker sind
die GitHub-Issues in `christiansieracki/skills`, siehe
`docs/agents/issue-tracker.md`. Diese Datei ist die Stufe davor: hier steht,
was jemand beim nächsten Schnitt aufgreifen soll, mit genug Zusammenhang, um
daraus ein Ticket zu machen.

Ein Punkt verschwindet hier, sobald er ein Ticket hat oder erledigt ist.

**Jeder Punkt hat ein Ziel.** Unter jedem Punkt steht eine Zeile `Ziel:`. Sie
nennt die Welle, in die er gehört, oder „bewusst nicht" mit dem Auslöser, der
ihn wieder öffnet. Gehört er in die laufende Welle, bekommt er gleich ein
Ticket und steht gar nicht erst hier. Ein Punkt ohne Ziel ist noch nicht fertig
aufgeschrieben.

Am Ende einer Welle stehen hier nur noch Punkte, deren Ziel eine spätere Welle
ist, und die Liste „Bewusst nicht gebaut". Was nach dem Ende einer Welle mit
„später" ohne benannte Welle hier stünde, zöge von Welle zu Welle mit.

## Offen

Bei der Durchsicht am 02.10.2026 vor der Abnahme von Welle 1d hat jeder Punkt
ein Ticket bekommen, siehe den Nachtrag in #29: #40 als Slice 1d/9, #38, #39
und #41 bis #48 vor der Abnahme, dazu Ergänzungen in #35, #36 und #37. Die
Punkte hier kamen danach aus den Interviews zur Welle zur Leseansicht und zur
Welle zur Wissenskarte und aus der Abnahme von 1d (#37).

### DVV Plan 1 als Übungsfolge mit ID

Die Athletik steht in den Plänen mit „—" in der Spalte ID, die Übungen sind im
Plan ausgeschrieben. Der DVV-Athletikplan ist laut Glossar eine Übungsfolge und
gehört als Karte nach `uebungen/`. Dann könnte ein Programmpunkt auf die Karte
zeigen, statt die Übungen in jeden Plan zu kopieren. Fiel im Interview zur Welle
zur Leseansicht auf, ist aber Arbeit an der Bibliothek.

Ziel: Welle 2.

### Quellgrafik aus PDFs, die nicht wie PlayDrill aufgebaut sind

Der Sammelimport nimmt aus einem PDF das größte eingebettete Bild. Das passt
nur zu PlayDrill. In den PDFs des Jugendtrainerlehrgangs liegen Bildreihen als
Einzelbilder, auf jeder Seite steht dieselbe Kopfleiste, und Gezeichnetes ist
gar kein Bild (ADR-0013). Lösung ist der Ausschnitt aus der gezeichneten
Seite mit `pypdfium2`, für Übungskarten wie für Wissenskarten. Fiel im
Interview zur Welle zur Wissenskarte am 04.10.2026 auf. Bis er gebaut ist,
läuft kein Sammelimport über PDFs, die nicht wie PlayDrill aufgebaut sind.

Ziel: Welle zur Wissenskarte, als erster Schnitt. Nach der Abnahme von 1d
(#37) prüfen, ob er vorher kommt, etwa vor die Welle zur Leseansicht.

### Eine schreibgeschützte Leseansicht bricht `leseansicht.py` ab

Bei der Abnahme von 1d war `trainings/h1-h2/2026-09-17.html` gesperrt. In den
Dateirechten stand ein Verweigern-Eintrag, wie ihn der Nextcloud-Client für
Dateien ohne Schreibrecht auf dem Server setzt. `leseansicht.py` brach mit
einem Traceback ab (`PermissionError`). Abhilfe wäre eine Meldung, die die
Datei nennt und sagt, dass sie gesperrt ist. Am 05.10.2026 hat der Trainer die
Datei in Nextcloud entsperrt, danach ist sie neu gebaut worden.

Ziel: Welle zur Leseansicht, die `leseansicht.py` ohnehin neu baut.

### Wiederkehrende Antworten bei der Freigabe in die Absprachen

Im ersten Durchgang über PlayDrill hatten 26 von 30 Entwürfen zusammen 45
Rückfragen ohne Vermutung. Zwölf fragten, wann die Rollen wechseln, vier, wohin
die Bälle zurückkommen, neun nach einer Kennung für den Angriff. Der Trainer hat
jede Gruppe einmal beantwortet: „Gewechselt wird nach Ansage", der Rückweg der
Bälle kommt nicht auf die Karte, die Kennung heißt `angriff`. Der Skill fragt
laut Anleitung eine Rückfrage nach der anderen. Abhilfe wäre, gleiche
Rückfragen gebündelt zu stellen und anzubieten, eine Antwort, die für den
ganzen Quellenordner gilt, in die Absprachen der `sammelimport.md` zu
schreiben. Dann fragt der nächste Durchgang nicht mehr danach.

Am 04.10.2026 kamen die beiden Antworten von Hand in die Absprachen von
`playdrill` und `vm_09_2026`, unter „Was die Quelle nicht sagt“. Die beiden
Entwürfe über `vm_09_2026` fragten danach nicht mehr, einer schrieb „Gewechselt
wird nach Ansage“ selbst in den Ablauf (ADR-0009, Nachtrag nach der Abnahme).

Ziel: Welle zur Wissenskarte, Schnitt 5, der die Freigabe im Skill ohnehin
anfasst.

### Ein neues Schaubild erreicht die Leseansicht erst nach einem Neubau

Die Leseansicht bettet das Schaubild einer Karte ein. Bekommt die Karte ein
neues Bild, zeigt jede Leseansicht, die schon gebaut ist, weiter das alte. Bei
der Abnahme von 1d bekam `ue-000015` ein SVG statt der PNG aus Ricos PDF, und
`trainings/h1-h2/2026-10-01.html` trug noch die PNG, bis sie von Hand neu
gebaut wurde. Weder der Skill `volleyball-schaubild` noch der Linter sagen
das. Abhilfe wäre, dass der Skill nach der Freigabe die Pläne nennt, die die
Karte benutzen, und anbietet, ihre Leseansichten neu zu bauen.

Ziel: Welle zur Leseansicht, die `leseansicht.py` ohnehin neu baut.

## Bewusst nicht gebaut

### Das PDF sieht aus wie die Leseansicht

`export_pdf.py` baut das PDF weiter aus der `.md`, mit eigenem CSS. Die neue
Leseansicht klappt auf und zu und taugt so nicht zum Drucken. Aus dem Interview
zur Welle zur Leseansicht.

Ziel: bewusst nicht. Auslöser: Das PDF soll aussehen wie die Leseansicht.

### Zeitmessung und Abhaken in der Leseansicht

Die Leseansicht zeigt den Ablauf, sie misst keine Zeit und hakt nichts ab. Die
Vorlage sagt das selbst: „Keine laufende Zeitmessung". Aus dem Interview zur
Welle zur Leseansicht.

Ziel: bewusst nicht. Auslöser: Der Trainer vermisst es in der Halle.

### Eine Liste in Blockform liest der Parser als leer

Aus #39. `lies_frontmatter` in `tpdaten.py` versteht Listen nur in eckigen
Klammern, so steht es in `DATENMODELL.md`. Schreibt jemand von Hand

```yaml
schaubild:
  - ue-000291-zirkel-1.png
  - ue-000291-zirkel-2.png
```

kommt `schaubild` als `null` an. Der Linter schweigt, die Leseansicht zeigt
kein Bild, und `volleyball-schaubild` hält die Karte für eine ohne Bild. Bei
`disziplin` fällt dieselbe Form auf, weil das Feld Pflicht ist, bei `schaubild`
nicht. Abhilfe wäre eine Meldung des Linters für jede Zeile mit `- ` im
Frontmatter einer Karte. Die Skripte und Skills schreiben die Form mit
Klammern.

Ziel: bewusst nicht. Auslöser: Eine Karte mit einer Liste in Blockform taucht
im Arbeitsordner auf.

### `vorbereiten --plan` achtet nicht auf `in_arbeit`

Aus #40. `in_arbeit` trägt nur `vorbereiten` ein, wenn es Aufträge schreibt,
und nur dort hält ein fremder Eintrag an. `vorbereiten --plan` prüft ihn nicht
und schreibt ihn nicht. Schriebe es ihn, bliebe er nach einem Lauf ohne neue
Dateien oder ohne Kandidaten mit Karte stehen, denn `uebernehmen` liefe nie.
Plant ein Trainer neue Dateien, während ein anderer importiert, schreiben der
Skill des einen und das Skript des anderen zugleich in die Übersicht, und die
Nextcloud legt eine Konfliktdatei an. Mit einem Trainer kommt das nicht vor.

Ziel: bewusst nicht. Auslöser: Ein zweiter Trainer importiert aus einem
Quellenordner, an dem schon einer arbeitet.

### Edge druckt mal in zwei, mal in zwanzig Sekunden

Aus #41. Derselbe Lauf von `export_pdf.py` über die acht Pläne unter
`trainings/h1-h2` dauerte am 03.10.2026 einmal 21 s und einige Stunden später
170 s, mit demselben Code. Die Zeit vergeht im Start von Edge. Ein Profilordner
für den ganzen Lauf spart rund ein Drittel, an der Schwankung selbst ändert er
nichts. `--no-first-run`, `--disable-extensions` und
`--disable-component-update` haben schon vorher nichts gebracht. Woran es
liegt, ist offen. `schaubild.py --png` trifft es genauso, mit einem Aufruf je
Runde.

Ziel: bewusst nicht. Auslöser: Ein Export oder eine Vorschau dauert dem Trainer
zu lange.

### Ein Weg quer durch den Namen eines Geräts

Aus #43. Ein Weg hört vor dem Namen eines Geräts nur auf, wenn er mit seiner
Spitze hineinreicht. Läuft er durch den Namen hindurch, etwa bis in die Mitte
des Geräts, kreuzt er das Wort: Der Name liegt mit dem Gerät unter den Wegen
und hat keinen Hof. Abhilfe wäre ein Hof wie beim Wort einer Stelle, und der
Name käme über die Wege. In den Szenen im Arbeitsordner kommt der Fall am
03.10.2026 nicht vor.

Ziel: bewusst nicht. Auslöser: Ein Schaubild zeigt einen Weg quer durch den
Namen eines Geräts.

### Zwei Geräte unter einem Spieler

Aus #44. Liegt die Mitte eines Geräts im Marker eines Spielers, zeichnet das
Skript das Gerät als Rahmen um den Marker. Liegen zwei Geräte unter demselben
Spieler, entstehen zwei Rahmen am selben Ort, und ihre Namen stehen
übereinander. Ein Ballwagen neben der Kiste steht in der Halle neben ihr und
hat seine Mitte deshalb nicht im Marker. In den Szenen im Arbeitsordner kommt
der Fall am 03.10.2026 nicht vor.

Ziel: bewusst nicht. Auslöser: Ein Schaubild braucht zwei Geräte unter einem
Spieler.

### Gestrichelt ist auch der Rand einer Zone

Aus #45. Die Zeichenerklärung, die das Skript setzt, sagt „gestrichelt ein
Ballweg". Gestrichelt sind im Bild aber auch der Rand einer Zone, das Netzband
und die Maßhilfslinien einer verschobenen Maßkette. Ein Ballweg hat dazu eine
Spitze und seine eigene Farbe, und der Wortlaut stammt aus der Abnahme von 1c.
Abhilfe wäre „gestrichelt mit Spitze ein Ballweg" oder ein anderer Strich für
den Rand einer Zone.

Ziel: bewusst nicht. Auslöser: Jemand liest den Rand einer Zone als Ballweg.

### Eine Datei, die nicht UTF-8 ist, bricht den Linter ab

Aus #47. Der Linter liest jetzt auch die Szenen. Ist eine nicht als UTF-8
gespeichert, bricht `index.py` mit `UnicodeDecodeError` ab, und mit ihm
`suche.py` und `sammelimport.py uebernehmen`, die den Index bauen. Für Karten
und Trainingspläne galt das schon vorher. Szenen schreibt der Skill, Karten
schreiben Skill und Skripte, beide in UTF-8. Abhilfe wäre eine Meldung je
Datei, die sich nicht lesen lässt, wie bei `ids_umstellen.py`.

Ziel: bewusst nicht. Auslöser: Eine Datei im Arbeitsordner, die nicht UTF-8 ist,
lässt `index.py` abbrechen.

### Ein HEIC, das schon im Zerlegungsplan steht

Aus #48. `bilder_aufbereiten.py` macht aus einem TIFF oder HEIC ein JPEG mit
`.jpg` und lässt nur liegen, worauf eine Karte zeigt. Steht die Datei schon in
der Übersicht einer `sammelimport.md` oder in einem Kartenentwurf, zeigen beide
danach ins Leere. Die Übersicht führt den Kandidaten mit der alten Datei, das
JPEG gilt als neue Datei, und `pruefen` weist den Entwurf ab, weil es seine
`quelldatei` nicht mehr gibt. Der Hinweis von `vorbereiten --plan` nennt das
HEIC trotzdem, denn er nennt jedes unlesbare Foto des Ordners. Im Ablauf kommt
der Hinweis vor dem Plan, das HEIC wird also aufbereitet, bevor es in eine
Zeile kommt. Ebenso bleibt ein HEIC unlesbar, auf das eine Karte zeigt. Abhilfe
wäre, Übersicht, Entwurf und Karte beim Umbenennen mitzuziehen.

Ziel: bewusst nicht. Auslöser: Ein TIFF oder HEIC steht schon in einer
Übersicht, einem Kartenentwurf oder auf einer Karte, und jemand muss es lesen.

### Alter oder Level auf der Wissenskarte

Viel aus dem Jugendtrainerlehrgang gilt nur für Kinder und Jugendliche, etwa
Förderstufen oder sensible Phasen. Die Wissenskarte hat dafür kein Feld, für
wen etwas gilt, steht in den Kernaussagen. Abhilfe wäre ein freiwilliges Feld
mit eigenem Vokabular, etwa `kinder`, `jugend`, `erwachsene`. Aus dem Interview
zur Welle zur Wissenskarte.

Ziel: bewusst nicht. Auslöser: Die Suche aus Welle 2 bringt für eine
Jugendgruppe die falschen Wissenskarten.

### Ein Beach-Team anlegen, solange es keins gibt

Beach ist seit Welle 1a im Plugin und an einer echten Beachübung abgenommen
(#9). Ein Team anzulegen ist Arbeit im Arbeitsordner mit dem Saisonplaner, kein
Code, und ohne echtes Beach-Team gibt es nichts anzulegen. Steht so seit #10.

Ziel: bewusst nicht. Auslöser: Es gibt ein echtes Beach-Team.

### Lange Titel aus dem Kartenentwurf

Die Titel der 30 Karten aus dem ersten Durchgang über PlayDrill beschreiben
ganze Abläufe, etwa „Dankeball auf der Abwehrposition hoch in die Feldmitte
spielen und dann zuspielen". Die Dateinamen von Karte und Quellgrafik werden
damit bis zu 95 Zeichen lang. Die Karten von Hand haben kurze Titel. Der
Trainer hat alle 30 so freigegeben. Abhilfe wäre eine Längengrenze im
Agenten oder ein gekürzter Name beim Übernehmen.

Ziel: bewusst nicht. Auslöser: Der Trainer kürzt Titel bei der Freigabe
regelmäßig, oder ein Pfad wird für Windows oder Nextcloud zu lang.

### Die Regel „wenig Text" zählt Ziel und Varianten mit

Die Regel zählt alles nach der Textmarke, bei PlayDrill also auch Ziel,
Varianten und Hinweise. Ein Blatt mit knapper Ausführung und langem Rest trifft
sie nicht. 29 der 260 Blätter haben zwischen „Ausführung" und der nächsten
Rubrik weniger als 150 Zeichen, meist knappe Stationsblätter. Ob ihr Text
reicht, zeigt sich bei ihren Entwürfen (ADR-0008, Nachtrag vom 04.10.2026).
Abhilfe wäre, nur bis zur nächsten Rubrik zu zählen, mit den Rubriken als
weiterer Einstellung in der `sammelimport.md`.

Ziel: bewusst nicht. Auslöser: Ein Entwurf liest seinen Ablauf aus der
Grafik, ohne dass die Regel ihn getroffen hat, und der Trainer muss die
Lesart korrigieren.

### Kopien desselben Blatts im Zerlegungsplan

35 der 70 Rückfragen im Zerlegungsplan über PlayDrill galten Kopien desselben
Blatts in einem anderen Ordner, mit gleichem Text und pixelgleicher Grafik.
Entschieden hat sie der Trainer in einem Zug: gestrichen als Duplikat.
Abhilfe wäre, dass `vorbereiten --plan` gleiche Texte mit gleicher Grafik in
der Planeingabe markiert. Der Plan über PlayDrill ist freigegeben.

Ziel: bewusst nicht. Auslöser: Ein weiterer Quellenordner bringt viele Kopien
in den Zerlegungsplan.

### `ids_umstellen.py` nennt nicht jede Leseansicht

Das Skript nennt am Ende die Aufrufe, die das Erzeugte neu bauen, sucht
Leseansichten aber nur unter `trainings/`. `_test-beach/2026-09-29.html`
fehlte in der Liste. Die Aufrufe stehen außerdem ohne Pfad zum Skript da,
`python index.py --md`, obwohl die Skripte nicht im Arbeitsordner liegen. Der
Arbeitsordner ist seit dem 04.10.2026 umgestellt.

Ziel: bewusst nicht. Auslöser: Ein zweiter Arbeitsordner wird umgestellt.

### Einen Kandidaten im Sammelimport vorziehen

`sammelimport.py vorbereiten` nimmt immer die nächsten offenen Kandidaten der
Reihe nach. Bei der Abnahme von 1d sollte der Sprungkraftzirkel (Kandidat 182
über PlayDrill) seine Karte bekommen, davor waren aber 149 Kandidaten offen.
Dass alle neun Blätter eine Quellgrafik hergeben, wurde deshalb in einer Kopie
geprüft, und die Karte entsteht im Durchgang, der bei 182 ankommt. Abhilfe wäre
`vorbereiten <ordner> --kandidat 182`.

Ziel: bewusst nicht. Auslöser: Ein Trainer braucht eine bestimmte Karte aus
einem laufenden Sammelimport früher, als die Reihe sie bringt.

### Ein Verweis im Trainingsplan auf eine Datei, die es nicht gibt

`trainings/h1-h2/2026-09-15.md` verwies im Text auf
`schaubilder/2026-09-15-annahme-zielzone.png`. Gezeichnet ist das Bild aber
als `.svg`. Der Linter prüft `schaubild:` auf den Karten, Pfade im Text eines
Plans liest er nicht. Bei der Abnahme von 1d ist der Verweis von Hand berichtigt
worden.

Ziel: bewusst nicht. Auslöser: Ein zweiter Verweis ins Leere fällt in einem
Plan auf.

## Was als Nächstes ansteht

Die Reihenfolge stammt aus #10 und ist dort begründet. Der Sammelimport kam am
30.09.2026 davor und ist Welle 1d (#29). Vor ihrer Abnahme (#37) kommen #38 bis
#48, die Reihenfolge steht im Nachtrag von #29. Die PlayDrill-Bibliothek
braucht die Wissenskarte nicht, und die Wissenskarte kann danach den
Sammelimport um ihre Kartensorte erweitern. Zwischen 1d und die Wissenskarte
kommt die Welle zur Leseansicht, beschlossen am 02.10.2026. Die Welle zur
Wissenskarte ist am 04.10.2026 im Interview festgelegt worden.

### Welle zur Leseansicht

Die Leseansicht bekommt die freigegebene Gestaltung vom Branch
`overhaul/html-generation-display`: den Ablauf zum Aufklappen, Hell, Dunkel und
System. Beschlossen im Interview am 02.10.2026. Kommt nach der Abnahme von 1d
(#37) und setzt auf #39 auf, weil beide `leseansicht.py` ändern.

- **Technik** steht in ADR-0012. `leseansicht.py` baut die Gestaltung nach,
  eine einzige Datei, ohne JavaScript ganz lesbar. Umschalter Hell, Dunkel,
  System, voreingestellt ist System. Keine festen Varianten nur hell oder nur
  dunkel.
- **Begriffe** stehen im Glossar: Ablauf, Programmpunkt, Zeitangabe, Abschnitt,
  Hallenskizze. „Teil" ist kein Begriff mehr.
- **Gliederung des Trainingsplans** kommt in `VORLAGEN.md`, `DATENMODELL.md`
  und den Skill Trainingsdesign, dazu in die Hilfetexte der Skripte (etwa
  `suche.py --dauer`):
  - Die Spalte heißt „Programmpunkt". Die Skripte verstehen weiter „Teil" und
    „Block".
  - Beginnt eine Überschrift mit einer Zeitangabe, gehört der Abschnitt zu
    diesem Programmpunkt. Bei zwei zur selben Zeit steht der Hallenteil dabei,
    ohne ihn gilt der Abschnitt für beide. Passt die Zeitangabe auf keinen,
    bleibt der Abschnitt unter „Vorbereitung", und der Generator meldet es.
  - Verschiebt sich eine Zeit, zieht der Skill die Überschriften mit.
  - Unter `## Zum Nachschlagen` wird jede `###` ein Reiter. Ein Verweis aus
    einem Programmpunkt ist ein Markdown-Link auf die Überschrift.
  - Eine Tabelle mit den Spalten `Nr | Übung | … | Heute` wird eine Liste zum
    Aufklappen, `Heute` ist die Dosierung im Kopf.
  - Der Plan schreibt kein „siehe unten" mehr. Der Generator ändert keinen
    Text.
- **Die Leseansicht**:
  - Kopf: Kurztitel, Wochentag und Datum, Name der Gruppe aus der Wurzeldatei,
    Teilnehmer, Dauer, Hallenteile aus `spielflaechen`. Der Fuß bleibt.
  - Ein aufgeklappter Programmpunkt zeigt „Heute", dann die zugehörigen
    Abschnitte in der Reihenfolge des Plans, mit ihrer Überschrift ohne
    Zeitangabe. Gleicht die Überschrift dem Namen der Übung, fällt sie weg.
    Danach das Schaubild der Karte, die Verweise und „Warum hier?" zugeklappt.
  - Mehrere Schaubilder stehen untereinander, jedes lässt sich vergrößern, und
    auch im Dunkeln liegen sie auf hellem Grund.
  - Pause und Umbau erscheinen gedämpft. Zwei Programmpunkte zur selben Zeit
    stehen untereinander, mit ihrem Hallenteil.
  - Unter „Vorbereitung" steht alles ohne Zeitangabe außer „Zum Nachschlagen",
    auch die Nachbereitung. Ein Abschnitt, der dabei leer wird, entfällt.
  - Der Satz zum Abhaken im Docstring fliegt raus, das gibt es nicht.
- **Ablage**: Die React-Dateien kommen nach `docs/gestaltung/leseansicht/`, sie
  werden nicht mit dem Plugin ausgeliefert. Danach wird der Branch gelöscht.
- **Abnahme**:
  - Die Pläne vom 01.10. und vom 17.09. werden von Hand umgestellt, der eine
    zum Vergleich mit der Vorlage, der andere wegen der Programmpunkte zur
    selben Zeit. `_vorlage.md` und die lebende `glossary.md` im Arbeitsordner
    ziehen wir von Hand nach.
  - Das Android-Handy auf beiden Wegen, per WhatsApp vom Rechner und aus der
    Nextcloud in den Browser, je in Hell und Dunkel.
  - Ein Desktop-Browser mit ausgeschaltetem JavaScript im schmalen Fenster.
  - Ein echtes iPhone: Ein Spieler bekommt die Datei per WhatsApp und schickt
    einen Screenshot. Klappt das bis zur Abnahme nicht, kommt es mit Ziel
    hierher.
- **Version**: ein kleiner Sprung, alte Pläne bleiben gültig.

### Welle zur Wissenskarte

Bisher „der zweite Ast von Welle 1b". Die Wissenskarte als eigene Kartensorte
(ADR-0002 mit Nachtrag), dazu der Ausschnitt als Quellgrafik für beide Sorten
(ADR-0013). Beschlossen im Interview am 04.10.2026. Kommt nach der Welle zur
Leseansicht. Ob der erste Schnitt vorher kommt, wird nach der Abnahme von 1d
geprüft, siehe „Quellgrafik aus PDFs, die nicht wie PlayDrill aufgebaut sind".
Tickets mit WK/ vorn.

- **Begriffe** stehen im Glossar: Wissenskarte, Ausschnitt, „Karte oder
  Übungskarte?", „Wissenskarte oder Prinzip?". „Karte" meint beide Sorten,
  „Bibliothek" `uebungen/` und `wissen/`.
- **Wofür:** Beim Planen begründet sie eine Übungswahl oder ein Prinzip. Dafür
  muss sie über Thema und Schwerpunkt zu finden sein.
- **Was Wissenskarte wird:** was keine Übung ist, aber sagen lässt, was es
  fürs Training heißt, ohne etwas zu erfinden. Bericht, Porträt, Werbung
  werden übersprungen. Eine Karte beantwortet eine Frage, ihr Titel ist diese
  Frage. Eine Fortsetzung, die dieselbe Frage beantwortet, ergänzt die Karte,
  ein langes Dokument wird eine Karte je Kapitel.
- **Die Karte:** `wissen/wi-######-<slug>.md`, die ID mit der Nummer des
  Trainers vorn und eigenem Zähler, vergeben bei der Freigabe.
  - Abschnitte `## Kernaussagen` und `## Was das fürs Training heißt`. Was die
    Quelle sagt, steht darin ohne Weiteres. Was der Entwurf ableitet, ist ein
    Vorschlag, den der Trainer bestätigt.
  - `thema`: Liste, Pflicht, aus `trainingslehre`, `methodik`, `psychologie`,
    `physiologie`, `ernaehrung`, `regelkunde`, `technik`, `taktik`.
  - `schwerpunkt`: freiwillig, inhaltliche und Steuerungsschwerpunkte, Abgleich
    mit der Disziplin wie bei der Übungskarte. Eine neue Kennung nur für
    Trainierbares, nach dem Ja des Trainers.
  - `disziplin` Pflicht ohne Vorgabe, `quelle` nie leer, `quelldatei`,
    `autor`, `angelegt` wie bei der Übungskarte.
  - `uebungen`: freiwillig, IDs der Übungen, die dazugehören. Der Linter meldet
    eine ID, die es nicht gibt. Die Übungskarte trägt nichts, die Gegenrichtung
    rechnet `index.py` aus.
  - Bilder stehen als Verweis im Text, an der Kernaussage, die sie zeigen. Kein
    Feld `schaubild`. Der Linter meldet einen Verweis ins Leere.
    `volleyball-schaubild` schlägt für Wissenskarten nichts vor.
  - Kein Feld für Alter oder Level.
- **Ausschnitt** (ADR-0013): Der Agent nennt Datei, bei einem PDF die Seite,
  und ein Rechteck in Prozent. Ein Skript schneidet aus dem Foto mit Pillow oder
  aus der mit `pypdfium2` gezeichneten PDF-Seite. Für Übungskarten und
  Wissenskarten, der Trainer sieht ihn bei der Freigabe.
  - `sammelimport.md` bekommt `quellgrafik: eingebettet | ausschnitt | keine`.
    `quellgrafik_ausschneiden: true` gilt weiter als `eingebettet`. Für einen
    neuen Quellenordner schlägt der Skill `ausschnitt` vor.
  - Fehlt `pypdfium2` oder Pillow, wo Ausschnitte gebraucht werden, bricht
    `vorbereiten` vor dem ersten Auftrag ab und schreibt nichts.
  - Bestehende Karten fasst die Welle nicht an.
- **Seitenbereich:** In der Spalte Dateien darf hinter einer Datei ein
  Seitenbereich stehen: `` `TechnikGuidelines.pdf` S. 12–15 ``. Der Auftrag
  bekommt nur diese Seiten, die Seiten kommen in `quelle`. Gilt für beide
  Sorten.
- **Sammelimport:**
  - Neues Ergebnis `wissen`, mit denselben Status wie Übungen.
  - `zurückgestellt` bleibt: kann später Karte werden, aber jetzt gibt es keine
    Sorte dafür, oder der Trainer holt es bewusst später. Der Zerlegungsplan
    schreibt es mit Grund, der Trainer kann bei der Freigabe zurückstellen.
    `übersprungen` bleibt für das, was nie Karte wird.
  - Zurückgestellte Zeilen kommen nur auf Ansage wieder dran („hol die
    zurückgestellten aus vm_09_2026"), mit ihrer alten Notiz in der
    Planeingabe. Die erste neue Zeile behält die alte Nummer.
  - Die Bibliotheksliste der Planeingabe führt die Wissenskarten mit.
  - Ein dritter Agent, `volleyball-wissenskarte`, gebaut wie der Kartenentwurf.
    `test_agenten.py` prüft ihn. Der Zerlegungsplan lernt nur das neue
    Ergebnis.
  - Die Zeile einer Wissenskarte nennt die Kandidaten der Übungen aus
    demselben Beitrag. `uebernehmen` trägt deren IDs in `uebungen` ein, sobald
    es sie gibt, egal was zuerst übernommen wird.
  - `ergänzt`: Nach dem Ja zu „Fortsetzung von wi-…" trägt der Skill neue
    Kernaussagen und Punkte fürs Training ohne Doppeltes ein und erweitert
    `quelle`, `quelldatei`, `thema`, `schwerpunkt`, `uebungen` und die
    Bildverweise. Er zeigt vorher, was dazukommt. ID und `angelegt` bleiben.
- **Einzelimport:** `volleyball-uebungsimport` lernt die Wissenskarte, der Name
  bleibt, die Beschreibung nennt beides. Duplikate prüft er über
  `suche.py --wissen --json`, das alle Wissenskarten ohne Filter auflistet.
- **Sonst:** Der Linter prüft Wissenskarten, `index.md` listet sie,
  `init_struktur.py` legt `wissen/` an.
- **Schnitte:**
  1. Ausschnitt, `quellgrafik:`, Seitenbereich, zuerst für Übungskarten,
     allein auslieferbar.
  2. Kartensorte: Schema, ID, Linter, `index.md`, `suche.py --wissen`,
     `init_struktur.py`, Datenmodell.
  3. Der Einzelimport.
  4. Der Zerlegungsplan mit `wissen`, dem Nachholen und der Bibliotheksliste.
  5. Agent, `pruefen` und `uebernehmen` für Wissenskarten, `uebungen`,
     Freigabe und Ergänzen im Skill.
  6. Abnahme.
- **Abnahme:**
  - Version installiert. In der `glossary.md` des Arbeitsordners sind die
    neuen Begriffe von Hand nachgezogen.
  - Ein Sammelimport über `jugendtrainerlehrgang/04_So_Vo` ergibt
    Übungskarten mit Ausschnitten aus PDF-Seiten.
  - Der erste Sammelimport über `vm_08_2026`: `ue-000030` bis `ue-000034`
    stehen als importiert, „Einarmig gehts auch, Teil 1" wird eine
    Wissenskarte mit Ausschnitt aus dem Foto.
  - In `vm_09_2026` werden die zurückgestellten Seiten 26 und 27 geholt. Sie
    ergänzen die Karte aus vm_08 oder werden eine eigene, in beiden Fällen
    mit `uebungen` `ue-000037` bis `ue-000041`.
  - `jugendtrainerlehrgang/03_Sa_Na` ergibt Wissenskarten mit Bildreihen als
    Ausschnitt.
  - Die Technik-Guidelines bekommen einen Plan mit Seitenbereichen je Technik
    und einen Durchgang über drei Techniken.
  - `Taktische_Aufschlaege.pdf` wird über den Einzelimport eine Wissenskarte
    mit `thema: [taktik]` und `schwerpunkt: [aufschlag]`. Beim zweiten
    Versuch erkennt er das Duplikat.
  - Der Linter meldet nichts, `index.md` listet die Wissenskarten,
    `suche.py --wissen` findet sie.
  - Die Tokens je Entwurf einer Wissenskarte stehen als Nachtrag in ADR-0009.
- **Version:** ein kleiner Sprung, kein Arbeitsordner bricht.

### Welle 2

Das Trainingsdesign auf Disziplin umstellen. Der Zugriff auf Wissenskarten über
die Suche, mit Filtern nach Thema und Schwerpunkt, und über die
Trainingsplanung. Wie eine Leseansicht die Bilder einer Wissenskarte zeigt,
deren Verweise im Text stehen. Die Verbindung von Prinzip und Wissenskarte im
Saisonplaner.

In Welle 1b wurde am Trainingsdesign nur der Abschnitt zum Schaubild angefasst,
der Rest des Skills blieb liegen und gehört hierher.

### Welle 3

Die Saisonfrage. Hallenjahr und Beachsommer passen nicht in das eine
`saison`-Feld der Wurzeldatei.

### Welle zum Stationsbetrieb

Den Stationsbetrieb als zweite Geometrie behandeln, über Feld und freie
Leinwand hinaus. Etwa eine Grundform „Zirkel": Die Stationen stehen nummeriert
im Kreis, mit einem Pfeil für den Wechsel, und der Trainer zählt nur die
Stationen auf, die Anordnung übernimmt das Skript. Das ist neues Vokabular und
braucht ein eigenes Interview und eine Spec. In #10 bewusst ausgelassen, am
02.10.2026 als eigene Welle beschlossen, mit der niedrigsten Priorität.
