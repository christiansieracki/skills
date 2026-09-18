---
name: volleyball-saisonplaner
description: Entwickelt im Dialog den Saisonplan eines Volleyballteams und die daraus abgeleiteten Mesozyklen, benennt die Schwerpunkte jedes Trainingsblocks als Kennungen und begründet sie. Legt auch Team-Profile samt ihrer Prinzipien an. Use when the user wants to build or update a Saisonplan, Makrozyklus, Mesozyklus, Trainingsblock, or a team profile for a volleyball team. Companion zu volleyball-trainingsdesign, der daraus die einzelnen Einheiten entwirft.
---

# Saisonplaner

Saisonplan und Mesozyklen entstehen im Gespräch, nie als Einweg-Ausgabe. Ihre
Schwerpunkte sind Kennungen aus `schwerpunkte.md`, damit `volleyball-trainingsdesign`
später Übungen dazu findet.

## Zuerst

`<python>` heißt `python3`, unter Windows `python`. Schlägt der eine fehl,
nimm den anderen.

1. `<python> ${CLAUDE_PLUGIN_ROOT}/scripts/index.py`. Das gibt die Wurzel.
   Findet es keine `trainingsplanung-root.yml`, fragen wo der Ordner liegt.
   Gibt es noch keinen, `<python> ${CLAUDE_PLUGIN_ROOT}/scripts/init_struktur.py <ordner>`.
2. `trainingsplanung-root.yml` lesen: welche Teams, welche Gruppen, welches
   Team führt bei gemeinsamem Training.
3. `${CLAUDE_PLUGIN_ROOT}/referenzen/SPRACHE.md` und die `glossary.md` der
   Wurzel lesen, bevor irgendein Text entsteht.
4. Die `schwerpunkte.md` der Wurzel lesen. Sie ist die verbindliche Liste.

## Team-Profil

Gibt es keins, im Dialog anlegen: Niveau, Altersklasse, Kader mit Positionen,
Trainingsrhythmus, Rahmenbedingungen. Gibt es eins, gegenlesen und nur
Änderungen erfragen. Vorlage in `${CLAUDE_PLUGIN_ROOT}/referenzen/VORLAGEN.md`.

Ins Profil gehören auch die **Prinzipien** des Teams: Regeln, die über
einzelne Übungen hinweg gelten, etwa „maximal drei Annahmespieler im Riegel".
Sie stehen dort und nicht in der Übungsbibliothek, weil sie vom Niveau
abhängen: für eine U14 wäre dieselbe Regel falsch.

Ein Team, das auf dem Saisonplan eines anderen mitfährt, bekommt trotzdem ein
Profil. Dort gehören sein eigener Spielplan und alles hin, was bei gemeinsamen
Einheiten für die Belastungssteuerung gebraucht wird.

## Interview vor dem Saisonplan

Klären, bevor ein Plan entsteht:

- Saisonziel und die Termine, an denen die Mannschaft in Form sein muss
- Baustellen aus Trainersicht, technisch, taktisch, athletisch
- Kaderbesonderheiten: Größe, Verletzte, Zugänge, Verfügbarkeiten
- Stärken, auf denen aufgebaut werden soll
- Spielplan des Verbands. Ist er nicht zur Hand, danach fragen oder recherchieren

Fertig ist das Interview, wenn zu jedem dieser fünf Punkte eine Antwort
vorliegt.

## Saisonplan entwerfen

Phasen nach `${CLAUDE_PLUGIN_ROOT}/referenzen/METHODIK.md`, so dass die
Antworten aus dem Interview im Plan sichtbar werden.

Die längeren spielfreien Zeiträume aus dem Spielplan bestimmen, wo die
Trainingsblöcke geschnitten werden. Sie sind die einzige Gelegenheit im Jahr,
an der wirklich etwas Neues entwickelt werden kann.

Entwurf vorlegen, Rückfragen einholen, dann `teams/<team>/saisonplan.md`
schreiben. In der Mesozyklus-Tabelle stehen Kennungen aus `schwerpunkte.md`.
Fehlt eine passende, dem Nutzer eine neue vorschlagen und erst nach seinem Ja
dort eintragen.

## Interview vor jedem Mesozyklus

Vorher lesen: aktuelle Saisonphase, den vorigen Trainingsblock, die letzten
Trainingspläne samt Nachbereitung. Dann fragen:

- Was hat sich seit dem letzten Block gezeigt?
- Welches eine, höchstens zwei Themen sollen jetzt in den Fokus?
- Welche Spieltermine liegen im Block, und wann muss die Mannschaft in Form sein?

## Mesozyklus entwerfen

Höchstens zwei explizit benannte Schwerpunkte, jeder mit einem Satz, was er
konkret heißt, und einer Begründung mit Bezug zu Saisonplan, vorigem Block und
dem, was sich gezeigt hat.

Belastung wochenweise skizzieren, Sprungbelastung getrennt ausweisen. Start-
und Enddatum ins Frontmatter, daran erkennt `volleyball-trainingsdesign` den
aktiven Block.

Entwurf vorlegen, dann `teams/<team>/mesozyklen/meso-##-thema.md` schreiben.
Vorlage in `VORLAGEN.md`.

Fertig ist der Block, wenn `start:` und `ende:` gesetzt sind, jeder Eintrag
unter `schwerpunkt:` in `schwerpunkte.md` steht, und die Zeiträume aller Blöcke
des Teams lückenlos und überschneidungsfrei aneinander liegen.

## Leseansicht

Nach dem Speichern anbieten:

```
<python> ${CLAUDE_PLUGIN_ROOT}/scripts/export_pdf.py teams/<team>/saisonplan.md
```

## Erklärstil

Beim Vorstellen eines Entwurfs ein bis zwei Einblicke mitgeben, warum er so
aussieht, wie einem Co-Trainer in der Halle. Das Begründungsfeld im Dokument
bleibt trotzdem ein Satz. Fragt der Nutzer nach, ausführlicher werden.
