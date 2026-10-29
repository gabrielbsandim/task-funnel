---
type: llm
weight: 1
focus: last_message
---

The user asked for Critical and Important findings only.

PASS if every finding in the answer is presented as Critical or Important, or as
something that makes the change untrustworthy (wrong money, lost data, a test that
cannot fail, a pre-existing bug the change now depends on). Saying that something was
checked and found correct is not a finding.

FAIL if the answer includes any finding graded or framed as Minor, Low, Nit,
Suggestion or Optional, or any finding about style, naming, formatting, comments,
imports, the language of identifiers or a lint rule.

Quote the line of the answer that decides the verdict.
