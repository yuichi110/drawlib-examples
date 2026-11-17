# 05. Multi-Turn Chat & Python Function Calling

The `google-genai` SDK turns stateless model requests into stateful, tool-augmented assistants using two built-in primitives: **`client.chats.create()`** for managing multi-turn conversation history, and **Automatic Python Function Calling (`tools=[fn]`)**, where the SDK introspects Python type hints and docstrings, executes local functions when Gemini requests them, and feeds the structured results back automatically.

```drawlib align=center code=fold file=ch05_function_calling_loop.png caption="Figure 5-1: Automatic Python Function Calling Execution Loop in google-genai"
from drawlib.canvas import save, setup
from drawlib.icons import ai, phosphor
from drawlib.lines import line
from drawlib.shapes import rectangle
from drawlib.styles import Styles
from drawlib.text import text

setup(width=152, height=76, dpi=150)

# Title
text(
    (76.0, 69.5),
    "Automatic Python Function Calling Loop (tools=[get_region_latency])",
    style=Styles.DarkBold.patch(text_size=11.8),
)

# --- Top Row (y_center = 51.0, height = 21.0 -> [40.5, 61.5]) ---
# 1. User Prompt (Neutral)
rectangle((23.5, 51.0), width=35.0, height=21.0, style=Styles.Neutral.patch(shape_r=2.0))
phosphor.chat_circle_text((10.0, 56.8), width=3.8, style=Styles.DarkBold)
text((25.0, 56.8), "1. User Prompt", style=Styles.DarkBold.patch(text_size=10.5))
text(
    (23.5, 47.2),
    '"Compare latency:\n2 cloud regions"',
    style=Styles.Dark.patch(text_size=10.0),
)

# 2. genai.Client (Focal PrimaryFlat)
rectangle((75.0, 51.0), width=37.0, height=21.0, style=Styles.PrimaryFlat.patch(shape_r=2.0))
phosphor.gear_six((60.5, 56.8), width=3.8, style=Styles.WhiteBold)
text((76.8, 56.8), "2. genai.Client", style=Styles.WhiteBold.patch(text_size=10.8))
text(
    (75.0, 47.2),
    "Type hints & docstring\n-> Auto JSON Schema",
    style=Styles.White.patch(text_size=10.0),
)

# 3. Gemini FunctionCall (PrimaryNeutral)
rectangle((127.0, 51.0), width=38.0, height=21.0, style=Styles.PrimaryNeutral.patch(shape_r=2.0))
ai.gemini((112.5, 56.8), width=3.8, style=Styles.Primary)
text((128.5, 56.8), "3. Gemini 3.8", style=Styles.DarkBold.patch(text_size=10.5))
text(
    (127.0, 47.2),
    'FunctionCall:\nregion="asia-northeast1"',
    style=Styles.Dark.patch(text_size=10.0),
)

# --- Bottom Row (y_center = 16.5, height = 21.0 -> [6.0, 27.0]) ---
# 4. Local Python Tool Execution (SecondaryNeutral)
rectangle((127.0, 16.5), width=38.0, height=21.0, style=Styles.SecondaryNeutral.patch(shape_r=2.0))
phosphor.terminal_window((112.5, 22.3), width=3.8, style=Styles.DarkBold)
text((128.8, 22.3), "4. Python Tool Exec", style=Styles.DarkBold.patch(text_size=10.5))
text(
    (127.0, 12.7),
    "get_region_latency()\n-> {p50: 14.2, p95: 31.5}",
    style=Styles.Dark.patch(text_size=10.0),
)

# 5. FunctionResponse JSON -> Gemini (PrimaryNeutral)
rectangle((75.0, 16.5), width=37.0, height=21.0, style=Styles.PrimaryNeutral.patch(shape_r=2.0))
ai.gemini((60.5, 22.3), width=3.8, style=Styles.Primary)
text((77.2, 22.3), "5. FunctionResponse", style=Styles.DarkBold.patch(text_size=10.5))
text(
    (75.0, 12.7),
    "SDK feeds JSON result\nback to Gemini 3.8",
    style=Styles.Dark.patch(text_size=10.0),
)

# 6. Final Grounded Answer (Neutral)
rectangle((23.5, 16.5), width=35.0, height=21.0, style=Styles.Neutral.patch(shape_r=2.0))
phosphor.check_circle((10.0, 22.3), width=3.8, style=Styles.SuccessBold)
text((25.0, 22.3), "6. Final Answer", style=Styles.DarkBold.patch(text_size=10.5))
text(
    (23.5, 12.7),
    "asia-northeast1 wins\n(14.2 ms p50 grounded)",
    style=Styles.Dark.patch(text_size=10.0),
)

# --- Connectors ---
line((41.0, 51.0), (56.5, 51.0), arrow_head="->", style=Styles.DarkBold)
text((48.75, 54.5), "Prompt", style=Styles.Dark.patch(text_size=10.0))

line((93.5, 51.0), (108.0, 51.0), arrow_head="->", style=Styles.DarkBold)
text((100.75, 54.5), "Schema", style=Styles.Dark.patch(text_size=10.0))

line((127.0, 40.5), (127.0, 27.0), arrow_head="->", style=Styles.PrimaryBold)
text((137.5, 33.75), "Invoke fn()", style=Styles.PrimaryBold.patch(text_size=10.0))

line((108.0, 16.5), (93.5, 16.5), arrow_head="->", style=Styles.DarkBold)
text((100.75, 20.0), "JSON", style=Styles.Dark.patch(text_size=10.0))

line((56.5, 16.5), (41.0, 16.5), arrow_head="->", style=Styles.SuccessBold)
text((48.75, 20.0), "Answer", style=Styles.SuccessBold.patch(text_size=10.0))

# SDK orchestration link across top and bottom stages
line((75.0, 40.5), (75.0, 27.0), arrow_head="->", style=Styles.PrimaryDashed)
text((85.5, 33.75), "Auto-Loop", style=Styles.PrimaryBold.patch(text_size=10.0))

save()
```

---

## 1. Client Setup & Stateful Multi-Turn Chat (`client.chats.create`)

Define `MODEL = "gemini-3.8-flash"` at the top of the cell, then read your `GEMINI_API_KEY` from Google Colab Secrets (`userdata.get`) to initialize a unified `genai.Client`:

```python
MODEL = "gemini-3.8-flash"

from google.colab import userdata
from google import genai

client = genai.Client(api_key=userdata.get("GEMINI_API_KEY"))
```

While `client.models.generate_content()` is stateless, **`client.chats.create()`** maintains an in-memory `list[types.Content]` transcript across turns. Each call to `chat.send_message()` appends a `Content(role="user")` message, sends the accumulated history to Gemini, and records the returned `Content(role="model")` turn (along with any intermediate tool calls). Because multi-turn sessions resend a growing shared prefix on every turn, they automatically benefit from Gemini 3.8's **Implicit Context Caching**, lowering time-to-first-token (TTFT) and input token cost on repeated prefixes with zero extra configuration.

```drawlib align=center code=fold file=ch05_chat_state_context.png caption="Figure 5-2: Multi-Turn Chat History Accumulation and Tool-Augmented Session Flow"
from drawlib.canvas import save, setup
from drawlib.icons import ai, phosphor
from drawlib.lines import line
from drawlib.shapes import rectangle
from drawlib.styles import Styles
from drawlib.text import text

setup(width=152, height=76, dpi=150)

# Title
text(
    (76.0, 69.5),
    "Multi-Turn History Accumulation & Implicit Context Caching",
    style=Styles.DarkBold.patch(text_size=11.8),
)

# --- Left Column: Sequential Notebook Calls (x in [6, 44], cx = 25.0) ---
rectangle((25.0, 51.0), width=38.0, height=14.0, style=Styles.Neutral.patch(shape_r=2.0))
phosphor.chat_circle((10.0, 53.8), width=3.5, style=Styles.DarkBold)
text((26.5, 53.8), "Turn 1: send_message()", style=Styles.DarkBold.patch(text_size=10.2))
text((25.0, 47.6), "Initial user message", style=Styles.Dark.patch(text_size=10.0))

rectangle((25.0, 32.0), width=38.0, height=14.0, style=Styles.Neutral.patch(shape_r=2.0))
phosphor.chats_circle((10.0, 34.8), width=3.5, style=Styles.DarkBold)
text((26.5, 34.8), "Turn 2: send_message()", style=Styles.DarkBold.patch(text_size=10.2))
text((25.0, 28.6), "Context-aware follow-up", style=Styles.Dark.patch(text_size=10.0))

rectangle((25.0, 13.0), width=38.0, height=14.0, style=Styles.PrimaryFlat.patch(shape_r=2.0))
phosphor.wrench((10.0, 15.8), width=3.5, style=Styles.WhiteBold)
text((26.5, 15.8), "Turn 3: Tool-Enabled", style=Styles.WhiteBold.patch(text_size=10.2))
text((25.0, 9.6), "tools=[get_region_latency]", style=Styles.White.patch(text_size=10.0))

# --- Center Container: Session History Stack (x in [56, 104], cx = 80.0) ---
rectangle((80.0, 34.5), width=48.0, height=57.0, style=Styles.MutedDashed.patch(shape_r=2.5))
text((80.0, 59.2), "chat.get_history() (list[Content])", style=Styles.DarkBold.patch(text_size=10.4))

rectangle((80.0, 51.0), width=42.0, height=7.6, style=Styles.Neutral.patch(shape_r=1.5))
text((80.0, 51.0), '1. Content(role="user")', style=Styles.DarkBold.patch(text_size=10.0))

rectangle((80.0, 41.5), width=42.0, height=7.6, style=Styles.PrimaryNeutral.patch(shape_r=1.5))
text((80.0, 41.5), '2. Content(role="model")', style=Styles.Dark.patch(text_size=10.0))

rectangle((80.0, 32.0), width=42.0, height=7.6, style=Styles.Neutral.patch(shape_r=1.5))
text((80.0, 32.0), '3. Content(role="user")', style=Styles.DarkBold.patch(text_size=10.0))

rectangle((80.0, 22.5), width=42.0, height=7.6, style=Styles.PrimaryNeutral.patch(shape_r=1.5))
text((80.0, 22.5), '4. Content(role="model")', style=Styles.Dark.patch(text_size=10.0))

rectangle((80.0, 13.0), width=42.0, height=7.6, style=Styles.SecondaryNeutral.patch(shape_r=1.5))
text((80.0, 13.0), "5. FunctionCall + Response", style=Styles.DarkBold.patch(text_size=10.0))

# --- Right Column: Gemini 3.8 & Implicit Caching (x in [115, 146], cx = 130.5) ---
rectangle((130.5, 48.5), width=31.0, height=25.0, style=Styles.PrimaryNeutral.patch(shape_r=2.0))
ai.gemini((130.5, 56.2), width=4.2, style=Styles.Primary)
text((130.5, 50.2), "Gemini 3.8 API", style=Styles.DarkBold.patch(text_size=10.5))
text(
    (130.5, 42.0),
    "Full Content[] list\nsent each turn",
    style=Styles.Dark.patch(text_size=10.0),
)

rectangle((130.5, 18.5), width=31.0, height=25.0, style=Styles.SecondaryNeutral.patch(shape_r=2.0))
phosphor.lightning((119.5, 26.5), width=3.8, style=Styles.SuccessBold)
text((132.2, 26.5), "Implicit Cache", style=Styles.DarkBold.patch(text_size=10.5))
text(
    (130.5, 15.5),
    "Repeated prefix\ncached auto-free\n(lower latency)",
    style=Styles.Dark.patch(text_size=10.0),
)

# --- Orthogonal Connectors ---
line((44.0, 51.0), (59.0, 51.0), arrow_head="->", style=Styles.DarkBold)
line((44.0, 32.0), (59.0, 32.0), arrow_head="->", style=Styles.DarkBold)
line((44.0, 13.0), (59.0, 13.0), arrow_head="->", style=Styles.PrimaryBold)

line((104.0, 48.5), (115.0, 48.5), arrow_head="->", style=Styles.DarkBold)
line((104.0, 18.5), (115.0, 18.5), arrow_head="->", style=Styles.SuccessBold)

save()
```

Create a stateful chat session with `MODEL` (`gemini-3.8-flash`), send two short messages, and inspect `chat.get_history()` to verify how `user` and `model` turns accumulate:

```python
chat = client.chats.create(model=MODEL)

reply_1 = chat.send_message("My favorite programming language is Python.")
print("Turn 1:", reply_1.text)

reply_2 = chat.send_message("What is my favorite language, in one sentence?")
print("Turn 2:", reply_2.text)

print("\n--- Accumulated Session History ---")
for idx, turn in enumerate(chat.get_history(), start=1):
    preview = " ".join(
        p.text.strip() for p in (turn.parts or []) if p.text and not p.thought
    )
    print(f"[{idx}] role={turn.role:<5} | {preview[:80]}")
```

---

## 2. Automatic Python Function Calling & Tool-Enabled Chat

To give Gemini live access to external metrics, databases, or internal APIs, pass plain typed Python functions directly into **`types.GenerateContentConfig(tools=[...])`**. Include **type annotations** (`region: str -> dict[str, float]`) and a clear **Google-style docstring** (`Args:` and `Returns:`): the SDK compiles them into a JSON Schema tool declaration automatically.

First, call `client.models.generate_content(model=MODEL, ...)` with a one-line prompt comparing two regions. `genai.Client` executes `get_region_latency()` locally for each requested region, feeds the returned dictionaries back as `FunctionResponse` payloads, and prints the grounded comparison:

```python
from google.genai import types

REGION_LATENCY_MS: dict[str, dict[str, float]] = {
    "asia-northeast1": {"p50_ms": 14.2, "p95_ms": 31.5},
    "us-central1": {"p50_ms": 24.5, "p95_ms": 58.4},
    "europe-west1": {"p50_ms": 38.6, "p95_ms": 84.2},
}


def get_region_latency(region: str) -> dict[str, float]:
    """Fetch live p50 and p95 API latency in milliseconds for a cloud region.

    Args:
        region: Cloud region ID ('asia-northeast1', 'us-central1', or 'europe-west1').

    Returns:
        Dictionary with 'p50_ms' median and 'p95_ms' tail latency values.
    """
    return REGION_LATENCY_MS.get(region, {"p50_ms": -1.0, "p95_ms": -1.0})


response = client.models.generate_content(
    model=MODEL,
    contents="Compare latency in asia-northeast1 and us-central1.",
    config=types.GenerateContentConfig(
        tools=[get_region_latency],
        temperature=0.1,
    ),
)
print(response.text)
```

Next, combine both primitives by passing `tools=[get_region_latency]` into **`client.chats.create(model=MODEL, config=...)`**. Across follow-up turns, the session remembers earlier regions while invoking new tool calls on demand and recording every `FunctionCall` and `FunctionResponse` inside `tool_chat.get_history()`:

```python
tool_chat = client.chats.create(
    model=MODEL,
    config=types.GenerateContentConfig(
        tools=[get_region_latency],
        temperature=0.1,
    ),
)

turn_1 = tool_chat.send_message("Check latency in asia-northeast1 and us-central1.")
print("Turn 1:\n", turn_1.text)

turn_2 = tool_chat.send_message("Check europe-west1 too. Which is fastest, in one sentence?")
print("\nTurn 2:\n", turn_2.text)

print("\n--- Recorded Tool Call Trace ---")
for turn in tool_chat.get_history():
    for part in turn.parts or []:
        if part.function_call:
            fc = part.function_call
            print(f"-> FunctionCall: {fc.name}({dict(fc.args or {})})")
        elif part.function_response:
            print(f"<- FunctionResponse: {part.function_response.response}")
```

> **Key Takeaways**: Define `MODEL = "gemini-3.8-flash"` once at the top of your notebook, use `client.chats.create(model=MODEL)` for stateful multi-turn context, pass typed Python functions into `tools=[fn]` for automatic function calling with `generate_content()`, and combine both in a tool-enabled chat session to handle multi-step follow-up questions with zero manual tool-loop boilerplate.
