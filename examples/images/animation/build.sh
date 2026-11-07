#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

echo "=== Building Animations ==="
"$SCRIPT_DIR/build_image.sh"

echo "All builds completed successfully! (Outputs in _build/images/)"
