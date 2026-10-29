---
type: llm
weight: 2
focus: last_message
---

Planted defect 3, a test that cannot fail. The only test in `src/fechamento.test.ts`
asserts `expect(salvar).toHaveBeenCalled()`, never the value saved, so it passes with
any total, including the wrong 970 the rounding produces for "850,40" and "120,30".

PASS if the answer reports that the test only checks that the mock was called and not
what it was called with (the total, or the closing), so it does not protect the
behaviour. FAIL if the test is not mentioned as a defect, or is mentioned only as
missing coverage of some other case without saying it asserts nothing about the value.

Quote the line of the answer that decides the verdict.
