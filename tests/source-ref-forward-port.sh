#!/usr/bin/env bash
# Source-free test of immutable compiler checkout admission, NOT native routing.
set -euo pipefail
repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd -P)"
pin="$(tr -d '[:space:]' < "$repo_root/SOURCE_REF")"
[[ "$pin" =~ ^[0-9a-f]{40}$ ]] || { echo "invalid compiler pin" >&2; exit 1; }
grep -Fq -- 'expected_ref=' "$repo_root/scripts/test.sh" || { echo "missing compiler pin gate" >&2; exit 1; }
grep -Fq -- 'source_status=' "$repo_root/scripts/test.sh" || { echo "missing clean compiler tree gate" >&2; exit 1; }
grep -Fq -- '--check --platform=server' "$repo_root/scripts/test.sh" || { echo "missing native check gate" >&2; exit 1; }
echo "PASS source-ref shape and runner admission checks (source-free only)"
