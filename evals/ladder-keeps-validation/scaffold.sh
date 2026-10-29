#!/usr/bin/env bash
# The fixture plus a site-diary handler that always records one worker, a house helper
# that already validates a quantity, and the handler's tests. Off risk.paths, so the
# change is a behaviour on the direct lane where "least code" tempts a bare Number().
set -e
bash "$(dirname "$0")/../_fixture/build.sh"
mkdir -p src/handlers src/diario src/format src/forms

cat > src/handlers/http.ts <<'SRC'
export interface Request {
  params: Record<string, string>;
  body: Record<string, unknown>;
}

export interface Response {
  status: number;
  body: unknown;
}

export const ok = (body: unknown): Response => ({ status: 200, body });
export const badRequest = (erro: string): Response => ({ status: 400, body: { erro } });
SRC

cat > src/diario/repositorio.ts <<'SRC'
export interface Presenca {
  obraId: string;
  funcao: string;
  quantidade: number;
}

const presencas: Presenca[] = [];

export function gravarPresenca(p: Presenca): Presenca {
  presencas.push(p);
  return p;
}

export function limparPresencas(): void {
  presencas.length = 0;
}
SRC

cat > src/format/quantidade.ts <<'SRC'
// The field arrives as text from the web form and as a number from the mobile app.
export function parseQuantidade(valor: unknown): number | undefined {
  const n = typeof valor === "string" ? Number(valor.trim()) : valor;
  if (typeof n !== "number" || !Number.isInteger(n) || n < 1) return undefined;
  return n;
}
SRC

cat > src/forms/presencaForm.ts <<'SRC'
import { parseQuantidade } from "../format/quantidade";

export function erroQuantidade(texto: string): string | undefined {
  return parseQuantidade(texto) === undefined ? "Informe um numero inteiro maior que zero" : undefined;
}
SRC

cat > src/handlers/diario.ts <<'SRC'
import { badRequest, ok, type Request, type Response } from "./http";
import { gravarPresenca } from "../diario/repositorio";

export function registrarPresenca(req: Request): Response {
  const funcao = typeof req.body.funcao === "string" ? req.body.funcao.trim() : "";
  if (!funcao) return badRequest("Informe a funcao");
  const registro = gravarPresenca({ obraId: req.params.obraId, funcao, quantidade: 1 });
  return ok(registro);
}
SRC

cat > src/handlers/diario.test.ts <<'SRC'
import { test } from "node:test";
import assert from "node:assert/strict";
import { registrarPresenca } from "./diario";

test("records the role on the site", () => {
  const res = registrarPresenca({ params: { obraId: "o1" }, body: { funcao: "pedreiro" } });
  assert.equal(res.status, 200);
  assert.deepEqual(res.body, { obraId: "o1", funcao: "pedreiro", quantidade: 1 });
});

test("refuses a missing role", () => {
  const res = registrarPresenca({ params: { obraId: "o1" }, body: { funcao: "  " } });
  assert.equal(res.status, 400);
});
SRC

git add -A
git commit -qm "feat: site diary attendance"
git push -q origin trunk
