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

## Nachtrag bei der Umsetzung des Sammelimports, 01.10.2026

Oben steht, kein anderes Skript bekomme eine neue Voraussetzung. Das gilt so
nicht mehr. Seit #33 braucht auch `sammelimport.py vorbereiten` Pillow, aber
nur, wenn in der `sammelimport.md` `quellgrafik_ausschneiden: true` steht.
Dann schneidet es die Quellgrafik aus dem PDF. Die Spec #29 hat das so entschieden und
sich dabei auf diese Entscheidung berufen.

Das Muster bleibt: Fehlt Pillow, bricht das Skript vor dem ersten Auftrag mit
Installationshinweis ab und schreibt nichts. Ohne die Einstellung läuft es mit
der Standardbibliothek. Eine mit Flate gepackte Quellgrafik, wie PlayDrill sie
einbettet, ließe sich auch ohne Pillow als PNG schreiben. Eine als JPEG
eingebettete nicht, wie oben. Die Spec hat Pillow gewählt, so wie die Vorlage
im PlayDrill-Log.

## Nachtrag zu HEIC und TIFF, 04.10.2026

Oben steht, HEIC und TIFF würden bewusst nicht mitgenommen. Seit #48 werden
sie aufbereitet. iPhones fotografieren in HEIC, und mit mehreren Trainern (#38)
kommen solche Fotos. Das Lesewerkzeug des Agenten zeigt nur PNG und JPEG. Ein
TIFF oder HEIC wird deshalb immer zu JPEG, auch unter 2 MB, unter demselben
Namen mit `.jpg`.

TIFF öffnet Pillow selbst. HEIC öffnet es erst mit dem Zusatzpaket
`pillow-heif`, und das ist optional wie Pillow. Fehlt es, nennt
`bilder_aufbereiten.py` die HEIC-Dateien samt Installationshinweis, lässt sie
liegen und bereitet die übrigen auf. Der Lauf endet dann rot. So bricht die
Zusage nicht still, wie oben befürchtet. Kein anderes Skript braucht
`pillow-heif`.

Mit dem neuen Namen gilt nicht mehr ganz, was oben über `quelldatei:` steht.
Zeigt eine Karte auf die Datei, bleibt sie liegen, und das Skript nennt die
Karte. Sonst bräche der Verweis.
