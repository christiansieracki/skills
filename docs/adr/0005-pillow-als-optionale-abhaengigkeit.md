# Pillow als optionale Abhängigkeit, nur für die Bildaufbereitung

Das Plugin hat sich in Welle 1a ausdrücklich darauf festgelegt, allein mit der
Standardbibliothek zu laufen. Für die Aufbereitung von Quellfotos — Verkleinern
und EXIF-Drehung — wird davon **eine begrenzte Ausnahme** gemacht: Ist Pillow
importierbar, arbeitet die Aufbereitung; fehlt es, meldet sie das im Klartext
samt Installationshinweis und bricht ab. Kein anderes Skript bekommt eine neue
Voraussetzung, und keines der bestehenden ändert sein Verhalten.

Anlass war ein harter Befund an der Quelle Volleyball-Magazin 09/2026: Von den
15 abfotografierten Seiten sind **14 in 8160×6120 Pixeln** aufgenommen, rund 50
Megapixel und 6 bis 8 MB je Datei. Sie lassen sich nicht öffnen — die Grenze
liegt weit darunter. Ohne Verkleinerung ist diese Quelle also nicht bloß
unbequem, sondern für einen Agenten **vollständig unlesbar**, und das gilt
ebenso für die Wissenskarten-Erweiterung, die von denselben Fotos lebt. Die
Aufbereitung ist damit keine Aufräumarbeit, sondern die Vorbedingung, unter der
die Quelle überhaupt benutzbar wird.

Alle 15 Seiten tragen zudem EXIF-Orientierung 6. Das Auslesen dieses Werts
gelingt mit der Standardbibliothek in wenigen Zeilen; das **Verkleinern** eines
JPEG gelingt damit nicht, weil die Standardbibliothek keinen JPEG-Dekodierer
mitbringt. Genau an dieser Stelle, und nur dort, bricht die Festlegung.

## Considered Options

- **Pillow hart voraussetzen.** Verworfen: der Import-Skill würde auf einer
  frischen Installation scheitern, bevor er irgendetwas Nützliches getan hat.
- **Ganz ohne Bibliothek**, also nur die Orientierung auslesen und melden.
  Verworfen, weil damit das eigentliche Problem — die Pixelzahl — unangetastet
  bliebe und die 14 Seiten unlesbar blieben.
- **Ein externes Werkzeug aufrufen** (ImageMagick o. ä.). Verworfen: auf einer
  Windows-Installation ist nichts davon vorhanden, die Abhängigkeit wäre also
  dieselbe, nur schlechter greifbar.

## Consequences

Die Aufbereitung gilt für JPEG **und** PNG, weil ein großer Screenshot dasselbe
Problem macht wie ein großes Foto und Pillow beide gleich behandelt; gedreht
wird nur, wo EXIF es verlangt. Bewusst nicht mitgenommen wird „alles, was Pillow
öffnet": HEIC und TIFF öffnet Pillow ohne Zusatzpaket gerade nicht, und die
Zusage würde still bei dem Nutzer brechen, der ein iPhone benutzt.

Das Original wird **ersetzt**, nicht ergänzt, nach einer Rückfrage für den
ganzen Stapel. Ein zweites Bild daneben würde `quelldatei:` mehrdeutig machen
und die Ersparnis aufheben, statt sie zu halbieren. Das ist der einzige
unumkehrbare Schritt dieses Astes; Nextcloud hält zusätzlich ältere Versionen
vor.
