#!/usr/bin/env bash
set -euo pipefail

repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
source_ref="$(tr -d '[:space:]' < "$repo_root/SOURCE_REF")"
managed_source="$repo_root/.cache/oreslang-source.java"
sibling_source="$repo_root/../oreslang-source.java"

if [[ ! "$source_ref" =~ ^[0-9a-f]{40}$ ]]; then
  echo "SOURCE_REF must contain one 40-character git SHA" >&2
  exit 64
fi

bash "$repo_root/scripts/audit.sh"

resolve_source() {
  if [[ -n "${ORESLANG_SOURCE_DIR:-}" ]]; then
    if [[ ! -f "$ORESLANG_SOURCE_DIR/pom.xml" ]]; then
      echo "ORESLANG_SOURCE_DIR does not contain pom.xml: $ORESLANG_SOURCE_DIR" >&2
      exit 66
    fi
    printf '%s\n' "$ORESLANG_SOURCE_DIR"
    return
  fi

  if [[ -f "$sibling_source/pom.xml" ]] \
    && [[ "$(git -C "$sibling_source" rev-parse HEAD 2>/dev/null || true)" == "$source_ref" ]]; then
    printf '%s\n' "$sibling_source"
    return
  fi

  mkdir -p "$repo_root/.cache"

  if [[ ! -f "$managed_source/pom.xml" ]]; then
    if [[ -d "$sibling_source/.git" ]]; then
      git clone --quiet --no-checkout "$sibling_source" "$managed_source"
      upstream="$(git -C "$sibling_source" remote get-url origin 2>/dev/null || true)"
      if [[ -n "$upstream" ]]; then
        git -C "$managed_source" remote set-url origin "$upstream"
      fi
    elif command -v gh >/dev/null 2>&1; then
      gh repo clone ores-truffle-oreslang/oreslang-source.java "$managed_source"
    else
      echo "Need a pinned oreslang-source.java checkout; install gh or set ORESLANG_SOURCE_DIR" >&2
      exit 69
    fi
  fi

  if ! git -C "$managed_source" cat-file -e "$source_ref^{commit}" 2>/dev/null; then
    git -C "$managed_source" fetch --quiet origin "$source_ref"
  fi

  git -C "$managed_source" checkout --quiet --detach "$source_ref"
  printf '%s\n' "$managed_source"
}

source_dir="$(resolve_source)"
test_file="$repo_root/tests/router_smoke.ores"

echo "==> Oreslang source: $source_dir"
echo "==> Source revision: $(git -C "$source_dir" rev-parse HEAD 2>/dev/null || printf unknown)"

echo "==> Build compiler/runtime"
mvn -B -ntp -q -e -f "$source_dir/pom.xml" -DskipTests compile

echo "==> Typecheck linked routing test"
mvn -B -ntp -q -e -f "$source_dir/pom.xml" -DskipTests exec:java \
  -Dexec.args="--check $test_file"

echo "==> Run routing test"
mvn -B -ntp -q -e -f "$source_dir/pom.xml" -DskipTests exec:java \
  -Dexec.args="$test_file"

echo "VERIFY PASS"
