# 2. 前提知識と測定方法

本章では、第3章以降の実機ベンチマーク結果を正確に読み解くための技術的な前提知識と計測メソドロジーを定義する。前半（2.1〜2.2節）では、`gemini-3.8-flash` の推論レイテンシを構成する3つの内部フェーズ（**Prefill・Thinking・Decoding**）と、単一の平均値では捉えられない体感差を可視化する **2次元トラジェクトリ（経過時間 × 累積出力文字数）**、および Google AI Studio（`google-genai` SDK）における Blocking / Streaming 実装パターンを解説する。後半（2.3〜2.4節）では、適応型 Thinking ルーターの基盤となる **Pydantic 構造化出力（`response_schema`）の Cold/Warm 文法コンパイル特性** と **`pydantic_core.from_json(..., allow_partial="trailing-strings")` による不完全 JSON 逐次差分抽出**、そしてマイクロ秒精度で全イベントを記録する **`ExecutionTracer`**（`src/gemini_evaluation/tracer.py`）の設計を詳述する。

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

以下に、`gemini-3.8-flash` に対する **`ThinkingConfig` 全6段階の解決関数（`resolve_thinking_config`）** と、**Blocking（`generate_content`）** および **Streaming（`generate_content_stream`）** の標準呼び出し実装を示す。

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


def resolve_thinking_config(thinking: str | int | None = 0) -> types.GenerateContentConfig | None:
    """6段階の thinking 指定 (0, minimal, low, medium, high, default) を GenerateContentConfig へ変換する。"""
    if thinking is None or thinking == "default":
        return None  # サーバー既定の動的推論 (default)
    if thinking in (0, "0"):
        return types.GenerateContentConfig(
            thinking_config=types.ThinkingConfig(thinking_budget=0)
        )
    level_map = {
        "minimal": types.ThinkingLevel.MINIMAL,
        "low": types.ThinkingLevel.LOW,
        "medium": types.ThinkingLevel.MEDIUM,
        "high": types.ThinkingLevel.HIGH,
    }
    return types.GenerateContentConfig(
        thinking_config=types.ThinkingConfig(thinking_level=level_map[str(thinking).lower()])
    )


# 2. Blocking 呼び出し (全文生成完了まで待機: TTFT == Total)
async def generate_text_blocking(prompt: str, thinking: str | int | None = 0) -> str:
    resp = await client.aio.models.generate_content(
        model=MODEL,
        contents=prompt,
        config=resolve_thinking_config(thinking),
    )
    return resp.text or ""


# 3. Streaming 呼び出し (TTFT 到達直後からチャンクを逐次 yield)
async def stream_text_progressive(prompt: str, thinking: str | int | None = 0) -> AsyncIterator[str]:
    stream = await client.aio.models.generate_content_stream(
        model=MODEL,
        contents=prompt,
        config=resolve_thinking_config(thinking),
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
