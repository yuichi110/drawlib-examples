# 4. Adaptive Thinking Router Pattern

Chapter 3 established a fundamental dilemma in `ThinkingConfig` level selection: fixing a low thinking level (`low`) yields fast initial responsiveness (`TTFT`) but risks insufficient or zero internal scratchpad verification on complex multi-step calculations (Tier 3), whereas fixing a high thinking level (`high`) achieves deep pre-verification at the cost of adding unnecessary reasoning latency to routine turns (Tiers 1–2) and freezing the UI for over 10–16 seconds.

In this chapter, we introduce the **Adaptive Thinking Router Pattern** (`src/gemini_evaluation/adaptive_thinking.py`) to resolve this trade-off. First, in **Section 4.1**, based on the 5-model cross-matrix benchmark from Chapter 3, we organize the candidate models and `thinking_level` options suitable for **Stage 1 (Fast Decision / Immediate Response & Routing Layer)** and **Stage 2 (Thinking Decision / Deep Reasoning & Verification Layer)**. Next, in **Sections 4.2–4.5**, we evaluate the standard pairing of **`gemini-3.8-flash` `low` (Stage 1) + `high` (Stage 2)** across 3 candidate architectures (Patterns A, B, and C) and 2 fixed baselines (Base Low and Base High) over a 45-run empirical benchmark (9 prompts × 5 methods), proving that **Pattern A (2-Field Integrated Pydantic Schema `{thinking: bool, response: str}` + Parallel Stage-2 Chaining)** is the optimal production architecture.

```drawlib align=center code=fold width=100% file=ch04_adaptive_architectures_hero.png caption="Figure 4-1: Side-by-Side Architecture Sequence Comparison of Candidate Adaptive Thinking Routers (Pattern A: 2-Field Integrated Pydantic, Pattern B: 1-Field Sequential Router, Pattern C: Tag Prefix) on gemini-3.8-flash (Stage 1 low -> Stage 2 high)"
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
    "Adaptive Thinking Router Architectures (Patterns A, B, C): Sequence & Latency (3.8-flash: low -> high)",
    style=Styles.DarkBold.patch(text_size=11.5),
)

# Top UX Target Bar
rectangle((86.0, 79.2), width=160.0, height=8.8, style=Styles.Neutral.patch(shape_r=1.2))
phosphor.gauge((10.5, 81.0), width=3.2, style=Styles.PrimaryBold)
text(
    (14.0, 81.0),
    "UX Latency Targets: (1) Eliminate 10.5–16.5s Fixed-High Freezes / (2) 100% JSON Schema Safety & Math Verification",
    style=Styles.PrimaryBold.patch(text_size=9.6, halign="left"),
)
text(
    (14.0, 77.0),
    "Stage 1 (thinking=low) streams direct answers or a 1-sentence bridge while Stage 2 (thinking=high) runs in parallel",
    style=Styles.Dark.patch(text_size=9.5, halign="left"),
)

# 3 Architecture Columns
cols = [
    (
        33.0,
        "★ Pattern A [Recommended]",
        "2-Field Pydantic + Parallel Stage 2",
        "Stage 1: thinking=low + JSON Schema",
        "Streams {thinking: bool, response: str}",
        "false: 1 API Call Direct Stream",
        "T1–2 Mean TTFT 2,517 / Total 4,352 ms",
        "true: Bridge (~2.1s) + Parallel Stage 2",
        "create_task hides high reasoning",
        [
            "• All-9 Mean TTFT: 2,388 ms (-81% vs high)",
            "• Eliminates up to 16.5s Tier 3 freeze",
            "• Faster than C + Schema-Safe [PASS]",
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
        "generate_content (low) returns {thinking}",
        "Stage 2: Sequential Stream API Call",
        "Always 2 RTTs (T1–2 TTFT 4,658 ms)",
        "true: Router RTT + high Wait Stack Up",
        "Tier 3 Mean TTFT 18,618 ms (Max 24.2s)",
        [
            "• All-9 Mean TTFT: 9,311 ms (Seq lag)",
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
        "Stage 1: thinking=low Plain Stream",
        "Prompt prefix tag without JSON schema",
        "[DIRECT]: Strip Tag & Stream Body",
        "T1–2 TTFT 2,565 ms / No schema check",
        "[THINK]: Bridge (~3.7s) + Parallel Stage 2",
        "Plain Stage 1 thinks up to 445 tok",
        [
            "• All-9 Mean TTFT: 2,930 ms (+0.54s vs A)",
            "• Risk of tag leak & multi-turn drift",
            "• Verdict: Pattern A is faster & safer [FAIL]",
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
    text((cx + 1.5, 67.8), title_s, style=hdr_st.patch(text_size=10.2))
    text((cx, 64.0), sub_s, style=sub_st.patch(text_size=9.5))

    # Step Box 1
    rectangle((cx, 56.5), width=48.2, height=8.6, style=Styles.WhiteFlat.patch(shape_r=1.0))
    text((cx, 58.4), s1_t, style=Styles.PrimaryBold.patch(text_size=9.6))
    text((cx, 54.6), s1_b, style=Styles.Dark.patch(text_size=9.4))

    arr_st = Styles.WhiteBold.patch(line_width=1.8) if card_st == Styles.PrimaryFlat else Styles.DarkBold.patch(line_width=1.8)
    line((cx, 52.2), (cx, 49.4), arrow_head="->", style=arr_st)

    # Step Box 2
    rectangle((cx, 45.0), width=48.2, height=8.6, style=mid_st.patch(shape_r=1.0))
    text((cx, 46.9), s2_t, style=Styles.DarkBold.patch(text_size=9.6))
    text((cx, 43.1), s2_b, style=Styles.Dark.patch(text_size=9.4))

    line((cx, 40.7), (cx, 37.9), arrow_head="->", style=arr_st)

    # Step Box 3
    rectangle((cx, 33.5), width=48.2, height=8.6, style=Styles.WhiteFlat.patch(shape_r=1.0))
    text((cx, 35.4), s3_t, style=Styles.SecondaryBold.patch(text_size=9.6))
    text((cx, 31.6), s3_b, style=Styles.Dark.patch(text_size=9.4))

    b_style = (
        Styles.White.patch(text_size=9.5, halign="left")
        if card_st == Styles.PrimaryFlat
        else Styles.Dark.patch(text_size=9.5, halign="left")
    )
    for idx, b_line in enumerate(bullets):
        text((cx - 22.8, 25.5 - idx * 4.2), b_line, style=b_style)

# Bottom conclusion bar
rectangle((86.0, 6.2), width=160.0, height=6.4, style=Styles.PrimaryNeutral.patch(shape_r=1.2))
phosphor.shield_check((10.5, 6.2), width=3.2, style=Styles.PrimaryBold)
text(
    (14.0, 6.2),
    "Conclusion: Pattern A hits 2,388 ms mean TTFT (-81.4% vs Base High), beating Pattern C (2,930 ms) with full schema safety.",
    style=Styles.DarkBold.patch(text_size=9.5, halign="left"),
)

save()
```

---

## 4.1 Candidate Model & `thinking_level` Matrix for Stage 1 (Fast Decision) and Stage 2 (Thinking Decision)

The Adaptive Thinking Router consists of two stages: **Stage 1 (Fast Decision / Immediate Response & Routing Layer)**, which immediately streams either a complete direct answer or a 1-sentence bridge acknowledgment, and **Stage 2 (Thinking Decision / Deep Reasoning & Pre-Verification Layer)**, which is launched in parallel in the background only when multi-step reasoning or complex calculation is required. Based on the 17-configuration × 10-query (170-run) empirical benchmark in Chapter 3 (Section 3.5), Tables 4-1A and 4-1B organize the candidate models and `thinking_level` settings for each stage.

### 1. Stage 1 Candidates (Fast Decision / Immediate Response & Routing Layer — Table 4-1A)

Stage 1 requires configurations that initiate streaming within **`0.7–2.6 s` on simple queries (`≤ 3.9 s` on complex queries)** without stalling the UI on extended internal reasoning.

| Candidate Group | Model (`model`) | Target `thinking_level` | Simple 5 Avg TTFT / Total | Complex 5 Avg TTFT / Total | Stage 1 Characteristics & Selection Criteria |
| :--- | :--- | :---: | ---: | ---: | :--- |
| **① Ultra-Fast Lightweight Tier** | **`gemini-3.5-flash-lite`** | **All levels**<br>(`minimal` / `low` / `medium` / `high`) | **`0.67–2.16 s`** /<br>`1.37–2.57 s` | **`0.68–3.49 s`** /<br>`2.06–4.84 s` | **Best choice for even faster initial response (TTFT)**. In particular, **`minimal` / `low` (~0.7s TTFT)** operate at `ThTok=0` for sub-second response. Ultra-fast token decoding keeps even `medium` / `high` faster than `3.8-flash [low]`. |
| **② Standard Balanced Tier** | **`gemini-3.8-flash`** | **`low`**<br>*(+ legacy `budget=0`)* | **`2.46 s`** / `5.04 s` | **`2.59 s`** / `7.97 s` | **Standard baseline evaluated in this chapter**. `low` keeps internal thought tokens minimal (`62–105 tok` avg) and pairs with Pydantic schemas for a stable ~2.2–2.5s initial response and high routine answer quality. |
| **③ High-Quality Gemini 4 Fast Tier** | **`gemini-4-hydrogen`** | **`low`** | **`2.60 s`** / **`3.37 s`** | **`3.91 s`** / **`5.90 s`** | Always-thinking (`184–658 tok`), but high decoding throughput finishes total generation faster than `3.8-flash [low]`. Strong candidate when Gemini 4 generation quality is desired even on Stage 1 direct answers. |

---

### 2. Stage 2 Candidates (Thinking Decision / Deep Reasoning & Pre-Verification Layer — Table 4-1B)

Stage 2 executes in parallel while Stage 1 streams its 1-sentence bridge message. The candidates are **`gemini-3.8-flash` (`medium` / `high`)** and **all `Gemini 4` configurations except `4-hydrogen [low]`**. Based on the internal thought token (`ThTok`) and latency characteristics measured in Chapter 3, these candidates divide naturally into **three operational categories**:

| Stage 2 Category | Model (`model`) | Target `thinking_level` | Complex 5 Avg TTFT / Total | Complex 5 Avg `ThTok` | Stage 2 Suitability & System Requirements |
| :--- | :--- | :---: | :---: | :---: | :--- |
| **A. Interactive Stream Chaining (Standard)**<br>*(Chains smoothly in 5–18s right after bridge)* | **`gemini-3.8-flash`** | **`medium` / `high`** | `6.16–13.43 s` /<br>`10.71–18.95 s` | `605–1,549 tok` | **Evaluated in this chapter (`high`)**. Running `600–1,500 tok` of pre-verification behind Stage 1's ~2s bridge display and user reading time completely hides perceived UI freezes. |
| **A. Interactive Stream Chaining (Recommended)**<br>*(Deeper reasoning with faster completion)* | **`gemini-4-hydrogen`** | **`medium` / `high` / `xhigh`** | `6.51–13.02 s` /<br>**`9.00–15.43 s`** | **`954–2,248 tok`** | **Top recommendation for deeper thinking in interactive chat systems**. Invests more thought tokens than `3.8-flash [high]` (up to `2,248 tok` avg at `xhigh`) while finishing full responses in `9–15 s`. |
| **B. Frontier Direct Base-Intelligence Tier**<br>*(Direct reasoning with `ThTok=0`)* | **`gemini-4-argon`**<br>**`gemini-4-carbon`** | **`low` / `medium`** *(Argon)*<br>**`low`** *(Carbon)* | `4.93–10.94 s` /<br>`12.49–19.40 s` | **`0.0 tok`** | Empirically operate with `thoughts_token_count = 0` (no internal scratchpad), answering directly via frontier model parameter scale. Completes in `12–19 s` and is viable as a Stage 2 worker. |
| **C. Complex Enterprise & Deep Reasoning Tier**<br>*(Initial response 13–34s / Total 19–40s)* | **`gemini-4-argon`**<br>**`gemini-4-carbon`** | **`high`** *(Argon)*<br>**`medium` / `high`** *(Carbon)* | `13.45–34.36 s` /<br>`19.22–40.21 s` | **`713–2,795 tok`**<br>*(Max 4,360 tok)* | **For complex business & enterprise workflows**. A ~30-second initial wait should generally be avoided in consumer chat, but for complex enterprise systems requiring strict multi-step audit, legal/financial analysis, or architecture verification, this is the most powerful Stage 2 tier. |

> **💡 Benchmark Configuration in This Chapter & Production Tuning Guidance**:
> Because testing the full Cartesian product of all Stage 1 × Stage 2 combinations would be prohibitively large, the empirical benchmark in Sections 4.2–4.5 evaluates the representative single-model pairing of **`gemini-3.8-flash` `low` (Stage 1: Fast Decision) + `high` (Stage 2: Thinking Decision)** to compare the routing architectures.
> When deploying **Pattern A** in production, we recommend tuning the Stage 1 and Stage 2 model assignments according to your system's latency and reasoning requirements:
> - **To achieve even faster initial response (TTFT)**: Replace Stage 1 with **`gemini-3.5-flash-lite` (`minimal` or `low`)**, reducing time-to-first-token from ~2.4 seconds down to **~0.7 seconds**.
> - **To achieve deeper and more accurate Thinking**: Upgrade Stage 2 to the **`Gemini 4` series**. For interactive chat systems, **`gemini-4-hydrogen` (`medium` / `high` / `xhigh`)** provides the best balance of deep thinking and fast completion (`9–15 s`), whereas for complex business/enterprise systems that can tolerate ~30 seconds of deep reasoning behind a bridge message, **`gemini-4-argon [high]`** or **`gemini-4-carbon [medium / high]`** is recommended.

---

## 4.2 UX Latency Targets & 3 Candidate Architectures (Patterns A, B, C)

### Cognitive UX Response-Time Thresholds & Design Targets

Our engineering targets for the Adaptive Thinking Router are:
1. **Eliminate the `10.5–16.5 s` blank-screen freezes caused by fixed `thinking=high` across all query tiers, keeping initial TTFT at the `thinking=low` baseline (~2.1–2.8 seconds)**.
2. **Enforce 100% decoder-level JSON schema safety while chaining Stage 2 (`thinking=high`, `674–1,591 tok` of pre-verification) in parallel exclusively on complex multi-step calculations (Tier 3)**.

### Architectural Comparison of Patterns A, B, and C

In `src/gemini_evaluation/adaptive_thinking.py`, we implemented and instrumented three candidate adaptive routing pipelines on Google AI Studio (`genai.Client(api_key=GEMINI_KEY)` with `gemini-3.8-flash`, assigning `thinking_level=LOW` to Stage 1 and `thinking_level=HIGH` to Stage 2), illustrated in Figure 4-1:

1. **Pattern A (Recommended — 2-Field Integrated Pydantic `{thinking: bool, response: str}` + Parallel Stage-2 Chaining)**
   - **Stage 1** initiates a single `generate_content_stream` call with `thinking_level=LOW` and `response_schema=AdaptiveStreamResponse`. Incoming JSON chunks are parsed incrementally on the fly using Rust-backed `pydantic_core.from_json(..., allow_partial="trailing-strings")`.
   - **`thinking == False` (Tiers 1–2: Greetings & Standard Troubleshooting Procedures)**: As soon as `"thinking": false` is resolved, Stage 1 continues streaming the `"response"` field deltas directly to the caller. **The entire turn completes in 1 API call**, achieving **`2,517 ms` mean TTFT** and **`4,352 ms` mean total completion** on Tiers 1–2.
   - **`thinking == True` (Tier 3: Complex Multi-Step Math)**: The instant `"thinking": true` is parsed (`1,608–2,411 ms`), Pattern A spawns **Stage 2 (`thinking=high` plain-text stream) in parallel** via `asyncio.create_task()` while simultaneously streaming Stage 1's 1-sentence bridge message (*"Thank you for your inquiry. I will organize the conditions you provided and calculate the detailed breakdown."*). While the user reads the bridge sentence, Stage 2 completes its deep internal reasoning scratchpad (`674–1,508 tokens`) in the background and seamlessly chains the verified calculation stream.
2. **Pattern B (1-Field Sequential Router `{thinking: bool}` + Stage-2 Stream)**
   - Avoids incremental JSON parsing by first executing a blocking `generate_content` call (`thinking=low`) with `ThinkingDecision(thinking: bool)` and then launching a second `generate_content_stream` call (`thinking=low` or `thinking=high`).
   - Because **every prompt requires 2 sequential API round-trips (`calls=2.0`)**, routine Tier 1–2 TTFT degrades to **`4,658 ms`**, and Tier 3 TTFT balloons to **`18,618 ms` (max `24,231 ms`)** (overall mean TTFT **`9,311 ms`**).
3. **Pattern C (Tag Prefix `[DIRECT]` / `[THINK]`)**
   - Uses prompt instructions to emit a plain-text `[DIRECT]` or `[THINK]` prefix tag (`Stage 1 thinking=low`) without a JSON schema.
   - Although one might expect plain text without a JSON schema to be faster, empirical testing proves that **Pattern A (`2,388 ms` overall mean TTFT, `2,131 ms` Tier 3 mean) is `542 ms` faster overall (`1.53 s` faster on Tier 3) than Pattern C (`2,930 ms` overall mean TTFT, `3,659 ms` Tier 3 mean)**. Because Pattern A uses constrained decoding (`response_schema`), the FSM forces the model to commit immediately to `{"thinking": true` with only `0–83 tok` of Stage 1 thought, whereas unconstrained plain-text Pattern C spends up to `445 tok` thinking under `thinking=low` before emitting `[THINK]`. Furthermore, Pattern C suffers from raw tag leakage risks (`[direct]`, `**[THINK]**`) and multi-turn tag omission drift.

---

## 4.3 45-Run Empirical Benchmark (9 Prompts × 5 Methods, `low` → `high`)

Using `src/gemini_evaluation/benchmark_adaptive_thinking.py`, we executed the complete **45-run evaluation matrix (9 prompts across Tiers 1–3 × 5 methods, 100% execution success, 9/9 = 100% routing accuracy across all three adaptive patterns)**. Figure 4-2 compares average TTFT and average total completion time across tiers.

```drawlib align=center code=fold width=100% file=ch04_tier_latency_barchart.png caption="Figure 4-2: Average TTFT (Left) and Average Total Completion Time (Right) by Complexity Tier (Tier 1, Tier 2, Tier 3, All-9 Mean) across All 5 Methods (gemini-3.8-flash: low / high)"
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
    "45-Run Benchmark (3.8-flash low -> high): Mean TTFT (Left) & Mean Total Time (Right) by Tier",
    style=Styles.DarkBold.patch(text_size=11.5),
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
    (10.0, Styles.PrimaryFlat, "★ Pattern A: 2-Field {thinking, response} (low -> high) [Recommended]"),
    (98.0, Styles.TealFlat, "Pattern C: Tag Prefix [DIRECT]/[THINK] (low -> high)"),
]
for lx, st, ltxt in leg_row1:
    rectangle((lx, 99.3), width=3.6, height=2.0, style=st.patch(shape_r=0.3))
    text((lx + 2.8, 99.3), ltxt, style=Styles.DarkBold.patch(text_size=10.0, halign="left"))

leg_row2 = [
    (10.0, Styles.SuccessFlat, "Base Low: Fixed thinking=low (0 tok on T3)"),
    (72.0, Styles.WarningFlat, "Base High: Fixed thinking=high"),
    (114.0, Styles.DangerFlat, "Pattern B: 1-Field Seq (low -> high)"),
]
for lx, st, ltxt in leg_row2:
    rectangle((lx, 95.1), width=3.6, height=2.0, style=st.patch(shape_r=0.3))
    text((lx + 2.8, 95.1), ltxt, style=Styles.Dark.patch(text_size=10.0, halign="left"))

# Left Panel: Average TTFT (ms)
rectangle((45.5, 52.0), width=79.0, height=76.0, style=Styles.WhiteFlat.patch(shape_r=1.4, line_width=0.8))
text((45.5, 86.8), "1. Time to First Token: Mean TTFT (ms)", style=Styles.PrimaryBold.patch(text_size=11.0))

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
chart_ttft.configure_x_axis(min_value=0, max_value=20000, tick_step=5000, format="{:,.0f}")
chart_ttft.add_series("pat_a", calc_means("pat_a_pydantic_2f", "ttft_ms"), style=Styles.PrimaryFlat)
chart_ttft.add_series("pat_c", calc_means("pat_c_tag", "ttft_ms"), style=Styles.TealFlat)
chart_ttft.add_series("base_low", calc_means("base_low", "ttft_ms"), style=Styles.SuccessFlat)
chart_ttft.add_series("base_high", calc_means("base_high", "ttft_ms"), style=Styles.WarningFlat)
chart_ttft.add_series("pat_b", calc_means("pat_b_pydantic_1f", "ttft_ms"), style=Styles.DangerFlat)
chart_ttft.draw(xy=(24.5, 17.5))

# Right Panel: Average Total Completion Time (ms)
rectangle((126.5, 52.0), width=79.0, height=76.0, style=Styles.WhiteFlat.patch(shape_r=1.4, line_width=0.8))
text((126.5, 86.8), "2. Stream Completion: Mean Total Time (ms)", style=Styles.DarkBold.patch(text_size=11.0))

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
chart_tot.configure_x_axis(min_value=0, max_value=30000, tick_step=10000, format="{:,.0f}")
chart_tot.add_series("pat_a", calc_means("pat_a_pydantic_2f", "total_ms"), style=Styles.PrimaryFlat)
chart_tot.add_series("pat_c", calc_means("pat_c_tag", "total_ms"), style=Styles.TealFlat)
chart_tot.add_series("base_low", calc_means("base_low", "total_ms"), style=Styles.SuccessFlat)
chart_tot.add_series("base_high", calc_means("base_high", "total_ms"), style=Styles.WarningFlat)
chart_tot.add_series("pat_b", calc_means("pat_b_pydantic_1f", "total_ms"), style=Styles.DangerFlat)
chart_tot.draw(xy=(105.5, 17.5))

# Bottom summary banner
rectangle((86.0, 6.2), width=160.0, height=6.4, style=Styles.PrimaryNeutral.patch(shape_r=1.2))
phosphor.check_circle((10.5, 6.2), width=3.2, style=Styles.PrimaryBold)
text(
    (14.0, 6.2),
    "Key Takeaway: Pattern A maintains ~2.4s TTFT across all tiers, eliminating the 16.5s Base High and 24.2s Pattern B freezes.",
    style=Styles.DarkBold.patch(text_size=9.6, halign="left"),
)

save()
```

### All 45 Runs TTFT × Total Scatter Distribution & UX Threshold Verification

To inspect run-by-run variance across all 45 executions rather than averages alone, Figure 4-3 plots every execution on the 2D plane of `ttft_ms` (X-axis) × `total_ms` (Y-axis).

```drawlib align=center code=fold width=100% file=ch04_all45_runs_scatter.png caption="Figure 4-3: TTFT vs. Total Completion Time Scatter Distribution Across All 45 Runs (9 Prompts × 5 Methods, gemini-3.8-flash low -> high)"
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
    "All 45 Runs (9 Prompts × 5 Methods: low -> high) TTFT × Total Distribution & Fast Response Zone",
    style=Styles.DarkBold.patch(text_size=11.8),
)

runs = load_adaptive_runs()
series_pts: dict[str, list[tuple[float, float]]] = {
    "pat_a_pydantic_2f": [],
    "pat_c_tag": [],
    "base_low": [],
    "base_high": [],
    "pat_b_pydantic_1f": [],
}
for r in runs:
    series_pts[r["method_key"]].append((float(r["ttft_ms"]), float(r["total_ms"])))

# Left Chart Container
rectangle((62.0, 47.0), width=112.0, height=69.0, style=Styles.WhiteFlat.patch(shape_r=1.4, line_width=0.8))

# 2-row custom legend at top of chart container
rectangle((62.0, 75.8), width=107.0, height=8.8, style=Styles.Neutral.patch(shape_r=1.0))
leg1 = [
    (11.5, Styles.PrimaryFlat, "★ Pattern A: 2-Field (low->high)"),
    (64.5, Styles.TealFlat, "Pattern C: Tag Prefix (low->high)"),
]
for lx, st, ltxt in leg1:
    rectangle((lx, 77.8), width=3.2, height=1.8, style=st.patch(shape_r=0.3))
    text((lx + 2.4, 77.8), ltxt, style=Styles.DarkBold.patch(text_size=10.0, halign="left"))

leg2 = [
    (11.5, Styles.SuccessFlat, "Base Low: Fixed low"),
    (46.5, Styles.WarningFlat, "Base High: Fixed high"),
    (83.5, Styles.DangerFlat, "Pattern B: 1-Field Seq"),
]
for lx, st, ltxt in leg2:
    rectangle((lx, 73.8), width=3.2, height=1.8, style=st.patch(shape_r=0.3))
    text((lx + 2.4, 73.8), ltxt, style=Styles.Dark.patch(text_size=10.0, halign="left"))

# Highlight UX target zone inside plot area
PX0 = 24.8
PW_AX = 82.5
PY0 = 25.0
PH_AX = 40.2

x_3500 = PX0 + (3500.0 / 25000.0) * PW_AX

rectangle(
    ((PX0 + x_3500) / 2.0, (PY0 + PY0 + PH_AX) / 2.0),
    width=x_3500 - PX0,
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
    label="Time to First Token: TTFT (ms)",
    min_value=0,
    max_value=25000,
    tick_step=5000,
    format="{:,.0f}",
)
chart.configure_y_axis(
    min_value=0,
    max_value=36000,
    tick_step=9000,
    format="{:,.0f}",
)

chart.add_series("Base High", series_pts["base_high"], style=Styles.WarningFlat, shape="rhombus", radius=1.2)
chart.add_series("Pattern B", series_pts["pat_b_pydantic_1f"], style=Styles.DangerFlat, shape="square", radius=1.15)
chart.add_series("Base Low", series_pts["base_low"], style=Styles.SuccessFlat, shape="square", radius=1.15)
chart.add_series("Pattern C", series_pts["pat_c_tag"], style=Styles.TealFlat, shape="triangle", radius=1.2)
chart.add_series("Pattern A", series_pts["pat_a_pydantic_2f"], style=Styles.PrimaryFlat, shape="circle", radius=1.3)

chart.draw(xy=(10.0, 16.5))
text((11.5, 68.0), "Total Time (ms)", style=Styles.DarkBold.patch(text_size=9.5, halign="left"))

# Vertical UX Threshold Line
line((x_3500, PY0), (x_3500, PY0 + PH_AX), style=Styles.PrimaryBold.patch(line_width=1.5))
text((x_3500 + 2.0, 68.0), "← 3.5s Fast TTFT Ceiling", style=Styles.PrimaryBold.patch(text_size=9.5, halign="left"))

# Right-side Summary Cards
rectangle((143.0, 47.0), width=44.0, height=69.0, style=Styles.PrimaryNeutral.patch(shape_r=1.5))
text((143.0, 77.2), "45-Run Distribution Insights", style=Styles.PrimaryBold.patch(text_size=11.0))

cards = [
    (
        63.0,
        "1. Pattern A Mean 2.39s",
        "All 9 runs stay in 1.8–3.5s TTFT,\ncutting Base High wait (12.8s)\nby -81.4%!",
        Styles.PrimaryBold,
    ),
    (
        44.5,
        "2. Orthogonal X/Y Scaling",
        "Even as Tier 3 Total reaches\n16–27s, Pattern A TTFT stays\n~2.1s without drifting right",
        Styles.SuccessBold,
    ),
    (
        26.0,
        "3. Base High / Pat B Freeze",
        "High reasoning directly stalls\nTTFT, freezing the screen for\nup to 16.5–24.2 seconds",
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
    "Conclusion: All 9 Pattern A runs stay locked inside the <=3.5s TTFT zone, eliminating the 10.5–16.5s Base High freezes.",
    style=Styles.DarkBold.patch(text_size=10.0, halign="left"),
)

save()
```

### Complete 9-Prompt × 5-Method Empirical Metrics Table (`gemini-3.8-flash`: `low` → `high`)

The table below lists the exact `TTFT / Total` (in `ms`), internal reasoning tokens (`ThTok`), routing decision accuracy, and Tier 3 math verification across all 45 runs.

| Prompt ID & Title | Expected Route<br>(A/B/C Match) | Base Low (`low`)<br>`TTFT / Total (ThTok)` | Base High (`high`)<br>`TTFT / Total (ThTok)` | ★ Pattern A (`2-Field`)<br>`TTFT / Total (ThTok)` | Pattern B (`1-Field Seq`)<br>`TTFT / Total (ThTok)` | Pattern C (`Tag Prefix`)<br>`TTFT / Total (ThTok)` | Quality & Math Verification |
| :--- | :---: | ---: | ---: | ---: | ---: | ---: | :--- |
| **`T1_1` Greeting (PC Boot Issue)** | `False` (`3/3`) | `1,533 / 5,741` (`0`) | `13,039 / 17,434` (`921`) | **`2,234 / 4,536` (`0`)** | `3,837 / 6,992` (`49`) | `2,087 / 6,318` (`56`) | All valid (Pattern A fastest Total) |
| **`T1_2` Thank You / Ack** | `False` (`3/3`) | `2,595 / 4,746` (`53`) | `10,501 / 13,758` (`852`) | **`2,144 / 2,614` (`34`)** | `4,145 / 6,945` (`28`) | `2,272 / 3,390` (`45`) | All valid (Pattern A fastest Total) |
| **`T1_3` Support Desk Hours** | `False` (`3/3`) | `2,428 / 9,769` (`0`) | `12,708 / 19,842` (`1117`) | **`2,190 / 3,987` (`0`)** | `5,077 / 10,777` (`153`) | `2,347 / 4,115` (`37`) | All valid (Pattern A fastest Total) |
| **`T2_1` Power Drain Procedure** | `False` (`3/3`) | `1,331 / 9,477` (`0`) | `11,964 / 20,864` (`991`) | **`2,174 / 5,764` (`46`)** | `4,197 / 13,589` (`42`) | `2,531 / 8,426` (`35`) | All valid (Pattern A fastest Total) |
| **`T2_2` Safe Mode & Backup** | `False` (`3/3`) | `2,923 / 15,001` (`0`) | `13,417 / 25,827` (`1153`) | **`2,870 / 3,811` (`0`)** | `5,210 / 14,835` (`42`) | `3,242 / 8,318` (`58`) | All valid (Pattern A fastest Total) |
| **`T2_3` DISM & SFC Commands** | `False` (`3/3`) | `2,576 / 14,011` (`0`) | `11,229 / 22,851` (`1019`) | **`3,489 / 5,398` (`0`)** | `5,481 / 14,097` (`60`) | `2,913 / 11,215` (`64`) | All valid (Pattern A fastest Total) |
| **`T3_1` Repair vs Replace 3-Yr** | `True` (`3/3`) | `2,922 / 13,899` (**`0`**) | `14,104 / 23,247` (`1466`) | **`1,795 / 21,482` (`902`)** | `16,402 / 26,659` (`1538`) | `3,250 / 21,309` (`1309`) | 4 `high` methods pre-verified |
| **`T3_2` 1.8TB Backup & Cloud** | `True` (`3/3`) | `1,392 / 9,583` (**`0`**) | `16,510 / 27,861` (`1882`) | **`2,728 / 27,017` (`1591`)** | `24,231 / 35,330` (`2346`) | `5,654 / 31,139` (`2073`) | 4 `high` methods pre-verified |
| **`T3_3` Rental vs On-Site Repair** | `True` (`3/3`) | `1,693 / 7,729` (**`0`**) | `11,965 / 18,577` (`1295`) | **`1,870 / 16,240` (`674`)** | `15,222 / 20,844` (`1362`) | `2,073 / 18,607` (`806`) | 4 `high` methods pre-verified |
| **Tier 1 Mean (3 Prompts)** | **`3/3` Match** | `2,186 / 6,752` (`18`) | `12,083 / 17,011` (`963`) | **`2,189 / 3,713` (`11`)** | `4,353 / 8,238` (`77`) | `2,235 / 4,608` (`46`) | **Pattern A fastest Total** |
| **Tier 2 Mean (3 Prompts)** | **`3/3` Match** | `2,277 / 12,830` (`0`) | `12,203 / 23,181` (`1054`) | **`2,844 / 4,991` (`15`)** | `4,963 / 14,174` (`48`) | `2,895 / 9,320` (`52`) | **Pattern A fastest Total** |
| **Tier 1–2 Mean (6 Prompts)** | **`6/6` Match** | `2,231 / 9,791` (`9`) | `12,143 / 20,096` (`1009`) | **`2,517 / 4,352` (`13`)** | `4,658 / 11,206` (`62`) | `2,565 / 6,964` (`49`) | **Pattern A fastest Total** |
| **Tier 3 Mean (3 Prompts)** | **`3/3` Match** | `2,002 / 10,404` (**`0`**) | `14,193 / 23,228` (`1548`) | **`2,131 / 21,580` (`1056`)** | `18,618 / 27,611` (`1749`) | `3,659 / 23,685` (`1396`) | **Base Low has `0 tok` on T3!** |
| **All-9 Prompts Mean** | **`9/9` Match** | `2,155 / 9,995` (`6`) | `12,826 / 21,140` (`1188`) | **`2,388 / 10,094` (`361`)** | `9,311 / 16,674` (`624`) | `2,930 / 12,538` (`498`) | **Pattern A optimal overall** |

> **Key Empirical Findings (Why Fixed `thinking=low` Is Insufficient and Why Pattern A Beats Pattern C)**:
> 1. **Fixed `base_low` generated `0 tok` of internal reasoning across all 3 Tier 3 complex prompts**: When calling `gemini-3.8-flash` with `thinking_level=LOW` on standard plain-text queries, `thoughts_token_count` was `0` on `T3_1`, `T3_2`, and `T3_3` alike—meaning the model began streaming immediately without performing any internal scratchpad verification. Guaranteeing pre-verification on complex calculations requires escalating to Stage 2 `medium` or `high` (`high` in this benchmark, averaging `1,056–1,548 tok`).
> 2. **Pattern A starts streaming `1.53 s` faster than Pattern C on Tier 3**: Because Pattern A's Stage 1 uses constrained decoding (`{thinking: bool, response: str}`), it commits to `"thinking": true` with only `0–83 tok` of thought across all three Tier 3 prompts, displaying its 1-sentence bridge at **`2,131 ms` mean TTFT** (eliminating **`12.1 s` of blank-screen freeze** compared to `Base High`'s `14,193 ms`).

---

## 4.4 Stream Trajectory Deep Dive (`thinking=false` Direct vs. `thinking=true` Parallel Chaining)

To visualize how Pattern A dynamically switches between single-call direct streaming (`low`) on routine queries and 2-stage parallel chaining (`low` → `high`) on complex calculations, Figure 4-4 plots the cumulative character trajectories from `load_adaptive_trajectory()` on **`T2_1` (Tier 2: Power Drain Procedure)** and **`T3_1` (Tier 3: 3-Year PC Repair vs. Replacement Cost Comparison)**.

```drawlib align=center code=fold width=100% file=ch04_trajectory_deep_dive.png caption="Figure 4-4: Cumulative Output Character Stream Trajectories on Tier 2 Standard Procedure (T2_1: thinking=false Single low Stream) vs. Tier 3 Complex Calculation (T3_1: thinking=true 1-Sentence Bridge + Parallel Stage-2 high Chaining)"
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
    "Stream Trajectory Deep Dive (low -> high): T2_1 (thinking=false Direct) vs. T3_1 (thinking=true Parallel Chain)",
    style=Styles.DarkBold.patch(text_size=11.5),
)

# Shared Legend Bar
rectangle((86.0, 82.8), width=162.0, height=5.2, style=Styles.Neutral.patch(shape_r=1.0))

leg_items = [
    (7.5, Styles.PrimaryBold, Styles.PrimaryFlat, "★ Pattern A (2-Field low->high)"),
    (47.5, Styles.TealBold, Styles.TealFlat, "Pattern C (Tag Prefix)"),
    (78.5, Styles.SuccessBold, Styles.SuccessFlat, "Base Low (Fixed low)"),
    (109.5, Styles.WarningBold, Styles.WarningFlat, "Base High (Fixed high)"),
    (141.5, Styles.DangerBold, Styles.DangerFlat, "Pattern B (1F Seq)"),
]
for lx, lst, cst, ltxt in leg_items:
    line((lx, 82.8), (lx + 3.2, 82.8), style=lst.patch(line_width=2.2))
    circle((lx + 1.6, 82.8), radius=0.7, style=cst)
    text((lx + 4.0, 82.8), ltxt, style=Styles.DarkBold.patch(text_size=9.2, halign="left"))


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
    rectangle((x0 + pw / 2, 46.5), width=pw + 14.0, height=65.0, style=Styles.LightFlat.patch(shape_r=1.6))
    text((x0 + pw / 2, 74.8), title_s, style=Styles.DarkBold.patch(text_size=10.6))
    text((x0 + pw / 2, 71.0), sub_s, style=Styles.PrimaryBold.patch(text_size=9.5))
    rectangle((x0 + pw / 2, y0 + ph / 2), width=pw, height=ph, style=Styles.WhiteFlat)

    def px(t_ms: float) -> float:
        return x0 + min(max(t_ms, 0.0), max_t) / max_t * pw

    def py(c_val: float) -> float:
        return y0 + min(max(c_val, 0.0), max_c) / max_c * ph

    for xt in x_ticks:
        tx = px(float(xt))
        line((tx, y0), (tx, y0 + ph), style=Styles.LightDashed.patch(line_width=0.7))
        text((tx, y0 - 2.4), f"{xt / 1000:.0f}s", style=Styles.Dark.patch(text_size=9.5))

    for yt in y_ticks:
        ty = py(float(yt))
        line((x0, ty), (x0 + pw, ty), style=Styles.LightDashed.patch(line_width=0.7))
        text((x0 - 3.6, ty), f"{yt:,}", style=Styles.Dark.patch(text_size=9.5))

    line((x0, y0), (x0 + pw, y0), style=Styles.Dark.patch(line_width=1.1))
    line((x0, y0), (x0, y0 + ph), style=Styles.Dark.patch(line_width=1.1))

    method_styles = [
        ("base_low", Styles.SuccessBold.patch(line_width=1.6), Styles.SuccessFlat, 0.6),
        ("pat_c_tag", Styles.TealBold.patch(line_width=1.7), Styles.TealFlat, 0.65),
        ("base_high", Styles.WarningBold.patch(line_width=1.8), Styles.WarningFlat, 0.7),
        ("pat_b_pydantic_1f", Styles.DangerBold.patch(line_width=1.8), Styles.DangerFlat, 0.7),
        ("pat_a_pydantic_2f", Styles.PrimaryBold.patch(line_width=2.5), Styles.PrimaryFlat, 0.9),
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
    ph=36.5,
    prompt_id="T2_1",
    title_s="1. Tier 2 Procedure (T2_1: Power Drain Steps)",
    sub_s="thinking=false: Stage 1 (low) finishes in 1 API call",
    max_t=22000.0,
    max_c=1600.0,
    x_ticks=[0, 5000, 10000, 15000, 20000],
    y_ticks=[0, 400, 800, 1200, 1600],
)

# Dedicated Top Callout Strip for Left Panel (y=58..67, zero curve overlap)
rectangle((26.5, 62.5), width=35.0, height=8.6, style=Styles.PrimaryNeutral.patch(shape_r=0.9))
text((26.5, 64.5), "★ Pat A: 2,174 ms TTFT", style=Styles.PrimaryBold.patch(text_size=9.0))
text((26.5, 60.5), "5,764 ms (Fastest!)", style=Styles.DarkBold.patch(text_size=9.0))
line((28.0, 58.2), (px_l(5764.0), py_l(626.0)), arrow_head="->", style=Styles.PrimaryBold.patch(line_width=1.4))

rectangle((63.5, 62.5), width=35.0, height=8.6, style=Styles.WhiteFlat.patch(shape_r=0.9, line_width=0.7))
text((63.5, 64.5), "Base High: 11,964 ms Freeze", style=Styles.WarningBold.patch(text_size=9.0))
text((63.5, 60.5), "991 wasted tok (5.5x slow)", style=Styles.Dark.patch(text_size=8.8))
line((56.0, 58.2), (px_l(11964.0), py_l(40.0)), arrow_head="->", style=Styles.WarningBold.patch(line_width=1.3))

# Right Panel: T3_1 (Complex Math, thinking=true)
px_r, py_r = draw_multi_trajectory_panel(
    x0=98.0,
    y0=18.5,
    pw=63.0,
    ph=36.5,
    prompt_id="T3_1",
    title_s="2. Tier 3 Complex Math (T3_1: Repair vs. Replace)",
    sub_s="thinking=true: Bridge (1,795ms) + Stage 2 (high) Parallel",
    max_t=28000.0,
    max_c=2000.0,
    x_ticks=[0, 7000, 14000, 21000, 28000],
    y_ticks=[0, 500, 1000, 1500, 2000],
)

# Dedicated Top Callout Strip for Right Panel (y=58..67, zero curve overlap)
rectangle((109.5, 62.5), width=35.5, height=8.6, style=Styles.PrimaryNeutral.patch(shape_r=0.9))
text((109.5, 64.5), "1. 1,795 ms Bridge Display", style=Styles.PrimaryBold.patch(text_size=9.0))
text((109.5, 60.5), "Cuts 12.3s Base High freeze!", style=Styles.DarkBold.patch(text_size=8.8))
line((103.5, 58.2), (px_r(1795.0), py_r(60.0)), arrow_head="->", style=Styles.PrimaryBold.patch(line_width=1.4))

rectangle((146.5, 62.5), width=35.5, height=8.6, style=Styles.WhiteFlat.patch(shape_r=0.9, line_width=0.7))
text((146.5, 64.5), "2. 11,615 ms~ Stage 2 Chain", style=Styles.PrimaryBold.patch(text_size=9.0))
text((146.5, 60.5), "859 tok verified at 21.5s", style=Styles.Dark.patch(text_size=8.8))
line((136.0, 58.2), (px_r(11615.0), py_r(90.0)), arrow_head="->", style=Styles.PrimaryBold.patch(line_width=1.4))

# Bottom summary banner
rectangle((86.0, 6.0), width=160.0, height=6.4, style=Styles.PrimaryNeutral.patch(shape_r=1.2))
phosphor.sparkle((10.5, 6.0), width=3.2, style=Styles.PrimaryBold)
text(
    (14.0, 6.0),
    "Conclusion: Pattern A finishes T2_1 fastest (5,764 ms) and hides Base High's 12.3s freeze on T3_1 behind a 1,795 ms bridge.",
    style=Styles.DarkBold.patch(text_size=10.0, halign="left"),
)

save()
```

### Two Decisive Advantages Demonstrated by Figure 4-4

1. **Single-Call Completion & Fastest Total Time on Left Panel `T2_1` (`thinking=false`: Power Drain Procedure)**:
   - Pattern A (thick blue curve) resolves `"thinking": false` at **`2,174 ms`**, immediately streams the `"response"` body, and **completes the entire answer at `5,764 ms`**—finishing faster than all other methods.
   - By contrast, Base High (yellow curve) burns `991 tokens` of unnecessary internal reasoning, **displaying zero characters until `11,964 ms`** and taking `20,864 ms` to finish.
2. **Eliminating `12.3 Seconds` of UI Freeze on Right Panel `T3_1` (`thinking=true`: Repair vs. Replace 3-Year Cost)**:
   - Base High (yellow curve) **freezes the screen with 0 characters for `14,104 ms`** while generating `1,466` internal reasoning tokens, and Pattern B (red curve) stalls even longer (`16,402 ms`). Meanwhile, Base Low (green curve) starts at `2,922 ms` but performs `0 tok` of internal reasoning.
   - Pattern A (thick blue curve) detects `"thinking": true` at **`1,795 ms`**, launches Stage 2 (`thinking=high`) asynchronously in the background, and immediately renders the 58-character Stage 1 bridge sentence—**eliminating `12,309 ms` (~12.3 seconds) of blank-screen freeze** compared to Base High. While the user reads the bridge sentence, Stage 2 completes `859 tokens` of deep reasoning and smoothly chains the verified breakdown at **`11,615 ms`**, finishing at **`21,482 ms`** with the exact verified answer (`162,400 JPY` repair vs. `184,500 JPY` replacement; **repair saves `22,100 JPY`**).

---

## 4.5 Google AI Studio Reference Implementation & Comprehensive Scorecard

### Pattern A Reference Implementation on Google AI Studio (`google-genai`, `low` → `high`)

Because `chunk.parsed` in the `google-genai` SDK remains `None` on intermediate streaming chunks, Pattern A uses `pydantic_core.from_json(..., allow_partial="trailing-strings")` (bundled with Pydantic v2) to incrementally extract the `thinking` boolean and unescaped `response` string deltas from the growing JSON buffer (`src/gemini_evaluation/adaptive_thinking.py`). As noted in Section 4.1, if you want even faster initial response (TTFT), simply change `STAGE1_MODEL` to `"gemini-3.5-flash-lite"` (`MINIMAL` or `LOW`), and if you want deeper Stage 2 reasoning, change `STAGE2_MODEL` to `"gemini-4-hydrogen"` (or `"gemini-4-argon"` / `"gemini-4-carbon"` for complex enterprise workflows).

```python
import asyncio
from collections.abc import AsyncIterator
from contextlib import aclosing
from typing import Any

from google import genai
from google.genai import types
from pydantic import BaseModel
from pydantic_core import from_json

# Standard pairing: gemini-3.8-flash (Stage 1: LOW -> Stage 2: HIGH)
# - For even faster TTFT (~0.7s): STAGE1_MODEL = "gemini-3.5-flash-lite"
# - For deeper Stage 2 reasoning: STAGE2_MODEL = "gemini-4-hydrogen" (or "gemini-4-argon" / "gemini-4-carbon")
STAGE1_MODEL = "gemini-3.8-flash"
STAGE2_MODEL = "gemini-3.8-flash"


class AdaptiveStreamResponse(BaseModel):
    """Minimal 2-field structured streaming schema for Pattern A."""

    thinking: bool  # Field 1: Routing flag resolved on the initial chunk
    response: str   # Field 2: Full answer when thinking=False, or 1-sentence bridge when True


def parse_partial_json_dict(raw_buf: str) -> dict[str, Any] | None:
    """Safely parse an incomplete JSON buffer into a dict without raising exceptions."""
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
    """Pattern A: 2-field integrated Pydantic stream (low) + parallel Stage-2 chaining (high)."""
    stage2_queue: asyncio.Queue[str | BaseException | None] = asyncio.Queue()
    stage2_task: asyncio.Task[None] | None = None

    async def _produce_stage2() -> None:
        try:
            st2 = await client.aio.models.generate_content_stream(
                model=STAGE2_MODEL,
                contents=prompt,
                config=types.GenerateContentConfig(
                    system_instruction=(
                        "An opening greeting and acknowledgment have already been displayed. "
                        "Do not repeat any greeting; immediately provide the calculation steps and conclusion."
                    ),
                    thinking_config=types.ThinkingConfig(
                        thinking_level=types.ThinkingLevel.HIGH,
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
            model=STAGE1_MODEL,
            contents=prompt,
            config=types.GenerateContentConfig(
                system_instruction=(
                    "For greetings or standard procedures, set thinking: false and output the full answer in response. "
                    "For multi-condition calculations or comparisons, set thinking: true and output only a 1-sentence bridge in response."
                ),
                response_mime_type="application/json",
                response_schema=AdaptiveStreamResponse,
                thinking_config=types.ThinkingConfig(
                    thinking_level=types.ThinkingLevel.LOW,
                ),
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

                # 1) Resolve thinking flag once and spawn Stage 2 (HIGH) in parallel if True
                if decided_thinking is None and isinstance(partial.get("thinking"), bool):
                    decided_thinking = partial["thinking"]
                    if decided_thinking:
                        stage2_task = asyncio.create_task(_produce_stage2())

                # 2) Immediately yield unemitted deltas from response
                resp_so_far = partial.get("response")
                if isinstance(resp_so_far, str) and len(resp_so_far) > emitted_len:
                    delta = resp_so_far[emitted_len:]
                    emitted_len = len(resp_so_far)
                    yield delta

        # 3) Enforce full Pydantic schema validation at EOF
        final_obj = AdaptiveStreamResponse.model_validate_json(json_buf)
        if len(final_obj.response) > emitted_len:
            yield final_obj.response[emitted_len:]

        # 4) Seamlessly chain the parallel Stage 2 stream when thinking=True
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
        # Cancel any unfinished Stage 2 background task on caller abort or exception
        if stage2_task is not None and not stage2_task.done():
            stage2_task.cancel()
```

### Comprehensive Evaluation Scorecard Across All 5 Methods (`gemini-3.8-flash`: `low` → `high`)

| Evaluation Criterion | ★ Pattern A (`pat_a_pydantic_2f`)<br>`{thinking, response}` (`low->high`) | Pattern C (`pat_c_tag`)<br>`[DIRECT]` / `[THINK]` Tag (`low->high`) | Pattern B (`pat_b_pydantic_1f`)<br>`{thinking}` Seq Router (`low->high`) | Base High (`base_high`)<br>Fixed `thinking=high` | Base Low (`base_low`)<br>Fixed `thinking=low` |
| :--- | :---: | :---: | :---: | :---: | :---: |
| **All-9 Prompts Mean TTFT** | **`2,388 ms` (Excellent `< 2.5s`)** | `2,930 ms` (Acceptable `< 3.5s`) | `9,311 ms` (Fail `> 3.5s`) | `12,826 ms` (Fail `> 3.5s`) | **`2,155 ms` (Excellent `< 2.5s`)** |
| **Tier 1–2 Mean TTFT / Total** | **`2,517 ms` / `4,352 ms` (Fastest Total)** | `2,565 ms` / `6,964 ms` | `4,658 ms` / `11,206 ms` | `12,143 ms` / `20,096 ms` | `2,231 ms` / `9,791 ms` |
| **Tier 3 Mean TTFT (Max)** | **`2,131 ms` (`2,728 ms`)** | `3,659 ms` (`5,654 ms`) | `18,618 ms` (`24,231 ms`) | `14,193 ms` (`16,510 ms`) | `2,002 ms` (`2,922 ms`) |
| **Routing Accuracy** | **`9 / 9` (`100%`)** | **`9 / 9` (`100%`)** | **`9 / 9` (`100%`)** | Fixed (`high` always) | Fixed (`low` always) |
| **Tier 3 Math Scratchpad (`ThTok`)** | **`3 / 3` (`674–1,591 tok` verified)** | **`3 / 3` (`806–2,073 tok` verified)** | **`3 / 3` (`1,362–2,346 tok` verified)** | **`3 / 3` (`1,295–1,882 tok` verified)** | **Fail (`0 tok` across all 3 T3)** |
| **API Calls (T1–2 / T3)** | **`1.0 call` / `2.0 calls`** | `1.0 call` / `2.0 calls` | `2.0 calls` / `2.0 calls` | `1.0 call` / `1.0 call` | `1.0 call` / `1.0 call` |
| **Decoder Type Safety & Extensibility** | **Excellent (Constrained Decoding)** | Fail (Tag leak & multi-turn drift) | Partial (Router only) | None (Plain text) | None (Plain text) |
| **Overall Verdict** | **★ Production Standard (Fastest & Safe)** | Reject (Slower than A & unsafe) | Reject (Up to `24.2s` freeze) | Not Recommended (Up to `16.5s` freeze) | Reject (`0 tok` on complex math) |
