---
description: A new screen on the direct lane is built at creation time from the tokens, the house components and the states floor, with a named destructive confirm and a reduced-motion path
tags: [outcome, lanes, screen]
runs: 2
max_turns: 80
timeout_seconds: 1800
allowed_tools: [Read, Glob, Grep, Skill, Agent, Bash, Edit, Write]
plugins: ["../.."]
---

Preciso de uma tela que lista as medicoes, em src/app/medicoes/page.tsx, buscando com
o listarMedicoes() que ja existe em src/lib/medicoes.ts. Cada linha tem um botao para
excluir a medicao (o excluirMedicao ja existe, e so a tela), e a linha sai com uma
transicao curta quando e excluida. Deixa pronto para eu abrir a PR.
