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
[[ ! -L "$ORESLANG_SOURCE_DIR" ]] || {
  echo "compiler checkout must not be a symlink" >&2
  exit 65
}
source_dir="$(cd "$ORESLANG_SOURCE_DIR" && pwd -P)" || exit 65
actual="$(git -C "$source_dir" rev-parse HEAD)" || {
  echo "compiler checkout must be a Git repository" >&2
  exit 65
}
[[ "$actual" == "$revision" ]] || {
  echo "compiler revision differs from SOURCE_REF" >&2
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
