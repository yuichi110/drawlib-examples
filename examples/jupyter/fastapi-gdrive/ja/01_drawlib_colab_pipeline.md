# 01. Drawlib × Google Colab 自動配信パイプライン

このハンズオンノートブックは、**Git リポジトリ内の Markdown ソースから Drawlib を通じて自動生成され、Google Drive 経由で Google Colab へ配信** されています。

```drawlib align=center code=fold file=01_pipeline_git_to_colab.png caption="Git Markdown ソースから Drawlib・rclone を経て Google Colab へ届く自動配信パイプライン"
from drawlib.canvas import save, setup
from drawlib.icons import ai, code as code_icons, phosphor, workspace
from drawlib.lines import line
from drawlib.shapes import circle, rectangle
from drawlib.styles import Styles
from drawlib.text import text

setup(width=128, height=58)

# Outer container
rectangle((64, 32.5), width=122, height=45, style=Styles.MutedDashed.patch(shape_r=2.0))
text(
    (64, 51.0),
    "Illustrated Notebook as Code: Git Markdown -> Drawlib -> Google Drive -> Colab",
    style=Styles.DarkBold.patch(text_size=10.6),
)

# Stage 1: Git Markdown Source
rectangle((16.0, 30.0), width=23, height=34, style=Styles.Neutral.patch(shape_r=1.8))
phosphor.git_branch((16.0, 41.2), width=4.8, style=Styles.PrimaryBold)
text((16.0, 34.4), "1. Git Source", style=Styles.DarkBold.patch(text_size=10.0))
text(
    (16.0, 22.8),
    "docs_src/fastapi/\n• Pure Markdown\n• drawlib code\n• Git SSOT",
    style=Styles.Dark.patch(text_size=9.2),
)

line((27.5, 30.0), (31.5, 30.0), arrow_head="->", style=Styles.DarkBold)

# Stage 2: Drawlib Compiler (Focal Hero)
rectangle((43.0, 30.0), width=23, height=34, style=Styles.PrimaryFlat.patch(shape_r=1.8))
circle((43.0, 41.2), radius=3.4, style=Styles.White.patch(shape_line_width=0))
ai.jupyter((43.0, 41.2), width=4.5, style=Styles.Neutral)
text((43.0, 34.0), "2. drawlib build", style=Styles.WhiteBold.patch(text_size=10.0))
text(
    (43.0, 22.8),
    "build jupyter\n• Base64 diagrams\n• Clean .ipynb\n• Zero local HTML",
    style=Styles.White.patch(text_size=9.2),
)

line((54.5, 30.0), (58.5, 30.0), arrow_head="->", style=Styles.DarkBold)

# Stage 3: rclone copy
rectangle((70.0, 30.0), width=23, height=34, style=Styles.PrimaryNeutral.patch(shape_r=1.8))
phosphor.arrows_clockwise((70.0, 41.2), width=4.8, style=Styles.PrimaryBold)
text((70.0, 34.0), "3. rclone sync", style=Styles.DarkBold.patch(text_size=10.0))
text(
    (70.0, 22.8),
    "-M metadata-set\n• Colab MIME type\n• Preserves IDs\n• Fast & headless",
    style=Styles.Dark.patch(text_size=9.2),
)

line((81.5, 30.0), (85.5, 30.0), arrow_head="->", style=Styles.DarkBold)

# Stage 4: Google Drive Shared Folder
rectangle((97.0, 30.0), width=23, height=34, style=Styles.SecondaryNeutral.patch(shape_r=1.8))
workspace.google_drive((97.0, 41.2), width=4.8, style=Styles.Neutral)
text((97.0, 34.4), "4. Google Drive", style=Styles.DarkBold.patch(text_size=10.0))
text(
    (97.0, 22.8),
    "Shared Folder\n• Viewer role\n• Clean .ipynb\n• Always updated",
    style=Styles.Dark.patch(text_size=9.2),
)

line((108.5, 30.0), (112.5, 30.0), arrow_head="->", style=Styles.DarkBold)

# Stage 5: Google Colaboratory (Recipient run)
rectangle((118.5, 30.0), width=18, height=34, style=Styles.Neutral.patch(shape_r=1.8))
code_icons.colab((118.5, 41.2), width=4.8, style=Styles.Neutral)
text((118.5, 34.4), "5. Colab", style=Styles.DarkBold.patch(text_size=10.0))
text(
    (118.5, 22.8),
    "Run in Cloud\n• Zero install\n• Free GPUs\n• Interactive",
    style=Styles.Dark.patch(text_size=9.2),
)

# Bottom ribbon
rectangle(
    (64, 5.2),
    width=122,
    height=6.4,
    style=Styles.Neutral.patch(shape_r=1.2),
    text="Illustration as Code   •   Self-Contained Base64 Diagrams   •   Zero Local Setup for Learners",
    text_style=Styles.DarkBold.patch(text_size=9.6),
)

save()
```

---

## 1. このノートブックの仕組み（Drawlib による Illustration as Code）

一般的な Jupyter ノートブック（`.ipynb`）を手作業で作成して共有すると、以下のような問題が生じます：
- 画面キャプチャを貼ると画像のリンク切れや画質劣化が起きる。
- `.ipynb` の JSON 内に肥大化した出力データが混ざり、Git での差分比較（Code Review）が難しくなる。
- 共有相手に Python 環境やパッケージのインストール手順を要求してしまう。

この課題を解決するのが **[Drawlib（ドローリブ）](https://www.drawlib.com/)** です。

### Drawlib が実現する 3 つの特徴
1. **Markdown と Python コードだけで記述（Git が Single Source of Truth）**:
   ノートブックの本文も図解も、すべて Git 管理下のプレーンテキスト（Markdown と Python）として記述されます。
2. **自己完結型の Base64 ベクター埋め込み**:
   ノートブック内に描かれているアーキテクチャ図は、ビルド時に自動で画像データ（Base64 Data URI）へ変換され、`.ipynb` 内に直接格納されます。外部画像サーバーは一切不要です。
3. **Google Drive + rclone で完全自動同期**:
   ビルドされた `.ipynb` は、`rclone` を介して Google Drive の共有フォルダへ同期され、受取人はブラウザの **Google Colaboratory** からワンクリックですぐに実行できます。

> [!TIP] Drawlib 公式サイト & ドキュメント
> Drawlib の詳細なアーキテクチャや他の図解コンポーネント（クラウド構成図、シーケンス図、データチャート等）については、公式 Web サイトをご覧ください：
> - **公式ドキュメント**: [https://www.drawlib.com/](https://www.drawlib.com/)
> - **API & CLI リファレンス**: [https://www.drawlib.com/api/](https://www.drawlib.com/api/)

---

## 2. 環境チェック

Google Colab 上でセルを実行（`Shift + Enter`）し、実行環境の Python バージョンを確認してみましょう。

```python
import sys
import platform

print("Python Version:", sys.version)
print("Platform:", platform.platform())
print("Google Colab Ready!")
```

次の第 2 章から、本格的な **FastAPI の Hello World とリクエスト処理の基本** に進みます！

