#!/usr/bin/env bash
# Exact-source native acceptance entrypoint (not a CI receipt by itself).
set -euo pipefail

repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd -P)"
: "${ORESLANG_SOURCE_DIR:?Set ORESLANG_SOURCE_DIR to the approved compiler checkout}"
source_dir="$(cd "$ORESLANG_SOURCE_DIR" && pwd -P)"
: "${ROUTER_EXPECTED_HEAD:?Set ROUTER_EXPECTED_HEAD to the full reviewed PR-head SHA}"
if [[ ! "$ROUTER_EXPECTED_HEAD" =~ ^[0-9a-f]{40}$ ]]; then
  echo "ROUTER_EXPECTED_HEAD must be a full lowercase SHA" >&2
  exit 65
fi
router_actual="$(git -C "$repo_root" rev-parse HEAD)"
if [[ "$router_actual" != "$ROUTER_EXPECTED_HEAD" ]]; then
  echo "wrong router head: actual=$router_actual expected=$ROUTER_EXPECTED_HEAD" >&2
  exit 65
fi
router_status="$(git -C "$repo_root" status --porcelain --untracked-files=all)" || {
  echo "cannot inspect router checkout status" >&2
  exit 65
}
if [[ -n "$router_status" ]]; then
  echo "router checkout is dirty; refusing exact-head acceptance" >&2
  exit 65
fi
expected_ref="$(tr -d '[:space:]' < "$repo_root/SOURCE_REF")"

if [[ ! "$expected_ref" =~ ^[0-9a-f]{40}$ ]]; then
  echo "SOURCE_REF is not an immutable 40-digit SHA" >&2
  exit 65
fi
if [[ "$(git -C "$source_dir" rev-parse --show-toplevel)" != "$source_dir" ]]; then
  echo "compiler source must be its own checkout root" >&2
  exit 65
fi
actual_ref="$(git -C "$source_dir" rev-parse HEAD)"
if [[ "$actual_ref" != "$expected_ref" ]]; then
  echo "wrong compiler source: actual=$actual_ref expected=$expected_ref" >&2
  exit 65
fi
source_status="$(git -C "$source_dir" status --porcelain --untracked-files=all)" || {
  echo "cannot inspect compiler checkout status" >&2
  exit 65
}
if [[ -n "$source_status" ]]; then
  echo "compiler checkout is dirty; refusing native acceptance" >&2
  exit 65
fi
command -v mvn >/dev/null || { echo "Maven required" >&2; exit 69; }
command -v java >/dev/null || { echo "Java required" >&2; exit 69; }
echo "ROUTER_CHECKOUT=$(git -C "$repo_root" rev-parse HEAD)"
echo "ROUTER_TREE=$(git -C "$repo_root" rev-parse 'HEAD^{tree}')"
echo "COMPILER_SOURCE=$actual_ref"
echo "COMPILER_TREE=$(git -C "$source_dir" rev-parse 'HEAD^{tree}')"
mvn -version
java -version

# Rebuild bytecode from the exact pinned source; never trust cached artifacts
# from another revision. Maven dependencies and JDK should also be attested
# by the executor, and this script does not attest their provenance.
(
  cd "$source_dir"
  mvn -q -DskipTests clean package dependency:build-classpath \
    -Dmdep.outputFile=target/classpath.txt
)
if [[ ! -f "$source_dir/target/classpath.txt" ||
      ! -d "$source_dir/target/classes" ]]; then
  echo "pinned compiler build did not produce launcher artifacts" >&2
  exit 69
fi
export ORESLANG_SOURCE_DIR="$source_dir"
export ORESLANG_COMPILER="$repo_root/scripts/compiler.sh"
bash "$repo_root/scripts/test.sh"
echo "native router acceptance: executed on pinned compiler checkout $expected_ref"
