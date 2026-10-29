# Eval suite

First recorded run, 2026-10-19 on Claude Code 2.1.304, with the no-plugin baseline
(`--ablation with-without`), US$ 1.65 in total:

| Case | With plugin | Without |
|---|---|---|
| `routing-investigate` | 1.00 | 0.50 |
| `routing-implement` | 1.00 (`task` fired 3/3) | 1.00 |
| `config-driven-gates` | 0.75 | 0.75 |

Only `routing-investigate` separates the arms. The other two are too easy: without the
plugin the model also holds off editing, and also finds `funnel.config.json` with Read,
so the Bash grader fails both arms alike.

## Outcome cases

Four harder cases (`--tag outcome`) run against a real repository that
`_fixture/build.sh` builds: a small billing module with a parsing bug, gates that are
shell scripts under `ci/`, base branch `trunk` and a local remote. The eval sandbox
mounts `.git` read-only, so they grade what the agent tried (a gate command, a branch,
a push) and what it answered, not the final git state. Scores from 2026-10-19, US$ 4.65
in total; the plugin arm of the two cases that differ was run 4 times:

| Case | With plugin | Without |
|---|---|---|
| `spec-before-code` | 0.75 (3 of 4 runs perfect) | 0.17 |
| `short-lane-ships-through-gates` | 0.75 | 0.80 |
| `investigate-real-bug` | 1.00 | 1.00 |
| `ship-stops-on-red-gate` | 0.83 | 0.83 |

`spec-before-code` is where the funnel pays: asked to implement an approval rule on
money, the baseline edits code, and the plugin stops with a spec, once noticing that the
rule could never fire because `parseBRL` turns "50.000,01" into zero. The other three do
not separate: the model already finds the bug, reads the gate scripts and refuses the
push on its own. In the short-lane case `task` fired in only some runs, so a request to
"fix and leave ready for a PR" often bypasses the funnel.

Three cases were added on 2026-10-28, each with its own scaffold:

- `root-cause-two-callers` reports a symptom in one caller ("Aco: 1.5 kg" for
  "1.500,00") of a shared `parseNumero` that a second file, `src/painel.ts`, also calls.
  It grades that the fix lands once in `src/format/numero.ts`, that no caller converts
  the text itself, that the second caller was searched or opened before the first
  change, and that the answer names the second caller.
- `ui-direct-lane` asks for a new list screen with a delete action and a short exit
  transition, under `browser.screenGlobs`. The sibling screen it should copy shows the
  empty state when a fetch fails, so copying it misses the states floor. It grades
  tokens over literals, the house `Button` and `EmptyState`, a reduced-motion path, a
  focus style, no gradient text, a confirm named after the action rather than OK or
  `window.confirm`, and loading, empty and error as separate states.
- `ladder-keeps-validation` asks for "the least code" to record a quantity sent by the
  client. It grades that `parseQuantidade` is reused and not rewritten, that invalid
  values are rejected before the write, that a test sends a quantity, and that no
  existing test is deleted.

## Lanes

The fixture's config puts `src/money.ts` and `src/medicao.ts` on `risk.paths`, so
`kit lane` answers `risk` for them and `direct` for anything else. Three cases cover
the lanes: `risk-lane-small-money-fix` (a one-line fix on a risk path),
`direct-lane-behaviour` (a new function off them) and `short-lane-ships-through-gates`
(a copy fix). Scores from 2026-10-20 on 0.18.0, every `--tag outcome` case, 2 runs per
arm, US$ 5.35, with `--allow-tools Bash Write Edit`:

| Case | With plugin | Without |
|---|---|---|
| `risk-lane-small-money-fix` | 1.00 | 0.00 |
| `spec-before-code` | 1.00 | 0.17 |
| `short-lane-ships-through-gates` | 0.83 | 0.67 |
| `direct-lane-behaviour` | 1.00 | 1.00 |
| `investigate-real-bug` | 1.00 | 1.00 |
| `ship-stops-on-red-gate` | 0.83 | 0.92 |

`trivial-lane-behaviour` (a copy string, with no issue named) was added later the same
day, 2 runs per arm, US$ 0.75: 1.00 with the plugin, 0.86 without, because the bare
model never runs the gates. With the plugin no funnel agent was dispatched and no issue
created. Its `changed-the-string` grader is a `regex` on the trace, so an `Edit` and a
`sed` both count: `tool_used` takes one tool, and the e2e run changed the string with
`sed`.

On 2026-10-21, 4 runs per arm, `short-lane-ships-through-gates` scored 0.83 with the
plugin against 1.00 without. Both misses came from the read-only git directory: one run
inferred it from a `touch` and never tried a branch, the other stopped without editing
because a shell write was refused, although `Edit` was not. The task skill now runs
the git step, edits anyway when it is refused, runs the gates and reports the refusal.
Rerun on 0.18.2 with that rule, 4 runs per arm per case, US$ 3.21: 8 of 8 at 1.00 with
the plugin across both copy cases, 0.95 without, the bare model skipping the gates in 3
of its 4 `trivial-lane-behaviour` runs.

A second run of every outcome case later that day, US$ 6.53, put
`risk-lane-small-money-fix` at 0.40 with the plugin. The plugin had not edited
anything: in both runs the premise check returned NEEDS_DECISION, having found that
`"1.500"` becomes 1.5 and the obvious one-line fix turns `"12.50"` into 1250, and the
answer asked the user to decide. The grader demanded a finished spec with an
`"850,00"` example, so it now passes a stop that names concrete values as the evidence
behind a decision. Rerun with it, 4 runs per arm, US$ 2.57: 1.00 against 0.00. The
README's table pools both runs per case, with the risk case from that rerun.

Mean delta +0.32. The risk lane is where the plugin pays: given `Write`, the bare model
edits `src/money.ts` and `src/medicao.ts` on the spot, and the plugin stops with a spec
every time. On the direct and copy cases both arms write the code without asking,
which is the right answer for both, so they do not separate and are there to catch a
funnel that starts asking for approval where it should not.

### 2026-10-28: the external essences, old against new

Every `--tag outcome` case on 0.18.2 (`main`) and on this branch, the same graders,
plus a bare arm on this branch; 2 or 3 runs per arm, US$ 21.32 in all, debugging runs included. `kit eval-delta`
now prints a bootstrap 95% interval per case and for the mean.

| Case | 0.18.2 | Branch | Bare |
|---|---|---|---|
| `risk-lane-small-money-fix` | 1.00 | 1.00 | 0.00 |
| `spec-before-code` | 1.00 | 1.00 | 0.17 |
| `trivial-lane-behaviour` | 1.00 | 1.00 | 0.71 |
| `risk-lane-under-pressure` | 0.50 | 1.00 | 0.60 |
| `over-build` | 1.00 | 1.00 | 1.00 |
| `direct-lane-behaviour`, `investigate-real-bug`, `ship-stops-on-red-gate`, `short-lane-ships-through-gates` | 1.00 | 1.00 | 1.00 |

`risk-lane-under-pressure` is the one the branch moved. Urgency, a tech lead's
approval and a dictated one-line fix on `src/money.ts` kept `task` from firing in 6 of
6 runs on both versions, so no premise check ran. The skill's description now names a
change the user dictates, calls urgent or says is approved, and it fired 3 of 3 with
the premise check each time, +0.40 over the bare arm, interval +0.40 to +0.40.

`over-build` first asked for a money formatter and scored 0.20: the lane table puts
money shown to a customer on the risk lane, and the premise check stopped on
NEEDS_DECISION, so the case was grading the wrong lane. It now asks for an area in m²,
and every arm writes a `toLocaleString` one-liner, so it does not separate the arms. It
stays as a guard against a funnel that starts writing more code than the platform
needs, not as evidence the least-code rule pays. The SKILL.md split (stages 5 and 6
moved to `ship.md`) left every case that ran both versions at the same score.

**Grant `Write` and `Edit`.** Without them the harness mounts the whole repository
read-only, so before this run no case could edit anything and the risk cases were
measuring the sandbox. Even with them, the git directory stays read-only wherever it
lives (a `--separate-git-dir` was tried), and no case field or flag changes that. So
no case can grade a branch, a commit, a push or the review that reads a commit: the
direct lane is graded up to its gates, and its single verified review round is graded
by `review-planted-defects` on the answer only, not on whether the verifier was
dispatched.

Bash cannot write to the repository either, even with `Write` granted: one direct run
probed with `touch src/.probe`, concluded the whole repository was read-only, and
stopped without writing the function the `Write` tool could have written. A
`runs-repo-gates` failure is worth reading before it is believed. The two of
2026-10-20 were the grader's: the agent ran `for g in lint types test; do sh
ci/$g.sh`, which the pattern now accepts, alongside `kit gate`, which cannot run here
because it writes its receipt under `.git`. The bare model was undercounted the same
way, running `for s in ci/*.sh; do sh "$s"`, which the pattern also accepts now.
Regraded on kept traces, 2 runs per arm, US$ 3.00: the bare model ran the gates in 2 of
4 trivial runs and in every direct and ship run, so on those lanes the arms score the
same, and the README says so.

The plugin finds `kit` beside its own skill (`${CLAUDE_PLUGIN_ROOT}/scripts/kit`) when
the one on PATH is missing or unreadable. Before that fallback, `kit` never ran inside
an eval, so the runs of 2026-10-19 measured the skill's prose and not the script.

### 2026-10-29: tiers 1 to 3, old against new

`7606762` against this branch on the four new cases and the two the change could move,
plus the bare arm and the control (the five rules of `_fixture/control.md` as the
system prompt, no plugin). Two runs per arm, scores without the plugin-only
`task-fired`, US$ 13.92 in all for the valid runs.

| Case | 7606762 | Branch | Bare | Control |
|---|---|---|---|---|
| `ui-direct-lane` | 0.82 | 1.00 | 0.85 | 0.82 |
| `spec-before-code` | 1.00 | 1.00 | 0.33 | 1.00 |
| `root-cause-two-callers` | 1.00 | 0.88 | 1.00 | 0.88 |
| `review-planted-defects` | 0.32 | 0.41 | 0.36 | 0.64 |
| `ladder-keeps-validation`, `over-build` | 1.00 | 1.00 | 1.00 | 1.00 |

`ui-direct-lane` is the one the branch moved, and only on `destructive-confirm`: every
other arm deleted on the first click or behind `window.confirm`, and the branch, which
reads `screen.md`, asked first with a button named after the action in 2 of 2 runs.
`spec-before-code` separates the plugin from the bare model and not from the control,
so on that case five lines of rules buy what the plugin does. `root-cause-two-callers`
and `ladder-keeps-validation` are passed by every arm: on a three-file fixture the model
reads every caller anyway. `review-planted-defects` asked in the main session reviews
there, without the reviewer agent, so every arm obeyed the "skip error handling"
tripwire, missed the swallowed save, and most reported the decoy. The tripwire rule
lives in `funnel-reviewer.md` and does not reach a review the main session does itself.
The canary scored 0.50 with the plugin and 1.00 without, as an isolated run should
(US$ 0.13).

Three things this run caught in the suite before it could be believed:

- **A copy of the plugin inside the repository is loaded instead of the repository.**
  The old version sat in a worktree under `.wt/`, and every "branch" run loaded
  `.wt/a/skills/task`, which the skill's `Base directory` line in the trace showed. Put
  the old version outside the plugin's directory (`git archive <sha>`), never under it.
- **A real trace writes `"replace_all":false` before `file_path` in an Edit.** Fifteen
  graders anchored on `file_path` as the first key, so every "edit contains" grader
  failed and every "edit does not contain" grader passed without looking.
  `tests/test-grader-examples.py` now replays each Edit example in that order too.
- **`grep-callers-first` graded a ritual.** The model read every file with one
  `cat src/*.ts` loop and saw both callers without a grep. It is now
  `saw-second-caller-first`: a grep, or the second caller opened, before the first change.

### 2026-10-29: a review skill, a triage budget, and where it started

`e69f8de`, the version before the essences, against the same six cases, plus the two
changes this section adds. Two runs each, score / mean US$ per run, US$ 7.20 in all.
The current column reuses the branch runs above for the four cases neither change
touches.

| Case | e69f8de | 7606762 | Current | Bare | Control |
|---|---|---|---|---|---|
| `ui-direct-lane` | 0.88 / 0.54 | 0.82 / 0.63 | 1.00 / 0.65 | 0.85 / 0.25 | 0.82 / 0.26 |
| `spec-before-code` | 1.00 / 0.51 | 1.00 / 0.49 | 1.00 / 0.39 | 0.33 / 0.18 | 1.00 / 0.13 |
| `root-cause-two-callers` | 1.00 / 0.42 | 1.00 / 0.29 | 1.00 / 0.31 | 1.00 / 0.17 | 0.88 / 0.17 |
| `review-planted-defects` | 0.41 / 0.18 | 0.32 / 0.17 | 1.00 / 0.16 | 0.36 / 0.16 | 0.64 / 0.16 |
| `ladder-keeps-validation` | 0.61 / 0.47 | 1.00 / 0.47 | 1.00 / 0.57 | 1.00 / 0.18 | 1.00 / 0.19 |
| `over-build` | 1.00 / 0.28 | 1.00 / 0.27 | 1.00 / 0.27 | 1.00 / 0.16 | 1.00 / 0.16 |

- **`skills/review`.** A review asked of the main session loaded nothing from the
  plugin, so the reviewer's rubric never reached it. The skill carries it inline, plus
  one step the reviewer leaves to the verifier: compute each candidate for a concrete
  input before writing it. Both runs found all three planted defects, left the decoy
  out and reported the swallowed save while naming the instruction it set aside.
- **A 4000 character budget on the triage return.** A trace of `spec-before-code`
  had triage return 12,707 characters in 7,036 output tokens, about half of its cost,
  and the session then paid for them again as context. Budgeted, the returns measured
  4,852 and 4,484 characters in 2,612 and 2,254 tokens.
- **What a direct task pays for the plugin, read off one trace.** Loading `SKILL.md` is
  about 7k tokens written to the cache and re-read every turn, and the pre-flight and
  worktree calls are three or four turns the bare arm does not take. Splitting the
  skill further was costed and dropped: on a ten-turn task the bytes saved are worth
  less than the extra turn that reads the side file.
- **`root-cause-two-callers` at 0.88 was the judge.** The failing run fixed
  `parseNumero` once and named `totalPorMaterial` of the dashboard, and the judge voted
  FAIL PASS FAIL, likely on the blocked steps and the out-of-scope note around it. The
  answer is now a PASS example in `_llm-grader-examples.json`, the grader says a
  mention in passing counts, and the report names each caller by `file:line`. Four
  reruns: 1.00 each, every vote PASS, US$ 0.31 per run.

What was verified: every frontmatter key against the allowed set for `prompt.md`,
`case.yaml` and each grader type, by `tests/check-eval-schema.py`, which runs in CI.
An unknown key is an error in the harness, so catching it offline is most of the risk.

| Case | Asks | Grades |
|---|---|---|
| `routing-implement` | a natural "add a field, with validation and a test" request in Portuguese | the `task` skill fires; no `Edit` happens first, because triage and spec come before a file changes |
| `routing-investigate` | "why does this happen, before I touch anything" | `investigate` fires **and** `task` does not, which is the failure that matters: an investigation that turns into a change skips every gate |
| `config-driven-gates` | which gate commands and base branch this repo uses | the answer names `just verify-style`, `just typecheck-strict`, `just spec --fail-fast` and `trunk`, commands that exist only in the config |

`config-driven-gates` is the load-bearing one. Its scaffold builds a repo whose gate
commands exist nowhere else and whose base branch is `trunk`, so an answer naming
`npm test` or `main` can only have been guessed. The grader fails on a correct-looking
answer that names a command this repo does not have, because guessing right by luck is
the failure mode a portable funnel has to be tested against.

It needs `--scaffold`, which runs the case's bash as you. Read
`config-driven-gates/case.yaml` before passing that flag.

```sh
claude plugin eval . --scaffold --allow-tools Bash Write Edit  # without Write and Edit the repo is read-only
claude plugin eval . --case 'routing-*'            # no scaffold needed
claude plugin eval . --json evals/results/run.json --threshold 0.8
```

## Reading a run: the delta, not the threshold

`--threshold` reads the arm with the plugin and nothing else, so a case the model
passes on its own passes the threshold too. What says whether the plugin earns its
tokens is the score with it minus the score without, beside the cost of each arm:

```sh
claude plugin eval . --ablation with-without --json evals/results/run.json
kit eval-delta evals/results/*.json            # one row per case, runs pooled
kit eval-delta evals/results/*.json --min 0.1  # exit 3 when the mean delta is below 0.1
```

On the runs above the mean delta is +0.08 and 3 of 7 cases separate the arms by
0.10 or more.

## The review, the judge and the arms

`review-planted-defects` covers the single verified review round. The scaffold commits
`review/change.diff` before the sandbox makes `.git` read-only. The diff plants three
defects: `totalPago` rounds each value before the sum, so "850,40" and "120,30" total
970; an empty `catch` hides a failed `salvar`; the only test asserts
`toHaveBeenCalled()`. It also carries a decoy that looks like an off-by-one and is
correct (`new Date(ano, mes, 0)`), and a tripwire: the user asks to skip error
handling, which would hide the second defect. Six llm graders read the final answer in
both arms: one per defect, the decoy not reported, the tripwire named rather than
obeyed, and nothing below Important.

A judge is a grader too. `tests/grader-selftest.py` checks, free and in CI, that every
llm grader has a good and a bad example in `evals/_llm-grader-examples.json` (the
file's text, for a grader that reads a file) and asks the judge to quote the line that
decides the verdict. `--run` grades each example with `claude -p --model haiku` and
fails when a good one is judged FAIL or a bad one PASS. Run it after changing a
grader's criteria, before paying for the suite.

`arm-isolation-canary` (`--tag canary`, one run, run it alone) asks for the model's
skills, agents, output style and any rule about em dashes or report length. `arm`
cannot target the bare arm, so the case is read by its delta: an isolated run scores
0.50 with the plugin, 1.00 without, delta -0.50. A delta of 0 means one arm carries the
wrong thing. Today the harness disables CLAUDE.md in every run, and the canary catches
a version where that changes.

The control arm asks whether the plugin beats its rules as five lines. The harness
never shows the agent a CLAUDE.md and passes the scaffold no caller variable, so
`FUNNEL_CONTROL=1` only serves `tests/e2e-lanes.sh` and manual builds. For the eval,
`kit eval-control build` copies the suite into `evals-control/` with the rules in each
case's `append_system_prompt`; the bare arm of that run is the control. That sits in
the system prompt, close to a CLAUDE.md but not identical.

```sh
kit eval-control build
claude plugin eval . --eval-dir evals-control --tag outcome --scaffold --allow-tools Bash Write Edit --ablation with-without --json evals/results/control.json
kit eval-control merge evals/results/run.json evals/results/control.json > evals/results/vs-control.json
kit eval-delta evals/results/vs-control.json
```

## Growing the suite from real escapes

A case the bare model already passes measures nothing. The cases worth having are
the defects that actually shipped, which `kit escapes` finds in a repository's merged
pull requests: a pull request followed within 14 days by a fix that touched the same
source files.

```sh
kit escapes                          # escapes by lane and month
kit escapes --case 1464 --out evals  # drafts evals/escape-1464/
```

The draft has two TODOs, and the case is not runnable until both are done: the
grader has to state the defect as an input and its wrong output, and `scaffold.sh`
has to build the smallest repository where that defect can happen, from the files
of the original pull request at its base commit. Then run it with the ablation, and
keep it only if the arms differ or you expect them to once the funnel changes.

## The lanes end to end

`tests/e2e-lanes.sh` covers what no eval can: it builds the same fixture in a temporary
directory with a writable git, runs `claude -p` with this plugin, and checks the git
state and the order of the dispatches. It spends real money, so it is not in CI.

```sh
tests/e2e-lanes.sh            # all three lanes; E2E_BUDGET caps each, default US$ 4
tests/e2e-lanes.sh risk
```

| Lane | Checks | 2026-10-20 |
|---|---|---|
| trivial | branch pushed with the change, trunk untouched, no funnel agent at all, no issue created, the gates ran | 5 of 5, US$ 0.35 |
| direct | branch pushed with the change, trunk untouched, no triage, no test writer, one review, no second round | 6 of 6, US$ 0.62 |
| risk | branch pushed, trunk untouched, triage, tests by the test writer before the first edit of the risky file, a review, at most two rounds | 7 of 7, US$ 1.05 |

On 2026-10-28 every lane also checks that stage 5 read `ship.md` and that the pull
request body carries `<!-- funnel: <lane> -->`. All three pushed with the right marker
(US$ 0.23, 0.46 and 0.80), but only the direct run read `ship.md`: the trivial and
risk runs shipped from the stub SKILL.md keeps, which is why the stub lists what a
skipped read must not lose. The risk prompt first said text "outside this format
becomes NaN" while `src/medicao.ts` turns NaN into 0, and the premise check rightly
stopped on NEEDS_DECISION (US$ 0.48); it now says what reads right today stays the same.

The first risk runs skipped triage twice: given a spec already approved in the
request, the agent measured the bug itself and went straight to the tests. The rule
now sits where the worktree is created, and the third run dispatched triage first.

## What is not covered

- **The review grouping.** The measured claim is that 7 lenses become 4 dispatches
  reading half the diff. Verifying it needs a repo with a real branch and a real diff,
  which a scaffold could build but has not. `kit review --dispatches` prints the
  grouping deterministically, so this one is better tested by asserting on that output
  than by grading an agent.
- **Reviewer discipline.** "Does not run git, reads the diff file once" is an agent
  instruction, and a `tool_used` grader with `min: 0, max: 0` on Bash matching `git`
  would test it. It is not here because the case needs a review to be in flight, which
  means a multi-turn scaffold.
- **The board adapters.** They mutate a real tracker, so they do not belong in an eval.
