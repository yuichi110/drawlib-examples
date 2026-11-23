# fastapi-gdrive — Drawlib Jupyter & Google Colab Project

This directory (`fastapi-gdrive_src/`) is the single source of truth for your illustrated Jupyter Notebooks (`.ipynb`), browser HTML preview, and standalone diagram images.

## Quick Commands

```bash
# Build HTML preview (+ bundled .ipynb), standalone .ipynb notebooks, and extracted images
./fastapi-gdrive_src/build.sh

# Build standalone .ipynb notebooks only (ideal for Google Drive + Colab sharing) -> fastapi-gdrive_jupyter/
./fastapi-gdrive_src/build_jupyter.sh

# Build 2-column HTML preview site with bundled .ipynb downloads -> fastapi-gdrive_html/
./fastapi-gdrive_src/build_html.sh

# Extract rendered diagram images -> fastapi-gdrive_images/
./fastapi-gdrive_src/build_image.sh

# Run AI Dry-Run verification only (without writing output files)
uv run drawlib build jupyter fastapi-gdrive_src/ --dry-run

# Serve the static HTML notebook preview in your browser (fastapi-gdrive_html/)
./fastapi-gdrive_src/serve.sh
```
