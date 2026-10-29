#!/usr/bin/env python3
"""Proves `kit design` flags each interface defect in the lines a branch adds, and nothing else.

    python3 tests/test-design.py

Every rule gets a case that must be flagged and one that must pass: a design check
with a false positive is a check somebody switches off. The ratchet cases put the
defect in the base, where it is not this branch's to fix.
"""
import json
import os
import shutil
import subprocess
import sys
import tempfile

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
KIT = os.path.join(ROOT, "scripts", "kit")
PASS, FAIL = 0, []
TOKENS = {"base": "main", "ui": {"tokens": ["src/styles/tokens.css"]}}
TOKEN_FILE = ":root {\n  --blue: #3b82f6;\n  --space-3: 12px;\n}\n"
REDUCE = "@media (prefers-reduced-motion: reduce) {\n  .a { transition: none; }\n}\n"


def check(name, ok, detail=""):
    global PASS
    if ok:
        PASS += 1
        return
    FAIL.append(f"{name}: {detail}")


def git(root, *args):
    subprocess.run(["git", *args], cwd=root, check=True, capture_output=True)


def write(root, path, text):
    full = os.path.join(root, path)
    os.makedirs(os.path.dirname(full), exist_ok=True)
    with open(full, "w") as handle:
        handle.write(text)


def repo(files, config):
    root = tempfile.mkdtemp(prefix="kit-design-")
    git(root, "init", "-q", "-b", "main")
    git(root, "config", "user.email", "t@t")
    git(root, "config", "user.name", "t")
    write(root, ".claude/funnel.config.json", json.dumps(config))
    write(root, "keep.txt", "x\n")
    for path, text in files.items():
        write(root, path, text)
    git(root, "add", "-A")
    git(root, "commit", "-q", "-m", "base")
    git(root, "update-ref", "refs/remotes/origin/main", "HEAD")
    return root


def case(name, added, want, rules=(), absent=(), base=None, path="src/components/a.css",
         config=None, extra=None, commit=True, args=(), says=None):
    """Writes `added` after the base text of `path`, runs kit design, checks exit and rule ids."""
    base_files = dict(base or {})
    root = repo(base_files, config or {"base": "main"})
    try:
        write(root, path, base_files.get(path, "") + added)
        for other, text in (extra or {}).items():
            write(root, other, text)
        if commit:
            git(root, "add", "-A")
            git(root, "commit", "-q", "-m", "change")
        out = subprocess.run([KIT, "design", *args], cwd=root, capture_output=True, text=True)
        text = out.stdout + out.stderr
        check(name, out.returncode == want, f"exit {out.returncode}, want {want}\n{text}")
        for rule in rules:
            check(f"{name}, reports {rule}", f"  {rule}  " in text, text)
        for rule in absent:
            check(f"{name}, not {rule}", f"  {rule}  " not in text, text)
        if says:
            check(f"{name}, says {says!r}", says in text, text)
        return text
    finally:
        shutil.rmtree(root, ignore_errors=True)


# gradient-text
case("background-clip text over a gradient", ".t {\n  background: linear-gradient(90deg, red, blue);\n"
     "  -webkit-background-clip: text;\n}\n", 1, ["gradient-text"])
case("Tailwind bg-clip-text over a gradient",
     '<h1 className="bg-gradient-to-r from-sky-500 to-blue-500 bg-clip-text">x</h1>\n', 1,
     ["gradient-text"], path="src/components/A.tsx")
case("background-clip text on a flat colour passes", ".t {\n  background-clip: text;\n  color: red;\n}\n", 0)

# side-tab
case("a 4px coloured left border", ".card {\n  border-left: 4px solid #6366f1;\n}\n", 1, ["side-tab"],
     says="4px")
case("Tailwind border-l-4", '<div className="border-l-4 border-blue-500 p-4">x</div>\n', 1, ["side-tab"],
     path="src/components/A.tsx")
case("a neutral left border passes", ".card {\n  border-left: 4px solid #e5e7eb;\n}\n", 0)
case("a 2px left border on a square card passes", ".card {\n  border-left: 2px solid #6366f1;\n}\n", 0)
case("Tailwind border-l-2 on a square box passes", '<div className="border-l-2 p-4">x</div>\n', 0,
     path="src/components/A.tsx")

# bounce-easing
case("an overshooting cubic-bezier", ".a {\n  transition: transform 0.3s cubic-bezier(0.68, -0.55, 0.265, 1.55);\n}\n"
     + REDUCE, 1, ["bounce-easing"], says="-0.55")
case("Tailwind animate-bounce", '<div className="animate-bounce motion-reduce:animate-none">x</div>\n', 1,
     ["bounce-easing"], path="src/components/A.tsx")
case("an ease that dips below the start", ".a {\n  transition: transform 0.3s cubic-bezier(0.6, -0.28, 0.735, 0.045);\n}\n"
     + REDUCE, 1, ["bounce-easing"])
case("an ease that overshoots the end", ".a {\n  transition: transform 0.3s cubic-bezier(0.175, 0.885, 0.32, 1.275);\n}\n"
     + REDUCE, 1, ["bounce-easing"])
case("a curve inside impeccable's 0.1 tolerance passes",
     ".a {\n  transition: transform 0.3s cubic-bezier(0.4, 1.05, 0.6, 1);\n}\n" + REDUCE, 0)
case("a standard ease passes",".a {\n  transition: transform 0.3s cubic-bezier(0.4, 0, 0.2, 1);\n}\n" + REDUCE, 0)

# tiny-text
case("10px body text", "p {\n  font-size: 10px;\n}\n", 1, ["tiny-text"], says="12px floor")
case("Tailwind text-[11px] on a paragraph", '<p className="text-[11px]">fine print</p>\n', 1, ["tiny-text"],
     path="src/components/A.tsx")
case("12px body text passes", "p {\n  font-size: 12px;\n}\n", 0)
case("an 11px button label passes the control floor", "button {\n  font-size: 11px;\n}\n", 0)
case("a 10px button label fails the control floor", "button {\n  font-size: 10px;\n}\n", 1, ["tiny-text"],
     says="11px floor")

# tight-leading
case("1.1 leading on a paragraph", "p {\n  line-height: 1.1;\n}\n", 1, ["tight-leading"], says="1.10x")
case("Tailwind leading-tight on small body text", '<p className="leading-tight text-sm">x</p>\n', 1,
     ["tight-leading"], path="src/components/A.tsx")
case("1.5 leading passes", "p {\n  line-height: 1.5;\n}\n", 0)
case("a heading keeps its tight leading", "h1 {\n  line-height: 1.1;\n}\n", 0)
case("display-size text keeps its tight leading", ".hero {\n  font-size: 32px;\n  line-height: 1.1;\n}\n", 0)

# wide-tracking
case("0.1em tracking on body text", "p {\n  letter-spacing: 0.1em;\n}\n", 1, ["wide-tracking"])
case("Tailwind tracking-widest on a paragraph", '<p className="tracking-widest">x</p>\n', 1,
     ["wide-tracking"], path="src/components/A.tsx")
case("0.02em tracking passes", "p {\n  letter-spacing: 0.02em;\n}\n", 0)
case("an uppercase eyebrow keeps wide tracking",
     ".eyebrow {\n  text-transform: uppercase;\n  letter-spacing: 0.1em;\n}\n", 0)

# off-token
token_base = {"src/styles/tokens.css": TOKEN_FILE}
case("a colour one off a token", ".a {\n  color: #3b82f7;\n}\n", 1, ["off-token"], base=token_base,
     config=TOKENS, says="--blue")
case("a colour equal to a token", ".a {\n  color: #3b82f6;\n}\n", 1, ["off-token"], base=token_base,
     config=TOKENS, says="use var(--blue)")
case("a length within half a pixel of a token", ".a {\n  padding: 12.4px;\n}\n", 1, ["off-token"],
     base=token_base, config=TOKENS, says="--space-3")
case("token use and an unrelated length pass", ".a {\n  color: var(--blue);\n  padding: 20px;\n}\n", 0,
     base=token_base, config=TOKENS)
case("off-token is skipped without ui.tokens", ".a {\n  color: #3b82f7;\n}\n", 0, base=token_base)

# img-alt
case("an img without alt", '<img src="/a.png" />\n', 1, ["img-alt"], path="src/components/A.tsx",
     says="without alt")
case("an img without src", '<img alt="A cat" />\n', 1, ["img-alt"], path="src/components/A.tsx",
     says="without src")
case("an img with src and empty alt passes", '<img src="/a.png" alt="" />\n', 0, path="src/components/A.tsx")
case("an img tag across lines passes", '<img\n  src="/a.png"\n  alt="A cat"\n/>\n', 0,
     path="src/components/A.tsx")

# outline-none
case("outline none with no focus-visible", ".a:focus {\n  outline: none;\n}\n", 1, ["outline-none"])
case("Tailwind outline-none with no focus-visible", '<button className="focus:outline-none">x</button>\n', 1,
     ["outline-none"], path="src/components/A.tsx")
case("outline none beside a focus-visible style passes",
     ".a:focus {\n  outline: none;\n}\n.a:focus-visible {\n  box-shadow: 0 0 0 2px var(--ring);\n}\n", 0)
case("Tailwind focus-visible ring passes",
     '<button className="focus:outline-none focus-visible:ring-2">x</button>\n', 0, path="src/components/A.tsx")

# motion-no-reduce
case("a transition in a file with no reduced-motion", ".a {\n  transition: opacity 0.2s ease;\n}\n", 1,
     ["motion-no-reduce"])
case("Tailwind transition with no motion-reduce", '<div className="transition-colors">x</div>\n', 1,
     ["motion-no-reduce"], path="src/components/A.tsx")
case("a transition beside a reduced-motion block passes",
     ".a {\n  transition: opacity 0.2s ease;\n}\n" + REDUCE, 0)
case("Tailwind motion-reduce passes",
     '<div className="transition-colors motion-reduce:transition-none">x</div>\n', 0, path="src/components/A.tsx")
case("a reduced-motion block the base already has counts", ".b {\n  transition: opacity 0.2s;\n}\n", 0,
     base={"src/components/a.css": REDUCE})
out = case("one finding per file, with the count", ".a { transition: opacity 0.2s; }\n"
           ".b { transition: color 0.2s; }\n@keyframes spin { to { opacity: 1; } }\n", 1,
           ["motion-no-reduce"], says="2 more added line(s)")
check("one finding per file, exactly one row", out.count("  motion-no-reduce  ") == 1, out)

# ignores
case("an ignore with evidence silences its rule",
     "/* design-ignore: side-tab who decided: brand spec v3, Ana in design review */\n"
     ".card { border-left: 4px solid #6366f1; }\n", 0)
case("an ignore on the same line silences its rule",
     ".card { border-left: 4px solid #6366f1; } /* design-ignore: side-tab who decided: brand spec v3 */\n", 0)
case("an ignore with no who decided is bad and silences nothing",
     "/* design-ignore: side-tab */\n.card { border-left: 4px solid #6366f1; }\n", 1, ["bad-ignore", "side-tab"])
case("an ignore with empty evidence is bad",
     "/* design-ignore: side-tab who decided: */\n.card { border-left: 4px solid #6366f1; }\n", 1,
     ["bad-ignore", "side-tab"])
case("an ignore for another rule silences nothing",
     "/* design-ignore: tiny-text who decided: brand spec */\n.card { border-left: 4px solid #6366f1; }\n", 1,
     ["side-tab"], absent=["bad-ignore"])
case("an ignore naming an unknown rule is bad",
     "/* design-ignore: nope who decided: brand spec */\n.a { color: red; }\n", 1, ["bad-ignore"])

# token-to-silence
case("a near-copy token minted for an off literal",
     ".a {\n  color: #3b82f7;\n}\n", 1, ["off-token", "token-to-silence"], base=token_base, config=TOKENS,
     extra={"src/styles/tokens.css": TOKEN_FILE.replace("}", "  --blue-2: #3b82f7;\n}")}, says="--blue-2")
case("a near-copy token used through var() is still caught",
     ".a {\n  color: var(--blue-2);\n}\n", 1, ["token-to-silence"], absent=["off-token"], base=token_base,
     config=TOKENS, extra={"src/styles/tokens.css": TOKEN_FILE.replace("}", "  --blue-2: #3b82f7;\n}")})
case("a genuinely new token used through var() passes",
     ".a {\n  color: var(--green);\n}\n", 0, base=token_base, config=TOKENS,
     extra={"src/styles/tokens.css": TOKEN_FILE.replace("}", "  --green: #22c55e;\n}")})

# the ratchet: only what the branch adds
legacy = "p {\n  font-size: 9px;\n  letter-spacing: 0.2em;\n}\n.a:focus {\n  outline: none;\n}\n"
case("an inherited violation on an untouched line is not reported", ".b {\n  color: red;\n}\n", 0,
     base={"src/components/a.css": legacy})
case("an added violation beside inherited ones is reported alone", "small {\n  font-size: 9px;\n}\n", 1,
     ["tiny-text"], absent=["wide-tracking", "outline-none"], base={"src/components/a.css": legacy})
case("an uncommitted new file is judged", "p {\n  font-size: 9px;\n}\n", 1, ["tiny-text"],
     path="src/components/new.css", commit=False)

# scope
case("a file outside the screen globs is skipped", "p {\n  font-size: 9px;\n}\n", 0, path="lib/a.css",
     says="no changed screen file")
case("a repo's own screen globs apply", "p {\n  font-size: 9px;\n}\n", 1, ["tiny-text"], path="web/ui/a.css",
     config={"base": "main", "browser": {"screenGlobs": ["web/ui/**"]}})
case("a test file under the globs is skipped", '<p className="text-[9px]">x</p>\n', 0,
     path="src/components/A.test.tsx")

# output
out = case("--json carries the findings", "p {\n  font-size: 9px;\n}\n", 1, args=["--json"])
try:
    rows = json.loads(out)["findings"]
    check("--json has the row", [r["rule"] for r in rows] == ["tiny-text"] and rows[0]["line"] == 2, out)
except ValueError:
    check("--json parses", False, out)
case("ui.detectCmd output is appended", "p {\n  font-size: 14px;\n}\n", 0,
     config={"base": "main", "ui": {"detectCmd": "echo '{\"extra\": 1}'"}}, says="== ui.detectCmd")
case("a missing ui.detectCmd never fails", "p {\n  font-size: 14px;\n}\n", 0,
     config={"base": "main", "ui": {"detectCmd": "kit-design-no-such-detector"}}, says="not installed")

print(f"{PASS} passed, {len(FAIL)} failed")
for line in FAIL:
    print(f"  FAIL {line}")
sys.exit(1 if FAIL else 0)
