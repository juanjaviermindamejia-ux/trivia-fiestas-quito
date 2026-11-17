"""Concurso televisivo en Tkinter. Datos y reglas permanecen en GameService."""

from __future__ import annotations

import tkinter as tk
from tkinter import messagebox

from src.hardware.relay_controller import RelayController
from src.services.game_service import GameService
from src.ui import theme as t
from src.ui.countdown import Countdown
from src.ui.widgets import HexButton, HexPanel, Stage


class MainWindow(tk.Tk):
    def __init__(
        self, game: GameService, relay: RelayController, relay_seconds: int
    ) -> None:
        super().__init__()
        self._game, self._relay = game, relay
        self._relay_delay_ms = relay_seconds * 1000
        self._option_buttons: list[HexButton] = []
        self._screen = "start"
        self._answer_pending = False
        self._answered_count = 0
        self._completed: dict[int, bool] = {}
        self._layout_job: str | None = None
        self._next_job: str | None = None
        self._timer_job: str | None = None
        self._countdown = Countdown(t.LIFELINE_SECONDS)
        self._lifeline_used: set[int] = set()
        self._relay_jobs: set[str] = set()
        self._layout_mode: tuple[bool, bool, int] | None = None
        self.title(t.WINDOW_TITLE)
        self.geometry(t.WINDOW_SIZE)
        self.minsize(320, 420)
        self.configure(bg=t.BACKGROUND)
        self._build_widgets()
        self.protocol("WM_DELETE_WINDOW", self._on_close)
        self._show_start_screen()

    def _label(self, master: tk.Misc, text: str = "", *, size: int = 12,
               color: str = t.TEXT, bg: str = t.BACKGROUND,
               bold: bool = False) -> tk.Label:
        return tk.Label(master, text=text, bg=bg, fg=color, justify="center",
                        font=("Arial", size, "bold" if bold else "normal"))

    def _build_widgets(self) -> None:
        self._viewport = Stage(self, bg=t.BACKGROUND, highlightthickness=0,
                               yscrollincrement=28, takefocus=False)
        self._viewport.pack(side="left", fill="both", expand=True)
        self._scrollbar = tk.Scrollbar(self, orient="vertical",
                                       command=self._viewport.yview,
                                       bg=t.PANEL, troughcolor=t.BACKGROUND,
                                       activebackground=t.OUTLINE)
        self._viewport.configure(yscrollcommand=self._scrollbar.set)
        self._page = tk.Frame(self._viewport, bg=t.BACKGROUND)
        self._page_window = self._viewport.create_window(
            30, 20, anchor="nw", window=self._page, width=1100)
        self._viewport.bind("<Configure>", self._schedule_layout)
        self._page.bind("<Configure>", self._update_scrollregion)
        self.bind("<MouseWheel>", self._on_wheel)
        self.bind("<Button-4>", lambda _e: self._scroll(-1))
        self.bind("<Button-5>", lambda _e: self._scroll(1))
        self.bind("<FocusIn>", self._reveal_focus)

        self._header = tk.Frame(self._page, bg=t.BACKGROUND)
        self._header.pack(fill="x", pady=(2, 24))
        self._title = tk.Label(
            self._header, text=t.WINDOW_TITLE, font=("Georgia", 46, "bold italic"),
            fg=t.GOLD_LIGHT, bg=t.BACKGROUND,
        )
        self._title.pack(fill="x")
        self._subtitle = self._label(self._header, "Responde 5 preguntas y gana", size=16)
        self._subtitle.pack(fill="x", pady=(2, 12))
        tk.Frame(self._header, bg=t.GOLD_DARK, height=2).pack(fill="x", padx=45)
        self._body = tk.Frame(self._page, bg=t.BACKGROUND)
        self._body.pack(fill="x")
        self._body.columnconfigure(0, weight=1)
        self._main = tk.Frame(self._body, bg=t.BACKGROUND)
        self._main.grid(row=0, column=0, sticky="new")
        self._main.bind("<Configure>", self._fit_content)
        self._build_lifelines()
        self._build_progress()
        self._question_panel = HexPanel(self._main, padding=22, inset=32)
        self._question_panel.pack(fill="x", pady=(12, 12))
        self._question_label = self._label(self._question_panel.content, size=23,
                                           bg=t.PANEL, bold=True)
        self._question_label.configure(wraplength=720)
        self._question_label.pack(fill="x")
        self._options_frame = tk.Frame(self._main, bg=t.BACKGROUND)
        self._options_frame.pack(fill="x")
        self._feedback = self._label(self._main, size=11, color=t.MUTED)
        self._feedback.configure(wraplength=700)
        self._feedback.pack(fill="x", pady=(12, 8))
        self._play_button = HexButton(self._main, "Jugar", self._start_game, primary=True)
        self._build_ladder()
        status = "ESP32 conectado" if self._relay.is_connected else "Modo sin relé · ESP32 no conectado"
        self._footer = self._label(self._page, status, size=10, color=t.MUTED)
        self._footer.pack(fill="x", pady=(24, 12))

    def _build_lifelines(self) -> None:
        self._lifelines = tk.Frame(self._main, bg=t.BACKGROUND)
        self._lifelines.pack(fill="x", pady=(0, 14))
        self._lifeline_items: list[HexButton] = []
        for index, label in enumerate(t.LIFELINE_NAMES):
            control = HexButton(self._lifelines, label,
                                lambda i=index: self._activate_lifeline(i))
            control.set_enabled(False)
            control.paint(t.DISABLED, t.OUTLINE)
            control.button.configure(bg=t.DISABLED, highlightbackground=t.DISABLED,
                                      font=("Arial", 11, "bold"))
            control.grid(row=0, column=index, sticky="nsew",
                         padx=(0 if index == 0 else 8, 0))
            self._lifelines.columnconfigure(index, weight=1, uniform="lifeline")
            self._lifeline_items.append(control)

    def _build_progress(self) -> None:
        self._progress_panel = HexPanel(self._main, border=t.CYAN, inset=24, padding=12)
        self._progress_panel.pack(fill="x")
        self._progress_label = self._label(self._progress_panel.content, size=14,
                                           bg=t.PANEL, bold=True)
        self._progress_label.configure(wraplength=600)
        self._progress_label.pack(fill="x")
        self._timer_label = self._label(
            self._progress_panel.content, "Activa un comodín para iniciar los 30 segundos",
            size=11, color=t.GOLD_LIGHT, bg=t.PANEL,
        )
        self._timer_label.pack(fill="x", pady=(6, 0))
        self._dots = tk.Canvas(self._progress_panel.content, height=33,
                               bg=t.PANEL, highlightthickness=0, takefocus=False)
        self._dots.pack(fill="x", pady=(6, 0))
        self._dots.bind("<Configure>", lambda _e: self._draw_progress())

    def _build_ladder(self) -> None:
        self._ladder = tk.Frame(self._body, bg=t.PANEL, padx=16, pady=20,
                                highlightbackground=t.GOLD, highlightthickness=2)
        self._ladder_title = tk.Label(
            self._ladder, text="Camino a la\nvictoria", bg=t.PANEL,
            fg=t.GOLD_LIGHT, font=("Georgia", 21, "bold"), justify="center",
        )
        self._ladder_title.pack(fill="x", pady=(0, 14))
        self._level_frame = tk.Frame(self._ladder, bg=t.PANEL)
        self._level_frame.pack(fill="x")
        self._levels: dict[int, tk.Label] = {}
        for level in range(self._game.questions_per_game, 0, -1):
            label = tk.Label(self._level_frame, bg=t.DISABLED, fg=t.TEXT,
                             font=("Arial", 13, "bold"), padx=10, pady=12,
                             anchor="w", highlightthickness=1,
                             highlightbackground=t.OUTLINE)
            label.pack(fill="x", pady=4)
            self._levels[level] = label
        self._rule_label = self._label(self._ladder, size=11, color=t.MUTED, bg=t.PANEL)
        self._rule_label.pack(fill="x", pady=(14, 0))

    # Pantallas: solo consumen el estado del servicio existente.
    def _show_start_screen(self) -> None:
        self._screen = "start"
        self._progress_label.configure(text="Tu próxima partida empieza aquí")
        self._question_label.configure(text="¿Cuánto sabes de Quito?")
        self._feedback.configure(
            text=f"Responde {self._game.questions_per_game} preguntas. "
                 f"Con {self._game.correct_answers_to_win} aciertos o más se enciende el relé.",
        )
        self._play_button.pack(fill="x", padx=36, pady=(4, 10))
        if self._game.questions_per_game != 5:
            self._subtitle.configure(text=f"Responde {self._game.questions_per_game} preguntas y gana")
        self._update_progress()
        self._sync_lifelines()

    def _show_question(self) -> None:
        self._stop_timer()
        self._lifeline_used.clear()
        self._screen = "question"
        self._answer_pending = False
        question = self._game.current_question
        self._question_label.configure(text=question.text)
        self._feedback.configure(text="Elige una respuesta para continuar. Se envía al seleccionarla.",
                                  fg=t.MUTED)
        self._clear_options()
        self._options_frame.pack(fill="x", before=self._feedback)
        for index, option in enumerate(question.options):
            button = HexButton(self._options_frame, f"{chr(ord('A') + index)}:  {option.text}",
                               lambda i=index: self._on_answer(i))
            self._option_buttons.append(button)
        self._layout_answers()
        self._update_progress()
        self._schedule_layout()
        self._timer_label.configure(
            text="Activa un comodín para iniciar los 30 segundos", fg=t.GOLD_LIGHT)
        self._sync_lifelines()

    def _show_result(self) -> None:
        self._stop_timer()
        result = self._game.result()
        self._screen = "result"
        self._clear_options()
        if result.timed_out:
            self._progress_label.configure(text="Partida terminada · Tiempo agotado")
            message = "Tiempo agotado\nPerdiste la partida."
            self._timer_label.configure(text="00:00 · Sin respuesta", fg=t.WRONG_BORDER)
            self._feedback.configure(
                text=f"No respondiste en {t.LIFELINE_SECONDS} segundos. "
                     f"Aciertos: {result.score} de {result.total}.", fg=t.WRONG_BORDER)
        else:
            self._progress_label.configure(
                text=f"Partida completada · {result.score} de {result.total} aciertos")
            self._timer_label.configure(text="Partida finalizada", fg=t.MUTED)
        if result.won:
            message = f"¡Ganaste!\n{result.score} de {result.total} aciertos"
            self._feedback.configure(text="¡Se enciende el relé!", fg=t.CORRECT_BORDER)
            self._relay.turn_on()
            self._schedule_relay_off()
        elif not result.timed_out:
            message = f"Puntaje: {result.score} de {result.total}\nInténtalo de nuevo."
            self._feedback.configure(
                text=f"La meta es {self._game.correct_answers_to_win} aciertos. Puedes volver a jugar.",
                fg=t.MUTED,
            )
        self._question_label.configure(text=message)
        self._play_button.set_text("Jugar de nuevo")
        self._play_button.pack(fill="x", padx=36, pady=(4, 10))
        self._update_progress()
        self._sync_lifelines()
        self._play_button.button.focus_set()

    def _start_game(self) -> None:
        self._stop_timer()
        self._play_button.set_enabled(False)
        try:
            self._game.start()
        except ValueError as error:
            self._screen = "error"
            self._answer_pending = False
            self._answered_count = 0
            self._completed.clear()
            self._clear_options()
            self._progress_label.configure(text="No se pudo iniciar · Reintenta la partida")
            self._question_label.configure(text="No se pudo iniciar la partida")
            self._feedback.configure(text=str(error), fg=t.WRONG_BORDER)
            self._play_button.set_text("Reintentar")
            self._timer_label.configure(text="Cronómetro detenido", fg=t.MUTED)
            self._sync_lifelines()
            self._play_button.pack(fill="x", padx=36, pady=(4, 10))
            self._update_progress()
            self._schedule_layout()
            messagebox.showerror(t.WINDOW_TITLE, str(error), parent=self)
            return
        finally:
            self._play_button.set_enabled(True)
        self._answered_count = 0
        self._completed.clear()
        self._play_button.pack_forget()
        self._show_question()
        self._viewport.yview_moveto(0)

    def _on_answer(self, selected_index: int) -> None:
        if self._screen != "question" or self._answer_pending:
            return
        # Comprobar también aquí cierra la carrera entre el clic y el tick de Tk.
        if self._countdown.expired:
            self._on_timeout()
            return
        if selected_index in self._game.eliminated_options:
            return
        self._answer_pending = True
        self._stop_timer()
        self._timer_label.configure(text="Respuesta enviada · Cronómetro detenido", fg=t.MUTED)
        self._sync_lifelines()
        question = self._game.current_question
        was_correct = self._game.submit_answer(selected_index)
        self._answered_count = self._game.current_number
        self._completed[self._game.current_number] = was_correct
        for index, (button, option) in enumerate(zip(self._option_buttons, question.options)):
            button.show_feedback(correct=option.is_correct, selected=index == selected_index)
        self._feedback.configure(
            text="¡Respuesta correcta!" if was_correct else "Respuesta incorrecta. La opción correcta está indicada.",
            fg=t.CORRECT_BORDER if was_correct else t.WRONG_BORDER,
        )
        self._update_progress()
        self._next_job = self.after(t.FEEDBACK_DELAY_MS, self._go_next)

    def _activate_lifeline(self, index: int) -> None:
        if self._screen != "question" or self._answer_pending or index in self._lifeline_used:
            return
        if self._countdown.expired:
            self._on_timeout()
            return
        if index == t.FIFTY_FIFTY_INDEX:
            try:
                eliminated = self._game.use_fifty_fifty()
            except ValueError as error:
                self._feedback.configure(text=str(error), fg=t.WRONG_BORDER)
                return
            for option_index in eliminated:
                self._option_buttons[option_index].set_enabled(False)
            self._layout_answers()
            text = "50:50 eliminó dos opciones incorrectas. Elige entre las restantes."
        else:
            text = "Cuenta regresiva activada. Responde antes de que llegue a cero."
        self._lifeline_used.add(index)
        self._feedback.configure(text=text, fg=t.MUTED)
        self._countdown.start()
        self._sync_lifelines()
        if self._timer_job is None:
            self._tick_countdown()

    def _sync_lifelines(self) -> None:
        compact = self._layout_mode is not None and self._layout_mode[0]
        playing = self._screen == "question" and not self._answer_pending
        for index, (control, name) in enumerate(zip(self._lifeline_items, t.LIFELINE_NAMES)):
            used = index in self._lifeline_used
            available = playing and not used
            if index == t.FIFTY_FIFTY_INDEX:
                available = available and self._game.can_use_fifty_fifty
            status = "Quitar 2 · 30 s" if index == t.FIFTY_FIFTY_INDEX else "Activar 30 s"
            if used:
                status = "Usado"
            elif not playing:
                status = "Al jugar" if self._screen == "start" else "No disponible"
            elif not available:
                status = "No disponible"
            control.set_text(f"{name} · {status}" if compact else f"{name}\n{status}")
            control.set_enabled(available)
            fill = t.PANEL if available or used else t.DISABLED
            border = t.GOLD if available else t.CYAN if used else t.OUTLINE
            control.paint(fill, border)
            control.button.configure(bg=fill, highlightbackground=fill)

    def _tick_countdown(self) -> None:
        self._timer_job = None
        if self._screen != "question" or self._answer_pending or not self._countdown.running:
            return
        seconds = self._countdown.remaining
        self._timer_label.configure(
            text=f"Tiempo para responder: 00:{seconds:02d}",
            fg=t.WRONG_BORDER if seconds <= t.TIMER_WARNING_SECONDS else t.GOLD_LIGHT,
        )
        if self._countdown.expired:
            self._on_timeout()
        else:
            self._timer_job = self.after(t.TIMER_REFRESH_MS, self._tick_countdown)

    def _stop_timer(self) -> None:
        if self._timer_job is not None:
            self.after_cancel(self._timer_job)
            self._timer_job = None
        self._countdown.cancel()

    def _on_timeout(self) -> None:
        if self._screen != "question" or self._answer_pending:
            return
        self._answer_pending = True
        self._game.expire_question()
        self._show_result()

    def _go_next(self) -> None:
        self._next_job = None
        if self._game.advance():
            self._show_question()
        else:
            self._show_result()

    def _schedule_relay_off(self) -> None:
        def turn_off() -> None:
            self._relay_jobs.discard(job)
            self._relay.turn_off()
        job = self.after(self._relay_delay_ms, turn_off)
        self._relay_jobs.add(job)

    def _on_close(self) -> None:
        self._stop_timer()
        for job in (self._layout_job, self._next_job, *self._relay_jobs):
            if job is not None:
                self.after_cancel(job)
        self._relay.close()
        self.destroy()

    def _clear_options(self) -> None:
        for button in self._option_buttons:
            button.destroy()
        self._option_buttons.clear()
        self._options_frame.pack_forget()

    # Adaptación y progreso puramente visual.
    def _display_total(self) -> int:
        if self._screen in ("question", "result"):
            return self._game.total_questions
        return self._game.questions_per_game

    def _update_progress(self) -> None:
        if self._screen == "question":
            self._progress_label.configure(
                text=f"Pregunta {self._game.current_number} de {self._game.total_questions}"
                     f"  ·  Aciertos: {self._game.score}",
            )
        current = self._game.current_number if self._screen == "question" else 0
        compact = self._layout_mode is not None and not self._layout_mode[1]
        for level, label in self._levels.items():
            active, done = level == current, level <= self._answered_count
            caption = "¡GANAS!" if level == self._display_total() else f"Pregunta {level}"
            if done:
                caption = "Correcta" if self._completed.get(level) else "Incorrecta"
            if (level == self._game.total_questions and self._screen == "result"
                    and self._game.result().won):
                caption = "¡GANAS!"
            if active and not done:
                caption = "En juego"
            if compact:
                if level == self._display_total():
                    caption = "¡GANAS!"
                else:
                    caption = "Lista" if done else "Actual" if active else "Pend."
            label.configure(
                text=f"{level}\n{caption}" if compact else f"{level}   {caption}",
                bg=t.GOLD if active else t.DISABLED,
                fg=t.BACKGROUND if active else t.GOLD_LIGHT if done else t.TEXT,
                highlightbackground=t.GOLD if active else t.OUTLINE,
            )
        self._draw_progress()

    def _draw_progress(self) -> None:
        self._dots.delete("all")
        total = self._display_total()
        width = self._dots.winfo_width()
        step = min(38, max(1, (width - 8) / max(1, total)))
        start = (width - step * (total - 1)) / 2
        for index in range(total):
            number = index + 1
            done = number <= self._answered_count
            active = self._screen == "question" and number == self._game.current_number
            x = start + step * index
            self._dots.create_oval(x - 12, 3, x + 12, 27,
                                   fill=t.GOLD if done else t.PANEL,
                                   outline=t.CYAN if active else t.GOLD if done else t.OUTLINE,
                                   width=3 if active else 1)
            self._dots.create_text(x, 15, text=str(number), font=("Arial", 10, "bold"),
                                   fill=t.BACKGROUND if done else t.TEXT)
            if done:
                self._dots.create_line(x - 5, 31, x + 5, 31, fill=t.GOLD, width=2)

    def _schedule_layout(self, _event: tk.Event = None) -> None:
        if self._layout_job is not None:
            self.after_cancel(self._layout_job)
        self._layout_job = self.after(30, self._layout)

    def _layout(self) -> None:
        self._layout_job = None
        width = self._viewport.winfo_width()
        margin = 14 if width < t.COMPACT_WIDTH else 36
        page_width = max(1, min(t.MAX_CONTENT_WIDTH, width - margin * 2))
        self._viewport.itemconfigure(self._page_window, width=page_width)
        self._viewport.coords(self._page_window, (width - page_width) / 2, 18)
        compact, sidebar = width < t.COMPACT_WIDTH, width >= t.SIDEBAR_WIDTH
        total = self._display_total()
        self._title.configure(font=("Georgia", 25 if compact else 46, "bold italic"),
                              wraplength=page_width - 12)
        self._subtitle.configure(text=f"Responde {total} preguntas y gana",
                                  font=("Arial", 12 if compact else 16), wraplength=page_width - 12)
        self._header.pack_configure(pady=(0, 16 if compact else 24))
        self._question_label.configure(font=("Arial", 17 if compact else 23, "bold"))
        if self._layout_mode != (compact, sidebar, total):
            self._layout_mode = compact, sidebar, total
            self._ladder.grid_forget()
            self._body.columnconfigure(1, minsize=260 if sidebar else 0, weight=0)
            if sidebar:
                self._ladder.grid(row=0, column=1, padx=(22, 0), sticky="new")
                self._ladder_title.configure(text="Camino a la\nvictoria", font=("Georgia", 21, "bold"))
            else:
                self._ladder.grid(row=1, column=0, pady=(14, 0), sticky="ew")
                self._ladder_title.configure(text="Camino a la victoria", font=("Georgia", 16, "bold"))
            for control in self._lifeline_items:
                control.grid_forget()
            for column in range(3):
                self._lifelines.columnconfigure(column, weight=1 if not compact or column == 0 else 0,
                                                  uniform="lifeline" if not compact else "")
            for index, control in enumerate(self._lifeline_items):
                control.set_padding(5 if compact else 10)
                control.button.configure(font=("Arial", 10 if compact else 11, "bold"),
                                          pady=2 if compact else 5)
                control.grid(row=index if compact else 0, column=0 if compact else index,
                             sticky="nsew", pady=2 if compact else 0,
                             padx=(0 if compact or index == 0 else 8, 0))
            for label in self._levels.values():
                label.pack_forget()
                label.grid_forget()
            for column in range(self._game.questions_per_game):
                self._level_frame.columnconfigure(column, weight=0, uniform="")
            for level, label in self._levels.items():
                if level > total:
                    continue
                if sidebar:
                    label.pack(fill="x", pady=4)
                    label.configure(font=("Arial", 13, "bold"), anchor="w", pady=12, padx=10)
                else:
                    column = total - level
                    label.grid(row=0, column=column, sticky="nsew", padx=2)
                    label.configure(font=("Arial", 9, "bold"), anchor="center", pady=8, padx=2)
                    self._level_frame.columnconfigure(column, weight=1, uniform="")
            self._rule_label.configure(
                text=f"Ganas con {self._game.correct_answers_to_win} aciertos "
                     f"de {total} preguntas.",
                wraplength=205 if sidebar else page_width - 55,
            )
        self._fit_content()
        self._sync_lifelines()
        self._update_progress()
        self._update_scrollregion()

    def _fit_content(self, _event: tk.Event = None) -> None:
        if self._layout_mode is None:
            return
        compact, _sidebar, _total = self._layout_mode
        main_width = self._main.winfo_width()
        self._question_label.configure(wraplength=max(100, main_width - 90))
        self._feedback.configure(wraplength=max(100, main_width - 20))
        self._progress_label.configure(wraplength=max(100, main_width - 65))
        self._timer_label.configure(wraplength=max(100, main_width - 65))
        self._footer.configure(wraplength=max(100, self._page.winfo_width() - 12))
        for control in self._lifeline_items:
            control.set_wraplength(main_width if compact else (main_width - 16) // 3)
        self._layout_answers()
        self._play_button.set_wraplength(main_width - 72)

    def _layout_answers(self) -> None:
        columns = 1 if self._viewport.winfo_width() < t.COMPACT_WIDTH else 2
        main_width = self._main.winfo_width()
        for column in range(2):
            self._options_frame.columnconfigure(column, weight=1 if column < columns else 0,
                                                uniform="answer" if column < columns else "")
        visible_index = 0
        for index, button in enumerate(self._option_buttons):
            if index in self._game.eliminated_options:
                button.grid_remove()
                continue
            button.grid(row=visible_index // columns, column=visible_index % columns,
                        sticky="nsew", padx=(0 if visible_index % columns == 0 else 10, 0), pady=5)
            button.set_wraplength((main_width - 10 * (columns - 1)) // columns)
            button.button.configure(font=("Arial", 13 if columns == 1 else 15, "bold"))
            visible_index += 1

    def _update_scrollregion(self, _event: tk.Event = None) -> None:
        height = self._page.winfo_reqheight() + 48
        viewport_height = self._viewport.winfo_height()
        width = self._viewport.winfo_width()
        self._viewport.configure(scrollregion=(0, 0, width, max(height, viewport_height)))
        visible = bool(self._scrollbar.winfo_manager())
        if height > viewport_height and not visible:
            self._scrollbar.pack(side="right", fill="y")
        elif height <= viewport_height and visible:
            self._scrollbar.pack_forget()
        self._viewport.draw(width, max(height, viewport_height))

    def _scroll(self, units: int) -> str:
        self._viewport.yview_scroll(units, "units")
        return "break"

    def _on_wheel(self, event: tk.Event) -> str:
        return self._scroll(-1 if event.delta > 0 else 1)

    def _reveal_focus(self, event: tk.Event) -> None:
        widget = event.widget
        if not isinstance(widget, tk.Button):
            return
        top = widget.winfo_rooty() - self._viewport.winfo_rooty()
        bottom = top + widget.winfo_height()
        height = self._viewport.winfo_height()
        if top < 0 or bottom > height:
            delta = top - 16 if top < 0 else bottom - height + 16
            region = self._viewport.cget("scrollregion").split()
            if region:
                total = float(region[3])
                self._viewport.yview_moveto((self._viewport.canvasy(0) + delta) / max(1, total))
