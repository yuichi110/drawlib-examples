# 2. Background & Measurement Methodology

This chapter defines the foundational concepts and instrumentation methodology used throughout the empirical evaluations in Chapters 3–5. Sections 2.1 and 2.2 decompose LLM inference latency on `gemini-3.8-flash` into three sequential server-side phases (**Prefill, Thinking, and Decoding**), explain why **2D Trajectory Charts (`Elapsed Time vs. Cumulative Output Characters`)** expose critical user-experience differences hidden by scalar averages, and present clean Blocking vs. Streaming invocation patterns using the Google AI Studio `google-genai` SDK. Sections 2.3 through 2.5 examine **Pydantic Structured Outputs (`response_schema`)**, **Cold vs. Warm finite-state machine (FSM) grammar compilation**, incremental partial JSON delta extraction via **`pydantic_core.from_json(..., allow_partial="trailing-strings")`**, the microsecond-precision **`ExecutionTracer`** (`src/gemini_evaluation/tracer.py`), and a **comprehensive cross-generational comparison of Gemini 3.5 / 3.8 / 4 models, `ThinkingConfig` options, and Context Caching rules**.

```drawlib align=center code=fold width=100% file=ch02_latency_phases_trajectory.png caption="Figure 2-1: Anatomy of the 3 LLM Latency Phases (Prefill → Thinking → Decoding) and Blocking vs. Streaming 2D Trajectory Comparison (thinking=0 Empirical Data)"
from drawlib.canvas import save, setup
from drawlib.icons import phosphor
from drawlib.lines import line
from drawlib.shapes import rectangle
from drawlib.styles import Styles
from drawlib.text import text
from drawlib.utils import draw_trajectory_panel, load_thinking_timeline

setup(width=156, height=82, dpi=150)

# Outer structural frame
rectangle((78.0, 41.0), width=152.0, height=78.0, style=Styles.MutedDashed.patch(shape_r=2.0))
text(
    (78.0, 76.6),
    "Anatomy of the 3 LLM Latency Phases (Prefill → Thinking → Decoding) & 2D Trajectories",
    style=Styles.DarkBold.patch(text_size=11.5),
)

# Top Section: 3 Latency Phases
rectangle((78.0, 60.2), width=145.6, height=24.0, style=Styles.PrimaryNeutral.patch(shape_r=1.5))
text(
    (78.0, 69.2),
    "Server-Side Processing Timeline Within a Single API Request (t = 0 ms Request Start → Stream Completed)",
    style=Styles.DarkBold.patch(text_size=10.3),
)

phases = [
    (
        26.5,
        39.0,
        "Phase 1: Prefill (Input)",
        "KV Cache Lookup + Prompt Token Eval",
        Styles.WhiteFlat,
        Styles.DarkBold,
        Styles.Dark,
    ),
    (
        76.0,
        46.0,
        "Phase 2: Thinking (Reasoning)",
        "thoughts_token_count (+9.0 ms/tok)",
        Styles.SecondaryNeutral,
        Styles.DarkBold,
        Styles.Dark,
    ),
    (
        127.0,
        44.0,
        "Phase 3: Decoding (Output)",
        "1st Token = TTFT → Autoregressive Stream",
        Styles.PrimaryFlat,
        Styles.WhiteBold,
        Styles.White,
    ),
]
for px, pw, p_title, p_sub, box_st, t_st, s_st in phases:
    rectangle((px, 60.4), width=pw, height=11.0, style=box_st.patch(shape_r=1.2))
    text((px, 62.6), p_title, style=t_st.patch(text_size=10.2))
    text((px, 58.2), p_sub, style=s_st.patch(text_size=10.0))

line((46.0, 60.4), (53.0, 60.4), arrow_head="->", style=Styles.DarkBold)
line((99.0, 60.4), (105.0, 60.4), arrow_head="->", style=Styles.DarkBold)

text(
    (78.0, 51.4),
    "• Streaming TTFT = End of Phase 1 + Phase 2  |  • Blocking TTFT = Total (End of Phase 1 + Phase 2 + Full Phase 3)",
    style=Styles.DarkBold.patch(text_size=10.0),
)

# Bottom Section: Side-by-Side 2D Trajectory Comparison (thinking=0, high-contrast pastel bands)
ex_block = load_thinking_timeline("blocking", "0")
ex_stream = load_thinking_timeline("streaming", "0")

draw_trajectory_panel(
    x0=15.0,
    y0=12.6,
    pw=54.0,
    ph=23.5,
    title="1. Blocking: generate_content (thinking=0)",
    subtitle="Stalls at 0 chars until 3,360 ms → Returns all 338 chars at once",
    ex=ex_block,
    max_t=4000.0,
    max_c=420.0,
    x_ticks=(0, 1000, 2000, 3000, 4000),
    y_ticks=(0, 200, 400),
    lang="en",
)

draw_trajectory_panel(
    x0=91.0,
    y0=12.6,
    pw=54.0,
    ph=23.5,
    title="★2. Streaming: generate_content_stream (thinking=0)",
    subtitle="Starts at TTFT 1,205 ms → Smoothly streams 373 chars to 3,192 ms",
    ex=ex_stream,
    max_t=4000.0,
    max_c=420.0,
    x_ticks=(0, 1000, 2000, 3000, 4000),
    y_ticks=(0, 200, 400),
    lang="en",
)

text((42.0, 4.2), "Elapsed Time (ms) — Y-Axis: Cumulative Chars", style=Styles.DarkBold.patch(text_size=10.0))
text((118.0, 4.2), "Elapsed Time (ms) — Pastel Purple: TTFT Wait / Pastel Blue: Streaming", style=Styles.DarkBold.patch(text_size=10.0))

save()
```

---

## 2.1 Latency Definition & Trajectory Anatomy

To diagnose and optimize latency in conversational LLM applications, engineers must look beyond total request duration and decompose each API call into **three sequential server-side execution phases**:

### 1. The Three Phases of LLM Inference

1. **Phase 1: Prefill (Input Token Processing & KV Cache Lookup)**:
   The server processes the input payload—comprising `system_instruction`, multi-turn conversation `history`, and the latest user `prompt` (`prompt_token_count`)—in parallel across Transformer layers to populate the Attention Key-Value (KV) cache. On Google AI Studio (`gemini-3.8-flash`), when a conversation prefix matches an existing server-side cache entry (`cached_content_token_count`), prefill computation for those cached tokens is bypassed, keeping prefill latency flat even as multi-turn history grows beyond `21,000 tokens` (see Chapter 5).
2. **Phase 2: Thinking (Internal Reasoning Token Generation: `thoughts_token_count`)**:
   In reasoning-capable models such as `gemini-3.8-flash`, before emitting the very first visible response token (`chunk.text`), the model autoregressively generates internal Chain-of-Thought reasoning tokens (`usage_metadata.thoughts_token_count`). Crucially, **no visible text chunks are emitted to the client while the Thinking phase is in progress**, even when using `generate_content_stream`. Every internal reasoning token adds approximately **`+9.0 ms`** directly to the initial wait time (TTFT).
3. **Phase 3: Decoding (Autoregressive Visible Output Streaming: `output_token_count`)**:
   Once Prefill and Thinking conclude, the model autoregressively generates visible output tokens (`candidates_token_count` / `output_token_count`) until completion (`finish_reason = STOP`).

### 2. TTFT vs. Total Completion Time and Why 2D Trajectory Charts Matter

From these three phases, the two fundamental client-side latency metrics are defined as:

```text
TTFT_streaming = T_Network_RTT + T_Prefill + T_Thinking
Total = TTFT_blocking = T_Network_RTT + T_Prefill + T_Thinking + T_Decoding
```

- **TTFT (Time to First Token / `time_to_first_token_ms`)**: Elapsed time from request initiation (`t = 0 ms`) until the first non-empty visible text chunk arrives at the client. TTFT directly governs **perceived responsiveness** in interactive UIs. In Blocking mode (`generate_content`), the response is withheld until decoding finishes, forcing `TTFT = Total`.
- **Total Completion Time (`stream_completed_ms`)**: Elapsed time from request initiation (`t = 0 ms`) until the final chunk (EOF) is received.
- **Why 2D Trajectory Charts (`Elapsed Time [ms] vs. Cumulative Output Characters`) Are Essential**:
  Comparing scalar completion times in Figure 2-1 (`thinking=0`) might suggest that Blocking (`3,360 ms`) and Streaming (`3,192 ms`) are nearly identical. However, plotting **Elapsed Time (x-axis) against Cumulative Visible Characters (y-axis)** reveals a stark difference in user experience:
  - **Blocking (Figure 2-1 Left)**: The UI remains frozen at `y = 0 chars` for the entire **`3,360 ms`**, after which all 338 characters appear as a single vertical step function.
  - **Streaming (Figure 2-1 Right)**: Visible text begins rendering at **`1,205 ms` (`2,155 ms` or `64%` earlier than Blocking)** right after the pastel-purple prefill band, then climbs smoothly across the pastel-blue decoding band (`1,205 → 3,192 ms`) at `~190 chars/s`—far exceeding human reading speed (`~10 chars/s`). Thus, the entire decoding phase is hidden behind the user's reading time. Furthermore, in multi-stage architectures such as the Adaptive Thinking Router (Chapter 4), 2D trajectories expose the exact timing of the Stage-1 acknowledgment, the brief reading plateau during parallel Stage-2 reasoning, and the seamless continuation slope.

---

## 2.2 Blocking vs. Streaming API Usage (`google-genai` on Google AI Studio)

All benchmarks in this report (`src/gemini_evaluation/llm_call.py`) use the official **`google-genai`** SDK against **Google AI Studio** (`genai.Client(api_key=GEMINI_KEY)`) and `gemini-3.8-flash` via `asyncio` (`client.aio`). Below is the reference implementation (`resolve_thinking_config`) for resolving all six `ThinkingConfig` options and invoking Blocking (`generate_content`) versus Streaming (`generate_content_stream`) (see **Section 2.5** for a detailed analysis of `thinking_level` vs. `thinking_budget` across Gemini 3.5, 3.8, and 4).

```python
from collections.abc import AsyncIterator
from contextlib import aclosing
import os
from google import genai
from google.genai import types

# 1. Initialize Google AI Studio Client using GEMINI_KEY from environment / .env
GEMINI_KEY = os.environ["GEMINI_KEY"]
MODEL = "gemini-3.8-flash"
client = genai.Client(api_key=GEMINI_KEY)


def resolve_thinking_config(thinking: str | int | None = 0) -> types.ThinkingConfig | None:
    """Map the 6 benchmark thinking options (0, minimal, low, medium, high, default) to ThinkingConfig.
    Note: Because gemini-3.8-flash rejects ThinkingLevel.MINIMAL (HTTP 400) and produces 0 thoughts
    at ThinkingLevel.LOW, benchmark labels 0 / minimal / low use legacy thinking_budget values to
    sample intermediate reasoning token counts (see Section 2.5).
    """
    if thinking is None or thinking == "default":
        return None  # Server default dynamic thinking (medium on gemini-3.8-flash)
    if isinstance(thinking, int):
        return types.ThinkingConfig(thinking_budget=thinking)
    key = str(thinking).strip().lower()
    if key == "0":
        return types.ThinkingConfig(thinking_budget=0)
    if key == "minimal":
        return types.ThinkingConfig(thinking_budget=256)
    if key == "low":
        return types.ThinkingConfig(thinking_budget=4096)
    level_map = {
        "medium": types.ThinkingLevel.MEDIUM,
        "high": types.ThinkingLevel.HIGH,
    }
    return types.ThinkingConfig(thinking_level=level_map[key])


# 2. Blocking Unary Call (waits for full completion: TTFT == Total)
async def generate_text_blocking(prompt: str, thinking: str | int | None = 0) -> str:
    cfg = resolve_thinking_config(thinking)
    resp = await client.aio.models.generate_content(
        model=MODEL,
        contents=prompt,
        config=types.GenerateContentConfig(thinking_config=cfg) if cfg else None,
    )
    return resp.text or ""


# 3. Progressive Streaming Call (yields text chunks immediately after TTFT)
async def stream_text_progressive(prompt: str, thinking: str | int | None = 0) -> AsyncIterator[str]:
    cfg = resolve_thinking_config(thinking)
    stream = await client.aio.models.generate_content_stream(
        model=MODEL,
        contents=prompt,
        config=types.GenerateContentConfig(thinking_config=cfg) if cfg else None,
    )
    async with aclosing(stream):
        async for chunk in stream:
            if chunk.text:
                yield chunk.text
```

---

## 2.3 Pydantic Structured Output & Partial JSON Streaming Mechanics

When building an adaptive router that decides whether a query requires deep reasoning (`thinking: bool`) while simultaneously streaming the user-facing reply (`response: str`), passing `response_mime_type="application/json"` and `response_schema=AdaptiveStreamResponse` to `GenerateContentConfig` enables **Constrained Decoding**.

To achieve low streaming TTFT with structured JSON, engineers must understand two critical mechanics: **(1) Cold vs. Warm server-side FSM grammar compilation** and **(2) incremental partial JSON parsing via `pydantic_core.from_json`**. Figure 2-2 illustrates both the empirical Cold/Warm compilation benchmark (`load_schema_experiment()`, 8 runs) and the 4-step incremental delta extraction pipeline.

```drawlib align=center code=fold width=100% file=ch02_pydantic_cold_warm_pipeline.png caption="Figure 2-2: Pydantic response_schema Cold vs. Warm Compilation Benchmark (2-Field vs. 6-Field, 8 Runs) and Incremental Partial JSON Extraction Pipeline via pydantic_core.from_json"
from drawlib.canvas import save, setup
from drawlib.charts.bar import BarChart
from drawlib.icons import phosphor
from drawlib.lines import line
from drawlib.shapes import rectangle
from drawlib.styles import Styles
from drawlib.text import text
from drawlib.utils import load_schema_experiment

setup(width=158, height=92, dpi=150)

# Outer structural frame
rectangle((79.0, 46.0), width=154.0, height=88.0, style=Styles.MutedDashed.patch(shape_r=2.0))
text(
    (79.0, 86.2),
    "Pydantic Structured Streaming: Cold vs. Warm Schema Compilation & Partial JSON Pipeline",
    style=Styles.DarkBold.patch(text_size=11.5),
)

# ─── Top Section: Cold vs. Warm Schema Compilation Experiment ────────────────
exp = load_schema_experiment()
by_key = {(str(r["schema_label"]), int(r["run_index"])): r for r in exp}

ordered_groups = [
    ("2F #1", [by_key[("minimal_2field", 1)]]),
    ("2F #2-4", [by_key[("minimal_2field", 2)], by_key[("minimal_2field", 3)], by_key[("minimal_2field", 4)]]),
    ("6F #1", [by_key[("rich_6field", 1)]]),
    ("6F #2-4", [by_key[("rich_6field", 2)], by_key[("rich_6field", 3)], by_key[("rich_6field", 4)]]),
]
cats = [lbl for lbl, _ in ordered_groups]
ttft_vals = [round(sum(float(r["ttft_ms"]) for r in rows) / len(rows), 0) for _, rows in ordered_groups]
tot_vals = [round(sum(float(r["total_ms"]) for r in rows) / len(rows), 0) for _, rows in ordered_groups]

rectangle((55.0, 61.5), width=98.0, height=41.0, style=Styles.Neutral.patch(shape_r=1.4))
rectangle((55.0, 61.2), width=95.6, height=38.8, style=Styles.WhiteFlat.patch(shape_r=1.0))

text((32.5, 77.2), "1. First Chunk Arrival: TTFT (ms)", style=Styles.PrimaryBold.patch(text_size=9.8))
chart_ttft = BarChart(
    axis_line_style=Styles.Dark,
    axis_text_style=Styles.DarkBold.patch(text_size=8.8),
    grid_style=Styles.MutedDashed,
    value_text_style=Styles.DarkBold.patch(text_size=8.8),
    value_format="{:,.0f}",
    width=40.0,
    height=23.5,
    categories=cats,
    orientation="vertical",
    bar_mode="group",
    bar_width_ratio=0.56,
    bar_r=0.3,
)
chart_ttft.configure_y_axis(min_value=0, max_value=4500, tick_step=1500, format="{:,.0f}")
chart_ttft.add_series(name="TTFT (ms)", values=ttft_vals, style=Styles.PrimaryFlat)
chart_ttft.draw(xy=(13.5, 48.2))

text((80.0, 77.2), "2. Stream Completion: Total (ms)", style=Styles.DarkBold.patch(text_size=9.8))
chart_tot = BarChart(
    axis_line_style=Styles.Dark,
    axis_text_style=Styles.DarkBold.patch(text_size=8.8),
    grid_style=Styles.MutedDashed,
    value_text_style=Styles.DarkBold.patch(text_size=8.8),
    value_format="{:,.0f}",
    width=40.0,
    height=23.5,
    categories=cats,
    orientation="vertical",
    bar_mode="group",
    bar_width_ratio=0.56,
    bar_r=0.3,
)
chart_tot.configure_y_axis(min_value=0, max_value=7500, tick_step=2500, format="{:,.0f}")
chart_tot.add_series(name="Total (ms)", values=tot_vals, style=Styles.SecondaryNeutral)
chart_tot.draw(xy=(61.0, 48.2))

# Right-side summary cards for Top Section
rectangle((129.5, 61.5), width=45.0, height=41.0, style=Styles.PrimaryNeutral.patch(shape_r=1.4))
text((129.5, 78.2), "Schema Experiment Insights", style=Styles.DarkBold.patch(text_size=10.4))

s_cards = [
    (
        69.4,
        "1. Cold #1 FSM Compilation",
        "6F #1 incurs FSM grammar build:\nTTFT 3,337 ms (flag at 2,954 ms)",
        Styles.WhiteFlat,
    ),
    (
        57.5,
        "2. -15.0% Faster Once Warm",
        "6F Warm (#2–#4) avg TTFT 2,837 ms\nFlag decided at avg 2,419 ms",
        Styles.WhiteFlat,
    ),
    (
        45.6,
        "3. 2F vs 6F Differs by +93ms",
        "2F Warm 2,744 ms vs 6F 2,837 ms\nField order governs streaming TTFT",
        Styles.SecondaryNeutral,
    ),
]
for cy, ch, cb, cst in s_cards:
    rectangle((129.5, cy), width=41.6, height=10.0, style=cst.patch(shape_r=0.9))
    text((129.5, cy + 2.4), ch, style=Styles.DarkBold.patch(text_size=9.8))
    text((129.5, cy - 1.8), cb, style=Styles.Dark.patch(text_size=9.5))

# ─── Bottom Section: pydantic_core.from_json Incremental Pipeline ────────────
rectangle((79.0, 20.8), width=146.0, height=34.0, style=Styles.PrimaryNeutral.patch(shape_r=1.5))
text(
    (79.0, 34.6),
    'Incremental Delta Extraction Pipeline via Rust pydantic_core.from_json(raw_bytes, allow_partial="trailing-strings")',
    style=Styles.DarkBold.patch(text_size=10.4),
)

p_steps = [
    (
        23.5,
        32.0,
        "Step 1: Hold Incomplete Bool",
        'Input: \'{"thinking": fa\'\n→ Returns: {} (Zero false branch)\nNon-string tokens held safely',
        Styles.WhiteFlat,
        Styles.DarkBold,
    ),
    (
        60.0,
        33.0,
        "Step 2: Lock Bool & Branch",
        'Input: \'{"thinking": false,\'\n→ {\'thinking\': False} (~2.5s)\nIf True: spawn Stage-2 task',
        Styles.SecondaryNeutral,
        Styles.DarkBold,
    ),
    (
        97.5,
        34.0,
        "★Step 3: Slice String Delta",
        'Input: \'..."response": "Line 1\\\'\n→ Holds trailing \\, yields \'Line 1\'\ndelta = msg[emitted_len:]',
        Styles.PrimaryFlat,
        Styles.WhiteBold,
    ),
    (
        134.5,
        31.0,
        "Step 4: EOF Full Validation",
        "At stream completion:\nmodel_validate_json(buf)\nverifies full Pydantic schema",
        Styles.WhiteFlat,
        Styles.DarkBold,
    ),
]
for px, pw, p_hdr, p_body, p_st, hdr_st in p_steps:
    rectangle((px, 18.8), width=pw, height=22.4, style=p_st.patch(shape_r=1.2))
    text((px, 26.8), p_hdr, style=hdr_st.patch(text_size=10.0))
    body_st = Styles.White.patch(text_size=10.0) if p_st == Styles.PrimaryFlat else Styles.Dark.patch(text_size=10.0)
    text((px, 15.8), p_body, style=body_st)

line((39.5, 18.8), (43.0, 18.8), arrow_head="->", style=Styles.DarkBold)
line((77.0, 18.8), (80.5, 18.8), arrow_head="->", style=Styles.DarkBold)
line((115.5, 18.8), (119.0, 18.8), arrow_head="->", style=Styles.DarkBold)

save()
```

### 1. Server-Side Constrained Decoding & Cold vs. Warm Schema Compilation

When `response_mime_type="application/json"` and `response_schema=AdaptiveStreamResponse` are supplied, Google AI Studio compiles the Pydantic `BaseModel`'s JSON Schema into a **finite-state machine (FSM) token mask** that constrains token sampling at every decoding step, guaranteeing `100%` syntactic validity.

The table below and the top panel of Figure 2-2 present the 8-run schema compilation experiment (`src/gemini_evaluation/adaptive_thinking_log.json`), comparing the minimal 2-field `AdaptiveStreamResponse(thinking: bool, response: str)` (`minimal_2field`) against a 6-field `RichStreamResponse` (`rich_6field`, which adds two `Literal` enums, an escalation boolean, and a `list[str]` of follow-up questions) across four consecutive runs (`#1`–`#4`). Across all 8 runs, the leading `thinking` field is resolved at or before the first visible `response` text chunk (`flag_decided_ms <= ttft_ms < total_ms`).

| Schema Variant (`schema_label`) | Run | Cache State | Flag Decided (`flag_decided_ms`) | First Token (`ttft_ms`) | Total Time (`total_ms`) | Output Chars |
| :--- | :-: | :-: | ---: | ---: | ---: | ---: |
| **`minimal_2field`** (`AdaptiveStreamResponse`) | **#1** | Warm (Post-Main) | `2,562.2 ms` | **`2,562.2 ms`** | `5,319.0 ms` | `496 chars` |
| **`minimal_2field`** (`AdaptiveStreamResponse`) | **#2** | Warm | `2,294.1 ms` | **`2,294.1 ms`** | `4,551.2 ms` | `455 chars` |
| **`minimal_2field`** (`AdaptiveStreamResponse`) | **#3** | Warm | `2,194.2 ms` | **`2,492.2 ms`** | `4,950.2 ms` | `579 chars` |
| **`minimal_2field`** (`AdaptiveStreamResponse`) | **#4** | Warm | `3,446.8 ms` | **`3,446.8 ms`** | `6,855.2 ms` | `686 chars` |
| **`rich_6field`** (`RichStreamResponse`) | **#1** | **Cold (1st New)** | `2,954.3 ms` | **`3,337.3 ms`** | `6,517.4 ms` | `507 chars` |
| **`rich_6field`** (`RichStreamResponse`) | **#2** | Warm | `2,157.1 ms` | **`2,504.4 ms`** | `4,526.9 ms` | `360 chars` |
| **`rich_6field`** (`RichStreamResponse`) | **#3** | Warm | `2,780.6 ms` | **`3,259.3 ms`** | `5,838.9 ms` | `422 chars` |
| **`rich_6field`** (`RichStreamResponse`) | **#4** | Warm | `2,320.5 ms` | **`2,747.5 ms`** | `6,504.9 ms` | `679 chars` |

- **Cold `#1` vs. Warm `#2–#4` (`-15.0%` TTFT Reduction)**:
  Because `minimal_2field` (`AdaptiveStreamResponse`) was already compiled during the preceding 45-run benchmark, `#1` started warm at `2,562.2 ms` (`#2–#4` warm average **`2,744.4 ms`**, 4-run average `2,698.8 ms`). In contrast, when the newly introduced 6-field schema (`rich_6field`) was sent for the very first time in **`rich_6field #1` (Cold)**, FSM grammar compilation resulted in **`TTFT = 3,337.3 ms`** (`flag_decided_ms = 2,954.3 ms`). On subsequent warm runs (`#2–#4`), the cached grammar dropped average TTFT to **`2,837.1 ms` (`2,504.4–3,259.3 ms`, `-500.2 ms` or `-15.0%` faster)** and resolved `thinking` at an average of **`2,419.4 ms`**.
- **Why Field Declaration Order—Not Field Count—Governs Streaming TTFT**:
  Once warm (`#2–#4`), expanding from 2 fields (`2,744.4 ms`) to 6 fields (`2,837.1 ms`) adds only **`+92.7 ms` (`+3.4%`)** to TTFT. Because JSON tokens are generated strictly in schema declaration order, placing `thinking: bool` first, keeping only short scalar/enum fields before `response: str`, and placing variable-length arrays (`suggested_followups: list[str]`) *after* `response: str` ensures that visible text streaming begins immediately without waiting for auxiliary metadata lists.

### 2. Incremental Delta Extraction via `pydantic_core.from_json(..., allow_partial="trailing-strings")`

During `generate_content_stream`, intermediate chunks contain unclosed JSON fragments (such as `'{"thinking": false, "response": "Thank you for'`), causing the SDK's built-in `chunk.parsed` property to remain `None` until the stream finishes.

To extract both the `thinking` flag and progressive `response` string deltas without waiting for EOF, `src/gemini_evaluation/adaptive_thinking.py` uses Pydantic v2's Rust parser **`pydantic_core.from_json(raw_bytes, allow_partial="trailing-strings")`**:

1. **Safe Holding of Incomplete Primitives**: When the buffer ends mid-token (`'{"thinking": fa'`), `allow_partial="trailing-strings"` withholds the incomplete key-value pair and returns `{}`. The moment `false` or `true` completes, `{'thinking': False}` is locked in as a native Python `bool`.
2. **Escape-Safe `O(1)` String Slicing**: If a chunk boundary splits a JSON escape sequence at the end of `"response"` (e.g., `'..."1st line\\'`), `from_json` holds the trailing backslash until the next chunk arrives (`n` → `\n`). Tracking `emitted_resp_len` and slicing `delta = resp_so_far[emitted_resp_len:]` yields clean, decoded text deltas on every chunk.

```python
from typing import Any
from pydantic import BaseModel
from pydantic_core import from_json


class AdaptiveStreamResponse(BaseModel):
    thinking: bool  # Field 1: Routing boolean resolved prior to first visible chunk
    response: str   # Field 2: Incrementally streamed full answer or 1-sentence ack


def parse_partial_json_dict(raw_buf: str) -> dict[str, Any] | None:
    """Safely parse incomplete streaming JSON bytes into a dict via Rust pydantic_core."""
    if not raw_buf:
        return None
    try:
        parsed = from_json(raw_buf.encode("utf-8"), allow_partial="trailing-strings")
        return parsed if isinstance(parsed, dict) else None
    except ValueError:
        return None
```

---

## 2.4 Measurement Architecture (`ExecutionTracer`)

Every benchmark in this report (`src/gemini_evaluation/benchmark_thinking.py`, `benchmark_adaptive_thinking.py`, and `benchmark_multiturn_chat.py`) is instrumented by **`ExecutionTracer`** (`src/gemini_evaluation/tracer.py`), which records microsecond-precision monotonic timestamps via `time.perf_counter()` alongside token usage metadata.

### Milestones and Token Metrics Recorded by `ExecutionTracer`

| Instrumentation Category | Field / Event (`ExecutionTracer`) | Definition & Measurement Point |
| :--- | :--- | :--- |
| **Request Origin** | `start` (`t_ms = 0.0`, `chars = 0`) | Monotonic `time.perf_counter()` origin recorded in `tracer.start_gemini()` immediately before invoking the Gemini API. |
| **Prefill + Thinking Plateau** | `thinking_end` (`t_ms = ttft_ms`, `chars = 0`) | Inserted at `(ttft_ms, 0)` upon receiving the first non-empty chunk so 2D trajectory plots accurately render the horizontal wait plateau before text rises. |
| **Streaming Chunk Series** | `chunk_1 .. chunk_N` (`t_ms`, `chars`) | Recorded by `tracer.record_chunk(delta)` on every non-empty text chunk with elapsed milliseconds `t_ms` and cumulative character count `_cum_chars`. |
| **Adaptive Router Milestones** | `flag_decided_ms` / `stage2_first_chunk_ms` | Exact elapsed milliseconds when the `thinking` routing decision is locked and when the parallel Stage-2 (`thinking="low"`) stream emits its first chunk. |
| **Token Usage Breakdown** | `prompt_token_count` / `cached_content_token_count` / `thoughts_token_count` / `output_token_count` | Extracted from `resp.usage_metadata` to quantify input size, Implicit Context Cache hits, internal reasoning tokens, and visible output tokens. |

All execution traces are serialized to human-readable YAML (`*_log.yaml`) and machine-readable JSON/JSONL (`*_log.json`, `*_runs.jsonl`, `*_turns.jsonl`), which are loaded directly by `examples/doc/gemini_latency/utils.py` to render every chart in this report.

---

## 2.5 Gemini 3.5 / 3.8 / 4 Model Lineup & Empirical API Option Verification

While Chapters 3–5 use **`gemini-3.8-flash`** as the primary benchmark baseline, Google AI Studio (Gemini API) has evolved significantly from the **Gemini 3.5 / 3.8 series** to the **Gemini 4 series (`Hydrogen` / `Argon` / `Carbon`)** in how `ThinkingConfig` (`thinking_level` vs. `thinking_budget`), **Context Caching** (Explicit vs. Implicit caching and the 2,050-token multi-turn uncached tail window), and sampling parameters behave.

This section synthesizes official documentation specifications and live API verification (`client.models.get()` and `generate_content()`) into three comprehensive reference tables (Tables 2-5A through 2-5C).

### 1. Active Model Lineup, Positioning, and Selection Criteria (Table 2-5A)

As of November 2026, legacy models `gemini-2.5-flash` (auto-routed to `gemini-3.5-flash-lite`), `gemini-2.5-pro` (auto-routed to `gemini-3.8-flash`), and `gemini-3.5-flash` (auto-routed to `gemini-3.6-flash`) are deprecated. Because **the Gemini 4 generation does not yet include a "Lite" tier model**, text and multimodal generation across all latency and reasoning tiers is covered by the **five active models (`3.5-flash-lite`, `3.8-flash`, `4-hydrogen`, `4-argon`, `4-carbon`)** summarized below.

| Model ID (`model`) | Status & Generation | Pricing (Input / Output per 1M tok) | Context Window / Single-Hop Output Cap | Default `thinking_level` | Positioning & Practical Selection Guidelines |
| :--- | :---: | :--- | :--- | :---: | :--- |
| **`gemini-3.5-flash`** | Deprecated<br>*(Auto-routed to `3.6-flash`)* | $1.50 / $7.50<br>*(3.6-flash pricing)* | Input `1,048,576`<br>Output `65,536` (separate) | `medium` | **[Deprecated 3.5 Flash]**<br>• API requests automatically route to `gemini-3.6-flash`.<br>• Migrate new workloads to `gemini-4-hydrogen` or `gemini-3.8-flash`. |
| **`gemini-3.5-flash-lite`** | **Active Stable**<br>*(Latest 3.x Lite)* | **$0.30 / $2.50** | Input `1,048,576`<br>Output `65,536` (separate) | **`minimal`**<br>*(0 thoughts)* | **[Fastest, Lowest-Cost Lite Workhorse]**<br>• Official recommended Lite model for new projects and the auto-migration target for `gemini-2.5-flash` (no Gemini 4 Lite exists yet).<br>• Defaults to `minimal` (`0` reasoning tokens) for ultra-fast routing, extraction, and classification; supports `medium` / `high` for autonomous subagent planning. |
| **`gemini-3.8-flash`** | **Active Stable**<br>*(Report Baseline)* | **$1.50 / $7.50** | Input `1,048,576`<br>Output `65,536` (separate) | `medium` | **[Final 3.x Flagship Flash]**<br>• Official migration target for `gemini-2.5-pro`. While `gemini-4-hydrogen` is recommended at the same price point, **`gemini-3.8-flash` remains preferred when (1) zero-thought (`0 tok`) low-latency execution via `thinking_level="low"` is required, or (2) Explicit Context Caching (`caches.create`) is needed**. |
| **`gemini-4-hydrogen`** | **Active Stable**<br>*(Recommended Flash Upgrade)* | **$1.50 / $7.50**<br>*(Free & Paid Tiers)* | **Unified 1M (`1,048,576`)**<br>Single-hop `65,536`<br>*(Long Decode up to 1M)* | **`high`** | **[Gemini 4 Mainstream Workhorse]**<br>• Same price as `3.8-flash` with stronger coding and agentic reasoning.<br>• Always-thinking architecture (thinking cannot be disabled), adding an exclusive **`xhigh`** level and **Long Decode (`automatic_continuation=True` up to 1M tokens)**. |
| **`gemini-4-argon`** | **Active Stable**<br>*(Paid Tier Only)* | **$2.00 / $10.00**<br>*($4 / $20 after Nov 30, 2026)* | **Unified 1M (`1,048,576`)**<br>REST `32,768` / Stream `65,536`<br>*(Long Decode up to 1M)* | `medium` | **[Efficient Frontier Reasoning (Pro Tier)]**<br>• Built for complex software architecture, math, and multi-step agentic tasks beyond `hydrogen`.<br>• Approaches `carbon` quality while spending fewer reasoning tokens and lower latency per turn. |
| **`gemini-4-carbon`** | **Active Stable**<br>*(Paid Tier Only)* | **$2.00 / $10.00**<br>*($4 / $20 after Nov 30, 2026)* | **Unified 1M (`1,048,576`)**<br>REST `32,768` / Stream `65,536`<br>*(Long Decode up to 1M)* | `medium` | **[Highest-Reasoning Frontier Model]**<br>• Spends the most reasoning tokens per turn; designed for the hardest software engineering, scientific reasoning, and cybersecurity tasks where accuracy outweighs latency. |

---

### 2. Model-by-Model `ThinkingConfig` (`thinking_level` vs. `thinking_budget`) Empirical Matrix (Table 2-5B)

In the Gemini API, numeric **`thinking_budget`** was introduced for the Gemini 2.5 series, whereas string enum **`thinking_level`** is the standard parameter for **Gemini 3 and Gemini 4**. Crucially, **`thinking_budget` is deprecated starting in Gemini 3**: to disable or minimize internal reasoning on Gemini 3+ models, developers should specify the model's lowest supported **`thinking_level`** (`"minimal"` or `"low"`) rather than `thinking_budget=0` (passing both `thinking_level` and `thinking_budget` simultaneously returns HTTP `400` on all models).

Table 2-5B compares all five `thinking_level` values (`minimal`, `low`, `medium`, `high`, `xhigh`) and legacy `thinking_budget` values (`0`, `256`, `4096`) across live API executions on a simple 1-word factual query versus a complex 5-person seating constraint puzzle (`usage_metadata.thoughts_token_count`).

| `ThinkingConfig` Parameter | `gemini-3.5-flash`<br>*(Auto-routed to `3.6-flash`)* | `gemini-3.5-flash-lite`<br>*(Active Lite)* | `gemini-3.8-flash`<br>*(Report Baseline)* | `gemini-4-hydrogen`<br>*(4 Mainstream)* | `gemini-4-argon` /<br>`gemini-4-carbon` |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **Supported `thinking_level`s** | **`minimal`, `low`, `medium`, `high`** (4 levels) | **`minimal`, `low`, `medium`, `high`** (4 levels) | **`low`, `medium`, `high`** (3 levels) | **`low`, `medium`, `high`, `xhigh`** (4 levels) | **`low`, `medium`, `high`** (3 levels) |
| **Unspecified (`None` / Default)** | Default = **`medium`**<br>Simple: `69 tok`<br>Complex: `2,711 tok` | Default = **`minimal`**<br>Simple: **`0 tok` (`None`)**<br>Complex: **`0 tok` (`None`)** | Default = **`medium`**<br>Simple: `0 tok` (`None`)<br>Complex: `1,303 tok` | Default = **`high`**<br>Simple: `68 tok`<br>Complex: `1,286 tok` | Default = **`medium`**<br>Dynamic reasoning |
| **`thinking_level="minimal"`** | ✅ **Supported (No-Thinking)**<br>Simple: **`0 tok`**<br>Complex: **`0 tok`** | ✅ **Supported (Default)**<br>Simple: **`0 tok`**<br>Complex: **`0 tok`** | ❌ **`400 INVALID_ARGUMENT`**<br>*(MINIMAL is not supported)* | ❌ **`400 INVALID_ARGUMENT`**<br>*(MINIMAL is not supported)* | ❌ **`400 INVALID_ARGUMENT`**<br>*(MINIMAL is not supported)* |
| **`thinking_level="low"`** | ✅ **Supported (Moderate)**<br>Simple: `70 tok`<br>Complex: `2,051 tok` | ✅ **Supported (Minimal)**<br>Simple: `41 tok`<br>Complex: **`0 tok`** | ✅ **Supported (Acts as 0 tok)**<br>Simple: **`0 tok`**<br>Complex: **`0 tok`** | ✅ **Supported (Always thinks)**<br>Simple: `35 tok`<br>Complex: `1,324 tok` | ✅ **Supported (Lowest)**<br>Simple: **`0 tok`**<br>Complex: Light reasoning |
| **`thinking_level="medium"`** | ✅ **Supported (Default)**<br>Simple: `73 tok`<br>Complex: `2,613 tok` | ✅ **Supported (Deep Thinking)**<br>Simple: `53 tok`<br>Complex: `4,175 tok` | ✅ **Supported (Default)**<br>Simple: `0 tok`<br>Complex: `1,403 tok` | ✅ **Supported**<br>Simple: `36 tok`<br>Complex: `1,528 tok` | ✅ **Supported (Default)** |
| **`thinking_level="high"`** | ✅ **Supported**<br>Simple: `70 tok`<br>Complex: `3,921 tok` | ✅ **Supported**<br>Simple: `58 tok`<br>Complex: `4,224 tok` | ✅ **Supported**<br>Simple: `61 tok`<br>Complex: `1,636 tok` | ✅ **Supported (Default)**<br>Simple: `67 tok`<br>Complex: `1,217 tok` | ✅ **Supported** |
| **`thinking_level="xhigh"`** | ❌ **`400 INVALID_ARGUMENT`**<br>*(XHIGH is not supported)* | ❌ **`400 INVALID_ARGUMENT`**<br>*(XHIGH is not supported)* | ❌ **`400 INVALID_ARGUMENT`**<br>*(XHIGH is not supported)* | ✅ **Supported (Hydrogen Only)**<br>Simple: `84 tok`<br>Complex: **`3,376 tok`** | ❌ **`400 INVALID_ARGUMENT`**<br>*(XHIGH is not supported)* |
| **`thinking_budget=0`**<br>*(Deprecated Legacy Param)* | ⚠️ Legacy compatible<br>Simple: **`0 tok`** / Complex: **`0 tok`** | ❌ **`400 INVALID_ARGUMENT`**<br>*(Rejected on 3.5-flash-lite)* | ⚠️ Legacy compatible<br>Simple: **`0 tok`** / Complex: **`0 tok`**<br>*(Used for benchmark `"0"`)* | ⚠️ **Maps to `low` (Warning)**<br>Simple: `32 tok` / Complex: `1,398 tok`<br>*(Does not disable thinking)* | ⚠️ Maps to nearest `thinking_level` (cannot disable thinking) |
| **`thinking_budget=256`**<br>*(Deprecated Legacy Param)* | ⚠️ Exceeds 256 cap<br>Simple: `63 tok` / Complex: `1,486 tok` | ⚠️ Exceeds 256 cap<br>Simple: `50 tok` / Complex: `2,009 tok` | ⚠️ Legacy compatible<br>Simple: **`0 tok`** / Complex: **`0 tok`**<br>*(Used for benchmark `"minimal"`)* | ⚠️ Maps to `thinking_level`<br>Simple: `69 tok` / Complex: `1,346 tok` | ⚠️ Maps to nearest `thinking_level` |
| **`thinking_budget=4096`**<br>*(Deprecated Legacy Param)* | ⚠️ Maps near `medium`/`high`<br>Simple: `68 tok` / Complex: `3,355 tok` | ⚠️ Maps near `medium`<br>Simple: `62 tok` / Complex: `3,449 tok` | ⚠️ **Intermediate thoughts**<br>Simple: `0 tok` / Complex: **`351–673 tok`**<br>*(Used for benchmark `"low"`)* | ⚠️ Maps to `thinking_level`<br>Complex: `1,471 tok` | ⚠️ Maps to nearest `thinking_level` |

---

### 3. Context Caching & API Parameter Evolution Across Generations (Table 2-5C)

| Feature / Parameter | `gemini-3.5-flash` / `gemini-3.5-flash-lite` | `gemini-3.8-flash`<br>*(Report Baseline)* | `gemini-4-hydrogen` / `argon` / `carbon` |
| :--- | :--- | :--- | :--- |
| **Implicit Context Caching**<br>*(Zero-Config Auto-Caching)* | ✅ **Enabled by default**<br>• Documented minimum: `4,096 tok`<br>• Bypasses prefill computation and discounts cached prefix tokens | ✅ **Enabled by default**<br>• Documented minimum: `4,096 tok`<br>• **Empirically activates at Turn 8 (`2,686 prompt_tokens`, `703 cached_tokens`) right after crossing `2,048 tok`** (Chapter 5) | ✅ **Enabled by default (95% discount)**<br>• Documented minimum: `4,096 tok`<br>• **Explicitly documents the `2,050-token` uncached tail rule in multi-turn loops** |
| **Multi-Turn Uncached Tail Window Rule**<br>*(Why caching starts above ~2,050 tok and leaves ~2,000 uncached tail tokens)* | Automatically caches matching prefixes while re-processing the trailing window at standard input rates. | In Chapter 5's 50-turn benchmark, **cache hits begin at Turn 8 (`2,686 tok`) and maintain a constant `Prompt - Cached ≈ 2,000 tokens` uncached tail across Turns 8–50**. | Gemini 4 documentation formally states:<br>*"Gemini caches the full previous request only if the new request adds at least **2,050 tokens**... For smaller additions, Gemini re-processes the last **2,050 tokens** of the previous request at the standard input rate."* |
| **Explicit Context Caching**<br>(`client.caches.create` / `createCachedContent`) | ✅ **Supported** (`v1beta`) | ✅ **Supported** (`v1beta`)<br>• Included in `supported_actions` | ❌ **Removed (Unsupported / Returns Error)**<br>• Standardized exclusively on Implicit Caching |
| **Sampling Parameters**<br>(`temperature`, `top_p`, `top_k`, `candidate_count`) | ⚠️ **Deprecated & Ignored**<br>• `candidate_count` unsupported | ⚠️ **Deprecated & Ignored**<br>• Fixed to optimal reasoning defaults | ⚠️ **Deprecated & Ignored**<br>• Ignored if in-range; out-of-range values return HTTP `400` |
| **Prefilled Model Turn Validation**<br>(`contents` ending with `role="model"`) | ❌ **Disallowed (`400` Error)**<br>*(Enforced from 3.6-flash / 3.5-flash-lite)* | ❌ **Disallowed (`400` Error)**<br>• Use `system_instruction` or `response_schema` instead | ❌ **Disallowed (`400` Error)** |

