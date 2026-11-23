#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

echo "=== Building Jupyter HTML Preview (with bundled .ipynb) ==="
"$SCRIPT_DIR/build_html.sh" "$@"

echo "=== Building Standalone Jupyter Notebooks (.ipynb only) ==="
"$SCRIPT_DIR/build_jupyter.sh" "$@"

echo "=== All builds completed successfully! ==="
