#!/usr/bin/env bash
set -euo pipefail

repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
expected_ref="$(tr -d '[:space:]' < "$repo_root/SOURCE_REF")"
if [[ ! "$expected_ref" =~ ^[0-9a-f]{40}$ ]]; then
  echo "SOURCE_REF must contain a full lowercase Git commit SHA" >&2
  exit 65
fi
compiler="${ORESLANG_COMPILER:-oreslang-compiler}"

if ! command -v "$compiler" >/dev/null 2>&1 && [[ ! -x "$compiler" ]]; then
  echo "oreslang compiler not found: $compiler" >&2
  echo "set ORESLANG_COMPILER to an executable built from SOURCE_REF=$expected_ref" >&2
  exit 69
fi

: "${ORESLANG_SOURCE_DIR:?Set ORESLANG_SOURCE_DIR to the SOURCE_REF compiler checkout}"
if [[ -n "$ORESLANG_SOURCE_DIR" ]]; then
  if [[ "$(git -C "$ORESLANG_SOURCE_DIR" rev-parse --show-toplevel)" != "$(cd "$ORESLANG_SOURCE_DIR" && pwd -P)" ]]; then
    echo "ORESLANG_SOURCE_DIR must be its own Git checkout" >&2
    exit 65
  fi
  source_status="$(git -C "$ORESLANG_SOURCE_DIR" status --porcelain --untracked-files=all)" || {
    echo "cannot inspect compiler checkout status" >&2
    exit 65
  }
  if [[ -n "$source_status" ]]; then
    echo "compiler source checkout must be clean" >&2
    exit 65
  fi
  actual_ref="$(git -C "$ORESLANG_SOURCE_DIR" rev-parse HEAD)"
  if [[ "$actual_ref" != "$expected_ref" ]]; then
    echo "ORESLANG_SOURCE_DIR is at $actual_ref" >&2
    echo "expected SOURCE_REF $expected_ref" >&2
    exit 65
  fi
fi

entry="$repo_root/tests/router_semantics.ores"
actual="$(mktemp "${TMPDIR:-/tmp}/oreslang-http-routing.XXXXXX")"
trap 'rm -f "$actual"' EXIT

cd "$repo_root"

"$compiler" --check --platform=server "$entry"
"$compiler" --platform=server "$entry" > "$actual"

diff -u "$repo_root/tests/expected.txt" "$actual"
echo "router semantics: PASS"

# The edge matrix is intentionally separate from the legacy monolithic
# semantics guest. Enforce paired, non-symlink fixtures before running any
# new guest so tests cannot silently disappear or escape the checkout.
edge_dir="$repo_root/tests/edge_cases"
[[ -d "$edge_dir" && ! -L "$edge_dir" ]] || {
  echo "unsafe or missing router edge fixture directory" >&2
  exit 65
}
shopt -s nullglob
edge_sources=("$edge_dir"/*.ores)
edge_expected=("$edge_dir"/*.expected)
(( ${#edge_sources[@]} >= 3 && ${#edge_sources[@]} == ${#edge_expected[@]} )) || {
  echo "incomplete router edge fixture inventory" >&2
  exit 65
}
for source in "${edge_sources[@]}"; do
  expected="${source%.ores}.expected"
  [[ -f "$source" && ! -L "$source" && -f "$expected" && ! -L "$expected" && -s "$expected" ]] || {
    echo "missing, unsafe or empty router edge fixture: $source" >&2
    exit 65
  }
done
for expected in "${edge_expected[@]}"; do
  [[ -f "${expected%.expected}.ores" && ! -L "${expected%.expected}.ores" ]] || {
    echo "orphan router edge expectation: $expected" >&2
    exit 65
  }
done
for source in "${edge_sources[@]}"; do
  expected="${source%.ores}.expected"
  "$compiler" --check --platform=server "$source"
  "$compiler" --platform=server "$source" > "$actual"
  diff -u "$expected" "$actual"
  echo "router edge: $(basename "$source") PASS"
done
