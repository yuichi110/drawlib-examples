#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$ROOT_DIR"

if [ -z "${DRAWLIB_CMD:-}" ]; then
    if command -v uv &> /dev/null && [ -f "pyproject.toml" ]; then
        DRAWLIB_CMD="uv run drawlib"
    elif command -v drawlib &> /dev/null; then
        DRAWLIB_CMD="drawlib"
    elif python3 -m drawlib --version &> /dev/null; then
        DRAWLIB_CMD="python3 -m drawlib"
    else
        DRAWLIB_CMD="drawlib"
    fi
fi

echo "Using Drawlib command: $DRAWLIB_CMD"
echo "Cleaning docs/..."
rm -rf docs
mkdir -p docs
touch docs/.nojekyll

check_slug() {
    local slug="$1"
    if [ -e "docs/$slug" ]; then
        echo "Error: Duplicate output slug 'docs/$slug' detected across categories." >&2
        exit 1
    fi
}

# 1. Standalone image projects (examples/images/*)
if [ -d "examples/images" ]; then
    for proj in examples/images/*; do
        [ -d "$proj" ] || continue
        slug="$(basename "$proj")"
        check_slug "$slug"
        echo "=== [images] Building $slug ==="
        $DRAWLIB_CMD build image "$proj" -o "docs/$slug/"
    done
fi

# 2. Linear document projects (examples/doc/*)
if [ -d "examples/doc" ]; then
    for proj in examples/doc/*; do
        [ -d "$proj" ] || continue
        slug="$(basename "$proj")"
        check_slug "$slug"
        echo "=== [doc] Building $slug (HTML / PDF / DOCX) ==="
        $DRAWLIB_CMD build html "$proj" -o "docs/$slug/"
        $DRAWLIB_CMD build pdf  "$proj" -o "docs/$slug/$slug.pdf" --generate-index
        $DRAWLIB_CMD build docx "$proj" -o "docs/$slug/$slug.docx" --generate-index
    done
fi

# 3. 16:9 presentation slide decks (examples/slide/*)
if [ -d "examples/slide" ]; then
    for proj in examples/slide/*; do
        [ -d "$proj" ] || continue
        slug="$(basename "$proj")"
        check_slug "$slug"
        echo "=== [slide] Building $slug (Slide HTML / PDF / PPTX) ==="
        $DRAWLIB_CMD build slide "$proj" -o "docs/$slug/"
        $DRAWLIB_CMD build pdf   "$proj" -o "docs/$slug/$slug.pdf"
        $DRAWLIB_CMD build pptx  "$proj" -o "docs/$slug/$slug.pptx"
    done
fi

# 4. Multi-page documentation sites (examples/site/*)
if [ -d "examples/site" ]; then
    for proj in examples/site/*; do
        [ -d "$proj" ] || continue
        slug="$(basename "$proj")"
        check_slug "$slug"
        echo "=== [site] Building $slug (HTML) ==="
        $DRAWLIB_CMD build html "$proj" -o "docs/$slug/"
    done
fi

# 5. Overlay static portal pages (index.html, style.css, image gallery pages)
if [ -d "portal" ]; then
    echo "=== Copying portal files to docs/ ==="
    cp -r portal/. docs/
fi

echo "=== Verifying links and assets in docs/ ==="
$DRAWLIB_CMD serve docs/ --check

echo "All builds completed successfully! Output: docs/"
