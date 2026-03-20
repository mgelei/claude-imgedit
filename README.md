# claude-imgedit

A Claude skill that enables AI-powered image editing. Upload an image, describe the changes you want, and get back an edited image — all within a Claude conversation.

## What It Does

This skill connects Claude to OpenAI's `gpt-image-1.5` image editing API. When you upload an image and ask for visual changes, Claude orchestrates the edit and returns the result inline.

**Example edits:**
- "Remove the background"
- "Make it look like a watercolor painting"
- "Add sunglasses to the person"
- "Change the season to winter"
- "Convert to black and white"

## Prerequisites

- A [Claude Pro/Team](https://claude.ai) account with code execution enabled
- An [OpenAI API key](https://platform.openai.com/api-keys) with Images API access
- Network egress enabled in Claude Web (for `api.openai.com`)

## Setup

### Option A: Upload as a Skill (Recommended)

1. Download or clone this repository
2. (Optional) Create a `.env` file at the project root with your API key:
   ```
   OPENAI_API_KEY=sk-your-key-here
   ```
3. Zip the project folder:
   ```bash
   zip -r claude-imgedit.zip claude-imgedit/ -x "claude-imgedit/.git/*" "claude-imgedit/.claude/*" "claude-imgedit/PLAN.md"
   ```
4. Go to **Claude Web → Settings → Customize → Skills**
5. Upload `claude-imgedit.zip`

### Option B: Without Packaging a `.env`

1. Upload the skill zip **without** a `.env` file
2. When you first use the skill, Claude will ask for your OpenAI API key
3. Paste your key into the conversation — Claude will configure it for the session

> **Security note**: If you include a `.env` file in the zip, it is for **personal use only**. Never share a zip containing your real API key. The repository commits only `.env.example` as a template.

## Usage

Once the skill is installed, simply:

1. Upload an image to the Claude conversation
2. Describe the edit you want (e.g., "remove the background and make it transparent")
3. Wait for Claude to process the edit via the OpenAI API
4. View the edited image inline — download it or request further edits

### Supported Formats

| Format | Status |
|--------|--------|
| PNG    | ✅ Supported |
| JPEG   | ✅ Supported |
| WebP   | ✅ Supported |

**Max file size**: 50 MB per image

### Available Parameters

Claude will use sensible defaults, but you can request specific settings:

- **Model**: `gpt-image-1.5` (default), `gpt-image-1`
- **Quality**: `auto` (default), `low`, `medium`, `high`
- **Size**: `auto` (default), `1024x1024`, `1536x1024`, `1024x1536`

## Project Structure

```
claude-imgedit/
├── SKILL.md                  # Skill instructions for Claude
├── scripts/
│   └── edit_image.py         # Core Python script for OpenAI API calls
├── references/
│   └── REFERENCE.md          # Detailed API docs & troubleshooting
├── assets/
│   └── example_prompts.md    # Example edit prompts & expected results
├── .env.example              # API key template (copy to .env)
├── README.md                 # This file
└── LICENSE
```

## How It Works

1. Claude reads `SKILL.md` when the skill activates
2. The uploaded image is saved to the VM filesystem
3. Claude runs `scripts/edit_image.py` with the image path and edit prompt
4. The script calls the OpenAI Images Edit API
5. The edited image is saved and displayed in the conversation

## Troubleshooting

| Issue | Solution |
|-------|----------|
| "Invalid API key" | Check your key at [platform.openai.com](https://platform.openai.com/api-keys) |
| "Rate limited" | Wait a moment and retry; check your OpenAI usage limits |
| "Content policy violation" | Rephrase your edit prompt; some edits are filtered |
| "File too large" | Compress or resize your image (max 50 MB) |
| "Timeout" | Large/complex edits may take longer — retry the request |

For detailed troubleshooting, see [`references/REFERENCE.md`](references/REFERENCE.md).

## Development

```bash
# Clone the repo
git clone https://github.com/your-username/claude-imgedit.git
cd claude-imgedit

# Install dependencies (for local testing)
uv pip install openai --system --break-system-packages

# Test the script directly
export OPENAI_API_KEY="sk-your-key"
python scripts/edit_image.py \
  --image-path test_image.png \
  --prompt "make the sky more blue" \
  --output-path output.png
```

## License

See [LICENSE](LICENSE) for details.
