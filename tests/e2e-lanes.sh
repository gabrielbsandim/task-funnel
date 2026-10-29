#!/usr/bin/env bash
# The three lanes end to end, on the eval fixture with a git directory the
# agent can write. `claude plugin eval` mounts it read-only, so no eval can grade a
# branch, a commit or the review that reads one. Real sessions on your account, about
# US$ 1 to 4 per lane, so this is not in CI.
# Usage: tests/e2e-lanes.sh [trivial|direct|risk|all]   (E2E_BUDGET caps each lane, default 4)
set -u
PLUGIN="$(cd "$(dirname "$0")/.." && pwd)"
LANES="${1:-all}"
[ "$LANES" = all ] && LANES="trivial direct risk"
fail=0
skipped=0

check() {
  if eval "$2"; then printf 'ok    %s\n' "$1"; return; fi
  printf 'FAIL  %s\n' "$1"
  fail=1
}

# One line per event, in order: AGENT <type>, WRITE <path>, READ <path>, MARK <lane>, BASH <command>,
# OUT <tool output line>.
events() {
  python3 - "$1" <<'PY'
import json, re, sys
mark = re.compile(r"<!--\s*funnel:\s*(trivial|direct|risk)\s*-->")
for raw in open(sys.argv[1], encoding="utf8"):
    try:
        event = json.loads(raw)
    except ValueError:
        continue
    for block in (event.get("message") or {}).get("content") or []:
        if not isinstance(block, dict):
            continue
        kind, data = block.get("type"), block.get("input") or {}
        if kind == "tool_use" and block.get("name") == "Agent":
            print("AGENT", (data.get("subagent_type") or "").split(":")[-1])
        if kind == "tool_use" and block.get("name") in ("Edit", "Write"):
            print("WRITE", data.get("file_path", ""))
        if kind == "tool_use" and block.get("name") == "Read":
            print("READ", data.get("file_path", ""))
        if kind == "tool_use":
            for lane in mark.findall(json.dumps(data, ensure_ascii=False)):
                print("MARK", lane)
        if kind == "tool_use" and block.get("name") == "Bash":
            print("BASH", " ".join(data.get("command", "").split()))
        if kind == "tool_result":
            content = block.get("content")
            text = content if isinstance(content, str) else " ".join(
                c.get("text", "") for c in content or [] if isinstance(c, dict))
            for line in text.splitlines():
                print("OUT", line)
PY
}

run_lane() {
  local lane="$1" prompt="$2" root
  root="$(mktemp -d)"
  mkdir "$root/cwd"
  (cd "$root/cwd" && bash "$PLUGIN/evals/_fixture/build.sh" >/dev/null)
  printf '\n== %s lane, in %s\n' "$lane" "$root"
  # Only this plugin: no user settings, plugins, MCP servers, CLAUDE.md or memory, so a
  # rule the run follows is a rule this plugin wrote.
  (cd "$root/cwd" && CLAUDE_CODE_DISABLE_CLAUDE_MDS=1 CLAUDE_CODE_DISABLE_AUTO_MEMORY=1 \
    claude -p "$prompt" --plugin-dir "$PLUGIN" --setting-sources project,local --strict-mcp-config \
    --permission-mode bypassPermissions --output-format stream-json --verbose \
    --max-budget-usd "${E2E_BUDGET:-4}") > "$root/trace.jsonl" 2>&1
  events "$root/trace.jsonl" > "$root/events.txt"
  ROOT="$root" EV="$root/events.txt"
  BRANCH="$(git -C "$root/remote.git" for-each-ref refs/heads --format='%(refname:short)' | grep -vx trunk | head -1)"
  printf 'trace %s/trace.jsonl, pushed branch: %s\n' "$root" "${BRANCH:-none}"
}

shipped() {
  check "stage 5 read ship.md" 'grep -qE "^(READ|BASH) .*skills/task/ship\.md" "$EV"'
  check "the pull request body carries <!-- funnel: $1 -->" "grep -qx 'MARK $1' \"\$EV\""
}

agents() { grep -c "^AGENT $1\$" "$EV"; }
pushed_touches() { [ -n "$BRANCH" ] && git -C "$ROOT/remote.git" log --name-only --format= "trunk..$BRANCH" | grep -qx "$1"; }

node_strips_types() {
  command -v node >/dev/null 2>&1 &&
    node -e 'const [a, b] = process.versions.node.split(".").map(Number); process.exit(a > 22 || (a === 22 && b >= 6) ? 0 : 1)'
}

# Hidden checks: the pushed branch's own code on inputs the prompt never named. $1 is the
# file, $2 a regex for the exported function, $3 a JS array of [label, args, (result) => ok].
hidden() {
  local file="$1" pick="$2" cases="$3" tree verdict label got
  if ! node_strips_types; then
    printf 'SKIP  hidden checks on %s: node %s cannot strip types, 22.6 or newer is needed\n' \
      "$file" "$(node --version 2>/dev/null || echo 'is missing')"
    skipped=$((skipped + 1))
    return
  fi
  tree="$ROOT/hidden"
  mkdir -p "$tree"
  [ -n "$BRANCH" ] && git -C "$ROOT/remote.git" archive "$BRANCH" | tar -x -C "$tree"
  [ -f "$tree/package.json" ] || printf '{"type":"module"}\n' > "$tree/package.json"
  cat > "$ROOT/hidden.mjs" <<'JS'
import { register } from "node:module";
import { pathToFileURL } from "node:url";
import { existsSync } from "node:fs";

// The produced code may import a sibling without its extension, which ESM refuses.
register("data:text/javascript," + encodeURIComponent(
  'export async function resolve(s, c, next) { try { return await next(s, c); } catch (e) { if (!s.startsWith(".")) throw e; return next(s + ".ts", c); } }'));

const [file, pick, source] = process.argv.slice(2);
const near = (r, x) => typeof r === "number" && Math.abs(r - x) < 1e-9;
const cases = new Function("near", `return ${source}`)(near);
const show = (v) => (typeof v === "string" ? JSON.stringify(v) : String(v)).slice(0, 80);
let fn;
let why = "";
try {
  const mod = existsSync(file) ? await import(pathToFileURL(file).href) : {};
  const fns = Object.entries(mod).filter(([, v]) => typeof v === "function");
  const re = new RegExp(pick, "i");
  fn = (fns.find(([k]) => re.test(k)) ?? (fns.length === 1 ? fns[0] : []))[1];
  why = `no exported function matching /${pick}/ (found: ${fns.map(([k]) => k).join(", ") || "none"})`;
} catch (error) {
  why = `cannot load: ${String(error.message).split("\n")[0]}`;
}
for (const [label, args, holds] of cases) {
  if (!fn) {
    console.log(`FAIL\t${label}\t${why}`);
    continue;
  }
  let result;
  try {
    result = fn(...args);
  } catch (error) {
    console.log(`FAIL\t${label}\tthrew ${String(error.message).split("\n")[0]}`);
    continue;
  }
  const passed = holds(result);
  console.log(`${passed ? "PASS" : "FAIL"}\t${label}\t${passed ? "" : `got ${show(result)}`}`);
}
JS
  local n=0
  while IFS=$'\t' read -r verdict label got; do
    n=$((n + 1))
    check "hidden: $label${got:+ ($got)}" '[ "$verdict" = PASS ]'
  done < <(node --experimental-strip-types --no-warnings "$ROOT/hidden.mjs" "$tree/$file" "$pick" "$cases" 2>&1)
  check "the hidden checks on $file printed a verdict" '[ "$n" -gt 0 ]'
}

for lane in $LANES; do
  case "$lane" in
    trivial)
      run_lane trivial 'A mensagem de texto longo esta como "Texto maior que o permitido", e o produto quer "Texto acima do limite permitido". Troca e abre a PR. Commit e push estao autorizados, nao precisa me perguntar.'
      check "a branch off trunk was pushed with src/messages.ts" 'pushed_touches src/messages.ts'
      check "trunk on the remote is untouched" '[ "$(git -C "$ROOT/remote.git" rev-list --count trunk)" = 1 ]'
      check "no funnel agent at all (triage, test writer, reviewer, verifier)" '! grep -qE "^AGENT funnel-(triage|test-writer|reviewer|verifier)$" "$EV"'
      check "no issue was created" '! grep -qE "^BASH .*(issue create|/issues)" "$EV"'
      check "the gates ran" 'grep -qE "^BASH .*(ci/(lint|types|test)\.sh|kit\"? gate)" "$EV"'
      shipped trivial
      ;;
    direct)
      run_lane direct 'A observacao da medicao precisa ser cortada em 500 caracteres, com "..." no fim quando cortar. Cria uma funcao para isso em src/texto.ts e abre a PR. Commit e push estao autorizados, nao precisa me perguntar.'
      check "a branch off trunk was pushed with src/texto.ts" 'pushed_touches src/texto.ts'
      check "trunk on the remote is untouched" '[ "$(git -C "$ROOT/remote.git" rev-list --count trunk)" = 1 ]'
      check "no premise check (funnel-triage) on the direct lane" '[ "$(agents funnel-triage)" = 0 ]'
      check "no funnel-test-writer on the direct lane" '[ "$(agents funnel-test-writer)" = 0 ]'
      check "one review ran (funnel-reviewer dispatched)" '[ "$(agents funnel-reviewer)" -ge 1 ]'
      check "kit review never opened a second round" '! grep -qE "^OUT .*round 2 of" "$EV"'
      shipped direct
      hidden src/texto.ts 'trunc|cort|limit|abrev|resum|encurt|observ' '[
        ["an empty observation stays empty", ["", 500], (r) => r === ""],
        ["a short observation is not cut", ["Concretagem da laje", 500], (r) => r === "Concretagem da laje"],
        ["exactly 500 characters is not cut", ["a".repeat(500), 500], (r) => r === "a".repeat(500)],
        ["501 characters is cut and ends in ...", ["b".repeat(501), 500], (r) => typeof r === "string" && r.endsWith("...") && r.startsWith("b".repeat(497)) && r.length <= 503],
        ["5000 characters come back at most 503 long", ["c".repeat(5000), 500], (r) => typeof r === "string" && r.endsWith("...") && r.length >= 500 && r.length <= 503]
      ]'
      ;;
    risk)
      run_lane risk 'O parseBRL quebra com separador de milhar: "12.500,00" nao vira 12500. Corrige. A spec ja esta aprovada: "12.500,00" vira 12500, "850,00" vira 850, "1.234.567,89" vira 1234567.89, tudo o que hoje ja e lido certo continua igual, e src/medicao.ts nao muda. Pode seguir ate a PR sem me perguntar; commit e push estao autorizados.'
      check "a branch off trunk was pushed with src/money.ts" 'pushed_touches src/money.ts'
      check "trunk on the remote is untouched" '[ "$(git -C "$ROOT/remote.git" rev-list --count trunk)" = 1 ]'
      check "the premise check ran (funnel-triage)" '[ "$(agents funnel-triage)" -ge 1 ]'
      check "tests were written by funnel-test-writer" '[ "$(agents funnel-test-writer)" -ge 1 ]'
      check "the tests came before any edit to src/money.ts" 'grep -nE "^(AGENT funnel-test-writer|WRITE .*src/money\.ts)" "$EV" | head -1 | grep -q funnel-test-writer'
      check "a review ran (funnel-reviewer dispatched)" '[ "$(agents funnel-reviewer)" -ge 1 ]'
      check "kit review never opened a third round" '! grep -qE "^OUT .*round 3 of" "$EV"'
      shipped risk
      hidden src/money.ts '^parseBRL$' '[
        ["parseBRL(\"1.500,00\") is 1500", ["1.500,00"], (r) => near(r, 1500)],
        ["parseBRL(\"0,01\") is 0.01", ["0,01"], (r) => near(r, 0.01)],
        ["parseBRL(\"0,5\") still reads 0.5", ["0,5"], (r) => near(r, 0.5)],
        ["parseBRL(\"1000\") still reads 1000", ["1000"], (r) => near(r, 1000)],
        ["parseBRL(\" 42,10 \") still trims to 42.1", [" 42,10 "], (r) => near(r, 42.1)]
      ]'
      ;;
    *) echo "unknown lane: $lane"; exit 2 ;;
  esac
done

[ "$skipped" -gt 0 ] && echo "SKIPPED $skipped group(s) of hidden checks, see SKIP above"
[ "$fail" -eq 0 ] && echo "OK" || echo "FAILED"
exit "$fail"
