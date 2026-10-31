#!/usr/bin/env bash
set -euo pipefail
root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
tmp="$(mktemp -d "${TMPDIR:-/tmp}/ores-runner.XXXXXX")"
tmp="$(cd "$tmp" && pwd -P)"
trap 'rm -rf "$tmp"' EXIT
project="$tmp/project with spaces"
mkdir -p "$project/scripts" "$project/tests" "$tmp/bin"
cp "$root/scripts/test.sh" "$project/scripts/test.sh"
cp "$root/SOURCE_REF" "$project/SOURCE_REF"
cp "$root/tests/expected.txt" "$project/tests/expected.txt"
cp "$root/tests/expected_adversarial.txt" "$project/tests/expected_adversarial.txt"
cp "$root/tests/router_semantics.ores" "$project/tests/router_semantics.ores"
cp "$root/tests/router_adversarial.ores" "$project/tests/router_adversarial.ores"
cat > "$tmp/bin/compiler" <<'COMPILER'
#!/usr/bin/env bash
set -euo pipefail
test "$PWD" = "$RUNNER_PROJECT"
entry="${@: -1}"
case "$entry" in
  "$RUNNER_PROJECT/tests/router_semantics.ores") suite=router_semantics; expected=expected.txt ;;
  "$RUNNER_PROJECT/tests/router_adversarial.ores") suite=router_adversarial; expected=expected_adversarial.txt ;;
  *) exit 64 ;;
esac
if [[ "$1" = --check ]]; then
  test "$#" = 3
  test "$2" = --platform=server
  echo "check:$suite" >> "$RUNNER_LOG"
  [[ "${RUNNER_CASE:-}" != check-failure ]] || exit 42
else
  test "$#" = 2
  test "$1" = --platform=server
  echo "run:$suite" >> "$RUNNER_LOG"
  [[ "${RUNNER_CASE:-}" != runtime-failure ]] || exit 43
  if [[ "${RUNNER_CASE:-}" = wrong-output ]]; then
    echo incorrect
  else
    cat "$RUNNER_PROJECT/tests/$expected"
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
test "$(cat "$RUNNER_LOG")" = $'check:router_semantics\nrun:router_semantics\ncheck:router_adversarial\nrun:router_adversarial'
for scenario in check-failure runtime-failure wrong-output; do
  : > "$RUNNER_LOG"
  if RUNNER_CASE="$scenario" bash "$project/scripts/test.sh" > "$tmp/output" 2>&1; then
    echo "runner accepted $scenario" >&2
    exit 1
  fi
  if [[ "$scenario" = check-failure ]]; then
    test "$(cat "$RUNNER_LOG")" = check:router_semantics
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
echo "runner contracts: PASS"
