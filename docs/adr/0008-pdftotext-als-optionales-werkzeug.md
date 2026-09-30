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
- Der Agent bekommt den Text wortgenau und dazu das ausgeschnittene Feldbild,
  das später auch auf der Karte steht.

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
