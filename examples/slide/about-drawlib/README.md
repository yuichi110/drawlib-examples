# About Drawlib — Official Bilingual 16:9 Showcase Deck (`slide`)

This directory contains bilingual (`en` / `ja`) slide Markdown files and embedded Drawlib Python diagrams compiled into an interactive HTML presentation deck (with Presenter View and live locale switching), print-ready vector PDFs, and editable 16:9 MS PowerPoint (`.pptx`) decks.

---

## 1. Directory Structure

- `drawlib.toml`: Unified project manifest (`type = "slide"`, `style = "default"`, `[i18n]` `default_lang = "en"`, `langs = ["en", "ja"]`).
- `en/` & `ja/`: Symmetric 39-slide English and Japanese chapters (`00_opening/` ... `07_closing/`).
- `_assets/`: Static image assets shared across locales.
- `styles.py`: Global styles script (`DefaultStyles` / `DefaultColors`).
- `utils.py`: Slide-calibrated macro helpers (`draw_page_number`, `draw_chapter_divider`, `draw_curved_agenda`, `draw_kpi_cards`).
- `style.css` / `slide.js`: Presentation styling and runtime interactivity.
- `build.sh`, `build_html.sh`, `build_pdf.sh`, `build_pptx.sh`, `build_image.sh`, `serve.sh`: Standalone build and preview scripts (outputs to `_build/`).

---

## 2. Building & Previewing Standalone

```bash
./build_html.sh   # Compile bilingual HTML slide decks (_build/html/{en,ja}/index.html)
./build_pdf.sh    # Compile vector PDF presentations (_build/about-drawlib_{en,ja}.pdf)
./build_pptx.sh   # Compile editable MS PowerPoint (_build/about-drawlib_{en,ja}.pptx)
./build_image.sh  # Extract standalone diagram images (_build/images/)
./build.sh        # Run all builds sequentially
./serve.sh        # Start local preview server at http://localhost:8000
```
