# Domain Docs

How the engineering skills should consume this repo's domain documentation when exploring the codebase.

## Before exploring, read these

This repo has **no `CONTEXT.md` and no `CONTEXT-MAP.md`**, by decision — see `docs/adr/0003-kein-context-md.md`. Its domain documentation is the plugin's own reference set, which is also what ships to users:

- **`plugins/volleyball/referenzen/start/glossary.md`** — the glossary, and the single source of truth for terminology. Defines Übung, Übungsfolge, Übungsquelle, Prinzip, Team, Trainingsgruppe, Trainingsplan, Leseansicht, plus the naming rules (the Block-Regel). `init_struktur.py` copies this file into every new workspace, so a user's live `glossary.md` is this file plus their club's own additions and history.
- **`plugins/volleyball/referenzen/DATENMODELL.md`** — the binding schema: card frontmatter, controlled values, the ID contract, folder layout. Deviating from it produces cards `suche.py` cannot find.
- **`plugins/volleyball/referenzen/SPRACHE.md`** — tone and wording rules for anything written into a workspace.
- **`docs/adr/`** — decisions and the reasoning behind them. Read the ones touching the area you're about to work in.

If a file doesn't exist, **proceed silently**. Don't flag its absence.

**Don't create a `CONTEXT.md`.** A new term belongs in the glossary above. A second glossary is exactly what `DATENMODELL.md` warns against with *"Zweimal pflegen heißt einmal vergessen."*

## Use the glossary's vocabulary

When your output names a domain concept (in an issue title, a refactor proposal, a hypothesis, a test name), use the term as the glossary defines it. Don't drift to synonyms it explicitly avoids — the "Nicht verwenden" table is binding, and so is the Block-Regel.

If the concept you need isn't in the glossary yet, that's a signal: either you're inventing language the project doesn't use (reconsider) or there's a real gap. A new Kennung or term is **proposed** by a skill and **entered by a human** — never invented in passing.

## Flag ADR conflicts

If your output contradicts an existing ADR, surface it explicitly rather than silently overriding:

> _Widerspricht ADR-0001 (eine Bibliothek mit Disziplin-Markierung), aber einen zweiten Blick wert, weil…_
