import json
import os

from config.get_config import config_data
from utils.get_time import get_time
from utils.http_client import HTTPClient, HTTPClientError
from utils.logger import setup_logger
from utils.paths import APP_LOG_FILE, ASK_ECHART_LOG_CSV, ASK_ECHART_OUTPUT_DIR, ensure_runtime_directories
from utils.write_csv import write_csv_from_list

logger = setup_logger(__name__, log_file=str(APP_LOG_FILE))


def _safe_retry_pair(retries_used) -> tuple:
    """Normalize retries metadata to a fixed two-value tuple.

    Args:
        retries_used: Response field that may contain retry counters.

    Returns:
        tuple: ``(retry_0, retry_1)`` with fallback ``(0, 0)`` when format is
        invalid.
    """
    if isinstance(retries_used, list) and len(retries_used) >= 2:
        return retries_used[0], retries_used[1]
    return 0, 0


def _save_html_output(response_json: dict) -> None:
    """Persist generated HTML chart content to the configured output directory.

    Args:
        response_json: Parsed response payload from the echart endpoint.

    Returns:
        None: Writes an HTML file when both file name and HTML content exist.
    """
    file_value = response_json.get("file")
    html = response_json.get("html")
    if not file_value or not html:
        return

    file_name = os.path.basename(file_value)
    if not file_name.endswith(".html"):
        file_name = file_name + ".html"

    output_path = ASK_ECHART_OUTPUT_DIR / file_name
    output_path.write_text(html, encoding="utf-8")
    logger.info("HTML chart saved to %s", output_path)


def _append_result_log(request: dict, response_json: dict) -> None:
    """Append summary and optional detail logs for one request result.

    Args:
        request: Request payload sent to the server.
        response_json: Parsed response payload returned by the server.

    Returns:
        None: Appends rows to the aggregated CSV log and per-result detail file.
    """
    retry_0, retry_1 = _safe_retry_pair(response_json.get("retries_used", [0, 0]))
    file_value = response_json.get("file", "")

    write_csv_from_list(
        str(ASK_ECHART_LOG_CSV),
        [
            get_time(),
            request["question"],
            request["retries"][0],
            request["retries"][1],
            "/",
            response_json.get("code", -1),
            retry_0,
            retry_1,
            file_value,
            config_data["llm"]["model"],
            "/",
        ],
    )

    if file_value:
        detail_name = os.path.basename(file_value) + ".txt"
        detail_path = ASK_ECHART_OUTPUT_DIR / detail_name
        write_csv_from_list(
            str(detail_path),
            [
                get_time(),
                request["question"],
                str(request),
                str(response_json),
                "/",
                config_data["llm"]["model"],
                "/",
            ],
        )


if __name__ == "__main__":
    ensure_runtime_directories()
    host = config_data["server"]["host"]
    port = config_data["server"]["port"]
    client = HTTPClient(host=host, port=port, timeout=60, max_retries=1, backoff_seconds=1, logger=logger)

    for _ in range(3):
        request = {
            "question": "List the countries where the official language has more than 50% speakers along with their capital and population.",
            "concurrent": [1, 1],
            "retries": [5, 5],
        }
        try:
            status_code, response_bytes = client.post_json("/ask/echart-file-2", request, retries=0)
        except HTTPClientError as exc:
            logger.error("Request failed after retries: %s", exc)
            print("Failed to get image data.")
            continue

        print(status_code)
        if status_code != 200:
            print("Failed to get image data.")
            continue

        try:
            response_json = json.loads(response_bytes.decode("utf-8"))
        except Exception as exc:
            logger.error("Invalid JSON response: %s", exc)
            print("Failed to parse response JSON.")
            continue

        if response_json.get("code") == 200:
            _save_html_output(response_json)

        _append_result_log(request, response_json)
        print("Success")
