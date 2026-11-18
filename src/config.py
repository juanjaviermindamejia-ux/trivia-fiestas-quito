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

    # ESP32 por puerto serial.
    # El puerto cambia según el equipo (COM3, COM5, /dev/ttyUSB0...). Para ver cuál
    # es el tuyo: python -m scripts.list_ports
    # Cada integrante puede usar el suyo sin editar este archivo, con la variable
    # de entorno TRIVIA_SERIAL_PORT (PowerShell: $env:TRIVIA_SERIAL_PORT = "COM5").
    serial_port: str = os.getenv("TRIVIA_SERIAL_PORT", "COM6")
    baud_rate: int = 115200  # debe ser igual a BAUD_RATE en el firmware (.ino)

    # Reglas del juego
    questions_per_game: int = 5
    correct_answers_to_win: int = 3


settings = Settings()
