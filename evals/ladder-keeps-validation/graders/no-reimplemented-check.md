---
type: regex
weight: 1
target: trace
match: not_contains
pattern: '"name":\s*"(?:Edit|Write)",\s*"input":\s*\{\s*(?:"replace_all":\s*(?:true|false),\s*)?"file_path":\s*"[^"]*src/handlers/[^"]*(?<!\.test)\.ts"(?:,\s*"old_string":\s*"(?:[^"\\]|\\.)*")?,\s*"(?:new_string|content)":\s*"(?:[^"\\]|\\.)*?(?:Number\.isInteger|Number\.isNaN|\bisNaN\(|parseInt\(|parseFloat\(|\bNumber\(|Math\.(?:floor|trunc|round)\()'
---
