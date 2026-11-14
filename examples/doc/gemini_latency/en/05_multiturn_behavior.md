# 5. Multi-Turn Chat Behavior & Context Caching

In production conversational AI systems (such as PC technical support desks and interactive troubleshooting assistants), users engage in extended multi-turn dialogues rather than isolated single-turn prompts. Moreover, realistic customer-support sessions mix a majority of routine diagnostic/procedural turns (`80%`) with occasional complex multi-condition calculation turns (`20%`, such as estimating battery backup duration during a power outage, virtual-memory sizing, or 3-year repair-vs-replacement total cost of ownership).

In this chapter, we **standardize exclusively on Streaming (`generate_content_stream`)** and analyze empirical measurements from a **50-turn continuous PC troubleshooting customer-support chat benchmark** (`src/gemini_evaluation/benchmark_multiturn_chat.py` / `multiturn_chat_log.json`, `150 total API executions` across `50 turns × 3 Streaming configurations`) on Google AI Studio (`google-genai` SDK with `gemini-3.8-flash`). We evaluate **initial response time (`TTFT`)** and **stream completion time (`Total`)**, alongside Gemini 3.8 Flash's zero-configuration **Implicit Context Caching (`cached_content_token_count`)**, across:

1. **`(1)` Single-Model Fixed Streaming (`gemini-3.8-flash` `low` and `high`)**:
   - **`streaming_low` (`3.8-flash [low]` fixed)**: Streams all 50 turns with `thinking_level="low"`.
   - **`streaming_high` (`3.8-flash [high]` fixed)**: Streams all 50 turns with `thinking_level="high"`.
2. **`(2)` Chapter 4's Adaptive Thinking Router (`adaptive_pat_a`: Pattern A `low → high`)**:
   - Streams the 2-field integrated Pydantic schema `{thinking: bool, response: str}` in Stage 1 (`3.8-flash [low]`). On the 40 routine turns (`thinking=false`), Stage 1 answers directly in a single API call; on the 10 complex calculation turns (`thinking=true`: every 5th turn `T5, 10, ..., 50`), Stage 1 streams a 1-sentence bridge message in ~2.85s while launching Stage 2 (`3.8-flash [high]`) in parallel to stream the verified calculation.

```drawlib align=center code=fold width=100% file=ch5_multiturn_hero.png caption="Figure 5-1: 50-Turn PC Support Multi-Turn Streaming Architecture & 3-Configuration TTFT / Total Comparison (gemini-3.8-flash)"
from drawlib.canvas import save, setup
from drawlib.icons import phosphor
from drawlib.lines import line
from drawlib.shapes import rectangle
from drawlib.styles import Styles
from drawlib.text import text

setup(width=156, height=82, dpi=150)

# Outer structural frame
rectangle((78, 41), width=152, height=78, style=Styles.MutedDashed.patch(shape_r=2.0))
text(
    (78, 76.0),
    "50-Turn PC Support Streaming Benchmark: (1) 3.8-flash low/high vs (2) Adaptive Thinking Router",
    style=Styles.DarkBold.patch(text_size=11.2),
)

# Top pipeline band: 50-Turn Evaluation Loop
rectangle((78, 61.2), width=146, height=18.0, style=Styles.PrimaryNeutral.patch(shape_r=1.5))
text(
    (78, 67.6),
    "Per-Turn Streaming Pipeline (40 Routine Turns [80%] + 10 Multi-Step Math Turns [20%: T5,10..50] with Rotated Call Order)",
    style=Styles.DarkBold.patch(text_size=10.0),
)

loop_steps = [
    (22.0, 29.5, "1. User Simulator", "gemini-3.8-flash (low)\n80% routine + 20% math (103 ch)", Styles.WhiteFlat),
    (57.5, 31.5, "2. History + New Turn", "history: list[Content]\n180 → 20,899 tok (37,531 ch)", Styles.WhiteFlat),
    (95.0, 34.0, "3. Implicit Cache Hit", "Auto-active at T8–9 (~2.7k tok)\n87.1% avg T41–50 (max 90.2%)", Styles.SecondaryNeutral),
    (132.5, 31.0, "4. 3 Streaming Configs", "Record Initial Response (TTFT)\n& Completion (Total) on all 50T", Styles.WhiteFlat),
]
for cx, w, st_top, st_bot, box_st in loop_steps:
    rectangle((cx, 58.4), width=w, height=10.8, style=box_st.patch(shape_r=1.2, line_width=0.8))
    text((cx, 61.2), st_top, style=Styles.DarkBold.patch(text_size=10.0))
    text((cx, 56.0), st_bot, style=Styles.Dark.patch(text_size=9.8))

line((36.8, 58.4), (41.7, 58.4), arrow_head="->", style=Styles.DarkBold)
line((73.3, 58.4), (78.0, 58.4), arrow_head="->", style=Styles.DarkBold)
line((112.0, 58.4), (117.0, 58.4), arrow_head="->", style=Styles.DarkBold)

# Left Column: (1) Single-Model Fixed Streaming (low vs high)
phosphor.lightning((7.5, 48.0), width=3.2, style=Styles.DarkBold)
text(
    (10.5, 48.0),
    "(1) Single-Model Fixed Streaming: 3.8-flash low vs high",
    style=Styles.DarkBold.patch(text_size=10.4, halign="left"),
)

# Card 1A: streaming_low
rectangle((42.0, 36.8), width=72.0, height=16.0, style=Styles.Neutral.patch(shape_r=1.4))
text(
    (7.8, 42.2),
    "1. streaming_low (gemini-3.8-flash [low] fixed)",
    style=Styles.DarkBold.patch(text_size=10.0, halign="left"),
)
text(
    (7.8, 38.4),
    "• Initial TTFT: Avg 2,310 ms (Med 2,084 ms | Routine 2,304 / Math 2,336 ms)",
    style=Styles.Dark.patch(text_size=9.5, halign="left"),
)
text(
    (7.8, 34.8),
    "• Completion Total: Avg 6,589 ms (Med 6,583 ms | Avg 0 thinking tokens)",
    style=Styles.Dark.patch(text_size=9.5, halign="left"),
)
text(
    (7.8, 31.2),
    "• Issue: Fast on all turns, but 0 thinking tokens on the 10 math turns",
    style=Styles.Dark.patch(text_size=9.5, halign="left"),
)

# Card 1B: streaming_high
rectangle((42.0, 19.6), width=72.0, height=15.6, style=Styles.Neutral.patch(shape_r=1.4))
text(
    (7.8, 24.8),
    "2. streaming_high (gemini-3.8-flash [high] fixed)",
    style=Styles.DarkBold.patch(text_size=10.0, halign="left"),
)
text(
    (7.8, 21.0),
    "• Initial TTFT: Avg 21,173 ms (Routine 16,958 ms / Math 38,033 ms)",
    style=Styles.Dark.patch(text_size=9.5, halign="left"),
)
text(
    (7.8, 17.4),
    "• Completion Total: Avg 23,827 ms (Routine 19,683 ms / Math 40,404 ms)",
    style=Styles.Dark.patch(text_size=9.5, halign="left"),
)
text(
    (7.8, 13.8),
    "• Issue: Wastes 1,534 thinking tokens (~17s freeze) on 40 routine turns",
    style=Styles.Dark.patch(text_size=9.5, halign="left"),
)

# Vertical divider
line((80.0, 12.0), (80.0, 49.5), style=Styles.MutedDashed.patch(line_width=1.0))

# Right Column: (2) Chapter 4 Adaptive Thinking Router (Pattern A: low -> high)
phosphor.star((84.2, 48.0), width=3.2, style=Styles.DarkBold)
text(
    (87.2, 48.0),
    "(2) Recommended: Ch.4 Adaptive Thinking Router (Pattern A)",
    style=Styles.DarkBold.patch(text_size=10.2, halign="left"),
)

rectangle((116.5, 28.2), width=69.0, height=33.2, style=Styles.PrimaryFlat.patch(shape_r=1.6))
text(
    (84.2, 41.8),
    "3. adaptive_pat_a (Stage 1: low → Parallel Stage 2: high)",
    style=Styles.WhiteBold.patch(text_size=9.8, halign="left"),
)
text(
    (84.2, 37.4),
    "• Routing Accuracy: 50 / 50 (100%) Match (40 Routine, 10 Math)",
    style=Styles.WhiteBold.patch(text_size=9.5, halign="left"),
)
text(
    (84.2, 33.2),
    "• Initial TTFT: Avg 2,618 ms (Med 2,420 ms / P95 3,841 ms)",
    style=Styles.White.patch(text_size=9.5, halign="left"),
)
text(
    (86.0, 29.4),
    "→ Routine 40T: 2,560 ms direct | Math 10T: 2,851 ms bridge",
    style=Styles.White.patch(text_size=9.5, halign="left"),
)
text(
    (84.2, 25.2),
    "• Completion Total: Avg 12,034 ms (Med 4,990 ms)",
    style=Styles.White.patch(text_size=9.5, halign="left"),
)
text(
    (86.0, 21.4),
    "→ Routine 40T: 5,008 ms | Math 10T: Stage 2 high (40,142 ms)",
    style=Styles.White.patch(text_size=9.5, halign="left"),
)
text(
    (84.2, 16.8),
    "• Stage 1→2 Cache Share: Stage 2 hits 90.2% (18,890 tok) at T50",
    style=Styles.WhiteBold.patch(text_size=9.5, halign="left"),
)

# Bottom architectural insight banner
rectangle((78.0, 6.2), width=146.0, height=6.0, style=Styles.SecondaryNeutral.patch(shape_r=1.2))
text(
    (78.0, 6.2),
    "Takeaway: Adaptive Thinking cuts TTFT by 87.6% (21.2s → 2.6s) and thinking tokens by 61.7% vs high while preserving math accuracy.",
    style=Styles.DarkBold.patch(text_size=9.5),
)

save()
```

---

## 5.1 50-Turn PC Support Streaming Benchmark Architecture & Methodology

### 1. Multi-Turn History Accumulation & Adaptive Routing in `google-genai`

Because the Gemini API is stateless across individual HTTP/gRPC requests, multi-turn chat in `google-genai` requires the application to maintain an ordered conversation list `history: list[types.Content]` (alternating `role="user"` and `role="model"` entries) and send the accumulated history plus the new user message on every turn (`src/gemini_evaluation/llm_call.py` and `src/gemini_evaluation/adaptive_thinking.py`):

```python
from google import genai
from google.genai import types

client = genai.Client(api_key=GEMINI_KEY)

# Append the current turn's user message to the accumulated history: list[types.Content]
contents: list[types.Content] = [
    *history,
    types.Content(role="user", parts=[types.Part.from_text(text=user_prompt)]),
]

# (1) Single-model fixed Streaming (thinking_level="low" or "high")
response_stream = await client.aio.models.generate_content_stream(
    model="gemini-3.8-flash",
    contents=contents,
    config=types.GenerateContentConfig(
        system_instruction=AGENT_SYSTEM_INSTRUCTION,
        thinking_config=types.ThinkingConfig(thinking_level="low"),  # or "high"
        temperature=0.2,
    ),
)
```

In our 50-turn benchmark (`src/gemini_evaluation/benchmark_multiturn_chat.py`), we simulate **a customer and a PC technical support specialist troubleshooting an unresponsive PC** across a realistic mix of **40 routine procedural turns (`80%`)** and **10 multi-condition numerical calculation turns (`20%`: every 5th turn)**:

1. **User Simulator (`gemini-3.8-flash`, `thinking_level="low"`)**:
   Generates a natural customer question (`avg 103.4 chars`) at each of the 50 troubleshooting stages:
   - **40 Routine Troubleshooting Turns (`expected_thinking=False`)**: Power/AC adapter checks, 30-second discharge, BIOS check, Safe Mode boot, driver rollback, `sfc /scannow`, clean boot, BitLocker recovery key lookup, repair packaging, and post-repair checks.
   - **10 Complex Multi-Condition Calculation Turns (`expected_thinking=True` at `Turns 5, 10, 15, 20, 25, 30, 35, 40, 45, 50`)**: Two turns per 10-turn cohort require exact multi-step arithmetic (e.g., Turn 5: `18 GB` USB backup feasibility on a `36 Wh` battery at `45 W` drain during a blackout; Turn 25: `pagefile.sys` + `hiberfil.sys` disk footprint on a `32 GB RAM` PC; Turn 40: standard warranty vs. accidental damage deductible comparison; Turn 50: 3-year cloud + external SSD backup TCO and `99.5%` SLA downtime budget).
2. **3 Streaming Configurations Evaluated with Rotated Call Order (`rot = (turn - 1) % 3`)**:
   Across all 50 turns (`180 → 20,899 prompt_tokens`, `37,531 cumulative chars`), we evaluate 3 Streaming configurations on the exact same `history`, rotating execution order every turn (using the `streaming_low` reply averaging `647.2 chars` as the canonical history entry):

| Streaming Configuration | Stage 1 / Single Config | Stage 2 (`thinking=true`) | Initial `TTFT` Avg (Med / P95) | Completion `Total` Avg (Med / P95) | Avg Thinking Tokens | Behavior Across 40 Routine vs. 10 Complex Turns |
| :--- | :--- | :--- | ---: | ---: | ---: | :--- |
| **`(1)` `streaming_low`** | `3.8-flash [low]` | — (Single Call) | **`2,310 ms`** (`2,084` / `4,269 ms`) | **`6,589 ms`** (`6,583` / `8,397 ms`) | `0 tok` | Fast on all turns, but uses `0` thinking tokens on the 10 complex math turns |
| **`(1)` `streaming_high`** | `3.8-flash [high]` | — (Single Call) | `21,173 ms` (`22,012` / `41,657 ms`) | `23,827 ms` (`23,887` / `43,621 ms`) | `1,981 tok` | Deep reasoning on math turns (`3,772 tok`), but stalls ~17.0s (`1,534 tok`) on routine turns |
| **`(2)` ★`adaptive_pat_a`**<br>(Ch.4 Pattern A) | `3.8-flash [low]`<br>(`{thinking, response}`) | `3.8-flash [high]`<br>(Parallel + Cache Share) | **`2,618 ms`** (`2,420` / **`3,841 ms`**) | **`12,034 ms`** (**`4,990`** / `43,215 ms`) | **`758 tok`**<br>(`-61.7%`) | **`50/50 (100%)` accuracy**: Routine 40T finish in `2,560 / 5,008 ms`; Math 10T stream bridge at `2,851 ms` + Stage 2 `high` (`40,142 ms`) |

---

## 5.2 Input Token Growth & Automatic Implicit Context Caching (With Stage 1 → Stage 2 Cache Sharing)

As each `(user, model)` message pair is appended to `history`, `prompt_token_count` grows linearly at **`~+423 tokens/turn`** (`180 tokens` at Turn 1 → `2,710 tokens` at Turn 8 → `9,523 tokens` at Turn 25 → **`20,899 tokens`** at Turn 50).

Crucially, **once input context reaches `~2,710–3,050 tokens` at Turns 8–9, Gemini 3.8 Flash's automatic Implicit Context Caching (`usage_metadata.cached_content_token_count`) activates without any explicit cache API calls—and on complex calculation turns (`T10..T50`), Stage 2 (`high`) of `adaptive_pat_a` reuses the exact same cached history prefix warmed by Stage 1 (`low`)**.

```drawlib align=center code=fold width=100% file=ch5_token_cache_growth.png caption="Figure 5-2: 50-Turn Input Token Growth (prompt_tokens vs cached_tokens vs Uncached Delta ~2,400 tok)"
from drawlib.canvas import save, setup
from drawlib.charts.line import LineChart
from drawlib.icons import phosphor
from drawlib.lines import line
from drawlib.shapes import rectangle
from drawlib.styles import Styles
from drawlib.text import text
from drawlib.utils import load_multiturn_turns

setup(width=156, height=86, dpi=150)

# Outer structural frame
rectangle((78.0, 43.0), width=152.0, height=82.0, style=Styles.MutedDashed.patch(shape_r=2.0))
text(
    (78.0, 80.0),
    "50-Turn Input Token Growth & Automatic Implicit Context Caching (cached_content_token_count)",
    style=Styles.DarkBold.patch(text_size=11.5),
)

# Load 50-turn token & implicit cache metrics dynamically from benchmark JSONL
turns = load_multiturn_turns()
categories = [
    f"T{t}" if t in {1, 5, 10, 15, 20, 25, 30, 35, 40, 45, 50} else ""
    for t in range(1, 51)
]
prompt_vals = [float(t["variants"]["streaming_low"]["prompt_tokens"]) for t in turns]
cached_vals = [float(t["variants"]["adaptive_pat_a"]["cached_tokens"]) for t in turns]
uncached_vals = [max(p - c, 0.0) for p, c in zip(prompt_vals, cached_vals)]

# Left Card: LineChart container
rectangle(
    (50.5, 39.5),
    width=93.0,
    height=71.0,
    style=Styles.WhiteFlat.patch(shape_r=1.6, line_width=0.9),
)

# Legend backdrop band at top of left card
rectangle((50.5, 65.2), width=88.0, height=14.8, style=Styles.Neutral.patch(shape_r=1.2))

chart = LineChart(
    axis_line_style=Styles.Dark,
    categories=categories,
    width=84.0,
    height=42.5,
    smooth=False,
    show_points=False,
    axis_text_style=Styles.Dark.patch(text_size=10.0),
    grid_style=Styles.MutedDashed,
)
chart.add_series(
    "Total Input Tokens (prompt_tokens: 180 → 20,899)",
    prompt_vals,
    style=Styles.PrimaryFlat,
    line_width=2.6,
    point_shape="none",
)
chart.add_series(
    "Implicit Cache Hits (Stage1 18,507 / Stage2 18,890)",
    cached_vals,
    style=Styles.SuccessFlat,
    line_width=2.4,
    point_shape="none",
)
chart.add_series(
    "Uncached Prefill Delta (prompt - cached: ~2,400 tok)",
    uncached_vals,
    style=Styles.SecondaryFlat,
    line_width=2.0,
    line_style="dashed",
    point_shape="none",
)
chart.configure_y_axis(
    min_value=0.0,
    max_value=24000.0,
    tick_step=6000.0,
    format="{:,.0f}",
)
chart.draw(xy=(8.5, 9.5))
chart.draw_legend(
    xy=(10.5, 70.0),
    text_style=Styles.DarkBold.patch(text_size=9.5),
    orientation="vertical",
    item_gap=1.3,
)

# Axis labels
text((9.5, 54.0), "Tokens (tok)", style=Styles.DarkBold.patch(text_size=10.0, halign="left"))
text((51.5, 6.2), "Conversation Turn (Turn 1 to Turn 50)", style=Styles.DarkBold.patch(text_size=10.0))

# Callout annotation inside chart pointing to Turn 8-9 cache activation
rectangle((48.5, 36.5), width=38.0, height=8.0, style=Styles.Neutral.patch(shape_r=1.0))
text(
    (48.5, 38.3),
    "Turns 8–9 (~2,710 tok threshold)",
    style=Styles.DarkBold.patch(text_size=9.5),
)
text(
    (48.5, 34.7),
    "Auto Cache Active (88–90.2% at T50)",
    style=Styles.Dark.patch(text_size=9.5),
)
line((38.0, 32.5), (24.0, 15.0), arrow_head="->", style=Styles.DarkBold.patch(line_width=1.6))

# Right Panel: Neutral Summary Card Panel
rectangle((125.5, 39.5), width=51.0, height=71.0, style=Styles.Neutral.patch(shape_r=1.6))
phosphor.chart_line_up((103.5, 70.8), width=3.4, style=Styles.DarkBold)
text(
    (106.8, 70.8),
    "Implicit Context Caching Insights",
    style=Styles.DarkBold.patch(text_size=10.5, halign="left"),
)

summary_cards = [
    (
        59.2,
        "1. Linear Growth (~+423 tok/turn)",
        "User (~103 ch) + Agent (~647 ch) pairs\ngrow input from 180 to 20,899 tokens",
    ),
    (
        43.8,
        "2. Zero-Config Activation at T8–9",
        "Crossing ~2,710 tokens at Turns 8–9\ntriggers KV cache hits automatically",
    ),
    (
        28.4,
        "3. Stage 1→2 Prefix Cache Sharing",
        "Parallel Stage 2 (high) reuses Stage 1\ncache, hitting 18,890 tok (90.2%) at T50",
    ),
    (
        13.0,
        "4. Uncached Delta Bounded (~2,400 tok)",
        "New prefill work stays flat around ~2.4k\ntokens, keeping TTFT at ~2.3–2.6s",
    ),
]

for cy, hdr, body in summary_cards:
    rectangle((125.5, cy), width=47.4, height=13.4, style=Styles.WhiteFlat.patch(shape_r=1.2, line_width=0.7))
    text((103.2, cy + 3.6), hdr, style=Styles.DarkBold.patch(text_size=9.8, halign="left"))
    text((103.2, cy - 2.0), body, style=Styles.Dark.patch(text_size=9.6, halign="left"))

save()
```

### How Implicit Context Caching Accelerates Both Single-Call and Adaptive Multi-Turn Streaming

1. **Zero-Configuration Activation at Turns 8–9 (`~2,710–3,050 Tokens`)**:
   During Turns 1–7 (`180–2,369 prompt_tokens`), `cached_content_token_count` remains `0`. Once the accumulated prefix reaches **Turn 8 (`2,710 tokens`, `633 cached tokens` on `adaptive_pat_a`)** and **Turn 9 (`3,050 tokens`, `728–956 cached tokens`)**, Gemini 3.8 Flash automatically caches the shared history prefix. Across **Turns 41–50**, the average cache hit rate reaches **`87.1%–87.7%`**.
2. **Stage 1 → Stage 2 Prefix Cache Sharing in `adaptive_pat_a`**:
   Because `adaptive_pat_a` uses the exact same `AGENT_SYSTEM_INSTRUCTION` for both Stage 1 and Stage 2 (appending Stage 1's routing instruction to the final user turn rather than mutating the system prompt), Stage 2 (`thinking_level="high"`) immediately hits the warmed KV cache on complex turns (`18,507 cached tokens` in Stage 1 and **`18,890 cached tokens [90.2%]` in Stage 2** at Turn 50).

---

## 5.3 50-Turn Evolution of Initial Response (`TTFT`) vs. Completion Time (`Total`)

To compare `(1) 3.8-flash low & high` and `(2) Adaptive Thinking Router (Pattern A)` without visual clutter, Figure 5-3 separates **Initial Response (`TTFT`) on the Left Panel** from **Stream Completion (`Total`) on the Right Panel** across all 50 turns.

```drawlib align=center code=fold width=100% file=ch5_latency_evolution_2panel.png caption="Figure 5-3: 2-Panel 50-Turn Streaming Latency Evolution (Left: Initial Response TTFT, Right: Stream Completion Total)"
from drawlib.canvas import save, setup
from drawlib.charts.line import LineChart
from drawlib.lines import line
from drawlib.shapes import circle, rectangle
from drawlib.styles import Styles
from drawlib.text import text
from drawlib.utils import load_multiturn_turns

setup(width=156, height=90, dpi=150)

# Outer structural frame
rectangle((78.0, 45.0), width=152.0, height=86.0, style=Styles.MutedDashed.patch(shape_r=2.0))
text(
    (78.0, 84.0),
    "50-Turn Streaming Latency Evolution (180 → 20,899 tok): Initial TTFT (Left) vs Completion Total (Right)",
    style=Styles.DarkBold.patch(text_size=11.2),
)

turns = load_multiturn_turns()
labeled_turns = {1, 10, 20, 30, 40, 50}
categories = [f"T{t['turn']}" if int(t["turn"]) in labeled_turns else "" for t in turns]

low_ttft = [float(t["variants"]["streaming_low"]["ttft_ms"]) for t in turns]
high_ttft = [float(t["variants"]["streaming_high"]["ttft_ms"]) for t in turns]
adap_ttft = [float(t["variants"]["adaptive_pat_a"]["ttft_ms"]) for t in turns]

low_total = [float(t["variants"]["streaming_low"]["total_ms"]) for t in turns]
high_total = [float(t["variants"]["streaming_high"]["total_ms"]) for t in turns]
adap_total = [float(t["variants"]["adaptive_pat_a"]["total_ms"]) for t in turns]

# =========================================================================
# Left Panel: Initial Response (TTFT) across 50 Turns
# =========================================================================
rectangle((42.5, 45.5), width=71.0, height=69.0, style=Styles.WhiteFlat.patch(shape_r=1.5, line_width=0.8))
rectangle((42.5, 73.2), width=67.0, height=11.6, style=Styles.Neutral.patch(shape_r=1.1))
text(
    (42.5, 76.6),
    "Left: Initial TTFT (Adaptive 2.62s & low 2.31s vs high 21.17s)",
    style=Styles.DarkBold.patch(text_size=9.5),
)

# Legend for Left Panel
line((10.0, 72.8), (13.6, 72.8), style=Styles.PrimaryBold.patch(line_width=2.6))
circle((11.8, 72.8), radius=0.6, style=Styles.PrimaryFlat)
text((14.4, 72.8), "★adaptive_pat_a (Avg 2,618ms / Med 2,420ms)", style=Styles.DarkBold.patch(text_size=9.6, halign="left"))

line((10.0, 69.4), (13.6, 69.4), style=Styles.TealBold.patch(line_width=2.0))
text((14.4, 69.4), "streaming_low (2,310ms)", style=Styles.Dark.patch(text_size=9.6, halign="left"))

line((44.5, 69.4), (48.1, 69.4), style=Styles.DangerBold.patch(line_width=2.0))
text((48.9, 69.4), "streaming_high (21,173ms)", style=Styles.Dark.patch(text_size=9.6, halign="left"))

chart_left = LineChart(
    axis_line_style=Styles.Dark,
    axis_text_style=Styles.Dark.patch(text_size=9.8),
    grid_style=Styles.MutedDashed,
    categories=categories,
    width=59.0,
    height=42.0,
    show_points=True,
    point_shape="circle",
    point_size=0.42,
)
chart_left.configure_x_axis(show_grid=False)
chart_left.configure_y_axis(
    min_value=0,
    max_value=60000,
    tick_step=15000,
    format="{:,.0f}",
)
chart_left.add_series(
    name="streaming_high TTFT",
    values=[min(v, 59500.0) for v in high_ttft],
    style=Styles.DangerFlat,
    line_width=1.8,
    point_size=0.38,
)
chart_left.add_series(
    name="streaming_low TTFT",
    values=low_ttft,
    style=Styles.TealFlat,
    line_width=2.0,
    point_size=0.38,
)
chart_left.add_series(
    name="adaptive_pat_a TTFT",
    values=adap_ttft,
    style=Styles.PrimaryFlat,
    line_width=2.5,
    point_size=0.48,
)
chart_left.draw(xy=(14.5, 19.5))
text((10.0, 63.8), "Initial TTFT (ms)", style=Styles.DarkBold.patch(text_size=9.8, halign="left"))
text((42.5, 14.2), "Turn Number (Adaptive & low stay at ~2–3s across all 50T)", style=Styles.DarkBold.patch(text_size=9.5))

# =========================================================================
# Right Panel: Stream Completion (Total) across 50 Turns
# =========================================================================
rectangle((115.5, 45.5), width=71.0, height=69.0, style=Styles.WhiteFlat.patch(shape_r=1.5, line_width=0.8))
rectangle((115.5, 73.2), width=67.0, height=11.6, style=Styles.Neutral.patch(shape_r=1.1))
text(
    (115.5, 76.6),
    "Right: Completion Total (5.0s Routine 40T; Deep high Math 10T)",
    style=Styles.DarkBold.patch(text_size=9.5),
)

# Legend for Right Panel
line((83.0, 72.8), (86.6, 72.8), style=Styles.PrimaryBold.patch(line_width=2.6))
circle((84.8, 72.8), radius=0.6, style=Styles.PrimaryFlat)
text((87.4, 72.8), "★adaptive_pat_a (Med 4,990ms / Avg 12,034ms)", style=Styles.DarkBold.patch(text_size=9.6, halign="left"))

line((83.0, 69.4), (86.6, 69.4), style=Styles.TealBold.patch(line_width=2.0))
text((87.4, 69.4), "streaming_low (6,589ms)", style=Styles.Dark.patch(text_size=9.6, halign="left"))

line((117.5, 69.4), (121.1, 69.4), style=Styles.DangerBold.patch(line_width=2.0))
text((121.9, 69.4), "streaming_high (23,827ms)", style=Styles.Dark.patch(text_size=9.6, halign="left"))

rx0, ry0, rpw, rph = 87.5, 19.5, 59.0, 42.0

chart_right = LineChart(
    axis_line_style=Styles.Dark,
    axis_text_style=Styles.Dark.patch(text_size=9.8),
    grid_style=Styles.MutedDashed,
    categories=categories,
    width=rpw,
    height=rph,
    show_points=True,
    point_shape="circle",
    point_size=0.42,
)
chart_right.configure_x_axis(show_grid=False)
chart_right.configure_y_axis(
    min_value=0,
    max_value=60000,
    tick_step=15000,
    format="{:,.0f}",
)
chart_right.add_series(
    name="streaming_high Total",
    values=[min(v, 59500.0) for v in high_total],
    style=Styles.DangerFlat,
    line_width=1.8,
    point_size=0.38,
)
chart_right.add_series(
    name="streaming_low Total",
    values=low_total,
    style=Styles.TealFlat,
    line_width=2.0,
    point_size=0.38,
)
chart_right.add_series(
    name="adaptive_pat_a Total",
    values=adap_total,
    style=Styles.PrimaryFlat,
    line_width=2.5,
    point_size=0.48,
)
chart_right.draw(xy=(rx0, ry0))
text((83.0, 63.8), "Completion Total (ms)", style=Styles.DarkBold.patch(text_size=9.8, halign="left"))
text((115.5, 14.2), "Turn Number (10 spikes mark math turns T5,10..50)", style=Styles.DarkBold.patch(text_size=9.5))

# Bottom callout bar
rectangle((78.0, 6.2), width=146.0, height=6.0, style=Styles.PrimaryNeutral.patch(shape_r=1.2))
text(
    (78.0, 6.2),
    "Takeaway: adaptive_pat_a stays near ~2.6s TTFT (left) while selectively activating Stage 2 reasoning on the 10 math turns (right).",
    style=Styles.DarkBold.patch(text_size=9.5),
)

save()
```

### Key Architectural Observations from Figure 5-3

1. **Left Panel (Initial Response `TTFT`): `adaptive_pat_a` and `streaming_low` Stay Flat at `~2.3–2.6s` Across All 50 Turns**:
   - The red curve (`streaming_high`) stalls for an average of **`16,958 ms`** on the 40 routine turns (`1,534` thinking tokens) and **`38,033 ms`** on the 10 calculation turns (**`21,173 ms` overall average**) before emitting a single visible character.
   - By contrast, the solid blue curve (**`adaptive_pat_a`**, avg **`2,618 ms`**, median **`2,420 ms`**, P95 **`3,841 ms`**) tracks the teal curve (**`streaming_low`**, avg **`2,310 ms`**, median **`2,084 ms`**) along the bottom of the chart across all 50 turns—streaming direct answers in `2,560 ms` on routine turns and immediate 1-sentence bridges in `2,851 ms` on complex calculation turns.
2. **Right Panel (Stream Completion `Total`): Fast `5.0s` Routine Completion + Selective `40.1s` Deep Calculation**:
   - On the 40 routine turns (`expected_thinking=False`), `adaptive_pat_a` finishes in a single Stage 1 (`low`) call averaging **`5,008 ms` (`4,695 ms` median)**—even faster than `streaming_low` (`6,411 ms`) due to concise structured output.
   - Exclusively on the 10 shaded calculation turns (`Turns 5, 10, 15, 20, 25, 30, 35, 40, 45, 50`), `adaptive_pat_a` rises to match `streaming_high` (`40,142 ms` vs. `40,404 ms`, generating an average of `3,671` thinking tokens in Stage 2). Across all 50 turns, `adaptive_pat_a` reduces median completion time by **`-79.1%`** (`4,990 ms` vs. `23,887 ms`) and mean completion time by **`-49.5%`** (`12,034 ms` vs. `23,827 ms`).

---

## 5.4 Bifurcated Thinking Token Distribution & 3-Turn Stream Trajectories (Turns 1, 25, and 50)

To examine how internal thinking tokens (`thoughts_token_count`) govern completion time and how chunks arrive during early (**Turn 1**: routine), mid (**Turn 25**: complex math), and late (**Turn 50**: complex math) turns, Figure 5-4 pairs a **scatter plot of `thoughts_tokens` vs `total_ms` across all 150 runs (`50 turns × 3 Streaming configs`)** on the left with a **3-Turn Trajectory Overlay (`Turn 1`, `Turn 25`, `Turn 50`)** on the right.

```drawlib align=center code=fold width=100% file=ch5_thinking_scatter_and_trajectories.png caption="Figure 5-4: Thinking Tokens vs Total Latency Scatter Plot (Left) & 3-Turn Stream Trajectory Overlay at Turns 1, 25, and 50 (Right)"
from drawlib.canvas import save, setup
from drawlib.charts.scatter import ScatterChart
from drawlib.lines import line, lines
from drawlib.shapes import circle, rectangle
from drawlib.styles import Styles
from drawlib.text import text
from drawlib.utils import load_multiturn_trajectory, load_multiturn_turns

setup(width=156, height=94, dpi=150)

# Outer structural frame
rectangle((78.0, 47.0), width=152.0, height=90.0, style=Styles.MutedDashed.patch(shape_r=2.0))
text(
    (78.0, 88.2),
    "Thinking Tokens vs Total Latency (Left) & Turn 1 / 25 / 50 Stream Trajectories (Right)",
    style=Styles.DarkBold.patch(text_size=11.5),
)

# =========================================================================
# Left Panel: Scatter plot of thoughts_tokens vs total_ms across 3 Streaming variants
# =========================================================================
rectangle((42.5, 47.5), width=71.0, height=73.0, style=Styles.WhiteFlat.patch(shape_r=1.5, line_width=0.8))
rectangle((42.5, 77.2), width=67.0, height=11.2, style=Styles.Neutral.patch(shape_r=1.1))
text(
    (42.5, 80.4),
    "Left: thoughts_tokens vs total_ms (Adaptive Splits 40T vs 10T)",
    style=Styles.DarkBold.patch(text_size=9.5),
)

pts_low: list[tuple[float, float]] = []
pts_high: list[tuple[float, float]] = []
pts_adap: list[tuple[float, float]] = []

for t_rec in load_multiturn_turns():
    v = t_rec["variants"]
    pts_low.append((float(v["streaming_low"]["thoughts_tokens"]), min(float(v["streaming_low"]["total_ms"]), 59000.0)))
    pts_high.append((min(float(v["streaming_high"]["thoughts_tokens"]), 5900.0), min(float(v["streaming_high"]["total_ms"]), 59000.0)))
    pts_adap.append((min(float(v["adaptive_pat_a"]["thoughts_tokens"]), 5900.0), min(float(v["adaptive_pat_a"]["total_ms"]), 59000.0)))

# Compact legend inside Left Panel header
circle((10.5, 76.2), radius=0.65, style=Styles.PrimaryFlat)
text((12.0, 76.2), "★adaptive_pat_a (50 runs)", style=Styles.DarkBold.patch(text_size=9.5, halign="left"))
circle((44.5, 76.2), radius=0.65, style=Styles.TealFlat)
text((46.0, 76.2), "streaming_low (50 runs)", style=Styles.DarkBold.patch(text_size=9.5, halign="left"))
circle((10.5, 73.0), radius=0.65, style=Styles.DangerFlat)
text((12.0, 73.0), "streaming_high (50 runs: 1,000–5,500 tok on all turns)", style=Styles.Dark.patch(text_size=9.5, halign="left"))

scatter = ScatterChart(
    axis_line_style=Styles.Dark,
    axis_text_style=Styles.Dark.patch(text_size=9.8),
    grid_style=Styles.MutedDashed,
    width=61.0,
    height=44.0,
    default_radius=0.85,
)
scatter.configure_x_axis(
    label="Internal Thinking Tokens (thoughts_token_count [tok])",
    min_value=0,
    max_value=6000,
    tick_step=1500,
    format="{:,.0f}",
)
scatter.configure_y_axis(
    min_value=0,
    max_value=60000,
    tick_step=15000,
    format="{:,.0f}",
)
scatter.add_series("streaming_high", pts_high, style=Styles.DangerFlat, shape="rhombus", radius=0.85)
scatter.add_series("streaming_low", pts_low, style=Styles.TealFlat, shape="triangle", radius=0.85)
scatter.add_series("adaptive_pat_a", pts_adap, style=Styles.PrimaryFlat, shape="circle", radius=0.9)
scatter.draw(xy=(12.5, 18.0))
text((10.0, 68.0), "Completion Total (ms)", style=Styles.DarkBold.patch(text_size=9.6, halign="left"))

# =========================================================================
# Right Panel: 3-Turn Trajectory Overlay (Turn 1, Turn 25, Turn 50)
# =========================================================================
rectangle((115.5, 47.5), width=71.0, height=73.0, style=Styles.WhiteFlat.patch(shape_r=1.5, line_width=0.8))
rectangle((115.5, 77.2), width=67.0, height=11.2, style=Styles.Neutral.patch(shape_r=1.1))
text(
    (115.5, 80.4),
    "Right: Turn 1 (Routine), Turn 25 & Turn 50 (Math) Trajectories",
    style=Styles.DarkBold.patch(text_size=9.5),
)

# Legend for Right Panel trajectories
line((83.5, 76.2), (87.5, 76.2), style=Styles.PrimaryBold.patch(line_width=2.5))
text((88.5, 76.2), "★adaptive_pat_a", style=Styles.DarkBold.patch(text_size=9.5, halign="left"))

line((114.5, 76.2), (118.5, 76.2), style=Styles.TealBold.patch(line_width=2.1))
text((119.5, 76.2), "streaming_low", style=Styles.DarkBold.patch(text_size=9.5, halign="left"))

line((83.5, 73.0), (87.5, 73.0), style=Styles.DangerDashed.patch(line_width=2.0))
text((88.5, 73.0), "streaming_high (stalled 19.6–36.5s during thinking)", style=Styles.Dark.patch(text_size=9.5, halign="left"))

sub_panels = [
    (1, 54.0, "Turn 1 (180 tok / Routine): adap 1.73/3.59s vs low 2.65/4.98s vs high 23.6s"),
    (25, 35.0, "Turn 25 (9,523 tok / Math): adap 2.08s→Stage2 35.3s vs high TTFT 19.6s"),
    (50, 16.0, "Turn 50 (20,899 tok / Math): adap 3.75s→Stage2 38.3s vs high TTFT 36.5s"),
]

max_t = 42000.0
max_c = 900.0
pw = 55.0
ph = 12.2
px0 = 88.5

for t_num, py0, sub_title in sub_panels:
    text((px0 + pw / 2, py0 + ph + 2.0), sub_title, style=Styles.DarkBold.patch(text_size=9.4))
    rectangle((px0 + pw / 2, py0 + ph / 2), width=pw, height=ph, style=Styles.Neutral.patch(line_width=0.5, shape_r=0))

    def to_x(ms: float) -> float:
        return px0 + min(max(ms, 0.0), max_t) / max_t * pw

    def to_y(ch: float, base_y: float = py0) -> float:
        return base_y + min(max(ch, 0.0), max_c) / max_c * ph

    for xt in (0, 10000, 20000, 30000, 40000):
        tx = to_x(float(xt))
        line((tx, py0), (tx, py0 + ph), style=Styles.MutedDashed.patch(line_width=0.5))
        if t_num == 50:
            text((tx, py0 - 2.2), f"{xt // 1000}s", style=Styles.Dark.patch(text_size=9.6))

    for yt in (0, 450, 900):
        ty = to_y(float(yt))
        line((px0, ty), (px0 + pw, ty), style=Styles.MutedDashed.patch(line_width=0.5))
        text((px0 - 1.2, ty), f"{yt}", style=Styles.Dark.patch(text_size=9.6, halign="right"))

    line((px0, py0), (px0 + pw, py0), style=Styles.Dark.patch(line_width=1.0))
    line((px0, py0), (px0, py0 + ph), style=Styles.Dark.patch(line_width=1.0))

    for v_key, st_line in (
        ("streaming_high", Styles.DangerDashed.patch(line_width=1.9)),
        ("streaming_low", Styles.TealBold.patch(line_width=2.0)),
        ("adaptive_pat_a", Styles.PrimaryBold.patch(line_width=2.5)),
    ):
        tr = load_multiturn_trajectory(t_num, v_key)
        gem_pts = tr["timeline_series"].get("gemini", [])
        if len(gem_pts) >= 2:
            coords = [(to_x(float(p["t_ms"])), to_y(float(p["chars"]))) for p in gem_pts]
            lines(coords, style=st_line)

text((px0 + pw / 2, 11.2), "Elapsed Time (0–42s) — Y-Axis: Cumulative Output Characters (0–900 chars)", style=Styles.DarkBold.patch(text_size=9.6))

# Bottom callout bar
rectangle((78.0, 5.8), width=146.0, height=5.8, style=Styles.SecondaryNeutral.patch(shape_r=1.2))
text(
    (78.0, 5.8),
    "Conclusion: At math Turns 25 & 50, adaptive_pat_a streams its bridge in 2.1–3.8s while Stage 2 (high) computes in parallel.",
    style=Styles.DarkBold.patch(text_size=9.5),
)

save()
```

### Key Findings from the Scatter & Trajectory Analysis

1. **Left Panel: Clean Bifurcation of `adaptive_pat_a` into Routine (`~0 tok`) and Complex Math (`~3,671 tok`) Clusters**:
   - While `streaming_high` (red diamonds) expends `1,000–5,500` thinking tokens indiscriminately across all 50 turns, `adaptive_pat_a` (blue circles) cleanly separates into two clusters: **40 routine turns at the bottom-left (`~0–30 tok`, `5,008 ms` avg Total)** and **10 complex math turns at the upper-right (`3,671 tok` avg, `40,142 ms` avg Total)**, saving **`61.7%` of total thinking tokens**.
2. **Right Panel: 3-Turn Stream Trajectory Snapshots (`Turn 1`, `Turn 25`, `Turn 50`)**:
   - **Turn 1 (`180 tok`, Routine Power Check, `expected_thinking=False`)**: `adaptive_pat_a` (solid blue) starts streaming at **`1,726 ms`** and finishes at **`3,592 ms`** in a single call, outperforming `streaming_low` (`2,652 / 4,984 ms`) while `streaming_high` stalls at `0 chars` until **`23,636 ms`**.
   - **Turn 25 (`9,523 tok`, Cache `74.1%`, Complex RAM/Pagefile Sizing Math, `expected_thinking=True`)**: `adaptive_pat_a` streams its Stage 1 bridge message at **`2,075 ms`** and seamlessly appends the Stage 2 (`high`, `2,916` thinking tokens, **`7,521 cached tokens [77.1%]`**) calculation response (`35,289 ms` Total), eliminating the `19,631 ms` dead-air stall of `streaming_high`.
   - **Turn 50 (`20,899 tok`, Cache `88.0%–90.2%`, Complex 3-Year Backup TCO & SLA Math, `expected_thinking=True`)**: With over `20.8k` input tokens, `adaptive_pat_a` delivers its bridge at **`3,753 ms`** (**`32.7s / 89.7%` earlier than `streaming_high` `36,492 ms`**) and completes Stage 2 (`3,435` thinking tokens, **`18,890 cached tokens [90.2%]`**) in **`38,274 ms`**, matching `streaming_high` (`38,857 ms`) in total completion time.

---

## 5.5 Cohort & Turn-Type Summary Table and Production Guidelines

### 1. Comprehensive Performance Table by 10-Turn Cohort and Turn Type (`Routine 40T` vs. `Math 10T`)

The table below summarizes input token growth, Implicit Context Cache hit rates, and initial (`TTFT`) / completion (`Total`) latencies across 10-turn cohorts, routine vs. complex turns, and all 50 turns combined.

| Cohort / Turn Segment (8 Routine + 2 Math per Cohort) | Avg `prompt_tokens` /<br>Cache (`Hit Rate`) | `(1)` `streaming_low`<br>Initial `TTFT` / `Total` [ThTok] | `(1)` `streaming_high`<br>Initial `TTFT` / `Total` [ThTok] | `(2)` ★`adaptive_pat_a` (Pattern A)<br>Initial `TTFT` / `Total` [ThTok] | `adaptive` vs `high`<br>TTFT / Total Delta |
| :--- | ---: | ---: | ---: | ---: | ---: |
| **Turns 1–10**<br>(Power, BIOS, T5 Blackout Backup, T10 Recovery Math) | `1,796 tok` (`180–3,438`)<br>Cache: `179–287 tok` (`10–15%`) | **`1,854`** / `5,583 ms`<br>[`0 tok`] | `23,553` / `25,329 ms`<br>[`2,386 tok`] | **`2,121`** / **`9,729 ms`** (Med `4,332`)<br>[`715 tok` / Match `10/10`] | **`-21,432 ms` (`-91.0%`)**<br>Total: `-61.6%` |
| **Turns 11–20**<br>(Drivers, `sfc`, T15 USB Speed, T20 Rebuild Math) | `5,533 tok` (`3,893–7,334`)<br>Cache: `3,151–3,383 tok` (`57–60%`) | **`2,372`** / `6,396 ms`<br>[`0 tok`] | `29,886` / `32,175 ms`<br>[`2,846 tok`] | **`2,431`** / **`14,142 ms`** (Med `4,953`)<br>[`949 tok` / Match `10/10`] | **`-27,455 ms` (`-91.9%`)**<br>Total: `-56.0%` |
| **Turns 21–30**<br>(Restore, T25 Pagefile, T30 Bandwidth Math) | `9,759 tok` (`7,800–11,710`)<br>Cache: `7,321–7,530 tok` (`75–76%`) | **`3,143`** / `6,880 ms`<br>[`0 tok`] | `21,374` / `23,842 ms`<br>[`1,965 tok`] | **`2,926`** / **`11,670 ms`** (Med `6,104`)<br>[`652 tok` / Match `10/10`] | **`-18,448 ms` (`-86.3%`)**<br>Total: `-51.1%` |
| **Turns 31–40**<br>(BitLocker, T35 Surface Scan, T40 Warranty Math) | `14,201 tok` (`12,293–16,156`)<br>Cache: `11,752–11,947 tok` (`83–84%`) | **`2,212`** / `6,737 ms`<br>[`0 tok`] | `14,686` / `17,870 ms`<br>[`1,237 tok`] | **`2,957`** / **`12,319 ms`** (Med `6,530`)<br>[`716 tok` / Match `10/10`] | **`-11,729 ms` (`-79.9%`)**<br>Total: `-31.1%` |
| **Turns 41–50**<br>(Repair, T45 3-Yr TCO, T50 Cloud SLA Math) | `18,757 tok` (`16,661–20,899`)<br>Cache: `16,337–16,528 tok` (**`87–88%`**) | **`1,970`** / `7,348 ms`<br>[`0 tok`] | `16,365` / `19,921 ms`<br>[`1,473 tok`] | **`2,655`** / **`12,312 ms`** (Med `6,242`)<br>[`757 tok` / Match `10/10`] | **`-13,710 ms` (`-83.8%`)**<br>Total: `-38.2%` |
| **Routine 40 Turns Avg**<br>(`expected_thinking=False`) | `9,676 tok`<br>(1 API call) | **`2,304`** / `6,411 ms`<br>(Med `2,060` / `6,497`) [`0`] | `16,958` / `19,683 ms`<br>(Med `20,701` / `22,721`) [`1,534`] | **`2,560`** / **`5,008 ms`**<br>(Med `2,352` / **`4,695`**) [`30`] | **`-14,398 ms` (`-84.9%`)**<br>Total: **`-74.6%`** |
| **Complex Math 10 Turns Avg**<br>(`expected_thinking=True`: `T5..50`) | `11,341 tok`<br>(Stage 1 + Stage 2 Parallel) | **`2,336`** / `7,302 ms`<br>(Med `2,310` / `7,370`) [`0`] | `38,033` / `40,404 ms`<br>(Med `32,083` / `34,257`) [`3,772`] | **`2,851`** / **`40,142 ms`**<br>(Med `2,618` / `38,900`) [`3,671`] | **`-35,182 ms` (`-92.5%`)**<br>Total: `-0.6%` (Full Depth) |
| **All 50 Turns Overall Avg**<br>(Median / P95) | **`10,009 tok`** (`180–20,899`)<br>Cache: **`77.4%–78.5%`** (Max **`90.2%`**) | **`2,310`** / **`6,589 ms`**<br>(Med `2,084` / `6,583`) [`0`] | **`21,173`** / **`23,827 ms`**<br>(Med `22,012` / `23,887`) [`1,981`] | **`2,618`** / **`12,034 ms`**<br>(Med `2,420` / **`4,990`**) [**`758`**] | **`-18,555 ms` (`-87.6%`)**<br>Total: **`-49.5%`** (Med **`-79.1%`**) |

### 2. Production Architecture Guidelines for Multi-Turn Streaming Chat

1. **Preserve Strict Prefix Immutability Across Stage 1 and Stage 2**:
   - Gemini 3.8 Flash's Implicit Context Caching matches the exact token prefix across `system_instruction` and historical `contents: list[types.Content]`.
   - **Best Practice**: Keep `system_instruction` identical between Stage 1 (`low`) and Stage 2 (`high`) and treat `history: list[types.Content]` as strictly **append-only** (injecting Stage 1's routing instructions into the final user turn). This enables Stage 2 to hit up to **`90.2%` (`18,890 cached tokens` at Turn 50)** of the conversation prefix warmed by Stage 1.
2. **Resolve the `low` vs. `high` Dilemma with Chapter 4's Adaptive Thinking Router (Pattern A)**:
   - Using fixed `streaming_low` across all 50 turns yields fast responses (`2,310 ms` TTFT / `6,589 ms` Total) but performs zero internal reasoning (`0 tok`) even when users ask multi-variable cost or capacity math questions. Conversely, fixed `streaming_high` freezes the UI for an average of **`21.2 seconds`** (`17.0s` on routine turns and `38.0s` on math turns).
   - Deploying **Pattern A (`low → high` 2-Field Integrated Pydantic Router)** delivers **`2,618 ms` average TTFT (`2,420 ms` median)** across all 50 turns, completes the 40 routine turns in **`5,008 ms`**, and selectively engages `high` reasoning (`3,671` thinking tokens) on the 10 calculation turns.
3. **Extending Stage 1 (`3.5-flash-lite`) or Stage 2 (`Gemini 4` Series)**:
   - As detailed in Section 4.1, teams seeking even faster initial response (`~1.0–1.5s` TTFT) can substitute **`gemini-3.5-flash-lite` (`minimal` / `low`)** in Stage 1, while complex enterprise workflows requiring deeper reasoning can route Stage 2 to **`gemini-4-hydrogen [high]`** or **`gemini-4-carbon [medium/high]`**.
