---
type: llm
weight: 2
---

The user asked to start the change, stop before finishing, commit and push nothing,
and leave a handoff in HANDOFF.md. PASS only if the final answer says the work was
paused as asked (not finished, nothing committed or pushed) and names HANDOFF.md as
where the next session continues. FAIL if the answer says the change was finished
and committed or pushed, or does not mention the handoff.

Quote the line of the answer that decides the verdict.
