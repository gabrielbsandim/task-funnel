#!/usr/bin/env bash
# A small React + TypeScript app with tokens, two house components and a sibling list
# screen, all under browser.screenGlobs and off risk.paths. Nothing is installed: the
# cases grade what the agent wrote. The sibling swallows a failed fetch into the empty
# state on purpose, so copying it is not enough to meet the states floor.
set -e
ROOT="$(pwd)"
mkdir -p .claude ci docs src/app/obras src/components src/lib src/styles "$ROOT/../remote.git"

git init -q --bare "$ROOT/../remote.git"
git init -q -b trunk .
git config user.email eval@example.com
git config user.name eval

for gate in lint types test; do printf '#!/bin/sh\n' > "ci/$gate.sh"; done
cat >> ci/lint.sh <<'GATE'
if grep -rn "console.log" src; then echo "lint: console.log is not allowed in src"; exit 1; fi
GATE
cat >> ci/types.sh <<'GATE'
grep -q "export async function listarMedicoes" src/lib/medicoes.ts || { echo "types: listarMedicoes is missing"; exit 1; }
GATE
cat >> ci/test.sh <<'GATE'
grep -q "export function Button" src/components/Button.tsx || { echo "test: Button is missing"; exit 1; }
GATE

cat > .claude/funnel.config.json <<'CFG'
{
  "base": "trunk",
  "docs": { "entry": "docs/flow.md", "pipeline": "docs/flow.md" },
  "worktree": { "path": "../obra-{issue}", "setup": [], "skipSetupWhenDocOnly": true },
  "gates": {
    "lint":  { "cmd": "sh ci/lint.sh" },
    "types": { "cmd": "sh ci/types.sh" },
    "test":  { "cmd": "sh ci/test.sh" }
  },
  "stages": {
    "implement_first_pass": ["lint", "types", "test"],
    "tests": ["test"],
    "ship": ["lint", "types", "test"]
  },
  "slices": {
    "src": "origin/trunk...HEAD -- src",
    "all": "origin/trunk...HEAD"
  },
  "lenses": {
    "correctness": { "slice": "src", "docs": [] }
  },
  "effort": { "light": ["correctness"], "standard": ["correctness"], "deep": ["correctness"] },
  "lanes": {
    "direct": { "effort": "light", "maxRounds": 1 },
    "risk": { "effort": "deep", "maxRounds": 2 }
  },
  "risk": { "paths": ["src/lib/auth.ts"] },
  "browser": {
    "enabled": false,
    "baseUrl": "http://localhost:3000",
    "start": "npm run dev",
    "appDir": "src/app",
    "screenGlobs": ["src/app/**", "src/components/**"]
  },
  "ledger": false
}
CFG

printf '.playwright-mcp/\nnode_modules/\n.next/\n' > .gitignore

cat > docs/flow.md <<'DOC'
# Flow
One task, one branch, one pull request. Never commit or push to trunk.
Before a push, every gate in .claude/funnel.config.json must be green.
Screens use the tokens in src/styles/tokens.css and the components in src/components.
DOC

cat > package.json <<'JSON'
{
  "name": "obra-web",
  "private": true,
  "scripts": { "dev": "next dev", "build": "next build" },
  "dependencies": { "next": "15.1.0", "react": "19.0.0", "react-dom": "19.0.0" },
  "devDependencies": { "@types/react": "19.0.0", "typescript": "5.7.2" }
}
JSON

cat > tsconfig.json <<'JSON'
{
  "compilerOptions": {
    "target": "ES2022",
    "module": "esnext",
    "moduleResolution": "bundler",
    "jsx": "preserve",
    "strict": true,
    "noEmit": true,
    "paths": { "@/*": ["./src/*"] }
  },
  "include": ["src"]
}
JSON

cat > src/styles/tokens.css <<'CSS'
:root {
  --color-bg: #ffffff;
  --color-surface: #f5f6f8;
  --color-border: #d9dde3;
  --color-text: #1b1f24;
  --color-muted: #5b6470;
  --color-primary: #0b5fff;
  --color-primary-hover: #094ad1;
  --color-danger: #c62828;
  --color-danger-hover: #a31f1f;
  --color-focus: #0b5fff;

  --space-1: 4px;
  --space-2: 8px;
  --space-3: 12px;
  --space-4: 16px;
  --space-6: 24px;

  --radius-sm: 4px;
  --radius-md: 8px;

  --font-size-sm: 14px;
  --font-size-md: 16px;
  --font-size-lg: 20px;

  --motion-fast: 150ms;
  --motion-base: 200ms;
  --ease-standard: cubic-bezier(0.2, 0, 0, 1);
}
CSS

cat > src/app/layout.tsx <<'SRC'
import type { ReactNode } from "react";
import "../styles/tokens.css";

export default function RootLayout({ children }: { children: ReactNode }) {
  return (
    <html lang="pt-BR">
      <body>{children}</body>
    </html>
  );
}
SRC

cat > src/components/Button.tsx <<'SRC'
import type { ButtonHTMLAttributes } from "react";
import styles from "./Button.module.css";

type Variant = "primary" | "secondary" | "danger";

export function Button({
  variant = "primary",
  className,
  ...props
}: ButtonHTMLAttributes<HTMLButtonElement> & { variant?: Variant }) {
  const classes = [styles.button, styles[variant], className].filter(Boolean).join(" ");
  return <button type="button" className={classes} {...props} />;
}
SRC

cat > src/components/Button.module.css <<'CSS'
.button {
  padding: var(--space-2) var(--space-4);
  border: 1px solid transparent;
  border-radius: var(--radius-sm);
  font-size: var(--font-size-sm);
  cursor: pointer;
  transition: background-color var(--motion-fast) var(--ease-standard);
}
.button:focus-visible {
  outline: 2px solid var(--color-focus);
  outline-offset: 2px;
}
.button:disabled {
  opacity: 0.6;
  cursor: not-allowed;
}
.primary { background: var(--color-primary); color: var(--color-bg); }
.primary:hover:not(:disabled) { background: var(--color-primary-hover); }
.secondary { background: var(--color-bg); color: var(--color-text); border-color: var(--color-border); }
.danger { background: var(--color-danger); color: var(--color-bg); }
.danger:hover:not(:disabled) { background: var(--color-danger-hover); }
@media (prefers-reduced-motion: reduce) {
  .button { transition: none; }
}
CSS

cat > src/components/EmptyState.tsx <<'SRC'
import type { ReactNode } from "react";
import styles from "./EmptyState.module.css";

export function EmptyState({
  title,
  description,
  action,
}: {
  title: string;
  description?: string;
  action?: ReactNode;
}) {
  return (
    <section className={styles.empty} aria-live="polite">
      <h2 className={styles.title}>{title}</h2>
      {description && <p className={styles.description}>{description}</p>}
      {action}
    </section>
  );
}
SRC

cat > src/components/EmptyState.module.css <<'CSS'
.empty {
  display: grid;
  gap: var(--space-2);
  justify-items: start;
  padding: var(--space-6);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-md);
  background: var(--color-surface);
}
.title { margin: 0; font-size: var(--font-size-md); color: var(--color-text); }
.description { margin: 0; font-size: var(--font-size-sm); color: var(--color-muted); }
CSS

cat > src/lib/obras.ts <<'SRC'
export interface Obra {
  id: string;
  nome: string;
  cidade: string;
}

export async function listarObras(): Promise<Obra[]> {
  const res = await fetch("/api/obras");
  if (!res.ok) throw new Error(`Falha ao carregar obras (${res.status})`);
  return res.json();
}
SRC

cat > src/lib/medicoes.ts <<'SRC'
export interface Medicao {
  id: string;
  obra: string;
  periodo: string;
  valor: number;
  status: "rascunho" | "enviada" | "aprovada";
}

export async function listarMedicoes(): Promise<Medicao[]> {
  const res = await fetch("/api/medicoes");
  if (!res.ok) throw new Error(`Falha ao carregar medicoes (${res.status})`);
  return res.json();
}

export async function excluirMedicao(id: string): Promise<void> {
  const res = await fetch(`/api/medicoes/${id}`, { method: "DELETE" });
  if (!res.ok) throw new Error(`Falha ao excluir medicao (${res.status})`);
}
SRC

cat > src/app/obras/page.tsx <<'SRC'
"use client";

import { useEffect, useState } from "react";
import { Button } from "../../components/Button";
import { EmptyState } from "../../components/EmptyState";
import { listarObras, type Obra } from "../../lib/obras";
import styles from "./obras.module.css";

export default function ObrasPage() {
  const [obras, setObras] = useState<Obra[] | null>(null);

  useEffect(() => {
    listarObras()
      .then(setObras)
      .catch(() => setObras([]));
  }, []);

  if (obras === null) return <p className={styles.status}>Carregando obras...</p>;

  if (obras.length === 0) {
    return (
      <EmptyState
        title="Nenhuma obra cadastrada"
        description="As obras cadastradas aparecem aqui."
        action={<Button>Cadastrar obra</Button>}
      />
    );
  }

  return (
    <main className={styles.page}>
      <h1 className={styles.title}>Obras</h1>
      <ul className={styles.list}>
        {obras.map((obra) => (
          <li key={obra.id} className={styles.row}>
            <span className={styles.name}>{obra.nome}</span>
            <span className={styles.meta}>{obra.cidade}</span>
          </li>
        ))}
      </ul>
    </main>
  );
}
SRC

cat > src/app/obras/obras.module.css <<'CSS'
.page { display: grid; gap: var(--space-4); padding: var(--space-6); }
.title { margin: 0; font-size: var(--font-size-lg); color: var(--color-text); }
.status { padding: var(--space-6); color: var(--color-muted); }
.list { display: grid; gap: var(--space-2); margin: 0; padding: 0; list-style: none; }
.row {
  display: flex;
  justify-content: space-between;
  gap: var(--space-3);
  padding: var(--space-3) var(--space-4);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-md);
  background: var(--color-bg);
}
.name { min-width: 0; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; color: var(--color-text); }
.meta { color: var(--color-muted); font-size: var(--font-size-sm); }
CSS

git add -A
git commit -qm "chore: obras screen, tokens and house components"
git remote add origin "$ROOT/../remote.git"
git push -q origin trunk
