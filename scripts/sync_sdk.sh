#!/usr/bin/env bash
# Re-vendor mojio_sdk from a local checkout of https://github.com/Danimal4326/mojio-py
#
#   ./scripts/sync_sdk.sh /path/to/mojio-py
#
# See custom_components/mojio/mojio_sdk/README.md for why the SDK is vendored.
set -euo pipefail

SDK_REPO="${1:-}"
if [ -z "$SDK_REPO" ]; then
    echo "usage: $0 /path/to/mojio-py" >&2
    exit 1
fi

SRC="$SDK_REPO/mojio_sdk"
if [ ! -d "$SRC" ]; then
    echo "error: $SRC does not exist - is that a mojio-py checkout?" >&2
    exit 1
fi

DEST="$(cd "$(dirname "$0")/.." && pwd)/custom_components/mojio/mojio_sdk"

# Keep the vendoring README, replace everything else.
find "$DEST" -name '*.py' -delete
cp "$SRC"/*.py "$DEST"/

REV="$(git -C "$SDK_REPO" rev-parse --short HEAD)"
BRANCH="$(git -C "$SDK_REPO" rev-parse --abbrev-ref HEAD)"
echo "Synced $(ls -1 "$DEST"/*.py | wc -l | tr -d ' ') files from ${REV} (${BRANCH})"
echo "Remember to update the 'Synced from' line in ${DEST}/README.md"
