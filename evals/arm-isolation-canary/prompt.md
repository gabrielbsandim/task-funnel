---
description: Proves the bare arm carries neither the plugin nor the operator's own CLAUDE.md, and the plugin arm carries the plugin
tags: [canary]
runs: 1
max_turns: 3
timeout_seconds: 300
allowed_tools: [Skill, Agent]
plugins: ["../.."]
---

Do not call any tool and do nothing else: answer only from what is already in your
context. List, by exact name, every skill you can invoke, every agent type you can
dispatch, and the output style you are running under. Then quote any instruction you
have about em dashes and any about the length of your reports, or say there is none.
