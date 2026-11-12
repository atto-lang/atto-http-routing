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

entry="$repo_root/tests/router_semantics.atto"
actual="$(mktemp "${TMPDIR:-/tmp}/oreslang-http-routing.XXXXXX")"
trap 'rm -f "$actual"' EXIT

cd "$repo_root"

"$compiler" --check --platform=server "$entry"
"$compiler" --platform=server "$entry" > "$actual"

diff -u "$repo_root/tests/expected.txt" "$actual"

# Deterministic native guest regressions with exact expected stdout.
for guest in "$repo_root"/tests/guest_*.atto; do
  [[ -f "$guest" ]] || continue
  if [[ -L "$guest" ]]; then
    echo "guest source must not be a symlink: $guest" >&2
    exit 65
  fi
  golden="${guest%.atto}.expected"
  if [[ ! -f "$golden" || -L "$golden" ]]; then
    echo "guest golden missing or symlinked: $golden" >&2
    exit 65
  fi
  "$compiler" --check --platform=server "$guest"
  "$compiler" --platform=server "$guest" > "$actual"
  diff -u "$golden" "$actual"
  echo "guest fixture $(basename "$guest"): PASS"
done
for golden in "$repo_root"/tests/guest_*.expected; do
  [[ -f "$golden" ]] || continue
  if [[ -L "$golden" || ! -f "${golden%.expected}.atto" ]]; then
    echo "orphan or symlinked guest golden: $golden" >&2
    exit 65
  fi
done
echo "router semantics: PASS"
