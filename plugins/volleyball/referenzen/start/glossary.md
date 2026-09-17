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
