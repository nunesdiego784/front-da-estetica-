"""Etiqueta compacta com a placa do veículo."""
import customtkinter as ctk

from utils import colors as C
from utils.fonts import display_font
from utils.formatting import format_plate


class PlateTag(ctk.CTkFrame):
    """Mostra a placa (ABC1D23 ou ABC-1234) dentro de uma moldura fina."""

    def __init__(self, master, plate: str):
        super().__init__(master, fg_color=C.BG, border_width=1, border_color=C.TEXT_MUTED,
                         corner_radius=4)
        ctk.CTkLabel(self, text=format_plate(plate) or "—", font=display_font(14, "bold"),
                     text_color=C.TEXT, height=20, width=0).grid(row=0, column=0, padx=8, pady=1)
