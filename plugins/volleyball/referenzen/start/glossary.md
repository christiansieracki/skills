# Glossar

Der eine Ort für Begriffsregeln. Alle Dokumente in diesem Ordner und alle
volleyball-Skills halten sich daran.

## Die Bausteine der Bibliothek

| Begriff | Was es ist | Wo es liegt |
|---|---|---|
| **Übung** | Eine einzelne Karte. Lässt sich allein in einen Trainingsteil setzen, meist 8 bis 25 Minuten. | `uebungen/ue-####-*.md` |
| **Übungsfolge** | Ein fertiger Ablauf, der nur als Ganzes Sinn ergibt, weil Reihenfolge und Dosierung dazugehören. Ein DVV-Athletikplan ist so eine. | `uebungen/`, mit `typ: folge` |
| **Übungsquelle** | Ein Fremddokument, aus dem Übungen gezogen wurden. Bleibt als Datei liegen, wird nie selbst zur Karte. | `quellen/` |
| **Prinzip** | Eine Regel, die über Übungen hinweg gilt, zum Beispiel „maximal drei Annahmespieler im Riegel". Hängt am Team, nicht an der Übung. | `teams/<team>/team-profil.md` |

Die Grenze beim Importieren: Lässt sich das Teil aus dem Zusammenhang reißen
und einzeln einsetzen? Dann Übung. Nur als Ganzes sinnvoll? Dann Folge. Ist es
ein kompletter Trainingsabend? Dann Quelle, aus der Übungen gezogen werden.

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
| **Leseansicht** | Die daraus erzeugte Fassung als HTML fürs Handy und als PDF zum Ausdrucken. Darf jederzeit weggeworfen und neu gebaut werden. |

Wer in die Leseansicht tippt, verliert seine Änderung beim nächsten Erzeugen.
Änderungen gehören immer in die `.md`.

## Szene und Schaubild

| Begriff | Was es ist | Wo es liegt |
|---|---|---|
| **Szene** | Die Beschreibung eines Schaubildes in YAML, in Metern gerechnet. Das ist die Quelle, hier wird geändert. | `schaubilder/ue-0042.szene.yml` |
| **Schaubild** | Das Bild, das daraus entsteht. Ein Erzeugnis: es wird beim nächsten Mal überschrieben. | `schaubilder/ue-0042.svg` |
| **Grundform** | Worauf eine Szene gezeichnet wird: eine Feldvorlage oder eine freie Leinwand. | in der Szene, als `form:` |
| **Feldvorlage** | Ein Spielfeld als Grundform: Halle 9×18 m oder Beach 8×16 m, mit den Linien, die es dort wirklich gibt. | `form: halle`, `form: beach` |
| **freie Leinwand** | Eine Fläche mit angesagtem Maß in Metern, ohne Spielfeld darauf. Für einen Aufbau, der auf kein Feld passt. | `form: frei` mit `groesse:` |
| **Zone** | Eine Fläche im Schaubild, die etwas bedeutet: eine Zielzone, ein Aufschlagbereich, das abgedeckte Stück Feld. Hat Rand und Beschriftung. | in der Szene, unter `zonen:` |
| **Gerät** | Ein Kasten, ein Ballwagen, eine Zielmatte im Schaubild, aus Rechtecken und Kreisen zusammengesetzt und beschriftet. | in der Szene, unter `geraete:` |
| **Maßkette** | Eine Abstandsangabe als Linie mit Maßstrichen und der gemessenen Zahl. Der beschriftete Pfeil daneben zeigt denselben Abstand anders. | in der Szene, unter `abstaende:` |
| **Textwerk** | Was neben dem Bild steht: Titel und Untertitel oben, die Legende daneben, die Fußzeile darunter. Es macht aus einer Skizze eine Anleitung. | in der Szene, ganz außen |
| **Legendenblock** | Ein Stück der Legende: eine Überschrift und die Zeilen darunter. Mehrere davon ergeben die Legendenspalte neben dem Bild. | in der Szene, unter `legende:` |

Dasselbe Verhältnis wie zwischen Trainingsplan und Leseansicht: Wer in das SVG
tippt, verliert es beim nächsten Erzeugen. Änderungen gehören in die Szene.

Was aufs Feld passt, wird aufs Feld gezeichnet und hat seinen Maßstab damit
geschenkt. Die freie Leinwand ist für den Rest da. Maßstäblich sind beide, und
eine Abstandsangabe darin auch.

**Zone oder Gerät?** Ein Gerät ist ein Gegenstand, den jemand in die Halle
stellt. Eine Zone ist eine Absprache über ein Stück Boden. Beide sind Flächen
mit Rand und Beschriftung und sehen deshalb im Bild verschieden aus: Wer den
Unterschied nicht sieht, räumt einen Kasten von einer Stelle weg, an der nie
einer stand.

Plätze heißen in der Halle nach ihrer **Positionsnummer** 1 bis 6, im Sand nach
einer **Rolle**. Im Sand gibt es keine Rotation, auf die sich eine Nummer
beziehen könnte. Die Rollen heißen nach dem, was der Spieler dort tut:
`block`, `abwehr`, `annahme-links`, `annahme-rechts`, `aufschlag`.

Ältere Schaubilder, die von Hand gezeichnet oder aus einer Quelle
ausgeschnitten wurden, haben keine Szene. Sie bleiben, wie sie sind.

## Die Block-Regel

„Block" ist im Volleyball ein Technikelement. Deshalb steht das Wort in unseren
Dokumenten **nur noch dafür**. Für Zeiträume und Abschnitte nehmen wir andere
Wörter.

| Gemeint ist | Begriff | Beispiel |
|---|---|---|
| Technikelement am Netz | **Block** | „Sprungangriff und Block im Aufbau", „Blockabstimmung", „kein Block" |
| Abschnitt einer Trainingseinheit | **Teil** | „Teil 68–90", „Erwärmungsteil", „Zuspielteil", Spaltenüberschrift „Teil" |
| 3–6-Wochen-Zeitraum (Mesozyklus) | **Trainingsblock** | „Rahmenbedingungen dieses Trainingsblocks", „erster Trainingsblock der Saison" |
| Räumliche Hallenaufteilung | **Hallenteil** | „zwei Hallenteile mit je einem Netz" |

**Trainingsblock oder Mesozyklus?** Beides ist erlaubt und meint dasselbe.
„Mesozyklus" steht in Überschriften und Dateinamen, „Trainingsblock" im
Fließtext, wo es natürlicher klingt. „Block" allein ist dafür tabu.

**Teil oder Hallenteil?** „Teil" ist immer ein Zeitabschnitt, „Hallenteil"
immer ein Raum. Wenn beides in einem Satz vorkommt, lieber „Hallenteil A" und
„Hallenteil B" schreiben, damit es eindeutig bleibt.

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
für beide Disziplinen.

## Weitere Sprachregeln

| Nicht verwenden | Stattdessen |
|---|---|
| Tapering | Belastung runterfahren, Entlastungswoche, lockere Woche vor dem Spieltag |
| Peak, peaken | Saisonhöhepunkt, Formhöhepunkt, die wichtigen Spieltage, „in Form kommen" |
| Movement Preps | Bewegungsvorbereitung, Mobilisation |
| Athletikspur | Athletikprogramm, Athletik über die Saison |

**Bleibt so:** Sideout, Annahme, Abwehr, Zuspiel, Libero, Riegel, 5-1, 6-2 und
die übrigen eingeführten Volleyballbegriffe.

## Eigene Regeln

Hier kommt rein, worauf ihr euch im Verein einigt: Begriffe, die bei euch etwas
Bestimmtes heißen, und Wörter, die ihr vermeiden wollt. Der Eintrag zuerst,
dann benutzen die Skills ihn.
