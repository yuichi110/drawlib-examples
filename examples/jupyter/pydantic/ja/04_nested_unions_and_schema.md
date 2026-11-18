# 04. ネスト構造・判別共用体（Discriminated Union）・JSON Schema

実務の REST API、Webhook イベントストリーム、および LLM のツール呼び出し／構造化出力では、単一のフラットなモデルだけで完結することは稀です。本番システムでは **ネストされた `BaseModel` 階層** を組み立て、**タグ付き判別共用体（`Field(discriminator=...)` + `TypeAdapter`）** によって多態的なペイロードを `O(1)` で高速振り分けし、さらに **`model_json_schema()`** から出力される標準 JSON Schema を FastAPI の OpenAPI 3.1 ドキュメント生成や LLM の文法制約付きデコーディング（Google GenAI SDK の `response_schema` など）で一元活用します。

```drawlib align=center code=fold file=ch04_discriminated_union_ja.png caption="図4-1: タグ付き判別共用体（Discriminated Union）と TypeAdapter による高速振り分け"
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
    'O(1) タグ付き共用体ルーティング: TypeAdapter + Field(discriminator="kind")',
    style=Styles.DarkBold.patch(text_size=11.5),
)

# Column 1: Incoming JSON Event List (Neutral)
rectangle((26.5, 37.5), width=33.0, height=39.0, style=Styles.Neutral.patch(shape_r=2.0))
phosphor.brackets_curly((26.5, 49.0), width=5.8, style=Styles.PrimaryBold)
text((26.5, 41.2), "受信 JSON リスト", style=Styles.DarkBold.patch(text_size=10.8))
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
text((68.5, 41.2), "O(1) 判別ルーター", style=Styles.WhiteBold.patch(text_size=10.8))
text(
    (68.5, 29.8),
    'discriminator="kind"\nTypeAdapter(list[...])\nタグ値で即座に分岐',
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
    "O(1) ハッシュ検索で一致モデルへ直行しピンポイントなエラーを返す — 全分岐の総当たり検証を回避",
    style=Styles.Muted.patch(text_size=10.0),
)

save()
```

---

## 1. ネスト構造と判別共用体（`Field(discriminator=...)` + `TypeAdapter`）

通常のタグなし共用体（`CardPayment | BankTransfer | WalletPayment`）では、バリデータが左から順番にすべての候補モデルを総当たりで試行するため、不一致時の CPU コストが増大するだけでなく、入力不備の際に全候補分の冗長な `ValidationError` が発生してしまいます。各サブモデルに `Literal[...]` 型のタグフィールド（`kind` など）を持たせ、`Annotated[..., Field(discriminator="kind")]` で束ねると、`pydantic-core` 内部での分岐が **`O(1)` のハッシュテーブル検索** へと最適化されます。

- **ネストされた `BaseModel` 合成**: `CheckoutOrder` の属性として `PaymentMethod` を埋め込むだけで、ネストされた辞書が1回の検証パスで適切な具象クラス（`CardPayment` / `BankTransfer` / `WalletPayment`）へと変換されます。
- **`TypeAdapter` によるコレクションの直接検証**: Webhook のイベント配列など、外側のラッパー `BaseModel` を持たない `list[PaymentMethod]` を直接検証したい場合は、モジュール読み込み時に `TypeAdapter(list[PaymentMethod])` を1回コンパイルして再利用します。
- **ピンポイントなエラー特定**: `{"kind": "card", "last4": "12AB"}` のように正規表現制約に違反した場合でも、`CardPayment` へ直行するため、`bank_code` や `provider` の欠落ノイズを含まない `'card' -> 'last4'` だけの正確なエラーが得られます。

```python
from typing import Annotated, Literal

from pydantic import BaseModel, Field, TypeAdapter, ValidationError


class CardPayment(BaseModel):
    kind: Literal["card"] = "card"
    last4: str = Field(pattern=r"^\d{4}$", description="マスク済みのカード番号下4桁。")
    amount: int = Field(gt=0, description="決済金額（セント単位）。")


class BankTransfer(BaseModel):
    kind: Literal["bank"] = "bank"
    bank_code: str = Field(min_length=4, max_length=11, description="SWIFTコードまたは銀行識別コード。")
    amount: int = Field(gt=0, description="振込金額（セント単位）。")


class WalletPayment(BaseModel):
    kind: Literal["wallet"] = "wallet"
    provider: Literal["apple_pay", "google_pay"] = Field(description="デジタルウォレット種別。")
    amount: int = Field(gt=0, description="決済金額（セント単位）。")


# 'kind' リテラル値で O(1) ルーティングを行う判別共用体（Discriminated Union）
PaymentMethod = Annotated[
    CardPayment | BankTransfer | WalletPayment,
    Field(discriminator="kind"),
]


class CheckoutOrder(BaseModel):
    order_id: str = Field(description="一意の注文ID。")
    customer_email: str = Field(description="購入者の確認用メールアドレス。")
    payment: PaymentMethod = Field(description="決済手段ごとの多態ペイロード。")


# 1. ネストされた CheckoutOrder ペイロードの検証
order = CheckoutOrder.model_validate(
    {
        "order_id": "ORD-2026-0042",
        "customer_email": "alice@example.com",
        "payment": {"kind": "card", "last4": "4242", "amount": 4800},
    }
)
print(f"Nested order {order.order_id} -> {type(order.payment).__name__}: {order.payment}")

# 2. TypeAdapter を用いた list[PaymentMethod] バッチ配列の直接検証
payment_batch_adapter = TypeAdapter(list[PaymentMethod])
payments = payment_batch_adapter.validate_python(
    [
        {"kind": "card", "last4": "4242", "amount": 4800},
        {"kind": "bank", "bank_code": "BOFAUS3N", "amount": 12500},
        {"kind": "wallet", "provider": "google_pay", "amount": 1900},
    ]
)
print("Batch routed types:", [type(item).__name__ for item in payments])

# 3. 特定バリアントのフィールド不正時におけるピンポイントな O(1) エラー報告
try:
    payment_batch_adapter.validate_python(
        [{"kind": "card", "last4": "12AB", "amount": 4800}]
    )
except ValidationError as exc:
    err = exc.errors(include_url=False)[0]
    print(f"Pinpoint error ({exc.error_count()} total): loc={err['loc']} -> {err['msg']}")
```

---

## 2. API・LLM 連携のための標準 JSON Schema 生成（`model_json_schema()`）

実行時の高速バリデーションに加えて、Pydantic v2 のすべての `BaseModel`（および `TypeAdapter`）は `.model_json_schema()` メソッドによって **JSON Schema Draft 2020-12** 準拠の辞書を直接出力できます。型制約・`Literal` 分類・`Field(discriminator=...)` マッピング・`Field(description=...)` の説明文を Python コード上で1回定義するだけで、システム全体の **Single Source of Truth（唯一の情報源）** として機能します。

```drawlib align=center code=fold file=ch04_json_schema_ecosystem_ja.png caption="図4-2: 単一の Pydantic モデルから FastAPI (OpenAPI) と LLM 構造化出力へのスキーマ展開"
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
    "Single Source of Truth: CheckoutOrder.model_json_schema() の展開",
    style=Styles.DarkBold.patch(text_size=11.5),
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
    "リクエスト/レスポンス検証と\nSwagger UI ドキュメント自動生成",
    icon=phosphor.globe,
    style=Styles.Neutral.patch(shape_r=2.0),
)
targets.add(
    "2. LLM 構造化出力",
    "google-genai response_schema\n文法制約付き JSON デコード",
    icon=ai.gemini,
    style=Styles.PrimaryNeutral.patch(shape_r=2.0),
    badge_style=Styles.White.patch(shape_line_color=Colors.Primary, shape_line_width=1.0),
)
targets.add(
    "3. フロントエンド・設定連携",
    "TypeScript 型定義の自動生成と\nIDE JSON/YAML 入力補完",
    icon=phosphor.browsers,
    style=Styles.SecondaryNeutral.patch(shape_r=2.0),
    badge_style=Styles.White.patch(shape_line_color=Colors.Secondary, shape_line_width=1.0),
    icon_style=Styles.SecondaryBold,
)
targets.draw(xy=(10.5, 9.0), width=131.0, height=23.5, align="bottom_left")

save()
```

`CheckoutOrder.model_json_schema()` を呼び出すと、再利用可能なサブモデル定義（`$defs`）、判別キーと参照先の対応表（`discriminator`）、必須属性リスト（`required`）、正規表現や数値範囲の制約、そして各フィールドの `description` メタデータが一括出力されます（日本語の `description` を出力するため `ensure_ascii=False` を指定しています）。次のショーケースである **Google GenAI SDK Cookbook** で `response_schema=CheckoutOrder` を渡した際も、内部ではまさにこの JSON Schema 生成機構が呼び出され、Gemini のトークン生成が有効な `CheckoutOrder` 形式へと厳密に制約されます。

```python
import json

schema = CheckoutOrder.model_json_schema()

print("Top-level schema keys:", list(schema.keys()))
print("Nested $defs models:", list(schema["$defs"].keys()))
print("\nFull JSON Schema (Draft 2020-12):")
print(json.dumps(schema, indent=2, ensure_ascii=False))
```
