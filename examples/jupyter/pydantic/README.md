# Pydantic v2 Hands-On Cookbook (`type = "jupyter"`)

Bilingual (`en` / `ja`) interactive Jupyter & Google Colab notebook series covering **Pydantic v2** (`BaseModel` Lax vs. Strict coercion, `Field` constraints & `ValidationError`, `@field_validator` / `@model_validator` / `@computed_field`, and nested Discriminated Unions + JSON Schema), richly illustrated with **Drawlib** and verified in-process via `execute = true`.

## Notebook Chapters (`en/` & `ja/`)

1. `01_basemodel_quickstart.md` — `BaseModel` Essentials & Type Coercion (Lax vs. Strict)
2. `02_fields_and_errors.md` — `Field` Constraints & Inspecting `ValidationError`
3. `03_validators_and_computed.md` — Custom Validators (`@field_validator`, `@model_validator`) & `@computed_field`
4. `04_nested_unions_and_schema.md` — Nested Models, Discriminated Unions & JSON Schema

## Quick Commands

```bash
# Build .ipynb notebooks + HTML preview (with AI Dry-Run execution) into _build/jupyter/
./examples/jupyter/pydantic/build.sh

# Run AI Dry-Run verification only
uv run drawlib build jupyter examples/jupyter/pydantic/ --dry-run

# Preview locally in browser
./examples/jupyter/pydantic/serve.sh
```
