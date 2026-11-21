#!/usr/bin/env python3
"""kit dream-digest reads one project's sessions and counts what recurs across them.

    python3 tests/test-dream-digest.py

The cases that matter: it never reads another project's folder, a pattern in one
session is never reported as shared, and the newest transcript can be left out.
"""
import json
import os
import subprocess
import sys
import tempfile
import time

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DIGEST = os.path.join(ROOT, "scripts", "dream-digest")

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


def write(path, rows, age):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as fh:
        for row in rows:
            fh.write(json.dumps(row) + "\n")
    stamp = time.time() - age
    os.utime(path, (stamp, stamp))


def said(text, stamp):
    return {"type": "user", "timestamp": stamp, "message": {"role": "user", "content": text}}


def call(tool_id, name):
    return {"type": "assistant", "message": {"role": "assistant", "content": [
        {"type": "tool_use", "id": tool_id, "name": name, "input": {"command": "x"}}]}}


def failed(tool_id, text):
    return {"type": "user", "toolUseResult": "e", "message": {"role": "user", "content": [
        {"type": "tool_result", "tool_use_id": tool_id, "is_error": True, "content": text}]}}


def ok(tool_id, text):
    return {"type": "user", "toolUseResult": "o", "message": {"role": "user", "content": [
        {"type": "tool_result", "tool_use_id": tool_id, "content": text}]}}


config = tempfile.mkdtemp()
project = "/work/my.app"
folder = os.path.join(config, "projects", "-work-my-app")
other = os.path.join(config, "projects", "-work-other")

write(os.path.join(folder, "s1.jsonl"), [
    said("no, use pnpm because the lockfile is pnpm", "2026-11-01T10:00:00Z"),
    call("a", "Bash"), failed("a", "Exit code 1\nnpm ERR! missing script: test 42"),
    call("b", "Read"), ok("b", "fine"),
    {"type": "system", "subtype": "compact_boundary"},
], age=300)
write(os.path.join(folder, "s2.jsonl"), [
    said("again: pnpm, not npm", "2026-11-02T10:00:00Z"),
    call("c", "Bash"), failed("c", "Exit code 1\nnpm ERR! missing script: test 7"),
    call("d", "Edit"), failed("d", "File has not been read yet"),
    said("x" * 700, "2026-11-02T11:00:00Z"),
], age=200)
write(os.path.join(folder, "s3.jsonl"), [said("the session running the digest", "2026-11-03T10:00:00Z")], age=10)
write(os.path.join(folder, "s1", "subagents", "agent-1.jsonl"), [said("a subagent prompt", "2026-11-01T10:05:00Z")], age=100)
write(os.path.join(other, "o1.jsonl"), [said("from another project entirely", "2026-11-01T09:00:00Z")], age=50)


def run(*args):
    env = dict(os.environ, CLAUDE_CONFIG_DIR=config)
    p = subprocess.run([sys.executable, DIGEST, "--project", project, *args],
                       capture_output=True, text=True, env=env)
    return p.stdout, p.stderr, p.returncode


out, err, code = run()
check("1 exits 0", code == 0, err)
check("2 reads only this project's folder", "another project entirely" not in out, out[:200])
check("3 never reads subagent transcripts", "a subagent prompt" not in out)
check("4 lists what the user typed", "use pnpm because the lockfile" in out and "again: pnpm" in out)
check("5 a shared error is counted across sessions, numbers folded",
      "2 of 3 sessions: Bash: npm ERR! missing script: test" in out, out[:400])
check("6 an error in one session is not reported as shared",
      "sessions: Edit" not in out and "Edit x1: File has not been read yet" in out, out)
check("7 a long message is cut and says by how much", "[+200 chars]" in out)
check("8 counts compactions", "1 compactions" in out)
check("9 sessions come oldest first", out.find("session s1") < out.find("session s2") < out.find("session s3"))

out, _, _ = run("--skip-newest")
check("10 --skip-newest leaves out the newest transcript", "the session running the digest" not in out
      and "session s2" in out, out[:300])
out, _, _ = run("--sessions", "1")
check("11 --sessions takes the newest N", "session s3" in out and "session s1" not in out)
out, _, _ = run("--max-chars", "120")
check("12 --max-chars cuts and says so", "[digest cut at 120 characters" in out and len(out) < 260, len(out))

p = subprocess.run([sys.executable, DIGEST, "--dir", other], capture_output=True, text=True)
check("13 --dir reads that folder instead", "another project entirely" in p.stdout and "pnpm" not in p.stdout, p.stdout[:200])

empty = tempfile.mkdtemp()
p = subprocess.run([sys.executable, DIGEST, "--project", "/nowhere"], capture_output=True, text=True,
                   env=dict(os.environ, CLAUDE_CONFIG_DIR=empty))
check("14 no transcripts exits 1 and names the folder", p.returncode == 1 and "-nowhere" in p.stderr, p.stderr)

print()
if failures:
    print(f"{len(failures)} failed: {', '.join(failures)}")
    sys.exit(1)
print(f"all passed ({passes} cases)")
