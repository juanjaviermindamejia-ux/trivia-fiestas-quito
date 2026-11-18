"""Convierte tres cuestionarios TXT en el banco SQLite reproducible (seed.sql).

Uso desde el directorio raíz: python -m scripts.import_question_banks
"""
from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
BANKS = (
    ("FQ", "Fiestas de Quito", ROOT / "banks" / "fiestas_de_quito.txt"),
    ("PG", "Programación", ROOT / "banks" / "programacion.txt"),
    ("ES", "ESPE", ROOT / "banks" / "espe.txt"),
)
START = re.compile(r"^\s*(\d+)\.\s*\[(?:Dificultad|Nivel):\s*([^\]]+)\]\s*(.*)$")
OPTION = re.compile(r"^\s*([A-D])\)\s*(.+)$")
ANSWER = re.compile(r"^\s*->\s*Respuesta correcta:\s*([A-D])\)\s*(.*)$")
SUBSCRIPTS = str.maketrans("0123456789", "₀₁₂₃₄₅₆₇₈₉")


@dataclass(frozen=True)
class Item:
    code: str
    category: str
    text: str
    difficulty: int
    options: tuple[tuple[str, int], ...]


def plain_text(value: str) -> str:
    """Adapta notación matemática simple del TXT a texto legible en Tkinter."""
    value = re.sub(r"\\text\{([^{}]*)\}", r"\1", value)
    value = re.sub(
        r"_\{(\d+)\}|_(\d+)",
        lambda match: (match.group(1) or match.group(2)).translate(SUBSCRIPTS),
        value,
    )
    return (value.replace("$", "").replace(r"\,", " ")
                 .replace(r"\log", "log").replace("`", "").strip())


def parse_file(prefix: str, category: str, path: Path) -> list[Item]:
    questions: list[Item] = []
    current: dict | None = None
    for lineno, original in enumerate(path.read_text(encoding="utf-8-sig").splitlines(), 1):
        line = original.strip()
        start = START.match(line)
        if start:
            if current:
                questions.append(complete_item(current, path))
            number, level, title = start.groups()
            level = level.casefold()
            if "alta" in level:
                difficulty = 3
            elif "intermedi" in level:
                difficulty = 2
            elif "básic" in level or "basic" in level:
                difficulty = 1
            else:
                raise ValueError(f"{path}:{lineno}: nivel no reconocido: {level}")
            current = {
                "code": f"{prefix}-{int(number):03d}", "category": category,
                "text_parts": [title] if title else [], "difficulty": difficulty,
                "options": {}, "answer": None,
            }
            continue
        if current is None:
            continue
        match = OPTION.match(line)
        if match:
            letter, text = match.groups()
            if letter in current["options"]:
                raise ValueError(f"{path}:{lineno}: opción duplicada {letter}")
            current["options"][letter] = plain_text(text)
        elif match := ANSWER.match(line):
            current["answer"] = match.group(1)
            declared_text = plain_text(match.group(2))
            actual_text = current["options"].get(current["answer"])
            if declared_text and actual_text != declared_text:
                raise ValueError(f"{path}:{lineno}: la respuesta no coincide con la opción")
        elif line and current["answer"] is None:
            if not current["options"]:
                current["text_parts"].append(line)
            else:
                raise ValueError(f"{path}:{lineno}: línea inesperada en las opciones: {line}")
    if current:
        questions.append(complete_item(current, path))
    expected_codes = [f"{prefix}-{number:03d}" for number in range(1, 51)]
    if [q.code for q in questions] != expected_codes:
        raise ValueError(f"{path}: se esperaban exactamente 50 preguntas numeradas del 1 al 50")
    return questions


def complete_item(record: dict, path: Path) -> Item:
    letters = tuple(record["options"])
    if letters != ("A", "B", "C", "D"):
        raise ValueError(f"{path}: {record['code']} no tiene A, B, C y D: {letters}")
    if record["answer"] not in letters:
        raise ValueError(f"{path}: {record['code']} no tiene una respuesta válida")
    choices = tuple(record["options"].values())
    if len(set(choices)) != 4 or any(not value for value in choices):
        raise ValueError(f"{path}: {record['code']} tiene opciones duplicadas o vacías")
    question_text = plain_text(" ".join(record["text_parts"]))
    if not question_text:
        raise ValueError(f"{path}: {record['code']} tiene un enunciado vacío")
    return Item(
        code=record["code"], category=record["category"],
        text=question_text, difficulty=record["difficulty"],
        options=tuple((record["options"][letter], int(letter == record["answer"]))
                      for letter in ("A", "B", "C", "D")),
    )


def quote(text: str) -> str:
    return "'" + text.replace("'", "''") + "'"


def generate_seed(items: list[Item]) -> str:
    keys = ", ".join(quote(item.code) for item in items)
    qvalues = ",\n".join(
        f"    ({quote(i.code)}, {quote(i.text)}, {quote(i.category)}, {i.difficulty})"
        for i in items
    )
    option_values = ",\n".join(
        f"    ({quote(i.code)}, {quote(value)}, {is_correct})"
        for i in items for value, is_correct in i.options
    )
    return (
        "-- Generado con: python -m scripts.import_question_banks\n"
        "-- Se reemplazan los bancos anteriores conservando los IDs y su historial de uso.\n"
        "BEGIN TRANSACTION;\n"
        "DELETE FROM options;\n"
        f"DELETE FROM questions WHERE code NOT IN ({keys});\n"
        "INSERT INTO questions (code, text, category, difficulty) VALUES\n"
        f"{qvalues}\n"
        "ON CONFLICT(code) DO UPDATE SET text = excluded.text, "
        "category = excluded.category, difficulty = excluded.difficulty;\n"
        "WITH fresh_options(code, text, is_correct) AS (VALUES\n"
        f"{option_values}\n)\n"
        "INSERT INTO options (question_id, text, is_correct)\n"
        "SELECT q.id, o.text, o.is_correct FROM fresh_options AS o "
        "JOIN questions AS q ON q.code = o.code;\n"
        "COMMIT;\n"
    )


def main() -> None:
    items = [item for prefix, category, path in BANKS
             for item in parse_file(prefix, category, path)]
    if len(items) != 150:
        raise ValueError("Se esperaban 150 preguntas (50 en cada banco)")
    output = ROOT / "sql" / "seed.sql"
    output.write_text(generate_seed(items), encoding="utf-8")
    print(f"Importadas {len(items)} preguntas y {sum(len(i.options) for i in items)} opciones a {output}")


if __name__ == "__main__":
    main()
