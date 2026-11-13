# 4. Adaptive Thinking Router パターン

第3章では、`gemini-3.8-flash` において `thinking=0` 固定は高速であるものの多段階の算数・条件比較（Tier 3）で内部検算なしの結論先出しリスクを抱え、逆に `thinking=low` 固定は事前検算（`3/3` 完全検証）を達成するものの、定型対話（Tier 1・2）に不要な推論遅延を加算し、Tier 3 では最大 `12.16 秒` にわたり画面が無応答で凍結するジレンマを明らかにした。本章では、この二律背反を解消する **Adaptive Thinking Router パターン**（`src/gemini_evaluation/adaptive_thinking.py`）を提案し、3つの候補アーキテクチャ（パターンA・B・C）の設計、9設問×5方式＝全45実行のベンチマーク、および2段階並列ストリームの軌跡解析を通じて、**パターンA（2フィールド統合 Pydantic スキーマ `{thinking: bool, response: str}` ＋ Stage 2 並列チェイニング）** が最適解であることを実証する。

```drawlib align=center code=fold width=100% file=ch04_adaptive_architectures_hero_ja.png caption="図4-1: Adaptive Thinking Router 候補3方式（Pattern A: 2フィールド統合 Pydantic・Pattern B: 1フィールド直列ルーター・Pattern C: 先頭タグ）のシーケンス・アーキテクチャ比較"
from drawlib.canvas import save, setup
from drawlib.icons import phosphor
from drawlib.lines import line
from drawlib.shapes import rectangle
from drawlib.styles import Styles
from drawlib.text import text

setup(width=172, height=94, dpi=150)

# Outer structural frame
rectangle((86.0, 47.0), width=168.0, height=90.0, style=Styles.MutedDashed.patch(shape_r=2.0))
text(
    (86.0, 87.6),
    "Adaptive Thinking Router 3方式（Pattern A・B・C）のアーキテクチャとレイテンシー比較",
    style=Styles.DarkBold.patch(text_size=12.0),
)

# Top UX Target Bar
rectangle((86.0, 79.2), width=160.0, height=8.8, style=Styles.Neutral.patch(shape_r=1.2))
phosphor.gauge((10.5, 81.0), width=3.2, style=Styles.PrimaryBold)
text(
    (14.0, 81.0),
    "対話 UX 目標基準：① 初回トークン表示 TTFT を最小化（数秒〜12秒の無応答フリーズを排除） / ② 100% のスキーマ型安全性と事前検算",
    style=Styles.PrimaryBold.patch(text_size=10.5, halign="left"),
)
text(
    (14.0, 77.0),
    "Stage 1 (thinking=0) で即時応答または受付ブリッジ文を表示しつつ、複雑計算時のみ裏で Stage 2 (thinking=low) を並列実行",
    style=Styles.Dark.patch(text_size=10.0, halign="left"),
)

# 3 Architecture Columns
cols = [
    (
        33.0,
        "★ Pattern A [推奨・標準採用]",
        "2フィールド統合 Pydantic + 並列 Stage 2",
        "Stage 1: thinking=0 + JSON Schema",
        "{thinking: bool, response: str} を逐次解析",
        "false: 1回呼出で即時ストリーム完結",
        "不要な内部思考を 0 tok に完全排除",
        "true: 受付1文 (~2.3s) + Stage 2 並列",
        "asyncio.create_task で low 思考を裏へ隠蔽",
        [
            "• 全9問平均 TTFT: 2,340 ms (low比 -63%)",
            "• Tier 3 の最大12秒フリーズを受付文で解消",
            "• デコーダ型保証・計算 3/3 完全検証 [◎]",
        ],
        Styles.PrimaryFlat,
        Styles.WhiteBold,
        Styles.White,
        Styles.SecondaryNeutral,
        phosphor.star,
    ),
    (
        86.0,
        "Pattern B [比較：直列ルーター]",
        "1フィールド分離 {thinking: bool} + Stream",
        "Stage 1: ルーター専用 Blocking 呼出",
        "generate_content で {thinking} のみ判定",
        "Stage 2: 判定完了後に2回目を直列呼出",
        "false 時も 2回往復 (T1–2 TTFT 3,522 ms)",
        "true 時はルーター + low 思考が直列加算",
        "Tier 3 平均 TTFT 11,488 ms (最大 12.6秒)",
        [
            "• 全9問平均 TTFT: 6,177 ms (直列ペナルティ)",
            "• 常時 2 API Call で直列 RTT ペナルティ",
            "• 判定：初動遅延が大きく不採用 [×]",
        ],
        Styles.Neutral,
        Styles.DangerBold,
        Styles.DarkBold,
        Styles.WhiteFlat,
        phosphor.git_branch,
    ),
    (
        139.0,
        "Pattern C [比較：非JSONタグ]",
        "先頭プレフィックス [DIRECT] / [THINK]",
        "Stage 1: thinking=0 平文ストリーム",
        "プロンプト指示のみで先頭タグを出力",
        "[DIRECT]: タグ除去後に平文ストリーム",
        "TTFT 1,920 ms / スキーマ検証なし",
        "[THINK]: 受付1文 (~1.8s) + Stage 2 並列",
        "進行構造は A と同じだがスキーマ制約なし",
        [
            "• 全9問平均 TTFT: 1,879 ms (A と差 0.46s)",
            "• 表記揺れで生タグ露出・長期履歴で欠落",
            "• 判定：差 <0.5s のため安全な A に統一",
        ],
        Styles.SecondaryNeutral,
        Styles.SecondaryBold,
        Styles.DarkBold,
        Styles.WhiteFlat,
        phosphor.tag,
    ),
]

for (
    cx,
    title_s,
    sub_s,
    s1_t,
    s1_b,
    s2_t,
    s2_b,
    s3_t,
    s3_b,
    bullets,
    card_st,
    hdr_st,
    sub_st,
    mid_st,
    ic_fn,
) in cols:
    rectangle((cx, 42.5), width=51.0, height=58.0, style=card_st.patch(shape_r=1.6))
    ic_fn((cx - 21.5, 67.8), width=3.2, style=hdr_st)
    text((cx + 1.5, 67.8), title_s, style=hdr_st.patch(text_size=10.5))
    text((cx, 64.0), sub_s, style=sub_st.patch(text_size=10.0))

    # Step Box 1
    rectangle((cx, 56.5), width=48.2, height=8.6, style=Styles.WhiteFlat.patch(shape_r=1.0))
    text((cx, 58.4), s1_t, style=Styles.PrimaryBold.patch(text_size=10.0))
    text((cx, 54.6), s1_b, style=Styles.Dark.patch(text_size=10.0))

    arr_st = Styles.WhiteBold.patch(line_width=1.8) if card_st == Styles.PrimaryFlat else Styles.DarkBold.patch(line_width=1.8)
    line((cx, 52.2), (cx, 49.4), arrow_head="->", style=arr_st)

    # Step Box 2
    rectangle((cx, 45.0), width=48.2, height=8.6, style=mid_st.patch(shape_r=1.0))
    text((cx, 46.9), s2_t, style=Styles.DarkBold.patch(text_size=10.0))
    text((cx, 43.1), s2_b, style=Styles.Dark.patch(text_size=10.0))

    line((cx, 40.7), (cx, 37.9), arrow_head="->", style=arr_st)

    # Step Box 3
    rectangle((cx, 33.5), width=48.2, height=8.6, style=Styles.WhiteFlat.patch(shape_r=1.0))
    text((cx, 35.4), s3_t, style=Styles.SecondaryBold.patch(text_size=10.0))
    text((cx, 31.6), s3_b, style=Styles.Dark.patch(text_size=10.0))

    b_style = (
        Styles.White.patch(text_size=10.0, halign="left")
        if card_st == Styles.PrimaryFlat
        else Styles.Dark.patch(text_size=10.0, halign="left")
    )
    for idx, b_line in enumerate(bullets):
        text((cx - 22.8, 25.5 - idx * 4.2), b_line, style=b_style)

# Bottom conclusion bar
rectangle((86.0, 6.2), width=160.0, height=6.4, style=Styles.PrimaryNeutral.patch(shape_r=1.2))
phosphor.shield_check((10.5, 6.2), width=3.2, style=Styles.PrimaryBold)
text(
    (14.0, 6.2),
    "結論：Pattern A は平均 TTFT 2,340 ms (Base Low 比 -63%) で C との差も 461 ms (<0.5s) に収まり、型安全性と応答速度を両立する。",
    style=Styles.DarkBold.patch(text_size=10.0, halign="left"),
)

save()
```

---

## 4.1 UX レイテンシー目標と3つの候補アーキテクチャ（Pattern A・B・C）

### 認知 UX の応答時間閾値と設計ターゲット

対話型テクニカルサポート UI において、私たちが目指す Adaptive Thinking Router の定量的ゴールは以下の2点に集約される。
1. **すべての難易度ティアで数秒〜12秒におよぶ内部推論中の画面フリーズを解消し、初回表示 TTFT を `thinking=0` 水準に抑えること**。
2. **非構造化の最速ベースライン（先頭タグ方式）に対する TTFT オーバーヘッドを `< 0.5 秒`（人間の体感弁別閾値以下）に抑えつつ、100% のスキーマ型安全性と計算正確性を保証すること**。

### 候補3方式（Pattern A・B・C）の構造比較

`src/gemini_evaluation/adaptive_thinking.py` では、Google AI Studio（`genai.Client(api_key=GEMINI_KEY)`、`gemini-3.8-flash`）上で以下の3つの適応型アーキテクチャを実装した（図4-1）。

1. **Pattern A（推奨・標準採用：2フィールド統合 Pydantic `{thinking: bool, response: str}` ＋ 並列 Stage 2 チェイニング）**
   - **Stage 1** として `thinking_budget=0` かつ `response_schema=AdaptiveStreamResponse` を指定した単一の `generate_content_stream` を開始し、到着する JSON チャンクを Rust 製 `pydantic_core.from_json(..., allow_partial="trailing-strings")` でインクリメンタルに解析する。
   - **`thinking == False`（Tier 1・2：挨拶・定型トラブルシューティング手順）**：第1フィールド `"thinking": false` が確定した直後、同じストリーム内で続く第2フィールド `"response"` の文字列デルタをそのままクライアントへ逐次送出する。**API 呼び出しは1回のみで完結**する。
   - **`thinking == True`（Tier 3：複雑な多段階計算）**：`"thinking": true` が確定した瞬間に、`asyncio.create_task()` でバックグラウンドの **Stage 2（`thinking=low` の平文ストリーム）を並列起動** する。同時に Stage 1 は「ご質問ありがとうございます。ご提示いただいた条件を整理して詳しく試算いたします。」という1文（45〜70文字）のブリッジメッセージのみを出力して直ちに終了する。ユーザーがブリッジメッセージを読んでいる間に Stage 2 が内部推論（`755〜951 tok`）を完了し、シームレスに計算本編のストリームを連結する。
2. **Pattern B（比較対照：1フィールド直列ルーター `{thinking: bool}` ＋ Stage 2 ストリーム）**
   - 部分 JSON パースを行わず、第1段階として 1フィールドの `ThinkingDecision(thinking: bool)` をブロッキング呼び出し（`generate_content`）で判定し、その結果を見てから第2段階の `generate_content_stream`（`thinking=0` または `thinking=low`）を直列に呼び出す方式。
   - 実装は単純だが、**簡単な挨拶であっても必ず2回の API 往復（`calls=2`）が直列に発生** するため、全9問平均 TTFT は **`6,177 ms`**（Tier 3 では **`11,488 ms`**）まで悪化する。
3. **Pattern C（比較対照：非 JSON 先頭タグ `[DIRECT]` / `[THINK]`）**
   - `response_schema` を使わず、システムプロンプトの指示のみで先頭に `[DIRECT]` または `[THINK]` タグを出力させ、文字列スライスでタグを除去してルーティングする方式。
   - 全9問平均 TTFT は **`1,879 ms`** で、Pattern A（**`2,340 ms`**）との差は **`461 ms`（`< 0.5 秒`）** に収まる。一方で、Pattern C には「タグ表記揺れによる画面への生タグ露出リスク」や「長期マルチターン対話でのタグ欠落ドリフト」という重大な運用上の弱点がある。

---

## 4.2 全45実行（9設問 × 5方式）の実測ベンチマーク評価

`src/gemini_evaluation/benchmark_adaptive_thinking.py` により、Tier 1（3問）・Tier 2（3問）・Tier 3（3問）の計9問に対して、固定ベースライン2方式（`base_0`, `base_low`）と適応型3方式（`pat_a_pydantic_2f`, `pat_b_pydantic_1f`, `pat_c_tag`）の **全45実行（成功率 100%、適応型3方式すべてでルーティング正解率 9/9＝100%）** を計測した。難易度ティア別の平均 TTFT と平均完了時間（Total）を比較したグループ棒グラフを図4-2に示す。

```drawlib align=center code=fold width=100% file=ch04_tier_latency_barchart_ja.png caption="図4-2: 難易度ティア別（Tier 1・Tier 2・Tier 3・全9問平均）× 全5方式における平均 TTFT（左）と平均完了時間 Total（右）の比較"
from statistics import mean

from drawlib.canvas import save, setup
from drawlib.charts.bar import BarChart
from drawlib.icons import phosphor
from drawlib.shapes import rectangle
from drawlib.styles import Styles
from drawlib.text import text
from drawlib.utils import load_adaptive_runs

setup(width=172, height=112, dpi=150)

# Outer structural frame
rectangle((86.0, 56.0), width=168.0, height=108.0, style=Styles.MutedDashed.patch(shape_r=2.0))
text(
    (86.0, 105.8),
    "全45実行ベンチマーク：難易度ティア別の平均 TTFT (左) と 平均完了時間 Total (右)",
    style=Styles.DarkBold.patch(text_size=12.0),
)

runs = load_adaptive_runs()
tier_groups = [
    ("tier1_simple", "Tier 1: 挨拶"),
    ("tier2_procedure", "Tier 2: 手続き"),
    ("tier3_complex", "Tier 3: 複雑計算"),
    ("all", "全9問平均"),
]
categories = [lbl for _, lbl in tier_groups]


def calc_means(m_key: str, metric: str) -> list[float]:
    out: list[float] = []
    for tk, _ in tier_groups:
        sub = [r for r in runs if r["method_key"] == m_key and (tk == "all" or r["tier"] == tk)]
        out.append(float(round(mean(float(r[metric]) for r in sub))))
    return out


# 2-row Legend at top
rectangle((86.0, 97.2), width=160.0, height=9.2, style=Styles.Neutral.patch(shape_r=1.2))

leg_row1 = [
    (10.0, Styles.PrimaryFlat, "★ Pattern A: 2F統合 {thinking, response} [推奨]"),
    (92.0, Styles.TealFlat, "Pattern C: 先頭タグ [DIRECT]/[THINK]"),
]
for lx, st, ltxt in leg_row1:
    rectangle((lx, 99.3), width=3.6, height=2.0, style=st.patch(shape_r=0.3))
    text((lx + 2.8, 99.3), ltxt, style=Styles.DarkBold.patch(text_size=10.0, halign="left"))

leg_row2 = [
    (10.0, Styles.SuccessFlat, "Base 0: 固定 thinking=0 (内部検算なし)"),
    (68.0, Styles.WarningFlat, "Base Low: 固定 thinking=low"),
    (118.0, Styles.DangerFlat, "Pattern B: 1F直列ルーター (常時2回呼出)"),
]
for lx, st, ltxt in leg_row2:
    rectangle((lx, 95.1), width=3.6, height=2.0, style=st.patch(shape_r=0.3))
    text((lx + 2.8, 95.1), ltxt, style=Styles.Dark.patch(text_size=10.0, halign="left"))

# Left Panel: Average TTFT (ms)
rectangle((45.5, 52.0), width=79.0, height=76.0, style=Styles.WhiteFlat.patch(shape_r=1.4, line_width=0.8))
text((45.5, 86.8), "① 初回トークン到着時間：平均 TTFT (ms)", style=Styles.PrimaryBold.patch(text_size=11.0))

chart_ttft = BarChart(
    axis_line_style=Styles.Dark,
    axis_text_style=Styles.DarkBold.patch(text_size=9.5),
    grid_style=Styles.MutedDashed,
    value_text_style=Styles.DarkBold.patch(text_size=8.6),
    width=52.0,
    height=64.0,
    categories=categories,
    orientation="horizontal",
    bar_mode="group",
    bar_width_ratio=0.74,
    bar_r=0.3,
)
chart_ttft.configure_x_axis(min_value=0, max_value=15000, tick_step=5000, format="{:,.0f}")
chart_ttft.add_series("pat_a", calc_means("pat_a_pydantic_2f", "ttft_ms"), style=Styles.PrimaryFlat)
chart_ttft.add_series("pat_c", calc_means("pat_c_tag", "ttft_ms"), style=Styles.TealFlat)
chart_ttft.add_series("base_0", calc_means("base_0", "ttft_ms"), style=Styles.SuccessFlat)
chart_ttft.add_series("base_low", calc_means("base_low", "ttft_ms"), style=Styles.WarningFlat)
chart_ttft.add_series("pat_b", calc_means("pat_b_pydantic_1f", "ttft_ms"), style=Styles.DangerFlat)
chart_ttft.draw(xy=(24.5, 17.5))

# Right Panel: Average Total Completion Time (ms)
rectangle((126.5, 52.0), width=79.0, height=76.0, style=Styles.WhiteFlat.patch(shape_r=1.4, line_width=0.8))
text((126.5, 86.8), "② 全文ストリーミング完了：平均 Total (ms)", style=Styles.DarkBold.patch(text_size=11.0))

chart_tot = BarChart(
    axis_line_style=Styles.Dark,
    axis_text_style=Styles.DarkBold.patch(text_size=9.5),
    grid_style=Styles.MutedDashed,
    value_text_style=Styles.DarkBold.patch(text_size=8.6),
    width=52.0,
    height=64.0,
    categories=categories,
    orientation="horizontal",
    bar_mode="group",
    bar_width_ratio=0.74,
    bar_r=0.3,
)
chart_tot.configure_x_axis(min_value=0, max_value=24000, tick_step=8000, format="{:,.0f}")
chart_tot.add_series("pat_a", calc_means("pat_a_pydantic_2f", "total_ms"), style=Styles.PrimaryFlat)
chart_tot.add_series("pat_c", calc_means("pat_c_tag", "total_ms"), style=Styles.TealFlat)
chart_tot.add_series("base_0", calc_means("base_0", "total_ms"), style=Styles.SuccessFlat)
chart_tot.add_series("base_low", calc_means("base_low", "total_ms"), style=Styles.WarningFlat)
chart_tot.add_series("pat_b", calc_means("pat_b_pydantic_1f", "total_ms"), style=Styles.DangerFlat)
chart_tot.draw(xy=(105.5, 17.5))

# Bottom summary banner
rectangle((86.0, 6.2), width=160.0, height=6.4, style=Styles.PrimaryNeutral.patch(shape_r=1.2))
phosphor.check_circle((10.5, 6.2), width=3.2, style=Styles.PrimaryBold)
text(
    (14.0, 6.2),
    "要点：Pattern A は全ティアで TTFT ~2.3秒を維持し、Base Low の最大12.2秒・Pattern B の12.6秒におよぶ初動凍結を完全に解消する。",
    style=Styles.DarkBold.patch(text_size=10.0, halign="left"),
)

save()
```

### 全45実行の TTFT × Total 散布図と UX 閾値ライン検証

平均値だけでなく、全9設問×5方式＝45実行の1回ごとのばらつきを検証するため、すべての実行を「X軸：初回トークン到着時間 `ttft_ms` × Y軸：全文完了時間 `total_ms`」の2次元平面上にプロットしたのが図4-3である。

```drawlib align=center code=fold width=100% file=ch04_all45_runs_scatter_ja.png caption="図4-3: 全45実行（9設問 × 5方式）の TTFT × Total レイテンシー分布と初動応答ゾーンの比較"
from drawlib.canvas import save, setup
from drawlib.charts.scatter import ScatterChart
from drawlib.icons import phosphor
from drawlib.lines import line
from drawlib.shapes import rectangle
from drawlib.styles import Styles
from drawlib.text import text
from drawlib.utils import load_adaptive_runs

setup(width=172, height=92, dpi=150)

# Outer structural frame
rectangle((86.0, 46.0), width=168.0, height=88.0, style=Styles.MutedDashed.patch(shape_r=2.0))
text(
    (86.0, 85.8),
    "全45実行 (9設問 × 5方式) の TTFT × Total 分布と初動応答ゾーン比較",
    style=Styles.DarkBold.patch(text_size=12.0),
)

runs = load_adaptive_runs()
series_pts: dict[str, list[tuple[float, float]]] = {
    "pat_a_pydantic_2f": [],
    "pat_c_tag": [],
    "base_0": [],
    "base_low": [],
    "pat_b_pydantic_1f": [],
}
for r in runs:
    series_pts[r["method_key"]].append((float(r["ttft_ms"]), float(r["total_ms"])))

# Left Chart Container
rectangle((62.0, 47.0), width=112.0, height=69.0, style=Styles.WhiteFlat.patch(shape_r=1.4, line_width=0.8))

# 2-row custom legend at top of chart container
rectangle((62.0, 75.8), width=107.0, height=8.8, style=Styles.Neutral.patch(shape_r=1.0))
leg1 = [
    (11.5, Styles.PrimaryFlat, "★ Pattern A: 2F統合 (9実行)"),
    (64.5, Styles.TealFlat, "Pattern C: 先頭タグ (9実行)"),
]
for lx, st, ltxt in leg1:
    rectangle((lx, 77.8), width=3.2, height=1.8, style=st.patch(shape_r=0.3))
    text((lx + 2.4, 77.8), ltxt, style=Styles.DarkBold.patch(text_size=10.0, halign="left"))

leg2 = [
    (11.5, Styles.SuccessFlat, "Base 0: 固定0 (9)"),
    (46.5, Styles.WarningFlat, "Base Low: 固定low (9)"),
    (83.5, Styles.DangerFlat, "Pattern B: 1F直列 (9)"),
]
for lx, st, ltxt in leg2:
    rectangle((lx, 73.8), width=3.2, height=1.8, style=st.patch(shape_r=0.3))
    text((lx + 2.4, 73.8), ltxt, style=Styles.Dark.patch(text_size=10.0, halign="left"))

# Highlight UX target zone inside plot area
PX0 = 25.8
PW_AX = 82.0
PY0 = 27.5
PH_AX = 37.7

x_2500 = PX0 + (2500.0 / 14000.0) * PW_AX
x_3500 = PX0 + (3500.0 / 14000.0) * PW_AX

rectangle(
    ((PX0 + x_2500) / 2.0, (PY0 + PY0 + PH_AX) / 2.0),
    width=x_2500 - PX0,
    height=PH_AX,
    style=Styles.PrimaryNeutralFlat,
)

chart = ScatterChart(
    axis_line_style=Styles.Dark,
    axis_text_style=Styles.Dark.patch(text_size=10.0),
    grid_style=Styles.MutedDashed,
    width=102.0,
    height=52.0,
    default_radius=1.25,
)
chart.configure_x_axis(
    label="初回トークン到着時間 TTFT (ms)",
    min_value=0,
    max_value=14000,
    tick_step=3500,
    format="{:,.0f}",
)
chart.configure_y_axis(
    label="Total (ms)",
    min_value=0,
    max_value=24000,
    tick_step=6000,
    format="{:.0f}",
)

chart.add_series("Base Low", series_pts["base_low"], style=Styles.WarningFlat, shape="rhombus", radius=1.2)
chart.add_series("Pattern B", series_pts["pat_b_pydantic_1f"], style=Styles.DangerFlat, shape="square", radius=1.15)
chart.add_series("Base 0", series_pts["base_0"], style=Styles.SuccessFlat, shape="square", radius=1.15)
chart.add_series("Pattern C", series_pts["pat_c_tag"], style=Styles.TealFlat, shape="triangle", radius=1.2)
chart.add_series("Pattern A", series_pts["pat_a_pydantic_2f"], style=Styles.PrimaryFlat, shape="circle", radius=1.3)

chart.draw(xy=(10.0, 16.5))

# Vertical UX Threshold Lines
line((x_2500, PY0), (x_2500, PY0 + PH_AX), style=Styles.PrimaryBold.patch(line_width=1.5))
text((x_2500, PY0 + PH_AX + 2.0), "2.5s 即応帯", style=Styles.PrimaryBold.patch(text_size=10.0))

line((x_3500, PY0), (x_3500, PY0 + PH_AX), style=Styles.DangerBold.patch(line_width=1.5))
text((x_3500 + 8.5, PY0 + PH_AX + 2.0), "3.5s 許容上限", style=Styles.DangerBold.patch(text_size=10.0))

# Right-side Summary Cards
rectangle((143.0, 47.0), width=44.0, height=69.0, style=Styles.PrimaryNeutral.patch(shape_r=1.5))
text((143.0, 77.2), "全45実行の分布インサイト", style=Styles.PrimaryBold.patch(text_size=11.0))

cards = [
    (
        63.0,
        "1. Pattern A は平均 2.34秒",
        "全9問が TTFT 2.0〜3.0s 帯に\n収束し、Base Low (平均 6.29s)\nの初動待機を -63% 短縮!",
        Styles.PrimaryBold,
    ),
    (
        44.5,
        "2. Y軸伸長と X軸の直交分離",
        "Tier 3 で Total が 16〜20秒へ\n伸びても Pattern A の TTFT は\n~2.3秒のまま右へドリフトしない",
        Styles.SuccessBold,
    ),
    (
        26.0,
        "3. Base Low / Pat B の凍結",
        "計算負荷がそのまま TTFT に\n直結し、最大 12,155〜12,590 ms\nまで無応答で画面が停止する",
        Styles.DangerBold,
    ),
]
for cy, ctitle, cbody, hst in cards:
    rectangle((143.0, cy), width=40.4, height=15.6, style=Styles.WhiteFlat.patch(shape_r=1.0))
    text((143.0, cy + 4.8), ctitle, style=hst.patch(text_size=10.0))
    text((143.0, cy - 1.5), cbody, style=Styles.Dark.patch(text_size=10.0))

# Bottom banner
rectangle((86.0, 6.2), width=160.0, height=6.4, style=Styles.SecondaryNeutral.patch(shape_r=1.2))
phosphor.target((10.5, 6.2), width=3.2, style=Styles.SecondaryBold)
text(
    (14.0, 6.2),
    "結論：Pattern A は全9問で TTFT ~2.3秒にロックされ、複雑計算時の 9〜12秒におよぶ画面フリーズを根絶している。",
    style=Styles.DarkBold.patch(text_size=10.0, halign="left"),
)

save()
```

### 全9設問 × 5方式の実測メトリクス一覧テーブル

図4-2・図4-3の元データである全45実行の `TTFT / Total`（単位：`ms`）、ルーティング判定結果、および Tier 3 計算精度を下表にまとめる。

| 設問 ID・タイトル | 期待分岐<br>（A/B/C判定） | Base 0 (`t=0`)<br>`TTFT / Total` | Base Low (`low`)<br>`TTFT / Total` | ★ Pattern A (`2F統合`)<br>`TTFT / Total` | Pattern B (`1F直列`)<br>`TTFT / Total` | Pattern C (`先頭タグ`)<br>`TTFT / Total` | 回答品質・計算検証 |
| :--- | :---: | ---: | ---: | ---: | ---: | ---: | :--- |
| **`T1_1` 初回挨拶（PC起動トラブル）** | `False` (`3/3`) | `1,548 / 3,477` | `3,572 / 5,361` | **`2,980 / 4,768`** | `3,103 / 5,451` | `2,248 / 4,230` | 全方式妥当 |
| **`T1_2` お礼・相槌** | `False` (`3/3`) | `1,940 / 3,267` | `4,244 / 5,274` | **`2,020 / 3,522`** | `3,332 / 4,837` | `2,217 / 3,139` | 全方式妥当 |
| **`T1_3` サポート窓口受付時間** | `False` (`3/3`) | `1,671 / 4,578` | `2,928 / 4,823` | **`2,222 / 4,347`** | `2,982 / 5,650` | `1,561 / 3,581` | 全方式妥当 |
| **`T2_1` 電源が入らない時の放電手順** | `False` (`3/3`) | `2,336 / 7,610` | `5,901 / 12,158` | **`2,243 / 4,629`** | `3,647 / 10,879` | `1,899 / 5,914` | 全方式妥当（A が最速完了） |
| **`T2_2` 修理出し前の事前準備確認** | `False` (`3/3`) | `1,748 / 7,837` | `6,349 / 11,836` | **`2,126 / 6,073`** | `3,897 / 10,757` | `1,910 / 7,448` | 全方式妥当（A が最速完了） |
| **`T2_3` 水こぼし発生時の緊急対処** | `False` (`3/3`) | `2,076 / 5,454` | `5,750 / 9,683` | **`2,531 / 5,509`** | `4,169 / 8,988` | `1,687 / 5,869` | 全方式妥当 |
| **`T3_1` PC修理vs買い替え3年比較** | `True` (`3/3`) | `1,515 / 7,895` | `8,950 / 17,058` | **`2,120 / 16,650`** | `11,226 / 20,762` | `1,613 / 16,499` | `low` 4方式が事前検算済 |
| **`T3_2` 500GB SSDバックアップ時間** | `True` (`3/3`) | `2,235 / 9,017` | `12,155 / 19,297` | **`2,456 / 19,344`** | `12,590 / 18,325` | `1,834 / 15,826` | `low` 4方式が事前検算済 |
| **`T3_3` 3台PC保守・メモリ増設2年** | `True` (`3/3`) | `1,840 / 8,443` | `6,762 / 13,384` | **`2,365 / 20,707`** | `10,649 / 18,167` | `1,939 / 17,085` | `low` 4方式が事前検算済 |
| **Tier 1 平均（3問）** | **`3/3` 一致** | `1,720 / 3,774` | `3,581 / 5,153` | **`2,407 / 4,212`** | `3,139 / 5,313` | `2,009 / 3,650` | 不要思考 `0 tok`（A・B・C） |
| **Tier 2 平均（3問）** | **`3/3` 一致** | `2,053 / 6,967` | `6,000 / 11,226` | **`2,300 / 5,404`** | `3,904 / 10,208` | `1,832 / 6,410` | **Pattern A が完了最速** |
| **Tier 1–2 平均（6問）** | **`6/6` 一致** | `1,887 / 5,371` | `4,791 / 8,189` | **`2,354 / 4,808`** | `3,522 / 7,760` | `1,920 / 5,030` | **Pattern A が完了最速** |
| **Tier 3 平均（3問）** | **`3/3` 一致** | `1,863 / 8,452` | `9,289 / 16,580` | **`2,314 / 18,900`** | `11,488 / 19,085` | `1,795 / 16,470` | `thinking=low` 4方式が事前検算 |
| **全9問平均** | **`9/9` 一致** | `1,879 / 6,398` | `6,290 / 10,986` | **`2,340 / 9,505`** | `6,177 / 11,535` | `1,879 / 8,843` | **Pattern A が総合最適** |

---

## 4.3 ストリーム軌跡の深掘り（`thinking=false` 直接完結 vs. `thinking=true` 並列チェイニング）

Pattern A がどのようにして「定型質問での単一ストリーム完結」と「複雑計算での2段階並列チェイニング」を切り替えているのかを視覚化するため、`load_adaptive_trajectory()` を用いて **`T2_1`（Tier 2：電源が入らない時の放電・最小構成手順）** と **`T3_1`（Tier 3：PC修理 vs. 買い替え 3年間総費用比較）** の累積出力文字数軌跡を比較したのが図4-4である。

```drawlib align=center code=fold width=100% file=ch04_trajectory_deep_dive_ja.png caption="図4-4: Tier 2 定型手続き (T2_1: thinking=false 直接完結) と Tier 3 複雑計算 (T3_1: thinking=true 並列 Stage 2 チェイニング) のストリーム軌跡比較"
from drawlib.canvas import save, setup
from drawlib.icons import phosphor
from drawlib.lines import line
from drawlib.shapes import circle, rectangle
from drawlib.styles import Styles
from drawlib.text import text
from drawlib.utils import load_adaptive_trajectory

setup(width=172, height=96, dpi=150)

# Outer structural frame
rectangle((86.0, 48.0), width=168.0, height=92.0, style=Styles.MutedDashed.patch(shape_r=2.0))
text(
    (86.0, 89.6),
    "ストリーム軌跡の深掘り：T2_1 (thinking=false 直接完結) vs. T3_1 (thinking=true 並列チェイニング)",
    style=Styles.DarkBold.patch(text_size=12.0),
)

# Shared Legend Bar
rectangle((86.0, 82.8), width=162.0, height=5.2, style=Styles.Neutral.patch(shape_r=1.0))

leg_items = [
    (8.5, Styles.PrimaryBold, Styles.PrimaryFlat, "★ Pattern A (2F統合)"),
    (44.5, Styles.TealBold, Styles.TealFlat, "Pattern C (先頭タグ)"),
    (77.5, Styles.SuccessBold, Styles.SuccessFlat, "Base 0 (固定0)"),
    (110.5, Styles.WarningBold, Styles.WarningFlat, "Base Low (固定low)"),
    (142.5, Styles.DangerBold, Styles.DangerFlat, "Pattern B (1F直列)"),
]
for lx, lst, cst, ltxt in leg_items:
    line((lx, 82.8), (lx + 3.4, 82.8), style=lst.patch(line_width=2.2))
    circle((lx + 1.7, 82.8), radius=0.75, style=cst)
    text((lx + 4.3, 82.8), ltxt, style=Styles.DarkBold.patch(text_size=9.6, halign="left"))


def draw_multi_trajectory_panel(
    *,
    x0: float,
    y0: float,
    pw: float,
    ph: float,
    prompt_id: str,
    title_s: str,
    sub_s: str,
    max_t: float,
    max_c: float,
    x_ticks: list[int],
    y_ticks: list[int],
) -> tuple[object, object]:
    rectangle((x0 + pw / 2, y0 + ph / 2 + 2.5), width=pw + 14.0, height=ph + 19.0, style=Styles.LightFlat.patch(shape_r=1.6))
    text((x0 + pw / 2, y0 + ph + 8.2), title_s, style=Styles.DarkBold.patch(text_size=11.0))
    text((x0 + pw / 2, y0 + ph + 4.4), sub_s, style=Styles.PrimaryBold.patch(text_size=10.0))
    rectangle((x0 + pw / 2, y0 + ph / 2), width=pw, height=ph, style=Styles.WhiteFlat)

    def px(t_ms: float) -> float:
        return x0 + min(max(t_ms, 0.0), max_t) / max_t * pw

    def py(c_val: float) -> float:
        return y0 + min(max(c_val, 0.0), max_c) / max_c * ph

    for xt in x_ticks:
        tx = px(float(xt))
        line((tx, y0), (tx, y0 + ph), style=Styles.LightDashed.patch(line_width=0.7))
        text((tx, y0 - 2.6), f"{xt / 1000:.0f}s", style=Styles.Dark.patch(text_size=10.0))

    for yt in y_ticks:
        ty = py(float(yt))
        line((x0, ty), (x0 + pw, ty), style=Styles.LightDashed.patch(line_width=0.7))
        text((x0 - 3.6, ty), f"{yt:,}", style=Styles.Dark.patch(text_size=10.0))

    line((x0, y0), (x0 + pw, y0), style=Styles.Dark.patch(line_width=1.1))
    line((x0, y0), (x0, y0 + ph), style=Styles.Dark.patch(line_width=1.1))

    method_styles = [
        ("base_0", Styles.SuccessBold.patch(line_width=1.6), Styles.SuccessFlat, 0.65),
        ("pat_c_tag", Styles.TealBold.patch(line_width=1.7), Styles.TealFlat, 0.7),
        ("base_low", Styles.WarningBold.patch(line_width=1.8), Styles.WarningFlat, 0.75),
        ("pat_b_pydantic_1f", Styles.DangerBold.patch(line_width=1.8), Styles.DangerFlat, 0.75),
        ("pat_a_pydantic_2f", Styles.PrimaryBold.patch(line_width=2.5), Styles.PrimaryFlat, 0.95),
    ]

    for m_key, l_st, c_st, rad in method_styles:
        tr = load_adaptive_trajectory(prompt_id, m_key)
        pts = tr["client_output"]
        if len(pts) >= 2:
            coords = [(px(float(p["t_ms"])), py(float(p["chars"]))) for p in pts]
            for i in range(len(coords) - 1):
                line(coords[i], coords[i + 1], style=l_st)
            for cx_p, cy_p in coords:
                circle((cx_p, cy_p), radius=rad, style=c_st)

    return px, py


# Left Panel: T2_1 (Standard Procedure, thinking=false)
px_l, py_l = draw_multi_trajectory_panel(
    x0=15.0,
    y0=18.5,
    pw=63.0,
    ph=46.0,
    prompt_id="T2_1",
    title_s="① Tier 2 定型手続き (T2_1: 放電・最小構成手順)",
    sub_s="thinking=false：単一 API 呼出で即時ストリーム完結",
    max_t=14000.0,
    max_c=1600.0,
    x_ticks=[0, 3000, 6000, 9000, 12000],
    y_ticks=[0, 400, 800, 1200, 1600],
)

# Callouts inside Left Panel
rectangle((39.5, 55.5), width=42.0, height=10.0, style=Styles.PrimaryNeutral.patch(shape_r=0.9))
text((39.5, 57.8), "★ Pattern A: 2,243 ms 開始", style=Styles.PrimaryBold.patch(text_size=9.6))
text((39.5, 53.4), "4,629 ms で全5方式最速完了!", style=Styles.DarkBold.patch(text_size=9.6))
line((34.0, 50.5), (px_l(4629.0), py_l(482.0)), arrow_head="->", style=Styles.PrimaryBold.patch(line_width=1.5))

rectangle((55.5, 29.0), width=41.0, height=9.4, style=Styles.WhiteFlat.patch(shape_r=0.9, line_width=0.7))
text((55.5, 31.2), "Base Low: 5,901 ms まで無応答", style=Styles.WarningBold.patch(text_size=9.5))
text((55.5, 26.8), "不要思考 423 tok で初動が 2.6倍遅延", style=Styles.Dark.patch(text_size=9.4))
line((px_l(5901.0), 24.3), (px_l(5901.0), py_l(40.0)), arrow_head="->", style=Styles.WarningBold.patch(line_width=1.4))

# Right Panel: T3_1 (Complex Math, thinking=true)
px_r, py_r = draw_multi_trajectory_panel(
    x0=98.0,
    y0=18.5,
    pw=63.0,
    ph=46.0,
    prompt_id="T3_1",
    title_s="② Tier 3 複雑計算 (T3_1: PC修理vs買い替え比較)",
    sub_s="thinking=true：受付1文 (2,120ms) + Stage 2 (low) 並列連結",
    max_t=22000.0,
    max_c=1600.0,
    x_ticks=[0, 5000, 10000, 15000, 20000],
    y_ticks=[0, 400, 800, 1200, 1600],
)

# Callouts inside Right Panel
rectangle((124.5, 55.5), width=48.5, height=10.6, style=Styles.PrimaryNeutral.patch(shape_r=0.9))
text((124.5, 58.0), "① 2,120 ms 受付1文 + Stage 2 並列起動", style=Styles.PrimaryBold.patch(text_size=9.5))
text((124.5, 53.2), "Base Low (8.95s) の 6.8秒画面凍結を解消!", style=Styles.DarkBold.patch(text_size=9.5))
line((108.0, 50.2), (px_r(2120.0), py_r(60.0)), arrow_head="->", style=Styles.PrimaryBold.patch(line_width=1.5))

rectangle((137.5, 29.5), width=44.0, height=9.6, style=Styles.WhiteFlat.patch(shape_r=0.9, line_width=0.7))
text((137.5, 31.8), "② 10,948 ms〜 Stage 2 (859 tok) 連結", style=Styles.PrimaryBold.patch(text_size=9.5))
text((137.5, 27.3), "26,200円修理がお得を 16,650 ms で完結", style=Styles.Dark.patch(text_size=9.4))
line((px_r(10948.0), 24.7), (px_r(10948.0), py_r(90.0)), arrow_head="->", style=Styles.PrimaryBold.patch(line_width=1.5))

# Bottom summary banner
rectangle((86.0, 6.0), width=160.0, height=6.4, style=Styles.PrimaryNeutral.patch(shape_r=1.2))
phosphor.sparkle((10.5, 6.0), width=3.2, style=Styles.PrimaryBold)
text(
    (14.0, 6.0),
    "結論：Pattern A は T2_1 で 4,629 ms 最速完了し、T3_1 では 2,120 ms ブリッジ文で Base Low の 6.8秒画面凍結を隠蔽する。",
    style=Styles.DarkBold.patch(text_size=10.0, halign="left"),
)

save()
```

### 図4-4 の軌跡が示す2つの決定的な優位性

1. **左パネル `T2_1`（`thinking=false`：電源が入らない時の放電手順）における単一 API 完結と最速完了**：
   - Pattern A（青太線）は `2,068 ms` で `"thinking": false` を確定し、**`2,243 ms`** から `"response"` フィールドのストリーミングを開始して **`4,629 ms` でストリーム完了** し、全5方式で最も早く回答を完結させている。
   - これは Pydantic JSON スキーマによって簡潔で構造化された手順案内（`482 文字`）が出力されるためであり、Pattern C（`5,914 ms` 完了）や Base 0（`7,610 ms` 完了）、Base Low（`12,158 ms` 完了）よりも圧倒的に歯切れよく完了する。
2. **右パネル `T3_1`（`thinking=true`：PC修理 vs. 買い替え3年比較）における `6.8 秒` の画面凍結解消**：
   - Base Low（黄線）は **`8,950 ms` にわたり累積文字数 0 文字のまま画面が凍結** し、Pattern B（赤線）はさらに遅い **`11,226 ms`** まで1文字も表示されない。
   - 対して Pattern A（青太線）は、**`2,078 ms`** で `"thinking": true` を検知した瞬間にバックグラウンドで Stage 2（`thinking=low`）を非同期起動しつつ、Stage 1 のブリッジメッセージ（59文字）を **`2,120 ms`** で即座に画面へ表示する。これにより、Base Low と比較して **`6,830 ms`（約 `6.8 秒`）もの無応答フリーズを完全に解消** している。ユーザーがブリッジ文を読んでいる間に Stage 2 が `859 トークン` の内部推論を終え、**`10,948 ms`** から本計算のストリームが滑らかに立ち上がって **`16,650 ms`** に正確な試算結果（`修理の方が 26,200 円安い`）を完結させている。

---

## 4.4 Google AI Studio 実装コードと総合評価スコアカード

### Pattern A の Google AI Studio (`google-genai`) リファレンス実装

`google-genai` SDK のストリーミング時は `chunk.parsed` がストリーム途中で常に `None` となるため、Pydantic v2 標準同梱の `pydantic_core.from_json(..., allow_partial="trailing-strings")` を用いて不完全な JSON バッファから安全に `thinking` フラグとエスケープ解決済みの `response` デルタを抽出する（`src/gemini_evaluation/adaptive_thinking.py`）。なお、本番環境では `genai.Client` インスタンスをアプリケーション起動時に1度だけ生成して再利用し、`finally` ブロックで Stage-2 バックグラウンドタスクの確実なクリーンアップを行う。

```python
import asyncio
from collections.abc import AsyncIterator
from contextlib import aclosing
from typing import Any

from google import genai
from google.genai import types
from pydantic import BaseModel
from pydantic_core import from_json

MODEL = "gemini-3.8-flash"


class AdaptiveStreamResponse(BaseModel):
    """Pattern A 用の最小2フィールド構造化ストリーミングスキーマ。"""

    thinking: bool  # 第1フィールド：初回チャンク以前に確定するルーティングフラグ
    response: str   # 第2フィールド：thinking=False 時は回答全文、True 時は受付1文


def parse_partial_json_dict(raw_buf: str) -> dict[str, Any] | None:
    """ストリーム途中の不完全な JSON を例外なく安全に辞書へ逐次パースする。"""
    if not raw_buf:
        return None
    try:
        parsed = from_json(raw_buf.encode("utf-8"), allow_partial="trailing-strings")
        return parsed if isinstance(parsed, dict) else None
    except ValueError:
        return None


async def stream_adaptive_router(
    client: genai.Client,
    prompt: str,
) -> AsyncIterator[str]:
    """Pattern A: 2フィールド統合 Pydantic ストリーム + Stage 2 並列チェイニング。"""
    stage2_queue: asyncio.Queue[str | BaseException | None] = asyncio.Queue()
    stage2_task: asyncio.Task[None] | None = None

    async def _produce_stage2() -> None:
        try:
            st2 = await client.aio.models.generate_content_stream(
                model=MODEL,
                contents=prompt,
                config=types.GenerateContentConfig(
                    system_instruction=(
                        "冒頭の挨拶や受付文は既に表示済みです。"
                        "挨拶を繰り返さず、直ちに本題の計算ステップと結論を回答してください。"
                    ),
                    thinking_config=types.ThinkingConfig(
                        thinking_level=types.ThinkingLevel.LOW,
                    ),
                    temperature=0.2,
                ),
            )
            async with aclosing(st2):
                async for ch2 in st2:
                    if ch2.text:
                        await stage2_queue.put(ch2.text)
            await stage2_queue.put(None)
        except BaseException as exc:
            await stage2_queue.put(exc)

    json_buf = ""
    emitted_len = 0
    decided_thinking: bool | None = None

    try:
        st1 = await client.aio.models.generate_content_stream(
            model=MODEL,
            contents=prompt,
            config=types.GenerateContentConfig(
                system_instruction=(
                    "挨拶や定型手続き案内では thinking: false とし response に回答全文を出力してください。"
                    "複数条件の数値計算・比較では thinking: true とし response に1文の受付メッセージのみを出力してください。"
                ),
                response_mime_type="application/json",
                response_schema=AdaptiveStreamResponse,
                thinking_config=types.ThinkingConfig(thinking_budget=0),
                temperature=0.2,
            ),
        )
        async with aclosing(st1):
            async for ch1 in st1:
                if not ch1.text:
                    continue
                json_buf += ch1.text
                partial = parse_partial_json_dict(json_buf)
                if partial is None:
                    continue

                # 1) thinking フラグが確定した瞬間に1度だけ判定し、True なら Stage 2 を並列起動
                if decided_thinking is None and isinstance(partial.get("thinking"), bool):
                    decided_thinking = partial["thinking"]
                    if decided_thinking:
                        stage2_task = asyncio.create_task(_produce_stage2())

                # 2) response の未送出デルタを即時 yield
                resp_so_far = partial.get("response")
                if isinstance(resp_so_far, str) and len(resp_so_far) > emitted_len:
                    delta = resp_so_far[emitted_len:]
                    emitted_len = len(resp_so_far)
                    yield delta

        # 3) EOF で Pydantic スキーマ完全検証を実行
        final_obj = AdaptiveStreamResponse.model_validate_json(json_buf)
        if len(final_obj.response) > emitted_len:
            yield final_obj.response[emitted_len:]

        # 4) thinking=True の場合は並列実行中の Stage 2 ストリームをシームレスに連結
        if decided_thinking and stage2_task is not None:
            yield "\n\n"
            while True:
                item = await stage2_queue.get()
                if item is None:
                    break
                if isinstance(item, BaseException):
                    raise item
                yield item
            await stage2_task
    finally:
        # 呼び出し側の中断や例外発生時に未完了の Stage 2 タスクを確実にキャンセル
        if stage2_task is not None and not stage2_task.done():
            stage2_task.cancel()
```

> **Pydantic スキーマの Cold/Warm 特性とフィールド定義順のベストプラクティス**：第2章（2.3節）の `load_schema_experiment()`（`src/gemini_evaluation/adaptive_thinking_log.json`）で詳述したとおり、新規の JSON スキーマを初回送信した際（`RichStreamResponse #1 (Cold)`：`TTFT 3,337.3 ms`、`flag_decided_ms 2,954.3 ms`）にはサーバー側の制約付きデコード文法（FSM）コンパイルが走るが、**2回目以降（Warm `#2〜#4`）は文法キャッシュが適用され、6フィールド版（TTFT `2,504.4〜3,259.3 ms`・平均 `2,837.1 ms`、Cold 比 `-15.0%` 短縮）と2フィールド版（Warm `#2〜#4` 平均 `2,744.4 ms`）がわずか `+92.7 ms`（`+3.4%`）差のほぼ同等の速度で推移する**。分類タグ等を加えた6フィールドの `RichStreamResponse` でも、`thinking: bool` を先頭・可変長リストを `response: str` の後ろに配置すれば Warm 時の `flag_decided_ms` は平均 `2,419.4 ms`（`2,157.1〜2,780.6 ms`）と高速である。本番環境ではコンテナ起動時に1回ダミーウォームアップを実行しておくことで Cold 遅延を完全に排除できる。

### 全5方式の総合評価スコアカード

| 評価項目 | ★ Pattern A (`pat_a_pydantic_2f`)<br>`{thinking, response}` 統合 | Pattern C (`pat_c_tag`)<br>`[DIRECT]` / `[THINK]` タグ | Pattern B (`pat_b_pydantic_1f`)<br>`{thinking}` 直列ルーター | Base Low (`base_low`)<br>固定 `thinking=low` | Base 0 (`base_0`)<br>固定 `thinking=0` |
| :--- | :---: | :---: | :---: | :---: | :---: |
| **全9問平均 TTFT** | **`2,340 ms` (優良 `< 2.5s`)** | **`1,879 ms` (優良 `< 2.5s`)** | `6,177 ms` (不可 `> 3.5s`) | `6,290 ms` (不可 `> 3.5s`) | `1,879 ms` (優良 `< 2.5s`) |
| **Tier 1–2 平均 TTFT / 完了** | **`2,354 ms` / `4,808 ms` (最速完了)** | `1,920 ms` / `5,030 ms` | `3,522 ms` / `7,760 ms` | `4,791 ms` / `8,189 ms` | `1,887 ms` / `5,371 ms` |
| **Tier 3 平均 TTFT（最大）** | **`2,314 ms` (`2,456 ms`)** | `1,795 ms` (`1,939 ms`) | `11,488 ms` (`12,590 ms`) | `9,289 ms` (`12,155 ms`) | `1,863 ms` (`2,235 ms`) |
| **ルーティング正解率** | **`9 / 9` (`100%`)** | **`9 / 9` (`100%`)** | **`9 / 9` (`100%`)** | 固定（常時思考） | 固定（思考なし） |
| **Tier 3 複雑計算検証** | **`3 / 3` (`100%` 事前検算)** | **`3 / 3` (`100%` 事前検算)** | **`3 / 3` (`100%` 事前検算)** | **`3 / 3` (`100%` 事前検算)** | **自己回帰リスク（事前検算なし）** |
| **API 呼び出し回数 (T1–2 / T3)** | **`1.0 回` / `2.0 回`** | `1.0 回` / `2.0 回` | `2.0 回` / `2.0 回` | `1.0 回` / `1.0 回` | `1.0 回` / `1.0 回` |
| **デコーダ層の型保証・拡張性** | **優良（Constrained Decoding）** | 不可（タグ露出・履歴ドリフト懸念） | 一部のみ（ルーターのみ型保証） | なし（平文） | なし（平文） |
| **総合判定** | **★ 本番標準採用（推奨）** | 不採用（型安全性ゆえAへ統一） | 不採用（直列2回遅延） | 非推奨（最大 `12.2s` 凍結） | 不採用（複雑計算リスク） |

