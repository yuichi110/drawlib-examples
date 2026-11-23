#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

if [ -f ".env" ]; then
    set -a
    # shellcheck source=/dev/null
    source ".env"
    set +a
fi

RCLONE_REMOTE="${RCLONE_REMOTE:-gdrive}"
# 公開先 Google Drive フォルダ: https://drive.google.com/drive/folders/1dPZ0bikr9EY2VXQX2OCHhL3He9jxX2kH
GDRIVE_FOLDER_ID="${GDRIVE_FOLDER_ID:-1dPZ0bikr9EY2VXQX2OCHhL3He9jxX2kH}"
# 全言語（ja / en）のビルド済みノートブックを同期
JUPYTER_SRC_DIR="${JUPYTER_SRC_DIR:-_build/jupyter}"
GDRIVE_SYNC_MODE="${GDRIVE_SYNC_MODE:-sync}"

if ! command -v rclone &> /dev/null; then
    echo "Error: rclone is not installed. Run 'brew install rclone' first." >&2
    exit 1
fi
if [ ! -d "$JUPYTER_SRC_DIR" ]; then
    echo "Error: Build directory '$JUPYTER_SRC_DIR' not found. Run ./build_jupyter.sh first." >&2
    exit 1
fi

echo "Syncing FastAPI notebooks to Google Drive ($GDRIVE_SYNC_MODE): $JUPYTER_SRC_DIR -> ${RCLONE_REMOTE}: (folder=$GDRIVE_FOLDER_ID)"
rclone "$GDRIVE_SYNC_MODE" \
    "$JUPYTER_SRC_DIR/" \
    "${RCLONE_REMOTE}:" \
    --drive-root-folder-id="${GDRIVE_FOLDER_ID}" \
    --include "*.ipynb" \
    -M --metadata-set Content-Type=application/vnd.google.colaboratory \
    --stats-one-line \
    -v \
    "$@"

