#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

if [ ! -f "_build/html/index.html" ]; then
    "$SCRIPT_DIR/build_html.sh"
fi

if [ -z "${DRAWLIB_CMD:-}" ]; then
    if command -v uv &> /dev/null && ( [ -f "pyproject.toml" ] || [ -f "../pyproject.toml" ] || [ -f "../../pyproject.toml" ] || [ -f "../../../pyproject.toml" ] ); then
        DRAWLIB_CMD="uv run drawlib"
    elif command -v drawlib &> /dev/null; then
        DRAWLIB_CMD="drawlib"
    else
        DRAWLIB_CMD="uv run drawlib"
    fi
fi

PORT="${1:-8000}"
echo "Serving presentation at http://localhost:${PORT}..."
$DRAWLIB_CMD serve _build/html/ -p "${PORT}"
