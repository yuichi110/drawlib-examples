# Gemini 3.8 Flash Latency & Architecture Evaluation Report (`doc` Multi-Language Project)

This directory contains the bilingual (English & Japanese) Gemini 3.8 Flash Latency & Architecture Evaluation Report compiled into **HTML, A4 vector PDFs (`_en.pdf` / `_ja.pdf`), editable MS Word (`.docx`), Markdown, and standalone images**.

---

## 1. Directory Structure

- `drawlib.toml`: Unified project manifest (`type = "doc"`, `style = "google"`, `[i18n]` `default_lang = "en"`, `langs = ["en", "ja"]`).
- `en/`: English report chapters (`00_cover.md` .. `05_multiturn_behavior.md`).
- `ja/`: Japanese report chapters (`00_cover.md` .. `05_multiturn_behavior.md`) and `ja/styles.py` (`FontJapanese` override).
- `_assets/`: Shared image assets (`favicon.png`, `linux.png`) across all locales.
- `styles.py`: Default drawing theme (`GoogleStyles` / `GoogleColors`).
- `utils.py`: Shared drawing helper functions and benchmark log loaders (`src/gemini_evaluation/`).
- `style.css`: Google Editorial document & A4 print stylesheet.
- `template.html`: Jinja2 HTML layout with top-right language switcher (hidden in print/PDF).
- `build.sh`, `build_html.sh`, `build_pdf.sh`, `build_docx.sh`, `build_markdown.sh`, `build_image.sh`, `serve.sh`: Standalone build and preview scripts (outputs to `_build/`).

---

## 2. Building & Previewing Standalone

```bash
./build_html.sh       # Compile standalone HTML (_build/html/)
./build_pdf.sh        # Compile A4 vector PDFs (_build/gemini_latency_en.pdf, _build/gemini_latency_ja.pdf)
./build_docx.sh       # Compile editable MS Word (_build/gemini_latency_en.docx, _build/gemini_latency_ja.docx)
./build_markdown.sh   # Compile Markdown (_build/markdown/)
./build_image.sh      # Extract diagram images (_build/images/)
./build.sh            # Run all builds sequentially
./serve.sh            # Start local preview server at http://localhost:8000
```
