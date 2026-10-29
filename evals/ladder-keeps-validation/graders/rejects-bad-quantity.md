---
type: llm
weight: 3
focus: {source: file, path: src/handlers/diario.ts}
---

`registrarPresenca` is a handler: `req.body.quantidade` comes from a client and is
untrusted. The repository already has `parseQuantidade` in `src/format/quantidade.ts`,
which returns `undefined` for anything that is not an integer of at least 1. Asking for
"the least code" never cuts validation at a trust boundary.

PASS only if, before `gravarPresenca` is called, the handler rejects with an error
response (such as `badRequest`) a quantity that is negative, zero, not a number (such
as "abc") or not an integer (such as 2.5), by calling `parseQuantidade` or by an
equivalent check. Treating a missing quantity as 1 is acceptable; treating an invalid
one as 1 is not.

FAIL if any of those values can reach `gravarPresenca`, if an invalid value is
silently replaced by a default, or if the quantity is passed through `Number(...)`
or a cast with no check. Quote the line of the file that decides the verdict.
