# Drawlib Quickstart Document Project (`doc`)

This directory contains multi-chapter specification and tutorial documents compiled into static HTML, vector PDF, editable MS Word (`.docx`), Markdown, and exported images using Drawlib.

---

## 1. Directory Structure

- `drawlib.toml`: Unified project manifest (`type = "doc"`, `style = "google"`, `[i18n]` `default_lang = "en"`, `langs = ["en"]`).
- `en/`: English tutorial and guide chapters (`00-cover.md` ... `15-best_practices.md`).
- `_assets/`: Shared image and font assets across locales.
- `styles.py`: Global styles script (themes, styles, font presets).
- `utils.py`: Reusable drawing helper functions, macros, and project constants.
- `style.css`: Document stylesheet (layout, typography, paged media rules).
- `template.html`: Jinja2 HTML layout.
- `build.sh`, `build_html.sh`, `build_pdf.sh`, `build_docx.sh`, `build_markdown.sh`, `build_image.sh`, `serve.sh`: Standalone build and preview scripts (outputs to `_build/`).

---

## 2. Building & Previewing Standalone

```bash
./build_html.sh       # Compile standalone HTML (_build/html/)
./build_pdf.sh        # Compile vector PDF (_build/quickstart_en.pdf)
./build_docx.sh       # Compile editable MS Word (_build/quickstart_en.docx)
./build_markdown.sh   # Compile Markdown (_build/markdown/)
./build_image.sh      # Export diagram images (_build/images/)
./build.sh            # Run all builds sequentially
./serve.sh            # Start local preview server at http://localhost:8000
```
