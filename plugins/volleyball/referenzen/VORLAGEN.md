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
Gerüst:

```markdown
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

# Training <Datum> — <Kurztitel>

## Schwerpunkte dieser Einheit
Ein bis zwei, mit Bezug zum Trainingsblock.

## Rahmenbedingungen

## Ablauf
| Zeit | Teil | Übung | ID | Anpassung heute | Warum hier |
|---|---|---|---|---|---|

## Material gesamt

## Schaubilder

## Organisation und Coaching-Hinweise

## Nachbereitung
**Was lief gut:**
**Belastung und Auffälligkeiten:**
**Haben sich Anpassungen bewährt?**
**Konsequenz für die nächste Einheit oder den Trainingsblock:**
```

Zur Ablauftabelle: **ID** verweist auf die Karte, **Anpassung heute** ist
alles, was an diesem Abend anders war. Keine Spalte Quelle und keine Spalte
Material, beides steht auf der Karte.

Die Frage „Haben sich Anpassungen bewährt?" in der Nachbereitung ist der
Moment, in dem die Bibliothek wächst: was getaugt hat, wandert als Variation
oder eigene Karte in `uebungen/`.
