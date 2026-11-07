# Personal Web & Social Media Animations (`images`)

This directory showcases custom hero and brand animations for personal websites and social media profiles authored declaratively in pure Python with **Drawlib** and **AI coding agents**.

From a single `drawlib.anim.Animation` choreography (`1100 × 710 px`, `25 fps`), Drawlib compiles multi-format animated assets tailored for every publishing channel:
- **Lossless APNG (`.png`)**: Full 24-bit RGB + 8-bit alpha transparency for personal websites, blogs, and GitHub READMEs.
- **Animated WebP (`.webp`)**: Compact lossless animations for fast hero-banner page loads.
- **Dither-Free Animated GIF (`.gif`)**: Crisp 256-color Median Cut animations (`Image.Dither.NONE`) for universal playback across X, LinkedIn, Notion, and slide decks.

---

## 1. Directory Structure

- `drawlib.toml`: Project configuration manifest (`type = "images"`).
- `styles.py`: Shared semantic theme configuration.
- `utils.py`: Optical display typography, `3×3` block choreography, jump/duck kinematics, and flat palette tokens.
- `_assets/avenger.ttf`: Custom geometric display font loaded via `FontFile`.
- `grit_computing.py`: Light solid lossless APNG (`grit_computing.png`).
- `grit_computing_webp.py`: Light compact lossless Animated WebP (`grit_computing.webp`).
- `grit_computing_gif.py`: Light dither-free Animated GIF (`grit_computing.gif`).
- `grit_computing_transparent.py`: Transparent background 8-bit alpha APNG (`grit_computing_transparent.png`).
- `grit_computing_dark.py`: Dark theme lossless APNG (`grit_computing_dark.png`).
- `grit_computing_dark_gif.py`: Dark theme dither-free Animated GIF (`grit_computing_dark.gif`).
- `build.sh` / `build_image.sh`: Standalone batch build scripts (outputs to `_build/images/`).

---

## 2. Building Standalone

```bash
./build.sh   # Renders all 6 animation variants into _build/images/
```
