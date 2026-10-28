#!/usr/bin/env python3
"""Every SKILL.md stays under what Claude Code re-attaches after a compaction.

After a compaction each invoked skill comes back cut at 20,000 characters, and what
falls past the cut is gone for the rest of the session. The task skill was 24,059
characters, so the cut landed inside stage 4 and stages 5 and 6 were lost in exactly
the sessions that compact most. Bytes are counted, which is never fewer than
characters, so a pass here is a pass under either unit.

The second half checks that what moved out is still reachable: each reference file
the task skill tells the session to read exists, and still carries the rules the
stub promises it holds.

Run: python3 tests/test-skill-size.py
"""
import glob
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
LIMIT = 20_000
failures = []
passes = 0


def check(name, ok, detail=""):
    global passes
    if ok:
        passes += 1
        print(f"ok    {name}")
        return
    failures.append(name)
    print(f"FAIL  {name}  {detail}")


for path in sorted(glob.glob(os.path.join(ROOT, "skills", "*", "SKILL.md"))):
    size = os.path.getsize(path)
    name = os.path.relpath(path, ROOT)
    check(f"1 {name} is under {LIMIT} bytes", size < LIMIT, f"{size} bytes, cut at {LIMIT}")

task_dir = os.path.join(ROOT, "skills", "task")
skill = open(os.path.join(task_dir, "SKILL.md"), encoding="utf-8").read()
for ref in ("review.md", "ship.md", "evidence.md"):
    check(f"2 SKILL.md names {ref}", f"`{ref}`" in skill, "the pointer is gone")
    check(f"2 {ref} exists", os.path.isfile(os.path.join(task_dir, ref)), "the file is gone")

check("3 stage 5 tells the session to read ship.md",
      "Read `ship.md` in this skill's directory now" in skill, "the read instruction is gone")
ship = open(os.path.join(task_dir, "ship.md"), encoding="utf-8").read()
for literal in ("## Stage 5", "## Stage 6", "kit gate ship", "kit pr-body", "<!-- funnel: risk -->",
                "kit board in_review", "kit worktree gc --yes", "kit context", "600 characters"):
    check(f"3 ship.md keeps {literal!r}", literal in ship, "a rule fell out in the move")

print(f"\n{passes} passed, {len(failures)} failed")
sys.exit(1 if failures else 0)
