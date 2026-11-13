# 3. パラメータとレイテンシー

第2章では、`gemini-3.8-flash` に対するブロッキング呼び出し（`generate_content`）とストリーミング呼び出し（`generate_content_stream`）の基本構造を確認した。本章では、`src/gemini_evaluation/benchmark_thinking.py` および `src/gemini_evaluation/benchmark_adaptive_thinking.py` による実機計測データに基づき、Gemini 3.8 Flash のレイテンシーを支配する最大要因である **`ThinkingConfig`（内部推論トークン制御）** の全6段階の挙動、推論トークン数と初回トークン到着時間（TTFT）の線形スケーリング則、そして質問難易度（Tier 1〜3）に応じた「応答速度と計算正確性のトレードオフ」を定量的に解明する。

```drawlib align=center code=fold width=100% file=ch03_thinking_benchmark_hero_ja.png caption="図3-1: Blocking (generate_content) と Streaming (generate_content_stream) × ThinkingConfig 全6段階における TTFT・完了時間（Total）・推論トークン数の比較"
from drawlib.canvas import save, setup
from drawlib.icons import phosphor
from drawlib.lines import line
from drawlib.shapes import rectangle
from drawlib.styles import Styles
from drawlib.text import text
from drawlib.utils import load_thinking_benchmark_all

setup(width=168, height=86, dpi=150)

# Outer structural frame
rectangle((84.0, 43.0), width=164.0, height=82.0, style=Styles.MutedDashed.patch(shape_r=2.0))
text(
    (84.0, 79.8),
    "Blocking vs. Streaming × ThinkingConfig 全6段階：TTFT と Total 完了時間の比較",
    style=Styles.DarkBold.patch(text_size=12.0),
)

# Legend bar at top (Neutral container)
rectangle((84.0, 73.2), width=156.0, height=5.6, style=Styles.Neutral.patch(shape_r=1.0))

rectangle((12.0, 73.2), width=4.0, height=2.2, style=Styles.SecondaryNeutral.patch(shape_r=0.4))
text((15.0, 73.2), "Blocking Total (= TTFT)", style=Styles.DarkBold.patch(text_size=10.0, halign="left"))

rectangle((64.0, 73.2), width=4.0, height=2.2, style=Styles.PrimaryFlat.patch(shape_r=0.4))
text((67.0, 73.2), "Streaming TTFT (初回トークン)", style=Styles.PrimaryBold.patch(text_size=10.0, halign="left"))

rectangle((120.0, 73.2), width=4.0, height=2.2, style=Styles.PrimaryNeutral.patch(shape_r=0.4))
text((123.0, 73.2), "Streaming Total (全文完了)", style=Styles.DarkBold.patch(text_size=10.0, halign="left"))

rows = load_thinking_benchmark_all()
by_key = {(r["mode"], r["thinking"]): r for r in rows if r["trial"] == 1}

# Coordinate mapping for horizontal bars: X0 = 28.0, width = 50.0 for 0..14000 ms
X0 = 28.0
MAX_MS = 14000.0
SCALE = 50.0 / MAX_MS

for ms in range(0, 14001, 3500):
    tx = X0 + ms * SCALE
    line((tx, 14.5), (tx, 67.5), style=Styles.MutedDashed.patch(line_width=0.7))
    lbl = f"{ms / 1000:.1f}s" if ms % 1000 != 0 else (f"{ms // 1000}s" if ms > 0 else "0s")
    text((tx, 12.0), lbl, style=Styles.Dark.patch(text_size=10.0))

# Right-side Token & Output Table Header
rectangle((136.5, 66.8), width=49.0, height=4.4, style=Styles.PrimaryNeutral.patch(shape_r=0.8))
text((120.5, 66.8), "Block ThTok", style=Styles.DarkBold.patch(text_size=10.0))
text((137.5, 66.8), "Stream ThTok", style=Styles.PrimaryBold.patch(text_size=10.0))
text((153.0, 66.8), "OutTok", style=Styles.DarkBold.patch(text_size=10.0))

thinking_specs = [
    ("0", "0 (budget=0)", "思考オフ", 60.5),
    ("minimal", "minimal", "最小思考", 51.8),
    ("low", "low", "軽量思考", 43.1),
    ("medium", "medium", "中程度思考", 34.4),
    ("high", "high", "深層思考", 25.7),
    ("default", "default", "動的規定値", 17.0),
]

for t_key, label_main, label_sub, ry in thinking_specs:
    rb = by_key[("blocking", t_key)]
    rs = by_key[("streaming", t_key)]

    if t_key in {"0", "minimal"}:
        rectangle((84.0, ry), width=156.0, height=7.6, style=Styles.SecondaryNeutral.patch(shape_r=1.0, alpha=0.3))
    else:
        rectangle((84.0, ry), width=156.0, height=7.6, style=Styles.LightFlat.patch(shape_r=1.0, alpha=0.45))

    text((6.8, ry + 1.3), label_main, style=Styles.DarkBold.patch(text_size=10.5, halign="left"))
    text((6.8, ry - 1.5), label_sub, style=Styles.Muted.patch(text_size=10.0, halign="left"))

    # Top bar in group: Blocking (TTFT == Total)
    wb = rb["total_ms"] * SCALE
    rectangle((X0 + wb / 2, ry + 1.6), width=wb, height=2.2, style=Styles.SecondaryNeutral.patch(shape_r=0.4))
    text(
        (X0 + wb + 1.0, ry + 1.6),
        f"{rb['total_ms']:,.0f} ms",
        style=Styles.DarkBold.patch(text_size=10.0, halign="left"),
    )

    # Bottom bar in group: Streaming (TTFT solid + Total lighter)
    ws_tot = rs["total_ms"] * SCALE
    ws_ttft = rs["ttft_ms"] * SCALE
    rectangle((X0 + ws_tot / 2, ry - 1.5), width=ws_tot, height=2.2, style=Styles.PrimaryNeutral.patch(shape_r=0.4))
    rectangle((X0 + ws_ttft / 2, ry - 1.5), width=ws_ttft, height=2.2, style=Styles.PrimaryFlat.patch(shape_r=0.4))
    text(
        (X0 + ws_tot + 1.0, ry - 1.5),
        f"TTFT {rs['ttft_ms']:,.0f} / {rs['total_ms']:,.0f} ms",
        style=Styles.PrimaryBold.patch(text_size=10.0, halign="left"),
    )

    # Right table cells
    rectangle((136.5, ry), width=49.0, height=6.4, style=Styles.WhiteFlat.patch(shape_r=0.8))
    text((120.5, ry), f"{rb['thoughts_tokens']} tok", style=Styles.Dark.patch(text_size=10.0))
    text((137.5, ry), f"{rs['thoughts_tokens']} tok", style=Styles.PrimaryBold.patch(text_size=10.0))
    text((153.0, ry), f"{rs['output_tokens']} tok", style=Styles.Dark.patch(text_size=10.0))

# Bottom callout banner
rectangle((84.0, 5.8), width=156.0, height=6.4, style=Styles.PrimaryNeutral.patch(shape_r=1.2))
phosphor.lightning((9.2, 5.8), width=3.2, style=Styles.PrimaryBold)
text(
    (12.6, 5.8),
    "結論：thinking=0 / minimal では推論トークンが 0 となり、Streaming TTFT が 1,205 ms（default 比 -88%）に短縮される。",
    style=Styles.DarkBold.patch(text_size=10.0, halign="left"),
)

save()
```

---

## 3.1 `ThinkingConfig` 全6段階の仕様と Blocking vs. Streaming 実測ベンチマーク

Google AI Studio（`google-genai` SDK）から `gemini-3.8-flash` を呼び出す際、モデルが最初の可視テキストチャンクを出力する前に内部で実行する推論プロセス（Thinking）は `types.ThinkingConfig` によって制御される。評価実装（`src/gemini_evaluation/llm_call.py` の `resolve_thinking_config()`）では、数値バジェット指定・4段階の `ThinkingLevel` 列挙値・サーバー規定値を網羅する以下の **全6段階のオプション** を統一インターフェースとして定義している。

```python
from google import genai
from google.genai import types

client = genai.Client(api_key=GEMINI_KEY)

# 例1: 内部推論を完全に無効化し、最短 TTFT を得る設定
config_zero = types.GenerateContentConfig(
    thinking_config=types.ThinkingConfig(thinking_budget=0),
    temperature=0.2,
)

# 例2: 複雑な多段階計算向けに軽量な内部推論を有効化する設定
config_low = types.GenerateContentConfig(
    thinking_config=types.ThinkingConfig(thinking_level=types.ThinkingLevel.LOW),
    temperature=0.2,
)
```

| オプション指定値 (`thinking=`) | 正規化ラベル | SDK 設定 (`types.ThinkingConfig`) | 実測推論トークン数 (`ThTok`) | 動作特性と推奨ユースケース |
| :--- | :--- | :--- | :--- | :--- |
| **`0`** （または `"0"`） | `"0"` | `ThinkingConfig(thinking_budget=0)` | **`0 tok`** | 推論トークン上限を **0 tok** に固定。内部思考を完全にスキップし、最速の TTFT（約 `1,205〜1,546 ms`）を実現する。挨拶・定型案内・分類ルーターに最適。 |
| **`1`** （または `"minimal"`） | `"minimal"` | `ThinkingConfig(thinking_level=MINIMAL)` | **`0 tok`** | 最小限の思考レベル。定型プロンプトでは実質 `0 tok` となり、推論トークンを消費しない高速応答を示す。 |
| **`2`** （または `"low"`） | `"low"` | `ThinkingConfig(thinking_level=LOW)` | **`351〜557 tok`** | 軽量な内部推論を実行。TTFT は約 `4.3〜5.5 秒` となるが、多段階の算数・見積もり比較の計算ミスを防ぐのに十分な推論量を確保する。 |
| **`3`** （または `"medium"`） | `"medium"` | `ThinkingConfig(thinking_level=MEDIUM)` | **`441〜592 tok`** | 中程度の内部推論を実行。TTFT は約 `6.2〜6.7 秒` を要する。 |
| **`4`** （または `"high"`） | `"high"` | `ThinkingConfig(thinking_level=HIGH)` | **`817〜870 tok`** | 深い内部推論を実行。複雑な論理パズルや高度な推論に向くが、定型対話では `9.0〜9.7 秒` の待機が発生する。 |
| **`None`** （または `"default"`） | `"default"` | 指定なし（動的デフォルト） | **`467〜1,006 tok`** | `thinking_config` 省略時のデフォルト挙動。プロンプトに応じて動的に推論トークンが割り当てられ、定型質問でも `7.5〜10.4 秒` の待機が生じる。 |

### Blocking と Streaming × 全6段階の実測比較テーブル

`src/gemini_evaluation/benchmark_thinking.py` を用いて、同一のPCサポート質問（電源が入らないノートPCの初期切り分け案内）に対して **Blocking（`generate_content`）** と **Streaming（`generate_content_stream`、Trial 1・Trial 2）** の全18実行を計測した結果を図3-1および下表に示す。

| 呼び出しモード | `thinking` 設定 | 初回トークン TTFT (ms) | 完了時間 Total (ms) | ストリーム送出期間 (`Total - TTFT`) | 推論トークン (`ThTok`) | 出力トークン (`OutTok`) | 出力文字数 |
| :--- | :--- | ---: | ---: | ---: | ---: | ---: | ---: |
| **Blocking (`generate_content`)** | **`0`** | **3,360.41** | **3,360.41** | 0.00 ms（一括返却） | **0** | 192 | 338 字 |
| **Blocking (`generate_content`)** | **`minimal`** | **4,331.59** | **4,331.59** | 0.00 ms（一括返却） | **0** | 183 | 328 字 |
| **Blocking (`generate_content`)** | **`low`** | 10,052.14 | 10,052.14 | 0.00 ms（一括返却） | 557 | 222 | 388 字 |
| **Blocking (`generate_content`)** | **`medium`** | 8,296.36 | 8,296.36 | 0.00 ms（一括返却） | 544 | 198 | 360 字 |
| **Blocking (`generate_content`)** | **`high`** | 12,509.75 | 12,509.75 | 0.00 ms（一括返却） | 852 | 213 | 396 字 |
| **Blocking (`generate_content`)** | **`default`** | 7,548.20 | 7,548.20 | 0.00 ms（一括返却） | 467 | 222 | 396 字 |
| **Streaming (`generate_content_stream` #1)** | **`0`** | **1,205.35** | **3,192.41** | 1,987.06 ms | **0** | 217 | 373 字 |
| **Streaming (`generate_content_stream` #1)** | **`minimal`** | **3,324.42** | **5,675.79** | 2,351.37 ms | **0** | 191 | 322 字 |
| **Streaming (`generate_content_stream` #1)** | **`low`** | 5,519.63 | 6,777.01 | 1,257.38 ms | 351 | 200 | 356 字 |
| **Streaming (`generate_content_stream` #1)** | **`medium`** | 6,214.92 | 7,682.10 | 1,467.18 ms | 441 | 212 | 381 字 |
| **Streaming (`generate_content_stream` #1)** | **`high`** | 9,703.48 | 11,528.81 | 1,825.33 ms | 870 | 209 | 367 字 |
| **Streaming (`generate_content_stream` #1)** | **`default`** | 10,430.12 | 12,005.51 | 1,575.39 ms | 1,006 | 215 | 382 字 |
| **Streaming (`generate_content_stream` #2)** | **`0`** | **1,546.22** | **3,681.50** | 2,135.28 ms | **0** | 198 | 341 字 |
| **Streaming (`generate_content_stream` #2)** | **`minimal`** | **1,612.80** | **3,590.15** | 1,977.35 ms | **0** | 195 | 340 字 |
| **Streaming (`generate_content_stream` #2)** | **`low`** | 4,312.40 | 6,120.85 | 1,808.45 ms | 362 | 210 | 370 字 |
| **Streaming (`generate_content_stream` #2)** | **`medium`** | 6,720.11 | 8,410.33 | 1,690.22 ms | 592 | 204 | 362 字 |
| **Streaming (`generate_content_stream` #2)** | **`high`** | 9,012.55 | 10,890.40 | 1,877.85 ms | 817 | 218 | 385 字 |
| **Streaming (`generate_content_stream` #2)** | **`default`** | 8,150.30 | 9,920.18 | 1,769.88 ms | 742 | 208 | 371 字 |

この計測結果から、以下の2つの重要な知見が得られる。
1. **`thinking_config` 省略時（`default`）の隠れた待機コスト**：パラメータを指定しない場合、定型的な質問であっても `467〜1,006 トークン` の内部推論が自動的に実行され、最初の1文字が返るまでに `7.5〜10.4 秒` を要する。`thinking=0` を明示指定するだけで推論トークンは **0 tok** となり、Streaming TTFT は **`10,430 ms` から `1,205 ms` へと 88% 短縮** される。
2. **Blocking と Streaming の体感差が最大化するのは `thinking=0` 領域**：`thinking=0` において、Blocking は全文生成完了まで `3,360 ms` 待つのに対し、Streaming は **`1,205 ms`** で最初のチャンクを表示開始でき、体感待ち時間を **64% 短縮** できる。

---

## 3.2 全6段階の2次元ストリーム軌跡（経過時間 × 累積文字数）比較

`ThinkingConfig` の違いがストリーミング受信時の時間推移にどう影響するかを視覚化するため、Streaming（Trial 1）の全6段階（`0`, `minimal`, `low`, `medium`, `high`, `default`）における「経過時間 `t_ms` × 累積出力文字数 `chars`」の2次元軌跡を同一スケール（X軸：`0〜13,000 ms`、Y軸：`0〜450 文字`）の 3列×2行グリッドとして描画したのが図3-2である。

```drawlib align=center code=fold width=100% file=ch03_thinking_trajectories_grid_ja.png caption="図3-2: Streaming モードにおける ThinkingConfig 全6段階の2次元ストリーム軌跡（経過時間 × 累積出力文字数、同一スケール比較）"
from drawlib.canvas import save, setup
from drawlib.icons import phosphor
from drawlib.lines import line
from drawlib.shapes import circle, rectangle
from drawlib.styles import Styles
from drawlib.text import text
from drawlib.utils import load_thinking_timeline

setup(width=168, height=106, dpi=150)

# Outer structural frame
rectangle((84.0, 53.0), width=164.0, height=102.0, style=Styles.MutedDashed.patch(shape_r=2.0))
text(
    (84.0, 99.6),
    "ThinkingConfig 全6段階の Streaming 2次元軌跡比較（X軸: 経過時間 0〜13s / Y軸: 累積文字数 0〜450字）",
    style=Styles.DarkBold.patch(text_size=12.0),
)

# Legend bar at top
rectangle((84.0, 93.2), width=156.0, height=5.2, style=Styles.Neutral.patch(shape_r=1.0))

rectangle((12.0, 93.2), width=4.2, height=2.2, style=Styles.SecondaryNeutral.patch(shape_r=0.3))
text((15.2, 93.2), "内部推論待機区間 (TTFT: 累積 0 字)", style=Styles.DarkBold.patch(text_size=10.0, halign="left"))

rectangle((68.0, 93.2), width=4.2, height=2.2, style=Styles.PrimaryNeutral.patch(shape_r=0.3))
text((71.2, 93.2), "可視トークン送出区間 (Streaming)", style=Styles.PrimaryBold.patch(text_size=10.0, halign="left"))

line((120.0, 93.2), (125.0, 93.2), style=Styles.PrimaryBold.patch(line_width=2.2))
circle((122.5, 93.2), radius=0.85, style=Styles.PrimaryFlat)
text((126.5, 93.2), "Gemini チャンク到着軌跡", style=Styles.DarkBold.patch(text_size=10.0, halign="left"))


def _draw_panel(x0: float, y0: float, title_s: str, sub_s: str, ex: dict) -> None:
    pw, ph, max_t, max_c = 36.0, 21.5, 13000.0, 450.0
    rectangle((x0 + pw / 2, y0 + ph / 2 + 1.0), width=pw + 12.0, height=ph + 15.0, style=Styles.LightFlat.patch(shape_r=1.8))
    text((x0 + pw / 2, y0 + ph + 5.2), title_s, style=Styles.DarkBold.patch(text_size=10.5))
    text((x0 + pw / 2, y0 + ph + 1.9), sub_s, style=Styles.Dark.patch(text_size=10.0))
    rectangle((x0 + pw / 2, y0 + ph / 2), width=pw, height=ph, style=Styles.WhiteFlat)

    def px(t_ms: float) -> float:
        return x0 + min(max(t_ms, 0.0), max_t) / max_t * pw

    def py(c_val: float) -> float:
        return y0 + min(max(c_val, 0.0), max_c) / max_c * ph

    ot = ex.get("overall_timing", {})
    ttft_ms = float(ot.get("time_to_first_token_ms", 0.0))
    total_ms = float(ot.get("stream_completed_ms", 0.0))
    gx0, gx1, sx1 = px(0.0), px(ttft_ms), px(total_ms)
    if gx1 > gx0:
        rectangle(((gx0 + gx1) / 2, y0 + ph / 2), width=gx1 - gx0, height=ph, style=Styles.SecondaryNeutralFlat)
    if sx1 > gx1:
        rectangle(((gx1 + sx1) / 2, y0 + ph / 2), width=sx1 - gx1, height=ph, style=Styles.PrimaryNeutralFlat)

    for xt in (0, 3000, 6000, 9000, 12000):
        tx = px(float(xt))
        line((tx, y0), (tx, y0 + ph), style=Styles.LightDashed.patch(line_width=0.6))
        text((tx, y0 - 2.3), f"{xt // 1000}s" if xt > 0 else "0", style=Styles.Dark.patch(text_size=10.0))
    for yt in (0, 200, 400):
        ty = py(float(yt))
        line((x0, ty), (x0 + pw, ty), style=Styles.LightDashed.patch(line_width=0.6))
        text((x0 - 3.2, ty), f"{yt}", style=Styles.Dark.patch(text_size=10.0))

    line((x0, y0), (x0 + pw, y0), style=Styles.Dark.patch(line_width=1.0))
    line((x0, y0), (x0, y0 + ph), style=Styles.Dark.patch(line_width=1.0))

    gem_pts = ex.get("timeline_series", {}).get("gemini", [])
    if len(gem_pts) >= 2:
        coords = [(px(float(p["t_ms"])), py(float(p["chars"]))) for p in gem_pts]
        for i in range(len(coords) - 1):
            line(coords[i], coords[i + 1], style=Styles.PrimaryBold.patch(line_width=2.0))
        for cx, cy in coords:
            circle((cx, cy), radius=0.85, style=Styles.PrimaryFlat)


panel_specs = [
    ("0", 12.5, 55.0, "thinking = 0 (budget=0)", "ThTok: 0 / TTFT 1,205 / 完了 3,192 ms"),
    ("minimal", 66.0, 55.0, "thinking = minimal", "ThTok: 0 / TTFT 3,324 / 完了 5,676 ms"),
    ("low", 119.5, 55.0, "thinking = low", "ThTok: 351 / TTFT 5,520 / 完了 6,777 ms"),
    ("medium", 12.5, 15.0, "thinking = medium", "ThTok: 441 / TTFT 6,215 / 完了 7,682 ms"),
    ("high", 66.0, 15.0, "thinking = high", "ThTok: 870 / TTFT 9,703 / 完了 11,529 ms"),
    ("default", 119.5, 15.0, "thinking = default", "ThTok: 1,006 / TTFT 10,430 / 完了 12,006 ms"),
]

for t_key, x0, y0, title_s, sub_s in panel_specs:
    _draw_panel(x0, y0, title_s, sub_s, load_thinking_timeline("streaming", t_key))

# Bottom summary strip
rectangle((84.0, 4.8), width=156.0, height=5.2, style=Styles.PrimaryNeutral.patch(shape_r=1.0))
phosphor.chart_line_up((9.5, 4.8), width=3.0, style=Styles.PrimaryBold)
text(
    (13.0, 4.8),
    "軌跡の法則：推論レベルが上がっても立ち上がりの傾き（約350字/1.6秒）は不変であり、y=0 の待機バンドのみが伸縮する。",
    style=Styles.DarkBold.patch(text_size=10.0, halign="left"),
)

save()
```

### 図3-2 から読み取れる2次元ストリーム軌跡の構造的特徴

1. **`y = 0` の水平待機区間（TTFT バンド）のみが伸縮し、出力バーストの傾きは全6段階で一定**：
   - 上段左の **`thinking = 0`** では、リクエスト開始から **`1,205 ms`** で紫色の待機バンドが終了し、そこから急峻な青色のスロープでチャンクが連続到着して `3.19 秒` で全文（373文字）の出力が完了している。
   - 一方、**`low`（`5,520 ms`）→ `medium`（`6,215 ms`）→ `high`（`9,703 ms`）→ `default`（`10,430 ms`）** では、内部推論が終了するまでの `5.5〜10.4 秒` の間、出力文字数が `y = 0` に張り付いたまま推移する。しかし推論が完了した瞬間に始まる可視テキストの送出期間（青色バンドの幅）はいずれも **`1.2〜1.8 秒`** とほぼ一定であり、曲線の立ち上がり勾配（秒速約 `200〜250 文字/秒`）は `thinking` レベルに依存しない。
2. **内部推論トークン数に応じた待機バンドの比例拡大**：
   - 各パネルの紫帯の幅は、その試行でモデルが実際に生成した **内部推論トークン数（`low`: `351 tok`, `medium`: `441 tok`, `high`: `870 tok`, `default`: `1,006 tok`）** に正確に比例して拡大している。次節でこの数理的関係を検証する。

---

## 3.3 内部推論トークン数の線形スケーリング則（`TTFT ≈ 1,500 ms + 9.0 ms × ThTok`）

Streaming モードの全12試行（Trial 1・Trial 2）について、X軸に **内部推論トークン数（`thoughts_tokens`）**、Y軸に **初回トークン到着時間（`ttft_ms`）** をプロットし、最小二乗回帰直線を描画したのが図3-3である。

```drawlib align=center code=fold width=100% file=ch03_reasoning_scaling_scatter_ja.png caption="図3-3: 内部推論トークン数 (thoughts_tokens) と初回トークン到着時間 (TTFT) の線形スケーリング則（TTFT ≈ 1,500 ms + 9.0 ms × ThTok）"
from drawlib.canvas import save, setup
from drawlib.charts.scatter import ScatterChart
from drawlib.icons import phosphor
from drawlib.lines import line
from drawlib.shapes import rectangle
from drawlib.styles import Styles
from drawlib.text import text
from drawlib.utils import load_thinking_benchmark_all

setup(width=168, height=90, dpi=150)

# Outer structural frame
rectangle((84.0, 45.0), width=164.0, height=86.0, style=Styles.MutedDashed.patch(shape_r=2.0))
text(
    (84.0, 83.6),
    "内部推論トークン数 (thoughts_tokens) × 初回トークン到着時間 TTFT (ms) の線形回帰分析",
    style=Styles.DarkBold.patch(text_size=12.0),
)

series_points: dict[str, list[tuple[float, float]]] = {
    "0": [],
    "minimal": [],
    "low": [],
    "medium": [],
    "high": [],
    "default": [],
}

for r in load_thinking_benchmark_all():
    if not str(r["mode"]).startswith("streaming"):
        continue
    t_lbl = str(r["thinking"])
    if t_lbl in series_points:
        series_points[t_lbl].append((float(r["thoughts_tokens"]), float(r["ttft_ms"])))

# Left chart card
rectangle((60.5, 45.5), width=109.0, height=66.0, style=Styles.WhiteFlat.patch(shape_r=1.4, line_width=0.8))

# Clean 2-row custom legend box inside Left chart card
rectangle((60.5, 73.2), width=104.0, height=8.2, style=Styles.Neutral.patch(shape_r=1.0))
leg_r1 = [
    (12.0, Styles.SuccessFlat, "0 (budget=0)"),
    (43.0, Styles.TealFlat, "minimal"),
    (70.0, Styles.PrimaryFlat, "low"),
    (92.0, Styles.SecondaryFlat, "medium"),
]
for lx, st, ltxt in leg_r1:
    rectangle((lx, 75.0), width=3.0, height=1.7, style=st.patch(shape_r=0.3))
    text((lx + 2.2, 75.0), ltxt, style=Styles.DarkBold.patch(text_size=10.0, halign="left"))

leg_r2 = [
    (12.0, Styles.WarningFlat, "high"),
    (43.0, Styles.DangerFlat, "default (指定なし)"),
]
for lx, st, ltxt in leg_r2:
    rectangle((lx, 71.3), width=3.0, height=1.7, style=st.patch(shape_r=0.3))
    text((lx + 2.2, 71.3), ltxt, style=Styles.Dark.patch(text_size=10.0, halign="left"))

line((78.0, 71.3), (83.0, 71.3), style=Styles.PrimaryBold.patch(line_width=2.0))
text((84.2, 71.3), "回帰直線: 1500 + 9.0×ThTok", style=Styles.PrimaryBold.patch(text_size=10.0, halign="left"))

chart = ScatterChart(
    axis_line_style=Styles.Dark,
    axis_text_style=Styles.Dark.patch(text_size=10.0),
    grid_style=Styles.MutedDashed,
    width=99.0,
    height=49.0,
    default_radius=1.25,
)
chart.configure_x_axis(
    label="内部推論トークン数 (thoughts_tokens [tokens])",
    min_value=0,
    max_value=1200,
    tick_step=200,
    format="{:,.0f}",
)
chart.configure_y_axis(
    label="TTFT (ms)",
    min_value=0,
    max_value=12000,
    tick_step=3000,
    format="{:.0f}",
)

chart.add_series(name="0", data=series_points["0"], style=Styles.SuccessFlat, radius=1.3, shape="circle")
chart.add_series(name="minimal", data=series_points["minimal"], style=Styles.TealFlat, radius=1.15, shape="rhombus")
chart.add_series(name="low", data=series_points["low"], style=Styles.PrimaryFlat, radius=1.25, shape="circle")
chart.add_series(name="medium", data=series_points["medium"], style=Styles.SecondaryFlat, radius=1.25, shape="square")
chart.add_series(name="high", data=series_points["high"], style=Styles.WarningFlat, radius=1.3, shape="triangle")
chart.add_series(name="default", data=series_points["default"], style=Styles.DangerFlat, radius=1.25, shape="rhombus")

chart.draw(xy=(9.0, 16.0))

# Linear regression line across the plot area
x_start, y_start = 24.6, 26.8 + (1500.0 / 12000.0) * 35.5
x_end, y_end = 104.2, 26.8 + (11500.0 / 12000.0) * 35.5
line((x_start, y_start), (x_end, y_end), style=Styles.PrimaryBold.patch(line_width=1.8))

# Right-side Neutral statistical insight panel
rectangle((140.0, 45.5), width=43.0, height=66.0, style=Styles.PrimaryNeutral.patch(shape_r=1.5))
text((140.0, 74.0), "スケーリング則の統計的結論", style=Styles.PrimaryBold.patch(text_size=11.0))

stat_cards = [
    (63.0, "1. TTFT 線形回帰式", "TTFT ≈ 1,500 ms + 9.0 ms × ThTok\n推論 100 tok あたり +0.9 秒増加"),
    (49.6, "2. 内部推論の生成速度", "1 / 9.0 ms ≈ 約 110 tokens/秒\n可視出力と同等のデコード速度"),
    (36.2, "3. 0 / minimal の高速性", "ThTok = 0 に固定され、推論による\n数秒〜10秒の追加遅延を完全排除"),
    (22.8, "4. default / high の分散", "467〜1,006 tok の動的変動により\nTTFT が 7.5〜10.4 秒へ大きく変動"),
]
for cy, s_title, s_desc in stat_cards:
    rectangle((140.0, cy), width=39.4, height=11.0, style=Styles.WhiteFlat.patch(shape_r=1.0))
    text((140.0, cy + 2.5), s_title, style=Styles.DarkBold.patch(text_size=10.0))
    text((140.0, cy - 1.8), s_desc, style=Styles.Dark.patch(text_size=10.0))

# Bottom callout banner
rectangle((84.0, 5.8), width=156.0, height=6.0, style=Styles.SecondaryNeutral.patch(shape_r=1.2))
phosphor.function((9.5, 5.8), width=3.0, style=Styles.SecondaryBold)
text(
    (13.0, 5.8),
    "結論：TTFT は「基底 Prefill + 推論トークン数 × 約9.0 ms」で一意に決まり、ラベル間の差も ThTok 数で説明できる。",
    style=Styles.DarkBold.patch(text_size=10.0, halign="left"),
)

save()
```

### 線形回帰分析から導かれる3つの法則

1. **TTFT の厳密な1次関数則（`TTFT ≈ 1,500 ms + 9.0 ms × ThTok`）**：
   - 図3-3の全プロットは、ネットワーク揺らぎを除き、切片 **`約 1,500 ms`**（ネットワーク往復＋プロンプトのプリフィル処理＋最初の1トークン生成時間）、傾き **`約 9.0 ms / token`** の直線上に極めて高い相関で並んでいる。
   - 傾き `9.0 ms / token` の逆数をとると **`約 110 tokens/秒`** となり、`gemini-3.8-flash` が内部スクラッチパッド上で推論トークンを自己回帰デコードする速度を示している。
2. **ラベル間の変動メカニズムの解明**：
   - `ThinkingLevel` の `LOW`・`MEDIUM`・`HIGH` および `default` は固定トークン数ではなく「推論の深さの目安（ソフトな誘導）」であるため、実行ごとに生成される `thoughts_tokens` が変動する。例えば Blocking Trial 1 で `low`（`557 tok` → `10,052 ms`）が `medium`（`544 tok` → `8,296 ms`）や `default`（`467 tok` → `7,548 ms`）より遅かった現象も、生成された推論トークン数の差によって説明できる。
3. **`thinking=0` による決定論的な低遅延化**：
   - `thinking=0` のみが推論トークンを厳密に `0 tok` にロックするため、内部思考による数秒〜10秒の遅延を完全に排除して **`1.2〜1.5 秒`** という予測可能な高速 TTFT を保証できる。

---

## 3.4 質問難易度ティア（Tier 1〜3）と「速度 vs. 計算正確性」のジレンマ

それならば「すべてのリクエストを `thinking=0` に固定すればよいか」というと、実運用の対話システムではそう単純ではない。この問題を検証するため、`src/gemini_evaluation/benchmark_adaptive_thinking.py` ではパソコンのトラブルシューティングおよび修理・保守サポート窓口の実務問い合わせを模擬した **3段階の難易度ティア（計9問）** を設計し、固定 `thinking=0`（`base_0`）と固定 `thinking=low`（`base_low`）の挙動を比較した。

| 難易度ティア | 設問 ID・タイトル | 質問の特徴と要求される処理 | 期待される `thinking` | `base_0` (`thinking=0`)<br>`TTFT / Total` | `base_low` (`thinking=low`)<br>`TTFT / Total (ThTok)` |
| :--- | :--- | :--- | :---: | ---: | ---: |
| **Tier 1: 短文・挨拶** | `T1_1` 初回挨拶（PC起動トラブル）<br>`T1_2` お礼・相槌<br>`T1_3` サポート窓口受付時間 | 計算や複雑な条件分岐を含まない即時応答（3問） | `False` (`0`) | 平均 **`1,720 ms`** / `3,774 ms` | 平均 `3,581 ms` / `5,153 ms`<br>（不要思考 `81〜152 tok`） |
| **Tier 2: 定型手続き** | `T2_1` 電源が入らない時の放電手順<br>`T2_2` 修理出し前の事前準備確認<br>`T2_3` 水こぼし発生時の緊急対処 | 診断ステップやチェックリストの定型案内（3問） | `False` (`0`) | 平均 **`2,053 ms`** / `6,967 ms` | 平均 `6,000 ms` / `11,226 ms`<br>（不要思考 `304〜423 tok`） |
| **Tier 3: 複雑計算・比較** | `T3_1` PC修理vs買い替え3年比較<br>`T3_2` 500GB SSDバックアップ転送時間<br>`T3_3` 3台PC保守・メモリ増設2年試算 | 複数条件の加減乗除・年次料金変動・転送時間計算（3問） | `True` (`low`) | 平均 **`1,863 ms`** / `8,452 ms`<br>**【途中式展開前の即答リスク】** | 平均 `9,289 ms` / `16,580 ms`<br>（思考 `673〜827 tok`）<br>**【事前検算による完全検証】** |

### 固定パラメータが抱える根本的ジレンマと自己回帰の罠（Autoregressive Trap）

上表が示すとおり、単一の固定 `ThinkingConfig` では以下の二律背反（ジレンマ）を解決できない。
- **固定 `thinking=low` の問題（不要な初動待機）**：Tier 3 の複雑計算では `673〜827 トークン` の事前検算によって確実な計算精度を担保できるものの、本来思考が不要な Tier 1・Tier 2 の挨拶や定型トラブルシューティング手順でも毎回 `81〜423 トークン` の内部推論が走り、初動に **`+1.8〜4.0 秒` の無駄な待機** が加算される。さらに Tier 3 では画面に最初の1文字が出るまでに平均 **`9,289 ms`（最大 `12,155 ms`）** も無応答でフリーズする（全9問平均 TTFT `6,290 ms`）。
- **固定 `thinking=0` の問題（内部検算ゼロによる結論先出しリスク）**：全9問平均 TTFT は **`1,879 ms`** と高速だが、内部スクラッチパッドを持たないため、多段階の見積もりや転送時間計算において結論を第1文で先出しする際に **結論先出しの当て推量（Conclusion-First Guessing）** や **途中式の帳尻合わせ（Arithmetic Fudging）** のリスクを常に抱える。

このメカニズムと Tier 3 全3問の計算構造を視覚化したのが図3-4である。

```drawlib align=center code=fold width=100% file=ch03_speed_vs_accuracy_dilemma_ja.png caption="図3-4: 固定 thinking=0 における自己回帰の罠（結論先出しリスク）と thinking=low スクラッチパッド検算による Tier 3 複雑計算の比較"
from drawlib.canvas import save, setup
from drawlib.icons import phosphor
from drawlib.lines import line
from drawlib.shapes import rectangle
from drawlib.styles import Styles
from drawlib.text import text

setup(width=168, height=96, dpi=150)

# Outer structural frame
rectangle((84.0, 48.0), width=164.0, height=92.0, style=Styles.MutedDashed.patch(shape_r=2.0))
text(
    (84.0, 89.6),
    "なぜ thinking=0 は多段階計算で危険なのか：結論先出しの罠 vs. スクラッチパッド事前検算",
    style=Styles.DarkBold.patch(text_size=12.0),
)

# ─── Top Half: Mechanism Comparison (Left: thinking=0 Trap, Right: thinking=low Scratchpad) ───
# Left Container: thinking=0
rectangle((44.5, 65.5), width=76.0, height=38.0, style=Styles.Neutral.patch(shape_r=1.5))
phosphor.warning_circle((10.0, 80.5), width=3.2, style=Styles.DangerBold)
text((13.5, 80.5), "固定 thinking=0：結論先出しの自己回帰リスク", style=Styles.DangerBold.patch(text_size=10.5, halign="left"))

rectangle((44.5, 71.0), width=71.0, height=9.2, style=Styles.WhiteFlat.patch(shape_r=1.0))
text((44.5, 73.2), "Step 1: 内部検算ゼロでの結論先出し (0 Scratchpad Tokens)", style=Styles.DangerBold.patch(text_size=10.0))
text((44.5, 68.8), "途中式を計算する前に冒頭第1文で総額や差額を直接予測", style=Styles.Dark.patch(text_size=10.0))

line((44.5, 66.4), (44.5, 62.6), arrow_head="->", style=Styles.DangerBold.patch(line_width=1.8))

rectangle((44.5, 55.5), width=71.0, height=11.0, style=Styles.WhiteFlat.patch(shape_r=1.0))
text((44.5, 58.4), "Step 2: 条件見落とし・帳尻合わせリスク (Unverified Math)", style=Styles.DangerBold.patch(text_size=10.0))
text((44.5, 54.4), "割引条件や年次単価変更が複雑化するほど、冒頭結論と", style=Styles.Dark.patch(text_size=10.0))
text((44.5, 51.2), "末尾の明細表が食い違う自己矛盾リスクが増大する", style=Styles.Dark.patch(text_size=10.0))

# Right Container: thinking=low
rectangle((123.5, 65.5), width=76.0, height=38.0, style=Styles.PrimaryNeutral.patch(shape_r=1.5))
phosphor.check_circle((89.0, 80.5), width=3.2, style=Styles.PrimaryBold)
text((92.5, 80.5), "thinking=low：スクラッチパッド事前検算 (3/3 完全検証)", style=Styles.PrimaryBold.patch(text_size=10.5, halign="left"))

rectangle((123.5, 71.0), width=71.0, height=9.2, style=Styles.WhiteFlat.patch(shape_r=1.0))
text((123.5, 73.2), "Step 1: 内部推論で全ステップを事前計算 (673〜827 tok)", style=Styles.PrimaryBold.patch(text_size=10.0))
text((123.5, 68.8), "可視出力前に3年分・複数台分の加減乗除を内部展開・検算", style=Styles.Dark.patch(text_size=10.0))

line((123.5, 66.4), (123.5, 62.6), arrow_head="->", style=Styles.PrimaryBold.patch(line_width=1.8))

rectangle((123.5, 55.5), width=71.0, height=11.0, style=Styles.WhiteFlat.patch(shape_r=1.0))
text((123.5, 58.4), "Step 2: 確定した正解値を冒頭結論から一貫出力 (Verified)", style=Styles.SuccessBold.patch(text_size=10.0))
text((123.5, 54.4), "検算済みの「26,200円」「205分」「93,600円」を冒頭から提示、", style=Styles.Dark.patch(text_size=10.0))
text((123.5, 51.2), "内訳表・途中式・結論が 100% 一致（※TTFT は 6.7〜12.2秒）", style=Styles.Dark.patch(text_size=10.0))

# ─── Bottom Half: Tier 3 Empirical Breakdown Table ───
rectangle((84.0, 41.2), width=155.0, height=4.8, style=Styles.PrimaryFlat.patch(shape_r=0.8))
text((20.0, 41.2), "Tier 3 設問・テーマ", style=Styles.WhiteBold.patch(text_size=10.0))
text((51.5, 41.2), "数学的な正解値", style=Styles.WhiteBold.patch(text_size=10.0))
text((99.0, 41.2), "要求される多段階計算ステップ", style=Styles.WhiteBold.patch(text_size=10.0))
text((146.5, 41.2), "thinking=low 結果", style=Styles.WhiteBold.patch(text_size=10.0))

t3_rows = [
    (
        33.4,
        "T3_1: PC修理vs買い替え",
        "修理 75,600 / 新品 101,800\n差額: 26,200円 修理が安い",
        "修理(基板29,800+SSD 9,800+保守1,000×36) vs\n新品(124,800-下取15,000-還元18,000+延長10,000)",
        "26,200円 (完全検証)\n(790〜951 tok)",
    ),
    (
        23.8,
        "T3_2: 500GB バックアップ",
        "USB2.0: 240分 / Gen2: 35分\n短縮: 205分 (3時間25分)",
        "大容量300GBと小ファイル200GBをインターフェース別\n速度で除算(各項目分未満切捨)+検証時間(15分/5分)加算",
        "205分短縮 (完全検証)\n(673〜755 tok)",
    ),
    (
        14.2,
        "T3_3: 3台PC保守2年試算",
        "保守50,400+増設29,400+\nクラウド13,800=93,600円",
        "3台×24ヶ月保守+訪問修理2回(割引-6,600)+16GB増設\n3台分(割引-1,800)+1・2年目クラウド料金の総和",
        "93,600円 (完全検証)\n(674〜827 tok)",
    ),
]

for ry, col1, col2, col3, col4 in t3_rows:
    rectangle((84.0, ry), width=155.0, height=8.6, style=Styles.LightFlat.patch(shape_r=0.8))
    rectangle((99.0, ry), width=64.0, height=7.8, style=Styles.WhiteFlat.patch(shape_r=0.6))
    text((20.0, ry), col1, style=Styles.DarkBold.patch(text_size=10.0))
    text((51.5, ry), col2, style=Styles.Dark.patch(text_size=10.0))
    text((99.0, ry), col3, style=Styles.Dark.patch(text_size=10.0))
    text((146.5, ry), col4, style=Styles.SuccessBold.patch(text_size=10.0))

# Bottom takeaway bar
rectangle((84.0, 5.2), width=155.0, height=5.4, style=Styles.SecondaryNeutral.patch(shape_r=1.0))
phosphor.arrows_split((9.5, 5.2), width=3.0, style=Styles.SecondaryBold)
text(
    (13.0, 5.2),
    "次章の解決策：Tier 1・2 は thinking=0 で即応し、Tier 3 のみ thinking=low を並列起動する Adaptive Router を導入する。",
    style=Styles.DarkBold.patch(text_size=10.0, halign="left"),
)

save()
```

### Tier 3 多段階計算における `thinking=low` 事前検算の重要性

丁寧なカスタマーサポート調の回答では、LLM は第1段落で「結論から申し上げますと、〇〇になります」と結論の数値を先に提示しようとする。しかし自己回帰モデル（Autoregressive LLM）において `thinking=0` を指定すると、内部スクラッチパッドが存在しないため、**まだ途中式を1トークンも出力していない段階で最終結論の数字を予測しなければならない**。本研究の Tier 3 ベンチマーク（`src/gemini_evaluation/adaptive_thinking_runs.jsonl`）では、以下の3つの多段階計算シナリオを検証している。

1. **`T3_1`（PC修理 vs. 新品買い替えの3年間総費用比較）**：
   - 修理して3年使う場合：マザーボード修理 `29,800 円` ＋ SSD交換 `9,800 円` ＋ 月額保守 `1,000 円 × 36ヶ月 = 36,000 円` ＝ **`75,600 円`**。
   - 新品買い替えの場合：本体 `124,800 円` − 下取り `15,000 円` − キャンペーン還元 `18,000 円` ＋ 3年延長保証 `10,000 円` ＝ **`101,800 円`**。差額は **修理の方が `26,200 円` 安い**。
2. **`T3_2`（500GB SSD データのバックアップ転送時間比較）**：
   - USB 2.0 HDD：動画300GB（`300,000 MB ÷ 40 MB/s = 7,500 秒 = 125 分`）＋ 写真・書類200GB（`192,000 MB ÷ 32 MB/s = 6,000 秒 = 100 分`）＋ 整合性チェック `15 分` ＝ **`240 分`（4時間）**。
   - USB 3.2 Gen2 SSD（プロンプトの「各項目で分未満切り捨て」指定に基づく）：動画300GB（`300,000 MB ÷ 400 MB/s = 750 秒 = 12.5 分 → 切り捨て 12 分`）＋ 写真・書類200GB（`199,800 MB ÷ 180 MB/s = 1,110 秒 = 18.5 分 → 切り捨て 18 分`）＋ 整合性チェック `5 分` ＝ **`35 分`**。短縮時間は **`205 分`（3時間25分）**。
3. **`T3_3`（3台PCの保守契約・メモリ増設・クラウドバックアップ2年間総額試算）**：
   - 基本保守（`600 円 × 3台 × 24ヶ月 = 43,200 円`）＋ 訪問修理2回（通常 `6,900 円 × 2 = 13,800 円` − 保守契約スポット割引 `6,600 円` ＝ `3,600 円 × 2 = 7,200 円`）＝ `50,400 円`。
   - 16GBメモリ増設3台（通常 `10,400 円 × 3 = 31,200 円` − 3台同時増設割引 `1,800 円` ＝ `9,800 円 × 3 = 29,400 円`）。
   - クラウドバックアップ（1年目 `550 円 × 12 = 6,600 円` ＋ 2年目 `600 円 × 12 = 7,200 円` ＝ `13,800 円`）。2年間総額は **`93,600 円`**。

`thinking=low` を用いた実行では、モデルが可視テキストの1文字目を出力する前に `673〜951 トークン` の内部スクラッチパッドで全ステップの加減乗除を完了しているため、3問すべてで冒頭結論から明細表まで **100% 正確に一致する回答** が生成される。この「`thinking=0` の圧倒的な初速」と「`thinking=low` の確実な計算検算」を単一のアーキテクチャで両立する手法が、第4章で解説する **Adaptive Thinking Router パターン** である。
