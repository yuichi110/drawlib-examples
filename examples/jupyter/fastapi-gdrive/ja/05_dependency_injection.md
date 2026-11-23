# 05. 依存性注入 (Dependency Injection / Depends)

FastAPI を他の Web フレームワークから際立たせる強力な機能が **依存性注入（Dependency Injection: DI）** です。`Depends` を使うことで、共通ロジック（認証チェック、DB セッション管理、権限判定、パラメータ検証など）をエンドポイント間でスマートに共有できます。

```drawlib align=center code=fold file=05_dependency_injection_tree.png caption="FastAPI における Depends による依存関係の有向グラフ解決とエンドポイントへの自動注入フロー"
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
    "Dependency Injection with Depends: Incoming Request -> Resolve Dependencies -> Inject into Endpoint",
    style=Styles.DarkBold.patch(text_size=10.6),
)

# 1. Incoming Request
rectangle((18.0, 27.5), width=22, height=31, style=Styles.Neutral.patch(shape_r=1.8))
phosphor.globe((18.0, 38.0), width=5.0, style=Styles.Dark)
text((18.0, 31.8), "Request", style=Styles.DarkBold.patch(text_size=10.0))
text(
    (18.0, 20.5),
    "GET /items\n• Headers\n• Query params\n• Cookies / Body",
    style=Styles.Dark.patch(text_size=8.8),
)

line((29.0, 33.0), (37.0, 37.0), arrow_head="->", style=Styles.DarkBold)
line((29.0, 22.0), (37.0, 18.0), arrow_head="->", style=Styles.DarkBold)

# 2. Dependency A: Pagination
rectangle((51.0, 37.0), width=26, height=13, style=Styles.PrimaryNeutral.patch(shape_r=1.5))
text((51.0, 39.5), "Depends(pagination)", style=Styles.DarkBold.patch(text_size=9.2))
text((51.0, 33.5), "skip: int, limit: int", style=Styles.Dark.patch(text_size=8.5))

# 3. Dependency B: Auth Check
rectangle((51.0, 18.0), width=26, height=13, style=Styles.PrimaryNeutral.patch(shape_r=1.5))
text((51.0, 20.5), "Depends(verify_key)", style=Styles.DarkBold.patch(text_size=9.2))
text((51.0, 14.5), "X-API-Key header", style=Styles.Dark.patch(text_size=8.5))

line((64.0, 37.0), (74.0, 31.0), arrow_head="->", style=Styles.DarkBold)
line((64.0, 18.0), (74.0, 24.0), arrow_head="->", style=Styles.DarkBold)

# 4. Target Endpoint (Focal Hero)
rectangle((88.0, 27.5), width=26, height=31, style=Styles.PrimaryFlat.patch(shape_r=1.8))
code_icons.fastapi((88.0, 38.0), width=5.0, style=Styles.White)
text((88.0, 31.8), "Endpoint Function", style=Styles.WhiteBold.patch(text_size=10.0))
text(
    (88.0, 20.5),
    "read_items(\n  params = Inject A,\n  client = Inject B\n)",
    style=Styles.White.patch(text_size=8.8),
)

line((101.0, 27.5), (107.0, 27.5), arrow_head="->", style=Styles.DarkBold)

# 5. Clean Response
rectangle((118.0, 27.5), width=18, height=31, style=Styles.SecondaryNeutral.patch(shape_r=1.8))
phosphor.check_circle((118.0, 38.0), width=5.0, style=Styles.PrimaryBold)
text((118.0, 31.8), "Response", style=Styles.DarkBold.patch(text_size=10.0))
text(
    (118.0, 20.5),
    "HTTP 200\nVerified\nJSON Data",
    style=Styles.Dark.patch(text_size=8.8),
)

# Bottom ribbon
rectangle(
    (64, 4.8),
    width=122,
    height=6.0,
    style=Styles.Neutral.patch(shape_r=1.2),
    text="Hierarchical Dependency Trees   •   Code Reuse (DRY)   •   Security & DB Lifecycles",
    text_style=Styles.DarkBold.patch(text_size=9.5),
)

save()
```

---

## 1. 共通パラメータ処理の分離

ページネーション（`skip`, `limit`）など、複数のエンドポイントで共通して使うパラメータ処理を関数として切り出し、`Depends` で注入します。

```python
from fastapi import Depends, FastAPI, Header, HTTPException, status
from fastapi.testclient import TestClient

app = FastAPI(title="Dependency Injection")

# 1. 共通パラメータ用 Dependency
def common_parameters(skip: int = 0, limit: int = 10):
    return {"skip": skip, "limit": limit}

@app.get("/items/")
def read_items(params: dict = Depends(common_parameters)):
    return {
        "applied_params": params,
        "items": [f"Item_{i}" for i in range(params["skip"], params["skip"] + params["limit"])],
    }

client = TestClient(app)

res = client.get("/items/?skip=5&limit=2")
print("Items with DI ->", res.json())
```

---

## 2. セキュリティとヘッダー検証の依存関係

API キーなどの共通ヘッダー検証も `Depends` で記述できます。条件を満たさない場合は依存関数側で `HTTPException` を送出します。

```python
API_SECRET_KEY = "drawlib-secret-token"

# 2. 認証用 Dependency
def verify_api_key(x_api_key: str = Header(..., description="API 認証キー")):
    if x_api_key != API_SECRET_KEY:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or missing API Key",
        )
    return {"client_id": "authorized_user"}

# 認証とページネーションの両方を注入した保護エンドポイント
@app.get("/secure-data/")
def get_secure_data(
    user: dict = Depends(verify_api_key),
    pagination: dict = Depends(common_parameters),
):
    return {
        "status": "authenticated",
        "user": user,
        "pagination": pagination,
        "secret_payload": [10, 20, 30],
    }
```

---

## 3. 認証の挙動テスト

`TestClient` を使って、API キーがない場合（401）と正しいキーを付与した場合（200）の挙動を確認します。

```python
# 1. キーなしでアクセス (401 Unauthorized または 422 Header 欠損)
res_unauth = client.get("/secure-data/")
print("Without Key -> Status:", res_unauth.status_code)

# 2. 不正なキーでアクセス (401 Unauthorized)
res_bad = client.get("/secure-data/", headers={"X-API-Key": "wrong-key"})
print("Wrong Key   -> Status:", res_bad.status_code, res_bad.json()["detail"])

# 3. 正しいキーでアクセス (200 OK)
res_auth = client.get("/secure-data/", headers={"X-API-Key": "drawlib-secret-token"})
print("Valid Key   -> Status:", res_auth.status_code)
print("Auth Data   ->", res_auth.json())
```

---

## 次の章へ

`Depends` により、エンドポイント本体をビジネスロジックだけに集中させられることがわかりました。
次の **第 6 章（認証とセキュリティ: JWT Bearer トークン）** では、この `Depends` を応用して、標準的な **OAuth2 / JWT Bearer トークン認証** を実装します！

