# 08. 本番アーキテクチャと運用 (Production Architecture & Deployment)

FastAPI は、Starlette（非同期 Web コア）と Pydantic（データバリデーション）の上に構築された、Python エコシステム屈指の超高速 ASGI Web フレームワークです。

シリーズの締めくくりとなる本章では、FastAPI を本番環境（クラウド、コンテナ、クラスタ）で高信頼・高スループットに運用するための **推奨アーキテクチャ設計**、**Lifespan イベント管理**、および **非同期バックグラウンド処理 (`BackgroundTasks`)** を学びます。

```drawlib align=center code=fold file=08_production_backend_architecture.png caption="クラウド本番環境における FastAPI バックエンドアーキテクチャとデータフロー"
from drawlib.canvas import save, setup
from drawlib.icons import code as code_icons, phosphor
from drawlib.lines import line
from drawlib.shapes import rectangle
from drawlib.styles import Styles
from drawlib.text import text

setup(width=128, height=64)

# Outer boundary
rectangle((64, 35.5), width=122, height=49, style=Styles.MutedDashed.patch(shape_r=2.0))
text(
    (64, 56.5),
    "Production FastAPI Architecture: Reverse Proxy -> Containerized ASGI Workers -> Storage & Cache",
    style=Styles.DarkBold.patch(text_size=10.2),
)

# 1. Client Tier
rectangle((16.0, 35.5), width=20, height=30, style=Styles.Neutral.patch(shape_r=1.5))
phosphor.globe((16.0, 45.0), width=4.5, style=Styles.Dark)
text((16.0, 39.5), "Clients", style=Styles.DarkBold.patch(text_size=9.5))
text(
    (16.0, 28.5),
    "• Web Browsers\n• Mobile Apps\n• Third-party APIs",
    style=Styles.Dark.patch(text_size=8.2),
)

line((26.0, 35.5), (34.0, 35.5), arrow_head="->", style=Styles.DarkBold)
text((30.0, 38.0), "HTTPS", style=Styles.Dark.patch(text_size=8.0))

# 2. Ingress / Reverse Proxy Tier
rectangle((44.0, 35.5), width=20, height=30, style=Styles.PrimaryNeutral.patch(shape_r=1.5))
phosphor.shield_check((44.0, 45.0), width=4.5, style=Styles.PrimaryBold)
text((44.0, 39.5), "Reverse Proxy", style=Styles.DarkBold.patch(text_size=9.5))
text(
    (44.0, 27.5),
    "Nginx / AWS ALB\n• SSL/TLS Term\n• Rate Limiting\n• Static Caching",
    style=Styles.Dark.patch(text_size=8.0),
)

line((54.0, 35.5), (62.0, 35.5), arrow_head="->", style=Styles.DarkBold)
text((58.0, 38.0), "ASGI", style=Styles.Dark.patch(text_size=8.0))

# 3. Application Tier (Docker / Kubernetes Pod)
rectangle((80.0, 35.5), width=36, height=33, style=Styles.Neutral.patch(shape_r=1.8))
text((80.0, 50.0), "Docker Container (FastAPI + Uvicorn)", style=Styles.DarkBold.patch(text_size=8.5))

# Sub-box 3A: FastAPI Application Core (Hero Focal Point)
rectangle((80.0, 40.5), width=32, height=13, style=Styles.PrimaryFlat.patch(shape_r=1.2))
code_icons.fastapi((68.0, 40.5), width=4.2, style=Styles.White)
text((83.0, 43.5), "FastAPI Application", style=Styles.WhiteBold.patch(text_size=9.0))
text(
    (83.0, 37.0),
    "Uvicorn Workers • DI • Validation",
    style=Styles.White.patch(text_size=8.0),
)

# Sub-box 3B: Asynchronous Background Tasks
rectangle((80.0, 24.5), width=32, height=11, style=Styles.SecondaryNeutral.patch(shape_r=1.2))
phosphor.lightning((68.0, 24.5), width=4.0, style=Styles.PrimaryBold)
text((83.0, 27.0), "BackgroundTasks", style=Styles.DarkBold.patch(text_size=8.8))
text(
    (83.0, 21.5),
    "Async Emails • Audit • Webhooks",
    style=Styles.Dark.patch(text_size=7.8),
)

# 4. Storage & Cache Tier
line((96.0, 42.5), (104.0, 42.5), arrow_head="->", style=Styles.DarkBold)
line((96.0, 35.5), (104.0, 26.5), arrow_head="->", style=Styles.DarkBold)

rectangle((115.0, 42.5), width=22, height=13, style=Styles.Neutral.patch(shape_r=1.5))
phosphor.database((115.0, 46.5), width=4.0, style=Styles.Dark)
text((115.0, 40.5), "PostgreSQL", style=Styles.DarkBold.patch(text_size=9.0))
text((115.0, 35.5), "ACID Relational DB", style=Styles.Dark.patch(text_size=7.8))

rectangle((115.0, 24.5), width=22, height=13, style=Styles.Neutral.patch(shape_r=1.5))
phosphor.stack((115.0, 28.5), width=4.0, style=Styles.Dark)
text((115.0, 22.5), "Redis", style=Styles.DarkBold.patch(text_size=9.0))
text((115.0, 17.5), "Cache & Token Store", style=Styles.Dark.patch(text_size=7.8))

# Bottom ribbon
rectangle(
    (64, 4.8),
    width=122,
    height=5.8,
    style=Styles.Neutral.patch(shape_r=1.2),
    text="ASGI Concurrency   •   High-Throughput Non-Blocking I/O   •   Scalable Cloud Deployment",
    text_style=Styles.DarkBold.patch(text_size=9.3),
)

save()
```

---

## 1. アプリケーションのライフサイクル管理 (`lifespan`)

本番環境では、アプリケーション起動時にデータベース接続プールやキャッシュ接続を確立し、終了時に安全にクローズする必要があります。
FastAPI では、モダンな Python の `asynccontextmanager` を用いた **Lifespan イベント** が標準推奨されています。

```python
from contextlib import asynccontextmanager
from typing import Dict, List

from fastapi import BackgroundTasks, FastAPI, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.testclient import TestClient

# モックの外部リソース接続プール
app_resources: Dict[str, any] = {}

@asynccontextmanager
async def lifespan(app: FastAPI):
    # --- 起動時処理 (Startup) ---
    print("[Startup] Initializing Database Connection Pool & Redis Cache...")
    app_resources["db_connected"] = True
    app_resources["sent_emails"] = []
    yield
    # --- 終了時処理 (Shutdown) ---
    print("[Shutdown] Closing connection pools and flushing queues...")
    app_resources["db_connected"] = False
```

---

## 2. CORS ミドルウェアの設定

ブラウザから直接 API が呼び出される本番構成では、**CORS (Cross-Origin Resource Sharing)** を適切に構成して、許可されたドメインからのリクエストのみを受け付けます。

```python
app = FastAPI(
    title="Production Ready FastAPI",
    version="1.0.0",
    lifespan=lifespan,
)

# CORS ミドルウェアの追加
app.add_middleware(
    CORSMiddleware,
    allow_origins=["https://myapp.example.com", "http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE"],
    allow_headers=["*"],
)
```

---

## 3. 非同期バックグラウンドタスク (`BackgroundTasks`)

メール送信や監査ログの記録など、レスポンス返却をブロックしたくない処理は `BackgroundTasks` を利用してバックグラウンドで非同期実行します。
クライアントには即座に `200 OK` が返るため、体感レイテンシを大幅に短縮できます。

```python
def send_notification_email(email: str, message: str):
    """レスポンス返却後に非同期で実行されるタスク"""
    log_entry = f"Sent email to {email}: {message}"
    print(f"  [Background Worker] {log_entry}")
    app_resources["sent_emails"].append(log_entry)

@app.post("/register/", status_code=status.HTTP_202_ACCEPTED)
def register_user(email: str, background_tasks: BackgroundTasks):
    # 1. ユーザー登録処理（即時実行）
    user_data = {"email": email, "status": "active"}

    # 2. バックグラウンドタスクの登録（レスポンス後に実行）
    background_tasks.add_task(
        send_notification_email,
        email=email,
        message="Welcome to FastAPI Illustrated by Drawlib!",
    )

    # 3. クライアントへ即座にレスポンス返却
    return {
        "message": "User registered successfully. Welcome email is queued.",
        "user": user_data,
    }

@app.get("/health/")
def health_check():
    """ロードバランサー用の死活監視ヘルスチェックエンドポイント"""
    return {
        "status": "healthy",
        "database": "connected" if app_resources.get("db_connected") else "disconnected",
        "queued_emails_count": len(app_resources.get("sent_emails", [])),
    }
```

---

## 4. TestClient による本番フローの統合テスト

`TestClient` のコンテキストマネージャーを使用すると、`lifespan` の起動と終了、および `BackgroundTasks` の実行結果を完全に検証できます。

```python
# lifespan を伴うコンテキスト内でテスト実行
with TestClient(app) as client:
    # 1. ヘルスチェック確認
    health_res = client.get("/health/")
    print("Health Check:", health_res.json())

    # 2. ユーザー登録リクエスト (HTTP 202 Accepted)
    reg_res = client.post("/register/?email=alice@drawlib.org")
    print("Registration Response:", reg_res.status_code, reg_res.json()["message"])

    # 3. バックグラウンドタスクが実行されたか確認
    health_after = client.get("/health/")
    print("Updated Status:", health_after.json())
    print("Logged Emails:", app_resources["sent_emails"])
```

---

## 5. 本番運用のベストプラクティスまとめ

1. **Uvicorn + プロセス管理**:
   * シングルプロセス運用ではなく、マルチコア CPU を活かすため Gunicorn の Uvicorn ワーカー (`uvicorn.workers.UvicornWorker`) や Docker / Kubernetes による複数コンテナ分散配置を行います。
2. **リバースプロキシ連携**:
   * TLS/SSL 終端、レートリミット、静的ファイルの配信は Nginx や AWS ALB に任せ、FastAPI は純粋なビジネスロジックの処理に特化させます。
3. **ログとトレーシング**:
   * JSON 形式の構造化ログや OpenTelemetry による分散トレーシングを組み込み、可観測性（Observability）を担保します。

---

## シリーズのまとめ & Drawlib について

本シリーズ（全 7 章）を通して、FastAPI の基礎からルーティング、Pydantic バリデーション、依存性注入、JWT 認証、そして本番アーキテクチャまでを一貫して体験しました。

この Jupyter ノートブック内のすべてのアーキテクチャ図・フロー図・シーケンス図は、Python ライブラリ **[Drawlib](https://github.com/yuichi-fukuda/drawlib)** によってコードから自動生成されています。

```text
図を描くのではなく、コードで図を定義する（Illustration as Code）
```

Drawlib を使えば、ドキュメントの更新と図の保守を Git 上で完全に同期し、常に正確で美しい技術資料や Colab ノートブックを自動生成できます。ぜひ皆さんの Python プロジェクトでも Drawlib をご活用ください！

* **Drawlib 公式ドキュメント**: [https://drawlib.org/](https://drawlib.org/)
* **GitHub リポジトリ**: [https://github.com/yuichi-fukuda/drawlib](https://github.com/yuichi-fukuda/drawlib)
* **Google Drive / Colab デモフォルダ**: [FastAPI Jupyter Showcase](https://drive.google.com/drive/folders/1dPZ0bikr9EY2VXQX2OCHhL3He9jxX2kH?usp=drive_link)

