"""Barra de navegação superior fixa (64 px): logo, menu, busca, notificações e usuário."""
from typing import Callable

import customtkinter as ctk

from utils import colors as C
from utils import theme
from utils.fonts import text_font

from .nav_link import NavLink
from .widgets import bind_hover, icon_button, label, search_box


class TopNav(ctk.CTkFrame):
    """Navegação principal. Nenhuma sidebar: todo o menu fica no topo."""

    def __init__(self, master, app, items, on_navigate: Callable, user_name: str = "Admin"):
        super().__init__(master, fg_color=C.BG, height=theme.NAV_HEIGHT, corner_radius=0)
        self.app = app
        self._on_navigate = on_navigate
        self._links: dict = {}
        self.grid_propagate(False)
        self.grid_rowconfigure(0, weight=1)
        self.grid_columnconfigure(2, weight=1)

        logo = ctk.CTkFrame(self, fg_color="transparent")
        logo.grid(row=0, column=0, padx=(24, 20), sticky="w")
        label(logo, "LUSTRE", 24, C.TEXT, "bold", display=True, height=30, width=0).pack(side="left")
        label(logo, "DETAIL", 24, C.ACCENT, "bold", display=True, height=30, width=0).pack(side="left", padx=(6, 0))

        links = ctk.CTkFrame(self, fg_color="transparent")
        links.grid(row=0, column=1, sticky="w")
        for i, (key, text) in enumerate(items):
            link = NavLink(links, text, lambda k=key: self._on_navigate(k))
            link.grid(row=0, column=i)
            self._links[key] = link

        right = ctk.CTkFrame(self, fg_color="transparent")
        right.grid(row=0, column=3, padx=(8, 20), sticky="e")
        self.search_frame, self.search_entry = search_box(
            right, "Buscar…", width=170, on_change=self._on_search)
        self.search_entry.bind("<Return>", lambda e: self._open_first_result(), add="+")
        self.search_entry.bind("<Escape>", lambda e: self._clear_search(), add="+")
        self.search_frame.grid(row=0, column=0, padx=(0, 10))

        bell_box = ctk.CTkFrame(right, fg_color="transparent", width=36, height=36)
        bell_box.grid(row=0, column=1, padx=(0, 6))
        bell_box.grid_propagate(False)
        self.bell = icon_button(bell_box, "bell", lambda: self._toggle_notifications(), size=34)
        self.bell.place(x=1, y=1)
        self.badge = ctk.CTkFrame(bell_box, width=8, height=8, corner_radius=4, fg_color=C.ACCENT)

        self.avatar = ctk.CTkButton(
            right, text=user_name[:2].upper(), width=32, height=32, corner_radius=16,
            fg_color=C.SURFACE_HOVER, hover_color=C.BORDER, border_width=1, border_color=C.BORDER,
            text_color=C.ACCENT, font=text_font(12, "bold"), command=self._toggle_user_menu)
        self.avatar.grid(row=0, column=2)
        label(right, user_name, 13, C.TEXT, height=22, width=0).grid(row=0, column=3, padx=(8, 0))

        self._results: list = []
        self.refresh_notifications()

    # ------------------------------------------------------------- navegação
    def set_active(self, key: str) -> None:
        for k, link in self._links.items():
            link.set_active(k == key)

    # ------------------------------------------------------------------ busca
    def focus_search(self) -> None:
        self.search_entry.focus_set()

    def _on_search(self, text: str) -> None:
        self._results = self.app.repo.global_search(text)
        if len(text.strip()) < 2:
            self.app.popovers.close()
            return
        self.app.popovers.show_custom(self.search_frame, self._build_results, width=330,
                                      align="right", toggle=False)

    def _build_results(self, frame) -> None:
        if not self._results:
            label(frame, "Nenhum resultado.", 13, C.TEXT_MUTED, height=34, width=300).grid(padx=14, pady=6)
            return
        for i, res in enumerate(self._results):
            row = ctk.CTkFrame(frame, fg_color="transparent", corner_radius=6, width=318, height=44)
            row.grid(row=i, column=0, padx=6, pady=(6 if i == 0 else 0, 6 if i == len(self._results) - 1 else 0))
            row.grid_propagate(False)
            row.grid_columnconfigure(1, weight=1)
            row.grid_rowconfigure(0, weight=1)
            label(row, res["kind"].upper(), 10, C.ACCENT, "bold", height=16, width=84).grid(row=0, column=0, padx=(8, 0))
            label(row, res["label"], 13, C.TEXT, height=20, width=210).grid(row=0, column=1, sticky="w")
            bind_hover(row, lambda r=row: r.configure(fg_color=C.SURFACE_HOVER),
                       lambda r=row: r.configure(fg_color="transparent"))
            self._bind_click(row, lambda r=res: self._open_result(r))

    def _bind_click(self, widget, command) -> None:
        widget.bind("<Button-1>", lambda e: command(), add="+")
        for child in widget.winfo_children():
            self._bind_click(child, command)

    def _open_result(self, res: dict) -> None:
        self.app.popovers.close()
        self.app.navigate(res["page"], res["query"])

    def _open_first_result(self) -> None:
        if self._results:
            self._open_result(self._results[0])

    def _clear_search(self) -> None:
        self.search_entry.delete(0, "end")
        self.app.popovers.close()

    # ----------------------------------------------------------- notificações
    def refresh_notifications(self) -> None:
        notes = self.app.repo.notifications()
        warn = any(n["kind"] == "warning" for n in notes)
        if warn:
            self.badge.place(x=22, y=6)
            self.badge.lift()
        else:
            self.badge.place_forget()

    def _toggle_notifications(self) -> None:
        notes = self.app.repo.notifications()

        def build(frame):
            if not notes:
                label(frame, "Tudo em dia. Sem notificações.", 13, C.TEXT_MUTED, height=34, width=300
                      ).grid(padx=14, pady=8)
                return
            for i, note in enumerate(notes):
                color = C.ACCENT if note["kind"] == "warning" else C.TEXT_MUTED
                lines = max(1, -(-len(note["text"]) // 38))
                row = ctk.CTkFrame(frame, fg_color="transparent", corner_radius=6, width=328,
                                   height=lines * 19 + 18)
                row.grid(row=i, column=0, padx=6, pady=(6 if i == 0 else 0, 6 if i == len(notes) - 1 else 2))
                row.grid_propagate(False)
                row.grid_columnconfigure(1, weight=1)
                row.grid_rowconfigure(0, weight=1)
                label(row, "●", 12, color, height=18, width=18).grid(row=0, column=0, padx=(8, 0), sticky="n", pady=(9, 0))
                label(row, note["text"], 13, C.TEXT, height=lines * 19, wraplength=270, justify="left",
                      anchor="w").grid(row=0, column=1, sticky="w", padx=(4, 8))
                bind_hover(row, lambda r=row: r.configure(fg_color=C.SURFACE_HOVER),
                           lambda r=row: r.configure(fg_color="transparent"))
                self._bind_click(row, lambda n=note: self._open_result({"page": n["page"], "query": None}))

        self.app.popovers.show_custom(self.bell, build, width=340, align="right")

    # ---------------------------------------------------------------- usuário
    def _toggle_user_menu(self) -> None:
        items = [
            ("Configurações da oficina", self.app.open_settings),
            ("Sobre o Lustre Detail", self.app.show_about),
            ("Restaurar dados de demonstração", lambda: self.app.reset_data(True), True),
            ("Limpar todos os dados", lambda: self.app.reset_data(False), True),
        ]
        self.app.popovers.show_menu(self.avatar, items, width=260, align="right")
