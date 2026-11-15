"""Crea las tablas y carga las preguntas iniciales desde los archivos .sql."""
from pathlib import Path

from src.database.connection import get_connection


def initialize_database(db_path: Path, schema_path: Path, seed_path: Path) -> None:
    with get_connection(db_path) as connection:
        connection.executescript(schema_path.read_text(encoding="utf-8"))
        connection.executescript(seed_path.read_text(encoding="utf-8"))
