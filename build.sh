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

# 6. Jupyter & Google Colab notebooks (examples/jupyter/*)
if [ -d "examples/jupyter" ]; then
    for proj in examples/jupyter/*; do
        [ -d "$proj" ] || continue
        slug="$(basename "$proj")"
        check_slug "$slug"
        echo "=== [jupyter] Building $slug (Jupyter .ipynb & HTML) ==="
        $DRAWLIB_CMD build jupyter "$proj" -o "docs/$slug/"
    done
fi

# 7. Overlay static portal pages (index.html, style.css, image gallery pages)
if [ -d "portal" ]; then
    echo "=== Copying portal files to docs/ ==="
    cp -r portal/. docs/
fi

# 8. Inject showcase .demo-banner (for examples/{doc,slide,site,catalog,jupyter}/*) and
#    GA4 tag into generated HTML pages in docs/ (after PDF/DOCX/PPTX builds so
#    headless Chromium exports do not fire analytics or render the web banner,
#    and without polluting reusable sample source files under examples/).
#    TODO(security): SRI is intentionally omitted on googletagmanager.com/gtag/js
#    because Google dynamically serves container scripts; portal pages enforce a
#    strict SHA-256 CSP hash instead of 'unsafe-inline'.
GA4_ID="G-S9N5BZ1VRC"
echo "=== Injecting showcase banners and GA4 ($GA4_ID) into generated HTML pages in docs/ ==="
python3 - "$GA4_ID" <<'PY'
import pathlib
import re
import shutil
import sys

ga4_id = sys.argv[1]
docs_root = pathlib.Path("docs")
examples_root = pathlib.Path("examples")

# Remove any stray local _build/ directories that may have been copied into docs/
for stray_build in list(docs_root.glob("*/_build")):
    if stray_build.is_dir():
        shutil.rmtree(stray_build)

banner_css = """
/* Drawlib Showcase Top Banner */
:root {
    --demo-banner-h: 38px;
}

html {
    scroll-padding-top: 52px;
}

.demo-banner {
    position: sticky;
    top: 0;
    z-index: 1050;
    min-height: var(--demo-banner-h);
    background: #0f172a;
    color: #f8fafc;
    border-bottom: 1px solid #334155;
    font-family: var(--rtd-font, "Inter", -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif);
    font-size: 0.84rem;
    line-height: 1.4;
    padding: 0.42rem 1.25rem;
    display: flex;
    align-items: center;
}

.demo-banner-inner {
    width: 100%;
    max-width: 1380px;
    margin: 0 auto;
    display: flex;
    flex-wrap: wrap;
    align-items: center;
    justify-content: space-between;
    gap: 0.45rem 1rem;
}

.demo-banner-badge {
    display: inline-block;
    background: #4f46e5;
    color: #ffffff;
    font-size: 0.68rem;
    font-weight: 700;
    letter-spacing: 0.04em;
    padding: 0.12rem 0.48rem;
    border-radius: 4px;
    flex-shrink: 0;
}

.demo-banner-text {
    flex: 1 1 auto;
    color: #e2e8f0;
}

.demo-banner code {
    background: rgba(255, 255, 255, 0.12);
    color: #f8fafc;
    padding: 0.08rem 0.35rem;
    border-radius: 4px;
    font-size: 0.82em;
}

.demo-banner a {
    color: #a5b4fc;
    font-weight: 600;
    text-decoration: none;
}

.demo-banner a:hover {
    color: #e0e7ff;
    text-decoration: underline;
}

.demo-banner-links {
    display: inline-flex;
    flex-wrap: wrap;
    align-items: center;
    gap: 0.25rem 0.45rem;
}

.demo-banner-links a,
.demo-banner-links strong {
    white-space: nowrap;
}

.demo-banner-links strong {
    color: #ffffff;
}

.demo-banner-sep {
    color: #64748b;
}

@media (min-width: 769px) {
    .sidebar {
        top: var(--demo-banner-h);
        height: calc(100vh - var(--demo-banner-h));
    }
}

@media (max-width: 768px) {
    .demo-banner {
        position: static;
        padding: 0.5rem 1rem;
    }

    body:has(.sidebar) .demo-banner {
        margin-top: 60px;
    }

    body:has(.sidebar) .content-wrapper {
        margin-top: 0;
    }
}

.presentation-viewport {
    height: calc(100vh - var(--demo-banner-h, 38px));
}

:fullscreen .demo-banner,
body.presenter-mode .demo-banner {
    display: none !important;
}

:fullscreen .presentation-viewport {
    height: 100vh;
}

@media print {
    .demo-banner {
        display: none !important;
    }
}
"""

category_labels = {
    "doc": (
        'Sample Engineering Whitepaper (<code>type = "doc"</code>) built with '
        '<a href="https://www.drawlib.com/" target="_blank" rel="noopener noreferrer">Drawlib</a>',
        '<a href="https://www.drawlib.com/ja/" target="_blank" rel="noopener noreferrer">Drawlib</a> '
        'で構築された技術ホワイトペーパーのサンプルプロジェクト（<code>type = "doc"</code>）',
    ),
    "slide": (
        'Sample 16:9 Presentation Deck (<code>type = "slide"</code>) built with '
        '<a href="https://www.drawlib.com/" target="_blank" rel="noopener noreferrer">Drawlib</a>',
        '<a href="https://www.drawlib.com/ja/" target="_blank" rel="noopener noreferrer">Drawlib</a> '
        'で構築された 16:9 プレゼン資料のサンプルプロジェクト（<code>type = "slide"</code>）',
    ),
    "site": (
        'Sample Documentation Site (<code>type = "site"</code>) built with '
        '<a href="https://www.drawlib.com/" target="_blank" rel="noopener noreferrer">Drawlib</a>',
        '<a href="https://www.drawlib.com/ja/" target="_blank" rel="noopener noreferrer">Drawlib</a> '
        'で構築されたドキュメントサイトのサンプルプロジェクト（<code>type = "site"</code>）',
    ),
    "catalog": (
        'Sample Reference Catalog (<code>type = "catalog"</code>) built with '
        '<a href="https://www.drawlib.com/" target="_blank" rel="noopener noreferrer">Drawlib</a>',
        '<a href="https://www.drawlib.com/ja/" target="_blank" rel="noopener noreferrer">Drawlib</a> '
        'で構築されたリファレンスカタログのサンプルプロジェクト（<code>type = "catalog"</code>）',
    ),
    "jupyter": (
        'Sample Jupyter &amp; Colab Notebook (<code>type = "jupyter"</code>) built with '
        '<a href="https://www.drawlib.com/" target="_blank" rel="noopener noreferrer">Drawlib</a>',
        '<a href="https://www.drawlib.com/ja/" target="_blank" rel="noopener noreferrer">Drawlib</a> '
        'で構築された Jupyter / Colab ノートブックのサンプルプロジェクト（<code>type = "jupyter"</code>）',
    ),
}

html_lang_re = re.compile(r'<html\b[^>]*\blang=["\']([^"\']+)["\']', re.IGNORECASE)
body_open_re = re.compile(r"(<body\b[^>]*>)", re.IGNORECASE)
refresh_re = re.compile(r'<meta\b[^>]*http-equiv=["\']?refresh["\']?', re.IGNORECASE)

banner_injected = 0
for category in ("doc", "slide", "site", "catalog", "jupyter"):
    cat_dir = examples_root / category
    if not cat_dir.is_dir():
        continue
    for proj_dir in sorted(cat_dir.iterdir()):
        if not proj_dir.is_dir():
            continue
        slug = proj_dir.name
        out_dir = docs_root / slug
        if not out_dir.is_dir():
            continue

        # 1. Append .demo-banner CSS to all style.css files in docs/<slug>/
        for css_path in sorted(out_dir.rglob("style.css")):
            css_text = css_path.read_text(encoding="utf-8")
            if ".demo-banner" not in css_text:
                css_path.write_text(css_text.rstrip() + "\n" + banner_css, encoding="utf-8")

        # 2. For slide decks, adjust slide.js so scale calculation accounts for .demo-banner height
        slide_js = out_dir / "slide.js"
        if slide_js.is_file():
            js_text = slide_js.read_text(encoding="utf-8")
            target_js = "    const windowHeight = window.innerHeight;"
            replacement_js = (
                "    const bannerEl = document.querySelector('.demo-banner');\n"
                "    const bannerH = (bannerEl && !document.fullscreenElement && !isPresenterMode)"
                " ? (bannerEl.offsetHeight || 38) : 0;\n"
                "    const windowHeight = Math.max(100, window.innerHeight - bannerH);"
            )
            if target_js in js_text and "bannerEl" not in js_text:
                js_text = js_text.replace(target_js, replacement_js, 1)
                js_text = js_text.replace(
                    "  window.addEventListener('resize', updateScale);",
                    "  window.addEventListener('resize', updateScale);\n"
                    "  window.addEventListener('load', updateScale);\n"
                    "  document.addEventListener('fullscreenchange', updateScale);",
                    1,
                )
                slide_js.write_text(js_text, encoding="utf-8")

        # 3. Inject .demo-banner HTML right after <body...> in each non-redirect HTML file
        for html_path in sorted(out_dir.rglob("*.html")):
            content = html_path.read_text(encoding="utf-8")
            if 'class="demo-banner"' in content or refresh_re.search(content):
                continue

            lang_match = html_lang_re.search(content)
            lang_val = lang_match.group(1).lower() if lang_match else "en"
            is_ja = lang_val.startswith("ja")
            lang_code = "ja" if is_ja else "en"

            rel_parts = html_path.relative_to(docs_root).parts
            rel_to_docs = "../" * (len(rel_parts) - 1)
            rel_to_proj = "../" * (len(rel_parts) - 2)

            text_en, text_ja = category_labels[category]
            banner_text = text_ja if is_ja else text_en
            aria_label = "ポータルナビゲーション" if is_ja else "Portal Navigation"
            drawlib_url = "https://www.drawlib.com/ja/" if is_ja else "https://www.drawlib.com/"

            links = [f'<a href="{rel_to_docs}index.html">All Examples</a>']
            for ext, label in (("pdf", "PDF"), ("docx", "DOCX"), ("pptx", "PPTX")):
                candidates = [
                    f"{slug}_{lang_code}.{ext}",
                    f"{slug}_en.{ext}",
                    f"{slug}.{ext}",
                ]
                for cand in candidates:
                    if (out_dir / cand).is_file():
                        links.append(f'<a href="{rel_to_proj}{cand}">{label}</a>')
                        break

            repo_url = f"https://github.com/yuichi110/drawlib-examples/tree/main/examples/{category}/{slug}"
            links.append(f'<a href="{repo_url}" target="_blank" rel="noopener noreferrer">Source (GitHub) ↗</a>')
            links.append(f'<a href="{drawlib_url}" target="_blank" rel="noopener noreferrer">Drawlib ↗</a>')

            links_html = '\n                <span class="demo-banner-sep">·</span>\n                '.join(links)
            banner_html = (
                f'    <div class="demo-banner" role="region" aria-label="{aria_label}">\n'
                f'        <div class="demo-banner-inner">\n'
                f'            <span class="demo-banner-badge">DRAWLIB SHOWCASE</span>\n'
                f'            <span class="demo-banner-text">\n'
                f'                {banner_text}\n'
                f'            </span>\n'
                f'            <span class="demo-banner-links">\n'
                f'                {links_html}\n'
                f'            </span>\n'
                f'        </div>\n'
                f'    </div>'
            )

            if body_open_re.search(content):
                new_content = body_open_re.sub(lambda m: f"{m.group(1)}\n{banner_html}", content, count=1)
                html_path.write_text(new_content, encoding="utf-8")
                banner_injected += 1

print(f"Injected showcase banner into {banner_injected} generated HTML file(s).")

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

injected = 0
for html_path in sorted(docs_root.rglob("*.html")):
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
