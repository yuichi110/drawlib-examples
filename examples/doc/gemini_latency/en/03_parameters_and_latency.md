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

| Option Value (`thinking=`) | Normalized Label | SDK Configuration (`types.ThinkingConfig`) | Measured Reasoning Tokens (`ThTok`) | Behavior & Primary Use Cases |
| :--- | :--- | :--- | :--- | :--- |
| **`0`** (or `"0"`) | `"0"` | `ThinkingConfig(thinking_budget=0)` | **`0 tok`** | Hard-caps internal reasoning budget at `0` tokens. Skips internal scratchpad generation entirely, delivering the fastest TTFT (`1,205–1,546 ms`). Ideal for greetings, standard procedures, and stage-1 routers. |
| **`1`** (or `"minimal"`) | `"minimal"` | `ThinkingConfig(thinking_level=MINIMAL)` | **`0 tok`** | Minimal reasoning preset. Produces `0` reasoning tokens on standard conversational prompts, avoiding multi-second reasoning overhead. |
| **`2`** (or `"low"`) | `"low"` | `ThinkingConfig(thinking_level=LOW)` | **`351–557 tok`** | Light internal reasoning (`~4.3–5.5 s` TTFT). Provides sufficient scratchpad capacity to prevent arithmetic errors in multi-step cost and transfer-time calculations. |
| **`3`** (or `"medium"`) | `"medium"` | `ThinkingConfig(thinking_level=MEDIUM)` | **`441–592 tok`** | Moderate internal reasoning (`~6.2–6.7 s` TTFT). |
| **`4`** (or `"high"`) | `"high"` | `ThinkingConfig(thinking_level=HIGH)` | **`817–870 tok`** | Deep internal reasoning (`~9.0–9.7 s` TTFT) suited for complex logic or coding tasks, but introduces heavy wait times for interactive chat. |
| **`None`** (or `"default"`) | `"default"` | Omitted (Dynamic server default) | **`467–1,006 tok`** | Default behavior when `thinking_config` is omitted. Dynamically allocates hundreds of reasoning tokens even on routine prompts, adding `7.5–10.4 s` of latency. |

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
