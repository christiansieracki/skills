# Datenmodell

Verbindlich für alle vier Skills. Wer hier abweicht, produziert Karten, die
`suche.py` nicht findet.

## Ordner

Der Arbeitsordner wird an der Markerdatei `trainingsplanung-root.yml` erkannt.
Ab dem geöffneten Ordner nach oben suchen, nie einen Pfad raten. `finde_wurzel()`
in `scripts/tpdaten.py` macht das.

```
<wurzel>/
├── trainingsplanung-root.yml   Gruppen, Teams, führendes Team
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
Skill hart kodieren.

## Die Übungskarte

Dateiname `ue-####-sprechender-slug.md`, Frontmatter komplett:

```yaml
---
id: ue-0042                      # stabil, ändert sich nie
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
schaubild: null                  # Dateiname in schaubilder/, landet in der Leseansicht
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
beim Umbenennen der Datei. Sonst brechen alle Pläne, die auf sie zeigen.

Nächste freie ID: `python3 scripts/suche.py --json` (Windows: `python`) und die
höchste Nummer plus eins. Format immer vierstellig mit führenden Nullen. Beim
Sammelimport vergibt `sammelimport.py uebernehmen` sie selbst, erst bei der
Freigabe (ADR-0010).

Der Dateiname beginnt mit der ID, darf aber sonst geändert werden.

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
---

# Sammelimport playdrill

## Absprachen

Freitext: wie sich die Quelle liest und welche Feldregeln für jede Karte
daraus gelten. Geht unverändert in jeden Auftrag.

## Übersicht

| Kandidat | Dateien | Was es ist | Ergebnis | Status | Karte | Notiz |
|---|---|---|---|---|---|---|
| 1 | `Ü_Abwehr/Abwehr vom Kasten.pdf` | Abwehr gegen Angriffe vom Kasten | uebung | importiert | ue-0291 | spieler_min auf 6 |
| 2 | `seite-24.jpg`, `seite-25.jpg` | Übung über zwei Seiten | uebung | offen | | kein Entwurf |
```

- Die Spalte **Kandidat** trägt die Nummer des Kandidaten, fortlaufend je
  Quellenordner. Sie bleibt und benennt Entwurf und Auftrag.
- **Dateien** stehen relativ zum Quellenordner, jede in Backticks.
- **Ergebnis** ist eins von `uebung`, `folge`, `zurückgestellt`, `übersprungen`.
  Aus `uebung` und `folge` wird eine Karte mit diesem `typ`.
- **Status** ist eins von `offen`, `bereit`, `rückfrage`, `importiert`,
  `ergänzt`, `übersprungen`, `zurückgestellt`. Die ersten drei warten noch auf
  ihre Karte. `rückfrage` heißt: Der Entwurf hat eine Rückfrage ohne
  Vermutung, hier muss einzeln gefragt werden.

Die Übersicht ist der freigegebene Zerlegungsplan. Bis zur Freigabe schreibt
ihn der Skill im Gespräch mit dem Trainer. Danach schreibt nur noch
`sammelimport.py` hinein, auch wenn mehrere Agenten parallel entwerfen. Den
Status setzt das Skript aus den Dateien auf der Platte. Die Rückmeldung eines
Agenten zählt dabei nicht.

### `kartenentwuerfe/<ordner>/`

Alles, was ein laufender Sammelimport erzeugt, liegt hier. `planeingabe.md` ist
die Eingabe für den Zerlegungsplan: jede Datei des Quellenordners, die noch in
keiner Zeile der Übersicht steht, bei PDFs ihr Text, und die Bibliotheksliste,
in der die Karten aus diesem Quellenordner markiert sind. Der Rest ist nach der
Nummer des Kandidaten benannt: `17.auftrag.md` ist der Auftrag für den Agenten,
`17.md` der Kartenentwurf.

Ein Kartenentwurf hat das Frontmatter der Karte ohne `id` (ADR-0010), die
Abschnitte der Karte und am Ende `## Freigabe` mit beiden Listen:

```markdown
## Freigabe

Vorschläge:
- `level_max`: Technikübung, die Schwierigkeit steuert der Ball.

Rückfragen:
1. Wohin kommen die gefangenen Bälle zurück? Vermutung im Entwurf: keine
```

Jede Rückfrage endet auf `Vermutung im Entwurf: …` oder auf
`Vermutung im Entwurf: keine`. Eine leere Liste heißt `Vorschläge: keine`.

Bei der Freigabe bekommt der Entwurf seine ID und wird Karte in `uebungen/`,
mit `angelegt` von heute und ohne `## Freigabe`. Entwurf und Auftrag
verschwinden dann. Ist im Quellenordner nichts mehr offen, verschwindet auch
`kartenentwuerfe/<ordner>/`.

Den Ordner `kartenentwuerfe/` legt `init_struktur.py` nicht an. Er entsteht mit
dem ersten Sammelimport. `index.py` und `suche.py` lesen ihn nicht, ein
Kartenentwurf taucht also in keiner Suche auf.

## Das Schaubild ist ein Erzeugnis, die Szene ist die Quelle

Ein Schaubild wird nicht von Hand gezeichnet. Die Quelle ist eine **Szene**:
eine Beschreibung in YAML, die durchgehend in Metern rechnet und aus der
`schaubild.py` ein SVG erzeugt (ADR-0004). Beide liegen in `schaubilder/`
unter demselben Basisnamen:

```
schaubilder/ue-0042.szene.yml    die Quelle, hier wird geändert
schaubilder/ue-0042.svg          das Erzeugnis, wird überschrieben
```

Auf der Karte steht in `schaubild:` der Dateiname des **Bildes**, nicht der
Szene. Zeigt er ins Leere, meldet `index.py` das. Das Feld trägt einen
Dateinamen und schreibt keine Endung vor: ältere Schaubilder ohne Szene bleiben
liegen, wie sie sind.

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
Charakter der Übung wirklich, eine eigene Karte mit `variante_von: ue-####`.

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

- **Pillow:** `bilder_aufbereiten.py` braucht es und bricht ohne es mit einem
  Installationshinweis ab (ADR-0005).
- **`pdftotext`:** `sammelimport.py vorbereiten --plan` liest damit den Text
  von PDFs. Gesucht wird erst im PATH, unter Windows danach neben `git.exe`,
  denn Git für Windows bringt es mit. Fehlt es, sagt das Skript das einmal mit
  Installationshinweis und macht ohne Text weiter (ADR-0008).

Die übrigen Skripte brauchen weder Pillow noch `pdftotext`.

| Skript | Wofür |
|---|---|
| `index.py` | Index neu bauen, Bibliothek prüfen, mit `--md` die Lesebrille schreiben |
| `suche.py` | Übungen filtern, das ist der normale Zugriff auf die Bibliothek |
| `leseansicht.py` | aus einem Trainingsplan die HTML-Fassung fürs Handy erzeugen, samt den Schaubildern der verwendeten Übungen |
| `export_pdf.py` | PDF zum Ausdrucken |
| `schaubild.py` | aus einer Szene das Schaubild als SVG zeichnen |
| `bilder_aufbereiten.py` | Quellbilder verkleinern und nach EXIF geradedrehen |
| `sammelimport.py` | Sammelimport über einen Quellenordner: `vorbereiten --plan` legt die Eingabe für den Zerlegungsplan an, `vorbereiten` die Aufträge, `pruefen` setzt den Status aus den Entwürfen, `uebernehmen` macht freigegebene Entwürfe zu Karten |

`index.py` ohne Argumente ist auch der Linter: doppelte IDs, fehlende oder
unbekannte `disziplin`, unbekannte Schwerpunkte, fehlende Level, ins Leere
zeigende `variante_von`, `schaubild` auf eine Datei, die es unter
`schaubilder/` nicht gibt, Trainingspläne mit unbekannten IDs. Vor größeren
Änderungen und nach jedem Import laufen lassen.
