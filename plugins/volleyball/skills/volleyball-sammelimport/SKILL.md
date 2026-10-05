---
name: volleyball-sammelimport
description: Führt den Sammelimport über einen ganzen Quellenordner im Gespräch, von den Absprachen über den Zerlegungsplan und die Kartenentwürfe der Plugin-Agenten bis zur Freigabe und Übernahme in die Übungsbibliothek. Use when the user asks for a Sammelimport über quellen/<ordner>, wants a whole folder of drill sources (PlayDrill PDFs, photographed magazine pages) imported at once, or says „weiter mit dem Sammelimport <ordner>“. Companion zu volleyball-uebungsimport, der einzelne Quellen importiert.
---

# Sammelimport

Ein Quellenordner wird als Ganzes importiert, über mehrere Sitzungen. Der
Trainer gibt zweimal frei: erst den Zerlegungsplan, dann je Durchgang die
Kartenentwürfe. Wo jeder Kandidat steht, liest `sammelimport.py` von der
Platte. Deshalb kann jede Sitzung dort weitermachen, wo die letzte aufgehört
hat.

Was im Arbeitsordner schon steht, ändert der Skill erst nach dem Ja des
Trainers: `glossary.md`, `schwerpunkte.md`, die `sammelimport.md` und
bestehende Karten. Hilfsdateien zum Ansehen kommen ins Temp-Verzeichnis der
Sitzung, nie in den Arbeitsordner.

## Zuerst

`<python>` heißt `python3`, unter Windows `python`. Schlägt der eine fehl,
nimm den anderen. `sammelimport.py` steht für
`<python> ${CLAUDE_PLUGIN_ROOT}/scripts/sammelimport.py`, `<ordner>` für den
Quellenordner relativ zu `quellen/`, etwa `playdrill`.

1. `<python> ${CLAUDE_PLUGIN_ROOT}/scripts/index.py`. Das gibt die Wurzel.
   Findet es keine `trainingsplanung-root.yml`, fragen wo der Ordner liegt.
   Gibt es dort kein `quellen/<ordner>/`, fragen, welcher Ordner gemeint ist.
   Alle Aufrufe laufen aus der Wurzel. Von woanders steht `--wurzel <pfad>`
   vor dem Unterbefehl: `sammelimport.py --wurzel <pfad> pruefen <ordner>`.
2. In `${CLAUDE_PLUGIN_ROOT}/referenzen/DATENMODELL.md` den Abschnitt „Der
   Sammelimport“ lesen: `sammelimport.md`, Ergebnis und Status eines
   Kandidaten, was die Unterbefehle tun.
3. `${CLAUDE_PLUGIN_ROOT}/referenzen/SPRACHE.md` und die `glossary.md` der
   Wurzel lesen.
4. Beim ersten Start in diesem Arbeitsordner, wenn unter `quellen/` noch
   keine `sammelimport.md` liegt: Fehlt der `glossary.md` der Wurzel der
   Abschnitt `## Sammelimport`, anbieten, ihn aus der Saat
   `${CLAUDE_PLUGIN_ROOT}/referenzen/start/glossary.md` einzufügen. Er kommt
   an dieselbe Stelle wie dort, vor `## Team und Trainingsgruppe`. Gibt es
   diese Überschrift nicht, kommt er vor `## Eigene Regeln`. Fehlt unter
   „Weitere Sprachregeln“ die Zeile zu „Feldbild“, kommt sie mit. Eingefügt
   wird nach dem Ja. Ohne Ja geht es trotzdem weiter.

## Der Ablauf

Bei jedem Einstieg, ob „Sammelimport über `quellen/<ordner>`“ oder „weiter mit
dem Sammelimport `<ordner>`“:

1. Liegt in `quellen/<ordner>/` keine `sammelimport.md`, die Absprachen
   anlegen.
2. Der Zerlegungsplan für die Dateien, die neu sind.
3. In den Einstellungen der `sammelimport.md` nachsehen, wer unter
   `in_arbeit` steht. Ist es ein anderer Trainer als der dieses Rechners laut
   `trainer:` in der Wurzeldatei, ihn und das Datum nennen und erst nach dem
   Ja weitermachen. Die Entwürfe, die dort liegen, sind dann seine. Das Ja
   gilt in dieser Sitzung auch für `--trotzdem` im Durchgang.
4. `sammelimport.py pruefen <ordner> --json`. Stehen darin Kandidaten mit
   `bereit` oder `rückfrage`, liegen ihre Entwürfe schon da, etwa nach einem
   Abbruch am Nutzungslimit des Abos. Für sie kommt zuerst die Freigabe, ab
   Schritt 4 des Durchgangs. Neu entworfen werden sie nicht.
5. Durchgänge, bis nichts mehr offen ist oder der Trainer Schluss macht.

Ist der Zerlegungsplan noch nicht freigegeben, bricht `pruefen` mit einer
Meldung ab. Dann ist Schritt 2 noch nicht durch.

## Die Absprachen anlegen

Die Absprachen sind die Regeln, die für jede Karte aus diesem Quellenordner
gelten. Sie gehen unverändert in jeden Auftrag.

Erst selbst hinsehen: den Ordner auflisten und zwei, drei Dateien öffnen, aus
verschiedenen Unterordnern. Liegt im Ordner schon eine Notiz mit Absprachen,
etwa das Log eines Imports von Hand, kommen die Vorschläge von dort. Dann
einzeln fragen, jede Frage mit einem Vorschlag aus dem, was du gesehen hast:

- **Wie sich die Quelle liest:** eine Übung je Datei oder mehrere je Seite,
  was der Dateiname sagt, wie eine Datei aufgebaut ist, was Farben und Linien
  im Bild bedeuten.
- **`quelle`:** das Format der Quellenangabe auf jeder Karte, etwa Sammlung,
  Titel in der Quelle und Ersteller, oder Heft, Seite und Beitrag.
- **`level_min`:** woher es kommt, etwa aus einer Kategorie im Dateinamen
  oder einer Rubrik auf der Seite. Sagt die Quelle nichts, schlägt der Entwurf
  es vor.
- **Was als Schaubild gilt:** Bettet ein PDF eine Feldskizze ein, die auf die
  Karte soll, heißt das `quellgrafik_ausschneiden: true`. Bei Fotos von Seiten
  `false`, die Karten bekommen ihr Bild später mit `volleyball-schaubild`.
- **Textmarke und Platzhalter:** ab welchem Wort eine Datei ihren Ablauf
  beschreibt, und was dort steht, wenn sie keinen hat. Daran erkennt
  `vorbereiten`, dass der Ablauf aus dem Bild kommt. Beide sind optional.
- **`ohne`:** welche Ordner und Dateien der Zerlegungsplan auslässt, etwa
  Vorlagen, Aufstellungen oder eigene Notizen.
- **`autor`:** wer auf den Karten als `autor` steht, meist der Trainer, der
  importiert.
- **Kandidaten je Durchgang:** Vorgabe 30. Weniger, wenn das Abo schnell ans
  Limit kommt.

Dann die ganze Datei vorlegen und nach dem Ja als
`quellen/<ordner>/sammelimport.md` schreiben:

```markdown
---
kandidaten_je_durchgang: 30
plan_freigegeben: null
textmarke: "Ausführung:"
platzhalter: "hier könnte ihr Text stehen"
quellgrafik_ausschneiden: true
ohne: [Vorlagen, notizen.md]
---

# Sammelimport <ordner>

## Absprachen

### So liest sich die Quelle

- …

### Felder

- **quelle:** …
- **level_min:** …
- **schaubild:** …
- **autor:** …

### Was die Quelle nicht sagt

Festgelegt bei der Freigabe am TT.MM.JJJJ.

- Nennt die Quelle nicht, …, steht ….

## Übersicht
```

- Eine Einstellung, die nicht gebraucht wird, fehlt ganz.
- `ohne` steht in eckigen Klammern auf einer Zeile.
- Unter `## Absprachen` stehen Zwischenüberschriften mit `###`. Eine mit `##`
  beendete den Abschnitt, und was danach kommt, fehlte in jedem Auftrag.
- `### Was die Quelle nicht sagt` ist optional und fehlt beim Anlegen meist.
  Er wächst bei der Freigabe, siehe „Die Freigabe“.
- `in_arbeit` trägt nur das Skript ein.

## Gebündelt fragen

Im Zerlegungsplan wie bei der Freigabe kommen Rückfragen zu Dutzenden, und
viele fragen dasselbe. Sie kommen deshalb gebündelt, in einem Zug:

1. **Gruppen:** Gleiche Rückfragen bilden eine Gruppe mit einem Namen. Jede
   Gruppe nennt die Kandidaten, die dazugehören, und hat genau eine
   empfohlene Antwort.
2. **Der Rest:** Was in keine Gruppe passt, steht danach als Liste mit
   Buchstaben, je Frage der Kandidat und ein Vorschlag.
3. **Annehmen:** Eine Frage mit zwei Antworten: Alles gilt so, oder es gibt
   Ausnahmen.
4. **Ausnahmen:** Gibt es welche, kommt eine eigene Frage nach ihnen. Der
   Trainer schreibt sie frei hinein, etwa „c anders: …, 14 gehört nicht zu
   den Kopien“. Freitext zu einer gewählten Option geht verloren.

Fertig, wenn jede Rückfrage eine Antwort hat: aus ihrer Gruppe, als
angenommener Vorschlag oder als Ausnahme.

## Der Zerlegungsplan

1. `sammelimport.py vorbereiten --plan <ordner>`. Es schreibt
   `kartenentwuerfe/<ordner>/planeingabe.md`: jede Datei, die noch in keiner
   Zeile der Übersicht steht und die `ohne` nicht auslässt.
   - **„Keine neuen Dateien“:** Kein Agent, und kein Plan wird vorgelegt.
     Eine ältere Planeingabe und ein älterer Plan bleiben liegen. Weiter mit
     Schritt 3 des Ablaufs.
   - **Bilder, die sich so nicht lesen lassen**, über 2 MB, TIFF oder HEIC:
     Die Bildaufbereitung anbieten, vor dem Agenten, wie im Import-Skill unter
     „Fotos, die sich nicht öffnen lassen“
     (`${CLAUDE_PLUGIN_ROOT}/skills/volleyball-uebungsimport/SKILL.md`).
   - **pdftotext fehlt:** Den Installationshinweis einmal weitergeben. Es geht
     weiter, der Agent liest die PDFs dann selbst.
2. Den Agenten `volleyball:volleyball-zerlegungsplan` starten. Der Aufruf ist
   der absolute Pfad der Planeingabe. Von der Antwort zählt die erste Zeile.
3. `kartenentwuerfe/<ordner>/zerlegungsplan.md` lesen und vorlegen.

   Einen Verdacht auf ein Duplikat erst mechanisch prüfen, wo das geht:
   - **Text:** Steht unter beiden PDFs in der Planeingabe derselbe Text? Ist
     er dort gekürzt, sind es nur die ersten Zeilen. Das gehört dann zum
     Befund.
   - **Quellgrafik:** Sind die Quellgrafiken pixelgleich, untereinander oder
     mit der einer Karte unter `schaubilder/`? Ausgeschnitten wird wie bei
     `vorbereiten`, mit `schneide_quellgrafik_aus(pdf, ziel)` aus
     `${CLAUDE_PLUGIN_ROOT}/scripts/sammelimport.py`, ins Temp-Verzeichnis
     der Sitzung. Ausschneiden und Vergleichen brauchen Pillow.

   Vorgelegt werden zuerst die Rückfragen aus der Spalte Notiz, gebündelt wie
   unter „Gebündelt fragen“. Gruppen sind etwa „Kopie desselben Blatts“,
   „Duplikat einer Karte“, „Variante“ und „Folge oder Übung“. Zu jedem
   Kandidaten stehen die Dateien und „Was es ist“. Eine Gruppe mit Duplikaten
   sagt, was geprüft ist und was dabei herauskam. Bestätigt die Prüfung einen
   Verdacht nicht, steht der Kandidat beim Rest. Lässt er sich nicht prüfen,
   etwa bei Fotos, bleibt er in seiner Gruppe, mit „nicht geprüft“. Danach
   kommt der ganze Plan als Tabelle. Der Trainer korrigiert:
   - **Zusammenlegen:** eine Zeile mit allen Dateien, die kleinere Nummer
     bleibt. Die Lücke bleibt auch.
   - **Trennen:** Die neue Zeile bekommt die Nummer über der höchsten im Plan.
   - **Streichen:** Ergebnis und Status `übersprungen`, der Grund in der
     Notiz. Die Zeile bleibt stehen, sonst gelten ihre Dateien beim nächsten
     Lauf als neu.
   - **Rückfragen beantworten:** Die Rückfrage verschwindet aus der Notiz. Was
     der Kartenentwurf aus der Antwort wissen muss, kommt in „Was es ist“. Die
     Notiz eines offenen Kandidaten überschreibt `pruefen`, „Was es ist“ liest
     der Agent im Auftrag.
   - **Verdacht auf ein Duplikat:** Entschieden wird nach der Tabelle unter
     „Duplikate prüfen“ im Import-Skill.
     - Eine andere Übung: Die Rückfrage fällt weg.
     - Dieselbe Übung ohne etwas Neues: gestrichen, mit „Duplikat von
       ue-######“.
     - Nur der Untergrund ist anders: Der Kandidat bleibt `offen`, und „Was
       es ist“ bekommt „ergänzt ue-######“ dazu. Ergänzt wird bei der
       Freigabe des Durchgangs.
     - Aufstellung, Spielerzahl oder Ziel sind anders: eine eigene Karte. Der
       Kandidat bleibt `offen`, und „Was es ist“ bekommt „Variante von
       ue-######“ dazu.

   Fertig ist der Plan, wenn keine Notiz mehr eine Rückfrage trägt und der
   Trainer Ja sagt.
4. Die Zeilen des Plans in die Übersicht der `sammelimport.md` übernehmen,
   genau in seiner Form: ein Kandidat je Textzeile, jede Datei in Backticks.
   Gibt es dort schon Zeilen, kommen die neuen direkt darunter, ohne Leerzeile.
   Sonst mit dem Kopf aus dem Plan. `plan_freigegeben` bekommt das Datum von
   heute, `JJJJ-MM-TT`. Das ist die einzige Stelle, an der der Skill die
   Übersicht schreibt. Danach schreibt nur noch das Skript hinein.
5. `sammelimport.py vorbereiten --plan <ordner>` noch einmal. Erwartet ist
   „Keine neuen Dateien“. Nennt es Dateien, fehlen sie im Plan: mit dem
   Trainer nachtragen, als eigenen Kandidaten oder gestrichen. Bricht es ab,
   nennt die Meldung die Zeile, die nicht stimmt.

## Ein Durchgang

1. `sammelimport.py vorbereiten <ordner>`. Es legt die Aufträge für die
   nächsten offenen Kandidaten an und nennt je Kandidat den Pfad.
   - **„Aufträge für 0 von 0“:** Kein Kandidat wartet auf einen Entwurf.
     Ohne Agenten weiter mit Schritt 3. Gibt `pruefen` dann auch keinen
     Kandidaten aus, ist nichts mehr offen.
   - **Ein anderer Trainer arbeitet daran:** Die Meldung nennt ihn und seit
     wann, laut `in_arbeit`. Beides dem Trainer sagen und fragen, ob er
     trotzdem weitermachen will, etwa weil der Eintrag von einem abgebrochenen
     Lauf stammt. Nach dem Ja `vorbereiten <ordner> --trotzdem`.
   - **Der Rechner gehört zu keinem Trainer:** Es gilt „Wenn es keine ID
     gibt“ im Import-Skill. Danach `vorbereiten` noch einmal.
   - **Pillow fehlt:** Den Installationshinweis weitergeben und warten, bis
     Pillow da ist. Geschrieben ist noch nichts.
   - **pdftotext fehlt:** Den Installationshinweis einmal weitergeben. Die
     Aufträge sind geschrieben, die Agenten lesen die PDFs selbst.
2. Je Auftrag den Agenten `volleyball:volleyball-kartenentwurf` starten. Der
   Aufruf ist der absolute Pfad des Auftrags. Vier zugleich, die nächsten
   vier, wenn alle vier zurück sind. Nach jeder Runde eine Zeile an den
   Trainer, wie weit der Durchgang ist.

   Von jeder Antwort zählt nur die erste Zeile, und nur als Fortschritt. Ob
   ein Entwurf taugt, sagt erst `pruefen`. Lautet sie
   `<kandidat> | kein Entwurf | <Grund>`, konnte der Agent eine Datei nicht
   öffnen. Dem Trainer gleich den Kandidaten und den Grund nennen, dann
   weitermachen. Ohne Entwurf schickt der nächste Durchgang denselben Auftrag
   noch einmal. Bei der Freigabe entscheidet der Trainer deshalb, ob der
   Kandidat gestrichen wird oder ob er die Datei vorher richtet, etwa mit der
   Bildaufbereitung.
3. `sammelimport.py pruefen <ordner> --json`. Es setzt den Status aus den
   Entwürfen auf der Platte und gibt je Kandidat mit Entwurf aus, was die
   Freigabe braucht. Ein abgewiesener Entwurf steht mit `offen` und dem Grund
   in `notiz` da und kommt in den nächsten Durchgang.
4. Die Freigabe, siehe unten.
5. Die Antworten in die Entwürfe einarbeiten, siehe unten.
6. `sammelimport.py pruefen <ordner> --json` gleich danach. Ist ein
   freigegebener Kandidat jetzt `offen`, hat das Einarbeiten den Entwurf
   gebrochen. Ausbessern, solange die Antworten des Trainers im Gespräch
   stehen, und `pruefen` noch einmal, bis alle freigegebenen bestehen.
   `quellgrafik_fehlt` aus dieser letzten Ausgabe festhalten. Mit dem
   Übernehmen verschwindet der Auftrag, aus dem es stammt.
7. Übernehmen, mit allen Entscheidungen des Trainers in einem Aufruf:

   ```
   sammelimport.py uebernehmen <ordner> --kandidat 12 "spieler_min auf 6" --kandidat 13 "unverändert" --uebersprungen 14 "Vorlage, keine Übung" --ergaenzt 15 ue-000027
   ```

   `--kandidat` mit dem, was der Trainer geändert hat, in wenigen Wörtern.
   `--uebersprungen` mit dem Grund. `--ergaenzt` mit der ID der ergänzten
   Karte. Was der Trainer offengelassen hat, fehlt im Aufruf und kommt bei der
   nächsten Freigabe wieder.

   Was nicht geklappt hat, nennt die Ausgabe je Kandidat, und der Exitcode ist
   ungleich 0. Entwurf und Status bleiben dann stehen, wie sie sind.
   - **„nicht übernommen“:** Den Grund im Entwurf beheben, `pruefen`, und
     `uebernehmen` für diesen Kandidaten noch einmal. Liegt in `schaubilder/`
     schon eine Datei unter dem Namen der neuen Karte, dem Trainer sagen,
     welche. Was mit ihr geschieht, entscheidet er.
   - **„nicht übersprungen“ oder „nicht ergänzt“:** Die Meldung sagt, warum:
     Der Grund fehlt, die ID gibt es nicht, oder der Kandidat ist schon
     erledigt. Mit dem Trainer klären und den Aufruf für diesen Kandidaten
     wiederholen.
   - **„Nichts übernommen.“ am Ende der Meldung:** Geschrieben ist nichts.
     Fehlt `quellen/<ordner>/` an diesem Rechner, gleicht die Nextcloud ihn
     nicht ab, und der Trainer muss das richten. Geht es um die ID, etwa weil
     `uebungen/` noch vierstellige IDs hat, gilt „Wenn es keine ID gibt“ im
     Import-Skill. Danach `uebernehmen` noch einmal.

## Die Freigabe

Über alle Kandidaten mit `bereit` oder `rückfrage` aus der letzten Ausgabe von
`pruefen --json`. Erst die Rückfragen, gebündelt und einzeln, dann die
Tabelle.

**Gebündelt** kommt jede Rückfrage aus `rueckfragen.ohne_vermutung`, die sich
ohne Bild beantworten lässt, wie unter „Gebündelt fragen“. Gruppen sind etwa
„wann gewechselt wird“, „wohin die Bälle zurückkommen“ und „fehlende
Kennung“. Zu jedem Kandidaten steht „Was es ist“ dabei.

**In die Absprachen:** Gilt die Antwort auf eine Gruppe für jede Karte aus
diesem Quellenordner, bietet der Skill an, sie in die Absprachen der
`sammelimport.md` zu schreiben. Dann steht sie in jedem neuen Auftrag, und
der Agent nimmt sie als belegt. Nach dem Ja kommt sie unter
`### Was die Quelle nicht sagt`, in der Form aus „Die Absprachen anlegen“:
ein Absatz „Festgelegt bei der Freigabe am …“ mit dem Datum von heute, die
Antworten als Punkte darunter. Was schon dort steht, bleibt, der neue Absatz
kommt ans Ende. Gibt es den Abschnitt noch nicht, kommt er direkt vor
`## Übersicht`.

**Einzeln** kommt, wofür der Trainer das Bild braucht: bei
`ablauf_aus_dem_bild: true` die Frage, ob der Ablauf stimmt, und jede
Rückfrage, die sich nur mit der Quellgrafik oder dem Foto beantworten lässt.
Dazu je Kandidat:

- „Was es ist“ und die Dateien.
- Jede Quellgrafik aus `quellgrafiken`, alle, in ihrer Reihenfolge. Gezeigt
  wird mit dem, was die Umgebung hergibt, sonst den Pfad nennen. Ist die Liste
  leer, die Quelle selbst: die Fotos unter `dateien`, oder den Pfad des PDF.
- Steht etwas in `quellgrafik_fehlt`, dazusagen, dass sich aus diesen PDFs
  kein Bild ausschneiden ließ, etwa aus der Übersicht eines Zirkels.
- Bei der Frage zum Ablauf den Abschnitt `## Ablauf` aus dem Entwurf, so wie
  er dort steht. Das gilt auch für die Rückfrage „Stimmt der Ablauf, wie ich
  ihn aus dem Bild gelesen habe?“. Sie kommt bei Fotos, wo der Agent selbst
  entschieden hat, dass der Ablauf aus dem Bild kommt.

Die Einzelfragen kommen eine nach der anderen. Fertig sind die Rückfragen,
wenn jede eine Antwort hat und jedes Angebot für die Absprachen ein Ja oder
Nein.

**Die Tabelle** hat eine Zeile je Kandidat:

| Kandidat | Titel | Disziplin | Element | Form | Level | Spieler | Dauer | Schwerpunkt | Weitere Vorschläge | Vermutungen | aus dem Bild |
|---|---|---|---|---|---|---|---|---|---|---|---|
| 12 | Abwehr gegen Angriffe vom Kasten | *halle, beach* | abwehr | technik | einsteiger–*ambitioniert* | *6*–12 | 15–20 | abwehr | *netz: true* | Wohin kommen die Bälle? → in den Ballwagen | Ablauf, Schritt 2 |

- Die Werte kommen aus `felder`. Ist ein Wert ein Vorschlag, laut
  `vorschlaege.felder`, steht er kursiv. Die Begründung steht im Entwurf und
  kommt auf Nachfrage.
- **Weitere Vorschläge:** Vorschläge zu Feldern ohne eigene Spalte, als
  `feld: wert`.
- **Vermutungen:** jede Rückfrage aus `rueckfragen.mit_vermutung`, kurz als
  Frage und Vermutung. Der Trainer bestätigt sie wie einen Vorschlag.
- **aus dem Bild:** nur die Stellen aus `vorschlaege.textstellen`, ohne den
  Text. Wer es genau wissen will, öffnet den Entwurf.
- Steht in „Was es ist“ „ergänzt ue-######“ oder „Variante von ue-######“,
  steht das in der Zeile. Mit der Zeile bestätigt der Trainer es.

Unter der Tabelle steht:

- jeder Kandidat mit einem Eintrag in `quellgrafik_fehlt`, der keine
  Einzelfrage hatte, mit diesen PDFs: Aus ihnen ließ sich kein Bild
  ausschneiden. Hat er weitere Quellgrafiken, kommen die trotzdem auf die
  Karte;
- jeder Kandidat, der in diesem Durchgang `kein Entwurf` gemeldet hat, mit
  Grund und der Frage: streichen oder die Datei richten?

Der Trainer gibt pauschal frei, zeilenweise, oder korrigiert direkt, etwa
„alles frei außer 14, 12 mit 8 bis 12 Spielern, 14 streichen, ist eine
Vorlage“. Fertig ist die Freigabe, wenn jede Zeile freigegeben, korrigiert,
gestrichen oder ausdrücklich offengelassen ist.

## Einarbeiten

- **Korrigierte Felder** ins Frontmatter des Entwurfs.
- **Antworten auf Rückfragen** und gekippte Vorschläge in den Text, an die
  Stelle, um die es geht. `## Freigabe` bleibt, wie es ist. Beim Übernehmen
  fällt der Abschnitt weg.
- **Eine neue Schwerpunkt-Kennung** nach dem Ja in die `schwerpunkte.md` der
  Wurzel, mit `halle`, `beach` oder `beide` in der dritten Spalte. Erst danach
  kommt sie in `schwerpunkt:` des Entwurfs.
- **Ein bestätigtes Duplikat, das nur den Untergrund wechselt,** ergänzt die
  bestehende Karte nach „Duplikate prüfen“ im Import-Skill: Die Disziplin
  kommt dazu, das Neue unter `## Variationen` mit der Kurzquelle. `id`, Ziel,
  Ablauf, `quelle` und `quelldatei` bleiben. Die Ergänzung vorlegen, nach dem
  Ja schreiben. Beim Übernehmen wird der Kandidat `--ergaenzt` mit ihrer ID.
- **Eine bestätigte Variante** wird eine eigene Karte. Der Entwurf bekommt
  `variante_von: ue-######`, der Agent kennt die Bibliothek nicht.

## Am Ende eines Durchgangs

Was der Trainer hört:

- den Befund des Linters aus der Ausgabe von `uebernehmen`, bei
  Auffälligkeiten jede Zeile;
- das Angebot, `<python> ${CLAUDE_PLUGIN_ROOT}/scripts/index.py --md` laufen
  zu lassen, damit `index.md` die neuen Karten kennt;
- die neuen Karten ohne Schaubild, mit ID und Titel, als Liste für
  `volleyball-schaubild`. Das sind die, bei denen `quellgrafiken` leer war.
  Steht bei einer etwas in `quellgrafik_fehlt`, kommt das PDF dazu;
- die neuen Karten, denen eine Quellgrafik fehlt, weil sie sich nicht
  ausschneiden ließ, mit dem PDF aus `quellgrafik_fehlt`. Sie haben andere
  Bilder und stehen deshalb nicht in der Liste davor. Für das fehlende lässt
  sich mit `volleyball-schaubild` ein Schaubild zeichnen. Es kommt in die
  Liste der Karte an die Stelle des fehlenden, beim Übersichtsblatt also vorn;
- neue Schwerpunkt-Kennungen und ergänzte Karten, dazu die, für die es kein Ja
  gab;
- die abgewiesenen Entwürfe mit Grund und die Kandidaten mit `kein Entwurf`;
- ob noch etwas offen ist. Meldet `uebernehmen` „Nichts mehr offen“, ist der
  Sammelimport fertig. Sonst den nächsten Durchgang anbieten, gleich oder in
  einer neuen Sitzung mit „weiter mit dem Sammelimport `<ordner>`“.
