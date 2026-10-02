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

Zurzeit nichts. Bei der Durchsicht am 02.10.2026 vor der Abnahme von Welle 1d
hat jeder Punkt ein Ticket bekommen, siehe den Nachtrag in #29: #40 als Slice
1d/9, #38, #39 und #41 bis #48 vor der Abnahme, dazu Ergänzungen in #35, #36
und #37.

## Bewusst nicht gebaut

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

### Ein Beach-Team anlegen, solange es keins gibt

Beach ist seit Welle 1a im Plugin und an einer echten Beachübung abgenommen
(#9). Ein Team anzulegen ist Arbeit im Arbeitsordner mit dem Saisonplaner, kein
Code, und ohne echtes Beach-Team gibt es nichts anzulegen. Steht so seit #10.

Ziel: bewusst nicht. Auslöser: Es gibt ein echtes Beach-Team.

## Was als Nächstes ansteht

Die Reihenfolge stammt aus #10 und ist dort begründet. Der Sammelimport kam am
30.09.2026 davor und ist Welle 1d (#29). Vor ihrer Abnahme (#37) kommen #38 bis
#48, die Reihenfolge steht im Nachtrag von #29. Die PlayDrill-Bibliothek
braucht die Wissenskarte nicht, und die Wissenskarte kann danach den
Sammelimport um ihre Kartensorte erweitern.

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

### Welle zum Stationsbetrieb

Den Stationsbetrieb als zweite Geometrie behandeln, über Feld und freie
Leinwand hinaus. Etwa eine Grundform „Zirkel": Die Stationen stehen nummeriert
im Kreis, mit einem Pfeil für den Wechsel, und der Trainer zählt nur die
Stationen auf, die Anordnung übernimmt das Skript. Das ist neues Vokabular und
braucht ein eigenes Interview und eine Spec. In #10 bewusst ausgelassen, am
02.10.2026 als eigene Welle beschlossen, mit der niedrigsten Priorität.
