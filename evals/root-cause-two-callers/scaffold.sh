#!/usr/bin/env bash
# The fixture plus a shared parser with a thousands-separator bug and two callers in two
# files, all off risk.paths. The prompt names the symptom in one caller only.
set -e
bash "$(dirname "$0")/../_fixture/build.sh"
mkdir -p src/format

cat > src/format/numero.ts <<'SRC'
// Quantities come from the form as Brazilian text: "1.500,00" or "12,5".
export function parseNumero(text: string): number {
  return parseFloat(text.trim().replace(",", "."));
}
SRC

cat > src/relatorio.ts <<'SRC'
import { parseNumero } from "./format/numero";

export interface Lancamento {
  material: string;
  quantidade: string;
  unidade: string;
}

export function linhaRelatorio(l: Lancamento): string {
  return `${l.material}: ${parseNumero(l.quantidade)} ${l.unidade}`;
}
SRC

cat > src/painel.ts <<'SRC'
import { parseNumero } from "./format/numero";
import type { Lancamento } from "./relatorio";

export function totalPorMaterial(lancamentos: Lancamento[], material: string): number {
  return lancamentos
    .filter((l) => l.material === material)
    .reduce((soma, l) => soma + parseNumero(l.quantidade), 0);
}
SRC

git add -A
git commit -qm "feat: material consumption report and dashboard"
git push -q origin trunk
