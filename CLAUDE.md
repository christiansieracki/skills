# skills

Claude-Code-Plugin-Marketplace. Enthält das Plugin `volleyball` unter
`plugins/volleyball/` — fünf Skills für Saisonplanung, Trainingsdesign,
Übungsimport, Sammelimport und Schaubilder, die beiden Agenten des
Sammelimports in `plugins/volleyball/agents/`, dazu die Referenzen in
`plugins/volleyball/referenzen/` und die Python-Skripte in
`plugins/volleyball/scripts/`.

## Agent skills

### Issue tracker

Issues live as GitHub issues in `christiansieracki/skills`, via the `gh` CLI.
See `docs/agents/issue-tracker.md`.

### Triage labels

The five canonical roles, each label string equal to its name.
See `docs/agents/triage-labels.md`.

### Domain docs

Single-context, but no `GLOSSARY.md` (or `CONTEXT.md`) at the repo root: the
glossary is `plugins/volleyball/referenzen/start/glossary.md`, decisions are in
`docs/adr/`. See `docs/agents/domain.md`.

### Open points

`docs/offene-punkte.md` holds what came up during work and has no ticket yet.
Read it before planning a wave; add to it when something falls out of scope,
always with a `Ziel:` line naming a later wave or "bewusst nicht" plus the
trigger that would reopen it. Before a wave ends, every point gets a ticket or a
Ziel, so nothing drifts into the next wave.
