"""Configuración central del proyecto. Aquí no hay lógica, solo valores."""
import os
from dataclasses import dataclass
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent


@dataclass(frozen=True)
class Settings:
    # Base de datos
    db_path: Path = BASE_DIR / "data" / "trivia.db"
    schema_path: Path = BASE_DIR / "sql" / "schema.sql"
    seed_path: Path = BASE_DIR / "sql" / "seed.sql"

    # ESP32 (cada integrante puede definir su puerto sin editar el código:
    # variable de entorno TRIVIA_SERIAL_PORT)
    serial_port: str = os.getenv("TRIVIA_SERIAL_PORT", "COM3")
    baud_rate: int = 115200
    relay_seconds: int = 5

    # Reglas del juego
    questions_per_game: int = 5
    correct_answers_to_win: int = 3


settings = Settings()
