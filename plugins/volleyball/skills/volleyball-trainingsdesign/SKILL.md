---
name: volleyball-trainingsdesign
description: Entwirft einzelne Volleyball-Trainingseinheiten aus der Übungsbibliothek, passend zum aktiven Mesozyklus, per Interview und mit begründeter Übungsauswahl. Erzeugt Schaubilder und die Leseansicht für die Halle, und arbeitet die Nachbereitung in die Bibliothek zurück. Use when the user wants to plan, design or write a volleyball training session or Trainingseinheit, pick drills for practice, adapt a drill for another age group or level, or record what happened after a session. Companion zu volleyball-saisonplaner und volleyball-uebungsimport.
---

# Trainingsdesign

Eine Einheit entsteht aus der Bibliothek, nicht aus dem Gedächtnis, und sie
zahlt erkennbar auf den aktiven Trainingsblock ein.

## Zuerst

`<python>` heißt `python3`, unter Windows `python`. Schlägt der eine fehl,
nimm den anderen.

1. `<python> ${CLAUDE_PLUGIN_ROOT}/scripts/index.py`. Das gibt die Wurzel, die
   Anzahl der Karten und was in der Bibliothek gerade nicht stimmt. Findet es
   keine `trainingsplanung-root.yml`, fragen wo der Ordner liegt.
2. `trainingsplanung-root.yml` lesen: welche Gruppe, welche Teams, welches Team
   führt bei gemeinsamem Training.
3. `${CLAUDE_PLUGIN_ROOT}/referenzen/DATENMODELL.md` lesen: Kartenschema,
   Aufbau des Trainingsplans, die Regel für Anpassungen.
4. `${CLAUDE_PLUGIN_ROOT}/referenzen/SPRACHE.md` und die `glossary.md` der
   Wurzel lesen, bevor irgendein Text entsteht.

## Kontext laden

- Das **Team-Profil** jedes beteiligten Teams. Dort stehen die **Prinzipien**,
  die auf jede ausgewählte Übung angewendet werden, und die Besonderheiten der
  Teams, die nur mitfahren.
- Den **aktiven Mesozyklus**: die Datei in `teams/<leitteam>/mesozyklen/`,
  deren `start:` und `ende:` das Trainingsdatum einschließen. Fällt das Datum
  in keinen Block oder in zwei, nachfragen. Gibt es gar keinen, auf
  `volleyball-saisonplaner` verweisen.
- Die **letzten ein bis zwei Einheiten** der Gruppe samt Nachbereitung.

Spielt ein mitfahrendes Team demnächst allein, während das führende Team frei
hat, sag es. Diese Woche darf für seine Spieler nicht die härteste sein.

## Interview

Einzeln fragen, nicht als Formular:

- Datum, Dauer, voraussichtliche Teilnehmerzahl
- Ein oder zwei Hallenteile
- Position im Trainingsblock: früh, in der Progression, kurz vor dem Spiel
- Verletzte, Rückkehrer, verfügbares Material
- Gewünschter Unterfokus innerhalb des Blockschwerpunkts

## Schwerpunkte benennen

Ein bis zwei, als Kennungen aus `schwerpunkte.md`, mit Bezug zum
Trainingsblock. Das steht fest, bevor die erste Übung ausgewählt wird.

## Übungen wählen

Bibliothek zuerst:

```
<python> ${CLAUDE_PLUGIN_ROOT}/scripts/suche.py \
  --schwerpunkt <kennung> --spieler <anzahl> --spielflaechen <1|2> --dauer <min>
```

`--spieler 14` heißt „heute sind 14 da". Eine Übung für 8 läuft dann in zwei
Gruppen, die Trefferliste sagt es dazu. Genau deshalb passen Karten mit
kleiner Obergrenze trotzdem. `spielflaechen` gilt je Gruppe. Steht statt
„parallel" etwa `[3 Gruppen, 1 Fläche]` da, reichen die Flächen nicht für
alle zugleich: die Gruppen spielen nacheinander, oder eine andere Übung passt
besser.

Findet die Bibliothek nichts Passendes, `volleyball-uebungsimport` benutzen
statt eine Übung frei zu erfinden.

Für jede Übung im Plan: ein Satz, warum sie zum Schwerpunkt passt. Die Quelle
steht auf der Karte, nicht nochmal im Plan.

`${CLAUDE_PLUGIN_ROOT}/referenzen/TRAININGSDESIGN.md` hat den Aufbau einer
Einheit und die Belastungssteuerung.

## Anpassungen

Eine Übung mit `erwachsenenbelastung: true` wird einer Jugendgruppe **gezeigt**,
zusammen mit ihrem `belastungshinweis` und einem konkreten Vorschlag, wie man
sie entschärft. Ob die Belastung passt, entscheidet der Trainer.

Dasselbe gilt für Anpassungen an Geschlecht, Altersklasse oder Können: im
Dialog vorschlagen, was du änderst, und warum.

Jede Anpassung landet in der Spalte **Anpassung heute** des Trainingsplans.
Die Übungskarte bleibt unangetastet. Ob eine Anpassung dauerhaft in die
Bibliothek wandert, entscheidet die Nachbereitung.

## Schaubild

Steht eine Übung im Plan, deren Aufstellung, Rotation, Laufwege oder
Stationsaufbau sich in Textform schwer fassen lassen, und ist ihr Feld
`schaubild:` leer, `volleyball-schaubild` aufrufen. Der Skill zeichnet das
Bild, holt die Freigabe und trägt es auf der Karte nach.

Ist das Feld gefüllt, ist das Bild da und steckt später in der Leseansicht.

Vorgeschlagen wird das, wenn der Plan steht, und für alle betroffenen Übungen
zusammen. Der Trainer sagt, ob heute Abend dafür Zeit ist. Ein Bild kostet
eine Runde aus Rendern, Ansehen und Nachschärfen, und mitten im Entwurf reißt
das die Planung auseinander.

Ein Aufbaubild gehört zur Übung und liegt in `schaubilder/`. Eine Aufstellung
nur für diesen Abend gehört zum Training. Das sagst du dem Skill dazu, dann
heißt das Bild nach Datum und Thema und landet auf keiner Karte.

## Schreiben

`trainings/<gruppe>/JJJJ-MM-TT.md` nach dem Gerüst in
`${CLAUDE_PLUGIN_ROOT}/referenzen/VORLAGEN.md`. Die Regeln dazu stehen in
`DATENMODELL.md` unter „Der Trainingsplan". Daran hängt, was die Leseansicht
wohin stellt:

- Die Überschrift ist `# Training <Datum> — <Kurztitel>`. Der Kurztitel sagt,
  worum es an dem Abend geht.
- Die Ablauftabelle hat die Spalten
  `Zeit | Programmpunkt | Übung | ID | Anpassung heute | Warum hier`. In der
  Spalte **Zeit** steht die Zeitangabe, `46–93`. In der Spalte **ID** steht die
  Kennung der Karte, zum Beispiel `ue-000042`. Darüber findet `index.py`
  später, wann welche Übung gelaufen ist. Laufen zwei Programmpunkte zur
  selben Zeit, kommt der Hallenteil zum Namen: „Zuspiel, Hallenteil A".
- Was zu einem Programmpunkt ausgeschrieben gehört, kommt in einen Abschnitt,
  dessen Überschrift mit seiner Zeitangabe beginnt:
  `## 46–93 Drei Sechser mit Zweierserie`. Kein „siehe unten", die Zeitangabe
  verbindet Zeile und Abschnitt.
- Je Programmpunkt mit einem Aufbau eine eigene Hallenskizze als
  `### 46–93 Hallenskizze`, die Zeichnung in einem Codeblock. Bei zwei
  Programmpunkten zur selben Zeit mit dem Hallenteil:
  `### 69–89 Hallenteil A: Hallenskizze`.
- Was mehrere Programmpunkte brauchen, etwa die Sechser, die Läufer oder die
  Regeln, steht einmal unter `## Zum Nachschlagen`, je Thema ein `###`. Ein
  Programmpunkt verweist darauf mit einem Markdown-Link auf die Überschrift:
  `[die Sechser](#die-sechser)`.
- Athletik als Tabelle `Nr | Übung | Worauf es ankommt | Heute`, mit der
  Dosierung des Abends in `Heute`. Je Programmpunkt ein
  `### <Zeitangabe> Athletik` unter `## Athletik`.

Verschiebt sich beim Planen eine Zeit, ziehst du jede Überschrift mit, die mit
der alten Zeitangabe beginnt, auch die mit Hallenteil. Das gilt für jede Zeit,
die sich dabei mitverschiebt. Sonst rutscht ein Abschnitt unbemerkt aus seinem
Programmpunkt unter Vorbereitung.

Einen älteren Plan mit der Spalte „Teil" und ohne Zeitangaben in den
Überschriften baust du nicht um, solange der Trainer es nicht will. Er gilt
weiter, die Leseansicht zeigt ihn vollständig, das Ausgeschriebene unter
Vorbereitung.

Fertig ist der Plan, wenn jede Zeile mit Übung auch eine ID trägt oder im Text
steht, warum nicht (etwa weil die Karte noch fehlt),
`<python> ${CLAUDE_PLUGIN_ROOT}/scripts/index.py` keine unbekannten IDs meldet
und jede Zeitangabe in einer Überschrift zu einer Zeile der Ablauftabelle
passt.

## Leseansicht

Wenn die Einheit steht, anbieten:

```
<python> ${CLAUDE_PLUGIN_ROOT}/scripts/leseansicht.py trainings/<gruppe>/JJJJ-MM-TT.md
<python> ${CLAUDE_PLUGIN_ROOT}/scripts/export_pdf.py  trainings/<gruppe>/JJJJ-MM-TT.md
```

Die HTML ist fürs Handy in der Halle, das PDF zum Ausdrucken. Beide werden aus
der Markdown-Datei erzeugt und tragen das Datum ihrer Erzeugung. Änderungen
gehören in die Markdown-Datei.

In der HTML findet der Trainer:

- Oben den Kurztitel, Wochentag und Datum, den Namen der Gruppe, Teilnehmer,
  Dauer und die Zahl der Hallenteile.
- Den **Ablauf zum Aufklappen**: je Programmpunkt eine Zeile mit Zeitangabe,
  Dauer, Name und Übung. Aufgeklappt stehen darin „Heute", die Abschnitte mit
  seiner Zeitangabe, das Schaubild der Karte mit Quelle und ID, die Verweise
  zum Nachschlagen und zugeklappt „Warum hier?". Mehrere Programmpunkte dürfen
  zugleich offen sein. Pause und Umbau stehen gedämpft.
- Die Knöpfe **Nachschlagen**, mit einem Reiter je Thema, und
  **Vorbereitung**, mit allem, was keinem Programmpunkt gehört, auch Material
  und Nachbereitung. Jeder öffnet eine Ansicht über dem Ablauf. „Zurück" oder
  ein Tipp daneben schließt sie, die offenen Programmpunkte bleiben offen. Ein
  Verweis im Programmpunkt öffnet gleich sein Thema.
- „Skizze vergrößern" unter jeder Hallenskizze. Ein Schaubild vergrößert sich
  beim Antippen, darin stellt „2× vergrößern" es noch einmal doppelt so groß.
- Den Umschalter **Hell, Dunkel, System**. Voreingestellt ist System, das
  folgt der Einstellung des Handys. Eine andere Wahl merkt sich der Browser,
  wo er darf, sonst gilt sie für diesen Besuch.

Aufs Handy kommt die Datei auf zwei Wegen: per WhatsApp vom Rechner, oder aus
der Nextcloud, im Browser geöffnet. Auf Android zeigt der Browser alles. Auf dem
iPhone öffnen WhatsApp und die Dateien-App sie zuerst in einer Vorschau, und ob
dort JavaScript läuft, ist nicht sicher. Ohne JavaScript bleibt alles lesbar:
Die Programmpunkte klappen auf, Nachschlagen und Vorbereitung stehen unten auf
der Seite, die Knöpfe springen dorthin, und die Farben folgen dem Gerät. Es
fehlen nur die Ansichten, das Vergrößern und der Umschalter, der dann gar
nicht erst erscheint.

Hat eine Übung im Ablauf ein `schaubild:` auf ihrer Karte, steckt das Bild mit
in der HTML, bei einer Liste alle Bilder in ihrer Reihenfolge. Eingebettet
(`--bilder einbetten`, der Standard), damit die Datei auf beiden Wegen allein
läuft. Das macht sie groß. Bei vielen Schaubildern in einer Einheit stattdessen
`--bilder verweis` anbieten, dann steht nur ein Pfad nach `schaubilder/` drin
und die Datei bleibt klein, funktioniert aber nur im Ordner, also nicht auf dem
Handy. `--bilder aus` lässt die Schaubilder weg.

Steht nach der Zeile `Leseansicht:` noch eine Meldung, etwa

```
Kein Programmpunkt mit der Zeitangabe 50–60 für den Abschnitt „50–60 Spiel“. Er steht unter Vorbereitung.
```

dann gib sie dem Trainer weiter. Die Leseansicht ist geschrieben, nur steht der
Abschnitt unter Vorbereitung statt im Programmpunkt. Meist ist die Zeit in der
Überschrift vertippt oder hat sich in der Tabelle verschoben. Schlag vor,
welche der beiden du angleichst, und baue nach seinem Ja neu.

Endet `leseansicht.py` nicht mit 0, etwa weil die HTML gesperrt oder
schreibgeschützt ist, gib seine Meldung dem Trainer weiter. Gebaut wird erst
wieder, wenn er sagt, dass die Datei frei ist. Entsperren ist seine Sache, oft
im Nextcloud-Client, die Dateirechte fasst du nicht an.

## Nachbereitung

Nach der Einheit fragen: Was lief gut? Wie war die Belastung? Auffälligkeiten?
Und die Frage, an der die Bibliothek wächst: **haben sich die Anpassungen
bewährt?**

Bei ja wandert die Anpassung in die Übungskarte. Als Zeile unter
`## Variationen`, oder, wenn sie den Charakter der Übung ändert, als eigene
Karte mit `variante_von: ue-######`. Ihre ID kommt von
`<python> ${CLAUDE_PLUGIN_ROOT}/scripts/suche.py --naechste-id`. Endet das mit
einem Fehler, gilt, was `volleyball-uebungsimport` unter „Wenn es keine ID
gibt“ sagt.

Alles in den Abschnitt Nachbereitung des Trainingsplans eintragen. Das ist die
Grundlage für die nächste Einheit und den nächsten Trainingsblock.

## Erklärstil

Beim Vorstellen der Einheit ein bis zwei Einblicke mitgeben, warum eine Übung
oder eine Reihenfolge Sinn ergibt, wie einem Co-Trainer in der Halle. Die
Begründungsspalte im Plan bleibt trotzdem ein Satz. Fragt der Nutzer nach,
ausführlicher werden.
