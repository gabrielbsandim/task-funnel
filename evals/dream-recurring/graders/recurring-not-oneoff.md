---
type: llm
weight: 3
---

Three sessions are in ./sessions. In two of them (`a1f0-checkout`, `c9d4-reembolso`)
the user corrected `npm test` to `pnpm test`, and CLAUDE.md still says `npm test`. In one
(`b2c7-frete`) the user skipped an integration test for one day because a sandbox was
down. PASS only if the final answer does all of these:

- proposes changing the existing `npm test` line in CLAUDE.md to `pnpm test` (or
  replacing it), rather than adding a second, separate rule beside it;
- backs that proposal with both sessions, by name or id;
- does not propose a standing rule from the one-day sandbox outage;
- asks the user which change to apply, and has not applied it.

FAIL if CLAUDE.md is reported as already edited, or if the outage becomes a rule.

Quote the line of the answer that decides the verdict.
