#!/usr/bin/env bash
set -euo pipefail

repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
: "${ORESLANG_SOURCE_DIR:?Set ORESLANG_SOURCE_DIR to the pinned clean Java compiler checkout}"
expected_ref="$(tr -d '[:space:]' < "$repo_root/SOURCE_REF")"
actual_ref="$(git -C "$ORESLANG_SOURCE_DIR" rev-parse HEAD)"
if [[ "$expected_ref" != "$actual_ref" ]]; then
  echo "Pinned compiler mismatch: $actual_ref != $expected_ref" >&2
  exit 65
fi
if [[ -n "$(git -C "$ORESLANG_SOURCE_DIR" status --porcelain --untracked-files=all)" ]]; then
  echo "Compiler checkout is dirty" >&2
  exit 65
fi
compiler="${ORESLANG_COMPILER:-$repo_root/scripts/compiler.sh}"
entry="$repo_root/tests/router_generation_authority.atto"
actual="$(mktemp "${TMPDIR:-/tmp}/atto-generation-auth.XXXXXX")"
trap 'rm -f "$actual"' EXIT
"$compiler" --check --platform=server "$entry"
"$compiler" --platform=server "$entry" > "$actual"
# Required same-runtime snapshot regression: ten true lines, no exceptions.
# Never invert the assertion or accept the vulnerable six-false baseline.
# This is NOT a test of supervisor/cross-isolate runtime-minted authority.
diff -u "$repo_root/tests/router_generation_authority.expected.txt" "$actual"
echo "router generation authority: PASS"
