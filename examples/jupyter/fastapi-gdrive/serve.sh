#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

if [ -z "${DRAWLIB_CMD:-}" ]; then
    if command -v uv &> /dev/null && ( [ -f "pyproject.toml" ] || [ -f "../pyproject.toml" ] || [ -f "../../pyproject.toml" ] || [ -f "../../../pyproject.toml" ] ); then
        DRAWLIB_CMD="uv run drawlib"
    elif command -v drawlib &> /dev/null; then
        DRAWLIB_CMD="drawlib"
    elif python3 -m drawlib --version &> /dev/null; then
        DRAWLIB_CMD="python3 -m drawlib"
    elif command -v uvx &> /dev/null; then
        DRAWLIB_CMD="uvx drawlib"
    else
        DRAWLIB_CMD="drawlib"
    fi
fi

echo "Starting local preview server on _build/html/ ..."
$DRAWLIB_CMD serve _build/html/ "$@"
