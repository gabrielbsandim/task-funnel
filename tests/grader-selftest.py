#!/usr/bin/env python3
"""Every llm eval grader passes a good final answer and fails a bad one.

Without --run, free and in CI: each `llm` grader under evals/ has at least one answer
marked pass and one marked fail in evals/_llm-grader-examples.json, keyed like
_grader-examples.json, and its criteria end by asking the judge to quote the line that
decides the verdict. A grader that reads a file keys its examples by that file's text. With --run, which spends money: every example is graded by
`claude -p --model haiku`, the harness's default judge, against that grader's
criteria, and a good answer has to PASS and a bad one FAIL.

Run: python3 tests/grader-selftest.py [--run] [--model M] [--only TEXT]
"""
import glob
import json
import os
import re
import subprocess
import sys
import tempfile
from concurrent.futures import ThreadPoolExecutor

try:
    import yaml
except ImportError:
    print("pyyaml is not installed, llm grader self-test skipped")
    sys.exit(0)

ROOT = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "evals")
CLOSING = "Quote the line of the {} that decides the verdict."
JUDGE = """You are grading the final answer of an AI coding agent against a rubric.

<rubric>
{criteria}
</rubric>

<answer>
{answer}
</answer>

Apply the rubric to the answer. End with one line that is exactly VERDICT: PASS or VERDICT: FAIL."""
failures = []
passes = 0


def check(name, ok, detail=""):
    global passes
    if ok:
        passes += 1
        return
    failures.append(name)
    print(f"FAIL  {name}  {detail}")


def grader(path):
    match = re.match(r"^---\n(.*?)\n---\n?(.*)$", open(path, encoding="utf8").read(), re.S)
    if not match:
        return {}, ""
    config = yaml.safe_load(match.group(1)) or {}
    return config, (config.get("criteria") or match.group(2)).strip()


with open(os.path.join(ROOT, "_llm-grader-examples.json"), encoding="utf8") as handle:
    examples = json.load(handle)


def examples_for(name):
    value = examples.get(name)
    return examples_for(value) if isinstance(value, str) else value


graders, used = [], set()
for path in sorted(glob.glob(os.path.join(ROOT, "*", "graders", "*.md"))):
    config, criteria = grader(path)
    if config.get("type") != "llm":
        continue
    label = os.path.relpath(path, ROOT)[: -len(".md")]
    name = os.path.basename(label)
    key = label.replace(f"{os.sep}graders{os.sep}", "/")
    key = key if key in examples else name
    used.add(key)
    cases = examples_for(key) or []
    closing = CLOSING.format("answer" if config.get("focus", "last_message") == "last_message" else "file")
    check(f"{label} ends by asking for the deciding line", " ".join(criteria.split()).endswith(closing),
          f"the last sentence should be: {closing}")
    if not cases:
        check(f"{label} has examples", False, "no entry in _llm-grader-examples.json")
        continue
    check(f"{label} has an answer that passes", any(e.get("pass") is True for e in cases), "only failing answers")
    check(f"{label} has an answer that fails", any(e.get("pass") is False for e in cases), "only passing answers")
    for example in cases:
        check(f"{label}: {example.get('why')} has an answer", bool((example.get("answer") or "").strip()))
        graders.append((label, criteria, example))

reached = set(used)
for key in used:
    while isinstance(examples.get(key), str):
        key = examples[key]
        reached.add(key)
for key in sorted(set(examples) - reached):
    check(f"_llm-grader-examples.json: {key} belongs to an llm grader", False, "no llm grader has this name")


def judge(model, criteria, answer):
    env = dict(os.environ, CLAUDE_CODE_DISABLE_CLAUDE_MDS="1")
    with tempfile.TemporaryDirectory() as cwd:
        out = subprocess.run(
            ["claude", "-p", "--model", model, "--output-format", "json", "--max-turns", "1", "--tools", "",
             "--setting-sources", "project", "--strict-mcp-config", "--no-session-persistence"],
            input=JUDGE.format(criteria=criteria, answer=answer), capture_output=True, text=True,
            cwd=cwd, env=env, timeout=300)
    if out.returncode != 0:
        return None, 0.0, (out.stderr or out.stdout).strip()[-200:]
    data = json.loads(out.stdout)
    verdicts = re.findall(r"VERDICT:\s*(PASS|FAIL)", data.get("result") or "")
    return (verdicts[-1] == "PASS" if verdicts else None), data.get("total_cost_usd") or 0.0, ""


def run(model, only):
    picked = [g for g in graders if only in g[0]]
    with ThreadPoolExecutor(max_workers=4) as pool:
        results = list(pool.map(lambda g: judge(model, g[1], g[2]["answer"]), picked))
    cost = 0.0
    print(f"\n{'grader':<56} {'example':<44} {'want':>4} {'got':>5}")
    for (label, _, example), (got, usd, err) in zip(picked, results):
        cost += usd
        want = "PASS" if example["pass"] else "FAIL"
        shown = {True: "PASS", False: "FAIL", None: "none"}[got]
        print(f"{label:<56} {example['why'][:44]:<44} {want:>4} {shown:>5}")
        check(f"judge on {label}: {example['why']}", got is example["pass"], err or f"judged {shown}, want {want}")
    print(f"\n{len(picked)} answer(s) judged by {model}, US$ {cost:.4f}")


if "--run" in sys.argv:
    model = sys.argv[sys.argv.index("--model") + 1] if "--model" in sys.argv else "haiku"
    run(model, sys.argv[sys.argv.index("--only") + 1] if "--only" in sys.argv else "")

print(f"\n{passes} passed, {len(failures)} failed")
sys.exit(1 if failures else 0)
