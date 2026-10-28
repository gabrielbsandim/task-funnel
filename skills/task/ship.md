# Stages 5 and 6: ship and report

Read at the start of stage 5, after the last review round's fixes are committed. It
lives outside `SKILL.md` so that the skill stays under the 20,000 characters Claude
Code re-attaches after a compaction: past that point a skill is cut, and these two
stages were the part that fell off (`evidence.md` &middot; *A skill cut at
compaction*).

## Stage 5 · Ship

1. `kit gate ship`. Gates whose receipt already covers this exact tree are skipped and
   say so. The tree SHA includes untracked files, so any edit invalidates the receipt.
2. Push. The fix for a red pre-push hook is the failing check, never `--no-verify`.
3. Open the pull request exactly as the pipeline document says: base, draft state and
   issue reference are its decisions. Fill the repo's template honestly.

   **The body has a budget, and it is checked.** Write it to a file and run
   `kit pr-body <file>` before `gh pr create`: at most **2000 characters of prose** and
   **600 per section**, not counting the template, tables, checkboxes or fenced blocks.
   Cut, do not relocate (`evidence.md` &middot; *A body that competes with the diff*).

   The body carries, and nothing else: what changed and why, in the template's own
   sections; what to check; the findings table, one row per finding that reached the
   verifier, which costs no prose; what is knowingly left out and who owns it; and on
   its last line the lane marker, `<!-- funnel: direct -->`, `<!-- funnel: risk -->` or
   `<!-- funnel: trivial -->`, which is how `kit escapes` later tells the lanes apart.
   The `pr-body-gate` hook refuses a body from a task run that has none.

   There is no separate findings comment. The table is in the body, and a comment
   answering a person's question in review goes through `kit ledger`, which measures
   it on a comment's budget.
4. `kit board in_review --issue <issue>`, after the pull request URL exists.
5. Never `done`. The tracker's own automation owns that column.
6. `kit worktree gc --yes`, not `rm`. The pull request is open at exactly this head and
   everything is pushed, which is the definition of finished (`evidence.md` &middot;
   *The worktree leak*).

## Stage 6 · Report

**Six items, hard cap, at most 600 characters of prose in total.** Anything that does
not fit goes in the pull request body's budget or nowhere (`evidence.md` &middot; *Why
the budget is in characters*).

1. The pull request link, its draft state and base, the issue it closes, and the lane.
2. What changed, in one sentence naming the class of defect, not each instance.
3. Gates: the count that ran, failed and was skipped by receipt, and the tree SHA.
4. Review: rounds used of the lane's cap, findings by severity, how many the verifier
   refuted.
5. What was left out, and the issue that owns it. If this run created issues, the count
   and the parent each one hangs under.
6. What needs the user, or "nothing". On the risk lane, `/clear` before the next task.

Then `kit context`, and say the verdict in item 6 when it is anything but HOLD.

A gate that stopped the funnel replaces line 1 and is named without varnish. A number
with no command behind it is not a number. Never declare done without lines 3 and 4.

## How to know the funnel is paying

```
kit escapes                     # merged pull requests a later fix corrected, by lane and month
kit usage --all --by-stage      # what each stage cost, per run
kit eval-delta evals/results/*.json   # what the plugin changes against the bare model
```

The funnel's claim is fewer escapes on the risk lane than off the funnel, at a cost
per task the direct lane keeps close to working without it. Each escape `kit escapes`
finds becomes an eval case with `kit escapes --case <n> --out evals`, so the suite
grows from the defects that actually shipped (`evidence.md` &middot; *Measuring
escapes*).
