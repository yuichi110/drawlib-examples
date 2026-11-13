# 5. Multi-Turn Chat Behavior & Context Caching

In production conversational AI systems (such as PC technical support desks and interactive troubleshooting assistants), users engage in extended multi-turn dialogues rather than isolated single-turn prompts. In this chapter, we analyze empirical measurements from a **50-turn continuous PC troubleshooting customer-support chat benchmark** (`src/gemini_evaluation/benchmark_multiturn_chat.py` / `multiturn_chat_log.json`, `200 total API executions` across `50 turns × 4 variants`) on Google AI Studio (`google-genai` SDK with `gemini-3.8-flash`). We examine how linear conversation history growth (`176 → 21,490 prompt_tokens`, `42,281 cumulative characters`) affects latency and how Gemini 3.8 Flash's zero-configuration **Implicit Context Caching (`cached_content_token_count`)** bounds prefill latency across long conversations.

```drawlib align=center code=fold width=100% file=ch5_multiturn_hero.png caption="Figure 5-1: 50-Turn PC Support Multi-Turn Evaluation Architecture & 4-Variant Average Latency Comparison (gemini-3.8-flash)"
from drawlib.canvas import save, setup
from drawlib.icons import phosphor
from drawlib.lines import line
from drawlib.shapes import rectangle
from drawlib.styles import Styles
from drawlib.text import text

setup(width=156, height=80, dpi=150)

# Outer structural frame
rectangle((78, 40), width=152, height=76, style=Styles.MutedDashed.patch(shape_r=2.0))
text(
    (78, 74.2),
    "50-Turn PC Support Multi-Turn Architecture & 4-Variant Latency Comparison (gemini-3.8-flash)",
    style=Styles.DarkBold.patch(text_size=11.5),
)

# Top pipeline band: 50-Turn Evaluation Loop
rectangle((78, 59.8), width=146, height=18.0, style=Styles.PrimaryNeutral.patch(shape_r=1.5))
text(
    (78, 66.2),
    "Per-Turn Benchmark Pipeline (50-Step PC Troubleshooting Scenario with Rotated Call Order for Fair Cache Warm-Up)",
    style=Styles.DarkBold.patch(text_size=10.2),
)

loop_steps = [
    (22.0, 29.5, "1. User Simulator", "gemini-3.8-flash (t=0)\nPC issue query (avg 85.6 ch)", Styles.WhiteFlat),
    (57.5, 31.5, "2. History + New Turn", "history: list[Content]\n176 → 21,490 tok (42,281 ch)", Styles.WhiteFlat),
    (95.0, 34.0, "3. Implicit Cache Hit", "Auto-active at T8–9 (~2.7k tok)\n87.2% hit in T41–50 (max 90.6%)", Styles.SecondaryNeutral),
    (132.5, 31.0, "4. Evaluate 4 Variants", "Detailed support guide\n(avg 753.0 ch, ~8.8× user query)", Styles.WhiteFlat),
]
for cx, w, st_top, st_bot, box_st in loop_steps:
    rectangle((cx, 57.0), width=w, height=10.8, style=box_st.patch(shape_r=1.2, line_width=0.8))
    text((cx, 59.8), st_top, style=Styles.DarkBold.patch(text_size=10.2))
    text((cx, 54.6), st_bot, style=Styles.Dark.patch(text_size=10.0))

line((36.8, 57.0), (41.7, 57.0), arrow_head="->", style=Styles.DarkBold)
line((73.3, 57.0), (78.0, 57.0), arrow_head="->", style=Styles.DarkBold)
line((112.0, 57.0), (117.0, 57.0), arrow_head="->", style=Styles.DarkBold)

# Left Column: thinking=0 (Fast & Deterministic)
phosphor.lightning((7.5, 46.8), width=3.4, style=Styles.DarkBold)
text(
    (10.5, 46.8),
    "thinking=0 (Fast & Deterministic)",
    style=Styles.DarkBold.patch(text_size=10.8, halign="left"),
)

# Focal Card: streaming_t0
rectangle((42.0, 34.4), width=72.0, height=18.6, style=Styles.PrimaryFlat.patch(shape_r=1.6))
phosphor.star((8.2, 40.8), width=3.2, style=Styles.WhiteBold)
text(
    (11.2, 40.8),
    "Recommended: streaming_t0 (Streaming × thinking=0)",
    style=Styles.WhiteBold.patch(text_size=10.5, halign="left"),
)
text(
    (7.8, 36.6),
    "• First Token (TTFT): Avg 2,460 ms (Median 2,029 ms)",
    style=Styles.White.patch(text_size=10.0, halign="left"),
)
text(
    (7.8, 32.8),
    "• Stream Total: Avg 6,323 ms (-3,964 ms / 62% earlier vs Blocking)",
    style=Styles.White.patch(text_size=10.0, halign="left"),
)
text(
    (7.8, 29.0),
    "• 50-Turn Scaling: 2,180ms (T11–20) → 2,574ms (T41–50) [+29ms/1k]",
    style=Styles.WhiteBold.patch(text_size=10.0, halign="left"),
)

# Secondary Card: blocking_t0
rectangle((42.0, 17.2), width=72.0, height=12.4, style=Styles.Neutral.patch(shape_r=1.4))
text(
    (7.8, 20.6),
    "Baseline: blocking_t0 (Blocking × thinking=0)",
    style=Styles.DarkBold.patch(text_size=10.2, halign="left"),
)
text(
    (7.8, 16.8),
    "• TTFT = Total: Avg 6,424 ms (Median 6,062 ms)",
    style=Styles.Dark.patch(text_size=10.0, halign="left"),
)
text(
    (7.8, 13.2),
    "• Waits until all ~753 chars finish decoding (+3.96s perceived delay)",
    style=Styles.Dark.patch(text_size=10.0, halign="left"),
)

# Vertical divider
line((80.0, 11.0), (80.0, 48.5), style=Styles.MutedDashed.patch(line_width=1.0))

# Right Column: thinking=default (Dynamic Thinking Inflation)
phosphor.warning((84.2, 46.8), width=3.4, style=Styles.DarkBold)
text(
    (87.2, 46.8),
    "thinking=default (Dynamic Reasoning Inflation: 10–13s Avg)",
    style=Styles.DarkBold.patch(text_size=10.8, halign="left"),
)

# Card: streaming_default
rectangle((116.5, 35.8), width=69.0, height=15.6, style=Styles.Neutral.patch(shape_r=1.4))
text(
    (84.0, 40.4),
    "streaming_default (Streaming × thinking=default)",
    style=Styles.DarkBold.patch(text_size=10.2, halign="left"),
)
text(
    (84.0, 36.2),
    "• Avg TTFT: 9,838 ms | Avg Total: 12,335 ms",
    style=Styles.Dark.patch(text_size=10.0, halign="left"),
)
text(
    (84.0, 32.2),
    "• Avg 858 thinking tokens block visible streaming for ~9.8s",
    style=Styles.Dark.patch(text_size=10.0, halign="left"),
)

# Card: blocking_default
rectangle((116.5, 17.6), width=69.0, height=13.2, style=Styles.Neutral.patch(shape_r=1.4))
text(
    (84.0, 21.4),
    "blocking_default (Blocking × thinking=default)",
    style=Styles.DarkBold.patch(text_size=10.2, halign="left"),
)
text(
    (84.0, 17.4),
    "• Avg TTFT = Total: 13,025 ms (Avg 954 thinking tokens)",
    style=Styles.Dark.patch(text_size=10.0, halign="left"),
)
text(
    (84.0, 13.6),
    "• Volatile (6.7s–22.0s) driven by 0–2,237 reasoning tokens",
    style=Styles.Dark.patch(text_size=10.0, halign="left"),
)

# Bottom architectural insight banner
rectangle((78.0, 6.2), width=146.0, height=6.0, style=Styles.SecondaryNeutral.patch(shape_r=1.2))
text(
    (78.0, 6.2),
    "Key Takeaway: Across 50 turns of ~753-char replies, streaming_t0 delivers the first token 3.96s (62%) earlier with flat scaling.",
    style=Styles.DarkBold.patch(text_size=10.0),
)

save()
```

---

## 5.1 50-Turn PC Support Benchmark Architecture & Methodology

### 1. Multi-Turn History Accumulation in `google-genai`

Because the Gemini API is stateless across individual HTTP/gRPC requests, multi-turn chat in `google-genai` requires the application to maintain an ordered conversation list `history: list[types.Content]` (alternating `role="user"` and `role="model"` entries) and send the entire accumulated history plus the new user message on every turn (`src/gemini_evaluation/llm_call.py`):

```python
from google import genai
from google.genai import types

client = genai.Client(api_key=GEMINI_KEY)

# Append the current turn's user message to the accumulated history: list[types.Content]
contents: list[types.Content] = [
    *history,
    types.Content(role="user", parts=[types.Part.from_text(text=user_prompt)]),
]

response_stream = await client.aio.models.generate_content_stream(
    model="gemini-3.8-flash",
    contents=contents,
    config=types.GenerateContentConfig(
        system_instruction=AGENT_SYSTEM_INSTRUCTION,
        thinking_config=types.ThinkingConfig(thinking_budget=0),
        temperature=0.2,
    ),
)
```

In this architecture, `prompt_token_count` grows monotonically with every turn. To evaluate how this growth impacts real-world latency, our 50-turn benchmark (`src/gemini_evaluation/benchmark_multiturn_chat.py`) implements an asymmetric two-agent simulation of **a customer and a PC technical support specialist troubleshooting an unresponsive PC**:

1. **User Simulator (`gemini-3.8-flash`, `thinking=0`)**:
   Generates a concise `70–100 char` customer question (`avg 85.6 chars`) across 50 sequential PC troubleshooting stages:
   - **Turns 1–10 (Power, Discharge & Safe Mode)**: Black screen on power-on, blinking AC adapter LED, 30-second power-button discharge, logo freeze, BIOS `F2` SSD check, BIOS reset error `0xc0000001`, and booting into Windows Safe Mode.
   - **Turns 11–20 (Data Backup & Software/Driver Isolation)**: Backing up work documents to USB in Safe Mode, uninstalling recent Windows Updates, rolling back a yellow-bang display driver in Device Manager, running `sfc /scannow` / `DISM` and `chkdsk`, isolating post-login freezes via Task Manager and `msconfig` clean boot, thermal check, and Windows Memory Diagnostic.
   - **Turns 21–30 (Storage Health, System Restore & USB Recovery Media)**: Checking SSD S.M.A.R.T. health, Event Viewer `Kernel-Power 41` logs, disabling Fast Startup, PCIe link power management, BIOS/chipset updates, `MEMORY_MANAGEMENT` BSOD System Restore, Reset this PC (Keep my files), Cloud Download vs. Local Reinstall, creating a USB recovery drive on another PC, and BIOS boot order / Secure Boot configuration.
   - **Turns 31–45 (BitLocker, Hardware Diagnostics & Repair Logistics)**: Locating the 48-digit BitLocker recovery key on a smartphone, running built-in hardware Diagnostics (detecting a memory module error code), verifying 1-year standard warranty vs. accidental damage coverage by serial number, pickup repair packaging, AC adapter inclusion rules, SSD data wipe consent, paid data recovery options, loaner/rental PC availability, on-site same-day repair eligibility, out-of-warranty cancellation fees, and trade-in replacement discounts.
   - **Turns 46–50 (Post-Repair Verification & Preventive Backup)**: Post-repair inspection checklist and warranty period, malware scanning before restoring USB backups, automated system image backups to external SSD, OneDrive cloud folder sync, and 3 daily maintenance habits.
2. **PC Support Agent (`gemini-3.8-flash`)**:
   Reads the accumulated `history` and generates a comprehensive diagnostic and step-by-step response (`avg 753.0 chars`, **~8.8× longer** than the user query) covering troubleshooting steps, decision criteria, and safety precautions.
3. **4-Variant Evaluation with Rotated Call Order (`rot = (turn - 1) % 4`)**:
   Across all 50 turns (`176 → 21,490 prompt_tokens`, `42,281 cumulative chars`), we evaluate 4 variants on the exact same `history`, rotating execution order to eliminate cache-warmup bias:

| Variant Key | SDK Method | `ThinkingConfig` | Avg `TTFT` (Median) | Avg `Total` | Avg Thinking Tokens | Architectural Role |
| :--- | :--- | :--- | ---: | ---: | ---: | :--- |
| **`streaming_t0`** | `generate_content_stream` | `thinking_budget=0` | **`2,460 ms`** (`2,029 ms`) | **`6,323 ms`** | `19 tok` (T2–50: `0`) | **Recommended**: Delivers first token **`3,964 ms` (`3.96s` / `62%`) earlier** every turn |
| **`blocking_t0`** | `generate_content` | `thinking_budget=0` | `6,424 ms` (`6,062 ms`) | `6,424 ms` | `0 tok` | Waits for full ~753-char completion (`TTFT = Total`) |
| **`streaming_default`** | `generate_content_stream` | Default (dynamic) | `9,838 ms` (`10,500 ms`) | `12,335 ms` | `858 tok` | Internal reasoning stalls first visible token for ~9.8s |
| **`blocking_default`** | `generate_content` | Default (dynamic) | `13,025 ms` (`12,548 ms`) | `13,025 ms` | `954 tok` | Waits ~13.0s for reasoning + full text generation |

---

## 5.2 Input Token Growth & Automatic Implicit Context Caching (`cached_content_token_count`)

As each `(user, model)` message pair is appended to `history`, `prompt_token_count` grows linearly at **`~+435 tokens/turn`** (`176 tokens` at Turn 1 → `2,686 tokens` at Turn 8 → `10,060 tokens` at Turn 25 → **`21,490 tokens`** at Turn 50).

Our key empirical finding is that **once input context reaches `~2,686–3,045 tokens` at Turns 8–9, Gemini 3.8 Flash's automatic Implicit Context Caching (`usage_metadata.cached_content_token_count`) activates without any explicit cache API calls**, advancing every turn and reaching an **`87.2%` average hit rate in Turns 41–50 (`88.4%` on `streaming_t0` and `90.6%` peak on `blocking_t0` at Turn 50: `19,480 / 21,490 tokens` cached)**.

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
prompt_vals = [float(t["variants"]["streaming_t0"]["prompt_tokens"]) for t in turns]
cached_vals = [float(t["variants"]["streaming_t0"]["cached_tokens"]) for t in turns]
uncached_vals = [p - c for p, c in zip(prompt_vals, cached_vals)]

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
    "Total Input Tokens (prompt_tokens: 176 → 21,490 tok)",
    prompt_vals,
    style=Styles.PrimaryFlat,
    line_width=2.6,
    point_shape="none",
)
chart.add_series(
    "Implicit Cache Hits (cached_tokens: peak 18,995–19,480 tok)",
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
    xy=(11.5, 70.0),
    text_style=Styles.DarkBold.patch(text_size=10.0),
    orientation="vertical",
    item_gap=1.3,
)

# Axis labels
text((9.5, 54.0), "Tokens (tok)", style=Styles.DarkBold.patch(text_size=10.0, halign="left"))
text((51.5, 6.2), "Conversation Turn (Turn 1 to Turn 50)", style=Styles.DarkBold.patch(text_size=10.0))

# Callout annotation inside chart pointing to Turn 8-9 cache activation
rectangle((44.5, 38.0), width=40.0, height=8.0, style=Styles.Neutral.patch(shape_r=1.0))
text(
    (44.5, 39.8),
    "Turns 8–9 (~2,686 tok threshold)",
    style=Styles.DarkBold.patch(text_size=10.0),
)
text(
    (44.5, 36.2),
    "Auto Cache Active (up to 90.6% at T50)",
    style=Styles.Dark.patch(text_size=10.0),
)
line((36.0, 34.0), (24.0, 15.0), arrow_head="->", style=Styles.DarkBold.patch(line_width=1.6))

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
        "1. Linear Growth (~+435 tok/turn)",
        "User (~86 ch) + Agent (~753 ch) pairs\ngrow input from 176 to 21,490 tokens",
    ),
    (
        43.8,
        "2. Zero-Config Activation at T8–9",
        "Crossing ~2,686 tokens at Turns 8–9\ntriggers KV cache hits automatically",
    ),
    (
        28.4,
        "3. 87.2% Hit in T41–50 (90.6% Peak)",
        "Cache boundary advances every turn,\nhitting up to 19,480 / 21,490 tok at T50",
    ),
    (
        13.0,
        "4. Uncached Delta Bounded (~2,400 tok)",
        "New prefill work stays flat around ~2.4k\ntokens across all turns past Turn 9",
    ),
]

for cy, hdr, body in summary_cards:
    rectangle((125.5, cy), width=47.4, height=13.4, style=Styles.WhiteFlat.patch(shape_r=1.2, line_width=0.7))
    text((103.2, cy + 3.6), hdr, style=Styles.DarkBold.patch(text_size=10.0, halign="left"))
    text((103.2, cy - 2.0), body, style=Styles.Dark.patch(text_size=10.0, halign="left"))

save()
```

### How Automatic Implicit Context Caching Works Across 50 Turns

1. **Zero-Configuration Activation at Turns 8–9 (`~2,686–3,045 Tokens`)**:
   During Turns 1–7 (`176–2,298 prompt_tokens`), `cached_content_token_count` remains `0`. Once the accumulated prefix reaches **Turn 8 (`2,686 tokens`)** and **Turn 9 (`3,045 tokens`)**, Gemini 3.8 Flash automatically caches the shared history prefix (`703–1,060 cached tokens`).
2. **Continuous Per-Turn Prefix Expansion**:
   From Turn 9 onward, as conversation history grows, the cached prefix boundary advances continuously on every turn: Turn 10 (`1,061 tok`) → Turn 20 (`5,064 tok`) → Turn 30 (`9,935 tok`) → Turn 40 (`14,533 tok`) → Turn 50 (**`18,995 tok` [`88.4%`] on `streaming_t0`, and `19,480 tok` [`90.6%`] on `blocking_t0`**). Across **Turns 41–50**, the average cache hit rate reaches **`87.2%`** (`streaming_t0`).
3. **Bounded Uncached Prefill Delta (`~2,400 Tokens`)**:
   As shown by the dashed purple line in Figure 5-2, the uncached token delta (`prompt_tokens - cached_tokens`) requiring fresh KV-cache prefill computation on each turn remains flat around **`~2,340–2,540 tokens` (`~1,980–2,010 tokens` on `blocking_t0`)** from Turn 9 through Turn 50.

---

## 5.3 50-Turn Latency Scaling (`+29 ms / 1k tokens` with `thinking=0`)

Because Implicit Context Caching reuses the KV cache for `85–90%+` of historical tokens in the second half of the dialogue, **`streaming_t0` TTFT increases by only `+394 ms` between Turns 11–20 (`2,180 ms` avg) and Turns 41–50 (`2,574 ms` avg)** despite a `+13,700 token` increase in prompt size. This represents a flat linear scaling slope of **`+29 ms per 1,000 input tokens`**, keeping median time-to-first-token at **`2,029 ms`** across the 50-turn troubleshooting session.

```drawlib align=center code=fold width=100% file=ch5_latency_evolution_2panel.png caption="Figure 5-3: 2-Panel 50-Turn Latency Evolution (Left: thinking=0 Flat Scaling, Right: thinking=default Latency & Thinking Token Bars)"
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
    "50-Turn Latency Evolution (176 → 21,490 tok): thinking=0 (Left) vs thinking=default (Right)",
    style=Styles.DarkBold.patch(text_size=11.5),
)

turns = load_multiturn_turns()
labeled_turns = {1, 10, 20, 30, 40, 50}
categories = [f"T{t['turn']}" if int(t["turn"]) in labeled_turns else "" for t in turns]

s0_ttft = [float(t["variants"]["streaming_t0"]["ttft_ms"]) for t in turns]
s0_total = [float(t["variants"]["streaming_t0"]["total_ms"]) for t in turns]
b0_total = [float(t["variants"]["blocking_t0"]["total_ms"]) for t in turns]

sd_ttft = [float(t["variants"]["streaming_default"]["ttft_ms"]) for t in turns]
bd_total = [float(t["variants"]["blocking_default"]["total_ms"]) for t in turns]
sd_th_tok = [float(t["variants"]["streaming_default"]["thoughts_tokens"]) for t in turns]

# =========================================================================
# Left Panel: thinking=0 (Flat +29 ms / 1k tok scaling)
# =========================================================================
rectangle((42.5, 45.5), width=71.0, height=69.0, style=Styles.WhiteFlat.patch(shape_r=1.5, line_width=0.8))
rectangle((42.5, 73.2), width=67.0, height=11.6, style=Styles.Neutral.patch(shape_r=1.1))
text(
    (42.5, 76.6),
    "Left Panel: thinking=0 (Median TTFT 2,029ms, +29ms/1k tok)",
    style=Styles.DarkBold.patch(text_size=10.2),
)

# Legend for Left Panel
line((10.0, 72.8), (13.6, 72.8), style=Styles.PrimaryBold.patch(line_width=2.6))
circle((11.8, 72.8), radius=0.6, style=Styles.PrimaryFlat)
text((14.5, 72.8), "streaming_t0 TTFT (Avg 2,460ms)", style=Styles.DarkBold.patch(text_size=10.0, halign="left"))

line((10.0, 69.4), (13.6, 69.4), style=Styles.TealDashed.patch(line_width=1.9))
text((14.5, 69.4), "streaming_t0 Total (6,323ms)", style=Styles.Dark.patch(text_size=10.0, halign="left"))

line((47.2, 69.4), (50.8, 69.4), style=Styles.SecondaryBold.patch(line_width=2.1))
text((51.6, 69.4), "blocking_t0 (6,424ms)", style=Styles.Dark.patch(text_size=10.0, halign="left"))

chart_left = LineChart(
    axis_line_style=Styles.Dark,
    axis_text_style=Styles.Dark.patch(text_size=10.0),
    grid_style=Styles.MutedDashed,
    categories=categories,
    width=59.0,
    height=42.0,
    show_points=True,
    point_shape="circle",
    point_size=0.45,
)
chart_left.configure_x_axis(show_grid=False)
chart_left.configure_y_axis(
    min_value=0,
    max_value=14000,
    tick_step=3500,
    format="{:,.0f}",
)
chart_left.add_series(
    name="blocking_t0 Total",
    values=b0_total,
    style=Styles.SecondaryFlat,
    line_width=2.0,
    point_size=0.4,
)
chart_left.add_series(
    name="streaming_t0 Total",
    values=s0_total,
    style=Styles.TealFlat,
    line_width=1.8,
    line_style="dashed",
    point_shape="none",
)
chart_left.add_series(
    name="streaming_t0 TTFT",
    values=s0_ttft,
    style=Styles.PrimaryFlat,
    line_width=2.6,
    point_size=0.5,
)
chart_left.draw(xy=(14.5, 19.5))
text((10.0, 63.8), "Latency (ms)", style=Styles.DarkBold.patch(text_size=10.0, halign="left"))
text((44.0, 14.2), "Turn Number (T11–20 avg 2,180ms → T41–50 avg 2,574ms)", style=Styles.DarkBold.patch(text_size=10.0))

# =========================================================================
# Right Panel: thinking=default (Latency + Thinking Token Bars)
# =========================================================================
rectangle((115.5, 45.5), width=71.0, height=69.0, style=Styles.WhiteFlat.patch(shape_r=1.5, line_width=0.8))
rectangle((115.5, 73.2), width=67.0, height=11.6, style=Styles.Neutral.patch(shape_r=1.1))
text(
    (115.5, 76.6),
    "Right Panel: thinking=default (Latency & Thinking Bars)",
    style=Styles.DarkBold.patch(text_size=10.2),
)

# Legend for Right Panel
line((83.5, 72.8), (87.5, 72.8), style=Styles.WarningBold.patch(line_width=2.2))
circle((85.5, 72.8), radius=0.55, style=Styles.WarningFlat)
text((88.5, 72.8), "streaming_def TTFT (9,838ms)", style=Styles.DarkBold.patch(text_size=10.0, halign="left"))

line((83.5, 69.4), (87.5, 69.4), style=Styles.DangerBold.patch(line_width=2.0))
text((88.5, 69.4), "blocking_def Total (13,025ms)", style=Styles.Dark.patch(text_size=10.0, halign="left"))

rectangle((124.0, 69.4), width=3.0, height=2.0, style=Styles.SecondaryNeutral.patch(line_width=0.6))
text((126.5, 69.4), "ThTok (avg 858)", style=Styles.Dark.patch(text_size=10.0, halign="left"))

# Draw Thinking Token vertical bars strictly inside the inner plot area (x: 97.7..144.2, y0: 25.8)
rx0, ry0, rpw, rph = 87.5, 19.5, 59.0, 42.0
inner_x0, inner_x1, inner_y0, inner_h = 97.7, 144.2, 25.8, 32.5
for idx, th_val in enumerate(sd_th_tok):
    bx = inner_x0 + (idx / max(len(sd_th_tok) - 1, 1)) * (inner_x1 - inner_x0)
    bh = min(th_val / 2400.0, 1.0) * inner_h
    if bh > 0.2:
        rectangle(
            (bx, inner_y0 + bh / 2.0),
            width=0.62,
            height=bh,
            style=Styles.SecondaryNeutral.patch(line_width=0.3, shape_r=0),
        )

chart_right = LineChart(
    axis_line_style=Styles.Dark,
    axis_text_style=Styles.Dark.patch(text_size=10.0),
    grid_style=Styles.MutedDashed,
    categories=categories,
    width=rpw,
    height=rph,
    show_points=True,
    point_shape="circle",
    point_size=0.45,
)
chart_right.configure_x_axis(show_grid=False)
chart_right.configure_y_axis(
    min_value=0,
    max_value=24000,
    tick_step=6000,
    format="{:,.0f}",
)
chart_right.add_series(
    name="blocking_default Total",
    values=bd_total,
    style=Styles.DangerFlat,
    line_width=1.8,
    point_size=0.4,
)
chart_right.add_series(
    name="streaming_default TTFT",
    values=sd_ttft,
    style=Styles.WarningFlat,
    line_width=2.2,
    point_size=0.45,
)
chart_right.draw(xy=(rx0, ry0))
text((83.0, 63.8), "Latency (ms) / ThTok", style=Styles.DarkBold.patch(text_size=10.0, halign="left"))
text((117.0, 14.2), "Turn Number (Driven by 0–2,237 Thinking Token Spikes)", style=Styles.DarkBold.patch(text_size=10.0))

# Bottom callout bar
rectangle((78.0, 6.2), width=146.0, height=6.0, style=Styles.PrimaryNeutral.patch(shape_r=1.2))
text(
    (78.0, 6.2),
    "Takeaway: streaming_t0 (left, solid blue) stays near ~2.0s median TTFT through Turn 50, while default (right) swings up to 22.0s.",
    style=Styles.DarkBold.patch(text_size=10.0),
)

save()
```

### Key Architectural Observations from Figure 5-3

1. **Left Panel (`thinking=0`): Stable `~2.0s` Median First-Token Latency Across 50 Turns**:
   - The solid blue curve (`streaming_t0 TTFT`, avg **`2,460 ms`**, Turns 2–50 avg **`2,295 ms`**, median **`2,029 ms`**) remains tightly bounded across the conversation, running consistently **`3,964 ms` (`3.96s` / `62%`) below** the solid purple curve (`blocking_t0 Total=TTFT`, avg **`6,424 ms`**).
   - Meanwhile, the dashed teal curve (`streaming_t0 Total`, avg **`6,323 ms`**) tracks `blocking_t0` (`6,424 ms`) almost identically, proving that streaming introduces zero completion-time penalty.
2. **Right Panel (`thinking=default`): Volatility Dominated by Thinking Token Count**:
   - Under `thinking=default`, the model dynamically generates an average of **`858–954` thinking tokens** per turn (shaded vertical bars, range `0–2,237 tokens`), causing both `streaming_default` TTFT (avg **`9,838 ms`**) and `blocking_default` Total (avg **`13,025 ms`**) to fluctuate wildly up to `22.0s` regardless of turn number.

---

## 5.4 Thinking Token Volatility & 2D Trajectory Snapshots (Turn 1 vs Turn 25 vs Turn 50)

To prove what drives latency under `thinking=default` and visualize how chunks arrive across early (**Turn 1**), mid (**Turn 25**), and late (**Turn 50**) conversation turns, Figure 5-4 pairs a **scatter plot of `thoughts_tokens` vs `total_ms` across all 100 `thinking=default` executions (`50 turns × 2 modes`)** on the left with a **3-Turn Trajectory Overlay (`Turn 1`, `Turn 25`, `Turn 50` from `load_multiturn_trajectory()`)** on the right.

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
    "Thinking Tokens vs Total Latency (Left) & Turn 1 / 25 / 50 Trajectories (Right)",
    style=Styles.DarkBold.patch(text_size=11.5),
)

# =========================================================================
# Left Panel: Scatter plot of thoughts_tokens vs total_ms (100 default runs + t=0 ref)
# =========================================================================
rectangle((42.5, 47.5), width=71.0, height=73.0, style=Styles.WhiteFlat.patch(shape_r=1.5, line_width=0.8))
rectangle((42.5, 77.2), width=67.0, height=11.2, style=Styles.Neutral.patch(shape_r=1.1))
text(
    (42.5, 80.4),
    "Left: thoughts_tokens vs total_ms (Total ≈ 6,300ms + 7.0ms×ThTok)",
    style=Styles.DarkBold.patch(text_size=10.0),
)

pts_s_def: list[tuple[float, float]] = []
pts_b_def: list[tuple[float, float]] = []
pts_s_t0: list[tuple[float, float]] = []

for t_rec in load_multiturn_turns():
    v = t_rec["variants"]
    pts_s_def.append((float(v["streaming_default"]["thoughts_tokens"]), float(v["streaming_default"]["total_ms"])))
    pts_b_def.append((float(v["blocking_default"]["thoughts_tokens"]), float(v["blocking_default"]["total_ms"])))
    pts_s_t0.append((0.0, float(v["streaming_t0"]["total_ms"])))

# Compact legend inside Left Panel header
circle((11.0, 76.2), radius=0.65, style=Styles.WarningFlat)
text((12.5, 76.2), "streaming_default (50 runs)", style=Styles.DarkBold.patch(text_size=10.0, halign="left"))
circle((46.0, 76.2), radius=0.65, style=Styles.DangerFlat)
text((47.5, 76.2), "blocking_default (50 runs)", style=Styles.DarkBold.patch(text_size=10.0, halign="left"))
circle((11.0, 73.0), radius=0.65, style=Styles.PrimaryFlat)
text((12.5, 73.0), "streaming_t0 (X=0 ref, 50 runs)   Strong Linear Scaling", style=Styles.Dark.patch(text_size=10.0, halign="left"))

scatter = ScatterChart(
    axis_line_style=Styles.Dark,
    axis_text_style=Styles.Dark.patch(text_size=10.0),
    grid_style=Styles.MutedDashed,
    width=63.0,
    height=46.0,
    default_radius=0.85,
)
scatter.configure_x_axis(
    label="Internal Thinking Tokens (thoughts_token_count [tok])",
    min_value=0,
    max_value=2400,
    tick_step=800,
    format="{:,.0f}",
)
scatter.configure_y_axis(
    label="Total Latency (ms)",
    min_value=0,
    max_value=24000,
    tick_step=6000,
    format="{:,.0f}",
)
scatter.add_series("blocking_default", pts_b_def, style=Styles.DangerFlat, shape="rhombus", radius=0.85)
scatter.add_series("streaming_default", pts_s_def, style=Styles.WarningFlat, shape="triangle", radius=0.9)
scatter.add_series("streaming_t0", pts_s_t0, style=Styles.PrimaryFlat, shape="circle", radius=0.85)
scatter.draw(xy=(11.5, 18.0))

# =========================================================================
# Right Panel: 3-Turn Trajectory Overlay (Turn 1, Turn 25, Turn 50)
# =========================================================================
rectangle((115.5, 47.5), width=71.0, height=73.0, style=Styles.WhiteFlat.patch(shape_r=1.5, line_width=0.8))
rectangle((115.5, 77.2), width=67.0, height=11.2, style=Styles.Neutral.patch(shape_r=1.1))
text(
    (115.5, 80.4),
    "Right: Turn 1, Turn 25 & Turn 50 Trajectories (Time vs Chars)",
    style=Styles.DarkBold.patch(text_size=10.0),
)

# Legend for Right Panel trajectories
line((83.5, 76.2), (87.5, 76.2), style=Styles.PrimaryBold.patch(line_width=2.4))
text((88.5, 76.2), "streaming_t0", style=Styles.DarkBold.patch(text_size=10.0, halign="left"))

line((111.5, 76.2), (115.5, 76.2), style=Styles.SecondaryBold.patch(line_width=2.2))
text((116.5, 76.2), "blocking_t0", style=Styles.DarkBold.patch(text_size=10.0, halign="left"))

line((83.5, 73.0), (87.5, 73.0), style=Styles.DangerDashed.patch(line_width=2.0))
text((88.5, 73.0), "streaming_default (stalled during thinking)", style=Styles.Dark.patch(text_size=10.0, halign="left"))

sub_panels = [
    (1, 54.0, "Turn 1 (176 tok / Initial Power Issue): blk_t0 5,418ms vs str_def 10,411ms"),
    (25, 35.0, "Turn 25 (10,060 tok / Cache 75.0%): str_t0 3,833ms vs blk_t0 5,962ms"),
    (50, 16.0, "Turn 50 (21,490 tok / Cache 88.4%): str_t0 4,083ms vs blk_t0 8,074ms"),
]

max_t = 20000.0
max_c = 1050.0
pw = 55.0
ph = 12.2
px0 = 88.5

for t_num, py0, sub_title in sub_panels:
    text((px0 + pw / 2, py0 + ph + 2.0), sub_title, style=Styles.DarkBold.patch(text_size=10.0))
    rectangle((px0 + pw / 2, py0 + ph / 2), width=pw, height=ph, style=Styles.Neutral.patch(line_width=0.5, shape_r=0))

    def to_x(ms: float) -> float:
        return px0 + min(max(ms, 0.0), max_t) / max_t * pw

    def to_y(ch: float, base_y: float = py0) -> float:
        return base_y + min(max(ch, 0.0), max_c) / max_c * ph

    for xt in (0, 5000, 10000, 15000, 20000):
        tx = to_x(float(xt))
        line((tx, py0), (tx, py0 + ph), style=Styles.MutedDashed.patch(line_width=0.5))
        if t_num == 50:
            text((tx, py0 - 2.2), f"{xt // 1000}s", style=Styles.Dark.patch(text_size=10.0))

    for yt in (0, 500, 1000):
        ty = to_y(float(yt))
        line((px0, ty), (px0 + pw, ty), style=Styles.MutedDashed.patch(line_width=0.5))
        text((px0 - 1.2, ty), f"{yt}", style=Styles.Dark.patch(text_size=10.0, halign="right"))

    line((px0, py0), (px0 + pw, py0), style=Styles.Dark.patch(line_width=1.0))
    line((px0, py0), (px0, py0 + ph), style=Styles.Dark.patch(line_width=1.0))

    for v_key, st_line in (
        ("streaming_default", Styles.DangerDashed.patch(line_width=1.9)),
        ("blocking_t0", Styles.SecondaryBold.patch(line_width=2.0)),
        ("streaming_t0", Styles.PrimaryBold.patch(line_width=2.4)),
    ):
        tr = load_multiturn_trajectory(t_num, v_key)
        gem_pts = tr["timeline_series"].get("gemini", [])
        if len(gem_pts) >= 2:
            coords = [(to_x(float(p["t_ms"])), to_y(float(p["chars"]))) for p in gem_pts]
            lines(coords, style=st_line)

text((px0 + pw / 2, 11.2), "Elapsed Time (s) — Y-Axis: Cumulative Output Characters (0–1,000 chars)", style=Styles.DarkBold.patch(text_size=10.0))

# Bottom callout bar
rectangle((78.0, 5.8), width=146.0, height=5.8, style=Styles.SecondaryNeutral.patch(shape_r=1.2))
text(
    (78.0, 5.8),
    "Conclusion: At Turns 25 and 50, streaming_t0 (solid blue) begins streaming 2.1–4.0s earlier than blocking_t0 despite 21.5k input tokens.",
    style=Styles.DarkBold.patch(text_size=10.0),
)

save()
```

### Key Findings from the Scatter & Trajectory Analysis

1. **Left Panel: `Total ≈ 6,300 ms + 7.0 ms × ThTok` Governs Multi-Turn Latency**:
   - Plotting all 100 `thinking=default` executions (`50 turns × 2 modes`) confirms that total completion time is governed by reasoning token count (`0–2,237 tokens`), **not** turn number (`Total ≈ 6,300 ms + 7.0 ms × ThTok`).
   - The `~6,300 ms` y-intercept represents the base decoding time for a `~753-char` detailed technical support response, while each 1,000 thinking tokens add `~7.0 seconds` of pre-output delay.
2. **Right Panel: 3-Turn Trajectory Snapshots (`Turn 1`, `Turn 25`, `Turn 50`)**:
   - **Turn 1 (`176 tok`, Cache `0%`, Initial Unresponsive PC Query)**: Apart from the initial cold request, `blocking_t0` (solid purple) remains flat at `0 chars` until **`5,418 ms`**, and `streaming_default` (dashed red) stalls at `0 chars` for **`10,411 ms`** (`1,087` thinking tokens) before streaming.
   - **Turn 25 (`10,060 tok`, Cache `7,547 tok [75.0%]`, BIOS/Chipset Update Guide)**: Even with 57× more input context, `streaming_t0` (solid blue) starts streaming at **`3,833 ms`**, delivering the first visible characters **`2,129 ms` (`36%`) earlier** than `blocking_t0` (`5,962 ms`).
   - **Turn 50 (`21,490 tok`, Cache `18,995 tok [88.4%]`, Preventive Maintenance Summary)**: At the 50th turn (`122×` larger context), Implicit Context Caching serves `88.4–90.6%` of the prompt from KV cache. As a result, `streaming_t0` begins streaming at **`4,083 ms`**—**`3,991 ms` (`49%`) earlier** than `blocking_t0` (`8,074 ms`)—and completes the `902-char` reply at `9,554 ms` (whereas `streaming_default` stalls for `16,498 ms` due to `1,584` thinking tokens).

---

## 5.5 Comprehensive 10-Turn Cohort Table & Production Guidelines for Multi-Turn Chat

### 1. 10-Turn Cohort Summary Table (`Turns 1–10` through `Turns 41–50`)

The table below summarizes input token growth, Implicit Context Cache hit rates, and latency across 10-turn cohorts and all 50 turns combined.

| Turn Cohort & Troubleshooting Stage | Avg `prompt_tokens`<br>(Min–Max) | Avg `cached_tokens`<br>(`streaming_t0` Hit Rate) | `streaming_t0`<br>TTFT / Total (`ms`) | `blocking_t0`<br>TTFT = Total (`ms`) | Streaming TTFT Lead<br>(`streaming_t0 - blocking_t0`) | `streaming_default`<br>TTFT / Total (`ms`) [Avg ThTok] | `blocking_default`<br>Total (`ms`) [Avg ThTok] |
| :--- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| **Turns 1–10**<br>(Power, Discharge, BIOS, Safe Mode) | `1,768 tok`<br>(`176–3,407`) | `177 tok`<br>(`10.0%`, active T8–9) | **`2,853`** / `5,910 ms`<br>(T2–10: `2,000 ms`) | `5,125 ms` | **`-2,272 ms`** (`-44.3%`) | `11,687` / `13,467 ms`<br>[`1,211 tok`] | `12,988 ms`<br>[`1,099 tok`] |
| **Turns 11–20**<br>(Backup, Drivers, `sfc`, Memory Diag) | `5,635 tok`<br>(`3,817–7,539`) | `3,229 tok`<br>(`57.3%`) | **`2,180`** / `5,586 ms` | `6,742 ms` | **`-4,562 ms`** (`-67.7%`) | `9,357` / `11,643 ms`<br>[`828 tok`] | `14,398 ms`<br>[`1,154 tok`] |
| **Turns 21–30**<br>(SSD SMART, Restore, USB Boot Media) | `10,280 tok`<br>(`8,005–12,478`) | `7,784 tok`<br>(`75.7%`) | **`2,361`** / `6,804 ms` | `6,666 ms` | **`-4,305 ms`** (`-64.6%`) | `9,969` / `12,658 ms`<br>[`913 tok`] | `12,731 ms`<br>[`954 tok`] |
| **Turns 31–40**<br>(BitLocker, HW Diag, Pickup Repair) | `15,007 tok`<br>(`12,995–16,915`) | `12,556 tok`<br>(`83.7%`) | **`2,331`** / `6,260 ms` | `6,653 ms` | **`-4,322 ms`** (`-65.0%`) | `8,265` / `11,405 ms`<br>[`517 tok`] | `12,480 ms`<br>[`802 tok`] |
| **Turns 41–50**<br>(Loaner PC, On-Site, Backup & Maint) | `19,338 tok`<br>(`17,309–21,490`) | `16,872 tok`<br>(**`87.2%`**) | **`2,574`** / `7,054 ms` | `6,935 ms` | **`-4,361 ms`** (`-62.9%`) | `9,910` / `12,504 ms`<br>[`823 tok`] | `12,527 ms`<br>[`763 tok`] |
| **All 50 Turns** | **`10,406 tok`**<br>(`176–21,490`) | **`8,124 tok`**<br>(`78.1%` / Peak **`90.6%`**) | **`2,460`** / **`6,323 ms`**<br>(Median **`2,029 ms`**) | **`6,424 ms`** | **`-3,964 ms`** (**`-61.7%`**) | **`9,838`** / **`12,335 ms`**<br>[**`858 tok`**] | **`13,025 ms`**<br>[**`954 tok`**] |

### 2. Production Architecture Guidelines for Multi-Turn Chat

1. **Preserve Strict Prefix Immutability to Maximize Implicit Context Caching**:
   - Gemini 3.8 Flash's Implicit Context Caching matches the exact token prefix across `system_instruction` and historical `contents: list[types.Content]`.
   - **Anti-Pattern**: Injecting per-request dynamic timestamps, random request UUIDs, or mutating device telemetry JSON inside `system_instruction` invalidates the token prefix on every turn, dropping the cache hit rate to `0%`.
   - **Best Practice**: Keep `system_instruction` static and treat `history: list[types.Content]` as strictly **append-only**. Place dynamic per-turn metadata (such as current diagnostic status or retrieved knowledge-base snippets) at the end of the latest user turn message.
2. **Standardize on `Streaming × thinking=0` (`streaming_t0`) for Conversational UX**:
   - When technical support responses average `~753 chars`, full token generation takes `~6.42 seconds` even with `thinking=0`.
   - Using `generate_content_stream` with `thinking_budget=0` delivers the first token in **`2,460 ms` on average (`2,029 ms` median, `3,964 ms` / `62%` earlier than Blocking)** and scales at just **`+29 ms per 1,000 input tokens`**, maintaining responsive UX through Turn 50.
3. **Combine Multi-Turn Prefix Caching with the Two-Field Integrated Adaptive Router (Pattern A)**:
   - Leaving `thinking=default` enabled across all turns inflates average TTFT to **`9,838 ms`**.
   - Instead, pair `thinking=0` streaming for routine troubleshooting turns with the **2-Field Integrated Pydantic Router (Pattern A)** from Chapter 4 when a turn requires complex multi-step cost or transfer-time math. Because Stage 1 (`thinking=0` prefix check) and Stage 2 (`thinking=low` parallel handoff) share the exact same `system_instruction` + `history` prefix, Stage 2 automatically benefits from the warmed Implicit Context Cache.
