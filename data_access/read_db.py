from threading import Lock
from typing import Dict, List, Tuple

import pandas as pd
from sqlalchemy import inspect, text
from sqlalchemy.exc import SQLAlchemyError

from data_access.db_conn import engine

tables_data = None
foreign_keys_cache = None
comments_cache = None
tables_data_lock = Lock()


def _build_select_all_query(table_name: str, columns: List[str]):
    """Build a deterministic SELECT statement with explicit columns.

    Args:
        table_name: Physical table name from SQLAlchemy inspector.
        columns: Ordered table column names from SQLAlchemy inspector.

    Returns:
        sqlalchemy.sql.elements.TextClause: SQL text object.
    """
    quoted_columns = ", ".join(f"`{column}`" for column in columns)
    return text(f"SELECT {quoted_columns} FROM `{table_name}`")


def _load_schema_metadata(inspector) -> Tuple[Dict[str, Dict[str, Tuple[str, str]]], List[Dict[str, Dict[str, str]]]]:
    """Load foreign keys and table/column comments in one metadata pass."""
    foreign_keys: Dict[str, Dict[str, Tuple[str, str]]] = {}
    table_comments: Dict[str, str] = {}
    column_comments: Dict[str, Dict[str, str]] = {}

    for table_name in inspector.get_table_names():
        fks = inspector.get_foreign_keys(table_name)
        if fks:
            foreign_keys[table_name] = {}
            for fk in fks:
                constrained_columns = fk.get("constrained_columns", [])
                referred_columns = fk.get("referred_columns", [])
                referred_table = fk.get("referred_table")
                for index, column in enumerate(constrained_columns):
                    if referred_table and index < len(referred_columns):
                        foreign_keys[table_name][column] = (referred_table, referred_columns[index])

        table_comment_info = inspector.get_table_comment(table_name) or {}
        table_comments[table_name] = table_comment_info.get("text") or ""

        column_comments[table_name] = {}
        for column in inspector.get_columns(table_name):
            column_name = str(column.get("name", ""))
            column_comments[table_name][column_name] = str(column.get("comment") or "")

    return foreign_keys, [table_comments, column_comments]


def _load_tables_data(inspector) -> Dict[str, pd.DataFrame]:
    """Load all table data using explicit column lists for stable query plans."""
    loaded_tables: Dict[str, pd.DataFrame] = {}
    with engine.connect() as connection:
        for table_name in inspector.get_table_names():
            columns = [str(column.get("name")) for column in inspector.get_columns(table_name)]
            query = _build_select_all_query(table_name, columns)
            loaded_tables[table_name] = pd.read_sql(query, connection)
    return loaded_tables


def get_data_from_db(force_reload: bool = False):
    """Load table data and schema metadata with in-process cache.

    Args:
        force_reload: Whether to bypass cache and reload from database.

    Returns:
        tuple: ``(tables_data, keys, comments)``.
    """
    global tables_data
    global foreign_keys_cache
    global comments_cache

    if force_reload or tables_data is None or foreign_keys_cache is None or comments_cache is None:
        with tables_data_lock:
            if force_reload or tables_data is None or foreign_keys_cache is None or comments_cache is None:
                try:
                    inspector = inspect(engine)
                    tables_data = _load_tables_data(inspector)
                    foreign_keys_cache, comments_cache = _load_schema_metadata(inspector)
                except SQLAlchemyError as exc:
                    raise RuntimeError(f"Failed to load database data: {exc}") from exc

    return tables_data, foreign_keys_cache, comments_cache


if __name__ == "__main__":
    data = get_data_from_db()
    print(type(data), "\n")
    print(data[2][1])
    print("###########################################\n\n")

