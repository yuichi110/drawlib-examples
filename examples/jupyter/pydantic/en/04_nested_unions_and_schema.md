# 04. Nested Models, Discriminated Unions & JSON Schema

Real-world REST APIs, webhook event streams, and LLM tool/structured-output contracts rarely validate flat records in isolation. Instead, production systems compose **nested `BaseModel` hierarchies**, route polymorphic payloads in `O(1)` time via **tagged Discriminated Unions (`Field(discriminator=...)` + `TypeAdapter`)**, and export a single canonical **JSON Schema (`model_json_schema()`)** that simultaneously powers FastAPI's OpenAPI 3.1 documentation and grammar-constrained LLM decoding (such as Google GenAI SDK's `response_schema`).

```drawlib align=center code=fold file=ch04_discriminated_union.png caption="Figure 4-1: O(1) Routing with Tagged Discriminated Unions and TypeAdapter"
from drawlib.canvas import save, setup
from drawlib.icons import phosphor
from drawlib.lines import line
from drawlib.shapes import rectangle
from drawlib.smartarts import CardList
from drawlib.styles import Colors, Styles
from drawlib.text import text

setup(width=152, height=76, dpi=150)

# Outer diagram boundary (5.0-unit canvas margins)
rectangle((76, 38), width=142, height=66, style=Styles.MutedDashed.patch(shape_r=2.5))
text(
    (76, 65.5),
    'O(1) Tagged Union Routing: TypeAdapter + Field(discriminator="kind")',
    style=Styles.DarkBold.patch(text_size=11.8),
)

# Column 1: Incoming JSON Event List (Neutral)
rectangle((26.5, 37.5), width=33.0, height=39.0, style=Styles.Neutral.patch(shape_r=2.0))
phosphor.brackets_curly((26.5, 49.0), width=5.8, style=Styles.PrimaryBold)
text((26.5, 41.2), "JSON Event List", style=Styles.DarkBold.patch(text_size=10.8))
text(
    (26.5, 29.8),
    '{"kind": "card", ...}\n{"kind": "bank", ...}\n{"kind": "wallet", ...}',
    style=Styles.Dark.patch(text_size=10.0),
)

# Arrow 1 -> Focal Discriminator Hub (8.0-unit gap)
line((43.0, 37.5), (51.0, 37.5), arrow_head="->", style=Styles.PrimaryBold)

# Column 2: Discriminator Router Hub (Focal Hero: PrimaryFlat)
rectangle((68.5, 37.5), width=35.0, height=39.0, style=Styles.PrimaryFlat.patch(shape_r=2.0))
phosphor.arrows_split((68.5, 49.0), width=5.8, style=Styles.WhiteBold)
text((68.5, 41.2), "O(1) Tag Router", style=Styles.WhiteBold.patch(text_size=10.8))
text(
    (68.5, 29.8),
    'discriminator="kind"\nTypeAdapter(list[...])\nDirect Hash Lookup',
    style=Styles.White.patch(text_size=10.0),
)

# Orthogonal 1-to-3 Fan-Out Bus (6.5-unit trunk + 7.5-unit branches)
line((86.0, 37.5), (92.5, 37.5), style=Styles.PrimaryBold)
line((92.5, 21.0), (92.5, 54.0), style=Styles.PrimaryBold)
for target_y in (54.0, 37.5, 21.0):
    line((92.5, target_y), (100.0, target_y), arrow_head="->", style=Styles.PrimaryBold)

# Column 3: 3 Polymorphic Payment Variant Models (Neutral Baseline)
variants = CardList(
    style=Styles.Neutral.patch(shape_r=2.0),
    text_style=Styles.DarkBold.patch(text_size=10.5),
    description_style=Styles.Dark.patch(text_size=10.0),
    badge_shape="rounded_rect",
    badge_style=Styles.White.patch(shape_line_color=Colors.Muted, shape_line_width=1.0),
    icon_style=Styles.PrimaryBold,
    direction="vertical",
    spacing=3.5,
)
variants.add(
    "CardPayment",
    'kind="card" | last4',
    icon=phosphor.credit_card,
    style=Styles.PrimaryNeutral.patch(shape_r=2.0),
    badge_style=Styles.White.patch(shape_line_color=Colors.Primary, shape_line_width=1.0),
)
variants.add(
    "BankTransfer",
    'kind="bank" | bank_code',
    icon=phosphor.bank,
    style=Styles.Neutral.patch(shape_r=2.0),
)
variants.add(
    "WalletPayment",
    'kind="wallet" | provider',
    icon=phosphor.wallet,
    style=Styles.SecondaryNeutral.patch(shape_r=2.0),
    badge_style=Styles.White.patch(shape_line_color=Colors.Secondary, shape_line_width=1.0),
    icon_style=Styles.SecondaryBold,
)
variants.draw(xy=(100.0, 14.5), width=42.5, height=46.0, align="bottom_left")

text(
    (76, 9.0),
    "Jumps straight to the matching model in O(1) with pinpoint errors — no sequential Union trial-and-error",
    style=Styles.Muted.patch(text_size=10.0),
)

save()
```

---

## 1. Nested Models & Discriminated Unions (`Field(discriminator=...)` + `TypeAdapter`)

With an untagged Python union (`CardPayment | BankTransfer | WalletPayment`), a validator must try each branch sequentially from left to right—wasting CPU cycles on misses and emitting noisy multi-branch `ValidationError` reports whenever an input fails. Attaching a `Literal[...]` tag field (such as `kind`) to every variant and combining them via `Annotated[..., Field(discriminator="kind")]` turns union dispatch into an **`O(1)` hash-table lookup** inside `pydantic-core`:

- **Nested `BaseModel` Composition**: Embed `PaymentMethod` directly inside `CheckoutOrder` so nested dictionaries are validated and instantiated into concrete subclass instances (`CardPayment`, `BankTransfer`, or `WalletPayment`) in a single pass.
- **Standalone Collection Validation (`TypeAdapter`)**: When validating bare lists (`list[PaymentMethod]`) or webhook arrays without wrapping them in an outer `BaseModel`, compile a reusable `TypeAdapter(list[PaymentMethod])` once at module import time.
- **Pinpoint Error Diagnostics**: If `{"kind": "card", "last4": "12AB"}` fails regex validation, Pydantic jumps straight to `CardPayment` and reports **only** the exact `'card' -> 'last4'` error rather than complaining about missing `bank_code` or `provider` fields.

```python
from typing import Annotated, Literal

from pydantic import BaseModel, Field, TypeAdapter, ValidationError


class CardPayment(BaseModel):
    kind: Literal["card"] = "card"
    last4: str = Field(pattern=r"^\d{4}$", description="Masked last 4 digits of the card.")
    amount: int = Field(gt=0, description="Payment amount in cents.")


class BankTransfer(BaseModel):
    kind: Literal["bank"] = "bank"
    bank_code: str = Field(min_length=4, max_length=11, description="SWIFT or bank routing code.")
    amount: int = Field(gt=0, description="Transfer amount in cents.")


class WalletPayment(BaseModel):
    kind: Literal["wallet"] = "wallet"
    provider: Literal["apple_pay", "google_pay"] = Field(description="Digital wallet provider.")
    amount: int = Field(gt=0, description="Payment amount in cents.")


# O(1) Tagged Discriminated Union routed by the 'kind' literal field
PaymentMethod = Annotated[
    CardPayment | BankTransfer | WalletPayment,
    Field(discriminator="kind"),
]


class CheckoutOrder(BaseModel):
    order_id: str = Field(description="Unique order identifier.")
    customer_email: str = Field(description="Buyer confirmation email address.")
    payment: PaymentMethod = Field(description="Polymorphic payment method payload.")


# 1. Validate a nested CheckoutOrder payload
order = CheckoutOrder.model_validate(
    {
        "order_id": "ORD-2026-0042",
        "customer_email": "alice@example.com",
        "payment": {"kind": "card", "last4": "4242", "amount": 4800},
    }
)
print(f"Nested order {order.order_id} -> {type(order.payment).__name__}: {order.payment}")

# 2. Validate a bare batch list[PaymentMethod] directly via TypeAdapter
payment_batch_adapter = TypeAdapter(list[PaymentMethod])
payments = payment_batch_adapter.validate_python(
    [
        {"kind": "card", "last4": "4242", "amount": 4800},
        {"kind": "bank", "bank_code": "BOFAUS3N", "amount": 12500},
        {"kind": "wallet", "provider": "google_pay", "amount": 1900},
    ]
)
print("Batch routed types:", [type(item).__name__ for item in payments])

# 3. Pinpoint O(1) error reporting when a specific variant field is invalid
try:
    payment_batch_adapter.validate_python(
        [{"kind": "card", "last4": "12AB", "amount": 4800}]
    )
except ValidationError as exc:
    err = exc.errors(include_url=False)[0]
    print(f"Pinpoint error ({exc.error_count()} total): loc={err['loc']} -> {err['msg']}")
```

---

## 2. Generating Standard JSON Schema (`model_json_schema()`) for APIs & LLMs

Beyond runtime validation, every Pydantic v2 `BaseModel` (and `TypeAdapter`) compiles directly into **JSON Schema Draft 2020-12** via `.model_json_schema()`. Defining constraints, `Literal` taxonomies, `Field(discriminator=...)` mappings, and `Field(description=...)` hints once in Python establishes a **Single Source of Truth** across your entire engineering stack:

```drawlib align=center code=fold file=ch04_json_schema_ecosystem.png caption="Figure 4-2: One Pydantic Model Powering FastAPI OpenAPI Docs and LLM Structured Outputs"
from drawlib.canvas import save, setup
from drawlib.icons import ai, phosphor
from drawlib.lines import line
from drawlib.shapes import rectangle
from drawlib.smartarts import CardList
from drawlib.styles import Colors, Styles
from drawlib.text import text

setup(width=152, height=78, dpi=150)

# Outer diagram boundary (5.0-unit canvas margins)
rectangle((76, 39), width=142, height=68, style=Styles.MutedDashed.patch(shape_r=2.5))
text(
    (76, 67.5),
    "Single Source of Truth: CheckoutOrder.model_json_schema() Ecosystem",
    style=Styles.DarkBold.patch(text_size=11.8),
)

# Top Focal Hub: Canonical JSON Schema Compiler (PrimaryFlat)
rectangle((76.0, 53.5), width=98.0, height=16.0, style=Styles.PrimaryFlat.patch(shape_r=2.0))
phosphor.file_code((34.5, 53.5), width=6.0, style=Styles.WhiteBold)
text(
    (80.0, 56.5),
    "CheckoutOrder.model_json_schema()",
    style=Styles.WhiteBold.patch(text_size=11.0),
)
text(
    (80.0, 50.2),
    "JSON Schema 2020-12  |  $defs  |  discriminator  |  required  |  description",
    style=Styles.White.patch(text_size=10.0),
)

# Symmetrical 1-to-3 Orthogonal Bus (6.5-unit trunk + 6.5-unit downward branches)
line((76.0, 45.5), (76.0, 39.0), style=Styles.PrimaryBold)
line((31.0, 39.0), (121.0, 39.0), style=Styles.PrimaryBold)
for target_x in (31.0, 76.0, 121.0):
    line((target_x, 39.0), (target_x, 32.5), arrow_head="->", style=Styles.PrimaryBold)

# Bottom Tier: 3 Downstream Ecosystem Consumers (Neutral Baseline)
targets = CardList(
    style=Styles.Neutral.patch(shape_r=2.0),
    text_style=Styles.DarkBold.patch(text_size=10.5),
    description_style=Styles.Dark.patch(text_size=10.0),
    badge_shape="rounded_rect",
    badge_style=Styles.White.patch(shape_line_color=Colors.Muted, shape_line_width=1.0),
    icon_style=Styles.PrimaryBold,
    direction="horizontal",
    spacing=4.0,
)
targets.add(
    "1. FastAPI & OpenAPI 3.1",
    "Request/Response Validation\n& Interactive Swagger Docs",
    icon=phosphor.globe,
    style=Styles.Neutral.patch(shape_r=2.0),
)
targets.add(
    "2. LLM Structured Outputs",
    "google-genai response_schema\nGrammar-Constrained JSON",
    icon=ai.gemini,
    style=Styles.PrimaryNeutral.patch(shape_r=2.0),
    badge_style=Styles.White.patch(shape_line_color=Colors.Primary, shape_line_width=1.0),
)
targets.add(
    "3. Frontend & Config Types",
    "TypeScript SDK Codegen &\nIDE JSON/YAML Autocomplete",
    icon=phosphor.browsers,
    style=Styles.SecondaryNeutral.patch(shape_r=2.0),
    badge_style=Styles.White.patch(shape_line_color=Colors.Secondary, shape_line_width=1.0),
    icon_style=Styles.SecondaryBold,
)
targets.draw(xy=(10.5, 9.0), width=131.0, height=23.5, align="bottom_left")

save()
```

Calling `CheckoutOrder.model_json_schema()` emits reusable sub-model definitions under `$defs`, an explicit `discriminator` mapping (`"card"` -> `"#/$defs/CardPayment"`), `required` property arrays, regex `pattern` / numeric bounds, and `description` strings. Notice how cleanly this single dictionary bridges backend APIs and AI engineering—in fact, passing `response_schema=CheckoutOrder` in the **Google GenAI SDK Cookbook** uses this exact schema introspection under the hood to constrain Gemini's token decoding to valid `CheckoutOrder` JSON:

```python
import json

schema = CheckoutOrder.model_json_schema()

print("Top-level schema keys:", list(schema.keys()))
print("Nested $defs models:", list(schema["$defs"].keys()))
print("\nFull JSON Schema (Draft 2020-12):")
print(json.dumps(schema, indent=2))
```
