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
    elif command -v uvx &> /dev/null; then
        DRAWLIB_CMD="uvx drawlib"
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
        $DRAWLIB_CMD show "$proj/en/00_opening/01_title.md" 1 -o "docs/$slug/preview.png"
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

# 5. API & reference catalogs (examples/catalog/*)
if [ -d "examples/catalog" ]; then
    for proj in examples/catalog/*; do
        [ -d "$proj" ] || continue
        slug="$(basename "$proj")"
        check_slug "$slug"
        echo "=== [catalog] Building $slug (Catalog HTML) ==="
        $DRAWLIB_CMD build html "$proj" -o "docs/$slug/"
    done
fi

# 6. Overlay static portal pages (index.html, style.css, image gallery pages)
if [ -d "portal" ]; then
    echo "=== Copying portal files to docs/ ==="
    cp -r portal/. docs/
fi

# 7. Inject GA4 tag into generated HTML pages in docs/ (after PDF/PPTX builds
#    so headless Chromium exports do not fire analytics, and without polluting
#    reusable sample source files under examples/).
#    TODO(security): SRI is intentionally omitted on googletagmanager.com/gtag/js
#    because Google dynamically serves container scripts; portal pages enforce a
#    strict SHA-256 CSP hash instead of 'unsafe-inline'.
GA4_ID="G-S9N5BZ1VRC"
echo "=== Injecting GA4 ($GA4_ID) into generated HTML pages in docs/ ==="
python3 - "$GA4_ID" <<'PY'
import pathlib
import re
import sys

ga4_id = sys.argv[1]
snippet = (
    f"    <!-- Google tag (gtag.js) -->\n"
    f'    <script async src="https://www.googletagmanager.com/gtag/js?id={ga4_id}"></script>\n'
    f"    <script>\n"
    f"        window.dataLayer = window.dataLayer || [];\n"
    f"        function gtag(){{dataLayer.push(arguments);}}\n"
    f"        gtag('js', new Date());\n\n"
    f"        gtag('config', '{ga4_id}');\n"
    f"    </script>"
)

title_re = re.compile(r"([ \t]*<title>.*?</title>)", re.IGNORECASE | re.DOTALL)
refresh_re = re.compile(r'<meta\b[^>]*http-equiv=["\']?refresh["\']?', re.IGNORECASE)

injected = 0
for html_path in sorted(pathlib.Path("docs").rglob("*.html")):
    content = html_path.read_text(encoding="utf-8")
    if "googletagmanager.com/gtag/js" in content or refresh_re.search(content):
        continue
    if title_re.search(content):
        new_content = title_re.sub(lambda m: f"{m.group(1)}\n{snippet}", content, count=1)
    elif "</head>" in content:
        new_content = content.replace("</head>", f"{snippet}\n</head>", 1)
    else:
        continue
    html_path.write_text(new_content, encoding="utf-8")
    injected += 1

print(f"Injected GA4 tag into {injected} generated HTML file(s).")
PY

echo "=== Verifying links and assets in docs/ ==="
$DRAWLIB_CMD serve docs/ --check

echo "All builds completed successfully! Output: docs/"
