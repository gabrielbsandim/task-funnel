---
type: regex
weight: 2
target: trace
pattern: '^(?:(?!"name":\s*"(?:Edit|Write)",\s*"input":\s*\{\s*(?:"replace_all":\s*(?:true|false),\s*)?"file_path":\s*"[^"]*src/(?:format/numero|relatorio|painel)\.ts")[\s\S])*?(?:"name":\s*"Grep",\s*"input":\s*\{[^}]*?(?:parseNumero|format/numero)|"name":\s*"Read",\s*"input":\s*\{[^}]*?src/painel\.ts|"name":\s*"Bash",\s*"input":\s*\{\s*"command":\s*"(?:[^"\\]|\\.)*?(?:\b(?:grep|rg|ag)\b(?:[^"\\]|\\.)*?(?:parseNumero|format/numero)|src/painel\.ts|src/\*(?:\.ts)?\b))'
---
