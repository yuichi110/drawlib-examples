# About Drawlib — 16:9 Slide Presentation (`slide`)

This directory contains slide Markdown files and drawing code compiled into an interactive HTML presentation deck, print-ready vector PDF, and editable 16:9 MS PowerPoint (`.pptx`) using Drawlib.

---

## 1. Directory Structure

- `drawlib.toml`: Unified project manifest (`type = "slide"`, `style = "default"`, `[i18n]` `default_lang = "en"`, `langs = ["en"]`).
- `en/`: English slide deck chapters (`00_opening/` ... `07_ai_agent_workflow/`).
- `_assets/`: Static image assets (logos, mascots) shared across locales.
- `styles.py`: Global styles script (themes, styles, font presets).
- `utils.py`: Slide macro helpers (cards, tables, timelines, flows).
- `style.css` / `slide.js`: Presentation styling and runtime interactivity.
- `build.sh`, `build_html.sh`, `build_pdf.sh`, `build_pptx.sh`, `build_image.sh`, `serve.sh`: Standalone build and preview scripts (outputs to `_build/`).

---

## 2. Building & Previewing Standalone

```bash
./build_html.sh   # Compile interactive HTML slide deck (_build/html/)
./build_pdf.sh    # Compile vector PDF presentation (_build/about-drawlib_en.pdf)
./build_pptx.sh   # Compile editable MS PowerPoint (_build/about-drawlib_en.pptx)
./build_image.sh  # Extract standalone diagram images (_build/images/)
./build.sh        # Run all builds sequentially
./serve.sh        # Start local preview server at http://localhost:8000
```
