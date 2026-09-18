# Volleyball Trainingsplanung

Drei Skills, die zusammen auf einem Markdown-Ordner arbeiten.

| Skill | Wofür |
|---|---|
| `volleyball-saisonplaner` | Saisonplan und Mesozyklen für ein Team |
| `volleyball-trainingsdesign` | einzelne Trainingseinheiten |
| `volleyball-uebungsimport` | neue Übungskarten aus PDFs, Screenshots und Links |

Sie teilen sich Datenmodell, Skripte und Sprachregeln, deshalb liegen sie in
einem Plugin und nicht in dreien.

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
├── skills/            die drei SKILL.md
├── referenzen/        DATENMODELL, SPRACHE, VORLAGEN, METHODIK, ...
└── scripts/           index.py, suche.py, leseansicht.py, export_pdf.py
```

**Im Plugin liegt das Werkzeug, im Arbeitsordner liegen die Daten.** Übungen,
Teams, Trainings, Quellen und die Schwerpunktliste gehören dem Verein und
werden nicht mit einem Plugin-Update überschrieben.

## Voraussetzungen

Python 3 für die Skripte, nur Standardbibliothek. Für den PDF-Export pandoc,
dazu eine PDF-Maschine wie wkhtmltopdf oder weasyprint. Fehlt die Maschine,
druckt Edge oder Chrome die HTML-Fassung, dafür ist keine Installation nötig.
Und eine Claude-Umgebung, die Dateien lesen und schreiben darf.

Aufgerufen wird Python auf macOS und Linux mit `python3`, unter Windows mit
`python`. Dort zeigt `python3` auf den Platzhalter aus dem Microsoft Store und
bricht mit einer Meldung ab, bevor das Skript startet. In den Skills und in
den Skripten steht dafür `<python>`.
