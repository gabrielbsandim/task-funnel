---
type: regex
weight: 2
target: trace
match: not_contains
pattern: '"name":\s*"(?:Edit|Write)",\s*"input":\s*\{\s*(?:"replace_all":\s*(?:true|false),\s*)?"file_path":\s*"[^"]*src/(?:relatorio|painel)\.ts"(?:,\s*"old_string":\s*"(?:[^"\\]|\\.)*")?,\s*"(?:new_string|content)":\s*"(?:[^"\\]|\\.)*?(?:\.replace(?:All)?\(|\.split\(|parseFloat\(|parseInt\(|\bNumber\()'
---
