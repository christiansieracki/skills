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
und #41 bis #48 vor der Abnahme, dazu Ergänzungen in #35, #36 und #37. Der
Punkt hier kam danach aus dem Interview zur Welle zur Leseansicht.

### DVV Plan 1 als Übungsfolge mit ID

Die Athletik steht in den Plänen mit „—" in der Spalte ID, die Übungen sind im
Plan ausgeschrieben. Der DVV-Athletikplan ist laut Glossar eine Übungsfolge und
gehört als Karte nach `uebungen/`. Dann könnte ein Programmpunkt auf die Karte
zeigen, statt die Übungen in jeden Plan zu kopieren. Fiel im Interview zur Welle
zur Leseansicht auf, ist aber Arbeit an der Bibliothek.

Ziel: Welle 2.

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
Sammelimport um ihre Kartensorte erweitern. Zwischen 1d und die Wissenskarte
kommt die Welle zur Leseansicht, beschlossen am 02.10.2026.

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
