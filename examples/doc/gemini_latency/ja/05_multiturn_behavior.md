# 5. マルチターンチャットでの挙動とコンテキストキャッシュ

実運用の対話型AIアプリケーション（パソコンのトラブルシューティング窓口やテクニカルサポート等）では、単発プロンプトではなく数十ターンにわたる連続対話が行われる。さらに実際のサポート対話では、大半を占める「定型的な確認・手順案内ターン」の合間に、バッテリー持続時間やクラウド転送時間、3年間の修理vs買い替え総費用（TCO）といった「多段階の条件計算・推論が必要なターン」が混在する。

本章では、すべて **Streaming（`generate_content_stream`）に統一** したうえで、Google AI Studio（`google-genai` SDK / `gemini-3.8-flash`）における **50ターン連続PCサポートチャットベンチマーク**（`src/gemini_evaluation/benchmark_multiturn_chat.py` / `multiturn_chat_log.json`、全50ターン × 3構成 ＝ 計150実行）の実測データに基づき、以下の **(1) 単一モデル固定 Streaming 2構成** と **(2) 第4章の Adaptive Thinking Router 構成** における **初期応答時間（`TTFT`）** と **全体完了時間（`Total`）**、および設定不要で自動発動する **暗黙的コンテキストキャッシュ（Implicit Context Caching：`cached_content_token_count`）** の実効性を定量的に解明する。

1. **`(1)` 単一モデル固定 Streaming（`gemini-3.8-flash` `low` / `high`）**：
   - **`streaming_low`（`3.8-flash [low]` 固定）**：全50ターンを `thinking_level="low"` でストリーミング応答。
   - **`streaming_high`（`3.8-flash [high]` 固定）**：全50ターンを `thinking_level="high"` でストリーミング応答。
2. **`(2)` 第4章の Adaptive Thinking Router 構成（`adaptive_pat_a`：Pattern A `low → high`）**：
   - Stage 1（`3.8-flash [low]`）で 2フィールド統合 Pydantic スキーマ `{thinking: bool, response: str}` をストリーミング生成し、定型ターン（`thinking=false`：40ターン）はそのまま1回の API 呼び出しで即答完走、複雑計算ターン（`thinking=true`：5ターンに1回の計10ターン）は1文のブリッジメッセージを即時ストリーミングしつつ裏で Stage 2（`3.8-flash [high]`）を並列起動して深層推論回答を後続結合する構成。

```drawlib align=center code=fold width=100% file=ch5_multiturn_hero_ja.png caption="図5-1: 50ターン連続PCサポートチャット（Streaming統一）の評価アーキテクチャと3構成の初期応答（TTFT）・完了時間（Total）比較"
from drawlib.canvas import save, setup
from drawlib.icons import phosphor
from drawlib.lines import line
from drawlib.shapes import rectangle
from drawlib.styles import Styles
from drawlib.text import text

setup(width=156, height=82, dpi=150)

# Outer structural frame
rectangle((78, 41), width=152, height=78, style=Styles.MutedDashed.patch(shape_r=2.0))
text(
    (78, 76.0),
    "50ターン連続PCサポート対話（Streaming統一）：(1) 3.8-flash low/high vs (2) Adaptive Thinking Router",
    style=Styles.DarkBold.patch(text_size=11.2),
)

# Top pipeline band: 50-Turn Evaluation Loop
rectangle((78, 61.2), width=146, height=18.0, style=Styles.PrimaryNeutral.patch(shape_r=1.5))
text(
    (78, 67.6),
    "各ターンの評価パイプライン（定型手順 40ターン [80%] ＋ 多段階の数値計算 10ターン [20%: T5,10..50]・呼び出し順を毎ターン巡回）",
    style=Styles.DarkBold.patch(text_size=10.0),
)

loop_steps = [
    (22.0, 29.5, "1. 顧客シミュレータ", "gemini-3.8-flash (low)\n定型80% + 計算20% (平均103字)", Styles.WhiteFlat),
    (57.5, 31.5, "2. 蓄積履歴 + 新規質問", "history: list[Content]\n180 → 20,899 tok (37,531字)", Styles.WhiteFlat),
    (95.0, 34.0, "3. 暗黙キャッシュ自動発動", "Turn 8–9 で自動発動\nT41–50 平均 87.1%・最大 90.2%", Styles.SecondaryNeutral),
    (132.5, 31.0, "4. Streaming 3構成で計測", "初期応答 TTFT と完了 Total\nを全50ターンで統一記録", Styles.WhiteFlat),
]
for cx, w, st_top, st_bot, box_st in loop_steps:
    rectangle((cx, 58.4), width=w, height=10.8, style=box_st.patch(shape_r=1.2, line_width=0.8))
    text((cx, 61.2), st_top, style=Styles.DarkBold.patch(text_size=10.0))
    text((cx, 56.0), st_bot, style=Styles.Dark.patch(text_size=9.8))

line((36.8, 58.4), (41.7, 58.4), arrow_head="->", style=Styles.DarkBold)
line((73.3, 58.4), (78.0, 58.4), arrow_head="->", style=Styles.DarkBold)
line((112.0, 58.4), (117.0, 58.4), arrow_head="->", style=Styles.DarkBold)

# Left Column: (1) Single-Model Fixed Streaming (low vs high)
phosphor.Sliders((7.5, 48.0), width=3.2, style=Styles.DarkBold) if hasattr(phosphor, "Sliders") else phosphor.lightning((7.5, 48.0), width=3.2, style=Styles.DarkBold)
text(
    (10.5, 48.0),
    "(1) 単一モデル固定 Streaming：3.8-flash low vs 3.8-flash high",
    style=Styles.DarkBold.patch(text_size=10.4, halign="left"),
)

# Card 1A: streaming_low
rectangle((42.0, 36.8), width=72.0, height=16.0, style=Styles.Neutral.patch(shape_r=1.4))
text(
    (7.8, 42.2),
    "① streaming_low（gemini-3.8-flash [low] 固定）",
    style=Styles.DarkBold.patch(text_size=10.0, halign="left"),
)
text(
    (7.8, 38.4),
    "• 初期応答 TTFT：平均 2,310 ms（中央値 2,084 ms / 定型 2.30s・計算 2.34s）",
    style=Styles.Dark.patch(text_size=9.5, halign="left"),
)
text(
    (7.8, 34.8),
    "• 全体完了 Total：平均 6,589 ms（中央値 6,583 ms / 思考トークン 0 tok）",
    style=Styles.Dark.patch(text_size=9.5, halign="left"),
)
text(
    (7.8, 31.2),
    "• 課題：高速だが複雑計算10Tでも思考が走らず多段階検算が省略される",
    style=Styles.Dark.patch(text_size=9.5, halign="left"),
)

# Card 1B: streaming_high
rectangle((42.0, 19.6), width=72.0, height=15.6, style=Styles.Neutral.patch(shape_r=1.4))
text(
    (7.8, 24.8),
    "② streaming_high（gemini-3.8-flash [high] 固定）",
    style=Styles.DarkBold.patch(text_size=10.0, halign="left"),
)
text(
    (7.8, 21.0),
    "• 初期応答 TTFT：平均 21,173 ms（定型 16,958 ms / 計算 38,033 ms）",
    style=Styles.Dark.patch(text_size=9.5, halign="left"),
)
text(
    (7.8, 17.4),
    "• 全体完了 Total：平均 23,827 ms（定型 19,683 ms / 計算 40,404 ms）",
    style=Styles.Dark.patch(text_size=9.5, halign="left"),
)
text(
    (7.8, 13.8),
    "• 課題：定型40Tでも平均 1,534 tok 思考し初期応答まで約17秒フリーズ",
    style=Styles.Dark.patch(text_size=9.5, halign="left"),
)

# Vertical divider
line((80.0, 12.0), (80.0, 49.5), style=Styles.MutedDashed.patch(line_width=1.0))

# Right Column: (2) Chapter 4 Adaptive Thinking Router (Pattern A: low -> high)
phosphor.star((84.2, 48.0), width=3.2, style=Styles.DarkBold)
text(
    (87.2, 48.0),
    "(2) ★第4章の構成：Adaptive Thinking Router (Pattern A)",
    style=Styles.DarkBold.patch(text_size=10.2, halign="left"),
)

rectangle((116.5, 28.2), width=69.0, height=33.2, style=Styles.PrimaryFlat.patch(shape_r=1.6))
text(
    (84.2, 41.8),
    "③ adaptive_pat_a（Stage 1: low 判定 → Stage 2: high 並列）",
    style=Styles.WhiteBold.patch(text_size=9.8, halign="left"),
)
text(
    (84.2, 37.4),
    "• ルーティング適合率：50 / 50 (100%) 一致（定型40T=F, 計算10T=T）",
    style=Styles.WhiteBold.patch(text_size=9.5, halign="left"),
)
text(
    (84.2, 33.2),
    "• 初期応答 TTFT：平均 2,618 ms（中央値 2,420 ms / P95 3,841 ms）",
    style=Styles.White.patch(text_size=9.5, halign="left"),
)
text(
    (85.8, 29.4),
    "→ 定型40Tは 2,560 ms 即答、計算10Tも 2,851 ms でブリッジ表示",
    style=Styles.White.patch(text_size=9.5, halign="left"),
)
text(
    (84.2, 25.2),
    "• 全体完了 Total：平均 12,034 ms（中央値 4,990 ms）",
    style=Styles.White.patch(text_size=9.5, halign="left"),
)
text(
    (85.8, 21.4),
    "→ 定型40Tは 5,008 ms 完走、計算10Tは Stage 2 (40,142 ms)",
    style=Styles.White.patch(text_size=9.5, halign="left"),
)
text(
    (84.2, 16.8),
    "• Stage 1→2 キャッシュ共有：T50 でも 90.2% (18,890 tok) ヒット",
    style=Styles.WhiteBold.patch(text_size=9.5, halign="left"),
)

# Bottom architectural insight banner
rectangle((78.0, 6.2), width=146.0, height=6.0, style=Styles.SecondaryNeutral.patch(shape_r=1.2))
text(
    (78.0, 6.2),
    "結論：Adaptive Thinking (Pattern A) は high 固定比で TTFT を 87.6% 短縮 (21.2s→2.6s)・思考量を 61.7% 削減しつつ計算10Tの深い推論を両立する。",
    style=Styles.DarkBold.patch(text_size=9.4),
)

save()
```

---

## 5.1 マルチターン（50ターン連続）PCサポートチャットベンチマークの設計（Streaming統一）

### 1. `google-genai` におけるマルチターン履歴送信と Adaptive Thinking の結合

ステートレスな LLM API でマルチターン対話を実装する場合、アプリケーション側で過去の対話履歴 `history: list[types.Content]`（`role="user"` および `role="model"` の交互配列）を保持し、毎ターンのリクエスト時に過去の全履歴リストの末尾へ新規ユーザー発言を結合して `contents` へ渡す構造となる（`src/gemini_evaluation/llm_call.py` および `src/gemini_evaluation/adaptive_thinking.py`）。

```python
from google import genai
from google.genai import types

client = genai.Client(api_key=GEMINI_KEY)

# 過去の累積履歴 history: list[types.Content] の末尾に当ターンの新規質問を追加して送信
contents: list[types.Content] = [
    *history,
    types.Content(role="user", parts=[types.Part.from_text(text=user_prompt)]),
]

# (1) 単一モデル固定 Streaming (thinking_level="low" または "high")
response_stream = await client.aio.models.generate_content_stream(
    model="gemini-3.8-flash",
    contents=contents,
    config=types.GenerateContentConfig(
        system_instruction=AGENT_SYSTEM_INSTRUCTION,
        thinking_config=types.ThinkingConfig(thinking_level="low"),  # または "high"
        temperature=0.2,
    ),
)
```

本ベンチマーク（`src/gemini_evaluation/benchmark_multiturn_chat.py`）では、**「パソコンが突然動かなくなった顧客とテクニカルサポート窓口の段階的トラブルシューティング会話」** を模した50ターン連続シナリオにおいて、実運用と同じく **定型案内ターン（80%：40ターン）** と **多段階の数値計算・比較推論ターン（20%：5ターンに1回の計10ターン）** を織り交ぜて計測を実施した。

1. **顧客シミュレータ（User Simulator：`gemini-3.8-flash`, `thinking_level="low"`）**：
   Turn 1〜50 の段階的シナリオに沿って顧客質問（実測平均 **`103.4 文字`**）を生成する。
   - **定型確認・手順案内ターン（40ターン：`expected_thinking=False`）**：電源・ACアダプタ確認、30秒放電、BIOS確認、セーフモード起動、`sfc /scannow`、クリーンブート、BitLocker回復キー確認、梱包手順、返却後チェックなど、即座に手順を案内すべき40ターン。
   - **複雑計算・多段階推論ターン（10ターン：`expected_thinking=True`、`Turn 5, 10, 15, 20, 25, 30, 35, 40, 45, 50`）**：各10ターン区間に2回ずつ（5の倍数ターン）、具体的な数値条件を提示して正確な段階的計算を求める質問（例：Turn 5 の停電時バッテリー残量 `36Wh`・消費電力 `45W` での `18GB` 外付けSSD退避可否計算、Turn 25 の `32GB RAM` 環境でのページングファイル・休止状態 `hiberfil.sys` 占有容量試算、Turn 40 の自然故障無償修理 vs 落下物損時の自己負担額比較、Turn 50 の3年間クラウド＋外付けSSDバックアップ総費用と月間稼働率99.5%許容ダウンタイム計算など）を配置。
2. **Streaming 3構成の同一履歴・巡回計測（`rot = (turn - 1) % 3`）**：
   Turn 1（`180 prompt_tokens`）から Turn 50（`20,899 prompt_tokens`、履歴累計 **`37,531 文字`**）までの各ターンにおいて、同一の `history` に対して以下の3構成をすべて **Streaming（`generate_content_stream`）** で実行し、呼び出し順を毎ターン巡回した（次ターンへ引き継ぐ正準履歴には `streaming_low` の回答平均 `647.2 文字` を採用）。

| 比較構成（すべて Streaming） | Stage 1 / 単一構成 | Stage 2（`thinking=true` 時） | 初期応答 `TTFT` 平均（中央値 / P95） | 全体完了 `Total` 平均（中央値 / P95） | 平均思考トークン数 | 定型40T / 計算10T の挙動と特徴 |
| :--- | :--- | :--- | ---: | ---: | ---: | :--- |
| **`(1)` `streaming_low`** | `3.8-flash [low]` | —（単一呼び出し） | **`2,310 ms`** (`2,084` / `4,269 ms`) | **`6,589 ms`** (`6,583` / `8,397 ms`) | `0 tok` | 全ターン高速だが、計算10Tでも思考 `0 tok` となり多段階検算を行わない |
| **`(1)` `streaming_high`** | `3.8-flash [high]` | —（単一呼び出し） | `21,173 ms` (`22,012` / `41,657 ms`) | `23,827 ms` (`23,887` / `43,621 ms`) | `1,981 tok` | 計算10Tで深い推論（`3,772 tok`）を行うが、定型40Tでも `1,534 tok` 思考し初期応答に約17秒要する |
| **`(2)` ★`adaptive_pat_a`**<br>（第4章 Pattern A） | `3.8-flash [low]`<br>(`{thinking, response}`) | `3.8-flash [high]`<br>（並列起動・キャッシュ共有） | **`2,618 ms`** (`2,420` / **`3,841 ms`**) | **`12,034 ms`** (**`4,990`** / `43,215 ms`) | **`758 tok`**<br>(`-61.7%`) | **適合率 `50/50 (100%)`**：定型40Tは `2,560 / 5,008 ms` で即答、計算10Tは `2,851 ms` でブリッジ表示＋裏で `high` 推論（`40,142 ms`） |

---

## 5.2 入力トークン数の直線的増加と暗黙的コンテキストキャッシュ（Stage 1・Stage 2 間のキャッシュ共有）

50ターンの連続対話において、各ターン完了後に `(user, model)` の2メッセージを `history` に追加していくと、エージェントへの入力トークン数（`prompt_token_count`）は **1ターンあたり平均 `+423 tokens`** のペースで直線的に増加する（Turn 1 で `180 tokens` → Turn 8 で `2,710 tokens` → Turn 25 で `9,523 tokens` → Turn 50 で **`20,899 tokens`**）。

本検証における重要な発見は、**入力コンテキストが約 `2,710〜3,050 tokens` に達した Turn 8〜9 において、明示的なキャッシュ作成 API を一切呼び出していないにもかかわらず、Gemini 3.8 Flash の暗黙的コンテキストキャッシュ（Implicit Context Caching：`usage_metadata.cached_content_token_count`）が自動的に発動し、さらに `adaptive_pat_a` の複雑計算ターンでは Stage 1（`low`）と Stage 2（`high`）の間でも同一履歴プレフィックスの KV キャッシュがそのまま共有された** 点である。

```drawlib align=center code=fold width=100% file=ch5_token_cache_growth_ja.png caption="図5-2: 50ターン連続PCサポート対話における入力トークン数（prompt_tokens）の増加と暗黙的コンテキストキャッシュ（cached_tokens）のヒット推移"
from drawlib.canvas import save, setup
from drawlib.charts.line import LineChart
from drawlib.icons import phosphor
from drawlib.lines import line
from drawlib.shapes import rectangle
from drawlib.styles import Styles
from drawlib.text import text
from drawlib.utils import load_multiturn_turns

setup(width=156, height=86, dpi=150)

# Outer structural frame
rectangle((78.0, 43.0), width=152.0, height=82.0, style=Styles.MutedDashed.patch(shape_r=2.0))
text(
    (78.0, 80.0),
    "50ターン連続PCサポート対話における入力トークン増加と暗黙的コンテキストキャッシュの自動発動推移",
    style=Styles.DarkBold.patch(text_size=11.5),
)

# Load 50-turn token & implicit cache metrics dynamically from benchmark JSONL
turns = load_multiturn_turns()
categories = [
    f"T{t}" if t in {1, 5, 10, 15, 20, 25, 30, 35, 40, 45, 50} else ""
    for t in range(1, 51)
]
prompt_vals = [float(t["variants"]["streaming_low"]["prompt_tokens"]) for t in turns]
cached_vals = [float(t["variants"]["adaptive_pat_a"]["cached_tokens"]) for t in turns]
uncached_vals = [max(p - c, 0.0) for p, c in zip(prompt_vals, cached_vals)]

# Left Card: LineChart container
rectangle(
    (50.5, 39.5),
    width=93.0,
    height=71.0,
    style=Styles.WhiteFlat.patch(shape_r=1.6, line_width=0.9),
)

# Legend backdrop band at top of left card
rectangle((50.5, 65.2), width=88.0, height=14.8, style=Styles.Neutral.patch(shape_r=1.2))

chart = LineChart(
    axis_line_style=Styles.Dark,
    categories=categories,
    width=84.0,
    height=42.5,
    smooth=False,
    show_points=False,
    axis_text_style=Styles.Dark.patch(text_size=10.0),
    grid_style=Styles.MutedDashed,
)
chart.add_series(
    "総入力トークン数 (prompt_tokens: 180 → 20,899 tok)",
    prompt_vals,
    style=Styles.PrimaryFlat,
    line_width=2.6,
    point_shape="none",
)
chart.add_series(
    "暗黙キャッシュヒット数 (cached_tokens: 最大 18,507〜18,890 tok)",
    cached_vals,
    style=Styles.SuccessFlat,
    line_width=2.4,
    point_shape="none",
)
chart.add_series(
    "実質未キャッシュ差分 (prompt - cached: ~2,400 tok で一定推移)",
    uncached_vals,
    style=Styles.SecondaryFlat,
    line_width=2.0,
    line_style="dashed",
    point_shape="none",
)
chart.configure_y_axis(
    min_value=0.0,
    max_value=24000.0,
    tick_step=6000.0,
    format="{:,.0f}",
)
chart.draw(xy=(8.5, 9.5))
chart.draw_legend(
    xy=(11.5, 70.0),
    text_style=Styles.DarkBold.patch(text_size=9.6),
    orientation="vertical",
    item_gap=1.3,
)

# Axis labels
text((9.5, 54.0), "トークン数 (tok)", style=Styles.DarkBold.patch(text_size=10.0, halign="left"))
text((51.5, 6.2), "対話ターン番号 (Turn 1 〜 Turn 50)", style=Styles.DarkBold.patch(text_size=10.0))

# Callout annotation inside chart pointing to Turn 8-9 cache activation
rectangle((44.5, 38.0), width=41.0, height=8.0, style=Styles.Neutral.patch(shape_r=1.0))
text(
    (44.5, 39.8),
    "Turn 8–9 (~2,710 tok 突破で自動発動)",
    style=Styles.DarkBold.patch(text_size=9.8),
)
text(
    (44.5, 36.2),
    "Stage 1/2 とも T50 で 88.0〜90.2% ヒット",
    style=Styles.Dark.patch(text_size=9.8),
)
line((36.0, 34.0), (24.0, 15.0), arrow_head="->", style=Styles.DarkBold.patch(line_width=1.6))

# Right Panel: Neutral Summary Card Panel
rectangle((125.5, 39.5), width=51.0, height=71.0, style=Styles.Neutral.patch(shape_r=1.6))
phosphor.chart_line_up((103.5, 70.8), width=3.4, style=Styles.DarkBold)
text(
    (106.8, 70.8),
    "トークン増加と暗黙キャッシュの要点",
    style=Styles.DarkBold.patch(text_size=10.5, halign="left"),
)

summary_cards = [
    (
        59.2,
        "1. 直線的な履歴増加 (+423 tok/T)",
        "質問(平均103字)＋回答(平均647字)の蓄積で\nTurn 1 (180) → Turn 50 (20,899) へ増加",
    ),
    (
        43.8,
        "2. Turn 8–9 で暗黙キャッシュ自動発動",
        "API 設定なしに Turn 8 (2,710 tok) から\nKV キャッシュが自動有効化され連続ヒット",
    ),
    (
        28.4,
        "3. Stage 1→2 でも同一キャッシュを共有",
        "計算ターンで並列起動する Stage 2 (high)\nも T50 で 18,890 tok (90.2%) キャッシュヒット",
    ),
    (
        13.0,
        "4. 未キャッシュ差分は約2,400 tokで一定",
        "新規 Prefill 計算対象が ~2,400 tok の一定\n帯域に抑えられ 20k tok でも初期応答 2秒台",
    ),
]

for cy, hdr, body in summary_cards:
    rectangle((125.5, cy), width=47.4, height=13.4, style=Styles.WhiteFlat.patch(shape_r=1.2, line_width=0.7))
    text((103.2, cy + 3.6), hdr, style=Styles.DarkBold.patch(text_size=9.8, halign="left"))
    text((103.2, cy - 2.0), body, style=Styles.Dark.patch(text_size=9.6, halign="left"))

save()
```

### 図5-2 から導かれる暗黙的コンテキストキャッシュと Adaptive Router の親和性

1. **Turn 8〜9 におけるゼロ設定発動と連続拡張**：
   Turn 1〜7（`180〜2,369 prompt_tokens`）では `cached_content_token_count = 0` であったが、入力が `2,710 tokens` に達した **Turn 8**（`adaptive_pat_a` で `633 cached_tokens`）および **Turn 9**（`3,050 tokens`、`streaming_low` で `728 cached_tokens`・`adaptive_pat_a` で `956 cached_tokens`）においてバックエンドの KV キャッシュが自動生成された。以降 Turn 50 まで毎ターンキャッシュ境界が前進し、**Turn 41〜50 の平均キャッシュヒット率は `87.1%〜87.7%`（Turn 50 単体では `88.0%〜90.2%`）** に達している。
2. **Adaptive Thinking Router（Pattern A）における Stage 1 → Stage 2 キャッシュ共有効果**：
   `adaptive_pat_a` では、Stage 2（`thinking_level="high"`）の `system_instruction` をチャット本体の `AGENT_SYSTEM_INSTRUCTION` と完全一致させ、Stage 1 のルーティング指示は末尾のユーザーメッセージ側に付与するプレフィックス不変設計（Prefix-Preserving Prompting）を採用している。その結果、複雑計算ターン（`Turn 10, 20, 25, 30, 40, 50`）で Stage 2 が起動した際にも、Stage 1 とまったく同じ過去履歴 KV キャッシュ（Turn 50 の Stage 1 で `18,507 tok`、**Stage 2 で `18,890 tok [90.2%]`**）が即座にヒットし、Stage 2 起動時の Prefill 再計算コストが最小化されている。

---

## 5.3 全50ターンにわたる初期応答（TTFT）と完了時間（Total）の推移比較

グラフの視認性を高め、`(1) 3.8-flash low / high` と `(2) Adaptive Thinking Router (Pattern A)` の3構成の違いを明確に比較するため、図5-3では **左パネルに「初期応答時間（`TTFT`）の50ターン推移」** を、**右パネルに「全体完了時間（`Total`）の50ターン推移」** を分けてプロットした。

```drawlib align=center code=fold width=100% file=ch5_latency_evolution_2panel_ja.png caption="図5-3: Turn 1〜50 における3構成のレイテンシ推移（左パネル：初期応答 TTFT 比較、右パネル：全体完了 Total 比較）"
from drawlib.canvas import save, setup
from drawlib.charts.line import LineChart
from drawlib.lines import line
from drawlib.shapes import circle, rectangle
from drawlib.styles import Styles
from drawlib.text import text
from drawlib.utils import load_multiturn_turns

setup(width=156, height=90, dpi=150)

# Outer structural frame
rectangle((78.0, 45.0), width=152.0, height=86.0, style=Styles.MutedDashed.patch(shape_r=2.0))
text(
    (78.0, 84.0),
    "Turn 1〜50 における3構成（Streaming統一）の初期応答 TTFT (左) と全体完了 Total (右) の推移比較",
    style=Styles.DarkBold.patch(text_size=11.2),
)

turns = load_multiturn_turns()
labeled_turns = {1, 10, 20, 30, 40, 50}
categories = [f"T{t['turn']}" if int(t["turn"]) in labeled_turns else "" for t in turns]

low_ttft = [float(t["variants"]["streaming_low"]["ttft_ms"]) for t in turns]
high_ttft = [float(t["variants"]["streaming_high"]["ttft_ms"]) for t in turns]
adap_ttft = [float(t["variants"]["adaptive_pat_a"]["ttft_ms"]) for t in turns]

low_total = [float(t["variants"]["streaming_low"]["total_ms"]) for t in turns]
high_total = [float(t["variants"]["streaming_high"]["total_ms"]) for t in turns]
adap_total = [float(t["variants"]["adaptive_pat_a"]["total_ms"]) for t in turns]

# =========================================================================
# Left Panel: Initial Response (TTFT) across 50 Turns
# =========================================================================
rectangle((42.5, 45.5), width=71.0, height=69.0, style=Styles.WhiteFlat.patch(shape_r=1.5, line_width=0.8))
rectangle((42.5, 73.2), width=67.0, height=11.6, style=Styles.Neutral.patch(shape_r=1.1))
text(
    (42.5, 76.6),
    "左：初期応答 TTFT（Adaptive 2.62s・low 2.31s vs high 21.2s）",
    style=Styles.DarkBold.patch(text_size=9.5),
)

# Legend for Left Panel (3 items cleanly arranged)
line((10.0, 72.8), (13.6, 72.8), style=Styles.PrimaryBold.patch(line_width=2.6))
circle((11.8, 72.8), radius=0.6, style=Styles.PrimaryFlat)
text((14.4, 72.8), "★adaptive_pat_a (平均 2,618ms / 中央値 2,420ms)", style=Styles.DarkBold.patch(text_size=9.5, halign="left"))

line((10.0, 69.4), (13.6, 69.4), style=Styles.TealBold.patch(line_width=2.0))
text((14.4, 69.4), "streaming_low (2,310ms)", style=Styles.Dark.patch(text_size=9.5, halign="left"))

line((44.5, 69.4), (48.1, 69.4), style=Styles.DangerBold.patch(line_width=2.0))
text((48.9, 69.4), "streaming_high (21,173ms)", style=Styles.Dark.patch(text_size=9.5, halign="left"))

chart_left = LineChart(
    axis_line_style=Styles.Dark,
    axis_text_style=Styles.Dark.patch(text_size=9.8),
    grid_style=Styles.MutedDashed,
    categories=categories,
    width=59.0,
    height=42.0,
    show_points=True,
    point_shape="circle",
    point_size=0.42,
)
chart_left.configure_x_axis(show_grid=False)
chart_left.configure_y_axis(
    min_value=0,
    max_value=60000,
    tick_step=15000,
    format="{:,.0f}",
)
chart_left.add_series(
    name="streaming_high TTFT",
    values=[min(v, 59500.0) for v in high_ttft],
    style=Styles.DangerFlat,
    line_width=1.8,
    point_size=0.38,
)
chart_left.add_series(
    name="streaming_low TTFT",
    values=low_ttft,
    style=Styles.TealFlat,
    line_width=2.0,
    point_size=0.38,
)
chart_left.add_series(
    name="adaptive_pat_a TTFT",
    values=adap_ttft,
    style=Styles.PrimaryFlat,
    line_width=2.5,
    point_size=0.48,
)
chart_left.draw(xy=(14.5, 19.5))
text((10.0, 63.8), "初期応答 TTFT (ms)", style=Styles.DarkBold.patch(text_size=9.8, halign="left"))
text((44.0, 14.2), "ターン番号（Adaptive と low は全50ターンで ~2〜3秒帯を維持）", style=Styles.DarkBold.patch(text_size=9.5))

# =========================================================================
# Right Panel: Stream Completion (Total) across 50 Turns
# =========================================================================
rectangle((115.5, 45.5), width=71.0, height=69.0, style=Styles.WhiteFlat.patch(shape_r=1.5, line_width=0.8))
rectangle((115.5, 73.2), width=67.0, height=11.6, style=Styles.Neutral.patch(shape_r=1.1))
text(
    (115.5, 76.6),
    "右：全体完了 Total（定型40Tは 5.0s 即答・計算10Tのみ high 推論）",
    style=Styles.DarkBold.patch(text_size=9.5),
)

# Legend for Right Panel
line((83.0, 72.8), (86.6, 72.8), style=Styles.PrimaryBold.patch(line_width=2.6))
circle((84.8, 72.8), radius=0.6, style=Styles.PrimaryFlat)
text((87.4, 72.8), "★adaptive_pat_a (中央値 4,990ms / 平均 12,034ms)", style=Styles.DarkBold.patch(text_size=9.5, halign="left"))

line((83.0, 69.4), (86.6, 69.4), style=Styles.TealBold.patch(line_width=2.0))
text((87.4, 69.4), "streaming_low (6,589ms)", style=Styles.Dark.patch(text_size=9.5, halign="left"))

line((117.5, 69.4), (121.1, 69.4), style=Styles.DangerBold.patch(line_width=2.0))
text((121.9, 69.4), "streaming_high (23,827ms)", style=Styles.Dark.patch(text_size=9.5, halign="left"))

rx0, ry0, rpw, rph = 87.5, 19.5, 59.0, 42.0

chart_right = LineChart(
    axis_line_style=Styles.Dark,
    axis_text_style=Styles.Dark.patch(text_size=9.8),
    grid_style=Styles.MutedDashed,
    categories=categories,
    width=rpw,
    height=rph,
    show_points=True,
    point_shape="circle",
    point_size=0.42,
)
chart_right.configure_x_axis(show_grid=False)
chart_right.configure_y_axis(
    min_value=0,
    max_value=60000,
    tick_step=15000,
    format="{:,.0f}",
)
chart_right.add_series(
    name="streaming_high Total",
    values=[min(v, 59500.0) for v in high_total],
    style=Styles.DangerFlat,
    line_width=1.8,
    point_size=0.38,
)
chart_right.add_series(
    name="streaming_low Total",
    values=low_total,
    style=Styles.TealFlat,
    line_width=2.0,
    point_size=0.38,
)
chart_right.add_series(
    name="adaptive_pat_a Total",
    values=adap_total,
    style=Styles.PrimaryFlat,
    line_width=2.5,
    point_size=0.48,
)
chart_right.draw(xy=(rx0, ry0))
text((83.0, 63.8), "全体完了 Total (ms)", style=Styles.DarkBold.patch(text_size=9.8, halign="left"))
text((117.0, 14.2), "ターン番号（T5,10..50 の計算10ターンのみ Stage 2 high が稼働）", style=Styles.DarkBold.patch(text_size=9.5))

# Bottom callout bar
rectangle((78.0, 6.2), width=146.0, height=6.0, style=Styles.PrimaryNeutral.patch(shape_r=1.2))
text(
    (78.0, 6.2),
    "要点：adaptive_pat_a (青実線) は左パネル(TTFT)で常に ~2.6s の下限を張り付き、右パネル(Total)では計算10Tのみ選択的に深い推論を実行する。",
    style=Styles.DarkBold.patch(text_size=9.5),
)

save()
```

### 図5-3 の左右比較から読み取れる重要事実

1. **左パネル（初期応答 `TTFT`）：`adaptive_pat_a` と `streaming_low` は全50ターンで `2〜3秒台` に完全収束**：
   - 赤線（`streaming_high`）は定型確認ターンでも内部思考（平均 `1,534 tok`）のため平均 **`16,958 ms`**、複雑計算ターンでは平均 **`38,033 ms`**（全50ターン平均 **`21,173 ms`**）まで1文字目が出力されない。
   - 対して青線（**`adaptive_pat_a`**、全50ターン平均 **`2,618 ms`**、中央値 **`2,420 ms`**、P95 **`3,841 ms`**）は、緑線（**`streaming_low`**、平均 **`2,310 ms`**、中央値 **`2,084 ms`**）とほぼ完全に重なってグラフ最下部の `2〜3秒帯` をフラットに推移しており、複雑計算ターン（`T5, 10, ..., 50`）においても `2,851 ms` で1文目のブリッジメッセージを即座にストリーミング開始できている。
2. **右パネル（全体完了 `Total`）：定型40ターンの即答完走（`5.0秒`）と計算10ターンの選択的深層推論（`40.1秒`）**：
   - 定型案内40ターン（`expected_thinking=False`）において、`adaptive_pat_a` は Stage 1（`low`）の1回呼び出しのみで完結し、簡潔な構造化応答によって平均 **`5,008 ms`（中央値 `4,695 ms`）** で完了する（`streaming_low` の平均 `6,411 ms` よりも高速）。
   - そして複雑計算10ターン（`Turn 5, 10, 15, 20, 25, 30, 35, 40, 45, 50`）においてのみ、`adaptive_pat_a` の青線が選択的に立ち上がり、Stage 2（`high`、平均 `3,671 思考トークン`）による厳密な多段階計算を実行して平均 **`40,142 ms`**（`streaming_high` の平均 `40,404 ms` と同等）で完了する。結果として、50ターン全体の中央値完了時間は **`4,990 ms`**（`streaming_high` 中央値 `23,887 ms` 比で **`-79.1%` 短縮**）を達成している。

---

## 5.4 思考トークン分布の二極化と Turn 1・25・50 のストリーム軌跡比較

3構成における内部思考トークン数（`thoughts_token_count`）と完了時間（`Total`）の関係、および会話序盤（**Turn 1**：定型）・中盤（**Turn 25**：複雑計算）・終盤（**Turn 50**：複雑計算）におけるチャンク送出軌跡の違いを同時検証するため、図5-4の左パネルに全150実行（50ターン × 3構成）の **`thoughts_tokens` 対 `total_ms` 散布図** を、右パネルに `load_multiturn_trajectory()` から抽出した **Turn 1・Turn 25・Turn 50 のストリーム軌跡オーバーレイ** を示す。

```drawlib align=center code=fold width=100% file=ch5_thinking_scatter_and_trajectories_ja.png caption="図5-4: 3構成の思考トークン数と完了時間の散布図（左）および Turn 1・25・50 におけるストリーム軌跡比較（右）"
from drawlib.canvas import save, setup
from drawlib.charts.scatter import ScatterChart
from drawlib.lines import line, lines
from drawlib.shapes import circle, rectangle
from drawlib.styles import Styles
from drawlib.text import text
from drawlib.utils import load_multiturn_trajectory, load_multiturn_turns

setup(width=156, height=94, dpi=150)

# Outer structural frame
rectangle((78.0, 47.0), width=152.0, height=90.0, style=Styles.MutedDashed.patch(shape_r=2.0))
text(
    (78.0, 88.2),
    "思考トークン数 × 完了時間 散布図 (左) と Turn 1・25・50 ストリーム軌跡比較 (右)",
    style=Styles.DarkBold.patch(text_size=11.5),
)

# =========================================================================
# Left Panel: Scatter plot of thoughts_tokens vs total_ms across 3 Streaming variants
# =========================================================================
rectangle((42.5, 47.5), width=71.0, height=73.0, style=Styles.WhiteFlat.patch(shape_r=1.5, line_width=0.8))
rectangle((42.5, 77.2), width=67.0, height=11.2, style=Styles.Neutral.patch(shape_r=1.1))
text(
    (42.5, 80.4),
    "左：思考トークン vs Total（定型40Tと計算10Tへ二極分離）",
    style=Styles.DarkBold.patch(text_size=9.5),
)

pts_low: list[tuple[float, float]] = []
pts_high: list[tuple[float, float]] = []
pts_adap: list[tuple[float, float]] = []

for t_rec in load_multiturn_turns():
    v = t_rec["variants"]
    pts_low.append((float(v["streaming_low"]["thoughts_tokens"]), min(float(v["streaming_low"]["total_ms"]), 59000.0)))
    pts_high.append((min(float(v["streaming_high"]["thoughts_tokens"]), 5900.0), min(float(v["streaming_high"]["total_ms"]), 59000.0)))
    pts_adap.append((min(float(v["adaptive_pat_a"]["thoughts_tokens"]), 5900.0), min(float(v["adaptive_pat_a"]["total_ms"]), 59000.0)))

# Compact legend inside Left Panel header
circle((10.5, 76.2), radius=0.65, style=Styles.PrimaryFlat)
text((12.0, 76.2), "★adaptive_pat_a (50回)", style=Styles.DarkBold.patch(text_size=9.5, halign="left"))
circle((44.5, 76.2), radius=0.65, style=Styles.TealFlat)
text((46.0, 76.2), "streaming_low (50回)", style=Styles.DarkBold.patch(text_size=9.5, halign="left"))
circle((10.5, 73.0), radius=0.65, style=Styles.DangerFlat)
text((12.0, 73.0), "streaming_high (50回：全ターンで 1,000〜5,500 tok に分散)", style=Styles.Dark.patch(text_size=9.3, halign="left"))

scatter = ScatterChart(
    axis_line_style=Styles.Dark,
    axis_text_style=Styles.Dark.patch(text_size=9.8),
    grid_style=Styles.MutedDashed,
    width=63.0,
    height=46.0,
    default_radius=0.85,
)
scatter.configure_x_axis(
    label="内部思考トークン数 (thoughts_token_count [tok])",
    min_value=0,
    max_value=6000,
    tick_step=1500,
    format="{:,.0f}",
)
scatter.configure_y_axis(
    min_value=0,
    max_value=60000,
    tick_step=15000,
    format="{:,.0f}",
)
scatter.add_series("streaming_high", pts_high, style=Styles.DangerFlat, shape="rhombus", radius=0.85)
scatter.add_series("streaming_low", pts_low, style=Styles.TealFlat, shape="triangle", radius=0.85)
scatter.add_series("adaptive_pat_a", pts_adap, style=Styles.PrimaryFlat, shape="circle", radius=0.9)
scatter.draw(xy=(11.5, 18.0))
text((10.0, 66.8), "全体完了 Total (ms)", style=Styles.DarkBold.patch(text_size=9.6, halign="left"))

# =========================================================================
# Right Panel: 3-Turn Trajectory Overlay (Turn 1, Turn 25, Turn 50)
# =========================================================================
rectangle((115.5, 47.5), width=71.0, height=73.0, style=Styles.WhiteFlat.patch(shape_r=1.5, line_width=0.8))
rectangle((115.5, 77.2), width=67.0, height=11.2, style=Styles.Neutral.patch(shape_r=1.1))
text(
    (115.5, 80.4),
    "右：Turn 1(定型)・Turn 25(計算)・Turn 50(計算) の文字送出軌跡",
    style=Styles.DarkBold.patch(text_size=9.5),
)

# Legend for Right Panel trajectories
line((83.5, 76.2), (87.5, 76.2), style=Styles.PrimaryBold.patch(line_width=2.5))
text((88.5, 76.2), "★adaptive_pat_a", style=Styles.DarkBold.patch(text_size=9.5, halign="left"))

line((114.5, 76.2), (118.5, 76.2), style=Styles.TealBold.patch(line_width=2.1))
text((119.5, 76.2), "streaming_low", style=Styles.DarkBold.patch(text_size=9.5, halign="left"))

line((83.5, 73.0), (87.5, 73.0), style=Styles.DangerDashed.patch(line_width=2.0))
text((88.5, 73.0), "streaming_high (思考完了まで 19.6〜36.5秒停止)", style=Styles.Dark.patch(text_size=9.3, halign="left"))

sub_panels = [
    (1, 54.0, "Turn 1 (180 tok / 定型)：adap 1.73/3.59s vs low 2.65/4.98s vs high 23.6s"),
    (25, 35.0, "Turn 25 (9,523 tok / 計算)：adap TTFT 2.08s→Stage2 35.3s vs high 19.6s"),
    (50, 16.0, "Turn 50 (20,899 tok / 計算)：adap TTFT 3.75s→Stage2 38.3s vs high 36.5s"),
]

max_t = 42000.0
max_c = 900.0
pw = 55.0
ph = 12.2
px0 = 88.5

for t_num, py0, sub_title in sub_panels:
    text((px0 + pw / 2, py0 + ph + 2.0), sub_title, style=Styles.DarkBold.patch(text_size=9.4))
    rectangle((px0 + pw / 2, py0 + ph / 2), width=pw, height=ph, style=Styles.Neutral.patch(line_width=0.5, shape_r=0))

    def to_x(ms: float) -> float:
        return px0 + min(max(ms, 0.0), max_t) / max_t * pw

    def to_y(ch: float, base_y: float = py0) -> float:
        return base_y + min(max(ch, 0.0), max_c) / max_c * ph

    for xt in (0, 10000, 20000, 30000, 40000):
        tx = to_x(float(xt))
        line((tx, py0), (tx, py0 + ph), style=Styles.MutedDashed.patch(line_width=0.5))
        if t_num == 50:
            text((tx, py0 - 2.2), f"{xt // 1000}s", style=Styles.Dark.patch(text_size=9.6))

    for yt in (0, 450, 900):
        ty = to_y(float(yt))
        line((px0, ty), (px0 + pw, ty), style=Styles.MutedDashed.patch(line_width=0.5))
        text((px0 - 1.2, ty), f"{yt}", style=Styles.Dark.patch(text_size=9.6, halign="right"))

    line((px0, py0), (px0 + pw, py0), style=Styles.Dark.patch(line_width=1.0))
    line((px0, py0), (px0, py0 + ph), style=Styles.Dark.patch(line_width=1.0))

    for v_key, st_line in (
        ("streaming_high", Styles.DangerDashed.patch(line_width=1.9)),
        ("streaming_low", Styles.TealBold.patch(line_width=2.0)),
        ("adaptive_pat_a", Styles.PrimaryBold.patch(line_width=2.5)),
    ):
        tr = load_multiturn_trajectory(t_num, v_key)
        gem_pts = tr["timeline_series"].get("gemini", [])
        if len(gem_pts) >= 2:
            coords = [(to_x(float(p["t_ms"])), to_y(float(p["chars"]))) for p in gem_pts]
            lines(coords, style=st_line)

text((px0 + pw / 2, 11.2), "経過時間 (秒: 0〜42s) — Y軸: 累積出力文字数 (0〜900字)", style=Styles.DarkBold.patch(text_size=9.8))

# Bottom callout bar
rectangle((78.0, 5.8), width=146.0, height=5.8, style=Styles.SecondaryNeutral.patch(shape_r=1.2))
text(
    (78.0, 5.8),
    "結論：Turn 25・50 の複雑計算ターンでも adaptive_pat_a (青実線) は 2.1〜3.8秒でブリッジを即答し、裏で Stage 2 (high) の深層回答を結合する。",
    style=Styles.DarkBold.patch(text_size=9.8),
)

save()
```

### 図5-4 から導かれる2つの定量的結論

1. **左パネル：`adaptive_pat_a` による「定型40ターンのゼロ思考クラスタ」と「計算10ターンの深層推論クラスタ」への完全二極化**：
   - `streaming_high`（赤ひし形）は定型ターンを含め全50ターンで `1,000〜5,500 tokens` の思考が発生し、完了時間が `10〜60秒` に広く分散している。
   - 一方 `adaptive_pat_a`（青丸）は、左下の **「定型40ターン群（思考 `~0〜30 tok`・完了平均 `5,008 ms`）」** と右上の **「複雑計算10ターン群（思考平均 `3,671 tok`・完了平均 `40,142 ms`）」** の2つのクラスタへ綺麗に二極分離しており、不要な思考コストを **`61.7%` 削減** している。
2. **右パネル：Turn 1・Turn 25・Turn 50 を通じた2段階ストリーム軌跡の比較**：
   - **Turn 1（`180 tok`・定型起動相談・`expected_thinking=False`）**：`adaptive_pat_a`（青実線）は **`1,726 ms`** でストリームを開始して **`3,592 ms`** で完走し、`streaming_low`（`2,652 / 4,984 ms`）と同等以上の速さで即答している（一方 `streaming_high` は `2,505 思考トークン` のため **`23,636 ms`** まで無応答）。
   - **Turn 25（`9,523 tok`・キャッシュ `74.1%`・`32GB RAM` 環境でのページング/休止ファイル容量計算・`expected_thinking=True`）**：`adaptive_pat_a`（青実線）は **`2,075 ms`** で Stage 1 の1文ブリッジを送出して体感フリーズを解消し、同時に並列起動した Stage 2（`high`、キャッシュ **`7,521 tok [77.1%]` ヒット**、`2,916 思考トークン`）の計算結果を後続ストリームとして滑らかに結合している。
   - **Turn 50（`20,899 tok`・キャッシュ `88.0%〜90.2%`・3年間バックアップ総費用＆稼働率99.5%計算・`expected_thinking=True`）**：入力が2万トークンを超えた最終ターンでも、`adaptive_pat_a` は **`3,753 ms`** で初回チャンクを送出し（`streaming_high` の `36,492 ms` 比で **`-32.7秒 [-89.7%]` 先行**）、Stage 2 でも暗黙キャッシュが **`18,890 tok [90.2%]`** ヒットすることで `streaming_high`（`38,857 ms`）と同等の **`38,274 ms`** で厳密な計算回答を完走している。

---

## 5.5 区間別・ターン種別パフォーマンス集計表とマルチターン本番設計ガイドライン

### 1. ターン種別（定型40ターン vs 複雑計算10ターン）および10ターン区間別の包括的統計表

全50ターンを「定型案内ターン（40ターン）」「複雑計算ターン（10ターン：`T5, 10, ..., 50`）」および10ターンごとの5コホート（`Turns 1–10` 〜 `Turns 41–50`）で集計したベンチマーク結果を下表に示す。

| 集計区分（各コホートに定型8T＋計算2T） | 平均入力 (`prompt`) /<br>キャッシュ (`ヒット率`) | `(1)` `streaming_low`<br>初期応答 `TTFT` / 完了 `Total` [思考] | `(1)` `streaming_high`<br>初期応答 `TTFT` / 完了 `Total` [思考] | `(2)` ★`adaptive_pat_a` (Pattern A)<br>初期応答 `TTFT` / 完了 `Total` [思考] | `adaptive` vs `high`<br>TTFT 短縮 / Total 短縮 |
| :--- | ---: | ---: | ---: | ---: | ---: |
| **Turns 1–10**<br>(電源・放電・T5停電退避・T10復旧時間計算) | `1,796 tok` (`180〜3,438`)<br>Cache: `179〜287 tok` (`10〜15%`) | **`1,854`** / `5,583 ms`<br>[`0 tok`] | `23,553` / `25,329 ms`<br>[`2,386 tok`] | **`2,121`** / **`9,729 ms`** (中央値 `4,332`)<br>[`715 tok` / 適合 `10/10`] | **`-21,432 ms` (`-91.0%`)**<br>Total: `-61.6%` |
| **Turns 11–20**<br>(ドライバ・T15転送・T20再構築時間計算) | `5,533 tok` (`3,893〜7,334`)<br>Cache: `3,151〜3,383 tok` (`57〜60%`) | **`2,372`** / `6,396 ms`<br>[`0 tok`] | `29,886` / `32,175 ms`<br>[`2,846 tok`] | **`2,431`** / **`14,142 ms`** (中央値 `4,953`)<br>[`949 tok` / 適合 `10/10`] | **`-27,455 ms` (`-91.9%`)**<br>Total: `-56.0%` |
| **Turns 21–30**<br>(復元・T25仮想メモリ・T30帯域計算) | `9,759 tok` (`7,800〜11,710`)<br>Cache: `7,321〜7,530 tok` (`75〜76%`) | **`3,143`** / `6,880 ms`<br>[`0 tok`] | `21,374` / `23,842 ms`<br>[`1,965 tok`] | **`2,926`** / **`11,670 ms`** (中央値 `6,104`)<br>[`652 tok` / 適合 `10/10`] | **`-18,448 ms` (`-86.3%`)**<br>Total: `-51.1%` |
| **Turns 31–40**<br>(暗号化・T35読取・T40保証自己負担計算) | `14,201 tok` (`12,293〜16,156`)<br>Cache: `11,752〜11,947 tok` (`83〜84%`) | **`2,212`** / `6,737 ms`<br>[`0 tok`] | `14,686` / `17,870 ms`<br>[`1,237 tok`] | **`2,957`** / **`12,319 ms`** (中央値 `6,530`)<br>[`716 tok` / 適合 `10/10`] | **`-11,729 ms` (`-79.9%`)**<br>Total: `-31.1%` |
| **Turns 41–50**<br>(修理・T45 3年TCO・T50保守費用計算) | `18,757 tok` (`16,661〜20,899`)<br>Cache: `16,337〜16,528 tok` (**`87〜88%`**) | **`1,970`** / `7,348 ms`<br>[`0 tok`] | `16,365` / `19,921 ms`<br>[`1,473 tok`] | **`2,655`** / **`12,312 ms`** (中央値 `6,242`)<br>[`757 tok` / 適合 `10/10`] | **`-13,710 ms` (`-83.8%`)**<br>Total: `-38.2%` |
| **定型案内 40ターン平均**<br>(`expected_thinking=False`) | `9,676 tok`<br>(1回呼び出し完結) | **`2,304`** / `6,411 ms`<br>(中央値 `2,060` / `6,497`) [`0`] | `16,958` / `19,683 ms`<br>(中央値 `20,701` / `22,721`) [`1,534`] | **`2,560`** / **`5,008 ms`**<br>(中央値 `2,352` / **`4,695`**) [`30`] | **`-14,398 ms` (`-84.9%`)**<br>Total: **`-74.6%`** |
| **複雑計算 10ターン平均**<br>(`expected_thinking=True`: `T5..50`) | `11,341 tok`<br>(Stage 1 + Stage 2 並列) | **`2,336`** / `7,302 ms`<br>(中央値 `2,310` / `7,370`) [`0`] | `38,033` / `40,404 ms`<br>(中央値 `32,083` / `34,257`) [`3,772`] | **`2,851`** / **`40,142 ms`**<br>(中央値 `2,618` / `38,900`) [`3,671`] | **`-35,182 ms` (`-92.5%`)**<br>Total: `-0.6%` (同等推論) |
| **全50ターン総合平均**<br>(中央値 / P95) | **`10,009 tok`** (`180〜20,899`)<br>Cache: **`77.4%〜78.5%`** (最大**`90.2%`**) | **`2,310`** / **`6,589 ms`**<br>(中央値 `2,084` / `6,583`) [`0`] | **`21,173`** / **`23,827 ms`**<br>(中央値 `22,012` / `23,887`) [`1,981`] | **`2,618`** / **`12,034 ms`**<br>(中央値 `2,420` / **`4,990`**) [**`758`**] | **`-18,555 ms` (`-87.6%`)**<br>Total: **`-49.5%`** (中央値 **`-79.1%`**) |

### 2. マルチターンチャット本番設計の3大ベストプラクティス

1. **プレフィックス不変性（Prefix Immutability）の厳守と Stage 1・Stage 2 キャッシュ共有**：
   - Gemini 3.8 Flash の暗黙的コンテキストキャッシュは、`system_instruction` と過去の `history: list[types.Content]` の **先頭からのトークン系列が完全一致（Prefix Match）** している場合に自動で KV キャッシュを再利用する。
   - **推奨パターン**：`system_instruction` と過去ターンの `history` は完全な **追記専用（Append-Only）** として不変に保ち、Adaptive Thinking Router の Stage 1 と Stage 2 でも同一の `system_instruction` を共有する（Stage 1 固有の JSON 出力指示は末尾の最新ユーザー発言側に結合する）。これにより、Stage 2（`high`）が並列起動した際にも過去履歴の最大 **`90.2%`（Turn 50 で `18,890 tokens`）** が即座にキャッシュヒットする。
2. **単一 `low` 固定と単一 `high` 固定のジレンマを第4章の Adaptive Thinking Router（Pattern A）で解消**：
   - 50ターンのサポート対話において、`streaming_low` 固定では初期応答（`2,310 ms`）・完了（`6,589 ms`）とも高速だが、バッテリー残量計算や3年間TCO試算などの複雑ターンでも思考トークンが `0 tok` となり計算ミスや条件見落としのリスクが残る。逆に `streaming_high` 固定では定型40ターンでも平均 `1,534 tok` の思考が走り、毎ターン1文字目が出るまで平均 **`21.2 秒`**（複雑ターンでは **`38.0 秒`**）画面がフリーズする。
   - 第4章で確立した **Pattern A（2フィールド統合構造化ストリーム：`low → high`）** を適用することで、**全50ターンで `2.62 秒`（中央値 `2.42 秒`）の初期応答** を維持しながら、定型40ターンは平均 **`5.01 秒`** で即答完走し、複雑計算10ターンのみ裏で `high` 推論（平均 `3,671 tok`）を走らせて高い計算精度を担保できる。
3. **さらなる初期応答高速化（`3.5-flash-lite`）や超深層推論（`Gemini 4` 系）への拡張**：
   - 第4章 4.1節で整理した通り、Stage 1 の初期応答（TTFT）を `2.6秒` からさらに **`1.0〜1.5秒台`** へ短縮したい場合は Stage 1 に **`gemini-3.5-flash-lite`（`minimal` / `low`）** を採用し、Stage 2 の思考をより深くしたい複雑な業務システムでは Stage 2 に **`gemini-4-hydrogen [high]`** や **`gemini-4-carbon [medium/high]`** を組み合わせる構成が推奨される。
