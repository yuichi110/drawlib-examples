# 2. 前提知識と測定方法

本章では、第3章以降の実機ベンチマーク結果を正確に読み解くための技術的な前提知識と計測メソドロジーを定義する。前半（2.1〜2.2節）では、`gemini-3.8-flash` の推論レイテンシを構成する3つの内部フェーズ（**Prefill・Thinking・Decoding**）と、単一の平均値では捉えられない体感差を可視化する **2次元トラジェクトリ（経過時間 × 累積出力文字数）**、および Google AI Studio（`google-genai` SDK）における Blocking / Streaming 実装パターンを解説する。後半（2.3〜2.5節）では、適応型 Thinking ルーターの基盤となる **Pydantic 構造化出力（`response_schema`）の Cold/Warm 文法コンパイル特性** と **`pydantic_core.from_json(..., allow_partial="trailing-strings")` による不完全 JSON 逐次差分抽出**、マイクロ秒精度で全イベントを記録する **`ExecutionTracer`**（`src/gemini_evaluation/tracer.py`）の設計、そして **現行 Gemini 3.5 / 3.8 / 4 シリーズ全モデルの分類と `ThinkingConfig`・Context Caching 仕様の実機比較検証** を詳述する。

```drawlib align=center code=fold width=100% file=ch02_latency_phases_trajectory_ja.png caption="図2-1: LLM推論の3フェーズ構造（Prefill → Thinking → Decoding）と Blocking vs. Streaming の2次元トラジェクトリ比較（thinking=0 実測値）"
from drawlib.canvas import save, setup
from drawlib.icons import phosphor
from drawlib.lines import line
from drawlib.shapes import rectangle
from drawlib.styles import Styles
from drawlib.text import text
from drawlib.utils import draw_trajectory_panel, load_thinking_timeline

setup(width=156, height=82, dpi=150)

# Outer structural frame
rectangle((78.0, 41.0), width=152.0, height=78.0, style=Styles.MutedDashed.patch(shape_r=2.0))
text(
    (78.0, 76.6),
    "LLM推論の3フェーズ構造（Prefill → Thinking → Decoding）と 2D トラジェクトリ比較",
    style=Styles.DarkBold.patch(text_size=11.5),
)

# Top Section: 3 Latency Phases
rectangle((78.0, 60.2), width=145.6, height=24.0, style=Styles.PrimaryNeutral.patch(shape_r=1.5))
text(
    (78.0, 69.2),
    "1リクエスト内のサーバー側処理タイムライン（t = 0 ms リクエスト送信 → 全文生成完了）",
    style=Styles.DarkBold.patch(text_size=10.3),
)

phases = [
    (
        26.5,
        39.0,
        "Phase 1: Prefill (入力処理)",
        "KVキャッシュ照合 + 入力トークン並列処理",
        Styles.WhiteFlat,
        Styles.DarkBold,
        Styles.Dark,
    ),
    (
        76.0,
        46.0,
        "Phase 2: Thinking (内部推論)",
        "thoughts_token_count 生成 (+9.0ms/tok)",
        Styles.SecondaryNeutral,
        Styles.DarkBold,
        Styles.Dark,
    ),
    (
        127.5,
        43.0,
        "Phase 3: Decoding (出力生成)",
        "1トークン目 = TTFT → 自己回帰ストリーム",
        Styles.PrimaryFlat,
        Styles.WhiteBold,
        Styles.White,
    ),
]
for px, pw, p_title, p_sub, box_st, t_st, s_st in phases:
    rectangle((px, 60.4), width=pw, height=11.0, style=box_st.patch(shape_r=1.2))
    text((px, 62.6), p_title, style=t_st.patch(text_size=10.2))
    text((px, 58.2), p_sub, style=s_st.patch(text_size=10.0))

line((46.0, 60.4), (53.0, 60.4), arrow_head="->", style=Styles.DarkBold)
line((99.0, 60.4), (106.0, 60.4), arrow_head="->", style=Styles.DarkBold)

text(
    (78.0, 51.4),
    "• Streaming TTFT = Phase 1 + Phase 2 完了時点  |  • Blocking TTFT = Total (Phase 1 + Phase 2 + Phase 3 全完了時点)",
    style=Styles.DarkBold.patch(text_size=10.0),
)

# Bottom Section: Side-by-Side 2D Trajectory Comparison (thinking=0, high-contrast pastel bands)
ex_block = load_thinking_timeline("blocking", "0")
ex_stream = load_thinking_timeline("streaming", "0")

draw_trajectory_panel(
    x0=15.0,
    y0=12.6,
    pw=54.0,
    ph=23.5,
    title="① Blocking: generate_content (thinking=0)",
    subtitle="3,360 ms まで 0字待機 → 全338字を一括返却",
    ex=ex_block,
    max_t=4000.0,
    max_c=420.0,
    x_ticks=(0, 1000, 2000, 3000, 4000),
    y_ticks=(0, 200, 400),
    lang="ja",
)

draw_trajectory_panel(
    x0=91.0,
    y0=12.6,
    pw=54.0,
    ph=23.5,
    title="★② Streaming: generate_content_stream (thinking=0)",
    subtitle="TTFT 1,205 ms で表示開始 → 3,192 ms まで滑らかに373字送出",
    ex=ex_stream,
    max_t=4000.0,
    max_c=420.0,
    x_ticks=(0, 1000, 2000, 3000, 4000),
    y_ticks=(0, 200, 400),
    lang="ja",
)

text((42.0, 4.2), "経過時間 (ms) — 縦軸: 累積出力文字数", style=Styles.DarkBold.patch(text_size=10.0))
text((118.0, 4.2), "経過時間 (ms) — 薄紫帯: TTFT待機 / 薄青帯: ストリーム送出", style=Styles.DarkBold.patch(text_size=10.0))

save()
```

---

## 2.1 レイテンシの定義（3フェーズ構造）と2次元トラジェクトリ解剖

大規模言語モデル（LLM）の API 呼び出しにおける応答遅延を正確に評価・最適化するためには、単なる「リクエストから完了までの合計時間」ではなく、サーバー内部で直列に進行する **3つの処理フェーズ** に分解して理解する必要がある。

### 1. LLM 推論を構成する 3 つのフェーズ

1. **Phase 1: Prefill（入力処理＋KVキャッシュ照合）**：
   クライアントから送信された `system_instruction`、会話履歴 `history`、および最新のユーザー入力 `prompt`（合計 `prompt_token_count`）を Transformer レイヤーで並列処理し、Attention の Key-Value（KV）キャッシュを構築するフェーズである。Google AI Studio の `gemini-3.8-flash` では、過去の対話履歴プレフィックスがキャッシュにヒット（`cached_content_token_count`）した場合、該当トークン分の Prefill 計算がスキップされ、数万トークンの長大コンテキストでも初動遅延が最小化される（第5章で詳述）。
2. **Phase 2: Thinking（内部推論トークン生成：`thoughts_token_count`）**：
   `gemini-3.8-flash` のような推論（Reasoning / Thinking）対応モデルにおいて、ユーザーに見える回答本文（`chunk.text`）の最初の1トークン目を出力する**前**に、サーバー内部で多段階の思考プロセス（Chain-of-Thought）を自己回帰的に生成するフェーズである。ここで生成された推論トークン数はレスポンスの `usage_metadata.thoughts_token_count` に記録される。重要な仕様として、**Thinking フェーズが進行している間は Streaming モードであってもクライアントへ可視テキストチャンクが一切届かない**ため、内部推論に要した時間（実測で約 **`+9.0 ms / token`**）はすべて初回応答待機時間（TTFT）へ直列に上乗せされる。
3. **Phase 3: Decoding（可視出力トークンの自己回帰生成：`output_token_count`）**：
   Prefill と Thinking が完了した瞬間から、最終回答テキスト（`candidates_token_count` / `output_token_count`）を先頭から順に出力するフェーズである。

### 2. TTFT（Time to First Token）と Total 完了時間、および 2D トラジェクトリの重要性

上記の3フェーズを踏まえると、クライアント側で観測される2つの主要レイテンシ指標は次のように定式化される。

```text
TTFT_streaming = T_Network_RTT + T_Prefill + T_Thinking
Total = TTFT_blocking = T_Network_RTT + T_Prefill + T_Thinking + T_Decoding
```

- **TTFT（Time to First Token / `time_to_first_token_ms`）**：リクエスト送信時刻（`t = 0 ms`）から、最初の非空テキストチャンクがクライアントに到着するまでの経過時間である。対話型 UI においてユーザーが「AI が反応した」と知覚する**体感待ち時間**そのものを表す。Blocking 呼び出しでは全文生成が終わるまでレスポンスが返らないため、常に `TTFT = Total` となる。
- **Total Completion Time（全体完了時間 / `stream_completed_ms`）**：リクエスト送信（`t = 0 ms`）から最終チャンク（EOF）の受信が完了するまでの合計時間である。
- **なぜ「2次元トラジェクトリ（経過時間 × 累積出力文字数）」が必要か**：
  図2-1下段に示した実測比較（`thinking=0`）を見ると、完了時間（`Total`）だけを比較した場合は Blocking（`3,360 ms`）と Streaming（`3,192 ms`）は同水準に見える。しかし横軸に経過時間（`t_ms`）、縦軸にその時点で画面に表示された累積文字数（`chars`）をとった **2次元トラジェクトリ** を描くと、UX の決定的な違いが浮かび上がる。
  - **Blocking（図2-1左）**：`0 ms` から `3,360 ms` まで縦軸 `y = 0 chars`（画面白紙）のまま推移し、`3,360 ms` 時点で338文字が垂直ステップ状に一括出現する。
  - **Streaming（図2-1右）**：薄紫帯の Prefill 待機を終えた **`1,205 ms`（Blocking より `2,155 ms` / `64%` 早い時点）** で最初のチャンクが立ち上がり、薄青帯の区間（`1,205 → 3,192 ms`）にわたって滑らかな右肩上がりの傾斜で373文字が逐次表示される。人間がテキストを読む速度（日本語で約400〜600文字/分＝1秒あたり7〜10文字）よりも Gemini 3.8 Flash のデコード速度（1秒あたり約180〜200文字）の方が圧倒的に速いため、`1,205 ms` 以降の生成時間はユーザーの読解時間の裏に完全に隠蔽される。さらに第4章で扱う「段階1の受付文表示＋段階2の並列推論連結」のようなマルチステージ挙動も、2次元トラジェクトリを用いることで「初動の立ち上がり → 読解中のプラトー → 本回答の急勾配ストリーム」として視覚的に厳密評価できる。

---

## 2.2 Blocking vs. Streaming API の実装方法（Google AI Studio `google-genai` SDK）

本検証プロジェクト（`src/gemini_evaluation/llm_call.py`）では、Google AI Studio の公式 Python SDK である **`google-genai`** を用い、環境変数 `GEMINI_KEY` によるシンプルな API キー認証（`genai.Client(api_key=GEMINI_KEY)`）と非同期クライアント（`client.aio`）で全計測を統一している。

以下に、`gemini-3.8-flash` に対する **`ThinkingConfig` 全6段階の解決関数（`resolve_thinking_config`）** と、**Blocking（`generate_content`）** および **Streaming（`generate_content_stream`）** の標準呼び出し実装を示す（※`gemini-3.8-flash` 固有の `thinking_level` / `thinking_budget` の仕様詳細および他モデルとの違いは **2.5節** で詳述する）。

```python
from collections.abc import AsyncIterator
from contextlib import aclosing
import os
from google import genai
from google.genai import types

# 1. Google AI Studio クライアントの初期化 (.env または環境変数の GEMINI_KEY を使用)
GEMINI_KEY = os.environ["GEMINI_KEY"]
MODEL = "gemini-3.8-flash"
client = genai.Client(api_key=GEMINI_KEY)


def resolve_thinking_config(thinking: str | int | None = 0) -> types.ThinkingConfig | None:
    """6段階の thinking 指定 (0, minimal, low, medium, high, default) を ThinkingConfig へ変換する。
    ※ gemini-3.8-flash では ThinkingLevel.MINIMAL が非対応 (400エラー) かつ ThinkingLevel.LOW が
      思考トークン 0 となるため、ベンチマーク上の 0 / minimal / low には後方互換の thinking_budget を割り当てて段階計測している（2.5節参照）。
    """
    if thinking is None or thinking == "default":
        return None  # サーバー既定の動的推論 (gemini-3.8-flash の既定は medium)
    if isinstance(thinking, int):
        return types.ThinkingConfig(thinking_budget=thinking)
    key = str(thinking).strip().lower()
    if key == "0":
        return types.ThinkingConfig(thinking_budget=0)
    if key == "minimal":
        return types.ThinkingConfig(thinking_budget=256)
    if key == "low":
        return types.ThinkingConfig(thinking_budget=4096)
    level_map = {
        "medium": types.ThinkingLevel.MEDIUM,
        "high": types.ThinkingLevel.HIGH,
    }
    return types.ThinkingConfig(thinking_level=level_map[key])


# 2. Blocking 呼び出し (全文生成完了まで待機: TTFT == Total)
async def generate_text_blocking(prompt: str, thinking: str | int | None = 0) -> str:
    cfg = resolve_thinking_config(thinking)
    resp = await client.aio.models.generate_content(
        model=MODEL,
        contents=prompt,
        config=types.GenerateContentConfig(thinking_config=cfg) if cfg else None,
    )
    return resp.text or ""


# 3. Streaming 呼び出し (TTFT 到達直後からチャンクを逐次 yield)
async def stream_text_progressive(prompt: str, thinking: str | int | None = 0) -> AsyncIterator[str]:
    cfg = resolve_thinking_config(thinking)
    stream = await client.aio.models.generate_content_stream(
        model=MODEL,
        contents=prompt,
        config=types.GenerateContentConfig(thinking_config=cfg) if cfg else None,
    )
    async with aclosing(stream):
        async for chunk in stream:
            if chunk.text:
                yield chunk.text
```

---

## 2.3 Pydantic 構造化出力と不完全 JSON 逐次パース（Partial JSON Streaming）の仕組み

対話システムにおいて「質問の難易度に応じて内部推論（Thinking）の ON/OFF を自動判定したい」場合や、「画面表示テキストと同時に UI 制御用のフラグ・カテゴリを構造化取得したい」場合には、`GenerateContentConfig` に `response_mime_type="application/json"` と Pydantic の `BaseModel` クラス（`response_schema=...`）を指定する **構造化出力（Structured Outputs）** を利用する。

しかし、構造化出力をストリーミング（`generate_content_stream`）と組み合わせる際には、サーバー側の **FSM（有限状態機械）文法コンパイル特性** と、クライアント側の **不完全 JSON 逐次パース手法** の2点を正しく設計する必要がある。図2-2に、実機で計測した Cold vs. Warm スキーマコンパイル実験（`load_schema_experiment()`、全8試行）と、`pydantic_core.from_json(..., allow_partial="trailing-strings")` による逐次差分抽出パイプラインを示す。

```drawlib align=center code=fold width=100% file=ch02_pydantic_cold_warm_pipeline_ja.png caption="図2-2: Pydantic response_schema の Cold vs. Warm コンパイル実験（2項目 vs. 6項目、全8試行）と pydantic_core.from_json による逐次差分抽出パイプライン"
from drawlib.canvas import save, setup
from drawlib.charts.bar import BarChart
from drawlib.icons import phosphor
from drawlib.lines import line
from drawlib.shapes import rectangle
from drawlib.styles import Styles
from drawlib.text import text
from drawlib.utils import load_schema_experiment

setup(width=158, height=92, dpi=150)

# Outer structural frame
rectangle((79.0, 46.0), width=154.0, height=88.0, style=Styles.MutedDashed.patch(shape_r=2.0))
text(
    (79.0, 86.2),
    "Pydantic 構造化ストリーム：Cold vs. Warm スキーマコンパイルと不完全 JSON 逐次抽出機構",
    style=Styles.DarkBold.patch(text_size=11.5),
)

# ─── Top Section: Cold vs. Warm Schema Compilation Experiment ────────────────
exp = load_schema_experiment()
by_key = {(str(r["schema_label"]), int(r["run_index"])): r for r in exp}

ordered_groups = [
    ("2F #1", [by_key[("minimal_2field", 1)]]),
    ("2F #2-4", [by_key[("minimal_2field", 2)], by_key[("minimal_2field", 3)], by_key[("minimal_2field", 4)]]),
    ("6F #1", [by_key[("rich_6field", 1)]]),
    ("6F #2-4", [by_key[("rich_6field", 2)], by_key[("rich_6field", 3)], by_key[("rich_6field", 4)]]),
]
cats = [lbl for lbl, _ in ordered_groups]
ttft_vals = [round(sum(float(r["ttft_ms"]) for r in rows) / len(rows), 0) for _, rows in ordered_groups]
tot_vals = [round(sum(float(r["total_ms"]) for r in rows) / len(rows), 0) for _, rows in ordered_groups]

rectangle((55.0, 61.5), width=98.0, height=41.0, style=Styles.Neutral.patch(shape_r=1.4))
rectangle((55.0, 61.2), width=95.6, height=38.8, style=Styles.WhiteFlat.patch(shape_r=1.0))

text((32.5, 77.2), "① 初回チャンク到着 TTFT (ms)", style=Styles.PrimaryBold.patch(text_size=9.8))
chart_ttft = BarChart(
    axis_line_style=Styles.Dark,
    axis_text_style=Styles.DarkBold.patch(text_size=8.8),
    grid_style=Styles.MutedDashed,
    value_text_style=Styles.DarkBold.patch(text_size=8.8),
    value_format="{:,.0f}",
    width=40.0,
    height=23.5,
    categories=cats,
    orientation="vertical",
    bar_mode="group",
    bar_width_ratio=0.56,
    bar_r=0.3,
)
chart_ttft.configure_y_axis(min_value=0, max_value=4500, tick_step=1500, format="{:,.0f}")
chart_ttft.add_series(name="TTFT (ms)", values=ttft_vals, style=Styles.PrimaryFlat)
chart_ttft.draw(xy=(13.5, 48.2))

text((80.0, 77.2), "② 全文完了時間 Total (ms)", style=Styles.DarkBold.patch(text_size=9.8))
chart_tot = BarChart(
    axis_line_style=Styles.Dark,
    axis_text_style=Styles.DarkBold.patch(text_size=8.8),
    grid_style=Styles.MutedDashed,
    value_text_style=Styles.DarkBold.patch(text_size=8.8),
    value_format="{:,.0f}",
    width=40.0,
    height=23.5,
    categories=cats,
    orientation="vertical",
    bar_mode="group",
    bar_width_ratio=0.56,
    bar_r=0.3,
)
chart_tot.configure_y_axis(min_value=0, max_value=7500, tick_step=2500, format="{:,.0f}")
chart_tot.add_series(name="Total (ms)", values=tot_vals, style=Styles.SecondaryNeutral)
chart_tot.draw(xy=(61.0, 48.2))

# Right-side summary cards for Top Section
rectangle((129.5, 61.5), width=45.0, height=41.0, style=Styles.PrimaryNeutral.patch(shape_r=1.4))
text((129.5, 78.2), "スキーマ検証 (8試行) の結論", style=Styles.DarkBold.patch(text_size=10.4))

s_cards = [
    (
        69.4,
        "1. 新規スキーマ初回 (Cold)",
        "6F #1 は FSM 文法構築を伴い\nTTFT 3,337 ms (確定 2,954 ms)",
        Styles.WhiteFlat,
    ),
    (
        57.5,
        "2. Warm 時は -15.0% 短縮",
        "6F Warm (#2〜#4) 平均 2,837 ms\nthinking 確定も平均 2,419 ms",
        Styles.WhiteFlat,
    ),
    (
        45.6,
        "3. 2項目 vs 6項目は差 +93ms",
        "2F Warm 2,744 ms vs 6F 2,837 ms\nフィールド定義順こそが決定要因",
        Styles.SecondaryNeutral,
    ),
]
for cy, ch, cb, cst in s_cards:
    rectangle((129.5, cy), width=41.6, height=10.0, style=cst.patch(shape_r=0.9))
    text((129.5, cy + 2.4), ch, style=Styles.DarkBold.patch(text_size=9.8))
    text((129.5, cy - 1.8), cb, style=Styles.Dark.patch(text_size=9.5))

# ─── Bottom Section: pydantic_core.from_json Incremental Pipeline ────────────
rectangle((79.0, 20.8), width=146.0, height=34.0, style=Styles.PrimaryNeutral.patch(shape_r=1.5))
text(
    (79.0, 34.6),
    'Rust 製 pydantic_core.from_json(raw_bytes, allow_partial="trailing-strings") による逐次差分抽出パイプライン',
    style=Styles.DarkBold.patch(text_size=10.4),
)

p_steps = [
    (
        23.5,
        32.0,
        "Step 1: 未完boolの保留",
        '入力: \'{"thinking": fa\'\n→ 返却: {} (誤判定ゼロ)\n非文字列の断片は安全保留',
        Styles.WhiteFlat,
        Styles.DarkBold,
    ),
    (
        60.0,
        33.0,
        "Step 2: bool確定と分岐",
        '入力: \'{"thinking": false,\'\n→ {\'thinking\': False} (~2.5s)\ntrue 時は即 Stage-2 並列起動',
        Styles.SecondaryNeutral,
        Styles.DarkBold,
    ),
    (
        97.5,
        34.0,
        "★Step 3: 文字列差分抽出",
        '入力: \'..."response": "1行目\\\'\n→ 末尾 \\ を保留し \'1行目\' 返却\ndelta = msg[emitted_len:]',
        Styles.PrimaryFlat,
        Styles.WhiteBold,
    ),
    (
        134.5,
        31.0,
        "Step 4: EOF 完全型検証",
        "ストリーム完了時に\nmodel_validate_json(buf)\nで全必須項目を最終保証",
        Styles.WhiteFlat,
        Styles.DarkBold,
    ),
]
for px, pw, p_hdr, p_body, p_st, hdr_st in p_steps:
    rectangle((px, 18.8), width=pw, height=22.4, style=p_st.patch(shape_r=1.2))
    text((px, 26.8), p_hdr, style=hdr_st.patch(text_size=10.0))
    body_st = Styles.White.patch(text_size=10.0) if p_st == Styles.PrimaryFlat else Styles.Dark.patch(text_size=10.0)
    text((px, 15.8), p_body, style=body_st)

line((39.5, 18.8), (43.0, 18.8), arrow_head="->", style=Styles.DarkBold)
line((77.0, 18.8), (80.5, 18.8), arrow_head="->", style=Styles.DarkBold)
line((115.5, 18.8), (119.0, 18.8), arrow_head="->", style=Styles.DarkBold)

save()
```

### 1. サーバー側 Constrained Decoding（制約付きデコード）と Cold vs. Warm 文法コンパイル

`response_mime_type="application/json"` と `response_schema=AdaptiveStreamResponse` を指定すると、Google AI Studio バックエンドは与えられた Pydantic モデルの JSON Schema を解析し、デコーダ層で構文違反トークンの生成確率をマスクする **有限状態機械（FSM: Finite-State Machine）文法** へコンパイルする。これにより、マークダウンのコードフェンス混入や閉じ括弧漏れが数学的にゼロとなる。

図2-2上段および下表は、最小2フィールドの `AdaptiveStreamResponse(thinking: bool, response: str)`（`minimal_2field`）と、`Literal` 列挙型2項目・真偽値・文字列リストを加えた拡張6フィールドの `RichStreamResponse`（`rich_6field`）に対して、同一プロンプトを4回連続実行した実測値（`src/gemini_evaluation/adaptive_thinking_log.json`）である。なお、すべての試行において先頭フィールド `thinking` の確定時刻（`flag_decided_ms`）は第2フィールド `response` の初回チャンク表示時刻（`ttft_ms`）以前に成立（`flag_decided_ms <= ttft_ms < total_ms`）している。

| スキーマ構成 (`schema_label`) | 試行 | キャッシュ状態 | `thinking` 確定 (`flag_decided_ms`) | 初回チャンク (`ttft_ms`) | 全体完了 (`total_ms`) | 出力文字数 |
| :--- | :-: | :-: | ---: | ---: | ---: | ---: |
| **`minimal_2field`** (`AdaptiveStreamResponse`) | **#1** | Warm (本実験直後) | `2,562.2 ms` | **`2,562.2 ms`** | `5,319.0 ms` | `496 字` |
| **`minimal_2field`** (`AdaptiveStreamResponse`) | **#2** | Warm | `2,294.1 ms` | **`2,294.1 ms`** | `4,551.2 ms` | `455 字` |
| **`minimal_2field`** (`AdaptiveStreamResponse`) | **#3** | Warm | `2,194.2 ms` | **`2,492.2 ms`** | `4,950.2 ms` | `579 字` |
| **`minimal_2field`** (`AdaptiveStreamResponse`) | **#4** | Warm | `3,446.8 ms` | **`3,446.8 ms`** | `6,855.2 ms` | `686 字` |
| **`rich_6field`** (`RichStreamResponse`) | **#1** | **Cold (新規初回)** | `2,954.3 ms` | **`3,337.3 ms`** | `6,517.4 ms` | `507 字` |
| **`rich_6field`** (`RichStreamResponse`) | **#2** | Warm | `2,157.1 ms` | **`2,504.4 ms`** | `4,526.9 ms` | `360 字` |
| **`rich_6field`** (`RichStreamResponse`) | **#3** | Warm | `2,780.6 ms` | **`3,259.3 ms`** | `5,838.9 ms` | `422 字` |
| **`rich_6field`** (`RichStreamResponse`) | **#4** | Warm | `2,320.5 ms` | **`2,747.5 ms`** | `6,504.9 ms` | `679 字` |

- **新規スキーマ初回（Cold `#1`）と Warm `#2〜#4` の比較（`-15.0%` 短縮）**：
  `minimal_2field`（`AdaptiveStreamResponse`）は直前の本実験（45試行）で既にコンパイル済みだったため `#1` から `2,562.2 ms`（`#2〜#4` 平均 **`2,744.4 ms`**、全4回平均 `2,698.8 ms`）で応答した。一方、新規の6フィールド構成 `rich_6field` を初めて送信した **`rich_6field #1`（Cold）では、FSM 文法コンパイルに伴い `TTFT = 3,337.3 ms`（`flag_decided_ms = 2,954.3 ms`）** を要したが、直後の **`#2〜#4`（Warm）ではコンパイル済みキャッシュが適用され、平均 TTFT は `2,837.1 ms`（`2,504.4〜3,259.3 ms`、Cold 比 `-500.2 ms` / `-15.0%` 短縮）**、`thinking` フラグ確定時刻も平均 **`2,419.4 ms`** へ短縮された。
- **フィールド数（2項目 vs. 6項目）よりも「フィールド定義順」が TTFT を支配する**：
  Warm `#2〜#4` 同士を比較すると、2フィールド構成（平均 `2,744.4 ms`）と6フィールド構成（平均 `2,837.1 ms`）の TTFT 差はわずか **`+92.7 ms`（`+3.4%`）** に過ぎない。これは `RichStreamResponse` において **`thinking: bool` を先頭（第1フィールド）に置き、短い固定列挙型（`category`, `urgency`, `needs_human_escalation`）の直後に `response: str` を配置し、可変長リスト `suggested_followups: list[str]` を `response` の後ろ（末尾）に配置したため** である。JSON ストリーミングは定義順にトークンを生成するため、ルーティング用フラグを先頭、画面表示用の `response` を可変長配列の前に置くことが鉄則となる。

### 2. `pydantic_core.from_json(..., allow_partial="trailing-strings")` による逐次差分抽出

`generate_content_stream` で構造化 JSON を受信する際、ストリーム途中のチャンクには閉じ括弧のない JSON 断片（例：`'{"thinking": false, "response": "いつもご利用'`）が入るため、SDK 標準の `chunk.parsed` はストリーム完了まで常に `None` となる。

そこで `src/gemini_evaluation/adaptive_thinking.py` では、Pydantic v2 に標準搭載されている Rust 製パーサー **`pydantic_core.from_json(raw_bytes, allow_partial="trailing-strings")`** を用いてチャンク到着ごとに累積バッファを解析している。この方式は以下の決定的な利点を持つ。

1. **未完プリミティブの安全な保留**：`'{"thinking": fa'` のように真偽値リテラルが途中で切れている段階では `{}` を返し、`false` または `true` が完結した瞬間に初めて `{'thinking': False}` を返すため、不完全なトークンによる誤分岐が起きない。
2. **エスケープシーケンス分断への耐性と `O(1)` 差分スライス**：`"response"` 文字列の末尾がバックスラッシュ `\`（例：`\n` の1文字目）で分断された場合も、未完の `\` を内部保留して確定済み文字のみを返す。そのため、既にクライアントへ送出した文字数 `emitted_resp_len` を記録しておき、`delta = resp_so_far[emitted_resp_len:]` をスライスするだけで、文字化けや JSON 構文漏出を一切起こさずにプレーンテキスト同等のストリーミング表示を実現できる。

```python
from typing import Any
from pydantic import BaseModel
from pydantic_core import from_json


class AdaptiveStreamResponse(BaseModel):
    thinking: bool  # 第1フィールド：初回チャンク以前に確定するルーティングフラグ
    response: str   # 第2フィールド：逐次ストリーム表示する回答本文（または受付1文）


def parse_partial_json_dict(raw_buf: str) -> dict[str, Any] | None:
    """不完全なストリーミング JSON 文字列を Rust 製 pydantic_core で安全に辞書へ変換する。"""
    if not raw_buf:
        return None
    try:
        parsed = from_json(raw_buf.encode("utf-8"), allow_partial="trailing-strings")
        return parsed if isinstance(parsed, dict) else None
    except ValueError:
        return None
```

---

## 2.4 計測基盤アーキテクチャ（`ExecutionTracer`）

本レポートの全ベンチマーク（`src/gemini_evaluation/benchmark_thinking.py`、`benchmark_adaptive_thinking.py`、`benchmark_multiturn_chat.py`）は、`src/gemini_evaluation/tracer.py` に実装された共通計測クラス **`ExecutionTracer`** を用いて計測・シリアライズされている。

### `ExecutionTracer` が記録するマイクロ秒精度マイルストーンとトークン内訳

`ExecutionTracer` は、OS のシステム時計補正の影響を受けない単調増加タイマー **`time.perf_counter()`** を基準時計として使用し、各 API 呼び出しで以下の時系列イベントとメタデータを記録する。

| 記録カテゴリ | フィールド名 (`ExecutionTracer`) | 計測タイミング・定義 |
| :--- | :--- | :--- |
| **リクエスト開始** | `start` (`t_ms = 0.0`, `chars = 0`) | `tracer.start_gemini()` 呼び出し時点（API 呼び出し直前）の `time.perf_counter()` 原点。 |
| **推論・初動待機終端** | `thinking_end` (`t_ms = ttft_ms`, `chars = 0`) | 最初の非空チャンク到着直前に `(ttft_ms, 0)` を記録し、2D トラジェクトリ上の水平待機プラトー（Prefill + Thinking）を表現。 |
| **ストリーミングチャンク** | `chunk_1 .. chunk_N` (`t_ms`, `chars`) | `tracer.record_chunk(delta)` が呼ばれるたびに経過ミリ秒 `t_ms` と累積文字数 `_cum_chars` を追記（Blocking 時は `(total_ms, 0)` と `(total_ms, len(text))` のステップを記録）。 |
| **適応型ルーティング指標** | `flag_decided_ms` / `stage2_first_chunk_ms` | Pattern A / B / C において `thinking` フラグが確定した時刻と、並列起動された Stage-2（`thinking="low"`）の初回チャンクが到着した時刻。 |
| **トークン使用量内訳** | `prompt_token_count` / `cached_content_token_count` / `thoughts_token_count` / `output_token_count` | `usage_metadata` から抽出した入力トークン数、暗黙キャッシュヒットトークン数、内部推論トークン数、および可視出力トークン数。 |

すべての計測結果は人間が読みやすい YAML（`*_log.yaml`）およびプログラム処理用の JSON / JSONL（`*_log.json`、`*_runs.jsonl`、`*_turns.jsonl`）として保存され、本レポート内のすべての Drawlib チャートは `examples/doc/gemini_latency/utils.py` のローダー関数を介してこれらの実測ログから直接描画されている。

---

## 2.5 Gemini 3.5 / 3.8 / 4 シリーズのモデル分類と API オプション仕様の網羅検証

本レポートの第3章〜第5章では **`gemini-3.8-flash`** をベンチマーク対象モデルとして使用しているが、Google AI Studio（Gemini API）では **Gemini 3.5 / 3.8 シリーズ** から最新の **Gemini 4 シリーズ（`Hydrogen` / `Argon` / `Carbon`）** にかけて、`ThinkingConfig`（`thinking_level` と `thinking_budget` の扱い）や **Context Caching（Explicit / Implicit キャッシュとマルチターン末尾再処理ウィンドウ）**、サンプリングパラメータの仕様が大きく変化している。

本節では、公式ドキュメントの仕様と実機 API（`client.models.get()` および `generate_content()`）による検証結果を突き合わせ、**現行モデルの選び分け**と**モデル別の利用可能オプション・実測挙動**を3つの詳細な一覧表（表2-5A〜表2-5C）に整理する。

### 1. 現行モデルの分類・ポジショニングと選び分け指針（表2-5A）

現在（2026年11月時点）、旧世代の `gemini-2.5-flash`（`gemini-3.5-flash-lite` へ自動転送）、`gemini-2.5-pro`（`gemini-3.8-flash` へ自動転送）、および `gemini-3.5-flash`（`gemini-3.6-flash` へ自動転送）はすべて Deprecated（非推奨）となっている。一方で **Gemini 4 世代には「Lite」相当の超軽量モデルがまだ存在しない**ため、音声（Live / TTS）や画像生成（Nano Banana 系）の専用モデルを除けば、テキスト・マルチモーダル生成は実質的に下表の **現行 5 モデル（`3.5-flash-lite`、`3.8-flash`、`4-hydrogen`、`4-argon`、`4-carbon`）** から選択すれば全領域をカバーできる。

| モデルID (`model`) | 提供状態・世代 | 価格 (Input / Output 1M tok) | コンテキスト枠 / 単発出力上限 | 既定 `thinking_level` | ポジショニングと実務上の選択基準 |
| :--- | :---: | :--- | :--- | :---: | :--- |
| **`gemini-3.5-flash`** | Deprecated<br>*(3.6-flash へ自動転送)* | $1.50 / $7.50<br>*(3.6-flash 価格)* | 入力 `1,048,576`<br>出力 `65,536` (個別枠) | `medium` | **【旧世代 Flash（非推奨）】**<br>・現在はリクエストが自動的に `gemini-3.6-flash` へルーティングされる。<br>・新規開発では選ぶ必要はなく、`gemini-4-hydrogen` または `gemini-3.8-flash` へ移行する。 |
| **`gemini-3.5-flash-lite`** | **現役 Stable**<br>*(3.x 最新 Lite)* | **$0.30 / $2.50** | 入力 `1,048,576`<br>出力 `65,536` (個別枠) | **`minimal`**<br>*(思考 0 tok)* | **【最速・最安の軽量ワークホース（Lite 枠）】**<br>・Gemini 4 世代に Lite が存在しないため、**新規開発の軽量・高スループット枠における公式推奨モデル**（`2.5-flash` の公式移行先）。<br>・既定の `minimal` で思考トークン `0` の最速応答を返しつつ、サブエージェントの自律計画時のみ `medium` / `high` で思考させる使い分けに最適。 |
| **`gemini-3.8-flash`** | **現役 Stable**<br>*(本レポート検証対象)* | **$1.50 / $7.50** | 入力 `1,048,576`<br>出力 `65,536` (個別枠) | `medium` | **【3.x 世代の最終完成版 Flash】**<br>・`2.5-pro` の公式移行先。基本は同価格の後継 `gemini-4-hydrogen` への移行が推奨される。<br>・ただし **① `thinking_level="low"`（または `thinking_budget=0`）で思考トークンを完全に `0`（低遅延）にしたい場合**、および **② Explicit Context Caching（`caches.create`）を利用したい場合** は `4-hydrogen` が非対応のため、あえて `3.8-flash` を選択する明確なメリットがある。 |
| **`gemini-4-hydrogen`** | **現役 Stable**<br>*(Flash 後継推奨)* | **$1.50 / $7.50**<br>*(Free / Paid 両対応)* | **統合 1M 枠 (`1,048,576`)**<br>単発出力 `65,536`<br>*(Long Decode 最大 1M)* | **`high`** | **【Gemini 4 標準メインストリーム】**<br>・`3.8-flash` と同価格で推論・コーディング能力が向上した現行の基本推奨モデル。<br>・常時思考型（思考 0 トークン化は不可）であり、Hydrogen 専用の最高推論レベル **`xhigh`** と **Long Decode（`automatic_continuation=True` による最大 1M トークン連続出力）** に対応する。 |
| **`gemini-4-argon`** | **現役 Stable**<br>*(Paid Tier 限定)* | **$2.00 / $10.00**<br>*(2026/12/1 以降 $4 / $20)* | **統合 1M 枠 (`1,048,576`)**<br>REST 単発 `32,768` / Stream `65,536`<br>*(Long Decode 最大 1M)* | `medium` | **【高効率フロンティア推論（Pro 相当枠）】**<br>・`hydrogen` では解けない高度なソフトウェア設計・数学・複雑なマルチステップ推論向け。<br>・`carbon` に迫る推論精度を維持しつつ、1ターンあたりの思考トークン消費量と応答レイテンシを抑えたバランス型上位モデル。 |
| **`gemini-4-carbon`** | **現役 Stable**<br>*(Paid Tier 限定)* | **$2.00 / $10.00**<br>*(2026/12/1 以降 $4 / $20)* | **統合 1M 枠 (`1,048,576`)**<br>REST 単発 `32,768` / Stream `65,536`<br>*(Long Decode 最大 1M)* | `medium` | **【最高峰フロンティア推論（最難関タスク枠）】**<br>・1ターンあたり最も多くの思考トークンを投入し、難解なバグ解析・科学推論・サイバーセキュリティ防御など、レイテンシよりも**回答の到達精度が最優先**される場面の最終選択肢。 |

---

### 2. モデル別 `ThinkingConfig`（`thinking_level` vs. `thinking_budget`）仕様と実機検証マトリクス（表2-5B）

Gemini API における内部推論（Thinking）の制御パラメータには、Gemini 2.5 世代で導入された数値上限指定の **`thinking_budget`** と、Gemini 3 以降で導入された抽象度指定の **`thinking_level`** の2種類が存在する。

ここで最も重要な設計原則として、**`thinking_budget` は Gemini 3 以降の全モデルにおいて公式に非推奨（Deprecated）** であり、**「思考をオフ（0トークン化）または最小化したい場合は `thinking_budget=0` ではなく、各モデルがサポートする最小の `thinking_level`（`minimal` または `low`）を指定する」** のが正規の仕様である（なお、同一リクエスト内で `thinking_level` と `thinking_budget` を同時指定すると全モデルで `400` エラーとなる）。

下表（表2-5B）に、各モデルに対して `thinking_level` 全5種類（`minimal`, `low`, `medium`, `high`, `xhigh`）および後方互換の `thinking_budget`（`0`, `256`, `4096`）を送信した際の実機 API 挙動と生成された思考トークン数（`usage_metadata.thoughts_token_count`：単純な1問1答プロンプト／複雑な5人座席配置パズルプロンプト）を示す。

| 指定パラメータ (`ThinkingConfig`) | `gemini-3.5-flash`<br>*(3.6-flash へ自動転送)* | `gemini-3.5-flash-lite`<br>*(現役 Lite)* | `gemini-3.8-flash`<br>*(本レポート検証対象)* | `gemini-4-hydrogen`<br>*(4 標準モデル)* | `gemini-4-argon` /<br>`gemini-4-carbon` |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **サポートされる `thinking_level`** | **`minimal`, `low`, `medium`, `high`** (4段階) | **`minimal`, `low`, `medium`, `high`** (4段階) | **`low`, `medium`, `high`** (3段階) | **`low`, `medium`, `high`, `xhigh`** (4段階) | **`low`, `medium`, `high`** (3段階) |
| **未指定 (`None` / デフォルト)** | 既定 = **`medium`**<br>単純: `69 tok`<br>複雑: `2,711 tok` | 既定 = **`minimal`**<br>単純: **`0 tok` (`None`)**<br>複雑: **`0 tok` (`None`)** | 既定 = **`medium`**<br>単純: `0 tok` (`None`)<br>複雑: `1,303 tok` | 既定 = **`high`**<br>単純: `68 tok`<br>複雑: `1,286 tok` | 既定 = **`medium`**<br>複雑推論で動的思考 |
| **`thinking_level="minimal"`** | ✅ **対応（思考オフ相当）**<br>単純: **`0 tok`**<br>複雑: **`0 tok`** | ✅ **対応（既定・思考オフ）**<br>単純: **`0 tok`**<br>複雑: **`0 tok`** | ❌ **`400 INVALID_ARGUMENT`**<br>*(MINIMAL is not supported)* | ❌ **`400 INVALID_ARGUMENT`**<br>*(MINIMAL is not supported)* | ❌ **`400 INVALID_ARGUMENT`**<br>*(MINIMAL is not supported)* |
| **`thinking_level="low"`** | ✅ **対応（軽量〜中程度思考）**<br>単純: `70 tok`<br>複雑: `2,051 tok` | ✅ **対応（極小思考）**<br>単純: `41 tok`<br>複雑: **`0 tok`** | ✅ **対応（実質思考オフ）**<br>単純: **`0 tok`**<br>複雑: **`0 tok`** | ✅ **対応（最小レベル・常時思考）**<br>単純: `35 tok`<br>複雑: `1,324 tok` | ✅ **対応（最小レベル）**<br>単純: **`0 tok`**<br>複雑: 軽量思考 |
| **`thinking_level="medium"`** | ✅ **対応（既定）**<br>単純: `73 tok`<br>複雑: `2,613 tok` | ✅ **対応（本格思考開始）**<br>単純: `53 tok`<br>複雑: `4,175 tok` | ✅ **対応（既定）**<br>単純: `0 tok`<br>複雑: `1,403 tok` | ✅ **対応**<br>単純: `36 tok`<br>複雑: `1,528 tok` | ✅ **対応（既定）** |
| **`thinking_level="high"`** | ✅ **対応**<br>単純: `70 tok`<br>複雑: `3,921 tok` | ✅ **対応**<br>単純: `58 tok`<br>複雑: `4,224 tok` | ✅ **対応**<br>単純: `61 tok`<br>複雑: `1,636 tok` | ✅ **対応（既定）**<br>単純: `67 tok`<br>複雑: `1,217 tok` | ✅ **対応** |
| **`thinking_level="xhigh"`** | ❌ **`400 INVALID_ARGUMENT`**<br>*(XHIGH is not supported)* | ❌ **`400 INVALID_ARGUMENT`**<br>*(XHIGH is not supported)* | ❌ **`400 INVALID_ARGUMENT`**<br>*(XHIGH is not supported)* | ✅ **対応（Hydrogen 専用）**<br>単純: `84 tok`<br>複雑: **`3,376 tok`** | ❌ **`400 INVALID_ARGUMENT`**<br>*(XHIGH is not supported)* |
| **`thinking_budget=0`**<br>*(非推奨・レガシー指定)* | ⚠️ 後方互換で動作<br>単純: **`0 tok`** / 複雑: **`0 tok`** | ❌ **`400 INVALID_ARGUMENT`**<br>*(0 指定はエラーで拒否)* | ⚠️ 後方互換で動作<br>単純: **`0 tok`** / 複雑: **`0 tok`**<br>*(本検証の `"0"` で使用)* | ⚠️ **`low` に強制変換（警告）**<br>単純: `32 tok` / 複雑: `1,398 tok`<br>*(思考 0 にはならない)* | ⚠️ 最寄りの `thinking_level` に自動変換（思考オフ不可） |
| **`thinking_budget=256`**<br>*(非推奨・レガシー指定)* | ⚠️ 上限256を超えて思考<br>単純: `63 tok` / 複雑: `1,486 tok` | ⚠️ 上限256を超えて思考<br>単純: `50 tok` / 複雑: `2,009 tok` | ⚠️ 後方互換で動作<br>単純: **`0 tok`** / 複雑: **`0 tok`**<br>*(本検証の `"minimal"` で使用)* | ⚠️ `thinking_level` に丸め込み<br>単純: `69 tok` / 複雑: `1,346 tok` | ⚠️ 最寄りの `thinking_level` に自動変換 |
| **`thinking_budget=4096`**<br>*(非推奨・レガシー指定)* | ⚠️ `medium`〜`high` 相当<br>単純: `68 tok` / 複雑: `3,355 tok` | ⚠️ `medium` 相当<br>単純: `62 tok` / 複雑: `3,449 tok` | ⚠️ **中間思考量を生成**<br>単純: `0 tok` / 複雑: **`351〜673 tok`**<br>*(本検証の `"low"` で使用)* | ⚠️ `thinking_level` に丸め込み<br>複雑: `1,471 tok` | ⚠️ 最寄りの `thinking_level` に自動変換 |

#### 表2-5B から導かれる重要な実装上の注意点

1. **モデルによって「思考オフ（`0 tok`）」を実現する正規の指定方法が異なる**：
   - **`gemini-3.5-flash-lite` / `gemini-3.5-flash`（`3.6-flash`）**：`thinking_level="minimal"` を指定する（特に `3.5-flash-lite` はデフォルトが `"minimal"` のため未指定でも `0 tok` となる一方、**`thinking_budget=0` を渡すと `400 INVALID_ARGUMENT` でクラッシュする**ため注意が必要である）。
   - **`gemini-3.8-flash`**：`"minimal"` が廃止（`400` エラー）された代わりに、**`thinking_level="low"` が実質的な思考オフ（実測 `0 tok`）として機能**する。
   - **`gemini-4-hydrogen`**：公式仕様として「思考の無効化は不可（cannot disable thinking）」と定められており、`thinking_level="low"` や `thinking_budget=0` を渡しても必ず思考トークン（複雑問題で約 `1,300〜1,400 tok`）が生成される。
2. **本レポートの検証コード（`src/gemini_evaluation/llm_call.py`）における 6 段階ラベルの定義理由**：
   - 表2-5B の `gemini-3.8-flash` 列から分かるとおり、`gemini-3.8-flash` の公式 `thinking_level` は `low`（実測 `0 tok`）の次がいきなり `medium`（実測 `1,300〜1,400 tok`）へ跳躍する。
   - そこで第3章〜第4章のベンチマークでは、「思考ゼロ（`0 tok`）」と「深い思考（`1,300+ tok`）」の間にある **中程度の思考トークン領域（`350〜670 tok` 帯）でのレイテンシと計算精度の推移**を精密に測定するため、`resolve_thinking_config()` において `"0"` → `thinking_budget=0`（実測 `0 tok`）、`"minimal"` → `thinking_budget=256`（実測 `0 tok`）、`"low"` → `thinking_budget=4096`（実測 `351〜673 tok`）、`"medium"` → `ThinkingLevel.MEDIUM`、`"high"` → `ThinkingLevel.HIGH`、`"default"` → `None`（サーバー既定＝`medium`）というマッピングを採用している。

---

### 3. Context Caching（暗黙・明示キャッシュ）および API 制約の世代間比較（表2-5C）

長大なシステムプロンプトやマルチターン対話履歴の Prefill コスト・TTFT を削減する **Context Caching** や、サンプリング系パラメータの扱いについても、Gemini 3.5 / 3.8 / 4 で下表（表2-5C）の仕様差が存在する。

| 機能・パラメータ項目 | `gemini-3.5-flash` / `gemini-3.5-flash-lite` | `gemini-3.8-flash`<br>*(本レポート検証対象)* | `gemini-4-hydrogen` / `argon` / `carbon` |
| :--- | :--- | :--- | :--- |
| **Implicit Context Caching**<br>*(暗黙的キャッシュ：自動適用)* | ✅ **デフォルト ON**（設定不要）<br>・公称最小入力トークン数：`4,096 tok`<br>・キャッシュヒット分は Prefill 計算をスキップし入力単価を大幅割引 | ✅ **デフォルト ON**（設定不要）<br>・公称最小入力トークン数：`4,096 tok`<br>・**実測では総入力が `2,048 tok` を超えた直後の Turn 8（`2,686 tok`）からキャッシュヒット開始**（第5章参照） | ✅ **デフォルト ON**（設定不要・**95% 割引**）<br>・公称最小入力トークン数：`4,096 tok`<br>・**マルチターン時の「末尾 2,050 トークン再処理ルール」が公式ドキュメントに明文化** |
| **マルチターン対話におけるキャッシュ境界の内部アルゴリズム**<br>*(なぜ約 2,050 tok から始まり末尾が非キャッシュで残るのか)* | プレフィックス一致に対してキャッシュが自動構築されるが、直近ターンの末尾ウィンドウは通常レートで再処理される。 | 第5章の50ターン連続対話ベンチマークにて、**Turn 8（`2,686 prompt_tokens`）で `703 cached_tokens` が初発動し、以降 Turn 50 まで常に `Prompt - Cached ≈ 2,000 tokens`（末尾約2,000トークン）が非キャッシュとして残る**挙動を実測確認。 | Gemini 4 公式ドキュメントにて以下の内部仕様が正式に明記された：<br>*"新規リクエストの増分（モデル出力・思考・関数結果を含む）が **2,050 トークン以上** の場合のみ前回リクエスト全体がキャッシュされ、**2,050 トークン未満の増分では前回リクエストの末尾 2,050 トークンを通常入力レートで再処理する**"* |
| **Explicit Context Caching**<br>(`client.caches.create` / `createCachedContent`) | ✅ **サポート** (`v1beta`)<br>・任意の TTL を指定して明示的にキャッシュオブジェクトを作成・再利用可能 | ✅ **サポート** (`v1beta`)<br>・`models.get` の `supported_actions` に `createCachedContent` を含む | ❌ **廃止（全モデル非サポート・エラー）**<br>・`createCachedContent` は削除され、Implicit Caching のみに完全一本化 |
| **サンプリングパラメータ**<br>(`temperature`, `top_p`, `top_k`, `candidate_count`) | ⚠️ **Deprecated（非推奨・API側で無視）**<br>・`candidate_count` は非対応 | ⚠️ **Deprecated（非推奨・API側で無視）**<br>・推論品質維持のためデフォルト値固定（リクエストから削除推奨） | ⚠️ **Deprecated（非推奨・API側で無視）**<br>・有効範囲内の値は無視され、範囲外の値を渡すと `400` バリデーションエラー |
| **Model ロールでのプリフィル終了**<br>(`contents` 末尾が `role="model"`) | ❌ **`400 INVALID_ARGUMENT` エラー**<br>*(3.6-flash / 3.5-flash-lite 以降で禁止)* | ❌ **`400 INVALID_ARGUMENT` エラー**<br>・出力形式の強制には `system_instruction` または `response_schema` を使用する | ❌ **`400 INVALID_ARGUMENT` エラー** |

#### 表2-5C から導かれるコンテキストキャッシュの重要インサイト

公式ドキュメントの一覧表では、Gemini 3.8 や Gemini 4 の Implicit Context Caching の最小入力トークン数は **`4,096 tokens`** と記載されている。しかし第5章の実機50ターン検証（`gemini-3.8-flash`）では、`4,096 tokens` 未満である **Turn 8（`prompt_token_count = 2,686`）の時点で既に `cached_content_token_count = 703` のキャッシュヒットが自動的に始まっている**。

この一見矛盾する現象は、Gemini 4 の公式リリースノートで明文化された **「1ターンあたりの増分が 2,050 トークン未満のマルチターン対話では、前回リクエストの末尾 2,050 トークンを通常レートで再処理し、それより前のプレフィックスをキャッシュする」** という内部ルールによって完全に説明できる。すなわち、総入力トークン数が **`2,048〜2,050 tokens` の末尾再処理ウィンドウを超えた瞬間（Turn 7 の `2,298 tok` → Turn 8 の `2,686 tok`）から、末尾約 `2,000 tokens` を除いた先頭プレフィックス部分（`2,686 - 2,000 ≈ 686〜703 tok`）がキャッシュにヒットし始める** ためである（詳細は第5章 5.2節で検証する）。

