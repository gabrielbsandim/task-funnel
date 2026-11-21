#!/usr/bin/env bash
set -euo pipefail
git init -q -b main .
cat > CLAUDE.md <<'EOF'
# shop-api

- Run the tests with `npm test` before saying a change is done.
- Money is stored in cents, as integers.
EOF
printf '{ "name": "shop-api", "packageManager": "pnpm@9.12.0", "scripts": { "test": "vitest run" } }\n' > package.json
printf 'lockfileVersion: 9.0\n' > pnpm-lock.yaml
mkdir -p sessions
u() { printf '{"type":"user","timestamp":"%s","message":{"role":"user","content":%s}}\n' "$1" "$(python3 -c 'import json,sys;print(json.dumps(sys.argv[1]))' "$2")"; }
tu() { printf '{"type":"assistant","message":{"role":"assistant","content":[{"type":"tool_use","id":"%s","name":"Bash","input":{"command":"npm test"}}]}}\n' "$1"; }
te() { printf '{"type":"user","toolUseResult":"e","message":{"role":"user","content":[{"type":"tool_result","tool_use_id":"%s","is_error":true,"content":"Exit code 1\\nnpm ERR! code ENOWORKSPACES"}]}}\n' "$1"; }
{ u 2026-11-03T10:00:00Z "adiciona desconto por cupom no checkout"; tu t1; te t1
  u 2026-11-03T10:20:00Z "nao, aqui e pnpm: roda pnpm test, o npm quebra por causa do workspace"; } > sessions/a1f0-checkout.jsonl
{ u 2026-11-06T09:00:00Z "o sandbox do gateway de pagamento esta fora do ar hoje, pula o teste de integracao so por agora"
  u 2026-11-06T09:30:00Z "corrige o arredondamento do frete"; } > sessions/b2c7-frete.jsonl
{ u 2026-11-10T14:00:00Z "cria o endpoint de reembolso"; tu t2; te t2
  u 2026-11-10T14:15:00Z "de novo o npm test... e pnpm test nesse repo, ja falei"; } > sessions/c9d4-reembolso.jsonl
touch -d 2026-11-03T10:30:00Z sessions/a1f0-checkout.jsonl
touch -d 2026-11-06T09:40:00Z sessions/b2c7-frete.jsonl
touch -d 2026-11-10T14:20:00Z sessions/c9d4-reembolso.jsonl
