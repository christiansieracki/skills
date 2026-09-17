# Schaubild-Vorlage: Volleyballfeld

Basis für alle räumlichen Schaubilder (Aufstellungen, Rotationen, Stationen, Laufwege). Über das Diagramm-Modul des Visualizers als SVG rendern. Farben immer über die vom Modul vorgegebenen CSS-Variablen, nicht hart kodieren.

## Maße & Orientierung

- Feld 9×18 m, im Schaubild als Hochformat-Rechteck (ein Team pro Feldhälfte).
- Netz waagerecht in der Mitte, Angriffslinie (3-m-Linie) je Hälfte einzeichnen.
- Sechs Positionen nach Volleyball-Konvention nummeriert: hinten 1/6/5, vorne 2/3/4. Position 1 = Aufschlagposition rechts hinten.

## Feldvorlage (SVG-Grundgerüst)

```svg
<svg viewBox="0 0 300 560" xmlns="http://www.w3.org/2000/svg">
  <!-- Spielfeld -->
  <rect x="30" y="20" width="240" height="480" fill="none" stroke="currentColor" stroke-width="2"/>
  <!-- Netz / Mittellinie -->
  <line x1="30" y1="260" x2="270" y2="260" stroke="currentColor" stroke-width="3" stroke-dasharray="6 4"/>
  <!-- Angriffslinien (3 m) -->
  <line x1="30" y1="180" x2="270" y2="180" stroke="currentColor" stroke-width="1"/>
  <line x1="30" y1="340" x2="270" y2="340" stroke="currentColor" stroke-width="1"/>
  <!-- Positionsmarker: <circle> mit Nummer; Laufwege als <path> mit Pfeil -->
</svg>
```

## Konventionen

- **Spieler:** Kreis mit Positionsnummer (1-6) oder Kürzel (Z=Zuspiel, D=Diagonal, AA=Außenannahme, MB=Mittelblock, L=Libero).
- **Laufweg:** durchgezogener Pfeil. **Ballweg:** gestrichelter Pfeil. In einer kurzen Legende unter dem Feld erklären.
- **Stationsaufbau:** mehrere kleine Felder/Zonen nebeneinander, jede Station beschriftet (Übungsname + Gruppengröße).
- Beschriftungen kurz halten; das Schaubild ergänzt den Text, ersetzt die Übungsbeschreibung nicht.

## Wann welches Schaubild

- **Aufstellung/Rotation:** ein Feld, sechs nummerierte Positionen, ggf. Pfeile für die Rotation.
- **Angriffs-/Laufsystem:** Lauf- und Ballwege als Pfeile auf einer Feldhälfte.
- **Stationsbetrieb:** Feld in Zonen unterteilt, Gruppen/Rotation der Gruppen andeuten.
