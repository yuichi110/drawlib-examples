# 5. マルチターンチャットでの挙動とコンテキストキャッシュ

実運用の対話型AIアプリケーション（パソコンのトラブルシューティング窓口やテクニカルサポート等）では、単発プロンプトではなく数十ターンにわたる連続対話が行われる。本章では、Google AI Studio（`google-genai` SDK / `gemini-3.8-flash`）における **パソコンが動かなくなったシナリオでの顧客とサポート窓口の50ターン連続チャットベンチマーク**（`src/gemini_evaluation/benchmark_multiturn_chat.py` / `multiturn_chat_log.json`）の実測データ（全50ターン × 4条件 ＝ 計200実行）に基づき、会話履歴の肥大化（`176 → 21,490 prompt_tokens`、累計 `42,281 文字`）に対するレイテンシ推移と、設定不要で自動発動する **暗黙的コンテキストキャッシュ（Implicit Context Caching：`cached_content_token_count`）** の実効性を定量的に解明する。

```drawlib align=center code=fold width=100% file=ch5_multiturn_hero_ja.png caption="図5-1: 50ターン連続PCサポートチャット評価アーキテクチャと4条件の平均レイテンシ比較（gemini-3.8-flash）"
from drawlib.canvas import save, setup
from drawlib.icons import phosphor
from drawlib.lines import line
from drawlib.shapes import rectangle
from drawlib.styles import Styles
from drawlib.text import text

setup(width=156, height=80, dpi=150)

# Outer structural frame
rectangle((78, 40), width=152, height=76, style=Styles.MutedDashed.patch(shape_r=2.0))
text(
    (78, 74.2),
    "50ターン連続PCサポート対話評価アーキテクチャと4条件の平均レイテンシ比較 (gemini-3.8-flash)",
    style=Styles.DarkBold.patch(text_size=11.5),
)

# Top pipeline band: 50-Turn Evaluation Loop
rectangle((78, 59.8), width=146, height=18.0, style=Styles.PrimaryNeutral.patch(shape_r=1.5))
text(
    (78, 66.2),
    "各ターンの評価パイプライン（PCトラブル50段階シナリオ・呼び出し順を毎ターン巡回しキャッシュ偏りを排除）",
    style=Styles.DarkBold.patch(text_size=10.2),
)

loop_steps = [
    (22.0, 29.5, "1. 顧客シミュレータ", "gemini-3.8-flash (t=0)\nPC故障相談 (平均 85.6字)", Styles.WhiteFlat),
    (57.5, 31.5, "2. 蓄積履歴 + 新規質問", "history: list[Content]\n176 → 21,490 tok (42,281字)", Styles.WhiteFlat),
    (95.0, 34.0, "3. 暗黙キャッシュ自動発動", "Turn 8–9 で自動発動\nT41–50 平均 87.2%・最大 90.6%", Styles.SecondaryNeutral),
    (132.5, 31.0, "4. 同一履歴で4条件計測", "詳細診断・手順回答\n(平均 753.0字・質問の約8.8倍)", Styles.WhiteFlat),
]
for cx, w, st_top, st_bot, box_st in loop_steps:
    rectangle((cx, 57.0), width=w, height=10.8, style=box_st.patch(shape_r=1.2, line_width=0.8))
    text((cx, 59.8), st_top, style=Styles.DarkBold.patch(text_size=10.2))
    text((cx, 54.6), st_bot, style=Styles.Dark.patch(text_size=10.0))

line((36.8, 57.0), (41.7, 57.0), arrow_head="->", style=Styles.DarkBold)
line((73.3, 57.0), (78.0, 57.0), arrow_head="->", style=Styles.DarkBold)
line((112.0, 57.0), (117.0, 57.0), arrow_head="->", style=Styles.DarkBold)

# Left Column: thinking=0 (Fast & Deterministic)
phosphor.lightning((7.5, 46.8), width=3.4, style=Styles.DarkBold)
text(
    (10.5, 46.8),
    "thinking=0（思考オフ：高速・低分散）",
    style=Styles.DarkBold.patch(text_size=10.8, halign="left"),
)

# Focal Card: streaming_t0
rectangle((42.0, 34.4), width=72.0, height=18.6, style=Styles.PrimaryFlat.patch(shape_r=1.6))
phosphor.star((8.2, 40.8), width=3.2, style=Styles.WhiteBold)
text(
    (11.2, 40.8),
    "★第一推奨：streaming_t0（Streaming × thinking=0）",
    style=Styles.WhiteBold.patch(text_size=10.5, halign="left"),
)
text(
    (7.8, 36.6),
    "• 初回トークン TTFT：平均 2,460 ms（中央値 2,029 ms）",
    style=Styles.White.patch(text_size=10.0, halign="left"),
)
text(
    (7.8, 32.8),
    "• 全体完了 Total：平均 6,323 ms（Blocking比 -3,964ms / 62%先行）",
    style=Styles.White.patch(text_size=10.0, halign="left"),
)
text(
    (7.8, 29.0),
    "• 50ターン推移：T11–20 平均 2,180ms → T41–50 平均 2,574ms",
    style=Styles.WhiteBold.patch(text_size=10.0, halign="left"),
)

# Secondary Card: blocking_t0
rectangle((42.0, 17.2), width=72.0, height=12.4, style=Styles.Neutral.patch(shape_r=1.4))
text(
    (7.8, 20.6),
    "比較基準：blocking_t0（Blocking × thinking=0）",
    style=Styles.DarkBold.patch(text_size=10.2, halign="left"),
)
text(
    (7.8, 16.8),
    "• TTFT = Total：平均 6,424 ms（中央値 6,062 ms）",
    style=Styles.Dark.patch(text_size=10.0, halign="left"),
)
text(
    (7.8, 13.2),
    "• 約753字の全文デコード完了まで無応答（初回表示が +3,964 ms 遅延）",
    style=Styles.Dark.patch(text_size=10.0, halign="left"),
)

# Vertical divider
line((80.0, 11.0), (80.0, 48.5), style=Styles.MutedDashed.patch(line_width=1.0))

# Right Column: thinking=default (Dynamic Thinking Inflation)
phosphor.warning((84.2, 46.8), width=3.4, style=Styles.DarkBold)
text(
    (87.2, 46.8),
    "thinking=default（動的思考：平均10〜13秒へ膨張）",
    style=Styles.DarkBold.patch(text_size=10.8, halign="left"),
)

# Card: streaming_default
rectangle((116.5, 35.8), width=69.0, height=15.6, style=Styles.Neutral.patch(shape_r=1.4))
text(
    (84.0, 40.4),
    "streaming_default（Streaming × thinking=default）",
    style=Styles.DarkBold.patch(text_size=10.2, halign="left"),
)
text(
    (84.0, 36.2),
    "• TTFT 平均 9,838 ms / Total 平均 12,335 ms",
    style=Styles.Dark.patch(text_size=10.0, halign="left"),
)
text(
    (84.0, 32.2),
    "• 平均 858 思考トークンにより初回文字出力まで約9.8秒待機",
    style=Styles.Dark.patch(text_size=10.0, halign="left"),
)

# Card: blocking_default
rectangle((116.5, 17.6), width=69.0, height=13.2, style=Styles.Neutral.patch(shape_r=1.4))
text(
    (84.0, 21.4),
    "blocking_default（Blocking × thinking=default）",
    style=Styles.DarkBold.patch(text_size=10.2, halign="left"),
)
text(
    (84.0, 17.4),
    "• TTFT = Total 平均 13,025 ms（平均 954 思考トークン）",
    style=Styles.Dark.patch(text_size=10.0, halign="left"),
)
text(
    (84.0, 13.6),
    "• 思考量（0〜2,237 tok）に応じて 6.7〜22.0秒まで大きく変動",
    style=Styles.Dark.patch(text_size=10.0, halign="left"),
)

# Bottom architectural insight banner
rectangle((78.0, 6.2), width=146.0, height=6.0, style=Styles.SecondaryNeutral.patch(shape_r=1.2))
text(
    (78.0, 6.2),
    "結論：詳細診断回答（平均753.0字）が続く50ターン対話では、streaming_t0 が毎ターン 3.96秒 (62%) 早く表示を開始し高い応答性を維持する。",
    style=Styles.DarkBold.patch(text_size=10.0),
)

save()
```

---

## 5.1 マルチターン（50ターン連続）PCサポートチャットベンチマークの設計と評価手法

### 1. `google-genai` におけるマルチターン履歴送信の構造

ステートレスな LLM API でマルチターン対話を実装する場合、アプリケーション側で過去の対話履歴 `history: list[types.Content]`（`role="user"` および `role="model"` の交互配列）を保持し、毎ターンのリクエスト時に過去の全履歴リストの末尾へ新規ユーザー発言を結合して `contents` へ渡す構造となる（`src/gemini_evaluation/llm_call.py`）。

```python
from google import genai
from google.genai import types

client = genai.Client(api_key=GEMINI_KEY)

# 過去の累積履歴 history: list[types.Content] の末尾に当ターンの新規質問を追加して送信
contents: list[types.Content] = [
    *history,
    types.Content(role="user", parts=[types.Part.from_text(text=user_prompt)]),
]

response_stream = await client.aio.models.generate_content_stream(
    model="gemini-3.8-flash",
    contents=contents,
    config=types.GenerateContentConfig(
        system_instruction=AGENT_SYSTEM_INSTRUCTION,
        thinking_config=types.ThinkingConfig(thinking_budget=0),
        temperature=0.2,
    ),
)
```

この構造では、ターンが進むにつれて毎回のリクエストに含まれる `prompt_token_count` が単調増加する。そこで本ベンチマーク（`src/gemini_evaluation/benchmark_multiturn_chat.py`）では、**「パソコンが突然動かなくなった顧客とテクニカルサポート窓口の段階的トラブルシューティング会話」** を模した以下の非対称設計で **50ターン連続計測** を実施した。

1. **顧客シミュレータ（User Simulator：`gemini-3.8-flash`, `thinking=0`）**：
   パソコンが起動しない初期症状（Turn 1–10：電源・ACアダプタ・放電・BIOS確認・セーフモード起動）から、データ退避と原因切り分け（Turn 11–20：USBバックアップ・ドライバ・`sfc /scannow`・クリーンブート・メモリ診断）、OS復旧試行（Turn 21–30：S.M.A.R.T.確認・イベントビューアー・システムの復元・回復ドライブ・USBブート）、修理手続きと保証確認（Turn 31–45：BitLocker回復キー・メーカー診断エラー・自然故障保証・引取修理梱包・代替機レンタル・出張修理・下取り買い替え）、修理後のデータ復元と再発防止策（Turn 46–50：返却後チェック・ウイルススキャン・イメージバックアップ・クラウド同期・日常メンテナンス）に至る50段階の連続シナリオに沿って、`70〜100文字` 程度の自然な顧客質問（実測平均 **`85.6 文字`**）を毎ターン生成する。
2. **PCサポートエージェント（Agent：`gemini-3.8-flash`）**：
   蓄積された会話履歴 `history` を踏まえ、確認手順・判断基準・安全上の注意点を含む丁寧なサポート回答（実測平均 **`753.0 文字`**、顧客質問の **約8.8倍** の文量）を生成する。
3. **同一履歴に対する4条件の巡回計測（`rot = (turn - 1) % 4`）**：
   Turn 1（`176 prompt_tokens`）から Turn 50（`21,490 prompt_tokens`、履歴累計 **`42,281 文字`**）までの各ターンにおいて、まったく同一の `history` と新規質問に対して以下の4条件を順次実行し、コンテキストキャッシュのウォームアップ順序によるバイアスを排除するため呼び出し順を毎ターン巡回した。

| 検証バリアント | 呼び出し API メソッド | `ThinkingConfig` 設定 | 初回応答 `TTFT` 平均（中央値） | 全体完了 `Total` 平均 | 平均思考トークン数 | 特徴・位置づけ |
| :--- | :--- | :--- | ---: | ---: | ---: | :--- |
| **`streaming_t0`** | `generate_content_stream` | `thinking_budget=0` | **`2,460 ms`** (`2,029 ms`) | **`6,323 ms`** | `19 tok` (T2–50: `0 tok`) | **★第一推奨**：毎ターン **`3,964 ms` (`3.96秒` / `62%`)** 早く表示開始 |
| **`blocking_t0`** | `generate_content` | `thinking_budget=0` | `6,424 ms` (`6,062 ms`) | `6,424 ms` | `0 tok` | 約753字の全文生成完了まで待機（`TTFT = Total`） |
| **`streaming_default`** | `generate_content_stream` | デフォルト（動的思考） | `9,838 ms` (`10,500 ms`) | `12,335 ms` | `858 tok` | 内部思考完了まで約9.8秒ストリーム停止 |
| **`blocking_default`** | `generate_content` | デフォルト（動的思考） | `13,025 ms` (`12,548 ms`) | `13,025 ms` | `954 tok` | 内部思考＋全文生成完了まで約13.0秒待機 |

---

## 5.2 入力トークン数の直線的増加と暗黙的コンテキストキャッシュ（Implicit Context Caching）の自動発動

50ターンの連続対話において、各ターン完了後に `(user, model)` の2メッセージを `history` に追加していくと、エージェントへの入力トークン数（`prompt_token_count`）は **1ターンあたり平均 `+435 tokens`** のペースで直線的に増加する（Turn 1 で `176 tokens` → Turn 8 で `2,686 tokens` → Turn 25 で `10,060 tokens` → Turn 50 で **`21,490 tokens`**）。

本検証における最も重要な発見は、**入力コンテキストが約 `2,600〜3,000 tokens` を超えた Turn 8〜9 において、明示的なキャッシュ作成 API を一切呼び出していないにもかかわらず、Gemini 3.8 Flash の暗黙的コンテキストキャッシュ（Implicit Context Caching：`usage_metadata.cached_content_token_count`）が自動的に発動し、Turn 50 まで毎ターン連続してキャッシュ境界が自動拡張された** 点である。

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
prompt_vals = [float(t["variants"]["streaming_t0"]["prompt_tokens"]) for t in turns]
cached_vals = [float(t["variants"]["streaming_t0"]["cached_tokens"]) for t in turns]
uncached_vals = [p - c for p, c in zip(prompt_vals, cached_vals)]

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
    "総入力トークン数 (prompt_tokens: 176 → 21,490 tok)",
    prompt_vals,
    style=Styles.PrimaryFlat,
    line_width=2.6,
    point_shape="none",
)
chart.add_series(
    "暗黙キャッシュヒット数 (cached_tokens: 最大 18,995〜19,480 tok)",
    cached_vals,
    style=Styles.SuccessFlat,
    line_width=2.4,
    point_shape="none",
)
chart.add_series(
    "実質未キャッシュ差分 (prompt - cached: ~2,400 tok)",
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
    text_style=Styles.DarkBold.patch(text_size=10.0),
    orientation="vertical",
    item_gap=1.3,
)

# Axis labels
text((9.5, 54.0), "トークン数 (tok)", style=Styles.DarkBold.patch(text_size=10.0, halign="left"))
text((51.5, 6.2), "対話ターン番号 (Turn 1 〜 Turn 50)", style=Styles.DarkBold.patch(text_size=10.0))

# Callout annotation inside chart pointing to Turn 8-9 cache activation
rectangle((44.5, 38.0), width=40.0, height=8.0, style=Styles.Neutral.patch(shape_r=1.0))
text(
    (44.5, 39.8),
    "Turn 8–9 (~2,686 tok 突破で自動発動)",
    style=Styles.DarkBold.patch(text_size=10.0),
)
text(
    (44.5, 36.2),
    "毎ターン追随し T50 で最大 90.6% ヒット",
    style=Styles.Dark.patch(text_size=10.0),
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
        "1. 直線的な履歴増加 (+435 tok/T)",
        "質問(平均86字)＋回答(平均753字)の蓄積で\nTurn 1 (176) → Turn 50 (21,490) へ増加",
    ),
    (
        43.8,
        "2. Turn 8–9 で暗黙キャッシュ自動発動",
        "API 設定なしに Turn 8–9 から KV キャッシュ\nが自動有効化され毎ターン連続ヒット",
    ),
    (
        28.4,
        "3. T41–50 平均 87.2%・最大 90.6%",
        "履歴伸長に追随してキャッシュ境界が毎ターン\n前進し T50 で最大 19,480/21,490 tok ヒット",
    ),
    (
        13.0,
        "4. 未キャッシュ差分は約2,400 tokで一定",
        "新規 Prefill 計算対象が ~2,400 tok の一定\n帯域に抑えられ定数時間 O(1) 応答を実現",
    ),
]

for cy, hdr, body in summary_cards:
    rectangle((125.5, cy), width=47.4, height=13.4, style=Styles.WhiteFlat.patch(shape_r=1.2, line_width=0.7))
    text((103.2, cy + 3.6), hdr, style=Styles.DarkBold.patch(text_size=10.0, halign="left"))
    text((103.2, cy - 2.0), body, style=Styles.Dark.patch(text_size=10.0, halign="left"))

save()
```

### 図5-2 から導かれる暗黙的コンテキストキャッシュの挙動メカニズム

1. **Turn 8〜9 におけるゼロ設定発動**：
   Turn 1〜7（`176〜2,298 prompt_tokens`）では `cached_content_token_count = 0` であったが、入力が `2,686 tokens` に達した **Turn 8**（`blocking_t0` で `703 cached_tokens`）および **Turn 9**（`3,045 tokens`、`streaming_t0` で `704 cached_tokens`・`blocking_t0` で `1,060 cached_tokens`）において、バックエンドで KV キャッシュが自動生成された。
2. **毎ターンの連続的なプレフィックス拡張**：
   Turn 9 以降、会話履歴が伸びるにつれてキャッシュヒット数は Turn 10（`1,061 tok`）→ Turn 20（`5,064 tok`）→ Turn 30（`9,935 tok`）→ Turn 40（`14,533 tok`）→ Turn 50（`streaming_t0` で **`18,995 tok` [88.4%]**、`blocking_t0` で **`19,480 tok` [90.6%]**）と毎ターン滑らかに自動更新された。その結果、**Turn 41〜50 の平均キャッシュヒット率は `87.2%`（`streaming_t0` 基準）、ピーク時は `90.6%`** に達している。
3. **実質未キャッシュ差分（Uncached Delta）の一定化**：
   図5-2の紫破線が示す通り、毎ターン新たに Prefill 計算が必要となる未キャッシュトークン数（`prompt_tokens - cached_tokens`）は、Turn 9 以降 **`約 2,340〜2,540 tokens`（`blocking_t0` では `約 1,980〜2,010 tokens`）** の極めてフラットな一定幅に完全に封じ込められている。

---

## 5.3 長期対話（全50ターン）にわたるレイテンシ推移とスケーリング特性

暗黙的コンテキストキャッシュが過去の履歴トークンの **`85〜90% 以上`** の KV キャッシュを再利用するため、**`streaming_t0`（Streaming × `thinking=0`）の初回応答時間（TTFT）は履歴が `21,490 tokens` まで膨らんでも約 `2.0〜2.5 秒` の安定した帯域を維持する**。具体的には、ウォームアップ後の Turn 11〜20 平均 **`2,180 ms`** から Turn 41〜50 平均 **`2,574 ms`** への推移（`+13,700 tokens` の増加に対してわずか `+394 ms`、傾き **`+29 ms / 1,000 input tokens`**）に留まっている。

```drawlib align=center code=fold width=100% file=ch5_latency_evolution_2panel_ja.png caption="図5-3: Turn 1〜50 におけるレイテンシ推移の2パネル比較（左：thinking=0 の安定スケーリング、右：thinking=default の思考トークン変動と遅延膨張）"
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
    "Turn 1〜50（176 → 21,490 tok）におけるレイテンシ推移：thinking=0 (左) vs thinking=default (右)",
    style=Styles.DarkBold.patch(text_size=11.5),
)

turns = load_multiturn_turns()
labeled_turns = {1, 10, 20, 30, 40, 50}
categories = [f"T{t['turn']}" if int(t["turn"]) in labeled_turns else "" for t in turns]

s0_ttft = [float(t["variants"]["streaming_t0"]["ttft_ms"]) for t in turns]
s0_total = [float(t["variants"]["streaming_t0"]["total_ms"]) for t in turns]
b0_total = [float(t["variants"]["blocking_t0"]["total_ms"]) for t in turns]

sd_ttft = [float(t["variants"]["streaming_default"]["ttft_ms"]) for t in turns]
bd_total = [float(t["variants"]["blocking_default"]["total_ms"]) for t in turns]
sd_th_tok = [float(t["variants"]["streaming_default"]["thoughts_tokens"]) for t in turns]

# =========================================================================
# Left Panel: thinking=0 (Flat scaling)
# =========================================================================
rectangle((42.5, 45.5), width=71.0, height=69.0, style=Styles.WhiteFlat.patch(shape_r=1.5, line_width=0.8))
rectangle((42.5, 73.2), width=67.0, height=11.6, style=Styles.Neutral.patch(shape_r=1.1))
text(
    (42.5, 76.6),
    "左パネル：thinking=0（中央値 2,029ms・傾き +29ms/1k tok）",
    style=Styles.DarkBold.patch(text_size=10.2),
)

# Legend for Left Panel
line((10.0, 72.8), (13.6, 72.8), style=Styles.PrimaryBold.patch(line_width=2.6))
circle((11.8, 72.8), radius=0.6, style=Styles.PrimaryFlat)
text((14.5, 72.8), "streaming_t0 TTFT (平均 2,460ms)", style=Styles.DarkBold.patch(text_size=10.0, halign="left"))

line((10.0, 69.4), (13.6, 69.4), style=Styles.TealDashed.patch(line_width=1.9))
text((14.5, 69.4), "streaming_t0 Total (6,323ms)", style=Styles.Dark.patch(text_size=10.0, halign="left"))

line((47.2, 69.4), (50.8, 69.4), style=Styles.SecondaryBold.patch(line_width=2.1))
text((51.6, 69.4), "blocking_t0 (6,424ms)", style=Styles.Dark.patch(text_size=10.0, halign="left"))

chart_left = LineChart(
    axis_line_style=Styles.Dark,
    axis_text_style=Styles.Dark.patch(text_size=10.0),
    grid_style=Styles.MutedDashed,
    categories=categories,
    width=59.0,
    height=42.0,
    show_points=True,
    point_shape="circle",
    point_size=0.45,
)
chart_left.configure_x_axis(show_grid=False)
chart_left.configure_y_axis(
    min_value=0,
    max_value=14000,
    tick_step=3500,
    format="{:,.0f}",
)
chart_left.add_series(
    name="blocking_t0 Total",
    values=b0_total,
    style=Styles.SecondaryFlat,
    line_width=2.0,
    point_size=0.4,
)
chart_left.add_series(
    name="streaming_t0 Total",
    values=s0_total,
    style=Styles.TealFlat,
    line_width=1.8,
    line_style="dashed",
    point_shape="none",
)
chart_left.add_series(
    name="streaming_t0 TTFT",
    values=s0_ttft,
    style=Styles.PrimaryFlat,
    line_width=2.6,
    point_size=0.5,
)
chart_left.draw(xy=(14.5, 19.5))
text((10.0, 63.8), "時間 (ms)", style=Styles.DarkBold.patch(text_size=10.0, halign="left"))
text((44.0, 14.2), "ターン番号（T11–20 平均 2,180ms → T41–50 平均 2,574ms）", style=Styles.DarkBold.patch(text_size=10.0))

# =========================================================================
# Right Panel: thinking=default (Latency + Thinking Token Bars)
# =========================================================================
rectangle((115.5, 45.5), width=71.0, height=69.0, style=Styles.WhiteFlat.patch(shape_r=1.5, line_width=0.8))
rectangle((115.5, 73.2), width=67.0, height=11.6, style=Styles.Neutral.patch(shape_r=1.1))
text(
    (115.5, 76.6),
    "右パネル：thinking=default（思考トークン棒＋応答時間）",
    style=Styles.DarkBold.patch(text_size=10.2),
)

# Legend for Right Panel
line((83.5, 72.8), (87.5, 72.8), style=Styles.WarningBold.patch(line_width=2.2))
circle((85.5, 72.8), radius=0.55, style=Styles.WarningFlat)
text((88.5, 72.8), "streaming_def TTFT (9,838ms)", style=Styles.DarkBold.patch(text_size=10.0, halign="left"))

line((83.5, 69.4), (87.5, 69.4), style=Styles.DangerBold.patch(line_width=2.0))
text((88.5, 69.4), "blocking_def Total (13,025ms)", style=Styles.Dark.patch(text_size=10.0, halign="left"))

rectangle((124.0, 69.4), width=3.0, height=2.0, style=Styles.SecondaryNeutral.patch(line_width=0.6))
text((126.5, 69.4), "思考 tok (平均858)", style=Styles.Dark.patch(text_size=10.0, halign="left"))

# Draw Thinking Token vertical bars strictly inside the inner plot area (x: 97.7..144.2, y0: 25.8)
rx0, ry0, rpw, rph = 87.5, 19.5, 59.0, 42.0
inner_x0, inner_x1, inner_y0, inner_h = 97.7, 144.2, 25.8, 32.5
for idx, th_val in enumerate(sd_th_tok):
    bx = inner_x0 + (idx / max(len(sd_th_tok) - 1, 1)) * (inner_x1 - inner_x0)
    bh = min(th_val / 2400.0, 1.0) * inner_h
    if bh > 0.2:
        rectangle(
            (bx, inner_y0 + bh / 2.0),
            width=0.62,
            height=bh,
            style=Styles.SecondaryNeutral.patch(line_width=0.3, shape_r=0),
        )

chart_right = LineChart(
    axis_line_style=Styles.Dark,
    axis_text_style=Styles.Dark.patch(text_size=10.0),
    grid_style=Styles.MutedDashed,
    categories=categories,
    width=rpw,
    height=rph,
    show_points=True,
    point_shape="circle",
    point_size=0.45,
)
chart_right.configure_x_axis(show_grid=False)
chart_right.configure_y_axis(
    min_value=0,
    max_value=24000,
    tick_step=6000,
    format="{:,.0f}",
)
chart_right.add_series(
    name="blocking_default Total",
    values=bd_total,
    style=Styles.DangerFlat,
    line_width=1.8,
    point_size=0.4,
)
chart_right.add_series(
    name="streaming_default TTFT",
    values=sd_ttft,
    style=Styles.WarningFlat,
    line_width=2.2,
    point_size=0.45,
)
chart_right.draw(xy=(rx0, ry0))
text((83.0, 63.8), "時間 (ms) / 思考量", style=Styles.DarkBold.patch(text_size=10.0, halign="left"))
text((117.0, 14.2), "ターン番号（思考 0〜2,237 tok の乱高下に完全連動）", style=Styles.DarkBold.patch(text_size=10.0))

# Bottom callout bar
rectangle((78.0, 6.2), width=146.0, height=6.0, style=Styles.PrimaryNeutral.patch(shape_r=1.2))
text(
    (78.0, 6.2),
    "要点：streaming_t0 (左・青実線) は中央値 2.03s を維持する一方、default (右) は思考トークン量に応じて最大 22秒まで激しく振動する。",
    style=Styles.DarkBold.patch(text_size=10.0),
)

save()
```

### 図5-3 の左右比較から読み取れる重要事実

1. **左パネル（`thinking=0`）：Turn 50 まで中央値 `2.03 秒` の初回応答を維持する安定性**：
   - 青実線（`streaming_t0 TTFT`）は初回 Turn 1 のコールドスタートを除き `1,082〜4,761 ms`（全50ターン平均 **`2,460 ms`**、Turn 2〜50 平均 **`2,295 ms`**、中央値 **`2,029 ms`**）の安定した帯域に収まり、紫実線（`blocking_t0 Total=TTFT`、平均 **`6,424 ms`**）の常に **`3,964 ms`（`3.96秒` / `62%`）下側** を平行に推移している。
   - さらに緑破線（`streaming_t0 Total`、平均 **`6,323 ms`**）は `blocking_t0`（`6,424 ms`）とほぼ完全に重なっており、ストリーミング化に伴う全体完了時間のオーバーヘッドはゼロである。
2. **右パネル（`thinking=default`）：ターン番号ではなく思考トークン量に支配される乱高下**：
   - `thinking=default` では、各ターンのPCトラブル相談内容に対するモデルの動的判断によって `thoughts_token_count`（背景の縦棒）が平均 **`858〜954 tokens`**（範囲 `0〜2,237 tokens`）の間で激しく変動する。
   - ストリーミング（`streaming_default`）であっても、内部思考が完了するまで1文字目の可視テキストチャンクが送出されないため、平均 TTFT は **`9,838 ms`** に膨張し、ストリーミング本来の体感速度優位性が思考待機時間に埋没してしまう。

---

## 5.4 内部思考トークンの変動分析と 2D ストリーム軌跡スナップショット（Turn 1 vs Turn 25 vs Turn 50）

`thinking=default` におけるレイテンシ変動の正体と、会話序盤（**Turn 1**）・中盤（**Turn 25**）・終盤（**Turn 50**）におけるチャンク送出軌跡の違いを同時検証するため、図5-4の左パネルに `thinking=default` 全100実行（50ターン × 2モード）の **`thoughts_tokens` 対 `total_ms` 散布図** を、右パネルに `load_multiturn_trajectory()` から抽出した **Turn 1・Turn 25・Turn 50 の3ターン軌跡オーバーレイ** を示す。

```drawlib align=center code=fold width=100% file=ch5_thinking_scatter_and_trajectories_ja.png caption="図5-4: 思考トークン数と完了時間の線形相関（左）および Turn 1・25・50 における3モードのストリーム軌跡比較（右）"
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
    "思考トークン数 × Total 相関散布図 (左) と Turn 1・25・50 ストリーム軌跡比較 (右)",
    style=Styles.DarkBold.patch(text_size=11.5),
)

# =========================================================================
# Left Panel: Scatter plot of thoughts_tokens vs total_ms (100 default runs + t=0 ref)
# =========================================================================
rectangle((42.5, 47.5), width=71.0, height=73.0, style=Styles.WhiteFlat.patch(shape_r=1.5, line_width=0.8))
rectangle((42.5, 77.2), width=67.0, height=11.2, style=Styles.Neutral.patch(shape_r=1.1))
text(
    (42.5, 80.4),
    "左：思考トークン数 vs 完了時間 (Total ≈ 6,300ms + 7.0ms×ThTok)",
    style=Styles.DarkBold.patch(text_size=10.0),
)

pts_s_def: list[tuple[float, float]] = []
pts_b_def: list[tuple[float, float]] = []
pts_s_t0: list[tuple[float, float]] = []

for t_rec in load_multiturn_turns():
    v = t_rec["variants"]
    pts_s_def.append((float(v["streaming_default"]["thoughts_tokens"]), float(v["streaming_default"]["total_ms"])))
    pts_b_def.append((float(v["blocking_default"]["thoughts_tokens"]), float(v["blocking_default"]["total_ms"])))
    pts_s_t0.append((0.0, float(v["streaming_t0"]["total_ms"])))

# Compact legend inside Left Panel header
circle((11.0, 76.2), radius=0.65, style=Styles.WarningFlat)
text((12.5, 76.2), "streaming_default (50回)", style=Styles.DarkBold.patch(text_size=10.0, halign="left"))
circle((46.0, 76.2), radius=0.65, style=Styles.DangerFlat)
text((47.5, 76.2), "blocking_default (50回)", style=Styles.DarkBold.patch(text_size=10.0, halign="left"))
circle((11.0, 73.0), radius=0.65, style=Styles.PrimaryFlat)
text((12.5, 73.0), "streaming_t0 (X=0 基準・50回)   強い正の線形相関", style=Styles.Dark.patch(text_size=10.0, halign="left"))

scatter = ScatterChart(
    axis_line_style=Styles.Dark,
    axis_text_style=Styles.Dark.patch(text_size=10.0),
    grid_style=Styles.MutedDashed,
    width=63.0,
    height=46.0,
    default_radius=0.85,
)
scatter.configure_x_axis(
    label="内部思考トークン数 (thoughts_token_count [tok])",
    min_value=0,
    max_value=2400,
    tick_step=800,
    format="{:,.0f}",
)
scatter.configure_y_axis(
    label="全体完了時間 Total (ms)",
    min_value=0,
    max_value=24000,
    tick_step=6000,
    format="{:,.0f}",
)
scatter.add_series("blocking_default", pts_b_def, style=Styles.DangerFlat, shape="rhombus", radius=0.85)
scatter.add_series("streaming_default", pts_s_def, style=Styles.WarningFlat, shape="triangle", radius=0.9)
scatter.add_series("streaming_t0", pts_s_t0, style=Styles.PrimaryFlat, shape="circle", radius=0.85)
scatter.draw(xy=(11.5, 18.0))

# =========================================================================
# Right Panel: 3-Turn Trajectory Overlay (Turn 1, Turn 25, Turn 50)
# =========================================================================
rectangle((115.5, 47.5), width=71.0, height=73.0, style=Styles.WhiteFlat.patch(shape_r=1.5, line_width=0.8))
rectangle((115.5, 77.2), width=67.0, height=11.2, style=Styles.Neutral.patch(shape_r=1.1))
text(
    (115.5, 80.4),
    "右：Turn 1・25・50 の文字送出軌跡（経過時間 vs 累積文字数）",
    style=Styles.DarkBold.patch(text_size=10.0),
)

# Legend for Right Panel trajectories
line((83.5, 76.2), (87.5, 76.2), style=Styles.PrimaryBold.patch(line_width=2.4))
text((88.5, 76.2), "streaming_t0", style=Styles.DarkBold.patch(text_size=10.0, halign="left"))

line((111.5, 76.2), (115.5, 76.2), style=Styles.SecondaryBold.patch(line_width=2.2))
text((116.5, 76.2), "blocking_t0", style=Styles.DarkBold.patch(text_size=10.0, halign="left"))

line((83.5, 73.0), (87.5, 73.0), style=Styles.DangerDashed.patch(line_width=2.0))
text((88.5, 73.0), "streaming_default（思考待機後にストリーム開始）", style=Styles.Dark.patch(text_size=10.0, halign="left"))

sub_panels = [
    (1, 54.0, "Turn 1 (176 tok / 初回起動相談)：blk_t0 5,418ms vs str_def 10,411ms"),
    (25, 35.0, "Turn 25 (10,060 tok / Cache 75.0%)：str_t0 3,833ms vs blk_t0 5,962ms"),
    (50, 16.0, "Turn 50 (21,490 tok / Cache 88.4%)：str_t0 4,083ms vs blk_t0 8,074ms"),
]

max_t = 20000.0
max_c = 1050.0
pw = 55.0
ph = 12.2
px0 = 88.5

for t_num, py0, sub_title in sub_panels:
    text((px0 + pw / 2, py0 + ph + 2.0), sub_title, style=Styles.DarkBold.patch(text_size=10.0))
    rectangle((px0 + pw / 2, py0 + ph / 2), width=pw, height=ph, style=Styles.Neutral.patch(line_width=0.5, shape_r=0))

    def to_x(ms: float) -> float:
        return px0 + min(max(ms, 0.0), max_t) / max_t * pw

    def to_y(ch: float, base_y: float = py0) -> float:
        return base_y + min(max(ch, 0.0), max_c) / max_c * ph

    for xt in (0, 5000, 10000, 15000, 20000):
        tx = to_x(float(xt))
        line((tx, py0), (tx, py0 + ph), style=Styles.MutedDashed.patch(line_width=0.5))
        if t_num == 50:
            text((tx, py0 - 2.2), f"{xt // 1000}s", style=Styles.Dark.patch(text_size=10.0))

    for yt in (0, 500, 1000):
        ty = to_y(float(yt))
        line((px0, ty), (px0 + pw, ty), style=Styles.MutedDashed.patch(line_width=0.5))
        text((px0 - 1.2, ty), f"{yt}", style=Styles.Dark.patch(text_size=10.0, halign="right"))

    line((px0, py0), (px0 + pw, py0), style=Styles.Dark.patch(line_width=1.0))
    line((px0, py0), (px0, py0 + ph), style=Styles.Dark.patch(line_width=1.0))

    for v_key, st_line in (
        ("streaming_default", Styles.DangerDashed.patch(line_width=1.9)),
        ("blocking_t0", Styles.SecondaryBold.patch(line_width=2.0)),
        ("streaming_t0", Styles.PrimaryBold.patch(line_width=2.4)),
    ):
        tr = load_multiturn_trajectory(t_num, v_key)
        gem_pts = tr["timeline_series"].get("gemini", [])
        if len(gem_pts) >= 2:
            coords = [(to_x(float(p["t_ms"])), to_y(float(p["chars"]))) for p in gem_pts]
            lines(coords, style=st_line)

text((px0 + pw / 2, 11.2), "経過時間 (秒) — Y軸: 累積出力文字数 (0〜1,000字)", style=Styles.DarkBold.patch(text_size=10.0))

# Bottom callout bar
rectangle((78.0, 5.8), width=146.0, height=5.8, style=Styles.SecondaryNeutral.patch(shape_r=1.2))
text(
    (78.0, 5.8),
    "結論：中盤 Turn 25・終盤 Turn 50 ともに streaming_t0 (青実線) は blocking_t0 より 2.1〜4.0秒早く滑らかに文字を送出する。",
    style=Styles.DarkBold.patch(text_size=10.0),
)

save()
```

### 図5-4 から導かれる2つの定量的結論

1. **左パネル：`Total ≈ 6,300 ms + 7.0 ms × ThTok` の線形支配則**：
   - `thinking=default` の全100実行（50ターン × Streaming / Blocking）をプロットすると、ターン番号（Turn 1 か Turn 50 か）には関係なく、内部思考トークン数 `ThTok`（`0〜2,237 tokens`）に対して強い正の直線相関を示す。
   - 切片の約 `6,300 ms` は平均 `753 文字` の詳細なPCサポート回答生成に要するベースデコード時間であり、そこから右上に伸びる最大 `+15 秒` の追加遅延は内部思考トークンの生成コストで説明される。
2. **右パネル：Turn 1・Turn 25・Turn 50 を通じたストリーム軌跡の比較**：
   - **Turn 1（`176 tok`・キャッシュ `0%`・電源が入らない初回相談）**：初回コールドリクエストを除けば、`blocking_t0`（紫実線）は `5,418 ms` まで **0文字** のまま待機してから `505 文字` を一括出力し、`streaming_default`（赤破線）は `1,087 思考トークン` のため **`10,411 ms`** まで画面が停止する。
   - **Turn 25（`10,060 tok`・キャッシュ `7,547 tok [75.0%]`・BIOS/チップセット更新手順）**：履歴が57倍以上に増えた中盤でも、`streaming_t0`（青実線）は **`3,833 ms`** からストリームを開始し、`898 文字` を滑らかに出力して `blocking_t0`（`5,962 ms`）に対し **`2,129 ms`（`36%`）早く** 初回応答を届けている。
   - **Turn 50（`21,490 tok`・キャッシュ `18,995 tok [88.4%]`・日常メンテナンス総括）**：履歴が122倍に達した最終ターンにおいても、暗黙キャッシュが約 `19,000 tokens` をヒットするため、`streaming_t0` は **`4,083 ms`** で初回チャンクを送出し、`blocking_t0`（`8,074 ms`）に対して **`3,991 ms`（`49%`）先行** して `902 文字` を完走している（一方 `streaming_default` は `1,584 思考トークン` により `16,498 ms` まで無応答となる）。

---

## 5.5 区間別（10ターンごと）の包括的統計テーブルとマルチターン本番設計ガイドライン

### 1. 区間別（10ターンごと）パフォーマンス集計表

全50ターンを10ターンごとの5コホート（`Turns 1–10` 〜 `Turns 41–50`）および全50ターン平均で集計した包括的ベンチマーク結果を下表に示す。

| ターン区間・主な相談トピック | 平均入力 (`prompt`) /<br>キャッシュ (`ヒット率`) | `streaming_t0`<br>TTFT / Total (`ms`) | `blocking_t0`<br>Total (`ms`) | Streaming 先行幅<br>(`str_t0 - blk_t0`) | `streaming_default`<br>TTFT / Total [思考] | `blocking_default`<br>Total [思考] |
| :--- | ---: | ---: | ---: | ---: | ---: | ---: |
| **Turns 1–10**<br>(電源・放電・BIOS・セーフモード) | `1,768 tok` (`176〜3,407`)<br>Cache: `177 tok` (`10.0%`) | **`2,853`** / `5,910`<br>(T2–10: `2,000`) | `5,125` | **`-2,272 ms`**<br>(`-44.3%`) | `11,687` / `13,467`<br>[`1,211 tok`] | `12,988`<br>[`1,099 tok`] |
| **Turns 11–20**<br>(データ退避・ドライバ・メモリ診断) | `5,635 tok` (`3,817〜7,539`)<br>Cache: `3,229 tok` (`57.3%`) | **`2,180`** / `5,586` | `6,742` | **`-4,562 ms`**<br>(`-67.7%`) | `9,357` / `11,643`<br>[`828 tok`] | `14,398`<br>[`1,154 tok`] |
| **Turns 21–30**<br>(SSD診断・復元・USB回復メディア) | `10,280 tok` (`8,005〜12,478`)<br>Cache: `7,784 tok` (`75.7%`) | **`2,361`** / `6,804` | `6,666` | **`-4,305 ms`**<br>(`-64.6%`) | `9,969` / `12,658`<br>[`913 tok`] | `12,731`<br>[`954 tok`] |
| **Turns 31–40**<br>(BitLocker・メーカー診断・引取修理) | `15,007 tok` (`12,995〜16,915`)<br>Cache: `12,556 tok` (`83.7%`) | **`2,331`** / `6,260` | `6,653` | **`-4,322 ms`**<br>(`-65.0%`) | `8,265` / `11,405`<br>[`517 tok`] | `12,480`<br>[`802 tok`] |
| **Turns 41–50**<br>(代替機・出張修理・バックアップ総括) | `19,338 tok` (`17,309〜21,490`)<br>Cache: `16,872 tok` (**`87.2%`**) | **`2,574`** / `7,054` | `6,935` | **`-4,361 ms`**<br>(`-62.9%`) | `9,910` / `12,504`<br>[`823 tok`] | `12,527`<br>[`763 tok`] |
| **全50ターン平均** | **`10,406 tok`** (`176〜21,490`)<br>Cache: **`8,124 tok`** (`78.1%` / 最大**`90.6%`**) | **`2,460`** / **`6,323`**<br>(中央値 **`2,029`**) | **`6,424`** | **`-3,964 ms`**<br>(**`-61.7%`**) | **`9,838`** / **`12,335`**<br>[**`858 tok`**] | **`13,025`**<br>[**`954 tok`**] |

### 2. マルチターンチャット本番設計の3大ベストプラクティス

1. **プレフィックス不変性（Prefix Immutability）の厳守による暗黙キャッシュ最大化**：
   - Gemini 3.8 Flash の暗黙的コンテキストキャッシュ（Implicit Context Caching）は、`system_instruction` と過去の `history: list[types.Content]` の **先頭からのトークン系列が完全一致（Prefix Match）** している場合に自動で KV キャッシュを再利用する。
   - **アンチパターン**：`system_instruction` の先頭や途中に「現在時刻（秒単位のタイムスタンプ）」や「リクエストごとの UUID」を動的に埋め込むと、毎ターン先頭トークンが変化してプレフィックス一致が崩れ、長大履歴になってもキャッシュヒット率が `0%` に低下する。
   - **推奨パターン**：`system_instruction` と過去ターンの `history` は完全な **追記専用（Append-Only）** として不変に保ち、動的なコンテキスト情報（最新の診断ステータスや検索結果など）は必ず **末尾の最新ターンメッセージ側** に注入する。
2. **長文応答を伴うマルチターン対話では `Streaming × thinking=0` を標準採用**：
   - PCのトラブルシューティング案内のように回答が平均 `753 文字` に及ぶ実用的なチャットでは、`thinking=0` であっても全文のトークン生成完了までに平均 `6.42 秒` を要する。
   - `generate_content_stream` × `thinking_budget=0`（`streaming_t0`）を採用することで、初回文字表示（TTFT）を全50ターン平均 **`2,460 ms`（中央値 `2,029 ms`）** に短縮し、`blocking_t0`（`6,424 ms`）に対して毎ターン **`3.96 秒`（`62%`）** の体感応答高速化をオーバーヘッドなしで実現できる。
3. **高度な推論が必要なターンにのみ第4章の Adaptive Thinking Router（Pattern A）を結合**：
   - マルチターン対話で無条件に `thinking=default` を使うと、定型的な確認ターンでも平均 `858 tokens` の思考が走り TTFT が `9.8 秒` まで悪化する。
   - 基本ターンは `streaming_t0`（`thinking_budget=0`）で高速応答しつつ、修理vs買い替えの3年間総費用比較や大容量データの退避時間試算といった複雑な多段階計算が求められる質問にのみ第4章で検証した **2フィールド統合構造化ストリーム（Pattern A）** を組み合わせることで、暗黙的コンテキストキャッシュ（Stage 1 と Stage 2 の間でも同一履歴プレフィックスがキャッシュ共有される）を最大限に活かした高速・高精度な対話アーキテクチャを構築できる。
