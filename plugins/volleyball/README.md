# Volleyball Trainingsplanung

Fünf Skills, die zusammen auf einem Markdown-Ordner arbeiten.

| Skill | Wofür |
|---|---|
| `volleyball-saisonplaner` | Saisonplan und Mesozyklen für ein Team |
| `volleyball-trainingsdesign` | einzelne Trainingseinheiten |
| `volleyball-uebungsimport` | neue Übungskarten aus PDFs, Screenshots und Links |
| `volleyball-sammelimport` | einen ganzen Quellenordner auf einmal importieren, mit Freigabe im Chat |
| `volleyball-schaubild` | Schaubilder zu einer Übung, aus einer Szene gezeichnet |

Sie teilen sich Datenmodell, Skripte und Sprachregeln, deshalb liegen sie in
einem Plugin und nicht in fünfen.

Dazu kommen zwei Agenten, die nur der Sammelimport startet. Beide arbeiten mit
Sonnet und dürfen nur lesen und schreiben (ADR-0009).

| Agent | Wofür |
|---|---|
| `volleyball-zerlegungsplan` | legt fest, welche Dateien eines Quellenordners welche Karte ergeben |
| `volleyball-kartenentwurf` | schreibt aus dem Auftrag eines Kandidaten einen Kartenentwurf |

## Wie der Arbeitsordner gefunden wird

An der Markerdatei `trainingsplanung-root.yml`. Die Skills suchen ab dem
geöffneten Ordner nach oben, deshalb darf der Ordner heißen und liegen, wo er
will, solange die Markerdatei mitwandert.

Existiert noch keiner: `python3 scripts/init_struktur.py <zielordner>` legt ihn
mit Startfassungen von `schwerpunkte.md` und `glossary.md` an. Unter Windows
heißt der Aufruf `python`.

## Aufbau

```
plugins/volleyball/
├── skills/            die fünf SKILL.md
├── agents/            die beiden Agenten des Sammelimports
├── referenzen/        DATENMODELL, SPRACHE, VORLAGEN, METHODIK, ...
├── scripts/           index.py, suche.py, leseansicht.py, export_pdf.py,
│                      bilder_aufbereiten.py, schaubild.py, szene.py,
│                      sammelimport.py, ids_umstellen.py
└── tests/             Linter, Suche, Leseansicht, Bildaufbereitung,
                       Schaubilder, PDF-Export, Sammelimport und das
                       Umstellen der IDs gegen einen künstlichen Arbeitsordner,
                       dazu die Agenten gegen das Datenmodell
```

**Im Plugin liegt das Werkzeug, im Arbeitsordner liegen die Daten.** Übungen,
Teams, Trainings, Quellen und die Schwerpunktliste gehören dem Verein und
werden nicht mit einem Plugin-Update überschrieben.

## Tests

```
python3 -m unittest discover -s plugins/volleyball/tests
```

Unter Windows heißt der Aufruf `python`. Die Suite baut sich einen künstlichen
Arbeitsordner im Temp-Verzeichnis und prüft Linter und Suche darüber, so wie
die Skills sie aufrufen: über die Kommandozeile mit `--wurzel`. Die echte
Bibliothek wird nie angefasst und muss dafür nicht einmal existieren.
`unittest` kommt aus der Standardbibliothek, installiert werden muss nichts.

Die Prüfungen der Bildaufbereitung werden übersprungen, wenn Pillow fehlt.
Die Begründung steht im Kopf von `tests/test_bilder.py`.

Der Test des PDF-Exports läuft nur, wo das Skript über Edge oder Chrome
druckt, und braucht dann zehn bis zwanzig Sekunden. Warum, steht im Kopf von
`tests/test_export.py`.

## Voraussetzungen

Python 3 für die Skripte, nur Standardbibliothek. Begrenzte Ausnahmen sind
Pillow und `pdftotext`. Pillow braucht `bilder_aufbereiten.py`, dazu
`sammelimport.py`, wenn es Quellgrafiken aus PDFs ausschneiden soll. Fehlt es,
sagen beide im Klartext, wie es zu installieren ist, und schreiben nichts.
`pdftotext` liest im Sammelimport den Text der PDFs. Ohne es geht es weiter,
die Agenten lesen die PDFs dann selbst. Unter Windows bringt Git für Windows es
mit. Die übrigen Skripte hängen an keinem der beiden, eine frische Installation
ist also sofort benutzbar.

Für den PDF-Export pandoc, dazu eine PDF-Maschine wie wkhtmltopdf oder
weasyprint. Fehlt die Maschine, druckt Edge oder Chrome die HTML-Fassung, dafür
ist keine Installation nötig. Und eine Claude-Umgebung, die Dateien lesen und
schreiben darf.

Aufgerufen wird Python auf macOS und Linux mit `python3`, unter Windows mit
`python`. Dort zeigt `python3` auf den Platzhalter aus dem Microsoft Store und
bricht mit einer Meldung ab, bevor das Skript startet. In den Skills und in
den Skripten steht dafür `<python>`.
