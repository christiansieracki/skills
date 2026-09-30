# Der Sammelimport arbeitet mit einem Plugin-Agenten

Der Sammelimport startet je Kandidat einen Subagenten über das Agent-Tool. Den
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
ein Skill, der je Kandidat eine zweite Claude-Instanz startet, von innen nach
außen gebaut ist. Das Agent-Tool gibt es überall, wo der Skill läuft.

Das Weitermachen nach einem Abbruch hängt nicht am Mechanismus. Es kommt aus der
Übersicht in `sammelimport.md`, die den Status jedes Kandidaten trägt.

## Considered Options

- **Ein Skript startet `claude -p` je Kandidat.** Verworfen aus den Gründen oben.
- **Die API direkt, oder `claude -p --bare`.** Verworfen: `--bare` spart den
  Überbau nur mit einem `ANTHROPIC_API_KEY`, also mit Abrechnung je Aufruf
  neben dem Abo.
- **Ein Werkzeug im Repo außerhalb des Plugins.** Verworfen mit der Entscheidung,
  den Sammelimport ins Plugin zu nehmen.

## Consequences

Die Sitzung, die den Sammelimport führt, wächst je Kandidat um den Aufruf und die
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
weg. Was ein Kandidat kostet, muss der Probelauf anders messen.

Damit hat das Plugin zum ersten Mal einen eigenen Agenten. ADR-0006 hat das
Muster eingeführt, dass ein Skill einen anderen aufruft. Hier ruft ein Skill
einen Agenten auf, der nur für ihn da ist und keinen eigenen Einstieg hat.

## Nachtrag nach dem Probelauf, 30.09.2026

Der Probelauf ist vor der Spec als Wegwerf-Prototyp gelaufen, auf dem lokalen
Branch `prototyp/sammelimport-probelauf`. Die Entscheidung für den Agenten hat
er bestätigt. Drei Stellen oben gelten so nicht mehr.

- **Modell:** Sonnet 5.5. Haiku 4.5 hat in 13 von 20 Entwürfen etwas
  geschrieben, das die Quelle nicht sagt, und den Zerlegungsplan über die
  Magazinfotos falsch gemacht.
- **Kosten:** Die Kostenangabe fällt nicht weg. Das Agent-Tool meldet je Aufruf
  `subagent_tokens`, Werkzeugaufrufe und Dauer. Ein Kartenentwurf kostete mit
  einem allgemeinen Subagenten im Median 91 000 Tokens. Ob das genau die Menge
  ist, die vom Abo abgeht, ist offen.
- **Sitzungen:** Eine Sitzung je Unterordner reicht nicht. Nach 44 Aufrufen und
  rund 3 Millionen Tokens war das Nutzungslimit des Abos erreicht, der größte
  Unterordner hat aber 59 Kandidaten. Gearbeitet wird deshalb mit etwa 30
  Kandidaten auf einmal. Sechs Aufrufe hatten ihren Entwurf noch geschrieben und
  brachen erst bei der Rückmeldung ab. Den Status in der Übersicht setzt deshalb
  ein Prüfskript aus den Entwürfen, die auf der Platte liegen. Die Rückmeldung
  des Agenten zeigt nur den Fortschritt.
