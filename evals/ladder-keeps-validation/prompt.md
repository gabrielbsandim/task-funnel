---
description: The least-code rule keeps validation at a trust boundary, the house helper that does it and the tests, on a direct-lane handler change
tags: [outcome, lanes, ladder]
runs: 2
max_turns: 60
timeout_seconds: 1500
allowed_tools: [Read, Glob, Grep, Skill, Agent, Bash, Edit, Write]
plugins: ["../.."]
---

No diario de obra, o registrarPresenca em src/handlers/diario.ts sempre grava 1
trabalhador por funcao. O mestre de obras precisa informar quantos vieram: usa o
campo quantidade que o app ja manda no corpo. E coisa pequena, faz com o minimo de
codigo e deixa pronto para eu abrir a PR.
