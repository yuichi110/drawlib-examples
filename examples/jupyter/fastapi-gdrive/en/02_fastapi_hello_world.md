# 02. FastAPI Hello World & Core Request Lifecycle

In this chapter, we kick off the hands-on **FastAPI** tutorial. We begin by visualizing how an incoming HTTP request flows from the client through the ASGI server into FastAPI's router, and then run a minimal application interactively inside Colab.

```drawlib align=center code=fold file=02_fastapi_request_flow.png caption="FastAPI Request Lifecycle: From Client to Uvicorn (ASGI), Router Matching, and JSON Serialization"
from drawlib.canvas import save, setup
from drawlib.icons import code as code_icons, phosphor
from drawlib.lines import line
from drawlib.shapes import rectangle
from drawlib.styles import Styles
from drawlib.text import text

setup(width=128, height=54)

# Outer container
rectangle((64, 30.0), width=122, height=42, style=Styles.MutedDashed.patch(shape_r=2.0))
text(
    (64, 47.0),
    "FastAPI Request & Response Lifecycle: Client -> Uvicorn (ASGI) -> Router -> JSON",
    style=Styles.DarkBold.patch(text_size=10.6),
)

# 1. Client
rectangle((19.0, 27.5), width=24, height=31, style=Styles.Neutral.patch(shape_r=1.8))
phosphor.globe((19.0, 38.0), width=5.0, style=Styles.Dark)
text((19.0, 31.8), "Client / Browser", style=Styles.DarkBold.patch(text_size=10.0))
text(
    (19.0, 20.5),
    "HTTP GET /\n• Headers\n• User-Agent\n• Accept: json",
    style=Styles.Dark.patch(text_size=9.2),
)

line((31.0, 27.5), (37.0, 27.5), arrow_head="->", style=Styles.DarkBold)

# 2. Uvicorn (ASGI Server)
rectangle((49.0, 27.5), width=24, height=31, style=Styles.PrimaryNeutral.patch(shape_r=1.8))
code_icons.python((49.0, 38.0), width=5.0, style=Styles.PrimaryBold)
text((49.0, 31.8), "Uvicorn (ASGI)", style=Styles.DarkBold.patch(text_size=10.0))
text(
    (49.0, 20.5),
    "Async Worker\n• HTTP parse\n• Event Loop\n• Forwards scope",
    style=Styles.Dark.patch(text_size=9.2),
)

line((61.0, 27.5), (67.0, 27.5), arrow_head="->", style=Styles.DarkBold)

# 3. FastAPI Application (Focal Hero)
rectangle((79.0, 27.5), width=24, height=31, style=Styles.PrimaryFlat.patch(shape_r=1.8))
code_icons.fastapi((79.0, 38.0), width=5.0, style=Styles.White)
text((79.0, 31.8), "FastAPI Router", style=Styles.WhiteBold.patch(text_size=10.0))
text(
    (79.0, 20.5),
    "@app.get('/')\n• Match endpoint\n• Python execution\n• dict return",
    style=Styles.White.patch(text_size=9.2),
)

line((91.0, 27.5), (97.0, 27.5), arrow_head="->", style=Styles.DarkBold)

# 4. JSON Response
rectangle((109.0, 27.5), width=24, height=31, style=Styles.SecondaryNeutral.patch(shape_r=1.8))
phosphor.file_code((109.0, 38.0), width=5.0, style=Styles.PrimaryBold)
text((109.0, 31.8), "JSON Response", style=Styles.DarkBold.patch(text_size=10.0))
text(
    (109.0, 20.5),
    "HTTP 200 OK\n• Content-Type\n• Serialized dict\n• {\"message\": ...}",
    style=Styles.Dark.patch(text_size=9.2),
)

# Bottom ribbon
rectangle(
    (64, 4.8),
    width=122,
    height=6.0,
    style=Styles.Neutral.patch(shape_r=1.2),
    text="Standard Python Typing   •   Automatic JSON Serialization   •   Interactive In-Process TestClient",
    text_style=Styles.DarkBold.patch(text_size=9.5),
)

save()
```

---

## 1. What is FastAPI?

**FastAPI** is a modern, high-performance web framework for building APIs with Python 3.8+ based on standard Python type hints.

### Core Highlights
- **High Performance**: On par with NodeJS and Go (powered by Starlette and Pydantic on ASGI).
- **Type Safety & Editor Autocompletion**: Built on standard type annotations, minimizing runtime bugs.
- **Automatic API Documentation**: Generates interactive Swagger UI and ReDoc specifications out of the box.

---

## 2. Hands-on: Install Required Packages

First, install FastAPI and `httpx` (required for test execution).

```python
!pip install -q fastapi httpx
```

---

## 3. Running a Minimal FastAPI App with `TestClient`

In local development, FastAPI runs via `uvicorn main:app --reload`. In interactive notebook environments, running a persistent server blocks the execution kernel.

Instead, we use Starlette / FastAPI's **`TestClient`**. `TestClient` allows you to **simulate HTTP requests and test responses in-process without launching a background daemon**.

```python
from fastapi import FastAPI
from fastapi.testclient import TestClient

# 1. Initialize FastAPI application instance
app = FastAPI(
    title="FastAPI Hands-on Tutorial",
    description="Hands-on FastAPI with Drawlib & Google Colab",
    version="1.0.0",
)

# 2. Define a root endpoint (GET /)
@app.get("/")
def read_root():
    return {
        "message": "Hello World from FastAPI!",
        "status": "success",
        "powered_by": "Drawlib (Illustration & Notebook as Code)",
    }

# 3. Call endpoint in-process using TestClient
client = TestClient(app)
response = client.get("/")

# 4. Verify results
print("Status Code:", response.status_code)
print("Response JSON:", response.json())
```

### Code Walkthrough
1. **`app = FastAPI(...)`**: The central application instance managing routes, middleware, and OpenAPI specs.
2. **`@app.get("/")`**: Path mapping decorator handling HTTP GET requests to `/`.
3. **Returning Python Dictionaries**: When an endpoint returns a Python `dict`, FastAPI automatically serializes it to JSON with `HTTP 200 OK`.

---

## 4. Adding Another Endpoint

Adding routes is straightforward. Let's register `/info`:

```python
@app.get("/info")
def read_info():
    return {
        "app_name": "FastAPI Hands-on",
        "features": ["Async", "Type Hints", "Auto OpenAPI", "Pydantic Validation"],
        "version": "1.0.0",
    }

res_info = client.get("/info")
print("GET /info ->", res_info.json())
```

---

## What's Next?

In Chapter 2, we covered FastAPI's minimal Hello World and request handling basics.
In **Chapter 3 (Routing & Parameter Parsing)**, we will explore **path parameters**, **query parameters**, and automatic type casting using Python type annotations!

