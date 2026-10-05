# Leseansicht: freigegebene Designrichtung

**Vorlage, keine Quelle.** Diese Dateien sind die Vorlage für die Gestaltung
der Leseansicht. Nachgebaut wird sie in
`plugins/volleyball/scripts/leseansicht.py`, ohne Node und ohne Build-Schritt
(ADR-0012, #50). Mit dem Plugin werden sie nicht ausgeliefert. Der Hinweis
unten, es sei „noch kein allgemeines Datenformat“ abzuleiten, ist durch #50 und
ADR-0012 abgelöst. Die Beispieldaten `training-data.json` und das Bild
`training-2026-10-01-dankeball.png` liegen bis zur Abnahme (LA/10, #60) auf dem
Branch `overhaul/html-generation-display` und verschwinden mit ihm. Ohne sie
lassen sich die TSX-Dateien nicht bauen. Das müssen sie auch nicht.

Die bevorzugte Variante ist der kompakte **Ablauf zum Aufklappen**.
Hell und Dunkel gehören zur gleichen Gestaltung, nicht zu unterschiedlichen
Inhaltsversionen.

## Vorlagen

- `Accordion.tsx`: feste helle Ansicht.
- `AccordionDark.tsx`: feste dunkle Ansicht.
- `AccordionTemplate.tsx`: gemeinsame Ansicht mit **Hell / Dunkel / System**.
  Standard ist System; `prefers-color-scheme` folgt der Geräteeinstellung
  auch bei Änderungen. Eine manuelle Auswahl wird nach Möglichkeit gespeichert.
  Ohne verfügbaren Browser-Speicher gilt sie für den aktuellen Besuch.
  Geöffnete Ablaufteile bleiben beim Farbwechsel geöffnet.
- Die CSS-Dateien enthalten beide Farbpaletten und die gemeinsame Darstellung.
- `_shared.tsx`, `training-data.json` und das lokale PNG enthalten gemeinsame
  Bedienung und das vollständige Vergleichsbeispiel vom 01.10.2026.

## Verwendung und Grenzen

Dies sind React-/TypeScript-Designvorlagen, keine direkt zu öffnenden HTML-Dateien.
Sie benötigen React, React DOM und einen Bundler mit CSS-/JSON-Imports und
Unterstützung für `new URL(..., import.meta.url)` (z. B. Vite).
Die jeweilige exportierte Komponente in einen React-Einstieg einbinden.
Das Diagramm liegt lokal bei; es gibt keinen Bezug zu einer Replit-Vorschau-URL.

Datum, Kopfdaten und Trainingsinhalte sind bewusst das feste Vergleichsbeispiel.
Noch kein allgemeines Datenformat und keine neue Generator-Schnittstelle ableiten.
Nur vertrauenswürdige lokale Inhalte in die HTML-Inhaltsfelder übernehmen.

Der vorhandene Python-Generator ist unverändert. Die spätere Übertragung in
eine eigenständige Offline-HTML-Datei muss Skript, Stile und Diagramme vollständig
einbetten. Öffnen über Drive/WhatsApp und die tatsächlichen Android-/iPhone-
Dateiöffnungswege sind noch nicht validiert. Die automatische Farbauswahl allein
belegt diese Kompatibilität nicht.