# Drawlib OGP & GitHub Social Preview (`images`)

This directory contains standalone Python scripts (`type = "images"`) that generate `1280 × 640 px` Open Graph Protocol (OGP) / GitHub Social Preview banner images for `drawlib`.

---

## 1. Directory Structure

- `drawlib.toml`: Project configuration manifest (`type = "images"`).
- `styles.py`: Shared semantic theme and font configuration.
- `utils.py`: Shared `1280 × 640 px` canvas setup and card/layout helper utilities.
- `_assets/`: Shared brand logo raster assets (`logo_transparent.png`, `logo_dark_transparent.png`).
- `social_preview.py`: Primary GitHub Social Preview (`Git Repo • Single Source of Truth`).
- `social_preview_codebase.py`: Alternative stage naming variant (`Codebase` -> `Docs as Code`).
- `social_preview_minimal.py`: Minimal 3-column variant (`Git Repo` -> `AI Agent + Drawlib` -> `Site, Doc, Slide`).
- `build.sh` / `build_image.sh`: Standalone batch build scripts (outputs to `_build/images/`).

---

## 2. Building Standalone

```bash
./build.sh   # Renders all OGP PNGs into _build/images/
```
