# Der Sammelimport arbeitet mit einem Plugin-Agenten

Der Sammelimport startet je Einheit einen Subagenten über das Agent-Tool. Den
Agenten bringt das Plugin selbst mit, als `volleyball-kartenentwurf` unter
`agents/`. Er hat nur `Read` und `Write`, und sein Prompt ist ein knapper
Auszug der Regeln für einen Kartenentwurf. Das Modell steht in der Definition,
der Skill kann es je Aufruf überschreiben. Der Agent schreibt seinen
Kartenentwurf selbst und meldet eine Zeile zurück.

In `offene-punkte.md` stand vorher ein Skript, das je PDF `claude -p` startet.
Ein Orchestrator sammelt dabei keinen Kontext an, und ein abgebrochener Lauf
macht bei der ersten offenen Zeile weiter. Das passte, solange der Lauf ein
Werkzeug für die PlayDrill-Bibliothek auf einem Rechner war. Beim Interview am
30.09.2026 wurde daraus ein Teil des Plugins, weil er auch abfotografierte
Magazinseiten verarbeiten und sich wiederholen lassen soll. Damit muss er auf
jedem Rechner laufen, auf dem das Plugin installiert ist.

`claude -p` setzt voraus, dass die Kommandozeile `claude` im PATH liegt. Wer
Claude Code nur als Desktop-App benutzt, hat das nicht sicher. Dazu kommt, dass
ein Skill, der je Einheit eine zweite Claude-Instanz startet, von innen nach
außen gebaut ist. Das Agent-Tool gibt es überall, wo der Skill läuft.

Das Weitermachen nach einem Abbruch hängt nicht am Mechanismus. Es kommt aus der
Übersicht in `sammelimport.md`, die den Status jeder Einheit trägt.

## Considered Options

- **Ein Skript startet `claude -p` je Einheit.** Verworfen aus den Gründen oben.
- **Die API direkt, oder `claude -p --bare`.** Verworfen: `--bare` spart den
  Überbau nur mit einem `ANTHROPIC_API_KEY`, also mit Abrechnung je Aufruf
  neben dem Abo.
- **Ein Werkzeug im Repo außerhalb des Plugins.** Verworfen mit der Entscheidung,
  den Sammelimport ins Plugin zu nehmen.

## Consequences

Die Sitzung, die den Sammelimport führt, wächst je Einheit um den Aufruf und die
eine Zeile Antwort, geschätzt 300 Tokens. Deshalb eine Sitzung je Unterordner,
der größte bei PlayDrill hat 59 Dateien. Die nächste Sitzung macht an der
Übersicht weiter.

Der Agent kann nicht nachfragen. Was er fragen würde, schreibt er als Rückfrage
in den Kartenentwurf. Ein Skript prüft jeden Entwurf danach auf kontrollierte
Werte, bekannte Kennungen und eine vorhandene `quelldatei`.

Der Auszug der Regeln liegt als Agentendefinition im Plugin und wird mit ihm
versioniert. Ein Test im Repo prüft seine kontrollierten Werte gegen
`tpdaten.py`, damit er dem Datenmodell nicht unbemerkt hinterherläuft.

Die Kostenangabe je Aufruf, die `claude -p --output-format json` liefert, fällt
weg. Was eine Einheit kostet, muss der Probelauf anders messen.

Damit hat das Plugin zum ersten Mal einen eigenen Agenten. ADR-0006 hat das
Muster eingeführt, dass ein Skill einen anderen aufruft. Hier ruft ein Skill
einen Agenten auf, der nur für ihn da ist und keinen eigenen Einstieg hat.
