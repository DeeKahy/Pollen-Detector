#!/usr/bin/env bash
# Makes diff.pdf: the report with changes since another version marked, like a
# pull request on GitHub. Added text is blue and underlined, removed text is red
# and struck through.
#
#   cd report && ./diff.sh                    # compare with origin/main
#   cd report && ./diff.sh HEAD~3             # compare with three commits ago
#   cd report && ./diff.sh path/to/old/report # compare with a copy of report/
#   ./diff.sh <old> --tex-only                # only write diff.tex here (CI builds it)
#
# Needs latexmk, latexpand and latexdiff (all in TeX Live and in `nix develop`).
set -euo pipefail

old_arg="${1:-origin/main}"
tex_only=false
[ "${2:-}" = "--tex-only" ] && tex_only=true
here="$(cd "$(dirname "$0")" && pwd)"
work="$(mktemp -d)"
trap 'rm -rf "$work"' EXIT

# 1. The old report: a folder, or report/ as it was in a git version.
if [ -d "$old_arg" ]; then
  mkdir -p "$work/old" && cp -R "$old_arg"/. "$work/old/"
else
  repo="$(git -C "$here" rev-parse --show-toplevel)"
  mkdir -p "$work/git"
  git -C "$repo" archive "$old_arg" report | tar -x -C "$work/git"
  mv "$work/git/report" "$work/old"
fi
old="$work/old"

# 2. The new report: used in place (--tex-only) or as a clean copy.
if $tex_only; then
  new="$here"
else
  cp -R "$here" "$work/new"
  new="$work/new"
  rm -rf "$new/build" "$new"/main.{aux,bbl,bcf,blg,fdb_latexmk,fls,log,out,run.xml,toc,pdf}
fi

# 3. Both reports as one flat .tex file each. latexmkrc writes the chapter list
#    (build/chapters.tex) first, then latexpand pastes every \input into main.tex.
flatten() {
  (cd "$1" && perl -e 'do "./latexmkrc"; die $@ if $@' && latexpand --empty-comments main.tex > "$2")
}
flatten "$old" "$work/old.tex"
flatten "$new" "$work/new.tex"

# 4. Mark the differences. Figures that were removed still need their files.
#    Our red placeholders are text: the marks go inside them, so long ones can wrap.
cp -n "$old"/figures/* "$new/figures/" 2>/dev/null || true
latexdiff --type=UNDERLINE --math-markup=whole --graphics-markup=both \
  --append-textcmd=fillin,future --exclude-safecmd=fillin,future \
  "$work/old.tex" "$work/new.tex" > "$new/diff.tex" 2> "$work/latexdiff.log"

if $tex_only; then
  echo "Wrote $new/diff.tex"
  exit 0
fi

# 5. Build it with the new report's setup, figures and references.
(cd "$new" && latexmk -pdf -interaction=nonstopmode -halt-on-error diff.tex > /dev/null) || {
  echo "diff.pdf failed to build, see the end of the log:" >&2
  tail -40 "$new/diff.log" >&2
  exit 1
}
cp "$new/diff.pdf" "$here/diff.pdf"
echo "Wrote $here/diff.pdf (changes since $old_arg)"
