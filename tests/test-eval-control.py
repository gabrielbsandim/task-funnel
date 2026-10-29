#!/usr/bin/env python3
"""Proves the control arm reaches the agent by the one door the eval harness leaves open.

The harness runs every agent with CLAUDE_CODE_DISABLE_CLAUDE_MDS=1 and the scaffold with
no caller variable, so the fixture's CLAUDE.md alone would be read by nobody. This
checks the fixture writes it on FUNNEL_CONTROL=1 or the marker, that `eval-control
build` puts the same five lines in every case's append_system_prompt, and that `merge`
pairs the plugin arm with the control arm for eval-delta.

    python3 tests/test-eval-control.py
"""
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile

PLUGIN = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SCRIPT = os.path.join(PLUGIN, "scripts", "eval-control")
RULES = open(os.path.join(PLUGIN, "evals", "_fixture", "control.md"), encoding="utf8").read()
PASS, FAIL = 0, []


def check(name, ok, detail=""):
    global PASS
    if ok:
        PASS += 1
        return
    FAIL.append(name)
    print(f"FAIL  {name}  {detail}")


def fixture(build, env=None):
    work = tempfile.mkdtemp()
    repo = os.path.join(work, "repo")
    os.mkdir(repo)
    out = subprocess.run(["bash", build], cwd=repo, capture_output=True, text=True,
                         env=dict(os.environ, **(env or {})))
    claude_md = os.path.join(repo, "CLAUDE.md")
    text = open(claude_md, encoding="utf8").read() if os.path.exists(claude_md) else None
    shutil.rmtree(work)
    return out.returncode, text


def appended(prompt):
    head = re.match(r"\A---\n(.*?\n)---\n", open(prompt, encoding="utf8").read(), re.S).group(1)
    line = re.search(r"^append_system_prompt: (.*)$", head, re.M)
    return json.loads(line.group(1)) if line else None


def run_file(cases):
    fh = tempfile.NamedTemporaryFile("w", suffix=".json", delete=False)
    json.dump({"cases": [{"name": n, "arms": {"with": [{"score": w, "costUsd": 0.2, "error": None}],
                                                "without": [{"score": wo, "costUsd": 0.1, "error": None}]}}
                         for n, w, wo in cases]}, fh)
    fh.close()
    return fh.name


check("RULES is five lines", len(RULES.strip().splitlines()) == 5, RULES)
build = os.path.join(PLUGIN, "evals", "_fixture", "build.sh")
code, text = fixture(build)
check("the plain fixture has no CLAUDE.md", code == 0 and text is None, f"exit {code}")
code, text = fixture(build, {"FUNNEL_CONTROL": "1"})
check("FUNNEL_CONTROL=1 writes the five lines as CLAUDE.md", code == 0 and text == RULES, f"exit {code}")

root = tempfile.mkdtemp()
try:
    shutil.copytree(os.path.join(PLUGIN, "evals"), os.path.join(root, "evals"),
                    ignore=shutil.ignore_patterns("results"))
    os.makedirs(os.path.join(root, "evals", "results"))
    out = subprocess.run([SCRIPT, "build", "--root", root], capture_output=True, text=True)
    check("build succeeds", out.returncode == 0, out.stderr)
    check("build prints the command to run", "--eval-dir evals-control" in out.stdout, out.stdout)
    copy = os.path.join(root, "evals-control")
    cases = [c for c in os.listdir(copy) if not c.startswith("_") and os.path.isdir(os.path.join(copy, c))]
    check("every case was copied", cases and all(os.path.exists(os.path.join(copy, c, "prompt.md")) for c in cases))
    check("results are not copied", not os.path.exists(os.path.join(copy, "results")))
    bad = [c for c in cases if appended(os.path.join(copy, c, "prompt.md")) != RULES.strip()]
    check("every copied prompt carries the five rules", not bad, f"missing in {bad}")
    original = os.path.join(root, "evals", cases[0], "prompt.md")
    check("the source suite is untouched", appended(original) is None)
    code, text = fixture(os.path.join(copy, "_fixture", "build.sh"))
    check("the copy's fixture writes CLAUDE.md through the marker", code == 0 and text == RULES, f"exit {code}")
    text = open(original, encoding="utf8").read()
    with open(original, "w", encoding="utf8") as fh:
        fh.write(text.replace("\n---\n", "\nappend_system_prompt: \"x\"\n---\n", 1))
    out = subprocess.run([SCRIPT, "build", "--root", root], capture_output=True, text=True)
    check("a case that already appends a prompt is refused", out.returncode == 1 and cases[0] in out.stderr,
          out.stderr)
finally:
    shutil.rmtree(root)

plugin = run_file([("spec", 1.0, 0.2), ("gates", 1.0, 0.5)])
control = run_file([("spec", 0.9, 0.6)])
out = subprocess.run([SCRIPT, "merge", plugin, control], capture_output=True, text=True)
merged = json.loads(out.stdout) if out.returncode == 0 else {"cases": []}
spec = next((c for c in merged["cases"] if c["name"] == "spec"), {})
check("merge keeps the plugin's with arm", [r["score"] for r in spec.get("arms", {}).get("with", [])] == [1.0], out.stdout)
check("merge takes the control's without arm", [r["score"] for r in spec.get("arms", {}).get("without", [])] == [0.6],
      out.stdout)
paired = tempfile.NamedTemporaryFile("w", suffix=".json", delete=False)
paired.write(out.stdout)
paired.close()
delta = subprocess.run([os.path.join(PLUGIN, "scripts", "eval-delta"), paired.name], capture_output=True, text=True)
row = next((l for l in delta.stdout.splitlines() if l.startswith("spec")), "")
check("eval-delta reads the pair as plugin minus control", "+0.40" in row, delta.stdout + delta.stderr)
check("a case the control never ran shows no delta", any(l.startswith("gates") and "n/a" in l
                                                        for l in delta.stdout.splitlines()), delta.stdout)
for path in (plugin, control, paired.name):
    os.unlink(path)

print(f"\n{PASS} passed, {len(FAIL)} failed")
sys.exit(1 if FAIL else 0)
