#!/usr/bin/env python3
"""The SessionStart work-in-progress hook keeps what is in use and drops the rest.

    python3 tests/test-wip.py

The deletion cases matter most: a hook that removes a folder somebody read
yesterday is worse than the /tmp it replaces, and one that never removes anything
is a second junk drawer.
"""
import json
import os
import shutil
import subprocess
import sys
import tempfile
import time

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
HOOK = os.path.join(ROOT, "hooks", "wip.py")
DAY = 86400

failures = []
passes = 0


def check(name, cond, detail=""):
    global passes
    if cond:
        passes += 1
        print(f"ok    {name}")
        return
    failures.append(f"{name}: {detail}")
    print(f"FAIL  {name}: {detail}")


def put(path, text="x", mtime_days=0.0, atime_days=None):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as fh:
        fh.write(text)
    now = time.time()
    a = now - (mtime_days if atime_days is None else atime_days) * DAY
    os.utime(path, (a, now - mtime_days * DAY))


def fire(wip, cwd, env_file=None, extra_env=None, stdin=None):
    env = dict(os.environ)
    env["CLAUDE_WIP_ROOT"] = wip
    env["KIT_WIP_DEBUG"] = "1"
    for k in ("KIT_WIP", "KIT_WIP_TTL_DAYS", "CLAUDE_ENV_FILE"):
        env.pop(k, None)
    if env_file:
        env["CLAUDE_ENV_FILE"] = env_file
    env.update(extra_env or {})
    payload = stdin if stdin is not None else json.dumps({"cwd": cwd, "source": "startup"})
    p = subprocess.run([sys.executable, HOOK], input=payload, capture_output=True,
                       text=True, env=env, cwd=cwd)
    return p.stdout, p.stderr, p.returncode


def said(out):
    if not out.strip():
        return ""
    return json.loads(out)["hookSpecificOutput"]["additionalContext"]


def git(*args, cwd):
    subprocess.run(["git", *args], cwd=cwd, check=True, capture_output=True)


base = tempfile.mkdtemp(prefix="kit-wip-")
try:
    repo = os.path.join(base, "shop")
    os.makedirs(repo)
    git("init", "-q", cwd=repo)
    git("-c", "user.email=t@t", "-c", "user.name=t", "commit", "-q", "--allow-empty", "-m", "init", cwd=repo)
    tree = os.path.join(base, "shop-feature")
    git("worktree", "add", "-q", tree, cwd=repo)
    plain = os.path.join(base, "notes")
    os.makedirs(plain)

    wip = os.path.join(base, "wip")
    put(os.path.join(wip, "shop", "fresh", "pr.md"))
    put(os.path.join(wip, "shop", "stale", "spec.md"), mtime_days=8)
    put(os.path.join(wip, "shop", "read-lately", "spec.md"), mtime_days=9, atime_days=1)
    put(os.path.join(wip, "shop", "one-live-file", "old.md"), mtime_days=30)
    put(os.path.join(wip, "shop", "one-live-file", "new.md"), mtime_days=2)
    put(os.path.join(wip, "gone", "x", "f.md"), mtime_days=20)

    env_file = os.path.join(base, "env")
    out, err, rc = fire(wip, repo, env_file=env_file)
    text = said(out)
    check("exits 0", rc == 0, err)
    check("a topic untouched past the TTL is deleted",
          not os.path.exists(os.path.join(wip, "shop", "stale")))
    check("a topic read inside the TTL is kept, whatever its mtime",
          os.path.isdir(os.path.join(wip, "shop", "read-lately")))
    check("one live file keeps its whole topic, old files included",
          os.path.isfile(os.path.join(wip, "shop", "one-live-file", "old.md")))
    check("a fresh topic is kept", os.path.isdir(os.path.join(wip, "shop", "fresh")))
    check("a repository folder left empty is removed", not os.path.exists(os.path.join(wip, "gone")))
    check("names the repository folder", os.path.join(wip, "shop") in text, text)
    check("lists the topics that are there", "- fresh/ (1 files" in text and "one-live-file/" in text, text)
    check("does not list what it deleted", "stale/" not in text, text)
    with open(env_file, encoding="utf-8") as fh:
        exported = fh.read()
    check("exports CLAUDE_WIP to the session", exported.strip() == f"export CLAUDE_WIP={os.path.join(wip, 'shop')}", exported)

    out, _, _ = fire(wip, tree)
    check("a worktree shares its main checkout's folder", os.path.join(wip, "shop") + " " in said(out), said(out))

    out, _, _ = fire(wip, repo, extra_env={"KIT_WIP_TTL_DAYS": "0.5"})
    check("KIT_WIP_TTL_DAYS shortens the TTL",
          not os.path.exists(os.path.join(wip, "shop", "read-lately")))

    out, _, _ = fire(wip, plain)
    check("outside git the folder is named after the directory", os.path.join(wip, "notes") in said(out), said(out))
    check("an empty repository folder lists no topics", "Topics already there" not in said(out), said(out))

    out, err, rc = fire(wip, repo, extra_env={"KIT_WIP": "off"})
    check("KIT_WIP=off is silent", rc == 0 and out == "", out + err)

    out, err, rc = fire(wip, plain, stdin="not json")
    check("bad stdin falls back to the working directory", rc == 0 and os.path.join(wip, "notes") in said(out), out + err)

    blocked = os.path.join(base, "file-not-dir")
    put(blocked)
    env = dict(os.environ, CLAUDE_WIP_ROOT=blocked)
    env.pop("KIT_WIP_DEBUG", None)
    p = subprocess.run([sys.executable, HOOK], input="{}", capture_output=True, text=True, env=env, cwd=plain)
    check("an unusable root fails silent", p.returncode == 0 and p.stdout == "", p.stdout + p.stderr)
finally:
    shutil.rmtree(base, ignore_errors=True)

print(f"\n{passes} ok, {len(failures)} failed")
sys.exit(1 if failures else 0)
