# Die Leseansicht wird in Python nachgebaut und läuft auch ohne JavaScript

Die freigegebene Gestaltung der Leseansicht liegt als React-Vorlage vor: der
Ablauf zum Aufklappen, Hell, Dunkel und System, mit Dialogen für Nachschlagen,
Vorbereitung und das Vergrößern der Bilder (Branch
`overhaul/html-generation-display`, Commit `314f205`). `leseansicht.py` baut
diese Gestaltung nach und erzeugt weiter eine einzige HTML-Datei. CSS und Bilder
stecken darin, dazu ein kurzes JavaScript ohne Bibliothek. Die Programmpunkte
klappen über `<details>` auf. JavaScript braucht es nur für die Dialoge, das
Vergrößern und den Umschalter Hell, Dunkel und System.

Ohne JavaScript bleibt alles lesbar. Jeder Programmpunkt lässt sich aufklappen,
Nachschlagen und Vorbereitung stehen unten auf der Seite, und das Farbschema
folgt dem Gerät. Der Trainer schickt sich die Datei vom Rechner per WhatsApp
aufs Handy oder lädt sie aus der Nextcloud und öffnet sie im Browser. Auf keinem
der beiden Wege ist sicher, dass die App, die die Datei zuerst zeigt,
JavaScript ausführt.

## Considered Options

- **Ein fertig gebautes React-Paket im Plugin**, Python legt nur die Daten als
  JSON hinein. Verworfen: Das Repo bräuchte Node und Vite, um das Paket nach
  jeder Änderung neu zu bauen. Bisher kommt das Plugin ganz ohne Build-Schritt
  aus, selbst Pillow ist nur optional (ADR-0005). Ohne JavaScript bliebe die
  Seite außerdem leer.
- **Die React-Vorlage beim Trainer bauen.** Verworfen: Kein Trainer hat Node.
- **Nur HTML und CSS, ganz ohne JavaScript.** Verworfen: Der Umschalter für
  Hell und Dunkel und das Nachschlagen aus einem Programmpunkt heraus gehören zur
  freigegebenen Gestaltung. Ohne Skript gibt es beides nicht.

## Consequences

Die React-Dateien sind eine Vorlage für die Gestaltung, keine Quelle. Was gilt,
steht nach dem Nachbau in `leseansicht.py` und seinen Tests. Wer die Gestaltung
ändern will, ändert sie dort.

Die README der Vorlage sagt, es sei „noch kein allgemeines Datenformat"
abzuleiten. Das ist mit der Welle zur Leseansicht überholt. Wie der
Trainingsplan gegliedert sein muss, damit der Generator seine Abschnitte den
Programmpunkten zuordnen kann, steht in `VORLAGEN.md` und `DATENMODELL.md`.
