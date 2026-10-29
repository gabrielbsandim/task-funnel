---
type: llm
weight: 2
focus: {source: file, path: src/app/medicoes/page.tsx}
---

Deleting a measurement cannot be undone, so the repository's rule is that a
destructive action asks first, and the button that confirms names what it does (for
example "Excluir medicao"), never OK, Yes, Sim, Submit, Confirm or Confirmar alone.
`window.confirm` fails the rule, because its button is the browser's OK.

PASS only if the delete asks the user before calling `excluirMedicao`, and the
control that confirms the deletion is labelled with the action (a verb such as
Excluir or Remover, alone or with the object).

FAIL if the delete calls `excluirMedicao` on the first click with no confirmation,
uses `window.confirm` or `confirm(`, or labels the confirming control with a generic
word such as OK, Sim, Confirmar or Submit. Quote the line of the file that decides
the verdict.
