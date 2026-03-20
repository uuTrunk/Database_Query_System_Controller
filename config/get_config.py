from pathlib import Path
from typing import Any, Dict

import yaml

from utils.paths import CONFIG_FILE

REQUIRED_TOP_LEVEL_KEYS = ("mysql", "llm", "server")
REQUIRED_SERVER_KEYS = ("host", "port")
REQUIRED_LLM_KEYS = ("model_provider", "model")


def _validate_config(data: Dict[str, Any]) -> Dict[str, Any]:
    """Validate required configuration keys.

    Args:
        data: Parsed YAML configuration dictionary.

    Returns:
        dict[str, Any]: The same configuration dictionary when all required keys exist.

    Raises:
        KeyError: If any required top-level or nested key is missing.
    """
    missing = [key for key in REQUIRED_TOP_LEVEL_KEYS if key not in data]
    if missing:
        raise KeyError(f"Missing required top-level config keys: {missing}")

    server_missing = [key for key in REQUIRED_SERVER_KEYS if key not in data["server"]]
    if server_missing:
        raise KeyError(f"Missing required server config keys: {server_missing}")

    llm_missing = [key for key in REQUIRED_LLM_KEYS if key not in data["llm"]]
    if llm_missing:
        raise KeyError(f"Missing required llm config keys: {llm_missing}")

    return data


def load_config(config_file: Path = CONFIG_FILE) -> Dict[str, Any]:
    """Load and validate application configuration from a YAML file.

    Args:
        config_file: Path to the YAML configuration file.

    Returns:
        dict[str, Any]: Validated configuration data with normalized server port type.

    Raises:
        FileNotFoundError: If the configuration file does not exist.
        ValueError: If YAML parsing fails.
        TypeError: If YAML content is not a dictionary.
        KeyError: If required keys are missing.
    """
    config_path = Path(config_file)
    if not config_path.exists():
        raise FileNotFoundError(f"Config file not found: {config_path}")

    try:
        with config_path.open("r", encoding="utf-8") as stream:
            loaded = yaml.safe_load(stream) or {}
    except yaml.YAMLError as exc:
        raise ValueError(f"Invalid YAML in config file: {config_path}") from exc

    if not isinstance(loaded, dict):
        raise TypeError(f"Config file must contain a YAML object: {config_path}")

    config = _validate_config(loaded)
    config["server"]["port"] = int(config["server"]["port"])
    return config


try:
    config_data = load_config()
except Exception as exc:
    raise RuntimeError(f"Failed to load configuration from {CONFIG_FILE}: {exc}") from exc



