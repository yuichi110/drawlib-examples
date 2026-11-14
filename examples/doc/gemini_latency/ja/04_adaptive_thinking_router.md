# 4. Adaptive Thinking Router パターン

第3章では、`ThinkingConfig` のレベル選択において「低レベル固定（`low` 等）は初動 TTFT が速いものの複雑な多段階計算（Tier 3）で内部スクラッチパッド検算が不足または発動しないリスクを抱え、逆に高レベル固定（`high` 等）は深い事前検算を達成するものの、定型対話（Tier 1・2）にも不要な推論遅延を加算して十数秒にわたり画面が無応答で凍結する」というジレンマを明らかにした。

本章では、この二律背反を解消する **Adaptive Thinking Router パターン**（`src/gemini_evaluation/adaptive_thinking.py`）を提案する。まず **4.1節** で第3章の5モデル横断ベンチマークに基づき、**Stage 1（簡易判断・即応層）** と **Stage 2（Thinking 判断・深層推論層）** に適用可能なモデルおよび `thinking_level` の候補を整理する。続く **4.2〜4.5節** では、標準機である **`gemini-3.8-flash` の `low`（Stage 1）＋ `high`（Stage 2）** の組み合わせを用いて、3つの候補アーキテクチャ（Pattern A・B・C）および固定ベースライン（Base Low・Base High）の計5方式×9設問＝全45実行を実機計測し、**Pattern A（2フィールド統合 Pydantic スキーマ `{thinking: bool, response: str}` ＋ Stage 2 並列チェイニング）** が最適解であることを実証する。

```drawlib align=center code=fold width=100% file=ch04_adaptive_architectures_hero_ja.png caption="図4-1: Adaptive Thinking Router 候補3方式（Pattern A: 2フィールド統合 Pydantic・Pattern B: 1フィールド直列ルーター・Pattern C: 先頭タグ）のシーケンス・アーキテクチャ比較（gemini-3.8-flash: Stage 1 low -> Stage 2 high）"
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
    "Adaptive Thinking Router 3方式（Pattern A・B・C）のアーキテクチャと実測比較 (3.8-flash: low -> high)",
    style=Styles.DarkBold.patch(text_size=11.5),
)

# Top UX Target Bar
rectangle((86.0, 79.2), width=160.0, height=8.8, style=Styles.Neutral.patch(shape_r=1.2))
phosphor.gauge((10.5, 81.0), width=3.2, style=Styles.PrimaryBold)
text(
    (14.0, 81.0),
    "対話 UX 目標基準：① 初回トークン TTFT の最小化（固定 high の 10.5〜16.5秒凍結を排除） / ② 100% のスキーマ型保証と事前検算",
    style=Styles.PrimaryBold.patch(text_size=9.5, halign="left"),
)
text(
    (14.0, 77.0),
    "Stage 1 (thinking=low) で即時応答または受付ブリッジ1文を表示しつつ、複雑計算時のみ裏で Stage 2 (thinking=high) を並列実行",
    style=Styles.Dark.patch(text_size=9.5, halign="left"),
)

# 3 Architecture Columns
cols = [
    (
        33.0,
        "★ Pattern A [推奨・標準採用]",
        "2フィールド統合 Pydantic + 並列 Stage 2",
        "Stage 1: thinking=low + JSON Schema",
        "{thinking: bool, response: str} を逐次解析",
        "false: 1回呼出で即時ストリーム完結",
        "Tier 1–2 平均 TTFT 2,517 / 完了 4,352 ms",
        "true: 受付1文 (~2.1s) + Stage 2 並列",
        "create_task で high 推論を裏へ隠蔽",
        [
            "• 全9問平均 TTFT: 2,388 ms (High比 -81%)",
            "• Tier 3 最大16.5秒の画面凍結を解消",
            "• C より高速・デコーダ型保証・検算 [◎]",
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
        "generate_content (low) で {thinking} 判定",
        "Stage 2: 判定完了後に2回目を直列呼出",
        "false 時も 2回往復 (T1–2 TTFT 4,658 ms)",
        "true 時はルーター + high 思考が直列加算",
        "Tier 3 平均 TTFT 18,618 ms (最大 24.2秒)",
        [
            "• 全9問平均 TTFT: 9,311 ms (直列遅延)",
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
        "Stage 1: thinking=low 平文ストリーム",
        "プロンプト指示のみで先頭タグを出力",
        "[DIRECT]: タグ除去後に平文ストリーム",
        "T1–2 TTFT 2,565 ms / スキーマ検証なし",
        "[THINK]: 受付1文 (~3.7s) + Stage 2 並列",
        "平文ゆえ Stage 1 でも思考が走り初動鈍化",
        [
            "• 全9問平均 TTFT: 2,930 ms (A比 +0.54s)",
            "• 表記揺れで生タグ露出・長期履歴で欠落",
            "• 判定：速度も型安全性も A が優位 [×]",
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
    text((cx + 1.5, 67.8), title_s, style=hdr_st.patch(text_size=10.2))
    text((cx, 64.0), sub_s, style=sub_st.patch(text_size=9.5))

    # Step Box 1
    rectangle((cx, 56.5), width=48.2, height=8.6, style=Styles.WhiteFlat.patch(shape_r=1.0))
    text((cx, 58.4), s1_t, style=Styles.PrimaryBold.patch(text_size=9.6))
    text((cx, 54.6), s1_b, style=Styles.Dark.patch(text_size=9.4))

    arr_st = Styles.WhiteBold.patch(line_width=1.8) if card_st == Styles.PrimaryFlat else Styles.DarkBold.patch(line_width=1.8)
    line((cx, 52.2), (cx, 49.4), arrow_head="->", style=arr_st)

    # Step Box 2
    rectangle((cx, 45.0), width=48.2, height=8.6, style=mid_st.patch(shape_r=1.0))
    text((cx, 46.9), s2_t, style=Styles.DarkBold.patch(text_size=9.6))
    text((cx, 43.1), s2_b, style=Styles.Dark.patch(text_size=9.4))

    line((cx, 40.7), (cx, 37.9), arrow_head="->", style=arr_st)

    # Step Box 3
    rectangle((cx, 33.5), width=48.2, height=8.6, style=Styles.WhiteFlat.patch(shape_r=1.0))
    text((cx, 35.4), s3_t, style=Styles.SecondaryBold.patch(text_size=9.6))
    text((cx, 31.6), s3_b, style=Styles.Dark.patch(text_size=9.4))

    b_style = (
        Styles.White.patch(text_size=9.5, halign="left")
        if card_st == Styles.PrimaryFlat
        else Styles.Dark.patch(text_size=9.5, halign="left")
    )
    for idx, b_line in enumerate(bullets):
        text((cx - 22.8, 25.5 - idx * 4.2), b_line, style=b_style)

# Bottom conclusion bar
rectangle((86.0, 6.2), width=160.0, height=6.4, style=Styles.PrimaryNeutral.patch(shape_r=1.2))
phosphor.shield_check((10.5, 6.2), width=3.2, style=Styles.PrimaryBold)
text(
    (14.0, 6.2),
    "結論：Pattern A は平均 TTFT 2,388 ms (Base High 比 -81.4%) で Pattern C (2,930 ms) よりも速く、型安全性と応答速度を両立する。",
    style=Styles.DarkBold.patch(text_size=9.6, halign="left"),
)

save()
```

---

## 4.1 簡易判断（Stage 1）と Thinking 判断（Stage 2）のモデル・`thinking_level` 候補マトリクス

Adaptive Thinking Router は、リクエストを受け取って即座に定型回答または受付ブリッジ文を返す **Stage 1（簡易判断・即応＆ルーティング層）** と、複雑な推論・多段階計算が必要な場合のみバックグラウンドで並列起動される **Stage 2（Thinking する判断・深層推論＆事前検算層）** の2段構成をとる。第3章（3.5節）で実施した現行5モデル × 全 `thinking_level`（17構成・170試行）の計測結果に基づき、それぞれのステージに配置すべき候補モデルと `thinking_level` を整理する。

### 1. Stage 1（簡易判断・即応＆ルーティング層）の候補（表4-1A）

Stage 1 には **「簡単な質問で TTFT 0.7〜2.6秒以内（複雑質問でも 3.9秒以内）」** で応答を開始でき、不要な長時間思考で画面を止めない構成を選定する。

| 候補グループ | モデル名 (`model`) | 対象 `thinking_level` | 簡単5問 平均 TTFT / Total | 複雑5問 平均 TTFT / Total | Stage 1（簡易判断・即応層）としての特性と選定基準 |
| :--- | :--- | :---: | ---: | ---: | :--- |
| **① 超高速・最軽量枠** | **`gemini-3.5-flash-lite`** | **全レベル**<br>(`minimal` / `low` / `medium` / `high`) | **`0.67〜2.16 s`** /<br>`1.37〜2.57 s` | **`0.68〜3.49 s`** /<br>`2.06〜4.84 s` | **初期応答のさらなる高速化に最適**。特に **`minimal` / `low`（TTFT 約0.7秒）** は `ThTok=0` で圧倒的なサブ秒応答を実現する。推論デコードも超高速なため `medium` / `high` でも `3.8-flash [low]` 以下の初速に収まる。 |
| **② 標準バランス枠** | **`gemini-3.8-flash`** | **`low`**<br>*(＋互換 `budget=0`)* | **`2.46 s`** / `5.04 s` | **`2.59 s`** / `7.97 s` | **本章の実測で採用する標準機**。`low` は不要な思考トークンが最小限（平均62〜105 tok）に抑えられ、Pydantic スキーマと組み合わせることで約2.2〜2.5秒の安定した初動と高い定型回答品質を両立する。 |
| **③ 高品質 Gemini 4 即応枠** | **`gemini-4-hydrogen`** | **`low`** | **`2.60 s`** / **`3.37 s`** | **`3.91 s`** / **`5.90 s`** | 常時思考型（184〜658 tok）だがデコード速度が速いため、全文完了は `3.8-flash [low]` より高速。Stage 1 の定型回答から Gemini 4 世代の表現力・品質で返したい場合の有力候補。 |

---

### 2. Stage 2（Thinking する判断・深層推論＆事前検算層）の候補（表4-1B）

Stage 2 は、Stage 1 が1文の受付ブリッジメッセージをストリーミング表示している裏で並列実行される。候補は **`gemini-3.8-flash` の `medium` / `high`**、および **`Gemini 4` シリーズの `4-hydrogen [low]` 以外すべて** となるが、第3章の実測で判明した内部思考トークン（`ThTok`）と待機時間の特性から、以下の **3つの運用カテゴリ** に分けて選定するのが実践的である。

| Stage 2 カテゴリ | モデル名 (`model`) | 対象 `thinking_level` | 複雑5問 平均 TTFT / Total | 複雑5問 平均 `ThTok` | Stage 2（Thinking 層）としての適性とシステム要件 |
| :--- | :--- | :---: | :---: | :---: | :--- |
| **A. 対話ストリーム連結向け（標準）**<br>*(受付文の直後に5〜18秒で滑らかに連結)* | **`gemini-3.8-flash`** | **`medium` / `high`** | `6.16〜13.43 s` /<br>`10.71〜18.95 s` | `605〜1,549 tok` | **本章の実測で採用（`high`）**。Stage 1 の受付文表示（約2秒）＋ユーザーの読解時間の裏で `600〜1,500 tok` の事前検算を回すことで、体感の無応答フリーズを完全に隠蔽できる。 |
| **A. 対話ストリーム連結向け（推奨）**<br>*(より深く思考しつつ高速に完了)* | **`gemini-4-hydrogen`** | **`medium` / `high` / `xhigh`** | `6.51〜13.02 s` /<br>**`9.00〜15.43 s`** | **`954〜2,248 tok`** | **対話システムでより深い Thinking を行う場合の最推奨候補**。`3.8-flash [high]` より多くの思考トークン（`xhigh` で平均2,248 tok）を投入しながら、高速なデコードにより 9〜15秒で全文が完了する。 |
| **B. 大型モデル基礎知能枠**<br>*(内部 `ThTok=0` のダイレクト推論)* | **`gemini-4-argon`**<br>**`gemini-4-carbon`** | **`low` / `medium`** *(Argon)*<br>**`low`** *(Carbon)* | `4.93〜10.94 s` /<br>`12.49〜19.40 s` | **`0.0 tok`** | 実測上、これらは `thoughts_token_count = 0`（内部スクラッチパッドなし）で動作し、フロンティアモデルの基礎パラメータ規模で直接回答する。完了12〜19秒で対話の Stage 2 としても利用可能。 |
| **C. 複雑業務システム・深層推論枠**<br>*(初期応答 13〜34秒 / 完了 19〜40秒)* | **`gemini-4-argon`**<br>**`gemini-4-carbon`** | **`high`** *(Argon)*<br>**`medium` / `high`** *(Carbon)* | `13.45〜34.36 s` /<br>`19.22〜40.21 s` | **`713〜2,795 tok`**<br>*(最大 4,360 tok)* | **複雑な業務システム・専門解析向け**。30秒近くの初期応答待ちは一般的なコンシューマ向けチャットでは避けるべきだが、厳密な多段階検算や法務・財務・設計監査を伴う業務システムでは極めて強力な Stage 2 候補となる。 |

> **💡 本章における検証構成と実運用への推奨指針**：
> すべてのモデル × `thinking_level` のペアリングで総当たり検証を行うと組み合わせが膨大になるため、本章（4.2〜4.5節）の実機ベンチマークでは、単一モデル内で完結する代表的な組み合わせとして **`gemini-3.8-flash` の `low`（Stage 1：簡易判断）＋ `high`（Stage 2：Thinking 判断）** を用いてルーティング方式の優劣を検証する。
> 実運用システムを構築する際は、本章の **Pattern A** のコードをベースとして、以下のチューニングを行うことを推奨する。
> - **さらに初期応答（TTFT）を速くしたい場合**：Stage 1 のモデルを **`gemini-3.5-flash-lite`（`minimal` または `low`）** に置き換えることで、初回トークン表示を約2.4秒から **約0.7秒** へと劇的に短縮できる。
> - **より Thinking を深く・高精度にしたい場合**：Stage 2 のモデルを **`Gemini 4` 系** に置き換える。一般的な対話システムであれば高速かつ思考量の多い **`gemini-4-hydrogen`（`medium` / `high` / `xhigh`）** が最適であり、30秒前後の推論時間を許容できる複雑な業務システムであれば **`gemini-4-argon [high]`** や **`gemini-4-carbon [medium / high]`** を Stage 2 ワーカーに指定するのが推奨される。

---

## 4.2 UX レイテンシー目標と3つの候補アーキテクチャ（Pattern A・B・C）

### 認知 UX の応答時間閾値と設計ターゲット

対話型テクニカルサポート UI において、私たちが目指す Adaptive Thinking Router の定量的ゴールは以下の2点に集約される。
1. **すべての難易度ティアで `thinking=high` 固定時に発生する `10.5〜16.5 秒` もの内部推論中の画面フリーズを解消し、初回表示 TTFT を `thinking=low` 水準（約 `2.1〜2.8 秒`）に抑えること**。
2. **100% の JSON スキーマ型安全性をデコーダ層で保証しつつ、複雑計算（Tier 3）のみ Stage 2（`thinking=high`）の徹底的な事前検算（`674〜1,591 tok`）を並列チェイニングすること**。

### 候補3方式（Pattern A・B・C）の構造比較

`src/gemini_evaluation/adaptive_thinking.py` では、Google AI Studio（`genai.Client(api_key=GEMINI_KEY)`、`gemini-3.8-flash`）上で Stage 1 に `thinking_level=LOW`、Stage 2 に `thinking_level=HIGH` を割り当てた以下の3つの適応型アーキテクチャを実装した（図4-1）。

1. **Pattern A（推奨・標準採用：2フィールド統合 Pydantic `{thinking: bool, response: str}` ＋ 並列 Stage 2 チェイニング）**
   - **Stage 1** として `thinking_level=LOW` かつ `response_schema=AdaptiveStreamResponse` を指定した単一の `generate_content_stream` を開始し、到着する JSON チャンクを Rust 製 `pydantic_core.from_json(..., allow_partial="trailing-strings")` でインクリメンタルに解析する。
   - **`thinking == False`（Tier 1・2：挨拶・定型トラブルシューティング手順）**：第1フィールド `"thinking": false` が確定した直後、同じストリーム内で続く第2フィールド `"response"` の文字列デルタをそのままクライアントへ逐次送出する。**API 呼び出しは1回のみで完結**する。
   - **`thinking == True`（Tier 3：複雑な多段階計算）**：`"thinking": true` が確定した瞬間（`1,608〜2,411 ms`）に、`asyncio.create_task()` でバックグラウンドの **Stage 2（`thinking=high` の平文ストリーム）を並列起動** する。同時に Stage 1 は「ご質問ありがとうございます。ご提示いただいた条件を整理して詳しく試算いたします。」という1文（45〜70文字）のブリッジメッセージのみを出力して直ちに終了する。ユーザーがブリッジメッセージを読んでいる間に Stage 2 が深い内部推論（`674〜1,508 tok`）を完了し、シームレスに計算本編のストリームを連結する。
2. **Pattern B（比較対照：1フィールド直列ルーター `{thinking: bool}` ＋ Stage 2 ストリーム）**
   - 部分 JSON パースを行わず、第1段階として 1フィールドの `ThinkingDecision(thinking: bool)` をブロッキング呼び出し（`generate_content`, `thinking=low`）で判定し、その結果を見てから第2段階の `generate_content_stream`（`thinking=low` または `thinking=high`）を直列に呼び出す方式。
   - 実装は単純だが、**簡単な挨拶であっても必ず2回の API 往復（`calls=2`）が直列に発生** し（Tier 1–2 平均 TTFT `4,658 ms`）、Tier 3 ではルーターの待機時間と `thinking=high` の推論待機が直列加算されるため、Tier 3 平均 TTFT は **`18,618 ms`（最大 `24,231 ms`）** まで悪化する。
3. **Pattern C（比較対照：非 JSON 先頭タグ `[DIRECT]` / `[THINK]`）**
   - `response_schema` を使わず、システムプロンプトの指示のみで先頭に `[DIRECT]` または `[THINK]` タグを出力させ（Stage 1 `thinking=low`）、文字列スライスでタグを除去してルーティングする方式。
   - 一見すると JSON スキーマを使わない Pattern C の方が速そうに見えるが、実測では **Pattern A（全9問平均 TTFT `2,388 ms`、Tier 3 平均 `2,131 ms`）の方が Pattern C（全9問平均 TTFT `2,930 ms`、Tier 3 平均 `3,659 ms`）よりも平均 `542 ms`（Tier 3 では `1.53 秒`）高速** であった。これは、Pattern A では `response_schema` の制約付きデコーディング（FSM）によってモデルが第1トークンから直ちに `{"thinking": true` を確定させる（Stage 1 思考 `0〜83 tok`）のに対し、自由テキストの Pattern C では `thinking=low` であってもタグ出力前に最大 `445 tok` の内部思考が走ってしまうためである。さらに Pattern C には「タグ表記揺れによる生タグ露出リスク」や「長期履歴でのタグ欠落ドリフト」という構造的弱点もある。

---

## 4.3 全45実行（9設問 × 5方式）の実測ベンチマーク評価（`low` → `high`）

`src/gemini_evaluation/benchmark_adaptive_thinking.py` により、Tier 1（3問）・Tier 2（3問）・Tier 3（3問）の計9問に対して、固定ベースライン2方式（`base_low`, `base_high`）と適応型3方式（`pat_a_pydantic_2f`, `pat_b_pydantic_1f`, `pat_c_tag`）の **全45実行（成功率 100%、適応型3方式すべてでルーティング正解率 9/9＝100%）** を計測した。難易度ティア別の平均 TTFT と平均完了時間（Total）を比較したグループ棒グラフを図4-2に示す。

```drawlib align=center code=fold width=100% file=ch04_tier_latency_barchart_ja.png caption="図4-2: 難易度ティア別（Tier 1・Tier 2・Tier 3・全9問平均）× 全5方式（gemini-3.8-flash: low / high）における平均 TTFT（左）と平均完了時間 Total（右）の比較"
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
    "全45実行ベンチマーク (3.8-flash low -> high)：難易度ティア別の平均 TTFT (左) と 平均 Total (右)",
    style=Styles.DarkBold.patch(text_size=11.5),
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
    (10.0, Styles.PrimaryFlat, "★ Pattern A: 2F統合 {thinking, response} (low -> high) [推奨]"),
    (96.0, Styles.TealFlat, "Pattern C: 先頭タグ [DIRECT]/[THINK] (low -> high)"),
]
for lx, st, ltxt in leg_row1:
    rectangle((lx, 99.3), width=3.6, height=2.0, style=st.patch(shape_r=0.3))
    text((lx + 2.8, 99.3), ltxt, style=Styles.DarkBold.patch(text_size=10.0, halign="left"))

leg_row2 = [
    (10.0, Styles.SuccessFlat, "Base Low: 固定 thinking=low (T3で思考0 tok)"),
    (72.0, Styles.WarningFlat, "Base High: 固定 thinking=high"),
    (118.0, Styles.DangerFlat, "Pattern B: 1F直列ルーター (low -> high)"),
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
chart_ttft.configure_x_axis(min_value=0, max_value=20000, tick_step=5000, format="{:,.0f}")
chart_ttft.add_series("pat_a", calc_means("pat_a_pydantic_2f", "ttft_ms"), style=Styles.PrimaryFlat)
chart_ttft.add_series("pat_c", calc_means("pat_c_tag", "ttft_ms"), style=Styles.TealFlat)
chart_ttft.add_series("base_low", calc_means("base_low", "ttft_ms"), style=Styles.SuccessFlat)
chart_ttft.add_series("base_high", calc_means("base_high", "ttft_ms"), style=Styles.WarningFlat)
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
chart_tot.configure_x_axis(min_value=0, max_value=30000, tick_step=10000, format="{:,.0f}")
chart_tot.add_series("pat_a", calc_means("pat_a_pydantic_2f", "total_ms"), style=Styles.PrimaryFlat)
chart_tot.add_series("pat_c", calc_means("pat_c_tag", "total_ms"), style=Styles.TealFlat)
chart_tot.add_series("base_low", calc_means("base_low", "total_ms"), style=Styles.SuccessFlat)
chart_tot.add_series("base_high", calc_means("base_high", "total_ms"), style=Styles.WarningFlat)
chart_tot.add_series("pat_b", calc_means("pat_b_pydantic_1f", "total_ms"), style=Styles.DangerFlat)
chart_tot.draw(xy=(105.5, 17.5))

# Bottom summary banner
rectangle((86.0, 6.2), width=160.0, height=6.4, style=Styles.PrimaryNeutral.patch(shape_r=1.2))
phosphor.check_circle((10.5, 6.2), width=3.2, style=Styles.PrimaryBold)
text(
    (14.0, 6.2),
    "要点：Pattern A は全ティアで TTFT ~2.4秒を維持し、Base High の最大16.5秒・Pattern B の最大24.2秒の初動凍結を完全に解消する。",
    style=Styles.DarkBold.patch(text_size=9.5, halign="left"),
)

save()
```

### 全45実行の TTFT × Total 散布図と UX 閾値ライン検証

平均値だけでなく、全9設問×5方式＝45実行の1回ごとのばらつきを検証するため、すべての実行を「X軸：初回トークン到着時間 `ttft_ms` × Y軸：全文完了時間 `total_ms`」の2次元平面上にプロットしたのが図4-3である。

```drawlib align=center code=fold width=100% file=ch04_all45_runs_scatter_ja.png caption="図4-3: 全45実行（9設問 × 5方式、gemini-3.8-flash low -> high）の TTFT × Total レイテンシー分布と初動応答ゾーンの比較"
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
    "全45実行 (9設問 × 5方式: low -> high) の TTFT × Total 分布と初動応答ゾーン比較",
    style=Styles.DarkBold.patch(text_size=12.0),
)

runs = load_adaptive_runs()
series_pts: dict[str, list[tuple[float, float]]] = {
    "pat_a_pydantic_2f": [],
    "pat_c_tag": [],
    "base_low": [],
    "base_high": [],
    "pat_b_pydantic_1f": [],
}
for r in runs:
    series_pts[r["method_key"]].append((float(r["ttft_ms"]), float(r["total_ms"])))

# Left Chart Container
rectangle((62.0, 47.0), width=112.0, height=69.0, style=Styles.WhiteFlat.patch(shape_r=1.4, line_width=0.8))

# 2-row custom legend at top of chart container
rectangle((62.0, 75.8), width=107.0, height=8.8, style=Styles.Neutral.patch(shape_r=1.0))
leg1 = [
    (11.5, Styles.PrimaryFlat, "★ Pattern A: 2F統合 (low->high)"),
    (64.5, Styles.TealFlat, "Pattern C: 先頭タグ (low->high)"),
]
for lx, st, ltxt in leg1:
    rectangle((lx, 77.8), width=3.2, height=1.8, style=st.patch(shape_r=0.3))
    text((lx + 2.4, 77.8), ltxt, style=Styles.DarkBold.patch(text_size=10.0, halign="left"))

leg2 = [
    (11.5, Styles.SuccessFlat, "Base Low: 固定low"),
    (46.5, Styles.WarningFlat, "Base High: 固定high"),
    (83.5, Styles.DangerFlat, "Pattern B: 1F直列"),
]
for lx, st, ltxt in leg2:
    rectangle((lx, 73.8), width=3.2, height=1.8, style=st.patch(shape_r=0.3))
    text((lx + 2.4, 73.8), ltxt, style=Styles.Dark.patch(text_size=10.0, halign="left"))

# Highlight UX target zone inside plot area
PX0 = 24.8
PW_AX = 82.5
PY0 = 25.0
PH_AX = 40.2

x_3500 = PX0 + (3500.0 / 25000.0) * PW_AX

rectangle(
    ((PX0 + x_3500) / 2.0, (PY0 + PY0 + PH_AX) / 2.0),
    width=x_3500 - PX0,
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
    max_value=25000,
    tick_step=5000,
    format="{:,.0f}",
)
chart.configure_y_axis(
    min_value=0,
    max_value=36000,
    tick_step=9000,
    format="{:,.0f}",
)

chart.add_series("Base High", series_pts["base_high"], style=Styles.WarningFlat, shape="rhombus", radius=1.2)
chart.add_series("Pattern B", series_pts["pat_b_pydantic_1f"], style=Styles.DangerFlat, shape="square", radius=1.15)
chart.add_series("Base Low", series_pts["base_low"], style=Styles.SuccessFlat, shape="square", radius=1.15)
chart.add_series("Pattern C", series_pts["pat_c_tag"], style=Styles.TealFlat, shape="triangle", radius=1.2)
chart.add_series("Pattern A", series_pts["pat_a_pydantic_2f"], style=Styles.PrimaryFlat, shape="circle", radius=1.3)

chart.draw(xy=(10.0, 16.5))
text((11.5, 68.0), "全文完了 Total (ms)", style=Styles.DarkBold.patch(text_size=9.5, halign="left"))

# Vertical UX Threshold Line
line((x_3500, PY0), (x_3500, PY0 + PH_AX), style=Styles.PrimaryBold.patch(line_width=1.5))
text((x_3500 + 2.0, 68.0), "← 3.5s 即応上限ライン", style=Styles.PrimaryBold.patch(text_size=9.5, halign="left"))

# Right-side Summary Cards
rectangle((143.0, 47.0), width=44.0, height=69.0, style=Styles.PrimaryNeutral.patch(shape_r=1.5))
text((143.0, 77.2), "全45実行の分布インサイト", style=Styles.PrimaryBold.patch(text_size=11.0))

cards = [
    (
        63.0,
        "1. Pattern A は平均 2.39秒",
        "全9問が TTFT 1.8〜3.5s 帯に\n収束し、Base High (平均 12.8s)\nの初動待機を -81.4% 短縮!",
        Styles.PrimaryBold,
    ),
    (
        44.5,
        "2. Y軸伸長と X軸の直交分離",
        "Tier 3 で Total が 16〜27秒へ\n伸びても Pattern A の TTFT は\n~2.1秒のまま右へドリフトしない",
        Styles.SuccessBold,
    ),
    (
        26.0,
        "3. Base High / Pat B の凍結",
        "high の推論負荷が TTFT に直結\nし、最大 16.5〜24.2 秒まで\n無応答で画面が停止する",
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
    "結論：Pattern A は全9問で TTFT 3.5秒以内にロックされ、Base High の 10.5〜16.5秒におよぶ画面フリーズを根絶している。",
    style=Styles.DarkBold.patch(text_size=10.0, halign="left"),
)

save()
```

### 全9設問 × 5方式の実測メトリクス一覧テーブル（`gemini-3.8-flash`: `low` → `high`）

図4-2・図4-3の元データである全45実行の `TTFT / Total`（単位：`ms`）、内部推論トークン数（`ThTok`）、ルーティング判定結果、および Tier 3 計算精度を下表にまとめる。

| 設問 ID・タイトル | 期待分岐<br>（A/B/C判定） | Base Low (`low`)<br>`TTFT / Total (ThTok)` | Base High (`high`)<br>`TTFT / Total (ThTok)` | ★ Pattern A (`2F統合`)<br>`TTFT / Total (ThTok)` | Pattern B (`1F直列`)<br>`TTFT / Total (ThTok)` | Pattern C (`先頭タグ`)<br>`TTFT / Total (ThTok)` | 回答品質・計算検証 |
| :--- | :---: | ---: | ---: | ---: | ---: | ---: | :--- |
| **`T1_1` 初回挨拶（PC起動トラブル）** | `False` (`3/3`) | `1,533 / 5,741` (`0`) | `13,039 / 17,434` (`921`) | **`2,234 / 4,536` (`0`)** | `3,837 / 6,992` (`49`) | `2,087 / 6,318` (`56`) | 全方式妥当（A が最速完了） |
| **`T1_2` お礼・相槌** | `False` (`3/3`) | `2,595 / 4,746` (`53`) | `10,501 / 13,758` (`852`) | **`2,144 / 2,614` (`34`)** | `4,145 / 6,945` (`28`) | `2,272 / 3,390` (`45`) | 全方式妥当（A が最速完了） |
| **`T1_3` サポート窓口受付時間** | `False` (`3/3`) | `2,428 / 9,769` (`0`) | `12,708 / 19,842` (`1117`) | **`2,190 / 3,987` (`0`)** | `5,077 / 10,777` (`153`) | `2,347 / 4,115` (`37`) | 全方式妥当（A が最速完了） |
| **`T2_1` 電源が入らない時の放電手順** | `False` (`3/3`) | `1,331 / 9,477` (`0`) | `11,964 / 20,864` (`991`) | **`2,174 / 5,764` (`46`)** | `4,197 / 13,589` (`42`) | `2,531 / 8,426` (`35`) | 全方式妥当（A が最速完了） |
| **`T2_2` セーフモード起動とデータ退避** | `False` (`3/3`) | `2,923 / 15,001` (`0`) | `13,417 / 25,827` (`1153`) | **`2,870 / 3,811` (`0`)** | `5,210 / 14,835` (`42`) | `3,242 / 8,318` (`58`) | 全方式妥当（A が最速完了） |
| **`T2_3` システム修復コマンドの実行** | `False` (`3/3`) | `2,576 / 14,011` (`0`) | `11,229 / 22,851` (`1019`) | **`3,489 / 5,398` (`0`)** | `5,481 / 14,097` (`60`) | `2,913 / 11,215` (`64`) | 全方式妥当（A が最速完了） |
| **`T3_1` PC修理vs買い替え3年比較** | `True` (`3/3`) | `2,922 / 13,899` (**`0`**) | `14,104 / 23,247` (`1466`) | **`1,795 / 21,482` (`902`)** | `16,402 / 26,659` (`1538`) | `3,250 / 21,309` (`1309`) | `high` 4方式が深い事前検算済 |
| **`T3_2` 1.8TB退避＋クラウド転送時間** | `True` (`3/3`) | `1,392 / 9,583` (**`0`**) | `16,510 / 27,861` (`1882`) | **`2,728 / 27,017` (`1591`)** | `24,231 / 35,330` (`2346`) | `5,654 / 31,139` (`2073`) | `high` 4方式が深い事前検算済 |
| **`T3_3` 代替機レンタルvs当日出張修理** | `True` (`3/3`) | `1,693 / 7,729` (**`0`**) | `11,965 / 18,577` (`1295`) | **`1,870 / 16,240` (`674`)** | `15,222 / 20,844` (`1362`) | `2,073 / 18,607` (`806`) | `high` 4方式が深い事前検算済 |
| **Tier 1 平均（3問）** | **`3/3` 一致** | `2,186 / 6,752` (`18`) | `12,083 / 17,011` (`963`) | **`2,189 / 3,713` (`11`)** | `4,353 / 8,238` (`77`) | `2,235 / 4,608` (`46`) | **Pattern A が完了最速** |
| **Tier 2 平均（3問）** | **`3/3` 一致** | `2,277 / 12,830` (`0`) | `12,203 / 23,181` (`1054`) | **`2,844 / 4,991` (`15`)** | `4,963 / 14,174` (`48`) | `2,895 / 9,320` (`52`) | **Pattern A が完了最速** |
| **Tier 1–2 平均（6問）** | **`6/6` 一致** | `2,231 / 9,791` (`9`) | `12,143 / 20,096` (`1009`) | **`2,517 / 4,352` (`13`)** | `4,658 / 11,206` (`62`) | `2,565 / 6,964` (`49`) | **Pattern A が完了最速** |
| **Tier 3 平均（3問）** | **`3/3` 一致** | `2,002 / 10,404` (**`0`**) | `14,193 / 23,228` (`1548`) | **`2,131 / 21,580` (`1056`)** | `18,618 / 27,611` (`1749`) | `3,659 / 23,685` (`1396`) | **Base Low は T3 で思考 `0 tok`!** |
| **全9問平均** | **`9/9` 一致** | `2,155 / 9,995` (`6`) | `12,826 / 21,140` (`1188`) | **`2,388 / 10,094` (`361`)** | `9,311 / 16,674` (`624`) | `2,930 / 12,538` (`498`) | **Pattern A が総合最適** |

> **注目すべき発見（なぜ固定 `thinking=low` では不十分で、かつ Pattern A が Pattern C より速いのか）**：
> 1. **固定 `base_low` は Tier 3 全3問で内部思考トークンが `0 tok` だった**：`gemini-3.8-flash` に `thinking_level=LOW` を指定して通常の質問応答を行わせた結果、`T3_1`・`T3_2`・`T3_3` のいずれの複雑計算でも `thoughts_token_count = 0` となり、事前検算なしに即答を開始した。つまり複雑計算で確実に内部スクラッチパッド検算を発動させるには、Stage 2 として `medium` または `high`（本実験では `high`、平均 `1,056〜1,548 tok`）へエスカレーションする仕組みが不可欠である。
> 2. **Pattern A は Tier 3 で Pattern C より `1.53 秒` 速く初動を開始する**：Pattern A の Stage 1 は Pydantic スキーマ（`{thinking: bool, response: str}`）の制約付きデコーディングにより、Tier 3 の全3問でわずか `0〜83 tok` の思考で即座に `"thinking": true` を出力し、平均 **`2,131 ms`** で受付1文を表示した（`Base High` の `14,193 ms` 比で **約12.1秒のフリーズ解消**）。

---

## 4.4 ストリーム軌跡の深掘り（`thinking=false` 直接完結 vs. `thinking=true` 並列チェイニング）

Pattern A がどのようにして「定型質問での単一ストリーム完結（`low`）」と「複雑計算での2段階並列チェイニング（`low` → `high`）」を切り替えているのかを視覚化するため、`load_adaptive_trajectory()` を用いて **`T2_1`（Tier 2：電源が入らない時の放電手順）** と **`T3_1`（Tier 3：PC修理 vs. 買い替え 3年間総コスト比較）** の累積出力文字数軌跡を比較したのが図4-4である。

```drawlib align=center code=fold width=100% file=ch04_trajectory_deep_dive_ja.png caption="図4-4: Tier 2 定型手続き (T2_1: thinking=false 単一 low 完結) と Tier 3 複雑計算 (T3_1: thinking=true 受付1文 + Stage 2 high 並列連結) のストリーム軌跡比較"
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
    "ストリーム軌跡の深掘り (low -> high)：T2_1 (thinking=false 直接完結) vs. T3_1 (thinking=true 並列連結)",
    style=Styles.DarkBold.patch(text_size=11.5),
)

# Shared Legend Bar
rectangle((86.0, 82.8), width=162.0, height=5.2, style=Styles.Neutral.patch(shape_r=1.0))

leg_items = [
    (7.5, Styles.PrimaryBold, Styles.PrimaryFlat, "★ Pattern A (2F統合 low->high)"),
    (46.5, Styles.TealBold, Styles.TealFlat, "Pattern C (先頭タグ)"),
    (77.5, Styles.SuccessBold, Styles.SuccessFlat, "Base Low (固定low)"),
    (108.5, Styles.WarningBold, Styles.WarningFlat, "Base High (固定high)"),
    (140.5, Styles.DangerBold, Styles.DangerFlat, "Pattern B (1F直列)"),
]
for lx, lst, cst, ltxt in leg_items:
    line((lx, 82.8), (lx + 3.2, 82.8), style=lst.patch(line_width=2.2))
    circle((lx + 1.6, 82.8), radius=0.7, style=cst)
    text((lx + 4.0, 82.8), ltxt, style=Styles.DarkBold.patch(text_size=9.2, halign="left"))


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
    rectangle((x0 + pw / 2, 46.5), width=pw + 14.0, height=65.0, style=Styles.LightFlat.patch(shape_r=1.6))
    text((x0 + pw / 2, 74.8), title_s, style=Styles.DarkBold.patch(text_size=10.6))
    text((x0 + pw / 2, 71.0), sub_s, style=Styles.PrimaryBold.patch(text_size=9.5))
    rectangle((x0 + pw / 2, y0 + ph / 2), width=pw, height=ph, style=Styles.WhiteFlat)

    def px(t_ms: float) -> float:
        return x0 + min(max(t_ms, 0.0), max_t) / max_t * pw

    def py(c_val: float) -> float:
        return y0 + min(max(c_val, 0.0), max_c) / max_c * ph

    for xt in x_ticks:
        tx = px(float(xt))
        line((tx, y0), (tx, y0 + ph), style=Styles.LightDashed.patch(line_width=0.7))
        text((tx, y0 - 2.4), f"{xt / 1000:.0f}s", style=Styles.Dark.patch(text_size=9.5))

    for yt in y_ticks:
        ty = py(float(yt))
        line((x0, ty), (x0 + pw, ty), style=Styles.LightDashed.patch(line_width=0.7))
        text((x0 - 3.6, ty), f"{yt:,}", style=Styles.Dark.patch(text_size=9.5))

    line((x0, y0), (x0 + pw, y0), style=Styles.Dark.patch(line_width=1.1))
    line((x0, y0), (x0, y0 + ph), style=Styles.Dark.patch(line_width=1.1))

    method_styles = [
        ("base_low", Styles.SuccessBold.patch(line_width=1.6), Styles.SuccessFlat, 0.6),
        ("pat_c_tag", Styles.TealBold.patch(line_width=1.7), Styles.TealFlat, 0.65),
        ("base_high", Styles.WarningBold.patch(line_width=1.8), Styles.WarningFlat, 0.7),
        ("pat_b_pydantic_1f", Styles.DangerBold.patch(line_width=1.8), Styles.DangerFlat, 0.7),
        ("pat_a_pydantic_2f", Styles.PrimaryBold.patch(line_width=2.5), Styles.PrimaryFlat, 0.9),
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
    ph=36.5,
    prompt_id="T2_1",
    title_s="① Tier 2 定型手続き (T2_1: 放電・AC確認手順)",
    sub_s="thinking=false：Stage 1 (low) 単一呼出で最速ストリーム完結",
    max_t=22000.0,
    max_c=1600.0,
    x_ticks=[0, 5000, 10000, 15000, 20000],
    y_ticks=[0, 400, 800, 1200, 1600],
)

# Dedicated Top Callout Strip for Left Panel (y=58..67, zero curve overlap)
rectangle((26.5, 62.5), width=35.0, height=8.6, style=Styles.PrimaryNeutral.patch(shape_r=0.9))
text((26.5, 64.5), "★ Pat A: 2,174 ms 開始", style=Styles.PrimaryBold.patch(text_size=9.0))
text((26.5, 60.5), "5,764 ms 最速完了!", style=Styles.DarkBold.patch(text_size=9.0))
line((28.0, 58.2), (px_l(5764.0), py_l(626.0)), arrow_head="->", style=Styles.PrimaryBold.patch(line_width=1.4))

rectangle((63.5, 62.5), width=35.0, height=8.6, style=Styles.WhiteFlat.patch(shape_r=0.9, line_width=0.7))
text((63.5, 64.5), "Base High: 11,964 ms 凍結", style=Styles.WarningBold.patch(text_size=9.0))
text((63.5, 60.5), "不要思考 991 tok で遅延", style=Styles.Dark.patch(text_size=8.8))
line((56.0, 58.2), (px_l(11964.0), py_l(40.0)), arrow_head="->", style=Styles.WarningBold.patch(line_width=1.3))

# Right Panel: T3_1 (Complex Math, thinking=true)
px_r, py_r = draw_multi_trajectory_panel(
    x0=98.0,
    y0=18.5,
    pw=63.0,
    ph=36.5,
    prompt_id="T3_1",
    title_s="② Tier 3 複雑計算 (T3_1: PC修理vs買い替え比較)",
    sub_s="thinking=true：受付1文 (1,795ms) + Stage 2 (high) 並列連結",
    max_t=28000.0,
    max_c=2000.0,
    x_ticks=[0, 7000, 14000, 21000, 28000],
    y_ticks=[0, 500, 1000, 1500, 2000],
)

# Dedicated Top Callout Strip for Right Panel (y=58..67, zero curve overlap)
rectangle((109.5, 62.5), width=35.5, height=8.6, style=Styles.PrimaryNeutral.patch(shape_r=0.9))
text((109.5, 64.5), "① 1,795 ms 受付1文表示", style=Styles.PrimaryBold.patch(text_size=9.0))
text((109.5, 60.5), "High比 12.3秒の凍結解消!", style=Styles.DarkBold.patch(text_size=8.8))
line((103.5, 58.2), (px_r(1795.0), py_r(60.0)), arrow_head="->", style=Styles.PrimaryBold.patch(line_width=1.4))

rectangle((146.5, 62.5), width=35.5, height=8.6, style=Styles.WhiteFlat.patch(shape_r=0.9, line_width=0.7))
text((146.5, 64.5), "② 11,615 ms〜 Stage 2 連結", style=Styles.PrimaryBold.patch(text_size=9.0))
text((146.5, 60.5), "859 tok 検算・21.5s 完結", style=Styles.Dark.patch(text_size=8.8))
line((136.0, 58.2), (px_r(11615.0), py_r(90.0)), arrow_head="->", style=Styles.PrimaryBold.patch(line_width=1.4))

# Bottom summary banner
rectangle((86.0, 6.0), width=160.0, height=6.4, style=Styles.PrimaryNeutral.patch(shape_r=1.2))
phosphor.sparkle((10.5, 6.0), width=3.2, style=Styles.PrimaryBold)
text(
    (14.0, 6.0),
    "結論：Pattern A は T2_1 で 5,764 ms 最速完了し、T3_1 では 1,795 ms ブリッジ文で Base High の 12.3秒画面凍結を隠蔽する。",
    style=Styles.DarkBold.patch(text_size=10.0, halign="left"),
)

save()
```

### 図4-4 の軌跡が示す2つの決定的な優位性

1. **左パネル `T2_1`（`thinking=false`：電源が入らない時の放電手順）における単一 API 完結と最速完了**：
   - Pattern A（青太線）は **`2,174 ms`** で `"thinking": false` を確定して `"response"` フィールドのストリーミングを開始し、**`5,764 ms` でストリーム完了** して全5方式で最も早く回答を完結させている。
   - 対して Base High（黄線）は不要な内部推論を `991 tok` も回すため **`11,964 ms` まで1文字も表示されず**、完了に `20,864 ms` を要している。
2. **右パネル `T3_1`（`thinking=true`：PC修理 vs. 買い替え3年比較）における `12.3 秒` の画面凍結解消**：
   - Base High（黄線）は `1,466 tok` の内部推論が終わる **`14,104 ms` にわたり累積文字数 0 文字のまま画面が凍結** し、Pattern B（赤線）はさらに遅い **`16,402 ms`** まで1文字も表示されない。また Base Low（緑線）は `2,922 ms` で始まるものの内部推論が `0 tok` で走っており事前検算が行われない。
   - 対して Pattern A（青太線）は、**`1,795 ms`** で `"thinking": true` を検知した瞬間にバックグラウンドで Stage 2（`thinking=high`）を非同期起動しつつ、Stage 1 のブリッジメッセージ（58文字）を即座に画面へ表示する。これにより、Base High と比較して **`12,309 ms`（約 `12.3 秒`）もの無応答フリーズを完全に解消** している。ユーザーがブリッジ文を読んでいる間に Stage 2 が `859 トークン` の内部推論を終え、**`11,615 ms`** から本計算のストリームが滑らかに立ち上がって **`21,482 ms`** に正確な試算結果（修理 `162,400円` vs. 買い替え `184,500円`、**修理が `22,100円` お得**）を完結させている。

---

## 4.5 Google AI Studio 実装コードと総合評価スコアカード

### Pattern A の Google AI Studio (`google-genai`) リファレンス実装（`low` → `high`）

`google-genai` SDK のストリーミング時は `chunk.parsed` がストリーム途中で常に `None` となるため、Pydantic v2 標準同梱の `pydantic_core.from_json(..., allow_partial="trailing-strings")` を用いて不完全な JSON バッファから安全に `thinking` フラグとエスケープ解決済みの `response` デルタを抽出する（`src/gemini_evaluation/adaptive_thinking.py`）。なお、4.1節で述べたとおり、初期応答をさらに高速化したければ Stage 1 の `STAGE1_MODEL` を `"gemini-3.5-flash-lite"`（`MINIMAL` または `LOW`）に変更し、Stage 2 の思考をより深くしたければ `STAGE2_MODEL` を `"gemini-4-hydrogen"`（または複雑業務システムでは `"gemini-4-argon"` / `"gemini-4-carbon"`）へ差し替えるだけでそのまま動作する。

```python
import asyncio
from collections.abc import AsyncIterator
from contextlib import aclosing
from typing import Any

from google import genai
from google.genai import types
from pydantic import BaseModel
from pydantic_core import from_json

# 標準構成: gemini-3.8-flash (Stage 1: LOW -> Stage 2: HIGH)
# ・初期応答をさらに高速化する場合: STAGE1_MODEL = "gemini-3.5-flash-lite"
# ・思考をより深くする場合: STAGE2_MODEL = "gemini-4-hydrogen" (または "gemini-4-argon" / "gemini-4-carbon")
STAGE1_MODEL = "gemini-3.8-flash"
STAGE2_MODEL = "gemini-3.8-flash"


class AdaptiveStreamResponse(BaseModel):
    """Pattern A 用の最小2フィールド構造化ストリーミングスキーマ。"""

    thinking: bool  # 第1フィールド：初回チャンクで確定するルーティングフラグ
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
    """Pattern A: 2フィールド統合 Pydantic ストリーム (low) + Stage 2 並列チェイニング (high)。"""
    stage2_queue: asyncio.Queue[str | BaseException | None] = asyncio.Queue()
    stage2_task: asyncio.Task[None] | None = None

    async def _produce_stage2() -> None:
        try:
            st2 = await client.aio.models.generate_content_stream(
                model=STAGE2_MODEL,
                contents=prompt,
                config=types.GenerateContentConfig(
                    system_instruction=(
                        "冒頭の挨拶や受付文は既に表示済みです。"
                        "挨拶を繰り返さず、直ちに本題の計算ステップと結論を回答してください。"
                    ),
                    thinking_config=types.ThinkingConfig(
                        thinking_level=types.ThinkingLevel.HIGH,
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
            model=STAGE1_MODEL,
            contents=prompt,
            config=types.GenerateContentConfig(
                system_instruction=(
                    "挨拶や定型手続き案内では thinking: false とし response に回答全文を出力してください。"
                    "複数条件の数値計算・比較では thinking: true とし response に1文の受付メッセージのみを出力してください。"
                ),
                response_mime_type="application/json",
                response_schema=AdaptiveStreamResponse,
                thinking_config=types.ThinkingConfig(
                    thinking_level=types.ThinkingLevel.LOW,
                ),
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

                # 1) thinking フラグが確定した瞬間に1度だけ判定し、True なら Stage 2 (HIGH) を並列起動
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

### 全5方式の総合評価スコアカード（`gemini-3.8-flash`: `low` → `high`）

| 評価項目 | ★ Pattern A (`pat_a_pydantic_2f`)<br>`{thinking, response}` 統合 (`low->high`) | Pattern C (`pat_c_tag`)<br>`[DIRECT]` / `[THINK]` タグ (`low->high`) | Pattern B (`pat_b_pydantic_1f`)<br>`{thinking}` 直列ルーター (`low->high`) | Base High (`base_high`)<br>固定 `thinking=high` | Base Low (`base_low`)<br>固定 `thinking=low` |
| :--- | :---: | :---: | :---: | :---: | :---: |
| **全9問平均 TTFT** | **`2,388 ms` (優良 `< 2.5s`)** | `2,930 ms` (許容 `< 3.5s`) | `9,311 ms` (不可 `> 3.5s`) | `12,826 ms` (不可 `> 3.5s`) | **`2,155 ms` (優良 `< 2.5s`)** |
| **Tier 1–2 平均 TTFT / 完了** | **`2,517 ms` / `4,352 ms` (最速完了)** | `2,565 ms` / `6,964 ms` | `4,658 ms` / `11,206 ms` | `12,143 ms` / `20,096 ms` | `2,231 ms` / `9,791 ms` |
| **Tier 3 平均 TTFT（最大）** | **`2,131 ms` (`2,728 ms`)** | `3,659 ms` (`5,654 ms`) | `18,618 ms` (`24,231 ms`) | `14,193 ms` (`16,510 ms`) | `2,002 ms` (`2,922 ms`) |
| **ルーティング正解率** | **`9 / 9` (`100%`)** | **`9 / 9` (`100%`)** | **`9 / 9` (`100%`)** | 固定（常時 `high`） | 固定（常時 `low`） |
| **Tier 3 複雑計算検証 (`ThTok`)** | **`3 / 3` (`674〜1,591 tok` 検算)** | **`3 / 3` (`806〜2,073 tok` 検算)** | **`3 / 3` (`1,362〜2,346 tok` 検算)** | **`3 / 3` (`1,295〜1,882 tok` 検算)** | **不可（全3問で `0 tok`・無検算）** |
| **API 呼び出し回数 (T1–2 / T3)** | **`1.0 回` / `2.0 回`** | `1.0 回` / `2.0 回` | `2.0 回` / `2.0 回` | `1.0 回` / `1.0 回` | `1.0 回` / `1.0 回` |
| **デコーダ層の型保証・拡張性** | **優良（Constrained Decoding）** | 不可（タグ露出・履歴ドリフト懸念） | 一部のみ（ルーターのみ型保証） | なし（平文） | なし（平文） |
| **総合判定** | **★ 本番標準採用（最速＆型安全）** | 不採用（A より遅く型保証なし） | 不採用（最大 `24.2s` 凍結） | 非推奨（最大 `16.5s` 凍結） | 不採用（複雑計算で思考 `0 tok`） |
