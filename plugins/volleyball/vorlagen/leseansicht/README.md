# Leseansicht: freigegebene Designrichtung

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