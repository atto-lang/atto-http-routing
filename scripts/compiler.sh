#!/usr/bin/env bash
set -euo pipefail

: "${ORESLANG_SOURCE_DIR:?Set ORESLANG_SOURCE_DIR to the pinned oreslang-source.java checkout}"
repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd -P)"
java_bin="${ORES_JAVA:-java}"

# A runtime launcher must not silently execute bytecode from a different
# compiler revision. The backend checker also validates this; retain the
# check for callers invoking scripts/compiler.sh directly.
pin="$repo_root/SOURCE_REF"
[[ -f "$pin" && ! -L "$pin" ]] || {
  echo "SOURCE_REF is missing or is a symlink" >&2
  exit 65
}
revision="$(tr -d '[:space:]' < "$pin")"
[[ "$revision" =~ ^[0-9a-f]{40}$ ]] || {
  echo "SOURCE_REF must be a full lowercase commit SHA" >&2
  exit 65
}
# Refuse symbolic aliases in any path component, including parents. Do
# not let ".." collapse a symlink before it can be checked.
if [[ "$ORESLANG_SOURCE_DIR" = /* ]]; then
  source_input="$ORESLANG_SOURCE_DIR"
else
  source_input="$(pwd -P)/$ORESLANG_SOURCE_DIR"
fi
if [[ "/$source_input/" == *"/../"* ]]; then
  echo "compiler checkout must not contain parent traversal" >&2
  exit 65
fi
candidate="$source_input"
while [[ "$candidate" != "/" ]]; do
  if [[ -L "$candidate" ]]; then
    echo "compiler checkout path must not contain symlinks" >&2
    exit 65
  fi
  candidate="$(dirname "$candidate")"
done
source_dir="$(cd "$ORESLANG_SOURCE_DIR" && pwd -P)" || exit 65
git_root="$(git -C "$source_dir" rev-parse --show-toplevel)" || {
  echo "compiler checkout must be a Git repository" >&2
  exit 65
}
[[ "$git_root" == "$source_dir" ]] || {
  echo "compiler checkout must be its own Git root" >&2
  exit 65
}
actual="$(git -C "$source_dir" rev-parse HEAD)" || {
  echo "compiler checkout has no HEAD" >&2
  exit 65
}
[[ "$actual" == "$revision" ]] || {
  echo "compiler revision differs from SOURCE_REF" >&2
  exit 65
}
source_status="$(git -C "$source_dir" status --porcelain --untracked-files=all)" || {
  echo "compiler checkout status cannot be verified" >&2
  exit 65
}
[[ -z "$source_status" ]] || {
  echo "compiler checkout must be clean" >&2
  exit 65
}

# Do not follow output symlinks to unrelated bytecode or dependency lists.
for artifact in \
  "$source_dir/target" \
  "$source_dir/target/classes" \
  "$source_dir/target/classes/dev" \
  "$source_dir/target/classes/dev/oreslang" \
  "$source_dir/target/classes/dev/oreslang/launcher"; do
  [[ ! -L "$artifact" ]] || {
    echo "compiler output directory must not be a symlink" >&2
    exit 65
  }
done
classpath="$source_dir/target/classpath.txt"
entry="$source_dir/target/classes/dev/oreslang/launcher/OresMain.class"
[[ -f "$classpath" && -s "$classpath" && ! -L "$classpath" ]] || {
  echo "compiler classpath must be nonempty and not a symlink; build core first" >&2
  exit 69
}
[[ -f "$entry" && -s "$entry" && ! -L "$entry" ]] || {
  echo "compiler entrypoint class is missing or unsafe; build core first" >&2
  exit 69
}
exec "$java_bin" --enable-native-access=ALL-UNNAMED -Dpolyglot.engine.WarnInterpreterOnly=false \
  -cp "$source_dir/target/classes:$(cat "$classpath")" dev.oreslang.launcher.OresMain "$@"
