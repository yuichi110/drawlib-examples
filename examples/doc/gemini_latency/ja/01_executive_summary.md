# 1. エグゼクティブサマリー

本レポートは、Google AI Studio（`google-genai` SDK、`genai.Client(api_key=GEMINI_KEY)`）上の **`gemini-3.8-flash`**（および現行5モデル）を用いた対話型AIシステム（PCテクニカルサポート・トラブルシューティング対話）において、**「高速な初期応答（TTFT）」「多段階算数・条件比較（修理vs買い替え損益・データ転送時間・保守契約試算）の100%の計算正確性」「50ターン連続対話における平坦なレイテンシスケーリング」** の3要件を同時に達成するためのアーキテクチャ検証報告書である。実機 API 計測ログ（単発 `ThinkingConfig` 18試行、現行5モデル×全 `thinking_level`＋`budget=0` 横断比較 220試行、適応型ルーティング `low → high` 45試行、50ターン連続PCサポート Streaming チャット 150試行）の定量分析から、単発・マルチターンを問わず **`Streaming`（`generate_content_stream`）を基本通信方式とし、Stage 1（`low`）の Pydantic 2フィールド構造化ストリーム `{thinking: bool, response: str}` と Stage 2（`high`）の並列起動を組み合わせた「適応型 Thinking ルーター（Pattern A）」を標準採用する構成** を第一推奨アーキテクチャとして結論づけた。

```drawlib align=center code=fold width=100% file=ch01_exec_summary_hero_ja.png caption="図1-1: エンドツーエンド方式選定マトリクス — 固定設定（low / high）の二律背反と適応型ルーター（Pattern A）＋50ターン暗黙キャッシュ統合構成"
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
    "エンドツーエンド方式選定マトリクス：固定設定 (low / high) vs. 適応型 Thinking ルーター (Pattern A)",
    style=Styles.DarkBold.patch(text_size=11.2),
)

cols = [
    (
        29.0,
        "① 固定 thinking=low",
        "Streaming + thinking_level='low'",
        "単発・50ターン速度：◎ 高速",
        "TTFT 約2.3〜2.5s で即座にストリーム",
        "複雑計算・比較 (Tier 3)：× 推論浅",
        "推論トークンほぼ0で多段検証が不足",
        [
            "• 判定：定型案内・簡易切り分け用",
            "• 複数条件の算数・比較には不十分",
        ],
        Styles.Neutral,
        Styles.DangerBold,
        Styles.DarkBold,
        phosphor.x_circle,
    ),
    (
        78.0,
        "② 固定 thinking=high",
        "常時 1,200〜3,800 tok の深層推論",
        "複雑計算・比較 (Tier 3)：◎ 3/3",
        "深い内部思考により計算整合性を確保",
        "初期応答 (TTFT)：× 大幅遅延",
        "単発平均 13.9s / 50T平均 21.2s 待機",
        [
            "• 判定：リアルタイム対話に非推奨",
            "• 定型80%の質問でも約17秒フリーズ",
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
        "thinking=false (定型)：low 1回完結",
        "allow_partial 抽出で即時ストリーム",
        "thinking=true (複雑)：並列 Stage-2",
        "受付1文先行 (~2.3–2.8s) + 裏で high",
        [
            "• 判定：★本番標準アーキテクチャ",
            "• 単発 9/9・50T 50/50 (100%) 一致",
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
    "50ターン連続PCサポート Streaming 対話における推奨エンドツーエンド構成",
    style=Styles.DarkBold.patch(text_size=10.4),
)

steps = [
    (23.5, 31.0, "1. プレフィックス不変履歴", "append-only list[Content]", Styles.WhiteFlat),
    (59.5, 33.0, "2. 暗黙キャッシュ自動共有", "Stage 1→2 で最大90.2%ヒット", Styles.SecondaryNeutral),
    (97.5, 35.0, "3. Pattern A (low → high)", "定型40Tは1回・計算10Tは並列", Styles.WhiteFlat),
    (134.0, 30.0, "4. 高速表示 & 深層推論", "TTFT 2.62s (-87.6%短縮)", Styles.WhiteFlat),
]
for sx, sw, s_top, s_bot, s_st in steps:
    rectangle((sx, 10.4), width=sw, height=9.2, style=s_st.patch(shape_r=1.0))
    text((sx, 12.4), s_top, style=Styles.DarkBold.patch(text_size=9.8))
    text((sx, 8.4), s_bot, style=Styles.Dark.patch(text_size=9.5))

line((39.0, 10.4), (43.0, 10.4), arrow_head="->", style=Styles.DarkBold)
line((76.0, 10.4), (80.0, 10.4), arrow_head="->", style=Styles.DarkBold)
line((115.0, 10.4), (119.0, 10.4), arrow_head="->", style=Styles.DarkBold)

save()
```

---

## 1.1 全検証スイートの主要ベンチマーク横断比較

本レポートで実施した3つのコア評価スイート（① 単発通信方式 × `ThinkingConfig` ベンチマーク、② 適応型 Thinking ルーター `low → high` 評価、③ 50ターン連続マルチターンPCサポート Streaming 対話ベンチマーク）の代表レイテンシ指標（初期応答 `TTFT` および完了時間 `Total`）を横断比較したのが図1-2である。

```drawlib align=center code=fold width=100% file=ch01_benchmark_comparison_chart_ja.png caption="図1-2: 全3検証スイート（単発呼び出し・適応型ルーター・50ターン連続 Streaming 対話）における代表構成の初期応答 (TTFT) と完了時間 (Total) の横断比較"
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
    "全3検証スイート横断比較：初期応答時間 (TTFT) vs. 完了時間 (Total)",
    style=Styles.DarkBold.patch(text_size=11.5),
)

categories = [
    "[単発] Stream low",
    "[単発] Block low",
    "[単発] Stream high",
    "[第4章] ★Pattern A (low→high)",
    "[第4章] 固定 low (base_low)",
    "[第4章] 固定 high (base_high)",
    "[50T] ★Adaptive (Pattern A)",
    "[50T] (1) 固定 Stream low",
    "[50T] (1) 固定 Stream high",
]

ttft_vals = [1806.0, 3539.0, 9912.0, 2336.0, 2473.0, 13868.0, 2618.0, 2310.0, 21173.0]
total_vals = [3633.0, 3539.0, 11488.0, 11231.0, 6419.0, 18430.0, 12034.0, 6589.0, 23827.0]

chart = BarChart(
    axis_line_style=Styles.Dark,
    axis_text_style=Styles.DarkBold.patch(text_size=9.8),
    grid_style=Styles.MutedDashed,
    value_text_style=Styles.DarkBold.patch(text_size=9.8),
    value_format="{:,.0f}",
    width=70.0,
    height=56.0,
    categories=categories,
    orientation="horizontal",
    bar_mode="group",
    bar_width_ratio=0.78,
    bar_r=0.35,
)
chart.configure_x_axis(
    min_value=0,
    max_value=26000,
    tick_step=6500,
    format="{:,.0f}",
)
chart.add_series(
    name="初期応答 TTFT (ms)",
    values=ttft_vals,
    style=Styles.PrimaryFlat,
)
chart.add_series(
    name="完了時間 Total (ms)",
    values=total_vals,
    style=Styles.SecondaryNeutral,
)

chart.draw(xy=(33.0, 16.5))
text((68.0, 11.2), "経過時間 (ms)", style=Styles.DarkBold.patch(text_size=10.0))
chart.draw_legend(
    xy=(33.0, 75.5),
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
        "1. 単発 & 5モデル横断 (第3章)",
        "• Stream low：TTFT 1,806 ms\n• 5モデル×22構成 (budget=0含) 比較\n• 3.5-lite は budget=0 が 400 エラー",
        Styles.WhiteFlat,
    ),
    (
        42.6,
        "2. 適応型ルーター (第4章)",
        "• ★Pattern A：平均 TTFT 2,336 ms\n• 固定 high (13,868ms) 比 -83.2%\n• 分岐 9/9・複雑計算 3/3 全問正解",
        Styles.WhiteFlat,
    ),
    (
        26.4,
        "3. 50ターン Streaming (第5章)",
        "• ★Adaptive：TTFT 2,618 ms (-87.6%)\n• 完了中央値 4,990 ms (high比 -79.1%)\n• Stage 1→2 キャッシュ最大 90.2%",
        Styles.SecondaryNeutral,
    ),
]
for cy, c_hdr, c_body, c_st in cards:
    rectangle((130.5, cy), width=39.6, height=14.0, style=c_st.patch(shape_r=1.0))
    text((130.5, cy + 4.4), c_hdr, style=Styles.DarkBold.patch(text_size=10.0))
    text((112.2, cy - 1.5), c_body, style=Styles.Dark.patch(text_size=9.8, halign="left"))

# Bottom takeaway bar
rectangle((79.0, 5.8), width=148.0, height=6.4, style=Styles.SecondaryNeutral.patch(shape_r=1.2))
phosphor.lightning((8.5, 5.8), width=3.0, style=Styles.DarkBold)
text(
    (11.8, 5.8),
    "結論：Streaming × Pattern A（Stage 1 low → 並列 Stage 2 high）により、全シナリオで ~2.3–2.6s の初期応答と深層計算精度を両立する。",
    style=Styles.DarkBold.patch(text_size=9.8, halign="left"),
)

save()
```

### 全検証スイート横断サマリー表

| 評価スイート・シナリオ | 方式・パラメータ構成 | 初期応答 (TTFT) | 完了時間 (Total) | 推論トークン (`ThTok`) | 品質・スケーラビリティ評価 | 判定 |
| :--- | :--- | ---: | ---: | ---: | :--- | :---: |
| **単発呼び出し**<br>(第3章・PC起動切り分け) | **Streaming `thinking_level="low"`** | **`1,806 ms`** | `3,633 ms` | `135 tok` | 初回表示が Blocking 比 **`-49%`** 高速（`minimal` なら `1,304 ms`） | **★定型推奨** |
| 単発呼び出し | Blocking `thinking_level="low"` | `3,539 ms` | `3,539 ms` | `124 tok` | 全文完了まで `3.54秒` 画面無応答 | バッチ用 |
| 単発呼び出し | Streaming `thinking_level="high"` | `9,912 ms` | `11,488 ms` | `946 tok` | 内部推論により単発でも TTFT が約10秒へ増大 | 単発固定は非推奨 |
| **5モデル横断比較**<br>(第3章・22構成×10問) | **`3.5-flash-lite` / `3.8-flash` / `4`系**<br>(`thinking_level` + 非推奨 `budget=0`) | `706 ms`〜`30,368 ms` | `2,240 ms`〜`34,637 ms` | `0`〜`2,369 tok` | `3.5-flash-lite` は `budget=0` が **`400 INVALID_ARGUMENT`**（`minimal` 必須）。他4モデルは `low` 相当へフォールバック | `thinking_level` へ統一 |
| **適応型ルーター**<br>(第4章・`3.8-flash` `low→high`) | **★Pattern A (`{thinking, response}`)** | **`2,336 ms`**<br>(T3: `2,337 ms`) | `11,231 ms`<br>(T1・2: `6,625 ms`) | T1・2: `95`<br>T3: `1,392 tok` | 分岐 **`9/9`**・Tier 3 算数 **`3/3` (100%)**<br>固定 `high` 比で初期応答 **`-83.2%`** 短縮 | **★本番標準** |
| 適応型ルーター比較 | Pattern C (先頭タグ `[DIRECT]/[THINK]`) | `2,063 ms` | `10,167 ms` | T1・2: `66`<br>T3: `1,197 tok` | 分岐 `9/9`・計算 `3/3`。ただし構文保証なし・タグ露出リスクあり | 不採用 |
| 適応型ルーター比較 | Pattern B (1項目分離 `{thinking}`) | `6,770 ms`<br>(T3: `13,865 ms`) | `11,648 ms` | T1・2: `172`<br>T3: `1,355 tok` | 常時2回直列呼び出し（`calls=2.0`）により初動が大幅遅延 | 不採用 |
| 適応型ルーター比較 | 固定 `thinking_level="low"` (`base_low`) | `2,473 ms` | `6,419 ms` | 平均 `91 tok` | 高速だが Tier 3 複雑計算で深い推論が行われない | 複雑計算に不適 |
| 適応型ルーター比較 | 固定 `thinking_level="high"` (`base_high`) | `13,868 ms`<br>(T3: `20,037 ms`) | `18,430 ms` | 平均 `1,201 tok` | Tier 3 計算は深いが、定型質問でも `9.8〜20.0秒` 画面が停止 | 固定運用は非推奨 |
| **50ターン Streaming**<br>(第5章・定型40T＋計算10T) | **★`(2)` `adaptive_pat_a` (Pattern A)** | **`2,618 ms`**<br>(中央値 `2,420 ms`) | **`12,034 ms`**<br>(中央値 **`4,990 ms`**) | 平均 **`758 tok`**<br>(`high`比 `-61.7%`) | 分岐 **`50/50 (100%)`**。定型40Tは `5,008 ms` 完結、計算10Tは並列 `high`（キャッシュ最大 **`90.2%`** 共有） | **★長期対話標準** |
| 50ターン Streaming | `(1)` `streaming_low` (`low` 固定) | **`2,310 ms`**<br>(中央値 `2,084 ms`) | `6,589 ms`<br>(中央値 `6,583 ms`) | `0 tok` | 全ターン高速だが、10回の複雑計算ターンでも推論トークン `0` | 定型専用 |
| 50ターン Streaming | `(1)` `streaming_high` (`high` 固定) | `21,173 ms`<br>(計算10T: `38,033 ms`) | `23,827 ms`<br>(中央値 `23,887 ms`) | 平均 `1,981 tok` | 定型40ターンでも平均 `16,958 ms`（`1,534 tok`）初動がフリーズ | 非推奨 |

---

## 1.2 本番システム設計に向けた5つの推奨アクション

実機検証から導かれた、Google AI Studio（`gemini-3.8-flash` および Gemini 3.5 / 4 シリーズ）を本番組み込みする際のアーキテクチャ設計原則を以下の5点に要約する。

1. **ユーザー向け対話 UI はすべて `generate_content_stream`（Streaming）に統一する**：
   単発呼び出しでも Blocking `low`（`3,539 ms`）に対して Streaming `low`（`TTFT 1,806 ms`）は **`-49%`** 早く表示を開始し、50ターン連続対話でも初期応答を約 `2.3〜2.6 秒` に抑えながら残りの生成時間をユーザーの読解時間の裏へ隠蔽できる。
2. **非推奨の `thinking_budget=0` ではなく、`thinking_level`（`minimal` / `low` / `medium` / `high`）で明示制御する**：
   第3章の5モデル横断検証（220試行）で実証した通り、レガシーな `thinking_budget=0` は **`gemini-3.5-flash-lite` で `400 INVALID_ARGUMENT` エラー**となり、他4モデルでも内部的に `low` 相当へフォールバックされる。ゼロ推論が必要な場合は `thinking_level="minimal"`（`3.5-flash-lite` / `3.8-flash`）、軽量ルーティングには `thinking_level="low"` を明示指定すべきである。
3. **「`low` と `high` の二律背反」は第4章の Pattern A（Pydantic 2項目統合ルーター `low → high`）で解決する**：
   `low` 固定では複雑計算ターンで深い推論が行われず、`high` 固定では単発平均 `13.9 秒`・50ターン平均 `21.2 秒` も画面が停止する。`AdaptiveStreamResponse(thinking: bool, response: str)` を Stage 1（`3.8-flash [low]`）でストリームしつつ `thinking=True` 検知時に Stage 2（`3.8-flash [high]`）を並列起動する **Pattern A** により、全50ターン平均 TTFT **`2,618 ms`（`high` 比 `-87.6%`）**・完了中央値 **`4,990 ms`（`-79.1%`）**・分岐一致 **`50/50 (100%)`** を達成できる。
4. **要件に応じて Stage 1 を `3.5-flash-lite`、Stage 2 を `Gemini 4` シリーズへスケールさせる**：
   第4章（4.1節）で整理した通り、初期応答をさらに短縮（`~1.0〜1.5s`）したい場合は Stage 1 に **`gemini-3.5-flash-lite`（`minimal` / `low`）** を採用し、複雑な業務システムでより深い推論が必要な場合は Stage 2 に **`gemini-4-hydrogen [high]`** や **`gemini-4-carbon [medium / high]`** を組み合わせる構成が推奨される。
5. **マルチターン対話では履歴プレフィックスを不変（append-only）に保ち、Stage 1→2 間で暗黙キャッシュを共有する**：
   `system_instruction` を Stage 1・Stage 2 間で完全一致させ、`history: list[types.Content]` を追記専用（append-only）に保つことで、ターン8〜9（約2,710トークン）から **Implicit Context Caching（`cached_content_token_count`）** が自動発動し、複雑計算ターンの Stage 2（`high`）でも最大 **`90.2%`（ターン50で `18,890 cached tokens`）** のキャッシュヒット率を享受できる。

