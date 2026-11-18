# 02. Field 制約と ValidationError の構造理解

`int` や `str` といった型ヒントだけでも基本的な型安全性は確保できますが、実務のデータモデルには「数量は正の整数」「SKU コードの正規表現」「限定された配送区分」「インスタンス間で共有されない初期リスト」「camelCase の JSON キー変換」といったドメイン固有の制約が不可欠です。Pydantic では `Field(...)`・`typing.Annotated`・`typing.Literal` を用いてこれらのルールを宣言的に付与でき、Rust 製コア（`pydantic-core`）が**全フィールドを1パスで一括検証**するため、最初のエラーで途中終了せずにすべての違反箇所を一度に収集できます。

```drawlib align=center code=fold file=ch02_field_constraints_ja.png caption="図2-1: 宣言的な Field 制約カテゴリと一括エラー収集（ValidationError）の仕組み"
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
    "宣言的な Field 制約カテゴリと一括バリデーションエンジン",
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
    "1. 数値の範囲制約",
    "gt, ge, lt, le, multiple_of\n例: Field(gt=0, le=1000)",
    badge_text="F1",
    icon=phosphor.sliders_horizontal,
    style=Styles.PrimaryNeutral.patch(shape_r=2.0),
)
left_cards.add(
    "3. 閉じた選択肢 (Literal)",
    "Literal['standard', 'express']\n定義外のカテゴリ文字列を拒否",
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
    "2. 文字列長・正規表現ルール",
    "min_length, max_length, pattern\n例: Annotated による SKU 形式検証",
    badge_text="F2",
    icon=phosphor.text_aa,
)
right_cards.add(
    "4. 安全な初期値と Alias",
    "default_factory=list, alias='itemQty'\nリスト共有防止と camelCase 変換",
    badge_text="F4",
    icon=phosphor.arrows_left_right,
    style=Styles.SecondaryNeutral.patch(shape_r=2.0),
)
right_cards.draw(xy=(78.5, 18.5), width=64.5, height=41.5, align="bottom_left")

# Bottom Focal Element (1 PrimaryFlat hero bar): Single-Pass Outcome
rectangle((76.0, 11.5), width=134.0, height=7.8, style=Styles.PrimaryFlat.patch(shape_r=2.0))
phosphor.shield_check((23.0, 11.5), width=4.6, style=Styles.WhiteBold)
text(
    (79.5, 11.5),
    "一括バリデーション: 全フィールドを1パスで検証 → 検証済みインスタンス または ValidationError",
    style=Styles.WhiteBold.patch(text_size=10.2),
)

save()
```

---

## 1. `Field` と `Literal` による宣言的なフィールド制約

数値の上下限（`gt`, `ge`, `lt`, `le`）、文字列長（`min_length`, `max_length`）、正規表現（`pattern`）は `Field(...)` でフィールドに直接宣言します。複数モデルで共通利用する制約付き型には `Annotated[T, Field(...)]`、取り得る選択肢が決まっている属性には `Literal[...]` を組み合わせるのが定石です。

また、以下の `tags: list[str] = Field(default_factory=list)` に注目してください。ミュータブルな空リストの共有バグを防ぐため、`default_factory=list` を指定することで `OrderItem` の生成ごとに独立した新しい `list` インスタンスが作られます。

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

外部の REST / GraphQL API では `camelCase`（`itemQty`, `unitPrice`）の JSON キーが使われる一方、Python コード内では `snake_case`（`item_qty`, `unit_price`）で統一したい場面が頻繁にあります。`Field(alias=...)` と `ConfigDict(populate_by_name=True)` を併用すれば、入力時は**両方のキー名**を受け付けつつ、出力時は `model_dump(by_alias=True)` で外部向けの `camelCase` 辞書へ自在に変換できます。

```python
class ApiOrderItem(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    item_qty: int = Field(gt=0, le=1000, alias="itemQty")
    unit_price: float = Field(ge=0.0, alias="unitPrice")


# 1. 外部 API からの camelCase JSON ペイロードを検証
from_json = ApiOrderItem.model_validate({"itemQty": 4, "unitPrice": 19.95})

# 2. Python コード内では snake_case の属性名で直接初期化
from_python = ApiOrderItem(item_qty=2, unit_price=49.00)

print("Python snake_case dump:", from_json.model_dump())
print("External camelCase dump:", from_python.model_dump(by_alias=True))
```

---

## 2. `ValidationError` の内部構造（`err.errors()`）

手続き型の `if ... raise ValueError(...)` チェックでは最初の不正フィールドで処理が中断されますが、Pydantic は全フィールドを最後まで走査し、すべての違反を1つの `ValidationError` に集約します。`err.errors()` を呼び出すと、各違反の `loc`（発生箇所タプル）・`type`（機械可読エラーコード）・`msg`（人間向け説明文）・`input`（拒否された入力値）を格納した `list[dict]` が得られ、HTTP `422 Unprocessable Entity` のエラーレスポンスにそのまま活用できます。

```drawlib align=center code=fold file=ch02_validation_error_anatomy_ja.png caption="図2-2: API エラーレスポンスにそのまま使える ValidationError.errors() の構造"
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
    "HTTP 422 エラー応答に直結する ValidationError.errors() の構造",
    style=Styles.DarkBold.patch(text_size=12.0),
)

# 1. Left Panel: Invalid Input Payload with 3 Simultaneous Violations
input_panel = Panel(
    "1. 不正な入力データ",
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
    (43.5, 'name: ""', "min_length=3 違反"),
    (30.0, "quantity: 0", "gt=0 違反"),
    (16.5, 'tier: "overnight"', "Literal 候補外"),
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
    "全違反を一括集約\n\nerror_count() == 3\n\nerr.errors()\n-> list[dict]",
    style=Styles.White.patch(text_size=10.0),
)

# Connector 2 (6.5-unit gap)
line((76.5, 34.25), (83.0, 34.25), arrow_head="->", style=Styles.DarkBold)

# 3. Right Panel + Table: Structured Dict Keys inside err.errors()
output_panel = Panel(
    "3. err.errors() 各要素の辞書構造",
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
        ["キー", "役割と出力例（quantity=0 の場合）"],
        ["loc", "発生位置: ('quantity',)"],
        ["type", "種別コード: 'greater_than'"],
        ["msg", "説明文: 'Input should be > 0'"],
        ["input", "拒否された入力値: 0"],
    ],
    align="top_left",
)

save()
```

実際に3つの制約違反（`name=""`, `quantity=0`, `tier="overnight"`）を同時に含む不正データを `OrderItem` に渡し、`ValidationError` を捕捉して `err.error_count()` と `err.errors()` の各フィールド（`loc`, `type`, `msg`）を整形出力してみましょう。

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
