"""Consulta preguntas y valida su selección aleatoria, sin repetir hasta agotar banco."""
from __future__ import annotations

import sqlite3
from pathlib import Path
from random import choice

from src.database.connection import get_connection
from src.models.question import Option, Question

CATEGORY_ORDER = ("Fiestas de Quito", "Programación", "ESPE")


class QuestionRepository:
    def __init__(self, db_path: Path) -> None:
        self._db_path = db_path

    def get_categories(self) -> list[str]:
        """Establece un ciclo estable: Quito, Programación, ESPE."""
        with get_connection(self._db_path) as connection:
            categories = {
                row["category"] for row in connection.execute(
                    "SELECT DISTINCT category FROM questions"
                ).fetchall()
            }
        return [name for name in CATEGORY_ORDER if name in categories] + sorted(
            categories.difference(CATEGORY_ORDER)
        )

    def draw_question(
        self, category: str, exclude_ids: set[int] | None = None
    ) -> Question | None:
        """Extrae y registra UNA pregunta mostrada del banco solicitado.

        El conjunto used_ids es el arreglo de validación por categoría. Cuando
        todas las preguntas de ese banco ya aparecieron, se vacía su historial
        y empieza una nueva ronda aleatoria. Se excluyen también las preguntas
        que ya están en la partida en curso, incluso si se reinicia un ciclo.
        SQLite conserva los registros entre ejecuciones de la aplicación.
        """
        exclude_ids = exclude_ids or set()
        with get_connection(self._db_path) as connection:
            # Serializa lectura + selección + marcado si hay dos procesos abiertos.
            connection.execute("BEGIN IMMEDIATE")
            question_rows = connection.execute(
                "SELECT id, text, category, difficulty "
                "FROM questions WHERE category = ?",
                (category,),
            ).fetchall()
            if not question_rows:
                return None
            used_ids = {
                row["question_id"] for row in connection.execute(
                    "SELECT question_id FROM used_questions WHERE category = ?",
                    (category,),
                ).fetchall()
            }
            bank_ids = {row["id"] for row in question_rows}
            used_ids.intersection_update(bank_ids)
            if used_ids == bank_ids:
                # El ciclo se agotó: únicamente se vacía la lista de este banco.
                connection.execute(
                    "DELETE FROM used_questions WHERE category = ?", (category,)
                )
                used_ids.clear()

            candidates = [
                row for row in question_rows
                if row["id"] not in used_ids and row["id"] not in exclude_ids
            ]
            if not candidates:
                return None
            row = choice(candidates)
            question = self._build_question(connection, row)
            if len(question.options) != 4 or sum(o.is_correct for o in question.options) != 1:
                raise ValueError(f"Pregunta ID {question.id}: se requieren 4 opciones y 1 correcta")
            if question.id in used_ids or question.id in exclude_ids:
                raise ValueError("Se detectó una pregunta repetida; no se mostrará")
            connection.execute(
                "INSERT INTO used_questions(category, question_id) VALUES (?, ?)",
                (category, question.id),
            )
            return question

    def get_random_questions(self, amount: int) -> list[Question]:
        """Listado aleatorio de consulta (no consume el historial del juego)."""
        with get_connection(self._db_path) as connection:
            rows = connection.execute(
                "SELECT id, text, category, difficulty FROM questions "
                "ORDER BY RANDOM() LIMIT ?",
                (amount,),
            ).fetchall()
            return [self._build_question(connection, row) for row in rows]

    def get_questions_for_game(self) -> list[Question]:
        """Compatibilidad con las reglas/pruebas anteriores del proyecto."""
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
        return Question(
            id=row["id"], text=row["text"], options=options,
            category=row["category"], difficulty=row["difficulty"],
        )
