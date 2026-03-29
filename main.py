import base64
import concurrent.futures
import hashlib
import hmac
import json
import math
import random
import string
from pathlib import Path
from typing import Any, Dict, Optional, Tuple

from pywebio import start_server
from pywebio.input import PASSWORD, TEXT, input, input_group
from pywebio.output import clear, put_error, put_html, put_image, put_markdown, put_text

from config.get_config import config_data
from training.predict import predict
from utils.http_client import HTTPClient, HTTPClientError
from utils.logger import setup_logger
from utils.paths import APP_LOG_FILE, LOGIN_PAGE_TEMPLATE_FILE, TMP_IMG_DIR, ensure_runtime_directories

logger = setup_logger(__name__, log_file=str(APP_LOG_FILE))
ensure_runtime_directories()

auth_config = config_data.get("auth", {}) if isinstance(config_data, dict) else {}
LOGIN_USERNAME = str(auth_config.get("username", "admin"))
LOGIN_PASSWORD = str(auth_config.get("password", ""))
LOGIN_PASSWORD_SHA256 = str(auth_config.get("password_sha256", "")).strip().lower()

DEFAULT_LOGIN_PAGE_HTML = """<div style=\"text-align:center;margin-top:10vh;font-family:'Segoe UI',sans-serif;\"><h1>Data Copilot</h1></div>"""

http_client = HTTPClient(
    host=config_data["server"]["host"],
    port=config_data["server"]["port"],
    timeout=60,
    max_retries=1,
    backoff_seconds=1.0,
    logger=logger,
)


def _compute_future_timeout_seconds(client: HTTPClient, safety_margin: float = 5.0) -> float:
    """Compute a safe wait timeout for future.result based on HTTP retry policy.

    Args:
        client (HTTPClient): Configured HTTP client instance.
        safety_margin (float, optional): Extra seconds added to avoid edge truncation.

    Returns:
        float: Maximum expected request wall time in seconds.
    """
    attempts = max(1, int(client.max_retries) + 1)
    request_budget = float(client.timeout) * attempts
    # backoff pattern in HTTPClient: backoff * 2^(attempt_index-1) for failed attempts before last one
    backoff_budget = 0.0
    for attempt_index in range(1, attempts):
        backoff_budget += float(client.backoff_seconds) * (2 ** (attempt_index - 1))
    return request_budget + backoff_budget + max(0.0, float(safety_margin))


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


def _render_login_page() -> None:
    """Render a Chrome-inspired static login screen."""
    try:
        login_html = LOGIN_PAGE_TEMPLATE_FILE.read_text(encoding="utf-8")
    except Exception as exc:
        logger.warning("Failed to load login template %s: %s", LOGIN_PAGE_TEMPLATE_FILE, exc)
        login_html = DEFAULT_LOGIN_PAGE_HTML

    put_html(login_html)


def _authenticate_user() -> None:
    """Authenticate with fixed admin credentials before entering the dashboard."""

    def _password_is_valid(raw_password: str) -> bool:
        if LOGIN_PASSWORD_SHA256:
            candidate_hash = hashlib.sha256(raw_password.encode("utf-8")).hexdigest().lower()
            return hmac.compare_digest(candidate_hash, LOGIN_PASSWORD_SHA256)
        return hmac.compare_digest(raw_password, LOGIN_PASSWORD)

    while True:
        clear()
        _render_login_page()
        credentials = input_group(
            "",
            [
                input(name="username", type=TEXT, required=True, placeholder="请输入账号"),
                input(name="password", type=PASSWORD, required=True, placeholder="请输入密码"),
            ],
        )

        if (
            hmac.compare_digest(str(credentials.get("username", "")), LOGIN_USERNAME)
            and _password_is_valid(str(credentials.get("password", "")))
        ):
            clear()
            put_markdown("## 登录成功")
            put_text("正在进入可视化界面...")
            return

        put_error("账号或密码错误，请重试。")


def main() -> None:
    """Run the interactive PyWebIO app for graph generation requests.

    Args:
        None.

    Returns:
        None: This function serves an interactive loop until the process exits.
    """
    _authenticate_user()
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
        future_timeout_seconds = _compute_future_timeout_seconds(http_client)
        with concurrent.futures.ThreadPoolExecutor(max_workers=num_threads) as executor:
            futures = [
                executor.submit(http_client.post_json, "/ask/graph-steps", request)
                for _ in range(num_threads)
            ]

            for future in concurrent.futures.as_completed(futures):
                try:
                    status_code, response_body = future.result(timeout=future_timeout_seconds)
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
