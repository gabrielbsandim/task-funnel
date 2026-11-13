# task-funnel

[![Version](https://img.shields.io/badge/Version-v0.21.0-blue.svg)](https://github.com/gabrielbsandim/task-funnel/releases)
[![Platform](https://img.shields.io/badge/Supported%20By-Claude%20Code%20%7C%20Antigravity-6B46C1.svg)]()
[![License: MIT](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)

**Give Claude Code or Antigravity a task. Get back a verified pull request you can trust.**

A delivery funnel plugin that turns `"fix this"` or an issue number into an isolated git worktree branch, runs your real project checks (lint, types, tests), subjects the code to an adversarial review whose findings must survive refutation, and opens a clean draft PR while advancing your project board.

When a change touches critical paths (money, permissions, multi-tenancy, database schemas), **task-funnel stops for your explicit approval on the specification before a single line of production code is written.**

```bash
/task-funnel:task 575
```

---

## How It Works: Dynamic Risk Lanes

Rather than treating every task with the same heavy ceremony or letting agents run wild on sensitive code, `task-funnel` classifies work into three lanes based on your repository's configured `risk.paths`:

```
                    ┌────────────────────────┐
                    │ Issue / Task / Prompt  │
                    └───────────┬────────────┘
                                │
                        [Risk Evaluator]
                                │
        ┌───────────────────────┼───────────────────────┐
        ▼                       ▼                       ▼
  [Trivial Lane]          [Direct Lane]            [Risk Lane]
(Copy, typos, docs)     (Standard features)   (Money, auth, schema)
        │                       │                       │
   Direct Edit             Short Spec              Premise Check
        │                       │                       │
   Your Checks             Implementation        ╔═════════════════════╗
        │                       │                ║ STOP FOR APPROVAL   ║
        │                  Your Checks           ║ (Spec & Plan)       ║
        │                       │                ╚══════════┬══════════╝
        │                 1-Round Review                    │
        │                 (Refutation gate)            Tests First
        │                       │                           │
        │                       │                     Implementation
        │                       │                           │
        │                       │                      Your Checks
        │                       │                           │
        │                       │                   5-Lens Review
        │                       │                   (2 Refutation rounds)
        └───────────────────────┼───────────────────────────┘
                                ▼
               ┌─────────────────────────────────┐
               │ Isolated Git Worktree Branch    │
               │ Passes All Gates & Tests        │
               │ Board Updated + Draft PR Opened │
               └─────────────────────────────────┘
```

| Lane | Best For | Verification Pipeline |
| :--- | :--- | :--- |
| **`trivial`** | Typos, copy strings, documentation, config tweaks | Code edit → Runs repo checks → Pushes branch & draft PR. |
| **`direct`** | Standard features, helpers, routine bugfixes | Short spec → Code edit → Runs repo checks → 1-round refutation review → Draft PR. |
| **`risk`** | Payments, permissions, tenancy, migrations, shared APIs | Premise verification → Spec written & **waits for human approval** → Tests written first → Code edit → 5-lens adversarial review (up to 2 refutation rounds) → Draft PR. |

---

## Measured Performance: Why Use It?

Measured per lane across identical models, prompts, and codebases using `claude plugin eval --ablation with-without`:

| Task Category | Bare Claude Code | With task-funnel |
| :--- | :--- | :--- |
| **Trivial Task** (copy fix) | Skips repo checks in 3 of 8 runs (**0.95**) | Runs checks every time, 8 of 8 (**1.00**)<br>*(+$0.12, +13s)* |
| **Simple Task** (helper function) | Writes code, passes (**1.00**) | Writes code, runs checks, adds verified review (**1.00**)<br>*(+$0.12, -1s)* |
| **Risky Task** (payment/rule fix) | Edits code without checks: **0.08** accuracy | Checks premise, stops for human spec approval: **1.00** accuracy<br>*(+$0.33, +63s)* |

### Key Guarantees

1. **Worktree Isolation:** Work always runs in an independent git worktree (`.claude/worktrees/`). Your current checkout is never altered or dirtied.
2. **Refutation Review:** Every review finding is assigned to an independent agent instructed to refute the finding. Only bugs that reliably reproduce are allowed to trigger a fix cycle.
3. **Budget & Loop Caps:** Review loops are strictly capped. A test suite never runs twice on identical code hashes (saving up to 359s per push).
4. **Predictable Autonomy:** Stops only where human judgment is strictly necessary: approving the spec for high-risk logic, splitting tasks exceeding PR scope, and final PR review.

---

## Installation

### Claude Code

```bash
claude plugin marketplace add gabrielbsandim/task-funnel
claude plugin install task-funnel@task-funnel
/task-funnel:setup
```

### Antigravity

```bash
git clone https://github.com/gabrielbsandim/task-funnel.git
./task-funnel/scripts/kit setup
```

`kit setup` symlinks `kit` onto your `PATH` and installs the Antigravity bundle under `~/.gemini/config/plugins/task-funnel`.

> **Prerequisites:** Linux or macOS, `git`, `jq`, `python3`, and `gh` (GitHub CLI authenticated).

---

## Slash Commands

| Command | Purpose |
| :--- | :--- |
| `/task-funnel:task <id\|prompt>` | Full delivery pipeline: spec, tests, code, review, and draft PR. |
| `/task-funnel:investigate <query>` | Read-only codebase diagnosis. Delivers verified evidence with zero edits. |
| `/task-funnel:ship` | Packages committed branch work through review into a clean draft PR. |
| `/task-funnel:review` | Runs an adversarial, refutation-backed review against any external diff, branch, or PR. |
| `/task-funnel:backlog` | Grooms your open board: groups related issues, links epics, suggests release batches. |
| `/task-funnel:note <text>` | Captures durable architectural facts into a local Markdown knowledge vault. |

---

## Repository Configuration

`task-funnel` adapts to any language or stack via a single root configuration file: `.claude/funnel.config.json`.

```bash
kit config init      # Generates a starting template tailored to your repo
kit config check     # Validates commands, branch references, and paths
```

Example configuration excerpt:

```json
{
  "gates": {
    "test": "pnpm test",
    "lint": "pnpm lint",
    "typecheck": "pnpm typecheck"
  },
  "risk": {
    "paths": ["src/billing/**", "src/auth/**", "prisma/schema.prisma"]
  }
}
```

---

## Privacy & Security

- **Zero Telemetry:** No analytics or external event tracking.
- **Direct Remotes:** Branches and pull requests interact exclusively with your configured git remote and GitHub API using your local `gh` credentials.
- See [`docs/reference.md#what-it-runs-writes-and-sends`](docs/reference.md#what-it-runs-writes-and-sends) for a complete audit of executed commands and filesystem access.

---

## Documentation

- [`docs/reference.md`](docs/reference.md): Comprehensive guide: CLI usage, browser testing, board integrations (GitHub Projects, Jira, Azure DevOps), and agent models.
- [`evals/README.md`](evals/README.md): Benchmark methodology and steps to reproduce ablation studies.

---

## License

[MIT](LICENSE) © Gabriel Sandim
