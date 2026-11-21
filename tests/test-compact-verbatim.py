#!/usr/bin/env python3
"""The PreCompact hook asks for the user's long messages, and only those.

    python3 tests/test-compact-verbatim.py

What it must never do is list a tool result, a slash command or a hook's own text as
something the user said, or fail a compaction: every broken input is silence.
The second half checks the measurement `kit compact-loss` reports.
"""
import json
import os
import subprocess
import sys
import tempfile

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
HOOK = os.path.join(ROOT, "hooks", "compact-verbatim.py")
LOSS = os.path.join(ROOT, "scripts", "compact-loss")

failures = []
passes = 0


def check(name, cond, detail=""):
    global passes
    if cond:
        passes += 1
        print(f"ok    {name}")
        return
    failures.append(name)
    print(f"FAIL  {name}: {detail}")


def user(content, **extra):
    return {"type": "user", "message": {"role": "user", "content": content}, **extra}


def summary(text):
    return user(text, isCompactSummary=True)


def transcript(rows, raw_lines=()):
    fd, path = tempfile.mkstemp(suffix=".jsonl")
    with os.fdopen(fd, "w", encoding="utf-8") as fh:
        for line in raw_lines:
            fh.write(line + "\n")
        for row in rows:
            fh.write(json.dumps(row) + "\n")
    return path


def fire(payload, env=None):
    full = {k: v for k, v in os.environ.items() if not k.startswith("KIT_")}
    full["KIT_COMPACT_VERBATIM_DEBUG"] = "1"
    full.update(env or {})
    raw = payload if isinstance(payload, str) else json.dumps(payload)
    p = subprocess.run([sys.executable, HOOK], input=raw, capture_output=True, text=True, env=full)
    return p.stdout, p.stderr, p.returncode


def compact(path, **extra):
    return {"hook_event_name": "PreCompact", "trigger": "manual", "transcript_path": path, **extra}


LONG_A = "Keep the migration untouched. " + "a" * 300
LONG_B = "Use the billing parser for every amount. " + "b" * 300
LONG_C = "Typed while the agent worked: keep the old endpoint. " + "k" * 300
OLD = "Before the last compaction: " + "o" * 300

path = transcript([
    user(OLD),
    summary("Summary of the earlier part."),
    user(LONG_A),
    user("ok, go"),
    user([{"type": "tool_result", "tool_use_id": "t1", "content": "x" * 400}], toolUseResult={"stdout": "x"}),
    user("<command-name>/compact</command-name> " + "c" * 400),
    user([{"type": "text", "text": "<system-reminder>" + "r" * 400 + "</system-reminder>"}]),
    user("meta " + "m" * 400, isMeta=True),
    user("side " + "s" * 400, isSidechain=True),
    user([{"type": "text", "text": LONG_B}]),
    {"type": "attachment", "attachment": {"type": "queued_command", "commandMode": "prompt", "prompt": LONG_C}},
    {"type": "attachment", "attachment": {"type": "queued_command", "prompt": "<task-notification>" + "t" * 400}},
    {"type": "attachment", "attachment": {"type": "queued_command", "commandMode": "prompt", "prompt": "side " + "q" * 400}, "isSidechain": True},
], raw_lines=["not json", "[1, 2]"])

out, err, code = fire(compact(path))
check("1 exits 0 with no stderr", code == 0 and not err, f"{code} {err[:200]}")
check("2 lists the long messages since the newest summary, one typed mid-turn", "holds 3 of them" in out and '"Typed while the agent worked' in out, out[:600])
check("3 names how each begins, in order",
      out.find('"Keep the migration untouched.') < out.find('"Use the billing parser') and
      out.find('"Keep the migration untouched.') != -1, out[:400])
check("4 leaves out what came before the newest summary", "Before the last compaction" not in out)
check("5 leaves out tool results, commands, reminders, meta and sidechain",
      not any(t in out for t in ("xxxx", "cccc", "rrrr", "mmmm", "ssss", "tttt", "qqqq")), out)
check("6 never quotes a long message in full", "a" * 120 not in out)

out, _, _ = fire(compact(path, custom_instructions="focus on the parser"))
check("7 repeats the user's /compact instructions", out.rstrip().endswith("focus on the parser"), out[-200:])

short = transcript([user("fix it"), user("ok")])
out, err, code = fire(compact(short))
check("8 says nothing when no message is long", out == "" and code == 0 and not err, repr(out))

out, _, _ = fire(compact(path), env={"KIT_COMPACT_VERBATIM": "off"})
check("9 KIT_COMPACT_VERBATIM=off disables it", out == "")

for name, payload in (("missing transcript", compact("/nonexistent/x.jsonl")),
                      ("no transcript_path", {"trigger": "auto"}),
                      ("transcript_path not a string", {"transcript_path": 3}),
                      ("bad json", "{nope")):
    out, err, code = fire(payload)
    check(f"10 {name} is silent", out == "" and code == 0 and not err, f"{out!r} {err[:200]}")

many = transcript([user(f"message {i:03d} " + "z" * 300) for i in range(100)])
out, _, _ = fire(compact(many))
check("11 the list stays under the 10,000 character stdout budget", 0 < len(out) < 10_000, len(out))
check("12 over the cap it keeps the first and the newest",
      '"message 000' in out and '"message 099' in out and '"message 050' not in out, out[-300:])
check("13 and says how many it skipped", "60 more in between" in out, out[-200:])

loss = transcript([
    user("whole one " + "w" * 300),
    user("cut one " + "k" * 300),
    user("missing one " + "q" * 300),
    user("short"),
    summary("whole one " + "w" * 300 + " and cut one " + "k" * 192),
    user("after the summary " + "n" * 300),
])
p = subprocess.run([sys.executable, LOSS, loss], capture_output=True, text=True)
check("14 compact-loss counts whole, cut and missing",
      "compactions 1" in p.stdout and "whole 1, cut 1, missing 1" in p.stdout, p.stdout + p.stderr)
p = subprocess.run([sys.executable, LOSS, "--exclude", os.path.basename(loss), loss], capture_output=True, text=True)
check("15 --exclude drops a transcript by path", "transcripts 0" in p.stdout, p.stdout)

print()
if failures:
    print(f"{len(failures)} failed: {', '.join(failures)}")
    sys.exit(1)
print(f"all passed ({passes} cases)")
