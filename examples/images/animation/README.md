# GRIT COMPUTING Hero Animations (`images`)

High-resolution (`1100 × 710 px`, 2× Retina) pure-Python remake of the classic `p5.js` top hero animation on [`www.yuichi.com`](https://www.yuichi.com/), compiled across **APNG**, **Animated WebP**, and **dither-free Animated GIF** (`v0.3.7`) using `drawlib.anim.Animation`.

---

## 1. Directory Structure

- `drawlib.toml`: Project configuration manifest (`type = "images"`).
- `styles.py`: Shared semantic theme configuration.
- `utils.py`: Optical `Avenger` display typography, collision-free `3×3` cluster migration choreography, parabolic jump/duck physics, and discrete palette tokens.
- `_assets/avenger.ttf`: Geometric display font used for the `GRIT` and `COMPUTING` wordmarks.
- `grit_computing.py`: Light solid lossless APNG (`grit_computing.png`).
- `grit_computing_webp.py`: Light compact lossless Animated WebP (`grit_computing.webp`).
- `grit_computing_gif.py`: Light dither-free 256-color Animated GIF (`grit_computing.gif`).
- `grit_computing_transparent.py`: Light 8-bit alpha transparent APNG (`grit_computing_transparent.png`).
- `grit_computing_dark.py`: Dark theme lossless APNG (`grit_computing_dark.png`).
- `grit_computing_dark_gif.py`: Dark theme dither-free Animated GIF (`grit_computing_dark.gif`).
- `build.sh` / `build_image.sh`: Standalone batch build scripts (outputs to `_build/images/`).

---

## 2. Building Standalone

```bash
./build.sh   # Renders all 6 animation variants into _build/images/
```
