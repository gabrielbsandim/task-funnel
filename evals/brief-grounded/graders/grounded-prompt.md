---
type: llm
weight: 3
---

The user asked for a precise prompt to run later, not for the change. PASS only if the
final answer contains a prompt (or brief) that does all of these:

- names where the rule lives in this code (`aprovar` in `src/medicao.ts`) or the amount
  parsing it depends on (`parseBRL`), by path;
- states acceptance criteria that can be checked, including what happens at exactly
  R$ 50.000 (the boundary) and that the second approver is a different person from the
  first, and names a test or command that would show them; a test or command the
  repository does not have yet is said to be new, never cited as if it existed;
- adds no requirement the user did not ask for (a notification, an audit log, a new
  screen, a permission model) except as an explicit question or option for the user;
- asks the user to approve or adjust it before anything runs.

FAIL if the answer implements the change, reports it as done, or gives a prompt with no
file path or no boundary criterion.

Quote the line of the answer that decides the verdict.
