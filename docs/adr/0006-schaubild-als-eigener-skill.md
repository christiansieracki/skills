# Das Schaubild bekommt einen eigenen Skill

Das Zeichnen wird nicht als Modus in den Import eingebaut, sondern als vierter
Skill `volleyball-schaubild` mit eigenem Einstieg. Import und Trainingsdesign
rufen ihn auf, wenn ein Schaubild fällig ist; der Trainer kann ihn ebenso gut
direkt ansprechen, für Karten, die längst in der Bibliothek liegen.

Ausschlaggebend war die Kontextgrenze. Das Zeichnen ist teuer: jedes Bild
durchläuft eine Schleife aus Rendern, Ansehen und sprachlichem Nachschärfen.
Fünfzehn Karten mit je zwei Runden sind eine eigene Sitzung, kein Anhängsel an
einen Import. Ein frisches Kontextfenster braucht aber etwas, das man
**ansprechen** kann — und genau das ist die Beschreibung eines Skills. Ein Modus
im Import-Skill würde die Trennung formal erlauben und praktisch entwerten, weil
das neue Fenster das gesamte Importwissen mitlädt, das es nicht braucht.

Die Zweiteilung ist optional, nicht vorgeschrieben. Der Import schlägt den
sinnvolleren Weg nach der **Zahl der Kandidaten** vor: ein oder zwei Bilder
entstehen gleich mit, solange das Material frisch im Blick ist; ab drei schließt
der Import sauber ab, nennt die IDs und überlässt das Zeichnen einem neuen
Fenster.

## Considered Options

- **Nur eine aufgebohrte Referenz plus Skript**, auf die beide bestehenden Skills
  verweisen. Verworfen, weil eine Referenz keinen Auslöser hat: sie wird gelesen,
  wenn ein Skill sie nennt, aber sie startet nichts. Der direkte Einstieg „zeichne
  ein Schaubild für ue-0042" hätte damit kein Ziel.

## Consequences

Der Zeichen-Skill findet seine Kandidaten **selbst** — Karten ohne `schaubild:`,
deren Beschreibung räumlich ist — statt sich auf eine mitgeschriebene Arbeitsliste
zu stützen. Eine solche Liste wäre ein dritter Zustand, der veraltet, sobald
jemand von Hand ein Bild ergänzt, und `suche.py` beantwortet die Frage ohnehin.
Der Import nennt die IDs am Ende trotzdem, damit sie sich kopieren lassen.

Damit ruft erstmals ein Skill dieses Plugins einen anderen auf; bisher kennen die
Skills einander nur über die `description`. Das neue Muster muss eng formuliert
werden, sonst feuert es bei jeder Kleinigkeit.

Der Auslöser bleibt eng: vorgeschlagen wird ein Schaubild nur, wenn es einen
Anlass gibt — die Quelle enthält ein Feldbild, oder die Beschreibung ist räumlich
— und der Vorschlag kommt gesammelt am Ende eines Imports, nicht zwischen jeder
Karte. Es bleibt ein Vorschlag: ein vorhandenes Bild aus der Quelle
auszuschneiden bleibt erlaubt, so wie es bei den vier PlayDrill-Feldbildern aus
Ricos PDF bereits geschehen ist.
