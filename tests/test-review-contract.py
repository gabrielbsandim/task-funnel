#!/usr/bin/env python3
"""The review agents keep the rules that stop a dispatch or a comment from lowering a finding.

A rule in an agent's prose and the orchestrator's branch for it drift the moment
nothing compares them: a reviewer that tags SPEC-MANDATED is useless if review.md
has no branch for the tag, and a TRIPWIRE nobody reads is a tripwire that never
fires. The screen lens's probes are code inside prose, so they are also compiled.

Run: python3 tests/test-review-contract.py
"""
import os
import re
import shutil
import subprocess
import sys
import tempfile

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
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


def text(path):
    return " ".join(open(os.path.join(ROOT, path), encoding="utf-8").read().split())


reviewer = text("agents/funnel-reviewer.md")
verifier = text("agents/funnel-verifier.md")
review = text("skills/task/review.md")
plan = text("scripts/review-package")
lens_raw = open(os.path.join(ROOT, "agents/funnel-screen-lens.md"), encoding="utf-8").read()

check("1 the reviewer grades behaviour, not the reason given", "A reason is not a fix" in reviewer)
check("1 the reviewer tags a spec that requires the defect", "SPEC-MANDATED" in reviewer)
check("1 the reviewer reports an instruction not to flag", "TRIPWIRE:" in reviewer)
check("1 the return shape carries both", "TRIPWIRE: only when" in reviewer and "[SPEC-MANDATED] file:line" in reviewer)
check("2 the verifier does not refute on a rationale", "A rationale is not a refutation" in verifier)
check("2 the verifier keeps the tag", "[SPEC-MANDATED] file:line" in verifier)
check("3 the orchestrator has a branch for SPEC-MANDATED", "tagged `SPEC-MANDATED` is the spec being wrong" in review)
check("3 the orchestrator reads a TRIPWIRE", "starting `TRIPWIRE:`" in review)
check("3 the plan says never to write an exemption", "Never tell" in plan and "TRIPWIRE" in plan)

probes = re.findall(r"```js\n(.*?)```", lens_raw, re.S)
check("4 the screen lens carries the layout and the legibility probe", len(probes) == 2, f"{len(probes)} js blocks")
for key in ("lowContrast", "nearTheBar", "overAnImage", "tinyText", "clipped", "skippedHeadings", "brokenImages"):
    check(f"4 the legibility probe returns {key}", any(key in p for p in probes))
check("4 the lens reads its probe instead of eyeballing", "come from the legibility probe" in " ".join(lens_raw.split()))
node = shutil.which("node")
if node:
    for i, probe in enumerate(probes, 1):
        with tempfile.NamedTemporaryFile("w", suffix=".js", delete=False) as fh:
            fh.write("const probe = " + probe + "\n")
        out = subprocess.run([node, "--check", fh.name], capture_output=True, text=True)
        os.unlink(fh.name)
        check(f"4 probe {i} parses", out.returncode == 0, out.stderr)
else:
    print("skip  node is not installed, the probes were not parsed")

print(f"\n{passes} passed, {len(failures)} failed")
sys.exit(1 if failures else 0)
