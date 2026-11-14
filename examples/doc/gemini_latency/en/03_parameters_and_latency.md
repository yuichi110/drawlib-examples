# 3. Parameters & Latency

Chapter 2 examined the baseline delivery mechanics of blocking (`generate_content`) and streaming (`generate_content_stream`) calls against `gemini-3.8-flash`. In this chapter, we analyze empirical measurements from `src/gemini_evaluation/benchmark_thinking.py` and `src/gemini_evaluation/benchmark_adaptive_thinking.py` to quantify the single largest determinant of Gemini 3.8 Flash latency: **`ThinkingConfig` (internal reasoning token control)**. We evaluate all six thinking configurations across blocking and streaming modes, derive the linear scaling law linking internal reasoning tokens to Time to First Token (TTFT), and demonstrate the fundamental speed-versus-accuracy dilemma across query complexity tiers (Tiers 1–3).

```drawlib align=center code=fold width=100% file=ch03_thinking_benchmark_hero.png caption="Figure 3-1: TTFT, Total Completion Time, and Reasoning Token Comparison across Blocking (generate_content) vs. Streaming (generate_content_stream) × All 6 ThinkingConfig Levels"
from drawlib.canvas import save, setup
from drawlib.icons import phosphor
from drawlib.lines import line
from drawlib.shapes import rectangle
from drawlib.styles import Styles
from drawlib.text import text
from drawlib.utils import load_thinking_benchmark_all

setup(width=168, height=86, dpi=150)

# Outer structural frame
rectangle((84.0, 43.0), width=164.0, height=82.0, style=Styles.MutedDashed.patch(shape_r=2.0))
text(
    (84.0, 79.8),
    "Blocking vs. Streaming × All 6 ThinkingConfig Levels: TTFT & Total Latency",
    style=Styles.DarkBold.patch(text_size=12.0),
)

# Legend bar at top (Neutral container)
rectangle((84.0, 73.2), width=156.0, height=5.6, style=Styles.Neutral.patch(shape_r=1.0))

rectangle((12.0, 73.2), width=4.0, height=2.2, style=Styles.SecondaryNeutral.patch(shape_r=0.4))
text((15.0, 73.2), "Blocking Total (= TTFT)", style=Styles.DarkBold.patch(text_size=10.0, halign="left"))

rectangle((64.0, 73.2), width=4.0, height=2.2, style=Styles.PrimaryFlat.patch(shape_r=0.4))
text((67.0, 73.2), "Streaming TTFT (First Token)", style=Styles.PrimaryBold.patch(text_size=10.0, halign="left"))

rectangle((120.0, 73.2), width=4.0, height=2.2, style=Styles.PrimaryNeutral.patch(shape_r=0.4))
text((123.0, 73.2), "Streaming Total (Completion)", style=Styles.DarkBold.patch(text_size=10.0, halign="left"))

rows = load_thinking_benchmark_all()
by_key = {(r["mode"], r["thinking"]): r for r in rows if r["trial"] == 1}

# Coordinate mapping for horizontal bars: X0 = 28.0, width = 50.0 for 0..14000 ms
X0 = 28.0
MAX_MS = 14000.0
SCALE = 50.0 / MAX_MS

for ms in range(0, 14001, 3500):
    tx = X0 + ms * SCALE
    line((tx, 14.5), (tx, 67.5), style=Styles.MutedDashed.patch(line_width=0.7))
    lbl = f"{ms / 1000:.1f}s" if ms % 1000 != 0 else (f"{ms // 1000}s" if ms > 0 else "0s")
    text((tx, 12.0), lbl, style=Styles.Dark.patch(text_size=10.0))

# Right-side Token & Output Table Header
rectangle((136.5, 66.8), width=49.0, height=4.4, style=Styles.PrimaryNeutral.patch(shape_r=0.8))
text((120.5, 66.8), "Block ThTok", style=Styles.DarkBold.patch(text_size=10.0))
text((137.5, 66.8), "Stream ThTok", style=Styles.PrimaryBold.patch(text_size=10.0))
text((153.0, 66.8), "OutTok", style=Styles.DarkBold.patch(text_size=10.0))

thinking_specs = [
    ("0", "0 (budget=0)", "Reasoning Off", 60.5),
    ("minimal", "minimal", "Minimal Level", 51.8),
    ("low", "low", "Light Reasoning", 43.1),
    ("medium", "medium", "Moderate Level", 34.4),
    ("high", "high", "Deep Reasoning", 25.7),
    ("default", "default", "Dynamic Default", 17.0),
]

for t_key, label_main, label_sub, ry in thinking_specs:
    rb = by_key[("blocking", t_key)]
    rs = by_key[("streaming", t_key)]

    if t_key in {"0", "minimal"}:
        rectangle((84.0, ry), width=156.0, height=7.6, style=Styles.SecondaryNeutral.patch(shape_r=1.0, alpha=0.3))
    else:
        rectangle((84.0, ry), width=156.0, height=7.6, style=Styles.LightFlat.patch(shape_r=1.0, alpha=0.45))

    text((6.8, ry + 1.3), label_main, style=Styles.DarkBold.patch(text_size=10.5, halign="left"))
    text((6.8, ry - 1.5), label_sub, style=Styles.Muted.patch(text_size=10.0, halign="left"))

    # Top bar in group: Blocking (TTFT == Total)
    wb = rb["total_ms"] * SCALE
    rectangle((X0 + wb / 2, ry + 1.6), width=wb, height=2.2, style=Styles.SecondaryNeutral.patch(shape_r=0.4))
    text(
        (X0 + wb + 1.0, ry + 1.6),
        f"{rb['total_ms']:,.0f} ms",
        style=Styles.DarkBold.patch(text_size=10.0, halign="left"),
    )

    # Bottom bar in group: Streaming (TTFT solid + Total lighter)
    ws_tot = rs["total_ms"] * SCALE
    ws_ttft = rs["ttft_ms"] * SCALE
    rectangle((X0 + ws_tot / 2, ry - 1.5), width=ws_tot, height=2.2, style=Styles.PrimaryNeutral.patch(shape_r=0.4))
    rectangle((X0 + ws_ttft / 2, ry - 1.5), width=ws_ttft, height=2.2, style=Styles.PrimaryFlat.patch(shape_r=0.4))
    text(
        (X0 + ws_tot + 1.0, ry - 1.5),
        f"TTFT {rs['ttft_ms']:,.0f} / {rs['total_ms']:,.0f} ms",
        style=Styles.PrimaryBold.patch(text_size=10.0, halign="left"),
    )

    # Right table cells
    rectangle((136.5, ry), width=49.0, height=6.4, style=Styles.WhiteFlat.patch(shape_r=0.8))
    text((120.5, ry), f"{rb['thoughts_tokens']} tok", style=Styles.Dark.patch(text_size=10.0))
    text((137.5, ry), f"{rs['thoughts_tokens']} tok", style=Styles.PrimaryBold.patch(text_size=10.0))
    text((153.0, ry), f"{rs['output_tokens']} tok", style=Styles.Dark.patch(text_size=10.0))

# Bottom callout banner
rectangle((84.0, 5.8), width=156.0, height=6.4, style=Styles.PrimaryNeutral.patch(shape_r=1.2))
phosphor.lightning((9.2, 5.8), width=3.2, style=Styles.PrimaryBold)
text(
    (12.6, 5.8),
    "Takeaway: Setting thinking=0 or minimal eliminates reasoning tokens (0 tok), cutting Streaming TTFT to 1,205 ms (-88% vs. default).",
    style=Styles.DarkBold.patch(text_size=10.0, halign="left"),
)

save()
```

---

## 3.1 `ThinkingConfig` Levels & Empirical Benchmark across Blocking vs. Streaming

When calling `gemini-3.8-flash` via the Google AI Studio SDK (`google-genai`), internal reasoning before the first visible text token is governed by `types.ThinkingConfig`. In `src/gemini_evaluation/llm_call.py` (`resolve_thinking_config()`), we expose six standardized configuration levels covering explicit zero budget, four `ThinkingLevel` enum presets, and the server's dynamic default:

```python
from google import genai
from google.genai import types

client = genai.Client(api_key=GEMINI_KEY)

# Option 1: Disable internal reasoning completely for fastest TTFT
config_zero = types.GenerateContentConfig(
    thinking_config=types.ThinkingConfig(thinking_budget=0),
    temperature=0.2,
)

# Option 2: Enable light internal reasoning for multi-step calculations
config_low = types.GenerateContentConfig(
    thinking_config=types.ThinkingConfig(thinking_level=types.ThinkingLevel.LOW),
    temperature=0.2,
)
```

| Option Value (`thinking=`) | Normalized Label | SDK Configuration (`types.ThinkingConfig` via `llm_call.py`) | Measured Reasoning Tokens (`ThTok`) | Behavior & Primary Use Cases |
| :--- | :--- | :--- | :--- | :--- |
| **`0`** (or `"0"`) | `"0"` | `ThinkingConfig(thinking_budget=0)` | **`0 tok`** | Hard-caps internal reasoning budget at `0` tokens. Skips internal scratchpad generation entirely, delivering the fastest TTFT (`1,205–1,546 ms`). Ideal for greetings, standard procedures, and stage-1 routers. |
| **`1`** (or `"minimal"`) | `"minimal"` | `ThinkingConfig(thinking_budget=256)` *(because `gemini-3.8-flash` only supports `LOW` / `MEDIUM` / `HIGH` enum levels)* | **`0 tok`** | Minimal reasoning budget (`256 tok` cap). Produces `0` reasoning tokens on standard conversational prompts, avoiding multi-second reasoning overhead. |
| **`2`** (or `"low"`) | `"low"` | `ThinkingConfig(thinking_budget=4096)` *(equivalent to `ThinkingLevel.LOW`)* | **`351–557 tok`** | Light internal reasoning (`~4.3–5.5 s` TTFT). Provides sufficient scratchpad capacity to prevent arithmetic errors in multi-step cost and transfer-time calculations. |
| **`3`** (or `"medium"`) | `"medium"` | `ThinkingConfig(thinking_level=MEDIUM)` | **`441–592 tok`** | Moderate internal reasoning (`~6.2–6.7 s` TTFT). Explicit specification of the server's default level. |
| **`4`** (or `"high"`) | `"high"` | `ThinkingConfig(thinking_level=HIGH)` | **`817–870 tok`** | Deep internal reasoning (`~9.0–9.7 s` TTFT) suited for complex logic or coding tasks, but introduces heavy wait times for interactive chat. |
| **`None`** (or `"default"`) | `"default"` | Omitted (Dynamic server default = equivalent to `MEDIUM`) | **`467–1,006 tok`** | Default behavior when `thinking_config` is omitted. Dynamically allocates hundreds of reasoning tokens even on routine prompts, adding `7.5–10.4 s` of latency. |

### Complete 18-Run Benchmark Table (`Blocking` vs. `Streaming`)

Using `src/gemini_evaluation/benchmark_thinking.py`, we benchmarked all six `ThinkingConfig` options across **Blocking (`generate_content`)** and **Streaming (`generate_content_stream`, Trial 1 and Trial 2)** on an identical PC technical support prompt (initial troubleshooting steps for an unresponsive laptop). Figure 3-1 and the table below summarize all 18 executions.

| Delivery Mode | `thinking` Level | TTFT (ms) | Total Completion (ms) | Stream Delivery Window (`Total - TTFT`) | Reasoning Tokens (`ThTok`) | Output Tokens (`OutTok`) | Output Chars |
| :--- | :--- | ---: | ---: | ---: | ---: | ---: | ---: |
| **Blocking (`generate_content`)** | **`0`** | **3,360.41** | **3,360.41** | 0.00 ms (Single payload) | **0** | 192 | 338 chars |
| **Blocking (`generate_content`)** | **`minimal`** | **4,331.59** | **4,331.59** | 0.00 ms (Single payload) | **0** | 183 | 328 chars |
| **Blocking (`generate_content`)** | **`low`** | 10,052.14 | 10,052.14 | 0.00 ms (Single payload) | 557 | 222 | 388 chars |
| **Blocking (`generate_content`)** | **`medium`** | 8,296.36 | 8,296.36 | 0.00 ms (Single payload) | 544 | 198 | 360 chars |
| **Blocking (`generate_content`)** | **`high`** | 12,509.75 | 12,509.75 | 0.00 ms (Single payload) | 852 | 213 | 396 chars |
| **Blocking (`generate_content`)** | **`default`** | 7,548.20 | 7,548.20 | 0.00 ms (Single payload) | 467 | 222 | 396 chars |
| **Streaming (`generate_content_stream` #1)** | **`0`** | **1,205.35** | **3,192.41** | 1,987.06 ms | **0** | 217 | 373 chars |
| **Streaming (`generate_content_stream` #1)** | **`minimal`** | **3,324.42** | **5,675.79** | 2,351.37 ms | **0** | 191 | 322 chars |
| **Streaming (`generate_content_stream` #1)** | **`low`** | 5,519.63 | 6,777.01 | 1,257.38 ms | 351 | 200 | 356 chars |
| **Streaming (`generate_content_stream` #1)** | **`medium`** | 6,214.92 | 7,682.10 | 1,467.18 ms | 441 | 212 | 381 chars |
| **Streaming (`generate_content_stream` #1)** | **`high`** | 9,703.48 | 11,528.81 | 1,825.33 ms | 870 | 209 | 367 chars |
| **Streaming (`generate_content_stream` #1)** | **`default`** | 10,430.12 | 12,005.51 | 1,575.39 ms | 1,006 | 215 | 382 chars |
| **Streaming (`generate_content_stream` #2)** | **`0`** | **1,546.22** | **3,681.50** | 2,135.28 ms | **0** | 198 | 341 chars |
| **Streaming (`generate_content_stream` #2)** | **`minimal`** | **1,612.80** | **3,590.15** | 1,977.35 ms | **0** | 195 | 340 chars |
| **Streaming (`generate_content_stream` #2)** | **`low`** | 4,312.40 | 6,120.85 | 1,808.45 ms | 362 | 210 | 370 chars |
| **Streaming (`generate_content_stream` #2)** | **`medium`** | 6,720.11 | 8,410.33 | 1,690.22 ms | 592 | 204 | 362 chars |
| **Streaming (`generate_content_stream` #2)** | **`high`** | 9,012.55 | 10,890.40 | 1,877.85 ms | 817 | 218 | 385 chars |
| **Streaming (`generate_content_stream` #2)** | **`default`** | 8,150.30 | 9,920.18 | 1,769.88 ms | 742 | 208 | 371 chars |

Two architectural conclusions stand out from these measurements:
1. **The Hidden Cost of Omitting `thinking_config` (`default`)**: Leaving `thinking_config` unset triggers `467–1,006` internal reasoning tokens even on straightforward support queries, delaying first-token arrival to `7.55–10.43 s`. Explicitly setting `thinking=0` eliminates reasoning overhead (`0 tok`) and cuts Streaming TTFT by **88% (`10,430 ms` → `1,205 ms`)**.
2. **Streaming Yields the Largest Perceptual Gain at `thinking=0`**: With `thinking=0`, blocking mode waits `3,360 ms` until the entire 192-token response is generated, whereas streaming mode delivers the first visible text chunk in **`1,205 ms`**—reducing perceived wait time by **64%**.

---

## 3.2 2D Trajectory Comparison across All 6 Thinking Levels

To visualize how internal reasoning alters the temporal delivery profile of a streaming response, Figure 3-2 plots the 2D cumulative character trajectories (`elapsed time t_ms` vs. `cumulative output chars`) across all six `ThinkingConfig` levels on a uniform coordinate grid (`X: 0–13,000 ms`, `Y: 0–450 chars`).

```drawlib align=center code=fold width=100% file=ch03_thinking_trajectories_grid.png caption="Figure 3-2: 2D Streaming Trajectories (Elapsed Time vs. Cumulative Output Characters) across All 6 ThinkingConfig Levels on a Uniform Scale"
from drawlib.canvas import save, setup
from drawlib.icons import phosphor
from drawlib.lines import line
from drawlib.shapes import circle, rectangle
from drawlib.styles import Styles
from drawlib.text import text
from drawlib.utils import load_thinking_timeline

setup(width=168, height=106, dpi=150)

# Outer structural frame
rectangle((84.0, 53.0), width=164.0, height=102.0, style=Styles.MutedDashed.patch(shape_r=2.0))
text(
    (84.0, 99.6),
    "2D Streaming Trajectories across All 6 ThinkingConfig Levels (X: 0–13s / Y: 0–450 chars)",
    style=Styles.DarkBold.patch(text_size=12.0),
)

# Legend bar at top
rectangle((84.0, 93.2), width=156.0, height=5.2, style=Styles.Neutral.patch(shape_r=1.0))

rectangle((12.0, 93.2), width=4.2, height=2.2, style=Styles.SecondaryNeutral.patch(shape_r=0.3))
text((15.2, 93.2), "Internal Reasoning Wait (TTFT: 0 chars)", style=Styles.DarkBold.patch(text_size=10.0, halign="left"))

rectangle((72.0, 93.2), width=4.2, height=2.2, style=Styles.PrimaryNeutral.patch(shape_r=0.3))
text((75.2, 93.2), "Visible Streaming Burst", style=Styles.PrimaryBold.patch(text_size=10.0, halign="left"))

line((117.0, 93.2), (122.0, 93.2), style=Styles.PrimaryBold.patch(line_width=2.2))
circle((119.5, 93.2), radius=0.85, style=Styles.PrimaryFlat)
text((123.5, 93.2), "Gemini Chunk Trajectory", style=Styles.DarkBold.patch(text_size=10.0, halign="left"))


def _draw_panel(x0: float, y0: float, title_s: str, sub_s: str, ex: dict) -> None:
    pw, ph, max_t, max_c = 36.0, 21.5, 13000.0, 450.0
    rectangle((x0 + pw / 2, y0 + ph / 2 + 1.0), width=pw + 12.0, height=ph + 15.0, style=Styles.LightFlat.patch(shape_r=1.8))
    text((x0 + pw / 2, y0 + ph + 5.2), title_s, style=Styles.DarkBold.patch(text_size=10.5))
    text((x0 + pw / 2, y0 + ph + 1.9), sub_s, style=Styles.Dark.patch(text_size=10.0))
    rectangle((x0 + pw / 2, y0 + ph / 2), width=pw, height=ph, style=Styles.WhiteFlat)

    def px(t_ms: float) -> float:
        return x0 + min(max(t_ms, 0.0), max_t) / max_t * pw

    def py(c_val: float) -> float:
        return y0 + min(max(c_val, 0.0), max_c) / max_c * ph

    ot = ex.get("overall_timing", {})
    ttft_ms = float(ot.get("time_to_first_token_ms", 0.0))
    total_ms = float(ot.get("stream_completed_ms", 0.0))
    gx0, gx1, sx1 = px(0.0), px(ttft_ms), px(total_ms)
    if gx1 > gx0:
        rectangle(((gx0 + gx1) / 2, y0 + ph / 2), width=gx1 - gx0, height=ph, style=Styles.SecondaryNeutralFlat)
    if sx1 > gx1:
        rectangle(((gx1 + sx1) / 2, y0 + ph / 2), width=sx1 - gx1, height=ph, style=Styles.PrimaryNeutralFlat)

    for xt in (0, 3000, 6000, 9000, 12000):
        tx = px(float(xt))
        line((tx, y0), (tx, y0 + ph), style=Styles.LightDashed.patch(line_width=0.6))
        text((tx, y0 - 2.3), f"{xt // 1000}s" if xt > 0 else "0", style=Styles.Dark.patch(text_size=10.0))
    for yt in (0, 200, 400):
        ty = py(float(yt))
        line((x0, ty), (x0 + pw, ty), style=Styles.LightDashed.patch(line_width=0.6))
        text((x0 - 3.2, ty), f"{yt}", style=Styles.Dark.patch(text_size=10.0))

    line((x0, y0), (x0 + pw, y0), style=Styles.Dark.patch(line_width=1.0))
    line((x0, y0), (x0, y0 + ph), style=Styles.Dark.patch(line_width=1.0))

    gem_pts = ex.get("timeline_series", {}).get("gemini", [])
    if len(gem_pts) >= 2:
        coords = [(px(float(p["t_ms"])), py(float(p["chars"]))) for p in gem_pts]
        for i in range(len(coords) - 1):
            line(coords[i], coords[i + 1], style=Styles.PrimaryBold.patch(line_width=2.0))
        for cx, cy in coords:
            circle((cx, cy), radius=0.85, style=Styles.PrimaryFlat)


panel_specs = [
    ("0", 12.5, 55.0, "thinking = 0 (budget=0)", "ThTok: 0 / TTFT 1,205 / Total 3,192 ms"),
    ("minimal", 66.0, 55.0, "thinking = minimal", "ThTok: 0 / TTFT 3,324 / Total 5,676 ms"),
    ("low", 119.5, 55.0, "thinking = low", "ThTok: 351 / TTFT 5,520 / Total 6,777 ms"),
    ("medium", 12.5, 15.0, "thinking = medium", "ThTok: 441 / TTFT 6,215 / Total 7,682 ms"),
    ("high", 66.0, 15.0, "thinking = high", "ThTok: 870 / TTFT 9,703 / Total 11,529 ms"),
    ("default", 119.5, 15.0, "thinking = default", "ThTok: 1,006 / TTFT 10,430 / Total 12,006 ms"),
]

for t_key, x0, y0, title_s, sub_s in panel_specs:
    _draw_panel(x0, y0, title_s, sub_s, load_thinking_timeline("streaming", t_key))

# Bottom summary strip
rectangle((84.0, 4.8), width=156.0, height=5.2, style=Styles.PrimaryNeutral.patch(shape_r=1.0))
phosphor.chart_line_up((9.5, 4.8), width=3.0, style=Styles.PrimaryBold)
text(
    (13.0, 4.8),
    "Trajectory Invariant: Higher thinking levels only stretch the y=0 wait band; once reasoning ends, all burst ~360 chars in ~1.6s.",
    style=Styles.DarkBold.patch(text_size=10.0, halign="left"),
)

save()
```

### Key Structural Observations from the 2D Trajectories

1. **Only the Horizontal `y = 0` Wait Band Stretches; Visible Streaming Velocity Is Invariant**:
   - In **`thinking = 0`** (top-left panel), the purple pre-first-token wait band ends at **`1,205 ms`**, immediately transitioning into a steep blue streaming ramp that completes all 373 characters by `3.19 s`.
   - Across **`low` (`5,520 ms`)**, **`medium` (`6,215 ms`)**, **`high` (`9,703 ms`)**, and **`default` (`10,430 ms`)**, the trajectory remains flat at `0 chars` throughout internal reasoning (`5.5–10.4 s`). Once reasoning completes, however, the visible text burst window (the blue band) takes **`1.2–1.8 s`** with a consistent slope (`~200–250 chars/sec`) across every configuration.
2. **Proportional Wait-Band Scaling with Internal Reasoning Tokens**:
   - The width of the purple wait band scales directly with the number of internal reasoning tokens (`thoughts_tokens`) generated on each run (`low`: `351 tok`, `medium`: `441 tok`, `high`: `870 tok`, `default`: `1,006 tok`).

---

## 3.3 Linear Scaling Law of Reasoning Tokens (`TTFT ≈ 1,500 ms + 9.0 ms × ThTok`)

To isolate the mathematical relationship between internal reasoning volume and TTFT, Figure 3-3 plots **`thoughts_tokens` (X-axis)** against **`ttft_ms` (Y-axis)** across all 12 streaming executions in `load_thinking_benchmark_all()`, overlaid with the linear regression trendline.

```drawlib align=center code=fold width=100% file=ch03_reasoning_scaling_scatter.png caption="Figure 3-3: Linear Scaling Law of Internal Reasoning Tokens (thoughts_tokens) vs. Streaming TTFT (TTFT ≈ 1,500 ms + 9.0 ms × ThTok)"
from drawlib.canvas import save, setup
from drawlib.charts.scatter import ScatterChart
from drawlib.icons import phosphor
from drawlib.lines import line
from drawlib.shapes import rectangle
from drawlib.styles import Styles
from drawlib.text import text
from drawlib.utils import load_thinking_benchmark_all

setup(width=168, height=90, dpi=150)

# Outer structural frame
rectangle((84.0, 45.0), width=164.0, height=86.0, style=Styles.MutedDashed.patch(shape_r=2.0))
text(
    (84.0, 83.6),
    "Internal Reasoning Tokens (thoughts_tokens) vs. Streaming TTFT (ms): Linear Regression",
    style=Styles.DarkBold.patch(text_size=12.0),
)

series_points: dict[str, list[tuple[float, float]]] = {
    "0": [],
    "minimal": [],
    "low": [],
    "medium": [],
    "high": [],
    "default": [],
}

for r in load_thinking_benchmark_all():
    if not str(r["mode"]).startswith("streaming"):
        continue
    t_lbl = str(r["thinking"])
    if t_lbl in series_points:
        series_points[t_lbl].append((float(r["thoughts_tokens"]), float(r["ttft_ms"])))

# Left chart card
rectangle((60.5, 45.5), width=109.0, height=66.0, style=Styles.WhiteFlat.patch(shape_r=1.4, line_width=0.8))

# Clean 2-row custom legend box inside Left chart card
rectangle((60.5, 73.2), width=104.0, height=8.2, style=Styles.Neutral.patch(shape_r=1.0))
leg_r1 = [
    (12.0, Styles.SuccessFlat, "0 (budget=0)"),
    (43.0, Styles.TealFlat, "minimal"),
    (70.0, Styles.PrimaryFlat, "low"),
    (92.0, Styles.SecondaryFlat, "medium"),
]
for lx, st, ltxt in leg_r1:
    rectangle((lx, 75.0), width=3.0, height=1.7, style=st.patch(shape_r=0.3))
    text((lx + 2.2, 75.0), ltxt, style=Styles.DarkBold.patch(text_size=10.0, halign="left"))

leg_r2 = [
    (12.0, Styles.WarningFlat, "high"),
    (43.0, Styles.DangerFlat, "default (dynamic)"),
]
for lx, st, ltxt in leg_r2:
    rectangle((lx, 71.3), width=3.0, height=1.7, style=st.patch(shape_r=0.3))
    text((lx + 2.2, 71.3), ltxt, style=Styles.Dark.patch(text_size=10.0, halign="left"))

line((78.0, 71.3), (83.0, 71.3), style=Styles.PrimaryBold.patch(line_width=2.0))
text((84.2, 71.3), "Fit: 1500 + 9.0×ThTok", style=Styles.PrimaryBold.patch(text_size=10.0, halign="left"))

chart = ScatterChart(
    axis_line_style=Styles.Dark,
    axis_text_style=Styles.Dark.patch(text_size=10.0),
    grid_style=Styles.MutedDashed,
    width=99.0,
    height=49.0,
    default_radius=1.25,
)
chart.configure_x_axis(
    label="Internal Reasoning Tokens (thoughts_tokens [tokens])",
    min_value=0,
    max_value=1200,
    tick_step=200,
    format="{:,.0f}",
)
chart.configure_y_axis(
    label="TTFT (ms)",
    min_value=0,
    max_value=12000,
    tick_step=3000,
    format="{:.0f}",
)

chart.add_series(name="0", data=series_points["0"], style=Styles.SuccessFlat, radius=1.3, shape="circle")
chart.add_series(name="minimal", data=series_points["minimal"], style=Styles.TealFlat, radius=1.15, shape="rhombus")
chart.add_series(name="low", data=series_points["low"], style=Styles.PrimaryFlat, radius=1.25, shape="circle")
chart.add_series(name="medium", data=series_points["medium"], style=Styles.SecondaryFlat, radius=1.25, shape="square")
chart.add_series(name="high", data=series_points["high"], style=Styles.WarningFlat, radius=1.3, shape="triangle")
chart.add_series(name="default", data=series_points["default"], style=Styles.DangerFlat, radius=1.25, shape="rhombus")

chart.draw(xy=(9.0, 16.0))

# Linear regression line across the plot area
x_start, y_start = 24.6, 26.8 + (1500.0 / 12000.0) * 35.5
x_end, y_end = 104.2, 26.8 + (11500.0 / 12000.0) * 35.5
line((x_start, y_start), (x_end, y_end), style=Styles.PrimaryBold.patch(line_width=1.8))

# Right-side Neutral statistical insight panel
rectangle((140.0, 45.5), width=43.0, height=66.0, style=Styles.PrimaryNeutral.patch(shape_r=1.5))
text((140.0, 74.0), "Scaling Law Insights", style=Styles.PrimaryBold.patch(text_size=11.0))

stat_cards = [
    (63.0, "1. Linear Regression Formula", "TTFT ≈ 1,500 ms + 9.0 ms × ThTok\nEach +100 tok adds +0.90 s to TTFT"),
    (49.6, "2. Internal Reasoning Speed", "1 / 9.0 ms ≈ ~110 tokens/sec\nMatches visible autoregressive speed"),
    (36.2, "3. 0 / minimal Convergence", "Locked at 0 tok on the Y-intercept\nEliminates multi-second wait"),
    (22.8, "4. default / high Variance", "Spans 467–1,006 tok across runs\nInflating TTFT to 7.5–10.4 s"),
]
for cy, s_title, s_desc in stat_cards:
    rectangle((140.0, cy), width=39.4, height=11.0, style=Styles.WhiteFlat.patch(shape_r=1.0))
    text((140.0, cy + 2.5), s_title, style=Styles.DarkBold.patch(text_size=10.0))
    text((140.0, cy - 1.8), s_desc, style=Styles.Dark.patch(text_size=10.0))

# Bottom callout banner
rectangle((84.0, 5.8), width=156.0, height=6.0, style=Styles.SecondaryNeutral.patch(shape_r=1.2))
phosphor.function((9.5, 5.8), width=3.0, style=Styles.SecondaryBold)
text(
    (13.0, 5.8),
    "Conclusion: Streaming TTFT follows ~1,500 ms base prefill + ~9.0 ms per reasoning token (~110 tok/s), explaining run-to-run variance.",
    style=Styles.DarkBold.patch(text_size=10.0, halign="left"),
)

save()
```

### Three Empirical Laws from the Regression Analysis

1. **Strict Linear Scaling (`TTFT ≈ 1,500 ms + 9.0 ms × ThTok`)**:
   - Every streaming execution aligns along a linear trajectory with an intercept of **`~1,500 ms`** (network RTT + prompt prefill + first token generation) and a slope of **`~9.0 ms / token`**.
   - Taking the reciprocal of `9.0 ms / token` shows that `gemini-3.8-flash` generates internal reasoning tokens at **`~110 tokens/sec`**.
2. **Why `default`, `medium`, and `high` Vary Across Runs**:
   - Because `LOW`, `MEDIUM`, `HIGH`, and `default` act as soft complexity priors rather than rigid token caps, the actual `thoughts_tokens` sampled on a given call varies dynamically (`351–1,006 tokens`).
3. **Deterministic Low Latency Requires `thinking=0`**:
   - Only `thinking=0` clamps `thoughts_tokens` at `0 tok`, eliminating multi-second reasoning overhead and locking TTFT into **`1.2–1.5 s`**.

---

## 3.4 Query Complexity Tiers (Tier 1–3) & The Speed-vs-Accuracy Dilemma

If `thinking=0` delivers `~1.2–1.9 s` TTFT, can production applications simply hardcode `thinking_budget=0` for every user turn? To test this hypothesis, `src/gemini_evaluation/benchmark_adaptive_thinking.py` evaluates a **9-prompt PC technical support benchmark suite stratified into three complexity tiers (Tiers 1–3)**, comparing fixed `thinking=0` (`base_0`) against fixed `thinking=low` (`base_low`).

| Complexity Tier | Prompt IDs & Titles | Query Characteristics | Expected `thinking` | Fixed `thinking=0` (`base_0`)<br>`TTFT / Total` | Fixed `thinking=low` (`base_low`)<br>`TTFT / Total (ThTok)` |
| :--- | :--- | :--- | :---: | ---: | ---: |
| **Tier 1: Greetings & Short Queries** | `T1_1` Initial PC Boot Greeting<br>`T1_2` Thanks / Follow-up<br>`T1_3` Support Hours | Conversational turns requiring no arithmetic or multi-condition logic (3 prompts) | `False` (`0`) | Mean **`1,720 ms`** / `3,774 ms` | Mean `3,581 ms` / `5,153 ms`<br>(Unneeded `81–152 tok`) |
| **Tier 2: Standard Procedures** | `T2_1` Power Discharge Reset<br>`T2_2` Pre-Repair Checklist<br>`T2_3` Liquid Spill Emergency | Step-by-step troubleshooting guides and checklists (3 prompts) | `False` (`0`) | Mean **`2,053 ms`** / `6,967 ms` | Mean `6,000 ms` / `11,226 ms`<br>(Unneeded `304–423 tok`) |
| **Tier 3: Multi-Step Support Math** | `T3_1` 3-Year PC Repair vs. Buy<br>`T3_2` 500GB SSD Transfer Time<br>`T3_3` 2-Year 3-PC Maintenance | Multi-step cost comparisons, transfer rate equations, multi-year contracts (3 prompts) | `True` (`low`) | Mean **`1,863 ms`** / `8,452 ms`<br>**[Unverified Conclusion-First Risk]** | Mean `9,289 ms` / `16,580 ms`<br>(Reasoning `673–827 tok`)<br>**[Scratchpad-Verified 3/3]** |

### The Fundamental Dilemma of Fixed `ThinkingConfig`

As the benchmark matrix demonstrates, any fixed `ThinkingConfig` forces an unacceptable compromise:
- **Fixed `thinking=low` Penalizes Routine Turns and Freezes on Complex Turns**: While `base_low` pre-verifies all Tier 3 multi-step calculations using `673–827` reasoning tokens, it wastes `81–423` reasoning tokens on Tier 1 greetings and Tier 2 procedures—adding a **`1.8s–4.0s` wait** where no reasoning is needed (`6,290 ms` overall mean TTFT). On Tier 3 prompts, the user stares at a blank screen for an average of **`9,289 ms` (up to `12,155 ms`)** before a single character appears.
- **Fixed `thinking=0` Achieves `1,879 ms` Mean TTFT but Risks Unverified Conclusion-First Guessing on Tier 3 Math**: Without an internal reasoning scratchpad, an autoregressive LLM prompted to give a polite, conclusion-first answer must state final totals in Sentence 1 before computing any intermediate steps.

Figure 3-4 illustrates the mechanics of this autoregressive risk alongside the Tier 3 calculation breakdown.

```drawlib align=center code=fold width=100% file=ch03_speed_vs_accuracy_dilemma.png caption="Figure 3-4: Conclusion-First Guessing Risk in Fixed thinking=0 vs. Scratchpad Pre-Verification in thinking=low across Tier 3 PC Support Calculations"
from drawlib.canvas import save, setup
from drawlib.icons import phosphor
from drawlib.lines import line
from drawlib.shapes import rectangle
from drawlib.styles import Styles
from drawlib.text import text

setup(width=168, height=96, dpi=150)

# Outer structural frame
rectangle((84.0, 48.0), width=164.0, height=92.0, style=Styles.MutedDashed.patch(shape_r=2.0))
text(
    (84.0, 89.6),
    "Why Fixed thinking=0 Is Risky on Multi-Step Math: Conclusion-First Guessing vs. Scratchpad",
    style=Styles.DarkBold.patch(text_size=12.0),
)

# ─── Top Half: Mechanism Comparison (Left: thinking=0 Trap, Right: thinking=low Scratchpad) ───
# Left Container: thinking=0
rectangle((44.5, 65.5), width=76.0, height=38.0, style=Styles.Neutral.patch(shape_r=1.5))
phosphor.warning_circle((10.0, 80.5), width=3.2, style=Styles.DangerBold)
text((13.5, 80.5), "Fixed thinking=0: Conclusion-First Risk (0 Scratchpad)", style=Styles.DangerBold.patch(text_size=10.5, halign="left"))

rectangle((44.5, 71.0), width=71.0, height=9.2, style=Styles.WhiteFlat.patch(shape_r=1.0))
text((44.5, 73.2), "Step 1: Conclusion-First Guessing (0 Scratchpad Tokens)", style=Styles.DangerBold.patch(text_size=10.0))
text((44.5, 68.8), "Must state final totals in Sentence 1 before intermediate math", style=Styles.Dark.patch(text_size=10.0))

line((44.5, 66.4), (44.5, 62.6), arrow_head="->", style=Styles.DangerBold.patch(line_width=1.8))

rectangle((44.5, 55.5), width=71.0, height=11.0, style=Styles.WhiteFlat.patch(shape_r=1.0))
text((44.5, 58.4), "Step 2: Risk of Arithmetic Fudging & Self-Contradiction", style=Styles.DangerBold.patch(text_size=10.0))
text((44.5, 54.4), "As multi-year discounts and tiered rates compound, opening", style=Styles.Dark.patch(text_size=10.0))
text((44.5, 51.2), "headlines risk contradicting the step-by-step breakdown!", style=Styles.Dark.patch(text_size=10.0))

# Right Container: thinking=low
rectangle((123.5, 65.5), width=76.0, height=38.0, style=Styles.PrimaryNeutral.patch(shape_r=1.5))
phosphor.check_circle((89.0, 80.5), width=3.2, style=Styles.PrimaryBold)
text((92.5, 80.5), "thinking=low: Scratchpad Verification (3/3 Verified)", style=Styles.PrimaryBold.patch(text_size=10.5, halign="left"))

rectangle((123.5, 71.0), width=71.0, height=9.2, style=Styles.WhiteFlat.patch(shape_r=1.0))
text((123.5, 73.2), "Step 1: Internal Scratchpad Pre-Computation (673–827 tok)", style=Styles.PrimaryBold.patch(text_size=10.0))
text((123.5, 68.8), "Solves all multi-year & transfer equations before visible text", style=Styles.Dark.patch(text_size=10.0))

line((123.5, 66.4), (123.5, 62.6), arrow_head="->", style=Styles.PrimaryBold.patch(line_width=1.8))

rectangle((123.5, 55.5), width=71.0, height=11.0, style=Styles.WhiteFlat.patch(shape_r=1.0))
text((123.5, 58.4), "Step 2: Coherent, Verified Output from Sentence 1", style=Styles.SuccessBold.patch(text_size=10.0))
text((123.5, 54.4), "States verified totals ('26,200 yen', '205 min', '93,600 yen')", style=Styles.Dark.patch(text_size=10.0))
text((123.5, 51.2), "with 100% table consistency (at the cost of 6.7–12.2s TTFT)", style=Styles.Dark.patch(text_size=10.0))

# ─── Bottom Half: Tier 3 Empirical Breakdown Table ───
rectangle((84.0, 41.2), width=155.0, height=4.8, style=Styles.PrimaryFlat.patch(shape_r=0.8))
text((20.0, 41.2), "Tier 3 Prompt", style=Styles.WhiteBold.patch(text_size=10.0))
text((51.5, 41.2), "True Math Answer", style=Styles.WhiteBold.patch(text_size=10.0))
text((99.0, 41.2), "Required Multi-Step Calculation", style=Styles.WhiteBold.patch(text_size=10.0))
text((146.5, 41.2), "thinking=low Result", style=Styles.WhiteBold.patch(text_size=10.0))

t3_rows = [
    (
        33.4,
        "T3_1: Repair vs. Buy",
        "Repair: 75,600 / New: 101,800\nDiff: 26,200 yen cheaper",
        "Repair (board 29,800 + SSD 9,800 + plan 1,000×36) vs.\nNew (124,800 - trade 15,000 - rebate 18,000 + care 10,000)",
        "26,200 yen (Verified)\n(790–951 tok)",
    ),
    (
        23.8,
        "T3_2: 500GB Transfer",
        "USB2.0: 240m / Gen2: 35m\nSaved: 205 min (3h 25m)",
        "Divide 300GB video & 200GB small files by interface speeds\n(floor per item) and add verification times (15m vs 5m)",
        "205 min (Verified)\n(673–755 tok)",
    ),
    (
        14.2,
        "T3_3: 3-PC 2-Yr Plan",
        "50,400 + 29,400 + 13,800\nTotal: 93,600 yen",
        "3 PCs × 24m plan + 2 on-site visits (-6,600) + 3 RAM\nupgrades (-1,800) + Year-1 & Year-2 cloud backup fees",
        "93,600 yen (Verified)\n(674–827 tok)",
    ),
]

for ry, col1, col2, col3, col4 in t3_rows:
    rectangle((84.0, ry), width=155.0, height=8.6, style=Styles.LightFlat.patch(shape_r=0.8))
    rectangle((99.0, ry), width=64.0, height=7.8, style=Styles.WhiteFlat.patch(shape_r=0.6))
    text((20.0, ry), col1, style=Styles.DarkBold.patch(text_size=10.0))
    text((51.5, ry), col2, style=Styles.Dark.patch(text_size=10.0))
    text((99.0, ry), col3, style=Styles.Dark.patch(text_size=10.0))
    text((146.5, ry), col4, style=Styles.SuccessBold.patch(text_size=10.0))

# Bottom takeaway bar
rectangle((84.0, 5.2), width=155.0, height=5.4, style=Styles.SecondaryNeutral.patch(shape_r=1.0))
phosphor.arrows_split((9.5, 5.2), width=3.0, style=Styles.SecondaryBold)
text(
    (13.0, 5.2),
    "Next Step: Chapter 4 introduces an Adaptive Router that keeps thinking=0 on Tiers 1–2 and chains thinking=low on Tier 3.",
    style=Styles.DarkBold.patch(text_size=10.0, halign="left"),
)

save()
```

### Breakdown of the Three Tier 3 PC Support Calculations

Inspecting the benchmark prompts in `src/gemini_evaluation/benchmark_adaptive_thinking.py` highlights why multi-step calculations benefit from `thinking=low` scratchpad verification:

1. **`T3_1` (3-Year PC Repair vs. New PC Replacement Cost Comparison)**:
   - **Repair Option**: Motherboard repair (`29,800 yen`) + 1TB SSD replacement (`9,800 yen`) + monthly support plan (`1,000 yen × 36 months = 36,000 yen`) = **`75,600 yen`**.
   - **Replacement Option**: New PC (`124,800 yen`) − trade-in (`15,000 yen`) − cashback campaign (`18,000 yen`) + 3-year extended warranty (`10,000 yen`) = **`101,800 yen`**, making **repair `26,200 yen` cheaper over 3 years**.
2. **`T3_2` (500GB SSD Backup Transfer Time Comparison)**:
   - **USB 2.0 External HDD**: 300GB video (`300,000 MB ÷ 40 MB/s = 7,500 s = 125 min`) + 200GB small files (`192,000 MB ÷ 32 MB/s = 6,000 s = 100 min`) + verification (`15 min`) = **`240 min` (4 hours)**.
   - **USB 3.2 Gen2 External SSD** (floor-rounded per item as specified in the prompt): 300GB video (`300,000 MB ÷ 400 MB/s = 750 s = 12.5 → 12 min`) + 200GB small files (`199,800 MB ÷ 180 MB/s = 1,110 s = 18.5 → 18 min`) + verification (`5 min`) = **`35 min`**, saving **`205 min` (3 hours 25 minutes)**.
3. **`T3_3` (2-Year 3-PC Maintenance, RAM Upgrade, and Cloud Backup Cost Simulation)**:
   - **Maintenance & On-Site Repair**: `600 yen × 3 PCs × 24 months = 43,200 yen` + 2 on-site repairs (standard `6,900 yen × 2 = 13,800 yen` − maintenance spot discount `6,600 yen` = `3,600 yen × 2 = 7,200 yen`) = `50,400 yen`.
   - **16GB RAM Upgrades (3 PCs)**: Standard `10,400 yen × 3 = 31,200 yen` − simultaneous 3-PC discount `1,800 yen` = `9,800 yen × 3 = 29,400 yen`.
   - **Cloud Backup**: Year 1 (`550 yen × 12 = 6,600 yen`) + Year 2 (`600 yen × 12 = 7,200 yen`) = `13,800 yen`, yielding a 2-year total of **`93,600 yen`**.

In Chapter 4, we design and benchmark the **Adaptive Thinking Router Pattern** to combine fast `thinking=0` responsiveness on Tiers 1–2 with parallel `thinking=low` scratchpad verification on Tier 3.

---

## 3.5 Cross-Model × `thinking_level` (Plus Deprecated `thinking_budget=0`) Latency Comparison across All 5 Active Models (5 Simple + 5 Complex Queries = 220 Runs)

Sections 3.1 through 3.4 analyzed `ThinkingConfig` behavior on `gemini-3.8-flash`. In production architecture design, however, engineers must choose among the **five active Gemini 3.5 / 3.8 / 4 models** introduced in Section 2.5 (`gemini-3.5-flash-lite`, `gemini-3.8-flash`, `gemini-4-hydrogen`, `gemini-4-argon`, and `gemini-4-carbon`) and understand how each model's supported `thinking_level` options—as well as the deprecated legacy `thinking_budget=0` setting—scale across both **Simple conversational queries** and **Complex multi-step calculations**.

To provide a direct apples-to-apples comparison, we created `src/gemini_evaluation/benchmark_cross_model_thinking.py` and executed **220 live streaming API calls (`generate_content_stream`)** sending the exact same **5 Simple queries (`S1`–`S5`)** and **5 Complex queries (`C1`–`C5`)** across all **22 `(model, thinking_level / budget=0)` configurations** (`src/gemini_evaluation/cross_model_thinking_log.yaml` / `.json`).

```drawlib align=center code=fold width=100% file=ch03_cross_model_thinking_comparison.png caption="Figure 3-5: Cross-Model × thinking_level + Deprecated thinking_budget=0 (22 Configurations) Streaming TTFT, Total Completion Time, and Reasoning Token Comparison across 5 Simple Queries (S1–S5) vs. 5 Complex Queries (C1–C5) (220 Total Runs)"
from drawlib.canvas import save, setup
from drawlib.icons import phosphor
from drawlib.lines import line
from drawlib.shapes import rectangle
from drawlib.styles import Styles
from drawlib.text import text
from drawlib.utils import load_cross_model_thinking_benchmark

setup(width=172, height=158, dpi=150)

# Outer structural frame
rectangle((86.0, 79.0), width=168.0, height=154.0, style=Styles.MutedDashed.patch(shape_r=2.0))
text(
    (86.0, 151.6),
    "5 Active Models × All thinking_level Options + Deprecated budget=0 (22 Configs): Simple vs. Complex",
    style=Styles.DarkBold.patch(text_size=11.2),
)

# Top Legend Bar
rectangle((86.0, 145.2), width=160.0, height=5.2, style=Styles.Neutral.patch(shape_r=1.0))
rectangle((9.5, 145.2), width=4.0, height=2.2, style=Styles.PrimaryFlat.patch(shape_r=0.3))
text((12.5, 145.2), "Streaming TTFT (First Token)", style=Styles.PrimaryBold.patch(text_size=9.8, halign="left"))

rectangle((53.5, 145.2), width=4.0, height=2.2, style=Styles.PrimaryNeutral.patch(shape_r=0.3))
text((56.5, 145.2), "Streaming Total (Completion)", style=Styles.DarkBold.patch(text_size=9.8, halign="left"))

rectangle((98.5, 145.2), width=4.0, height=2.2, style=Styles.SecondaryFlat.patch(shape_r=0.3))
text((101.5, 145.2), "[budget=0*] Deprecated thinking_budget=0", style=Styles.DarkBold.patch(text_size=9.8, halign="left"))

# Column Headers
rectangle((24.0, 138.8), width=36.0, height=4.4, style=Styles.PrimaryNeutral.patch(shape_r=0.8))
text((24.0, 138.8), "Model / Config (22 Configs)", style=Styles.DarkBold.patch(text_size=10.0))

rectangle((68.5, 138.8), width=49.0, height=4.4, style=Styles.PrimaryNeutral.patch(shape_r=0.8))
text((68.5, 138.8), "1. Simple 5-Query Avg (S1-S5) [0–30s]", style=Styles.DarkBold.patch(text_size=10.0))

rectangle((121.5, 138.8), width=53.0, height=4.4, style=Styles.PrimaryNeutral.patch(shape_r=0.8))
text((121.5, 138.8), "2. Complex 5-Query Avg (C1-C5) [0–42s]", style=Styles.DarkBold.patch(text_size=10.0))

rectangle((157.5, 138.8), width=16.0, height=4.4, style=Styles.SecondaryNeutral.patch(shape_r=0.8))
text((157.5, 138.8), "Avg ThTok", style=Styles.DarkBold.patch(text_size=10.0))

data = load_cross_model_thinking_benchmark()
agg = data["aggregated"]

SX0 = 45.0
SW = 32.0
S_MAX = 30000.0

CX0 = 96.0
CW = 36.0
C_MAX = 42000.0

for ms in (0, 10000, 20000, 30000):
    gx = SX0 + (ms / S_MAX) * SW
    line((gx, 13.5), (gx, 136.2), style=Styles.LightDashed.patch(line_width=0.6))
    text((gx, 11.2), f"{ms // 1000}s", style=Styles.Dark.patch(text_size=9.5))

for ms in (0, 10000, 20000, 30000, 40000):
    gx = CX0 + (ms / C_MAX) * CW
    line((gx, 13.5), (gx, 136.2), style=Styles.LightDashed.patch(line_width=0.6))
    text((gx, 11.2), f"{ms // 1000}s", style=Styles.Dark.patch(text_size=9.5))

short_names = {
    "gemini-3.5-flash-lite": "3.5-flash-lite",
    "gemini-3.8-flash": "3.8-flash",
    "gemini-4-hydrogen": "4-hydrogen",
    "gemini-4-argon": "4-argon",
    "gemini-4-carbon": "4-carbon",
}

for idx, row in enumerate(agg):
    ry = 133.5 - idx * 5.6
    m_short = short_names.get(row["model"], row["model"])
    lvl = row["thinking_level"]
    status = row.get("status", "OK")
    is_budget0 = lvl == "budget=0"
    is_lite_or_fast = row["model"] in {"gemini-3.5-flash-lite", "gemini-4-hydrogen"} and lvl in {"minimal", "low"}

    if status == "UNSUPPORTED_400":
        bg_st = Styles.DangerFlat.patch(shape_r=0.6, alpha=0.14)
    elif is_budget0:
        bg_st = Styles.SecondaryNeutral.patch(shape_r=0.6, alpha=0.38)
    elif is_lite_or_fast:
        bg_st = Styles.PrimaryNeutral.patch(shape_r=0.6, alpha=0.32)
    else:
        bg_st = Styles.LightFlat.patch(shape_r=0.6, alpha=0.45) if idx % 2 == 0 else Styles.WhiteFlat.patch(shape_r=0.6)

    rectangle((86.0, ry), width=160.0, height=5.0, style=bg_st)

    lbl_text = f"{m_short} [budget=0*]" if is_budget0 else f"{m_short} [{lvl}]"
    lbl_style = Styles.DangerBold.patch(text_size=9.5, halign="left") if status == "UNSUPPORTED_400" else Styles.DarkBold.patch(text_size=9.5, halign="left")
    text((7.2, ry), lbl_text, style=lbl_style)

    if status == "UNSUPPORTED_400":
        rectangle((96.0, ry), width=102.0, height=3.6, style=Styles.WhiteFlat.patch(shape_r=0.5, line_width=0.6))
        phosphor.x_circle((55.0, ry), width=2.8, style=Styles.DangerBold)
        text(
            (57.4, ry),
            "400 INVALID_ARGUMENT (thinking_budget=0 unsupported → use minimal)",
            style=Styles.DangerBold.patch(text_size=9.5, halign="left"),
        )
        rectangle((157.5, ry), width=15.0, height=3.8, style=Styles.WhiteFlat.patch(shape_r=0.5))
        text((157.5, ry), "N/A", style=Styles.DangerBold.patch(text_size=9.5))
        continue

    bar_tot_st = Styles.SecondaryNeutral.patch(shape_r=0.3) if is_budget0 else Styles.PrimaryNeutral.patch(shape_r=0.3)
    bar_ttft_st = Styles.SecondaryFlat.patch(shape_r=0.3) if is_budget0 else Styles.PrimaryFlat.patch(shape_r=0.3)

    # Simple bar
    s_ttft = float(row["simple_ttft_avg_ms"])
    s_tot = float(row["simple_total_avg_ms"])
    sw_tot = min(s_tot / S_MAX, 1.0) * SW
    sw_ttft = min(s_ttft / S_MAX, 1.0) * SW
    rectangle((SX0 + sw_tot / 2, ry), width=max(sw_tot, 0.4), height=2.4, style=bar_tot_st)
    rectangle((SX0 + sw_ttft / 2, ry), width=max(sw_ttft, 0.4), height=2.4, style=bar_ttft_st)
    text(
        (SX0 + sw_tot + 0.8, ry),
        f"{s_ttft / 1000:.1f}s / {s_tot / 1000:.1f}s",
        style=Styles.Dark.patch(text_size=9.5, halign="left"),
    )

    # Complex bar
    c_ttft = float(row["complex_ttft_avg_ms"])
    c_tot = float(row["complex_total_avg_ms"])
    c_th = float(row["complex_thoughts_avg"])
    cw_tot = min(c_tot / C_MAX, 1.0) * CW
    cw_ttft = min(c_ttft / C_MAX, 1.0) * CW
    rectangle((CX0 + cw_tot / 2, ry), width=max(cw_tot, 0.4), height=2.4, style=bar_tot_st)
    rectangle((CX0 + cw_ttft / 2, ry), width=max(cw_ttft, 0.4), height=2.4, style=bar_ttft_st)
    text(
        (CX0 + cw_tot + 0.8, ry),
        f"{c_ttft / 1000:.1f}s / {c_tot / 1000:.1f}s",
        style=Styles.DarkBold.patch(text_size=9.5, halign="left"),
    )

    # Complex thoughts token pill
    rectangle((157.5, ry), width=15.0, height=3.8, style=Styles.WhiteFlat.patch(shape_r=0.5))
    text((157.5, ry), f"{c_th:,.0f} tok", style=Styles.PrimaryBold.patch(text_size=9.5))

# Bottom callout banner
rectangle((86.0, 5.2), width=160.0, height=5.4, style=Styles.PrimaryNeutral.patch(shape_r=1.0))
phosphor.gauge((9.8, 5.2), width=3.0, style=Styles.PrimaryBold)
text(
    (13.2, 5.2),
    "Takeaway: budget=0* fails with HTTP 400 on 3.5-flash-lite and coerces to low on the other 4 models; always specify thinking_level.",
    style=Styles.DarkBold.patch(text_size=9.8, halign="left"),
)

save()
```

---

### 1. Benchmark Suite: 5 Simple Queries (`S1`–`S5`) + 5 Complex Queries (`C1`–`C5`) (Table 3-5A)

Every model and `thinking_level` (as well as deprecated `thinking_budget=0`) configuration was evaluated on the exact same 10 PC technical support queries shown in Table 3-5A.

| Query ID | Category | Query Title | Prompt Summary & Processing Requirements |
| :---: | :---: | :--- | :--- |
| **`S1`** | **Simple** | Initial PC Boot Greeting | Initial intake response to a customer reporting that their laptop suddenly stopped turning on. |
| **`S2`** | **Simple** | Power Reset Thanks / Closing | Polite closing response after the customer confirms that power discharge restored the power LED. |
| **`S3`** | **Simple** | Support Center Hours | Standard guidance on phone vs. chat support operating hours and business days. |
| **`S4`** | **Simple** | Forced Shutdown Hold Time | Short factual answer on how many seconds (`~4–10s`) to hold the power button when Windows freezes. |
| **`S5`** | **Simple** | Model & Serial Number Location | Guidance on where to find the model number and serial sticker on a laptop (bottom cover, battery bay, BIOS). |
| **`C1`** | **Complex** | 3-Year Repair vs. Replacement Cost | Repair plan (board `38,000` + SSD `22,000` + power `2,400×36` + Year-2 battery `16,000` = `162,400 yen`) vs. Replacement plan (new PC `168,000` − trade-in `25,000` − 10% points `14,300` + power `1,550×36` = `184,500 yen`; repair saves **`22,100 yen`**). |
| **`C2`** | **Complex** | 1.8TB Local + Cloud Transfer Time | 1,200GB video at `300 MB/s` (`4,000s`) + 600GB small CAD files at `50 MB/s` (`12,000s`) local backup (`266m 40s`) + 360GB cloud upload at `40 MB/s` (`9,000s` = `150m`), totaling **`6 hours 56 minutes 40 seconds`**. |
| **`C3`** | **Complex** | Loaner Rental vs. Same-Day On-Site | 8-day depot repair (`32,000` + 2-day downtime `36,000` + 6-day rental `21,000` + setup `4,000` = `93,000 yen`) vs. Same-day on-site repair (`32,000` + dispatch `22,000` + rush `12,000` + half-day downtime `9,000` = `75,000 yen`; on-site saves **`18,000 yen`**). |
| **`C4`** | **Complex** | 3-PC 2-Year Maintenance & Upgrade | 3 PCs × 24m base plan (`43,200 yen`) + 2 discounted on-site repairs (`7,200 yen`) + 3 discounted 16GB RAM upgrades (`29,400 yen`) + Year-1 & Year-2 cloud backup (`13,800 yen`) = **`93,600 yen`**. |
| **`C5`** | **Complex** | 4-Drive RAID5 12TB Rebuild Time | 4×4TB RAID5 (`12TB` usable × 75% used = **`9.0TB` stored**); rebuilding `12,000,000 MB` takes 5 daytime hours at `100 MB/s` (`1,800,000 MB`) + `10,200,000 MB` at night (`250 MB/s` = `40,800s` = `11h 20m`) = **`16 hours 20 minutes`**. |

---

### 2. Aggregated Latency & Token Summary across All 22 Configurations (Table 3-5B)

Table 3-5B summarizes the **Simple 5-query averages (`S1`–`S5`)**, **Complex 5-query averages (`C1`–`C5`)**, and **Overall 10-query averages** across all 22 `(model, thinking_level / budget=0)` configurations.

| Model (`model`) | Config (`thinking_level` / `budget=0`) | Simple (`S1`–`S5`) Avg TTFT | Simple (`S1`–`S5`) Avg Total | Simple Avg `ThTok` / `OutTok` | Complex (`C1`–`C5`) Avg TTFT | Complex (`C1`–`C5`) Avg Total | Complex Avg `ThTok` / `OutTok` | Overall 10-Query Avg TTFT / Total |
| :--- | :---: | ---: | ---: | :---: | ---: | ---: | :---: | ---: |
| **`gemini-3.5-flash-lite`** | **`budget=0`** *(deprecated/error)* | ❌ `400 Error` | ❌ `400 Error` | Unsupported (use `minimal`) | ❌ `400 Error` | ❌ `400 Error` | Unsupported (use `minimal`) | **❌ `400 INVALID_ARGUMENT`** |
| **`gemini-3.5-flash-lite`** | **`minimal`** *(default)* | **`733.9 ms`** | **`1,378.9 ms`** | `0.0` / `188.6` | **`677.6 ms`** | **`2,063.2 ms`** | `0.0` / `588.8` | **`705.8 ms` / `1,721.0 ms`** |
| **`gemini-3.5-flash-lite`** | **`low`** | **`671.6 ms`** | **`1,373.5 ms`** | `0.0` / `203.4` | **`1,467.2 ms`** | **`2,815.4 ms`** | `336.4` / `558.2` | **`1,069.4 ms` / `2,094.5 ms`** |
| **`gemini-3.5-flash-lite`** | **`medium`** | `1,399.9 ms` | `1,933.5 ms` | `232.2` / `174.0` | `2,719.0 ms` | `4,078.8 ms` | `884.4` / `581.0` | `2,059.5 ms` / `3,006.2 ms` |
| **`gemini-3.5-flash-lite`** | **`high`** | `2,158.7 ms` | `2,568.6 ms` | `459.4` / `169.6` | `3,493.9 ms` | `4,837.8 ms` | `1,313.0` / `591.8` | `2,826.3 ms` / `3,703.2 ms` |
| **`gemini-3.8-flash`** | **`budget=0`** *(deprecated/legacy)* | `3,041.6 ms` | `5,457.5 ms` | `100.0` / `213.0` | `2,564.7 ms` | `7,653.2 ms` | `91.8` / `627.8` | `2,803.2 ms` / `6,555.4 ms` |
| **`gemini-3.8-flash`** | **`low`** | `2,458.7 ms` | `5,041.8 ms` | `62.0` / `238.0` | `2,586.6 ms` | `7,965.4 ms` | `104.6` / `653.4` | `2,522.7 ms` / `6,503.6 ms` |
| **`gemini-3.8-flash`** | **`medium`** *(default)* | `3,950.6 ms` | `6,655.5 ms` | `206.8` / `252.0` | `6,155.5 ms` | `10,707.2 ms` | `605.0` / `567.2` | `5,053.1 ms` / `8,681.4 ms` |
| **`gemini-3.8-flash`** | **`high`** | `10,186.7 ms` | `12,502.7 ms` | `799.6` / `243.4` | `13,429.9 ms` | `18,948.5 ms` | `1,549.0` / `693.4` | `11,808.3 ms` / `15,725.6 ms` |
| **`gemini-4-hydrogen`** | **`budget=0`** *(deprecated/coerced)* | `3,018.6 ms` | `3,870.3 ms` | `147.4` / `146.0` | `5,341.2 ms` | `7,474.6 ms` | `670.4` / `508.6` | `4,179.9 ms` / `5,672.5 ms` |
| **`gemini-4-hydrogen`** | **`low`** | `2,598.0 ms` | **`3,367.6 ms`** | `183.8` / `146.0` | `3,908.6 ms` | **`5,899.8 ms`** | `657.6` / `521.6` | **`3,253.3 ms` / `4,633.7 ms`** |
| **`gemini-4-hydrogen`** | **`medium`** | `3,762.3 ms` | `5,150.8 ms` | `231.6` / `218.4` | `6,506.2 ms` | `9,004.7 ms` | `954.2` / `593.2` | `5,134.2 ms` / `7,077.7 ms` |
| **`gemini-4-hydrogen`** | **`high`** *(default)* | `4,060.9 ms` | `5,244.0 ms` | `273.0` / `205.6` | `9,339.2 ms` | `11,804.2 ms` | `1,156.0` / `593.8` | `6,700.1 ms` / `8,524.1 ms` |
| **`gemini-4-hydrogen`** | **`xhigh`** *(exclusive)* | `7,650.8 ms` | `8,738.9 ms` | `761.6` / `221.2` | `13,015.8 ms` | `15,431.1 ms` | **`2,248.0`** / `632.8` | `10,333.3 ms` / `12,085.0 ms` |
| **`gemini-4-argon`** | **`budget=0`** *(deprecated/legacy)* | `9,817.2 ms` | `13,952.0 ms` | `0.0` / `222.2` | `13,300.9 ms` | `21,158.1 ms` | `0.0` / `715.8` | `11,559.1 ms` / `17,555.0 ms` |
| **`gemini-4-argon`** | **`low`** | `4,382.4 ms` | `8,649.0 ms` | `0.0` / `250.4` | `10,940.2 ms` | `19,397.1 ms` | `0.0` / `698.4` | `7,661.3 ms` / `14,023.0 ms` |
| **`gemini-4-argon`** | **`medium`** *(default)* | `6,137.7 ms` | `10,080.2 ms` | `0.0` / `231.8` | **`4,931.3 ms`** | **`13,279.8 ms`** | `0.0` / `699.6` | **`5,534.5 ms` / `11,680.0 ms`** |
| **`gemini-4-argon`** | **`high`** | `22,181.4 ms` | `25,528.0 ms` | `774.6` / `235.6` | `27,175.9 ms` | `34,240.4 ms` | `1,100.0` / `601.0` | `24,678.6 ms` / `29,884.2 ms` |
| **`gemini-4-carbon`** | **`budget=0`** *(deprecated/legacy)* | `4,854.2 ms` | `7,891.5 ms` | `0.0` / `222.2` | `4,434.0 ms` | `12,103.0 ms` | `0.0` / `684.8` | `4,644.1 ms` / `9,997.2 ms` |
| **`gemini-4-carbon`** | **`low`** | `7,677.8 ms` | `11,455.9 ms` | `0.0` / `223.4` | `5,400.9 ms` | `12,485.9 ms` | `0.0` / `641.6` | `6,539.4 ms` / `11,970.9 ms` |
| **`gemini-4-carbon`** | **`medium`** *(default)* | `6,309.1 ms` | `9,129.1 ms` | `97.6` / `217.2` | `13,448.1 ms` | `19,218.0 ms` | `713.2` / `565.6` | `9,878.6 ms` / `14,173.5 ms` |
| **`gemini-4-carbon`** | **`high`** | `14,648.2 ms` | `17,207.2 ms` | `722.4` / `227.0` | `34,355.5 ms` | `40,209.9 ms` | **`2,794.6`** / `608.4` | `24,501.9 ms` / `28,708.5 ms` |

---

### 3. Per-Query Breakdown across All 22 Configurations (Tables 3-5C & 3-5D)

Each cell reports **`TTFT (ms)` / `Total (ms)` (`ThTok`)**.

#### Table 3-5C: Simple Queries (`S1`–`S5`) Breakdown by Model × Configuration (22 Configs)

| Model | Config (`level`) | `S1` Boot Greeting | `S2` Reset Thanks | `S3` Support Hours | `S4` Hold Seconds | `S5` Serial Sticker | Simple 5-Query Avg |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| **`gemini-3.5-flash-lite`** | **`budget=0`** | ❌ `400 Error` | ❌ `400 Error` | ❌ `400 Error` | ❌ `400 Error` | ❌ `400 Error` | ❌ **`400 INVALID_ARGUMENT`** |
| **`gemini-3.5-flash-lite`** | **`minimal`** | `754` / `1,415` (`0`) | `795` / `1,025` (`0`) | `736` / `1,509` (`0`) | `562` / `795` (`0`) | `822` / `2,150` (`0`) | **`733.9`** / `1,378.9` (`0.0`) |
| **`gemini-3.5-flash-lite`** | **`low`** | `781` / `1,460` (`0`) | `586` / `858` (`0`) | `625` / `1,667` (`0`) | `662` / `905` (`0`) | `704` / `1,978` (`0`) | **`671.6`** / `1,373.5` (`0.0`) |
| **`gemini-3.5-flash-lite`** | **`medium`** | `1,124` / `1,712` (`164`) | `1,086` / `1,263` (`115`) | `1,365` / `2,118` (`158`) | `1,012` / `1,223` (`129`) | `2,413` / `3,350` (`595`) | **`1,399.9`** / `1,933.5` (`232.2`) |
| **`gemini-3.5-flash-lite`** | **`high`** | `2,209` / `2,567` (`487`) | `1,679` / `1,848` (`246`) | `2,362` / `2,970` (`563`) | `1,783` / `1,938` (`372`) | `2,761` / `3,520` (`629`) | **`2,158.7`** / `2,568.6` (`459.4`) |
| **`gemini-3.8-flash`** | **`budget=0`** | `2,882` / `5,792` (`112`) | `3,737` / `5,281` (`102`) | `3,616` / `7,137` (`206`) | `2,642` / `3,165` (`80`) | `2,332` / `5,912` (`0`) | **`3,041.6`** / `5,457.5` (`100.0`) |
| **`gemini-3.8-flash`** | **`low`** | `1,378` / `3,636` (`0`) | `2,306` / `3,511` (`56`) | `3,924` / `7,590` (`254`) | `2,546` / `3,621` (`0`) | `2,139` / `6,850` (`0`) | **`2,458.7`** / `5,041.8` (`62.0`) |
| **`gemini-3.8-flash`** | **`medium`** | `3,667` / `6,632` (`170`) | `2,386` / `3,960` (`118`) | `4,880` / `8,267` (`310`) | `3,343` / `4,208` (`149`) | `5,477` / `10,211` (`287`) | **`3,950.6`** / `6,655.5` (`206.8`) |
| **`gemini-3.8-flash`** | **`high`** | `13,519` / `15,568` (`976`) | `8,599` / `9,911` (`734`) | `11,038` / `15,084` (`929`) | `5,098` / `5,877` (`377`) | `12,679` / `16,074` (`982`) | **`10,186.7`** / `12,502.7` (`799.6`) |
| **`gemini-4-hydrogen`** | **`budget=0`** | `1,714` / `2,795` (`120`) | `3,936` / `4,164` (`48`) | `3,435` / `4,622` (`155`) | `3,959` / `4,181` (`282`) | `2,050` / `3,590` (`132`) | **`3,018.6`** / `3,870.3` (`147.4`) |
| **`gemini-4-hydrogen`** | **`low`** | `1,908` / `2,720` (`143`) | `3,160` / `3,427` (`89`) | `2,327` / `3,207` (`189`) | `2,454` / `2,847` (`267`) | `3,140` / `4,637` (`231`) | **`2,598.0`** / `3,367.6` (`183.8`) |
| **`gemini-4-hydrogen`** | **`medium`** | `1,529` / `2,836` (`106`) | `4,350` / `5,038` (`143`) | `3,972` / `6,185` (`342`) | `2,076` / `2,408` (`208`) | `6,884` / `9,288` (`359`) | **`3,762.3`** / `5,150.8` (`231.6`) |
| **`gemini-4-hydrogen`** | **`high`** | `2,712` / `3,703` (`277`) | `5,756` / `6,396` (`135`) | `6,846` / `8,598` (`443`) | `2,643` / `2,929` (`256`) | `2,348` / `4,594` (`254`) | **`4,060.9`** / `5,244.0` (`273.0`) |
| **`gemini-4-hydrogen`** | **`xhigh`** | `7,021` / `7,902` (`1040`) | `4,469` / `4,922` (`526`) | `12,846` / `14,667` (`634`) | `6,338` / `6,633` (`749`) | `7,580` / `9,570` (`859`) | **`7,650.8`** / `8,738.9` (`761.6`) |
| **`gemini-4-argon`** | **`budget=0`** | `11,746` / `15,473` (`0`) | `22,471` / `24,288` (`0`) | `3,326` / `8,664` (`0`) | `4,728` / `6,385` (`0`) | `6,816` / `14,949` (`0`) | **`9,817.2`** / `13,952.0` (`0.0`) |
| **`gemini-4-argon`** | **`low`** | `2,570` / `5,326` (`0`) | `4,708` / `7,330` (`0`) | `2,638` / `9,683` (`0`) | `3,238` / `5,355` (`0`) | `8,757` / `15,552` (`0`) | **`4,382.4`** / `8,649.0` (`0.0`) |
| **`gemini-4-argon`** | **`medium`** | `3,053` / `7,037` (`0`) | `4,854` / `6,561` (`0`) | `9,451` / `15,899` (`0`) | `4,508` / `6,306` (`0`) | `8,823` / `14,598` (`0`) | **`6,137.7`** / `10,080.2` (`0.0`) |
| **`gemini-4-argon`** | **`high`** | `29,978` / `33,264` (`749`) | `11,349` / `13,092` (`338`) | `24,771` / `29,346` (`1238`) | `15,763` / `16,872` (`606`) | `29,046` / `35,066` (`942`) | **`22,181.4`** / `25,528.0` (`774.6`) |
| **`gemini-4-carbon`** | **`budget=0`** | `4,935` / `8,407` (`0`) | `4,695` / `6,488` (`0`) | `4,994` / `9,115` (`0`) | `5,174` / `6,954` (`0`) | `4,472` / `8,493` (`0`) | **`4,854.2`** / `7,891.5` (`0.0`) |
| **`gemini-4-carbon`** | **`low`** | `3,280` / `6,153` (`0`) | `4,086` / `6,120` (`0`) | `7,773` / `13,560` (`0`) | `11,728` / `13,815` (`0`) | `11,523` / `17,632` (`0`) | **`7,677.8`** / `11,455.9` (`0.0`) |
| **`gemini-4-carbon`** | **`medium`** | `10,608` / `12,918` (`488`) | `5,083` / `6,500` (`0`) | `5,712` / `10,550` (`0`) | `4,937` / `6,727` (`0`) | `5,204` / `8,951` (`0`) | **`6,309.1`** / `9,129.1` (`97.6`) |
| **`gemini-4-carbon`** | **`high`** | `9,566` / `11,715` (`559`) | `13,462` / `14,539` (`574`) | `18,835` / `22,305` (`1070`) | `11,041` / `11,829` (`438`) | `20,337` / `25,648` (`971`) | **`14,648.2`** / `17,207.2` (`722.4`) |

#### Table 3-5D: Complex Queries (`C1`–`C5`) Breakdown by Model × Configuration (22 Configs)

| Model | Config (`level`) | `C1` 3-Yr Repair vs Buy | `C2` 1.8TB Transfer | `C3` Loaner vs On-Site | `C4` 3-PC 2-Yr Plan | `C5` RAID5 Rebuild | Complex 5-Query Avg |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| **`gemini-3.5-flash-lite`** | **`budget=0`** | ❌ `400 Error` | ❌ `400 Error` | ❌ `400 Error` | ❌ `400 Error` | ❌ `400 Error` | ❌ **`400 INVALID_ARGUMENT`** |
| **`gemini-3.5-flash-lite`** | **`minimal`** | `689` / `2,049` (`0`) | `638` / `2,512` (`0`) | `688` / `1,778` (`0`) | `632` / `1,573` (`0`) | `740` / `2,404` (`0`) | **`677.6`** / `2,063.2` (`0.0`) |
| **`gemini-3.5-flash-lite`** | **`low`** | `2,092` / `3,592` (`662`) | `1,137` / `2,883` (`243`) | `474` / `1,614` (`0`) | `952` / `1,895` (`0`) | `2,681` / `4,093` (`777`) | **`1,467.2`** / `2,815.4` (`336.4`) |
| **`gemini-3.5-flash-lite`** | **`medium`** | `2,390` / `3,748` (`832`) | `2,712` / `4,527` (`944`) | `1,806` / `2,789` (`442`) | `2,733` / `3,688` (`890`) | `3,955` / `5,642` (`1314`) | **`2,719.0`** / `4,078.8` (`884.4`) |
| **`gemini-3.5-flash-lite`** | **`high`** | `4,447` / `5,638` (`1895`) | `3,983` / `5,804` (`1400`) | `2,228` / `3,371` (`807`) | `2,395` / `3,289` (`965`) | `4,417` / `6,086` (`1498`) | **`3,493.9`** / `4,837.8` (`1313.0`) |
| **`gemini-3.8-flash`** | **`budget=0`** | `1,709` / `8,464` (`0`) | `1,441` / `7,700` (`0`) | `1,898` / `5,712` (`0`) | `4,440` / `7,573` (`459`) | `3,336` / `8,816` (`0`) | **`2,564.7`** / `7,653.2` (`91.8`) |
| **`gemini-3.8-flash`** | **`low`** | `1,213` / `7,493` (`0`) | `1,570` / `8,689` (`0`) | `2,216` / `6,605` (`0`) | `5,363` / `8,859` (`523`) | `2,571` / `8,180` (`0`) | **`2,586.6`** / `7,965.4` (`104.6`) |
| **`gemini-3.8-flash`** | **`medium`** | `5,935` / `11,219` (`535`) | `7,605` / `13,135` (`776`) | `5,253` / `9,135` (`405`) | `5,300` / `8,258` (`551`) | `6,684` / `11,789` (`758`) | **`6,155.5`** / `10,707.2` (`605.0`) |
| **`gemini-3.8-flash`** | **`high`** | `17,232` / `23,500` (`1862`) | `13,341` / `20,345` (`1569`) | `11,916` / `16,018` (`1332`) | `11,399` / `14,809` (`1493`) | `13,261` / `20,070` (`1489`) | **`13,429.9`** / `18,948.5` (`1549.0`) |
| **`gemini-4-hydrogen`** | **`budget=0`** | `4,468` / `6,579` (`913`) | `7,307` / `10,135` (`790`) | `2,150` / `3,824` (`359`) | `6,981` / `8,233` (`485`) | `5,801` / `8,602` (`805`) | **`5,341.2`** / `7,474.6` (`670.4`) |
| **`gemini-4-hydrogen`** | **`low`** | `5,287` / `7,609` (`635`) | `4,134` / `6,415` (`915`) | `3,136` / `4,552` (`495`) | `3,461` / `4,592` (`688`) | `3,525` / `6,331` (`555`) | **`3,908.6`** / `5,899.8` (`657.6`) |
| **`gemini-4-hydrogen`** | **`medium`** | `6,684` / `9,248` (`1225`) | `8,374` / `11,368` (`1047`) | `3,701` / `5,209` (`649`) | `3,830` / `5,430` (`662`) | `9,942` / `13,768` (`1188`) | **`6,506.2`** / `9,004.7` (`954.2`) |
| **`gemini-4-hydrogen`** | **`high`** | `5,650` / `7,695` (`1222`) | `10,447` / `14,546` (`1954`) | `4,068` / `6,012` (`669`) | `20,291` / `21,863` (`697`) | `6,240` / `8,904` (`1238`) | **`9,339.2`** / `11,804.2` (`1156.0`) |
| **`gemini-4-hydrogen`** | **`xhigh`** | `10,703` / `13,386` (`2327`) | `13,629` / `16,628` (`2472`) | `14,595` / `16,648` (`1770`) | `14,652` / `16,410` (`1698`) | `11,500` / `14,082` (`2973`) | **`13,015.8`** / `15,431.1` (`2248.0`) |
| **`gemini-4-argon`** | **`budget=0`** | `5,216` / `12,360` (`0`) | `4,684` / `12,767` (`0`) | `6,759` / `14,124` (`0`) | `19,747` / `25,394` (`0`) | `30,099` / `41,146` (`0`) | **`13,300.9`** / `21,158.1` (`0.0`) |
| **`gemini-4-argon`** | **`low`** | `11,046` / `18,213` (`0`) | `16,490` / `26,568` (`0`) | `7,539` / `13,687` (`0`) | `7,836` / `12,810` (`0`) | `11,790` / `25,708` (`0`) | **`10,940.2`** / `19,397.1` (`0.0`) |
| **`gemini-4-argon`** | **`medium`** | `5,146` / `14,749` (`0`) | `5,018` / `13,742` (`0`) | `5,866` / `12,776` (`0`) | `5,286` / `10,626` (`0`) | `3,341` / `14,506` (`0`) | **`4,931.3`** / `13,279.8` (`0.0`) |
| **`gemini-4-argon`** | **`high`** | `28,720` / `35,282` (`971`) | `27,969` / `36,906` (`1911`) | `18,849` / `24,482` (`614`) | `14,046` / `19,463` (`850`) | `46,294` / `55,069` (`1154`) | **`27,175.9`** / `34,240.4` (`1100.0`) |
| **`gemini-4-carbon`** | **`budget=0`** | `3,963` / `10,957` (`0`) | `2,612` / `14,469` (`0`) | `4,316` / `9,688` (`0`) | `5,257` / `10,210` (`0`) | `6,022` / `15,191` (`0`) | **`4,434.0`** / `12,103.0` (`0.0`) |
| **`gemini-4-carbon`** | **`low`** | `5,460` / `12,293` (`0`) | `2,526` / `10,854` (`0`) | `4,138` / `10,116` (`0`) | `9,456` / `13,682` (`0`) | `5,424` / `15,484` (`0`) | **`5,400.9`** / `12,485.9` (`0.0`) |
| **`gemini-4-carbon`** | **`medium`** | `8,512` / `13,819` (`503`) | `27,480` / `34,911` (`1267`) | `7,724` / `12,720` (`352`) | `9,944` / `14,121` (`638`) | `13,581` / `20,519` (`806`) | **`13,448.1`** / `19,218.0` (`713.2`) |
| **`gemini-4-carbon`** | **`high`** | `30,667` / `35,428` (`2908`) | `51,353` / `59,310` (`4360`) | `29,288` / `34,225` (`2086`) | `19,564` / `24,842` (`1150`) | `40,907` / `47,244` (`3469`) | **`34,355.5`** / `40,209.9` (`2794.6`) |

---

### 4. Six Key Architectural Insights from the 220-Run Cross-Model Benchmark

1. **Empirical Behavior of Deprecated `thinking_budget=0` (`400 Error` on `3.5-flash-lite`; Coerced to `low` on the Other 4 Models)**:
   - **`gemini-3.5-flash-lite`**: Passing `thinking_budget=0` fails with **`400 INVALID_ARGUMENT`** across all 10 queries. To achieve zero-thinking inference on `3.5-flash-lite`, applications must pass **`thinking_level="minimal"`**.
   - **`gemini-3.8-flash` / `gemini-4-hydrogen` / `gemini-4-argon` / `gemini-4-carbon`**: While accepted for backward compatibility, `thinking_budget=0` is coerced server-side to each model's minimum thinking level (`low`). For example, `gemini-3.8-flash [budget=0]` averages `2,564.7 ms` (`91.8 tok`) on Complex queries—virtually identical to `low` (`2,586.6 ms`, `104.6 tok`)—and `gemini-4-hydrogen [budget=0]` still expends **`670.4` thinking tokens** on Complex queries (`657.6 tok` on `low`), confirming that `thinking_budget=0` cannot force zero thinking on always-thinking models.
2. **`gemini-3.5-flash-lite` Delivers Sub-Second TTFT (`~0.7s`) and Ultra-Fast Reasoning Decoding (`~450–500 tok/s`)**:
   - At `minimal` (its default), `3.5-flash-lite` keeps `thoughts_tokens = 0` across both Simple and Complex queries, achieving **Simple avg `TTFT = 733.9 ms` and Complex avg `TTFT = 677.6 ms` (`705.8 ms` overall)**.
   - Even at `high` on Complex queries—where it generates an average of **`1,313.0` reasoning tokens**—it reaches first token in **`3,493.9 ms` (`Total = 4,837.8 ms`)**, corresponding to `~450–500 reasoning tokens/sec` (`~4×` faster than `gemini-3.8-flash`).
3. **`gemini-4-hydrogen` Reasons More Thoroughly than `gemini-3.8-flash` Yet Completes Faster (`Total`)**:
   - Because `gemini-4-hydrogen` is an always-on reasoning model, `4-hydrogen [low]` generates `183.8 tok` on Simple queries and `657.6 tok` on Complex queries (vs. `62.0 tok` and `104.6 tok` on `3.8-flash [low]`).
   - While `3.8-flash [low]` starts slightly earlier on Complex queries (`TTFT = 2,586.6 ms` vs. `3,908.6 ms`), **`4-hydrogen [low]` has a much faster output decoding rate and finishes the entire response `~2.1 seconds` earlier (`Complex Total = 5,899.8 ms` vs. `7,965.4 ms`, and `Overall Total = 4,633.7 ms` vs. `6,503.6 ms`)**.
   - At `high`, **`4-hydrogen [high]` (`Overall TTFT = 6,700.1 ms / Total = 8,524.1 ms`) is 43–46% faster than `3.8-flash [high]` (`11,808.3 ms / 15,725.6 ms`)**.
4. **The Exclusive `xhigh` Tier on `gemini-4-hydrogen`**:
   - On Complex queries, `4-hydrogen [xhigh]` invests an average of **`2,248.0` reasoning tokens (up to `2,973 tok`)** while completing in **`TTFT = 13,015.8 ms` / `Total = 15,431.1 ms`**—delivering **1.45× more reasoning tokens in 3.5 seconds less total time than `3.8-flash [high]` (`1,549.0 tok`, `18,948.5 ms`)**.
5. **Bimodal Latency Behavior (`low` / `medium` vs. `high`) on `gemini-4-argon` and `gemini-4-carbon`**:
   - Frontier models `4-argon` and `4-carbon` operate with `thoughts_token_count = 0` at `low` (and `4-argon [medium]`), allowing `4-argon [medium]` to answer Complex queries in **`TTFT = 4,931.3 ms` (`Total = 13,279.8 ms`)**.
   - At `high` (and `4-carbon [medium]`), deep multi-step reasoning engages (`4-carbon [high]` averages **`2,794.6 tok`** and **`34.4s TTFT / 40.2s Total`** on Complex queries), making them best suited for asynchronous background workers or escalated deep-analysis tasks rather than synchronous chat UI turns.
6. **Implications for the Adaptive Thinking Router (Chapter 4)**:
   - Pairing **`gemini-3.5-flash-lite` (all levels)**, **`gemini-3.8-flash [low]`**, or **`gemini-4-hydrogen [low]`** as the Stage-1 immediate response router with **`gemini-3.8-flash [medium / high]`** or **`Gemini 4` series (`4-hydrogen [medium+]` / `4-argon` / `4-carbon`)** as the parallel Stage-2 reasoning worker achieves ~1–2s perceived responsiveness alongside rigorous multi-step calculation verification.

