# Wissenskarte als eigene Kartensorte, nicht als Übungstyp

Fremdquellen enthalten mehr als Übungen: Trainingstheorie, Methodik,
Sportpsychologie, Physiologie. Dieses Wissen wird als **Wissenskarte** unter
`wissen/wi-####-slug.md` gesammelt, mit eigenem ID-Kreis, eigenem schmalem
Schema und den beiden Abschnitten `## Kernaussagen` und
`## Was das fürs Training heißt`.

Anlass war die Quelle Volleyball-Magazin 09/2026: von drei geprüften Seiten
enthält eine Übungen. Ein Import, der nur Übungen zieht, wirft den größeren
Teil solcher Quellen weg.

## Considered Options

- **Ein neuer Wert `typ: wissen` auf der Übungskarte.** Verworfen: der Linter
  verlangt auf jeder Übungskarte `form`, `spielphase`, `level_min` und
  `level_max`. Auf einem Text über Schlafqualität ist das sinnlos, und
  `suche.py --element annahme` würde Theoriebeiträge zwischen die Übungen
  mischen.

## Consequences

Geteilt wird das Vokabular, nicht das Schema: dieselben `schwerpunkt`-
Kennungen, dasselbe `disziplin`-Feld, dieselbe Quellendisziplin. Dazu kommt
ein eigenes, kleines `thema`-Vokabular (trainingslehre, methodik, psychologie,
physiologie, ernaehrung, regelkunde), weil Themen wie Schlaf oder Ernährung in
keine Schwerpunkt-Kennung passen — `schwerpunkte.md` ist ausdrücklich als
„das, was man trainieren kann" definiert, und diese Eigenschaft trägt die
gesamte Suche.

Die Abgrenzung zum **Prinzip**: ein Prinzip ist normativ und hängt am Team
(„maximal drei Annahmespieler im Riegel"), eine Wissenskarte ist Hintergrund
und hängt an niemandem. Ein Prinzip kann aus einer Wissenskarte entstehen; die
Karte bleibt dann als Begründung stehen.

## Nachtrag, 04.10.2026

Aus dem Interview zur Welle zur Wissenskarte.

- **ID:** nicht `wi-####`, sondern wie die Übung seit ADR-0011 sechsstellig mit
  der Nummer des Trainers vorn, `wi-000001`. Der Bereich ist derselbe, der
  Zähler ein eigener. Vergeben wird sie erst bei der Freigabe (ADR-0010).
- **Karte und Bibliothek:** „Karte“ meint beide Sorten, „Bibliothek“
  `uebungen/` und `wissen/` zusammen. Kartenentwurf, Rückfrage und Freigabe
  gelten so für beide, ohne neues Wort.
- **Prüffrage:** Wissenskarte wird, was keine Übung ist, aber sagen lässt,
  was es fürs Training heißt, ohne etwas zu erfinden. Ein Spielbericht oder
  ein Porträt bleibt liegen.
- **`thema`** bekommt zu den sechs Werten oben `technik` und `taktik`. Sonst
  hätten Technikbeschreibungen wie die Merkmale des oberen Zuspiels und
  Beiträge wie „Taktische Aufschläge“ kein Thema.
- **`schwerpunkt`** darf auf der Wissenskarte auch Steuerungsschwerpunkte
  tragen, etwa `belastungssteuerung`. Mit ihnen plant der Saisonplaner einen
  Trainingsblock, und genau dafür soll er die Karte finden. Das Feld ist
  freiwillig, ein Beitrag über Schlaf hat keine Kennung.
- **Bilder** stehen nicht im Feld `schaubild` wie bei der Übungskarte, sondern
  als Verweis im Text, an der Kernaussage, die sie zeigen. Eine Wissenskarte
  hat keine Leseansicht, die ein Feld anzeigen könnte, und ein Bild ohne
  Zusammenhang erklärt auf einer Wissenskarte nichts. Wie eine Leseansicht es
  später zeigt, entscheidet Welle 2.
