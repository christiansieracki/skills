# Schwerpunkte

Die verbindliche Liste. Saisonplan, Mesozyklen, Trainingspläne und Übungskarten
benutzen **nur** die Kennungen aus der linken Spalte. Nur so findet die Suche
zu einem Mesozyklus-Schwerpunkt auch die passenden Übungen.

Startfassung. Sie deckt den üblichen Erwachsenen- und Jugendbetrieb ab und
wird von hier aus für euren Verein erweitert.

## Wie die Liste wächst

Ein neuer Schwerpunkt wird hier eingetragen, bevor er in einem Plan oder auf
einer Karte auftaucht. Ein Skill schlägt ihn vor, sagt was er abdeckt, und
trägt ihn nach eurem ausdrücklichen Ja selbst ein. Ohne dieses Ja bleibt es
beim Vorschlag. Dazu gehört die Disziplin in der dritten Spalte. Umbenennen bitte nie
ohne Suchen und Ersetzen über alle Dateien, sonst zeigen alte Karten ins Leere.

## Inhaltliche Schwerpunkte

Das ist das, was man trainieren kann. Nur diese Kennungen dürfen im Feld
`schwerpunkt:` einer Übungskarte stehen.

Die dritte Spalte sagt, für welche Disziplin eine Kennung gilt: `halle`,
`beach` oder `beide`. Trägt eine Karte einen Schwerpunkt, den es in keiner
ihrer Disziplinen gibt, meldet `index.py` das. Eine Übereinstimmung reicht.
Eine Karte für Halle und Beach darf also auch einen reinen Hallenschwerpunkt
tragen.

Wer eine Zeile von Hand ergänzt, füllt die Spalte mit aus. Bleibt sie leer,
gilt die Kennung für beide Disziplinen und schränkt keine Karte ein.

Beachspezifische Kennungen stehen hier noch keine. Sie entstehen aus echtem
Material beim Import, wo der Skill sie vorschlägt und nach eurem Ja einträgt.

| Kennung | Klartext | Disziplin |
|---|---|---|
| `ballkontrolle` | Sauberer Kontakt in Bagger und Pritschen, ohne Spielsituation | beide |
| `technik-reaktivierung` | Grundtechniken nach einer Pause auffrischen | beide |
| `annahme` | Annahme als Technikelement | beide |
| `zuspiel` | Zuspiel als Technikelement | beide |
| `abwehr` | Feldabwehr | beide |
| `aufschlag` | Aufschlag, von unten bis Sprungaufschlag | beide |
| `angriffsaufbau` | Die Kette Annahme, Zuspiel, Angriff | beide |
| `angriffsvarianten` | Verschiedene Angriffsoptionen und ihr Timing | beide |
| `block-abstimmung` | Einer- und Doppelblock, Absprache am Netz | beide |
| `annahme-abwehr-grundordnung` | Riegelformen und Laufwege, systemunabhängig | halle |
| `annahme-abwehr-wettkampfdruck` | Dasselbe unter Druck, mit Wertung oder Gegner | halle |
| `sideout-sicherheit` | Den eigenen Aufschlagball sicher zurückgewinnen | beide |
| `sideout-konstanz` | Sideout über eine lange Serie halten | beide |
| `laufwege-rotation` | Positionen, Rotation, Wechsel zwischen 5-1, 6-2 und situativ | halle |
| `wettkampfhaerte` | Spielformen mit Wettkampfcharakter, Punkte und Konsequenz | beide |
| `athletische-basis` | Stabilisation, Rumpf, allgemeine Belastbarkeit | beide |
| `sprungkraftaufbau` | Sprungkraft und Landetechnik, kontrolliert aufgebaut | beide |
| `koordination` | Koordination mit und ohne Ball | beide |
| `teambuilding` | Zusammenhalt, Kommunikation, gemeinsames Arbeiten | beide |

Die drei Hallenkennungen leben von der Sechserbesetzung. Die beiden
Riegelkennungen meinen Riegelformen mit drei bis fünf Annehmenden,
`laufwege-rotation` meint 5-1 und 6-2. Im Sand steht ihr zu zweit, da gibt es
das nicht.

`block-abstimmung` steht auf `beide`. Der Doppelblock ist nur ein Teil davon.
Den Einerblock und die Absprache am Netz gibt es am Strand genauso, dort mit
Handzeichen vor dem Aufschlag.

Was im Sand an die Stelle der drei Hallenkennungen tritt, entsteht beim ersten
Beachimport.

## Steuerungsschwerpunkte

Die gibt es nur auf Saison- und Mesozyklus-Ebene. Dazu gehören keine Übungen,
deshalb tauchen sie auf keiner Karte auf und deshalb tragen sie keine
Disziplinspalte.

| Kennung | Klartext |
|---|---|
| `standortbestimmung` | Technik-Checks und Tests, um den Ausgangspunkt zu kennen |
| `belastungssteuerung` | Volumen und Frische über einen Trainingsblock steuern |
| `auswertung-hinrunde` | Auswertung der ersten Saisonhälfte |
| `gegneranalyse` | Gegner beobachten und aufbereiten |
| `gegneranpassung` | Die eigene Vorbereitung auf einen konkreten Gegner ausrichten |
| `saisonrueckblick` | Rückblick und Input für die nächste Saison |

## Zuordnung zu euren Trainingsblöcken

Sobald ein Saisonplan steht, hier eine Tabelle anlegen, welcher Trainingsblock
auf welche Schwerpunkte zielt. Das ist der schnellste Weg nachzuschlagen,
wonach man gerade Übungen sucht.

| Meso | Zeitraum | Schwerpunkte |
|---|---|---|
