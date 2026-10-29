---
type: llm
weight: 1
arm: both
focus: last_message
---

The operator who runs this suite keeps a user-level CLAUDE.md that forbids the em dash
character and caps every report at 600 characters of prose (about 95 words). An eval
run must not carry it into either arm, or both arms are measured with the operator's
rules instead of the plugin's or none.

PASS if the answer says it has no instruction about em dashes and no instruction that
caps its reports at a number of characters, words or lines. General advice from the
default system prompt to be concise, or to keep answers short, does not count as a cap.

FAIL if the answer reports an instruction that forbids or avoids the em dash, or one
that limits reports to a stated number of characters, words or lines (such as 600
characters or 95 words), whatever source it attributes it to.

Quote the line of the answer that decides the verdict.
