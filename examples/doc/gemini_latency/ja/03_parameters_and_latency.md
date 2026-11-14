# 3. パラメータとレイテンシー

第2章では、`gemini-3.8-flash` に対するブロッキング呼び出し（`generate_content`）とストリーミング呼び出し（`generate_content_stream`）の基本構造、および Gemini 3.5 / 3.8 / 4 シリーズのモデル仕様を確認した。本章では、`src/gemini_evaluation/benchmark_thinking.py`、`src/gemini_evaluation/benchmark_adaptive_thinking.py`、および `src/gemini_evaluation/benchmark_cross_model_thinking.py` による実機計測データに基づき、レイテンシーを支配する最大要因である **`ThinkingConfig`（内部推論トークン制御）** の全6段階の挙動（3.1〜3.2節）、推論トークン数と初回トークン到着時間（TTFT）の線形スケーリング則（3.3節）、質問難易度（Tier 1〜3）に応じた「応答速度と計算正確性のトレードオフ」（3.4節）、そして **現行5モデル（`3.5-flash-lite` / `3.8-flash` / `4-hydrogen` / `4-argon` / `4-carbon`）× 各 `thinking_level` に同一の簡単クエリ5種・複雑クエリ5種を投入した170試行の横断レイテンシー比較（3.5節）** を定量的に解明する。

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

Google AI Studio（`google-genai` SDK）から `gemini-3.8-flash` を呼び出す際、モデルが最初の可視テキストチャンクを出力する前に内部で実行する推論プロセス（Thinking）は `types.ThinkingConfig` によって制御される。第2章 2.5節で検証したとおり、`gemini-3.8-flash` では `ThinkingLevel.MINIMAL` が非対応（`400` エラー）かつ `ThinkingLevel.LOW` が極小思考（定型質問では `0 tok`）となるため、評価実装（`src/gemini_evaluation/llm_call.py` の `resolve_thinking_config()`）では後方互換の `thinking_budget` と `ThinkingLevel` を組み合わせた以下の **全6段階のオプション** を定義し、推論トークン数に応じた段階的なレイテンシ推移を計測している（純粋な `thinking_level` のみを用いた5モデル横断比較は **3.5節** を参照）。

```python
from google import genai
from google.genai import types

client = genai.Client(api_key=GEMINI_KEY)

# 例1: 内部推論を完全に無効化し、最短 TTFT を得る設定
config_zero = types.GenerateContentConfig(
    thinking_config=types.ThinkingConfig(thinking_budget=0),
)

# 例2: 複雑な多段階計算向けに中程度の内部推論を有効化する設定
config_low = types.GenerateContentConfig(
    thinking_config=types.ThinkingConfig(thinking_budget=4096),
)
```

| オプション指定値 (`thinking=`) | 正規化ラベル | SDK 設定 (`types.ThinkingConfig`) | 実測推論トークン数 (`ThTok`) | 動作特性と推奨ユースケース |
| :--- | :--- | :--- | :--- | :--- |
| **`0`** （または `"0"`） | `"0"` | `ThinkingConfig(thinking_budget=0)` | **`0 tok`** | 推論トークン上限を **0 tok** に固定。内部思考を完全にスキップし、最速の TTFT（約 `1,205〜1,546 ms`）を実現する。挨拶・定型案内・分類ルーターに最適。 |
| **`1`** （または `"minimal"`） | `"minimal"` | `ThinkingConfig(thinking_budget=256)` | **`0 tok`** | 極小バジェット指定。定型プロンプトでは実質 `0 tok` となり、推論トークンを消費しない高速応答を示す。 |
| **`2`** （または `"low"`） | `"low"` | `ThinkingConfig(thinking_budget=4096)` | **`351〜557 tok`** | 軽量〜中程度の内部推論を実行。TTFT は約 `4.3〜5.5 秒` となるが、多段階の算数・見積もり比較の計算ミスを防ぐのに十分な推論量を確保する。 |
| **`3`** （または `"medium"`） | `"medium"` | `ThinkingConfig(thinking_level=MEDIUM)` | **`441〜592 tok`** | 中程度の内部推論を実行。TTFT は約 `6.2〜6.7 秒` を要する。 |
| **`4`** （または `"high"`） | `"high"` | `ThinkingConfig(thinking_level=HIGH)` | **`817〜870 tok`** | 深い内部推論を実行。複雑な論理パズルや高度な推論に向くが、定型対話では `9.0〜9.7 秒` の待機が発生する。 |
| **`None`** （または `"default"`） | `"default"` | 指定なし（動的デフォルト＝`MEDIUM`） | **`467〜1,006 tok`** | `thinking_config` 省略時のデフォルト挙動。プロンプトに応じて動的に推論トークンが割り当てられ、定型質問でも `7.5〜10.4 秒` の待機が生じる。 |

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

---

## 3.5 現行5モデル × `thinking_level`（＋非推奨 `thinking_budget=0`）横断レイテンシー比較（簡単5問・複雑5問＝全220試行）

前節までは `gemini-3.8-flash` 単体における `ThinkingConfig` の挙動を分析したが、実運用でモデルを選定する際には、第2章 2.5節で整理した **現行5モデル（`gemini-3.5-flash-lite` / `gemini-3.8-flash` / `gemini-4-hydrogen` / `gemini-4-argon` / `gemini-4-carbon`）** のそれぞれにおいて、`thinking_level`（および後方互換用の非推奨オプション `thinking_budget=0`）を変えたときに **簡単な質問（Simple）** と **複雑な多段階計算（Complex）** でレイテンシー（TTFT・Total）および内部推論トークン数（`ThTok`）がどう変化するかを横断把握する必要がある。

そこで `src/gemini_evaluation/benchmark_cross_model_thinking.py` を作成し、**簡単なクエリ 5種類（`S1`〜`S5`）** と **複雑なクエリ 5種類（`C1`〜`C5`）** の計10問を、5モデル × 各モデルがサポートする全 `thinking_level`（17構成）＋ 非推奨の `thinking_budget=0`（5構成）の **計22構成** に対して同一条件の Streaming（`generate_content_stream`）で一斉送信する **合計 220 試行の実機ベンチマーク**（`src/gemini_evaluation/cross_model_thinking_log.yaml` / `.json`）を実施した。

```drawlib align=center code=fold width=100% file=ch03_cross_model_thinking_comparison_ja.png caption="図3-5: 現行5モデル × 全 thinking_level ＋ 非推奨 thinking_budget=0（全22構成）における簡単クエリ5問平均 vs. 複雑クエリ5問平均の Streaming TTFT・Total・推論トークン数比較（全220試行）"
from drawlib.canvas import save, setup
from drawlib.icons import phosphor
from drawlib.lines import line
from drawlib.shapes import rectangle
from drawlib.styles import Styles
from drawlib.text import text
from drawlib.utils import load_cross_model_thinking_benchmark

setup(width=172, height=158, dpi=150)

# Outer structural frame
rectangle((86.0, 79.0), width=168.0, height=154.0, style=Styles.MutedDashed.patch(shape_r=2.0))
text(
    (86.0, 151.6),
    "現行5モデル × 全 thinking_level ＋ 非推奨 budget=0（全22構成）：簡単5問 vs 複雑5問 実測比較",
    style=Styles.DarkBold.patch(text_size=11.5),
)

# Top Legend Bar
rectangle((86.0, 145.2), width=160.0, height=5.2, style=Styles.Neutral.patch(shape_r=1.0))
rectangle((9.5, 145.2), width=4.0, height=2.2, style=Styles.PrimaryFlat.patch(shape_r=0.3))
text((12.5, 145.2), "Streaming TTFT (初期応答)", style=Styles.PrimaryBold.patch(text_size=9.8, halign="left"))

rectangle((52.5, 145.2), width=4.0, height=2.2, style=Styles.PrimaryNeutral.patch(shape_r=0.3))
text((55.5, 145.2), "Streaming Total (全文完了)", style=Styles.DarkBold.patch(text_size=9.8, halign="left"))

rectangle((96.5, 145.2), width=4.0, height=2.2, style=Styles.SecondaryFlat.patch(shape_r=0.3))
text((99.5, 145.2), "[budget=0*] 非推奨 thinking_budget=0 (後方互換/非対応)", style=Styles.DarkBold.patch(text_size=9.8, halign="left"))

# Column Headers
rectangle((24.0, 138.8), width=36.0, height=4.4, style=Styles.PrimaryNeutral.patch(shape_r=0.8))
text((24.0, 138.8), "モデル / 設定 (22構成)", style=Styles.DarkBold.patch(text_size=10.0))

rectangle((68.5, 138.8), width=49.0, height=4.4, style=Styles.PrimaryNeutral.patch(shape_r=0.8))
text((68.5, 138.8), "① 簡単クエリ 5問平均 (S1-S5) [0〜30s]", style=Styles.DarkBold.patch(text_size=10.0))

rectangle((121.5, 138.8), width=53.0, height=4.4, style=Styles.PrimaryNeutral.patch(shape_r=0.8))
text((121.5, 138.8), "② 複雑クエリ 5問平均 (C1-C5) [0〜42s]", style=Styles.DarkBold.patch(text_size=10.0))

rectangle((157.5, 138.8), width=16.0, height=4.4, style=Styles.SecondaryNeutral.patch(shape_r=0.8))
text((157.5, 138.8), "複雑 ThTok", style=Styles.DarkBold.patch(text_size=10.0))

data = load_cross_model_thinking_benchmark()
agg = data["aggregated"]

SX0 = 45.0
SW = 32.0
S_MAX = 30000.0

CX0 = 96.0
CW = 36.0
C_MAX = 42000.0

for ms in (0, 10000, 20000, 30000):
    gx = SX0 + (ms / S_MAX) * SW
    line((gx, 13.5), (gx, 136.2), style=Styles.LightDashed.patch(line_width=0.6))
    text((gx, 11.2), f"{ms // 1000}s", style=Styles.Dark.patch(text_size=9.5))

for ms in (0, 10000, 20000, 30000, 40000):
    gx = CX0 + (ms / C_MAX) * CW
    line((gx, 13.5), (gx, 136.2), style=Styles.LightDashed.patch(line_width=0.6))
    text((gx, 11.2), f"{ms // 1000}s", style=Styles.Dark.patch(text_size=9.5))

short_names = {
    "gemini-3.5-flash-lite": "3.5-flash-lite",
    "gemini-3.8-flash": "3.8-flash",
    "gemini-4-hydrogen": "4-hydrogen",
    "gemini-4-argon": "4-argon",
    "gemini-4-carbon": "4-carbon",
}

for idx, row in enumerate(agg):
    ry = 133.5 - idx * 5.6
    m_short = short_names.get(row["model"], row["model"])
    lvl = row["thinking_level"]
    status = row.get("status", "OK")
    is_budget0 = lvl == "budget=0"
    is_lite_or_fast = row["model"] in {"gemini-3.5-flash-lite", "gemini-4-hydrogen"} and lvl in {"minimal", "low"}

    if status == "UNSUPPORTED_400":
        bg_st = Styles.DangerFlat.patch(shape_r=0.6, alpha=0.14)
    elif is_budget0:
        bg_st = Styles.SecondaryNeutral.patch(shape_r=0.6, alpha=0.38)
    elif is_lite_or_fast:
        bg_st = Styles.PrimaryNeutral.patch(shape_r=0.6, alpha=0.32)
    else:
        bg_st = Styles.LightFlat.patch(shape_r=0.6, alpha=0.45) if idx % 2 == 0 else Styles.WhiteFlat.patch(shape_r=0.6)

    rectangle((86.0, ry), width=160.0, height=5.0, style=bg_st)

    lbl_text = f"{m_short} [budget=0*]" if is_budget0 else f"{m_short} [{lvl}]"
    lbl_style = Styles.DangerBold.patch(text_size=9.5, halign="left") if status == "UNSUPPORTED_400" else Styles.DarkBold.patch(text_size=9.5, halign="left")
    text((7.2, ry), lbl_text, style=lbl_style)

    if status == "UNSUPPORTED_400":
        rectangle((96.0, ry), width=102.0, height=3.6, style=Styles.WhiteFlat.patch(shape_r=0.5, line_width=0.6))
        phosphor.x_circle((55.0, ry), width=2.8, style=Styles.DangerBold)
        text(
            (57.4, ry),
            "400 INVALID_ARGUMENT (thinking_budget=0 非対応 → minimal を指定)",
            style=Styles.DangerBold.patch(text_size=9.5, halign="left"),
        )
        rectangle((157.5, ry), width=15.0, height=3.8, style=Styles.WhiteFlat.patch(shape_r=0.5))
        text((157.5, ry), "非対応", style=Styles.DangerBold.patch(text_size=9.5))
        continue

    bar_tot_st = Styles.SecondaryNeutral.patch(shape_r=0.3) if is_budget0 else Styles.PrimaryNeutral.patch(shape_r=0.3)
    bar_ttft_st = Styles.SecondaryFlat.patch(shape_r=0.3) if is_budget0 else Styles.PrimaryFlat.patch(shape_r=0.3)

    # Simple bar
    s_ttft = float(row["simple_ttft_avg_ms"])
    s_tot = float(row["simple_total_avg_ms"])
    sw_tot = min(s_tot / S_MAX, 1.0) * SW
    sw_ttft = min(s_ttft / S_MAX, 1.0) * SW
    rectangle((SX0 + sw_tot / 2, ry), width=max(sw_tot, 0.4), height=2.4, style=bar_tot_st)
    rectangle((SX0 + sw_ttft / 2, ry), width=max(sw_ttft, 0.4), height=2.4, style=bar_ttft_st)
    text(
        (SX0 + sw_tot + 0.8, ry),
        f"{s_ttft / 1000:.1f}s / {s_tot / 1000:.1f}s",
        style=Styles.Dark.patch(text_size=9.5, halign="left"),
    )

    # Complex bar
    c_ttft = float(row["complex_ttft_avg_ms"])
    c_tot = float(row["complex_total_avg_ms"])
    c_th = float(row["complex_thoughts_avg"])
    cw_tot = min(c_tot / C_MAX, 1.0) * CW
    cw_ttft = min(c_ttft / C_MAX, 1.0) * CW
    rectangle((CX0 + cw_tot / 2, ry), width=max(cw_tot, 0.4), height=2.4, style=bar_tot_st)
    rectangle((CX0 + cw_ttft / 2, ry), width=max(cw_ttft, 0.4), height=2.4, style=bar_ttft_st)
    text(
        (CX0 + cw_tot + 0.8, ry),
        f"{c_ttft / 1000:.1f}s / {c_tot / 1000:.1f}s",
        style=Styles.DarkBold.patch(text_size=9.5, halign="left"),
    )

    # Complex thoughts token pill
    rectangle((157.5, ry), width=15.0, height=3.8, style=Styles.WhiteFlat.patch(shape_r=0.5))
    text((157.5, ry), f"{c_th:,.0f} tok", style=Styles.PrimaryBold.patch(text_size=9.5))

# Bottom callout banner
rectangle((86.0, 5.2), width=160.0, height=5.4, style=Styles.PrimaryNeutral.patch(shape_r=1.0))
phosphor.gauge((9.8, 5.2), width=3.0, style=Styles.PrimaryBold)
text(
    (13.2, 5.2),
    "結論：budget=0* は 3.5-flash-lite で 400 エラーとなり、他4モデルでも内部的に low 相当へ丸められるため thinking_level 指定が必須。",
    style=Styles.DarkBold.patch(text_size=9.8, halign="left"),
)

save()
```

---

### 1. 検証クエリ10種（簡単5種 `S1`〜`S5` ＋ 複雑5種 `C1`〜`C5`）の定義（表3-5A）

すべてのモデルと `thinking_level`（および非推奨 `thinking_budget=0`）の組み合わせに対して、以下の同一10クエリ（PCテクニカルサポート窓口の対話シナリオ）を送信した。

| クエリID | 区分 | タイトル | プロンプト概要と要求される処理特性 |
| :---: | :---: | :--- | :--- |
| **`S1`** | **簡単 (Simple)** | 初回挨拶（PC起動トラブル） | 「パソコンが急に動かなくなったので相談させてください」に対する初期受付・ヒアリング応答。 |
| **`S2`** | **簡単 (Simple)** | お礼・復旧報告への応答 | 「放電手順で無事に電源ランプがつきました。ありがとうございます！」に対するクロージング挨拶。 |
| **`S3`** | **簡単 (Simple)** | サポート窓口受付時間の確認 | 電話窓口およびチャット窓口の一般的な受付時間・営業曜日の定型案内。 |
| **`S4`** | **簡単 (Simple)** | フリーズ時の強制終了秒数 | Windows 完全フリーズ時に電源ボタンを何秒長押しすべきか（約4〜10秒）の短文事実回答。 |
| **`S5`** | **簡単 (Simple)** | 型番・シリアル番号の記載場所 | ノートPC本体の型番・シリアル番号シール貼付箇所（底面・バッテリー裏・BIOS等）の定型案内。 |
| **`C1`** | **複雑 (Complex)** | 修理vs買い替え3年間総費用比較 | 修理プラン（基板38,000＋SSD 22,000＋電気代2,400×36＋2年目電池16,000＝`162,400円`）vs 買い替えプラン（本体168,000−下取25,000−10%還元14,300＋電気代1,550×36＝`184,500円`、修理が `22,100円` お得）の多段階試算。 |
| **`C2`** | **複雑 (Complex)** | 1.8TB退避＋クラウド転送時間試算 | 動画1,200GB（300MB/s＝`4,000秒`）＋設計小ファイル600GB（50MB/s＝`12,000秒`）のローカル退避（計`266分40秒`）＋重要360GBクラウド転送（40MB/s＝`9,000秒`＝`150分`、総合計 `6時間56分40秒`）のステップ計算。 |
| **`C3`** | **複雑 (Complex)** | 代替機レンタルvs当日出張修理比較 | 引取修理8日間（修理32,000＋停止損失18,000×2日＋レンタル3,500×6日＋設定4,000＝`93,000円`）vs 当日出張修理（基本32,000＋出張22,000＋特急12,000＋半日損失9,000＝`75,000円`、出張が `18,000円` 有利）の損益比較。 |
| **`C4`** | **複雑 (Complex)** | 3台PC保守・増設・クラウド2年試算 | 3台×24ヶ月基本保守（`43,200円`）＋訪問修理2回割引後（`7,200円`）＋16GB増設3台割引後（`29,400円`）＋1・2年目クラウド（`13,800円`）＝総額 **`93,600円`** の4項目合算。 |
| **`C5`** | **複雑 (Complex)** | RAID5 NAS 12TB再構築時間試算 | 4TB×4台 RAID5（実効12TB×使用率75%＝保存データ量 **`9.0TB`**）のリビルド12TB（`12,000,000MB`）：最初の5時間（100MB/s＝`1,800,000MB` 処理）＋残り `10,200,000MB`（夜間250MB/s＝`40,800秒`＝`11時間20分`）＝合計 **`16時間20分`** の時間帯別速度計算。 |

---

### 2. 全5モデル × 全 `thinking_level` ＋ 非推奨 `thinking_budget=0`（全22構成）の集計比較テーブル（表3-5B）

表3-5Bに、全22構成における **簡単クエリ5問（`S1`〜`S5`）の平均値**、**複雑クエリ5問（`C1`〜`C5`）の平均値**、および **全10問の総合平均値** を示す。

| モデル名 (`model`) | 設定 (`thinking_level` / `budget=0`) | 簡単5問 (`S1`–`S5`) 平均 TTFT | 簡単5問 (`S1`–`S5`) 平均 Total | 簡単5問 平均 `ThTok` / `OutTok` | 複雑5問 (`C1`–`C5`) 平均 TTFT | 複雑5問 (`C1`–`C5`) 平均 Total | 複雑5問 平均 `ThTok` / `OutTok` | 全10問 総合平均 TTFT / Total |
| :--- | :---: | ---: | ---: | :---: | ---: | ---: | :---: | ---: |
| **`gemini-3.5-flash-lite`** | **`budget=0`** *(非推奨・非対応)* | ❌ `400 Error` | ❌ `400 Error` | 非対応 (`minimal` を使用) | ❌ `400 Error` | ❌ `400 Error` | 非対応 (`minimal` を使用) | **❌ `400 INVALID_ARGUMENT`** |
| **`gemini-3.5-flash-lite`** | **`minimal`** *(既定)* | **`733.9 ms`** | **`1,378.9 ms`** | `0.0` / `188.6` | **`677.6 ms`** | **`2,063.2 ms`** | `0.0` / `588.8` | **`705.8 ms` / `1,721.0 ms`** |
| **`gemini-3.5-flash-lite`** | **`low`** | **`671.6 ms`** | **`1,373.5 ms`** | `0.0` / `203.4` | **`1,467.2 ms`** | **`2,815.4 ms`** | `336.4` / `558.2` | **`1,069.4 ms` / `2,094.5 ms`** |
| **`gemini-3.5-flash-lite`** | **`medium`** | `1,399.9 ms` | `1,933.5 ms` | `232.2` / `174.0` | `2,719.0 ms` | `4,078.8 ms` | `884.4` / `581.0` | `2,059.5 ms` / `3,006.2 ms` |
| **`gemini-3.5-flash-lite`** | **`high`** | `2,158.7 ms` | `2,568.6 ms` | `459.4` / `169.6` | `3,493.9 ms` | `4,837.8 ms` | `1,313.0` / `591.8` | `2,826.3 ms` / `3,703.2 ms` |
| **`gemini-3.8-flash`** | **`budget=0`** *(非推奨・互換)* | `3,041.6 ms` | `5,457.5 ms` | `100.0` / `213.0` | `2,564.7 ms` | `7,653.2 ms` | `91.8` / `627.8` | `2,803.2 ms` / `6,555.4 ms` |
| **`gemini-3.8-flash`** | **`low`** | `2,458.7 ms` | `5,041.8 ms` | `62.0` / `238.0` | `2,586.6 ms` | `7,965.4 ms` | `104.6` / `653.4` | `2,522.7 ms` / `6,503.6 ms` |
| **`gemini-3.8-flash`** | **`medium`** *(既定)* | `3,950.6 ms` | `6,655.5 ms` | `206.8` / `252.0` | `6,155.5 ms` | `10,707.2 ms` | `605.0` / `567.2` | `5,053.1 ms` / `8,681.4 ms` |
| **`gemini-3.8-flash`** | **`high`** | `10,186.7 ms` | `12,502.7 ms` | `799.6` / `243.4` | `13,429.9 ms` | `18,948.5 ms` | `1,549.0` / `693.4` | `11,808.3 ms` / `15,725.6 ms` |
| **`gemini-4-hydrogen`** | **`budget=0`** *(非推奨・low丸め)* | `3,018.6 ms` | `3,870.3 ms` | `147.4` / `146.0` | `5,341.2 ms` | `7,474.6 ms` | `670.4` / `508.6` | `4,179.9 ms` / `5,672.5 ms` |
| **`gemini-4-hydrogen`** | **`low`** | `2,598.0 ms` | **`3,367.6 ms`** | `183.8` / `146.0` | `3,908.6 ms` | **`5,899.8 ms`** | `657.6` / `521.6` | **`3,253.3 ms` / `4,633.7 ms`** |
| **`gemini-4-hydrogen`** | **`medium`** | `3,762.3 ms` | `5,150.8 ms` | `231.6` / `218.4` | `6,506.2 ms` | `9,004.7 ms` | `954.2` / `593.2` | `5,134.2 ms` / `7,077.7 ms` |
| **`gemini-4-hydrogen`** | **`high`** *(既定)* | `4,060.9 ms` | `5,244.0 ms` | `273.0` / `205.6` | `9,339.2 ms` | `11,804.2 ms` | `1,156.0` / `593.8` | `6,700.1 ms` / `8,524.1 ms` |
| **`gemini-4-hydrogen`** | **`xhigh`** *(専用)* | `7,650.8 ms` | `8,738.9 ms` | `761.6` / `221.2` | `13,015.8 ms` | `15,431.1 ms` | **`2,248.0`** / `632.8` | `10,333.3 ms` / `12,085.0 ms` |
| **`gemini-4-argon`** | **`budget=0`** *(非推奨・互換)* | `9,817.2 ms` | `13,952.0 ms` | `0.0` / `222.2` | `13,300.9 ms` | `21,158.1 ms` | `0.0` / `715.8` | `11,559.1 ms` / `17,555.0 ms` |
| **`gemini-4-argon`** | **`low`** | `4,382.4 ms` | `8,649.0 ms` | `0.0` / `250.4` | `10,940.2 ms` | `19,397.1 ms` | `0.0` / `698.4` | `7,661.3 ms` / `14,023.0 ms` |
| **`gemini-4-argon`** | **`medium`** *(既定)* | `6,137.7 ms` | `10,080.2 ms` | `0.0` / `231.8` | **`4,931.3 ms`** | **`13,279.8 ms`** | `0.0` / `699.6` | **`5,534.5 ms` / `11,680.0 ms`** |
| **`gemini-4-argon`** | **`high`** | `22,181.4 ms` | `25,528.0 ms` | `774.6` / `235.6` | `27,175.9 ms` | `34,240.4 ms` | `1,100.0` / `601.0` | `24,678.6 ms` / `29,884.2 ms` |
| **`gemini-4-carbon`** | **`budget=0`** *(非推奨・互換)* | `4,854.2 ms` | `7,891.5 ms` | `0.0` / `222.2` | `4,434.0 ms` | `12,103.0 ms` | `0.0` / `684.8` | `4,644.1 ms` / `9,997.2 ms` |
| **`gemini-4-carbon`** | **`low`** | `7,677.8 ms` | `11,455.9 ms` | `0.0` / `223.4` | `5,400.9 ms` | `12,485.9 ms` | `0.0` / `641.6` | `6,539.4 ms` / `11,970.9 ms` |
| **`gemini-4-carbon`** | **`medium`** *(既定)* | `6,309.1 ms` | `9,129.1 ms` | `97.6` / `217.2` | `13,448.1 ms` | `19,218.0 ms` | `713.2` / `565.6` | `9,878.6 ms` / `14,173.5 ms` |
| **`gemini-4-carbon`** | **`high`** | `14,648.2 ms` | `17,207.2 ms` | `722.4` / `227.0` | `34,355.5 ms` | `40,209.9 ms` | **`2,794.6`** / `608.4` | `24,501.9 ms` / `28,708.5 ms` |

---

### 3. クエリ別（全10問個別）× 22構成の完全計測マトリクス（表3-5C・表3-5D）

各セルの表記は **`TTFT (ms)` / `Total (ms)` (`ThTok`)** である。

#### 表3-5C：簡単クエリ 5種類（`S1`〜`S5`）のモデル × 設定（22構成）別計測結果

| モデル名 | 設定 (`level`) | `S1` 初回挨拶 | `S2` お礼・復旧報告 | `S3` 窓口受付時間 | `S4` 強制終了秒数 | `S5` 型番記載場所 | 簡単5問 平均 |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| **`gemini-3.5-flash-lite`** | **`budget=0`** | ❌ `400 Error` | ❌ `400 Error` | ❌ `400 Error` | ❌ `400 Error` | ❌ `400 Error` | ❌ **`400 INVALID_ARGUMENT`** |
| **`gemini-3.5-flash-lite`** | **`minimal`** | `754` / `1,415` (`0`) | `795` / `1,025` (`0`) | `736` / `1,509` (`0`) | `562` / `795` (`0`) | `822` / `2,150` (`0`) | **`733.9`** / `1,378.9` (`0.0`) |
| **`gemini-3.5-flash-lite`** | **`low`** | `781` / `1,460` (`0`) | `586` / `858` (`0`) | `625` / `1,667` (`0`) | `662` / `905` (`0`) | `704` / `1,978` (`0`) | **`671.6`** / `1,373.5` (`0.0`) |
| **`gemini-3.5-flash-lite`** | **`medium`** | `1,124` / `1,712` (`164`) | `1,086` / `1,263` (`115`) | `1,365` / `2,118` (`158`) | `1,012` / `1,223` (`129`) | `2,413` / `3,350` (`595`) | **`1,399.9`** / `1,933.5` (`232.2`) |
| **`gemini-3.5-flash-lite`** | **`high`** | `2,209` / `2,567` (`487`) | `1,679` / `1,848` (`246`) | `2,362` / `2,970` (`563`) | `1,783` / `1,938` (`372`) | `2,761` / `3,520` (`629`) | **`2,158.7`** / `2,568.6` (`459.4`) |
| **`gemini-3.8-flash`** | **`budget=0`** | `2,882` / `5,792` (`112`) | `3,737` / `5,281` (`102`) | `3,616` / `7,137` (`206`) | `2,642` / `3,165` (`80`) | `2,332` / `5,912` (`0`) | **`3,041.6`** / `5,457.5` (`100.0`) |
| **`gemini-3.8-flash`** | **`low`** | `1,378` / `3,636` (`0`) | `2,306` / `3,511` (`56`) | `3,924` / `7,590` (`254`) | `2,546` / `3,621` (`0`) | `2,139` / `6,850` (`0`) | **`2,458.7`** / `5,041.8` (`62.0`) |
| **`gemini-3.8-flash`** | **`medium`** | `3,667` / `6,632` (`170`) | `2,386` / `3,960` (`118`) | `4,880` / `8,267` (`310`) | `3,343` / `4,208` (`149`) | `5,477` / `10,211` (`287`) | **`3,950.6`** / `6,655.5` (`206.8`) |
| **`gemini-3.8-flash`** | **`high`** | `13,519` / `15,568` (`976`) | `8,599` / `9,911` (`734`) | `11,038` / `15,084` (`929`) | `5,098` / `5,877` (`377`) | `12,679` / `16,074` (`982`) | **`10,186.7`** / `12,502.7` (`799.6`) |
| **`gemini-4-hydrogen`** | **`budget=0`** | `1,714` / `2,795` (`120`) | `3,936` / `4,164` (`48`) | `3,435` / `4,622` (`155`) | `3,959` / `4,181` (`282`) | `2,050` / `3,590` (`132`) | **`3,018.6`** / `3,870.3` (`147.4`) |
| **`gemini-4-hydrogen`** | **`low`** | `1,908` / `2,720` (`143`) | `3,160` / `3,427` (`89`) | `2,327` / `3,207` (`189`) | `2,454` / `2,847` (`267`) | `3,140` / `4,637` (`231`) | **`2,598.0`** / `3,367.6` (`183.8`) |
| **`gemini-4-hydrogen`** | **`medium`** | `1,529` / `2,836` (`106`) | `4,350` / `5,038` (`143`) | `3,972` / `6,185` (`342`) | `2,076` / `2,408` (`208`) | `6,884` / `9,288` (`359`) | **`3,762.3`** / `5,150.8` (`231.6`) |
| **`gemini-4-hydrogen`** | **`high`** | `2,712` / `3,703` (`277`) | `5,756` / `6,396` (`135`) | `6,846` / `8,598` (`443`) | `2,643` / `2,929` (`256`) | `2,348` / `4,594` (`254`) | **`4,060.9`** / `5,244.0` (`273.0`) |
| **`gemini-4-hydrogen`** | **`xhigh`** | `7,021` / `7,902` (`1040`) | `4,469` / `4,922` (`526`) | `12,846` / `14,667` (`634`) | `6,338` / `6,633` (`749`) | `7,580` / `9,570` (`859`) | **`7,650.8`** / `8,738.9` (`761.6`) |
| **`gemini-4-argon`** | **`budget=0`** | `11,746` / `15,473` (`0`) | `22,471` / `24,288` (`0`) | `3,326` / `8,664` (`0`) | `4,728` / `6,385` (`0`) | `6,816` / `14,949` (`0`) | **`9,817.2`** / `13,952.0` (`0.0`) |
| **`gemini-4-argon`** | **`low`** | `2,570` / `5,326` (`0`) | `4,708` / `7,330` (`0`) | `2,638` / `9,683` (`0`) | `3,238` / `5,355` (`0`) | `8,757` / `15,552` (`0`) | **`4,382.4`** / `8,649.0` (`0.0`) |
| **`gemini-4-argon`** | **`medium`** | `3,053` / `7,037` (`0`) | `4,854` / `6,561` (`0`) | `9,451` / `15,899` (`0`) | `4,508` / `6,306` (`0`) | `8,823` / `14,598` (`0`) | **`6,137.7`** / `10,080.2` (`0.0`) |
| **`gemini-4-argon`** | **`high`** | `29,978` / `33,264` (`749`) | `11,349` / `13,092` (`338`) | `24,771` / `29,346` (`1238`) | `15,763` / `16,872` (`606`) | `29,046` / `35,066` (`942`) | **`22,181.4`** / `25,528.0` (`774.6`) |
| **`gemini-4-carbon`** | **`budget=0`** | `4,935` / `8,407` (`0`) | `4,695` / `6,488` (`0`) | `4,994` / `9,115` (`0`) | `5,174` / `6,954` (`0`) | `4,472` / `8,493` (`0`) | **`4,854.2`** / `7,891.5` (`0.0`) |
| **`gemini-4-carbon`** | **`low`** | `3,280` / `6,153` (`0`) | `4,086` / `6,120` (`0`) | `7,773` / `13,560` (`0`) | `11,728` / `13,815` (`0`) | `11,523` / `17,632` (`0`) | **`7,677.8`** / `11,455.9` (`0.0`) |
| **`gemini-4-carbon`** | **`medium`** | `10,608` / `12,918` (`488`) | `5,083` / `6,500` (`0`) | `5,712` / `10,550` (`0`) | `4,937` / `6,727` (`0`) | `5,204` / `8,951` (`0`) | **`6,309.1`** / `9,129.1` (`97.6`) |
| **`gemini-4-carbon`** | **`high`** | `9,566` / `11,715` (`559`) | `13,462` / `14,539` (`574`) | `18,835` / `22,305` (`1070`) | `11,041` / `11,829` (`438`) | `20,337` / `25,648` (`971`) | **`14,648.2`** / `17,207.2` (`722.4`) |

#### 表3-5D：複雑クエリ 5種類（`C1`〜`C5`）のモデル × 設定（22構成）別計測結果

| モデル名 | 設定 (`level`) | `C1` 修理vs買替3年 | `C2` 1.8TB退避転送 | `C3` 代替機vs出張 | `C4` 3台PC保守2年 | `C5` RAID5再構築 | 複雑5問 平均 |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| **`gemini-3.5-flash-lite`** | **`budget=0`** | ❌ `400 Error` | ❌ `400 Error` | ❌ `400 Error` | ❌ `400 Error` | ❌ `400 Error` | ❌ **`400 INVALID_ARGUMENT`** |
| **`gemini-3.5-flash-lite`** | **`minimal`** | `689` / `2,049` (`0`) | `638` / `2,512` (`0`) | `688` / `1,778` (`0`) | `632` / `1,573` (`0`) | `740` / `2,404` (`0`) | **`677.6`** / `2,063.2` (`0.0`) |
| **`gemini-3.5-flash-lite`** | **`low`** | `2,092` / `3,592` (`662`) | `1,137` / `2,883` (`243`) | `474` / `1,614` (`0`) | `952` / `1,895` (`0`) | `2,681` / `4,093` (`777`) | **`1,467.2`** / `2,815.4` (`336.4`) |
| **`gemini-3.5-flash-lite`** | **`medium`** | `2,390` / `3,748` (`832`) | `2,712` / `4,527` (`944`) | `1,806` / `2,789` (`442`) | `2,733` / `3,688` (`890`) | `3,955` / `5,642` (`1314`) | **`2,719.0`** / `4,078.8` (`884.4`) |
| **`gemini-3.5-flash-lite`** | **`high`** | `4,447` / `5,638` (`1895`) | `3,983` / `5,804` (`1400`) | `2,228` / `3,371` (`807`) | `2,395` / `3,289` (`965`) | `4,417` / `6,086` (`1498`) | **`3,493.9`** / `4,837.8` (`1313.0`) |
| **`gemini-3.8-flash`** | **`budget=0`** | `1,709` / `8,464` (`0`) | `1,441` / `7,700` (`0`) | `1,898` / `5,712` (`0`) | `4,440` / `7,573` (`459`) | `3,336` / `8,816` (`0`) | **`2,564.7`** / `7,653.2` (`91.8`) |
| **`gemini-3.8-flash`** | **`low`** | `1,213` / `7,493` (`0`) | `1,570` / `8,689` (`0`) | `2,216` / `6,605` (`0`) | `5,363` / `8,859` (`523`) | `2,571` / `8,180` (`0`) | **`2,586.6`** / `7,965.4` (`104.6`) |
| **`gemini-3.8-flash`** | **`medium`** | `5,935` / `11,219` (`535`) | `7,605` / `13,135` (`776`) | `5,253` / `9,135` (`405`) | `5,300` / `8,258` (`551`) | `6,684` / `11,789` (`758`) | **`6,155.5`** / `10,707.2` (`605.0`) |
| **`gemini-3.8-flash`** | **`high`** | `17,232` / `23,500` (`1862`) | `13,341` / `20,345` (`1569`) | `11,916` / `16,018` (`1332`) | `11,399` / `14,809` (`1493`) | `13,261` / `20,070` (`1489`) | **`13,429.9`** / `18,948.5` (`1549.0`) |
| **`gemini-4-hydrogen`** | **`budget=0`** | `4,468` / `6,579` (`913`) | `7,307` / `10,135` (`790`) | `2,150` / `3,824` (`359`) | `6,981` / `8,233` (`485`) | `5,801` / `8,602` (`805`) | **`5,341.2`** / `7,474.6` (`670.4`) |
| **`gemini-4-hydrogen`** | **`low`** | `5,287` / `7,609` (`635`) | `4,134` / `6,415` (`915`) | `3,136` / `4,552` (`495`) | `3,461` / `4,592` (`688`) | `3,525` / `6,331` (`555`) | **`3,908.6`** / `5,899.8` (`657.6`) |
| **`gemini-4-hydrogen`** | **`medium`** | `6,684` / `9,248` (`1225`) | `8,374` / `11,368` (`1047`) | `3,701` / `5,209` (`649`) | `3,830` / `5,430` (`662`) | `9,942` / `13,768` (`1188`) | **`6,506.2`** / `9,004.7` (`954.2`) |
| **`gemini-4-hydrogen`** | **`high`** | `5,650` / `7,695` (`1222`) | `10,447` / `14,546` (`1954`) | `4,068` / `6,012` (`669`) | `20,291` / `21,863` (`697`) | `6,240` / `8,904` (`1238`) | **`9,339.2`** / `11,804.2` (`1156.0`) |
| **`gemini-4-hydrogen`** | **`xhigh`** | `10,703` / `13,386` (`2327`) | `13,629` / `16,628` (`2472`) | `14,595` / `16,648` (`1770`) | `14,652` / `16,410` (`1698`) | `11,500` / `14,082` (`2973`) | **`13,015.8`** / `15,431.1` (`2248.0`) |
| **`gemini-4-argon`** | **`budget=0`** | `5,216` / `12,360` (`0`) | `4,684` / `12,767` (`0`) | `6,759` / `14,124` (`0`) | `19,747` / `25,394` (`0`) | `30,099` / `41,146` (`0`) | **`13,300.9`** / `21,158.1` (`0.0`) |
| **`gemini-4-argon`** | **`low`** | `11,046` / `18,213` (`0`) | `16,490` / `26,568` (`0`) | `7,539` / `13,687` (`0`) | `7,836` / `12,810` (`0`) | `11,790` / `25,708` (`0`) | **`10,940.2`** / `19,397.1` (`0.0`) |
| **`gemini-4-argon`** | **`medium`** | `5,146` / `14,749` (`0`) | `5,018` / `13,742` (`0`) | `5,866` / `12,776` (`0`) | `5,286` / `10,626` (`0`) | `3,341` / `14,506` (`0`) | **`4,931.3`** / `13,279.8` (`0.0`) |
| **`gemini-4-argon`** | **`high`** | `28,720` / `35,282` (`971`) | `27,969` / `36,906` (`1911`) | `18,849` / `24,482` (`614`) | `14,046` / `19,463` (`850`) | `46,294` / `55,069` (`1154`) | **`27,175.9`** / `34,240.4` (`1100.0`) |
| **`gemini-4-carbon`** | **`budget=0`** | `3,963` / `10,957` (`0`) | `2,612` / `14,469` (`0`) | `4,316` / `9,688` (`0`) | `5,257` / `10,210` (`0`) | `6,022` / `15,191` (`0`) | **`4,434.0`** / `12,103.0` (`0.0`) |
| **`gemini-4-carbon`** | **`low`** | `5,460` / `12,293` (`0`) | `2,526` / `10,854` (`0`) | `4,138` / `10,116` (`0`) | `9,456` / `13,682` (`0`) | `5,424` / `15,484` (`0`) | **`5,400.9`** / `12,485.9` (`0.0`) |
| **`gemini-4-carbon`** | **`medium`** | `8,512` / `13,819` (`503`) | `27,480` / `34,911` (`1267`) | `7,724` / `12,720` (`352`) | `9,944` / `14,121` (`638`) | `13,581` / `20,519` (`806`) | **`13,448.1`** / `19,218.0` (`713.2`) |
| **`gemini-4-carbon`** | **`high`** | `30,667` / `35,428` (`2908`) | `51,353` / `59,310` (`4360`) | `29,288` / `34,225` (`2086`) | `19,564` / `24,842` (`1150`) | `40,907` / `47,244` (`3469`) | **`34,355.5`** / `40,209.9` (`2794.6`) |

---

### 4. 全220試行の横断ベンチマークから得られる6つの重要インサイト

1. **非推奨 `thinking_budget=0` の実機挙動（`3.5-flash-lite` で 400 エラー、他4モデルでも `low` 相当へ丸められる）**：
   - **`gemini-3.5-flash-lite`**：`thinking_budget=0` を渡すと全10問すべてで **`400 INVALID_ARGUMENT`（非対応）** となる。思考トークンを `0 tok` にしたい場合は公式仕様どおり **`thinking_level="minimal"`** を指定する必要がある。
   - **`gemini-3.8-flash` / `gemini-4-hydrogen` / `gemini-4-argon` / `gemini-4-carbon`**：後方互換としてエラーにならず受理されるものの、サーバー内部で各モデルの最小思考レベル（`low`）相当へ丸められる。実際、`gemini-3.8-flash [budget=0]` は複雑5問平均 `2,564.7 ms`（`ThTok = 91.8`）で `low`（`2,586.6 ms`, `ThTok = 104.6`）と同等であり、`gemini-4-hydrogen [budget=0]` も複雑5問平均で **`670.4 tok`**（`low` は `657.6 tok`）の思考トークンを消費するため、`thinking_budget=0` によって推論を強制ゼロ化できるわけではない。
2. **`gemini-3.5-flash-lite` の圧倒的なサブ秒レスポンスと高速推論デコード**：
   - `minimal`（デフォルト）では簡単・複雑を問わず推論トークンが `0 tok` に保たれ、**簡単5問平均 `TTFT = 733.9 ms`、複雑5問平均 `TTFT = 677.6 ms`（総合平均 `705.8 ms`）** というサブ秒の初動応答を実現している。
   - さらに特筆すべきは `low` / `medium` / `high` での推論トークン生成速度であり、例えば複雑5問の `high` では平均 **`1,313.0 tok`** もの内部推論を行いながら **平均 `TTFT = 3,493.9 ms`（完了 `4,837.8 ms`）** で返答している（1秒あたり約450〜500推論トークンに相当し、`3.8-flash` の約4倍高速）。
3. **`gemini-4-hydrogen` は `gemini-3.8-flash` より多く思考しつつ、全文完了（`Total`）は逆に速い**：
   - `gemini-4-hydrogen` は常時思考型であるため、`low` でも簡単5問で平均 `183.8 tok`、複雑5問で平均 `657.6 tok` を思考する（`3.8-flash` の `low` はそれぞれ `62.0 tok` / `104.6 tok`）。
   - そのため複雑5問の初動 TTFT は `3.8-flash [low]`（`2,586.6 ms`）の方が `4-hydrogen [low]`（`3,908.6 ms`）より約1.3秒速いが、**出力トークンのデコード速度は `4-hydrogen` の方が大幅に高速化されているため、全文完了時間（`Total`）は `4-hydrogen [low]` の方が約2.1秒も短い（複雑5問平均 `5,899.8 ms` vs. `7,965.4 ms`、全10問総合平均でも `4,633.7 ms` vs. `6,503.6 ms`）**。
   - `medium` や `high` でも同様であり、特に **`4-hydrogen [high]`（総合平均 TTFT `6,700.1 ms` / Total `8,524.1 ms`）は `3.8-flash [high]`（総合平均 TTFT `11,808.3 ms` / Total `15,725.6 ms`）に比べて約43〜46%高速** である。
4. **`gemini-4-hydrogen` 専用の `xhigh` レベルの実力**：
   - `4-hydrogen [xhigh]` は複雑5問で平均 **`2,248.0 tok`（最大 `2,973 tok`）** の徹底的な内部検算を実行しながら、平均 `TTFT = 13,015.8 ms` / `Total = 15,431.1 ms` で完了する。これは **`3.8-flash [high]`（`1,549.0 tok` で Total `18,948.5 ms`）よりも短い待ち時間で約1.45倍深い思考トークンを投入できる** ことを意味する。
5. **`gemini-4-argon` と `gemini-4-carbon` における `low` / `medium` vs. `high` の二極化特性**：
   - フロンティア推論モデルである `4-argon` と `4-carbon` は、`low`（および `4-argon` の `medium`）では `usage_metadata.thoughts_token_count = 0` のダイレクト応答モードとして動作し、`4-argon [medium]` では複雑5問を平均 **`TTFT = 4,931.3 ms`（`Total = 13,279.8 ms`）** で処理する。
   - 一方、`high`（および `4-carbon` の `medium`）では重厚な長尺推論が発動し、特に **`4-carbon [high]` の複雑5問では平均 `2,794.6 tok`（`C2` では最大 `4,360 tok`）を費やして平均 `TTFT = 34.4 秒` / `Total = 40.2 秒`** を要するため、対話UIのフロントエンドに直接つなぐのではなく、非同期バックグラウンドジョブやエスカレーション後の深層解析ワーカーとして配置するのが適切である。
6. **Adaptive Thinking Router（第4章）への応用指針**：
   - ステージ1の即時受付・ルーティング層には **`gemini-3.5-flash-lite`（全レベル）**、**`gemini-3.8-flash [low]`**、または **`gemini-4-hydrogen [low]`** を配置し、複雑計算と判定されたステージ2の並列推論ワーカーには **`gemini-3.8-flash [medium / high]`** または **`Gemini 4` シリーズ（`4-hydrogen` の `medium` 以上 / `4-argon` / `4-carbon`）** を組み合わせることで、初動1〜2秒台の体感速度と深い多段階推論精度を両立できる。

