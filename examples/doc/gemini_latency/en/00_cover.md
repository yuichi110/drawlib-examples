# Gemini 3.8 Flash Latency & Architecture Evaluation Report

**Empirical Analysis of Streaming Delivery, `ThinkingConfig`, Pydantic Adaptive Routing & 50-Turn Context Caching on Google AI Studio (`google-genai` SDK)**

**Author:** Yuichi Ito | **Date:** 2026-11 | **Target:** Google AI Studio (`google-genai` SDK / `gemini-3.8-flash`)

```drawlib align=center width=100% code=false file=ch00_cover_hero.png caption="Figure 0-1: Three Core Evaluation Pillars and Key Empirical Findings on Google AI Studio (gemini-3.8-flash)"
from drawlib.canvas import save, setup
from drawlib.icons import phosphor
from drawlib.lines import line
from drawlib.shapes import rectangle
from drawlib.styles import Styles
from drawlib.text import text

setup(width=156, height=76, dpi=150)

# Outer structural frame
rectangle((78.0, 38.0), width=152.0, height=72.0, style=Styles.MutedDashed.patch(shape_r=2.0))

# Top Header Banner
rectangle((78.0, 64.5), width=144.0, height=12.4, style=Styles.PrimaryNeutral.patch(shape_r=1.4))
text(
    (78.0, 67.2),
    "Three Core Evaluation Pillars on Google AI Studio (gemini-3.8-flash)",
    style=Styles.DarkBold.patch(text_size=11.5),
)
text(
    (78.0, 62.0),
    "google-genai SDK (api_key=GEMINI_KEY) | ThinkingConfig, Pydantic Partial JSON & 50-Turn PC Support",
    style=Styles.Dark.patch(text_size=10.0),
)

# Pillar 1: Delivery Mode & ThinkingConfig (Neutral)
rectangle((78.0, 48.0), width=144.0, height=15.0, style=Styles.Neutral.patch(shape_r=1.4))
phosphor.sliders_horizontal((10.5, 51.0), width=3.2, style=Styles.DarkBold)
text(
    (13.8, 51.0),
    "1. Delivery & 5-Model Matrix",
    style=Styles.DarkBold.patch(text_size=10.5, halign="left"),
)
text(
    (9.5, 45.0),
    "Ch. 2–3 (18 Single + 220 Cross-Model)",
    style=Styles.Dark.patch(text_size=10.0, halign="left"),
)
line((58.0, 41.8), (58.0, 54.2), style=Styles.Muted)
text(
    (60.5, 51.0),
    "• Stream vs Block | 5 Active Models × 17 thinking_level + 5 budget=0 Configs",
    style=Styles.DarkBold.patch(text_size=10.0, halign="left"),
)
text(
    (60.5, 45.0),
    "• Trade-off: Fixed low lacks deep reasoning; Fixed high stalls TTFT for 14–21s",
    style=Styles.Dark.patch(text_size=10.0, halign="left"),
)

# Pillar 2: Adaptive Thinking Router (PrimaryFlat — Focal Point)
rectangle((78.0, 30.5), width=144.0, height=15.0, style=Styles.PrimaryFlat.patch(shape_r=1.4))
phosphor.star((10.5, 33.5), width=3.2, style=Styles.WhiteBold)
text(
    (13.8, 33.5),
    "★2. Adaptive Router (Pattern A)",
    style=Styles.WhiteBold.patch(text_size=10.5, halign="left"),
)
text(
    (9.5, 27.5),
    "Ch. 4 (3.8-flash low→high, 45 Runs)",
    style=Styles.White.patch(text_size=10.0, halign="left"),
)
line((58.0, 24.3), (58.0, 36.7), style=Styles.White)
text(
    (60.5, 33.5),
    "• {thinking: bool, response: str} Partial JSON Stream + Parallel Stage-2 high",
    style=Styles.WhiteBold.patch(text_size=10.0, halign="left"),
)
text(
    (60.5, 27.5),
    "• 1-Call low on Tiers 1–2 | 2,336ms Avg TTFT | 9/9 Routing | 3/3 Complex Math",
    style=Styles.White.patch(text_size=10.0, halign="left"),
)

# Pillar 3: Multi-Turn Scalability & Context Caching (SecondaryNeutral)
rectangle((78.0, 13.0), width=144.0, height=15.0, style=Styles.SecondaryNeutral.patch(shape_r=1.4))
phosphor.database((10.5, 16.0), width=3.2, style=Styles.DarkBold)
text(
    (13.8, 16.0),
    "3. 50-Turn Streaming & Cache",
    style=Styles.DarkBold.patch(text_size=10.5, halign="left"),
)
text(
    (9.5, 10.0),
    "Ch. 5 (50 Turns × 3 Configs = 150 Runs)",
    style=Styles.Dark.patch(text_size=10.0, halign="left"),
)
line((58.0, 6.8), (58.0, 19.2), style=Styles.Muted)
text(
    (60.5, 16.0),
    "• (1) 3.8-flash low / high vs (2) Ch.4 Adaptive Router (Initial TTFT & Total)",
    style=Styles.DarkBold.patch(text_size=10.0, halign="left"),
)
text(
    (60.5, 10.0),
    "• Stage 1→2 Implicit Cache sharing (up to 90.2%) keeps TTFT at 2,618ms (-87.6%)",
    style=Styles.Dark.patch(text_size=10.0, halign="left"),
)

save()
```

---

### Report Overview & Chapter Structure (Chapters 1–5)

This technical report presents a comprehensive empirical evaluation of **`gemini-3.8-flash`** (and the full Gemini 3.5 / 4 model lineup) on **Google AI Studio (`google-genai` SDK via `genai.Client(api_key=GEMINI_KEY)`)**, synthesizing live API benchmark executions recorded in `src/gemini_evaluation/` under a PC troubleshooting customer-support scenario. It establishes actionable architecture patterns that simultaneously achieve responsive Time to First Token (TTFT), deep multi-step mathematical accuracy, and flat latency scaling across 50-turn conversational histories.

| Chapter | Title | Scope & Key Empirical Findings |
| :---: | :--- | :--- |
| **Chapter 1** | **Executive Summary** | End-to-end architecture decision matrix, cross-benchmark latency comparisons, and production configuration guidelines. |
| **Chapter 2** | **Background & Measurement Methodology** | Anatomy of the 3 LLM latency phases (Prefill, Thinking, Decoding), 2D trajectory charts (`Elapsed Time vs. Cumulative Characters`), Pydantic `response_schema` Cold vs. Warm FSM grammar compilation, incremental delta extraction via `pydantic_core.from_json(..., allow_partial="trailing-strings")`, `ExecutionTracer` instrumentation, and **empirical comparison of Gemini 3.5 / 3.8 / 4 models, `ThinkingConfig` options, and Context Caching rules**. |
| **Chapter 3** | **Parameters & Latency** | Empirical evaluation of Blocking (`generate_content`) vs. Streaming (`generate_content_stream`) across all 6 `ThinkingConfig` levels, the linear scaling law of `thoughts_token_count`, the speed-vs-accuracy trade-off across PC support query Tiers 1–3, and a **220-run cross-model latency comparison across all 5 active Gemini models × 17 `thinking_level` options + 5 deprecated `thinking_budget=0` scenarios on 5 Simple + 5 Complex queries**. |
| **Chapter 4** | **Adaptive Thinking Router** | Candidate model and `thinking_level` taxonomy for Stage 1 (fast routing) and Stage 2 (deep reasoning: Categories A/B/C), followed by a 45-run empirical evaluation using **`gemini-3.8-flash` (`low → high`)**. Demonstrates why **Pattern A** achieves **`2,336 ms` avg TTFT**, **`100%`** routing accuracy, and **`100%`** Tier 3 calculation accuracy. |
| **Chapter 5** | **Multi-Turn Chat Behavior & Context Caching** | Standardized exclusively on **Streaming (`generate_content_stream`)** across a 50-turn continuous PC troubleshooting dialogue (`150 runs`), comparing **`(1)` `3.8-flash low` & `high`** against **`(2)` Chapter 4's Adaptive Thinking Router (`Pattern A: low → high`)** on both initial response (`TTFT`) and completion (`Total`), with Stage 1→2 **Implicit Context Cache sharing (up to `90.2%` hit rate)**. |

| Document Metadata | Value |
| :--- | :--- |
| **Title (`title`)** | Gemini 3.8 Flash Latency & Architecture Evaluation Report |
| **Subtitle (`subtitle`)** | Empirical Analysis of Streaming Delivery, ThinkingConfig, Pydantic Adaptive Routing & 50-Turn Context Caching |
| **Author (`author`)** | Yuichi Ito |
| **Date (`date`)** | 2026-11 |
| **Target SDK & Model** | Google AI Studio `google-genai` SDK (`genai.Client(api_key=GEMINI_KEY)`) / `gemini-3.8-flash` & 5 active models |
| **Evaluation Codebase** | `src/gemini_evaluation/llm_call.py`, `src/gemini_evaluation/adaptive_thinking.py`, `src/gemini_evaluation/tracer.py` |
