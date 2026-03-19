# Claude Image Edit Skill — Extended Reference

## 1. OpenAI Images Edit API Reference

### Endpoint

```
POST https://api.openai.com/v1/images/edits
```

### Authentication

```
Authorization: Bearer <OPENAI_API_KEY>
```

The request body must be sent as `multipart/form-data` (required for file uploads).

### Parameters

| Parameter | Type | Required | Description |
|---|---|---|---|
| `image` | file | **Yes** | Source image to edit. Accepts PNG, JPEG, or WebP. Max 50 MB. |
| `prompt` | string | **Yes** | A text description of the desired edit. Max 32,000 characters. |
| `model` | string | No | Model to use. One of `gpt-image-1.5` (default), `gpt-image-1`, `gpt-image-1-mini`, `chatgpt-image-latest`. |
| `mask` | file | No | PNG image used as a mask. Transparent (alpha = 0) areas indicate where the image should be edited. Must be less than 4 MB and have the same dimensions as the input image. |
| `size` | string | No | Output size. One of `1024x1024`, `1536x1024` (landscape), `1024x1536` (portrait), or `auto` (default). |
| `quality` | string | No | Output quality. One of `low`, `medium`, `high`, or `auto` (default). |
| `output_format` | string | No | Output image format. One of `png` (default), `jpeg`, `webp`. |
| `background` | string | No | Background handling. One of `transparent`, `opaque`, or `auto`. Transparent backgrounds only work with `png` or `webp` output formats. |
| `input_fidelity` | string | No | How closely the output should match the input image. `high` preserves more of the original; `low` (default) gives the model more creative freedom. |
| `output_compression` | integer | No | Compression level, 0–100. Only applies to `jpeg` and `webp` output formats. Lower values = smaller files but lower quality. |
| `n` | integer | No | Number of images to generate. Range: 1–10. Default: 1. |
| `moderation` | string | No | Content moderation level. `auto` (default) applies standard filtering. `low` reduces filtering sensitivity. |
| `response_format` | string | No | Format of the returned image data. `b64_json` (default for gpt-image models) returns base64-encoded image data. `url` returns a temporary URL. |

### Response Structure

```json
{
  "created": 1234567890,
  "data": [
    {
      "b64_json": "<base64-encoded-image-data>",
      "revised_prompt": "The prompt as interpreted by the model"
    }
  ]
}
```

When `response_format` is `url`:

```json
{
  "created": 1234567890,
  "data": [
    {
      "url": "https://...",
      "revised_prompt": "The prompt as interpreted by the model"
    }
  ]
}
```

---

## 2. Supported Image Formats

| Format | MIME Type | Supported as Input | Supported as Output | Notes |
|---|---|---|---|---|
| PNG | `image/png` | ✅ | ✅ | Supports transparency. Required format for mask files. |
| JPEG | `image/jpeg` | ✅ | ✅ | No transparency support. Good for photographs. |
| WebP | `image/webp` | ✅ | ✅ | Supports transparency. Good compression. |

- **No conversion needed** — all three formats are natively accepted by the API as input.
- **Size limit**: 50 MB per image (input).
- **Mask constraint**: Must be PNG, under 4 MB, and exactly match the input image dimensions.

---

## 3. Model Capabilities

### `gpt-image-1.5` (Default)

The latest and most capable model. Best quality output with the widest parameter support.

- Supports all parameters listed above
- Best at following complex edit instructions
- Highest fidelity output
- Recommended for production use

### `gpt-image-1`

Previous-generation model. Still reliable but may produce lower-quality results for complex edits.

- Supports core parameters
- Good for simpler edits
- Faster in some cases

### `gpt-image-1-mini`

Lightweight variant optimized for speed and cost.

- Lower quality than full models
- Faster response times
- Lower cost per image

### `chatgpt-image-latest`

Tracks the model currently used in the ChatGPT product.

- May change without notice as ChatGPT updates
- Not recommended for stable production pipelines

### Comparison

| Feature | gpt-image-1.5 | gpt-image-1 | gpt-image-1-mini | chatgpt-image-latest |
|---|---|---|---|---|
| Quality | Best | Good | Adequate | Varies |
| Speed | Standard | Standard | Faster | Varies |
| Cost | Higher | Standard | Lower | Varies |
| Stability | Stable | Stable | Stable | May change |
| Recommended | ✅ Production | ✅ Fallback | ✅ Cost-sensitive | ❌ Production |

---

## 4. Rate Limits & Quotas

Rate limits are **tier-based** and depend on your OpenAI account's usage tier. Check your current limits at:

> **https://platform.openai.com/settings/organization/limits**

### Common Limit Dimensions

| Dimension | Description |
|---|---|
| Requests per minute (RPM) | Total API calls allowed per minute |
| Images per minute (IPM) | Total images generated per minute (affected by `n` parameter) |
| Tokens per minute (TPM) | Relevant when prompts are long |

### How Rate Limiting Works

When you exceed a limit, the API returns a **429 Too Many Requests** response with a `Retry-After` header indicating how long to wait (in seconds).

```json
{
  "error": {
    "message": "Rate limit reached for gpt-image-1.5 in organization ...",
    "type": "tokens",
    "code": "rate_limit_exceeded"
  }
}
```

**Best practices:**

- Implement exponential backoff with jitter on 429 responses
- Track your usage against known limits
- Use `n=1` and batch sequentially rather than requesting many images at once
- Consider `gpt-image-1-mini` for lower-priority work to conserve quota

---

## 5. Common Error Codes

| Status Code | Error | Description | Common Causes | Resolution |
|---|---|---|---|---|
| **400** | Bad Request | The request is malformed or violates content policy. | Invalid parameter values; unsupported file format; prompt triggers content filter; mask dimensions don't match image; file exceeds size limit. | Validate all parameters. Check file format and size. Rephrase prompt if flagged by content policy. Ensure mask matches input dimensions. |
| **401** | Unauthorized | Authentication failed. | Missing `Authorization` header; invalid API key; expired key; key from wrong organization. | Verify the API key is correct and active at https://platform.openai.com/api-keys. Ensure the key has image generation permissions. |
| **403** | Forbidden | The request is authenticated but not authorized. | Account lacks access to the requested model; billing quota exhausted; organization restrictions. | Check billing status. Verify model access in your OpenAI dashboard. Contact OpenAI support if permissions seem incorrect. |
| **429** | Too Many Requests | Rate limit exceeded. | Too many requests in a short period; burst of concurrent requests; high `n` values consuming quota. | Wait for the duration specified in the `Retry-After` header. Implement exponential backoff. Reduce request frequency or concurrency. |
| **500** | Internal Server Error | An unexpected error on OpenAI's servers. | Transient infrastructure issue. | Retry after a brief delay (1–5 seconds). If persistent, check https://status.openai.com. |
| **502** | Bad Gateway | Upstream server error. | Transient network or infrastructure issue between you and OpenAI. | Retry after a brief delay. Usually resolves on its own. |
| **503** | Service Unavailable | The service is temporarily overloaded or down. | High traffic; maintenance window. | Retry with exponential backoff. Check OpenAI status page for outage reports. |

---

## 6. Troubleshooting Guide

### "Invalid API key" / 401 Unauthorized

1. Verify the key exists and is active at https://platform.openai.com/api-keys
2. Ensure the key starts with `sk-`
3. Check that the environment variable is set correctly:
   ```bash
   echo $OPENAI_API_KEY | head -c 7  # Should print "sk-..." 
   ```
4. Confirm the key belongs to an organization with image API access
5. Regenerate the key if it may have been compromised or revoked

### "Content policy violation" / 400 Bad Request

The prompt or image was flagged by OpenAI's content filter.

- Rephrase the prompt to avoid ambiguous or sensitive language
- Remove any references to real people by name
- Avoid requests for violent, sexual, or otherwise prohibited content
- If the edit is legitimate, try rephrasing with more neutral terminology
- Use `moderation: "low"` to reduce filter sensitivity (if appropriate for your use case)

### "File too large" / 400 Bad Request

The input image exceeds the 50 MB limit.

- Resize the image before uploading (e.g., scale down to 2048px on the longest side)
- Convert to JPEG with moderate compression to reduce file size
- Use a tool like `PIL`/`Pillow` in Python:
  ```python
  from PIL import Image
  img = Image.open("large_image.png")
  img.thumbnail((2048, 2048))
  img.save("resized.jpg", quality=85)
  ```
- For masks: ensure they are under 4 MB and match input dimensions exactly

### "Rate limited" / 429 Too Many Requests

- Wait for the duration in the `Retry-After` response header
- Implement exponential backoff: wait 1s, 2s, 4s, 8s, etc.
- Reduce concurrency — process images sequentially instead of in parallel
- Check your tier limits at https://platform.openai.com/settings/organization/limits
- Consider upgrading your usage tier for higher limits

### "Timeout" / Request takes too long

- Large images and high-quality settings take longer to process
- Set a generous client timeout (60–120 seconds)
- Retry on timeout — the server may have been under load
- Use `quality: "low"` or `"medium"` for faster results when speed matters
- Use `gpt-image-1-mini` for faster turnaround at the cost of quality

### "Unexpected output" / Image doesn't match expectations

- **Be specific in prompts**: describe exactly what to change and what to keep
- **Use `input_fidelity: "high"`** to preserve more of the original image
- **Use a mask** to constrain edits to a specific region
- **Describe the desired result**, not the process (e.g., "a red car" not "change the color to red")
- **Include context** about what should stay the same (e.g., "keep the background unchanged")
- Try multiple generations (`n: 2` or `n: 3`) and pick the best result

### SDK issues: `moderation` parameter

The `moderation` parameter is **not** a standard kwarg in the OpenAI Python SDK. Passing it directly will raise an error.

**Wrong:**
```python
# ❌ This will raise a TypeError
response = client.images.edit(
    image=open("photo.png", "rb"),
    prompt="Make the sky purple",
    moderation="low"  # NOT a valid kwarg
)
```

**Correct:**
```python
# ✅ Use extra_body to pass non-standard parameters
response = client.images.edit(
    image=open("photo.png", "rb"),
    prompt="Make the sky purple",
    extra_body={"moderation": "low"}
)
```

---

## 7. Python SDK Usage Notes

### Installation

```bash
pip install openai
```

### Client Setup

```python
from openai import OpenAI

client = OpenAI(
    api_key="sk-...",       # or set OPENAI_API_KEY env var
    timeout=120.0,          # seconds — increase for large images
    max_retries=3           # automatic retries on transient errors
)
```

### Basic Edit Request

```python
response = client.images.edit(
    model="gpt-image-1.5",
    image=open("input.png", "rb"),
    prompt="Add a rainbow in the sky",
    size="1024x1024",
    quality="high",
    response_format="b64_json"
)

image_data = response.data[0].b64_json
```

### Saving the Result

```python
import base64

image_bytes = base64.b64decode(response.data[0].b64_json)
with open("output.png", "wb") as f:
    f.write(image_bytes)
```

### Using a Mask

```python
response = client.images.edit(
    model="gpt-image-1.5",
    image=open("input.png", "rb"),
    mask=open("mask.png", "rb"),
    prompt="Replace the masked area with a garden",
    size="auto",
    quality="high"
)
```

### Passing Non-Standard Parameters

Parameters not directly supported as kwargs (like `moderation`, `input_fidelity`, `output_compression`, `background`) must be passed via `extra_body`:

```python
response = client.images.edit(
    model="gpt-image-1.5",
    image=open("input.png", "rb"),
    prompt="Make the background transparent",
    size="auto",
    quality="high",
    extra_body={
        "moderation": "low",
        "input_fidelity": "high",
        "background": "transparent",
        "output_compression": 80
    }
)
```

### Response Data Access

```python
# Single image
b64_data = response.data[0].b64_json
revised_prompt = response.data[0].revised_prompt

# Multiple images (when n > 1)
for i, img in enumerate(response.data):
    image_bytes = base64.b64decode(img.b64_json)
    with open(f"output_{i}.png", "wb") as f:
        f.write(image_bytes)
```

### Error Handling

```python
from openai import (
    APIError,
    APIConnectionError,
    RateLimitError,
    AuthenticationError,
    BadRequestError
)

try:
    response = client.images.edit(
        image=open("input.png", "rb"),
        prompt="Edit this image"
    )
except AuthenticationError:
    print("Invalid API key. Check OPENAI_API_KEY.")
except BadRequestError as e:
    print(f"Bad request: {e.message}")
    # Could be content policy, bad format, or size issue
except RateLimitError as e:
    print(f"Rate limited. Retry after: {e.response.headers.get('Retry-After', '?')}s")
except APIConnectionError:
    print("Network error. Check connectivity and retry.")
except APIError as e:
    print(f"Server error ({e.status_code}). Retrying may help.")
```

### Timeout Configuration

For large images or high-quality edits, increase the timeout:

```python
# Per-client timeout (applies to all requests)
client = OpenAI(timeout=120.0)

# Per-request timeout override
response = client.images.edit(
    image=open("large_photo.png", "rb"),
    prompt="Enhance the details",
    timeout=180.0  # override for this request only
)
```
