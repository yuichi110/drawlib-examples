# 4. Adaptive Thinking Router Pattern

Chapter 3 established a fundamental dilemma in `gemini-3.8-flash`: fixing `thinking=0` yields fast responsiveness (`1,879 ms` mean TTFT) but lacks an internal reasoning scratchpad on multi-step calculations (Tier 3), whereas fixing `thinking=low` achieves full scratchpad verification (**3/3 verified**) on Tier 3 at the cost of adding unnecessary reasoning delay to routine turns (Tiers 1–2) and freezing the UI for up to `12.16 s` on complex turns. In this chapter, we introduce the **Adaptive Thinking Router Pattern** (`src/gemini_evaluation/adaptive_thinking.py`), evaluate three candidate architectures (Patterns A, B, and C) across a 45-run empirical benchmark (9 prompts × 5 methods), and prove why **Pattern A (2-Field Integrated Pydantic Schema `{thinking: bool, response: str}` + Parallel Stage-2 Chaining)** is the optimal production architecture.

```drawlib align=center code=fold width=100% file=ch04_adaptive_architectures_hero.png caption="Figure 4-1: Side-by-Side Architecture Sequence Comparison of Candidate Adaptive Thinking Routers (Pattern A: 2-Field Integrated Pydantic, Pattern B: 1-Field Sequential Router, Pattern C: Tag Prefix)"
from drawlib.canvas import save, setup
from drawlib.icons import phosphor
from drawlib.lines import line
from drawlib.shapes import rectangle
from drawlib.styles import Styles
from drawlib.text import text

setup(width=172, height=94, dpi=150)

# Outer structural frame
rectangle((86.0, 47.0), width=168.0, height=90.0, style=Styles.MutedDashed.patch(shape_r=2.0))
text(
    (86.0, 87.6),
    "Adaptive Thinking Router Architectures (Patterns A, B, C): Sequence & Latency Comparison",
    style=Styles.DarkBold.patch(text_size=12.0),
)

# Top UX Target Bar
rectangle((86.0, 79.2), width=160.0, height=8.8, style=Styles.Neutral.patch(shape_r=1.2))
phosphor.gauge((10.5, 81.0), width=3.2, style=Styles.PrimaryBold)
text(
    (14.0, 81.0),
    "UX Latency Targets: (1) Eliminate 9–12s Reasoning Freezes / (2) Overhead vs. Tag Baseline < 0.5s",
    style=Styles.PrimaryBold.patch(text_size=10.5, halign="left"),
)
text(
    (14.0, 77.0),
    "Stage 1 (thinking=0) streams direct answers or a 1-sentence bridge while Stage 2 (thinking=low) runs in parallel",
    style=Styles.Dark.patch(text_size=10.0, halign="left"),
)

# 3 Architecture Columns
cols = [
    (
        33.0,
        "★ Pattern A [Recommended]",
        "2-Field Integrated Pydantic + Parallel Stage 2",
        "Stage 1: thinking=0 + JSON Schema",
        "Streams {thinking: bool, response: str}",
        "false: 1 API Call Direct Stream",
        "Eliminates unneeded reasoning (0 tok)",
        "true: Bridge (~2.3s) + Parallel Stage 2",
        "asyncio.create_task hides low reasoning",
        [
            "• All-9 Mean TTFT: 2,340 ms (-63% vs low)",
            "• Eliminates up to 12.2s Tier 3 freeze",
            "• Decoder Type-Safe & 3/3 Math [PASS]",
        ],
        Styles.PrimaryFlat,
        Styles.WhiteBold,
        Styles.White,
        Styles.SecondaryNeutral,
        phosphor.star,
    ),
    (
        86.0,
        "Pattern B [Sequential Router]",
        "1-Field Router {thinking: bool} + Stream",
        "Stage 1: Blocking Router API Call",
        "generate_content returns {thinking}",
        "Stage 2: Sequential Stream API Call",
        "Always 2 RTTs (T1–2 TTFT 3,522 ms)",
        "true: Router RTT + low Wait Stack Up",
        "Tier 3 Mean TTFT 11,488 ms (Max 12.6s)",
        [
            "• All-9 Mean TTFT: 6,177 ms (Sequential lag)",
            "• Always requires 2 sequential calls",
            "• Verdict: Excessive RTT penalty [FAIL]",
        ],
        Styles.Neutral,
        Styles.DangerBold,
        Styles.DarkBold,
        Styles.WhiteFlat,
        phosphor.git_branch,
    ),
    (
        139.0,
        "Pattern C [Tag Prefix Baseline]",
        "Plain-Text Prefix [DIRECT] / [THINK]",
        "Stage 1: thinking=0 Plain Stream",
        "Prompt-only prefix tag without JSON schema",
        "[DIRECT]: Strip Tag & Stream Body",
        "TTFT 1,920 ms / No schema validation",
        "[THINK]: Bridge (~1.8s) + Parallel Stage 2",
        "Same parallel flow but no schema safety",
        [
            "• All-9 Mean TTFT: 1,879 ms (461 ms vs A)",
            "• Risk of tag leak & multi-turn drift",
            "• Verdict: Unify on type-safe Pattern A",
        ],
        Styles.SecondaryNeutral,
        Styles.SecondaryBold,
        Styles.DarkBold,
        Styles.WhiteFlat,
        phosphor.tag,
    ),
]

for (
    cx,
    title_s,
    sub_s,
    s1_t,
    s1_b,
    s2_t,
    s2_b,
    s3_t,
    s3_b,
    bullets,
    card_st,
    hdr_st,
    sub_st,
    mid_st,
    ic_fn,
) in cols:
    rectangle((cx, 42.5), width=51.0, height=58.0, style=card_st.patch(shape_r=1.6))
    ic_fn((cx - 21.5, 67.8), width=3.2, style=hdr_st)
    text((cx + 1.5, 67.8), title_s, style=hdr_st.patch(text_size=10.5))
    text((cx, 64.0), sub_s, style=sub_st.patch(text_size=10.0))

    # Step Box 1
    rectangle((cx, 56.5), width=48.2, height=8.6, style=Styles.WhiteFlat.patch(shape_r=1.0))
    text((cx, 58.4), s1_t, style=Styles.PrimaryBold.patch(text_size=10.0))
    text((cx, 54.6), s1_b, style=Styles.Dark.patch(text_size=10.0))

    arr_st = Styles.WhiteBold.patch(line_width=1.8) if card_st == Styles.PrimaryFlat else Styles.DarkBold.patch(line_width=1.8)
    line((cx, 52.2), (cx, 49.4), arrow_head="->", style=arr_st)

    # Step Box 2
    rectangle((cx, 45.0), width=48.2, height=8.6, style=mid_st.patch(shape_r=1.0))
    text((cx, 46.9), s2_t, style=Styles.DarkBold.patch(text_size=10.0))
    text((cx, 43.1), s2_b, style=Styles.Dark.patch(text_size=10.0))

    line((cx, 40.7), (cx, 37.9), arrow_head="->", style=arr_st)

    # Step Box 3
    rectangle((cx, 33.5), width=48.2, height=8.6, style=Styles.WhiteFlat.patch(shape_r=1.0))
    text((cx, 35.4), s3_t, style=Styles.SecondaryBold.patch(text_size=10.0))
    text((cx, 31.6), s3_b, style=Styles.Dark.patch(text_size=10.0))

    b_style = (
        Styles.White.patch(text_size=10.0, halign="left")
        if card_st == Styles.PrimaryFlat
        else Styles.Dark.patch(text_size=10.0, halign="left")
    )
    for idx, b_line in enumerate(bullets):
        text((cx - 22.8, 25.5 - idx * 4.2), b_line, style=b_style)

# Bottom conclusion bar
rectangle((86.0, 6.2), width=160.0, height=6.4, style=Styles.PrimaryNeutral.patch(shape_r=1.2))
phosphor.shield_check((10.5, 6.2), width=3.2, style=Styles.PrimaryBold)
text(
    (14.0, 6.2),
    "Conclusion: Pattern A hits 2,340 ms mean TTFT (-63% vs Base Low), within 461 ms of Pattern C while guaranteeing JSON schema safety.",
    style=Styles.DarkBold.patch(text_size=10.0, halign="left"),
)

save()
```

---

## 4.1 UX Latency Target & 3 Candidate Architectures (Pattern A, B, C)

### Cognitive UX Response-Time Thresholds & Design Targets

Our engineering targets for the Adaptive Thinking Router are:
1. **Eliminate 9–12 second blank-screen freezes during internal reasoning by keeping TTFT near the `thinking=0` baseline across all query complexity tiers**.
2. **Keep TTFT overhead vs. an unstructured tag baseline `< 0.5 s` (below human perceptual discrimination)** while enforcing decoder-level JSON schema guarantees and 100% mathematical verification.

### Architectural Comparison of Patterns A, B, and C

In `src/gemini_evaluation/adaptive_thinking.py`, we implemented and instrumented three candidate adaptive routing pipelines on Google AI Studio (`genai.Client(api_key=GEMINI_KEY)` with `gemini-3.8-flash`), illustrated in Figure 4-1:

1. **Pattern A (Recommended — 2-Field Integrated Pydantic `{thinking: bool, response: str}` + Parallel Stage-2 Chaining)**
   - **Stage 1** initiates a single `generate_content_stream` call with `thinking_budget=0` and `response_schema=AdaptiveStreamResponse`. Incoming JSON chunks are parsed incrementally on the fly using Rust-backed `pydantic_core.from_json(..., allow_partial="trailing-strings")`.
   - **`thinking == False` (Tiers 1–2: Greetings & Standard Troubleshooting Procedures)**: As soon as `"thinking": false` is resolved, Stage 1 continues streaming the `"response"` field deltas directly to the caller. **The entire turn completes in 1 API call**, achieving **`2,354 ms` mean TTFT** and **`4,808 ms` mean total completion** on Tiers 1–2.
   - **`thinking == True` (Tier 3: Complex Multi-Step Math)**: The instant `"thinking": true` is parsed, Pattern A spawns **Stage 2 (`thinking=low` plain-text stream) in parallel** via `asyncio.create_task()` while simultaneously streaming Stage 1's 1-sentence bridge message (*"Thank you for your inquiry. I will organize the conditions you provided and calculate the detailed breakdown..."*). While the user reads the bridge sentence, Stage 2 completes its internal reasoning scratchpad (`755–951 tokens`) in the background and seamlessly chains the verified calculation stream.
2. **Pattern B (1-Field Sequential Router `{thinking: bool}` + Stage-2 Stream)**
   - Avoids incremental JSON parsing by first executing a blocking `generate_content` call with `ThinkingDecision(thinking: bool)` and then launching a second `generate_content_stream` call (`thinking=0` or `thinking=low`).
   - Because **every prompt requires 2 sequential API round-trips (`calls=2.0`)**, routine Tier 1–2 TTFT degrades to **`3,522 ms`**, and Tier 3 TTFT balloons to **`11,488 ms`** (overall mean TTFT **`6,177 ms`**).
3. **Pattern C (Tag Prefix `[DIRECT]` / `[THINK]`)**
   - Uses prompt instructions to emit a plain-text `[DIRECT]` or `[THINK]` prefix tag instead of a JSON schema.
   - While Pattern C achieves a **`1,879 ms` overall mean TTFT**, the difference versus Pattern A (**`2,340 ms`**) is only **`461 ms` (`< 0.5 s`)**. Moreover, because Pydantic's structured output keeps responses concise, **Pattern A finishes Tiers 1–2 faster than Pattern C (`4,808 ms` vs. `5,030 ms`)**, while eliminating Pattern C's risk of raw tag leakage (`[direct]`, `**[THINK]**`) and multi-turn few-shot tag omission.

---

## 4.2 45-Run Empirical Benchmark (9 Prompts × 5 Methods)

Using `src/gemini_evaluation/benchmark_adaptive_thinking.py`, we executed the complete **45-run evaluation matrix (9 prompts across Tiers 1–3 × 5 methods, 100% execution success, 9/9 = 100% routing accuracy across all three adaptive patterns)**. Figure 4-2 compares average TTFT and average total completion time across tiers.

```drawlib align=center code=fold width=100% file=ch04_tier_latency_barchart.png caption="Figure 4-2: Average TTFT (Left) and Average Total Completion Time (Right) by Complexity Tier (Tier 1, Tier 2, Tier 3, All-9 Mean) across All 5 Methods"
from statistics import mean

from drawlib.canvas import save, setup
from drawlib.charts.bar import BarChart
from drawlib.icons import phosphor
from drawlib.shapes import rectangle
from drawlib.styles import Styles
from drawlib.text import text
from drawlib.utils import load_adaptive_runs

setup(width=172, height=112, dpi=150)

# Outer structural frame
rectangle((86.0, 56.0), width=168.0, height=108.0, style=Styles.MutedDashed.patch(shape_r=2.0))
text(
    (86.0, 105.8),
    "45-Run Empirical Benchmark: Mean TTFT (Left) & Mean Total Completion Time (Right) by Tier",
    style=Styles.DarkBold.patch(text_size=12.0),
)

runs = load_adaptive_runs()
tier_groups = [
    ("tier1_simple", "Tier 1: Greeting"),
    ("tier2_procedure", "Tier 2: Procedure"),
    ("tier3_complex", "Tier 3: Complex"),
    ("all", "All-9 Mean"),
]
categories = [lbl for _, lbl in tier_groups]


def calc_means(m_key: str, metric: str) -> list[float]:
    out: list[float] = []
    for tk, _ in tier_groups:
        sub = [r for r in runs if r["method_key"] == m_key and (tk == "all" or r["tier"] == tk)]
        out.append(float(round(mean(float(r[metric]) for r in sub))))
    return out


# 2-row Legend at top
rectangle((86.0, 97.2), width=160.0, height=9.2, style=Styles.Neutral.patch(shape_r=1.2))

leg_row1 = [
    (10.0, Styles.PrimaryFlat, "★ Pattern A: 2-Field {thinking, response} [Recommended]"),
    (95.0, Styles.TealFlat, "Pattern C: Tag Prefix [DIRECT]/[THINK]"),
]
for lx, st, ltxt in leg_row1:
    rectangle((lx, 99.3), width=3.6, height=2.0, style=st.patch(shape_r=0.3))
    text((lx + 2.8, 99.3), ltxt, style=Styles.DarkBold.patch(text_size=10.0, halign="left"))

leg_row2 = [
    (10.0, Styles.SuccessFlat, "Base 0: Fixed thinking=0 (Unverified)"),
    (66.0, Styles.WarningFlat, "Base Low: Fixed thinking=low"),
    (116.0, Styles.DangerFlat, "Pattern B: 1-Field Sequential Router"),
]
for lx, st, ltxt in leg_row2:
    rectangle((lx, 95.1), width=3.6, height=2.0, style=st.patch(shape_r=0.3))
    text((lx + 2.8, 95.1), ltxt, style=Styles.Dark.patch(text_size=10.0, halign="left"))

# Left Panel: Average TTFT (ms)
rectangle((45.5, 52.0), width=79.0, height=76.0, style=Styles.WhiteFlat.patch(shape_r=1.4, line_width=0.8))
text((45.5, 86.8), "(1) Mean Time to First Token: TTFT (ms)", style=Styles.PrimaryBold.patch(text_size=11.0))

chart_ttft = BarChart(
    axis_line_style=Styles.Dark,
    axis_text_style=Styles.DarkBold.patch(text_size=9.5),
    grid_style=Styles.MutedDashed,
    value_text_style=Styles.DarkBold.patch(text_size=8.6),
    width=52.0,
    height=64.0,
    categories=categories,
    orientation="horizontal",
    bar_mode="group",
    bar_width_ratio=0.74,
    bar_r=0.3,
)
chart_ttft.configure_x_axis(min_value=0, max_value=15000, tick_step=5000, format="{:,.0f}")
chart_ttft.add_series("pat_a", calc_means("pat_a_pydantic_2f", "ttft_ms"), style=Styles.PrimaryFlat)
chart_ttft.add_series("pat_c", calc_means("pat_c_tag", "ttft_ms"), style=Styles.TealFlat)
chart_ttft.add_series("base_0", calc_means("base_0", "ttft_ms"), style=Styles.SuccessFlat)
chart_ttft.add_series("base_low", calc_means("base_low", "ttft_ms"), style=Styles.WarningFlat)
chart_ttft.add_series("pat_b", calc_means("pat_b_pydantic_1f", "ttft_ms"), style=Styles.DangerFlat)
chart_ttft.draw(xy=(24.5, 17.5))

# Right Panel: Average Total Completion Time (ms)
rectangle((126.5, 52.0), width=79.0, height=76.0, style=Styles.WhiteFlat.patch(shape_r=1.4, line_width=0.8))
text((126.5, 86.8), "(2) Mean Stream Completion: Total (ms)", style=Styles.DarkBold.patch(text_size=11.0))

chart_tot = BarChart(
    axis_line_style=Styles.Dark,
    axis_text_style=Styles.DarkBold.patch(text_size=9.5),
    grid_style=Styles.MutedDashed,
    value_text_style=Styles.DarkBold.patch(text_size=8.6),
    width=52.0,
    height=64.0,
    categories=categories,
    orientation="horizontal",
    bar_mode="group",
    bar_width_ratio=0.74,
    bar_r=0.3,
)
chart_tot.configure_x_axis(min_value=0, max_value=24000, tick_step=8000, format="{:,.0f}")
chart_tot.add_series("pat_a", calc_means("pat_a_pydantic_2f", "total_ms"), style=Styles.PrimaryFlat)
chart_tot.add_series("pat_c", calc_means("pat_c_tag", "total_ms"), style=Styles.TealFlat)
chart_tot.add_series("base_0", calc_means("base_0", "total_ms"), style=Styles.SuccessFlat)
chart_tot.add_series("base_low", calc_means("base_low", "total_ms"), style=Styles.WarningFlat)
chart_tot.add_series("pat_b", calc_means("pat_b_pydantic_1f", "total_ms"), style=Styles.DangerFlat)
chart_tot.draw(xy=(105.5, 17.5))

# Bottom summary banner
rectangle((86.0, 6.2), width=160.0, height=6.4, style=Styles.PrimaryNeutral.patch(shape_r=1.2))
phosphor.check_circle((10.5, 6.2), width=3.2, style=Styles.PrimaryBold)
text(
    (14.0, 6.2),
    "Takeaway: Pattern A keeps TTFT at ~2.3s across all tiers, eliminating the 9–12s freezes of Base Low and Pattern B.",
    style=Styles.DarkBold.patch(text_size=10.0, halign="left"),
)

save()
```

### All-45-Runs Scatter Distribution

To verify that Pattern A's responsiveness holds across individual prompts without tail spikes, Figure 4-3 plots every single execution (`45 runs = 9 prompts × 5 methods`) on the `TTFT (ms) × Total Completion (ms)` plane.

```drawlib align=center code=fold width=100% file=ch04_all45_runs_scatter.png caption="Figure 4-3: All-45-Runs Latency Distribution (TTFT vs. Total Completion Time) across All 5 Methods"
from drawlib.canvas import save, setup
from drawlib.charts.scatter import ScatterChart
from drawlib.icons import phosphor
from drawlib.lines import line
from drawlib.shapes import rectangle
from drawlib.styles import Styles
from drawlib.text import text
from drawlib.utils import load_adaptive_runs

setup(width=172, height=92, dpi=150)

# Outer structural frame
rectangle((86.0, 46.0), width=168.0, height=88.0, style=Styles.MutedDashed.patch(shape_r=2.0))
text(
    (86.0, 85.8),
    "All 45 Runs (9 Prompts × 5 Methods): TTFT vs. Total Latency Distribution",
    style=Styles.DarkBold.patch(text_size=12.0),
)

runs = load_adaptive_runs()
series_pts: dict[str, list[tuple[float, float]]] = {
    "pat_a_pydantic_2f": [],
    "pat_c_tag": [],
    "base_0": [],
    "base_low": [],
    "pat_b_pydantic_1f": [],
}
for r in runs:
    series_pts[r["method_key"]].append((float(r["ttft_ms"]), float(r["total_ms"])))

# Left Chart Container
rectangle((62.0, 47.0), width=112.0, height=69.0, style=Styles.WhiteFlat.patch(shape_r=1.4, line_width=0.8))

# 2-row custom legend at top of chart container
rectangle((62.0, 75.8), width=107.0, height=8.8, style=Styles.Neutral.patch(shape_r=1.0))
leg1 = [
    (11.5, Styles.PrimaryFlat, "★ Pattern A: 2-Field Pydantic (9)"),
    (64.5, Styles.TealFlat, "Pattern C: Tag Prefix (9)"),
]
for lx, st, ltxt in leg1:
    rectangle((lx, 77.8), width=3.2, height=1.8, style=st.patch(shape_r=0.3))
    text((lx + 2.4, 77.8), ltxt, style=Styles.DarkBold.patch(text_size=10.0, halign="left"))

leg2 = [
    (11.5, Styles.SuccessFlat, "Base 0: Fixed 0 (9)"),
    (46.5, Styles.WarningFlat, "Base Low: Fixed low (9)"),
    (83.5, Styles.DangerFlat, "Pattern B: 1-Field Router (9)"),
]
for lx, st, ltxt in leg2:
    rectangle((lx, 73.8), width=3.2, height=1.8, style=st.patch(shape_r=0.3))
    text((lx + 2.4, 73.8), ltxt, style=Styles.Dark.patch(text_size=10.0, halign="left"))

# Highlight UX target zone inside plot area
PX0 = 25.8
PW_AX = 82.0
PY0 = 27.5
PH_AX = 37.7

x_2500 = PX0 + (2500.0 / 14000.0) * PW_AX
x_3500 = PX0 + (3500.0 / 14000.0) * PW_AX

rectangle(
    ((PX0 + x_2500) / 2.0, (PY0 + PY0 + PH_AX) / 2.0),
    width=x_2500 - PX0,
    height=PH_AX,
    style=Styles.PrimaryNeutralFlat,
)

chart = ScatterChart(
    axis_line_style=Styles.Dark,
    axis_text_style=Styles.Dark.patch(text_size=10.0),
    grid_style=Styles.MutedDashed,
    width=102.0,
    height=52.0,
    default_radius=1.25,
)
chart.configure_x_axis(
    label="Time to First Token TTFT (ms)",
    min_value=0,
    max_value=14000,
    tick_step=3500,
    format="{:,.0f}",
)
chart.configure_y_axis(
    label="Total (ms)",
    min_value=0,
    max_value=24000,
    tick_step=6000,
    format="{:.0f}",
)

chart.add_series("Base Low", series_pts["base_low"], style=Styles.WarningFlat, shape="rhombus", radius=1.2)
chart.add_series("Pattern B", series_pts["pat_b_pydantic_1f"], style=Styles.DangerFlat, shape="square", radius=1.15)
chart.add_series("Base 0", series_pts["base_0"], style=Styles.SuccessFlat, shape="square", radius=1.15)
chart.add_series("Pattern C", series_pts["pat_c_tag"], style=Styles.TealFlat, shape="triangle", radius=1.2)
chart.add_series("Pattern A", series_pts["pat_a_pydantic_2f"], style=Styles.PrimaryFlat, shape="circle", radius=1.3)

chart.draw(xy=(10.0, 16.5))

# Vertical UX Threshold Lines
line((x_2500, PY0), (x_2500, PY0 + PH_AX), style=Styles.PrimaryBold.patch(line_width=1.5))
text((x_2500, PY0 + PH_AX + 2.0), "2.5s Target", style=Styles.PrimaryBold.patch(text_size=10.0))

line((x_3500, PY0), (x_3500, PY0 + PH_AX), style=Styles.DangerBold.patch(line_width=1.5))
text((x_3500 + 8.5, PY0 + PH_AX + 2.0), "3.5s Limit", style=Styles.DangerBold.patch(text_size=10.0))

# Right-side Summary Cards
rectangle((143.0, 47.0), width=44.0, height=69.0, style=Styles.PrimaryNeutral.patch(shape_r=1.5))
text((143.0, 77.2), "45-Run Distribution Insights", style=Styles.PrimaryBold.patch(text_size=11.0))

cards = [
    (
        63.0,
        "1. Pattern A Mean 2.34s",
        "All 9 prompts land in 2.0–3.0s\n(mean 2,340 ms), cutting Base Low\nTTFT (6,290 ms) by -63%!",
        Styles.PrimaryBold,
    ),
    (
        44.5,
        "2. Orthogonal X vs. Y Scaling",
        "As Tier 3 total time scales to\n16–20s on Y, Pattern A's TTFT stays\npinned at ~2.3s without X-drift",
        Styles.SuccessBold,
    ),
    (
        26.0,
        "3. Base Low / Pat B Freeze",
        "Reasoning delay pushes X-axis\nto 12,155–12,590 ms, leaving the\nuser screen blank for ~12 seconds",
        Styles.DangerBold,
    ),
]
for cy, ctitle, cbody, hst in cards:
    rectangle((143.0, cy), width=40.4, height=15.6, style=Styles.WhiteFlat.patch(shape_r=1.0))
    text((143.0, cy + 4.8), ctitle, style=hst.patch(text_size=10.0))
    text((143.0, cy - 1.5), cbody, style=Styles.Dark.patch(text_size=10.0))

# Bottom banner
rectangle((86.0, 6.2), width=160.0, height=6.4, style=Styles.SecondaryNeutral.patch(shape_r=1.2))
phosphor.target((10.5, 6.2), width=3.2, style=Styles.SecondaryBold)
text(
    (14.0, 6.2),
    "Conclusion: Every Pattern A execution stays strictly within ~2.0–3.0s TTFT, eliminating 9–12s blank-screen freezes.",
    style=Styles.DarkBold.patch(text_size=10.0, halign="left"),
)

save()
```

### Complete 45-Run Empirical Table (`TTFT / Total` in ms)

| Prompt ID & Title | Expected Route<br>(A/B/C Match) | Base 0 (`t=0`)<br>`TTFT / Total` | Base Low (`low`)<br>`TTFT / Total` | ★ Pattern A (`2F`)<br>`TTFT / Total` | Pattern B (`1F`)<br>`TTFT / Total` | Pattern C (`Tag`)<br>`TTFT / Total` | Quality & Verification |
| :--- | :---: | ---: | ---: | ---: | ---: | ---: | :--- |
| **`T1_1` Initial PC Boot Greeting** | `False` (`3/3`) | `1,548 / 3,477` | `3,572 / 5,361` | **`2,980 / 4,768`** | `3,103 / 5,451` | `2,248 / 4,230` | All valid |
| **`T1_2` Thanks / Follow-up** | `False` (`3/3`) | `1,940 / 3,267` | `4,244 / 5,274` | **`2,020 / 3,522`** | `3,332 / 4,837` | `2,217 / 3,139` | All valid |
| **`T1_3` Support Hours** | `False` (`3/3`) | `1,671 / 4,578` | `2,928 / 4,823` | **`2,222 / 4,347`** | `2,982 / 5,650` | `1,561 / 3,581` | All valid |
| **`T2_1` Power Discharge Reset** | `False` (`3/3`) | `2,336 / 7,610` | `5,901 / 12,158` | **`2,243 / 4,629`** | `3,647 / 10,879` | `1,899 / 5,914` | All valid (A fastest total) |
| **`T2_2` Pre-Repair Checklist** | `False` (`3/3`) | `1,748 / 7,837` | `6,349 / 11,836` | **`2,126 / 6,073`** | `3,897 / 10,757` | `1,910 / 7,448` | All valid (A fastest total) |
| **`T2_3` Liquid Spill Emergency** | `False` (`3/3`) | `2,076 / 5,454` | `5,750 / 9,683` | **`2,531 / 5,509`** | `4,169 / 8,988` | `1,687 / 5,869` | All valid |
| **`T3_1` 3-Yr PC Repair vs. Buy** | `True` (`3/3`) | `1,515 / 7,895` | `8,950 / 17,058` | **`2,120 / 16,650`** | `11,226 / 20,762` | `1,613 / 16,499` | All 4 `low` methods pre-verified |
| **`T3_2` 500GB SSD Transfer Time** | `True` (`3/3`) | `2,235 / 9,017` | `12,155 / 19,297` | **`2,456 / 19,344`** | `12,590 / 18,325` | `1,834 / 15,826` | All 4 `low` methods pre-verified |
| **`T3_3` 2-Yr 3-PC Maintenance** | `True` (`3/3`) | `1,840 / 8,443` | `6,762 / 13,384` | **`2,365 / 20,707`** | `10,649 / 18,167` | `1,939 / 17,085` | All 4 `low` methods pre-verified |
| **Tier 1 Mean (3 Prompts)** | **`3/3` Match** | `1,720 / 3,774` | `3,581 / 5,153` | **`2,407 / 4,212`** | `3,139 / 5,313` | `2,009 / 3,650` | `0 tok` reasoning on A/B/C |
| **Tier 2 Mean (3 Prompts)** | **`3/3` Match** | `2,053 / 6,967` | `6,000 / 11,226` | **`2,300 / 5,404`** | `3,904 / 10,208` | `1,832 / 6,410` | **Pattern A fastest completion** |
| **Tier 1–2 Mean (6 Prompts)** | **`6/6` Match** | `1,887 / 5,371` | `4,791 / 8,189` | **`2,354 / 4,808`** | `3,522 / 7,760` | `1,920 / 5,030` | **Pattern A fastest completion** |
| **Tier 3 Mean (3 Prompts)** | **`3/3` Match** | `1,863 / 8,452` | `9,289 / 16,580` | **`2,314 / 18,900`** | `11,488 / 19,085` | `1,795 / 16,470` | All 4 `low` methods `3/3` verified |
| **All-9 Prompts Mean** | **`9/9` Match** | `1,879 / 6,398` | `6,290 / 10,986` | **`2,340 / 9,505`** | `6,177 / 11,535` | `1,879 / 8,843` | **Pattern A optimal** |

---

## 4.3 Trajectory Deep Dive (`thinking=false` Direct vs. `thinking=true` Parallel Chaining)

To see how Pattern A operates millisecond by millisecond under both routing branches, Figure 4-4 plots the cumulative character trajectories loaded via `load_adaptive_trajectory()` for **`T2_1` (Tier 2 standard procedure: `thinking=false` direct stream)** and **`T3_1` (Tier 3 complex math: `thinking=true` parallel Stage-2 chaining)**.

```drawlib align=center code=fold width=100% file=ch04_trajectory_deep_dive.png caption="Figure 4-4: 2-Panel Trajectory Deep Dive Comparing Tier 2 Direct Streaming (T2_1: thinking=false) vs. Tier 3 Parallel Stage-2 Chaining (T3_1: thinking=true)"
from drawlib.canvas import save, setup
from drawlib.icons import phosphor
from drawlib.lines import line
from drawlib.shapes import circle, rectangle
from drawlib.styles import Styles
from drawlib.text import text
from drawlib.utils import load_adaptive_trajectory

setup(width=172, height=96, dpi=150)

# Outer structural frame
rectangle((86.0, 48.0), width=168.0, height=92.0, style=Styles.MutedDashed.patch(shape_r=2.0))
text(
    (86.0, 89.6),
    "Trajectory Deep Dive: T2_1 (thinking=false Direct Stream) vs. T3_1 (thinking=true Parallel Chaining)",
    style=Styles.DarkBold.patch(text_size=12.0),
)

# Shared Legend Bar
rectangle((86.0, 82.8), width=162.0, height=5.2, style=Styles.Neutral.patch(shape_r=1.0))

leg_items = [
    (8.5, Styles.PrimaryBold, Styles.PrimaryFlat, "★ Pattern A (2-Field)"),
    (45.0, Styles.TealBold, Styles.TealFlat, "Pattern C (Tag)"),
    (75.5, Styles.SuccessBold, Styles.SuccessFlat, "Base 0 (Fixed 0)"),
    (111.5, Styles.WarningBold, Styles.WarningFlat, "Base Low (Fixed low)"),
    (143.5, Styles.DangerBold, Styles.DangerFlat, "Pattern B (1F)"),
]
for lx, lst, cst, ltxt in leg_items:
    line((lx, 82.8), (lx + 3.4, 82.8), style=lst.patch(line_width=2.2))
    circle((lx + 1.7, 82.8), radius=0.75, style=cst)
    text((lx + 4.3, 82.8), ltxt, style=Styles.DarkBold.patch(text_size=9.6, halign="left"))


def draw_multi_trajectory_panel(
    *,
    x0: float,
    y0: float,
    pw: float,
    ph: float,
    prompt_id: str,
    title_s: str,
    sub_s: str,
    max_t: float,
    max_c: float,
    x_ticks: list[int],
    y_ticks: list[int],
) -> tuple[object, object]:
    rectangle((x0 + pw / 2, y0 + ph / 2 + 2.5), width=pw + 14.0, height=ph + 19.0, style=Styles.LightFlat.patch(shape_r=1.6))
    text((x0 + pw / 2, y0 + ph + 8.2), title_s, style=Styles.DarkBold.patch(text_size=11.0))
    text((x0 + pw / 2, y0 + ph + 4.4), sub_s, style=Styles.PrimaryBold.patch(text_size=10.0))
    rectangle((x0 + pw / 2, y0 + ph / 2), width=pw, height=ph, style=Styles.WhiteFlat)

    def px(t_ms: float) -> float:
        return x0 + min(max(t_ms, 0.0), max_t) / max_t * pw

    def py(c_val: float) -> float:
        return y0 + min(max(c_val, 0.0), max_c) / max_c * ph

    for xt in x_ticks:
        tx = px(float(xt))
        line((tx, y0), (tx, y0 + ph), style=Styles.LightDashed.patch(line_width=0.7))
        text((tx, y0 - 2.6), f"{xt / 1000:.0f}s", style=Styles.Dark.patch(text_size=10.0))

    for yt in y_ticks:
        ty = py(float(yt))
        line((x0, ty), (x0 + pw, ty), style=Styles.LightDashed.patch(line_width=0.7))
        text((x0 - 3.6, ty), f"{yt:,}", style=Styles.Dark.patch(text_size=10.0))

    line((x0, y0), (x0 + pw, y0), style=Styles.Dark.patch(line_width=1.1))
    line((x0, y0), (x0, y0 + ph), style=Styles.Dark.patch(line_width=1.1))

    method_styles = [
        ("base_0", Styles.SuccessBold.patch(line_width=1.6), Styles.SuccessFlat, 0.65),
        ("pat_c_tag", Styles.TealBold.patch(line_width=1.7), Styles.TealFlat, 0.7),
        ("base_low", Styles.WarningBold.patch(line_width=1.8), Styles.WarningFlat, 0.75),
        ("pat_b_pydantic_1f", Styles.DangerBold.patch(line_width=1.8), Styles.DangerFlat, 0.75),
        ("pat_a_pydantic_2f", Styles.PrimaryBold.patch(line_width=2.5), Styles.PrimaryFlat, 0.95),
    ]

    for m_key, l_st, c_st, rad in method_styles:
        tr = load_adaptive_trajectory(prompt_id, m_key)
        pts = tr["client_output"]
        if len(pts) >= 2:
            coords = [(px(float(p["t_ms"])), py(float(p["chars"]))) for p in pts]
            for i in range(len(coords) - 1):
                line(coords[i], coords[i + 1], style=l_st)
            for cx_p, cy_p in coords:
                circle((cx_p, cy_p), radius=rad, style=c_st)

    return px, py


# Left Panel: T2_1 (Standard Procedure, thinking=false)
px_l, py_l = draw_multi_trajectory_panel(
    x0=15.0,
    y0=18.5,
    pw=63.0,
    ph=46.0,
    prompt_id="T2_1",
    title_s="(1) Tier 2 Procedure (T2_1: Power Discharge Reset)",
    sub_s="thinking=false: Completes in 1 API Call (Direct Stream)",
    max_t=14000.0,
    max_c=1600.0,
    x_ticks=[0, 3000, 6000, 9000, 12000],
    y_ticks=[0, 400, 800, 1200, 1600],
)

# Callouts inside Left Panel
rectangle((39.5, 55.5), width=42.0, height=10.0, style=Styles.PrimaryNeutral.patch(shape_r=0.9))
text((39.5, 57.8), "★ Pattern A: Starts at 2,243 ms", style=Styles.PrimaryBold.patch(text_size=9.6))
text((39.5, 53.4), "Finishes first at 4,629 ms!", style=Styles.DarkBold.patch(text_size=9.6))
line((34.0, 50.5), (px_l(4629.0), py_l(482.0)), arrow_head="->", style=Styles.PrimaryBold.patch(line_width=1.5))

rectangle((55.5, 29.0), width=41.0, height=9.4, style=Styles.WhiteFlat.patch(shape_r=0.9, line_width=0.7))
text((55.5, 31.2), "Base Low: Blank until 5,901 ms", style=Styles.WarningBold.patch(text_size=9.5))
text((55.5, 26.8), "Wastes 423 reasoning tokens", style=Styles.Dark.patch(text_size=9.4))
line((px_l(5901.0), 24.3), (px_l(5901.0), py_l(40.0)), arrow_head="->", style=Styles.WarningBold.patch(line_width=1.4))

# Right Panel: T3_1 (Complex Math, thinking=true)
px_r, py_r = draw_multi_trajectory_panel(
    x0=98.0,
    y0=18.5,
    pw=63.0,
    ph=46.0,
    prompt_id="T3_1",
    title_s="(2) Tier 3 Complex Math (T3_1: 3-Yr PC Repair vs. Buy)",
    sub_s="thinking=true: Bridge Msg (2,120ms) + Parallel Stage 2 (low)",
    max_t=22000.0,
    max_c=1600.0,
    x_ticks=[0, 5000, 10000, 15000, 20000],
    y_ticks=[0, 400, 800, 1200, 1600],
)

# Callouts inside Right Panel
rectangle((124.5, 55.5), width=48.5, height=10.6, style=Styles.PrimaryNeutral.patch(shape_r=0.9))
text((124.5, 58.0), "(1) Bridge at 2,120 ms + Parallel Stage 2", style=Styles.PrimaryBold.patch(text_size=9.5))
text((124.5, 53.2), "Eliminates 6.8s freeze vs Base Low!", style=Styles.DarkBold.patch(text_size=9.5))
line((108.0, 50.2), (px_r(2120.0), py_r(60.0)), arrow_head="->", style=Styles.PrimaryBold.patch(line_width=1.5))

rectangle((137.0, 29.5), width=44.0, height=9.6, style=Styles.WhiteFlat.patch(shape_r=0.9, line_width=0.7))
text((137.0, 31.8), "(2) Stage 2 Chains at 10,948 ms (859 tok)", style=Styles.PrimaryBold.patch(text_size=9.5))
text((137.0, 27.3), "Verified 26,200 yen finishes at 16,650 ms", style=Styles.Dark.patch(text_size=9.4))
line((px_r(10948.0), 24.7), (px_r(10948.0), py_r(90.0)), arrow_head="->", style=Styles.PrimaryBold.patch(line_width=1.5))

# Bottom summary banner
rectangle((86.0, 6.0), width=160.0, height=6.4, style=Styles.PrimaryNeutral.patch(shape_r=1.2))
phosphor.sparkle((10.5, 6.0), width=3.2, style=Styles.PrimaryBold)
text(
    (14.0, 6.0),
    "Takeaway: Pattern A finishes T2_1 first (4,629 ms) and hides 6.8s of T3_1 wait behind a 2,120 ms bridge message.",
    style=Styles.DarkBold.patch(text_size=10.0, halign="left"),
)

save()
```

### Two Key Trajectory Findings from Figure 4-4

1. **Left Panel (`T2_1`: Standard Procedure, `thinking=false`) — Single-Call Direct Stream & Fastest Completion**:
   - Pattern A (thick blue curve) resolves `"thinking": false` at `2,068 ms`, begins streaming `"response"` deltas at **`2,243 ms`**, and completes at **`4,629 ms`**, finishing first among all five methods.
   - Because the Pydantic schema guides the model to produce a well-structured, concise 482-character troubleshooting guide, Pattern A finishes **`1,285 ms` faster than Pattern C (`5,914 ms`)** and **`2,981 ms` faster than Base 0 (`7,610 ms`)**.
2. **Right Panel (`T3_1`: Complex Math, `thinking=true`) — Eliminating `6.8 s` of Blank-Screen Freeze via Parallel Stage-2 Chaining**:
   - Fixed `base_low` (yellow curve) leaves the user staring at **0 characters** for **`8,950 ms`**, while sequential Pattern B (red curve) freezes for **`11,226 ms`**.
   - Pattern A (thick blue curve) resolves `"thinking": true` at **`2,078 ms`**, immediately launches Stage 2 (`thinking=low`) in the background via `asyncio.create_task()`, and streams the 59-character bridge message at **`2,120 ms`**—**eliminating `6,830 ms` (`6.8 s`) of blank-screen freeze** compared to `base_low`. While the user reads the bridge message, Stage 2 completes `859` internal reasoning tokens in parallel and seamlessly resumes streaming the verified calculation at **`10,948 ms`**, finishing at **`16,650 ms`** with 100% mathematical consistency (`26,200 yen` repair advantage).

---

## 4.4 Google AI Studio Implementation & Comprehensive Scorecard

### Clean Google AI Studio (`google-genai`) Implementation of Pattern A

Because `chunk.parsed` remains `None` on intermediate chunks during `generate_content_stream`, Pattern A uses `pydantic_core.from_json(..., allow_partial="trailing-strings")` to safely extract the boolean `thinking` flag and escape-decoded `response` deltas on every chunk (`src/gemini_evaluation/adaptive_thinking.py`). In production, instantiate `genai.Client` once at application startup and pass it into `stream_adaptive_router`, using a `finally` block to ensure any background Stage-2 task is cancelled if the caller disconnects early:

```python
import asyncio
from collections.abc import AsyncIterator
from contextlib import aclosing
from typing import Any

from google import genai
from google.genai import types
from pydantic import BaseModel
from pydantic_core import from_json

MODEL = "gemini-3.8-flash"


class AdaptiveStreamResponse(BaseModel):
    """Minimal 2-field Pydantic streaming schema for Pattern A."""

    thinking: bool  # Field 1: Resolved prior to first visible chunk to trigger routing
    response: str   # Field 2: Full answer if thinking=False, or 1-sentence bridge if True


def parse_partial_json_dict(raw_buf: str) -> dict[str, Any] | None:
    """Incrementally parse incomplete streaming JSON safely via Rust pydantic_core."""
    if not raw_buf:
        return None
    try:
        parsed = from_json(raw_buf.encode("utf-8"), allow_partial="trailing-strings")
        return parsed if isinstance(parsed, dict) else None
    except ValueError:
        return None


async def stream_adaptive_router(
    client: genai.Client,
    prompt: str,
) -> AsyncIterator[str]:
    """Pattern A: 2-Field Integrated Pydantic Stream + Parallel Stage-2 Chaining."""
    stage2_queue: asyncio.Queue[str | BaseException | None] = asyncio.Queue()
    stage2_task: asyncio.Task[None] | None = None

    async def _produce_stage2() -> None:
        try:
            st2 = await client.aio.models.generate_content_stream(
                model=MODEL,
                contents=prompt,
                config=types.GenerateContentConfig(
                    system_instruction=(
                        "The opening greeting and bridge message have already been shown. "
                        "Do not repeat the greeting; immediately present the calculation steps and conclusion."
                    ),
                    thinking_config=types.ThinkingConfig(
                        thinking_level=types.ThinkingLevel.LOW,
                    ),
                    temperature=0.2,
                ),
            )
            async with aclosing(st2):
                async for ch2 in st2:
                    if ch2.text:
                        await stage2_queue.put(ch2.text)
            await stage2_queue.put(None)
        except BaseException as exc:
            await stage2_queue.put(exc)

    json_buf = ""
    emitted_len = 0
    decided_thinking: bool | None = None

    try:
        st1 = await client.aio.models.generate_content_stream(
            model=MODEL,
            contents=prompt,
            config=types.GenerateContentConfig(
                system_instruction=(
                    "For greetings or standard procedures, set thinking: false and output the full answer in response. "
                    "For multi-condition financial math, set thinking: true and output only a 1-sentence bridge message."
                ),
                response_mime_type="application/json",
                response_schema=AdaptiveStreamResponse,
                thinking_config=types.ThinkingConfig(thinking_budget=0),
                temperature=0.2,
            ),
        )
        async with aclosing(st1):
            async for ch1 in st1:
                if not ch1.text:
                    continue
                json_buf += ch1.text
                partial = parse_partial_json_dict(json_buf)
                if partial is None:
                    continue

                # 1) Inspect thinking flag once resolved; launch Stage 2 in parallel if True
                if decided_thinking is None and isinstance(partial.get("thinking"), bool):
                    decided_thinking = partial["thinking"]
                    if decided_thinking:
                        stage2_task = asyncio.create_task(_produce_stage2())

                # 2) Yield newly decoded response slice immediately
                resp_so_far = partial.get("response")
                if isinstance(resp_so_far, str) and len(resp_so_far) > emitted_len:
                    delta = resp_so_far[emitted_len:]
                    emitted_len = len(resp_so_far)
                    yield delta

        # 3) Validate complete JSON payload at EOF
        final_obj = AdaptiveStreamResponse.model_validate_json(json_buf)
        if len(final_obj.response) > emitted_len:
            yield final_obj.response[emitted_len:]

        # 4) Seamlessly chain parallel Stage-2 stream when thinking=True
        if decided_thinking and stage2_task is not None:
            yield "\n\n"
            while True:
                item = await stage2_queue.get()
                if item is None:
                    break
                if isinstance(item, BaseException):
                    raise item
                yield item
            await stage2_task
    finally:
        # Ensure background Stage-2 task is cancelled if caller breaks early or an error occurs
        if stage2_task is not None and not stage2_task.done():
            stage2_task.cancel()
```

> **Schema Cold-vs-Warm Compilation & Field Ordering Best Practices**: As detailed in Section 2.3 (`load_schema_experiment()`, `src/gemini_evaluation/adaptive_thinking_log.json`), the first invocation of a new JSON schema (`RichStreamResponse #1 (Cold)`: `3,337.3 ms` TTFT, `2,954.3 ms` `flag_decided_ms`) incurs a one-time finite-state-machine (FSM) grammar compilation pass. Subsequent warm calls (`Warm #2–#4`) hit the server's grammar cache, dropping 6-field average TTFT by **`-15.0%` to `2,837.1 ms` (`2,504.4–3,259.3 ms`)**—within **`+92.7 ms` (`+3.4%`)** of the 2-field warm average (`2,744.4 ms`). Expanding the schema to 6 fields (`RichStreamResponse`) maintains an average warm `flag_decided_ms` of `2,419.4 ms` (`2,157.1–2,780.6 ms`) provided `thinking: bool` is placed first and variable-length lists (`suggested_followups: list[str]`) are placed **after** `response: str`. Running a single dummy warmup call at application startup eliminates cold-start latency completely.

### Comprehensive Evaluation Scorecard across All 5 Methods

| Evaluation Criterion | ★ Pattern A (`pat_a_pydantic_2f`)<br>2-Field Integrated Pydantic | Pattern C (`pat_c_tag`)<br>`[DIRECT]` / `[THINK]` Tag | Pattern B (`pat_b_pydantic_1f`)<br>1-Field Sequential Router | Base Low (`base_low`)<br>Fixed `thinking=low` | Base 0 (`base_0`)<br>Fixed `thinking=0` |
| :--- | :---: | :---: | :---: | :---: | :---: |
| **All-9 Prompts Mean TTFT** | **`2,340 ms` (PASS `< 2.5s`)** | **`1,879 ms` (PASS `< 2.5s`)** | `6,177 ms` (FAIL `> 3.5s`) | `6,290 ms` (FAIL `> 3.5s`) | `1,879 ms` (PASS `< 2.5s`) |
| **Tier 1–2 Mean TTFT / Total** | **`2,354 ms` / `4,808 ms` (Fastest Total)** | `1,920 ms` / `5,030 ms` | `3,522 ms` / `7,760 ms` | `4,791 ms` / `8,189 ms` | `1,887 ms` / `5,371 ms` |
| **Tier 3 Mean TTFT (Max)** | **`2,314 ms` (`2,456 ms`)** | `1,795 ms` (`1,939 ms`) | `11,488 ms` (`12,590 ms`) | `9,289 ms` (`12,155 ms`) | `1,863 ms` (`2,235 ms`) |
| **Routing Classification Accuracy** | **`9 / 9` (`100%`)** | **`9 / 9` (`100%`)** | **`9 / 9` (`100%`)** | N/A (Always On) | N/A (Always Off) |
| **Tier 3 Math Verification** | **`3 / 3` (`100%` Pre-Verified)** | **`3 / 3` (`100%` Pre-Verified)** | **`3 / 3` (`100%` Pre-Verified)** | **`3 / 3` (`100%` Pre-Verified)** | **Autoregressive Risk (Unverified)** |
| **API Calls per Turn (T1–2 / T3)** | **`1.0` / `2.0`** | `1.0` / `2.0` | `2.0` / `2.0` | `1.0` / `1.0` | `1.0` / `1.0` |
| **Decoder Type Safety & Extensibility** | **PASS (Constrained Decoding)** | FAIL (Tag leak & history drift risk) | Partial (Router only) | N/A (Plain text) | N/A (Plain text) |
| **Final Production Verdict** | **★ Recommended Standard** | Reject (Unify on A for type safety) | Reject (2-RTT sequential lag) | Not Recommended (`12.2s` freeze) | Reject (Tier 3 math risk) |

