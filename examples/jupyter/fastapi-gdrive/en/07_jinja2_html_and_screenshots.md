# 07. Jinja2 HTML Templates & Browser Screenshots

While FastAPI excels at serving structured JSON APIs, many real-world applications also need server-side rendered (SSR) HTML pages—such as admin dashboards, status reports, email previews, or printable invoices. FastAPI integrates seamlessly with **Jinja2** via `fastapi.templating.Jinja2Templates`.

In this chapter, you will build a FastAPI endpoint that renders a styled HTML dashboard with **Jinja2**, test it via `TestClient`, and capture a **real headless browser screenshot** right inside Google Colab using **Playwright**.

```drawlib align=center code=fold file=07_jinja2_screenshot_pipeline.png caption="FastAPI + Jinja2 HTML Rendering and Headless Playwright Screenshot Pipeline"
from drawlib.canvas import save, setup
from drawlib.icons import code as code_icons, phosphor
from drawlib.lines import line
from drawlib.shapes import rectangle
from drawlib.styles import Styles
from drawlib.text import text

setup(width=128, height=56)

# Outer container
rectangle((64, 31.0), width=122, height=42, style=Styles.MutedDashed.patch(shape_r=2.0))
text(
    (64, 48.0),
    "Jinja2 SSR & Screenshot Pipeline: Endpoint -> Template -> HTML -> Playwright PNG",
    style=Styles.DarkBold.patch(text_size=10.4),
)

# 1. FastAPI Endpoint
rectangle((19.0, 28.5), width=24, height=31, style=Styles.Neutral.patch(shape_r=1.8))
code_icons.fastapi((19.0, 39.0), width=5.0, style=Styles.Dark)
text((19.0, 32.8), "FastAPI Route", style=Styles.DarkBold.patch(text_size=10.0))
text(
    (19.0, 21.5),
    "GET /dashboard\n• Request object\n• Context dict\n• TestClient(app)",
    style=Styles.Dark.patch(text_size=9.5),
)

line((31.0, 28.5), (37.0, 28.5), arrow_head="->", style=Styles.DarkBold)

# 2. Jinja2Templates
rectangle((49.0, 28.5), width=24, height=31, style=Styles.PrimaryNeutral.patch(shape_r=1.8))
phosphor.file_html((49.0, 39.0), width=5.0, style=Styles.PrimaryBold)
text((49.0, 32.8), "Jinja2Templates", style=Styles.DarkBold.patch(text_size=10.0))
text(
    (49.0, 21.5),
    "dashboard.html\n• {{ title }}\n• {% for m ... %}\n• Auto-escaping",
    style=Styles.Dark.patch(text_size=9.5),
)

line((61.0, 28.5), (67.0, 28.5), arrow_head="->", style=Styles.DarkBold)

# 3. HTMLResponse (Focal Hero)
rectangle((79.0, 28.5), width=24, height=31, style=Styles.PrimaryFlat.patch(shape_r=1.8))
phosphor.code((79.0, 39.0), width=5.0, style=Styles.White)
text((79.0, 32.8), "HTMLResponse", style=Styles.WhiteBold.patch(text_size=10.0))
text(
    (79.0, 21.5),
    "HTTP 200 OK\n• text/html\n• Rendered DOM\n• Embedded CSS",
    style=Styles.White.patch(text_size=9.5),
)

line((91.0, 28.5), (97.0, 28.5), arrow_head="->", style=Styles.DarkBold)

# 4. Playwright Screenshot
rectangle((109.0, 28.5), width=24, height=31, style=Styles.SecondaryNeutral.patch(shape_r=1.8))
phosphor.camera((109.0, 39.0), width=5.0, style=Styles.PrimaryBold)
text((109.0, 32.8), "Playwright PNG", style=Styles.DarkBold.patch(text_size=10.0))
text(
    (109.0, 21.5),
    "Chromium\n• set_content()\n• screenshot()\n• IPython Image",
    style=Styles.Dark.patch(text_size=9.5),
)

# Bottom ribbon
rectangle(
    (64, 5.2),
    width=122,
    height=6.2,
    style=Styles.Neutral.patch(shape_r=1.2),
    text="Server-Side Rendering   •   In-Process TestClient   •   Visual Verification via Headless Chromium",
    text_style=Styles.DarkBold.patch(text_size=9.5),
)

save()
```

```python
!pip install -q fastapi httpx jinja2 playwright
!playwright install --with-deps chromium
```

---

## 1. Creating a Jinja2 Template & FastAPI Endpoint

To keep this notebook 100% self-contained in Google Colab, we write a clean `dashboard.html` template into a temporary directory and wire it to `Jinja2Templates`.

```python
from pathlib import Path
import tempfile

from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from fastapi.testclient import TestClient

template_dir = Path(tempfile.mkdtemp(prefix="fastapi_jinja2_"))
template_html = """<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8" />
  <title>{{ title }}</title>
  <style>
    body { font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif; background: #f8fafc; color: #0f172a; margin: 0; padding: 32px; }
    .container { max-width: 780px; margin: 0 auto; background: #ffffff; border: 1px solid #e2e8f0; border-radius: 12px; padding: 28px; box-shadow: 0 4px 12px rgba(15, 23, 42, 0.06); }
    .header { display: flex; justify-content: space-between; align-items: center; border-bottom: 1px solid #e2e8f0; padding-bottom: 16px; margin-bottom: 24px; }
    .badge { background: #dbeafe; color: #1d4ed8; font-weight: 600; font-size: 13px; padding: 4px 12px; border-radius: 999px; }
    .grid { display: grid; grid-template-columns: repeat(3, 1fr); gap: 16px; }
    .card { background: #f8fafc; border: 1px solid #e2e8f0; border-radius: 8px; padding: 16px; }
    .label { font-size: 12px; color: #64748b; text-transform: uppercase; letter-spacing: 0.04em; }
    .value { font-size: 24px; font-weight: 700; margin-top: 6px; color: #0f172a; }
  </style>
</head>
<body>
  <div class="container">
    <div class="header">
      <div>
        <h1 style="margin: 0; font-size: 22px;">{{ title }}</h1>
        <p style="margin: 4px 0 0; color: #64748b; font-size: 14px;">Service: {{ service_name }} ({{ version }})</p>
      </div>
      <span class="badge">{{ status }}</span>
    </div>
    <div class="grid">
      {% for metric in metrics %}
      <div class="card">
        <div class="label">{{ metric.label }}</div>
        <div class="value">{{ metric.value }}</div>
      </div>
      {% endfor %}
    </div>
  </div>
</body>
</html>
"""
(template_dir / "dashboard.html").write_text(template_html, encoding="utf-8")

app = FastAPI()
templates = Jinja2Templates(directory=str(template_dir))


@app.get("/dashboard", response_class=HTMLResponse)
def read_dashboard(request: Request):
    return templates.TemplateResponse(
        request=request,
        name="dashboard.html",
        context={
            "title": "FastAPI Service Status",
            "service_name": "orders-api",
            "version": "v1.4.2",
            "status": "HEALTHY",
            "metrics": [
                {"label": "Requests / min", "value": "12,480"},
                {"label": "P95 Latency", "value": "18.4 ms"},
                {"label": "Error Rate", "value": "0.02%"},
            ],
        },
    )


client = TestClient(app)
response = client.get("/dashboard")
print("Status:", response.status_code)
print("Content-Type:", response.headers["content-type"])
assert response.status_code == 200
assert "orders-api" in response.text
```

---

## 2. Capturing a Browser Screenshot with Playwright

Because Jupyter and Google Colab already run an active `asyncio` event loop, use **`async_playwright`** with top-level `await` instead of `sync_playwright`. We feed `response.text` directly into headless Chromium via `page.set_content()` and display the resulting PNG inline.

```python
from IPython.display import Image, display
from playwright.async_api import async_playwright

screenshot_path = "dashboard_screenshot.png"

async with async_playwright() as p:
    browser = await p.chromium.launch(args=["--no-sandbox"])
    page = await browser.new_page(viewport={"width": 900, "height": 420})
    await page.set_content(response.text, wait_until="load")
    await page.screenshot(path=screenshot_path, full_page=True)
    await browser.close()

display(Image(filename=screenshot_path))
```

---

## 3. Sharing Dependencies Across JSON & HTML Routes

A major advantage of FastAPI is that both JSON API endpoints and Jinja2 HTML routes share the exact same `Depends` pipeline (authentication, DB sessions, and settings).

```drawlib align=center code=fold file=07_json_vs_html_routing.png caption="Unified FastAPI Dependency Pipeline Serving Both JSON APIs and Jinja2 HTML Views"
from drawlib.canvas import save, setup
from drawlib.icons import phosphor
from drawlib.lines import line
from drawlib.shapes import rectangle
from drawlib.styles import Styles
from drawlib.text import text

setup(width=128, height=54)

rectangle((64, 27.0), width=122, height=46, style=Styles.MutedDashed.patch(shape_r=2.0))
text(
    (64, 45.5),
    "One FastAPI Application: Shared Depends() Across JSON APIs & Jinja2 HTML",
    style=Styles.DarkBold.patch(text_size=10.4),
)

# Shared Depends
rectangle((24.0, 24.5), width=32, height=28, style=Styles.PrimaryNeutral.patch(shape_r=1.8))
phosphor.plug((24.0, 33.5), width=5.0, style=Styles.PrimaryBold)
text((24.0, 27.5), "Shared Depends()", style=Styles.DarkBold.patch(text_size=10.0))
text(
    (24.0, 18.0),
    "• Current User / Auth\n• Metrics / DB Query\n• App Settings",
    style=Styles.Dark.patch(text_size=9.5),
)

# Branches
line((40.0, 29.0), (54.0, 34.0), arrow_head="->", style=Styles.DarkBold)
line((40.0, 20.0), (54.0, 15.0), arrow_head="->", style=Styles.DarkBold)

# JSON Route
rectangle((72.0, 34.0), width=36, height=13, style=Styles.Neutral.patch(shape_r=1.5))
text((72.0, 36.2), "GET /api/metrics", style=Styles.DarkBold.patch(text_size=10.0))
text((72.0, 31.2), "Pydantic -> JSONResponse", style=Styles.Dark.patch(text_size=9.5))

# HTML Route
rectangle((72.0, 15.0), width=36, height=13, style=Styles.PrimaryFlat.patch(shape_r=1.5))
text((72.0, 17.2), "GET /dashboard", style=Styles.WhiteBold.patch(text_size=10.0))
text((72.0, 12.2), "Jinja2 -> HTMLResponse", style=Styles.White.patch(text_size=9.5))

line((90.0, 34.0), (98.0, 34.0), arrow_head="->", style=Styles.DarkBold)
line((90.0, 15.0), (98.0, 15.0), arrow_head="->", style=Styles.DarkBold)

# Outputs
rectangle((109.5, 34.0), width=23, height=13, style=Styles.SecondaryNeutral.patch(shape_r=1.5))
text((109.5, 34.0), "JSON Client\n(SPA / Mobile)", style=Styles.DarkBold.patch(text_size=9.5))

rectangle((109.5, 15.0), width=23, height=13, style=Styles.SecondaryNeutral.patch(shape_r=1.5))
text((109.5, 15.0), "Browser / PNG\n(Playwright)", style=Styles.DarkBold.patch(text_size=9.5))

save()
```

In the final chapter (Chapter 8), we will zoom out to the production cloud architecture, Lifespan startup/shutdown hooks, and `BackgroundTasks`.

