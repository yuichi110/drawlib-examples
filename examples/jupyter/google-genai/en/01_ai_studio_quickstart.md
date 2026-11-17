# 01. Hello World with Google AI Studio

This cookbook uses `[jupyter].setup_packages` in `drawlib.toml` to automatically prepend `!pip install -q google-genai` at the top of every generated notebook, ensuring fast startup in Google Colab with zero manual package installation. To run your first Gemini call safely without hardcoding credentials in Git, generate an API key (`GEMINI_API_KEY`) in **Google AI Studio**—backed by a **Google Cloud Project**—and store it in Google Colab's **Secrets** sidebar (`🔑` icon on the left pane with **Notebook access** toggled ON).

```drawlib align=center code=fold file=ch01_aistudio_workflow.png caption="Figure 1-1: End-to-End Google AI Studio & Colab Secrets Setup Workflow"
from drawlib.canvas import save, setup
from drawlib.icons import ai, gcp, phosphor
from drawlib.lines import line
from drawlib.shapes import rectangle
from drawlib.styles import Colors, Styles
from drawlib.text import text

setup(width=152, height=76, dpi=150)

# Outer calm frame (50%+ neutral baseline)
rectangle(
    (76.0, 38.0),
    width=142.0,
    height=66.0,
    style=Styles.Neutral.patch(shape_r=2.5, shape_fill_color=Colors.Light, shape_line_color=Colors.Gray3),
)

# Header title & subtitle
text(
    (76.0, 65.5),
    "Google AI Studio + Google Colab: End-to-End Quickstart Workflow",
    style=Styles.DarkBold.patch(text_size=12.8),
)
text(
    (76.0, 60.3),
    "Google Cloud Project Key  •  Colab Secrets Vault  •  Unified google-genai SDK",
    style=Styles.Muted.patch(text_size=10.2),
)

# 4 horizontal stage cards: width=28.0, gap=7.5 (x spans 8.75..143.25)
card_w = 28.0
card_h = 34.0
cy = 37.8
cxs = [22.75, 58.25, 93.75, 129.25]

neutral_card = Styles.White.patch(shape_r=2.2, shape_line_color=Colors.Gray4)
soft_card = Styles.PrimaryNeutral.patch(shape_r=2.2)
hero_card = Styles.PrimaryFlat.patch(shape_r=2.2)

# Stage 1: Google Cloud Project + AI Studio
rectangle((cxs[0], cy), width=card_w, height=card_h, style=neutral_card)
rectangle((cxs[0], 50.2), width=14.0, height=4.4, style=Styles.SecondaryNeutral.patch(shape_r=1.2, shape_line_width=0))
text((cxs[0], 50.2), "STEP 1", style=Styles.DarkBold.patch(text_size=10.0))
rectangle((cxs[0], 41.5), width=9.2, height=9.2, style=Styles.PrimaryNeutral.patch(shape_r=2.0, shape_line_width=0))
gcp.project((cxs[0], 41.5), width=6.4, style=Styles.Primary)
text((cxs[0], 32.3), "AI Studio Key", style=Styles.DarkBold.patch(text_size=11.0))
text((cxs[0], 25.5), "Cloud Project\nGEMINI_API_KEY", style=Styles.Muted.patch(text_size=10.0))

# Stage 2: Colab Secrets Vault
rectangle((cxs[1], cy), width=card_w, height=card_h, style=neutral_card)
rectangle((cxs[1], 50.2), width=14.0, height=4.4, style=Styles.SecondaryNeutral.patch(shape_r=1.2, shape_line_width=0))
text((cxs[1], 50.2), "STEP 2", style=Styles.DarkBold.patch(text_size=10.0))
rectangle((cxs[1], 41.5), width=9.2, height=9.2, style=Styles.SecondaryNeutral.patch(shape_r=2.0, shape_line_width=0))
phosphor.key((cxs[1], 41.5), width=6.0, style=Styles.DarkBold)
text((cxs[1], 32.3), "Colab Secrets", style=Styles.DarkBold.patch(text_size=11.0))
text((cxs[1], 25.5), "Sidebar Key Icon\nNotebook Access ON", style=Styles.Muted.patch(text_size=10.0))

# Stage 3: Unified genai.Client (Focal Hero Card)
rectangle((cxs[2], cy), width=card_w, height=card_h, style=hero_card)
rectangle((cxs[2], 50.2), width=14.0, height=4.4, style=Styles.White.patch(shape_r=1.2, shape_line_width=0))
text((cxs[2], 50.2), "STEP 3", style=Styles.PrimaryBold.patch(text_size=10.0))
rectangle((cxs[2], 41.5), width=9.2, height=9.2, style=Styles.White.patch(shape_r=2.0, shape_line_width=0))
ai.gemini((cxs[2], 41.5), width=6.4, style=Styles.Primary)
text((cxs[2], 32.3), "genai.Client", style=Styles.WhiteBold.patch(text_size=11.2))
text((cxs[2], 25.5), "userdata.get(...)\napi_key=api_key", style=Styles.White.patch(text_size=10.0))

# Stage 4: Gemini 3.8 Flash Response & Usage Metadata
rectangle((cxs[3], cy), width=card_w, height=card_h, style=soft_card)
rectangle((cxs[3], 50.2), width=14.0, height=4.4, style=Styles.White.patch(shape_r=1.2, shape_line_color=Colors.Gray3))
text((cxs[3], 50.2), "STEP 4", style=Styles.PrimaryBold.patch(text_size=10.0))
rectangle((cxs[3], 41.5), width=9.2, height=9.2, style=Styles.White.patch(shape_r=2.0, shape_line_color=Colors.Gray3))
phosphor.sparkle((cxs[3], 41.5), width=6.0, style=Styles.PrimaryBold)
text((cxs[3], 32.3), "Flash Response", style=Styles.DarkBold.patch(text_size=11.0))
text((cxs[3], 25.5), "gemini-3.8-flash\ntext + usage_metadata", style=Styles.Dark.patch(text_size=10.0))

# Inter-stage orthogonal connectors (7.5-unit gap between card edges)
for idx in range(3):
    x_start = cxs[idx] + card_w / 2.0 + 0.6
    x_end = cxs[idx + 1] - card_w / 2.0 - 0.6
    line((x_start, cy), (x_end, cy), arrow_head="->", style=Styles.DarkBold)

# Bottom setup banner
rectangle(
    (76.0, 12.2),
    width=134.5,
    height=8.4,
    style=Styles.White.patch(shape_r=1.8, shape_line_color=Colors.Gray4),
)
phosphor.terminal_window((34.0, 12.2), width=4.6, style=Styles.PrimaryBold)
text(
    (80.0, 12.2),
    "Auto-Prepended Setup Cell:  !pip install -q google-genai   •   Zero Keys in Git",
    style=Styles.DarkBold.patch(text_size=10.2),
)

save()
```

## 1. Minimal Hello World (`userdata` + `genai.Client`)

Before running the code cell below in Google Colab, complete this one-time secret setup:

1. Open **Google AI Studio** (`aistudio.google.com/apikey`), click **Create API key**, and select an existing or new **Google Cloud Project**.
2. In Google Colab, click the **Secrets (`🔑`)** icon in the left sidebar, add a secret named `GEMINI_API_KEY`, paste your key value, and toggle **Notebook access** ON.
3. Define `MODEL = "gemini-3.8-flash"` at the top of the cell so you can easily customize the target model, then read `GEMINI_API_KEY` via `userdata.get(...)` and pass it to `genai.Client`:

```python
MODEL = "gemini-3.8-flash"

from google.colab import userdata
from google import genai

api_key = userdata.get("GEMINI_API_KEY")
client = genai.Client(api_key=api_key)

response = client.models.generate_content(
    model=MODEL,
    contents="Hello!",
)
print(response.text)
```

`genai.Client` is the single entry point across the entire `google-genai` SDK. Every `client.models.*` and `client.chats.*` call you learn in this chapter works identically whether you authenticate with an AI Studio API key or Google Cloud Vertex AI IAM credentials.

## 2. Google Cloud Project Linkage: Free Tier vs. Paid Tier

Every API key issued in Google AI Studio belongs to an underlying **Google Cloud Project**. If you already work with Google Cloud, you can select any existing project directly inside AI Studio's key creation dialog—allowing IAM owners and cloud administrators to govern API enablement (`generativelanguage.googleapis.com`), quota monitoring, and billing in one place:

- **Free Tier (Unbilled Project)**: When the selected Google Cloud Project has **no Cloud Billing account attached**, your API key runs on the Free Tier at zero cost. This is ideal for hackathons, classroom labs, and quick notebook experiments, with lower request/token rate quotas (RPM/TPM/RPD) and standard Free Tier terms where prompts and responses may be used to improve Google products.
- **Paid Tier (Cloud Billing Enabled)**: Enabling **Cloud Billing** on that exact same Google Cloud Project upgrades your `GEMINI_API_KEY` to Pay-as-You-Go token pricing. Paid Tier keys unlock higher production RPM/TPM quotas and **enterprise-grade data privacy**—your prompts and model outputs are **not** used to train Google models—with zero changes to your Python code.

```drawlib align=center code=fold file=ch01_billing_tiers.png caption="Figure 1-2: Google AI Studio Free Tier vs. Cloud Billing Paid Tier"
from drawlib.canvas import save, setup
from drawlib.icons import gcp, phosphor
from drawlib.lines import line
from drawlib.shapes import rectangle
from drawlib.smartarts import CardList, Panel
from drawlib.styles import Colors, Styles
from drawlib.text import text

setup(width=152, height=78, dpi=150)

# Top shared Google Cloud Project banner
rectangle(
    (76.0, 67.5),
    width=140.0,
    height=11.0,
    style=Styles.Neutral.patch(shape_r=2.0, shape_fill_color=Colors.Light, shape_line_color=Colors.Gray4),
)
gcp.project((14.5, 67.5), width=6.6, style=Styles.Primary)
text(
    (80.5, 69.8),
    "Same Google Cloud Project & Same GEMINI_API_KEY",
    style=Styles.DarkBold.patch(text_size=11.5),
)
text(
    (80.5, 65.0),
    "Link Cloud Billing to upgrade quotas and data privacy without changing a single line of SDK code",
    style=Styles.Muted.patch(text_size=10.0),
)

# Left Panel: Free Tier (100% Neutral styling)
left_panel = Panel(
    "Free Tier",
    "Unbilled Project",
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
free_cards.add("$0 Prototyping", "Unbilled Google Cloud Project", icon=phosphor.credit_card)
free_cards.add("Sandbox Rate Quotas", "Lower RPM / TPM limits for testing", icon=phosphor.chart_bar)
free_cards.add("Standard Free Terms", "Inputs/outputs may improve products", icon=phosphor.shield_check)
free_cards.draw(l_xy, width=l_w, height=l_h)

# Center upgrade connector (12.0-unit gap between panels)
line((71.2, 31.8), (80.8, 31.8), arrow_head="->", style=Styles.DarkBold)
text((76.0, 36.8), "Enable\nBilling", style=Styles.PrimaryBold.patch(text_size=10.0))

# Right Panel: Paid Tier (Focal PrimaryFlat header over calm neutral cards)
right_panel = Panel(
    "Paid Tier",
    "Cloud Billing Enabled",
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
paid_cards.add("Pay-as-You-Go Pricing", "Token usage billed to Cloud project", icon=phosphor.credit_card)
paid_cards.add("Higher RPM / TPM Quotas", "Scaled throughput for live apps", icon=phosphor.chart_bar)
paid_cards.add(
    "Enterprise Data Privacy",
    "Prompts NOT used to train models",
    icon=phosphor.shield_check,
    badge_style=Styles.PrimaryFlat,
    icon_style=Styles.WhiteBold,
)
paid_cards.draw(r_xy, width=r_w, height=r_h)

save()
```

## 3. `GenerateContentConfig` & Token Usage Metadata

To control model behavior and determinism, pass a `types.GenerateContentConfig` object (such as `system_instruction` and `temperature`) to `generate_content`. Every response also attaches `response.usage_metadata`, exposing exact token counts across your input prompt (`prompt_token_count`), internal reasoning (`thoughts_token_count`), and final answer (`candidates_token_count`):

```python
from google.genai import types

config = types.GenerateContentConfig(
    system_instruction="Answer in one short sentence.",
    temperature=0.2,
)

response = client.models.generate_content(
    model=MODEL,
    contents="What is Python?",
    config=config,
)
print(response.text)

usage = response.usage_metadata
print(f"Prompt tokens:     {usage.prompt_token_count or 0}")
print(f"Thoughts tokens:   {usage.thoughts_token_count or 0}")
print(f"Candidates tokens: {usage.candidates_token_count or 0}")
```

On `gemini-3.8-flash`, internal reasoning tokens are reported separately under `thoughts_token_count`, making it easy to monitor both prompt/output size and thinking overhead from a single `usage_metadata` object.

### Key Takeaways & Next Step

- **Zero-Friction Setup**: Auto-installing only `google-genai` and storing `GEMINI_API_KEY` in Colab Secrets keeps notebooks fast to launch, shareable, and safe to commit to Git across both Free and Paid Tiers.
- **Up Next in Chapter 02**: Learn how to switch `genai.Client` to **Google Cloud Vertex AI** (`vertexai=True`) using keyless IAM authentication while keeping 100% of your downstream `gemini-3.8-flash` code unchanged.
