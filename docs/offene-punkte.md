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
ein Ticket bekommen, siehe den Nachtrag in #29. Bei der Durchsicht am
05.10.2026 nach der Abnahme (#37) ebenso: #75 und #76 kommen in die Welle zur
Leseansicht, #77 davor. Der Ausschnitt für PDFs, die nicht wie PlayDrill
aufgebaut sind, bleibt in der Welle zur Wissenskarte (#62 bis #65), nach der
Welle zur Leseansicht. Beim Bau der Welle zur Leseansicht am 06.10.2026 kamen
Punkte aus #52 bis #59, #75, #76 und dem Code-Review dazu. Was davon die Abnahme prüfen soll,
steht als Kommentar in #60, der Rest hier mit Ziel. Bei der Abnahme (#60) am
25.10.2026 ist die Liste durchgesehen worden: Kein Auslöser ist eingetreten,
zwei Punkte aus der Abnahme stehen unter „Bewusst nicht gebaut", und der
Abschnitt zur Welle zur Leseansicht ist weggefallen. Beim Bau der Welle zur
Wissenskarte am 14. und 19.10.2026 kamen Punkte aus #62 bis #64, #66 bis #73
und dem Code-Review dazu. Was davon die Abnahme prüfen soll, steht als
Kommentar in #65 und #74, der Rest hier mit Ziel. Mit der Abnahme des
Ausschnitts (#65) am 25.10.2026 ist der Riegel gefallen: Ein Sammelimport über
PDFs, die nicht wie PlayDrill aufgebaut sind, läuft mit `quellgrafik:
ausschnitt`. Von dem, was bei dieser Abnahme liegen blieb, stehen zwei Punkte
in #78, zwei als Kommentar in #74 und zwei unter „Bewusst nicht gebaut“.
Bei der Abnahme der Wissenskarte (#74) vom 25. bis 27.10.2026 ist die Liste
durchgesehen worden. Eingetreten ist nur der Auslöser bei den langen Titeln,
und zwar bei Wissenskarten. Das nimmt #79 auf, der Punkt gilt jetzt nur noch
für Übungskarten. Aus der Abnahme kamen #79, ein Punkt für Welle 2 und zwei
unter „Bewusst nicht gebaut“. Drei Auslöser nannten die Abnahme selbst und
nennen jetzt einen Sammelimport. Mit #79 ist die Welle zur Wissenskarte am
31.10.2026 abgeschlossen, ihr Abschnitt unter „Was als Nächstes ansteht“ ist
weggefallen. Offen sind hier nur noch Punkte für Welle 2.

### DVV Plan 1 als Übungsfolge mit ID

Die Athletik steht in den Plänen mit „—" in der Spalte ID, die Übungen sind im
Plan ausgeschrieben. Der DVV-Athletikplan ist laut Glossar eine Übungsfolge und
gehört als Karte nach `uebungen/`. Dann könnte ein Programmpunkt auf die Karte
zeigen, statt die Übungen in jeden Plan zu kopieren. Fiel im Interview zur Welle
zur Leseansicht auf, ist aber Arbeit an der Bibliothek.

Ziel: Welle 2.

### „Block“ für den Trainingsblock

Aus #59. `TRAININGSDESIGN.md` sagt „siehe aktiven Block in `mesozyklen/`“ und
„frühe Einheiten im Block“, der Skill `volleyball-saisonplaner` an mehreren
Stellen „Block“ und „Blöcke“ für den Trainingsblock. Die Block-Regel im Glossar
lässt „Block“ allein nur für das Technikelement zu. Die Welle zur Leseansicht
hat nur „Teil“ für den Programmpunkt bereinigt.

Ziel: Welle 2, die das Trainingsdesign und den Saisonplaner ohnehin anfasst.

### `suche.py --lang` zeigt keinen Hintergrund

Aus #67. Welche Wissenskarten auf eine Übung zeigen, steht in `index.md` in der
Spalte „Hintergrund" und bei `suche.py --json` unter `hintergrund`. Die lange
Ausgabe mit `--lang` nennt es nicht.

Ziel: Welle 2, mit der Suche nach Wissenskarten.

### `index.md` für beide Kartensorten

Aus #74. Die Spalte „Hintergrund“ bei den Übungen nennt nur die IDs der
Wissenskarten, etwa `wi-000004, wi-000006, wi-000009`. Worum es geht, muss man
nachschlagen. Und die Datei heißt weiter „# Übungsindex“, obwohl unten 27
Wissenskarten nach Thema stehen. Abhilfe wäre die Frage als Link in der Spalte
und ein Titel, der beide Sorten meint.

Ziel: Welle 2, mit dem Zugriff auf Wissenskarten.

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

### Nach einem Schaubild wird die Leseansicht eingebettet neu gebaut

Aus #76. Der Skill `volleyball-schaubild` baut die betroffenen Leseansichten
mit der Voreinstellung von `leseansicht.py`, die Bilder also eingebettet. Eine
Leseansicht, die mit `--bilder verweis` gebaut war, ist danach eingebettet und
größer. Meldungen über Zeitangaben ohne Programmpunkt gibt er dabei nicht
weiter, die kommen mit Exitcode 0. Weiter gibt er nur, was den Neubau
scheitern lässt (#75).

Ziel: bewusst nicht. Auslöser: Ein Trainer baut Leseansichten mit `verweis`
und vermisst es nach einem Neubau, oder eine Meldung geht beim Neubau
verloren.

### Ein Link mit `javascript:` im Plan

Aus #52. Ein Markdown-Link im Trainingsplan kommt mit seinem Ziel in die
Leseansicht, auch `[x](javascript:…)`. Maskiert wird wie vorher, der Plan ist
der eigene des Trainers.

Ziel: bewusst nicht. Auslöser: Trainingspläne kommen aus fremden Quellen.

### Andere Skripte bei einer gesperrten Datei

Aus #75. `leseansicht.py` meldet eine gesperrte Zieldatei ohne Traceback.
`export_pdf.py` und die übrigen Skripte, die Dateien schreiben, brechen in dem
Fall weiter mit einem Traceback ab. Das Ticket hat sie ausgenommen.

Ziel: bewusst nicht. Auslöser: Ein gesperrtes PDF oder eine gesperrte Karte
bricht ein Skript in der Halle oder beim Import ab.

### Grenzfälle der Athletiktabelle

Aus #55. Eine Tabelle wird nur dann eine Liste zum Aufklappen, wenn ihre
ersten Spalten genau `Nr` und `Übung` heißen, und die Dosierung kommt nur aus
einer Spalte `Heute`. `Nr.` oder `Dosierung` lässt sie eine Tabelle bleiben.
Steht in `Nr` schon „1.“, erscheint „1.. Übung“, ist `Nr` leer, „. Übung“.
Sind die übrigen Zellen einer Zeile leer, klappt der Eintrag ins Leere auf.

Ziel: bewusst nicht. Auslöser: Ein echter Plan schreibt die Tabelle so. Bei
der Abnahme (#60) schrieben alle Pläne im Arbeitsordner genau
`Nr | Übung | Worauf es ankommt | Heute`.

### „Skizze vergrößern“ unter Nachschlagen

Aus #57 und der Abnahme (#60). Den Knopf gibt es nur unter Hallenskizzen in
einem Programmpunkt. Eine Skizze in einem Thema unter Zum Nachschlagen hat
keinen. Bei der Abnahme war alles auf dem Handy gut lesbar.

Ziel: bewusst nicht. Auslöser: Eine Skizze unter Nachschlagen ist auf dem
Handy zu klein.

### Eine Leseansicht, die dauerhaft gesperrt bleibt

Aus der Abnahme (#60). `2026-10-01.html` trägt seit dem 05.10.2026 vom
Nextcloud-Client einen Eintrag, der Benutzern Schreiben und Löschen verweigert,
und lässt sich wegen eines Nextcloud-Fehlers nicht entsperren. `leseansicht.py`
meldet das (#75), die Leseansicht bleibt aber auf dem alten Stand. Ein anderer
Name ginge nur von Hand über `--out`, und weder Skill noch Skript bieten ihn an.
Die Abnahme hat die Datei übersprungen.

Ziel: bewusst nicht. Auslöser: Eine gesperrte Leseansicht wird für eine
kommende Einheit gebraucht.

### Gleiche Überschriften unter „Zum Nachschlagen“

Aus #56. GitHub hängt an den Anker einer zweiten gleichen Überschrift `-1`
an, der Generator nicht. Steht „### Regeln“ unter Vorbereitung und unter Zum
Nachschlagen, verfehlt der Link aus der `.md` den Reiter. Ebenso bekäme ein
Thema namens „Vorbereitung“ oder „Nachschlagen“ denselben Anker wie die festen
Abschnitte.

Ziel: bewusst nicht. Auslöser: Ein Verweis in einem echten Plan trifft
deshalb nicht.

### Eine Leseansicht mit Sprungziel in der Adresse

Aus #56. Wird die Datei mit Sprungziel geöffnet, etwa
`2026-10-01.html#die-sechser`, springt der Browser zum Abschnitt unten, das
Skript öffnet aber nicht die Ansicht mit dem Reiter.

Ziel: bewusst nicht. Auslöser: Jemand teilt einen Link auf einen Reiter.

### Dieselbe Karte in zwei Programmpunkten

Aus #57. Jedes Schaubild steht einmal je Programmpunkt in der Datei, die
Ansicht zum Vergrößern bettet es nicht noch einmal ein. Nennt ein Plan
dieselbe Karte in zwei Programmpunkten, ist ihr Bild zweimal eingebettet.

Ziel: bewusst nicht. Auslöser: Ein Plan nennt dieselbe Karte zweimal, und die
Datei wird für WhatsApp zu groß.

### Parallele Testläufe und die PNGs der Schaubilder

Aus #58. `schaubild.py` legt PNGs in ein gemeinsames
`%TEMP%\volleyball-schaubild\`, und `Arbeitsordner.starte()` gibt keinem
Testlauf ein eigenes Temp-Verzeichnis. Liefen bei der Welle zur Leseansicht
sechs Suiten zugleich, scheiterten einmal zwei Schaubild-Tests mit „kein PNG
entstanden“. Allein laufen sie grün.

Ziel: bewusst nicht. Auslöser: Parallele Implementierer werden die Regel.
Dann setzt `starte()` TEMP und TMP je Arbeitsordner.

### Ein maskierter Strich in anderen Tabellen

Aus dem Code-Review der Welle zur Leseansicht. Die Zerlegung einer
Tabellenzeile steht jetzt als `tabellenzellen` in `tpdaten.py`, und die
Leseansicht lässt `\|` in seiner Zelle. `tpdaten.lies_schwerpunkt_zeilen` und
drei Testhelfer (`arbeitsordner.py`, `test_sammelimport.py`, `test_index.py`)
zerlegen weiter ohne `\|`.

Ziel: bewusst nicht. Auslöser: Ein Klartext in `schwerpunkte.md` enthält ein
`|`.

### Der Schleier hinter einer Ansicht in älteren Browsern

Aus dem Code-Review der Welle zur Leseansicht. Hinter einer geöffneten Ansicht
liegt ein Schleier aus der Palette. Ältere Browser geben die Variablen nicht an
`::backdrop` weiter, dort ist er auch im Dunkeln der helle.

Ziel: bewusst nicht. Auslöser: Jemand meldet einen zu hellen Schleier auf
einem älteren Handy.

### Frontmatter und Dauer in den Vorlagen

Aus #59. `VORLAGEN.md` führt `meso_woche: <n>` im Frontmatter des
Trainingsplans, die Saat-Vorlage und `DATENMODELL.md` nicht, und kein Skript
liest es. Die Saat-Vorlage hat `dauer: 120`, ihre Beispielzeilen enden bei 90.
Beides war schon vor der Welle so.

Ziel: bewusst nicht. Auslöser: Ein Skill oder Skript liest `meso_woche`, oder
ein Trainer stolpert über die Dauer in einem neuen Arbeitsordner.

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

### Lange Titel von Übungskarten

Die Titel der 30 Karten aus dem ersten Durchgang über PlayDrill beschreiben
ganze Abläufe, etwa „Dankeball auf der Abwehrposition hoch in die Feldmitte
spielen und dann zuspielen". Die Dateinamen von Karte und Quellgrafik werden
damit bis zu 95 Zeichen lang. Die Karten von Hand haben kurze Titel. Der
Trainer hat alle 30 so freigegeben. Abhilfe wäre eine Längengrenze im
Agenten oder ein gekürzter Name beim Übernehmen.

Bei der Abnahme der Wissenskarte (#74) hat der Trainer 9 von 30 Titeln von
Wissenskarten gekürzt, 7 davon waren zwei Fragen in einer, 2 eine lange
Frage. Das nimmt #79 auf. Für Übungskarten gilt der Punkt weiter.

Ziel: bewusst nicht. Auslöser: Der Trainer kürzt Titel von Übungskarten bei
der Freigabe regelmäßig, oder ein Pfad wird für Windows oder Nextcloud zu
lang.

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

### Ein durchsichtiges PNG als Ausschnitt

Aus #62. Ein Ausschnitt aus einem Foto wird ein JPEG. Ein PNG mit
durchsichtigen Flächen verliert dabei seinen Alphakanal, und diese Flächen
werden dunkel.

Ziel: bewusst nicht. Auslöser: Eine Quellgrafik aus einem durchsichtigen PNG
kommt schwarz auf die Karte.

### Jede Seite eines geteilten PDF in einer Zeile

Aus #64. Teilt der Zerlegungsplan ein PDF in Seitenbereiche, gilt die Datei
beim nächsten Lauf nicht mehr als neu. Der Agent soll deshalb jede Seite in
eine Zeile bringen, notfalls als `übersprungen`. Ein Skript prüft das nicht.
Eine vergessene Seite käme nie wieder in eine Planeingabe.

Ziel: bewusst nicht. Auslöser: Bei einem Sammelimport bleibt eine Seite in
keiner Zeile stehen. Bei der Abnahme (#74) stand jede Seite in einer Zeile.

### Eingebettete Quellgrafik und Seitenbereich

Aus #63 und #64. Bei `quellgrafik: eingebettet` nimmt `vorbereiten` das größte
eingebettete Bild des ganzen PDF, auch wenn der Kandidat nur einige Seiten
nennt. Auf die Seiten zu beschränken hieße, den Seitenbaum des PDF zu lesen.
Das kann der Leser der Standardbibliothek nicht, und Objektströme liest er auch
nicht. PlayDrill hat eine Übung je Datei und keine Seitenbereiche.

Ziel: bewusst nicht. Auslöser: Ein Quellenordner mit eingebetteten Bildern
braucht Seitenbereiche, oder ein Bild kommt von der falschen Seite.

### Seiten zählen ohne `pdftotext` und `pypdfium2`

Aus dem Code-Review der Welle zur Wissenskarte. `vorbereiten` zählt die Seiten
eines PDF mit `pdftotext`, sonst mit `pypdfium2`. Fehlen beide, bricht es bei
einem Seitenbereich nicht ab. Es schreibt die Aufträge und nennt jede Zeile,
deren Seitenbereich es nicht prüfen konnte. Beide Werkzeuge sind freiwillig
(ADR-0008, ADR-0013).

Ziel: bewusst nicht. Auslöser: Ein Agent sucht trotz dieser Meldung Seiten,
die es nicht gibt.

### Seiten lesen ohne Seitenbilder

Aus der Abnahme #65. Seiten als Bild legt `vorbereiten` nur bei `quellgrafik:
ausschnitt` neben den Auftrag. Hat ein PDF bei `eingebettet` oder `keine`
keinen Text oder einen Seitenbereich, sagt der Auftrag, der Agent lese das PDF
selbst, nur diese Seiten. Seitenweise zeichnet sein Werkzeug ein PDF aber mit
`pdftoppm`, und das fehlt unter Windows (ADR-0013, Nachtrag vom 25.10.2026).

Ziel: bewusst nicht. Auslöser: Ein Quellenordner mit `eingebettet` oder
`keine` braucht Seitenbereiche oder hat PDFs ohne Text.

### Die Seiten eines Seitenbereichs an drei Stellen

Aus dem Code-Review von 3.2.1. `sammelimport.py` zählt die Seiten eines
Seitenbereichs an drei Stellen mit `range(….erste, ….letzte + 1)` aus. Die
Dataclass `Seitenbilder` steht bei ihrer Funktion, nicht oben bei den anderen.

Ziel: bewusst nicht. Auslöser: Diese Stellen in `sammelimport.py` werden
wieder angefasst.

### Die Datei einer zurückgestellten Zeile fehlt

Aus #69. `vorbereiten --plan --zurueckgestellte` nennt die Dateien jeder
zurückgestellten Zeile. Fehlt eine davon im Quellenordner, steht sie trotzdem
in der Planeingabe, mit dem Pfad aus der Zeile.

Ziel: bewusst nicht. Auslöser: Das passiert bei der Abnahme oder danach.

### Steuerungsschwerpunkte auf einer Übungskarte

Aus #70. Die Tabelle der Kennungen im Auftrag nennt die Steuerungsschwerpunkte
auch für Übungen, und der Linter nimmt sie auf einer Übungskarte an. Gedacht
sind sie für Wissenskarten.

Ziel: bewusst nicht. Auslöser: Eine Übungskarte trägt einen
Steuerungsschwerpunkt.

### Ein falsches `Übungen:` in einer Zeile

Aus #72. Ob die Nummern und IDs hinter `Übungen:` stimmen, prüft erst das erste
`vorbereiten` nach der Freigabe des Plans. Dann muss der Trainer die Zeile von
Hand berichtigen, denn der Skill schreibt die Übersicht nur bei der Freigabe des
Plans. Abhilfe wäre, dass schon `vorbereiten --plan` die Angabe prüft.

Ziel: bewusst nicht. Auslöser: Das passiert bei einem Sammelimport. Bei der
Abnahme (#74) stimmte jedes `Übungen:`.

### Eine Übung aus `Übungen:` streichen

Aus #72. Bei der Freigabe kann der Trainer eine ID auf der Wissenskarte
ergänzen. Eine Nummer aus `Übungen:` herausnehmen kann er nicht, denn die Zeile
schreibt der Skill nur bei der Freigabe des Plans.

Ziel: bewusst nicht. Auslöser: Ein Trainer will eine Übung aus dem Beitrag
nicht an der Wissenskarte haben.

### Abbruch beim Übernehmen einer Übung oder Fortsetzung

Aus #72 und #73. `uebernehmen` setzt die Zeile einer Übung auf `importiert`,
bevor es ihre ID in die Wissenskarte schreibt. Bricht der Lauf dazwischen ab,
fehlt die Übung auf der Wissenskarte, ohne Meldung. Beim Ergänzen einer
Wissenskarte schreibt es erst die Karte und verschiebt dann die Bilder. Bricht
es dazwischen ab, findet ein zweiter Lauf keine Verweise mit den Namen aus dem
Entwurf mehr, löscht die Bilder mit dem Entwurf, und der Linter meldet tote
Bildverweise.

Ziel: bewusst nicht. Auslöser: Nach einem abgebrochenen Lauf fehlt einer
Wissenskarte eine Übung oder ein Bild.

### Ein Bildverweis mit `./` vorn

Aus #71. Im Entwurf einer Wissenskarte zählt nur der bloße Name eines
Ausschnitts, etwa `![…](17.quellgrafik.png)`. Schreibt der Agent
`./17.quellgrafik.png`, weist `pruefen` den Entwurf ab.

Ziel: bewusst nicht. Auslöser: Der Agent schreibt den Verweis bei einem
Sammelimport so. Bei der Abnahme (#74) hat er es nie getan.

### Ein TIFF oder HEIC, auf das eine Wissenskarte zeigt

Aus #66. `bilder_aufbereiten.py` lässt ein TIFF oder HEIC liegen, wenn eine
Übungskarte in `quelldatei` darauf zeigt. Die Wissenskarten liest es dafür
nicht. Zeigt eine Wissenskarte auf ein solches Bild, wird es trotzdem zum
JPEG, und ihre `quelldatei` zeigt ins Leere. Dazu passt „Ein HEIC, das schon
im Zerlegungsplan steht".

Ziel: bewusst nicht. Auslöser: Eine Wissenskarte zeigt auf ein TIFF oder HEIC.

### Verzweigungen nach Kartensorte im Sammelimport

Aus dem Code-Review der Welle zur Wissenskarte. `sammelimport.py` fragt an
vielen Stellen, ob ein Kandidat eine Übungskarte oder eine Wissenskarte wird,
und wählt danach Texte, Prüfungen und Ziele. Das an einer Stelle zu bündeln,
hieße, das Skript umzubauen.

Ziel: bewusst nicht. Auslöser: Eine dritte Kartensorte kommt dazu.

### Ein Quellenordner mit eigenen Quellenordnern darunter

Aus #74. `vorbereiten` nimmt jede Datei des Quellenordners samt Unterordnern.
Liegt darunter ein Ordner mit eigener `sammelimport.md`, etwa `03_Sa_Na` unter
`jugendtrainerlehrgang`, gelten dessen Dateien im oberen Ordner als neu, obwohl
sie schon in seiner Übersicht stehen. Bei der Abnahme ist das PDF der
Technik-Guidelines deshalb aus `jugendtrainerlehrgang` in einen eigenen Ordner
`swissvolley` gewandert. Abhilfe wäre, dass `vorbereiten` Unterordner mit
eigener `sammelimport.md` überspringt.

Ziel: bewusst nicht. Auslöser: Ein Ordner, unter dem schon Quellenordner
liegen, soll selbst als Ganzes importiert werden.

### Office-Dateien im Quellenordner

Aus #74. Ein Word-Dokument, eine Präsentation oder eine Tabelle liest weder
`pdftotext` noch das Werkzeug der Agenten. In `03_Sa_Na` steht deshalb die
Datei `03-2 … nach Weineck.doc` unter `ohne`. Wer so eine Datei braucht,
speichert sie als PDF in denselben Ordner und nimmt sie aus `ohne`, dann holt
der nächste Plan sie.

Ziel: bewusst nicht. Auslöser: Eine Datei soll Karte werden, die sich nicht
als PDF speichern lässt.

## Was als Nächstes ansteht

Die Reihenfolge stammt aus #10 und ist dort begründet. Der Sammelimport kam am
30.09.2026 davor und ist Welle 1d (#29), abgenommen und geschlossen am
05.10.2026. Die PlayDrill-Bibliothek braucht die Wissenskarte nicht, und die
Wissenskarte kann danach den Sammelimport um ihre Kartensorte erweitern.
Zwischen 1d und die Wissenskarte kam die Welle zur Leseansicht (#50),
beschlossen am 02.10.2026, abgenommen am 25.10.2026 mit 3.1.1 (#60). Die
Welle zur Wissenskarte (#61), festgelegt am 04.10.2026 im Interview, ist am
27.10.2026 abgenommen (#74) und am 31.10.2026 mit 3.2.3 abgeschlossen (#79).
Was sie gebracht hat, steht in ADR-0002 und ADR-0013, im Glossar und in
`DATENMODELL.md`.

Reihenfolge seit dem Ende der Welle zur Wissenskarte am 31.10.2026, wie in
#10 angelegt:

1. Welle 2.
2. Welle 3.
3. Die Welle zum Stationsbetrieb, mit der niedrigsten Priorität.

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
