# DDoS Incident Response — 16:9 Slide Presentation (`slide`)

This directory contains slide Markdown files and drawing code compiled into an interactive HTML presentation deck, print-ready vector PDF, and editable 16:9 MS PowerPoint (`.pptx`) using Drawlib.

---

## 1. Directory Structure

- `drawlib.toml`: Unified project manifest (`type = "slide"`, `style = "google"`, `[i18n]` `default_lang = "en"`, `langs = ["en"]`).
- `en/`: English slide deck chapters (`00_opening/` ... `05_closing/`).
- `_CONTENTS_PLANNING.md`: Underscore-prefixed slide deck blueprint (automatically excluded from compilation).
- `_assets/`: Shared static image assets across locales.
- `styles.py`: Global styles script (themes, styles, font presets).
- `utils.py`: Slide macro helpers (cards, tables, timelines, flows).
- `style.css` / `slide.js`: Presentation styling and runtime interactivity.
- `build.sh`, `build_html.sh`, `build_pdf.sh`, `build_pptx.sh`, `build_image.sh`, `serve.sh`: Standalone build and preview scripts (outputs to `_build/`).

---

## 2. Building & Previewing Standalone

```bash
./build_html.sh   # Compile interactive HTML slide deck (_build/html/)
./build_pdf.sh    # Compile vector PDF presentation (_build/ddos-incident-response_en.pdf)
./build_pptx.sh   # Compile editable MS PowerPoint (_build/ddos-incident-response_en.pptx)
./build_image.sh  # Extract standalone diagram images (_build/images/)
./build.sh        # Run all builds sequentially
./serve.sh        # Start local preview server at http://localhost:8000
```
