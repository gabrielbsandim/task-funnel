# task, a screen at creation time

Read this before writing any file under `.browser.screenGlobs`, on every lane. The
browser lens reads a screen after it exists, and only on the risk lane; this is what
the screen should already be when it gets there (`evidence.md` &middot; *A screen at
creation time*).

## Before the first line: what the repo already decided

1. **The sibling screen.** Open the nearest existing screen of the same kind (a list
   next to a list, a form next to a form) and copy its structure: layout, how it
   fetches, how it shows loading and errors, which components it uses.
2. **The house components.** A `Button`, `EmptyState`, `Dialog` or table the repo
   already has is used, never re-drawn. A new screen that builds its own button is two
   buttons the next change has to keep in step.
3. **The tokens.** Colors, spacing, radius, type and motion come from the repo's
   tokens (`var(--...)`, the theme object, the Tailwind config). A literal that
   matches a token is the token; a literal close to one is a bug.

The spec's SCREEN line names all three with their real values. When none exists,
say so in it, and use the platform's defaults rather than inventing a system.

## The states floor

Every interactive element has default, hover, focus, active and disabled; every
screen that loads data has loading, empty and error. Ship none of them half-done.

- **Loading** keeps the layout: a skeleton or the house loader, not a page that jumps.
- **Empty** says which kind it is, because each needs a different answer: first use
  (what will be here and the action that starts it), cleared by the user (how to
  recreate), no results (which filter to clear), no permission (why, and who grants
  it), failed to load (that is the error state).
- **Error** names the problem and the recovery, keeps what the user typed, and
  offers a retry when the failure can be transient.
- **Disabled** says why when the reason is not obvious from the screen.

## Harden what the user can break

- Long text: a 100-character name, an unbroken string. `min-width: 0` on flex
  children that hold text, and a wrap or truncate decision per field.
- Double submit: the action disables or ignores a second click while in flight.
- A destructive action asks, and the confirm button names what it does ("Excluir
  medição"), never OK, Yes, Submit or Confirm alone.
- Every control is reachable and visible by keyboard: a `:focus-visible` style
  whenever the default outline is removed, a label on every input and icon button.
- Motion conveys a state change, 150 to 250 ms, and every transition or animation
  has a `prefers-reduced-motion` path.

## Refuse

Gradient text, a colored border thicker than 1px on one side of a card or alert,
nested cards, a modal where an inline edit works, a font size below 12px, an `<img>`
without `alt`. Each is a default a model reaches for, not a decision.

## Then check it

`kit design` scans the lines this branch added under the screen globs for what a
static read can catch: gradient text, side stripes, bounce easing, tiny text, tight
leading, literals off the tokens, images without alt, outlines removed without a
focus style, motion without a reduced-motion path. A finding is fixed, or silenced
on its line with `design-ignore: <rule> who decided: <evidence>`; adding a token to
make a literal pass is the same finding.
