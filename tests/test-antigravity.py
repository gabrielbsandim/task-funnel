#!/usr/bin/env python3
"""Dual-host checks for Antigravity: bundle export, hook protocol, and transcripts.

    python3 tests/test-antigravity.py

Every literal a guard looks for is assembled at runtime so this test file stays
writable under the plugin's own hooks and passes the repository's em dash check.
"""
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import zipfile

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
KIT = os.path.join(ROOT, "scripts", "kit")
EXPORT = os.path.join(ROOT, "scripts", "export-antigravity")
CTX = os.path.join(ROOT, "scripts", "context")
USAGE = os.path.join(ROOT, "scripts", "usage")

D = "." + "env"
NV = "--no" + "-verify"
SKIP_MARK = "it" + ".skip"
DASH = chr(0x2014)

PASS, FAIL = 0, 0


def check(name, cond, detail=""):
    global PASS, FAIL
    if cond:
        PASS += 1
        print(f"ok    {name}")
    else:
        FAIL += 1
        print(f"FAIL  {name}\n        {detail}")


def run_hook(script, payload, event=None, env=None):
    cmd = [sys.executable, os.path.join(ROOT, "hooks", script)]
    if event:
        cmd.append(event)
    proc = subprocess.run(
        cmd,
        input=json.dumps(payload),
        capture_output=True,
        text=True,
        env={**os.environ, **(env or {})},
    )
    body = {}
    if proc.stdout.strip():
        try:
            body = json.loads(proc.stdout.strip())
        except ValueError:
            body = {"_raw": proc.stdout}
    return proc.returncode, body


def agy_pre(tool_name, args, workspace=None, transcript=""):
    return {
        "conversationId": "conv-1234",
        "workspacePaths": [workspace] if workspace else [ROOT],
        "transcriptPath": transcript,
        "stepIdx": 3,
        "toolCall": {"name": tool_name, "args": args},
    }


with open(os.path.join(ROOT, ".claude-plugin", "plugin.json"), encoding="utf-8") as fh:
    VERSION = json.load(fh)["version"]

# ------------------------------------------------------------------ 1. Bundle export
print("== 1. export-antigravity bundle")
with tempfile.TemporaryDirectory() as out:
    proc = subprocess.run([sys.executable, EXPORT, "--out", out, "--zip"], capture_output=True, text=True)
    bundle = os.path.join(out, "task-funnel")
    archive = os.path.join(out, "task-funnel-antigravity.zip")
    check("export exits 0", proc.returncode == 0, proc.stderr)
    check("plugin.json written at bundle root", os.path.isfile(os.path.join(bundle, "plugin.json")))
    check("hooks.json written at bundle root", os.path.isfile(os.path.join(bundle, "hooks.json")))
    check("hooks/hooks.json omitted so agy strict is clean", not os.path.exists(os.path.join(bundle, "hooks", "hooks.json")))
    check("commands/ omitted and converted to skill", not os.path.exists(os.path.join(bundle, "commands")))
    check("skills/setup/SKILL.md created from commands/setup.md", os.path.isfile(os.path.join(bundle, "skills", "setup", "SKILL.md")))
    check("assets/icon.png packaged outside dot-directories", os.path.isfile(os.path.join(bundle, "assets", "icon.png")))
    check("zip archive created", os.path.isfile(archive))

    manifest = json.load(open(os.path.join(bundle, "plugin.json"), encoding="utf-8"))
    check("version matches .claude-plugin/plugin.json", manifest.get("version") == VERSION, manifest)
    check("logo points to assets/icon.png", manifest.get("logo") == "assets/icon.png", manifest)

    with zipfile.ZipFile(archive) as zf:
        names = set(zf.namelist())
        check("zip holds task-funnel/plugin.json", "task-funnel/plugin.json" in names)
        kit_info = zf.getinfo("task-funnel/scripts/kit")
        check("zip preserves executable bit on scripts/kit", bool((kit_info.external_attr >> 16) & 0o111))

    task_skill = open(os.path.join(bundle, "skills", "task", "SKILL.md"), encoding="utf-8").read()
    for agent_name, want_model, want_mcp in (
        ("funnel-triage", "inherit", "false"),
        ("funnel-test-writer", "flash", "false"),
        ("funnel-reviewer", "flash", "false"),
        ("funnel-verifier", "flash", "false"),
        ("funnel-screen-lens", "inherit", "true"),
    ):
        agent_text = open(os.path.join(bundle, "agents", f"{agent_name}.md"), encoding="utf-8").read()
        check(f"{agent_name} model is {want_model}", f"\nmodel: {want_model}\n" in agent_text, agent_text[:300])
        check(f"{agent_name} inheritMcp is {want_mcp}", f"\ninheritMcp: {want_mcp}\n" in agent_text, agent_text[:300])
        if agent_name != "funnel-test-writer":
            check(f"{agent_name} gets no write tools", "write_file" not in agent_text and "edit_file" not in agent_text)
        else:
            check(f"{agent_name} gets write and edit tools", "write_file" in agent_text and "edit_file" in agent_text)
        row = re.search(rf"^\|.*`{re.escape(agent_name)}`\s*\|\s*(\S+)\s*\|", task_skill, re.M)
        check(f"bundled SKILL.md lists {agent_name} with {want_model}", bool(row) and row.group(1) == want_model)

    for skill_dir in os.listdir(os.path.join(bundle, "skills")):
        sp = os.path.join(bundle, "skills", skill_dir, "SKILL.md")
        check(f"bundled skills/{skill_dir}/SKILL.md stays under 20k", os.path.getsize(sp) < 20_000)

    agy_bin = shutil.which("agy")
    if agy_bin:
        val = subprocess.run([agy_bin, "plugin", "validate", bundle, "--strict"], capture_output=True, text=True)
        check("agy plugin validate --strict passes with 0 warnings", val.returncode == 0, val.stdout + val.stderr)

# ------------------------------------------------------------------ 2. Hook protocol
print("== 2. Antigravity hook protocol")
for desc, payload, want_decision in (
    ("blocks cat on secret file", agy_pre("run_command", {"CommandLine": f"cat {D}"}), "deny"),
    ("blocks reading mcp_config.json", agy_pre("run_command", {"CommandLine": "cat ~/.gemini/config/mcp_config.json"}), "deny"),
    ("allows cat on example file", agy_pre("run_command", {"CommandLine": f"cat {D}.example"}), "allow"),
    ("blocks push with hook bypass", agy_pre("run_command", {"CommandLine": f"git push {NV}"}), "deny"),
    ("allows ordinary test run", agy_pre("run_command", {"CommandLine": "npm test"}), "allow"),
):
    rc, out = run_hook("guards.py", payload, "PreToolUse")
    check(f"guards PreToolUse: {desc}", rc == 0 and out.get("decision") == want_decision, f"rc={rc} out={out}")

with tempfile.TemporaryDirectory() as tmp:
    spec = os.path.join(tmp, "calc.test.ts")
    open(spec, "w", encoding="utf-8").write("it('adds', () => { expect(1 + 1).toBe(2) })\n")

    rc, out = run_hook(
        "guards.py",
        agy_pre("edit_file", {"Path": spec, "Target": "it('adds'", "Replacement": SKIP_MARK + "('adds'"}, workspace=tmp),
        "PreToolUse",
    )
    check("edit_file skip marker denied", rc == 0 and out.get("decision") == "deny", out)

    rc, out = run_hook(
        "guards.py",
        agy_pre("replace_file_content", {"TargetFile": spec, "TargetContent": "toBe(2)", "ReplacementContent": "toBe(3)"}, workspace=tmp),
        "PreToolUse",
    )
    check("replace_file_content assertion edit allowed", rc == 0 and out.get("decision") == "allow", out)

    rc, out = run_hook(
        "guards.py",
        agy_pre(
            "multi_replace_file_content",
            {"TargetFile": spec, "ReplacementChunks": [{"TargetContent": "it('adds'", "ReplacementContent": SKIP_MARK + "('adds'"}]},
            workspace=tmp,
        ),
        "PreToolUse",
    )
    check("multi_replace_file_content skip marker denied", rc == 0 and out.get("decision") == "deny", out)

    doc = os.path.join(tmp, "notes.md")
    rc, out = run_hook(
        "guards.py",
        agy_pre("write_file", {"Path": doc, "Content": f"text {DASH} with dash\n"}, workspace=tmp),
        "PreToolUse",
        env={"KIT_NO_EM_DASH": "1"},
    )
    check("KIT_NO_EM_DASH denies before write_file lands", rc == 0 and out.get("decision") == "deny", out)

    rc, out = run_hook(
        "guards.py",
        agy_pre("write_file", {"Path": doc, "Content": f"text {DASH} with dash\n"}, workspace=tmp),
        "PostToolUse",
        env={"KIT_NO_EM_DASH": "1"},
    )
    check("PostToolUse emits empty JSON object", rc == 0 and out == {}, out)

    long_comment = "A sentence that repeats to exceed the comment budget. " * 40
    rc, out = run_hook(
        "guards.py",
        agy_pre(
            "call_mcp_tool",
            {"ServerName": "jira", "ToolName": "addCommentToJiraIssue", "Arguments": {"commentBody": long_comment}},
            workspace=tmp,
        ),
        "PreToolUse",
    )
    check("lazy call_mcp_tool Jira comment over budget denied", rc == 0 and out.get("decision") == "deny", out)

    short_body = os.path.join(tmp, "pr.md")
    open(short_body, "w", encoding="utf-8").write("## Summary\n\nFixes rounding.\n")
    tr = os.path.join(tmp, "transcript.jsonl")
    open(tr, "w", encoding="utf-8").write(
        json.dumps({
            "step_index": 1,
            "type": "PLANNER_RESPONSE",
            "tool_calls": [{"name": "read_file", "args": {"Path": json.dumps("/x/skills/task/SKILL.md")}}],
        }) + "\n"
    )
    rc, out = run_hook(
        "guards.py",
        agy_pre("run_command", {"CommandLine": f"gh pr create --body-file {short_body}"}, workspace=tmp, transcript=tr),
        "PreToolUse",
    )
    check("PR body without lane marker denied when Antigravity read task/SKILL.md", rc == 0 and out.get("decision") == "deny", out)

# ------------------------------------------------------------------ 3. Stop hook on Antigravity transcripts
print("== 3. Stop hook on Antigravity transcripts")
SCRATCH = os.path.join(os.path.expanduser("~"), ".cache")
os.makedirs(SCRATCH, exist_ok=True)
with tempfile.TemporaryDirectory(dir=SCRATCH) as tmp:
    main_repo = os.path.join(tmp, "app")
    os.makedirs(os.path.join(main_repo, ".claude"))
    subprocess.run(["git", "-C", tmp, "-c", "user.email=t@t", "-c", "user.name=t", "init", "-q", "-b", "trunk", main_repo], check=True)
    with open(os.path.join(main_repo, ".claude", "funnel.config.json"), "w", encoding="utf-8") as fh:
        json.dump({"base": "trunk"}, fh)
    subprocess.run(["git", "-C", main_repo, "-c", "user.email=t@t", "-c", "user.name=t", "commit", "-q", "--allow-empty", "-m", "init"], check=True)
    wt = os.path.join(tmp, "app-42")
    subprocess.run(["git", "-C", main_repo, "worktree", "add", "-q", "-b", "feat/42-test", wt], check=True)
    src = os.path.join(wt, "src", "billing.ts")

    def stop_case(steps, termination="NO_TOOL_CALL"):
        tpath = os.path.join(tmp, "transcript.jsonl")
        with open(tpath, "w", encoding="utf-8") as fh:
            for idx, step in enumerate(steps):
                fh.write(json.dumps({"step_index": idx, **step}) + "\n")
        payload = {"conversationId": "c1", "executionNum": 1, "terminationReason": termination, "transcriptPath": tpath}
        return run_hook("gate-receipt.py", payload)

    user_step = {"source": "USER_EXPLICIT", "type": "USER_INPUT", "content": "fix billing"}
    # Compact transcript encodes string args as JSON strings (`"\"/path\""`).
    edit_step = {"source": "MODEL", "type": "PLANNER_RESPONSE",
                 "tool_calls": [{"name": "edit_file", "args": {"Path": json.dumps(src)}}]}
    gate_step = {"source": "MODEL", "type": "PLANNER_RESPONSE",
                 "tool_calls": [{"name": "run_command", "args": {"CommandLine": json.dumps(f"env -C {wt} kit gate implement_first_pass")}}]}
    warned_step = {"source": "SYSTEM", "type": "SYSTEM_MESSAGE",
                   "content": f"{src} changed in {wt}, a funnel checkout, and no `kit gate` ran after it."}

    rc, out = stop_case([user_step, edit_step])
    check("ungated Antigravity edit returns decision=continue", rc == 0 and out.get("decision") == "continue", out)

    rc, out = stop_case([user_step, edit_step, gate_step])
    check("gated Antigravity edit returns decision=allow", rc == 0 and out.get("decision") == "allow", out)

    rc, out = stop_case([user_step, edit_step, warned_step])
    check("already-warned turn does not loop", rc == 0 and out.get("decision") == "allow", out)

    rc, out = stop_case([user_step, edit_step], termination="USER_CANCELED")
    check("canceled turn is never blocked", rc == 0 and out.get("decision") == "allow", out)

# ------------------------------------------------------------------ 4. context, usage, setup & version
print("== 4. kit context, usage, setup and version on Antigravity")
with tempfile.TemporaryDirectory() as tmp:
    brain = os.path.join(tmp, "brain")
    main_id = "aaaaaaaa-1111-2222-3333-444444444444"
    sub1_id = "bbbbbbbb-1111-2222-3333-444444444444"
    sub2_id = "cccccccc-1111-2222-3333-444444444444"
    repo_dir = os.path.join(tmp, "myrepo")
    os.makedirs(repo_dir)

    def write_agy_log(cid, steps):
        log_dir = os.path.join(brain, cid, ".system_generated", "logs")
        os.makedirs(log_dir, exist_ok=True)
        with open(os.path.join(log_dir, "transcript.jsonl"), "w", encoding="utf-8") as fh:
            for idx, s in enumerate(steps):
                fh.write(json.dumps({"step_index": idx, "created_at": "2026-11-01T15:00:00Z", **s}) + "\n")

    write_agy_log(main_id, [
        {"source": "USER_EXPLICIT", "type": "USER_INPUT", "content": f"Work in {repo_dir}\n<USER_SETTINGS_CHANGE>Gemini Pro</USER_SETTINGS_CHANGE>"},
        {"source": "MODEL", "type": "PLANNER_RESPONSE", "input_tokens": 25_000, "cache_read_tokens": 110_000, "output_tokens": 500,
         "tool_calls": [
             {"name": "invoke_subagent", "args": {"TypeName": '"task-funnel:funnel-triage"', "Role": '"Triage"', "Prompt": '"Check task"'}},
             {"name": "invoke_subagent", "args": {"TypeName": '"task-funnel:funnel-reviewer"', "Role": '"Reviewer"', "Prompt": '"dispatch 1"'}},
         ]},
        {"source": "MODEL", "type": "GENERIC", "content": f'Created At: 2026-11-01T15:00:01Z\nCompleted At: 2026-11-01T15:00:01Z\nCreated the following subagents:\n{{"conversationId": "{sub1_id}"}}\n{{"conversationId": "{sub2_id}"}}'},
        {"source": "MODEL", "type": "GENERIC", "content": f'Command exited with code 0.\n\nCommand output:\nCreated the following subagents:\n{{"conversationId": "{main_id}"}}'},
    ])
    write_agy_log(sub1_id, [
        {"source": "USER_EXPLICIT", "type": "USER_INPUT", "content": "Check task #42."},
        {"source": "MODEL", "type": "PLANNER_RESPONSE", "input_tokens": 10_000, "cache_read_tokens": 0, "output_tokens": 400},
    ])
    write_agy_log(sub2_id, [
        {"source": "USER_EXPLICIT", "type": "USER_INPUT", "content": "<USER_SETTINGS_CHANGE>Flash</USER_SETTINGS_CHANGE>\ndispatch 1   parts: correctness"},
        {"source": "MODEL", "type": "PLANNER_RESPONSE", "input_tokens": 8_000, "cache_read_tokens": 0, "output_tokens": 200},
    ])

    env = dict(os.environ)
    env.pop("CLAUDE_CODE_SESSION_ID", None)
    env["CLAUDE_CONFIG_DIR"] = os.path.join(tmp, "empty-claude")
    env["ANTIGRAVITY_BRAIN_DIR"] = brain
    env["ANTIGRAVITY_CONVERSATION_ID"] = main_id

    cproc = subprocess.run([sys.executable, CTX, "--json"], capture_output=True, text=True, env=env)
    cdata = json.loads(cproc.stdout)
    check("context picks ANTIGRAVITY_CONVERSATION_ID", cdata["session"] == "aaaaaaaa", cdata)
    check("context sums input_tokens + cache_read_tokens (135k -> AT THE NEXT BOUNDARY)",
          cdata["used"] == 135_000 and cdata["verdict"] == "AT THE NEXT BOUNDARY", cdata)

    uproc = subprocess.run([sys.executable, USAGE, "--json", "--by-stage"], capture_output=True, text=True, env=env)
    udata = json.loads(uproc.stdout)
    check("usage counts main output tokens", udata["main"]["output"] == 500, udata)
    check("usage counts spawned subagent transcripts", udata["subagent_transcripts"] == 2 and udata["subagents"]["output"] == 600, udata)
    check("usage --by-stage identifies 1 triage and 4 reviewer",
          udata["stages"]["1 triage"]["output"] == 400 and udata["stages"]["4 reviewer"]["output"] == 200, udata["stages"])

    # PreInvocation context-nudge emits injectSteps once per band and {} on repeat.
    nenv = dict(env, ANTIGRAVITY_CONFIG_DIR=os.path.join(tmp, "nudge-cfg"))
    nudge_py = os.path.join(ROOT, "hooks", "context-nudge.py")
    np1 = subprocess.run(
        [sys.executable, nudge_py],
        input=json.dumps({"conversationId": main_id}),
        capture_output=True, text=True, env=nenv,
    )
    nj1 = json.loads(np1.stdout)
    check("PreInvocation nudge emits injectSteps on band arrival",
          np1.returncode == 0 and "injectSteps" in nj1
          and "AT THE NEXT BOUNDARY" in nj1["injectSteps"][0]["systemMessage"]["systemMessage"], nj1)
    np2 = subprocess.run(
        [sys.executable, nudge_py],
        input=json.dumps({"conversationId": main_id}),
        capture_output=True, text=True, env=nenv,
    )
    check("PreInvocation nudge stays silent ({}) on same band",
          np2.returncode == 0 and json.loads(np2.stdout) == {}, np2.stdout)

    # Compaction CHECKPOINT resets epoch just like Claude's compact_boundary.
    with open(os.path.join(brain, main_id, ".system_generated", "logs", "transcript.jsonl"), "a", encoding="utf-8") as fh:
        fh.write(json.dumps({"step_index": 9, "source": "SYSTEM", "type": "CHECKPOINT", "content": "# Resuming from a compaction"}) + "\n")
    cproc2 = subprocess.run([sys.executable, CTX, "--json"], capture_output=True, text=True, env=env)
    cdata2 = json.loads(cproc2.stdout)
    check("CHECKPOINT marks session as just_compacted", cdata2["just_compacted"] is True and cdata2["verdict"] == "HOLD", cdata2)

    # kit setup + kit version against ANTIGRAVITY_CONFIG_DIR
    agy_cfg = os.path.join(tmp, "gemini-config")
    bindir = os.path.join(tmp, "bin")
    senv = dict(os.environ, CLAUDE_CONFIG_DIR=os.path.join(tmp, "empty-claude"), ANTIGRAVITY_CONFIG_DIR=agy_cfg)
    sproc = subprocess.run([KIT, "setup", bindir], capture_output=True, text=True, env=senv)
    check("kit setup installs Antigravity plugin when ANTIGRAVITY_CONFIG_DIR is set",
          sproc.returncode == 0 and os.path.isfile(os.path.join(agy_cfg, "plugins", "task-funnel", "plugin.json")),
          sproc.stdout + sproc.stderr)
    vproc = subprocess.run([KIT, "version", VERSION], capture_output=True, text=True, env=senv)
    check("kit version sees the installed Antigravity plugin",
          vproc.returncode == 0 and "up to date" in vproc.stdout, vproc.stdout + vproc.stderr)

    # review-package maps Claude model names to Antigravity enum values under ANTIGRAVITY_AGENT=1
    subprocess.run(["git", "init", "-q", "-b", "main"], cwd=repo_dir, check=True)
    subprocess.run(["git", "config", "user.email", "t@t"], cwd=repo_dir, check=True)
    subprocess.run(["git", "config", "user.name", "t"], cwd=repo_dir, check=True)
    os.makedirs(os.path.join(repo_dir, ".claude"), exist_ok=True)
    with open(os.path.join(repo_dir, ".claude", "funnel.config.json"), "w", encoding="utf-8") as fh:
        json.dump({
            "base": "main",
            "slices": {"all": "origin/main...HEAD"},
            "lenses": {"correctness": {"slice": "all", "docs": []}},
            "effort": {"standard": ["correctness"]},
            "reviewModel": {"standard": "opus"},
        }, fh)
    with open(os.path.join(repo_dir, "a.py"), "w", encoding="utf-8") as fh:
        fh.write("x = 1\n")
    subprocess.run(["git", "add", "-A"], cwd=repo_dir, check=True)
    subprocess.run(["git", "commit", "-q", "-m", "base"], cwd=repo_dir, check=True)
    subprocess.run(["git", "update-ref", "refs/remotes/origin/main", "HEAD"], cwd=repo_dir, check=True)
    with open(os.path.join(repo_dir, "a.py"), "w", encoding="utf-8") as fh:
        fh.write("x = 2\n")
    subprocess.run(["git", "commit", "-am", "change", "-q"], cwd=repo_dir, check=True)
    rproc = subprocess.run(
        [KIT, "review", "standard", "--reset-rounds"],
        cwd=repo_dir, capture_output=True, text=True,
        env=dict(os.environ, ANTIGRAVITY_AGENT="1"),
    )
    check("kit review maps reviewModel opus -> pro under ANTIGRAVITY_AGENT=1",
          rproc.returncode == 0 and "  model pro " in rproc.stdout, rproc.stdout + rproc.stderr)

print(f"\n{PASS} passed, {FAIL} failed")
sys.exit(1 if FAIL else 0)
