"""Presentación vectorial con botones Tkinter nativos y foco visible."""

import tkinter as tk
from typing import Callable

from src.ui import theme as t


class Stage(tk.Canvas):
    """Luces y pista estáticas: sin imágenes ni animaciones."""

    def draw(self, width: int, height: int) -> None:
        self.delete("stage")
        self.create_rectangle(0, 0, width, height, fill=t.BACKGROUND,
                              outline="", tags="stage")
        for side in (0, width):
            direction = 1 if side == 0 else -1
            for spread, color in ((190, "#061637"), (125, "#08214e"),
                                  (65, "#0a2b67"), (22, "#104398")):
                self.create_polygon(
                    side + direction * 65, 0,
                    side + direction * (65 + spread), height,
                    side - direction * spread, height,
                    fill=color, outline="", tags="stage",
                )
        for inset, color in ((18, "#122758"), (30, "#214a91"),
                             (38, t.GOLD_DARK), (42, t.GOLD)):
            self.create_oval(inset, height - 115, width - inset, height + 50,
                             outline=color, width=2, tags="stage")
        self.create_line(width * .2, 3, width * .5, 0, width * .8, 3,
                         fill="#2777d3", width=2, tags="stage")
        self.tag_lower("stage")


class HexPanel(tk.Canvas):
    """Hexágono cuya altura sigue al contenido, incluido texto multilínea."""

    def __init__(self, master: tk.Misc, *, fill: str = t.PANEL,
                 border: str = t.GOLD, inset: int = 26,
                 padding: int = 14) -> None:
        super().__init__(master, bg=t.BACKGROUND, highlightthickness=0,
                         bd=0, width=1, height=80, takefocus=False)
        self.fill, self.border = fill, border
        self.inset, self.padding = inset, padding
        self.content = tk.Frame(self, bg=fill)
        self._window = self.create_window(inset, padding, anchor="nw",
                                          window=self.content)
        self.content.bind("<Configure>", self._measure)
        self.bind("<Configure>", self._resize)
        self.after_idle(self._measure)

    def _measure(self, _event: tk.Event = None) -> None:
        height = self.content.winfo_reqheight() + self.padding * 2
        if int(self.cget("height")) != height:
            self.configure(height=height)
        self._draw()

    def _resize(self, event: tk.Event) -> None:
        self.itemconfigure(self._window, width=max(1, event.width - self.inset * 2))
        self._measure()

    def paint(self, fill: str, border: str) -> None:
        self.fill, self.border = fill, border
        self.content.configure(bg=fill)
        self._draw()

    def set_padding(self, padding: int) -> None:
        self.padding = padding
        self.coords(self._window, self.inset, padding)
        self._measure()

    def _draw(self) -> None:
        w, h = self.winfo_width(), self.winfo_height()
        tip = min(self.inset - 5, h / 3)
        self.delete("shape")
        self.create_polygon(
            2, h / 2, tip + 2, 3, w - tip - 2, 3,
            w - 2, h / 2, w - tip - 2, h - 3, tip + 2, h - 3,
            fill=self.fill, outline=self.border, width=2, tags="shape",
        )
        self.create_line(tip + 4, 5, w - tip - 4, 5,
                         fill=t.GOLD_LIGHT if self.border == t.GOLD else self.border,
                         tags="shape")
        self.tag_lower("shape")


class HexButton(HexPanel):
    """Silueta decorativa alrededor de un botón semántico de Tk."""

    def __init__(self, master: tk.Misc, text: str, command: Callable[[], None],
                 *, primary: bool = False) -> None:
        self._primary = primary
        self._base_fill = t.GOLD if primary else t.PANEL
        self._base_border = t.GOLD
        foreground = t.BACKGROUND if primary else t.TEXT
        super().__init__(master, fill=self._base_fill, padding=10, inset=25)
        self.button = tk.Button(
            self.content, text=text, command=command, width=1, wraplength=250,
            bg=self._base_fill, fg=foreground, relief="flat", bd=0,
            activebackground=t.GOLD_LIGHT if primary else t.PANEL_HOVER,
            activeforeground=foreground, font=("Arial", 15, "bold"),
            disabledforeground=t.MUTED, highlightthickness=0,
            highlightbackground=self._base_fill, highlightcolor=t.CYAN,
            cursor="hand2", padx=2, pady=5, takefocus=False,
        )
        self.button.pack(fill="x")
        self.button.bind("<Return>", self._keyboard_invoke)
        self.button.bind("<KP_Enter>", self._keyboard_invoke)
        self.button.bind("<Enter>", lambda _e: self._interaction(True))
        self.button.bind("<Leave>", lambda _e: self._interaction(False))
        self.button.bind("<FocusIn>", lambda _e: self._interaction(True))
        self.button.bind("<FocusOut>", lambda _e: self._interaction(False))
        self.bind("<Button-1>", lambda _e: self.button.invoke())

    def _keyboard_invoke(self, _event: tk.Event) -> str:
        self.button.invoke()
        return "break"

    def _interaction(self, active: bool) -> None:
        if str(self.button.cget("state")) == "disabled":
            return
        focused = self.focus_get() == self.button
        fill = (t.GOLD_LIGHT if self._primary else t.PANEL_HOVER) if active else self._base_fill
        self.paint(fill, t.CYAN if active or focused else self._base_border)
        self.button.configure(bg=fill, highlightbackground=fill)

    def set_wraplength(self, width: int) -> None:
        self.button.configure(wraplength=max(48, width - self.inset * 2 - 16))

    def set_text(self, text: str) -> None:
        self.button.configure(text=text)

    def set_enabled(self, enabled: bool) -> None:
        self.button.configure(state="normal" if enabled else "disabled",
                              takefocus=enabled, cursor="hand2" if enabled else "arrow")

    def show_feedback(self, *, correct: bool, selected: bool) -> None:
        self.set_enabled(False)
        if correct:
            fill, border, color = t.CORRECT, t.CORRECT_BORDER, t.TEXT
            status = "Tu respuesta · Correcta" if selected else "Respuesta correcta"
        elif selected:
            fill, border, color = t.WRONG, t.WRONG_BORDER, t.TEXT
            status = "Tu respuesta · Incorrecta"
        else:
            fill, border, color = t.DISABLED, t.OUTLINE, t.MUTED
            status = "Sin seleccionar"
        self._base_fill, self._base_border = fill, border
        self.paint(fill, border)
        self.button.configure(
            bg=fill, disabledforeground=color, highlightbackground=fill,
            text=f"{self.button.cget('text')}\n{status}",
        )
