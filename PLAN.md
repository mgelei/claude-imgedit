# PLAN: Claude Image Edit Skill

## Problem Statement

Build a Claude skill that enables image editing via a 3rd-party AI model API. The user uploads an image to a Claude conversation and provides a text prompt describing desired edits. The skill orchestrates a call to OpenAI's **`gpt-image-1.5`** image editing API, applies the requested changes, and renders the edited image back in the conversation for the user to view or download.

## Target Platform

- **Primary surface**: Claude Web (claude.ai) — uploaded via Settings > Customize > Skills as a .zip
- **v1 scope**: Claude Web only
- **Later adaptation**: Claude Code can be considered after Claude Web succeeds; Claude API is out of scope for v1 because this skill depends on external network access to call OpenAI
- **Runtime requirements**: Code execution and file creation must be enabled; network egress must be enabled (at minimum for `api.openai.com`)

## Skill Architecture

### Agent Skills directory structure

```
claude-imgedit/
├── SKILL.md                  # Required — metadata + instructions for Claude
├── scripts/
│   └── edit_image.py         # Core Python script for OpenAI API interaction
├── references/
│   └── REFERENCE.md          # Detailed API docs, supported formats, troubleshooting
├── assets/
│   └── example_prompts.md    # Example edit prompts and expected behaviors
└── README.md                 # Repo documentation (not part of the skill itself)
```

### SKILL.md Design

The `SKILL.md` frontmatter will include:

```yaml
---
name: image-edit
description: >
  Edit images using AI. When a user uploads an image and asks for visual
  changes (e.g. "remove the background", "make it look like a watercolor",
  "add a hat to the person"), use this skill to apply the edits via the
  OpenAI image editing API and return the result.
compatibility: >
  Requires network egress to api.openai.com. Requires code execution enabled.
  User must provide an OpenAI API key.
---
```

The markdown body will contain step-by-step instructions for Claude:

1. **Validate prerequisites** — check that the user has provided an OpenAI API key (ask if not)
2. **Extract the image** — save the user-uploaded image from the conversation to the VM filesystem
3. **Validate the image** — check format (PNG, JPEG, WebP) and file size constraints
4. **Run the edit script** — invoke `scripts/edit_image.py` with the image path, prompt, and API key
5. **Present the result** — display the edited image in the conversation response
6. **Offer follow-ups** — ask if the user wants further edits or to download the result

## Core Components

### 1. `SKILL.md` — Skill Instructions

The primary instructions file that Claude reads when the skill is activated. Contains:
- When to use the skill (trigger conditions)
- Step-by-step procedure for handling an image edit request
- How to ask for the API key if not provided
- How to handle the image from the conversation context
- Error recovery instructions
- How to present results

### 2. `scripts/edit_image.py` — API Integration Script

A self-contained Python script that:
- Accepts CLI arguments: `--image-path`, `--prompt`, `--output-path`, `--model`, `--size`, `--quality`
- Reads the source image from disk
- Calls the OpenAI Images Edit API (`POST /v1/images/edits`)
- Saves the edited image to the specified output path
- Prints a JSON result to stdout with: `{ "status", "output_path", "model_used", "error" }`
- Implements robust error handling (see Error Handling section)

**Key design decisions for the script:**
- **Primary dependency is the `openai` SDK** — use the official `openai` Python package; Pillow is optional for corrupt-image detection only
- **Dependency management with `uv`** — use `uv pip install` for fast, reliable package installation in the sandboxed VM
- **Credential source is not a CLI argument** — the script should read the OpenAI key from an environment variable or a local `.env` file loaded at runtime
- **Stateless** — no config files, no caching; all parameters passed via CLI args
- **Stdout for results, stderr for logs** — clean separation so Claude can parse the JSON result
- **Moderation handling** — the published guide documents `moderation`, but the current Python `images.edit()` surface used here does not expose it as a direct kwarg, so keep it in `extra_body` for edit calls
- **Response format is `b64_json`** — gpt-image-1.5 returns base64 by default; the script decodes and writes to the output path

### 3. `references/REFERENCE.md` — Extended Documentation

Loaded on-demand by Claude when troubleshooting or handling edge cases:
- OpenAI API rate limits and quotas
- Supported image formats and size constraints per model
- Common error codes and resolutions
- Model-specific capabilities and limitations of `gpt-image-1.5`

### 4. `assets/example_prompts.md` — Usage Examples

Example input/output pairs to help Claude understand what kinds of edits work well:
- Background removal
- Style transfer ("make it look like a watercolor painting")
- Object addition/removal
- Color adjustments
- Text overlay
- Compositing

## Data Flow

```
┌─────────────────────────────────────────────────────────────┐
│  Claude Web Conversation                                     │
│                                                              │
│  1. User uploads image + types edit prompt                   │
│     ↓                                                        │
│  2. Claude activates skill, reads SKILL.md                   │
│     ↓                                                        │
│  3. Claude checks for API key (asks user if missing)         │
│     ↓                                                        │
│  4. Claude saves uploaded image to VM filesystem              │
│     ↓                                                        │
│  5. Claude runs: python scripts/edit_image.py                │
│     --image-path /tmp/input.png                              │
│     --prompt "user's edit instruction"                       │
│     --output-path /tmp/output.png                            │
│     ↓                                                        │
│  6. Script calls OpenAI API (requires network egress)        │
│     POST https://api.openai.com/v1/images/edits              │
│     ↓                                                        │
│  7. Script saves result to /tmp/output.png                   │
│     ↓                                                        │
│  8. Claude reads the output image and renders it             │
│     in the conversation response                             │
│     ↓                                                        │
│  9. User sees edited image, can download or request          │
│     further edits                                            │
└─────────────────────────────────────────────────────────────┘
```

## API Integration Design

### OpenAI Images Edit API

- **Endpoint**: `POST https://api.openai.com/v1/images/edits`
- **Model**: `gpt-image-1.5` (default; also supported: `gpt-image-1`, `gpt-image-1-mini`, `chatgpt-image-latest`)
- **Input parameters**:
  - `image`: Source image file (PNG, JPEG, or WebP; max 50 MB; up to 16 images)
  - `prompt`: Text description of the desired edit (max 32,000 chars)
  - `model`: Model identifier (default: `gpt-image-1.5`)
  - `mask`: Optional PNG mask; transparent areas mark edit regions (<4 MB, same dims as input)
  - `size`: Output size — `"1024x1024"`, `"1536x1024"`, `"1024x1536"`, or `"auto"`
  - `quality`: `"low"`, `"medium"`, `"high"`, `"auto"` (default: `"auto"`)
  - `output_format`: `"png"` (default), `"jpeg"`, or `"webp"`
  - `background`: `"transparent"`, `"opaque"`, or `"auto"` (transparent only works with png/webp output)
  - `input_fidelity`: `"high"` or `"low"` (default: `"low"`) — controls how closely the output matches input
  - `output_compression`: 0–100 (only applies to jpeg/webp output)
  - `n`: Number of images to generate (1–10)
  - `moderation`: `"auto"` (default) or `"low"` — see Moderation section
  - `response_format`: `"b64_json"` (default for gpt-image models) or `"url"`
- **Response**: Base64-encoded image data (`b64_json`) by default for gpt-image-1.5
- **Authentication**: Bearer token via `Authorization` header

### Image Format Handling

PNG, JPEG, and WebP are all **natively supported** by `gpt-image-1.5` — no format conversion or Pillow normalization is required.

| Input Format | v1 Status |
|---|---|
| PNG | Natively supported |
| JPEG | Natively supported |
| WebP | Natively supported |

Pillow is **not required** for format normalization. It may still be used for file validation (detecting corrupt images) but is not a required dependency.

### Moderation

The API accepts a `moderation` parameter to control content filtering:
- `"auto"` — default, standard content filtering
- `"low"` — less restrictive filtering (use this as the default in the skill)

**Python SDK caveat**: The published guide documents `moderation`, but the current Python `images.edit()` surface used here does not expose it as a direct keyword argument. For this repo's edit flow, pass it via `extra_body`:

```python
client.images.edit(
    model="gpt-image-1.5",
    image=open("image.png", "rb"),
    prompt="your prompt",
    extra_body={"moderation": "low"}
)
```

In raw HTTP, `moderation` is still just a standard body field. The `extra_body` approach here is a Python-SDK-specific implementation detail.

### Model Abstraction

The script uses `gpt-image-1.5` and accepts a `--model` argument for forward compatibility with future models. This allows:
- Using `gpt-image-1.5` out of the box
- Upgrading to newer models in the future without code changes
- Users can request a specific model in conversation

## Error Handling Strategy

### Input Validation (before API call)
- **File not found**: Clear error message with the attempted path
- **Unsupported format**: List supported formats (PNG, JPEG, WebP)
- **File too large**: Report the 50 MB limit and suggest compression
- **Empty/corrupt image**: Attempt to open with Pillow; report if it fails

### API Errors (during API call)
- **401 Unauthorized**: Invalid API key — instruct Claude to ask user to re-enter
- **429 Rate Limited**: Retry with exponential backoff (max 3 retries, delays: 2s, 4s, 8s)
- **400 Bad Request**: Parse error message, report content policy violations clearly
- **500/502/503 Server Error**: Retry with exponential backoff (max 2 retries)
- **Timeout**: 120-second timeout per request; report timeout and suggest retry

### Output Validation (after API call)
- Verify the response contains valid image data
- Verify the output file was written successfully
- Report the output file size and dimensions

### Error Reporting Format
All errors returned as JSON to stdout:
```json
{
  "status": "error",
  "error": "Human-readable error message",
  "error_code": "RATE_LIMITED",
  "retryable": true
}
```

The SKILL.md will instruct Claude on how to interpret these errors and communicate them helpfully to the user.

## Security Considerations

### API Key Handling
- **Never hardcode** API keys in the skill files
- **Never log** API keys to stdout/stderr
- **Do not pass the API key as a CLI argument**
- On Claude Web, users may either paste the key into the conversation for that session or include a personal-use `.env` file in their uploaded skill package
- Commit only `.env.example` to the repository; never commit a real `.env`
- A real `.env` is allowed only in a personal uploaded zip and must never be committed to the repo
- The SKILL.md should explain that a packaged `.env` is for private personal use only and should not be shared
- Claude Web sessions are ephemeral, so pasted credentials may need to be supplied again in later sessions

### Content Safety
- The OpenAI API enforces its own content policies; the script should surface content policy rejections clearly to the user
- The SKILL.md should instruct Claude to not circumvent or help users circumvent content safety filters

### Network Security
- All API calls use HTTPS
- The script should verify SSL certificates (default behavior of the `openai` SDK)

## Prerequisites & Dependencies

### User Prerequisites
- An OpenAI API account with access to the Images API
- A valid OpenAI API key
- Claude Web with code execution and network egress enabled

### Python Dependencies
- `openai` — Official OpenAI Python SDK for API interaction
- `Pillow` — Optional; only needed if corrupt-image validation is desired (not required for format normalization)
- Managed via `uv` (fast Python package manager)

### Dependency Installation
The SKILL.md will instruct Claude to install dependencies at skill activation:
```bash
uv pip install openai
```

If corrupt-image detection via Pillow is desired, add it:

```bash
uv pip install openai Pillow
```

## Resolved Decisions

The following questions from the original plan have been resolved via API research (March 2026):

1. **Input formats**: PNG, JPEG, and WebP are all natively supported by `gpt-image-1.5`. No conversion needed; Pillow is not required for format normalization.
2. **File size limit**: 50 MB per input image (confirmed).
3. **Response format**: `b64_json` is the default for gpt-image models. The script decodes base64 and saves to the output path.
4. **Output file handoff**: The script outputs a single PNG file at `--output-path`. Claude reads and renders it inline.
5. **Moderation**: Use `moderation: "low"` via `extra_body` for this repo's Python edit flow (see Moderation section).
6. **Pillow dependency**: Not required for v1. May be added optionally for corrupt-image detection.

## Remaining Decisions

1. Add packaging guidance for `.env.example`, personal-use `.env`, and zip layout.
2. Keep the initial implementation focused on Claude Web only.

## Implementation Todos

1. **Create SKILL.md** — Write the main skill file with frontmatter and step-by-step instructions for Claude
2. **Create `scripts/edit_image.py`** — Implement the core Python script for OpenAI API interaction with full error handling and retry logic
3. **Create `references/REFERENCE.md`** — Write extended documentation covering API details, format constraints, and troubleshooting
4. **Create `assets/example_prompts.md`** — Compile example edit prompts and describe expected behaviors
5. **Update `README.md`** — Write repository documentation with setup instructions, usage guide, `.env.example` packaging guidance, and contribution info
6. **Test on Claude Web** — Package as .zip and upload to Claude Web for manual testing
7. **Iterate on SKILL.md instructions** — Refine based on testing to improve Claude's reliability in executing the workflow
