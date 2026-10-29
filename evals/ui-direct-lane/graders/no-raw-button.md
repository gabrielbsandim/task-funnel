---
type: regex
weight: 1
target: trace
match: not_contains
pattern: '"name":\s*"(?:Edit|Write)",\s*"input":\s*\{\s*(?:"replace_all":\s*(?:true|false),\s*)?"file_path":\s*"[^"]*src/app/medicoes/[^"]*"(?:,\s*"old_string":\s*"(?:[^"\\]|\\.)*")?,\s*"(?:new_string|content)":\s*"(?:[^"\\]|\\.)*?<button[\s>]'
---
