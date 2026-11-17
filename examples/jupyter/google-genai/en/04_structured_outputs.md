# 04. Type-Safe Structured Outputs with Pydantic

Prompting an LLM to "reply only in JSON" often breaks in production when responses include conversational preambles, trailing commas, or ` ```json ` Markdown code fences. Passing `response_mime_type="application/json"` together with `response_schema=<Pydantic BaseModel>` activates **grammar-constrained decoding**: Gemini restricts token sampling directly to the JSON Schema grammar derived from your model, and `response.parsed` returns an already-validated Pydantic instance with zero brittle regex or string stripping.

```drawlib align=center code=fold file=ch04_structured_pipeline.png caption="Figure 4-1: Grammar-Constrained Structured Output Pipeline with Pydantic"
from drawlib.canvas import save, setup
from drawlib.icons import phosphor
from drawlib.lines import line
from drawlib.shapes import rectangle
from drawlib.styles import Styles
from drawlib.text import text

setup(width=152, height=72, dpi=150)

# Outer pipeline boundary (Z-Layer 1)
rectangle((76, 36), width=142, height=62, style=Styles.MutedDashed.patch(shape_r=2.5))
text(
    (76, 61.5),
    "Grammar-Constrained Structured Extraction Pipeline (google-genai + Pydantic)",
    style=Styles.DarkBold.patch(text_size=12.0),
)

# 4-stage horizontal coordinates: 4 cards of width=29.5 with 6.0-unit arrow gaps
card_w = 29.5
card_h = 39.0
card_cy = 34.0
stage_xs = [22.75, 58.25, 93.75, 129.25]

# Stage 1: Unstructured Input + Pydantic Schema (Neutral)
rectangle((stage_xs[0], card_cy), width=card_w, height=card_h, style=Styles.Neutral.patch(shape_r=2.0))
phosphor.file_code((stage_xs[0], 46.8), width=6.0, style=Styles.PrimaryBold)
text((stage_xs[0], 39.0), "1. Input + Schema", style=Styles.DarkBold.patch(text_size=10.8))
text(
    (stage_xs[0], 25.0),
    "Incident Text\n+\nIncidentSummary\n(BaseModel)",
    style=Styles.Dark.patch(text_size=10.0),
)

# Stage 2: Grammar-Constrained Decoding (Focal Hero: PrimaryFlat)
rectangle((stage_xs[1], card_cy), width=card_w, height=card_h, style=Styles.PrimaryFlat.patch(shape_r=2.0))
phosphor.sparkle((stage_xs[1], 46.8), width=6.0, style=Styles.WhiteBold)
text((stage_xs[1], 39.0), "2. Grammar Decode", style=Styles.WhiteBold.patch(text_size=10.8))
text(
    (stage_xs[1], 25.0),
    "application/json\n+\nresponse_schema\n(Gemini 3.8)",
    style=Styles.White.patch(text_size=10.0),
)

# Stage 3: Validated Python Object (PrimaryNeutral)
rectangle((stage_xs[2], card_cy), width=card_w, height=card_h, style=Styles.PrimaryNeutral.patch(shape_r=2.0))
phosphor.shield_check((stage_xs[2], 46.8), width=6.0, style=Styles.PrimaryBold)
text((stage_xs[2], 39.0), "3. response.parsed", style=Styles.DarkBold.patch(text_size=10.8))
text(
    (stage_xs[2], 25.0),
    "Validated Instance\nsummary.severity\nsummary.action_items",
    style=Styles.Dark.patch(text_size=10.0),
)

# Stage 4: Downstream Typed Application & DB (SecondaryNeutral)
rectangle((stage_xs[3], card_cy), width=card_w, height=card_h, style=Styles.SecondaryNeutral.patch(shape_r=2.0))
phosphor.database((stage_xs[3], 46.8), width=6.0, style=Styles.SecondaryBold)
text((stage_xs[3], 39.0), "4. Typed App / DB", style=Styles.DarkBold.patch(text_size=10.8))
text(
    (stage_xs[3], 25.0),
    "Queue Routing\nAlerting &\nDB Persistence",
    style=Styles.Dark.patch(text_size=10.0),
)

# Connectors across 6.0-unit gaps (Z-Layer 3)
for idx in range(3):
    x_start = stage_xs[idx] + card_w / 2.0
    x_end = stage_xs[idx + 1] - card_w / 2.0
    line((x_start, card_cy), (x_end, card_cy), arrow_head="->", style=Styles.PrimaryBold)

text(
    (76, 9.2),
    "Zero regex or code-fence stripping — token sampling is constrained directly to the JSON Schema grammar",
    style=Styles.Muted.patch(text_size=10.0),
)

save()
```

---

## 1. Client Setup & Defining a Nested Pydantic Schema

First, set `MODEL = "gemini-3.8-flash"` at the top of the cell so you can switch models in one place, and initialize the `google-genai` client using your `GEMINI_API_KEY` stored in Google Colab Secrets (`🔑` panel on the left sidebar):

```python
MODEL = "gemini-3.8-flash"

from google.colab import userdata
from google import genai

client = genai.Client(api_key=userdata.get("GEMINI_API_KEY"))
```

Next, compose a nested Pydantic schema (`ActionItem` inside `IncidentSummary`) to extract structured postmortem metadata from a concise incident report. Passing `IncidentSummary` to `response_schema` instructs the SDK to compile the Pydantic model into a strict schema and populate `response.parsed` automatically (`pydantic` comes pre-installed in Google Colab and bundled with `google-genai`):

```python
from typing import Literal

from google.genai import types
from pydantic import BaseModel, Field


class ActionItem(BaseModel):
    owner: str = Field(description="Team responsible for the follow-up task.")
    task: str = Field(description="Concrete remediation step.")
    priority: Literal["P0", "P1", "P2"] = Field(description="Urgency tier (P0 highest).")


class IncidentSummary(BaseModel):
    title: str = Field(description="Concise incident headline under 60 characters.")
    severity: Literal["LOW", "MEDIUM", "HIGH", "CRITICAL"] = Field(
        description="Customer-impact severity level."
    )
    root_cause: str = Field(description="One-sentence technical root cause.")
    affected_services: list[str] = Field(description="Impacted service names.")
    action_items: list[ActionItem] = Field(description="Prioritized follow-up tasks.")


response = client.models.generate_content(
    model=MODEL,
    contents="Checkout API returned 502 errors for EU users for 12 minutes due to a Redis timeout.",
    config=types.GenerateContentConfig(
        response_mime_type="application/json",
        response_schema=IncidentSummary,
        temperature=0.1,
    ),
)

# response.parsed is an already-validated IncidentSummary instance with full IDE autocomplete
summary: IncidentSummary = response.parsed
print(f"[{summary.severity}] {summary.title} ({len(summary.action_items)} action items)")
print(summary.model_dump_json(indent=2))
```

---

## 2. Schema Design Best Practices & Fast Deterministic Classification

While grammar-constrained decoding guarantees syntactic validity, thoughtful Pydantic schema design dramatically improves **semantic accuracy** and **latency** on production workloads:

```drawlib align=center code=fold file=ch04_schema_best_practices.png caption="Figure 4-2: Pydantic Schema Design Patterns for Reliable LLM Extraction"
from drawlib.canvas import save, setup
from drawlib.icons import phosphor
from drawlib.shapes import rectangle
from drawlib.smartarts import CardList
from drawlib.styles import Styles
from drawlib.text import text

setup(width=152, height=74, dpi=150)

rectangle((76, 37), width=142, height=64, style=Styles.MutedDashed.patch(shape_r=2.5))
text(
    (76, 63.5),
    "4 Pydantic Schema Design Rules for Deterministic Gemini Extraction",
    style=Styles.DarkBold.patch(text_size=12.0),
)

# Left Column: Top-Left (R1) & Bottom-Left (R3)
left_cards = CardList(
    style=Styles.Neutral.patch(shape_r=2.0),
    text_style=Styles.DarkBold.patch(text_size=10.8),
    description_style=Styles.Dark.patch(text_size=10.0),
    badge_shape="rounded_rect",
    badge_style=Styles.SecondaryNeutral,
    badge_text_style=Styles.PrimaryBold.patch(text_size=10.0),
    icon_style=Styles.PrimaryBold,
    direction="vertical",
    spacing=4.0,
)
left_cards.add(
    "1. Closed Categories via Literal / Enum",
    "Constrain severity & queue labels\ninstead of free-form str fields.",
    badge_text="R1",
    icon=phosphor.tag,
    style=Styles.PrimaryNeutral.patch(shape_r=2.0),
    badge_style=Styles.PrimaryFlat,
    badge_text_style=Styles.WhiteBold.patch(text_size=10.0),
    icon_style=Styles.WhiteBold,
)
left_cards.add(
    "3. Concise Field(description=...) Hints",
    "Clarify units, length caps & edge cases\ndirectly on ambiguous attributes.",
    badge_text="R3",
    icon=phosphor.file_text,
)
left_cards.draw(xy=(9.0, 9.0), width=64.5, height=49.0, align="bottom_left")

# Right Column: Top-Right (R2) & Bottom-Right (R4)
right_cards = CardList(
    style=Styles.Neutral.patch(shape_r=2.0),
    text_style=Styles.DarkBold.patch(text_size=10.8),
    description_style=Styles.Dark.patch(text_size=10.0),
    badge_shape="rounded_rect",
    badge_style=Styles.SecondaryNeutral,
    badge_text_style=Styles.PrimaryBold.patch(text_size=10.0),
    icon_style=Styles.PrimaryBold,
    direction="vertical",
    spacing=4.0,
)
right_cards.add(
    "2. Nested list[SubModel] Composition",
    "Replace untyped dict[str, Any] maps\nwith explicit Pydantic sub-models.",
    badge_text="R2",
    icon=phosphor.tree_structure,
)
right_cards.add(
    '4. Low Temp + thinking_level="low"',
    'Pair temperature=0.0-0.2 with\nthinking_level="low" on Gemini 3.8.',
    badge_text="R4",
    icon=phosphor.lightning,
    style=Styles.SecondaryNeutral.patch(shape_r=2.0),
)
right_cards.draw(xy=(78.5, 9.0), width=64.5, height=49.0, align="bottom_left")

save()
```

Keep these four engineering rules in mind when authoring schemas for `response_schema`:

1. **Use `Literal` or `Enum` for closed categories**: Constrain finite taxonomies (`Literal["P0", "P1", "P2"]` or `str, Enum`) so downstream routers and database `ENUM` columns never encounter unexpected casing or synonyms.
2. **Compose nested `list[SubModel]` instead of `dict[str, Any]`**: Arbitrary open dictionaries lack fixed property names and cannot be grammar-constrained reliably; model structured records explicitly as `list[SubModel]`.
3. **Attach concise `Field(description=...)` metadata**: Descriptions are forwarded in the compiled JSON Schema, guiding Gemini on domain semantics (such as character budgets, ISO units, or urgency criteria) without bloating your main prompt.
4. **Tune `temperature` and `thinking_level` for deterministic speed**: For straightforward entity extraction and classification on `gemini-3.8-flash`, pairing `temperature=0.1` with `thinking_config=types.ThinkingConfig(thinking_level="low")` minimizes tail latency and output variance.

Putting all four rules together, you can combine a Python `Enum` with `list[RoutedIssue]` and `thinking_level="low"` to split a multi-issue customer ticket into typed routing records and iterate directly over `response.parsed`:

```python
from enum import Enum


class TicketQueue(str, Enum):
    BILLING = "billing"
    AUTH = "auth"
    ANALYTICS = "analytics"


class RoutedIssue(BaseModel):
    queue: TicketQueue = Field(description="Target support queue.")
    urgent: bool = Field(description="True if payment or login is blocked.")
    summary: str = Field(description="Actionable summary under 50 characters.")


class TriageBatch(BaseModel):
    issues: list[RoutedIssue] = Field(description="Distinct issues found in the message.")


triage_response = client.models.generate_content(
    model=MODEL,
    contents="Customer was billed twice on invoice #8821 and cannot export CSV reports.",
    config=types.GenerateContentConfig(
        response_mime_type="application/json",
        response_schema=TriageBatch,
        temperature=0.1,
        thinking_config=types.ThinkingConfig(thinking_level="low"),
    ),
)

batch: TriageBatch = triage_response.parsed
for item in batch.issues:
    flag = "URGENT" if item.urgent else "NORMAL"
    print(f"[{flag}] -> {item.queue.value}: {item.summary}")
```
