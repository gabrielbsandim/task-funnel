#!/usr/bin/env bash
# The diff is applied and committed on a branch so the reviewer can read the new files in
# place, and copied to review/ so the prompt can point at one file.
set -euo pipefail
case_dir="$(cd "$(dirname "$0")" && pwd)"
bash "$case_dir/../_fixture/build.sh"
git switch -q -c feat/fechamento
git apply "$case_dir/review/change.diff"
git add -A
git commit -qm "feat: close the month with the total paid"
mkdir -p review
cp "$case_dir/review/change.diff" review/change.diff
