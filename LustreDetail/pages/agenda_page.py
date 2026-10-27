"""Agenda: lista filtrável de agendamentos com ações de visualizar, editar e cancelar."""
from datetime import timedelta

import customtkinter as ctk

from components.appointments_table import AppointmentsTable
from components.filter_chips import FilterChips
from components.page_header import PageHeader
from components.widgets import entry, label, search_box
from utils import colors as C
from utils.formatting import parse_date_br

from .base_page import BasePage

DATE_OPTIONS = [("today", "Hoje"), ("tomorrow", "Amanhã"), ("7d", "Próximos 7 dias"), ("all", "Todos")]
STATUS_OPTIONS = [("all", "Todos os status"), ("scheduled", "Agendado"), ("in_progress", "Em andamento"),
                  ("done", "Concluído"), ("cancelled", "Cancelado")]


class AgendaPage(BasePage):
    def build(self) -> None:
        c, actions = self.content, self.app.appt_actions
        c.grid_rowconfigure(3, weight=1)
        self.header = PageHeader(c, "Agenda", "Gerencie os agendamentos da oficina.",
                                 actions=[("Novo agendamento", self.app.open_appointment_dialog, "primary", "plus")])
        self.header.grid(row=0, column=0, sticky="ew")

        bar = ctk.CTkFrame(c, fg_color="transparent")
        bar.grid(row=1, column=0, sticky="ew", pady=(18, 0))
        frame, self.search_entry = search_box(bar, "Buscar cliente, placa ou serviço…", 280,
                                              on_change=lambda t: self.refresh())
        frame.grid(row=0, column=0, padx=(0, 16))
        self.date_chips = FilterChips(bar, DATE_OPTIONS, self._on_date_chip, selected="today")
        self.date_chips.grid(row=0, column=1, padx=(0, 12))
        self.date_entry = entry(bar, "dd/mm/aaaa", width=110)
        self.date_entry.grid(row=0, column=2)
        self.date_entry.bind("<KeyRelease>", lambda e: self._on_date_typed(), add="+")

        self.status_chips = FilterChips(c, STATUS_OPTIONS, lambda k: self.refresh(), selected="all")
        self.status_chips.grid(row=2, column=0, sticky="w", pady=(12, 12))

        self.table = AppointmentsTable(
            c, self.repo.today, mode="full", on_view=actions.view, on_edit=actions.edit,
            on_cancel=actions.cancel, on_more=lambda v, btn: actions.more_menu(v, btn))
        self.table.grid(row=3, column=0, sticky="nsew")

    # ----------------------------------------------------------------- filtros
    def _on_date_chip(self, _key) -> None:
        self.date_entry.delete(0, "end")  # chip assume o controle
        self.refresh()

    def _on_date_typed(self) -> None:
        text = self.date_entry.get().strip()
        if not text:
            self.date_chips.select("today", notify=False)
            self.refresh()
            return
        try:
            parse_date_br(text)
        except ValueError:
            return  # ainda digitando
        self.date_chips.clear_selection()
        self.refresh()

    def _date_range(self):
        text = self.date_entry.get().strip()
        if text:
            try:
                d = parse_date_br(text).isoformat()
                return d, d
            except ValueError:
                pass
        key, t = self.date_chips.value, self.repo.today()
        if key == "today":
            return t.isoformat(), t.isoformat()
        if key == "tomorrow":
            d = (t + timedelta(days=1)).isoformat()
            return d, d
        if key == "7d":
            return t.isoformat(), (t + timedelta(days=6)).isoformat()
        return None, None

    def refresh(self) -> None:
        start, end = self._date_range()
        status = self.status_chips.value
        views = self.repo.appointment_views(
            self.search_text(), start, end, None if status in (None, "all") else status,
            newest_first=(start is None))
        self.table.set_rows(views, keep_page=False)
        self.header.set_subtitle(f"{len(views)} agendamento(s) encontrado(s) · "
                                 f"capacidade de {self.repo.capacity} simultâneo(s)")
