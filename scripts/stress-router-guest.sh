#!/usr/bin/env bash
# Repeated fresh-JVM Atto router baseline execution; NEVER retry-until-green.
set -euo pipefail

root="$(cd "$(dirname "$0")/.." && pwd -P)"
attempts=32
if [[ -v ROUTER_STRESS_ATTEMPTS ]]; then attempts="$ROUTER_STRESS_ATTEMPTS"; fi
limit=30
if [[ -v ROUTER_STRESS_TIMEOUT_SECONDS ]]; then limit="$ROUTER_STRESS_TIMEOUT_SECONDS"; fi
compiler="$root/scripts/compiler.sh"
if [[ -v ORESLANG_COMPILER ]]; then compiler="$ORESLANG_COMPILER"; fi
if [[ ! -v ORESLANG_SOURCE_DIR || -z "$ORESLANG_SOURCE_DIR" ]]; then
  echo "Provide ORESLANG_SOURCE_DIR as a pinned clean compiler checkout" >&2
  exit 64
fi
pin="$(tr -d '[:space:]' < "$root/SOURCE_REF")"
if [[ ! "$attempts" =~ ^[0-9]{1,3}$ ]] || (( 10#$attempts < 1 || 10#$attempts > 128 )); then
  echo "ROUTER_STRESS_ATTEMPTS must be 1..128" >&2; exit 64
fi
if [[ ! "$limit" =~ ^[0-9]{1,3}$ ]] || (( 10#$limit < 5 || 10#$limit > 120 )); then
  echo "ROUTER_STRESS_TIMEOUT_SECONDS must be 5..120" >&2; exit 64
fi
if ! command -v timeout >/dev/null 2>&1; then
  echo "GNU timeout is required (Linux runner)" >&2; exit 69
fi
if ! command -v "$compiler" >/dev/null 2>&1 && [[ ! -x "$compiler" ]]; then
  echo "Cannot execute pinned compiler: $compiler" >&2; exit 69
fi
if [[ ! "$pin" =~ ^[0-9a-f]{40}$ ]]; then
  echo "SOURCE_REF must be a full lowercase SHA" >&2; exit 65
fi
source_root="$(cd "$ORESLANG_SOURCE_DIR" && pwd -P)"
if [[ "$(git -C "$source_root" rev-parse --show-toplevel)" != "$source_root" ]]; then
  echo "Compiler source must be its own Git checkout" >&2; exit 65
fi
if [[ "$(git -C "$source_root" rev-parse HEAD)" != "$pin" ]]; then
  echo "Compiler HEAD does not match SOURCE_REF" >&2; exit 65
fi
source_status="$(git -C "$source_root" status --porcelain --untracked-files=all)" || {
  echo "Cannot inspect compiler source cleanliness" >&2
  exit 65
}
if [[ -n "$source_status" ]]; then
  echo "Compiler source must be clean" >&2; exit 65
fi

entry="$root/tests/router_semantics.atto"
golden="$root/tests/expected.txt"
if [[ ! -f "$entry" || -L "$entry" || ! -f "$golden" || -L "$golden" ]]; then
  echo "Missing or symlinked baseline guest/golden" >&2; exit 65
fi
# Bind BOTH baseline inputs to independently reviewed source Git blobs.
# A clean Java checkout alone does not prevent a replaced Router fixture or
# edited expected output from producing an undeserved green stress receipt.
expected_guest_blob=7f004e9e55def28ca568b0b12c2fb7e24c3124a5
expected_golden_blob=5ab1d42fbbf25e670dd4c0c763e17017f9d64d28
guest_blob="$(git hash-object -- "$entry")" || exit 65
golden_blob="$(git hash-object -- "$golden")" || exit 65
if [[ "$guest_blob" != "$expected_guest_blob" || "$golden_blob" != "$expected_golden_blob" ]]; then
  echo "Router guest/golden does not match independently pinned Git blobs" >&2
  exit 65
fi
printf 'ROUTER_BASELINE_GUEST_BLOB=%s\nROUTER_BASELINE_GOLDEN_BLOB=%s\n' \
  "$guest_blob" "$golden_blob"
tmp_base=/tmp
if [[ -v TMPDIR ]]; then tmp_base="$TMPDIR"; fi
tmp="$(mktemp -d "$tmp_base/atto-router-stack-stress.XXXXXX")"
trap 'rm -rf "$tmp"' EXIT
cd "$root"

for ((i=1; i<=attempts; i++)); do
  : > "$tmp/stdout"
  : > "$tmp/stderr"
  if timeout --signal=TERM --kill-after=5s "$limit" "$compiler" --platform=server "$entry" >"$tmp/stdout" 2>"$tmp/stderr"; then
    :
  else
    status=$?
    if grep -Fq "StackOverflowError" "$tmp/stderr"; then
      echo "STACK_OVERFLOW on fresh JVM iteration $i/$attempts (exit $status)" >&2
    elif (( status == 124 || status == 137 )); then
      echo "TIMEOUT or forced kill on iteration $i/$attempts (exit $status)" >&2
    else
      echo "Native guest failed on iteration $i/$attempts (exit $status)" >&2
    fi
    tail -n 65 "$tmp/stderr" >&2
    exit 1
  fi
  if ! diff -u "$golden" "$tmp/stdout" > "$tmp/diff"; then
    echo "Golden stdout mismatch on iteration $i/$attempts" >&2
    sed -n '1,80p' "$tmp/diff" >&2
    exit 1
  fi
  if grep -Fq "StackOverflowError" "$tmp/stderr"; then
    echo "STACK_OVERFLOW in stderr despite zero exit on iteration $i/$attempts" >&2
    tail -n 65 "$tmp/stderr" >&2
    exit 1
  fi
  echo "ROUTER_FRESH_JVM_BASELINE_$i"_PASS
done
echo "ROUTER_STRESS_$attempts"_FRESH_JVM_GUEST_PASSES
