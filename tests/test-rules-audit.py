#!/usr/bin/env python3
"""kit rules-audit checks line budgets, rigid-rule overload, and cross-layer conflicts.

    python3 tests/test-rules-audit.py
"""
import json
import os
import subprocess
import sys
import tempfile

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SCRIPT = os.path.join(ROOT, "scripts", "rules-audit")
KIT = os.path.join(ROOT, "scripts", "kit")

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


def write_file(path, text):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as fh:
        fh.write(text)


def run_audit(project, env=None, args=None, use_kit=False):
    cmd = [KIT, "rules-audit"] if use_kit else [sys.executable, SCRIPT]
    cmd += ["--project", project, *(args or [])]
    proc = subprocess.run(
        cmd,
        capture_output=True,
        text=True,
        env={**os.environ, **(env or {})},
    )
    return proc.stdout, proc.stderr, proc.returncode


# 1. Clean repo passes --strict and reports zero conflicts
with tempfile.TemporaryDirectory() as tmp:
    cfg = os.path.join(tmp, "cfg")
    proj = os.path.join(tmp, "clean_repo")
    write_file(os.path.join(cfg, "CLAUDE.md"), "# Global\nPrefer small diffs.\n")
    write_file(os.path.join(proj, "CLAUDE.md"), "# Repo\nRun tests before commit.\nAlways use pnpm.\n")
    write_file(os.path.join(proj, ".claude", "skills", "dev", "SKILL.md"),
               "# Dev skill\nAlways use pnpm, not npm.\nNever skip tests.\n")
    out, err, code = run_audit(proj, env={"CLAUDE_CONFIG_DIR": cfg}, args=["--json", "--strict"], use_kit=True)
    check("1 clean repo exits 0 under kit rules-audit --strict", code == 0, err + out)
    data = json.loads(out)
    check("1 clean repo counts 1 root rigid word", data["root_rigid_count"] == 1, data)
    check("1 clean repo counts skill rigid words without alerting",
          data["layers"]["repo-skills"]["rigid"] == 2 and not data["alerts"]["rigid_over_budget"], data)
    check("1 agreeing pnpm directives produce no tool conflict", len(data["contradictions"]) == 0, data["contradictions"])

# 2. @imports, line budget alert, rigid-word code-stripping (EN + PT), and alerts
with tempfile.TemporaryDirectory() as tmp:
    cfg = os.path.join(tmp, "cfg")
    proj = os.path.join(tmp, "rigid_repo")
    write_file(os.path.join(cfg, "CLAUDE.md"), "# Global\nNunca edite producao.\n")
    write_file(os.path.join(proj, "docs", "extra.md"), "\n".join(f"- item {i}" for i in range(15)) + "\n")
    write_file(os.path.join(proj, "CLAUDE.md"), (
        "# Root\n"
        "@docs/extra.md\n"
        "Never skip lint.\n"
        "Always check types.\n"
        "Obrigatorio rodar testes.\n"
        "Inline code `never always must` must not count thrice, only once outside.\n"
        "```sh\n"
        "never always must forbidden nunca sempre\n"
        "```\n"
    ))
    write_file(os.path.join(proj, "skills", "heavy", "SKILL.md"),
               "# Skill\n" + "\n".join("NEVER MUST ALWAYS" for _ in range(10)) + "\n")
    out, err, code = run_audit(
        proj,
        env={"CLAUDE_CONFIG_DIR": cfg},
        args=["--max-lines", "20", "--max-rigid", "4", "--json", "--strict"],
    )
    check("2 strict exits 1 on budget/rigid alerts", code == 1, err + out)
    data = json.loads(out)
    check("2 @import lines included in always-loaded count", data["always_loaded_lines"] > 20, data["always_loaded_lines"])
    check("2 code blocks and inline code stripped from rigid count", data["root_rigid_count"] == 5, data)
    check("2 alerts triggered for lines and root rigid",
          data["alerts"]["lines_over_budget"] and data["alerts"]["rigid_over_budget"], data["alerts"])

# 3. Contradiction detection: units (30 fps vs 60 fps), tools (pnpm vs npm), and polarity
with tempfile.TemporaryDirectory() as tmp:
    cfg = os.path.join(tmp, "cfg")
    proj = os.path.join(tmp, "conflict_repo")
    mem_dir = os.path.join(tmp, "mem")
    write_file(os.path.join(cfg, "CLAUDE.md"), "# Global\n")
    write_file(os.path.join(proj, "CLAUDE.md"), (
        "## Video\n"
        "- Always use 30 fps for reels.\n"
        "- Always use pnpm for installs.\n"
        "- Never edit `schema.prisma` directly.\n"
    ))
    write_file(os.path.join(proj, ".claude", "skills", "video", "SKILL.md"), (
        "## Render\n"
        "- Render at 60 fps in MP4.\n"
        "- Always run npm install first.\n"
    ))
    write_file(os.path.join(mem_dir, "MEMORY.md"), (
        "- Always edit `schema.prisma` before running migrations.\n"
    ))
    out, err, code = run_audit(
        proj,
        env={"CLAUDE_CONFIG_DIR": cfg},
        args=["--memory-dir", mem_dir, "--json", "--strict"],
    )
    check("3 strict exits 1 when contradictions exist", code == 1, err)
    data = json.loads(out)
    kinds = {c["kind"] for c in data["contradictions"]}
    summaries = " | ".join(c["summary"] for c in data["contradictions"])
    check("3 detects unit conflict (30 fps vs 60 fps)", "unit-conflict" in kinds and "30 fps vs 60 fps" in summaries, summaries)
    check("3 detects tool conflict (pnpm vs npm)", "tool-conflict" in kinds and "pnpm vs npm" in summaries, summaries)
    check("3 detects polarity conflict on backticked identifier", "polarity-conflict" in kinds and "schema.prisma" in summaries, summaries)

    md_out, _, md_code = run_audit(proj, env={"CLAUDE_CONFIG_DIR": cfg}, args=["--memory-dir", mem_dir])
    check("3 non-strict exits 0 and prints markdown headings",
          md_code == 0 and "## Layers" in md_out and "## Contradiction candidates" in md_out, md_out[:300])

print()
if failures:
    print(f"{len(failures)} failed: {', '.join(failures)}")
    sys.exit(1)
print(f"all passed ({passes} cases)")
