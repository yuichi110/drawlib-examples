# 2. Background & Measurement Methodology

This chapter defines the foundational concepts and instrumentation methodology used throughout the empirical evaluations in Chapters 3–5. Sections 2.1 and 2.2 decompose LLM inference latency on `gemini-3.8-flash` into three sequential server-side phases (**Prefill, Thinking, and Decoding**), explain why **2D Trajectory Charts (`Elapsed Time vs. Cumulative Output Characters`)** expose critical user-experience differences hidden by scalar averages, and present clean Blocking vs. Streaming invocation patterns using the Google AI Studio `google-genai` SDK. Sections 2.3 and 2.4 examine **Pydantic Structured Outputs (`response_schema`)**, **Cold vs. Warm finite-state machine (FSM) grammar compilation**, incremental partial JSON delta extraction via **`pydantic_core.from_json(..., allow_partial="trailing-strings")`**, and the microsecond-precision **`ExecutionTracer`** (`src/gemini_evaluation/tracer.py`).

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
        "thoughts_token_count (+9.5 ms/tok)",
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

# Bottom Section: Side-by-Side 2D Trajectory Comparison (thinking=0)
ex_block = load_thinking_timeline("blocking", "0")
ex_stream = load_thinking_timeline("streaming", "0")

draw_trajectory_panel(
    x0=15.0,
    y0=12.5,
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
    y0=12.5,
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
text((118.0, 4.2), "Elapsed Time (ms) — Purple: TTFT Wait / Blue: Streaming", style=Styles.DarkBold.patch(text_size=10.0))

save()
```

---

## 2.1 Latency Definition & Trajectory Anatomy

To diagnose and optimize latency in conversational LLM applications, engineers must look beyond total request duration and decompose each API call into **three sequential server-side execution phases**:

### 1. The Three Phases of LLM Inference

1. **Phase 1: Prefill (Input Token Processing & KV Cache Lookup)**:
   The server processes the input payload—comprising `system_instruction`, multi-turn conversation `history`, and the latest user `prompt` (`prompt_token_count`)—in parallel across Transformer layers to populate the Attention Key-Value (KV) cache. On Google AI Studio (`gemini-3.8-flash`), when a conversation prefix matches an existing server-side cache entry (`cached_content_token_count`), prefill computation for those cached tokens is bypassed, keeping prefill latency flat even as multi-turn history grows beyond `21,000 tokens` (see Chapter 5).
2. **Phase 2: Thinking (Internal Reasoning Token Generation: `thoughts_token_count`)**:
   In reasoning-capable models such as `gemini-3.8-flash`, before emitting the very first visible response token (`chunk.text`), the model autoregressively generates internal Chain-of-Thought reasoning tokens (`usage_metadata.thoughts_token_count`). Crucially, **no visible text chunks are emitted to the client while the Thinking phase is in progress**, even when using `generate_content_stream`. Every internal reasoning token adds approximately **`+9.5 ms`** directly to the initial wait time (TTFT).
3. **Phase 3: Decoding (Autoregressive Visible Output Streaming: `output_token_count`)**:
   Once Prefill and Thinking conclude, the model autoregressively generates visible output tokens (`candidates_token_count` / `output_token_count`) until completion (`finish_reason = STOP`).

### 2. TTFT vs. Total Completion Time and Why 2D Trajectory Charts Matter

From these three phases, the two fundamental client-side latency metrics are defined as:

$$\text{TTFT}_{\text{streaming}} = T_{\text{Network RTT}} + T_{\text{Prefill}} + T_{\text{Thinking}}$$

$$\text{Total} = \text{TTFT}_{\text{blocking}} = T_{\text{Network RTT}} + T_{\text{Prefill}} + T_{\text{Thinking}} + T_{\text{Decoding}}$$

- **TTFT (Time to First Token / `time_to_first_token_ms`)**: Elapsed time from request initiation ($t = 0\text{ ms}$) until the first non-empty visible text chunk arrives at the client. TTFT directly governs **perceived responsiveness** in interactive UIs. In Blocking mode (`generate_content`), the response is withheld until decoding finishes, forcing $\text{TTFT} = \text{Total}$.
- **Total Completion Time (`stream_completed_ms`)**: Elapsed time from request initiation ($t = 0\text{ ms}$) until the final chunk (EOF) is received.
- **Why 2D Trajectory Charts (`Elapsed Time [ms] vs. Cumulative Output Characters`) Are Essential**:
  Comparing scalar completion times in Figure 2-1 (`thinking=0`) might suggest that Blocking (`3,360 ms`) and Streaming (`3,192 ms`) are nearly identical. However, plotting **Elapsed Time ($x$-axis) against Cumulative Visible Characters ($y$-axis)** reveals a stark difference in user experience:
  - **Blocking (Figure 2-1 Left)**: The UI remains frozen at $y = 0\text{ chars}$ for the entire **`3,360 ms`**, after which all 338 characters appear as a single vertical step function.
  - **Streaming (Figure 2-1 Right)**: Visible text begins rendering at **`1,205 ms` (`2,155 ms` or `64%` earlier than Blocking)** right after the purple prefill band, then climbs smoothly across the blue decoding band (`1,205 → 3,192 ms`) at `~190 chars/s`—far exceeding human reading speed (`~10 chars/s`). Thus, the entire decoding phase is hidden behind the user's reading time. Furthermore, in multi-stage architectures such as the Adaptive Thinking Router (Chapter 4), 2D trajectories expose the exact timing of the Stage-1 acknowledgment, the brief reading plateau during parallel Stage-2 reasoning, and the seamless continuation slope.

---

## 2.2 Blocking vs. Streaming API Usage (`google-genai` on Google AI Studio)

All benchmarks in this report (`src/gemini_evaluation/llm_call.py`) use the official **`google-genai`** SDK against **Google AI Studio** (`genai.Client(api_key=GEMINI_KEY)`) and `gemini-3.8-flash` via `asyncio` (`client.aio`). Below is the reference implementation for resolving all six `ThinkingConfig` options and invoking Blocking (`generate_content`) versus Streaming (`generate_content_stream`).

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


def build_thinking_config(thinking: str | int | None = 0) -> types.GenerateContentConfig | None:
    """Map the 6 thinking options (0, minimal, low, medium, high, default) to GenerateContentConfig."""
    if thinking is None or thinking == "default":
        return None  # Server default dynamic thinking
    if thinking in (0, "0"):
        return types.GenerateContentConfig(
            thinking_config=types.ThinkingConfig(thinking_budget=0)
        )
    level_map = {
        "minimal": types.ThinkingLevel.MINIMAL,
        "low": types.ThinkingLevel.LOW,
        "medium": types.ThinkingLevel.MEDIUM,
        "high": types.ThinkingLevel.HIGH,
    }
    return types.GenerateContentConfig(
        thinking_config=types.ThinkingConfig(thinking_level=level_map[str(thinking).lower()])
    )


# 2. Blocking Unary Call (waits for full completion: TTFT == Total)
async def generate_text_blocking(prompt: str, thinking: str | int | None = 0) -> str:
    resp = await client.aio.models.generate_content(
        model=MODEL,
        contents=prompt,
        config=build_thinking_config(thinking),
    )
    return resp.text or ""


# 3. Progressive Streaming Call (yields text chunks immediately after TTFT)
async def stream_text_progressive(prompt: str, thinking: str | int | None = 0) -> AsyncIterator[str]:
    stream = await client.aio.models.generate_content_stream(
        model=MODEL,
        contents=prompt,
        config=build_thinking_config(thinking),
    )
    async with aclosing(stream):
        async for chunk in stream:
            if chunk.text:
                yield chunk.text
```

---

## 2.3 Pydantic Structured Output & Partial JSON Streaming Mechanics

When building an adaptive router that decides whether a query requires deep reasoning (`thinking: bool`) while simultaneously streaming the user-facing reply (`response: str`), passing `response_mime_type="application/json"` and `response_schema=AdaptiveStreamResponse` to `GenerateContentConfig` enables **Constrained Decoding**.

To achieve sub-second streaming TTFT with structured JSON, engineers must understand two critical mechanics: **(1) Cold vs. Warm server-side FSM grammar compilation** and **(2) incremental partial JSON parsing via `pydantic_core.from_json`**. Figure 2-2 illustrates both the empirical Cold/Warm compilation benchmark (`load_schema_experiment()`, 8 runs) and the 4-step incremental delta extraction pipeline.

```drawlib align=center code=fold width=100% file=ch02_pydantic_cold_warm_pipeline.png caption="Figure 2-2: Pydantic response_schema Cold (#1) vs. Warm (#2–#4) Compilation Benchmark (2-Field vs. 6-Field) and Incremental Partial JSON Extraction Pipeline via pydantic_core.from_json"
from drawlib.canvas import save, setup
from drawlib.charts.bar import BarChart
from drawlib.icons import phosphor
from drawlib.lines import line
from drawlib.shapes import rectangle
from drawlib.styles import Styles
from drawlib.text import text
from drawlib.utils import load_schema_experiment

setup(width=158, height=90, dpi=150)

# Outer structural frame
rectangle((79.0, 45.0), width=154.0, height=86.0, style=Styles.MutedDashed.patch(shape_r=2.0))
text(
    (79.0, 84.2),
    "Pydantic Structured Streaming: Cold vs. Warm Schema Compilation & Partial JSON Pipeline",
    style=Styles.DarkBold.patch(text_size=11.5),
)

# ─── Top Section: Cold vs. Warm Schema Compilation Experiment ────────────────
exp = load_schema_experiment()
by_key = {(str(r["schema_label"]), int(r["run_index"])): r for r in exp}

ordered_groups = [
    ("2F #1\n(Cold)", [by_key[("minimal_2field", 1)]]),
    ("2F #2\n(Warm)", [by_key[("minimal_2field", 2)]]),
    ("2F #3–4\n(Warm Avg)", [by_key[("minimal_2field", 3)], by_key[("minimal_2field", 4)]]),
    ("6F #1\n(Warm 1st)", [by_key[("rich_6field", 1)]]),
    ("6F #2–4\n(Warm Avg)", [by_key[("rich_6field", 2)], by_key[("rich_6field", 3)], by_key[("rich_6field", 4)]]),
]
cats = [lbl for lbl, _ in ordered_groups]
ttft_vals = [round(sum(float(r["ttft_ms"]) for r in rows) / len(rows), 0) for _, rows in ordered_groups]
tot_vals = [round(sum(float(r["total_ms"]) for r in rows) / len(rows), 0) for _, rows in ordered_groups]

rectangle((55.0, 60.5), width=98.0, height=39.5, style=Styles.Neutral.patch(shape_r=1.4))
rectangle((55.0, 60.2), width=95.6, height=37.4, style=Styles.WhiteFlat.patch(shape_r=1.0))

chart = BarChart(
    axis_line_style=Styles.Dark,
    axis_text_style=Styles.DarkBold.patch(text_size=10.0),
    grid_style=Styles.MutedDashed,
    value_text_style=Styles.DarkBold.patch(text_size=10.0),
    value_format="{:,.0f}",
    width=86.0,
    height=25.0,
    categories=cats,
    orientation="vertical",
    bar_mode="group",
    bar_width_ratio=0.58,
    bar_r=0.3,
)
chart.configure_y_axis(min_value=0, max_value=7500, tick_step=2500, format="{:,.0f}")
chart.add_series(name="TTFT: First Token (ms)", values=ttft_vals, style=Styles.PrimaryFlat)
chart.add_series(name="Total: Completion (ms)", values=tot_vals, style=Styles.SecondaryNeutral)
chart.draw(xy=(14.5, 47.2))
chart.draw_legend(
    xy=(24.0, 75.2),
    text_style=Styles.DarkBold.patch(text_size=10.0),
    orientation="horizontal",
    swatch_width=3.2,
    swatch_height=1.8,
    item_gap=8.0,
)

# Right-side summary cards for Top Section
rectangle((129.5, 60.5), width=45.0, height=39.5, style=Styles.PrimaryNeutral.patch(shape_r=1.4))
text((129.5, 76.8), "Schema Experiment Insights", style=Styles.DarkBold.patch(text_size=10.4))

s_cards = [
    (
        68.2,
        "1. Cold #1 FSM Compilation",
        "1st call incurs ~1.6s FSM build\nCold TTFT 2,625 ms → Warm 975 ms",
        Styles.WhiteFlat,
    ),
    (
        56.6,
        "2. -62.9% Faster Once Warm",
        "2F Warm (#2–#4) avg TTFT 975 ms\nFlag decided at avg 895 ms",
        Styles.WhiteFlat,
    ),
    (
        45.0,
        "3. 2F vs 6F Differs by +58ms",
        "6F Warm avg TTFT is 1,033 ms\nField order governs streaming TTFT",
        Styles.SecondaryNeutral,
    ),
]
for cy, ch, cb, cst in s_cards:
    rectangle((129.5, cy), width=41.6, height=9.8, style=cst.patch(shape_r=0.9))
    text((129.5, cy + 2.4), ch, style=Styles.DarkBold.patch(text_size=10.0))
    text((129.5, cy - 1.8), cb, style=Styles.Dark.patch(text_size=10.0))

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
        'Input: \'{"thinking": false,\'\n→ {\'thinking\': False} (895ms)\nIf True: spawn Stage-2 task',
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

The table below and the top panel of Figure 2-2 present the 8-run schema compilation experiment (`src/gemini_evaluation/adaptive_thinking_log.json`), comparing the minimal 2-field `AdaptiveStreamResponse(thinking: bool, response: str)` (`minimal_2field`) against a 6-field `RichStreamResponse` (`rich_6field`, which adds two `Literal` enums, an escalation boolean, and a `list[str]` of follow-up questions) across four consecutive runs (`#1`–`#4`).

| Schema Variant (`schema_label`) | Run | Cache State | Flag Decided (`flag_decided_ms`) | First Token (`ttft_ms`) | Total Time (`total_ms`) | Output Chars |
| :--- | :-: | :-: | ---: | ---: | ---: | ---: |
| **`minimal_2field`** (`AdaptiveStreamResponse`) | **#1** | **Cold (1st)** | `3,215.9 ms` | **`2,625.2 ms`** | `3,190.7 ms` | `237 chars` |
| **`minimal_2field`** (`AdaptiveStreamResponse`) | **#2** | Warm | `752.6 ms` | **`847.3 ms`** | `1,488.1 ms` | `239 chars` |
| **`minimal_2field`** (`AdaptiveStreamResponse`) | **#3** | Warm | `902.8 ms` | **`918.0 ms`** | `1,396.0 ms` | `245 chars` |
| **`minimal_2field`** (`AdaptiveStreamResponse`) | **#4** | Warm | `1,029.2 ms` | **`1,159.2 ms`** | `1,604.6 ms` | `244 chars` |
| **`rich_6field`** (`RichStreamResponse`) | **#1** | Warm Engine* | `865.5 ms` | **`1,056.6 ms`** | `1,759.3 ms` | `250 chars` |
| **`rich_6field`** (`RichStreamResponse`) | **#2** | Warm | `790.7 ms` | **`976.8 ms`** | `1,516.5 ms` | `203 chars` |
| **`rich_6field`** (`RichStreamResponse`) | **#3** | Warm | `901.1 ms` | **`1,127.6 ms`** | `1,874.4 ms` | `247 chars` |
| **`rich_6field`** (`RichStreamResponse`) | **#4** | Warm | `786.7 ms` | **`995.9 ms`** | `1,719.5 ms` | `250 chars` |

- **Cold `#1` vs. Warm `#2–#4` (`-62.9%` TTFT Reduction)**:
  On the very first cold invocation (`minimal_2field #1`), compiling the JSON Schema into a constrained-decoding FSM adds a one-time `~1.6 s` overhead (`Cold #1 TTFT = 2,625.2 ms`). On subsequent calls (`#2–#4`), the compiled grammar is served from cache, dropping average TTFT to **`974.8 ms` (`847–1,159 ms`, `-62.9%`)** and resolving the `thinking` boolean at an average of **`894.9 ms`**.
- **Why Field Declaration Order—Not Field Count—Governs Streaming TTFT**:
  Once warm (`#2–#4`), expanding from 2 fields (`974.8 ms`) to 6 fields (`1,033.4 ms`) adds only **`+58.6 ms`** to TTFT. Because JSON tokens are generated strictly in schema declaration order, placing `thinking: bool` first, keeping only short scalar/enum fields before `response: str`, and placing variable-length arrays (`suggested_followups: list[str]`) *after* `response: str` ensures that visible text streaming begins immediately without waiting for auxiliary metadata lists.

### 2. Incremental Delta Extraction via `pydantic_core.from_json(..., allow_partial="trailing-strings")`

During `generate_content_stream`, intermediate chunks contain unclosed JSON fragments (such as `'{"thinking": false, "response": "Thank you for'`), causing the SDK's built-in `chunk.parsed` property to remain `None` until the stream finishes.

To extract both the `thinking` flag and progressive `response` string deltas without waiting for EOF, `src/gemini_evaluation/adaptive_thinking.py` uses Pydantic v2's Rust parser **`pydantic_core.from_json(raw_bytes, allow_partial="trailing-strings")`**:

1. **Safe Holding of Incomplete Primitives**: When the buffer ends mid-token (`'{"thinking": fa'`), `allow_partial="trailing-strings"` withholds the incomplete key-value pair and returns `{}`. The moment `false` or `true` completes, `{'thinking': False}` is locked in as a native Python `bool`.
2. **Escape-Safe String Slicing**: If a chunk boundary splits a JSON escape sequence at the end of `"response"` (e.g., `'..."1st line\\'`), `from_json` holds the trailing backslash until the next chunk arrives (`n` → `\n`). Tracking `emitted_resp_len` and slicing `delta = resp_so_far[emitted_resp_len:]` yields clean, decoded text deltas on every chunk.

```python
from typing import Any
from pydantic import BaseModel
from pydantic_core import from_json


class AdaptiveStreamResponse(BaseModel):
    thinking: bool  # Field 1: Routing boolean resolved at ~750–900 ms
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
