---
type: regex
weight: 1
target: trace
match: not_contains
pattern: '"name":\s*"(?:Edit|Write)",\s*"input":\s*\{\s*(?:"replace_all":\s*(?:true|false),\s*)?"file_path":\s*"[^"]*src/(?:app|components)/[^"]*"(?:,\s*"old_string":\s*"(?:[^"\\]|\\.)*")?,\s*"(?:new_string|content)":\s*"(?!(?:[^"\\]|\\.)*?focus-visible)(?:[^"\\]|\\.)*?outline(?::\s*\\?"?(?:none|0)\b|-none\b)'
---
