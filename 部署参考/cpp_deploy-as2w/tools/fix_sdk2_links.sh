#!/usr/bin/env bash
# Windows checkouts may materialize SDK2 .so.0 symlinks as tiny text files.
set -euo pipefail
lib_dir=${1:-"${AS2W_SDK2_PREFIX:-$HOME/unitree_sdk2_install}/lib"}
for name in libddsc.so libddscxx.so; do
  link="$lib_dir/$name.0"
  target="$lib_dir/$name"
  [[ -s "$target" ]] || { echo "Missing SDK2 library: $target" >&2; exit 1; }
  if [[ -L "$link" ]]; then
    [[ $(readlink "$link") == "$name" ]] || { echo "Unexpected SDK2 symlink: $link" >&2; exit 1; }
    continue
  fi
  [[ -f "$link" && $(cat "$link") == "$name" ]] || {
    echo "Unexpected SDK2 versioned library: $link" >&2; exit 1;
  }
  rm -- "$link"
  ln -s "$name" "$link"
  echo "Restored $link -> $name"
done
