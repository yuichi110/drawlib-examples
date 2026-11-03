# Drawlib Logo Assets (`images`)

This directory contains standalone Python scripts (`type = "images"`) that generate the official Drawlib brand logos and favicon.

---

## 1. Directory Structure

- `drawlib.toml`: Project configuration manifest (`type = "images"`).
- `styles.py`: Global styles script (`DefaultColors` & `DefaultStyles`).
- `utils.py`: Reusable logo drawing functions (`draw_logo`, `draw_logo_icon`, `draw_logo_text`).
- `logo*.py`: Horizontal brand logos (light/dark, solid/transparent).
- `logo_icon*.py`: Standalone square icon marks (light/dark, solid/transparent).
- `logo_text*.py`: Standalone wordmarks (light/dark, solid/transparent).
- `favicon.py`: Official rounded white-card favicon (`favicon.png`).
- `build.sh` / `build_image.sh`: Standalone batch build scripts (outputs to `_build/images/`).

---

## 2. Building Standalone

```bash
./build.sh   # Renders all logo PNGs into _build/images/
```
