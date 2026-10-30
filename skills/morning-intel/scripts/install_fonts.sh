#!/usr/bin/env bash
# Install the three font families The Morning Intel uses (all SIL OFL, from github.com/google/fonts).
# Linux: ~/.local/share/fonts/morning-intel   macOS: ~/Library/Fonts
# Safe to re-run: existing files are skipped.
set -euo pipefail
BASE="https://raw.githubusercontent.com/google/fonts/main/ofl"
case "$(uname -s)" in
  Darwin) DEST="$HOME/Library/Fonts" ;;
  *)      DEST="${XDG_DATA_HOME:-$HOME/.local/share}/fonts/morning-intel" ;;
esac
mkdir -p "$DEST"
FILES=(
  "inter/Inter%5Bopsz,wght%5D.ttf|Inter-Variable.ttf"
  "ibmplexserif/IBMPlexSerif-Regular.ttf|IBMPlexSerif-Regular.ttf"
  "ibmplexserif/IBMPlexSerif-Italic.ttf|IBMPlexSerif-Italic.ttf"
  "ibmplexserif/IBMPlexSerif-SemiBold.ttf|IBMPlexSerif-SemiBold.ttf"
  "ibmplexserif/IBMPlexSerif-Bold.ttf|IBMPlexSerif-Bold.ttf"
  "ibmplexmono/IBMPlexMono-Regular.ttf|IBMPlexMono-Regular.ttf"
  "ibmplexmono/IBMPlexMono-Medium.ttf|IBMPlexMono-Medium.ttf"
)
for pair in "${FILES[@]}"; do
  src="${pair%%|*}"; out="$DEST/${pair##*|}"
  if [[ -s "$out" ]]; then echo "have  $out"; continue; fi
  curl -fsSL "$BASE/$src" -o "$out" && echo "got   $out"
done
command -v fc-cache >/dev/null && fc-cache -f "$DEST" >/dev/null || true
if command -v fc-list >/dev/null; then
  for fam in "Inter" "IBM Plex Serif" "IBM Plex Mono"; do
    fc-list : family | grep -qx "$fam\(,.*\)\?" && echo "ok    $fam" || echo "WARN  $fam not visible to fontconfig yet"
  done
fi
