#!/bin/sh
# Stable entry point for the context nudge. Copy this one file to a path that does
# not move, and register that path:
#
#   cp hooks/context-nudge.sh ~/.claude/hooks/
#   # then in settings.json:
#   "UserPromptSubmit": [{ "hooks": [
#     { "type": "command", "timeout": 20,
#       "command": "sh ~/.claude/hooks/context-nudge.sh" }]}]
#
# The Python half lives under a directory named after the version, so registering
# it directly would pin the hook to one release and make the hook itself the next
# thing that silently goes stale.
#
# Exits 0 with no output when there is nothing installed. A prompt is never the
# place to fail.
h=$(ls -d "${CLAUDE_CONFIG_DIR:-$HOME/.claude}"/plugins/cache/*/task-funnel/*/hooks/context-nudge.py 2>/dev/null |
  sort -V | tail -1)
if [ -z "$h" ] && { [ -n "${ANTIGRAVITY_CONFIG_DIR:-}" ] || [ -z "${CLAUDE_CONFIG_DIR:-}" ]; }; then
  agy_h="${ANTIGRAVITY_CONFIG_DIR:-$HOME/.gemini/config}/plugins/task-funnel/hooks/context-nudge.py"
  [ -f "$agy_h" ] && h="$agy_h"
fi
[ -n "$h" ] || exit 0
exec python3 "$h"
