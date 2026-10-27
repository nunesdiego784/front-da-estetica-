"""Faixa de indicadores (cartões com número grande em Barlow Condensed)."""
from dataclasses import dataclass

import customtkinter as ctk

from utils import colors as C

from .widgets import card, caption, label

_KIND_COLORS = {"positive": C.SUCCESS, "negative": C.DANGER, "warning": C.ACCENT,
                "neutral": C.TEXT_MUTED}


@dataclass
class StatData:
    """Dados de um indicador."""
    name: str
    value: str
    detail: str = ""
    status_text: str = ""
    status_kind: str = "neutral"   # positive | negative | warning | neutral


class StatStrip(ctk.CTkFrame):
    """Organiza até quatro indicadores lado a lado; ``update_stats`` atualiza os textos."""

    def __init__(self, master, count: int = 4):
        super().__init__(master, fg_color="transparent")
        self._cells = []
        for i in range(count):
            self.grid_columnconfigure(i, weight=1, uniform="stat")
            panel = card(self)
            panel.grid(row=0, column=i, sticky="nsew", padx=(0 if i == 0 else 8, 0 if i == count - 1 else 8))
            panel.grid_columnconfigure(0, weight=1)
            name = caption(panel, "")
            name.grid(row=0, column=0, sticky="w", padx=16, pady=(14, 0))
            status = label(panel, "", 11, C.TEXT_MUTED, "bold", anchor="e", height=18)
            status.grid(row=0, column=1, sticky="e", padx=(0, 16), pady=(14, 0))
            value = label(panel, "", 42, C.TEXT, "bold", display=True, height=52)
            value.grid(row=1, column=0, columnspan=2, sticky="w", padx=16)
            detail = label(panel, "", 12, C.TEXT_SECONDARY, height=20)
            detail.grid(row=2, column=0, columnspan=2, sticky="w", padx=16, pady=(0, 14))
            self._cells.append((name, status, value, detail))

    def update_stats(self, stats) -> None:
        for (name, status, value, detail), data in zip(self._cells, stats):
            name.configure(text=data.name.upper())
            value.configure(text=data.value)
            detail.configure(text=data.detail)
            status.configure(text=data.status_text,
                             text_color=_KIND_COLORS.get(data.status_kind, C.TEXT_MUTED))
