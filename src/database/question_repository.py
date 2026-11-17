"""Acceso a datos: único lugar donde se consultan las preguntas."""
import sqlite3
from pathlib import Path

from src.database.connection import get_connection
from src.models.question import Option, Question


class QuestionRepository:
    def __init__(self, db_path: Path) -> None:
        self._db_path = db_path

    def get_random_questions(self, amount: int) -> list[Question]:
        with get_connection(self._db_path) as connection:
            rows = connection.execute(
                "SELECT id, text, category, "
                "CASE WHEN CAST(substr(code, 4) AS INTEGER) > 5 THEN 5 "
                "ELSE CAST(substr(code, 4) AS INTEGER) END AS difficulty "
                "FROM questions ORDER BY RANDOM() LIMIT ?",
                (amount,),
            ).fetchall()
            return [self._build_question(connection, row) for row in rows]

    def get_questions_for_game(self) -> list[Question]:
        """Carga el banco para que el servicio pueda alternar categorías."""
        return self.get_random_questions(1000)

    @staticmethod
    def _build_question(connection: sqlite3.Connection, row: sqlite3.Row) -> Question:
        option_rows = connection.execute(
            "SELECT text, is_correct FROM options "
            "WHERE question_id = ? ORDER BY RANDOM()",
            (row["id"],),
        ).fetchall()
        options = tuple(
            Option(text=r["text"], is_correct=bool(r["is_correct"]))
            for r in option_rows
        )
        return Question(id=row["id"], text=row["text"], options=options,
                        category=row["category"], difficulty=row["difficulty"])
