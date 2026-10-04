# pypdfium2 als optionale Bibliothek für Ausschnitte aus PDF-Seiten

Der Sammelimport schneidet die Quellgrafik als Ausschnitt aus einer Seite. Bei
einem Foto schneidet Pillow aus. Bei einem PDF zeichnet `pypdfium2` zuerst die
Seite als Bild, danach schneidet Pillow aus. Nach Pillow (ADR-0005) und
`pdftotext` (ADR-0008) ist das die dritte Ausnahme von der Festlegung auf die
Standardbibliothek.

Seit 1d nimmt der Sammelimport aus einem PDF das größte eingebettete Bild. Das
passt zu PlayDrill: eine Übung je Datei, ein Bild je Übung. Beim Interview zur
Welle zur Wissenskarte am 04.10.2026 wurden die PDFs aus dem
Jugendtrainerlehrgang durchgezählt:

| PDF | Seiten | eingebettete Bilder |
|---|---|---|
| Oberes Zuspiel – Merkmale | 5 | 27 |
| SwissVolley Technik-Guidelines | 48 | 455 |
| Organisationsformen | 14 | 27 |
| Taktische Aufschläge | 1 | 1, ein Logo |

Eine Bildreihe zu einer Technik liegt dort als fünf Einzelbilder vor, auf jeder
Seite steht dieselbe Kopfleiste, und eine Grafik, die im PDF gezeichnet ist,
ist gar kein eingebettetes Bild. Das größte Bild trifft so fast nie das, was
auf die Karte gehört. Das gilt für Wissenskarten wie für Übungen aus solchen
PDFs.

Ein Werkzeug, das PDF-Seiten zeichnet, ist unter Windows nicht da. Git für
Windows bringt `pdftotext` mit, aber nicht `pdftoppm`. `pypdfium2` kommt mit
`pip install pypdfium2` und gibt eine Seite gleich als Pillow-Bild zurück.

## Considered Options

- **Einzelbilder.** Das Skript legt alle eingebetteten Bilder je Seite ab, ohne
  die, die auf vielen Seiten wiederkehren, und der Agent wählt per Nummer.
  Verworfen: Eine Bildreihe zerfällt in Einzelbilder, und gezeichnete Grafiken
  fehlen ganz.
- **Nur PDFs wie PlayDrill.** Verworfen: Gerade im Lehrgangs- und
  Verbandsmaterial tragen die Bilder den Inhalt.
- **PyMuPDF.** Zeichnet ebenso, steht aber unter der AGPL.

## Consequences

Der Agent nennt den Ausschnitt im Kartenentwurf: Datei, bei einem PDF die
Seite, und das Rechteck in Prozent der Seite. Das Skript schneidet ihn aus, und
der Trainer sieht ihn bei der Freigabe. Foto und PDF gehen damit denselben
Weg, für Übungskarten wie für Wissenskarten. Bei PlayDrill bleibt es beim
größten eingebetteten Bild ohne den durchsichtigen Rand.

`pypdfium2` ist freiwillig wie Pillow. Kein anderes Skript bekommt eine neue
Voraussetzung. Soll ein Quellenordner Ausschnitte aus PDF-Seiten bekommen und
die Bibliothek fehlt, bricht der Sammelimport vor dem ersten Auftrag ab, mit
Installationshinweis, und schreibt nichts. So entstehen keine Karten ohne Bild,
die eins haben sollten, wie bei Pillow in #29.

Tests, die `pypdfium2` brauchen, werden übersprungen, wo es fehlt.
`DATENMODELL.md` nennt künftig drei Ausnahmen.
