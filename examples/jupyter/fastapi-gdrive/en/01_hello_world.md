# Hello World (FastAPI + Google Drive)

This is a minimal Python-only Hello World notebook used to verify the end-to-end **Drawlib -> `.ipynb` -> `rclone` -> Google Drive -> Google Colab** workflow before adding FastAPI code and diagrams.

## 1. Python Hello World

```python
import sys

message = "Hello, FastAPI on Google Drive!"
print(message)
print(f"Python version: {sys.version.split()[0]}")
message
```

## 2. Simple Function Check

```python
def greet(name: str) -> dict[str, str]:
    return {"message": f"Hello, {name}!"}

greet("Colab")
```

