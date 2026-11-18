# 02. Field Constraints & Inspecting ValidationError

Type annotations like `int` and `str` guarantee basic shapes, but production payloads also carry domain invariants—positive quantities, bounded SKU formats, closed shipping tiers, isolated default lists, and camelCase JSON keys. Pydantic's `Field(...)`, `typing.Annotated`, and `typing.Literal` attach these rules declaratively onto each attribute, while Pydantic's Rust core (`pydantic-core`) evaluates **all** fields in a single pass—collecting every violation at once instead of halting on the first bad field.

```drawlib align=center code=fold file=ch02_field_constraints.png caption="Figure 2-1: Declarative Field Constraints and Single-Pass Multi-Error Collection"
from drawlib.canvas import save, setup
from drawlib.icons import phosphor
from drawlib.shapes import rectangle
from drawlib.smartarts import CardList
from drawlib.styles import Styles
from drawlib.text import text

setup(width=152, height=74, dpi=150)

# Outer boundary frame
rectangle((76, 37), width=142, height=64, style=Styles.MutedDashed.patch(shape_r=2.5))
text(
    (76, 64.2),
    "Declarative Field Constraints & Single-Pass Validation Engine",
    style=Styles.DarkBold.patch(text_size=12.0),
)

# Left Column: Numeric Bounds (F1) & Closed Choices (F3)
left_cards = CardList(
    style=Styles.Neutral.patch(shape_r=2.0),
    text_style=Styles.DarkBold.patch(text_size=10.8),
    description_style=Styles.Dark.patch(text_size=10.0),
    badge_shape="rounded_rect",
    badge_style=Styles.SecondaryNeutral,
    badge_text_style=Styles.PrimaryBold.patch(text_size=10.0),
    icon_style=Styles.PrimaryBold,
    direction="vertical",
    spacing=3.5,
)
left_cards.add(
    "1. Numeric Bounds",
    "gt, ge, lt, le, multiple_of\ne.g. Field(gt=0, le=1000)",
    badge_text="F1",
    icon=phosphor.sliders_horizontal,
    style=Styles.PrimaryNeutral.patch(shape_r=2.0),
)
left_cards.add(
    "3. Closed Choices (Literal)",
    "Literal['standard', 'express']\nRejects unknown category strings",
    badge_text="F3",
    icon=phosphor.tag,
)
left_cards.draw(xy=(9.0, 18.5), width=64.5, height=41.5, align="bottom_left")

# Right Column: String Rules (F2) & Safe Defaults / Aliases (F4)
right_cards = CardList(
    style=Styles.Neutral.patch(shape_r=2.0),
    text_style=Styles.DarkBold.patch(text_size=10.8),
    description_style=Styles.Dark.patch(text_size=10.0),
    badge_shape="rounded_rect",
    badge_style=Styles.SecondaryNeutral,
    badge_text_style=Styles.PrimaryBold.patch(text_size=10.0),
    icon_style=Styles.PrimaryBold,
    direction="vertical",
    spacing=3.5,
)
right_cards.add(
    "2. String Rules & Regex",
    "min_length, max_length, pattern\ne.g. Annotated SKU format rules",
    badge_text="F2",
    icon=phosphor.text_aa,
)
right_cards.add(
    "4. Safe Defaults & Aliases",
    "default_factory=list, alias='itemQty'\nIsolated mutables & JSON mapping",
    badge_text="F4",
    icon=phosphor.arrows_left_right,
    style=Styles.SecondaryNeutral.patch(shape_r=2.0),
)
right_cards.draw(xy=(78.5, 18.5), width=64.5, height=41.5, align="bottom_left")

# Bottom Focal Element (1 PrimaryFlat hero bar): Single-Pass Outcome
rectangle((76.0, 11.5), width=134.0, height=7.8, style=Styles.PrimaryFlat.patch(shape_r=2.0))
phosphor.shield_check((22.0, 11.5), width=4.6, style=Styles.WhiteBold)
text(
    (79.5, 11.5),
    "Single-Pass Validation: Checks ALL fields -> Validated Instance OR Multi-Field ValidationError",
    style=Styles.WhiteBold.patch(text_size=10.2),
)

save()
```

---

## 1. Declarative Constraints with `Field` & `Literal`

Use `Field(...)` to enforce numeric bounds (`gt`, `ge`, `lt`, `le`), string length caps (`min_length`, `max_length`), and regular expressions (`pattern`). When a constrained type is reused across models, wrap it in `Annotated[T, Field(...)]`; for finite sets of allowed values, use `Literal[...]`.

Notice `tags: list[str] = Field(default_factory=list)` below: in standard Python functions or classes, sharing a mutable default list risks leaking items across instances, whereas `default_factory=list` invokes `list()` freshly every time a new `OrderItem` is created:

```python
from typing import Annotated, Literal
from pydantic import BaseModel, ConfigDict, Field

SkuCode = Annotated[str, Field(pattern=r"^[A-Z]{3}-\d{4}$")]


class OrderItem(BaseModel):
    sku: SkuCode = "ORD-1024"
    name: str = Field(min_length=3, max_length=40)
    quantity: int = Field(gt=0, le=1000)
    unit_price: float = Field(ge=0.0)
    tier: Literal["standard", "express"] = "standard"
    tags: list[str] = Field(default_factory=list)


item = OrderItem(
    sku="PRO-4090",
    name="Mechanical Keyboard",
    quantity=2,
    unit_price=129.50,
    tier="express",
)
item.tags.append("fragile")

second_item = OrderItem(name="USB-C Cable", quantity=1, unit_price=12.00)
print("Validated item:", item.model_dump())
print("Second item tags (isolated list):", second_item.tags)
```

External REST and GraphQL APIs frequently exchange `camelCase` JSON keys (`itemQty`, `unitPrice`), whereas Python codebases follow `snake_case` (`item_qty`, `unit_price`). Pairing `Field(alias=...)` with `ConfigDict(populate_by_name=True)` lets your model accept **either** naming convention on input and export `camelCase` payloads on demand via `model_dump(by_alias=True)`:

```python
class ApiOrderItem(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    item_qty: int = Field(gt=0, le=1000, alias="itemQty")
    unit_price: float = Field(ge=0.0, alias="unitPrice")


# 1. Validate external camelCase JSON payload
from_json = ApiOrderItem.model_validate({"itemQty": 4, "unitPrice": 19.95})

# 2. Construct in Python using idiomatic snake_case names
from_python = ApiOrderItem(item_qty=2, unit_price=49.00)

print("Python snake_case dump:", from_json.model_dump())
print("External camelCase dump:", from_python.model_dump(by_alias=True))
```

---

## 2. Anatomy of `ValidationError` (`err.errors()`)

Unlike imperative `if ... raise ValueError(...)` checks that abort on the very first bad field, Pydantic validates every field in one pass and bundles all failures into a single `ValidationError`. Calling `err.errors()` returns a structured `list[dict]` where each entry pinpoints `loc`, `type`, `msg`, and `input`—making it ready to serialize directly into HTTP `422 Unprocessable Entity` responses:

```drawlib align=center code=fold file=ch02_validation_error_anatomy.png caption="Figure 2-2: Structure of ValidationError.errors() Entries for API Error Responses"
from drawlib.canvas import save, setup
from drawlib.icons import phosphor
from drawlib.lines import line
from drawlib.shapes import rectangle
from drawlib.smartarts import Panel, Table
from drawlib.styles import Colors, Styles
from drawlib.text import text

setup(width=152, height=74, dpi=150)

# Outer boundary frame
rectangle((76, 37), width=142, height=64, style=Styles.MutedDashed.patch(shape_r=2.5))
text(
    (76, 64.2),
    "Anatomy of ValidationError.errors() for HTTP 422 API Responses",
    style=Styles.DarkBold.patch(text_size=12.0),
)

# 1. Left Panel: Invalid Input Payload with 3 Simultaneous Violations
input_panel = Panel(
    "1. Invalid Input",
    style=Styles.Neutral.patch(shape_r=2.0),
    header_style=Styles.DangerNeutral.patch(shape_line_width=1.2),
    text_style=Styles.DarkBold.patch(text_size=10.5),
    icon=phosphor.warning_circle,
    icon_style=Styles.DangerBold,
    header_variant="filled",
    header_height=8.5,
)
input_panel.draw((9.0, 9.0), width=33.0, height=50.5, align="bottom_left")

bad_fields = [
    (43.5, 'name: ""', "violates min_length=3"),
    (30.0, "quantity: 0", "violates gt=0"),
    (16.5, 'tier: "overnight"', "not in Literal[...]"),
]
for cy, field_expr, reason in bad_fields:
    rectangle((25.5, cy), width=28.0, height=11.0, style=Styles.White.patch(shape_r=1.5))
    text((25.5, cy + 2.3), field_expr, style=Styles.DarkBold.patch(text_size=10.0))
    text((25.5, cy - 2.5), reason, style=Styles.Danger.patch(text_size=10.0))

# Connector 1 (6.5-unit gap)
line((42.0, 34.25), (48.5, 34.25), arrow_head="->", style=Styles.DarkBold)

# 2. Middle Focal Hero Card: Single-Pass ValidationError
rectangle((62.5, 34.25), width=28.0, height=50.5, style=Styles.PrimaryFlat.patch(shape_r=2.0))
phosphor.funnel((62.5, 49.5), width=6.2, style=Styles.WhiteBold)
text((62.5, 40.5), "2. ValidationError", style=Styles.WhiteBold.patch(text_size=10.6))
text(
    (62.5, 24.5),
    "Single-Pass Catch\n\nerror_count() == 3\n\nerr.errors()\n-> list[dict]",
    style=Styles.White.patch(text_size=10.0),
)

# Connector 2 (6.5-unit gap)
line((76.5, 34.25), (83.0, 34.25), arrow_head="->", style=Styles.DarkBold)

# 3. Right Panel + Table: Structured Dict Keys inside err.errors()
output_panel = Panel(
    "3. Each Dict in err.errors() (422 Body)",
    style=Styles.PrimaryNeutral.patch(shape_r=2.0),
    header_style=Styles.SecondaryNeutral.patch(shape_line_width=1.2),
    text_style=Styles.DarkBold.patch(text_size=10.5),
    icon=phosphor.brackets_curly,
    icon_style=Styles.PrimaryBold,
    header_variant="filled",
    header_height=8.5,
)
output_panel.draw((83.0, 9.0), width=60.0, height=50.5, align="bottom_left")

err_table = Table(
    cell_style=Styles.White,
    text_style=Styles.Dark.patch(text_size=10.0),
    header_cell_style=Styles.Dark,
    header_text_style=Styles.WhiteBold.patch(text_size=10.0),
    border_style=Styles.MutedThin,
)
err_table.set_style_cell_evenodd(
    even_color=Colors.Light,
    even_text_style=Styles.Dark.patch(text_size=10.0),
    odd_color=Colors.White,
    odd_text_style=Styles.Dark.patch(text_size=10.0),
)
err_table.set_style_cell_rowheader(
    background_color=Colors.SecondaryNeutral,
    text_style=Styles.PrimaryBold.patch(text_size=10.0),
)
err_table.set_style_cell_header(
    background_color=Colors.Dark,
    text_style=Styles.WhiteBold.patch(text_size=10.0),
)
err_table.set_style_border(
    top=Styles.Muted,
    top2=Styles.Muted,
    bottom=Styles.Muted,
    left=Styles.Muted,
    left2=Styles.Muted,
    right=Styles.Muted,
    between_rows=Styles.MutedThin,
)
err_table.draw_flexible(
    xy=(85.5, 48.5),
    column_widths=[12.5, 42.5],
    row_heights=[7.4, 7.4, 7.4, 7.4, 7.4],
    data=[
        ["Key", "Meaning & Example (quantity=0)"],
        ["loc", "Field path: ('quantity',)"],
        ["type", "Rule code: 'greater_than'"],
        ["msg", "Message: 'Input should be > 0'"],
        ["input", "Rejected value: 0"],
    ],
    align="top_left",
)

save()
```

Let's pass an intentionally invalid payload containing **three simultaneous violations** (`name=""`, `quantity=0`, and `tier="overnight"`), catch `ValidationError`, inspect `err.error_count()`, and extract `(loc, type, msg)` tuples ready for client-facing UI forms or API `422` error payloads:

```python
from pydantic import ValidationError

try:
    OrderItem(
        name="",
        quantity=0,
        unit_price=29.99,
        tier="overnight",
    )
except ValidationError as err:
    print(f"Collected {err.error_count()} field errors in a single pass:")
    for e in err.errors():
        print((e["loc"], e["type"], e["msg"]))

    api_422_body = {
        "status": 422,
        "errors": [
            {
                "field": ".".join(str(part) for part in e["loc"]),
                "code": e["type"],
                "message": e["msg"],
                "input": e["input"],
            }
            for e in err.errors()
        ],
    }
    print("\nAPI 422 response payload:", api_422_body)
```
