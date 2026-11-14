# drawlib-examples

Official showcase gallery of multi-page documentation sites (`site`), searchable API catalogs (`catalog`), linear documents (`doc`), 16:9 presentations (`slide`), standalone Python illustrations (`images`), and external document-engine use cases (`engine`) built with [**Drawlib**](https://github.com/yuichi110/drawlib).

---

## Repository Structure

```text
drawlib-examples/
├── build.sh                        # Clean-builds all examples + portal into docs/
├── portal/                         # Static portal overlay (docs/index.html & image galleries)
├── examples/                       # Source of Truth (organized by drawlib project type)
│   ├── doc/
│   │   └── gemini_latency/         # Bilingual (EN/JA) Gemini 3.8 Flash latency & architecture report
│   ├── slide/
│   │   └── ddos-incident-response/ # 16:9 cloud security postmortem deck
│   └── images/
│       ├── animation/              # AI-authored web & social animations (APNG, WebP & GIF)
│       ├── logo/                   # Official Drawlib brand logos & favicon
│       └── ogp/                    # 1280x640 GitHub Social Preview / OGP banners
└── docs/                           # Generated GitHub Pages output (100% build artifact)
```

*(Note: External `site`, `catalog`, `doc`, `slide`, and `engine` showcases linked directly from `portal/index.html` include the official Drawlib portals — [Drawlib Documentation](https://www.drawlib.com/), [Drawlib Architecture](https://www.drawlib.com/architecture/), [Drawlib API Specification](https://www.drawlib.com/api/), [Drawlib Quickstart Onboarding Guide](https://www.drawlib.com/quickstart/en/index.html), [About Drawlib — Official Showcase Deck](https://www.drawlib.com/about-drawlib/en/index.html), and [PNI Software Health Diagnostic Report (Drawlib Audit)](https://www.drawlib.com/reports/pni-full-audit/) maintained in [`yuichi110/drawlib`](https://github.com/yuichi110/drawlib) — as well as 6 multi-language OSS showcase suites:)*

| Language | Target OSS | Portal Hub | User Guide (`site`) | Architecture (`site`) | API Reference (`catalog`) | Health Audit (`pni501`) | Repository |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| **Python** | **FastAPI** `v0.162.2` | [fastapi.drawlib.com](https://fastapi.drawlib.com/) | [User Guide](https://fastapi.drawlib.com/user_guide/) | [Architecture](https://fastapi.drawlib.com/architecture/) | [API](https://fastapi.drawlib.com/api/) | [PNI501 (93/S)](https://fastapi.drawlib.com/pni501/) | [`yuichi110/drawlib-fastapi`](https://github.com/yuichi110/drawlib-fastapi) |
| **Java** | **MyBatis 3** `v3.6.0` | [mybatis3.drawlib.com](https://mybatis3.drawlib.com/) | [User Guide](https://mybatis3.drawlib.com/user_guide/) | [Architecture](https://mybatis3.drawlib.com/architecture/) | [API](https://mybatis3.drawlib.com/api/) | [PNI501 (90/S)](https://mybatis3.drawlib.com/pni501/) | [`yuichi110/drawlib-mybatis3`](https://github.com/yuichi110/drawlib-mybatis3) |
| **Go** | **Cobra** `v1.10.2` | [cobra.drawlib.com](https://cobra.drawlib.com/) | [User Guide](https://cobra.drawlib.com/user_guide/) | [Architecture](https://cobra.drawlib.com/architecture/) | [API](https://cobra.drawlib.com/api/) | [PNI501 (94/S)](https://cobra.drawlib.com/pni501/) | [`yuichi110/drawlib-cobra`](https://github.com/yuichi110/drawlib-cobra) |
| **PHP** | **Slim 4** `v4.15.3` | [slim.drawlib.com](https://slim.drawlib.com/) | [User Guide](https://slim.drawlib.com/user_guide/) | [Architecture](https://slim.drawlib.com/architecture/) | [API](https://slim.drawlib.com/api/) | [PNI501 (94/S)](https://slim.drawlib.com/pni501/) | [`yuichi110/drawlib-slim`](https://github.com/yuichi110/drawlib-slim) |
| **JavaScript** | **htmx** `v4.0.1` | [htmx.drawlib.com](https://htmx.drawlib.com/) | [User Guide](https://htmx.drawlib.com/user_guide/) | [Architecture](https://htmx.drawlib.com/architecture/) | [API](https://htmx.drawlib.com/api/) | [PNI501 (91/S)](https://htmx.drawlib.com/pni501/) | [`yuichi110/drawlib-htmx`](https://github.com/yuichi110/drawlib-htmx) |
| **TypeScript** | **Zod** `v4.6.7` | [zod.drawlib.com](https://zod.drawlib.com/) | [User Guide](https://zod.drawlib.com/user_guide/) | [Architecture](https://zod.drawlib.com/architecture/) | [API](https://zod.drawlib.com/api/) | [PNI501 (91/S)](https://zod.drawlib.com/pni501/) | [`yuichi110/drawlib-zod`](https://github.com/yuichi110/drawlib-zod) |

---

## Quick Start

### 1. Install Dependencies (`uv`)

```bash
uv sync
```

*(Note: For PDF export via headless Chromium on a fresh machine, run `uv run drawlib cache download --browser` once if Chromium is not yet cached.)*

### 2. Build Everything into `docs/`

```bash
./build.sh
```

`./build.sh` cleans `docs/`, compiles every project under `examples/` into HTML, PDF, DOCX / PPTX, and PNG assets, copies `portal/` into `docs/`, and runs `drawlib serve docs/ --check` to verify all links and assets.

### 3. Preview Locally

```bash
uv run drawlib serve docs/
```

---

## License

Apache License 2.0 — see [LICENSE](./LICENSE).
