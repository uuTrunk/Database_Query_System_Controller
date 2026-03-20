from pathlib import Path


def get_api_key_from_file(file_path: str = "./llm_access/api_key_qwen.txt") -> str:
    """Read an API key from a text file with explicit validation.

    Args:
        file_path: Relative or absolute path to the API key file.

    Returns:
        str: Non-empty API key string.

    Raises:
        FileNotFoundError: If the key file does not exist.
        ValueError: If the key file exists but is empty.
    """
    path = Path(file_path)
    if not path.is_absolute():
        path = Path(__file__).resolve().parent.parent / path

    if not path.exists():
        raise FileNotFoundError(f"API key file not found: {path}")

    api_key = path.read_text(encoding="utf-8").strip()
    if not api_key:
        raise ValueError(f"API key file is empty: {path}")

    return api_key

