#!/usr/bin/env bash
set -euo pipefail
root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
tmp="$(mktemp -d "${TMPDIR:-/tmp}/ores-runner.XXXXXX")"
tmp="$(cd "$tmp" && pwd -P)"
trap 'rm -rf "$tmp"' EXIT
project="$tmp/project with spaces"
mkdir -p "$project/scripts" "$project/tests/edge_cases" "$tmp/bin"
cp "$root/scripts/test.sh" "$project/scripts/test.sh"
cp "$root/scripts/run-guest.py" "$project/scripts/run-guest.py"
cp "$root/scripts/bounded_process.py" "$project/scripts/bounded_process.py"
cp "$root/SOURCE_REF" "$project/SOURCE_REF"
cp "$root/tests/expected.txt" "$project/tests/expected.txt"
cp "$root/tests/router_semantics.ores" "$project/tests/router_semantics.ores"
# Copy the independent edge suite into the ephemeral runner fixture. Without
# this, the fail-closed inventory in scripts/test.sh rejects the host test.
cp "$root/tests/edge_cases/"*.ores "$root/tests/edge_cases/"*.expected "$project/tests/edge_cases/"
cat > "$tmp/bin/compiler" <<'COMPILER'
#!/usr/bin/env bash
set -euo pipefail
test "$PWD" = "$RUNNER_PROJECT"
input="${@: -1}"
case "$input" in
  "$RUNNER_PROJECT"/tests/router_semantics.ores|"$RUNNER_PROJECT"/tests/edge_cases/*.ores) ;;
  *) echo "unrecognized guest fixture" >&2; exit 65 ;;
esac
if [[ "$1" = --check ]]; then
  test "$#" = 3
  test "$2" = --platform=server
  echo check >> "$RUNNER_LOG"
  [[ "${RUNNER_CASE:-}" != check-failure ]] || exit 42
else
  test "$#" = 2
  test "$1" = --platform=server
  echo run >> "$RUNNER_LOG"
  [[ "${RUNNER_CASE:-}" != runtime-failure ]] || exit 43
  if [[ "${RUNNER_CASE:-}" = wrong-output ]]; then
    echo incorrect
  else
    if [[ "$input" == "$RUNNER_PROJECT/tests/router_semantics.ores" ]]; then
      cat "$RUNNER_PROJECT/tests/expected.txt"
    else
      cat "${input%.ores}.expected"
    fi
  fi
fi
COMPILER
chmod +x "$tmp/bin/compiler"
export RUNNER_PROJECT="$project" RUNNER_LOG="$tmp/invocations"
export ORESLANG_COMPILER="$tmp/bin/compiler"
unset ORESLANG_SOURCE_DIR
cd "$tmp"
if bash "$project/scripts/test.sh" > "$tmp/output" 2>&1; then
  echo "missing compiler source provenance accepted" >&2
  exit 1
fi
grep -q 'Set ORESLANG_SOURCE_DIR' "$tmp/output"
mkdir "$tmp/source"
git -C "$tmp/source" init -q
printf 'compiler\n' > "$tmp/source/tracked"
git -C "$tmp/source" add tracked
git -C "$tmp/source" -c user.name=Runner -c user.email=runner@example.invalid commit -qm fixture
git -C "$tmp/source" rev-parse HEAD > "$project/SOURCE_REF"
export ORESLANG_SOURCE_DIR="$tmp/source"
bash "$project/scripts/test.sh"
test "$(cat "$RUNNER_LOG")" = $'check\nrun\ncheck\nrun\ncheck\nrun\ncheck\nrun'
for scenario in check-failure runtime-failure wrong-output; do
  : > "$RUNNER_LOG"
  if RUNNER_CASE="$scenario" bash "$project/scripts/test.sh" > "$tmp/output" 2>&1; then
    echo "runner accepted $scenario" >&2
    exit 1
  fi
  if [[ "$scenario" = check-failure ]]; then
    test "$(cat "$RUNNER_LOG")" = check
  fi
done
if ORESLANG_COMPILER="$tmp/missing" bash "$project/scripts/test.sh" > "$tmp/output" 2>&1; then
  echo "missing compiler accepted" >&2
  exit 1
fi
printf 'main\n' > "$project/SOURCE_REF"
if bash "$project/scripts/test.sh" > "$tmp/output" 2>&1; then
  echo "floating compiler revision accepted" >&2
  exit 1
fi
grep -q 'full lowercase Git commit SHA' "$tmp/output"
git -C "$tmp/source" rev-parse HEAD > "$project/SOURCE_REF"
ORESLANG_SOURCE_DIR="$tmp/source" bash "$project/scripts/test.sh"
printf 'dirty\n' >> "$tmp/source/tracked"
if ORESLANG_SOURCE_DIR="$tmp/source" bash "$project/scripts/test.sh" > "$tmp/output" 2>&1; then
  echo "dirty compiler checkout accepted" >&2
  exit 1
fi
grep -q 'must be clean' "$tmp/output"
git -C "$tmp/source" restore tracked
# A failed status command must not be mistaken for an empty/clean status.
git() {
  if [[ "$*" == *" status "* ]]; then return 128; fi
  command git "$@"
}
export -f git
if bash "$project/scripts/test.sh" > "$tmp/output" 2>&1; then
  echo "unreadable compiler status accepted" >&2
  exit 1
fi
grep -q 'cannot inspect compiler checkout status' "$tmp/output"
unset -f git

# Security-negative fixture inventory cases. Each must be rejected before a
# mock compiler is invoked, and the temporary fixture must be restored.
: > "$RUNNER_LOG"
mv "$project/tests/edge_cases/head-options.expected" "$tmp/saved-expected"
if bash "$project/scripts/test.sh" > "$tmp/output" 2>&1; then
  echo "missing edge expectation accepted" >&2; exit 1
fi
grep -q "incomplete router edge fixture inventory" "$tmp/output"
test ! -s "$RUNNER_LOG"
mv "$tmp/saved-expected" "$project/tests/edge_cases/head-options.expected"

: > "$RUNNER_LOG"
printf 'true\n' > "$project/tests/edge_cases/orphan.expected"
if bash "$project/scripts/test.sh" > "$tmp/output" 2>&1; then
  echo "orphan edge expectation accepted" >&2; exit 1
fi
grep -q "incomplete router edge fixture inventory" "$tmp/output"
test ! -s "$RUNNER_LOG"
rm "$project/tests/edge_cases/orphan.expected"

: > "$RUNNER_LOG"
mv "$project/tests/edge_cases/limits-failclosed.ores" "$tmp/saved-guest"
ln -s "$tmp/saved-guest" "$project/tests/edge_cases/limits-failclosed.ores"
if bash "$project/scripts/test.sh" > "$tmp/output" 2>&1; then
  echo "symlinked edge guest accepted" >&2; exit 1
fi
test ! -s "$RUNNER_LOG"
rm "$project/tests/edge_cases/limits-failclosed.ores"
mv "$tmp/saved-guest" "$project/tests/edge_cases/limits-failclosed.ores"

: > "$RUNNER_LOG"
ln -s "$tmp/source" "$tmp/source-link"
if ORESLANG_SOURCE_DIR="$tmp/source-link" bash "$project/scripts/test.sh" > "$tmp/output" 2>&1; then
  echo "symlinked compiler source accepted" >&2; exit 1
fi
grep -q "compiler source directory must not be a symlink" "$tmp/output"
test ! -s "$RUNNER_LOG"

: > "$RUNNER_LOG"
mv "$project/SOURCE_REF" "$tmp/saved-pin"
ln -s "$tmp/saved-pin" "$project/SOURCE_REF"
if bash "$project/scripts/test.sh" > "$tmp/output" 2>&1; then
  echo "symlinked compiler pin accepted" >&2; exit 1
fi
grep -q "SOURCE_REF must be a regular non-symlink file" "$tmp/output"
test ! -s "$RUNNER_LOG"
rm "$project/SOURCE_REF"
mv "$tmp/saved-pin" "$project/SOURCE_REF"
# Bounded helper is a trusted executable input; a symlink is never a safe
# substitute, even when it points at a nominally identical script.
: > "$RUNNER_LOG"
mv "$project/scripts/run-guest.py" "$tmp/saved-run-guest"
ln -s "$tmp/saved-run-guest" "$project/scripts/run-guest.py"
if bash "$project/scripts/test.sh" > "$tmp/output" 2>&1; then
  echo "symlinked bounded runner accepted" >&2
  exit 1
fi
grep -q "unsafe or missing bounded guest runner" "$tmp/output"
test ! -s "$RUNNER_LOG"
rm "$project/scripts/run-guest.py"
mv "$tmp/saved-run-guest" "$project/scripts/run-guest.py"

: > "$RUNNER_LOG"
mv "$project/scripts/bounded_process.py" "$tmp/saved-bounded"
ln -s "$tmp/saved-bounded" "$project/scripts/bounded_process.py"
if bash "$project/scripts/test.sh" > "$tmp/output" 2>&1; then
  echo "symlinked bounded helper accepted" >&2
  exit 1
fi
grep -q "unsafe or missing bounded guest runner" "$tmp/output"
test ! -s "$RUNNER_LOG"
rm "$project/scripts/bounded_process.py"
mv "$tmp/saved-bounded" "$project/scripts/bounded_process.py"

# Zero-byte guest files are not legitimate executable fixtures, even with
# a matching nonempty oracle, and must fail before mock compiler dispatch.
: > "$RUNNER_LOG"
mv "$project/tests/edge_cases/head-options.ores" "$tmp/saved-edge-source"
: > "$project/tests/edge_cases/head-options.ores"
if bash "$project/scripts/test.sh" > "$tmp/output" 2>&1; then
  echo "empty edge guest accepted" >&2; exit 1
fi
grep -q "missing, unsafe or empty router edge fixture" "$tmp/output"
test ! -s "$RUNNER_LOG"
rm "$project/tests/edge_cases/head-options.ores"
mv "$tmp/saved-edge-source" "$project/tests/edge_cases/head-options.ores"

: > "$RUNNER_LOG"
mv "$project/tests/router_semantics.ores" "$tmp/saved-legacy-source"
: > "$project/tests/router_semantics.ores"
if bash "$project/scripts/test.sh" > "$tmp/output" 2>&1; then
  echo "empty legacy guest accepted" >&2; exit 1
fi
grep -q "unsafe or missing router legacy fixture" "$tmp/output"
test ! -s "$RUNNER_LOG"
rm "$project/tests/router_semantics.ores"
mv "$tmp/saved-legacy-source" "$project/tests/router_semantics.ores"

: > "$RUNNER_LOG"
mv "$project/tests/edge_cases/head-options.expected" "$tmp/saved-edge-output"
: > "$project/tests/edge_cases/head-options.expected"
if bash "$project/scripts/test.sh" > "$tmp/output" 2>&1; then
  echo "empty edge expectation accepted" >&2; exit 1
fi
grep -q "missing, unsafe or empty router edge fixture" "$tmp/output"
test ! -s "$RUNNER_LOG"
rm "$project/tests/edge_cases/head-options.expected"
mv "$tmp/saved-edge-output" "$project/tests/edge_cases/head-options.expected"

: > "$RUNNER_LOG"
mv "$project/scripts/run-guest.py" "$tmp/saved-helper"
if bash "$project/scripts/test.sh" > "$tmp/output" 2>&1; then
  echo "missing bounded runner accepted" >&2; exit 1
fi
grep -q "unsafe or missing bounded guest runner" "$tmp/output"
test ! -s "$RUNNER_LOG"
mv "$tmp/saved-helper" "$project/scripts/run-guest.py"

echo "runner contracts: PASS"
