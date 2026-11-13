# Handoff: <topic>

Only for work another session has to finish. Save it as `handoff.md` in the topic
folder under `$CLAUDE_WIP`, next to the spec or plan it continues.

- Objective and acceptance: the outcome asked for, and the check that proves it
- State checked: date, branch, head sha, uncommitted files (never assume a clean tree)
- Done: the changes and where they live
- Evidence: each command run, its result and when; a check never run says "not run"
- Remaining: the smallest next action, what it depends on, the known risks
- Blockers: the cause, what waits on it, and what unblocks it
- Live resources: worktrees, processes, ports and databases still held, and their cleanup
- Revisit: sources or assumptions that may have changed since

A handoff is context, not proof. The session that picks it up checks the files, git
state, gates and live resources before acting on any claim in it. No secrets,
payloads or full logs.
