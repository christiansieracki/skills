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

## Nachtrag nach der Abnahme, 25.10.2026

Gemessen bei der Abnahme des Ausschnitts (#65) im echten Arbeitsordner, mit
einem Sammelimport über `jugendtrainerlehrgang/04_So_Vo`: „Kleine Spiele“ mit
26 Seiten und die „Spielreihe“ mit 9 Seiten, 15 Kandidaten mit Seitenbereich.

- **Seiten als Bild für den Agenten (3.2.1):** Was oben für das Skript steht,
  gilt auch für den Agenten. Sein Werkzeug zeichnet eine PDF-Seite mit
  `pdftoppm`, und das fehlt unter Windows. Die ersten vier Agenten meldeten
  deshalb „kein Entwurf“. Poppler mit dem Plugin einzurichten geht nicht, ein
  Plugin kann keine Programme installieren. Seit 3.2.1 legt `vorbereiten` bei
  `quellgrafik: ausschnitt` jede Seite eines PDF des Kandidaten als Bild neben
  den Auftrag, mit `pypdfium2` über dieselbe Funktion wie `ausschnitt.py`, 2000
  Pixel an der langen Kante. Der Agent misst seine Prozente an genau dem Bild,
  aus dem `pruefen` schneidet.
- **Getroffen:** Die 15 Entwürfe nennen 26 Ausschnitte, neun davon für die
  Folge Stationentraining. Alle 26 zeigen die richtige Zeichnung auf der
  richtigen Seite. 20 hat der Trainer behalten, wie sie waren, 6 mit je einem
  Satz korrigiert, gestrichen keinen. Bei allen sechs lag Text 1 bis 2
  Prozentpunkte neben der Zeichnung im Rahmen. Fünfmal ist ein Rand um einen
  Punkt gewandert, einmal sind es zwei Ränder. „Etwas“, im Skill etwa fünf
  Punkte, hätte dort die Zeichnung angeschnitten. Die Zahlen sind am Seitenbild
  nachgemessen.
- **Seitenzahlen:** Die gedruckten Seitenzahlen in „Kleine Spiele“ weichen ab,
  auf der siebten Seite steht etwa 20, auf der achten 30. Jeder Ausschnitt
  nennt die Seite der Datei, wie der Auftrag es verlangt.
- **Zeit:** `vorbereiten` brauchte für 15 Aufträge mit 33 Seitenbildern 8,5 s,
  17 der Bilder gehören zu einem Kandidaten. `pruefen` schnitt die 26
  Ausschnitte in 13,5 s, obwohl jeder Schnitt das PDF neu liest. Das PDF
  zwischenzuspeichern lohnt sich bei dieser Größe nicht.
- **Der alte Schlüssel:** `vorbereiten` über `playdrill` mit
  `quellgrafik_ausschneiden: true` lief in einer Kopie des Arbeitsordners ohne
  Fehler. Es schrieb 30 Aufträge in 13,5 s, mit eingebetteten Quellgrafiken wie
  bisher und ohne Seitenbilder.
