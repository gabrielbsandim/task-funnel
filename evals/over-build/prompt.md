---
description: A display helper the platform already provides, off the money and risk paths, is written as the least code that meets it
tags: [outcome, lanes, size]
runs: 3
max_turns: 60
timeout_seconds: 1500
allowed_tools: [Read, Glob, Grep, Skill, Agent, Bash, Edit, Write]
plugins: ["../.."]
---

Preciso mostrar a area medida na tela: 12500.5 tem que aparecer como "12.500,5 m²" e 80
como "80 m²". Cria uma funcao para isso em src/format.ts e deixa pronto para eu abrir a PR.
