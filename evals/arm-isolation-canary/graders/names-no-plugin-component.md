---
type: regex
weight: 1
arm: both
target: last_message
match: not_contains
flags: i
pattern: 'task-funnel|\bfunnel-(?:triage|test-writer|reviewer|verifier|screen-lens)\b|kit-terse'
---
