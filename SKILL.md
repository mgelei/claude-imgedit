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

If the user uploads an image but only asks a question about it (e.g., "What's in this image?"), do **not** activate this skill — that is an image understanding task, not an edit.

---

## 2. Prerequisites

Before running the edit for the first time in a session, complete these setup steps:

### Install Dependencies

```bash
uv pip install openai
```

Run this once per session. If it has already been installed, skip this step.

### Obtain the OpenAI API Key

Check for the API key in this order:

1. **Environment variable:** Check if `OPENAI_API_KEY` is already set in the environment.
2. **`.env` file:** Look for a `.env` file at the skill root directory (the same directory as this `SKILL.md` file). If it exists, read the `OPENAI_API_KEY` value from it.
3. **Ask the user:** If neither source provides a key, ask the user:
   > "I need an OpenAI API key to perform image edits. Please provide your API key, and I'll store it for this session."

   Once the user provides the key, write it to a `.env` file at the skill root:

   ```
   OPENAI_API_KEY=sk-...
   ```

   Alternatively, export it in the shell environment:

   ```bash
   export OPENAI_API_KEY="sk-..."
   ```

> **Tip:** For convenience in private use, you can include a `.env` file with your API key inside the uploaded skill zip. This way the key is available automatically. **Never share a skill zip that contains your API key.**

---

## 3. Step-by-Step Procedure

### Step 1: Save the Uploaded Image

Extract the user-uploaded image from the conversation context and save it to the VM filesystem.

```bash
# Save to a temporary location
cp <source> /tmp/input_image.png
```

Use an appropriate method to write the image bytes to disk. Common paths:

- `/tmp/input_image.png`
- `/tmp/input_image.jpg`

Preserve the original file extension when possible.

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

| Argument         | Description                                      |
|------------------|--------------------------------------------------|
| `--image-path`   | Path to the saved input image                    |
| `--prompt`       | The user's edit instruction (properly quoted)     |
| `--output-path`  | Where to save the edited result                  |

**Optional arguments:**

| Argument    | Default           | Options                                        |
|-------------|-------------------|------------------------------------------------|
| `--model`   | `gpt-image-1.5`  | Model name to use for the edit                  |
| `--size`    | `auto`            | `auto`, `1024x1024`, `1536x1024`, `1024x1536`  |
| `--quality` | `auto`            | `auto`, `low`, `medium`, `high`                 |

> **Important:** Do **not** pass `--model` unless the user explicitly asks to use a specific model. Omit the argument entirely so the script's default (`gpt-image-1.5`) is used.

### Step 4: Run the Edit Script

Set the `OPENAI_API_KEY` environment variable and execute the script:

```bash
OPENAI_API_KEY="$KEY" python scripts/edit_image.py \
  --image-path /tmp/input_image.png \
  --prompt "remove the background and replace it with a gradient" \
  --output-path /tmp/edited_image.png
```

With optional parameters:

```bash
OPENAI_API_KEY="$KEY" python scripts/edit_image.py \
  --image-path /tmp/input_image.png \
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

---

## 7. Reference

For detailed API documentation, advanced usage patterns, troubleshooting, and information about model capabilities, see:

📄 **`references/REFERENCE.md`**

Consult this file when you encounter unusual errors, need to understand API limits, or want to explore additional parameters not covered in this guide.
