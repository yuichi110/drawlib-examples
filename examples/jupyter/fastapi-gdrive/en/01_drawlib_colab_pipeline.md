# 01. Drawlib & Google Colab Automated Publishing Pipeline

This hands-on notebook is **automatically generated from Git Markdown source using Drawlib and delivered directly to Google Colab via Google Drive**.

```drawlib align=center code=fold file=01_pipeline_git_to_colab.png caption="Automated Publishing Pipeline: Git Markdown Source -> Drawlib -> rclone -> Google Drive -> Google Colab"
from drawlib.canvas import save, setup
from drawlib.icons import ai, code as code_icons, phosphor, workspace
from drawlib.lines import line
from drawlib.shapes import circle, rectangle
from drawlib.styles import Styles
from drawlib.text import text

setup(width=128, height=58)

# Outer container
rectangle((64, 32.5), width=122, height=45, style=Styles.MutedDashed.patch(shape_r=2.0))
text(
    (64, 51.0),
    "Illustrated Notebook as Code: Git Markdown -> Drawlib -> Google Drive -> Colab",
    style=Styles.DarkBold.patch(text_size=10.6),
)

# Stage 1: Git Markdown Source
rectangle((16.0, 30.0), width=23, height=34, style=Styles.Neutral.patch(shape_r=1.8))
phosphor.git_branch((16.0, 41.2), width=4.8, style=Styles.PrimaryBold)
text((16.0, 34.4), "1. Git Source", style=Styles.DarkBold.patch(text_size=10.0))
text(
    (16.0, 22.8),
    "docs_src/fastapi/\n• Pure Markdown\n• drawlib code\n• Git SSOT",
    style=Styles.Dark.patch(text_size=9.2),
)

line((27.5, 30.0), (31.5, 30.0), arrow_head="->", style=Styles.DarkBold)

# Stage 2: Drawlib Compiler (Focal Hero)
rectangle((43.0, 30.0), width=23, height=34, style=Styles.PrimaryFlat.patch(shape_r=1.8))
circle((43.0, 41.2), radius=3.4, style=Styles.White.patch(shape_line_width=0))
ai.jupyter((43.0, 41.2), width=4.5, style=Styles.Neutral)
text((43.0, 34.0), "2. drawlib build", style=Styles.WhiteBold.patch(text_size=10.0))
text(
    (43.0, 22.8),
    "build jupyter\n• Base64 diagrams\n• Clean .ipynb\n• Zero local HTML",
    style=Styles.White.patch(text_size=9.2),
)

line((54.5, 30.0), (58.5, 30.0), arrow_head="->", style=Styles.DarkBold)

# Stage 3: rclone copy
rectangle((70.0, 30.0), width=23, height=34, style=Styles.PrimaryNeutral.patch(shape_r=1.8))
phosphor.arrows_clockwise((70.0, 41.2), width=4.8, style=Styles.PrimaryBold)
text((70.0, 34.0), "3. rclone sync", style=Styles.DarkBold.patch(text_size=10.0))
text(
    (70.0, 22.8),
    "-M metadata-set\n• Colab MIME type\n• Preserves IDs\n• Fast & headless",
    style=Styles.Dark.patch(text_size=9.2),
)

line((81.5, 30.0), (85.5, 30.0), arrow_head="->", style=Styles.DarkBold)

# Stage 4: Google Drive Shared Folder
rectangle((97.0, 30.0), width=23, height=34, style=Styles.SecondaryNeutral.patch(shape_r=1.8))
workspace.google_drive((97.0, 41.2), width=4.8, style=Styles.Neutral)
text((97.0, 34.4), "4. Google Drive", style=Styles.DarkBold.patch(text_size=10.0))
text(
    (97.0, 22.8),
    "Shared Folder\n• Viewer role\n• Clean .ipynb\n• Always updated",
    style=Styles.Dark.patch(text_size=9.2),
)

line((108.5, 30.0), (112.5, 30.0), arrow_head="->", style=Styles.DarkBold)

# Stage 5: Google Colaboratory (Recipient run)
rectangle((118.5, 30.0), width=18, height=34, style=Styles.Neutral.patch(shape_r=1.8))
code_icons.colab((118.5, 41.2), width=4.8, style=Styles.Neutral)
text((118.5, 34.4), "5. Colab", style=Styles.DarkBold.patch(text_size=10.0))
text(
    (118.5, 22.8),
    "Run in Cloud\n• Zero install\n• Free GPUs\n• Interactive",
    style=Styles.Dark.patch(text_size=9.2),
)

# Bottom ribbon
rectangle(
    (64, 5.2),
    width=122,
    height=6.4,
    style=Styles.Neutral.patch(shape_r=1.2),
    text="Illustration as Code   •   Self-Contained Base64 Diagrams   •   Zero Local Setup for Learners",
    text_style=Styles.DarkBold.patch(text_size=9.6),
)

save()
```

---

## 1. How This Notebook Works (Illustration as Code with Drawlib)

Sharing raw Jupyter notebooks (`.ipynb`) often introduces friction:
- Pasted screenshot images suffer from broken links, blurry rendering, and stale content.
- Bloated output blobs in JSON make Git diffs and code review noisy.
- Recipients are burdened with local Python and virtual environment setup.

**[Drawlib](https://www.drawlib.com/)** solves these challenges cleanly.

### Key Guarantees of Drawlib
1. **Authored Exclusively in Git Markdown & Python**:
   Both prose narratives and architecture diagrams are maintained in plain text under Git version control.
2. **100% Self-Contained Base64 Vector Embedding**:
   All diagrams are converted at build time into inline Base64 Data URIs directly inside the `.ipynb` file. No external image host is required.
3. **Automated Publishing via Google Drive & rclone**:
   Compiled `.ipynb` notebooks are synced directly to a shared Google Drive folder using `rclone`, allowing recipients to open and run them in **Google Colaboratory** in a single click.

> [!TIP] Official Website & Documentation
> To explore Drawlib's complete architecture, drawing primitives, and domain icon suites, visit:
> - **Official Website**: [https://www.drawlib.com/](https://www.drawlib.com/)
> - **API & CLI Reference**: [https://www.drawlib.com/api/](https://www.drawlib.com/api/)

---

## 2. Environment Verification

Run this cell (`Shift + Enter`) on Google Colab to verify the runtime Python environment.

```python
import sys
import platform

print("Python Version:", sys.version)
print("Platform:", platform.platform())
print("Google Colab Ready!")
```

In the next chapter, we dive into **FastAPI Hello World and core request handling**!

