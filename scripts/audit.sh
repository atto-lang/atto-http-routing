#!/usr/bin/env bash
set -euo pipefail

repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
source_file="$repo_root/src/http_routing.ores"

if [[ ! -f "$source_file" ]]; then
  echo "missing $source_file" >&2
  exit 66
fi

if grep -nE 'java:|native_net|Socket|HttpClient|OresVM|OresContext' "$source_file"; then
  echo "routing core must remain transport/runtime neutral" >&2
  exit 1
fi

for symbol in \
  'define class RouteSnapshot' \
  'pub resolve' \
  'define class RouteMatch' \
  'pub fnc build_snapshot' \
  'pub fnc route_in_group'; do
  if ! grep -Fq "$symbol" "$source_file"; then
    echo "missing routing contract symbol: $symbol" >&2
    exit 1
  fi
done

echo "AUDIT PASS"
