---
name: volleyball-uebungsimport
description: Legt aus PDFs, Screenshots, Fotos, Links oder Stichpunkten neue Übungskarten in der Volleyball-Übungsbibliothek an, mit Duplikatprüfung und Quellenangabe. Use when the user wants to import, add, or digitise volleyball drills, feed a PDF or screenshot into the Übungsbibliothek, or asks what is already in the library. Companion zu volleyball-trainingsdesign und volleyball-saisonplaner.
---

# Übungsimport

Aus Fremdmaterial werden Karten, die `suche.py` findet. Der Nutzer bestätigt,
bevor geschrieben wird.

## Zuerst

`<python>` heißt `python3`, unter Windows `python`. Schlägt der eine fehl,
nimm den anderen.

1. Wurzel finden: `<python> ${CLAUDE_PLUGIN_ROOT}/scripts/index.py`. Das gibt
   den Ordner, die Anzahl der Karten und alles, was in der Bibliothek gerade
   nicht stimmt. Findet es keine `trainingsplanung-root.yml`, fragen wo der
   Ordner liegt, statt einen Pfad zu raten.
2. `${CLAUDE_PLUGIN_ROOT}/referenzen/DATENMODELL.md` lesen. Dort steht das
   Kartenschema und was in welches Feld darf.
3. `${CLAUDE_PLUGIN_ROOT}/referenzen/SPRACHE.md` und die `glossary.md` der
   Wurzel lesen. Übungskarten folgen demselben Ton wie alles andere im Ordner.

## Material hereinholen

| Eingabe | Vorgehen |
|---|---|
| PDF, Word, Bild im Ordner | direkt lesen |
| Webseite, verlinktes PDF | abrufen und lesen |
| YouTube, Instagram, TikTok | Video lässt sich nicht ansehen. Nach dem Transkript, einem Screenshot oder Stichpunkten fragen |
| Stichpunkte im Chat | direkt verwenden |

Steht in der Quelle zu wenig, um eine Übung zu beschreiben, sag das und frag
nach. Eine erfundene Übungskarte fällt erst in der Halle auf, wenn zwanzig
Leute warten.

Eine Datei, die noch nicht in `quellen/` liegt, gehört dorthin, bevor Karten
daraus entstehen. Die Karten verweisen mit `quelldatei:` darauf zurück.

## Zerlegen

Jedes Stück Material ist eins von dreien. `DATENMODELL.md` hat die Prüffrage:

- **Übung**, einzeln einsetzbar → eigene Karte, `typ: uebung`
- **Übungsfolge**, nur als Ganzes sinnvoll, Reihenfolge und Dosierung gehören
  dazu → eine Karte, `typ: folge`
- **Trainingsabend** → bleibt in `quellen/`, einzelne Übungen werden daraus
  gezogen

Ein DVV-Athletikplan ist eine Folge. In zwölf Karten zerlegt wäre seine
Dosierung weg.

## Vorlegen, bevor geschrieben wird

Dem Nutzer eine Liste zeigen: erkannter Titel, ein Satz Inhalt, vorgeschlagener
Typ. Er streicht, was keine eigene Übung ist. Für eine Quelle, der er traut,
kann er pauschal alles freigeben.

Dazu die Duplikatprüfung, **vor** dem Vorlegen: für jeden Kandidaten
`<python> ${CLAUDE_PLUGIN_ROOT}/scripts/suche.py --element <element> --json`
und die Titel vergleichen. Sieht etwas nach derselben Übung aus, den Kandidaten
zeigen und fragen: zusammenführen, als Variante anlegen, oder neu?

Eine bestehende Karte wird nur ergänzt, nie überschrieben. Beim Zusammenführen
kommt das Neue in den Abschnitt `## Variationen`.

Fertig ist dieser Schritt, wenn zu jedem Kandidaten eine Entscheidung des
Nutzers vorliegt.

## Karten schreiben

Pro freigegebener Übung eine Datei `uebungen/ue-####-slug.md` nach dem Schema
in `DATENMODELL.md`. Die nächste freie Nummer ergibt
`<python> ${CLAUDE_PLUGIN_ROOT}/scripts/suche.py --json`, höchste ID plus eins.

Für jedes Feld gilt: was in der Quelle steht, kommt rein. Was nicht drinsteht,
wird gefragt oder bleibt leer. Besonders diese vier verleiten zum Raten:

- `spieler_min` / `spieler_max`: aus dem Ablauf ableiten, wenn er die Rollen
  nennt. Sonst fragen.
- `level_min` / `level_max`: sagt die Quelle nichts, fragen.
- `erwachsenenbelastung`: nur setzen, wenn die Quelle Sprungvolumen,
  Zusatzlast oder Maximalkraft beschreibt. Dazu `belastungshinweis` in
  Klartext, damit ein Jugendtrainer weiß, was er anpassen muss.
- `schwerpunkt`: nur Kennungen aus der `schwerpunkte.md` der Wurzel. Passt
  keine, dem Nutzer eine neue vorschlagen und erst nach seinem Ja dort
  eintragen.

Inhalte in eigenen Worten wiedergeben, mit Kurzquelle in `quelle:`. Kein
Volltext aus der Vorlage.

## Prüfen

`<python> ${CLAUDE_PLUGIN_ROOT}/scripts/index.py` laufen lassen. Der Import ist
fertig, wenn es null Auffälligkeiten meldet und jede neue Karte
`suche.py --id ue-####` findet.

Danach anbieten, `index.py --md` laufen zu lassen, damit die Lesebrille
`index.md` die neuen Übungen kennt.

## Was der Nutzer am Ende hört

Wie viele Karten dazugekommen sind, welche IDs, und was du beim Zerlegen
entschieden hast, wo es nicht eindeutig war. Fragen, die du unterwegs gestellt
und selbst beantwortet hast, gehören in diese Zusammenfassung, damit er sie
kippen kann.
