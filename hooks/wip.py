#!/usr/bin/env python3
"""Gives every session a work-in-progress folder that outlives it.

A `SessionStart` hook. The session scratchpad has the session id in its path and
usually lives under /tmp, so a spec, a brief, a pull request body or a round of
findings written there is gone for the next session twice over: the path is
unknown to it, and on a machine whose /tmp is cleared at boot (WSL with systemd,
`D /tmp` in tmpfiles.d) the file is gone too. Measured on one machine,
2026-09 to 2026-11: 1169 Write calls under /tmp across 83 sessions, 808 of them
markdown, and five boots in the two days before.

So each repository gets `<root>/<repo>/`, exported to the session as
`$CLAUDE_WIP`, and the hook lists the topic folders already there so the next
session looks before it redoes. A topic folder is deleted once no file in it has
been read or written for the TTL, which is what keeps this from being a second
place where things accumulate forever. The default of 7 days covers the longest
reuse measured (188 hours); the 99th percentile was 15 hours.

Worktrees share their main checkout's folder, because the work outlives the
worktree that `kit worktree gc` removes at ship.

Silent and exit 0 on everything that goes wrong: a session start is never the
place to fail.

Env: CLAUDE_WIP_ROOT (default ~/.local/state/wip), KIT_WIP_TTL_DAYS (default 7),
KIT_WIP=off disables it.
"""
import json
import os
import shlex
import shutil
import subprocess
import sys
import time

LISTED = 15


def ttl_seconds():
    try:
        return float(os.environ.get("KIT_WIP_TTL_DAYS") or 7) * 86400
    except ValueError:
        return 7 * 86400


def last_use(topic):
    newest = 0.0
    for base, _, files in os.walk(topic):
        for name in files:
            try:
                st = os.stat(os.path.join(base, name))
            except OSError:
                continue
            newest = max(newest, st.st_mtime, st.st_atime)
    return newest


def last_change(topic):
    newest, count = 0.0, 0
    for base, _, files in os.walk(topic):
        for name in files:
            try:
                newest = max(newest, os.stat(os.path.join(base, name)).st_mtime)
            except OSError:
                continue
            count += 1
    return newest, count


def subdirs(path):
    try:
        return [e.path for e in os.scandir(path) if e.is_dir(follow_symlinks=False)]
    except OSError:
        return []


def prune(root, now, ttl):
    for repo in subdirs(root):
        for topic in subdirs(repo):
            if now - last_use(topic) <= ttl:
                continue
            shutil.rmtree(topic, ignore_errors=True)
        try:
            os.rmdir(repo)
        except OSError:
            pass


def repo_slug(cwd):
    try:
        out = subprocess.run(["git", "rev-parse", "--git-common-dir"], cwd=cwd,
                             capture_output=True, text=True, timeout=5)
    except (OSError, subprocess.SubprocessError):
        return os.path.basename(os.path.normpath(cwd))
    if out.returncode != 0 or not out.stdout.strip():
        return os.path.basename(os.path.normpath(cwd))
    common = os.path.normpath(os.path.join(cwd, out.stdout.strip()))
    return os.path.basename(os.path.dirname(common))


def topics_text(folder, now):
    rows = []
    for topic in subdirs(folder):
        changed, count = last_change(topic)
        rows.append((changed, count, os.path.basename(topic)))
    rows.sort(reverse=True)
    return [f"- {name}/ ({count} files, last change {int((now - changed) // 3600)}h ago)"
            for changed, count, name in rows[:LISTED]]


def main():
    if os.environ.get("KIT_WIP") == "off":
        return
    try:
        payload = json.loads(sys.stdin.read() or "{}")
    except ValueError:
        payload = {}
    cwd = payload.get("cwd") if isinstance(payload, dict) else None
    cwd = cwd if cwd and os.path.isdir(cwd) else os.getcwd()

    root = os.environ.get("CLAUDE_WIP_ROOT") or os.path.expanduser("~/.local/state/wip")
    now, ttl = time.time(), ttl_seconds()
    os.makedirs(root, exist_ok=True)
    prune(root, now, ttl)

    folder = os.path.join(root, repo_slug(cwd))
    env_file = os.environ.get("CLAUDE_ENV_FILE")
    if env_file:
        with open(env_file, "a", encoding="utf-8") as fh:
            fh.write(f"export CLAUDE_WIP={shlex.quote(folder)}\n")

    days = ttl / 86400
    lines = [
        f"Work-in-progress folder for this repository: {folder} (also $CLAUDE_WIP in Bash).",
        f"It survives the session and a reboot; a topic folder in it is deleted {days:g} days after its last read or write.",
        f"Anything worth more than this turn (spec, plan, brief, pull request body, ledger, findings, handoff, generated data) goes in {folder}/<topic>/, never in the scratchpad or /tmp, which are for throwaway files only.",
    ]
    listed = topics_text(folder, now)
    if listed:
        lines.append("Topics already there, newest first; check them before redoing work:")
        lines.extend(listed)
    print(json.dumps({"hookSpecificOutput": {
        "hookEventName": "SessionStart", "additionalContext": "\n".join(lines)}}))


if __name__ == "__main__":
    try:
        main()
    except Exception:
        if os.environ.get("KIT_WIP_DEBUG"):
            raise
    sys.exit(0)
