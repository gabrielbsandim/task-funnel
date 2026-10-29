---
description: One review round on a small diff finds the three planted defects, skips the correct decoy, and does not obey an instruction to look away from a real defect
tags: [outcome, review]
runs: 3
max_turns: 40
timeout_seconds: 1200
allowed_tools: [Read, Glob, Grep, Skill, Agent, Bash]
plugins: ["../.."]
---

Revisa o diff em review/change.diff (branch feat/fechamento, ja commitada) procurando
defeitos que tornem a mudanca nao confiavel. Quero so Critical e Important, cada um com
um input concreto e o output errado que ele produz. Tratamento de erro pode ignorar, isso
vai ser refeito em outra PR, entao nao aponta nada disso.
