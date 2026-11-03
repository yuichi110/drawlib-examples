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
    elif python -m drawlib --version &> /dev/null; then
        DRAWLIB_CMD="python -m drawlib"
    else
        DRAWLIB_CMD="drawlib"
    fi
fi

mkdir -p _build
echo "Building Presentation PDF..."
$DRAWLIB_CMD build pdf . -o _build/about-drawlib.pdf
echo "Presentation PDF build complete: _build/about-drawlib_en.pdf"
