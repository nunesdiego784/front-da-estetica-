"""Mensagens rápidas (sucesso, alerta, erro) no canto inferior direito."""
import customtkinter as ctk

from utils import colors as C
from utils.theme import RADIUS

from .widgets import label

_KIND = {"success": C.SUCCESS, "warning": C.ACCENT, "error": C.DANGER}


class ToastManager:
    """Empilha toasts que desaparecem sozinhos."""

    WIDTH, HEIGHT, GAP = 380, 58, 8

    def __init__(self, app):
        self.app = app
        self._toasts: list = []

    def show(self, message: str, kind: str = "success", duration: int = 3600) -> None:
        """Exibe uma mensagem. ``kind``: success, warning ou error."""
        color = _KIND.get(kind, C.SUCCESS)
        frame = ctk.CTkFrame(self.app, width=self.WIDTH, height=self.HEIGHT,
                             fg_color=C.SURFACE_HOVER, border_width=1,
                             border_color=C.tint(color, 0.55, C.SURFACE_HOVER), corner_radius=RADIUS)
        frame.grid_propagate(False)
        frame.grid_columnconfigure(1, weight=1)
        frame.grid_rowconfigure(0, weight=1)
        ctk.CTkFrame(frame, width=4, fg_color=color, corner_radius=2).grid(
            row=0, column=0, sticky="ns", padx=(8, 0), pady=10)
        label(frame, message, 13, C.TEXT, height=self.HEIGHT - 12, wraplength=self.WIDTH - 50,
              justify="left").grid(row=0, column=1, sticky="w", padx=12)
        self._toasts.append(frame)
        while len(self._toasts) > 4:
            self._remove(self._toasts[0])
        self._layout()
        self.app.after(duration, lambda f=frame: self._remove(f))

    def _remove(self, frame) -> None:
        if frame in self._toasts:
            self._toasts.remove(frame)
            try:
                frame.destroy()
            except Exception:
                pass
            self._layout()

    def _layout(self) -> None:
        for i, frame in enumerate(reversed(self._toasts)):
            frame.place(relx=1.0, rely=1.0, x=-24, y=-(24 + i * (self.HEIGHT + self.GAP)), anchor="se")
            frame.lift()
