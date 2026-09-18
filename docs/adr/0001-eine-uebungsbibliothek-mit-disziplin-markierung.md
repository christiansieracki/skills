# Eine Übungsbibliothek für Halle und Beach, mit Disziplin-Markierung auf der Karte

Die Bibliothek wird auf Beachvolleyball erweitert. Statt einer zweiten
Bibliothek bekommt jede Übungskarte ein Pflichtfeld `disziplin`, das eine
**Liste** aus `halle` und `beach` trägt. Getrennt wird beim Suchen, nicht beim
Ablegen.

Ausschlaggebend war der Bestand: von den 17 vorhandenen Karten laufen
mindestens sechs unverändert am Strand (`ue-0002` Zonenbaggern, `ue-0006`
Pritsch-Dreieck, `ue-0008` Lauf-ABC mit Ball, `ue-0009` Einspielen mit
Zielvorgabe, `ue-0012` Kleinfeld-Liga Zwei-gegen-Zwei, `ue-0013` Vier mit
sich). Eine zweite Bibliothek hätte diese doppelt gepflegt.

## Considered Options

- **Zwei Ordner oder zwei Wurzeln.** Verworfen: Die `id` ist in diesem System
  die Identität, über die Trainingspläne verweisen und `index.py` auflöst.
  Dieselbe Übung zweimal unter zwei IDs bricht genau diese Zusage. Die
  Trennung, die zwei Ordner kaufen, liefert ein Suchfilter billiger.
- **Einzelwert mit drittem Wert `beide`.** Verworfen: zwingt jeden Filter für
  immer zu „beach **oder** beide". Eine Liste macht daraus einen
  Mengenschnitt, genau wie `element` ihn schon benutzt.
- **Stiller Default `[halle]`, wenn das Feld fehlt.** Verworfen, nachdem klar
  war, dass es keine fremden Bibliotheken gibt, auf die Rücksicht zu nehmen
  wäre. Ein stiller Default schweigt genau dann, wenn beim Import das Feld
  vergessen wurde, und legt die Beachübung wortlos unter Halle ab.

## Consequences

`hallenteile` wird zu `spielflaechen` umbenannt. Das Feld hat nie „Hallenteil"
bedeutet — `suche.py` behandelt es als „so viele braucht die Übung, so viele
hast du". Auf einer Karte mit `disziplin: [halle, beach]` wäre der alte Name
eine Wortlüge, und „Hallenteil" bleibt im Glossar als reiner Raumbegriff
belegt. Betroffen sind rund 20 Fundstellen in Plugin und Arbeitsordner.

„Halle" wird damit zusätzlich zum Disziplinwert, obwohl „Hallenteil" bereits
den Raum meint. Das wird wie die bestehende Block-Regel als Sprachregel im
Glossar festgehalten, statt auf einen Anglizismus (`indoor`) auszuweichen, den
die Sprachliste des Projekts ohnehin ablehnt.
