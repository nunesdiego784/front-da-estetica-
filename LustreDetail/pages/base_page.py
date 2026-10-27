"""Página base: layout padrão, rolagem opcional, busca e ciclo de atualização."""
import customtkinter as ctk

from utils import colors as C
from utils.theme import PAGE_PAD_X


class BasePage(ctk.CTkFrame):
    """Todas as páginas herdam daqui.

    Subclasses implementam ``build()`` (cria widgets uma única vez) e ``refresh()``
    (relê os dados). Quando os dados mudam, o app marca as páginas como 'sujas' e
    a página visível é atualizada na hora; as demais, ao serem abertas.
    """

    scrollable = False

    def __init__(self, master, app):
        super().__init__(master, fg_color=C.BG, corner_radius=0)
        self.app = app
        self.repo = app.repo
        self.dirty = True
        self.search_entry = None
        self.grid_rowconfigure(0, weight=1)
        self.grid_columnconfigure(0, weight=1)
        if self.scrollable:
            self.body = ctk.CTkScrollableFrame(self, fg_color=C.BG, corner_radius=0,
                                               scrollbar_button_color=C.BORDER,
                                               scrollbar_button_hover_color=C.TEXT_MUTED)
        else:
            self.body = ctk.CTkFrame(self, fg_color=C.BG, corner_radius=0)
        self.body.grid(row=0, column=0, sticky="nsew")
        self.body.grid_columnconfigure(0, weight=1)
        self.body.grid_rowconfigure(0, weight=1)
        self.content = ctk.CTkFrame(self.body, fg_color="transparent")
        self.content.grid(row=0, column=0, sticky="nsew", padx=PAGE_PAD_X, pady=(24, 24))
        self.content.grid_columnconfigure(0, weight=1)
        self.build()

    # --- ciclo de vida -------------------------------------------------------
    def build(self) -> None:
        raise NotImplementedError

    def refresh(self) -> None:
        raise NotImplementedError

    def on_show(self) -> None:
        """Chamado quando a página passa a ser a visível."""
        if self.dirty:
            self.dirty = False
            self.refresh()

    def mark_dirty(self) -> None:
        self.dirty = True

    # --- busca ---------------------------------------------------------------
    def search_text(self) -> str:
        return self.search_entry.get().strip() if self.search_entry is not None else ""

    def focus_search(self) -> bool:
        """Foca o campo de busca da página (Ctrl+F). False se a página não tiver."""
        if self.search_entry is None:
            return False
        self.search_entry.focus_set()
        return True

    def set_search(self, text: str) -> None:
        if self.search_entry is not None:
            self.search_entry.delete(0, "end")
            self.search_entry.insert(0, text or "")
            self.refresh()
