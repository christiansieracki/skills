# Trainingsdesign: Einzeltraining-Aufbau

## Struktur einer Einheit

- **Erwärmung** (10-15 min): allgemein + volleyballspezifisch (Ballkontakt, Bewegungsmuster).
- **Hauptteil Technik/Taktik** (30-45 min): passend zum Meso-Schwerpunkt, vom isolierten Element zur Spielsituation.
- **Spielform** (20-30 min): Fokus im spielnahen Kontext anwenden (z.B. 4-4 oder 6-6 mit Zusatzregel, die den Fokus erzwingt).
- **Abschluss** (5-10 min): Cool-down, kurzes Feedback, Ausblick auf nächste Einheit.

Im Trainingsplan wird daraus der Ablauf: Jede Phase ist dort ein Programmpunkt oder mehrere, jeder mit seiner Zeitangabe in Minuten ab Beginn. Pause und Umbau sind eigene Programmpunkte. Wie der Plan gegliedert ist, steht in `VORLAGEN.md`.

## Belastungssteuerung auf Einheiten-Ebene

- Vor wichtigen Spielen: Volumen runter, Intensität/Qualität hoch (Taper).
- Nach intensiven Spielphasen: aktive Erholung einplanen, nicht direkt volle Wucht.
- Verletzungsprävention (Rumpfstabilität, Landetechnik, Schulterprogramm) durchgängig einplanen, nicht nur in der Vorbereitung.
- Position der Einheit im Mesozyklus beachten (siehe aktiven Block in `mesozyklen/`): frühe Einheiten im Block dürfen isolierter/grundlegender sein, späte Einheiten näher an der Wettkampfsituation.

## Wann ein Schaubild sinnvoll ist

Ein kleines Schaubild erzeugen (nicht nur beschreiben), wenn:
- eine **Spielfeld-Aufstellung** oder **Rotation** gezeigt werden soll,
- ein **Stationsaufbau** mit mehreren Gruppen/Positionen erklärt wird,
- **Laufwege** oder Zuspielmuster für eine Übung sonst nur schwer verständlich wären.

Kein Schaubild bei rein konditionellen Übungen oder wenn eine Zeile Text reicht. Gezeichnet wird es vom Skill `volleyball-schaubild`, aus einer Szene heraus. Das Schaubild einer Karte zeigt die Leseansicht von selbst beim Programmpunkt, der ihre ID trägt. Ein Bild nur für diesen Abend bekommt einen Kurzverweis unter `## Schaubilder` im Trainingsplan.

Wie die Übung an diesem Abend in der Halle steht, sagt meist ein Satz unter **Aufbau** im Abschnitt des Programmpunkts. Eine Hallenskizze im Trainingsplan, ein Codeblock unter `### <Zeitangabe> Hallenskizze`, gibt es nur, wenn der Programmpunkt kein Schaubild hat und ein, zwei Sätze den Aufbau nicht sagen, oder wenn der Aufbau heute anders ist als im Schaubild. Dann zeigt sie den ganzen Aufbau von heute, mit einem Satz darüber, was anders ist.

## Übungsauswahl: Prinzip

- Bibliothek vor Recherche — spart Zeit und hält den Bestand konsistent.
- Jede Übung im finalen Plan braucht eine **Begründung** (Bezug zum Schwerpunkt) und eine **Quelle** ("eigener Bestand" oder Kurzquelle bei Recherche).
- Recherchierte Inhalte immer in eigenen Worten in die Bibliothek übernehmen, nie Volltext kopieren.
