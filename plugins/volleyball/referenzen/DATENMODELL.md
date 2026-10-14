# Datenmodell

Verbindlich für alle fünf Skills. Wer hier abweicht, produziert Karten, die
`suche.py` nicht findet.

## Ordner

Der Arbeitsordner wird an der Markerdatei `trainingsplanung-root.yml` erkannt.
Ab dem geöffneten Ordner nach oben suchen, nie einen Pfad raten. `finde_wurzel()`
in `scripts/tpdaten.py` macht das.

```
<wurzel>/
├── trainingsplanung-root.yml   Gruppen, Teams, führendes Team, Trainer
├── README.md                   für Mittrainer
├── glossary.md                 Begriffsregeln
├── schwerpunkte.md             die erlaubten Schwerpunkt-Kennungen
├── index.md                    erzeugt, nur auf Ansage
├── teams/<team>/               team-profil.md, saisonplan.md, mesozyklen/
├── trainings/<gruppe>/         JJJJ-MM-TT.md, dazu _vorlage.md
├── uebungen/                   flach, eine Datei je Übung
├── wissen/                     flach, eine Datei je Wissenskarte
├── quellen/                    Originaldokumente
├── kartenentwuerfe/            Kartenentwürfe eines laufenden Sammelimports
└── schaubilder/                Schaubilder und die Szenen, aus denen sie entstehen
```

Die Gruppe ist, wer zusammen in der Halle steht, daran hängen die Einheiten.
Das Team ist die Wettkampfmannschaft mit Saisonplan. Welche Gruppe welche Teams
abdeckt und welches Team bei Konflikten führt, steht in der Wurzeldatei. Nie im
Skill hart kodieren. Dort steht auch, welcher Trainer welche Nummer hat, siehe
„Die ID“.

## Die Übungskarte

Dateiname `ue-######-sprechender-slug.md`, Frontmatter komplett:

```yaml
---
id: ue-000042                    # stabil, ändert sich nie
titel: "Annahme-Challenge auf dem Halbfeld"
typ: uebung                      # uebung | folge
disziplin: [halle]               # Liste, halle und/oder beach, Pflicht
element: [annahme]               # Liste, aus der Liste unten
spielphase: sideout              # sideout | break | keine
form: komplex                    # erwaermung technik komplex spielform station abschluss
schwerpunkt: [annahme, sideout-sicherheit]   # nur aus schwerpunkte.md
level_min: einsteiger            # einsteiger | fortgeschritten | ambitioniert
level_max: ambitioniert
spieler_min: 5
spieler_max: 8                   # null heißt: nach oben offen
dauer_min: 15
dauer_max: 25
spielflaechen: 1                 # wie viele eine Gruppe braucht
netz: true
erwachsenenbelastung: false
belastungshinweis: ""            # Klartext, wenn erwachsenenbelastung true ist
material: [zielmatte, baelle]    # kleingeschrieben, ohne Umlaute
schaubild: null                  # Dateiname in schaubilder/ oder Liste davon, landet in der Leseansicht
quelle: "..."                    # nie leer
quelldatei: null                 # Datei in quellen/, freier Text, bei zwei Seiten beide
variante_von: null               # id, wenn abgeleitet
autor: christian
angelegt: 2026-09-17
---

# <Titel>

## Ziel
## Ablauf
## Variationen
## Hinweise        (optional: Sicherheit, Aufbau, Dosierung)
```

**Kein Feld `eingesetzt`.** Wann eine Übung gelaufen ist, steht in den
Trainingsplänen, und `index.py` sammelt es von dort ein. Zweimal pflegen heißt
einmal vergessen.

### Kontrollierte Werte

- `disziplin`: halle, beach
- `element`: annahme, zuspiel, angriff, block, abwehr, aufschlag, ballkontrolle,
  athletik, koordination
- `spielphase`: sideout, break, keine
- `form`: erwaermung, technik, komplex, spielform, station, abschluss
- `level_min` / `level_max`: einsteiger, fortgeschritten, ambitioniert
- `schwerpunkt`: nur Kennungen aus `schwerpunkte.md` der Wurzel. Fehlt eine,
  vorschlagen, nach dem Ja des Nutzers dort eintragen, dann verwenden. Nie
  einfach eine neue erfinden.
  Jede Kennung führt dort eine Disziplin, siehe unten.

### Disziplin

`disziplin` ist Pflicht und trägt eine Liste. Eine Übung, die am Strand genauso
läuft wie in der Halle, bekommt beide Werte. Eine reine Beachübung trägt nur
`beach`. Die Bibliothek bleibt dabei eine, mit einem ID-Raum: getrennt wird
beim Suchen, nicht beim Ablegen.

**Es gibt keinen Default.** Fehlt das Feld oder ist die Liste leer, meldet
`index.py` das. Ein Default schwiege genau dann, wenn beim Import die Disziplin
vergessen wurde, und legte die Beachübung wortlos unter Halle ab.

Das Team führt die Disziplin als einzelnen Wert in seinem Profil, weil ein Team
immer eine von beiden spielt. Die Trainingsgruppe erbt sie von ihrem Leitteam.

### Schwerpunkt und Disziplin

In `schwerpunkte.md` trägt jede inhaltliche Kennung eine dritte Spalte mit
`halle`, `beach` oder `beide`. `index.py` meldet eine Karte, deren Schwerpunkt
in keiner ihrer Disziplinen gilt. Eine Hallenkarte mit einem reinen
Beachschwerpunkt fällt damit auf, bevor beim Planen jemand danach sucht.

Eine Übereinstimmung reicht. Eine Karte für Halle und Beach darf einen
Schwerpunkt tragen, den es nur in einer der beiden gibt.

Kennungen mit leerer dritter Spalte gelten für beide Disziplinen. Das sind die
Steuerungsschwerpunkte, die die Spalte gar nicht führen, und Zeilen, bei denen
sie beim Eintragen vergessen wurde. Ein Wert, den es nicht gibt, ist etwas
anderes und wird gemeldet. Sonst schaltete ein Tippfehler in der von Hand
gepflegten Datei still die Prüfung ab, für die die Spalte da ist.

Die Spalte trägt einen einzelnen Wert mit `beide`, während `disziplin` auf der
Karte eine Liste ist. ADR-0001 verwirft den Einzelwert für die Karte, weil er
jeden Filter für immer zu „beach oder beide" zwingt. Hier filtert niemand: die
Zelle wird beim Einlesen zur Menge aufgelöst und danach wie eine Liste
geschnitten. Eine Liste in einer Tabellenzelle wäre nur schlechter zu lesen.

### Übung oder Folge

`typ: folge` für einen fertigen Ablauf, der nur als Ganzes Sinn ergibt, weil
Reihenfolge und Dosierung dazugehören. Ein DVV-Athletikplan ist so einer, er
wird nicht in zwölf Einzelübungen zerlegt.

Prüffrage beim Import: lässt sich das Teil aus dem Zusammenhang reißen und
einzeln einsetzen? Dann Übung. Nur als Ganzes? Dann Folge. Ist es ein
kompletter Trainingsabend? Dann gehört es nach `quellen/` und es werden
einzelne Übungen daraus gezogen.

### Spieler und Spielflächen

`spieler_max` sagt, wie viele eine Gruppe der Übung fasst. Sind mehr da, läuft
sie in mehreren Gruppen. Was Gruppe dabei heißt, steht im Glossar.

`spielflaechen` gilt je Gruppe. Drei Gruppen einer Übung mit
`spielflaechen: 1` brauchen drei Flächen. So lief die Annahme-Challenge am
15.09.2026: 16 Leute, zwei Gruppen, zwei Netze. Zeigt die Quelle mehrere
Gruppen nebeneinander, steht auf der Karte, was eine von ihnen braucht.

`suche.py --spielflaechen` sortiert eine Übung aus, die schon für eine Gruppe
mehr Flächen braucht, als da sind. Reichen die Flächen nur nicht für alle
Gruppen zugleich, bleibt sie in den Treffern, denn die Gruppen können auch
nacheinander spielen. Die Trefferzeile sagt dann `[3 Gruppen, 1 Fläche]` statt
`[3 Gruppen parallel]`. Braucht eine Gruppe zwei Flächen, steht das dabei:
`[2 Gruppen je 2 Flächen, 3 Flächen]`.

### Belastung

`erwachsenenbelastung: true` heißt: die Übung enthält Sprungvolumen, Zusatzlast
oder Maximalkraft, die ein Jugendkörper so nicht wegsteckt. Das ist ein
**Hinweis, kein Filter.** Übungen damit werden Jugendtrainern gezeigt, mit dem
Klartext aus `belastungshinweis` und einem Vorschlag, wie man sie anpasst.
Entschieden wird in der Halle.

Setzen nur, wenn die Quelle es hergibt. Eine geratene Altersfreigabe ist
schlechter als gar keine. Im Zweifel nachfragen.

## Die Wissenskarte

Hintergrund aus einer Fremdquelle, in eigenen Worten (ADR-0002). Eine
Wissenskarte beantwortet genau eine Frage, die sich ein Trainer stellt, und
diese Frage ist ihr Titel. Wann etwas Wissenskarte wird und wann Übung oder
Prinzip, steht im Glossar.

Dateiname `wi-######-sprechender-slug.md`, der Slug aus der Frage ohne
Fragezeichen. Frontmatter komplett:

```yaml
---
id: wi-000001                    # stabil, ändert sich nie
titel: "Wann lohnt sich einarmige Abwehr?"   # die Frage, endet auf ?
thema: [technik, taktik]         # Liste, Pflicht, aus der Liste unten
schwerpunkt: [abwehr]            # Liste, freiwillig, auch Steuerungsschwerpunkte
disziplin: [halle, beach]        # Liste, Pflicht, ohne Default
uebungen: [ue-000037, ue-000038] # Liste, freiwillig, IDs aus uebungen/
quelle: "Volleyball-Magazin 08/2026, Einarmig gehts auch, Teil 1, S. 24–25"   # nie leer
quelldatei: "volleyballmagazin/vm_08_2026/seite-24.jpg"   # relativ zu quellen/
autor: christian
angelegt: 2026-10-20
---

# Wann lohnt sich einarmige Abwehr?

## Kernaussagen
## Was das fürs Training heißt
```

Beide Abschnitte gibt es auf jeder Wissenskarte. Unter „Kernaussagen“ steht
knapp, was die Quelle sagt, in eigenen Worten und ohne Volltext. Unter „Was das
fürs Training heißt“ steht, was daraus für die Halle folgt: was die Quelle dazu
sagt, und was der Trainer als Ableitung bestätigt hat.

Ein Feld `schaubild` hat die Wissenskarte nicht, eines für Alter oder Level
auch nicht.

### Kontrollierte Werte

- `thema`: trainingslehre, methodik, psychologie, physiologie, ernaehrung,
  regelkunde, technik, taktik. Fest wie `element`, kein Trainer erweitert die
  Liste selbst. Eine Karte darf mehrere Themen tragen.
- `disziplin`: halle, beach. Pflicht und ohne Default, wie bei der Übungskarte:
  Wissen nur über den Sand soll nicht still bei der Halle landen.
- `schwerpunkt`: Kennungen aus `schwerpunkte.md`, die inhaltlichen und die
  Steuerungsschwerpunkte, etwa `belastungssteuerung`. Mit denen plant der
  Saisonplaner einen Trainingsblock, und dazu soll er die Karte finden. Eine
  inhaltliche Kennung muss in einer Disziplin der Karte gelten, wie bei der
  Übungskarte. Ein Steuerungsschwerpunkt hat keine Disziplinspalte und gilt
  für beide. Das Feld ist freiwillig, ein Beitrag über Schlaf hat keine
  Kennung. Eine neue Kennung kommt nur für etwas dazu, das man trainieren kann,
  und erst nach dem Ja des Trainers.

### Übungen

`uebungen` nennt die Übungen, die zur Karte gehören, etwa die aus demselben
Beitrag. Die Übungskarte trägt nichts davon. Welche Wissenskarten auf eine
Übung zeigen, rechnet der Index aus, den `index.py` und `suche.py` bei jedem
Aufruf neu bauen. `index.md` nennt sie bei der Übung in der Spalte
„Hintergrund“, `suche.py --json` unter `hintergrund`. `index.py` meldet eine
ID, die es in `uebungen/` nicht gibt.

### Bilder

Ein Bild steht als Markdown-Bildverweis im Text, an der Kernaussage, die es
zeigt. Die Datei liegt in `schaubilder/`, ihr Name beginnt mit der ID der
Karte:

```markdown
## Kernaussagen

- Beim oberen Zuspiel bilden die Hände ein Dreieck über der Stirn.

  ![Bildreihe oberes Zuspiel](../schaubilder/wi-000003-oberes-zuspiel-1.png)
```

Der Weg ist relativ zur Karte, so zeigt jede Markdown-Ansicht das Bild. Ein
Bild ohne Zusammenhang erklärt auf einer Wissenskarte nichts, deshalb gibt es
kein Feld dafür. `index.py` meldet einen Bildverweis, dessen Datei es nicht
gibt.

### Wissenskarten finden

Eine Suche nach Thema und Schwerpunkt gibt es noch nicht. Gefunden wird eine
Wissenskarte auf zwei Wegen:

- `index.md` hat den Abschnitt „Wissenskarten“, nach Thema gegliedert. Eine
  Karte mit zwei Themen steht unter beiden. Je Karte stehen da die Frage, die
  ID und die IDs ihrer Übungen.
- `suche.py --wissen` listet alle Wissenskarten, eine Zeile je Karte mit ID,
  Frage, Thema und Schwerpunkt. Mit `--json` kommen dazu Disziplin, `quelle`,
  `quelldatei`, `uebungen` und die Datei, darüber prüft ein Import Duplikate.
  Zusammen mit einem Filter für Übungen, etwa `--element`, endet `--wissen`
  mit einer Meldung. Ohne `--wissen` findet `suche.py` nur Übungen.

### Die ID einer Wissenskarte

`wi-` und sechs Ziffern, vorn die Nummer des Trainers wie bei der Übung:
`wi-000001` ist die erste Wissenskarte von Trainer 00, `wi-010001` die erste
von Trainer 01. Der Bereich ist derselbe, der Zähler ein eigener. Gezählt wird
nur in `wissen/`, die Übungen zählen nicht mit.

Nächste freie ID: `python3 scripts/suche.py --naechste-id --wissen` (Windows:
`python`). Sonst gilt alles aus „Die ID“: Dateiname und `id:` zählen, kein
Trainer an diesem Rechner heißt keine ID, vergeben wird erst bei der Freigabe.
Vierstellige IDs gab es bei Wissenskarten nie. Eine vierstellige Übung hält
die nächste Wissenskarte deshalb nicht auf.

## Die ID

`id` ist die Identität. Trainingspläne verweisen darüber, `index.py` löst sie
auf die Datei auf. **Eine vergebene ID wird nie wieder geändert**, auch nicht
beim Umbenennen der Datei. Sonst brechen alle Pläne, die auf sie zeigen. Die
Umstellung auf sechs Stellen bricht diese Regel ein einziges Mal, mit einem
Skript, das den ganzen Arbeitsordner zugleich umstellt (ADR-0011).

Eine ID ist `ue-` und sechs Ziffern: zwei für die Nummer des Trainers, der sie
vergeben hat, vier laufend. `ue-000042` ist die Karte 42 von Trainer 00,
`ue-010001` die erste von Trainer 01. Jeder Trainer vergibt die höchste Nummer
in seinem Bereich plus eins. Zwei Trainer vergeben so nie dieselbe ID, auch
wenn Nextcloud ihre Rechner noch nicht abgeglichen hat. Die Wissenskarte trägt
`wi-` vorn und zählt für sich, siehe „Die ID einer Wissenskarte“.

Nächste freie ID: `python3 scripts/suche.py --naechste-id` (Windows: `python`).
Gezählt werden Dateiname und `id:` jeder Karte, aber nur im Bereich des
Trainers, der an diesem Rechner sitzt. Nie selbst aus der Trefferliste
rechnen. Beim Sammelimport vergibt `sammelimport.py uebernehmen` die ID über
dieselbe Funktion, erst bei der Freigabe (ADR-0010).

Keine ID gibt es, wenn der Rechner zu keinem Trainer gehört oder wenn
`uebungen/` noch eine vierstellige ID trägt. Der Aufruf endet dann mit
Exitcode 1 und sagt warum, bei einem unbekannten Rechner mit dessen Namen.

Ein Trainer an zwei Rechnern kann dieselbe ID zweimal vergeben, bevor Nextcloud
abgleicht. Das ist hingenommen. Der Linter meldet die doppelte ID.

Der Dateiname beginnt mit der ID, darf aber sonst geändert werden.

### Wer welcher Trainer ist

Der Abschnitt `trainer:` in der Wurzeldatei nennt je Trainer seine Nummer und
die Rechner, an denen er importiert:

```yaml
trainer:
  christian:
    nummer: "00"                 # zwei Ziffern, in Anführungszeichen
    rechner: [LAPTOP-J9V3J4LU]   # Liste in eckigen Klammern
```

Die Namen sind dieselben wie unter `gruppen.<gruppe>.trainer`. Erkannt wird der
Rechner an seinem Namen, so wie er sich selbst nennt, unter Windows ist das der
Gerätename. Groß- und Kleinschreibung zählen nicht. Auf dem Rechner selbst wird
nichts gespeichert, so sieht jeder in der Wurzeldatei, wer welche Nummer hat.
Jede Nummer gehört genau einem Trainer, jeder Rechner genau einem Trainer.

Den Eintrag legt `volleyball-uebungsimport` an, wenn `--naechste-id` den
Rechner nicht kennt: Er fragt, wer da sitzt. Ein Trainer aus der Liste bekommt
den Rechner dazu, ein neuer Trainer die nächste freie Nummer, der erste
überhaupt `00`. Eingetragen wird erst nach dem Ja des Trainers.
`init_struktur.py` legt den Abschnitt leer an.

Die nächste freie Nummer ist die höchste vergebene plus eins, die Meldung von
`--naechste-id` nennt sie. Eine Lücke wird nicht gefüllt: Ist ein Trainer
ausgetragen, steht seine Nummer noch vorn in seinen Karten.

### Vierstellige IDs

Bis 2.5.1 waren IDs vierstellig, etwa `ue-0042`. Seitdem gilt nur das neue
Format. `index.py` meldet eine Karte mit vierstelliger ID und einen
Trainingsplan, der noch eine nennt, jeweils mit Hinweis auf
`ids_umstellen.py`. Das Skript stellt einen Arbeitsordner um:

- Ohne `--schreiben` zeigt es jede Änderung und schreibt nichts.
- Jede vierstellige ID als ganzes Wort in den `.md`- und `.yml`-Dateien des
  Arbeitsordners wird `ue-00` und die vier Ziffern, auch unter `quellen/`.
- Karten in `uebungen/` und Dateien in `schaubilder/`, deren Name mit einer ID
  beginnt, werden umbenannt.
- Steht unter `trainer:` noch niemand, kommt der mit `--trainer` genannte
  Trainer hinein, als `00` und mit diesem Rechner. Steht dort schon jemand,
  bleibt der Abschnitt, wie er ist. Gehört dieser Rechner dann zu keinem
  Trainer, sagt das Skript es.
- `index.md` und die Leseansichten sind erzeugt und bleiben. Das Skript sagt
  am Ende, womit sie neu entstehen.
- Ist ein neuer Dateiname schon belegt, schreibt es nichts. Ein zweiter Lauf
  findet nichts mehr zu tun.

## Der Sammelimport

Ein Quellenordner unter `quellen/` wird als Ganzes importiert. Was die Begriffe
Quellenordner, Kandidat, Kartenentwurf, Rückfrage und Vermutung heißen, steht
im Glossar.

### `sammelimport.md`

Liegt im Quellenordner und hat drei Teile:

```markdown
---
kandidaten_je_durchgang: 30      # so viele Aufträge je Durchgang
plan_freigegeben: 2026-09-30     # null, solange der Plan nicht freigegeben ist
textmarke: "Ausführung:"         # optional: ab hier beschreibt die Quelle ihren Ablauf
platzhalter: "hier könnte ihr Text stehen"   # optional: was dort steht, wenn nichts dasteht
quellgrafik: eingebettet         # optional: eingebettet, ausschnitt oder keine
ohne: [Aufst_Pos_D, PLAYDRILL_IMPORT_LOG.md]   # optional: was der Zerlegungsplan auslässt
in_arbeit: christian, 2026-10-02 # schreibt das Skript: wer seit wann daran arbeitet
---

# Sammelimport playdrill

## Absprachen

Freitext: wie sich die Quelle liest und welche Feldregeln für jede Karte
daraus gelten. Geht unverändert in jeden Auftrag. Antworten aus der Freigabe,
die für jede Karte gelten, stehen zuletzt unter
`### Was die Quelle nicht sagt`.

## Übersicht

| Kandidat | Dateien | Was es ist | Ergebnis | Status | Karte | Notiz |
|---|---|---|---|---|---|---|
| 1 | `Ü_Abwehr/Abwehr vom Kasten.pdf` | Abwehr gegen Angriffe vom Kasten | uebung | importiert | ue-000291 | spieler_min auf 6 |
| 2 | `seite-24.jpg`, `seite-25.jpg` | Übung über zwei Seiten | uebung | offen | | kein Entwurf |
| 3 | `volley-meets-school.pdf` S. 12–13 | Ballgewöhnung mit dem Luftballon | uebung | offen | | |
| 4 | `seite-26.jpg`, `seite-27.jpg` | Einarmig gehts auch, Teil 2, S. 26–27: Wann lohnt sich einarmige Abwehr? Übungen: 5, ue-000041 | wissen | offen | | |
| 5 | `seite-28.jpg` | Einarmige Abwehr vom Kasten, Einarmig gehts auch, Teil 2, S. 28 | uebung | offen | | |
| 6 | `seite-30.jpg` | Drei Spielzüge über die Mitte | zurückgestellt | zurückgestellt | | Spielzüge, dafür gibt es keine Sorte |
```

- Die Spalte **Kandidat** trägt die Nummer des Kandidaten, fortlaufend je
  Quellenordner. Sie bleibt und benennt Entwurf und Auftrag. Ein zweiter Lauf
  zählt ab der höchsten Nummer in der Übersicht weiter.
- **Dateien** stehen relativ zum Quellenordner, jede in Backticks. Hinter
  einem PDF darf ein **Seitenbereich** stehen, `` `TechnikGuidelines.pdf` S. 12–15 ``
  oder `` `Merkmale.pdf` S. 3 ``, mit Halbgeviertstrich oder Bindestrich.
  Dann gehören nur diese Seiten zum Kandidaten, ohne Seitenbereich die ganze
  Datei. So ergibt ein langes PDF mehrere Kandidaten, und eine Datei steht
  mit verschiedenen Bereichen in mehreren Zeilen. Einen Seitenbereich gibt es
  nur bei PDFs. Hat ein Kandidat des Durchgangs einen an einem Foto, einen
  über die letzte Seite hinaus oder einen, der sich nicht lesen lässt, bricht
  `vorbereiten` vor dem ersten Auftrag ab, und die Meldung nennt die Zeile.
  Die letzte Seite kennt das Skript aus `pdftotext`. Ohne `pdftotext` merkt
  es erst der Agent.
- **Ergebnis** ist eins von `uebung`, `folge`, `wissen`, `zurückgestellt`,
  `übersprungen`. Aus `uebung` und `folge` wird eine Übungskarte mit diesem
  `typ`, aus `wissen` eine Wissenskarte. Ein anderes Ergebnis bricht jeden
  Unterbefehl ab.
- **`zurückgestellt`** heißt: Das kann später eine Karte werden, aber es gibt
  keine Sorte dafür, etwa eine Seite mit Spielzügen, oder der Trainer holt es
  bewusst später. Der Grund steht in der Notiz. **`übersprungen`** ist, was
  nie Karte wird: ein Bericht, ein Porträt, ein Interview ohne
  Trainingsbezug, Werbung, eine Vorlage, eine leere Seite, ein kompletter
  Trainingsabend. Auch hier mit Grund.
- **Status** ist eins von `offen`, `bereit`, `rückfrage`, `importiert`,
  `ergänzt`, `übersprungen`, `zurückgestellt`, bei Übungs- wie
  Wissenskarten. Die ersten drei warten noch auf ihre Karte. `rückfrage`
  heißt: Hier muss der Trainer eine Frage beantworten, bevor er freigibt.
  Entweder hat der Entwurf eine Rückfrage ohne Vermutung, oder sein Ablauf
  kommt laut Auftrag aus dem Bild. Den Status `zurückgestellt` kann auch eine
  Zeile mit `uebung`, `folge` oder `wissen` tragen, wenn der Trainer sie bei
  der Freigabe zurückstellt. Ihr Ergebnis bleibt dann.
- **Was es ist** sagt in wenigen Wörtern, worum es geht. Bei `wissen` endet
  es mit den Übungen aus demselben Beitrag, in der festen Form
  `Übungen: 13, 14, ue-000041`: Kandidatennummern für Übungen dieses Plans,
  IDs für Übungen, die schon Karte sind. Ohne solche Übungen fehlt der Teil.
  Steht dort `ergänzt ue-######` oder `ergänzt wi-######`, ergänzt der
  Kandidat diese Karte, statt eine eigene zu werden, und `Variante von
  ue-######` macht ihn zur Variante. Bei `wissen` steht das vor `Übungen:`.

`textmarke` und `platzhalter` sind für die Regel „wenig Text“. Stehen nach der
Textmarke, ohne den Platzhalter, weniger als 150 Zeichen, sagt der Auftrag
„Ablauf aus dem Bild“. Groß- und Kleinschreibung und Zeilenumbrüche zählen
dabei nicht. Ohne Textmarke, oder wenn eine Datei sie nicht trägt, zählt ihr
ganzer Text. Hat eine Datei gar keinen Text, entscheidet der Agent.

`quellgrafik` sagt, woher die Quellgrafik einer Karte kommt:

- `eingebettet`: das größte eingebettete Bild jedes PDF, ohne seinen
  durchsichtigen Rand. Das passt zu PlayDrill, eine Übung je PDF mit einem
  Feldbild.
- `ausschnitt`: Der Entwurf nennt seine Ausschnitte, Stellen auf der Seite
  eines Fotos oder PDF, und `pruefen` schneidet sie aus, siehe unten. Das
  passt zu Fotos von Seiten und zu jedem anderen PDF.
- `keine`: Die Karten bekommen ihr Bild später mit `volleyball-schaubild`.
  Ohne Einstellung gilt `keine`.

Vor dem Ausschnitt hieß die Einstellung `quellgrafik_ausschneiden`. `true` gilt weiter
als `eingebettet`, `false` als `keine`. Stehen beide da, oder ein Wert, den
es nicht gibt, bricht `vorbereiten` vor dem ersten Auftrag ab. Steht dort
noch das ältere `feldbild_ausschneiden`, ebenso, und die Meldung nennt
`quellgrafik`.

`ohne` ist eine Liste von Pfaden relativ zum Quellenordner, in eckigen
Klammern. Ein Ordner gilt mit allem darunter. Was dort steht, sieht der
Zerlegungsplan nicht: Es steht nicht in der Planeingabe, sein Text wird nicht
gelesen, und es gilt bei keinem Lauf als neu. Bei PlayDrill sind das die
Aufstellungen, die Vorlagen und die Logs des Trainers. Eine Liste aus
`- `-Zeilen weist das Skript ab, der Parser läse sie als leer.

`in_arbeit` trägt `sammelimport.py vorbereiten` ein, sobald es Aufträge
schreibt: den Trainer dieses Rechners aus `trainer:` in der Wurzeldatei und
den Tag, an dem er angefangen hat. Ohne Trainer an diesem Rechner schreibt
`vorbereiten` keinen Auftrag. Steht dort ein anderer Trainer, endet
`vorbereiten` mit einer Meldung, die ihn und das Datum nennt, und schreibt
nichts. So entwerfen zwei Trainer nicht dieselben Kandidaten zweimal. Mit
`--trotzdem` geht es weiter, etwa wenn der Eintrag von einem abgebrochenen
Lauf stammt. Ist nichts mehr offen, löscht `uebernehmen` den Eintrag.

Die Übersicht ist der freigegebene Zerlegungsplan. Bis zur Freigabe ist er ein
Entwurf des Agenten unter `kartenentwuerfe/<ordner>/`, den der Skill mit dem
Trainer bespricht und dann in die Übersicht schreibt. Danach schreibt nur noch
`sammelimport.py` hinein, auch wenn mehrere Agenten parallel entwerfen. Den
Status setzt das Skript aus den Dateien auf der Platte. Die Rückmeldung eines
Agenten zählt dabei nicht.

### `kartenentwuerfe/<ordner>/`

Alles, was ein laufender Sammelimport erzeugt, liegt hier. `planeingabe.md` ist
die Eingabe für den Zerlegungsplan: jede Datei des Quellenordners, die noch in
keiner Zeile der Übersicht steht und die `ohne` nicht auslässt, bei PDFs ihr
Text, die nächste freie Kandidatennummer, ohne Übersicht 1, und die
Bibliotheksliste, in der die Karten aus diesem Quellenordner markiert sind.
Die Bibliotheksliste hat zwei Teile: die Übungskarten mit ID, Titel, Element
und `quelldatei`, die Wissenskarten mit ID, Frage, Thema und `quelldatei`.
Eine Datei, die mit einem Seitenbereich in einer Zeile steht, ist nicht mehr
neu, gleich welche Seiten die Zeile nennt. In der Planeingabe steht im Text
eines PDF vor jeder Seite eine **Seitenmarke**, `=== Seite 3 ===`, auch vor
einer Seite ohne Text. Daran nennt der Zerlegungsplan Seitenbereiche.

**Nachholen:** Eine zurückgestellte Zeile kommt nie von selbst wieder, auch
nicht mit ihren Dateien. Holt der Trainer sie, nimmt
`vorbereiten --plan --zurueckgestellte` zu den neuen Dateien die Dateien
aller Zeilen mit Status `zurückgestellt`. Die Planeingabe nennt diese Zeilen
unter „Zurückgestellt“ mit Nummer, Dateien, „Was es ist“ und Notiz. Nennt
eine davon ein PDF mit Seitenbereich, steht von ihm nur der Text dieser
Seiten da, der Rest steht schon in anderen Zeilen. Die erste Zeile, die der
Plan aus einer zurückgestellten macht, trägt deren Nummer, weitere bekommen
neue Nummern ab der nächsten freien. Bei der Freigabe ersetzt eine Zeile mit
einer Nummer, die es in der Übersicht schon gibt, die alte, die übrigen kommen
darunter.

Daneben schreibt der Agent `volleyball-zerlegungsplan` den Plan als
`zerlegungsplan.md`, in der Form der Übersicht. Daraus wird nach der Freigabe
die Übersicht. Der Rest ist nach der Nummer des Kandidaten benannt:
`17.auftrag.md` ist der Auftrag, `17.md` der Kartenentwurf,
`17.quellgrafik.png` die Quellgrafik, bei mehreren `17.quellgrafik-1.png`,
`17.quellgrafik-2.png` und so weiter. Ein Ausschnitt aus einem Foto endet auf
`.jpg`. Den Entwurf schreibt bei `uebung` und `folge` der Agent
`volleyball-kartenentwurf`, bei `wissen` der Agent `volleyball-wissenskarte`.
`vorbereiten` nennt je Auftrag die Sorte, `uebungskarte` oder `wissenskarte`,
daran wählt der Skill den Agenten.

Der Auftrag trägt unter jedem PDF des Kandidaten dessen ganzen Text, oder den
Hinweis, dass der Agent das PDF selbst lesen muss. Nennt der Kandidat einen
Seitenbereich, steht nur der Text dieser Seiten da, und der Auftrag sagt, dass
der Agent im PDF nur diese Seiten öffnet, ohne Text, dass er diese Seiten
selbst liest. `quelldatei` nennt auch dann nur die Datei, die Seiten stehen
in `quelle`. Der Auftrag sagt, ob der Ablauf aus dem Bild kommt, gezählt
wird dafür nur der Text dieser Seiten.

Bei `quellgrafik: eingebettet` schneidet `vorbereiten`
aus jedem PDF des Kandidaten, das ein Bild einbettet, das größte Bild aus. Der
durchsichtige Rand fällt weg. Eine einzelne Quellgrafik steht im Entwurf als
`schaubild: 17.quellgrafik.png`. Mehrere nennt der Auftrag in der Reihenfolge
der Spalte Dateien, bei einer Folge also mit dem Übersichtsblatt vorn, und der
Entwurf trägt sie in dieser Reihenfolge als Liste ein:
`schaubild: [17.quellgrafik-1.png, 17.quellgrafik-2.png]`. Gezählt wird ohne
Lücke, ein PDF ohne Bild bekommt keine Nummer. Lässt sich ein Bild nicht lesen,
fehlt nur dieses, auch wenn es das der Übersicht ist. Die Stationen bekommen
ihre Quellgrafiken trotzdem, und für die Übersicht lässt sich danach mit
`volleyball-schaubild` ein Schaubild zeichnen. Der Auftrag nennt das PDF, in
dem der Agent selbst nachsieht. Eine fremde Quellgrafik darf der Entwurf nicht
nennen.

Bei `quellgrafik: ausschnitt` schneidet `vorbereiten` nichts vorab aus. Der
Auftrag sagt unter `## Ausschnitte`, dass der Entwurf seine Ausschnitte nennt,
in welcher Form und wie sie heißen: ein einzelner `17.quellgrafik.<endung>`,
mehrere ab 1 gezählt, die Endung `.jpg` aus einem Foto und `.png` aus einer
PDF-Seite, wie bei `ausschnitt.py`. Weil ein Ausschnitt seine Seite nennt,
trägt der Text eines PDF im Auftrag dann die Seitenmarken, gezählt wie im PDF,
bei einem Seitenbereich also ab seiner ersten Seite. Fehlt Pillow, oder hat
ein Kandidat des Durchgangs ein PDF und `pypdfium2` fehlt, bricht
`vorbereiten` vor dem ersten Auftrag ab und schreibt nichts (ADR-0013).

Der Auftrag einer Wissenskarte hat dieselbe Form, nur ohne die Angabe zum
Ablauf aus dem Bild, denn eine Wissenskarte hat keinen Ablauf. Die Kennungen
stehen darin samt den Steuerungsschwerpunkten. Bilder bekommt sie nur bei
`quellgrafik: ausschnitt`: Ihr Auftrag hat dann `## Ausschnitte` wie der einer
Übung, nur setzt der Entwurf jeden Ausschnitt als Bildverweis an die
Kernaussage, die er zeigt. Bei `eingebettet` und `keine` schneidet
`vorbereiten` für sie nichts aus, ihr Auftrag hat kein `## Ausschnitte` und
sagt, dass sie keine Bilder bekommt. Ein Durchgang nur mit Wissenskarten
braucht bei `eingebettet` deshalb kein Pillow.

Ein Kartenentwurf hat das Frontmatter der Karte ohne `id` (ADR-0010), die
Abschnitte der Karte und am Ende `## Freigabe` mit beiden Listen, davor, wenn
er welche hat, die Liste seiner Ausschnitte:

```markdown
## Freigabe

Ausschnitte:
- `17.quellgrafik-1.jpg`: `seite-26.jpg`, links 8, oben 42, rechts 94, unten 88
- `17.quellgrafik-2.png`: `Merkmale.pdf` S. 3, links 5, oben 20, rechts 95, unten 61

Vorschläge:
- `level_max`: Technikübung, die Schwierigkeit steuert der Ball.

Rückfragen:
1. Wohin kommen die gefangenen Bälle zurück? Vermutung im Entwurf: keine
```

Jede Rückfrage stellt genau eine Frage, mit genau einem Fragezeichen, und
endet auf `Vermutung im Entwurf: …` oder auf `Vermutung im Entwurf: keine`.
Ein Vorschlag beginnt mit seinem Ziel in Backticks: dem Feld, oder der
Überschrift des Abschnitts samt `##`, dahinter, wo im Abschnitt, etwa
`` `## Ablauf`, Schritt 2: … ``. Eine leere Liste heißt `Vorschläge: keine`.

Ein Ausschnitt nennt den Namen der Quellgrafik, die Datei des Kandidaten
relativ zum Quellenordner, bei einem PDF die Seite, gezählt ab 1, und das
Rechteck: links, oben, rechts, unten in ganzen Prozent der Seite, wie sie
aufrecht steht. Die Übungskarte trägt die Namen in `schaubild:`, wie eine
Quellgrafik, die `vorbereiten` ausgeschnitten hat. Die Wissenskarte setzt jeden
Ausschnitt als Bildverweis an die Kernaussage, die er zeigt, mit seinem Namen
als Pfad: `![Bildreihe oberes Zuspiel](17.quellgrafik-1.png)`.

Der Entwurf einer Wissenskarte hat das Frontmatter der Wissenskarte ohne `id`
und `angelegt`, auch `schwerpunkt` und `uebungen`, dann als `[]`, dazu ihre
beiden Abschnitte und `## Freigabe` in derselben Form. Was die Quelle sagt,
steht in ihm ohne Weiteres. Was daraus abgeleitet ist, steht als Vorschlag
unter `## Freigabe` und zeigt auf seinen Punkt:
`` `## Was das fürs Training heißt`, Punkt 2: … ``. So kommt keine Ableitung
ohne das Ja des Trainers auf die Karte.

`sammelimport.py pruefen` weist einen Entwurf ab, wenn er das Datenmodell
bricht oder die Form der Freigabe nicht einhält. Der Kandidat geht dann auf
`offen`, der Grund steht in der Notiz, und der nächste Durchgang entwirft ihn
neu. `uebernehmen` prüft genauso, setzt aber nichts, siehe unten. Geprüft
wird:

- das Frontmatter: jedes Feld der Karte außer `id` und `angelegt`, und keine
  `id`;
- die Felder mit denselben Regeln wie im Linter, darunter die kontrollierten
  Werte und `schwerpunkt` nur mit Kennungen aus `schwerpunkte.md`, die zur
  Disziplin der Karte passen;
- `quelldatei`: relativ zu `quellen/`, und jede genannte Datei liegt dort.
  Anders als auf einer Karte von Hand ist das hier kein freier Text: Der
  Auftrag gibt den Wert vor, mit den Dateien des Kandidaten, bei mehreren
  durch Komma getrennt. Trägt ein Dateiname selbst ein Komma, fügt die
  Prüfung benachbarte Teile wieder zusammen, bis jedes Stück eine vorhandene
  Datei nennt. Erst wenn das nicht aufgeht, ist der Wert falsch;
- die Quellgrafiken: nur die eigenen, jede einmal, und jede eingetragene liegt
  neben dem Entwurf;
- `## Freigabe` mit beiden Listen, jede Rückfrage und jeder Vorschlag in der
  Form oben. Ein Vorschlag nennt ein Feld aus dem Frontmatter oder einen
  Abschnitt, den der Entwurf hat;
- die Ausschnitte: jeder in der Form oben, mit dem Namen einer eigenen
  Quellgrafik, der nur einmal vorkommt, einer Datei des Kandidaten, bei einem
  Seitenbereich einer Seite daraus, einer Endung, die zur Datei passt, und
  bei einer Übung eingetragen in `schaubild:`, bei einer Wissenskarte in einem
  Bildverweis im Text. Dann schneidet `pruefen` jeden neu aus, über
  dieselbe Funktion wie `ausschnitt.py`, und legt ihn neben den Entwurf, bei
  jedem Lauf. Nach einer Änderung der Zahlen liegt danach der neue da. Lässt
  er sich nicht schneiden, etwa weil es die Seite nicht gibt, wird der Entwurf
  abgewiesen. Fehlt dafür Pillow oder `pypdfium2`, bricht `pruefen` ab und
  lässt die Übersicht, wie sie ist. `vorbereiten` und `uebernehmen` prüfen
  einen Entwurf genauso und schneiden dabei mit.

Welche Sorte Karte ein Entwurf werden soll, sagt das Ergebnis seiner Zeile,
nicht der Entwurf. Den Entwurf einer Wissenskarte prüft `pruefen` mit den
Regeln, die der Linter an eine Wissenskarte legt: das Frontmatter mit jedem
Feld der Wissenskarte außer `id` und `angelegt`, und keine `id`; ein Titel,
der auf `?` endet; `thema` und `disziplin` mit bekannten Werten; Kennungen
aus `schwerpunkte.md`, die zur Disziplin der Karte passen, auch
Steuerungsschwerpunkte; jede ID in `uebungen` aus `uebungen/`; `quelldatei`
wie oben; beide Abschnitte; `## Freigabe` wie oben. Jeder Bildverweis nennt
einen Ausschnitt aus der Liste, der nach dem Schneiden neben dem Entwurf
liegt. Ein Verweis auf einen gestrichenen Ausschnitt weist den Entwurf ab,
auch wenn dessen Datei vom letzten Lauf noch daneben liegt. Ein Entwurf in
der Form einer Übungskarte fällt unter einer `wissen`-Zeile durch. Den Status
`rückfrage` bekommt eine Wissenskarte nur durch eine Rückfrage ohne Vermutung.

Mit `--json` gibt `pruefen` je Kandidat mit Entwurf aus, was die Freigabe im
Chat braucht: unter `sorte` `uebungskarte` oder `wissenskarte`, die Felder des
Entwurfs, die Vorschläge getrennt nach Feldern und Textstellen, die
Rückfragen getrennt nach mit und ohne Vermutung, ob der Ablauf aus dem Bild
kommt, den Pfad des Entwurfs und als Liste `quellgrafiken` die Pfade der
Quellgrafiken, die er einträgt, in seiner Reihenfolge, bei einer Wissenskarte
die aus ihren Bildverweisen in der Reihenfolge des Texts. Als Liste
`ausschnitte` steht jeder Ausschnitt da, mit `name`, `pfad`, `datei`, `seite`
und `rechteck` (`links`, `oben`, `rechts`, `unten`). Kandidaten
ohne Entwurf stehen nur in der Übersicht. Die Textstellen ergeben in
der Tabelle die Spalte „aus dem Bild“. Als Liste `quellgrafik_fehlt` stehen die
PDFs des Kandidaten da, deren Bild sich nicht ausschneiden ließ, relativ zum
Quellenordner. `pruefen` liest sie aus dem Auftrag, sie sind also auch nach
einem Abbruch noch da. Mit dem Übernehmen verschwindet der Auftrag und mit ihm
diese Angabe.

Bei der Freigabe bekommt der Entwurf seine ID und wird Karte in `uebungen/`,
mit `angelegt` von heute und ohne `## Freigabe`. Entwurf und Auftrag
verschwinden dann. Der Entwurf einer Wissenskarte wird ebenso
`wissen/wi-######-<slug>.md`, mit der nächsten freien `wi-`-ID und dem Slug
aus der Frage ohne Fragezeichen. Fehlt `wissen/`, legt `uebernehmen` es an.
Übungen und Wissenskarten zählen getrennt, auch in einem Aufruf. Die
Quellgrafik einer Übung kommt unter dem Namen der Karte nach `schaubilder/`,
etwa `ue-000291-abwehr-vom-kasten.png`, und `schaubild:` zeigt darauf. Sie
behält ihre Endung, ein Ausschnitt aus einem Foto wird also
`ue-000291-abwehr-vom-kasten.jpg`. Mehrere bekommen den Namen der Karte mit
Nummer, in der Reihenfolge des Entwurfs, etwa `ue-000291-zirkel-1.png`, und
`schaubild:` trägt sie als
Liste. Eine einzelne Quellgrafik bleibt ein einzelner Name, auch wenn der
Entwurf sie in eckigen Klammern nennt. Die Quellgrafiken einer Wissenskarte
kommen ebenso unter ihrem Namen nach `schaubilder/`, mehrere nummeriert in der
Reihenfolge ihrer Bildverweise im Text, und die Verweise zeigen danach von
`wissen/` aus dorthin, etwa auf `../schaubilder/wi-000003-oberes-zuspiel-1.png`.
Streicht der Trainer einen Kandidaten, wird er `übersprungen`, mit dem Grund
in der Notiz. Stellt er ihn zurück, um
ihn später zu holen, wird er `zurückgestellt`, auch mit Grund, und sein
Ergebnis bleibt. Ergänzt er als Duplikat eine bestehende Karte, wird er
`ergänzt`, mit deren ID in der Spalte Karte. Aus allen dreien entsteht keine
Karte, aber auch ihr Entwurf und Auftrag verschwinden. Ist im Quellenordner
nichts mehr offen, verschwinden auch `kartenentwuerfe/<ordner>/` und
`in_arbeit`. Offen ist dabei jede Zeile, die noch auf ihre Karte wartet, ob
Übungs- oder Wissenskarte.

Nicht übernommen wird ein Kandidat, unter dessen Namen in `schaubilder/` schon
eine Datei liegt, einer, dessen freigegebener Entwurf die Prüfung nicht
besteht, und einer, für dessen Ausschnitt Pillow oder `pypdfium2` fehlt.
Entwurf und Status bleiben dann, wie sie sind, denn der Entwurf trägt
die Antworten des Trainers, und ein neuer Durchgang überschriebe sie. Die
Ausgabe nennt den Fehler, die übrigen Kandidaten übernimmt `uebernehmen`
trotzdem und endet mit einem Exitcode ungleich 0. Fehlt `quellen/<ordner>/`,
etwa weil die Nextcloud ihn an diesem Rechner nicht abgleicht, bricht
`uebernehmen` ab, bevor es etwas schreibt.

Den Ordner `kartenentwuerfe/` legt `init_struktur.py` nicht an. Er entsteht mit
dem ersten Sammelimport. `index.py` und `suche.py` lesen ihn nicht, ein
Kartenentwurf taucht also in keiner Suche auf.

## Das Schaubild ist ein Erzeugnis, die Szene ist die Quelle

Ein Schaubild wird nicht von Hand gezeichnet. Die Quelle ist eine **Szene**:
eine Beschreibung in YAML, die durchgehend in Metern rechnet und aus der
`schaubild.py` ein SVG erzeugt (ADR-0004). Beide liegen in `schaubilder/`
unter demselben Basisnamen:

```
schaubilder/ue-000042.szene.yml    die Quelle, hier wird geändert
schaubilder/ue-000042.svg          das Erzeugnis, wird überschrieben
```

Auf der Karte steht in `schaubild:` der Dateiname des **Bildes**, nicht der
Szene. Zeigt er ins Leere, meldet `index.py` das. Das Feld schreibt keine
Endung vor: ältere Schaubilder ohne Szene bleiben liegen, wie sie sind.

Hat eine Übung mehrere Bilder, trägt das Feld eine Liste in eckigen Klammern.
Ein Zirkel aus PlayDrill etwa hat ein Bild je Blatt, die Übersicht vorn:

```yaml
schaubild: [ue-000291-zirkel-1.png, ue-000291-zirkel-2.png, ue-000291-zirkel-3.png]
```

Beide Formen gelten. Die Leseansicht zeigt die Bilder in der Reihenfolge der
Liste, `suche.py --lang` nennt jedes als eigenen Pfad, und `index.py` meldet
jeden Eintrag einzeln, den es nicht gibt. Fehlt eine Datei, lässt die
Leseansicht nur dieses Bild weg. Eine Karte mit Liste hat Bilder, auch für
`volleyball-schaubild`, das Karten ohne Bild sucht.

Die **Grundform** einer Szene ist eine **Feldvorlage** oder eine **freie
Leinwand**. Als Feldvorlage gibt es Halle 9×18 m mit Netz und beiden
Angriffslinien und Beach 8×16 m mit Netz und sonst nichts. Die freie Leinwand
trägt ihr Maß in Metern und hat kein Feld darunter. Sie ist für den
Stationsaufbau da, der auf kein Feld passt.

Was nicht rendert, schreibt `schaubild.py` nicht. Mit mehreren Trainern ändert
aber einer die Szene, und keiner zeichnet neu. Deshalb liest `index.py` jede
`*.szene.yml` in `schaubilder/`, ohne zu zeichnen. Es meldet:

- eine Szene, die nicht aufgeht, mit dem Grund, den auch `schaubild.py` nennt;
- eine Szene ohne ihr SVG;
- ein SVG, das älter ist als seine Szene.

Die beiden letzten Meldungen nennen den Aufruf, der das Bild zeichnet. Ein Bild
ohne Szene meldet `index.py` nicht.

Was Szene, Feldvorlage und Rolle bedeuten, steht im Glossar. Wie eine Szene
aufgebaut ist, steht in `referenzen/SCHAUBILDER.md`.

## Der Trainingsplan

`trainings/<gruppe>/JJJJ-MM-TT.md`, Frontmatter mit `datum`, `gruppe`,
`leitteam`, `mesozyklus`, `teilnehmer`, `dauer`, `spielflaechen`, `trainer`,
`status`. Das Gerüst steht in `VORLAGEN.md`. Hier steht, woran `leseansicht.py`
erkennt, was wohin gehört.

### Kopf

Die Überschrift heißt `# Training <Datum> — <Kurztitel>`. Oben in der
Leseansicht steht der Kurztitel, also was nach dem Gedankenstrich kommt. Fehlt
der Gedankenstrich, steht dort die ganze Überschrift. Darunter stehen Wochentag
und Datum aus `datum`, der Name der Gruppe, `teilnehmer`, `dauer` und die Zahl
der Hallenteile aus `spielflaechen`. Was im Frontmatter fehlt oder leer ist,
fällt weg.

Den Namen der Gruppe liest die Leseansicht aus der Wurzeldatei, unter
`gruppen.<gruppe>.name`. Steht dort keiner, oder liegt der Plan außerhalb eines
Arbeitsordners, steht das Kürzel aus `gruppe`.

### Die Ablauftabelle

Die erste Tabelle unter `## Ablauf`, mit diesen Spalten:

```
| Zeit | Programmpunkt | Übung | ID | Anpassung heute | Warum hier |
```

Jede Zeile ist ein Programmpunkt, auch Pause und Umbau.

- **Zeit** ist die Zeitangabe: von–bis in ganzen Minuten ab Beginn, mit
  Halbgeviertstrich geschrieben, `46–93`. Ein Bindestrich wird auch erkannt.
  Daraus ergibt sich die Dauer des Programmpunkts. Steht etwas anderes da, etwa
  `18:00`, bleibt es als Text stehen, der Programmpunkt hat keine Dauer, und
  kein Abschnitt kann ihm zugeordnet werden.
- **Programmpunkt** ist sein Name. Laufen zwei zur selben Zeit, einer je
  Hallenteil, steht der Hallenteil im Namen: „Zuspiel, Hallenteil A". Er heißt
  nach einem einzelnen Buchstaben oder einer Ziffer, „Hallenteil wechseln"
  nennt keinen. Zeitangabe und Hallenteil zusammen bestimmen einen
  Programmpunkt. Beginnt der Name mit „Pause" oder „Umbau", erscheint er in der
  Leseansicht gedämpft.
- **ID** verweist auf die Karte. Was die Übung ist, steht dort, nicht hier.
- **Anpassung heute** ist alles, was an diesem Abend anders war als auf der
  Karte: Gruppengrößen, welches Netz, veränderte Regeln, Anpassung an eine
  Altersklasse. Die Karte bleibt dabei unberührt. „—" heißt: nichts anders.
- **Warum hier** ist ein Satz, warum die Übung an dieser Stelle steht.

Ältere Pläne nennen die zweite Spalte „Teil", noch ältere „Block", und die
Spalte Anpassung oft ohne „heute". Die Leseansicht versteht alle diese Namen,
die Pläne gelten weiter.

Es gibt keine Spalte Quelle und keine Spalte Material mehr. Beides steht auf
der Karte, Material zusätzlich gesammelt als eigener Abschnitt.

### Abschnitte und ihr Programmpunkt

Ein Abschnitt reicht von seiner Überschrift `##` oder `###` bis zur nächsten
derselben oder einer höheren Ebene. Beginnt die Überschrift mit einer
Zeitangabe, gehört der Abschnitt zu dem Programmpunkt mit dieser Zeitangabe.
In der Leseansicht steht er dort, wo man den Programmpunkt aufklappt:

```markdown
## 46–93 Drei Sechser mit Zweierserie
### 46–93 Hallenskizze
```

- Folgt auf die Zeitangabe ein Hallenteil, gehört der Abschnitt nur zum
  Programmpunkt in diesem Hallenteil: `### 69–89 Hallenteil A: Hallenskizze`.
  Ohne Hallenteil gehört er zu jedem Programmpunkt mit dieser Zeitangabe.
- Ein `###` ohne Zeitangabe folgt seinem `##`. Ein `###` mit eigener
  Zeitangabe entscheidet selbst, wohin er gehört, unter einem `##` mit
  Zeitangabe genauso wie unter einem ohne. Unter `## 69–89 Zuspiel` landet
  `### 69–89 Hallenteil A: Hallenskizze` nur bei Hallenteil A, und unter
  `## Athletik` wandert jeder `### <Zeitangabe> Athletik` zu seinem
  Programmpunkt.
- Im Programmpunkt steht jede Überschrift ohne Zeitangabe und Hallenteil.
  Gleicht der Rest dem Namen der Übung, fällt sie weg, beim `##` wie beim
  `###`.
- Eine Überschrift, die mit einer Uhrzeit wie `18:00` beginnt, trägt keine
  Zeitangabe.

Alles ohne Zeitangabe außer „Zum Nachschlagen" steht in der Leseansicht unter
**Vorbereitung**, in der Reihenfolge des Plans, auch die Nachbereitung. Was im
Abschnitt „Ablauf" neben der Tabelle steht, kommt dort unter „Ablauf", auch
wenn die Überschrift im Plan mehr sagt, etwa `## Ablauf (90 min)`. Ein
Abschnitt, der leer ist oder leer wird, weil alle seine `###` zu
Programmpunkten gewandert sind, fehlt.

Der Plan schreibt kein „siehe unten". Die Zeitangabe verbindet Zeile und
Abschnitt. `leseansicht.py` ändert keinen Text, auch nicht in alten Plänen:
Dort steht alles Ausgeschriebene unter Vorbereitung.

**Eine Zeitangabe ohne Programmpunkt.** Passt die Zeitangabe einer Überschrift
auf keinen Programmpunkt, bleibt der Abschnitt unter Vorbereitung.
`leseansicht.py` schreibt die Leseansicht trotzdem, endet mit 0 und meldet
jeden solchen Abschnitt auf der Konsole, unter der Zeile `Leseansicht:`:

```
Kein Programmpunkt mit der Zeitangabe 50–60 für den Abschnitt „50–60 Spiel“. Er steht unter Vorbereitung.
```

Mit Hallenteil heißt es „mit der Zeitangabe 69–89 in Hallenteil C". Meist ist
es ein Tippfehler oder eine Zeit, die sich beim Planen verschoben hat.

### Zum Nachschlagen

`## Zum Nachschlagen` ist ein fester Abschnitt für Themen, die mehrere
Programmpunkte brauchen: die Sechser, die Läufer im 5-1, die Regeln. Jedes
Thema steht als `###` darunter und wird in der Leseansicht ein Reiter mit
seiner Überschrift als Namen. Text vor dem ersten Thema steht über den Reitern.
Auch ein Thema ohne Text wird ein Reiter, damit ein Verweis darauf nicht ins
Leere führt. Nur ein `## Zum Nachschlagen` ganz ohne Text und ohne Thema fällt
weg.

Ein **Verweis** ist ein gewöhnlicher Markdown-Link auf ein Thema unter „Zum
Nachschlagen", genauer auf den Anker seiner Überschrift:
`[die Sechser](#die-sechser)`. Der Anker entsteht wie bei GitHub: klein
geschrieben, Satzzeichen fallen weg, jedes Leerzeichen wird ein Bindestrich,
Umlaute bleiben. Aus `### Die Läufer im 5-1 (Rotation)` wird
`#die-läufer-im-5-1-rotation`. So führt der Link auch in der `.md` zur
Überschrift.

Steht ein Verweis in „Anpassung heute", in einem Abschnitt des Programmpunkts
oder in „Warum hier", bekommt der Programmpunkt in der Leseansicht einen Knopf,
der den Reiter öffnet, je Reiter einen. Ohne JavaScript springt er zum Thema
unten auf der Seite. Ein Link auf etwas anderes bleibt ein gewöhnlicher Link.

### Athletik

Eine Tabelle, deren erste beiden Spalten `Nr` und `Übung` heißen, wird in der
Leseansicht eine Liste zum Aufklappen. Gedacht ist sie für die Athletik:

```markdown
| Nr | Übung | Worauf es ankommt | Heute |
|---|---|---|---|
| 1 | Ausfallschritt mit Drehung | Blick zur hinteren Hand | 3–5 Wdh. je Seite |
```

Zugeklappt steht „1. Ausfallschritt mit Drehung" und darunter, was in `Heute`
steht, die Dosierung dieses Abends. Die übrigen Spalten stehen im
aufgeklappten Eintrag, eine einzelne ohne Beschriftung, mehrere jede unter
ihrer Spaltenüberschrift. Jede andere Tabelle bleibt eine Tabelle, die man auf
dem Handy seitlich wischt.

Gehört Athletik zu mehreren Programmpunkten, bekommt jeder unter `## Athletik`
einen eigenen `### <Zeitangabe> Athletik` mit seiner Tabelle.

## Korrigieren ja, umschreiben nein

Mehrere Trainer arbeiten im selben Ordner.

Erlaubt: Tippfehler, fehlende Felder, klarere Formulierung, Schaubild ergänzen.

Nicht erlaubt: eine bestehende Karte auf ein anderes Niveau oder eine andere
Altersklasse umschreiben. Wer per ID auf sie verweist, bekommt sonst eine
andere Übung, ohne es zu merken.

Stattdessen: Anpassung in den Abschnitt `## Variationen`. Ändert sie den
Charakter der Übung wirklich, eine eigene Karte mit `variante_von: ue-######`.

Beim Planen entsteht eine Anpassung erst nur im Trainingsplan. Ob sie in die
Bibliothek wandert, entscheidet die Nachbereitung nach der Einheit. So wächst
die Bibliothek aus dem, was funktioniert hat.

## index.json gehört nicht nach Nextcloud

`index.py` baut den Index bei jedem Aufruf komplett neu, deshalb kann er nicht
veralten. Die `index.json` landet im Cache des Rechners. Läge sie im geteilten
Ordner, würde jeder Lauf jedes Trainers dieselbe Datei neu schreiben und der
Sync legte Konfliktkopien an.

`index.md` ist die Lesebrille für Menschen und gehört in die Wurzel, wird aber
nur auf ausdrückliche Ansage neu gebaut (`index.py --md`).

## Konfliktkopien

Ändern zwei Trainer dieselbe Datei, bevor Nextcloud abgleicht, behält der
Server eine Fassung unter dem alten Namen. Die andere legt der Nextcloud-Client
daneben, etwa als `2026-09-15 (conflicted copy christian 2026-10-03 101500).md`.

`index.py` meldet jede solche Datei im Arbeitsordner, auch unter `quellen/`,
und nennt die Datei, zu der sie gehört. Als Karte oder Trainingsplan zählt sie
nicht. Erkannt werden die Namen, die der Client schreibt:

- `(conflicted copy …)`, bei älteren Clients `_conflict-` mit Datum und
  Uhrzeit. Das sind zwei Fassungen einer Datei. Wer die Meldung bekommt, führt
  sie zusammen und löscht die Kopie.
- `(case clash from …)`. Auf dem Server liegen zwei Dateien, deren Namen sich
  nur in Groß- und Kleinschreibung unterscheiden, und unter Windows hat nur
  eine davon Platz. Eine der beiden bekommt einen anderen Namen.

## Skripte

Alle liegen unter `${CLAUDE_PLUGIN_ROOT}/scripts/` und brauchen nur Python 3
aus der Standardbibliothek. Es gibt drei Ausnahmen von der Standardbibliothek:

- **Pillow:** `bilder_aufbereiten.py` und `ausschnitt.py` brauchen es, dazu
  `sammelimport.py`, wenn die Quellgrafik eingebettet oder als Ausschnitt
  kommt. Alle drei brechen ohne es mit einem Installationshinweis ab und
  schreiben nichts (ADR-0005). HEIC öffnet Pillow erst mit dem Zusatzpaket
  `pillow-heif`. Fehlt es, nennt `bilder_aufbereiten.py` die HEIC-Dateien mit
  Installationshinweis, lässt sie liegen und bereitet die übrigen auf.
- **`pdftotext`:** `sammelimport.py vorbereiten` liest damit den Text von
  PDFs, für die Planeingabe und für die Aufträge. Gesucht wird erst im PATH,
  unter Windows danach neben `git.exe`, denn Git für Windows bringt es mit.
  Fehlt es, sagt das Skript das einmal mit Installationshinweis und macht ohne
  Text weiter (ADR-0008).
- **`pypdfium2`:** `ausschnitt.py` zeichnet damit eine PDF-Seite als Bild,
  bevor Pillow den Ausschnitt schneidet, und `sammelimport.py` über dieselbe
  Funktion. Fehlt es, endet ein Ausschnitt aus einem PDF mit
  Installationshinweis und schreibt nichts. Bei `quellgrafik: ausschnitt`
  bricht `vorbereiten` dann ab, sobald ein Kandidat des Durchgangs ein PDF
  hat. Ein Ausschnitt aus einem Foto geht ohne (ADR-0013).

Dazu nehmen zwei Skripte einen Browser, wo einer da ist:

- **Edge oder Chrome:** `export_pdf.py` druckt damit, wenn pandoc keine
  PDF-Maschine findet, und `schaubild.py --png` nimmt damit die Ansicht als
  PNG auf. Gesucht und aufgerufen wird der Browser allein in `browser.py`.
  Fehlt er, nennt `export_pdf.py` die anderen Wege zum PDF, und
  `schaubild.py` schreibt das SVG trotzdem und sagt, dass die Ansicht als PNG
  fehlt.

Die übrigen Skripte brauchen weder Pillow noch `pdftotext` noch `pypdfium2`
noch einen Browser.

| Skript | Wofür |
|---|---|
| `index.py` | Index neu bauen, Bibliothek prüfen, mit `--md` die Lesebrille schreiben, samt den Wissenskarten nach Thema |
| `suche.py` | Übungen filtern, das ist der normale Zugriff auf die Bibliothek. Mit `--wissen` alle Wissenskarten, mit `--naechste-id` die ID für die nächste Übungskarte, mit `--naechste-id --wissen` die für die nächste Wissenskarte, mit `--plaene-mit-leseansicht` die Trainingspläne, die eine Karte nennen und schon eine Leseansicht haben |
| `leseansicht.py` | aus einem Trainingsplan die HTML-Fassung fürs Handy erzeugen, samt den Schaubildern der verwendeten Übungen. Meldet jede Überschrift, deren Zeitangabe auf keinen Programmpunkt passt |
| `export_pdf.py` | PDF zum Ausdrucken |
| `schaubild.py` | aus einer Szene das Schaubild als SVG zeichnen, mit `--png` dazu eine Ansicht als PNG im Temp-Verzeichnis |
| `bilder_aufbereiten.py` | Quellbilder verkleinern, nach EXIF geradedrehen und aus TIFF und HEIC ein JPEG machen |
| `ausschnitt.py` | eine Quellgrafik als Ausschnitt schneiden, aus einem Foto oder einer PDF-Seite: `<quelle> [--seite N] --rechteck LINKS OBEN RECHTS UNTEN <ziel>`, das Rechteck in ganzen Prozent der aufrechten Seite. Aus einem Foto wird ein JPEG, aus einer PDF-Seite, deren lange Kante 2000 Pixel misst, ein PNG. Nennt am Ende das Maß in Pixeln |
| `sammelimport.py` | Sammelimport über einen Quellenordner: `vorbereiten --plan` legt die Eingabe für den Zerlegungsplan an, mit `--zurueckgestellte` samt den zurückgestellten Zeilen, `vorbereiten` die Aufträge, `pruefen` setzt den Status aus den Entwürfen und gibt mit `--json` aus, was die Freigabe braucht, `uebernehmen` macht freigegebene Entwürfe zu Karten und trägt gestrichene, zurückgestellte und ergänzende Kandidaten ein |
| `ids_umstellen.py` | einen Arbeitsordner von vierstelligen auf sechsstellige IDs umstellen, einmal je Arbeitsordner |

`index.py` ohne Argumente ist auch der Linter: doppelte IDs, vierstellige IDs
auf Karten und in Trainingsplänen, fehlende oder unbekannte `disziplin`,
unbekannte Schwerpunkte, fehlende Level, ins Leere zeigende `variante_von`,
jeder Eintrag in `schaubild` auf eine Datei, die es unter `schaubilder/` nicht
gibt, Szenen, die nicht aufgehen, Szenen ohne SVG oder mit einem älteren,
Trainingspläne mit unbekannten IDs, Konfliktkopien von Nextcloud. Eine Karte im
Ordner der anderen Sorte meldet er einmal, mit dem Ordner, in den sie gehört.

Bei einer Wissenskarte meldet er dazu eine ID, die nicht `wi-######` ist,
nicht vorn im Dateinamen steht oder doppelt vorkommt, einen Titel ohne
Fragezeichen am Ende, ein fehlendes, leeres oder unbekanntes `thema` und
ebenso `disziplin`, eine unbekannte Kennung in `schwerpunkt` und eine
inhaltliche, die in keiner Disziplin der Karte gilt, eine leere `quelle`, eine
ID in `uebungen`, die es in `uebungen/` nicht gibt, einen Bildverweis, dessen
Datei es nicht gibt, und einen fehlenden der beiden Abschnitte.

Vor größeren Änderungen und nach jedem Import laufen lassen.
