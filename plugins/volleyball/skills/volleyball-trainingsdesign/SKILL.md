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
kleiner Obergrenze trotzdem.

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

`trainings/<gruppe>/JJJJ-MM-TT.md` nach der Vorlage in
`${CLAUDE_PLUGIN_ROOT}/referenzen/VORLAGEN.md`. In der Ablauftabelle steht in
der Spalte **ID** die Kennung der Karte, zum Beispiel `ue-0042`. Darüber
findet `index.py` später, wann welche Übung gelaufen ist.

Fertig ist der Plan, wenn jede Zeile mit Übung auch eine ID trägt oder im Text
steht, warum nicht (etwa weil die Karte noch fehlt), und
`<python> ${CLAUDE_PLUGIN_ROOT}/scripts/index.py` keine unbekannten IDs meldet.

## Leseansicht

Wenn die Einheit steht, anbieten:

```
<python> ${CLAUDE_PLUGIN_ROOT}/scripts/leseansicht.py trainings/<gruppe>/JJJJ-MM-TT.md
<python> ${CLAUDE_PLUGIN_ROOT}/scripts/export_pdf.py  trainings/<gruppe>/JJJJ-MM-TT.md
```

Die HTML ist fürs Handy in der Halle, das PDF zum Ausdrucken. Beide werden aus
der Markdown-Datei erzeugt und tragen das Datum ihrer Erzeugung. Änderungen
gehören in die Markdown-Datei.

Hat eine Übung im Ablauf ein `schaubild:` auf ihrer Karte, steckt das Bild mit
in der HTML. Eingebettet, damit die Datei allein läuft, wenn man sie sich aufs
Handy schickt. Das macht sie groß. Bei vielen Schaubildern in einer Einheit
stattdessen `--bilder verweis` anbieten, dann steht nur ein Pfad nach
`schaubilder/` drin und die Datei bleibt klein, funktioniert aber nur im
Ordner.

## Nachbereitung

Nach der Einheit fragen: Was lief gut? Wie war die Belastung? Auffälligkeiten?
Und die Frage, an der die Bibliothek wächst: **haben sich die Anpassungen
bewährt?**

Bei ja wandert die Anpassung in die Übungskarte. Als Zeile unter
`## Variationen`, oder, wenn sie den Charakter der Übung ändert, als eigene
Karte mit `variante_von: ue-####`.

Alles in den Abschnitt Nachbereitung des Trainingsplans eintragen. Das ist die
Grundlage für die nächste Einheit und den nächsten Trainingsblock.

## Erklärstil

Beim Vorstellen der Einheit ein bis zwei Einblicke mitgeben, warum eine Übung
oder eine Reihenfolge Sinn ergibt, wie einem Co-Trainer in der Halle. Die
Begründungsspalte im Plan bleibt trotzdem ein Satz. Fragt der Nutzer nach,
ausführlicher werden.
