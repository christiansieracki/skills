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

## Disziplin vorschlagen

Jede Karte trägt `disziplin`, eine Liste aus `halle` und `beach`. Der
Vorschlag kommt aus der Quelle:

| Was in der Quelle steht | Vorschlag |
|---|---|
| Zu zweit über das ganze Feld, Handzeichen vor dem Aufschlag, Seitenwechsel wegen Wind und Sonne | `[beach]` |
| Libero, Riegel, 5-1, 6-2, Sechserbesetzung, Hallenteile | `[halle]` |
| Ein Ablauf, dem der Untergrund egal ist: Technik, Athletik, Koordination | `[halle, beach]` |

Sagt die Quelle dazu nichts, kommt in die Spalte ein `?` mit der Frage, was
gemeint ist. Der Nutzer beantwortet sie in derselben Liste. Eine Karte, die
als Halle durchgeht, weil niemand widersprochen hat, findet beim
Beachtraining nie wieder jemand.

Sand im Titel ist noch kein `beach`. Zonenbaggern im Sand läuft in der Halle
genauso und trägt beide Werte. Erst wenn die Quelle die Aufstellung, die
Spielerzahl oder das Ziel an den Sand bindet, ist es `beach` allein.

## Duplikate prüfen

Für jeden Kandidaten, bevor die Liste steht:

`<python> ${CLAUDE_PLUGIN_ROOT}/scripts/suche.py --element <element> --json`

Ohne `--disziplin`, damit die Suche über die Disziplingrenze hinwegschaut. Das
Duplikat einer Beachübung liegt in der Bibliothek unter `halle`, mit Filter
bekommst du es nie zu sehen. Dann Titel, Ziel und Ablauf vergleichen.

Sieht etwas nach derselben Übung aus, entscheidet diese Tabelle:

| Was sich unterscheidet | Was passiert |
|---|---|
| Nur der Untergrund | Die Disziplin kommt auf der **bestehenden** Karte dazu, die Sandbesonderheiten unter `## Variationen`. Keine zweite Karte. |
| Aufstellung, Spielerzahl oder Ziel | Eigene Karte mit `variante_von: ue-####` und eigener Disziplin |
| Es ist eine andere Übung | Neue Karte |

Zonenbaggern zu zweit im Sand ist dieselbe Übung: `beach` kommt zu `[halle]`
dazu, der weiche Stand in die Variationen. Zwei-gegen-Zwei über das ganze Feld
statt Sechs-gegen-Sechs ist eine andere Übung und bekommt eine eigene Karte
mit `variante_von`.

Eine bestehende Karte wird ergänzt, nie überschrieben. `id`, Ziel und Ablauf
bleiben stehen, damit jeder Trainingsplan, der auf sie zeigt, weiter dieselbe
Übung meint.

Was hier herauskommt, steht in der Vorlege-Liste und wird dort bestätigt.

## Vorlegen, bevor geschrieben wird

Eine Zeile je Kandidat:

| Titel | Inhalt in einem Satz | Typ | Disziplin | Duplikat |
|---|---|---|---|---|
| Zonenbaggern im Sand | Bagger in Zonen, zu zweit, ohne Netz | uebung | `[halle, beach]` | ergänzt ue-0002 |
| Sideout-Serie zu zweit | Aufschlag, Annahme, Angriff im Sand, auf Punkte | uebung | `[beach]` | — |
| Aufschlagserie mit Zielfeldern | Zehn Aufschläge auf wechselnde Zonen | uebung | `?` sagt die Quelle nicht | — |

Der Nutzer streicht, was keine eigene Übung ist, und korrigiert die Disziplin
direkt in der Spalte. Für eine Quelle, der er traut, kann er pauschal alles
freigeben.

Passt zu einem Kandidaten keine Kennung aus der `schwerpunkte.md` der Wurzel,
steht der Vorschlag für eine neue in derselben Liste, mit `halle`, `beach`
oder `beide` für die dritte Spalte jener Datei. Sag dazu, was die Kennung
abdeckt und warum keine vorhandene reicht. Nach einem ausdrücklichen Ja trägst
du sie dort ein, danach nimmt die Karte sie. Ohne dieses Ja bleibt es beim
Vorschlag.

Fertig ist dieser Schritt, wenn zu jedem Kandidaten eine Entscheidung des
Nutzers vorliegt und jede Zeile eine Disziplin trägt. Ein `?` heißt, es fehlt
noch eine Antwort.

## Karten schreiben

Pro freigegebener Übung eine Datei `uebungen/ue-####-slug.md` nach dem Schema
in `DATENMODELL.md`. Die nächste freie Nummer ergibt
`<python> ${CLAUDE_PLUGIN_ROOT}/scripts/suche.py --json`, höchste ID plus eins.

Ein Kandidat, der laut Liste eine bestehende Karte ergänzt, bekommt keine neue
Datei. Dort kommt die Disziplin ins Frontmatter, alles Weitere unter
`## Variationen`, mit der Kurzquelle im selben Absatz. `quelle:` und
`quelldatei:` bleiben stehen, die gehören der ursprünglichen Übung. Die neue
Quelldatei gehört trotzdem nach `quellen/`.

`disziplin` kommt aus der Vorlege-Liste, in eckigen Klammern und mit
mindestens einem Wert. Fehlt sie, meldet `index.py` die Karte.

Für die übrigen Felder gilt: was in der Quelle steht, kommt rein. Was nicht
drinsteht, wird gefragt oder bleibt leer. Besonders diese vier verleiten zum
Raten:

- `spieler_min` / `spieler_max`: aus dem Ablauf ableiten, wenn er die Rollen
  nennt. Sonst fragen.
- `level_min` / `level_max`: sagt die Quelle nichts, fragen.
- `erwachsenenbelastung`: nur setzen, wenn die Quelle Sprungvolumen,
  Zusatzlast oder Maximalkraft beschreibt. Dazu `belastungshinweis` in
  Klartext, damit ein Jugendtrainer weiß, was er anpassen muss.
- `schwerpunkt`: nur Kennungen aus der `schwerpunkte.md` der Wurzel, und jede
  muss zu mindestens einer Disziplin der Karte passen. Sonst meldet der Linter
  sie. Eine neue Kennung steht dort, bevor eine Karte sie trägt.

Inhalte in eigenen Worten wiedergeben, mit Kurzquelle in `quelle:`. Kein
Volltext aus der Vorlage.

## Prüfen

`<python> ${CLAUDE_PLUGIN_ROOT}/scripts/index.py` laufen lassen. Der Import ist
fertig, wenn es null Auffälligkeiten meldet und jede neue Karte
`suche.py --id ue-####` findet.

Eine ergänzte Karte gehört mit geprüft:
`suche.py --id ue-#### --disziplin <die dazugekommene Disziplin>` muss sie
jetzt zeigen.

Danach anbieten, `index.py --md` laufen zu lassen, damit die Lesebrille
`index.md` die neuen Übungen kennt.

## Was der Nutzer am Ende hört

Wie viele Karten dazugekommen sind, welche IDs, und welche Disziplin jede von
ihnen trägt. Dazu die bestehenden Karten, die eine Disziplin dazubekommen
haben, und was du beim Zerlegen entschieden hast, wo es nicht eindeutig war.
Neue Schwerpunkt-Kennungen, die du nach Freigabe eingetragen hast, stehen mit
dabei, und ebenso die, für die es kein Ja gab. Fragen, die du unterwegs gestellt und selbst
beantwortet hast, gehören ebenfalls hinein, damit er sie kippen kann.
