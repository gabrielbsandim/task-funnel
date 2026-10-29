---
type: llm
weight: 2
focus: {source: file, path: src/app/medicoes/page.tsx}
---

This is a new list screen that loads measurements with `listarMedicoes()` and
deletes one with `excluirMedicao(id)`. The repository's rule for a screen that loads
data is the states floor: loading, empty and error are each built, and a failed load
is the error state, not the empty one. The sibling screen in this repository turns a
failed fetch into an empty list, which is the defect the rule exists to stop.

PASS only if the file does all of these:

- renders a loading state while the list is being fetched;
- renders an empty state when the list comes back with no items;
- renders an error state, distinct from the empty state, when `listarMedicoes()`
  rejects, with a way to try again or a message that names the failure;
- while a delete is in flight, the delete control for that row is disabled or ignores
  a second click, and a failed delete is shown to the user rather than swallowed.

FAIL if a failed load shows the empty state or nothing, if any of the three load
states is missing, or if the delete can be fired twice for the same row. Quote the
line of the file that decides the verdict.
