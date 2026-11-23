# 02. FastAPI Hello World とリクエスト処理の基本

本章から本格的な **FastAPI** のハンズオンに入ります。まずは FastAPI の全体像と、クライアントから届いた HTTP リクエストがどのように処理されて JSON が返るかの流れを図解で理解し、Colab 上で実際に最小アプリケーションを実行してみましょう。

```drawlib align=center code=fold file=02_fastapi_request_flow.png caption="FastAPI におけるリクエスト受付・ルーティング・JSON レスポンス生成の基本処理フロー"
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
    "FastAPI Request & Response Lifecycle: Client -> Uvicorn (ASGI) -> Router -> JSON",
    style=Styles.DarkBold.patch(text_size=10.6),
)

# 1. Client
rectangle((19.0, 27.5), width=24, height=31, style=Styles.Neutral.patch(shape_r=1.8))
phosphor.globe((19.0, 38.0), width=5.0, style=Styles.Dark)
text((19.0, 31.8), "Client / Browser", style=Styles.DarkBold.patch(text_size=10.0))
text(
    (19.0, 20.5),
    "HTTP GET /\n• Headers\n• User-Agent\n• Accept: json",
    style=Styles.Dark.patch(text_size=9.2),
)

line((31.0, 27.5), (37.0, 27.5), arrow_head="->", style=Styles.DarkBold)

# 2. Uvicorn (ASGI Server)
rectangle((49.0, 27.5), width=24, height=31, style=Styles.PrimaryNeutral.patch(shape_r=1.8))
code_icons.python((49.0, 38.0), width=5.0, style=Styles.PrimaryBold)
text((49.0, 31.8), "Uvicorn (ASGI)", style=Styles.DarkBold.patch(text_size=10.0))
text(
    (49.0, 20.5),
    "Async Worker\n• HTTP parse\n• Event Loop\n• Forwards scope",
    style=Styles.Dark.patch(text_size=9.2),
)

line((61.0, 27.5), (67.0, 27.5), arrow_head="->", style=Styles.DarkBold)

# 3. FastAPI Application (Focal Hero)
rectangle((79.0, 27.5), width=24, height=31, style=Styles.PrimaryFlat.patch(shape_r=1.8))
code_icons.fastapi((79.0, 38.0), width=5.0, style=Styles.White)
text((79.0, 31.8), "FastAPI Router", style=Styles.WhiteBold.patch(text_size=10.0))
text(
    (79.0, 20.5),
    "@app.get('/')\n• Match endpoint\n• Python execution\n• dict return",
    style=Styles.White.patch(text_size=9.2),
)

line((91.0, 27.5), (97.0, 27.5), arrow_head="->", style=Styles.DarkBold)

# 4. JSON Response
rectangle((109.0, 27.5), width=24, height=31, style=Styles.SecondaryNeutral.patch(shape_r=1.8))
phosphor.file_code((109.0, 38.0), width=5.0, style=Styles.PrimaryBold)
text((109.0, 31.8), "JSON Response", style=Styles.DarkBold.patch(text_size=10.0))
text(
    (109.0, 20.5),
    "HTTP 200 OK\n• Content-Type\n• Serialized dict\n• {\"message\": ...}",
    style=Styles.Dark.patch(text_size=9.2),
)

# Bottom ribbon
rectangle(
    (64, 4.8),
    width=122,
    height=6.0,
    style=Styles.Neutral.patch(shape_r=1.2),
    text="Standard Python Typing   •   Automatic JSON Serialization   •   Interactive In-Process TestClient",
    text_style=Styles.DarkBold.patch(text_size=9.5),
)

save()
```

---

## 1. FastAPI とは？

**FastAPI** は、Python 3.8+ の標準的な型ヒント（Type Hints）をもとに設計された、極めて高速かつ高機能な Web API フレームワークです。

### 主な特徴
- **高速なパフォーマンス**: NodeJS や Go に匹敵する高い処理性能（Starlette と Pydantic をベースに ASGI 上で動作）。
- **型安全と自動補完**: Python の標準型アノテーションを使うため、エディタでの自動補完が効き、実行時エラーを最小化。
- **自動ドキュメント生成**: OpenAPI（Swagger UI）および ReDoc 仕様のインタラクティブな API 仕様書がゼロ設定で自動生成。

---

## 2. ハンズオン: パッケージのインストール

まずは FastAPI と、テスト用クライアントに必要な `httpx` をインストールします。

```python
!pip install -q fastapi httpx
```

---

## 3. 最小の FastAPI アプリを動かす（`TestClient` の活用）

通常、FastAPI をローカルで動かす際は `uvicorn main:app --reload` で Web サーバーを起動しますが、Jupyter / Colab 環境ではセルがブロッキングしてしまいます。

そこで本ハンズオンでは、Starlette / FastAPI 公式の **`TestClient`** を使います。
`TestClient` を使うと、**バックグラウンドサーバーを立ち上げることなく、セル内で即座に HTTP リクエストをシミュレーションしてレスポンスを検証** できます。

```python
from fastapi import FastAPI
from fastapi.testclient import TestClient

# 1. FastAPI アプリケーションのインスタンスを作成
app = FastAPI(
    title="FastAPI Hands-on Tutorial",
    description="Drawlib × Google Colab で学ぶ FastAPI 入門",
    version="1.0.0",
)

# 2. ルートエンドポイント (GET /) を定義
@app.get("/")
def read_root():
    return {
        "message": "Hello World from FastAPI!",
        "status": "success",
        "powered_by": "Drawlib (Illustration & Notebook as Code)",
    }

# 3. TestClient でエンドポイントを呼び出し
client = TestClient(app)
response = client.get("/")

# 4. 結果の検証
print("Status Code:", response.status_code)
print("Response JSON:", response.json())
```

### コードの解説
1. **`app = FastAPI(...)`**: API 全体を統括するアプリケーション本体です。タイトルや概要を設定できます。
2. **`@app.get("/")`**: パス `/` に対する HTTP GET リクエストをハンドリングする「パスマッピングデコレータ」です。
3. **辞書をそのまま返すだけ**: 関数が Python の辞書（`dict`）を返すと、FastAPI が自動的に `Content-Type: application/json` の JSON 文字列へシリアライズして HTTP 200 OK で返します。

---

## 4. 別のエンドポイントを追加してみる

エンドポイントの追加も非常に簡単です。新しいパス `/info` を追加してみましょう。

```python
@app.get("/info")
def read_info():
    return {
        "app_name": "FastAPI Hands-on",
        "features": ["Async", "Type Hints", "Auto OpenAPI", "Pydantic Validation"],
        "version": "1.0.0",
    }

# /info を呼び出す
res_info = client.get("/info")
print("GET /info ->", res_info.json())
```

---

## 次の章へ

第 2 章では、FastAPI の最小 Hello World とリクエスト処理の基本を体験しました。
次の **第 3 章（ルーティングとパラメータ解析）** では、URL に動的な変数を含める **パスパラメータ** や **クエリパラメータ**、そして Python の型ヒントによる **自動バリデーション** を学びます！

