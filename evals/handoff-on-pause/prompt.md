---
description: A task paused by the user stops without committing and leaves a handoff that separates what ran from what did not
tags: [outcome, handoff]
runs: 2
max_turns: 40
timeout_seconds: 1200
allowed_tools: [Read, Glob, Grep, Skill, Agent, Bash, Edit, Write]
plugins: ["../.."]
---

Comeca a mudar a mensagem tooLong em src/messages.ts para "Texto maior que 500 caracteres", mas eu preciso parar agora: nao termina, nao commita, nao sobe nada. Deixa um handoff em HANDOFF.md para a proxima sessao continuar.
