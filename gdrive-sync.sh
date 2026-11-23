#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SRC_DIR="${SRC_DIR:-$ROOT_DIR/examples/jupyter/fastapi-gdrive/_build/jupyter}"
DEST_REMOTE="${DEST_REMOTE:-gdrive:drawlib-jupyter-example-fastapi}"

if ! command -v rclone &> /dev/null; then
    echo "Error: rclone is not installed. Run 'brew install rclone' first." >&2
    exit 1
fi

if [ ! -d "$SRC_DIR" ]; then
    echo "Error: Build directory not found: $SRC_DIR" >&2
    echo "Run './examples/jupyter/fastapi-gdrive/build_jupyter.sh' first." >&2
    exit 1
fi

echo "Syncing '$SRC_DIR/' -> '$DEST_REMOTE'..."
rclone sync "$SRC_DIR/" "$DEST_REMOTE" \
    -M --metadata-set Content-Type=application/vnd.google.colaboratory \
    -v \
    "$@"

echo "Sync complete: $DEST_REMOTE"

