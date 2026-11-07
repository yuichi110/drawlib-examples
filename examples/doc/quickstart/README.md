# Drawlib Quickstart Onboarding Guide (`doc`)

Bilingual (`en` / `ja`) 16-chapter engineering handbook introducing **Drawlib (`v0.3.7`)** from Cartesian canvas fundamentals through 34 icon suites, 18 SmartArts, 10 quantitative charts, 6 engineering diagram engines, 5 auto-layout graph solvers, multi-format animations (`APNG` / `WebP` / `GIF`), 5 project archetypes (`site`, `catalog`, `doc`, `slide`, `images`), and autonomous AI agent visual self-correction workflows.

---

## 1. Directory Structure

- `drawlib.toml`: Project manifest (`type = "doc"`, `style = "google"`, `langs = ["en", "ja"]`).
- `en/` & `ja/`: Symmetric 16-chapter Markdown sources (`00_cover.md` – `15_best_practices.md`).
- `styles.py` / `ja/styles.py`: `GoogleStyles` theme tokens and `FontJapanese` CJK overrides.
- `utils.py`: Shared Python drawing helpers.
- `template.html` / `style.css`: Responsive linear document layout with language switcher and `@media print` A4 rules.
- `build.sh` / `build_*.sh`: Standalone HTML, PDF, DOCX, Markdown, and image build scripts.

---

## 2. Building & Previewing Standalone

```bash
./build.sh      # Compiles HTML, PDF (EN/JA), DOCX (EN/JA), Markdown, and PNGs into _build/
./serve.sh      # Serves _build/html/ locally
```
