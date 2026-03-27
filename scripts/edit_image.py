"""Claude image editing skill — calls the OpenAI image edit API.

Accepts an input image and a text prompt, sends them to the API,
and writes the edited image to the specified output path.
All structured output is printed as JSON to stdout; logs go to stderr.
"""

import argparse
import base64
import binascii
import contextlib
import json
import os
import random
import sys
import time
from pathlib import Path
from typing import Any, Optional

import openai
from openai import APIError, APITimeoutError, AuthenticationError, RateLimitError

SUPPORTED_EXTENSIONS = {".png", ".jpg", ".jpeg", ".webp"}
MAX_FILE_SIZE_BYTES = 50 * 1024 * 1024  # 50 MB
MAX_IMAGE_COUNT = 4  # Safety cap to protect API credits (API allows up to 10)
MAX_RATE_LIMIT_RETRIES = 3
MAX_SERVER_ERROR_RETRIES = 2
CLIENT_TIMEOUT = 120.0
LOG_PREFIX = "[edit_image]"


def log(msg: str) -> None:
    print(f"{LOG_PREFIX} {msg}", file=sys.stderr)


def output_success(
    output_paths: list[str],
    model_used: str,
    file_sizes: list[int],
) -> None:
    result: dict[str, Any] = {
        "status": "success",
        "model_used": model_used,
    }
    if len(output_paths) == 1:
        result["output_path"] = output_paths[0]
        result["file_size_bytes"] = file_sizes[0]
    else:
        result["output_paths"] = output_paths
        result["file_sizes_bytes"] = file_sizes
    print(json.dumps(result, indent=2))


def output_error(error: str, error_code: str, retryable: bool) -> None:
    print(json.dumps({
        "status": "error",
        "error": error,
        "error_code": error_code,
        "retryable": retryable,
    }, indent=2))


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Edit an image using the OpenAI image edit API.")
    parser.add_argument("--image-paths", "--image-path",
                        nargs="+", required=True, dest="image_paths",
                        help="Path(s) to one or more source image files. Up to 16.")
    prompt_group = parser.add_mutually_exclusive_group(required=True)
    prompt_group.add_argument("--prompt", help="Text description of the desired edit")
    prompt_group.add_argument("--prompt-file", help="Path to a UTF-8 text file containing the desired edit prompt")
    parser.add_argument("--output-path", required=True, help="Where to save the edited image")
    parser.add_argument("--model", default="gpt-image-1.5", help="Model identifier")
    parser.add_argument("--size", default="auto",
                        choices=["auto", "1024x1024", "1536x1024", "1024x1536"],
                        help="Output image size")
    parser.add_argument("--quality", default="auto",
                        choices=["auto", "low", "medium", "high"],
                        help="Output image quality")
    parser.add_argument("-n", "--n", type=int, default=1, dest="n",
                        help="Number of images to generate (1-4, default: 1)")
    return parser


def parse_args() -> argparse.Namespace:
    return build_parser().parse_args()


def load_api_key() -> Optional[str]:
    key = os.environ.get("OPENAI_API_KEY")
    if key:
        return key

    env_path = Path(__file__).resolve().parent.parent / ".env"
    if env_path.is_file():
        with open(env_path, "r") as f:
            for line in f:
                line = line.strip()
                if not line or line.startswith("#"):
                    continue
                if "=" in line:
                    k, _, v = line.partition("=")
                    k = k.strip()
                    v = v.strip().strip("\"'")
                    if k == "OPENAI_API_KEY" and v:
                        return v
    return None


def validate_image(image_path: str) -> Optional[dict[str, Any]]:
    path = Path(image_path)

    if not path.is_file():
        return {"error": f"File not found: {image_path}", "error_code": "FILE_NOT_FOUND", "retryable": False}

    if path.suffix.lower() not in SUPPORTED_EXTENSIONS:
        return {
            "error": f"Unsupported format '{path.suffix}'. Supported: {', '.join(sorted(SUPPORTED_EXTENSIONS))}",
            "error_code": "UNSUPPORTED_FORMAT",
            "retryable": False,
        }

    file_size = path.stat().st_size
    if file_size > MAX_FILE_SIZE_BYTES:
        size_mb = file_size / (1024 * 1024)
        return {
            "error": f"File is {size_mb:.1f} MB, exceeds 50 MB limit",
            "error_code": "FILE_TOO_LARGE",
            "retryable": False,
        }

    try:
        from PIL import Image
        with Image.open(path) as img:
            img.verify()
    except ImportError:
        pass
    except Exception as exc:
        return {"error": f"Image appears corrupt: {exc}", "error_code": "CORRUPT_IMAGE", "retryable": False}

    return None


def resolve_prompt(args: argparse.Namespace) -> tuple[Optional[str], Optional[dict[str, Any]]]:
    if args.prompt_file:
        prompt_path = Path(args.prompt_file)
        try:
            prompt = prompt_path.read_text(encoding="utf-8")
        except FileNotFoundError:
            return None, {
                "error": f"Prompt file not found: {prompt_path}",
                "error_code": "VALIDATION_ERROR",
                "retryable": False,
            }
        except UnicodeDecodeError as exc:
            return None, {
                "error": f"Prompt file is not valid UTF-8: {exc}",
                "error_code": "VALIDATION_ERROR",
                "retryable": False,
            }
        except OSError as exc:
            return None, {
                "error": f"Unable to read prompt file '{prompt_path}': {exc}",
                "error_code": "VALIDATION_ERROR",
                "retryable": False,
            }
    else:
        prompt = args.prompt

    if prompt is None or not prompt.strip():
        return None, {
            "error": "Prompt must not be empty",
            "error_code": "VALIDATION_ERROR",
            "retryable": False,
        }

    return prompt, None


def build_edit_request_kwargs(args: argparse.Namespace, image_file: Any, prompt: str) -> dict[str, Any]:
    kwargs: dict[str, Any] = {
        "model": args.model,
        "image": image_file,
        "prompt": prompt,
        "size": args.size,
        "quality": args.quality,
        "extra_body": {
            "moderation": "low",
        },
    }
    if args.n > 1:
        kwargs["n"] = args.n
    return kwargs


def call_api(client: openai.OpenAI, args: argparse.Namespace, prompt: str) -> dict[str, Any]:
    rate_limit_attempts = 0
    server_error_attempts = 0

    while True:
        try:
            with contextlib.ExitStack() as stack:
                files = [stack.enter_context(open(p, "rb")) for p in args.image_paths]
                image_arg = files[0] if len(files) == 1 else files
                response = client.images.edit(**build_edit_request_kwargs(args, image_arg, prompt))

            if not response.data:
                return {"error": "API returned empty data array", "error_code": "API_ERROR", "retryable": True}

            output_base = Path(args.output_path)
            output_base.parent.mkdir(parents=True, exist_ok=True)
            saved_paths: list[str] = []
            saved_sizes: list[int] = []

            for idx, item in enumerate(response.data):
                b64_data = item.b64_json
                if not b64_data:
                    return {"error": f"API returned no image data for result {idx + 1}",
                            "error_code": "API_ERROR", "retryable": True}

                try:
                    image_bytes = base64.b64decode(b64_data)
                except binascii.Error as exc:
                    return {"error": f"Failed to decode image data for result {idx + 1}: {exc}",
                            "error_code": "API_ERROR", "retryable": False}

                if len(response.data) == 1:
                    out_path = output_base
                else:
                    out_path = output_base.with_stem(f"{output_base.stem}_{idx + 1}")

                with open(out_path, "wb") as out_file:
                    out_file.write(image_bytes)

                file_size = out_path.stat().st_size
                log(f"Wrote {file_size} bytes to {out_path}")
                saved_paths.append(str(out_path))
                saved_sizes.append(file_size)

            return {"status": "success", "output_paths": saved_paths, "file_sizes": saved_sizes}

        except AuthenticationError:
            return {"error": "Invalid API key", "error_code": "INVALID_API_KEY", "retryable": False}

        except RateLimitError as exc:
            rate_limit_attempts += 1
            if rate_limit_attempts > MAX_RATE_LIMIT_RETRIES:
                return {"error": f"Rate limited after {MAX_RATE_LIMIT_RETRIES} retries: {exc}",
                        "error_code": "RATE_LIMITED", "retryable": True}
            try:
                retry_after = float(exc.response.headers.get("Retry-After", 0))
            except (AttributeError, ValueError, TypeError):
                retry_after = 0.0
            if retry_after > 0:
                delay = retry_after
            else:
                delay = (2 ** rate_limit_attempts) + random.uniform(0, 1)
            log(f"Rate limited, retry {rate_limit_attempts}/{MAX_RATE_LIMIT_RETRIES} in {delay:.1f}s")
            time.sleep(delay)

        except APITimeoutError:
            return {"error": f"Request timed out after {CLIENT_TIMEOUT:.0f}s", "error_code": "TIMEOUT", "retryable": True}

        except APIError as exc:
            if exc.status_code and exc.status_code in (500, 502, 503):
                server_error_attempts += 1
                if server_error_attempts > MAX_SERVER_ERROR_RETRIES:
                    return {"error": f"Server error after {MAX_SERVER_ERROR_RETRIES} retries: {exc}",
                            "error_code": "API_ERROR", "retryable": True}
                delay = (2 ** server_error_attempts) + random.uniform(0, 1)
                log(f"Server error {exc.status_code}, retry {server_error_attempts}/{MAX_SERVER_ERROR_RETRIES} in {delay:.1f}s")
                time.sleep(delay)
            elif exc.status_code == 400 and "content policy" in str(exc).lower():
                return {"error": f"Content policy violation: {exc}", "error_code": "CONTENT_POLICY", "retryable": False}
            elif exc.status_code in (400, 403):
                return {"error": str(exc), "error_code": "API_ERROR", "retryable": False}
            else:
                return {"error": str(exc), "error_code": "API_ERROR", "retryable": True}


def main() -> None:
    args = parse_args()

    api_key = load_api_key()
    if not api_key:
        output_error("OPENAI_API_KEY not found in environment or .env file", "INVALID_API_KEY", False)
        sys.exit(1)

    if len(args.image_paths) > 16:
        output_error("Too many images: max 16 supported", "VALIDATION_ERROR", False)
        sys.exit(1)

    if args.n < 1 or args.n > MAX_IMAGE_COUNT:
        output_error(
            f"Invalid value for --n: {args.n}. Must be between 1 and {MAX_IMAGE_COUNT}",
            "VALIDATION_ERROR",
            False,
        )
        sys.exit(1)

    for path in args.image_paths:
        validation_err = validate_image(path)
        if validation_err:
            output_error(**validation_err)
            sys.exit(1)

    prompt, prompt_err = resolve_prompt(args)
    if prompt_err:
        output_error(**prompt_err)
        sys.exit(1)

    log(f"Editing image(s): {', '.join(args.image_paths)}")
    log(f"Prompt: {prompt}")
    log(f"Model: {args.model}, size: {args.size}, quality: {args.quality}, n: {args.n}")

    client = openai.OpenAI(api_key=api_key, timeout=CLIENT_TIMEOUT)

    try:
        result = call_api(client, args, prompt)
    except Exception as exc:
        output_error(f"Unexpected error: {exc}", "UNKNOWN_ERROR", False)
        sys.exit(1)

    if result.get("status") == "success":
        output_success(result["output_paths"], args.model, result["file_sizes"])
    else:
        output_error(result["error"], result["error_code"], result["retryable"])
        sys.exit(1)


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        log("Interrupted by user")
        sys.exit(130)
