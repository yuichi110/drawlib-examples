# 06. 認証とセキュリティ (Authentication & JWT Bearer Token)

Web API の構築において、ユーザー認証とアクセス認可は不可欠な基盤です。FastAPI は `fastapi.security` モジュールを提供しており、業界標準の **OAuth2** および **JWT (JSON Web Token)** Bearer 認証を直感的かつ型安全に実装できます。

本章では、第 5 章で学んだ `Depends` をフル活用して、ステートレスな JWT トークンの発行・検証パイプラインを構築します。

```drawlib align=center code=fold file=06_jwt_auth_sequence.png caption="FastAPI における OAuth2 / JWT Bearer トークン認証と依存性注入による検証シーケンス"
from drawlib.canvas import save, setup
from drawlib.icons import phosphor
from drawlib.lines import line
from drawlib.shapes import rectangle
from drawlib.styles import Styles
from drawlib.text import text

setup(width=128, height=70)

# Outer container
rectangle((64, 38.5), width=122, height=53, style=Styles.MutedDashed.patch(shape_r=2.0))
text(
    (64, 61.5),
    "JWT Bearer Authentication: Login -> Sign Token -> Bearer Request -> Verify via Depends",
    style=Styles.DarkBold.patch(text_size=10.5),
)

# Column Headers
rectangle(
    (24.0, 53.5),
    width=32,
    height=7.0,
    style=Styles.Neutral.patch(shape_r=1.5),
    text="Client (Browser/App)",
    text_style=Styles.DarkBold.patch(text_size=9.2),
)
rectangle(
    (64.0, 53.5),
    width=32,
    height=7.0,
    style=Styles.Neutral.patch(shape_r=1.5),
    text="FastAPI: /token",
    text_style=Styles.DarkBold.patch(text_size=9.2),
)
rectangle(
    (104.0, 53.5),
    width=32,
    height=7.0,
    style=Styles.Neutral.patch(shape_r=1.5),
    text="FastAPI: /users/me",
    text_style=Styles.DarkBold.patch(text_size=9.2),
)

# Step 1: POST /token
line((24.0, 45.0), (64.0, 45.0), arrow_head="->", style=Styles.DarkBold)
text((44.0, 47.0), "1. POST /token (username/password)", style=Styles.Dark.patch(text_size=8.5))

# Step 2: Sign JWT
rectangle((64.0, 37.5), width=32, height=8.0, style=Styles.PrimaryNeutral.patch(shape_r=1.2))
text((64.0, 37.5), "Verify Credentials & Sign JWT\n(HS256 Secret Key)", style=Styles.DarkBold.patch(text_size=8.0))

# Step 3: Return Token
line((64.0, 30.0), (24.0, 30.0), arrow_head="->", style=Styles.DarkBold)
text((44.0, 32.0), "2. Return {\"access_token\": \"...\", \"token_type\": \"bearer\"}", style=Styles.Dark.patch(text_size=8.2))

# Step 4: Protected GET with Bearer Token
line((24.0, 22.5), (104.0, 22.5), arrow_head="->", style=Styles.PrimaryBold)
text((64.0, 24.5), "3. GET /users/me (Header: Authorization: Bearer <token>)", style=Styles.PrimaryBold.patch(text_size=8.4))

# Step 5: Verification box at Endpoint
rectangle((104.0, 15.0), width=32, height=8.5, style=Styles.PrimaryFlat.patch(shape_r=1.5))
text((104.0, 16.8), "Depends(get_current_user)", style=Styles.WhiteBold.patch(text_size=8.6))
text((104.0, 12.5), "• Decode Signature • Check Expiry", style=Styles.White.patch(text_size=7.8))

# Step 6: 200 OK Response
line((104.0, 7.5), (24.0, 7.5), arrow_head="->", style=Styles.SecondaryBold)
text((64.0, 9.3), "4. HTTP 200 OK (Current User Profile)", style=Styles.SecondaryBold.patch(text_size=8.4))

# Bottom ribbon
rectangle(
    (64, 3.2),
    width=122,
    height=4.8,
    style=Styles.Neutral.patch(shape_r=1.2),
    text="Stateless Scalability   •   Cryptographic Verification   •   OAuth2 Standard",
    text_style=Styles.DarkBold.patch(text_size=9.2),
)

save()
```

---

## 1. 必要なライブラリのセットアップ

Colab や Jupyter 上で実行する場合、JWT の署名と検証を行うライブラリが必要です。ここでは標準的な `pyjwt` を使用します。

```python
!pip install -q fastapi httpx pyjwt python-multipart
```

---

## 2. JWT の生成と検証ヘルパー

JWT は **Header（アルゴリズム）**, **Payload（クレーム情報・有効期限）**, **Signature（秘密鍵による署名）** の 3 つの要素から構成されます。

```python
import time
from datetime import datetime, timedelta, timezone
from typing import Optional

from fastapi import Depends, FastAPI, HTTPException, status
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from fastapi.testclient import TestClient
import jwt

# セキュリティ設定
SECRET_KEY = "drawlib-fastapi-super-secret-key-change-in-production"
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 30

# OAuth2 Bearer スキーム定義 (/token エンドポイントからトークンを取得することを宣言)
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")

# ダミーユーザーデータベース
FAKE_USERS_DB = {
    "alice": {
        "username": "alice",
        "full_name": "Alice Developer",
        "role": "admin",
        "hashed_password": "secretpassword123",
    }
}

def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    to_encode = data.copy()
    expire = datetime.now(timezone.utc) + (expires_delta or timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES))
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt
```

---

## 3. ユーザー認証と `Depends` によるトークン検証

認証済みユーザーを取得する依存関数 `get_current_user` を作成します。
FastAPI の `oauth2_scheme` が HTTP リクエストヘッダー（`Authorization: Bearer <token>`）からトークンを自動抽出し、`get_current_user` で署名と有効期限を検証します。

```python
app = FastAPI(title="FastAPI OAuth2 & JWT Demo")

def get_current_user(token: str = Depends(oauth2_scheme)):
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        # JWT の署名・有効期限を検証してデコード
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        username: str = payload.get("sub")
        if username is None:
            raise credentials_exception
    except jwt.PyJWTError:
        raise credentials_exception

    user = FAKE_USERS_DB.get(username)
    if user is None:
        raise credentials_exception
    return user
```

---

## 4. エンドポイントの実装: `/token` と保護された `/users/me`

1. `/token`: ユーザー名とパスワードを検証し、署名済み JWT アクセストークンを発行します。
2. `/users/me`: `Depends(get_current_user)` を指定した保護エンドポイントです。

```python
@app.post("/token")
def login(form_data: OAuth2PasswordRequestForm = Depends()):
    user = FAKE_USERS_DB.get(form_data.username)
    if not user or user["hashed_password"] != form_data.password:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Incorrect username or password",
        )
    # トークン発行
    access_token = create_access_token(data={"sub": user["username"], "role": user["role"]})
    return {"access_token": access_token, "token_type": "bearer"}

@app.get("/users/me")
def read_users_me(current_user: dict = Depends(get_current_user)):
    return {
        "status": "authorized",
        "username": current_user["username"],
        "full_name": current_user["full_name"],
        "role": current_user["role"],
    }
```

---

## 5. TestClient による認証フローの検証

実際に `TestClient` でログインを行い、トークンなし（401）、不正なトークン（401）、および有効な Bearer トークンでのアクセス（200）を確認します。

```python
client = TestClient(app)

# 1. トークンなしでアクセス -> 401 Unauthorized
res_no_token = client.get("/users/me")
print("1. Without Token:", res_no_token.status_code, res_no_token.json())

# 2. ログインしてアクセストークンを取得
login_res = client.post(
    "/token",
    data={"username": "alice", "password": "secretpassword123"},
)
print("2. Login Status:", login_res.status_code)
token_data = login_res.json()
access_token = token_data["access_token"]
print("   Obtained JWT:", access_token[:25] + "...")

# 3. 取得した Bearer トークンをヘッダーに付与してアクセス -> 200 OK
auth_header = {"Authorization": f"Bearer {access_token}"}
res_auth = client.get("/users/me", headers=auth_header)
print("3. Authenticated Access:", res_auth.status_code)
print("   Current User Profile:", res_auth.json())

# 4. 改ざんされたトークンでアクセス -> 401 Unauthorized
tampered_header = {"Authorization": f"Bearer {access_token}tampered"}
res_tampered = client.get("/users/me", headers=tampered_header)
print("4. Tampered Token Access:", res_tampered.status_code, res_tampered.json()["detail"])
```

---

## 次の章へ

これで、本番環境で通用する安全な OAuth2 / JWT 認証の仕組みが完成しました！
最後の **第 7 章（本番アーキテクチャと運用）** では、FastAPI アプリケーションをコンテナ化・非同期バックグラウンド処理・リバースプロキシ連携などを用いて本番運用するための全体アーキテクチャを学びます！

