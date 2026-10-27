"""Lustre Detail — sistema de gestão para estética automotiva.

Execute com:  python main.py
"""
import sys
import traceback
from pathlib import Path

import customtkinter as ctk

from components.appointment_actions import AppointmentActions
from components.dialogs import ConfirmDialog, Field, FormDialog, InfoDialog, ModalDialog
from components.divider import Divider
from components.new_appointment_dialog import NewAppointmentDialog
from components.popover import PopoverManager
from components.toast import ToastManager
from components.top_nav import TopNav
from data.repository import Repository, RepositoryError
from pages.agenda_page import AgendaPage
from pages.clients_page import ClientsPage
from pages.dashboard_page import DashboardPage
from pages.finance_page import FinancePage
from pages.inventory_page import InventoryPage
from pages.services_page import ServicesPage
from pages.vehicles_page import VehiclesPage
from utils import colors as C
from utils import fonts, theme

APP_NAME, APP_VERSION = "Lustre Detail", "1.0.0"

PAGES = [
    ("dashboard", "Dashboard", DashboardPage),
    ("agenda", "Agenda", AgendaPage),
    ("services", "Serviços", ServicesPage),
    ("clients", "Clientes", ClientsPage),
    ("vehicles", "Veículos", VehiclesPage),
    ("inventory", "Estoque", InventoryPage),
    ("finance", "Financeiro", FinancePage),
]


class LustreApp(ctk.CTk):
    """Janela principal: barra superior fixa + página atual + atalhos globais."""

    def __init__(self):
        fonts.register_bundled_fonts()      # antes de criar a janela
        theme.apply_theme()
        super().__init__(fg_color=C.BG)
        fonts.init_fonts(self)
        self.title(APP_NAME)
        self.geometry("1280x800")
        self.minsize(1120, 720)

        self.repo = Repository()
        self.toast = ToastManager(self)
        self.popovers = PopoverManager(self)
        self.appt_actions = AppointmentActions(self)
        self._pages: dict = {}
        self.current_key = None

        self.grid_rowconfigure(2, weight=1)
        self.grid_columnconfigure(0, weight=1)
        self.nav = TopNav(self, self, [(k, t) for k, t, _ in PAGES], self.navigate)
        self.nav.grid(row=0, column=0, sticky="ew")
        Divider(self).grid(row=1, column=0, sticky="ew")
        self.container = ctk.CTkFrame(self, fg_color=C.BG, corner_radius=0)
        self.container.grid(row=2, column=0, sticky="nsew")
        self.container.grid_rowconfigure(0, weight=1)
        self.container.grid_columnconfigure(0, weight=1)

        self.repo.subscribe(self._on_data_changed)
        self.bind("<Control-n>", self._shortcut_new)
        self.bind("<Control-N>", self._shortcut_new)
        self.bind("<Control-f>", self._shortcut_find)
        self.bind("<Control-F>", self._shortcut_find)
        self.bind("<Escape>", self._shortcut_escape)

        self.navigate("dashboard")
        if self.repo.load_warning:
            self.after(400, lambda: self.toast.show(self.repo.load_warning, "warning", 9000))

    # ---------------------------------------------------------------- erros
    def report_callback_exception(self, exc, val, tb):
        """Erros inesperados de callbacks: registra em arquivo e avisa com um toast."""
        text = "".join(traceback.format_exception(exc, val, tb))
        sys.stderr.write(text)
        try:
            log = self.repo.path.parent / "error.log"
            with open(log, "a", encoding="utf-8") as fh:
                fh.write(text + "\n")
            self.toast.show("Ocorreu um erro inesperado. Detalhes em error.log.", "error", 6000)
        except Exception:
            pass

    # ------------------------------------------------------------ navegação
    def navigate(self, key: str, query=None) -> None:
        """Abre uma página (criada sob demanda) e, opcionalmente, aplica uma busca."""
        self.popovers.close()
        if key not in self._pages:
            cls = next(c for k, _, c in PAGES if k == key)
            page = cls(self.container, self)
            page.grid(row=0, column=0, sticky="nsew")
            self._pages[key] = page
        if self.current_key and self.current_key != key:
            self._pages[self.current_key].grid_remove()
        page = self._pages[key]
        page.grid()
        page.lift()
        self.current_key = key
        self.nav.set_active(key)
        page.on_show()
        if query:
            page.set_search(query)

    def _on_data_changed(self) -> None:
        for page in self._pages.values():
            page.mark_dirty()
        if self.current_key:
            self._pages[self.current_key].on_show()
        self.nav.refresh_notifications()

    # --------------------------------------------------------------- diálogos
    def open_appointment_dialog(self, appointment=None) -> None:
        def saved(appt, edited=False):
            self.toast.show("Agendamento atualizado." if edited else "Agendamento criado.")
        NewAppointmentDialog(self, self.repo, appointment, saved)

    def open_settings(self) -> None:
        s = self.repo.settings()

        def submit(v):
            self.repo.update_settings(v["capacity"], v["open"], v["close"])
            self.toast.show("Configurações salvas.")
        FormDialog(self, "Configurações da oficina", [
            Field("capacity", "Capacidade (atendimentos simultâneos)"),
            Field("open", "Abertura (HH:MM)"), Field("close", "Fechamento (HH:MM)")],
            submit, s, subtitle="Usadas para validar a agenda.")

    def show_about(self) -> None:
        rep = fonts.fonts_report()
        InfoDialog(self, f"Sobre o {APP_NAME}", [
            ("Versão", APP_VERSION),
            ("Dados salvos em", str(self.repo.path)),
            ("Fonte de texto", rep["texto"]), ("Fonte de títulos", rep["titulos"]),
            ("Modo", "Dados de demonstração" if self.repo.is_demo else "Dados reais do usuário")])

    def reset_data(self, demo: bool) -> None:
        msg = ("Substituir TODOS os dados atuais pelos dados de demonstração?" if demo
               else "Apagar TODOS os dados (clientes, veículos, agenda, estoque e financeiro)? "
                    "Esta ação não pode ser desfeita.")

        def go():
            try:
                self.repo.reset(demo)
                self.toast.show("Dados de demonstração restaurados." if demo else "Dados apagados.")
            except RepositoryError as exc:
                self.toast.show(str(exc), "error")
        ConfirmDialog(self, "Confirmar", msg, go, confirm_text="Substituir" if demo else "Apagar tudo")

    # ---------------------------------------------------------------- atalhos
    def _shortcut_new(self, _event=None):
        if ModalDialog.open_count == 0:
            self.open_appointment_dialog()
        return "break"

    def _shortcut_find(self, _event=None):
        if ModalDialog.open_count == 0:
            page = self._pages.get(self.current_key)
            if not (page and page.focus_search()):
                self.nav.focus_search()
        return "break"

    def _shortcut_escape(self, _event=None):
        self.popovers.close()


def main() -> None:
    LustreApp().mainloop()


if __name__ == "__main__":
    main()
