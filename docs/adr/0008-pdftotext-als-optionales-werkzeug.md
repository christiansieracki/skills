# pdftotext als optionales Werkzeug für den Sammelimport

Der Sammelimport liest die Textebene von PDFs mit `pdftotext`, wenn es da ist.
Nach Pillow (ADR-0005) ist das die zweite Ausnahme von der Festlegung auf die
Standardbibliothek und die erste, die ein externes Programm aufruft. Fehlt es,
liest der Agent das PDF selbst. Der Sammelimport wird dann teurer, bricht aber
nicht ab.

Anlass war die PlayDrill-Bibliothek des Vereins: 258 offene PDFs, eine Übung je
Datei, alle mit Textebene. Drei Dinge gehen nur, wenn der Text schon vor dem
ersten Modellaufruf vorliegt:

- Der Zerlegungsplan bekommt von jeder Datei Titel und erste Zeilen als Text,
  geschätzt 25 000 Tokens für alle 258. Ohne Text bleiben nur die Dateinamen
  oder 258 einzelne Lesevorgänge.
- Welche Quelle zu wenig Text hat, steht vorher fest. Bei PlayDrill sind das 40
  von 258, bei 27 davon steht unter „Ausführung" nur der Platzhalter. Solche
  Kandidaten bekommen ihre Rückfrage nach Regel und nicht nach dem Urteil des
  Modells.
- Der Agent bekommt den Text wortgenau und dazu die ausgeschnittene
  Quellgrafik, die später auch auf der Karte steht.

ADR-0005 hat externe Werkzeuge verworfen, weil unter Windows keins vorhanden
ist. Für `pdftotext` gilt das nicht. Git für Windows bringt Xpdf 4.00 mit
(`…\Git\mingw64\bin\pdftotext.exe`), und Claude Code benutzt unter Windows die
Git Bash daraus. Wo das Plugin unter Windows läuft, ist `pdftotext` also in
aller Regel schon da, nur nicht im PATH von Windows. Unter macOS fehlt es ohne
`brew install poppler`, unter Linux ist es meist als `poppler-utils` da. Die
Entscheidung aus ADR-0005 für Pillow bleibt davon unberührt.

## Considered Options

- **pdftotext voraussetzen** und ohne es abbrechen, wie die Bildaufbereitung
  ohne Pillow. Verworfen: Beim 50-Megapixel-Foto gibt es keinen Weg ohne
  Pillow, beim PDF schon, denn der Agent kann es selbst lesen. Ein Abbruch
  nähme einem Mac-Nutzer den Sammelimport, der für ihn nur teurer würde.
- **Ganz ohne pdftotext**, der Agent liest jedes PDF. Verworfen: Der
  Zerlegungsplan hinge dann an den Dateinamen, und ob eine Quelle zu wenig Text
  hat, entschiede das Modell.

## Consequences

Gesucht wird erst im PATH, unter Windows danach neben `git.exe`
(`…\Git\cmd\git.exe` führt zu `…\Git\mingw64\bin\pdftotext.exe`). Aufgerufen
wird immer mit `-enc UTF-8`, weil Xpdf sonst Latin-1 schreibt und aus
„Ausführung" „Ausf�hrung" wird.

Nur die Vorstufe des Sammelimports ruft `pdftotext` auf. Kein anderes Skript
bekommt eine neue Voraussetzung, und der Agent ruft es nie selbst auf. Fehlt es,
sagt der Sammelimport das einmal, samt Installationshinweis, und macht weiter.

Tests, die `pdftotext` brauchen, werden übersprungen, wo es fehlt.
`DATENMODELL.md` nennt im Abschnitt zu den Skripten künftig zwei Ausnahmen.

## Nachtrag bei der Umsetzung, 01.10.2026

Umgesetzt in `sammelimport.py vorbereiten --plan` (#32). Zwei Stellen oben
gelten so nicht mehr.

- **Aufruf:** `-raw -enc UTF-8`. Ohne `-raw` zieht Xpdf 4.00 die Zeilen eines
  Absatzes zu einer zusammen. Aus den Kopfzeilen eines PlayDrill-Blatts,
  „Trainer/Ersteller", „ZEIT" und „Werkzeuge", wird dann eine Zeile. Poppler
  zieht nichts zusammen, mit `-raw` lesen beide gleich.
- **Wie viel Text:** Der Zerlegungsplan bekommt den ganzen Text, solange der
  Text aller PDFs in einen Aufruf passt, sonst je PDF die ersten Zeilen bis 400
  Zeichen. Die 25 000 Tokens oben galten für die ersten Zeilen allein. Im
  Probelauf hat die Kappung auf 400 Zeichen bei Übersichtsblättern die
  Stationsliste abgeschnitten. Die Schwelle liegt bei 400 000 Zeichen, rund
  100 000 Tokens. Gemessen: `quellen/playdrill` hat 310 000 Zeichen in 343 PDFs
  und kommt ganz, die 260 PDFs aus den Übungsordnern haben 190 000.

## Nachtrag nach der Abnahme, 04.10.2026

Gemessen bei der Abnahme von Welle 1d (#37) im echten Arbeitsordner.

- **Wenig Text:** Die Regel trifft 15 der 260 PDFs aus den Übungsordnern, nicht
  40 von 258 wie oben geschätzt. Den Platzhalter trägt auf der Textebene nur
  `Ü_Abwehr/#12P+_Kat1_Abwehr_Bewegung-Reaktion.pdf`, nicht 27. Von den 15 sind
  sechs Stationsblätter aus `Ü_Zirkelübung`, drei Fassungen von „Einspielen
  über 2+4" und zwei Blätter zur Beinarbeit des Zuspielers. 22 PDFs tragen die
  Textmarke „Ausführung:" nicht, bei ihnen zählt der ganze Text.
- **Die richtigen Blätter:** Im ersten Durchgang über 30 Kandidaten traf die
  Regel zwei, und bei beiden stand der Ablauf nur in der Grafik. Bei einem hat
  der Trainer die Lesart des Entwurfs deutlich korrigiert. Übersehen kann die
  Regel ein Blatt mit knapper Ausführung, wenn danach Ziel, Varianten und
  Hinweise stehen, denn sie zählt alles nach der Textmarke. 29 Blätter haben
  zwischen „Ausführung" und der nächsten Rubrik weniger als 150 Zeichen, meist
  knappe Stationsblätter. Ob ihr Ablauf aus der Grafik kommt, zeigt sich erst
  bei ihren Entwürfen, siehe `docs/offene-punkte.md`.
- **Die Schwelle trägt:** Mit `ohne:` hat die Planeingabe über PlayDrill
  221 242 Zeichen und bekommt je PDF den ganzen Text. Die Übersichtsblätter
  behalten ihre Stationslisten, der Baggerzirkel alle acht, der
  Sprungkraftzirkel ebenso.
- **Quellgrafik:** Angesehen sind die von sechs Kandidaten aus dem Durchgang und
  das Übersichtsblatt des Sprungkraftzirkels, dazu ausgeschnitten alle neun
  Blätter des Zirkels. Alle sind sauber ausgeschnitten, ohne durchsichtigen
  Rand. Das Übersichtsblatt zeigt eine neunte Station, die sein Text nicht
  nennt.
- **Neben `git.exe`:** Aus PowerShell ohne `mingw64\bin` im PATH findet
  `vorbereiten --plan` das `pdftotext` unter `Git\mingw64\bin`, wie oben unter
  Consequences beschrieben.
