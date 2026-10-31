---
name: volleyball-uebungsimport
description: Legt aus PDFs, Screenshots, Fotos, Links oder Stichpunkten neue Übungskarten und Wissenskarten in der Volleyball-Bibliothek an, mit Duplikatprüfung, Quellenangabe und Ausschnitten aus den Bildern der Quelle. Use when the user wants to import, add, or digitise volleyball drills or the theory behind them, feed a PDF or screenshot into the Übungsbibliothek, or asks what is already in the library. Companion zu volleyball-trainingsdesign und volleyball-saisonplaner.
---

# Übungsimport

Aus Fremdmaterial werden Karten, die `suche.py` findet: Übungskarten in
`uebungen/`, Wissenskarten in `wissen/`. Der Nutzer bestätigt, bevor
geschrieben wird.

## Zuerst

`<python>` heißt `python3`, unter Windows `python`. Schlägt der eine fehl,
nimm den anderen.

1. Wurzel finden: `<python> ${CLAUDE_PLUGIN_ROOT}/scripts/index.py`. Das gibt
   den Ordner, die Anzahl der Karten und alles, was in der Bibliothek gerade
   nicht stimmt. Findet es keine `trainingsplanung-root.yml`, fragen wo der
   Ordner liegt, statt einen Pfad zu raten.
2. `${CLAUDE_PLUGIN_ROOT}/referenzen/DATENMODELL.md` lesen. Dort stehen beide
   Kartenschemata, „Die Übungskarte“ und „Die Wissenskarte“, und was in
   welches Feld darf.
3. `${CLAUDE_PLUGIN_ROOT}/referenzen/SPRACHE.md` und die `glossary.md` der
   Wurzel lesen. Karten folgen demselben Ton wie alles andere im Ordner.

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

Ist das Material ein Ordner mit mehr als etwa zehn Dateien, den Sammelimport
anbieten. `volleyball-sammelimport` legt für den ganzen Ordner einen
Zerlegungsplan an, lässt die Kartenentwürfe von Agenten schreiben und legt sie
gesammelt zur Freigabe vor, statt Übung für Übung zu fragen. Der Trainer
entscheidet. Bleibt er hier, geht es hier weiter.

### Fotos, die sich nicht öffnen lassen

Abfotografierte Seiten kommen oft mit 50 Megapixeln und 7 MB je Datei aus dem
Handy. So groß lassen sie sich nicht lesen, und mit EXIF-Orientierung liegen
sie zusätzlich quer. Ein Foto vom iPhone ist ein HEIC, ein Scan oft ein TIFF,
und beides zeigt das Lesewerkzeug auch klein nicht. Dann vor dem Zerlegen
aufbereiten:

`<python> ${CLAUDE_PLUGIN_ROOT}/scripts/bilder_aufbereiten.py quellen/<ordner>`

Das verkleinert alles über 2 MB auf 2000 Pixel lange Kante und dreht nach EXIF
gerade. Kleinere Dateien bleiben unangetastet, die Dateinamen bleiben, und die
Originale werden ersetzt. TIFF und HEIC werden immer zu JPEG, unter demselben
Namen mit `.jpg`. Deshalb fragt das Skript einmal für den ganzen Stapel. Den
Menschen fragen, bevor `--ja` mitgegeben wird.

Fehlt Pillow, sagt das Skript, wie es zu installieren ist, und schreibt nichts.
Fehlt nur `pillow-heif`, bleiben die HEIC-Dateien liegen, und der Rest wird
aufbereitet. In beiden Fällen den Installationshinweis weitergeben, das nicht
umgehen und die Bilder auch nicht anders anfassen.

## Zerlegen

Jedes Stück Material ist eins von diesen. Es sind dieselben Prüffragen wie im
Glossar und im Sammelimport, damit beide Wege dieselben Karten ergeben:

- **Übung**, einzeln einsetzbar → eigene Karte, `typ: uebung`
- **Übungsfolge**, nur als Ganzes sinnvoll, Reihenfolge und Dosierung gehören
  dazu → eine Karte, `typ: folge`
- **Wissen**: keine Übung, aber es lässt sich sagen, was es fürs Training
  heißt, ohne etwas zu erfinden → eine Wissenskarte in `wissen/`
- **Trainingsabend** → bleibt in `quellen/`, einzelne Übungen werden daraus
  gezogen
- **Bericht, Porträt, Interview ohne Trainingsbezug, Werbung** → bleibt
  liegen, keine Karte

Ein DVV-Athletikplan ist eine Folge. In zwölf Karten zerlegt wäre seine
Dosierung weg. Eine Magazinseite mit einer Übung und der Theorie daneben
ergibt beides, eine Übungskarte und eine Wissenskarte.

### Der Zuschnitt einer Wissenskarte

Eine Wissenskarte beantwortet genau eine Frage, die sich ein Trainer stellt.
Die Frage ist ihr Titel, eine kurze Frage, und endet auf ein Fragezeichen:
„Wann lohnt sich einarmige Abwehr?“.

- Drei kurze Tipps zu Schlaf, Trinken und Aufwärmen sind drei Karten.
- Ein Heft über alle Techniken wird eine Karte je Technik, ein langes Dokument
  eine je Kapitel.
- Beantwortet die Quelle eine Frage, zu der es schon eine Karte gibt, ergänzt
  sie diese, siehe „Duplikate prüfen“.

Die Karte hat zwei Abschnitte:

- **Kernaussagen:** was die Quelle sagt, knapp und in eigenen Worten, ohne
  Volltext.
- **Was das fürs Training heißt:** was die Quelle dazu sagt. Was du daraus
  ableitest, ist ein Vorschlag mit Begründung. Er kommt in die Liste vor dem
  Schreiben und erst nach dem Ja auf die Karte. Sonst sieht eine erfundene
  Regel aus wie Fachwissen.

Bleibt dieser zweite Abschnitt leer, weil die Quelle nichts dazu sagt und
keine Ableitung ein Ja bekommt, ist es keine Wissenskarte und bleibt liegen
wie ein Bericht.

### Über Seitengrenzen hinweg

Eine Übung hört selten da auf, wo die Seite aufhört. Läuft der Ablauf oben auf
der Folgeseite weiter, gehört er zu derselben Übung und ergibt eine Karte.
Also erst bis zum Ende des Ablaufs lesen, dann zerlegen. Sonst steht der Aufbau
auf der einen Karte und die Dosierung auf der anderen. Für einen Beitrag, aus
dem eine Wissenskarte wird, gilt dasselbe.

`quelldatei:` nennt die Dateien relativ zu `quellen/`, bei abfotografierten
Seiten beide: `seite-04.jpg, seite-05.jpg`. Bei einem PDF bleibt es die
Datei, `dvv-athletik.pdf`, und die Seiten kommen in `quelle:`, etwa
`"DVV-Athletikplan, S. 12–13"`. So halten es beide Kartensorten und der
Sammelimport.

## Disziplin vorschlagen

Jede Karte trägt `disziplin`, eine Liste aus `halle` und `beach`, die
Wissenskarte genauso wie die Übungskarte. Der Vorschlag kommt aus der Quelle:

| Was in der Quelle steht | Vorschlag |
|---|---|
| Zu zweit über das ganze Feld, Handzeichen vor dem Aufschlag, Seitenwechsel wegen Wind und Sonne | `[beach]` |
| Libero, Riegel, 5-1, 6-2, Sechserbesetzung, Hallenteile | `[halle]` |
| Ein Ablauf oder Wissen, dem der Untergrund egal ist: Technik, Athletik, Koordination, Schlaf, Ernährung | `[halle, beach]` |

Sagt die Quelle dazu nichts, kommt in die Spalte ein `?` mit der Frage, was
gemeint ist. Der Nutzer beantwortet sie in derselben Liste. Eine Karte, die
als Halle durchgeht, weil niemand widersprochen hat, findet beim
Beachtraining nie wieder jemand.

Sand im Titel ist noch kein `beach`. Zonenbaggern im Sand läuft in der Halle
genauso und trägt beide Werte. Erst wenn die Quelle die Aufstellung, die
Spielerzahl oder das Ziel an den Sand bindet, ist es `beach` allein.

## Duplikate prüfen

Für jeden Kandidaten, bevor die Liste steht. Übungen und Wissenskarten haben
je ihre eigene Suche.

### Übungen

`<python> ${CLAUDE_PLUGIN_ROOT}/scripts/suche.py --element <element> --json`

Ohne `--disziplin`, damit die Suche über die Disziplingrenze hinwegschaut. Das
Duplikat einer Beachübung liegt in der Bibliothek unter `halle`, mit Filter
bekommst du es nie zu sehen. Dann Titel, Ziel und Ablauf vergleichen.

Sieht etwas nach derselben Übung aus, entscheidet diese Tabelle:

| Was sich unterscheidet | Was passiert |
|---|---|
| Nur der Untergrund | Die Disziplin kommt auf der **bestehenden** Karte dazu, die Sandbesonderheiten unter `## Variationen`. Keine zweite Karte. |
| Aufstellung, Spielerzahl oder Ziel | Eigene Karte mit `variante_von: ue-######` und eigener Disziplin |
| Es ist eine andere Übung | Neue Karte |

Zonenbaggern zu zweit im Sand ist dieselbe Übung: `beach` kommt zu `[halle]`
dazu, der weiche Stand in die Variationen. Zwei-gegen-Zwei über das ganze Feld
statt Sechs-gegen-Sechs ist eine andere Übung und bekommt eine eigene Karte
mit `variante_von`.

Eine bestehende Karte wird ergänzt, nie überschrieben. `id`, Ziel und Ablauf
bleiben stehen, damit jeder Trainingsplan, der auf sie zeigt, weiter dieselbe
Übung meint.

### Wissenskarten

`<python> ${CLAUDE_PLUGIN_ROOT}/scripts/suche.py --wissen --json`

Das sind alle Wissenskarten, je mit Frage, Thema, Schwerpunkt, Disziplin,
`quelle`, `quelldatei`, `uebungen` und Datei. Filtern lässt sich die Liste
noch nicht, ein Filter für Übungen wie `--element` beendet den Aufruf mit
einer Meldung. Gibt es keine Wissenskarte, ist die Liste leer.

Verglichen wird die Frage, nicht der Wortlaut des Titels:

| Was der Kandidat beantwortet | Was passiert |
|---|---|
| Dieselbe Frage wie eine bestehende Karte, etwa in der Fortsetzung eines Beitrags im nächsten Heft | Die bestehende Karte wird ergänzt. Keine zweite Karte. |
| Eine andere Frage, auch aus derselben Fortsetzung | Eigene Karte |

Nennt eine Karte schon dieselbe `quelldatei`, mit denselben Seiten in
`quelle`, ist der Beitrag schon importiert. Kommt dann nichts Neues dazu,
steht der Kandidat in der Liste als „Duplikat von wi-######“ und wird keine
Karte.

Beim Ergänzen bleiben ID und `angelegt`. Dazu kommt, ohne Doppeltes:

- neue Kernaussagen und neue Punkte fürs Training. Was die Karte schon sagt,
  auch mit anderen Worten, kommt nicht noch einmal. Eine Ableitung braucht
  das Ja wie auf einer neuen Karte;
- in `quelle` die neue Quelle, nach einem Semikolon, in `quelldatei` die neue
  Datei, nach einem Komma;
- in `thema`, `schwerpunkt` und `uebungen`, was neu ist;
- die Bilder der neuen Quelle, siehe „Ausschnitte“.

Was hier herauskommt, steht in der Vorlege-Liste und wird dort bestätigt.
Beim Ergänzen einer Wissenskarte gehört dazu, was auf die Karte kommt, so wie
es dort stehen wird.

## Vorlegen, bevor geschrieben wird

Eine Zeile je Kandidat, Übungen und Wissenskarten in je einer Tabelle:

| Titel | Inhalt in einem Satz | Typ | Disziplin | Duplikat |
|---|---|---|---|---|
| Zonenbaggern im Sand | Bagger in Zonen, zu zweit, ohne Netz | uebung | `[halle, beach]` | ergänzt ue-000002 |
| Sideout-Serie zu zweit | Aufschlag, Annahme, Angriff im Sand, auf Punkte | uebung | `[beach]` | — |
| Aufschlagserie mit Zielfeldern | Zehn Aufschläge auf wechselnde Zonen | uebung | `?` sagt die Quelle nicht | — |

| Frage | Thema | Schwerpunkt | Disziplin | Übungen | Duplikat |
|---|---|---|---|---|---|
| Wann lohnt sich einarmige Abwehr? | technik, taktik | abwehr | `[halle, beach]` | Sideout-Serie zu zweit | — |
| Was hat Schlaf mit der Reaktion zu tun? | physiologie | — | `[halle, beach]` | — | — |
| Wohin schlägt man taktisch auf? | taktik | aufschlag | `?` sagt die Quelle nicht | ue-000041 | ergänzt wi-000004 |

- **Thema:** aus der Liste in `DATENMODELL.md`, mindestens eins.
- **Schwerpunkt:** darf leer bleiben. Eine Wissenskarte darf auch
  Steuerungsschwerpunkte wie `belastungssteuerung` tragen, eine Übungskarte
  nicht.
- **Übungen:** die Übungen, die zur Karte gehören, etwa aus demselben
  Beitrag. Eine bestehende mit ID, eine aus der Tabelle darüber mit ihrem
  Titel. Sie bekommt ihre ID beim Schreiben.

Unter der Tabelle steht je Wissenskarte jede Ableitung für „Was das fürs
Training heißt“, mit Begründung in einem Satz, etwa:
`Wann lohnt sich einarmige Abwehr?`, Punkt 2: „Im Abwehrtraining Bälle
außerhalb der Reichweite beider Arme gezielt anspielen.“ Die Quelle zeigt,
dass einarmig dort noch ein Ball kommt, wo beidarmig keiner mehr kommt.
Bei „ergänzt wi-######“ steht da auch, was auf die bestehende Karte dazukommt.

Der Nutzer streicht, was keine eigene Karte ist, korrigiert die Disziplin
direkt in der Spalte und bestätigt oder kippt jede Ableitung. Für eine
Quelle, der er traut, kann er pauschal alles freigeben.

Passt zu einem Kandidaten keine Kennung aus der `schwerpunkte.md` der Wurzel,
steht der Vorschlag für eine neue in derselben Liste, mit `halle`, `beach`
oder `beide` für die dritte Spalte jener Datei. Sag dazu, was die Kennung
abdeckt und warum keine vorhandene reicht. Nach einem ausdrücklichen Ja trägst
du sie dort ein, danach nimmt die Karte sie. Ohne dieses Ja bleibt es beim
Vorschlag. Für eine Wissenskarte schlägst du eine neue Kennung nur für etwas
vor, das man trainieren kann. Ein Beitrag über Schlaf bekommt keine, die Liste
in `schwerpunkte.md` bleibt die dessen, was man trainieren kann.

Fertig ist dieser Schritt, wenn zu jedem Kandidaten eine Entscheidung des
Nutzers vorliegt, jede Zeile eine Disziplin trägt, jede Wissenskarte ein
Thema und jede Ableitung ein Ja oder ein Nein hat. Ein `?` heißt, es fehlt
noch eine Antwort.

## Ausschnitte

Hat die Quelle ein Bild, kommt es als Ausschnitt auf die Karte. Bei einer
Übung ist das ihre Skizze, ihr Feldbild oder eine Bildreihe, bei einer
Wissenskarte das Bild zu einer Kernaussage, etwa die Bildreihe zu einer
Technik oder eine Kurve. Eine Bildreihe ist ein Ausschnitt, nicht fünf.
Kopfleiste, Logo, Werbung und Porträt sind kein Bild der Karte. Eine Grafik,
die im PDF gezeichnet ist, zählt wie ein eingebettetes Bild, denn
ausgeschnitten wird aus der gezeichneten Seite.

Ein Ausschnitt ist die Datei, bei einem PDF die Seite, und ein Rechteck in
ganzen Prozent der Seite, wie sie aufrecht steht: links, oben, rechts, unten.
Das Rechteck fasst das ganze Bild samt seiner Beschriftung, mit etwas Rand.
Lieber zwei Prozent zu viel als eine Ecke abgeschnitten. Text der Seite, eine
Fußzeile oder ein Logo über, unter oder neben dem Bild gehört nicht dazu.
Liegt so etwas näher als zwei Prozent am Bild, endet der Rand davor, auch wenn
dann weniger Rand bleibt. Miss diese Kante am Bild der Seite nach.

Für jeden Ausschnitt der freigegebenen Kandidaten eine Runde:

1. **Schneiden**, ins Temp-Verzeichnis der Sitzung, außerhalb des
   Arbeitsordners. Ein Ausschnitt behält dort eine Datei über alle Runden.

   ```
   <python> ${CLAUDE_PLUGIN_ROOT}/scripts/ausschnitt.py <wurzel>/quellen/<foto> --rechteck <links> <oben> <rechts> <unten> <temp>/<name>.jpg
   <python> ${CLAUDE_PLUGIN_ROOT}/scripts/ausschnitt.py <wurzel>/quellen/<pdf> --seite <n> --rechteck <links> <oben> <rechts> <unten> <temp>/<name>.png
   ```

   Aus einem Foto wird ein JPEG, aus einer PDF-Seite ein PNG, das Ziel trägt
   die passende Endung. Die Seite zählt im PDF ab 1, nicht nach der Zahl, die
   auf der Seite gedruckt ist. Am Ende nennt das Skript das Maß in Pixeln.
2. **Zeigen**, mit dem, was die Umgebung hergibt, sonst den Pfad nennen. Dazu
   die Karte und bei einer Wissenskarte die Kernaussage, an die das Bild
   kommt.
3. **Korrigieren.** Der Nutzer behält den Ausschnitt, korrigiert ihn mit einem
   Satz, etwa „etwas weiter nach unten“ oder „rechts fehlt die Beschriftung“,
   oder streicht ihn. Aus dem Satz werden neue Zahlen, wie im Sammelimport:
   „Etwas“ sind etwa fünf Prozentpunkte, „weiter nach unten“ verschiebt oben
   und unten zugleich, „unten mehr“ nur unten. Liegt das Bild auf einer
   anderen Seite, ändert sich auch die Seite. Dann zurück zum Schneiden.

Fertig ist ein Ausschnitt, wenn der Nutzer ihn behält oder streicht. Ein
gestrichener kommt nicht auf die Karte.

Endet `ausschnitt.py` mit einem Fehler, ist nichts geschrieben, und die
Meldung sagt, was nicht stimmt, etwa eine Seite, die es nicht gibt. Fehlt
Pillow, oder bei einem PDF `pypdfium2`, nennt sie den Befehl zum Installieren.
Den weitergeben und fragen, ob der Nutzer installiert oder die Karte ohne das
Bild kommt. Das Bild nicht auf anderem Weg ausschneiden.

## Karten schreiben

Erst die Übungen, dann die Wissenskarten. So kennt eine Wissenskarte die IDs
der Übungen, die zu ihr gehören.

Jeder behaltene Ausschnitt kommt aus dem Temp-Verzeichnis nach
`schaubilder/`, unter dem Namen der Karte ohne `.md`:
`ue-000291-abwehr-vom-kasten.png`. Hat eine Karte mehrere,
bekommen sie eine Nummer in der Reihenfolge der Quelle,
`wi-000003-oberes-zuspiel-1.png`, `wi-000003-oberes-zuspiel-2.jpg`. Die Endung
bleibt die des Ausschnitts. Ein Name, unter dem in `schaubilder/` schon eine
Datei liegt, ist nicht frei: dann die nächste freie Nummer.

### Übungskarten

Pro freigegebener Übung eine Datei `uebungen/ue-######-slug.md` nach dem Schema
in `DATENMODELL.md`. Die ID holst du unmittelbar vor jeder Karte mit
`<python> ${CLAUDE_PLUGIN_ROOT}/scripts/suche.py --naechste-id`. Das Skript gibt
nur die ID aus. Rechne sie nicht selbst aus der Trefferliste: Jeder Trainer
vergibt in seinem eigenen Bereich, und welcher das ist, weiß nur das Skript.

`schaubild:` nennt die Ausschnitte der Übung, einen als Namen, mehrere als
Liste: `schaubild: [<erster>.png, <zweiter>.png]`. Ohne Ausschnitt steht dort
`null`.

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

### Wissenskarten

Pro freigegebener Wissenskarte eine Datei `wissen/wi-######-slug.md` nach
„Die Wissenskarte“ in `DATENMODELL.md`, der Slug aus der Frage ohne
Fragezeichen. Einem Arbeitsordner, der älter ist als die Wissenskarte, fehlt
`wissen/`. Dann legst du den Ordner an. Die ID holst du unmittelbar vor jeder
Karte mit

`<python> ${CLAUDE_PLUGIN_ROOT}/scripts/suche.py --naechste-id --wissen`

Sie zählt für sich, getrennt von den Übungen: `wi-000001` ist die erste
Wissenskarte, gleich wie viele Übungen es gibt.

- `titel` und die Überschrift `#` sind die Frage aus der Liste.
- `thema`, `schwerpunkt` und `disziplin` kommen aus der Liste, in eckigen
  Klammern. Ohne Schwerpunkt steht dort `[]`.
- `uebungen` nennt die IDs aus der Spalte Übungen. Eine neue Übung hat ihre
  jetzt, denn ihre Karte steht schon. Ohne Übungen steht dort `[]`.
- `quelle` ist die Kurzquelle, bei einem PDF mit den Seiten, `quelldatei` die
  Datei relativ zu `quellen/`.
- Darunter `## Kernaussagen` und `## Was das fürs Training heißt`, von den
  Ableitungen nur die mit Ja.
- Jeder Ausschnitt steht als Bildverweis unter der Kernaussage, die er zeigt,
  mit dem Weg von `wissen/` aus:
  `![Bildreihe oberes Zuspiel](../schaubilder/wi-000003-oberes-zuspiel-1.png)`.

Ein Kandidat, der laut Liste eine Wissenskarte ergänzt, bekommt keine neue
Datei. Was dazukommt, steht in der Liste und kommt so in die bestehende Karte,
nach „Duplikate prüfen“. Seine Ausschnitte bekommen den Namen dieser Karte mit
der nächsten Nummer nach den Bildern, die dort schon liegen, wie im
Sammelimport. Ein Bild ohne Nummer zählt als das erste: Nach
`wi-000003-oberes-zuspiel.png` kommt `wi-000003-oberes-zuspiel-2.jpg`. Eine
Karte ohne Bild bekommt ihre ab 1.

### Wenn es keine ID gibt

Endet der Aufruf mit einem Fehler, wird nichts geschrieben. Die Meldung sagt,
warum. Das gilt für `--naechste-id` mit und ohne `--wissen`:

- **Der Rechner gehört zu keinem Trainer.** Die Meldung nennt den Rechner, die
  eingetragenen Trainer und die Nummer, die ein neuer bekäme. Frag, wer da
  sitzt. Ist es ein Trainer aus der Liste, kommt der Rechner in dessen
  `rechner:`-Liste. Ist es ein neuer, bekommt er einen eigenen Eintrag mit
  dieser Nummer, der erste überhaupt `00`. Sein Name ist derselbe wie unter
  `gruppen.<gruppe>.trainer`. Zeig den Eintrag, wie er unter `trainer:` in
  `trainingsplanung-root.yml` stehen wird, und trag ihn erst nach dem Ja ein.
  Die Form steht in `DATENMODELL.md` unter „Wer welcher Trainer ist“. Danach
  `--naechste-id` noch einmal.
- **`uebungen/` hat noch vierstellige IDs.** Das hält nur die nächste Übung
  auf, Wissenskarten waren nie vierstellig. Der Arbeitsordner ist nicht
  umgestellt. Das macht
  `<python> ${CLAUDE_PLUGIN_ROOT}/scripts/ids_umstellen.py --trainer <name>`.
  Die bisherigen Karten bekommen `00` vorn, und `<name>` vergibt als Trainer
  `00` danach weiter, in aller Regel der, der bisher importiert hat. Steht
  unter `trainer:` noch niemand, trägt das Skript ihn mit diesem Rechner ein.
  Ohne `--schreiben` zeigt es nur, was sich ändert. Es benennt Karten im
  ganzen Ordner um, also für alle Trainer. Zeig, was es ändern würde, und
  schreib erst nach dem Ja. Bis dahin wird nichts importiert. Danach
  `--naechste-id` noch einmal.

## Prüfen

`<python> ${CLAUDE_PLUGIN_ROOT}/scripts/index.py` laufen lassen. Der Import ist
fertig, wenn es null Auffälligkeiten meldet, jede neue Übung
`suche.py --id ue-######` findet und jede neue Wissenskarte in
`suche.py --wissen` steht. Ein toter Bildverweis oder eine ID in `uebungen`,
die es nicht gibt, steht dann in der Meldung.

Eine ergänzte Karte gehört mit geprüft:
`suche.py --id ue-###### --disziplin <die dazugekommene Disziplin>` muss sie
jetzt zeigen. Eine ergänzte Wissenskarte nennt in `suche.py --wissen --json`
die neue `quelldatei`.

Danach anbieten, `index.py --md` laufen zu lassen, damit die Lesebrille
`index.md` die neuen Karten kennt.

## Schaubilder vorschlagen

Wenn die Karten stehen und geprüft sind, einmal über die neuen Übungen
schauen. Wissenskarten bekommen keinen Vorschlag: `volleyball-schaubild`
zeichnet nur Übungen, und die Bilder einer Wissenskarte kommen aus der Quelle.

Ein Schaubild wird für eine Übung ohne Bild vorgeschlagen, wo es einen Anlass
gibt: die Quelle hat ein Bild, das nicht als Ausschnitt auf die Karte kam,
oder der Ablauf auf der Karte ist räumlich, also eine Aufstellung, Laufwege,
eine Zielzone oder ein Stationsaufbau. Alles andere bleibt aus der Liste. Zu
drei Sätzen Kräftigung hilft ein Bild niemandem. Eine Übung mit Ausschnitt hat
ihr Bild schon. Eine Szene lässt sich für sie später trotzdem zeichnen.

Der Vorschlag kommt gesammelt am Ende, mit ID und Titel je Kandidat. Zwischen
zwei Karten wird nichts gezeichnet, sonst zerfällt das Zerlegen einer Quelle
in fünfzehn Bildschleifen.

Welcher Weg empfohlen wird, entscheidet die Zahl der Kandidaten:

| Kandidaten | Empfehlung |
|---|---|
| ein oder zwei | gleich mitzeichnen, solange das Material frisch im Blick ist: `volleyball-schaubild` aufrufen |
| drei oder mehr | den Import hier abschließen und das Zeichnen einer frischen Sitzung mit `volleyball-schaubild` überlassen |

Ein Bild kostet eine Runde aus Rendern, Ansehen und Nachschärfen. Ein
Kontextfenster trägt das Importwissen und ein Dutzend solcher Runden nicht
zusammen. Die frische Sitzung findet die Karten über dieselbe Suche wieder,
weil auf ihnen noch kein `schaubild:` steht.

Das bleibt eine Empfehlung. Der Nutzer entscheidet.

## Was der Nutzer am Ende hört

Wie viele Karten dazugekommen sind, Übungen und Wissenskarten, welche IDs, und
welche Disziplin jede von ihnen trägt, bei einer Wissenskarte dazu ihre Frage.
Dazu die bestehenden Karten, die eine Disziplin dazubekommen haben, die
ergänzten Wissenskarten, und was du beim Zerlegen entschieden hast, wo es
nicht eindeutig war, auch was liegen geblieben ist und warum. Neue
Schwerpunkt-Kennungen, die du nach Freigabe eingetragen hast, stehen mit
dabei, und ebenso die, für die es kein Ja gab. Genauso die Ableitungen ohne Ja
und die Bilder, die ohne Ausschnitt geblieben sind, mit dem Grund. Hast du
unter `trainer:` einen Rechner oder einen Trainer eingetragen, gehört das auch
dazu. Fragen, die du unterwegs gestellt und selbst beantwortet hast, gehören
ebenfalls hinein, damit er sie kippen kann.

Zum Schluss die Kandidaten für ein Schaubild, die offen geblieben sind, mit
ihren IDs. Aus dieser Zeile kopiert er sie in die nächste Sitzung.
