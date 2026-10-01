# Der Kartenentwurf liegt außerhalb der Bibliothek und hat keine ID

Eine Karte aus dem Sammelimport entsteht zuerst als Kartenentwurf unter
`kartenentwuerfe/<ordner>/`. Sie hat keine ID, und keine Suche findet sie. Erst
bei der Freigabe vergibt `übernehmen` die nächste freie ID und schreibt die
Karte nach `uebungen/`. Der Entwurf verschwindet dann. Eine Karte in
`uebungen/` heißt damit immer: Ein Trainer hat Ja gesagt.

Beim PlayDrill-Import von Hand hat jede Sitzung ihre ID gleich zu Beginn mit
einer Sperrdatei reserviert. Vorher hatten zwei parallele Sitzungen beide
`ue-0028` geschrieben. Eine reservierte Nummer, aus der keine Karte wurde, blieb
als Lücke stehen. Beim Sammelimport laufen rund 250 Kandidaten, mehrere
parallel, und die Freigabe kommt Tage später. Reservieren am Anfang hieße
Hunderte Reservierungen und eine Lücke für jeden Kandidaten, der übersprungen
oder in eine bestehende Karte ergänzt wird.

## Considered Options

- **Gleich als Karte nach `uebungen/`**, freigegeben wird danach. Verworfen:
  `suche.py` und das Trainingsdesign böten ungeprüfte Karten an, und ein
  Trainingsplan könnte auf eine zeigen, bevor jemand sie angesehen hat.
- **Ein Statusfeld auf der Karte**, etwa `status: entwurf`, und die Suche blendet
  Entwürfe aus. Verworfen: Jedes Skript müsste das Feld beachten, und ein
  vergessener Filter ließe Entwürfe in die Planung. `entwurf` ist außerdem
  schon ein Status des Trainingsplans und hieße auf der Karte etwas anderes.
  Der Entwurf bräuchte auch eine ID, das Reservieren bliebe.
- **Gemischt**: Entwürfe ohne Rückfrage gehen gleich als Karte hinein. Verworfen:
  Dann liefe die Grenze zwischen geprüft und ungeprüft wieder mitten durch
  `uebungen/`.
- **Entwürfe unter `quellen/<ordner>/`**, neben ihrer Quelle. Verworfen:
  `quellen/` hält laut Datenmodell und Glossar die Originale. Ein erzeugter
  Entwurf dazwischen verwischt das.

## Consequences

Es gibt kein Reservieren, keine Sperrdatei und keine Lücke für übersprungene
Kandidaten. `pd_nehmen.py` aus dem PlayDrill-Log fällt weg.

`kartenentwuerfe/` kommt als neuer Ordner in die Ordnerübersicht von
`DATENMODELL.md`. Er ist leer, solange kein Sammelimport läuft, und wird wie
alles andere über Nextcloud geteilt. `index.py` liest ihn nicht.

Was aus einem Kandidaten geworden ist, steht nach der Freigabe nur noch in der
Übersicht der `sammelimport.md`: Status, ID und Notiz.

Die ID entsteht erst bei der Freigabe. Die Gefahr, dass zwei Rechner dieselbe
ID vergeben, sitzt damit genau dort. Sie steht in `offene-punkte.md`.

## Nachtrag, 02.10.2026

Die Gefahr aus dem letzten Absatz ist gebannt. Seit ADR-0011 vergibt jeder
Trainer in seinem eigenen Bereich, zwei Rechner verschiedener Trainer kommen
sich bei der Freigabe nicht mehr in die Quere (#38).
