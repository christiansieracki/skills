# Vorlagen

Die **Übungskarte** steht nicht hier, sondern in `DATENMODELL.md`. Zwei Orte
für dasselbe Schema ist genau der Fehler, der die Bibliothek einmal schon
auseinandergebracht hat.

## teams/&lt;team&gt;/team-profil.md

```markdown
---
team: <kennung>
name: "<Anzeigename>"
saison: "JJJJ/JJ"
gruppe: <trainingsgruppe>
disziplin: halle | beach
niveau: einsteiger | fortgeschritten | ambitioniert
altersklasse: erwachsene | u20 | u18 | u16 | u14
trainer: [<name>]
saisonplan: <pfad oder null>
---

# Team-Profil <Name>

## Kader
| Spieler | Position | Stärken | Entwicklungsfelder |
|---|---|---|---|

## Prinzipien
Regeln, die für dieses Team über einzelne Übungen hinweg gelten. Der
Trainingsdesign-Skill liest sie, bevor er Übungen auswählt. Sie stehen hier
und nicht in der Bibliothek, weil sie vom Niveau abhängen.

### <Regel als Satz>
<Begründung, und wofür sie gilt.>

## Rahmenbedingungen
Halle, Zeiten, Material, Besonderheiten.

## Saisonziel
```

Ein Team ohne eigenen Saisonplan (weil es auf dem eines anderen Teams
mitfährt) bekommt trotzdem ein Profil. Dort gehören dann auch sein eigener
Spielplan und alles hin, was bei gemeinsamen Einheiten für die
Belastungssteuerung gebraucht wird.

## teams/&lt;team&gt;/saisonplan.md

```markdown
---
team: <kennung>
typ: saisonplan
saison: "JJJJ/JJ"
start: JJJJ-MM-TT
ende: JJJJ-MM-TT
stand: JJJJ-MM-TT
---

# Saisonplan <Team> <Saison>

## Was im Vorgespräch rauskam
Ziele, Baustellen, Kaderbesonderheiten, Stärken.

## Phasenübersicht
| Phase | Zeitraum | Hauptfokus |
|---|---|---|

## Spielplan
| Spieltag | Datum | Gegner | Hinweis |
|---|---|---|---|

## Saisonziel und Formhöhepunkte

## Mesozyklen
| # | Zeitraum | Wochen | TE | Schwerpunkte (max. 2) | Warum |
|---|---|---|---|---|---|

## Offene Punkte
```

Die Schwerpunkte in der Mesozyklus-Tabelle sind Kennungen aus
`schwerpunkte.md`, nicht frei formuliert. Sonst findet später niemand die
passenden Übungen dazu.

## teams/&lt;team&gt;/mesozyklen/meso-##-thema.md

```markdown
---
team: <kennung>
typ: mesozyklus
nummer: <n>
start: JJJJ-MM-TT
ende: JJJJ-MM-TT
schwerpunkt: [<kennung>, <kennung>]
---

# Mesozyklus <n>: <Thema>

**Zeitraum:** ... (3 bis 6 Wochen)
**Übergeordnete Phase:** ...

## Schwerpunkte
Maximal zwei, jeder mit einem Satz, was er konkret heißt.

## Warum jetzt
Bezug zum Saisonplan, zum vorherigen Trainingsblock, zu dem was sich gezeigt hat.

## Rahmenbedingungen dieses Trainingsblocks

## Wochenübersicht
| Woche | Termine | Schwerpunkt | Sprungbelastung | Belastung gesamt |
|---|---|---|---|---|

## Erfolgskriterien

## Nächste Schritte
```

`start:` und `ende:` sind Pflicht. Daran wird der aktive Trainingsblock zu
einem Trainingsdatum bestimmt.

## trainings/&lt;gruppe&gt;/JJJJ-MM-TT.md

Die gepflegte Fassung liegt als `trainings/<gruppe>/_vorlage.md` im
Arbeitsordner, damit auch jemand ohne Claude eine Einheit eintragen kann.
`init_struktur.py` kopiert sie aus `referenzen/start/_vorlage.md`. Sie zeigt
dasselbe Gerüst wie dieses hier und erklärt nur mehr dazu. Wer eins ändert,
ändert das andere mit.

````markdown
---
datum: JJJJ-MM-TT
gruppe: <gruppe>
leitteam: <team>
mesozyklus: teams/<team>/mesozyklen/<datei>.md
meso_woche: <n>
teilnehmer: <n>
dauer: <minuten>
spielflaechen: 1 | 2
trainer: <name>
status: entwurf | geplant | absolviert
---

# Training JJJJ-MM-TT — Kurztitel

## Schwerpunkte dieser Einheit
Ein bis zwei, dazu der Bezug zum Trainingsblock in zwei Sätzen.

## Rahmenbedingungen
Stichworte.

## Ablauf
| Zeit | Programmpunkt | Übung | ID | Anpassung heute | Warum hier |
|---|---|---|---|---|---|
| 0–15 | Erwärmung | | | | |
| 15–45 | Technik | | | | |
| 45–75 | Spielform | | | | |
| 75–90 | Abschluss | | | | |

## 45–75 Name der Übung
**Aufbau:** Feld, Netz, Gruppen, Material, worauf es beim Einteilen ankommt.

**Ablauf:** Die Übung, wie sie heute läuft. Was mehrere Programmpunkte
brauchen, per Link: [Thema](#thema).

**Worauf achten:**
-

### 45–75 Hallenskizze
Nur, wenn es ohne nicht geht (siehe unten). Ein Satz, was anders ist, darunter
der ganze Aufbau von heute, Kürzel mit Legende.
```
+-----------+-----------+
|  Z        |           |
+-----------+-----------+
Z  Zuspieler
```

## Athletik

### 0–15 Athletik
| Nr | Übung | Worauf es ankommt | Heute |
|---|---|---|---|
| 1 | | | |

## Zum Nachschlagen

### Thema
Was mehrere Programmpunkte brauchen, etwa die Sechser oder die Regeln.

## Material gesamt

## Organisation und Coaching-Hinweise

## Nachbereitung
**Was lief gut:**
**Belastung und Auffälligkeiten:**
**Haben sich Anpassungen bewährt?**
**Konsequenz für die nächste Einheit oder den Trainingsblock:**
````

Der **Kurztitel** nach dem Gedankenstrich sagt, worum es an dem Abend geht.
Die Leseansicht zeigt ihn oben als Überschrift.

Zur Ablauftabelle: Jede Zeile ist ein **Programmpunkt**, auch Pause und
Umbau. **Zeit** ist seine Zeitangabe, von–bis in Minuten ab Beginn. Laufen zwei
Programmpunkte zur selben Zeit, einer je Hallenteil, kommt der Hallenteil zum
Namen: „Zuspiel, Hallenteil A". **ID** verweist auf die Karte, **Anpassung
heute** sagt in einem Halbsatz, was an diesem Abend anders war als auf der
Karte. Keine Spalte Quelle und keine Spalte Material, beides steht auf der
Karte.

**Schwerpunkte** mit dem Bezug zum Trainingsblock in zwei Sätzen,
**Rahmenbedingungen** als Stichworte.

Zu den Abschnitten:

- Was zu einem Programmpunkt ausgeschrieben gehört, bekommt einen Abschnitt,
  dessen Überschrift mit seiner Zeitangabe beginnt:
  `## 46–93 Drei Sechser mit Zweierserie`. In der Leseansicht steht er im
  aufgeklappten Programmpunkt.
- Der Abschnitt beschreibt die Übung, wie sie heute läuft, in **Aufbau**,
  **Ablauf** und **Worauf achten**, die Anpassungen eingearbeitet. Er ist ohne
  die Karte verständlich und erwähnt sie nicht.
- Kein „siehe unten". Die Zeitangabe verbindet Zeile und Abschnitt.
- Eine **Hallenskizze** als `### 46–93 Hallenskizze`, die Zeichnung in einem
  Codeblock, gibt es nur, wenn der Programmpunkt kein Schaubild hat und ein,
  zwei Sätze den Aufbau nicht sagen, oder wenn der Aufbau heute anders ist als
  im Schaubild. Dann zeigt sie den ganzen Aufbau von heute, und darüber steht
  ein Satz, was anders ist. Bei zwei Programmpunkten zur selben Zeit mit dem
  Hallenteil: `### 69–89 Hallenteil A: Hallenskizze`.
- Die **Athletik** als Tabelle `Nr | Übung | Worauf es ankommt | Heute`,
  `Heute` ist die Dosierung dieses Abends. Gehört Athletik zu mehreren
  Programmpunkten, bekommt jeder unter `## Athletik` einen eigenen
  `### <Zeitangabe> Athletik`.
- **`## Zum Nachschlagen`** ist fest. Jede `###` darunter ist ein Thema, das
  mehrere Programmpunkte brauchen, in der Leseansicht wird es ein Reiter. Ein
  Programmpunkt verweist mit einem Markdown-Link auf seine Überschrift:
  `[die Sechser](#die-sechser)`.
- **`## Schaubilder`** gehört nicht zum festen Gerüst. Er kommt nach
  `## Material gesamt` dazu, wenn es ein Schaubild nur für diesen Abend gibt,
  mit einem Kurzverweis darauf. Das Schaubild einer Karte zeigt die
  Leseansicht von selbst beim Programmpunkt, das braucht keinen Abschnitt.
- **Organisation und Coaching-Hinweise** nur mit dem, was nirgends sonst im
  Plan steht.
- Alles andere steht in der Leseansicht unter Vorbereitung.

Die genauen Regeln stehen in `DATENMODELL.md` unter „Der Trainingsplan".

Die Frage „Haben sich Anpassungen bewährt?" in der Nachbereitung ist der
Moment, in dem die Bibliothek wächst: was getaugt hat, wandert als Variation
oder eigene Karte in `uebungen/`. Dort steht nur die Frage, die Anpassungen
selbst stehen schon in der Tabelle.
