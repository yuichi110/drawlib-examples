# Gemini 3.8 Flash レイテンシ・アーキテクチャ評価レポート

**Google AI Studio（`google-genai` SDK）における Streaming 配信・`ThinkingConfig`・Pydantic 適応型ルーティング・50ターン暗黙キャッシュの実機検証**

**Author:** Yuichi Ito | **Date:** 2026-11 | **Target:** Google AI Studio (`google-genai` SDK / `gemini-3.8-flash`)

```drawlib align=center width=100% code=false file=ch00_cover_hero_ja.png caption="図0-1: Google AI Studio (gemini-3.8-flash) におけるレイテンシ・アーキテクチャ検証の3大評価軸と主要結論"
from drawlib.canvas import save, setup
from drawlib.icons import phosphor
from drawlib.lines import line
from drawlib.shapes import rectangle
from drawlib.styles import Styles
from drawlib.text import text

setup(width=156, height=76, dpi=150)

# Outer structural frame
rectangle((78.0, 38.0), width=152.0, height=72.0, style=Styles.MutedDashed.patch(shape_r=2.0))

# Top Header Banner
rectangle((78.0, 64.5), width=144.0, height=12.4, style=Styles.PrimaryNeutral.patch(shape_r=1.4))
text(
    (78.0, 67.2),
    "Google AI Studio (gemini-3.8-flash) レイテンシ・アーキテクチャ検証の3大評価軸",
    style=Styles.DarkBold.patch(text_size=11.5),
)
text(
    (78.0, 62.0),
    "google-genai SDK (api_key=GEMINI_KEY) | 推論トークン制御・Pydantic構造化ストリーム・50ターンPCサポート対話",
    style=Styles.Dark.patch(text_size=10.0),
)

# Pillar 1: Delivery Mode & ThinkingConfig (Neutral)
rectangle((78.0, 48.0), width=144.0, height=15.0, style=Styles.Neutral.patch(shape_r=1.4))
phosphor.sliders_horizontal((10.5, 51.0), width=3.2, style=Styles.DarkBold)
text(
    (13.8, 51.0),
    "1. 通信方式 & 5モデル横断比較",
    style=Styles.DarkBold.patch(text_size=10.5, halign="left"),
)
text(
    (9.5, 45.0),
    "第2〜3章（単発18試行 + 5モデル220試行）",
    style=Styles.Dark.patch(text_size=10.0, halign="left"),
)
line((58.0, 41.8), (58.0, 54.2), style=Styles.Muted)
text(
    (60.5, 51.0),
    "• Stream vs Block | 現行5モデル × 全 thinking_level (17) + 非推奨 budget=0 (5)",
    style=Styles.DarkBold.patch(text_size=10.0, halign="left"),
)
text(
    (60.5, 45.0),
    "• 速度と精度の二律背反：固定 low は複雑計算が浅く、固定 high は初動が大幅遅延",
    style=Styles.Dark.patch(text_size=10.0, halign="left"),
)

# Pillar 2: Adaptive Thinking Router (PrimaryFlat — Focal Point)
rectangle((78.0, 30.5), width=144.0, height=15.0, style=Styles.PrimaryFlat.patch(shape_r=1.4))
phosphor.star((10.5, 33.5), width=3.2, style=Styles.WhiteBold)
text(
    (13.8, 33.5),
    "★2. 適応型ルーター (Pattern A)",
    style=Styles.WhiteBold.patch(text_size=10.5, halign="left"),
)
text(
    (9.5, 27.5),
    "第4章（3.8-flash low→high 45試行）",
    style=Styles.White.patch(text_size=10.0, halign="left"),
)
line((58.0, 24.3), (58.0, 36.7), style=Styles.White)
text(
    (60.5, 33.5),
    "• {thinking: bool, response: str} 不完全JSON逐次抽出 + Stage-2 high 並列連結",
    style=Styles.WhiteBold.patch(text_size=10.0, halign="left"),
)
text(
    (60.5, 27.5),
    "• 通常ターンは low 1回完結 ・ 初回応答 2,336ms ・ 分岐 9/9 正解 ・ 複雑計算 3/3 正解",
    style=Styles.White.patch(text_size=10.0, halign="left"),
)

# Pillar 3: Multi-Turn Scalability & Context Caching (SecondaryNeutral)
rectangle((78.0, 13.0), width=144.0, height=15.0, style=Styles.SecondaryNeutral.patch(shape_r=1.4))
phosphor.database((10.5, 16.0), width=3.2, style=Styles.DarkBold)
text(
    (13.8, 16.0),
    "3. 50ターン Streaming & 暗黙キャッシュ",
    style=Styles.DarkBold.patch(text_size=10.5, halign="left"),
)
text(
    (9.5, 10.0),
    "第5章（50ターン × 3構成 = 150試行）",
    style=Styles.Dark.patch(text_size=10.0, halign="left"),
)
line((58.0, 6.8), (58.0, 19.2), style=Styles.Muted)
text(
    (60.5, 16.0),
    "• (1) 3.8-flash low / high と (2) 第4章 Adaptive Router の初期応答(TTFT)・完了(Total)",
    style=Styles.DarkBold.patch(text_size=10.0, halign="left"),
)
text(
    (60.5, 10.0),
    "• 暗黙キャッシュ自動共有 (最大90.2%) で 50ターン平均 TTFT 2,618ms (high比 -87.6%)",
    style=Styles.Dark.patch(text_size=10.0, halign="left"),
)

save()
```

---

### レポート概要と章構成（全5章）

本レポートは、Google AI Studio（`google-genai` SDK、`genai.Client(api_key=GEMINI_KEY)`）上の **`gemini-3.8-flash`**（および Gemini 3.5 / 4 シリーズ全5モデル）を対象に、パソコンが動かなくなったトラブルシュートを行う顧客とサポート窓口の対話シナリオを通じて、対話型AIアプリケーションの初期応答速度（TTFT：Time to First Token）と深層推論品質・長期対話スケーラビリティを両立するためのアーキテクチャ設計を、実機 API 計測ログ（`src/gemini_evaluation/`）に基づいて体系化した技術白書である。

| 章番号 | タイトル | 検証内容と主要インサイト |
| :---: | :--- | :--- |
| **第1章** | **エグゼクティブサマリー** | 全検証の結論マトリクス、主要ベンチマーク指標の横断比較、および本番システムに向けた推奨アーキテクチャ設計指針。 |
| **第2章** | **前提知識と測定方法** | LLM推論の3フェーズ（Prefill・Thinking・Decoding）、2次元トラジェクトリ（経過時間×累積出力文字数）、Pydantic `response_schema` の Cold/Warm 文法コンパイル特性と `pydantic_core.from_json(..., allow_partial="trailing-strings")` による逐次差分抽出、`ExecutionTracer` の計測基盤、および **Gemini 3.5 / 3.8 / 4 シリーズ全モデルの分類と `ThinkingConfig`・Context Caching 仕様の実機比較検証**。 |
| **第3章** | **パラメータとレイテンシー** | Blocking（`generate_content`）vs. Streaming（`generate_content_stream`）× `ThinkingConfig` 全6段階の実測比較、内部推論トークン数と TTFT の線形スケーリング則、PCサポート難易度3段階（Tier 1〜3）におけるトレードオフ、および **現行5モデル × 全 `thinking_level`（17構成）＋非推奨 `thinking_budget=0`（5構成）の計22構成×10問（220試行）横断レイテンシー比較**。 |
| **第4章** | **適応型 Thinking ルーター（Adaptive Thinking Router）** | Stage 1（簡易判断）と Stage 2（Thinking 推論：用途別3カテゴリ A/B/C）のモデル・`thinking_level` 選定候補と、**`gemini-3.8-flash`（`low → high`）** による45試行比較。平均 TTFT **`2,336 ms`**・分岐精度 **`100%`**・複雑計算 **`100%`** を達成する **Pattern A** の優位性。 |
| **第5章** | **マルチターンチャットでの挙動とコンテキストキャッシュ** | 全構成を **Streaming に統一** し、50ターン連続PCサポート対話（計150実行）において **`(1)` `3.8-flash low` / `high`** と **`(2)` 第4章の Adaptive Thinking 構成（Pattern A `low → high`）** の初期応答（TTFT）と完了時間（Total）、および Stage 1→2 間で自動共有される暗黙的コンテキストキャッシュ（最大 **`90.2%`** ヒット）を実証。 |

| ドキュメントメタデータ | 内容 |
| :--- | :--- |
| **タイトル (`title`)** | Gemini 3.8 Flash レイテンシ・アーキテクチャ評価レポート |
| **サブタイトル (`subtitle`)** | Google AI Studio における Streaming・ThinkingConfig・適応型ルーティング・50ターン対話の実機検証 |
| **著者 (`author`)** | Yuichi Ito |
| **作成年月 (`date`)** | 2026-11 |
| **検証 SDK / モデル** | Google AI Studio `google-genai` SDK (`genai.Client(api_key=GEMINI_KEY)`) / `gemini-3.8-flash` ほか現行5モデル |
| **計測コード・ログ** | `src/gemini_evaluation/llm_call.py`, `src/gemini_evaluation/adaptive_thinking.py`, `src/gemini_evaluation/tracer.py` |
