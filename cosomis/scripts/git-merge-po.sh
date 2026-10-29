#!/bin/sh
# Git merge driver for gettext .po catalogs (see .gitattributes at the repo
# root; enable once per clone with `make setup-git` in cosomis/).
#
# Git calls it as: git-merge-po.sh %O %A %B %P
#   %O ancestor, %A current branch (result is written here), %B other branch
#
# The current branch's translations always win; entries that only exist on
# the other branch are added. This is what a line-based merge gets wrong:
# it silently keeps duplicates (msgfmt then refuses the whole file) and
# lets the other side overwrite reviewed translations.
#
# Exit status 1 leaves the file conflicted for a manual merge.
set -eu

current="$2"
other="$3"
path="${4:-$current}"

if ! command -v msgcat >/dev/null 2>&1; then
    echo "git-merge-po: msgcat (GNU gettext) not found, merge $path by hand" >&2
    exit 1
fi

merged="$(mktemp)"
trap 'rm -f "$merged"' EXIT

# --use-first: for a msgid present on both sides, keep the current branch's
# entry (translation, flags, comments) untouched.
msgcat --use-first -o "$merged" "$current" "$other"

if ! msgfmt --check-format -o /dev/null "$merged"; then
    echo "git-merge-po: merged $path does not compile, merge it by hand" >&2
    exit 1
fi

cp "$merged" "$current"
echo "git-merge-po: merged $path (current branch translations kept)" >&2
