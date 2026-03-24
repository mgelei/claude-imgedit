---
name: image-edit
description: >
  Edit images using AI. When a user uploads one or more images and asks for
  visual changes (e.g. "remove the background", "make it look like a watercolor",
  "add a hat to the person", "apply the style from another uploaded image"), use
  this skill to apply the edits via the OpenAI image editing API and return the result.
compatibility: >
  Requires network egress to api.openai.com. Requires code execution enabled.
  User must provide an OpenAI API key.
---

# Image Edit Skill — Instructions

## 1. When to Use This Skill

Activate this skill when **both** of the following are true:

1. The user has uploaded or provided an image in the conversation.
2. The user asks for a visual edit, change, or modification to that image.

**Example trigger phrases:**

- "Remove the background from this image"
- "Make this photo look like a watercolor painting"
- "Add sunglasses to the person in this picture"
- "Change the sky to a sunset"
- "Make the colors more vibrant"
- "Turn this into a pencil sketch"
- "Remove the text from this image"
- "Replace the car with a bicycle"
- "Crop out the person on the left"
- "Make it look like it was taken at night"
- "Convert this photo to a drawing, use the other image as style reference"
- "Apply the outfit from this selfie to the portrait"
- "Use the color palette from the other image when editing my photo"

If the user uploads an image but only asks a question about it (e.g., "What's in this image?"), do **not** activate this skill — that is an image understanding task, not an edit.

---

## 2. Prerequisites

Before running the edit for the first time in a session, complete these setup steps:

### Install Dependencies

Check whether `openai` is already available:

```bash
python -c "import openai" >/dev/null 2>&1 && echo "OPENAI_INSTALLED" || echo "OPENAI_MISSING"
```

If the output is `OPENAI_MISSING`, install dependencies with:

```bash
pip install openai --break-system-packages -q
```

Run this at most once per session. Use this exact `pip` command for sandbox setup; do not try `uv` first.

### Obtain the OpenAI API Key

> ⚠️ **Security — follow strictly:** Never print, echo, or display the API key value at any point. Do **not** run `cat .env`. Do **not** echo or log `$OPENAI_API_KEY`. Never include the key value in any message or output shown to the user.

The edit script reads the key automatically — first from the `OPENAI_API_KEY` environment variable, then from a `.env` file at the skill root. You only need to verify a key source exists before proceeding.

Check in this order:

1. **Environment variable:** Test whether `OPENAI_API_KEY` is set — without printing its value:

   ```bash
   if [ -n "$OPENAI_API_KEY" ]; then echo "KEY_IN_ENV"; else echo "NO_ENV_KEY"; fi
   ```

2. **`.env` file:** If no env var, check whether a `.env` file at the skill root contains the key — without reading the file:

   ```bash
   grep -q "^OPENAI_API_KEY=" .env 2>/dev/null && echo "KEY_IN_FILE" || echo "NO_FILE_KEY"
   ```

3. **Ask the user:** If neither check passes, ask the user:
   > "I need an OpenAI API key to perform image edits. Please provide your key, and I'll save it for future use."

   Once the user provides the key, write it to a `.env` file at the skill root using Python (to avoid the key appearing as a shell argument):

   ```bash
   python -c "
   import sys, pathlib
   key = sys.argv[1]
   pathlib.Path('.env').write_text(f'OPENAI_API_KEY={key}\n')
   print('Key saved to .env')
   " "USER_PROVIDED_KEY"
   ```

   Replace `USER_PROVIDED_KEY` with the key the user gave you. Do **not** echo or confirm the key value in any message after saving it.

> **Tip:** For convenience in private use, you can include a `.env` file with your API key inside the uploaded skill zip. This way the key is available automatically. **Never share a skill zip that contains your API key.**

---

## 3. Step-by-Step Procedure

### Step 1: Save the Uploaded Image(s)

Extract all user-uploaded images from the conversation context and save them to the VM filesystem.

```bash
# Single image
cp <source> /tmp/input_image.png

# Multiple images — save each with a numbered name
cp <source1> /tmp/input_image_1.png
cp <source2> /tmp/input_image_2.png
```

Use an appropriate method to write image bytes to disk. Preserve the original file extension when possible.

**When multiple images are uploaded:** save each uploaded image and pass all of them to the script. Do **not** infer which image is the target, do **not** assign reference roles, and do **not** rely on image order to carry meaning. The API model resolves image roles from the user's prompt.

### Step 2: Validate the Image

Before proceeding, verify:

- **File exists:** Confirm the file was written successfully.
- **Format:** The image must be **PNG**, **JPEG**, or **WebP**. Check the file extension and/or MIME type.
- **Size:** The file must be under **50 MB**. Check with:

```bash
ls -la /tmp/input_image.png
```

If validation fails, inform the user of the specific issue and stop.

### Step 3: Construct the Edit Command

The edit script is located at `scripts/edit_image.py` relative to the skill root directory.

**Required arguments:**

| Argument          | Description                                                                              |
|-------------------|------------------------------------------------------------------------------------------|
| `--image-paths`   | Path(s) to the saved image file(s). Pass one or more uploaded images. Up to 16 total.   |
| `--prompt`        | The user's edit instruction (properly quoted)                                            |
| `--output-path`   | Where to save the edited result                                                          |

**Prompt handling:** Use the user's edit request as the prompt. Preserve their wording except for the minimal quoting needed to run the shell command safely. Do **not** rewrite the request with ordinal labels, numbered image labels, or target/reference labels.

**Optional arguments:**

| Argument    | Default           | Options                                        |
|-------------|-------------------|------------------------------------------------|
| `--model`   | `gpt-image-1.5`  | Model name to use for the edit                  |
| `--size`    | `auto`            | `auto`, `1024x1024`, `1536x1024`, `1024x1536`  |
| `--quality` | `auto`            | `auto`, `low`, `medium`, `high`                 |

> **Important:** Do **not** pass `--model` unless the user explicitly asks to use a specific model. Omit the argument entirely so the script's default (`gpt-image-1.5`) is used.

### Step 4: Run the Edit Script

> ⚠️ **Security:** Do **not** prefix the command with `OPENAI_API_KEY=...` — the script reads the key from the environment or `.env` file automatically. Never echo or print `$OPENAI_API_KEY` at any point.

Execute the script directly:

```bash
python scripts/edit_image.py \
  --image-paths /tmp/input_image.png \
  --prompt "remove the background and replace it with a gradient" \
  --output-path /tmp/edited_image.png
```

With multiple images:

```bash
python scripts/edit_image.py \
  --image-paths /tmp/input_image_1.png /tmp/input_image_2.png \
  --prompt "Apply the outfit from the selfie to the photo of the woman with glasses" \
  --output-path /tmp/edited_image.png
```

With optional parameters:

```bash
python scripts/edit_image.py \
  --image-paths /tmp/input_image.png \
  --prompt "make it look like a watercolor painting" \
  --output-path /tmp/edited_image.png \
  --size 1024x1024 \
  --quality high
```

Wait for the script to complete. It may take 10–30 seconds depending on the image and the complexity of the edit.

### Step 5: Parse the Output

The script writes JSON to **stdout**. Parse the output and check the `status` field.

**Success response:**

```json
{
  "status": "success",
  "output_path": "/tmp/edited_image.png",
  "model_used": "gpt-image-1.5",
  "file_size_bytes": 123456
}
```

**Error response:**

```json
{
  "status": "error",
  "error": "Rate limit exceeded after retries",
  "error_code": "RATE_LIMITED",
  "retryable": true
}
```

### Step 6: Display the Result (on success)

If `status` is `"success"`:

1. Read the image file at the `output_path`.
2. Display it inline to the user in the conversation.
3. Briefly describe what was changed (e.g., "Here's your image with the background removed.").

### Step 7: Handle Errors (on failure)

If `status` is `"error"`, follow the error handling guidance in the next section.

---

## 4. Error Handling

When the script returns an error, interpret the `error_code` and respond helpfully:

| Error Code          | HTTP Status | Action                                                                                           |
|---------------------|-------------|--------------------------------------------------------------------------------------------------|
| `INVALID_API_KEY`   | 401         | Tell the user their API key is invalid or expired. Ask them to provide a new key.                |
| `RATE_LIMITED`      | 429         | Tell the user the API is rate-limited. Suggest waiting 30–60 seconds and retrying.               |
| `CONTENT_POLICY`    | —           | Tell the user the edit was rejected by content safety filters. Suggest rephrasing the prompt.     |
| `FILE_TOO_LARGE`    | —           | Tell the user the image exceeds the 50 MB limit. Suggest compressing or resizing before retrying.|
| `UNSUPPORTED_FORMAT`| —           | Tell the user the format is not supported. Supported formats: **PNG**, **JPEG**, **WebP**.        |
| `API_ERROR`         | varies      | Show the error message from the response. Suggest retrying.                                      |
| `TIMEOUT`           | —           | Tell the user the API call timed out. Suggest retrying — the servers may be under heavy load.     |

**Automatic retry logic:**

If the error JSON includes `"retryable": true`, offer to retry automatically:

> "The request failed but is retryable. Would you like me to try again?"

If the user agrees (or in non-interactive contexts), retry the same command up to **2 additional times** with a short delay between attempts.

---

## 5. Follow-Up Actions

After successfully presenting the edited image, offer the user these options:

- **Iterate on the edit:** Ask if they want further changes. If yes, use the **output image** as the new input for the next edit (chain edits together).
- **Adjust settings:** Offer to re-run with different `--quality` or `--size` settings if the result isn't quite right.
- **Download:** Remind the user they can download the edited image from the displayed result.

Example follow-up message:

> "Here's the edited image! Let me know if you'd like any further changes — I can refine this result or try a different style. You can also download the image above."

---

## 6. Tips for Best Results

Share these tips with the user if they seem unsure about how to phrase their request:

- **Be specific:** "Add a red Santa hat tilted slightly to the right on the person's head" works better than "add a hat."
- **Use clear, descriptive language:** The model responds best to detailed, unambiguous instructions.
- **For partial edits:** Describe both what to change *and* what to preserve. For example: "Change the wall color to blue, but keep the furniture and decorations exactly the same."
- **For style transfers:** Reference well-known art styles by name — e.g., "in the style of Monet's water lilies," "as a Studio Ghibli animation frame," or "like a retro 1980s poster."
- **Quality setting:** Use `high` for final outputs and `low` or `medium` for quick drafts or iterations.
- **Size setting:** Use `auto` to preserve the original aspect ratio, or choose a specific size if you need exact dimensions.
- **Multiple images:** Keep the user's wording intact and pass the uploaded images through to the API. Do not add image numbers or role labels; the model resolves that from the prompt.

---

## 7. Reference

For detailed API documentation, advanced usage patterns, troubleshooting, and information about model capabilities, see:

📄 **`references/REFERENCE.md`**

Consult this file when you encounter unusual errors, need to understand API limits, or want to explore additional parameters not covered in this guide.
