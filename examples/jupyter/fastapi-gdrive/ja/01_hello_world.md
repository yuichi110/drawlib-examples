# Hello World (FastAPI + Google Drive)

これは、FastAPI のコードや Drawlib の図解を追加する前に、**Drawlib -> `.ipynb` -> `rclone` -> Google Drive -> Google Colab** の一連の動作を確認するための最小構成（Python のみ）の Hello World ノートブックです。

## 1. Python Hello World

```python
import sys

message = "Hello, FastAPI on Google Drive!"
print(message)
print(f"Python version: {sys.version.split()[0]}")
message
```

## 2. 簡単な関数の動作確認

```python
def greet(name: str) -> dict[str, str]:
    return {"message": f"Hello, {name}!"}

greet("Colab")
```

