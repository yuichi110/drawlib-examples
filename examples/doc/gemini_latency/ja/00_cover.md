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

setup(width=100, height=58, dpi=150)

# Outer structural frame
rectangle((50.0, 29.0), width=96.0, height=54.0, style=Styles.MutedDashed.patch(shape_r=2.0))

# Top Header Banner
rectangle((50.0, 49.4), width=91.0, height=9.2, style=Styles.PrimaryNeutral.patch(shape_r=1.4))
text(
    (50.0, 51.4),
    "Google AI Studio (gemini-3.8-flash) レイテンシ・アーキテクチャ検証の3大評価軸",
    style=Styles.DarkBold.patch(text_size=11.0),
)
text(
    (50.0, 47.4),
    "google-genai SDK (api_key=GEMINI_KEY) | 推論トークン制御・Pydantic構造化ストリーム・50ターンPCサポート対話",
    style=Styles.Dark.patch(text_size=10.0),
)

# Pillar 1: Delivery Mode & ThinkingConfig (Neutral)
rectangle((50.0, 36.8), width=91.0, height=11.4, style=Styles.Neutral.patch(shape_r=1.4))
phosphor.sliders_horizontal((7.6, 39.1), width=2.8, style=Styles.DarkBold)
text(
    (10.0, 39.1),
    "1. 通信方式 & ThinkingConfig",
    style=Styles.DarkBold.patch(text_size=10.4, halign="left"),
)
text(
    (6.8, 34.5),
    "第2〜3章（全18試行 + 難易度別評価）",
    style=Styles.Dark.patch(text_size=10.0, halign="left"),
)
line((39.2, 32.2), (39.2, 41.4), style=Styles.Muted)
text(
    (40.8, 39.1),
    "• Stream t=0 vs Block | 内部推論トークン数 (ThTok) に比例して TTFT が線形増加",
    style=Styles.DarkBold.patch(text_size=10.0, halign="left"),
)
text(
    (40.8, 34.5),
    "• 速度と精度の二律背反：固定 t=0 は複雑計算で誤算リスク、固定 low は初動待機が増大",
    style=Styles.Dark.patch(text_size=10.0, halign="left"),
)

# Pillar 2: Adaptive Thinking Router (PrimaryFlat — Focal Point)
rectangle((50.0, 23.4), width=91.0, height=11.4, style=Styles.PrimaryFlat.patch(shape_r=1.4))
phosphor.star((7.6, 25.7), width=2.8, style=Styles.WhiteBold)
text(
    (10.0, 25.7),
    "★2. 適応型ルーター (Pattern A)",
    style=Styles.WhiteBold.patch(text_size=10.4, halign="left"),
)
text(
    (6.8, 21.1),
    "第4章（全45試行 + Cold/Warm 8試行）",
    style=Styles.White.patch(text_size=10.0, halign="left"),
)
line((39.2, 18.8), (39.2, 28.0), style=Styles.White)
text(
    (40.8, 25.7),
    "• {thinking: bool, response: str} 不完全JSON逐次抽出 + Stage-2 low 並列連結",
    style=Styles.WhiteBold.patch(text_size=10.0, halign="left"),
)
text(
    (40.8, 21.1),
    "• 通常ターンは1回呼出で即応 ・ 分岐判定 9/9 正解 ・ PC修理見積/転送計算 3/3 全問正解",
    style=Styles.White.patch(text_size=10.0, halign="left"),
)

# Pillar 3: Multi-Turn Scalability & Context Caching (SecondaryNeutral)
rectangle((50.0, 10.0), width=91.0, height=11.4, style=Styles.SecondaryNeutral.patch(shape_r=1.4))
phosphor.database((7.6, 12.3), width=2.8, style=Styles.DarkBold)
text(
    (10.0, 12.3),
    "3. 50ターン対話 & 暗黙キャッシュ",
    style=Styles.DarkBold.patch(text_size=10.4, halign="left"),
)
text(
    (6.8, 7.7),
    "第5章（50ターン × 4条件 = 200試行）",
    style=Styles.Dark.patch(text_size=10.0, halign="left"),
)
line((39.2, 5.4), (39.2, 14.6), style=Styles.Muted)
text(
    (40.8, 12.3),
    "• パソコン起動不能トラブルの客とサポート窓口の50ターン連続対話で Implicit Cache 自動発動",
    style=Styles.DarkBold.patch(text_size=10.0, halign="left"),
)
text(
    (40.8, 7.7),
    "• 履歴肥大化時もキャッシュヒットにより Streaming t=0 が平坦な TTFT 推移を維持",
    style=Styles.Dark.patch(text_size=10.0, halign="left"),
)

save()
```

---

### レポート概要と章構成（全5章）

本レポートは、Google AI Studio（`google-genai` SDK、`genai.Client(api_key=GEMINI_KEY)`）上の **`gemini-3.8-flash`** を対象に、パソコンが動かなくなったトラブルシュートを行う顧客とサポート窓口の対話シナリオを通じて、対話型AIアプリケーションの体感応答速度（TTFT：Time to First Token）と推論品質・長期対話スケーラビリティを両立するためのアーキテクチャ設計を、合計 **271 回の実機 API 計測ログ**（`src/gemini_evaluation/`）に基づいて体系化した技術白書である。

| 章 | タイトル | 検証内容と主要インサイト |
| :--- | :--- | :--- |
| **第1章** | **エグゼクティブサマリー** | 全検証の結論マトリクス、主要ベンチマーク指標の横断比較、および本番システムに向けた推奨アーキテクチャ設計指針。 |
| **第2章** | **前提知識と測定方法** | LLM推論の3フェーズ（Prefill・Thinking・Decoding）、2次元トラジェクトリ（経過時間×累積出力文字数）、Pydantic `response_schema` の Cold/Warm 文法コンパイル特性と `pydantic_core.from_json(..., allow_partial="trailing-strings")` による逐次差分抽出、および `ExecutionTracer` の計測基盤。 |
| **第3章** | **パラメータとレイテンシー** | Blocking（`generate_content`）vs. Streaming（`generate_content_stream`）× `ThinkingConfig` 全6段階（`0`, `minimal`, `low`, `medium`, `high`, `default`）の実測比較、内部推論トークン数と TTFT の線形スケーリング則、およびPCサポート難易度3段階（Tier 1〜3）における速度と計算正確性のトレードオフ。 |
| **第4章** | **適応型 Thinking ルーター（Adaptive Thinking Router）** | 固定設定の二律背反を解消する3つの適応型分岐方式（Pattern A: Pydantic 2フィールド統合ストリーム、Pattern B: 1フィールド分離ルーター、Pattern C: 非JSON先頭タグ）の45試行比較。分岐精度 **`100%`**・複雑計算 **`100%`** を達成する **Pattern A** の優位性。 |
| **第5章** | **マルチターンチャットでの挙動とコンテキストキャッシュ** | パソコンが動かなくなった顧客とPCサポート窓口による50ターン連続対話（計200実行）における4条件の推移比較。自動発動する暗黙的コンテキストキャッシュ（Implicit Context Caching）と平坦な TTFT スケーリング。 |

| ドキュメントメタデータ | 内容 |
| :--- | :--- |
| **タイトル (`title`)** | Gemini 3.8 Flash レイテンシ・アーキテクチャ評価レポート |
| **サブタイトル (`subtitle`)** | Google AI Studio における Streaming・ThinkingConfig・適応型ルーティング・50ターン対話の実機検証 |
| **著者 (`author`)** | Yuichi Ito |
| **作成年月 (`date`)** | 2026-11 |
| **検証 SDK / モデル** | Google AI Studio `google-genai` SDK (`genai.Client(api_key=GEMINI_KEY)`) / `gemini-3.8-flash` |
| **計測コード・ログ** | `src/gemini_evaluation/llm_call.py`, `src/gemini_evaluation/adaptive_thinking.py`, `src/gemini_evaluation/tracer.py` |
