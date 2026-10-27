"""Selo de status (Agendado, Em andamento, Concluído, Cancelado, Pendente...)."""
import customtkinter as ctk

from utils.fonts import text_font
from utils.theme import STATUS_STYLES


class StatusBadge(ctk.CTkLabel):
    """Selo compacto; as cores vêm de ``utils.theme.STATUS_STYLES``."""

    def __init__(self, master, status: str):
        text, fg, bg = STATUS_STYLES[status]
        super().__init__(master, text=f"  {text}  ", font=text_font(11, "bold"),
                         text_color=fg, fg_color=bg, corner_radius=4, height=22)

    def set_status(self, status: str) -> None:
        text, fg, bg = STATUS_STYLES[status]
        self.configure(text=f"  {text}  ", text_color=fg, fg_color=bg)
