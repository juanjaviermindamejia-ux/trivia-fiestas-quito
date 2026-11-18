"""Crea, migra y actualiza el banco de preguntas sin perder el historial de uso."""
from pathlib import Path

from src.database.connection import get_connection


def initialize_database(db_path: Path, schema_path: Path, seed_path: Path) -> None:
    with get_connection(db_path) as connection:
        connection.executescript(schema_path.read_text(encoding="utf-8"))
        columns = {
            row["name"]
            for row in connection.execute("PRAGMA table_info(questions)").fetchall()
        }
        # Migración para bases SQLite anteriores incluidas en la versión original.
        if "category" not in columns:
            connection.execute(
                "ALTER TABLE questions ADD COLUMN category TEXT NOT NULL "
                "DEFAULT 'Fiestas de Quito'"
            )
        if "difficulty" not in columns:
            connection.execute(
                "ALTER TABLE questions ADD COLUMN difficulty INTEGER NOT NULL DEFAULT 1"
            )
        connection.executescript(seed_path.read_text(encoding="utf-8"))
        invalid = connection.execute(
            "SELECT q.code FROM questions AS q "
            "LEFT JOIN options AS o ON o.question_id = q.id "
            "GROUP BY q.id HAVING COUNT(o.id) <> 4 "
            "OR COALESCE(SUM(o.is_correct), 0) <> 1 "
            "LIMIT 1"
        ).fetchone()
        if invalid:
            raise ValueError(
                f"La pregunta {invalid['code']} no tiene 4 opciones y 1 respuesta correcta."
            )
