"""Tabela de agendamentos (modo completo na Agenda, compacto no Dashboard)."""
from typing import Callable, Optional

import customtkinter as ctk

from utils import colors as C
from utils.formatting import format_date_br, relative_day_label, truncate

from .data_table import Column, DataTable
from .plate_tag import PlateTag
from .status_badge import StatusBadge
from .widgets import action_bar, label


class AppointmentsTable(DataTable):
    """Exibe ``AppointmentView`` em colunas: horário, cliente, veículo, serviço, status.

    No modo ``full`` adiciona a coluna de ações (visualizar, editar, cancelar e mais).
    Callbacks recebem o ``AppointmentView`` (o de 'mais ações' recebe também o botão).
    """

    def __init__(self, master, today_fn: Callable, mode: str = "full",
                 on_view: Optional[Callable] = None, on_edit: Optional[Callable] = None,
                 on_cancel: Optional[Callable] = None, on_more: Optional[Callable] = None,
                 page_size: Optional[int] = None, empty_text: str = "Nenhum agendamento encontrado."):
        self._today_fn = today_fn
        self._cb = dict(view=on_view, edit=on_edit, cancel=on_cancel, more=on_more)
        full = mode == "full"
        columns = [
            Column("Horário", 92, 0, render=self._cell_when),
            Column("Cliente", 130, 2, render=self._cell_client),
            Column("Veículo", 200, 3, render=self._cell_vehicle),
            Column("Serviço", 130, 2, text=lambda v: truncate(v.service_name, 26)),
            Column("Status", 130, 0, render=lambda p, v: StatusBadge(p, v.appt.status)),
        ]
        if full:
            columns.append(Column("Ações", 150, 0, render=self._cell_actions))
        super().__init__(master, columns, row_height=54, page_size=page_size, empty_text=empty_text,
                         show_pager=full)

    # ---------------------------------------------------------------- células
    def _cell_when(self, parent, v):
        f = ctk.CTkFrame(parent, fg_color="transparent")
        label(f, v.appt.time, 20, C.TEXT, "bold", display=True, height=24).grid(row=0, column=0, sticky="w")
        day = relative_day_label(v.appt.date, self._today_fn())
        text = day if day in ("Hoje", "Amanhã", "Ontem") else format_date_br(v.appt.date)
        label(f, text, 11, C.TEXT_SECONDARY, height=16).grid(row=1, column=0, sticky="w")
        return f

    def _cell_client(self, parent, v):
        f = ctk.CTkFrame(parent, fg_color="transparent")
        label(f, truncate(v.client_name, 24), 13, C.TEXT, height=20).grid(row=0, column=0, sticky="w")
        phone = v.client.phone if v.client else ""
        label(f, phone, 11, C.TEXT_SECONDARY, height=16).grid(row=1, column=0, sticky="w")
        return f

    def _cell_vehicle(self, parent, v):
        f = ctk.CTkFrame(parent, fg_color="transparent")
        label(f, truncate(v.vehicle_label, 18), 13, C.TEXT, height=20).grid(row=0, column=0, sticky="w")
        PlateTag(f, v.plate).grid(row=0, column=1, padx=(8, 0))
        return f

    def _cell_actions(self, parent, v):
        status = v.appt.status
        actions = [("eye", lambda b, v=v: self._call("view", v), False)]
        if status == "scheduled":
            actions.append(("edit", lambda b, v=v: self._call("edit", v), False))
        if status in ("scheduled", "in_progress"):
            actions.append(("x", lambda b, v=v: self._call("cancel", v), True))
        actions.append(("dots", lambda b, v=v: self._call("more", v, b), False))
        return action_bar(parent, actions)

    def _call(self, name, view, *extra):
        cb = self._cb.get(name)
        if cb:
            cb(view, *extra)
