# 03. Streaming 配信と ThinkingConfig による思考制御

**`gemini-3.8-flash`** を用いた対話型 AI アプリケーションの体感速度は、**Streaming 配信 (`generate_content_stream`)** による最初の1トークン到達時間（TTFT: Time To First Token）の短縮と、**`types.ThinkingConfig(thinking_level=...)`** によるタスク難度に応じた思考レベル（`"low"`・`"medium"`・`"high"`）の最適化という2つの軸で改善できます。
段階的なチャンク配信と明示的な思考レベル制御を組み合わせることで、複雑な推論精度を維持しつつ、数秒かかっていたブロッキング待機をサブ秒のインタラクティブな応答体験へと変革できます。

```drawlib align=center code=fold file=ch03_streaming_ttft_ja.png caption="図3-1: ブロッキング生成と Streaming 配信・thinking_level の TTFT タイムライン比較 (gemini-3.8-flash)"
from drawlib.canvas import save, setup
from drawlib.icons import phosphor
from drawlib.lines import line
from drawlib.shapes import rectangle
from drawlib.styles import Styles
from drawlib.text import text

setup(width=156, height=74, dpi=150)

# Header labels
text((6.0, 67.0), "配信モードと設定", style=Styles.DarkBold.patch(text_size=11.0, halign="left"))
text(
    (101.0, 67.0),
    "gemini-3.8-flash 経過時間タイムライン (秒)",
    style=Styles.DarkBold.patch(text_size=11.0),
)

# Vertical timeline gridlines (0.0s to 3.0s -> x = 56.0 to 146.0, 30 units/sec)
for i in range(7):
    tx = 56.0 + i * 15.0
    sec = i * 0.5
    line((tx, 13.0), (tx, 62.5), style=Styles.MutedDashedThin)
    text((tx, 8.2), f"{sec:.1f}s", style=Styles.Muted.patch(text_size=10.0))

line((56.0, 13.0), (146.0, 13.0), style=Styles.Dark)

# Row 1: Blocking generate_content()
rectangle((29.0, 55.0), width=46.0, height=12.5, style=Styles.Neutral.patch(shape_r=1.8))
phosphor.hourglass((11.0, 55.0), width=4.4, style=Styles.Dark)
text((15.2, 57.3), "1. ブロッキング呼び出し", style=Styles.DarkBold.patch(text_size=10.5, halign="left"))
text((15.2, 52.3), "generate_content()", style=Styles.Muted.patch(text_size=10.0, halign="left"))

rectangle(
    (72.5, 55.0),
    width=33.0,
    height=9.4,
    style=Styles.SecondaryNeutral.patch(shape_r=1.2),
    text="思考フェーズ (1.1s)",
    text_style=Styles.Dark.patch(text_size=10.0),
)
rectangle(
    (114.8, 55.0),
    width=50.4,
    height=9.4,
    style=Styles.Neutral.patch(shape_r=1.2),
    text="一括バッファ生成・TTFT 2.8s",
    text_style=Styles.DarkBold.patch(text_size=10.0),
)

# Row 2: Streaming + thinking_level="medium" (Default)
rectangle((29.0, 38.5), width=46.0, height=12.5, style=Styles.Neutral.patch(shape_r=1.8))
phosphor.brain((11.0, 38.5), width=4.4, style=Styles.PrimaryBold)
text((15.2, 40.8), "2. Stream + 通常思考", style=Styles.DarkBold.patch(text_size=10.5, halign="left"))
text((15.2, 35.8), 'thinking_level="medium"', style=Styles.Muted.patch(text_size=10.0, halign="left"))

rectangle(
    (72.5, 38.5),
    width=33.0,
    height=9.4,
    style=Styles.SecondaryNeutral.patch(shape_r=1.2),
    text="思考フェーズ (1.1s)",
    text_style=Styles.Dark.patch(text_size=10.0),
)
rectangle(
    (114.8, 38.5),
    width=50.4,
    height=9.4,
    style=Styles.PrimaryNeutral.patch(shape_r=1.2),
    text="TTFT 1.1s -> チャンク順次配信",
    text_style=Styles.PrimaryBold.patch(text_size=10.0),
)

# Row 3: Streaming + thinking_level="low" (Focal Hero)
rectangle((29.0, 22.0), width=46.0, height=12.5, style=Styles.PrimaryNeutral.patch(shape_r=1.8))
phosphor.lightning((11.0, 22.0), width=4.4, style=Styles.PrimaryBold)
text((15.2, 24.3), "3. 高速 Stream 配信", style=Styles.PrimaryBold.patch(text_size=10.5, halign="left"))
text((15.2, 19.3), 'thinking_level="low"', style=Styles.Dark.patch(text_size=10.0, halign="left"))

rectangle((60.0, 22.0), width=8.0, height=9.4, style=Styles.Neutral.patch(shape_r=1.0))
rectangle(
    (86.8, 22.0),
    width=44.4,
    height=9.4,
    style=Styles.PrimaryFlat.patch(shape_r=1.2),
    text="TTFT 0.28s・サブ秒即時配信",
    text_style=Styles.WhiteBold.patch(text_size=10.0),
)
text((111.5, 22.0), "1.75s で完了", style=Styles.PrimaryBold.patch(text_size=10.0, halign="left"))

save()
```

---

## 1. クライアント初期化とプログレッシブ Streaming (`generate_content_stream`)

まずは使用するモデル `MODEL = "gemini-3.8-flash"` を定義し、Google Colab の左サイドバーにある **🔑 シークレット (Secrets)** に登録した `GEMINI_API_KEY` を読み込んで統合 `genai.Client` を初期化します。

```python
MODEL = "gemini-3.8-flash"

from google.colab import userdata
from google import genai

client = genai.Client(api_key=userdata.get("GEMINI_API_KEY"))
```

通常の `client.models.generate_content()` はサーバー側で全文の生成が完了するまで応答を返しませんが、**`client.models.generate_content_stream()`** はトークンが生成され次第 `GenerateContentResponse` チャンクを HTTP ストリーム経由で順次返却します。`time.perf_counter()` を用いて最初の非空 `chunk.text` が届くまでの **`ttft_ms`** と全体の **`total_ms`** を計測してみましょう。

```python
import time

t0 = time.perf_counter()
ttft_ms = None

for chunk in client.models.generate_content_stream(
    model=MODEL,
    contents="3文で短いお話を書いてください。",
):
    if chunk.text:
        if ttft_ms is None:
            ttft_ms = (time.perf_counter() - t0) * 1000
        print(chunk.text, end="", flush=True)

total_ms = (time.perf_counter() - t0) * 1000
print(f"\n\nTTFT: {ttft_ms:.0f} ms | Total: {total_ms:.0f} ms")
```

> **補足:** ストリームの先頭や末尾には `usage_metadata` のみを含む空テキストのチャンクが届く場合があるため、出力や `ttft_ms` の計測前には必ず `if chunk.text:` でガードしてください。

---

## 2. `ThinkingConfig` (`thinking_level`) による思考レベルの適正化

`gemini-3.8-flash` は推論機能を備えたモデルであり、可視の出力トークンを生成する前に内部的な **思考トークン (`thoughts_token_count`)** を消費して回答計画や検証を行うことができます。内部思考は最初の出力トークンが返る *前* に実行されるため、`types.ThinkingConfig(thinking_level=...)` に指定する3段階の思考レベルが TTFT とトークンコストに直結します。

- **`thinking_level="low"`（思考 0 トークン・最速 TTFT）**: `gemini-3.8-flash` では内部思考を `0` トークンに抑え、日常チャット・ルーティング・意図分類・情報抽出でサブ秒の高速 TTFT を実現します。
- **`thinking_level="medium"`（既定値・バランス型の動的思考）**: プロンプトの難易度に応じて思考の深さを自動調整します。単純な質問では余分な思考を省きつつ、RAG 要約や SQL 生成では適切な推論を行います。
- **`thinking_level="high"`（深い多段階推論）**: 多段階の数学計算、アルゴリズム実装、アーキテクチャのトレードオフ分析など、精度重視のタスクに十分な思考トークンを割り当てます。

> **重要 (`gemini-3.8-flash` の API 仕様):** Gemini 2.5 世代の数値指定 `thinking_budget` は非推奨（レガシー互換）となったため、`thinking_level` を使用してください（両方の同時指定はエラーになります）。また `gemini-3.8-flash` がサポートする値は `"low"`・`"medium"`・`"high"` の3段階のみであり、`"minimal"` や `"xhigh"` を指定すると HTTP `400 INVALID_ARGUMENT` が返ります。

```drawlib align=center code=fold file=ch03_thinking_tiers_ja.png caption="図3-2: タスク難易度に応じた ThinkingConfig (thinking_level) 設計ガイド (gemini-3.8-flash)"
from drawlib.canvas import save, setup
from drawlib.icons import phosphor
from drawlib.smartarts import CardList
from drawlib.styles import Styles
from drawlib.text import text

setup(width=152, height=68, dpi=150)

text(
    (76.0, 61.5),
    "ワークロード別の thinking_level 選定ガイド (gemini-3.8-flash)",
    style=Styles.DarkBold.patch(text_size=12.0),
)

tiers = CardList(
    style=Styles.Neutral,
    text_style=Styles.DarkBold.patch(text_size=11.0),
    description_style=Styles.Dark.patch(text_size=10.0),
    badge_shape="circle",
    badge_style=Styles.PrimaryNeutral,
    icon_style=Styles.PrimaryBold,
    direction="horizontal",
    show_arrows=True,
    arrow_style=Styles.Dark,
    spacing=5.0,
)
tiers.add(
    'level = "low"',
    "思考 0 トークン・最速 TTFT\nチャット・ルーティング・\n情報抽出・意図分類",
    icon=phosphor.lightning,
    badge_style=Styles.PrimaryFlat,
    icon_style=Styles.WhiteBold,
)
tiers.add(
    'level = "medium"',
    "既定値・バランス型動的思考\nRAG 要約・SQL 生成・\n一般業務ワークロード",
    icon=phosphor.sliders,
    style=Styles.PrimaryNeutral,
)
tiers.add(
    'level = "high"',
    "深い多段階推論トークン\n多段階の数学・コード・\nシステム設計分析",
    icon=phosphor.brain,
)
tiers.draw(xy=(6.0, 6.5), width=140.0, height=49.5, align="bottom_left")

save()
```

### `thinking_level="low"` と `thinking_level="high"` の実測ベンチマーク

同一の計算プロンプトに対して `thinking_level="low"` と `thinking_level="high"` をそれぞれ実行し、ストリームの `usage_metadata` から `ttft_ms`、`total_ms`、内部思考トークン数 (`thoughts_token_count`)、出力トークン数 (`candidates_token_count`) を取得して比較テーブルを出力します。

```python
import time
from google.genai import types

prompt = "27 * 43 + 19 を計算してください。"
rows = []

for level in ("low", "high"):
    t0 = time.perf_counter()
    ttft_ms = None
    usage = None
    chunks = []

    for chunk in client.models.generate_content_stream(
        model=MODEL,
        contents=prompt,
        config=types.GenerateContentConfig(
            thinking_config=types.ThinkingConfig(thinking_level=level),
        ),
    ):
        if chunk.text:
            if ttft_ms is None:
                ttft_ms = (time.perf_counter() - t0) * 1000
            chunks.append(chunk.text)
        if chunk.usage_metadata is not None:
            usage = chunk.usage_metadata

    total_ms = (time.perf_counter() - t0) * 1000
    thoughts_tokens = getattr(usage, "thoughts_token_count", 0) or 0
    output_tokens = getattr(usage, "candidates_token_count", 0) or 0
    rows.append((level, ttft_ms or total_ms, total_ms, thoughts_tokens, output_tokens))
    print(f"[{level}] {''.join(chunks).strip()}")

print(f"\n{'Level':<8} {'TTFT (ms)':>10} {'Total (ms)':>11} {'Thoughts Tok':>14} {'Output Tok':>12}")
print("-" * 59)
for level, ttft_ms, total_ms, thoughts_tokens, output_tokens in rows:
    print(f"{level:<8} {ttft_ms:>10.1f} {total_ms:>11.1f} {thoughts_tokens:>14d} {output_tokens:>12d}")
```

### まとめ

- **ユーザー向け応答は `generate_content_stream` を基本にする**: 全文の生成完了を待たずに思考完了直後からチャンクを順次表示し、体感待機時間を大幅に短縮できます。
- **エンドポイントの SLA に合わせて `thinking_level` を選ぶ**: `gemini-3.8-flash` では、高速ルーティングや軽量チャットに `"low"`（思考 `0` トークン）、標準業務に既定の `"medium"`、高度な推論タスクに `"high"` を使い分けます。
- **`thoughts_token_count` を継続モニタリングする**: `usage_metadata.thoughts_token_count` と `candidates_token_count` を併せて記録することで、本番環境の推論トークン消費とレイテンシのバランスを定量的に管理できます。
