#!/usr/bin/env python3
"""Every deterministic eval grader passes its good examples and fails its bad ones.

A grader is code, and until this file nothing ran it except a paid eval. The
2026-10-20 runs undercounted both arms because `runs-repo-gates` did not accept the
gate loops the agents actually wrote, and that was found by reading traces after the
money was spent. `evals/_grader-examples.json` holds tool calls keyed by grader name,
each marked pass or fail, and this replays them through every `tool_used` and
`regex` grader of that name the way the harness does: a tool call's input is JSON,
`input_match` searches it, and a `trace` regex searches the serialized calls.

A deterministic grader with no example that passes and none that fails is itself a
failure, because a grader nobody has seen fail is a grader nobody knows can.

Run: python3 tests/test-grader-examples.py
"""
import glob
import json
import os
import re
import sys

try:
    import yaml
except ImportError:
    print("pyyaml is not installed, grader examples skipped")
    sys.exit(0)

ROOT = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "evals")
failures = []
passes = 0


def check(name, ok, detail=""):
    global passes
    if ok:
        passes += 1
        return
    failures.append(name)
    print(f"FAIL  {name}  {detail}")


def frontmatter(path):
    match = re.match(r"^---\n(.*?)\n---", open(path, encoding="utf8").read(), re.S)
    return (yaml.safe_load(match.group(1)) or {}) if match else {}


def serialize(tool, data):
    return json.dumps(data, separators=(",", ":"), ensure_ascii=False)


def trace_of(calls):
    return "\n".join(json.dumps({"type": "tool_use", "id": f"toolu_{i}", "name": tool, "input": data},
                                separators=(",", ":"), ensure_ascii=False)
                     for i, (tool, data) in enumerate(calls))


def grade(config, calls):
    kind = config["type"]
    if kind == "tool_used":
        pattern = config.get("input_match")
        count = sum(1 for tool, data in calls if tool == config["tool"]
                    and (pattern is None or re.search(pattern, serialize(tool, data))))
        high = config.get("max")
        return count >= config.get("min", 1) and (high is None or count <= high)
    found = re.search(config["pattern"], trace_of(calls), re.I if "i" in (config.get("flags") or "") else 0)
    return bool(found) == (config.get("match", "contains") != "not_contains")


with open(os.path.join(ROOT, "_grader-examples.json"), encoding="utf8") as handle:
    examples = json.load(handle)


def examples_for(name):
    value = examples.get(name)
    return examples_for(value) if isinstance(value, str) else value


for path in sorted(glob.glob(os.path.join(ROOT, "*", "graders", "*.md"))):
    config = frontmatter(path)
    if config.get("type") not in ("tool_used", "regex"):
        continue
    label = os.path.relpath(path, ROOT)
    name = os.path.basename(path)[: -len(".md")]
    case = path.split(os.sep)[-3]
    cases = examples_for(f"{case}/{name}") or examples_for(name)
    if not cases:
        check(f"{label} has examples", False, "no entry in _grader-examples.json")
        continue
    check(f"{label} has an example that passes", any(e["pass"] for e in cases), "only failing examples")
    check(f"{label} has an example that fails", any(not e["pass"] for e in cases), "only passing examples")
    for example in cases:
        got = grade(config, example["calls"])
        check(f"{label}: {example['why']}", got == example["pass"],
              f"graded {'PASS' if got else 'FAIL'}, the example says {'PASS' if example['pass'] else 'FAIL'}")

print(f"\n{passes} passed, {len(failures)} failed")
sys.exit(1 if failures else 0)
