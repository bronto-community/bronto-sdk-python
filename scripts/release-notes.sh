#!/usr/bin/env bash
# release-notes.sh — print the CHANGELOG section for one version.
#
# The release body comes from CHANGELOG.md rather than from generated commit
# notes. With a squashed history and few pull requests, `gh release create
# --generate-notes` would produce something close to empty, while the changelog
# is already the hand-curated artifact this project maintains. Extracting it
# means the release page and the changelog cannot disagree.
#
# Exits non-zero when the section is missing or empty, so a tag push fails
# before the release is created rather than publishing an empty page.
#
# Usage:
#   release-notes.sh 0.1.0     (leading v is accepted and ignored)
set -euo pipefail
cd "$(dirname "$0")/.."

if [ -z "${1:-}" ]; then
  echo "release-notes: usage: release-notes.sh X.Y.Z" >&2
  exit 1
fi

version="${1#v}"
changelog=CHANGELOG.md

# Everything between this version's heading and the next `## ` heading.
notes=$(awk -v want="## [$version]" '
  index($0, want) == 1 { grab = 1; next }
  grab && /^## / { exit }
  grab { print }
' "$changelog")

# Trim leading and trailing blank lines.
notes=$(printf '%s\n' "$notes" | sed -e '/./,$!d' | sed -e :a -e '/^\n*$/{$d;N;ba' -e '}')

if [ -z "$notes" ]; then
  echo "release-notes: no content under '## [$version]' in $changelog" >&2
  echo "Add the section (Keep a Changelog format) before tagging v$version." >&2
  exit 1
fi

printf '%s\n' "$notes"
