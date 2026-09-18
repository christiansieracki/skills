# Kein CONTEXT.md — die Plugin-Referenzen sind das Domänenmodell

Dieses Repo legt kein `CONTEXT.md` an. Das Domänenmodell steht in
`plugins/volleyball/referenzen/` — im Glossar `start/glossary.md` und im
Schema `DATENMODELL.md`. `docs/agents/domain.md` verweist dorthin.

`start/glossary.md` ist zugleich die Saat, die `init_struktur.py` in jeden
Arbeitsordner kopiert: die Begriffe werden also ohnehin gepflegt und
ausgeliefert. Ein `CONTEXT.md` daneben wäre ein zweites Glossar — genau das,
wovor `DATENMODELL.md` mit „Zweimal pflegen heißt einmal vergessen" warnt.

## Consequences

Ein neuer Begriff wird im Saat-Glossar eingetragen, nicht in einem
CONTEXT.md. Vereinsspezifische Regeln und die Umsetzungshistorie bleiben in
der lebenden `glossary.md` des jeweiligen Arbeitsordners; allgemeingültige
Regeln wandern von dort in die Saat hoch, so wie es mit der Block-Regel
bereits geschehen ist.
