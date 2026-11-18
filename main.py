"""Punto de entrada: arma las piezas y arranca la aplicación."""
import logging

from src.config import settings
from src.database.initializer import initialize_database
from src.database.question_repository import QuestionRepository
from src.hardware.relay_controller import create_relay_controller
from src.services.game_service import GameService
from src.ui.main_window import MainWindow


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")

    initialize_database(settings.db_path, settings.schema_path, settings.seed_path)
    repository = QuestionRepository(settings.db_path)
    game = GameService(repository, settings.questions_per_game,
                       settings.correct_answers_to_win)
    relay = create_relay_controller(settings.serial_port, settings.baud_rate)

    MainWindow(game, relay).mainloop()


if __name__ == "__main__":
    main()
