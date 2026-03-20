import base64
import concurrent.futures
import json
import math
import random
import string
from pathlib import Path
from typing import Any, Dict, Optional, Tuple

from pywebio import start_server
from pywebio.input import TEXT, input
from pywebio.output import put_error, put_image, put_markdown, put_text

from config.get_config import config_data
from training.predict import predict
from utils.http_client import HTTPClient, HTTPClientError
from utils.logger import setup_logger
from utils.paths import APP_LOG_FILE, TMP_IMG_DIR, ensure_runtime_directories

logger = setup_logger(__name__, log_file=str(APP_LOG_FILE))
ensure_runtime_directories()

http_client = HTTPClient(
    host=config_data["server"]["host"],
    port=config_data["server"]["port"],
    timeout=60,
    max_retries=1,
    backoff_seconds=1.0,
    logger=logger,
)


def calculate_optimal_threads(success_prob: float) -> int:
    """Compute a bounded thread count from predicted single-request success rate.

    The function finds the smallest ``n`` such that ``1 - (1 - p)^n >= 0.99`` and
    clamps the result into ``[1, 5]`` for runtime safety.

    Args:
        success_prob: Predicted success probability for one request, expected in
        ``[0.0, 1.0]``.

    Returns:
        int: Number of concurrent threads to use, bounded to ``1..5``.
    """
    p = max(0.0, min(float(success_prob), 0.999))
    if p >= 0.999:
        return 1
    if p <= 0:
        return 5

    required_threads = math.ceil(math.log(0.01) / math.log(1 - p))
    return max(1, min(required_threads, 5))


def _generate_image_path() -> Path:
    """Generate a unique temporary image path.

    Args:
        None.

    Returns:
        Path: Target path under the runtime temporary image directory.
    """
    suffix = "".join(random.choice(string.ascii_lowercase) for _ in range(8))
    return TMP_IMG_DIR / f"{suffix}.png"


def _parse_response_body(response_body: bytes) -> Dict[str, Any]:
    """Parse server response bytes into a JSON dictionary.

    Args:
        response_body: Raw HTTP response body in UTF-8 JSON bytes.

    Returns:
        dict[str, Any]: Parsed JSON payload.

    Raises:
        ValueError: If decoding or JSON parsing fails.
    """
    try:
        return json.loads(response_body.decode("utf-8"))
    except Exception as exc:
        raise ValueError(f"Invalid JSON response from server: {exc}") from exc


def parse_and_save_image(status_code: int, response_body: bytes) -> Tuple[Optional[Path], Dict[str, Any]]:
    """Parse an API response and persist image data when available.

    Args:
        status_code: HTTP status code returned by the server.
        response_body: Raw response payload bytes.

    Returns:
        tuple[Optional[Path], dict[str, Any]]: Saved image path (or ``None``)
        and parsed JSON payload.

    Raises:
        ValueError: If response JSON is invalid or image base64 decoding fails.
    """
    data = _parse_response_body(response_body)
    if status_code != 200 or data.get("code") != 200:
        return None, data

    image_base64 = data.get("image_data", "")
    if not image_base64:
        return None, data

    try:
        image_bytes = base64.b64decode(image_base64)
    except Exception as exc:
        raise ValueError(f"Failed to decode base64 image: {exc}") from exc

    image_path = _generate_image_path()
    image_path.write_bytes(image_bytes)
    return image_path, data


def main() -> None:
    """Run the interactive PyWebIO app for graph generation requests.

    Args:
        None.

    Returns:
        None: This function serves an interactive loop until the process exits.
    """
    put_markdown("# Data Copilot")

    while True:
        question = input("Enter your question", type=TEXT, required=True, placeholder="")
        put_markdown("## " + question)
        put_text("Processing your question...")

        try:
            predicted_success = float(predict(question))
        except Exception as exc:
            logger.exception("Predict failed: %s", exc)
            predicted_success = 0.2
            put_error(f"Prediction failed, fallback success probability used: {exc}")

        predicted_success = max(0.0, min(predicted_success, 1.0))
        num_threads = calculate_optimal_threads(predicted_success)

        put_markdown("**Prediction value:**")
        put_markdown(f"## {predicted_success:.4f}")
        put_markdown("**Using threads:**")
        put_markdown(f"## {num_threads}")

        request = {
            "question": question,
            "concurrent": [1, 1],
            "retries": [5, 5],
        }

        results = []
        with concurrent.futures.ThreadPoolExecutor(max_workers=num_threads) as executor:
            futures = [
                executor.submit(http_client.post_json, "/ask/graph-steps", request)
                for _ in range(num_threads)
            ]

            for future in concurrent.futures.as_completed(futures):
                try:
                    status_code, response_body = future.result(timeout=65)
                    results.append((status_code, response_body))
                except HTTPClientError as exc:
                    logger.error("Request failed after retries: %s", exc)
                    put_error(f"Request failed after retries: {exc}")
                except Exception as exc:
                    logger.exception("Request failed: %s", exc)
                    put_error(f"Request failed: {exc}")

        if not results:
            put_error("All requests failed.")
            continue

        success_count = 0
        for index, (status_code, response_body) in enumerate(results, start=1):
            try:
                image_path, data = parse_and_save_image(status_code, response_body)
            except Exception as exc:
                logger.exception("Failed to parse response: %s", exc)
                put_text(f"Result {index}: Failed (invalid response)")
                continue

            if image_path:
                put_image(image_path.read_bytes())
                put_text(f"Result {index}: Success")
                success_count += 1
            else:
                error_msg = data.get("msg", "unknown error") if isinstance(data, dict) else "unknown error"
                put_text(f"Result {index}: Failed ({error_msg})")

        if success_count == 0:
            put_error("No successful generation for this question.")


if __name__ == "__main__":
    start_server(main, port=8090)

# What are the top 6 cities with the highest population across all continents?
# List the countries with a surface area less than 100,000 sq km and their official languages.
# Display the average life expectancy in countries with a surface area larger than 500,000 square kilometers using a column chart.


# Provide the bottom 5 cities in terms of population from Europe.
# For countries with at least 5 million inhabitants, list the top 2 districts with the highest population.

# Chart the distribution of the population of cities in countries with more than 2 official languages using a histogram.
# Display the distribution of the city populations within countries having more than 2 official languages using a scatter plot.
