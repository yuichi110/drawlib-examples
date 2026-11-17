# 01. Google AI Studio で始める Hello World

本クックブックでは `drawlib.toml` の `[jupyter].setup_packages` 設定により、生成されるすべてのノートブック先頭に `!pip install -q google-genai` のみが自動挿入されるため、Google Colab 上で高速に起動でき手動パッケージ追加も不要です。Git リポジトリへ認証情報をハードコードせずに安全に Gemini を呼び出すため、**Google Cloud プロジェクト**に紐付いた API キー（`GEMINI_API_KEY`）を **Google AI Studio** で発行し、Colab 左サイドバーの **シークレット（`🔑` アイコン）** に保存して **「ノートブックからのアクセス（Notebook access）」** を ON に設定します。

```drawlib align=center code=fold file=ch01_aistudio_workflow_ja.png caption="図1-1: Google AI Studio APIキー発行と Colab シークレットによる最短実行フロー"
from drawlib.canvas import save, setup
from drawlib.icons import ai, gcp, phosphor
from drawlib.lines import line
from drawlib.shapes import rectangle
from drawlib.styles import Colors, Styles
from drawlib.text import text

setup(width=152, height=76, dpi=150)

# 外枠のニュートラルフレーム（50%以上を落ち着いた無彩色ベースで構成）
rectangle(
    (76.0, 38.0),
    width=142.0,
    height=66.0,
    style=Styles.Neutral.patch(shape_r=2.5, shape_fill_color=Colors.Light, shape_line_color=Colors.Gray3),
)

# ヘッダータイトル・サブタイトル
text(
    (76.0, 65.5),
    "Google AI Studio + Google Colab 最短セットアップ & 実行フロー",
    style=Styles.DarkBold.patch(text_size=12.8),
)
text(
    (76.0, 60.3),
    "Google Cloud プロジェクト連携  •  Colab シークレット管理  •  統一 google-genai SDK",
    style=Styles.Muted.patch(text_size=10.2),
)

# 4段階のステージカード: width=28.0, gap=7.5 (x = 8.75..143.25)
card_w = 28.0
card_h = 34.0
cy = 37.8
cxs = [22.75, 58.25, 93.75, 129.25]

neutral_card = Styles.White.patch(shape_r=2.2, shape_line_color=Colors.Gray4)
soft_card = Styles.PrimaryNeutral.patch(shape_r=2.2)
hero_card = Styles.PrimaryFlat.patch(shape_r=2.2)

# Stage 1: Google Cloud プロジェクト + AI Studio
rectangle((cxs[0], cy), width=card_w, height=card_h, style=neutral_card)
rectangle((cxs[0], 50.2), width=14.0, height=4.4, style=Styles.SecondaryNeutral.patch(shape_r=1.2, shape_line_width=0))
text((cxs[0], 50.2), "STEP 1", style=Styles.DarkBold.patch(text_size=10.0))
rectangle((cxs[0], 41.5), width=9.2, height=9.2, style=Styles.PrimaryNeutral.patch(shape_r=2.0, shape_line_width=0))
gcp.project((cxs[0], 41.5), width=6.4, style=Styles.Primary)
text((cxs[0], 32.3), "APIキー発行", style=Styles.DarkBold.patch(text_size=11.0))
text((cxs[0], 25.5), "Cloud プロジェクト選択\nGEMINI_API_KEY", style=Styles.Muted.patch(text_size=10.0))

# Stage 2: Colab シークレット保存
rectangle((cxs[1], cy), width=card_w, height=card_h, style=neutral_card)
rectangle((cxs[1], 50.2), width=14.0, height=4.4, style=Styles.SecondaryNeutral.patch(shape_r=1.2, shape_line_width=0))
text((cxs[1], 50.2), "STEP 2", style=Styles.DarkBold.patch(text_size=10.0))
rectangle((cxs[1], 41.5), width=9.2, height=9.2, style=Styles.SecondaryNeutral.patch(shape_r=2.0, shape_line_width=0))
phosphor.key((cxs[1], 41.5), width=6.0, style=Styles.DarkBold)
text((cxs[1], 32.3), "Colab シークレット", style=Styles.DarkBold.patch(text_size=11.0))
text((cxs[1], 25.5), "左ペイン鍵アイコン\nアクセス許可を ON", style=Styles.Muted.patch(text_size=10.0))

# Stage 3: genai.Client 初期化（主役の PrimaryFlat）
rectangle((cxs[2], cy), width=card_w, height=card_h, style=hero_card)
rectangle((cxs[2], 50.2), width=14.0, height=4.4, style=Styles.White.patch(shape_r=1.2, shape_line_width=0))
text((cxs[2], 50.2), "STEP 3", style=Styles.PrimaryBold.patch(text_size=10.0))
rectangle((cxs[2], 41.5), width=9.2, height=9.2, style=Styles.White.patch(shape_r=2.0, shape_line_width=0))
ai.gemini((cxs[2], 41.5), width=6.4, style=Styles.Primary)
text((cxs[2], 32.3), "genai.Client", style=Styles.WhiteBold.patch(text_size=11.2))
text((cxs[2], 25.5), "userdata.get(...)\napi_key=api_key", style=Styles.White.patch(text_size=10.0))

# Stage 4: gemini-3.8-flash 推論レスポンス
rectangle((cxs[3], cy), width=card_w, height=card_h, style=soft_card)
rectangle((cxs[3], 50.2), width=14.0, height=4.4, style=Styles.White.patch(shape_r=1.2, shape_line_color=Colors.Gray3))
text((cxs[3], 50.2), "STEP 4", style=Styles.PrimaryBold.patch(text_size=10.0))
rectangle((cxs[3], 41.5), width=9.2, height=9.2, style=Styles.White.patch(shape_r=2.0, shape_line_color=Colors.Gray3))
phosphor.sparkle((cxs[3], 41.5), width=6.0, style=Styles.PrimaryBold)
text((cxs[3], 32.3), "推論レスポンス", style=Styles.DarkBold.patch(text_size=11.0))
text((cxs[3], 25.5), "gemini-3.8-flash\ntext + usage_metadata", style=Styles.Dark.patch(text_size=10.0))

# ステージ間の矢印（カード間隔 7.5 ユニット）
for idx in range(3):
    x_start = cxs[idx] + card_w / 2.0 + 0.6
    x_end = cxs[idx + 1] - card_w / 2.0 - 0.6
    line((x_start, cy), (x_end, cy), arrow_head="->", style=Styles.DarkBold)

# 下部セットアップ情報バー
rectangle(
    (76.0, 12.2),
    width=134.5,
    height=8.4,
    style=Styles.White.patch(shape_r=1.8, shape_line_color=Colors.Gray4),
)
phosphor.terminal_window((34.5, 12.2), width=4.6, style=Styles.PrimaryBold)
text(
    (80.0, 12.2),
    "自動挿入セットアップセル:  !pip install -q google-genai   •   Git への鍵混入ゼロ",
    style=Styles.DarkBold.patch(text_size=10.2),
)

save()
```

## 1. Colab シークレットを使った最小構成の Hello World (`userdata` + `genai.Client`)

Google Colab で最初のコードセルを実行する前に、以下の手順（初回のみ）でシークレットを設定します。

1. **Google AI Studio**（`aistudio.google.com/apikey`）を開き、**「API キーを作成（Create API key）」** から既存または新規の **Google Cloud プロジェクト**を選択してキーを発行します。
2. Google Colab 左サイドバーの **シークレット（`🔑`）** アイコンを開き、名前を `GEMINI_API_KEY` としてキーを貼り付け、**「ノートブックからのアクセス」** トグルを ON にします。
3. セル先頭で `MODEL = "gemini-3.8-flash"` を定義して利用モデルを分かりやすく指定し、`userdata.get("GEMINI_API_KEY")` で読み込んだキーを `genai.Client` に渡します。

```python
MODEL = "gemini-3.8-flash"

from google.colab import userdata
from google import genai

api_key = userdata.get("GEMINI_API_KEY")
client = genai.Client(api_key=api_key)

response = client.models.generate_content(
    model=MODEL,
    contents="こんにちは！",
)
print(response.text)
```

`genai.Client` は `google-genai` SDK 全体で共通のエントリーポイントです。本章で学ぶ `client.models.*` や `client.chats.*` の呼び出しコードは、AI Studio の API キー認証でも Google Cloud Vertex AI の IAM 認証でも一切書き換えることなくそのまま動作します。

## 2. Google Cloud プロジェクト連携：無料枠（Free Tier）と従量課金枠（Paid Tier）

Google AI Studio で発行されるすべての API キーは、背後にある **Google Cloud プロジェクト**に紐付いています。普段から Google Cloud を利用している開発者は、AI Studio のキー作成ダイアログで既存のプロジェクトを選択できるため、API の有効化（`generativelanguage.googleapis.com`）やクォータ監視、請求管理を一元化できます。

- **無料枠 — Free Tier（課金未設定プロジェクト）**: 選択した Google Cloud プロジェクトに **Cloud Billing（請求先アカウント）が紐付いていない場合**、API キーは完全無料の Free Tier として動作します。ハッカソンや学習・プロトタイピングに最適ですが、レート制限（RPM/TPM/RPD）は低めに設定されており、入出力データが Google 製品の品質改善に利用される場合があります（機密データの送信は避けてください）。
- **従量課金枠 — Paid Tier（Cloud Billing 有効化済み）**: 同じ Google Cloud プロジェクトで **Cloud Billing** を有効化すると、同じ `GEMINI_API_KEY` が自動的に従量課金枠（Pay-as-You-Go）へアップグレードされます。Python コードを1行も変更することなく、本番ワークロード向けの高い RPM/TPM クォータと**エンタープライズ水準のデータプライバシー（プロンプトや出力が Google のモデル学習に使用されない保証）**が適用されます。

```drawlib align=center code=fold file=ch01_billing_tiers_ja.png caption="図1-2: Google AI Studio 無料枠と Cloud Billing 従量課金枠（Paid Tier）の比較"
from drawlib.canvas import save, setup
from drawlib.icons import gcp, phosphor
from drawlib.lines import line
from drawlib.shapes import rectangle
from drawlib.smartarts import CardList, Panel
from drawlib.styles import Colors, Styles
from drawlib.text import text

setup(width=152, height=78, dpi=150)

# 上部共通バナー: 同一の Google Cloud プロジェクト & API キー
rectangle(
    (76.0, 67.5),
    width=140.0,
    height=11.0,
    style=Styles.Neutral.patch(shape_r=2.0, shape_fill_color=Colors.Light, shape_line_color=Colors.Gray4),
)
gcp.project((14.5, 67.5), width=6.6, style=Styles.Primary)
text(
    (80.5, 69.8),
    "同一の Google Cloud プロジェクト & 同一の GEMINI_API_KEY",
    style=Styles.DarkBold.patch(text_size=11.5),
)
text(
    (80.5, 65.0),
    "Cloud Billing を紐付けるだけで、SDK コードを1行も変更せずにレート上限とデータ保護をアップグレード",
    style=Styles.Muted.patch(text_size=10.0),
)

# 左パネル: 無料枠 Free Tier（落ち着いたニュートラル配色）
left_panel = Panel(
    "無料枠 (Free Tier)",
    "課金未設定",
    style=Styles.Neutral,
    header_style=Styles.SecondaryNeutral.patch(shape_line_width=1.2),
    text_style=Styles.DarkBold.patch(text_size=11.2),
    description_style=Styles.Muted.patch(text_size=10.0),
    icon=phosphor.code,
    icon_style=Styles.DarkBold,
    header_variant="filled",
    header_height=10.0,
)
left_panel.draw((6.0, 5.5), width=64.0, height=52.5, align="bottom_left")
l_xy, l_w, l_h = left_panel.get_content_box((6.0, 5.5), width=64.0, height=52.5, padding=(3.2, 2.6))

free_cards = CardList(
    style=Styles.White,
    text_style=Styles.DarkBold.patch(text_size=10.5),
    description_style=Styles.Muted.patch(text_size=10.0),
    badge_shape="rounded_rect",
    badge_style=Styles.SecondaryNeutral,
    icon_style=Styles.DarkBold,
    spacing=2.2,
)
free_cards.add("完全無料（$0）で開始", "請求先アカウント未設定のプロジェクト", icon=phosphor.credit_card)
free_cards.add("検証用レートクォータ", "テスト向けの低めな RPM / TPM 上限", icon=phosphor.chart_bar)
free_cards.add("標準データ利用規約", "入出力が製品改善に使われる場合あり", icon=phosphor.shield_check)
free_cards.draw(l_xy, width=l_w, height=l_h)

# 中央のアップグレード矢印（パネル間隔 12.0 ユニット）
line((71.2, 31.8), (80.8, 31.8), arrow_head="->", style=Styles.DarkBold)
text((76.0, 36.8), "課金を\n有効化", style=Styles.PrimaryBold.patch(text_size=10.0))

# 右パネル: 従量課金枠 Paid Tier（ヘッダーのみ PrimaryFlat で強調）
right_panel = Panel(
    "従量課金枠 (Paid Tier)",
    "Cloud Billing 連携",
    style=Styles.PrimaryNeutral,
    header_style=Styles.PrimaryFlat,
    text_style=Styles.WhiteBold.patch(text_size=11.2),
    description_style=Styles.White.patch(text_size=10.0),
    icon=phosphor.sparkle,
    icon_style=Styles.WhiteBold,
    header_variant="filled",
    header_height=10.0,
)
right_panel.draw((82.0, 5.5), width=64.0, height=52.5, align="bottom_left")
r_xy, r_w, r_h = right_panel.get_content_box((82.0, 5.5), width=64.0, height=52.5, padding=(3.2, 2.6))

paid_cards = CardList(
    style=Styles.White,
    text_style=Styles.DarkBold.patch(text_size=10.5),
    description_style=Styles.Dark.patch(text_size=10.0),
    badge_shape="rounded_rect",
    badge_style=Styles.PrimaryNeutral,
    icon_style=Styles.PrimaryBold,
    spacing=2.2,
)
paid_cards.add("トークン従量課金", "Google Cloud 請求先へ統合請求", icon=phosphor.credit_card)
paid_cards.add("高い RPM / TPM クォータ", "本番アプリのトラフィックに対応", icon=phosphor.chart_bar)
paid_cards.add(
    "学習利用なし（データ保護）",
    "入出力は Google モデル学習に不使用",
    icon=phosphor.shield_check,
    badge_style=Styles.PrimaryFlat,
    icon_style=Styles.WhiteBold,
)
paid_cards.draw(r_xy, width=r_w, height=r_h)

save()
```

## 3. `GenerateContentConfig` とトークン消費量（`usage_metadata`）の確認

モデルの振る舞い（`system_instruction`）や出力の再現性（`temperature`）を制御するには、`types.GenerateContentConfig` を `generate_content` に渡します。また、レスポンスの `response.usage_metadata` からは、入力プロンプト（`prompt_token_count`）、内部思考（`thoughts_token_count`）、最終回答（`candidates_token_count`）の正確なトークン数を取得できます。

```python
from google.genai import types

config = types.GenerateContentConfig(
    system_instruction="1つの短い文で答えてください。",
    temperature=0.2,
)

response = client.models.generate_content(
    model=MODEL,
    contents="Pythonとは何ですか？",
    config=config,
)
print(response.text)

usage = response.usage_metadata
print(f"Prompt tokens:     {usage.prompt_token_count or 0}")
print(f"Thoughts tokens:   {usage.thoughts_token_count or 0}")
print(f"Candidates tokens: {usage.candidates_token_count or 0}")
```

`gemini-3.8-flash` では内部推論に費やされたトークン数が `thoughts_token_count` として独立して記録されるため、入出力サイズと思考コストの内訳を `usage_metadata` から一目で把握できます。

### まとめと次のステップ

- **高速かつセキュアな実行環境**: `google-genai` のみの軽量セットアップと Colab シークレットによる `GEMINI_API_KEY` 管理を組み合わせることで、Git への鍵漏洩を防ぎつつ、Google Cloud プロジェクトの無料枠・従量課金枠を素早く使い分けられます。
- **次章（Chapter 02）のプレビュー**: 続く第2章では、後続の `gemini-3.8-flash` 呼び出しコードを1行も変えずに、`genai.Client` の初期化だけを **Google Cloud Vertex AI**（`vertexai=True`・IAM 認証）へ切り替える方法を解説します。
