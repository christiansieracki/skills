# IDs sind sechsstellig und tragen die Nummer des Trainers

Eine ID ist `ue-` und sechs Ziffern: zwei für die Nummer des Trainers, vier
laufend. Jeder Trainer vergibt die höchste Nummer in seinem Bereich plus eins.
Wer welche Nummer hat und an welchen Rechnern er sitzt, steht unter `trainer:`
in der Wurzeldatei. Erkannt wird der Rechner an seinem Namen. Die bisherigen
Karten bekommen `00` vorn, `ue-0042` wird `ue-000042`.

Bis 2.5.1 war die nächste ID die höchste in `uebungen/` plus eins, gelesen aus
der lokalen Kopie. Zwei Rechner, die Nextcloud noch nicht abgeglichen hat,
vergeben so dieselbe ID. Am 26.09.2026 ist das zwei parallelen Sitzungen mit
`ue-0028` passiert (#29). Der Linter meldet es erst hinterher, und dann kann
ein Trainingsplan schon auf eine der beiden zeigen. Andere Trainer sollen
parallel importieren können, ohne sich abzusprechen. Mit eigenen Bereichen
kommen zwei Trainer einander nie in die Quere, auch ohne Abgleich.

## Considered Options

- **Hinterher umnummerieren**: Jeder vergibt wie bisher, und wer beim Abgleich
  eine doppelte ID findet, gibt seiner Karte eine neue. Verworfen: Bis dahin
  kann ein Trainingsplan auf die falsche Karte zeigen, und die neue Nummer
  bricht genau die Regel, dass eine vergebene ID sich nie ändert. Das hieße
  sie für jeden Zusammenstoß zu brechen statt einmal.
- **Eine Reservierungsdatei im Arbeitsordner**, in die jede Sitzung ihre
  Nummer einträgt, bevor sie schreibt. Verworfen: Die Datei liegt in derselben
  Nextcloud wie die Karten und wird genauso spät abgeglichen. Zwei Rechner
  reservieren dann dieselbe Nummer, und Nextcloud legt eine Konfliktkopie an.
  Für parallele Sitzungen auf einem Rechner gab es sie schon einmal, beim
  PlayDrill-Import von Hand (ADR-0010).
- **Die Nummer des Trainers auf dem Rechner speichern**, etwa in einer Datei
  im Profil. Verworfen: Dann sieht niemand, wer welche Nummer hat, und zwei
  Trainer könnten dieselbe wählen. In der Wurzeldatei steht es für alle
  sichtbar, und `suche.py --naechste-id` verweigert die ID, wenn zwei Trainer
  dieselbe Nummer tragen.

## Consequences

Die Umstellung bricht die Regel „Eine vergebene ID wird nie wieder geändert“
bewusst ein einziges Mal. Damit dabei kein Verweis ins Leere zeigt, stellt
`ids_umstellen.py` den ganzen Arbeitsordner auf einmal um: jede vierstellige
ID in `.md` und `.yml`, auch unter `quellen/`, und die Namen der Karten und
Schaubilder. Danach gilt nur das neue Format. Der Linter meldet vierstellige
IDs auf Karten und in Trainingsplänen, und solange es eine in `uebungen/`
gibt, vergibt `--naechste-id` keine neue. Sonst bekäme eine neue Karte
`ue-000042`, und die alte `ue-0042` würde beim Umstellen zu derselben.

Die Version springt auf 3.0.0, weil jeder bestehende Arbeitsordner umgestellt
werden muss. Ein installiertes 2.5.1 meldet jede sechsstellige ID als Fehler.

Ein Trainer an zwei Rechnern gleichzeitig kann weiter dieselbe ID vergeben,
bevor Nextcloud abgleicht. Das ist hingenommen: Es braucht denselben Trainer
an zwei Geräten zur selben Zeit, und der Linter meldet die doppelte ID.

Ein Rechner, der in keinem Eintrag steht, bekommt keine ID. Der
Import-Skill fragt dann, wer da sitzt, und trägt den Rechner oder einen neuen
Trainer erst nach dem Ja ein. Ein neuer Rechner kostet damit eine Frage beim
ersten Import.

Bei 100 Trainern und 9999 Karten je Trainer ist Schluss. Beides ist weit weg.
