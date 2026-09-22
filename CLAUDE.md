# skills

Claude-Code-Plugin-Marketplace. Enthält das Plugin `volleyball` unter
`plugins/volleyball/` — vier Skills für Saisonplanung, Trainingsdesign,
Übungsimport und Schaubilder, dazu die Referenzen in
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

Single-context: `CONTEXT.md` and `docs/adr/` at the repo root.
See `docs/agents/domain.md`.

### Open points

`docs/offene-punkte.md` holds what came up during work and has no ticket yet.
Read it before planning a wave; add to it when something falls out of scope.
