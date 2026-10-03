# Datenmodell

Verbindlich für alle vier Skills. Wer hier abweicht, produziert Karten, die
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
spielflaechen: 1                 # wie viele die Übung braucht
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

### Belastung

`erwachsenenbelastung: true` heißt: die Übung enthält Sprungvolumen, Zusatzlast
oder Maximalkraft, die ein Jugendkörper so nicht wegsteckt. Das ist ein
**Hinweis, kein Filter.** Übungen damit werden Jugendtrainern gezeigt, mit dem
Klartext aus `belastungshinweis` und einem Vorschlag, wie man sie anpasst.
Entschieden wird in der Halle.

Setzen nur, wenn die Quelle es hergibt. Eine geratene Altersfreigabe ist
schlechter als gar keine. Im Zweifel nachfragen.

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
wenn Nextcloud ihre Rechner noch nicht abgeglichen hat.

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
quellgrafik_ausschneiden: true   # optional: die Quellgrafik aus dem PDF ausschneiden
ohne: [Aufst_Pos_D, PLAYDRILL_IMPORT_LOG.md]   # optional: was der Zerlegungsplan auslässt
in_arbeit: christian, 2026-10-02 # schreibt das Skript: wer seit wann daran arbeitet
---

# Sammelimport playdrill

## Absprachen

Freitext: wie sich die Quelle liest und welche Feldregeln für jede Karte
daraus gelten. Geht unverändert in jeden Auftrag.

## Übersicht

| Kandidat | Dateien | Was es ist | Ergebnis | Status | Karte | Notiz |
|---|---|---|---|---|---|---|
| 1 | `Ü_Abwehr/Abwehr vom Kasten.pdf` | Abwehr gegen Angriffe vom Kasten | uebung | importiert | ue-000291 | spieler_min auf 6 |
| 2 | `seite-24.jpg`, `seite-25.jpg` | Übung über zwei Seiten | uebung | offen | | kein Entwurf |
```

- Die Spalte **Kandidat** trägt die Nummer des Kandidaten, fortlaufend je
  Quellenordner. Sie bleibt und benennt Entwurf und Auftrag. Ein zweiter Lauf
  zählt ab der höchsten Nummer in der Übersicht weiter.
- **Dateien** stehen relativ zum Quellenordner, jede in Backticks.
- **Ergebnis** ist eins von `uebung`, `folge`, `zurückgestellt`, `übersprungen`.
  Aus `uebung` und `folge` wird eine Karte mit diesem `typ`.
- **Status** ist eins von `offen`, `bereit`, `rückfrage`, `importiert`,
  `ergänzt`, `übersprungen`, `zurückgestellt`. Die ersten drei warten noch auf
  ihre Karte. `rückfrage` heißt: Hier muss einzeln gefragt werden. Entweder
  hat der Entwurf eine Rückfrage ohne Vermutung, oder sein Ablauf kommt laut
  Auftrag aus dem Bild.

`textmarke` und `platzhalter` sind für die Regel „wenig Text“. Stehen nach der
Textmarke, ohne den Platzhalter, weniger als 150 Zeichen, sagt der Auftrag
„Ablauf aus dem Bild“. Groß- und Kleinschreibung und Zeilenumbrüche zählen
dabei nicht. Ohne Textmarke, oder wenn eine Datei sie nicht trägt, zählt ihr
ganzer Text. Hat eine Datei gar keinen Text, entscheidet der Agent.

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

Die Übersicht ist der freigegebene Zerlegungsplan. Bis zur Freigabe schreibt
ihn der Skill im Gespräch mit dem Trainer. Danach schreibt nur noch
`sammelimport.py` hinein, auch wenn mehrere Agenten parallel entwerfen. Den
Status setzt das Skript aus den Dateien auf der Platte. Die Rückmeldung eines
Agenten zählt dabei nicht.

### `kartenentwuerfe/<ordner>/`

Alles, was ein laufender Sammelimport erzeugt, liegt hier. `planeingabe.md` ist
die Eingabe für den Zerlegungsplan: jede Datei des Quellenordners, die noch in
keiner Zeile der Übersicht steht und die `ohne` nicht auslässt, bei PDFs ihr
Text, die nächste freie Kandidatennummer, ohne Übersicht 1, und die
Bibliotheksliste, in der die Karten aus diesem Quellenordner markiert sind.
Der Rest ist nach der Nummer des Kandidaten benannt: `17.auftrag.md` ist der
Auftrag für den Agenten, `17.md` der Kartenentwurf, `17.quellgrafik.png` die
Quellgrafik, bei mehreren `17.quellgrafik-1.png`, `17.quellgrafik-2.png` und
so weiter.

Der Auftrag trägt unter jedem PDF des Kandidaten dessen ganzen Text, oder den
Hinweis, dass der Agent das PDF selbst lesen muss. Er sagt, ob der Ablauf aus
dem Bild kommt. Ist `quellgrafik_ausschneiden` an, schneidet `vorbereiten`
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

Ein Kartenentwurf hat das Frontmatter der Karte ohne `id` (ADR-0010), die
Abschnitte der Karte und am Ende `## Freigabe` mit beiden Listen:

```markdown
## Freigabe

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
  Abschnitt, den der Entwurf hat.

Mit `--json` gibt `pruefen` je Kandidat aus, was die Freigabe im Chat braucht:
die Felder des Entwurfs, die Vorschläge getrennt nach Feldern und Textstellen,
die Rückfragen getrennt nach mit und ohne Vermutung, ob der Ablauf aus dem Bild
kommt, den Pfad des Entwurfs und als Liste `quellgrafiken` die Pfade der
Quellgrafiken, die er einträgt, in seiner Reihenfolge. Die Textstellen ergeben in
der Tabelle die Spalte „aus dem Bild“.

Bei der Freigabe bekommt der Entwurf seine ID und wird Karte in `uebungen/`,
mit `angelegt` von heute und ohne `## Freigabe`. Entwurf und Auftrag
verschwinden dann. Die Quellgrafik kommt unter dem Namen der Karte nach
`schaubilder/`, etwa `ue-000291-abwehr-vom-kasten.png`, und `schaubild:` zeigt
darauf. Mehrere bekommen den Namen der Karte mit Nummer, in der Reihenfolge
des Entwurfs, etwa `ue-000291-zirkel-1.png`, und `schaubild:` trägt sie als
Liste. Eine einzelne Quellgrafik bleibt ein einzelner Name, auch wenn der
Entwurf sie in eckigen Klammern nennt. Streicht der Trainer einen Kandidaten,
wird er `übersprungen`, mit dem Grund in der Notiz. Ergänzt er als Duplikat
eine bestehende Karte, wird er `ergänzt`, mit deren ID in der Spalte Karte.
Aus beiden entsteht keine Karte, aber auch ihr Entwurf und Auftrag
verschwinden. Ist im Quellenordner nichts mehr offen, verschwinden auch
`kartenentwuerfe/<ordner>/` und `in_arbeit`.

Nicht übernommen wird ein Kandidat, unter dessen Namen in `schaubilder/` schon
eine Datei liegt, und einer, dessen freigegebener Entwurf die Prüfung nicht
besteht. Entwurf und Status bleiben dann, wie sie sind, denn der Entwurf trägt
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

Die Szene wird **nicht vom Linter geprüft.** Sie prüft sich beim Rendern
selbst, und was nicht rendert, wird nicht geschrieben.

Was Szene, Feldvorlage und Rolle bedeuten, steht im Glossar. Wie eine Szene
aufgebaut ist, steht in `referenzen/SCHAUBILDER.md`.

## Der Trainingsplan

`trainings/<gruppe>/JJJJ-MM-TT.md`, Frontmatter mit `datum`, `gruppe`,
`leitteam`, `mesozyklus`, `teilnehmer`, `dauer`, `spielflaechen`, `trainer`,
`status`.

Die Ablauftabelle hat die Spalten Zeit, Teil, Übung, ID, Anpassung, Warum hier.

- **ID** verweist auf die Karte. Was die Übung ist, steht dort, nicht hier.
- **Anpassung** ist alles, was an diesem Abend anders war als auf der Karte:
  Gruppengrößen, welches Netz, veränderte Regeln, Anpassung an eine
  Altersklasse. Die Karte bleibt dabei unberührt.

Es gibt keine Spalte Quelle und keine Spalte Material mehr. Beides steht auf
der Karte, Material zusätzlich gesammelt als eigener Abschnitt.

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

## Skripte

Alle liegen unter `${CLAUDE_PLUGIN_ROOT}/scripts/` und brauchen nur Python 3
aus der Standardbibliothek. Es gibt zwei Ausnahmen:

- **Pillow:** `bilder_aufbereiten.py` braucht es, dazu `sammelimport.py
  vorbereiten`, wenn es die Quellgrafik ausschneiden soll. Beide brechen ohne es
  mit einem Installationshinweis ab und schreiben nichts (ADR-0005).
- **`pdftotext`:** `sammelimport.py vorbereiten` liest damit den Text von
  PDFs, für die Planeingabe und für die Aufträge. Gesucht wird erst im PATH,
  unter Windows danach neben `git.exe`, denn Git für Windows bringt es mit.
  Fehlt es, sagt das Skript das einmal mit Installationshinweis und macht ohne
  Text weiter (ADR-0008).

Die übrigen Skripte brauchen weder Pillow noch `pdftotext`.

| Skript | Wofür |
|---|---|
| `index.py` | Index neu bauen, Bibliothek prüfen, mit `--md` die Lesebrille schreiben |
| `suche.py` | Übungen filtern, das ist der normale Zugriff auf die Bibliothek. Mit `--naechste-id` die ID für die nächste Karte |
| `leseansicht.py` | aus einem Trainingsplan die HTML-Fassung fürs Handy erzeugen, samt den Schaubildern der verwendeten Übungen |
| `export_pdf.py` | PDF zum Ausdrucken |
| `schaubild.py` | aus einer Szene das Schaubild als SVG zeichnen |
| `bilder_aufbereiten.py` | Quellbilder verkleinern und nach EXIF geradedrehen |
| `sammelimport.py` | Sammelimport über einen Quellenordner: `vorbereiten --plan` legt die Eingabe für den Zerlegungsplan an, `vorbereiten` die Aufträge, `pruefen` setzt den Status aus den Entwürfen und gibt mit `--json` aus, was die Freigabe braucht, `uebernehmen` macht freigegebene Entwürfe zu Karten und trägt gestrichene und ergänzende Kandidaten ein |
| `ids_umstellen.py` | einen Arbeitsordner von vierstelligen auf sechsstellige IDs umstellen, einmal je Arbeitsordner |

`index.py` ohne Argumente ist auch der Linter: doppelte IDs, vierstellige IDs
auf Karten und in Trainingsplänen, fehlende oder unbekannte `disziplin`,
unbekannte Schwerpunkte, fehlende Level, ins Leere zeigende `variante_von`,
jeder Eintrag in `schaubild` auf eine Datei, die es unter `schaubilder/` nicht
gibt, Trainingspläne mit unbekannten IDs. Vor größeren Änderungen und nach jedem
Import laufen lassen.
