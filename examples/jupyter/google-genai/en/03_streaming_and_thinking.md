# 03. Streaming Delivery & ThinkingConfig Control

Interactive AI applications on **`gemini-3.8-flash`** optimize perceived responsiveness along two independent axes: **streaming delivery (`generate_content_stream`)** cuts Time To First Token (TTFT) by yielding output chunks as soon as generation starts, while **`types.ThinkingConfig(thinking_level=...)`** right-sizes internal reasoning depth (`"low"`, `"medium"`, or `"high"`) to match each task's complexity.
Combining progressive streaming with an explicit thinking level turns multi-second blocking calls into sub-second interactive experiences—reserving deep chain-of-thought compute strictly for tasks that need it.

```drawlib align=center code=fold file=ch03_streaming_ttft.png caption="Figure 3-1: Blocking Generation vs. Streaming Delivery & Thinking Level Timeline (gemini-3.8-flash)"
from drawlib.canvas import save, setup
from drawlib.icons import phosphor
from drawlib.lines import line
from drawlib.shapes import rectangle
from drawlib.styles import Styles
from drawlib.text import text

setup(width=156, height=74, dpi=150)

# Header labels
text((6.0, 67.0), "Delivery Mode & Config", style=Styles.DarkBold.patch(text_size=11.0, halign="left"))
text(
    (101.0, 67.0),
    "Latency Timeline on gemini-3.8-flash (Seconds)",
    style=Styles.DarkBold.patch(text_size=11.0),
)

# Vertical timeline gridlines (0.0s to 3.0s -> x = 56.0 to 146.0, 30 units/sec)
for i in range(7):
    tx = 56.0 + i * 15.0
    sec = i * 0.5
    line((tx, 13.0), (tx, 62.5), style=Styles.MutedDashedThin)
    text((tx, 8.2), f"{sec:.1f}s", style=Styles.Muted.patch(text_size=10.0))

line((56.0, 13.0), (146.0, 13.0), style=Styles.Dark)

# Row 1: Blocking generate_content()
rectangle((29.0, 55.0), width=46.0, height=12.5, style=Styles.Neutral.patch(shape_r=1.8))
phosphor.hourglass((11.0, 55.0), width=4.4, style=Styles.Dark)
text((15.2, 57.3), "1. Blocking Call", style=Styles.DarkBold.patch(text_size=10.5, halign="left"))
text((15.2, 52.3), "generate_content()", style=Styles.Muted.patch(text_size=10.0, halign="left"))

rectangle(
    (72.5, 55.0),
    width=33.0,
    height=9.4,
    style=Styles.SecondaryNeutral.patch(shape_r=1.2),
    text="Thinking (1.1s)",
    text_style=Styles.Dark.patch(text_size=10.0),
)
rectangle(
    (114.8, 55.0),
    width=50.4,
    height=9.4,
    style=Styles.Neutral.patch(shape_r=1.2),
    text="Buffered Output • TTFT 2.8s",
    text_style=Styles.DarkBold.patch(text_size=10.0),
)

# Row 2: Streaming + thinking_level="medium" (Default)
rectangle((29.0, 38.5), width=46.0, height=12.5, style=Styles.Neutral.patch(shape_r=1.8))
phosphor.brain((11.0, 38.5), width=4.4, style=Styles.PrimaryBold)
text((15.2, 40.8), "2. Stream + Thinking", style=Styles.DarkBold.patch(text_size=10.5, halign="left"))
text((15.2, 35.8), 'thinking_level="medium"', style=Styles.Muted.patch(text_size=10.0, halign="left"))

rectangle(
    (72.5, 38.5),
    width=33.0,
    height=9.4,
    style=Styles.SecondaryNeutral.patch(shape_r=1.2),
    text="Thinking (1.1s)",
    text_style=Styles.Dark.patch(text_size=10.0),
)
rectangle(
    (114.8, 38.5),
    width=50.4,
    height=9.4,
    style=Styles.PrimaryNeutral.patch(shape_r=1.2),
    text="TTFT 1.1s -> Stream Chunks",
    text_style=Styles.PrimaryBold.patch(text_size=10.0),
)

# Row 3: Streaming + thinking_level="low" (Focal Hero)
rectangle((29.0, 22.0), width=46.0, height=12.5, style=Styles.PrimaryNeutral.patch(shape_r=1.8))
phosphor.lightning((11.0, 22.0), width=4.4, style=Styles.PrimaryBold)
text((15.2, 24.3), "3. Fast Stream", style=Styles.PrimaryBold.patch(text_size=10.5, halign="left"))
text((15.2, 19.3), 'thinking_level="low"', style=Styles.Dark.patch(text_size=10.0, halign="left"))

rectangle((60.0, 22.0), width=8.0, height=9.4, style=Styles.Neutral.patch(shape_r=1.0))
rectangle(
    (86.8, 22.0),
    width=44.4,
    height=9.4,
    style=Styles.PrimaryFlat.patch(shape_r=1.2),
    text="TTFT 0.28s • Instant Stream",
    text_style=Styles.WhiteBold.patch(text_size=10.0),
)
text((111.5, 22.0), "Done in 1.75s", style=Styles.PrimaryBold.patch(text_size=10.0, halign="left"))

save()
```

---

## 1. Client Setup & Progressive Streaming (`generate_content_stream`)

Start by setting `MODEL = "gemini-3.8-flash"` and initializing the unified `genai.Client` with your `GEMINI_API_KEY` stored in Google Colab Secrets (**🔑 Secrets** in the left sidebar):

```python
MODEL = "gemini-3.8-flash"

from google.colab import userdata
from google import genai

client = genai.Client(api_key=userdata.get("GEMINI_API_KEY"))
```

Whereas `client.models.generate_content()` buffers the entire completion on the server before returning, **`client.models.generate_content_stream()`** yields `GenerateContentResponse` chunks over an HTTP stream as soon as tokens are decoded. Measuring both **`ttft_ms`** (time until the first non-empty `chunk.text` arrives) and **`total_ms`** with `time.perf_counter()` quantifies how quickly users see the response start:

```python
import time

t0 = time.perf_counter()
ttft_ms = None

for chunk in client.models.generate_content_stream(
    model=MODEL,
    contents="Tell me a short story in 3 sentences.",
):
    if chunk.text:
        if ttft_ms is None:
            ttft_ms = (time.perf_counter() - t0) * 1000
        print(chunk.text, end="", flush=True)

total_ms = (time.perf_counter() - t0) * 1000
print(f"\n\nTTFT: {ttft_ms:.0f} ms | Total: {total_ms:.0f} ms")
```

> **Note:** Always guard `if chunk.text:` before printing or recording `ttft_ms`. Early or trailing stream frames (such as metadata-only chunks) can carry empty text payloads while updating `usage_metadata`.

---

## 2. Right-Sizing Reasoning with `ThinkingConfig` (`thinking_level`)

`gemini-3.8-flash` is a reasoning-capable model: before emitting visible output tokens, it can spend internal **thinking tokens** (`thoughts_token_count`) planning and verifying its answer. Because thinking runs *before* the first visible output token is emitted, setting `types.ThinkingConfig(thinking_level=...)` directly governs TTFT and token cost across three supported levels on `gemini-3.8-flash`:

- **`thinking_level="low"` (Zero Thoughts / Fastest TTFT)**: Produces `0` internal reasoning tokens on `gemini-3.8-flash`, delivering sub-second TTFT for conversational chat, intent routing, classification, and entity extraction.
- **`thinking_level="medium"` (Default — Balanced Dynamic Reasoning)**: Automatically adapts reasoning depth to prompt complexity—skipping extra thoughts on simple queries while allocating structured reasoning for RAG synthesis, summarization, and SQL drafting.
- **`thinking_level="high"` (Deep Reasoning)**: Dedicates thorough chain-of-thought tokens for multi-step math, algorithm generation, and architectural trade-off analysis.

> **Important (`gemini-3.8-flash` API Rules):** Numeric `thinking_budget` from Gemini 2.5 is deprecated in Gemini 3.8—use `thinking_level` instead (never pass both together). On `gemini-3.8-flash`, only `"low"`, `"medium"`, and `"high"` are valid; passing `"minimal"` or `"xhigh"` returns HTTP `400 INVALID_ARGUMENT`.

```drawlib align=center code=fold file=ch03_thinking_tiers.png caption="Figure 3-2: ThinkingConfig Levels by Task Complexity (gemini-3.8-flash)"
from drawlib.canvas import save, setup
from drawlib.icons import phosphor
from drawlib.smartarts import CardList
from drawlib.styles import Styles
from drawlib.text import text

setup(width=152, height=68, dpi=150)

text(
    (76.0, 61.5),
    "Selecting thinking_level Across Workload Tiers (gemini-3.8-flash)",
    style=Styles.DarkBold.patch(text_size=12.0),
)

tiers = CardList(
    style=Styles.Neutral,
    text_style=Styles.DarkBold.patch(text_size=11.0),
    description_style=Styles.Dark.patch(text_size=10.0),
    badge_shape="circle",
    badge_style=Styles.PrimaryNeutral,
    icon_style=Styles.PrimaryBold,
    direction="horizontal",
    show_arrows=True,
    arrow_style=Styles.Dark,
    spacing=5.0,
)
tiers.add(
    'level = "low"',
    "0 thoughts • Fast TTFT\nChat, routing, extraction\n& classification",
    icon=phosphor.lightning,
    badge_style=Styles.PrimaryFlat,
    icon_style=Styles.WhiteBold,
)
tiers.add(
    'level = "medium"',
    "Default • Dynamic depth\nRAG synthesis, SQL\n& balanced summaries",
    icon=phosphor.sliders,
    style=Styles.PrimaryNeutral,
)
tiers.add(
    'level = "high"',
    "Deep reasoning tokens\nMulti-step math, code\n& architecture design",
    icon=phosphor.brain,
)
tiers.draw(xy=(6.0, 6.5), width=140.0, height=49.5, align="bottom_left")

save()
```

### Benchmarking `thinking_level="low"` vs. `thinking_level="high"`

Let's run the same arithmetic prompt under `thinking_level="low"` and `thinking_level="high"`, capturing `ttft_ms`, `total_ms`, internal `thoughts_token_count`, and visible `candidates_token_count` from `usage_metadata` and printing a formatted comparison table:

```python
import time
from google.genai import types

prompt = "What is 27 * 43 + 19?"
rows = []

for level in ("low", "high"):
    t0 = time.perf_counter()
    ttft_ms = None
    usage = None
    chunks = []

    for chunk in client.models.generate_content_stream(
        model=MODEL,
        contents=prompt,
        config=types.GenerateContentConfig(
            thinking_config=types.ThinkingConfig(thinking_level=level),
        ),
    ):
        if chunk.text:
            if ttft_ms is None:
                ttft_ms = (time.perf_counter() - t0) * 1000
            chunks.append(chunk.text)
        if chunk.usage_metadata is not None:
            usage = chunk.usage_metadata

    total_ms = (time.perf_counter() - t0) * 1000
    thoughts_tokens = getattr(usage, "thoughts_token_count", 0) or 0
    output_tokens = getattr(usage, "candidates_token_count", 0) or 0
    rows.append((level, ttft_ms or total_ms, total_ms, thoughts_tokens, output_tokens))
    print(f"[{level}] {''.join(chunks).strip()}")

print(f"\n{'Level':<8} {'TTFT (ms)':>10} {'Total (ms)':>11} {'Thoughts Tok':>14} {'Output Tok':>12}")
print("-" * 59)
for level, ttft_ms, total_ms, thoughts_tokens, output_tokens in rows:
    print(f"{level:<8} {ttft_ms:>10.1f} {total_ms:>11.1f} {thoughts_tokens:>14d} {output_tokens:>12d}")
```

### Key Takeaways

- **Stream User-Facing Text (`generate_content_stream`)**: Eliminates full-response buffering so users read the opening sentence immediately after prefill and reasoning finish.
- **Match `thinking_level` to Route SLAs**: On `gemini-3.8-flash`, set `thinking_level="low"` (`0` thoughts) on latency-critical routers and chat, keep `"medium"` (default) for general workloads, and reserve `"high"` for complex analytical reasoning.
- **Inspect `thoughts_token_count`**: Monitor `usage_metadata.thoughts_token_count` alongside `candidates_token_count` to track internal reasoning token utilization and latency impact in production.
