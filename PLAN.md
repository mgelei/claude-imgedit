# PLAN: Claude Image Edit Skill

## Problem Statement

Build a Claude skill that enables image editing via a 3rd-party AI model API. The user uploads an image to a Claude conversation and provides a text prompt describing desired edits. The skill orchestrates a call to OpenAI's **`gpt-image-1.5`** image editing API, applies the requested changes, and renders the edited image back in the conversation for the user to view or download.

## Target Platform

- **Primary surface**: Claude Web (claude.ai) — uploaded via Settings > Customize > Skills as a .zip
- **Portability goal**: The skill follows the [Agent Skills open standard](https://agentskills.io/specification), making it compatible with Claude Code (`.claude/skills/`), the Claude API, and any other Agent Skills-compatible platform
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
- Accepts CLI arguments: `--image-path`, `--prompt`, `--api-key`, `--output-path`, `--model`, `--size`, `--quality`
- Reads the source image from disk
- Calls the OpenAI Images Edit API (`POST /v1/images/edits`)
- Saves the edited image to the specified output path
- Prints a JSON result to stdout with: `{ "status", "output_path", "model_used", "error" }`
- Implements robust error handling (see Error Handling section)

**Key design decisions for the script:**
- **No external dependencies beyond `openai` SDK** — use the official `openai` Python package; the script handles all HTTP/multipart complexity via the SDK
- **Dependency management with `uv`** — use `uv pip install` for fast, reliable package installation in the sandboxed VM
- **Dependencies declared in frontmatter** — the SKILL.md will declare `dependencies: openai` so Claude knows to install it
- **Stateless** — no config files, no caching; all parameters passed via CLI args
- **Stdout for results, stderr for logs** — clean separation so Claude can parse the JSON result

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
│     --api-key sk-...                                         │
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
- **Model**: `gpt-image-1.5`
- **Input parameters**:
  - `image`: The source image file (PNG recommended; JPEG/WebP converted to PNG first)
  - `prompt`: Text description of the desired edit
  - `model`: Model identifier
  - `size`: Output size (e.g. `1024x1024`, `auto`)
  - `quality`: Output quality (e.g. `auto`, `high`)
- **Response**: Base64-encoded image data or URL
- **Authentication**: Bearer token via `Authorization` header

### Image Format Handling

| Input Format | Handling |
|---|---|
| PNG | Pass directly to API |
| JPEG | Convert to PNG before API call (using Pillow) |
| WebP | Convert to PNG before API call (using Pillow) |

### Model Abstraction

The script uses `gpt-image-1.5` and accepts a `--model` argument for forward compatibility with future models. This allows:
- Using `gpt-image-1.5` out of the box
- Upgrading to newer models in the future without code changes
- Users can request a specific model in conversation

## Error Handling Strategy

### Input Validation (before API call)
- **File not found**: Clear error message with the attempted path
- **Unsupported format**: List supported formats and suggest conversion
- **File too large**: Report size limit and suggest compression (OpenAI limit: ~25MB for edits)
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
- API key is passed as a CLI argument and only lives in the VM's process memory
- The SKILL.md instructs Claude to ask the user for their API key at the start of the conversation
- On Claude Web, the VM is ephemeral — the key is not persisted between sessions
- On Claude Code, the SKILL.md should also support reading from a `.env` file or environment variable as an alternative

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
- `Pillow` — Image format conversion (JPEG/WebP → PNG) and validation
- Managed via `uv` (fast Python package manager)

### Dependency Installation
The SKILL.md will instruct Claude to install dependencies at skill activation:
```bash
uv pip install openai Pillow
```

## Cross-Platform Considerations

| Aspect | Claude Web | Claude Code |
|---|---|---|
| Image input | User uploads to conversation | File path on disk |
| API key source | User provides in conversation | `.env` file or env var |
| Image output | Rendered in conversation response | Saved to disk, path reported |
| Network access | Requires "Allow network egress" | Always available |
| Package install | `uv pip install` in sandbox | `uv pip install` locally |

The SKILL.md should contain conditional instructions so Claude adapts its behavior based on the platform it's running on.

## Implementation Todos

1. **Create SKILL.md** — Write the main skill file with frontmatter and step-by-step instructions for Claude
2. **Create `scripts/edit_image.py`** — Implement the core Python script for OpenAI API interaction with full error handling and retry logic
3. **Create `references/REFERENCE.md`** — Write extended documentation covering API details, format constraints, and troubleshooting
4. **Create `assets/example_prompts.md`** — Compile example edit prompts and describe expected behaviors
5. **Update `README.md`** — Write repository documentation with setup instructions, usage guide, and contribution info
6. **Test on Claude Web** — Package as .zip and upload to Claude Web for manual testing
7. **Test on Claude Code** — Install as a project skill and test end-to-end
8. **Iterate on SKILL.md instructions** — Refine based on testing to improve Claude's reliability in executing the workflow

## Open Questions / Future Considerations

- **Mask support**: The OpenAI API supports an optional mask parameter for targeted edits. Could be added as a future enhancement where the user describes what area to edit and Claude generates a mask.
- **Multiple output options**: Support generating multiple variations and letting the user pick.
- **Image generation (not just editing)**: The scope is currently edit-only, but the same script architecture could support generation from scratch.
- **Provider abstraction**: If support for other providers (Stability AI, etc.) is desired in the future, the script could be refactored to use a provider interface pattern.
- **Cost awareness**: The SKILL.md could instruct Claude to warn users about API costs before making calls.
