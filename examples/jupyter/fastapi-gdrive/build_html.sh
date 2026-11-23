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

echo "Using Drawlib command: $DRAWLIB_CMD"
echo "Building Jupyter HTML preview (with bundled .ipynb)..."
$DRAWLIB_CMD build html . -o _build/html/ "$@"
echo "HTML preview build complete: _build/html/"
