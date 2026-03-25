#!/usr/bin/env bash
#
# Build a lean skill zip for Claude Web upload.
# Run from the repository root: bash scripts/build.sh
#

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
ZIP_NAME="claude-imgedit.zip"
TOP_DIR="claude-imgedit"

# Skill files to include (paths relative to repo root)
SKILL_FILES=(
  SKILL.md
  scripts/edit_image.py
  references/REFERENCE.md
  assets/example_prompts.md
)

cd "$REPO_ROOT"

# Verify all required files exist
for f in "${SKILL_FILES[@]}"; do
  if [ ! -f "$f" ]; then
    echo "error: required file not found: $f" >&2
    exit 1
  fi
done

# Clean previous build
rm -f "$ZIP_NAME"

# Create a temporary staging directory
STAGING=$(mktemp -d)
trap 'rm -rf "$STAGING"' EXIT

DEST="$STAGING/$TOP_DIR"
for f in "${SKILL_FILES[@]}"; do
  mkdir -p "$DEST/$(dirname "$f")"
  cp "$f" "$DEST/$f"
done

# Include .env if present (personal API key)
if [ -f .env ]; then
  cp .env "$DEST/.env"
  echo "note: .env found — included in zip (do not share this zip)"
fi

# Build the zip
(cd "$STAGING" && zip -r - "$TOP_DIR") > "$ZIP_NAME"

echo ""
echo "Built $ZIP_NAME with contents:"
zipinfo -1 "$ZIP_NAME" | while read -r entry; do echo "  $entry"; done
