# 03. ルーティングとパラメータ解析

FastAPI の最大の魅力の 1 つは、Python の標準的な型アノテーション（Type Hints）を書くだけで、**URL からのパラメータ抽出・型変換・バリデーション・API 仕様書生成** がすべて自動で行われる点です。

```drawlib align=center code=fold file=03_parameter_resolution.png caption="URL パス・クエリ・ヘッダーからのパラメータ抽出と型アノテーションによる自動キャストフロー"
from drawlib.canvas import save, setup
from drawlib.icons import code as code_icons, phosphor
from drawlib.lines import line
from drawlib.shapes import rectangle
from drawlib.styles import Styles
from drawlib.text import text

setup(width=128, height=54)

# Outer container
rectangle((64, 30.0), width=122, height=42, style=Styles.MutedDashed.patch(shape_r=2.0))
text(
    (64, 47.0),
    "URL Parameter Resolution: Path & Query -> Type Hint Casting -> Automatic Validation",
    style=Styles.DarkBold.patch(text_size=10.6),
)

# 1. Incoming Request URL
rectangle((19.0, 27.5), width=24, height=31, style=Styles.Neutral.patch(shape_r=1.8))
phosphor.globe((19.0, 38.0), width=5.0, style=Styles.Dark)
text((19.0, 31.8), "Request URL", style=Styles.DarkBold.patch(text_size=10.0))
text(
    (19.0, 20.5),
    "GET /items/42\n?q=fastapi\n&limit=10",
    style=Styles.Dark.patch(text_size=9.2),
)

line((31.0, 27.5), (37.0, 27.5), arrow_head="->", style=Styles.DarkBold)

# 2. Path & Query Extractor
rectangle((49.0, 27.5), width=24, height=31, style=Styles.PrimaryNeutral.patch(shape_r=1.8))
phosphor.git_fork((49.0, 38.0), width=5.0, style=Styles.PrimaryBold)
text((49.0, 31.8), "Parameter Parser", style=Styles.DarkBold.patch(text_size=10.0))
text(
    (49.0, 20.5),
    "Extract Strings\n• {item_id} = '42'\n• q = 'fastapi'\n• limit = '10'",
    style=Styles.Dark.patch(text_size=9.2),
)

line((61.0, 27.5), (67.0, 27.5), arrow_head="->", style=Styles.DarkBold)

# 3. Python Type Hints (Focal Hero)
rectangle((79.0, 27.5), width=24, height=31, style=Styles.PrimaryFlat.patch(shape_r=1.8))
code_icons.python((79.0, 38.0), width=5.0, style=Styles.White)
text((79.0, 31.8), "Type Hint Cast", style=Styles.WhiteBold.patch(text_size=10.0))
text(
    (79.0, 20.5),
    "item_id: int\nq: str | None\nlimit: int = 10",
    style=Styles.White.patch(text_size=9.2),
)

line((91.0, 27.5), (97.0, 27.5), arrow_head="->", style=Styles.DarkBold)

# 4. Verified Execution
rectangle((109.0, 27.5), width=24, height=31, style=Styles.SecondaryNeutral.patch(shape_r=1.8))
phosphor.check_circle((109.0, 38.0), width=5.0, style=Styles.PrimaryBold)
text((109.0, 31.8), "Valid Function Call", style=Styles.DarkBold.patch(text_size=10.0))
text(
    (109.0, 20.5),
    "read_item(\n  item_id=42,\n  q='fastapi',\n  limit=10\n)",
    style=Styles.Dark.patch(text_size=8.8),
)

# Bottom ribbon
rectangle(
    (64, 4.8),
    width=122,
    height=6.0,
    style=Styles.Neutral.patch(shape_r=1.2),
    text="Path Parameters   •   Query Parameters with Defaults   •   Auto 422 Unprocessable Entity",
    text_style=Styles.DarkBold.patch(text_size=9.5),
)

save()
```

```python
!pip install -q fastapi httpx
```

---

## 1. パスパラメータ（Path Parameters）

URL の一部を変数として受け取るには、ルートパスに波括弧 `{param_name}` を含め、関数引数で同名の型アノテーションを記述します。

```python
from fastapi import FastAPI
from fastapi.testclient import TestClient

app = FastAPI(title="Routing & Parameters")

# item_id: int と型を指定するだけで、自動的に文字列から整数へキャストされる
@app.get("/items/{item_id}")
def read_item(item_id: int):
    return {
        "item_id": item_id,
        "type": str(type(item_id)),
    }

client = TestClient(app)

# 1. 正常な整数を渡す (HTTP 200 OK)
res_ok = client.get("/items/42")
print("Valid Item ID 42 ->", res_ok.status_code, res_ok.json())

# 2. 数値に変換できない文字列を渡す (HTTP 422 Unprocessable Entity が自動返却)
res_err = client.get("/items/not-a-number")
print("Invalid Item ID  ->", res_err.status_code, res_err.json()["detail"][0]["msg"])
```

---

## 2. クエリパラメータ（Query Parameters）

パスに含まれない関数引数は、自動的に **URL クエリパラメータ**（`?key=value`）として解釈されます。既定値やオプショナルな型も自然に書けます。

```python
@app.get("/search")
def search_items(q: str | None = None, limit: int = 10, offset: int = 0):
    return {
        "query": q,
        "limit": limit,
        "offset": offset,
        "items": [f"Item_{i}" for i in range(offset, offset + limit)],
    }

# 1. デフォルト値のまま呼び出し
res_default = client.get("/search")
print("Default Query ->", res_default.json()["limit"], res_default.json()["query"])

# 2. クエリパラメータを指定して呼び出し
res_custom = client.get("/search?q=drawlib&limit=3&offset=5")
print("Custom Query  ->", res_custom.json())
```

---

## 3. パスパラメータとクエリパラメータの併用

パスパラメータとクエリパラメータは自由に組み合わせることができます。

```python
@app.get("/users/{user_id}/orders/{order_id}")
def get_user_order(user_id: int, order_id: str, detailed: bool = False):
    return {
        "user_id": user_id,
        "order_id": order_id,
        "detailed": detailed,
    }

res_order = client.get("/users/100/orders/ord_abc123?detailed=true")
print("Combined Endpoint ->", res_order.json())
```

> [!TIP] `detailed: bool = False` の自動変換
> FastAPI は `detailed=true`、`detailed=1`、`detailed=yes`、`detailed=on` などを自動的に Python の `True` に解釈します。

---

## 次の章へ

パスとクエリの解析ができるようになりました。
次の **第 4 章（Pydantic とリクエストボディ検証）** では、HTTP POST リクエストで複雑な JSON データを安全に受け取る **Pydantic スキーマ** を学びます！

