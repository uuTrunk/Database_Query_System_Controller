import http.client
import json
import time
from typing import Any, Dict, Optional, Tuple


class HTTPClientError(RuntimeError):
    """Raised when all HTTP retries fail."""


class HTTPClient:
    """Simple JSON HTTP client with retry and timeout support."""

    def __init__(
        self,
        host: str,
        port: int,
        timeout: int = 30,
        max_retries: int = 2,
        backoff_seconds: float = 1.0,
        logger=None,
    ) -> None:
        self.host = host
        self.port = port
        self.timeout = timeout
        self.max_retries = max_retries
        self.backoff_seconds = backoff_seconds
        self.logger = logger

    def post_json(
        self,
        path: str,
        request_data: Dict[str, Any],
        retries: Optional[int] = None,
        timeout: Optional[int] = None,
    ) -> Tuple[int, bytes]:
        """POST JSON payload and return (status_code, response_bytes)."""
        request_timeout = timeout or self.timeout
        max_attempts = (retries if retries is not None else self.max_retries) + 1
        payload = json.dumps(request_data, ensure_ascii=False)
        headers = {"Content-Type": "application/json"}
        last_error: Optional[Exception] = None

        for attempt in range(1, max_attempts + 1):
            connection = http.client.HTTPConnection(self.host, self.port, timeout=request_timeout)
            try:
                connection.request("POST", path, body=payload.encode("utf-8"), headers=headers)
                response = connection.getresponse()
                return response.status, response.read()
            except Exception as exc:
                last_error = exc
                if self.logger:
                    self.logger.warning(
                        "HTTP request failed: path=%s attempt=%s/%s error=%s",
                        path,
                        attempt,
                        max_attempts,
                        exc,
                    )
                if attempt < max_attempts:
                    time.sleep(self.backoff_seconds * (2 ** (attempt - 1)))
            finally:
                connection.close()

        raise HTTPClientError(
            f"Request failed after {max_attempts} attempts: {path}; last_error={last_error}"
        )


def wait_for_server_ready(
    host: str,
    port: int,
    max_retries: int = 10,
    delay_seconds: float = 2.0,
    timeout: int = 2,
    logger=None,
) -> bool:
    """Poll the TCP endpoint until it accepts connections or retries are exhausted."""
    for attempt in range(1, max_retries + 1):
        connection = http.client.HTTPConnection(host, port, timeout=timeout)
        try:
            connection.connect()
            return True
        except Exception as exc:
            if logger:
                logger.info(
                    "Server not ready yet: %s:%s attempt=%s/%s error=%s",
                    host,
                    port,
                    attempt,
                    max_retries,
                    exc,
                )
            time.sleep(delay_seconds)
        finally:
            connection.close()

    return False
