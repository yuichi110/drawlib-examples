# drawlib-examples

Official showcase gallery of real-world documents (`doc`), 16:9 presentations (`slide`), and standalone Python illustrations (`images`) built with [**Drawlib**](https://github.com/yuichi110/drawlib).

---

## Repository Structure

```text
drawlib-examples/
├── build.sh                        # Clean-builds all examples + portal into docs/
├── portal/                         # Static portal overlay (docs/index.html & image galleries)
├── examples/                       # Source of Truth (organized by drawlib project type)
│   ├── doc/
│   │   ├── dogfooding/             # Bilingual (EN/JA) architectural whitepaper
│   │   └── quickstart/             # 16-chapter onboarding handbook
│   ├── slide/
│   │   ├── about-drawlib/          # 16:9 Drawlib showcase presentation deck
│   │   └── ddos-incident-response/ # 16:9 cloud security postmortem deck
│   └── images/
│       ├── logo/                   # Official Drawlib brand logos & favicon
│       └── ogp/                    # 1280x640 GitHub Social Preview / OGP banners
└── docs/                           # Generated GitHub Pages output (100% build artifact)
```

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
