# 04. Pydantic & Request Body Validation

One of the most critical aspects of API development is **validating incoming JSON payloads**. FastAPI integrates seamlessly with **Pydantic**, enabling automatic schema parsing, data validation, and documentation generation with standard Python classes.

```drawlib align=center code=fold file=04_pydantic_validation_flow.png caption="Pydantic Request Validation Flow: JSON Payload -> Schema Parsing -> Constraints -> Verified Model"
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
    "Pydantic Validation Flow: JSON Payload -> Schema Parsing -> Constraints -> Verified Model",
    style=Styles.DarkBold.patch(text_size=10.6),
)

# 1. Incoming JSON Payload
rectangle((19.0, 27.5), width=24, height=31, style=Styles.Neutral.patch(shape_r=1.8))
phosphor.file_code((19.0, 38.0), width=5.0, style=Styles.Dark)
text((19.0, 31.8), "JSON Payload", style=Styles.DarkBold.patch(text_size=10.0))
text(
    (19.0, 20.5),
    "POST /items/\n{\n  'name': 'Widget',\n  'price': 29.99\n}",
    style=Styles.Dark.patch(text_size=8.5),
)

line((31.0, 27.5), (37.0, 27.5), arrow_head="->", style=Styles.DarkBold)

# 2. Pydantic BaseModel
rectangle((49.0, 27.5), width=24, height=31, style=Styles.PrimaryNeutral.patch(shape_r=1.8))
code_icons.python((49.0, 38.0), width=5.0, style=Styles.PrimaryBold)
text((49.0, 31.8), "BaseModel", style=Styles.DarkBold.patch(text_size=10.0))
text(
    (49.0, 20.5),
    "class Item(Base):\n• name: str\n• price: float\n• tags: list = []",
    style=Styles.Dark.patch(text_size=8.8),
)

line((61.0, 27.5), (67.0, 27.5), arrow_head="->", style=Styles.DarkBold)

# 3. Field Constraints (Focal Hero)
rectangle((79.0, 27.5), width=24, height=31, style=Styles.PrimaryFlat.patch(shape_r=1.8))
phosphor.shield_check((79.0, 38.0), width=5.0, style=Styles.White)
text((79.0, 31.8), "Field Validator", style=Styles.WhiteBold.patch(text_size=10.0))
text(
    (79.0, 20.5),
    "Validation Engine\n• price > 0\n• max_length=50\n• type coercion",
    style=Styles.White.patch(text_size=9.0),
)

line((91.0, 27.5), (97.0, 27.5), arrow_head="->", style=Styles.DarkBold)

# 4. Success or 422 Error
rectangle((109.0, 27.5), width=24, height=31, style=Styles.SecondaryNeutral.patch(shape_r=1.8))
phosphor.check_square((109.0, 38.0), width=5.0, style=Styles.PrimaryBold)
text((109.0, 31.8), "Validated Object", style=Styles.DarkBold.patch(text_size=10.0))
text(
    (109.0, 20.5),
    "HTTP 201 Created\n• item.name\n• item.price\n(or 422 details)",
    style=Styles.Dark.patch(text_size=9.0),
)

# Bottom ribbon
rectangle(
    (64, 4.8),
    width=122,
    height=6.0,
    style=Styles.Neutral.patch(shape_r=1.2),
    text="Declarative Schemas   •   Field Constraints (ge, le, max_length)   •   Rich Error Diagnostics",
    text_style=Styles.DarkBold.patch(text_size=9.5),
)

save()
```

```python
!pip install -q fastapi httpx pydantic
```

---

## 1. Defining Schemas with Pydantic `BaseModel`

To declare request bodies, inherit from Pydantic's `BaseModel`:

```python
from fastapi import FastAPI, status
from fastapi.testclient import TestClient
from pydantic import BaseModel, Field

app = FastAPI(title="Pydantic & Validation")

class ItemCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=50, description="Item Name")
    price: float = Field(..., gt=0, description="Price must be greater than 0")
    tax: float | None = Field(default=None, ge=0, description="Optional Tax")
    tags: list[str] = Field(default_factory=list, description="Item Tags")

@app.post("/items/", status_code=status.HTTP_201_CREATED)
def create_item(item: ItemCreate):
    total_price = item.price + (item.tax or 0)
    return {
        "message": "Item created successfully",
        "item": item.model_dump(),
        "total_price": total_price,
    }

client = TestClient(app)
```

---

## 2. Valid POST Requests

Valid payloads deserialize into typed `ItemCreate` instances:

```python
valid_payload = {
    "name": "Drawlib Notebook Pro",
    "price": 120.0,
    "tax": 12.0,
    "tags": ["python", "jupyter", "diagram"],
}

res_valid = client.post("/items/", json=valid_payload)
print("POST Valid ->", res_valid.status_code)
print("Response JSON ->", res_valid.json())
```

---

## 3. Automatic HTTP 422 Validation Diagnostics

Invalid payloads (e.g. negative prices or empty names) trigger automatic **HTTP 422 Unprocessable Entity** responses with exact field error details:

```python
invalid_payload = {
    "name": "",
    "price": -50.0,
}

res_invalid = client.post("/items/", json=invalid_payload)
print("POST Invalid ->", res_invalid.status_code)
for err in res_invalid.json()["detail"]:
    print(f"Field: {err['loc']} -> Error: {err['msg']}")
```

---

## Next Steps

In **Chapter 5 (Dependency Injection with Depends)**, we examine FastAPI's signature feature: reusable dependency trees for database sessions, authentication, and security policies!

