"""Interfaz gráfica (Tkinter). Solo dibuja y delega la lógica al servicio."""
import tkinter as tk
from tkinter import messagebox

from src.hardware.relay_controller import RelayController
from src.services.game_service import GameService

WINDOW_TITLE = "Trivia Fiestas de Quito"
WINDOW_SIZE = "700x520"
BACKGROUND = "#fff4d6"
ACCENT = "#8b1e3f"
NEUTRAL_COLOR = "white"
CORRECT_COLOR = "#9be39b"
WRONG_COLOR = "#f4a0a0"
FEEDBACK_DELAY_MS = 1300


class MainWindow(tk.Tk):
    def __init__(
        self, game: GameService, relay: RelayController, relay_seconds: int
    ) -> None:
        super().__init__()
        self._game = game
        self._relay = relay
        self._relay_delay_ms = relay_seconds * 1000
        self._option_buttons: list[tk.Button] = []

        self.title(WINDOW_TITLE)
        self.geometry(WINDOW_SIZE)
        self.configure(bg=BACKGROUND)
        self._build_widgets()
        self.protocol("WM_DELETE_WINDOW", self._on_close)
        self._show_start_screen()

    # ---------- Construcción ----------
    def _build_widgets(self) -> None:
        tk.Label(self, text=WINDOW_TITLE, bg=BACKGROUND, fg=ACCENT,
                 font=("Arial", 22, "bold")).pack(pady=(15, 5))

        status = ("ESP32 conectado" if self._relay.is_connected
                  else "ESP32 no conectado (modo sin relé)")
        tk.Label(self, text=status, bg=BACKGROUND,
                 font=("Arial", 9)).pack()

        self._progress_label = tk.Label(self, bg=BACKGROUND, font=("Arial", 11))
        self._progress_label.pack(pady=5)

        self._question_label = tk.Label(self, bg=BACKGROUND, wraplength=620,
                                        font=("Arial", 16, "bold"))
        self._question_label.pack(pady=15)

        self._options_frame = tk.Frame(self, bg=BACKGROUND)
        self._options_frame.pack(fill="x")

        self._play_button = tk.Button(self, text="Jugar", bg=ACCENT, fg="white",
                                      font=("Arial", 14, "bold"),
                                      command=self._start_game)

    # ---------- Pantallas ----------
    def _show_start_screen(self) -> None:
        self._progress_label.config(text="")
        self._question_label.config(
            text=f"Responde {self._game.questions_per_game} preguntas.\n"
                 f"Con {self._game.correct_answers_to_win} aciertos o más "
                 "se enciende el relé.")
        self._play_button.pack(pady=20)

    def _show_question(self) -> None:
        question = self._game.current_question
        self._progress_label.config(
            text=f"Pregunta {self._game.current_number} de "
                 f"{self._game.total_questions}   |   Aciertos: {self._game.score}")
        self._question_label.config(text=question.text)
        self._clear_options()
        for index, option in enumerate(question.options):
            button = tk.Button(
                self._options_frame, text=option.text, bg=NEUTRAL_COLOR,
                font=("Arial", 13), wraplength=520,
                command=lambda i=index: self._on_answer(i))
            button.pack(fill="x", padx=60, pady=4)
            self._option_buttons.append(button)

    def _show_result(self) -> None:
        result = self._game.result()
        self._clear_options()
        self._progress_label.config(text="")
        if result.won:
            message = f"¡Ganaste! {result.score}/{result.total}\n¡Se enciende el relé!"
            self._relay.turn_on()
            self.after(self._relay_delay_ms, self._relay.turn_off)
        else:
            message = f"Puntaje: {result.score}/{result.total}\nInténtalo de nuevo."
        self._question_label.config(text=message)
        self._play_button.config(text="Jugar de nuevo")
        self._play_button.pack(pady=20)

    # ---------- Eventos ----------
    def _start_game(self) -> None:
        try:
            self._game.start()
        except ValueError as error:
            messagebox.showerror(WINDOW_TITLE, str(error))
            return
        self._play_button.pack_forget()
        self._show_question()

    def _on_answer(self, selected_index: int) -> None:
        question = self._game.current_question
        was_correct = self._game.submit_answer(selected_index)
        for button, option in zip(self._option_buttons, question.options):
            button.config(state="disabled")
            if option.is_correct:
                button.config(bg=CORRECT_COLOR)
        if not was_correct:
            self._option_buttons[selected_index].config(bg=WRONG_COLOR)
        self.after(FEEDBACK_DELAY_MS, self._go_next)

    def _go_next(self) -> None:
        if self._game.advance():
            self._show_question()
        else:
            self._show_result()

    def _on_close(self) -> None:
        self._relay.close()
        self.destroy()

    # ---------- Utilidades ----------
    def _clear_options(self) -> None:
        for button in self._option_buttons:
            button.destroy()
        self._option_buttons.clear()
