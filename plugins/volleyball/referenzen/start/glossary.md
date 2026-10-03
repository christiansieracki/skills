# Glossar

Der eine Ort für Begriffsregeln. Alle Dokumente in diesem Ordner und alle
volleyball-Skills halten sich daran.

## Die Bausteine der Bibliothek

| Begriff | Was es ist | Wo es liegt |
|---|---|---|
| **Übung** | Eine einzelne Karte. Lässt sich allein in einen Programmpunkt setzen, meist 8 bis 25 Minuten. | `uebungen/ue-######-*.md` |
| **Übungsfolge** | Ein fertiger Ablauf, der nur als Ganzes Sinn ergibt, weil Reihenfolge und Dosierung dazugehören. Ein DVV-Athletikplan ist so eine. | `uebungen/`, mit `typ: folge` |
| **Übungsquelle** | Ein Fremddokument, aus dem Übungen gezogen wurden. Bleibt als Datei liegen, wird nie selbst zur Karte. | `quellen/` |
| **Prinzip** | Eine Regel, die über Übungen hinweg gilt, zum Beispiel „maximal drei Annahmespieler im Riegel". Hängt am Team, nicht an der Übung. | `teams/<team>/team-profil.md` |

Die Grenze beim Importieren: Lässt sich das Teil aus dem Zusammenhang reißen
und einzeln einsetzen? Dann Übung. Nur als Ganzes sinnvoll? Dann Folge. Ist es
ein kompletter Trainingsabend? Dann Quelle, aus der Übungen gezogen werden.

## Die ID und die Nummer des Trainers

| Begriff | Was es ist | Wo es liegt |
|---|---|---|
| **Nummer des Trainers** | Zwei Ziffern für jeden Trainer, der Übungen anlegt. Sie stehen vorn in jeder ID, die er vergibt: `ue-010001` ist die erste Übung von Trainer 01. Die Karten aus der Zeit vor den sechsstelligen IDs tragen `00`. | `trainingsplanung-root.yml`, unter `trainer:` |
| **Bereich** | Alle IDs mit derselben Nummer des Trainers vorn. Jeder Trainer vergibt nur in seinem eigenen Bereich, die höchste Nummer darin plus eins. So vergeben zwei Trainer nie dieselbe ID, auch wenn Nextcloud ihre Rechner noch nicht abgeglichen hat. | `uebungen/ue-01####-*.md` für Trainer 01 |

Unter `trainer:` steht auch, an welchen Rechnern ein Trainer sitzt. Erkannt
wird ein Rechner an seinem Namen. Ein Rechner, der dort fehlt, bekommt keine
ID, bis jemand sagt, wer an ihm sitzt.

**Bereich oder Zone?** „Bereich“ allein meint in diesem Ordner immer die IDs
eines Trainers. Ein Stück Boden im Schaubild ist eine Zone, auch wenn es
Aufschlagbereich heißt.

## Sammelimport

| Begriff | Was es ist | Wo es liegt |
|---|---|---|
| **Quellenordner** | Ein Ordner mit Übungsquellen, die zusammen importiert werden, etwa eine PlayDrill-Bibliothek oder die Fotos eines Magazinhefts. Trägt die Absprachen, die für alle Karten daraus gelten. | `quellen/<ordner>/` mit `sammelimport.md` |
| **Sammelimport** | Der Import über einen ganzen Quellenordner: erst der Zerlegungsplan, dann die Kartenentwürfe, dann die Freigabe. Läuft über mehrere Sitzungen und macht dort weiter, wo er aufgehört hat. | `sammelimport.md` im Quellenordner |
| **Zerlegungsplan** | Die Liste, welche Dateien welche Karte ergeben, ob daraus eine Übung oder eine Folge wird und was liegen bleibt. Wird freigegeben, bevor der erste Kartenentwurf entsteht. | bis zur Freigabe `kartenentwuerfe/<ordner>/zerlegungsplan.md`, danach in `sammelimport.md` |
| **Kandidat** | Eine Zeile im Zerlegungsplan: die Dateien, aus denen eine Karte werden soll. Aus jedem Kandidaten entsteht ein Kartenentwurf. | in `sammelimport.md` |
| **Kartenentwurf** | Eine Karte, die noch nicht freigegeben ist. Hat keine ID, liegt nicht in `uebungen/`, und die Suche findet sie nicht. | `kartenentwuerfe/<ordner>/` |
| **Quellgrafik** | Das Bild aus der Übungsquelle selbst, etwa die Feldskizze eines PlayDrill-Blatts oder ein Stationsaufbau. Der Sammelimport schneidet sie aus dem PDF aus, bei der Freigabe wird sie das Schaubild der Karte. Ein Kandidat aus mehreren Blättern, etwa ein Zirkel, hat eine je Blatt mit Bild. Anders als ein gezeichnetes Schaubild hat sie keine Szene und wird nie neu erzeugt. | `kartenentwuerfe/<ordner>/17.quellgrafik.png`, bei mehreren `17.quellgrafik-1.png` und weiter, danach `schaubilder/ue-######-*.png` |
| **Rückfrage** | Was ein Kartenentwurf vom Trainer wissen muss, bevor er Karte werden kann. Etwa ein Ablauf, der nur aus dem Bild gelesen ist, oder ein Verdacht auf ein Duplikat. | im Kartenentwurf |
| **Vermutung** | Wie der Kartenentwurf eine Rückfrage vorläufig beantwortet. Sie steht im Text des Entwurfs, und die Rückfrage nennt sie. Nicht jede Rückfrage hat eine. | im Kartenentwurf |
| **Freigabe** | Das Ja des Trainers. Damit wird aus dem Kartenentwurf eine Karte mit ID. | danach `uebungen/` |

Ein Kartenentwurf trägt, was die Quelle belegt. Was er deutet, steht als
Vorschlag mit kurzer Begründung drin, und der Trainer bestätigt oder kippt es
bei der Freigabe. Hat die Quelle eine Lücke, wird nichts erfunden. Dann ist es
eine Rückfrage, und was der Entwurf dazu vermutet, steht als Vermutung dabei.
Auch die bestätigt oder kippt der Trainer.

**Kandidat oder Einheit?** Einheit heißt in diesem Ordner immer
Trainingseinheit. Was im Sammelimport zur Karte werden soll, ist ein Kandidat.

## Team und Trainingsgruppe

| Begriff | Was es ist |
|---|---|
| **Team** | Die Wettkampfmannschaft. Hat ein Team-Profil und meistens einen Saisonplan mit Mesozyklen. |
| **Trainingsgruppe** | Wer zusammen in der Halle steht. Daran hängen die Trainingseinheiten. |

Beides kann zusammenfallen, muss aber nicht. Zwei Mannschaften, die zusammen
trainieren, sind zwei Teams und eine Gruppe. Welche Gruppe welche Teams
abdeckt und welches Team führt, steht in `trainingsplanung-root.yml`.

## Trainingsplan und Leseansicht

| Begriff | Was es ist |
|---|---|
| **Trainingsplan** | Die `.md` einer Einheit. Das ist die Quelle, hier wird geändert. |
| **Ablauf** | Die Folge der Programmpunkte einer Einheit, als Tabelle im Trainingsplan. |
| **Programmpunkt** | Eine Zeile der Ablauftabelle: Zeitangabe, Name und meist eine Übung. Auch Pause und Umbau sind Programmpunkte. Laufen zwei gleichzeitig, steht beim Namen der Hallenteil: „Zuspiel, Hallenteil A". |
| **Zeitangabe** | Von–bis in Minuten ab Beginn der Einheit, wie in der Spalte Zeit: „46–93". Mit dem Hallenteil bestimmt sie einen Programmpunkt eindeutig. |
| **Abschnitt** | Ein Stück des Trainingsplans unter einer Überschrift (`##` oder `###`). |
| **Hallenskizze** | Die Zeichnung im Trainingsplan, wie die Halle in einem Programmpunkt an diesem Abend aufgebaut ist, mit Zeichen in einem Codeblock gezeichnet. Gehört zum Abend, nicht zur Übung. |
| **Leseansicht** | Die daraus erzeugte Fassung als HTML fürs Handy und als PDF zum Ausdrucken. Darf jederzeit weggeworfen und neu gebaut werden. |

Wer in die Leseansicht tippt, verliert seine Änderung beim nächsten Erzeugen.
Änderungen gehören immer in die `.md`.

Beginnt die Überschrift eines Abschnitts mit einer Zeitangabe, gehört der
Abschnitt zu diesem Programmpunkt: `## 46–93 Drei Sechser mit Zweierserie`.
Laufen zwei Programmpunkte zur selben Zeit, kommt der Hallenteil dazu:
`### 69–89 Hallenteil A: Hallenskizze`. Ohne ihn gilt der Abschnitt für beide.
In der Leseansicht steht er dort, wo man den Programmpunkt aufklappt.

**Schaubild oder Hallenskizze?** Das Schaubild gehört zur Karte und zeigt die
Übung. Die Hallenskizze gehört zum Trainingsplan und zeigt, wie die Übung an
diesem Abend steht. In der Leseansicht heißt das eine „Schaubild der Karte",
nie „Grundform": Grundform ist, worauf eine Szene gezeichnet wird.

## Szene und Schaubild

| Begriff | Was es ist | Wo es liegt |
|---|---|---|
| **Szene** | Die Beschreibung eines Schaubildes in YAML, in Metern gerechnet. Das ist die Quelle, hier wird geändert. | `schaubilder/ue-000042.szene.yml` |
| **Schaubild** | Das Bild, das daraus entsteht. Ein Erzeugnis: es wird beim nächsten Mal überschrieben. | `schaubilder/ue-000042.svg` |
| **Grundform** | Worauf eine Szene gezeichnet wird: eine Feldvorlage oder eine freie Leinwand. | in der Szene, als `form:` |
| **Feldvorlage** | Ein Spielfeld als Grundform: Halle 9×18 m oder Beach 8×16 m, mit den Linien, die es dort wirklich gibt. | `form: halle`, `form: beach` |
| **freie Leinwand** | Eine Fläche mit angesagtem Maß in Metern, ohne Spielfeld darauf. Für einen Aufbau, der auf kein Feld passt. | `form: frei` mit `groesse:` |
| **Zone** | Eine Fläche im Schaubild, die etwas bedeutet: eine Zielzone, ein Aufschlagbereich, das abgedeckte Stück Feld. Hat Rand und Beschriftung. | in der Szene, unter `zonen:` |
| **Gerät** | Ein Kasten, ein Ballwagen, eine Zielmatte im Schaubild, aus Rechtecken und Kreisen zusammengesetzt und beschriftet. | in der Szene, unter `geraete:` |
| **Stelle** | Ein Ort im Schaubild, der einen Namen braucht, ohne dass dort etwas steht: die Feldmitte, zu der gespielt wird, der Startpunkt eines Laufwegs, eine Linie des Feldes. Nur ein Wort, keine Fläche. | in der Szene, unter `stellen:` |
| **Maßkette** | Eine Abstandsangabe als Linie mit Maßstrichen und der gemessenen Zahl. Der beschriftete Pfeil daneben zeigt denselben Abstand anders. | in der Szene, unter `abstaende:` |
| **Textwerk** | Was neben dem Bild steht: Titel und Untertitel oben, die Legende daneben, die Fußzeile mit Zeichenerklärung und Quelle darunter. Es macht aus einer Skizze eine Anleitung. | in der Szene, ganz außen |
| **Legendenblock** | Ein Stück der Legende: eine Überschrift und die Zeilen darunter. Mehrere davon ergeben die Legendenspalte neben dem Bild. | in der Szene, unter `legende:` |

Dasselbe Verhältnis wie zwischen Trainingsplan und Leseansicht: Wer in das SVG
tippt, verliert es beim nächsten Erzeugen. Änderungen gehören in die Szene.

Was aufs Feld passt, wird aufs Feld gezeichnet und hat seinen Maßstab damit
geschenkt. Die freie Leinwand ist für den Rest da. Maßstäblich sind beide, und
eine Abstandsangabe darin auch.

**Zone oder Gerät?** Ein Gerät ist ein Gegenstand, den jemand in die Halle
stellt. Eine Zone ist eine Absprache über ein Stück Boden. Beide sind Flächen
mit Rand und Beschriftung und sehen deshalb im Bild verschieden aus: Wer den
Unterschied nicht sieht, räumt einen Kasten weg, wo nie einer stand.

**Zone oder Stelle?** Eine Zone ist eine Absprache über ein Stück Boden und hat
eine Fläche. Eine Stelle ist nur der Name eines Ortes, an dem nichts steht.
Steht dort jemand oder etwas, trägt dessen Marker oder Gerät den Namen, und es
braucht keine Stelle.

**Hervorgehoben** wird ein Spieler, der in der Übung eine Sonderrolle hat: der
Zuspieler, der nicht mitrotiert, oder der Angreifer auf der Kiste, der die
Bälle bringt. Sein Marker fällt auf einen Blick auf, die anderen bleiben
Umriss. Worin die Sonderrolle besteht, sagt die Legende.

Plätze heißen in der Halle nach ihrer **Positionsnummer** 1 bis 6, im Sand nach
einer **Rolle**. Im Sand gibt es keine Rotation, auf die sich eine Nummer
beziehen könnte. Die Rollen heißen nach dem, was der Spieler dort tut:
`block`, `abwehr`, `annahme-links`, `annahme-rechts`, `aufschlag`.

Ältere Schaubilder, die von Hand gezeichnet oder aus einer Quelle
ausgeschnitten wurden, haben keine Szene. Sie bleiben, wie sie sind.

## Die Block-Regel

„Block" ist im Volleyball ein Technikelement. Deshalb steht das Wort in unseren
Dokumenten **nur noch dafür**. Für Zeiträume und für die Zeilen im Ablauf
nehmen wir andere Wörter.

| Gemeint ist | Begriff | Beispiel |
|---|---|---|
| Technikelement am Netz | **Block** | „Sprungangriff und Block im Aufbau", „Blockabstimmung", „kein Block" |
| Zeile im Ablauf einer Trainingseinheit | **Programmpunkt** | „der Programmpunkt 46–93", „zwölf Programmpunkte", Spaltenüberschrift „Programmpunkt" |
| 3–6-Wochen-Zeitraum (Mesozyklus) | **Trainingsblock** | „Rahmenbedingungen dieses Trainingsblocks", „erster Trainingsblock der Saison" |
| Räumliche Hallenaufteilung | **Hallenteil** | „zwei Hallenteile mit je einem Netz" |

**Trainingsblock oder Mesozyklus?** Beides ist erlaubt und meint dasselbe.
„Mesozyklus" steht in Überschriften und Dateinamen, „Trainingsblock" im
Fließtext, wo es natürlicher klingt. „Block" allein ist dafür tabu.

**Kein „Teil" für den Programmpunkt.** Das Wort steckt schon in Hallenteil,
in Hauptteil und in den Teilen eines Geräts. Ältere Pläne tragen in der
Ablauftabelle noch die Spaltenüberschrift „Teil" und gelten weiter.

## Halle und Beach

Die Bibliothek trägt Übungen für beide Disziplinen. Auf der Übungskarte steht
das im Pflichtfeld `disziplin`, als Liste aus `halle` und `beach`. Eine Übung,
die am Strand genauso läuft wie in der Halle, trägt beide Werte. Ein Team
spielt immer eine der beiden Disziplinen, das steht im Team-Profil.

„Halle" ist damit doppelt belegt, denn „Hallenteil" meint schon den Raum.
Deshalb dieselbe Trennung wie bei der Block-Regel:

| Gemeint ist | Begriff | Beispiel |
|---|---|---|
| Die Disziplin, in der gespielt wird | **Halle**, **Beach** | „eine Übung für Halle und Beach", „Herren 1 spielt Halle" |
| Räumliche Aufteilung der Halle | **Hallenteil** | „zwei Hallenteile mit je einem Netz" |

Wie viele Flächen eine Übung braucht, sagt das Feld `spielflaechen`. Es gilt
für beide Disziplinen und je Gruppe: Sind mehr Spieler da, als die Übung fasst,
läuft sie in mehreren Gruppen, und jede braucht ihre eigenen Flächen. Drei
Gruppen einer Übung mit `spielflaechen: 1` brauchen drei. Eine Gruppe sind
hier die Leute, die eine Übung zusammen spielen. Die Trainingsgruppe sind alle,
die an dem Abend in der Halle stehen.

## Weitere Sprachregeln

| Nicht verwenden | Stattdessen |
|---|---|
| Tapering | Belastung runterfahren, Entlastungswoche, lockere Woche vor dem Spieltag |
| Peak, peaken | Saisonhöhepunkt, Formhöhepunkt, die wichtigen Spieltage, „in Form kommen" |
| Movement Preps | Bewegungsvorbereitung, Mobilisation |
| Athletikspur | Athletikprogramm, Athletik über die Saison |
| Teil, Trainingsteil für eine Zeile im Ablauf | Programmpunkt |
| Grundform für das Bild der Karte in der Leseansicht | Schaubild der Karte |
| Feldbild für das Bild, das der Sammelimport aus der Quelle ausschneidet | Quellgrafik |

**Bleibt so:** Sideout, Annahme, Abwehr, Zuspiel, Libero, Riegel, 5-1, 6-2 und
die übrigen eingeführten Volleyballbegriffe.

## Eigene Regeln

Hier kommt rein, worauf ihr euch im Verein einigt: Begriffe, die bei euch etwas
Bestimmtes heißen, und Wörter, die ihr vermeiden wollt. Der Eintrag zuerst,
dann benutzen die Skills ihn.
