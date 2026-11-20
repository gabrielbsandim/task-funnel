#!/usr/bin/env python3
"""Asks the compaction summary to keep the user's long messages whole.

A `PreCompact` hook. Claude Code uses a PreCompact hook's stdout as instructions
for the summary it is about to write (https://code.claude.com/docs/en/hooks,
PreCompact). The summary already lists the user's messages, but it shortens the
long ones, and those are the ones that carry a task's constraints: measured on
2026-11-20 over 934 compactions on one machine, of 137 user messages of 300 or
more characters, 91 came back whole, 10 cut and 36 not at all. After a compaction
the summary is the only copy the session has, so a dropped "never touch the
migration" is gone for the rest of the task. `kit compact-loss` re-measures it.

So the hook counts those messages in the context being compacted and asks for each
one verbatim, naming how each begins so the summary can be checked against the
list. It never quotes a message in full itself: the model writing the summary
already has them, and the stdout budget is 10,000 characters.

Messages before the newest summary are not listed: they are no longer in the
context, only in that summary. When the user passes instructions to /compact
they are repeated after the list, because the docs do not say whether stdout
replaces them or joins them.

Silent and exit 0 on everything that goes wrong. KIT_COMPACT_VERBATIM=off
disables it.
"""
import importlib.machinery
import importlib.util
import json
import os
import sys

MIN_CHARS = 300
LISTED = 40
ANCHOR = 80
CUSTOM_MAX = 4000


def load_compact_loss():
    path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "scripts", "compact-loss")
    loader = importlib.machinery.SourceFileLoader("kit_compact_loss", path)
    spec = importlib.util.spec_from_loader("kit_compact_loss", loader)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def anchor(text):
    flat = " ".join(text.split())
    return flat if len(flat) <= ANCHOR else flat[:ANCHOR].rstrip() + "..."


def instructions(messages, custom):
    long = [m for m in messages if len(m) >= MIN_CHARS]
    if not long:
        return ""
    # The first one is usually the task itself, and the newest ones are what the
    # work is in the middle of; what falls between is what the cap gives up.
    shown = long if len(long) <= LISTED else long[:1] + long[-(LISTED - 1):]
    lines = [
        "Keep the user's own words whole. In the summary's list of the user's messages, "
        f"reproduce every message the user typed of {MIN_CHARS} or more characters verbatim "
        "and in full: no paraphrase, no shortening, no ellipsis. They hold the constraints "
        "the rest of the session is held to, and after this summary they exist nowhere else.",
        f"The context being compacted holds {len(long)} of them. Each begins:",
    ]
    lines.extend(f'{i}. "{anchor(m)}"' for i, m in enumerate(shown, 1))
    if len(shown) < len(long):
        lines.append(f"({len(long) - len(shown)} more in between, the same rule applies.)")
    if isinstance(custom, str) and custom.strip():
        lines.append(f"The user's own instructions for this compaction also apply: {custom.strip()[:CUSTOM_MAX]}")
    return "\n".join(lines)


def main():
    if os.environ.get("KIT_COMPACT_VERBATIM") == "off":
        return
    try:
        payload = json.loads(sys.stdin.read() or "{}")
    except ValueError:
        return
    if not isinstance(payload, dict):
        return
    path = payload.get("transcript_path")
    if not isinstance(path, str) or not os.path.isfile(path):
        return
    text = instructions(load_compact_loss().user_messages(path), payload.get("custom_instructions"))
    if text:
        print(text)


if __name__ == "__main__":
    try:
        main()
    except Exception:
        if os.environ.get("KIT_COMPACT_VERBATIM_DEBUG"):
            raise
    sys.exit(0)
