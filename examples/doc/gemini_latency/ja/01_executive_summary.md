# 1. エグゼクティブサマリー

本レポートは、Google AI Studio（`google-genai` SDK、`genai.Client(api_key=GEMINI_KEY)`）上の **`gemini-3.8-flash`** を用いた対話型AIシステム（PCテクニカルサポート・トラブルシューティング対話）において、**「高速な初回トークン表示（TTFT）」「多段階算数・条件比較（修理vs買い替え損益・データ転送時間・保守契約試算）の100%の計算正確性」「50ターン連続対話における平坦なレイテンシスケーリング」** の3要件を同時に達成するためのアーキテクチャ検証報告書である。合計 **271 回の実機 API 実行ログ**（単発 `ThinkingConfig` 18試行、適応型ルーティング 45試行、Pydantic スキーマ Cold/Warm 8試行、50ターン連続PCサポートチャット 200試行）の定量分析から、単発・マルチターンを問わず **`Streaming`（`generate_content_stream`）を基本通信方式とし、Pydantic 2フィールド構造化ストリーム `{thinking: bool, response: str}` と `pydantic_core.from_json(..., allow_partial="trailing-strings")` による「適応型 Thinking ルーター（Pattern A）」を標準採用する構成** を第一推奨アーキテクチャとして結論づけた。

```drawlib align=center code=fold width=100% file=ch01_exec_summary_hero_ja.png caption="図1-1: エンドツーエンド方式選定マトリクス — 固定設定（thinking=0 / low）の二律背反と適応型ルーター（Pattern A）＋50ターン暗黙キャッシュ統合構成"
from drawlib.canvas import save, setup
from drawlib.icons import phosphor
from drawlib.lines import line
from drawlib.shapes import rectangle
from drawlib.styles import Styles
from drawlib.text import text

setup(width=156, height=78, dpi=150)

# Outer structural frame
rectangle((78.0, 39.0), width=152.0, height=74.0, style=Styles.MutedDashed.patch(shape_r=2.0))
text(
    (78.0, 72.8),
    "エンドツーエンド方式選定マトリクス：固定設定 vs. 適応型 Thinking ルーター (Pattern A)",
    style=Styles.DarkBold.patch(text_size=11.5),
)

cols = [
    (
        29.0,
        "① 固定 thinking=0",
        "Streaming + thinking_budget=0",
        "単発・50ターン速度：◎ 最速",
        "推論待機ゼロで即時ストリーム開始",
        "複雑計算・比較 (Tier 3)：× 不安定",
        "修理vs買替・SSD転送試算で数値矛盾",
        [
            "• 判定：定型案内・単純要約のみ適格",
            "• 算数・多段比較を含む対話は不可",
        ],
        Styles.Neutral,
        Styles.DangerBold,
        Styles.DarkBold,
        phosphor.x_circle,
    ),
    (
        78.0,
        "② 固定 thinking=low / default",
        "常時内部推論トークンを生成",
        "複雑計算・比較 (Tier 3)：◎ 3/3",
        "推論トークンにより計算整合性を確保",
        "体感待機時間 (TTFT)：× 大幅遅延",
        "定型ターンでも数秒〜十数秒待機",
        [
            "• 判定：リアルタイム対話に非推奨",
            "• 挨拶でも思考が走り画面が長時間停止",
        ],
        Styles.SecondaryNeutral,
        Styles.WarningBold,
        Styles.DarkBold,
        phosphor.clock,
    ),
    (
        127.0,
        "★③ 適応型ルーター (Pattern A)",
        "{thinking: bool, response: str} 統合",
        "thinking=false (T1・2)：1回完結",
        "allow_partial 抽出で即時ストリーム",
        "thinking=true (T3)：並列 Stage-2",
        "受付1文先行表示 + 裏で low 推論連結",
        [
            "• 判定：★本番標準アーキテクチャ",
            "• 分岐 9/9 一致・計算 3/3 全問正解",
        ],
        Styles.PrimaryFlat,
        Styles.WhiteBold,
        Styles.White,
        phosphor.star,
    ),
]

for cx, title_s, sub_s, b1_t, b1_b, b2_t, b2_b, bullets, card_st, hdr_st, sub_st, ic_fn in cols:
    rectangle((cx, 46.8), width=45.6, height=43.2, style=card_st.patch(shape_r=1.6))
    ic_fn((cx - 19.2, 64.6), width=3.0, style=hdr_st)
    text((cx - 16.4, 64.6), title_s, style=hdr_st.patch(text_size=10.3, halign="left"))
    text((cx, 60.6), sub_s, style=sub_st.patch(text_size=10.0))

    rectangle((cx, 53.0), width=42.0, height=8.4, style=Styles.WhiteFlat.patch(shape_r=1.0))
    text((cx, 55.0), b1_t, style=Styles.DarkBold.patch(text_size=10.0))
    text((cx, 51.0), b1_b, style=Styles.Dark.patch(text_size=10.0))

    rectangle((cx, 42.6), width=42.0, height=8.4, style=Styles.WhiteFlat.patch(shape_r=1.0))
    text((cx, 44.6), b2_t, style=Styles.DarkBold.patch(text_size=10.0))
    text((cx, 40.6), b2_b, style=Styles.Dark.patch(text_size=10.0))

    b_style = (
        Styles.WhiteBold.patch(text_size=10.0, halign="left")
        if card_st == Styles.PrimaryFlat
        else Styles.Dark.patch(text_size=10.0, halign="left")
    )
    for idx, b_line in enumerate(bullets):
        text((cx - 20.6, 34.4 - idx * 4.2), b_line, style=b_style)

# Bottom 50-Turn Scalability Banner
rectangle((78.0, 12.8), width=145.6, height=17.2, style=Styles.PrimaryNeutral.patch(shape_r=1.5))
text(
    (78.0, 18.6),
    "50ターン連続PCサポート対話における推奨エンドツーエンド構成",
    style=Styles.DarkBold.patch(text_size=10.4),
)

steps = [
    (23.5, 31.0, "1. プレフィックス不変履歴", "append-only list[Content]", Styles.WhiteFlat),
    (59.5, 33.0, "2. 暗黙キャッシュ自動発動", "長大履歴でも自動で高率ヒット", Styles.SecondaryNeutral),
    (97.5, 35.0, "3. Pattern A 構造化ストリーム", "Warm 文法キャッシュ + 差分抽出", Styles.WhiteFlat),
    (134.0, 30.0, "4. 高速表示 & 高精度", "平坦な TTFT 推移 + 計算精度100%", Styles.WhiteFlat),
]
for sx, sw, s_top, s_bot, s_st in steps:
    rectangle((sx, 10.4), width=sw, height=9.2, style=s_st.patch(shape_r=1.0))
    text((sx, 12.4), s_top, style=Styles.DarkBold.patch(text_size=10.0))
    text((sx, 8.4), s_bot, style=Styles.Dark.patch(text_size=10.0))

line((39.0, 10.4), (43.0, 10.4), arrow_head="->", style=Styles.DarkBold)
line((76.0, 10.4), (80.0, 10.4), arrow_head="->", style=Styles.DarkBold)
line((115.0, 10.4), (119.0, 10.4), arrow_head="->", style=Styles.DarkBold)

save()
```

---

## 1.1 全検証スイートの主要ベンチマーク横断比較

本レポートで実施した3つのコア評価スイート（① 単発通信方式 × `ThinkingConfig` ベンチマーク、② 適応型 Thinking ルーター評価、③ 50ターン連続マルチターンPCサポート対話ベンチマーク）の代表レイテンシ指標（TTFT および Total 完了時間）を横断比較したのが図1-2である。

```drawlib align=center code=fold width=100% file=ch01_benchmark_comparison_chart_ja.png caption="図1-2: 全3検証スイート（単発呼び出し・適応型ルーター・50ターン連続対話）における代表構成の TTFT と Total 完了時間の横断比較"
from drawlib.canvas import save, setup
from drawlib.charts.bar import BarChart
from drawlib.icons import phosphor
from drawlib.shapes import rectangle
from drawlib.styles import Styles
from drawlib.text import text

setup(width=158, height=88, dpi=150)

# Outer structural frame
rectangle((79.0, 44.0), width=154.0, height=84.0, style=Styles.MutedDashed.patch(shape_r=2.0))
text(
    (79.0, 82.0),
    "全3検証スイート横断比較：初回トークン時間 (TTFT) vs. 全体完了時間 (Total)",
    style=Styles.DarkBold.patch(text_size=11.5),
)

categories = [
    "[単発] Stream t=0",
    "[単発] Block t=0",
    "[単発] Stream default",
    "[適応型] ★Pattern A",
    "[適応型] 固定 t=0 (計算リスク)",
    "[適応型] 固定 low",
    "[50ターン] ★Stream t=0",
    "[50ターン] Block t=0",
    "[50ターン] Stream default",
]

ttft_vals = [1205.0, 3360.0, 10430.0, 2340.0, 1879.0, 6290.0, 2460.0, 6424.0, 9838.0]
total_vals = [3192.0, 3360.0, 12006.0, 9505.0, 6398.0, 10986.0, 6323.0, 6424.0, 12335.0]

chart = BarChart(
    axis_line_style=Styles.Dark,
    axis_text_style=Styles.DarkBold.patch(text_size=10.0),
    grid_style=Styles.MutedDashed,
    value_text_style=Styles.DarkBold.patch(text_size=10.0),
    value_format="{:,.0f}",
    width=72.0,
    height=56.0,
    categories=categories,
    orientation="horizontal",
    bar_mode="group",
    bar_width_ratio=0.78,
    bar_r=0.35,
)
chart.configure_x_axis(
    min_value=0,
    max_value=16000,
    tick_step=4000,
    format="{:,.0f}",
)
chart.add_series(
    name="TTFT: 初回トークン表示 (ms)",
    values=ttft_vals,
    style=Styles.PrimaryFlat,
)
chart.add_series(
    name="Total: 全文生成完了 (ms)",
    values=total_vals,
    style=Styles.SecondaryNeutral,
)

chart.draw(xy=(31.0, 16.5))
text((67.0, 11.2), "経過時間 (ms)", style=Styles.DarkBold.patch(text_size=10.0))
chart.draw_legend(
    xy=(31.0, 75.5),
    text_style=Styles.DarkBold.patch(text_size=10.0),
    orientation="horizontal",
    swatch_width=3.4,
    swatch_height=1.9,
    item_gap=8.0,
)

# Right-side Neutral Analytical Panel
rectangle((130.5, 45.0), width=43.0, height=58.0, style=Styles.PrimaryNeutral.patch(shape_r=1.5))
text((130.5, 70.6), "スイート別の定量ハイライト", style=Styles.DarkBold.patch(text_size=10.5))

cards = [
    (
        58.8,
        "1. 単発呼び出し (第3章)",
        "• Stream t=0：TTFT 1,205 ms\n• Block t=0 (3,360 ms) 比 -64%\n• default は推論により大幅遅延",
        Styles.WhiteFlat,
    ),
    (
        42.6,
        "2. 適応型ルーター (第4章)",
        "• ★Pattern A：平均 TTFT 2,340 ms\n• Tier 3 算数精度 100% (3/3)\n• 固定 low (6,290ms) の待機を解消",
        Styles.WhiteFlat,
    ),
    (
        26.4,
        "3. 50ターン連続対話 (第5章)",
        "• ★Stream t=0：平均 2,460 ms (中央値 2.03s)\n• Block t=0 (6,424ms) 比 -62% 高速\n• 暗黙キャッシュが最大 90.6% ヒット",
        Styles.SecondaryNeutral,
    ),
]
for cy, c_hdr, c_body, c_st in cards:
    rectangle((130.5, cy), width=39.6, height=14.0, style=c_st.patch(shape_r=1.0))
    text((130.5, cy + 4.4), c_hdr, style=Styles.DarkBold.patch(text_size=10.0))
    text((112.2, cy - 1.5), c_body, style=Styles.Dark.patch(text_size=10.0, halign="left"))

# Bottom takeaway bar
rectangle((79.0, 5.8), width=148.0, height=6.4, style=Styles.SecondaryNeutral.patch(shape_r=1.2))
phosphor.lightning((8.5, 5.8), width=3.0, style=Styles.DarkBold)
text(
    (11.8, 5.8),
    "結論：Streaming × Pattern A（通常ターン t=0 / 複雑ターン並列 low）により、全シナリオで高速な初回応答と計算精度 100% を両立する。",
    style=Styles.DarkBold.patch(text_size=10.0, halign="left"),
)

save()
```

### 全検証スイート横断サマリー表

| 評価スイート・シナリオ | 方式・パラメータ構成 | 初回応答 (TTFT) | 全体完了 (Total) | 推論トークン (`ThTok`) | 品質・スケーラビリティ評価 | 判定 |
| :--- | :--- | ---: | ---: | ---: | :--- | :---: |
| **単発呼び出し**<br>(第3章・PC起動切り分け) | **Streaming `thinking=0`** | **`1,205 ms`** | `3,192 ms` | `0 tok` | 初回表示が Blocking 比 **`-64%`** 高速 | **★定型推奨** |
| 単発呼び出し | Blocking `thinking=0` | `3,360 ms` | `3,360 ms` | `0 tok` | 全文完了まで `3.36秒` 画面無応答 | バッチ用 |
| 単発呼び出し | Streaming `thinking=default` | `10,430 ms` | `12,006 ms` | `1,006 tok` | 内部推論により TTFT が大幅に増加 | 非推奨 |
| **適応型ルーター**<br>(第4章・難易度Tier 1〜3) | **★Pattern A (`{thinking, response}`)** | **`2,340 ms`**<br>(T3: `2,314 ms`) | `9,505 ms` | T1・2: `0`<br>T3: `901 tok` | 分岐 **`9/9`**・Tier 3 算数 **`3/3` (100%)**<br>Pydantic デコーダ型保証・API平均 `1.33回` | **★本番標準** |
| 適応型ルーター比較 | Pattern C (先頭タグ `[DIRECT]/[THINK]`) | `1,879 ms` | `8,843 ms` | T1・2: `0`<br>T3: `828 tok` | 分岐 `9/9`・計算 `3/3`。ただし構文保証なし・タグ露出リスクあり | 不採用 |
| 適応型ルーター比較 | Pattern B (1項目分離 `{thinking}`) | `6,177 ms`<br>(T3: `11,488 ms`) | `11,535 ms` | T1・2: `0`<br>T3: `628 tok` | 常時2回直列呼び出し（`calls=2.0`）により初動が大幅遅延 | 不採用 |
| 適応型ルーター比較 | 固定 `thinking=0` (`base_0`) | `1,879 ms` | `6,398 ms` | `0 tok` | **Tier 3 複雑計算で自己回帰の罠（結論先出しの誤算リスク）** | 不採用 |
| 適応型ルーター比較 | 固定 `thinking=low` (`base_low`) | `6,290 ms`<br>(T3: `9,289 ms`) | `10,986 ms` | 平均 `439 tok` | Tier 3 計算は `3/3` 正解だが、最大 `12.2秒` 画面がフリーズ | 非推奨 |
| **50ターン連続対話**<br>(第5章・PCサポート対話) | **★Streaming `thinking=0`** | **`2,460 ms`**<br>(中央値 `2,029 ms`) | **`6,323 ms`** | `19 tok`<br>(T2–50: `0`) | Blocking 比 **`-3,964 ms` (`-62%`)** 高速。暗黙キャッシュ最大 **`90.6%`** ヒット | **★長期推奨** |
| 50ターン連続対話 | Blocking `thinking=0` | `6,424 ms` | `6,424 ms` | `0 tok` | 平均 `753 文字` の生成完了まで毎ターン無応答で待機 | バッチ用 |
| 50ターン連続対話 | Streaming `thinking=default` | `9,838 ms` | `12,335 ms` | 平均 `858 tok` | 推論完了まで約9.8秒ストリームが停止 | 非推奨 |

---

## 1.2 本番システム設計に向けた5つの推奨アクション

実機検証から導かれた、Google AI Studio（`gemini-3.8-flash`）を本番組み込みする際のアーキテクチャ設計原則を以下の5点に要約する。

1. **ユーザー向け対話 UI は必ず `generate_content_stream`（Streaming）を採用する**：
   単発呼び出しでも Blocking `thinking=0`（`3,360 ms`）に対して Streaming `thinking=0`（`TTFT 1,205 ms`）は **`-64%`** 早く表示を開始する。PCテクニカルサポートのように回答が平均 `753 文字` の詳細な手順解説に及ぶ50ターン対話では、Streaming `thinking=0`（平均 TTFT `2,460 ms`・中央値 `2,029 ms`）が Blocking（`6,424 ms`）に対して毎ターン **`3.96 秒`（`62%`）** 先行し、残りのデコード時間をユーザーの読解時間の裏へ完全に隠蔽できる。
2. **`ThinkingConfig` の無指定（`default`）運用を避け、明示的に制御する**：
   `gemini-3.8-flash` のデフォルト設定（`thinking=default`）は動的推論が有効化されており、単発でも `467〜1,006 トークン`、50ターン対話では平均 `858〜954 トークン`（最大 `2,237 トークン`）の内部推論が発生する。内部推論に要した時間はすべて初動（TTFT）へ直列に加算されるため、通常ターンでは必ず `ThinkingConfig(thinking_budget=0)` を明示指定する。
3. **「速度と計算精度の二律背反」は Pattern A（Pydantic 2項目統合ストリーム）で解決する**：
   `thinking=0` 固定では多段階のPC修理vs買い替え損益比較やデータ転送時間・保守契約試算（Tier 3）で自己回帰の誤算リスクが残り、`thinking=low` 固定では全9問平均 TTFT が `6,290 ms`（最大 `12,155 ms`）まで悪化する。`AdaptiveStreamResponse(thinking: bool, response: str)` を `pydantic_core.from_json(..., allow_partial="trailing-strings")` で逐次パースする **Pattern A** を採用すれば、通常質問（Tier 1・2）は API 1回呼び出しで即座に回答をストリームし、複雑計算（Tier 3）では `thinking=True` を検知した瞬間に Stage-2（`thinking="low"`）をバックグラウンドで並列起動しつつ Stage-1 の受付1文を **`TTFT 2,314 ms`** で先行表示できる（分岐精度 **`100%`**、計算精度 **`100%`**）。
4. **Pydantic スキーマは「ルーティング項目を先頭・本文を後方」に配置し、起動時に1回 Warmup する**：
   `response_schema` 指定時は、`thinking: bool` を第1フィールド、`response: str` を可変長リストより前に定義した上で、コンテナ起動時に1回ダミー呼び出しを実行して FSM キャッシュを Warm 化しておく設計が最適である。
5. **マルチターン対話では履歴プレフィックスを不変（append-only）に保ち、暗黙キャッシュを最大化する**：
   `system_instruction` と過去ターンの `history: list[types.Content]` を先頭から書き換えずに追記し続けることで、追加実装ゼロで **Implicit Context Caching（`cached_content_token_count`）** が自動発動し、50ターンに及ぶ長大なPCトラブルシューティング対話でも TTFT の増加を最小限に抑え込むことができる。
