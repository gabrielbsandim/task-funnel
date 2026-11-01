#!/usr/bin/env python3
"""Host protocol adapter so every hook runs unchanged on Claude Code and Antigravity.

Claude Code sends snake_case (`tool_name`, `tool_input`, `transcript_path`) and reads
exit code 2 plus stderr as a block. Antigravity sends protojson camelCase (`toolCall`,
`transcriptPath`, `workspacePaths`, `terminationReason`) and expects exit 0 with a JSON
verdict on stdout (`{"decision": "deny", "reason": ...}` on PreToolUse, `{}` on
PostToolUse, and `{"decision": "continue", "reason": ...}` on Stop).

Normalising at the boundary keeps one implementation of every rule instead of two copies
that drift. Imported lazily only when a payload is not Claude Code's, so Claude Code
calls pay zero extra import time.
"""
import io
import json
import os
import sys

AGY_KEYS = (
    "toolCall",
    "conversationId",
    "terminationReason",
    "transcriptPath",
    "workspacePaths",
    "invocationNum",
    "executionNum",
)


def is_antigravity(payload: dict) -> bool:
    if not isinstance(payload, dict) or "hook_event_name" in payload or "tool_name" in payload:
        return False
    return any(key in payload for key in AGY_KEYS)


def unwrap_arg(value):
    """Compact Antigravity transcripts encode each arg value as a JSON string."""
    if isinstance(value, str) and len(value) >= 2 and value[0] == '"' == value[-1]:
        try:
            return json.loads(value)
        except ValueError:
            return value
    return value


def normalize_tool(name: str, args: dict, compact_args: bool = False):
    """Map an Antigravity tool call to the (tool_name, tool_input) shape the guards read."""
    args = {k: unwrap_arg(v) for k, v in (args or {}).items()} if compact_args else (args or {})

    if name == "run_command":
        return "Bash", {"command": args.get("CommandLine") or args.get("command") or ""}

    if name in ("write_file", "write_to_file"):
        path = args.get("Path") or args.get("TargetFile") or args.get("file_path") or ""
        content = args.get("Content") or args.get("CodeContent") or args.get("content") or ""
        return "Write", {"file_path": path, "content": content}

    if name in ("edit_file", "replace_file_content"):
        path = args.get("Path") or args.get("TargetFile") or args.get("file_path") or ""
        old = args.get("Target") or args.get("TargetContent") or args.get("old_string") or ""
        new = args.get("Replacement") or args.get("ReplacementContent") or args.get("new_string") or ""
        return "Edit", {"file_path": path, "old_string": old, "new_string": new}

    if name == "multi_replace_file_content":
        path = args.get("TargetFile") or args.get("Path") or args.get("file_path") or ""
        chunks = args.get("ReplacementChunks")
        if isinstance(chunks, str):
            try:
                chunks = json.loads(chunks)
            except ValueError:
                chunks = []
        chunks = chunks if isinstance(chunks, list) else []
        old = "\n".join((c or {}).get("TargetContent") or "" for c in chunks if isinstance(c, dict))
        edits = [{"new_string": (c or {}).get("ReplacementContent") or ""} for c in chunks if isinstance(c, dict)]
        new = "\n".join(e["new_string"] for e in edits)
        return "Edit", {"file_path": path, "old_string": old, "new_string": new, "edits": edits}

    if name == "notebook_edit":
        path = args.get("NotebookPath") or args.get("Path") or args.get("notebook_path") or ""
        src = args.get("NewSource") or args.get("Content") or args.get("new_source") or ""
        return "NotebookEdit", {"notebook_path": path, "new_source": src, "content": src}

    if name == "call_mcp_tool":
        server = args.get("ServerName") or "mcp"
        tool = args.get("ToolName") or ""
        inner = args.get("Arguments")
        if isinstance(inner, str):
            try:
                inner = json.loads(inner)
            except ValueError:
                inner = {}
        return f"mcp__{server}__{tool}", inner if isinstance(inner, dict) else {}

    return name, args


def infer_event(payload: dict, hint: str = "") -> str:
    if hint:
        return hint
    if "terminationReason" in payload or "executionNum" in payload:
        return "Stop"
    if "toolCall" in payload:
        return "PostToolUse" if "error" in payload else "PreToolUse"
    return "PreInvocation"


def normalize_payload(payload: dict, event_hint: str = "") -> dict:
    if not is_antigravity(payload):
        return payload
    event = infer_event(payload, event_hint)
    tc = payload.get("toolCall") if isinstance(payload.get("toolCall"), dict) else {}
    raw_args = tc.get("args") if isinstance(tc.get("args"), dict) else {}
    tool_name, tool_input = normalize_tool(tc.get("name") or "", raw_args)
    workspaces = payload.get("workspacePaths") if isinstance(payload.get("workspacePaths"), list) else []
    file_target = tool_input.get("file_path") or tool_input.get("notebook_path") or ""
    cwd = (
        raw_args.get("Cwd")
        or raw_args.get("DirectoryPath")
        or (workspaces[0] if workspaces else "")
        or (os.path.dirname(file_target) if os.path.isabs(file_target) else "")
        or os.getcwd()
    )
    return {
        "_antigravity": True,
        "hook_event_name": event,
        "tool_name": tool_name,
        "tool_input": tool_input,
        "cwd": cwd,
        "transcript_path": payload.get("transcriptPath") or "",
        "session_id": payload.get("conversationId") or "",
        "termination_reason": payload.get("terminationReason") or "",
        "stop_hook_active": bool(payload.get("stop_hook_active")),
    }


def emit(event: str, code: int, reason: str) -> int:
    text = reason.strip()
    if event == "PreToolUse":
        out = {"decision": "allow"} if code == 0 else {"decision": "deny", "reason": text}
        sys.stdout.write(json.dumps(out) + "\n")
        return 0
    if event == "PostToolUse":
        sys.stdout.write("{}\n")
        return 0
    if event == "Stop":
        out = {"decision": "allow"} if code == 0 else {"decision": "continue", "reason": text}
        sys.stdout.write(json.dumps(out) + "\n")
        return 0
    return 0


def run_guard(fn, payload: dict, event_hint: str = "") -> int:
    if not is_antigravity(payload):
        return fn(payload)
    norm = normalize_payload(payload, event_hint)
    buf = io.StringIO()
    saved = sys.stderr
    sys.stderr = buf
    try:
        code = fn(norm)
    finally:
        sys.stderr = saved
    return emit(norm["hook_event_name"], code, buf.getvalue())
