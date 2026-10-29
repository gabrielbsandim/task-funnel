---
type: regex
weight: 2
target: trace
match: not_contains
pattern: '"name":\s*"(?:Edit|Write)",\s*"input":\s*\{\s*(?:"replace_all":\s*(?:true|false),\s*)?"file_path":\s*"[^"]*src/(?:app|components)/[^"]*"(?:,\s*"old_string":\s*"(?:[^"\\]|\\.)*")?,\s*"(?:new_string|content)":\s*"(?:[^"\\]|\\.)*?(?:\bconfirm\(|(?:>(?:\s|\\[nt])*|=\{?\\"|\{\\")(?:OK|Ok|Yes|Sim|Submit|Enviar|Confirm|Confirmar)(?:(?:\s|\\[nt])*<|\\"))'
---
