# 02. Hello World with Vertex AI & Backend Selection

The core architectural advantage of the unified `google-genai` SDK is that **only the `genai.Client(...)` initialization differs** between Google AI Studio and Google Cloud Vertex AI. Every downstream SDK call—`client.models.generate_content`, streaming, `ThinkingConfig`, Pydantic structured outputs, multi-turn `client.chats`, and tool/function calling—is **100% identical** across both backends.

```drawlib align=center code=fold file=ch02_unified_sdk_arch.png caption="Figure 2-1: Unified google-genai SDK Architecture Across AI Studio and Vertex AI"
from drawlib.canvas import save, setup
from drawlib.diagrams.architecture import ArchitectureDiagram, GcpIcon, Node, NodeGroup, PhosphorIcon
from drawlib.styles import Styles

setup(width=152, height=76, dpi=150)

d = ArchitectureDiagram(
    node_style=Styles.PrimaryBold,
    node_text_style=Styles.DarkBold.patch(text_size=10.0),
    edge_style=Styles.DarkBold,
    edge_text_style=Styles.Dark.patch(text_size=10.0),
    node_card_style=Styles.Neutral,
)

# Left-Top: Path A — Google AI Studio
path_a = d.add(
    NodeGroup(
        title="Path A: Google AI Studio",
        width=58.0,
        height=30.0,
        style=Styles.PrimaryDashed.patch(shape_r=2.0),
        text_style=Styles.PrimaryBold.patch(text_size=10.2, halign="left"),
    ),
    xy=(0.0, 36.0),
)
ai_auth = path_a.add(
    Node(
        "API Key\napi_key=...",
        width=20.0,
        height=18.0,
        icon=PhosphorIcon.KEY,
        icon_size=5.8,
        card_style=Styles.Neutral,
    ),
    xy=(12.5, 11.5),
)
ai_ep = path_a.add(
    Node(
        "AI Studio API\ngenerativelanguage\n.googleapis.com",
        width=26.5,
        height=18.0,
        icon=PhosphorIcon.SPARKLE,
        icon_size=5.8,
        card_style=Styles.PrimaryNeutral,
    ),
    xy=(42.25, 11.5),
)
d.connect(ai_auth, ai_ep, routing="direct")

# Left-Bottom: Path B — Google Cloud Vertex AI
path_b = d.add(
    NodeGroup(
        title="Path B: Vertex AI (GCP Project / VPC-SC)",
        width=58.0,
        height=31.0,
        style=Styles.PrimaryDashed.patch(shape_r=2.0),
        text_style=Styles.DarkBold.patch(text_size=10.2, halign="left"),
    ),
    xy=(0.0, 0.0),
)
vx_auth = path_b.add(
    Node(
        "IAM / ADC\nvertexai=True",
        width=20.0,
        height=18.5,
        icon=GcpIcon.IDENTITY_AND_ACCESS_MANAGEMENT,
        icon_size=5.8,
        card_style=Styles.Neutral,
    ),
    xy=(12.5, 12.0),
)
vx_ep = path_b.add(
    Node(
        "Vertex AI API\naiplatform\n.googleapis.com",
        width=26.5,
        height=18.5,
        icon=GcpIcon.VERTEX_AI,
        icon_size=5.8,
        card_style=Styles.PrimaryNeutral,
    ),
    xy=(42.25, 12.0),
)
d.connect(vx_auth, vx_ep, routing="direct")

# Center Focal Hub: Unified genai.Client
hub = d.add(
    Node(
        "genai.Client\nUnified SDK\nInterface",
        width=27.0,
        height=25.0,
        icon=PhosphorIcon.PLUGS_CONNECTED,
        icon_size=6.8,
        style=Styles.WhiteBold,
        card_style=Styles.PrimaryFlat,
        text_style=Styles.WhiteBold.patch(text_size=10.6),
    ),
    xy=(85.5, 33.0),
)

merge = d.junction((65.0, 33.0))
d.connect(ai_ep, merge, arrow="-", routing="orthogonal").via((65.0, 47.5))
d.connect(vx_ep, merge, arrow="-", routing="orthogonal").via((65.0, 12.0))
d.connect(merge, hub, routing="direct")

# Right: 100% Identical Downstream Calls
sdk_calls = d.add(
    NodeGroup(
        title="100% Identical Calls",
        width=30.0,
        height=66.0,
        style=Styles.MutedDashed.patch(shape_r=2.0),
        text_style=Styles.DarkBold.patch(text_size=10.2, halign="left"),
    ),
    xy=(112.0, 0.0),
)
models_node = sdk_calls.add(
    Node(
        "client.models.*\ngenerate_content\nStream / Schema",
        width=25.5,
        height=22.0,
        icon=PhosphorIcon.LIGHTNING,
        icon_size=6.0,
        card_style=Styles.Neutral,
    ),
    xy=(15.0, 44.5),
)
chats_node = sdk_calls.add(
    Node(
        "client.chats.*\nMulti-turn Chat &\nFunction Calling",
        width=25.5,
        height=22.0,
        icon=PhosphorIcon.CHAT_CIRCLE_TEXT,
        icon_size=6.0,
        card_style=Styles.PrimaryNeutral,
    ),
    xy=(15.0, 15.5),
)
fork_pt = d.junction((106.5, 33.0))
d.connect(hub, fork_pt, arrow="-", routing="direct")
d.connect(fork_pt, models_node, routing="orthogonal").via((106.5, 44.5))
d.connect(fork_pt, chats_node, routing="orthogonal").via((106.5, 15.5))

d.draw(xy=(5.0, 5.0))
save()
```

---

## 1. Minimal Hello World on Vertex AI (Keyless IAM Auth in Colab)

When targeting Google Cloud Vertex AI, you do not need to generate or distribute static API keys. Inside Google Colab, `auth.authenticate_user()` opens a browser sign-in prompt to establish short-lived Application Default Credentials (ADC) backed by Google Cloud IAM. Ensure the Vertex AI API (`aiplatform.googleapis.com`) is enabled on your project and your Google account has the **Vertex AI User** (`roles/aiplatform.user`) role.

```python
from google.colab import auth
from google import genai

# Authenticate with your Google account in the browser popup
auth.authenticate_user()

client = genai.Client(
    vertexai=True,
    project="your-gcp-project-id",  # Replace with your Google Cloud Project ID
    location="us-central1",         # Or "asia-northeast1", "global", etc.
)

response = client.models.generate_content(
    model="gemini-2.5-flash",
    contents="Hello from Vertex AI! List three advantages of keyless IAM authentication in two sentences.",
)
print(response.text)
```

### Keeping Your Project ID Out of Shared Notebooks

When committing notebooks to Git or sharing them with teammates, avoid hardcoding your Google Cloud Project ID in source cells. Store `GOOGLE_CLOUD_PROJECT` in **Colab Secrets** (the key icon in the left sidebar, with **Notebook access** toggled on) and read it dynamically with `userdata.get("GOOGLE_CLOUD_PROJECT")`:

```python
from google.colab import auth, userdata
from google import genai

auth.authenticate_user()

# Load GOOGLE_CLOUD_PROJECT securely from Colab Secrets
client = genai.Client(
    vertexai=True,
    project=userdata.get("GOOGLE_CLOUD_PROJECT"),
    location="asia-northeast1",
)

response = client.models.generate_content(
    model="gemini-2.5-flash",
    contents="Confirm that Vertex AI initialized cleanly using Colab Secrets.",
)
print(response.text)
```

> **Regional Endpoints vs. `location="global"`:**
> Use a **regional endpoint** such as `"us-central1"` (Iowa) or `"asia-northeast1"` (Tokyo) when your workload requires strict geographic data residency and predictable regional routing. Use **`location="global"`** when you want dynamic multi-region routing for maximum quota availability—or when testing **bleeding-edge Preview models** on Vertex AI that launch exclusively on the `global` endpoint before rolling out to individual regions.

---

## 2. Choosing Between Google AI Studio and Vertex AI

Because `google-genai` unifies both platforms behind one client interface, you can start prototyping in minutes with Google AI Studio and transition to Vertex AI whenever enterprise governance requires it—without rewriting a single model or chat call.

```drawlib align=center code=fold file=ch02_backend_comparison.png caption="Figure 2-2: Decision Matrix — Google AI Studio vs. Google Cloud Vertex AI"
from drawlib.canvas import save, setup
from drawlib.icons import phosphor
from drawlib.smartarts import Table
from drawlib.styles import Colors, Styles
from drawlib.text import text

setup(width=152, height=82, dpi=150)

# Title header with Phosphor icon
phosphor.scales((47.0, 75.5), width=5.0, style=Styles.PrimaryBold)
text(
    (79.5, 75.5),
    "Google AI Studio vs. Google Cloud Vertex AI",
    style=Styles.DarkBold.patch(text_size=12.5),
)

table = Table(
    cell_style=Styles.White,
    text_style=Styles.Dark.patch(text_size=10.2),
    header_cell_style=Styles.PrimaryFlat,
    header_text_style=Styles.WhiteBold.patch(text_size=11.0),
    border_style=Styles.MutedThin,
)

# 1. Neutral alternating rows
table.set_style_cell_evenodd(
    even_color=Colors.Light,
    even_text_style=Styles.Dark.patch(text_size=10.2),
    odd_color=Colors.White,
    odd_text_style=Styles.Dark.patch(text_size=10.2),
)

# 2. Bold neutral row headers in column 0
table.set_style_cell_rowheader(
    background_color=Colors.Neutral,
    text_style=Styles.DarkBold.patch(text_size=10.2),
)

# 3. Highlight 100% SDK compatibility row (row 6)
table.set_style_cell(
    background_color=Colors.PrimaryNeutral,
    text_style=Styles.PrimaryBold.patch(text_size=10.3),
    rows=[6],
    columns=[1, 2],
)

# 4. Re-apply focal header row style last so row 0 stays PrimaryFlat
table.set_style_cell_header(
    background_color=Colors.Primary,
    text_style=Styles.WhiteBold.patch(text_size=11.0),
)

table.set_style_border(
    top=Styles.Primary.patch(line_color=Colors.Primary, line_width=1.6),
    top2=Styles.Primary.patch(line_color=Colors.Primary, line_width=1.2),
    bottom=Styles.Primary.patch(line_color=Colors.Dark, line_width=1.4),
    left=Styles.Primary.patch(line_color=Colors.Muted, line_width=0.7),
    left2=Styles.Primary.patch(line_color=Colors.Muted, line_width=1.0),
    right=Styles.Primary.patch(line_color=Colors.Muted, line_width=0.7),
    between_columns=Styles.Primary.patch(line_color=Colors.Muted, line_width=0.7),
    between_rows=Styles.Primary.patch(line_color=Colors.Muted, line_width=0.7),
)

matrix_data = [
    ["Evaluation Axis", "Google AI Studio", "Google Cloud Vertex AI"],
    ["Authentication", "API Key (GEMINI_API_KEY)", "Keyless IAM / ADC & Service Accounts"],
    ["Billing Model", "Free Tier or GCP Project Pay-As-You-Go", "GCP Cloud Billing & Provisioned Quotas"],
    ["Regional Residency", "Global routing managed by Google", "Regional (us-central1, Tokyo) + global"],
    ["VPC-SC / CMEK", "Not supported (Public HTTPS API)", "Supported (VPC-SC, Private PSC, CMEK)"],
    ["Best Use Case", "Fast prototyping, notebooks & indie apps", "Enterprise production & IAM governance"],
    ["SDK Compatibility", "100% Identical (models.* / chats.*)", "100% Identical (models.* / chats.*)"],
]

table.draw_flexible(
    xy=(6.0, 69.5),
    column_widths=[34.0, 53.0, 53.0],
    row_heights=[9.5, 9.0, 9.0, 9.0, 9.0, 9.0, 9.0],
    data=matrix_data,
    align="top_left",
)

save()
```

### How Chapters 3 Through 5 Work

- **Concise Default Initialization in Chapters 3–5**: Because Google AI Studio API keys can be linked directly to a Google Cloud Project for billing and higher rate limits (as covered in Chapter 1), **Chapters 3 through 5 standardize on the concise 3-line AI Studio initialization** (`genai.Client(api_key=userdata.get("GEMINI_API_KEY"))`) so every notebook stays minimal and focused on core SDK capabilities.
- **Drop-In Compatibility for Vertex AI Users**: Every single code cell in Chapters 3–5—covering Streaming, `ThinkingConfig`, Multimodal Inputs, Pydantic Structured Outputs, Multi-turn Chat, and Function Calling—**runs unchanged on Vertex AI** simply by replacing that 3-line `client` initialization with this chapter's `vertexai=True` setup.
