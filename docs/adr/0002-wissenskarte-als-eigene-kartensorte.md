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
