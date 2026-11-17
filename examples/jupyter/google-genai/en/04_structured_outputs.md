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
    "Raw Incident Log\n+\nIncidentReport\n(BaseModel)",
    style=Styles.Dark.patch(text_size=10.0),
)

# Stage 2: Grammar-Constrained Decoding (Focal Hero: PrimaryFlat)
rectangle((stage_xs[1], card_cy), width=card_w, height=card_h, style=Styles.PrimaryFlat.patch(shape_r=2.0))
phosphor.sparkle((stage_xs[1], 46.8), width=6.0, style=Styles.WhiteBold)
text((stage_xs[1], 39.0), "2. Grammar Decode", style=Styles.WhiteBold.patch(text_size=10.8))
text(
    (stage_xs[1], 25.0),
    "application/json\n+\nresponse_schema\n(Gemini 2.5)",
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

# Stage 4: Downstream Persistence & Drawlib Table (SecondaryNeutral)
rectangle((stage_xs[3], card_cy), width=card_w, height=card_h, style=Styles.SecondaryNeutral.patch(shape_r=2.0))
phosphor.table((stage_xs[3], 46.8), width=6.0, style=Styles.SecondaryBold)
text((stage_xs[3], 39.0), "4. DB & Table UI", style=Styles.DarkBold.patch(text_size=10.8))
text(
    (stage_xs[3], 25.0),
    "Typed Persistence\nAlert Routing &\nDrawlib Table",
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

## 1. 3-Line Client Setup & Defining a Nested Pydantic Schema

First, initialize the `google-genai` client using your `GEMINI_API_KEY` stored in Google Colab Secrets (`🔑` panel on the left sidebar):

```python
from google.colab import userdata
from google import genai

client = genai.Client(api_key=userdata.get("GEMINI_API_KEY"))
```

Next, compose a nested Pydantic schema (`ActionItem` inside `IncidentSummary`) to extract structured postmortem metadata from an unstructured operational incident log. Passing `IncidentSummary` to `response_schema` instructs the SDK to compile the Pydantic model into a strict schema and populate `response.parsed` automatically:

```python
from typing import Literal

from google.genai import types
from pydantic import BaseModel, Field


class ActionItem(BaseModel):
    owner: str = Field(description="Team or engineer responsible for the follow-up task.")
    task: str = Field(description="Concrete, actionable engineering remediation step.")
    priority: Literal["P0", "P1", "P2"] = Field(description="Urgency tier from P0 (immediate) to P2.")


class IncidentSummary(BaseModel):
    title: str = Field(description="Concise incident headline under 60 characters.")
    severity: Literal["LOW", "MEDIUM", "HIGH", "CRITICAL"] = Field(
        description="Overall customer-impact severity level."
    )
    root_cause: str = Field(description="Single-sentence technical root cause explanation.")
    affected_services: list[str] = Field(description="Microservice names impacted during the outage.")
    action_items: list[ActionItem] = Field(description="Prioritized follow-up engineering action items.")


raw_incident_log = """
[2026-04-12 14:03 UTC] PagerDuty Alert: 5xx error rate on checkout-api spiked to 38%.
[14:09 UTC] On-call SRE noticed PostgreSQL connection pool at 100% saturation.
[14:16 UTC] Root cause identified: a slow upstream payment-webhook timeout triggered an
unbounded client retry storm from payment-worker into checkout-api.
[14:24 UTC] Mitigated by enabling circuit-breaker shedding and restarting stalled workers.
Follow-ups agreed in retro:
1. SRE Team to cap exponential backoff and enforce circuit-breaker budgets immediately (P0).
2. Payments Team to add PgBouncer pool saturation alerts at 80% utilization (P1).
3. Platform Team to replay webhook timeout scenarios in staging load tests next sprint (P2).
"""

response = client.models.generate_content(
    model="gemini-2.5-flash",
    contents=raw_incident_log,
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

## 2. Schema Design Best Practices & Rendering Extracted Data with Drawlib

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
    "Constrain severity & priority labels\ninstead of free-form str fields.",
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
    "4. Low Temperature + thinking_budget=0",
    "Pair temperature=0.0-0.2 with zero\nthinking budget for fast extraction.",
    badge_text="R4",
    icon=phosphor.lightning,
    style=Styles.SecondaryNeutral.patch(shape_r=2.0),
)
right_cards.draw(xy=(78.5, 9.0), width=64.5, height=49.0, align="bottom_left")

save()
```

Keep these four engineering rules in mind when authoring schemas for `response_schema`:

1. **Use `Literal` or `Enum` for closed categories**: Constrain finite taxonomies (`Literal["P0", "P1", "P2"]`) so downstream routers and database `ENUM` columns never encounter unexpected casing or synonyms.
2. **Compose nested `list[SubModel]` instead of `dict[str, Any]`**: Arbitrary open dictionaries lack fixed property names and cannot be grammar-constrained reliably; model key-value pairs explicitly as `list[SubModel]`.
3. **Attach concise `Field(description=...)` metadata**: Descriptions are forwarded in the compiled JSON Schema, guiding Gemini on domain semantics (such as character budgets, ISO units, or severity thresholds) without bloating your main prompt.
4. **Tune `temperature` and `thinking_budget` for deterministic speed**: For straightforward entity extraction on `gemini-2.5-flash`, pairing `temperature=0.1` with `thinking_config=types.ThinkingConfig(thinking_budget=0)` minimizes tail latency and output variance.

Because `summary.action_items` is already a strongly typed `list[ActionItem]`, you can feed it straight into a **Drawlib `Table`** (`setup(..., cwd=True)` + `Table` + `show()`) to render an executive incident summary right inside your notebook cell:

```python
from drawlib.canvas import setup, show
from drawlib.smartarts import Table
from drawlib.styles import Colors, Styles
from drawlib.text import text

setup(width=120, height=52, cwd=True)

text(
    (60, 46.5),
    f"[{summary.severity}] {summary.title}",
    style=Styles.DarkBold.patch(text_size=11.5),
)

items = summary.action_items[:4]
rows = [["Priority", "Owner", "Remediation Task"]] + [
    [item.priority, item.owner, item.task] for item in items
]

table = Table(
    cell_style=Styles.White,
    text_style=Styles.Dark.patch(text_size=10.0),
    header_cell_style=Styles.PrimaryFlat,
    header_text_style=Styles.WhiteBold.patch(text_size=10.5),
    border_style=Styles.MutedThin,
)
table.set_style_cell_evenodd(
    even_color=Colors.Light,
    even_text_style=Styles.Dark.patch(text_size=10.0),
    odd_color=Colors.White,
    odd_text_style=Styles.Dark.patch(text_size=10.0),
)
table.set_style_cell_header(
    background_color=Colors.Primary,
    text_style=Styles.WhiteBold.patch(text_size=10.5),
)

row_heights = [9.0] + [27.0 / max(len(items), 1)] * len(items)
table.draw_flexible(
    xy=(6, 41),
    column_widths=[18, 26, 64],
    row_heights=row_heights,
    data=rows,
    align="top_left",
)

show()
```
