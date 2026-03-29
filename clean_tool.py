from pathlib import Path
from typing import Tuple

from utils.paths import ASK_GRAPH_OUTPUT_DIR, BEST_MODEL_PATH, SAVES_DIR


def _safe_unlink(file_path: Path) -> bool:
    """Delete one file safely.

    Args:
        file_path: Target file path.

    Returns:
        bool: True when deleted successfully, False otherwise.
    """
    try:
        if file_path.is_file() or file_path.is_symlink():
            file_path.unlink()
            return True
    except Exception:
        return False
    return False


def clean_ask_graph_output() -> Tuple[int, int]:
    """Remove all files under output_store/ask-graph recursively.

    Returns:
        tuple[int, int]: (deleted_count, failed_count)
    """
    deleted = 0
    failed = 0

    if not ASK_GRAPH_OUTPUT_DIR.exists():
        return deleted, failed

    for path in ASK_GRAPH_OUTPUT_DIR.rglob("*"):
        if path.is_file() or path.is_symlink():
            if _safe_unlink(path):
                deleted += 1
            else:
                failed += 1

    return deleted, failed


def clean_saves_except_best() -> Tuple[int, int]:
    """Remove all .pth files in saves except model_best.pth.

    Returns:
        tuple[int, int]: (deleted_count, failed_count)
    """
    deleted = 0
    failed = 0

    if not SAVES_DIR.exists():
        return deleted, failed

    keep_name = BEST_MODEL_PATH.name
    for path in SAVES_DIR.glob("*.pth"):
        if path.name == keep_name:
            continue
        if _safe_unlink(path):
            deleted += 1
        else:
            failed += 1

    return deleted, failed


def main() -> None:
    """Run one-click cleanup for generated files."""
    ask_graph_deleted, ask_graph_failed = clean_ask_graph_output()
    saves_deleted, saves_failed = clean_saves_except_best()

    print("Cleanup completed.")
    print(
        f"ask-graph files: deleted={ask_graph_deleted}, failed={ask_graph_failed}"
    )
    print(
        f"saves .pth (except {BEST_MODEL_PATH.name}): deleted={saves_deleted}, failed={saves_failed}"
    )


if __name__ == "__main__":
    main()
