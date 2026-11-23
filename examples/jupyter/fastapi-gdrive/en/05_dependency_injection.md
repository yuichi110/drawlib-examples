# 05. Dependency Injection with Depends

One of FastAPI's standout architectural strengths is its built-in **Dependency Injection (DI)** system. Using `Depends`, you can cleanly factor out shared logic—such as authentication checks, database sessions, query parameters, and security policies—into modular, testable components.

```drawlib align=center code=fold file=05_dependency_injection_tree.png caption="FastAPI Dependency Injection Flow: Resolving Reusable Components via Depends into Endpoint Functions"
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
    "Dependency Injection with Depends: Incoming Request -> Resolve Dependencies -> Inject into Endpoint",
    style=Styles.DarkBold.patch(text_size=10.6),
)

# 1. Incoming Request
rectangle((18.0, 27.5), width=22, height=31, style=Styles.Neutral.patch(shape_r=1.8))
phosphor.globe((18.0, 38.0), width=5.0, style=Styles.Dark)
text((18.0, 31.8), "Request", style=Styles.DarkBold.patch(text_size=10.0))
text(
    (18.0, 20.5),
    "GET /items\n• Headers\n• Query params\n• Cookies / Body",
    style=Styles.Dark.patch(text_size=8.8),
)

line((29.0, 33.0), (37.0, 37.0), arrow_head="->", style=Styles.DarkBold)
line((29.0, 22.0), (37.0, 18.0), arrow_head="->", style=Styles.DarkBold)

# 2. Dependency A: Pagination
rectangle((51.0, 37.0), width=26, height=13, style=Styles.PrimaryNeutral.patch(shape_r=1.5))
text((51.0, 39.5), "Depends(pagination)", style=Styles.DarkBold.patch(text_size=9.2))
text((51.0, 33.5), "skip: int, limit: int", style=Styles.Dark.patch(text_size=8.5))

# 3. Dependency B: Auth Check
rectangle((51.0, 18.0), width=26, height=13, style=Styles.PrimaryNeutral.patch(shape_r=1.5))
text((51.0, 20.5), "Depends(verify_key)", style=Styles.DarkBold.patch(text_size=9.2))
text((51.0, 14.5), "X-API-Key header", style=Styles.Dark.patch(text_size=8.5))

line((64.0, 37.0), (74.0, 31.0), arrow_head="->", style=Styles.DarkBold)
line((64.0, 18.0), (74.0, 24.0), arrow_head="->", style=Styles.DarkBold)

# 4. Target Endpoint (Focal Hero)
rectangle((88.0, 27.5), width=26, height=31, style=Styles.PrimaryFlat.patch(shape_r=1.8))
code_icons.fastapi((88.0, 38.0), width=5.0, style=Styles.White)
text((88.0, 31.8), "Endpoint Function", style=Styles.WhiteBold.patch(text_size=10.0))
text(
    (88.0, 20.5),
    "read_items(\n  params = Inject A,\n  client = Inject B\n)",
    style=Styles.White.patch(text_size=8.8),
)

line((101.0, 27.5), (107.0, 27.5), arrow_head="->", style=Styles.DarkBold)

# 5. Clean Response
rectangle((118.0, 27.5), width=18, height=31, style=Styles.SecondaryNeutral.patch(shape_r=1.8))
phosphor.check_circle((118.0, 38.0), width=5.0, style=Styles.PrimaryBold)
text((118.0, 31.8), "Response", style=Styles.DarkBold.patch(text_size=10.0))
text(
    (118.0, 20.5),
    "HTTP 200\nVerified\nJSON Data",
    style=Styles.Dark.patch(text_size=8.8),
)

# Bottom ribbon
rectangle(
    (64, 4.8),
    width=122,
    height=6.0,
    style=Styles.Neutral.patch(shape_r=1.2),
    text="Hierarchical Dependency Trees   •   Code Reuse (DRY)   •   Security & DB Lifecycles",
    text_style=Styles.DarkBold.patch(text_size=9.5),
)

save()
```

```python
!pip install -q fastapi httpx
```

---

## 1. Extracting Reusable Query Logic

Parameters like pagination (`skip`, `limit`) can be factored into a reusable dependency function:

```python
from fastapi import Depends, FastAPI, Header, HTTPException, status
from fastapi.testclient import TestClient

app = FastAPI(title="Dependency Injection")

def common_parameters(skip: int = 0, limit: int = 10):
    return {"skip": skip, "limit": limit}

@app.get("/items/")
def read_items(params: dict = Depends(common_parameters)):
    return {
        "applied_params": params,
        "items": [f"Item_{i}" for i in range(params["skip"], params["skip"] + params["limit"])],
    }

client = TestClient(app)

res = client.get("/items/?skip=5&limit=2")
print("Items with DI ->", res.json())
```

---

## 2. Enforcing Security Headers with `Depends`

Dependencies can inspect request headers and raise `HTTPException` early if validation fails:

```python
API_SECRET_KEY = "drawlib-secret-token"

def verify_api_key(x_api_key: str = Header(..., description="API Access Key")):
    if x_api_key != API_SECRET_KEY:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or missing API Key",
        )
    return {"client_id": "authorized_user"}

@app.get("/secure-data/")
def get_secure_data(
    user: dict = Depends(verify_api_key),
    pagination: dict = Depends(common_parameters),
):
    return {
        "status": "authenticated",
        "user": user,
        "pagination": pagination,
        "secret_payload": [10, 20, 30],
    }
```

---

## 3. Testing Dependencies

Using `TestClient`, let's verify endpoint responses without an API key (422/401), with an invalid key (401), and with a valid key (200).

```python
# 1. Missing header -> 422
res_unauth = client.get("/secure-data/")
print("Without Key -> Status:", res_unauth.status_code)

# 2. Invalid key -> 401
res_bad = client.get("/secure-data/", headers={"X-API-Key": "wrong-key"})
print("Wrong Key   -> Status:", res_bad.status_code, res_bad.json()["detail"])

# 3. Valid key -> 200 OK
res_auth = client.get("/secure-data/", headers={"X-API-Key": "drawlib-secret-token"})
print("Valid Key   -> Status:", res_auth.status_code)
print("Auth Data   ->", res_auth.json())
```

---

## Next Steps

In **Chapter 6 (Authentication & JWT Bearer Security)**, we apply `Depends` to implement standard **OAuth2 Password flows with signed JWT tokens**!
