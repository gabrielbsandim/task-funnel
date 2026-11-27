#!/usr/bin/env python3
"""PreToolUse guard against expensive un-scoped flagship subagent dispatches.

Blocks generic `Agent`/`Task` (`general-purpose`, empty type, `self`, `fork`) and
Antigravity `invoke_subagent` (`self`) dispatches unless they declare a smaller
model (`sonnet`/`haiku` or `flash`/`flash_lite`) or belong to a scoped agent
(`Explore`, `Plan`, `research`, `task-funnel:*`, etc.).

Set KIT_AGENT_GUARD=off in the environment to bypass for a session.
"""
import importlib.machinery
import importlib.util
import json
import os
import sys

GENERIC_TYPES = {"", "general-purpose", "self", "fork"}
CHEAPER_TOKENS = ("sonnet", "haiku", "flash")


def _load_host():
    path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "host.py")
    loader = importlib.machinery.SourceFileLoader("kit_host", path)
    spec = importlib.util.spec_from_loader(loader.name, loader)
    module = importlib.util.module_from_spec(spec)
    loader.exec_module(module)
    return module


def check(payload: dict) -> int:
    if not isinstance(payload, dict):
        return 0
    if os.environ.get("KIT_AGENT_GUARD", "").lower() == "off":
        return 0
    if payload.get("tool_name") not in ("Agent", "Task"):
        return 0

    args = payload.get("tool_input") or {}
    if not isinstance(args, dict):
        return 0

    stype = str(args.get("subagent_type") or "").strip().lower()
    if stype not in GENERIC_TYPES:
        return 0

    model = str(args.get("model") or "").strip().lower()
    if model and any(tok in model for tok in CHEAPER_TOKENS):
        return 0

    label = stype or "default"
    model_note = f"model={model!r}" if model else "no explicit model (inherits flagship)"
    sys.stderr.write(
        f"Blocked: generic `{label}` subagent with {model_note}.\n"
        "Measured across local sessions: generic flagship dispatches averaged US$ 11.61/run\n"
        "vs US$ 0.31 for funnel-reviewer and US$ 2.30 for Explore because they inherit the\n"
        "session model plus every MCP schema.\n"
        "Use a scoped agent (`Explore`, `Plan`, `task-funnel:funnel-reviewer`, `research`),\n"
        "set `model` to `sonnet`/`haiku` (Antigravity: `flash`/`flash_lite`), or set\n"
        "KIT_AGENT_GUARD=off to allow flagship generic subagents.\n"
    )
    return 2


def main() -> int:
    try:
        payload = json.load(sys.stdin)
    except Exception:
        return 0
    if not isinstance(payload, dict):
        return 0
    if "hook_event_name" not in payload and "tool_name" not in payload:
        try:
            hint = sys.argv[1] if len(sys.argv) > 1 else ""
            return _load_host().run_guard(check, payload, hint)
        except Exception:
            return 0
    return check(payload)


if __name__ == "__main__":
    sys.exit(main())
