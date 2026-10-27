"""Diálogo para criar ou editar um agendamento."""
import math
from datetime import timedelta
from typing import Callable, Optional

import customtkinter as ctk

from data.repository import RepositoryError
from utils import colors as C
from utils.data_labels import region_options
from utils.formatting import (brl, format_date_br, format_duration, format_plate, min_to_time,
                              parse_time, time_to_min)

from .dialogs import ModalDialog
from .widgets import button, caption, combo, entry, label, textbox


def unique_labels(items, fmt) -> dict:
    """Mapeia rótulo -> id, acrescentando '#id' quando dois rótulos coincidirem."""
    out, seen = {}, {}
    for it in items:
        base = fmt(it)
        n = seen.get(base, 0)
        seen[base] = n + 1
        out[base if n == 0 else f"{base} #{it.id}"] = it.id
    return out


class NewAppointmentDialog(ModalDialog):
    """Cliente, veículo, serviço, data, horário, região do veículo e observações.

    Todas as regras (horário de funcionamento, capacidade, conflitos, datas
    passadas) são validadas pelo repositório; o diálogo mostra a mensagem de
    erro sem fechar para que o usuário corrija.
    """

    def __init__(self, master, repo, appointment=None, on_saved: Optional[Callable] = None):
        super().__init__(master, "Editar agendamento" if appointment else "Novo agendamento", 580, 640)
        self.repo, self.appointment, self._on_saved = repo, appointment, on_saved
        main, footer = self.shell("Editar agendamento" if appointment else "Novo agendamento",
                                  "Os horários respeitam o funcionamento e a capacidade configurados.")
        main.grid_columnconfigure((0, 1, 2), weight=1, uniform="col")

        cur_client = appointment.client_id if appointment else None
        cur_service = appointment.service_id if appointment else None
        clients = [c for c in repo.list_clients() if c.active or c.id == cur_client]
        self._clients = unique_labels(clients, lambda c: f"{c.name} · {c.phone}")
        services = [s for s in repo.list_services() if s.active or s.id == cur_service]
        self._services = unique_labels(
            services, lambda s: f"{s.name} · {brl(s.price_cents)} · {format_duration(s.duration_min)}")
        self._regions = {label_: val for val, label_ in region_options()}
        self._vehicles: dict = {}

        self.client_cb = self._field(main, 0, 0, 2, "Cliente", lambda p: combo(
            p, list(self._clients) or ["Nenhum cliente cadastrado"],
            command=lambda _v: self._fill_vehicles(), width=200))
        self.vehicle_cb = self._field(main, 0, 2, 1, "Veículo", lambda p: combo(p, ["—"], width=200))
        self.service_cb = self._field(main, 1, 0, 3, "Serviço", lambda p: combo(
            p, list(self._services) or ["Nenhum serviço cadastrado"],
            command=lambda _v: self._update_summary(), width=200))
        self.date_entry = self._field(main, 2, 0, 1, "Data", lambda p: entry(p, "DD/MM/AAAA", width=100))
        self.time_entry = self._field(main, 2, 1, 1, "Horário", lambda p: entry(p, "HH:MM", width=100))
        self.region_cb = self._field(main, 2, 2, 1, "Região (opcional)",
                                     lambda p: combo(p, list(self._regions), width=100))
        self.notes = self._field(main, 3, 0, 3, "Observações (opcional)", lambda p: textbox(p, height=70))
        # o campo de veículo ocupa a 3ª coluna; o cliente, as duas primeiras
        self.summary = label(main, "", 12, C.TEXT_SECONDARY, height=22)
        self.summary.grid(row=4, column=0, columnspan=3, sticky="w", pady=(8, 0))

        self._prefill(appointment)
        self.time_entry.bind("<KeyRelease>", lambda e: self._update_summary(), add="+")
        button(footer, "Cancelar", self.close, "ghost").pack(side="left", padx=(0, 8))
        button(footer, "Salvar alterações" if appointment else "Agendar", self.submit, "primary"
               ).pack(side="left")
        self.bind("<Return>", self._on_return)
        if not self._clients or not self._services:
            self.show_error("Cadastre ao menos um cliente, um veículo e um serviço antes de agendar.")
        self.after(220, lambda: self.date_entry.focus_set())

    # ------------------------------------------------------------------ layout
    @staticmethod
    def _field(parent, row, col, span, text, factory):
        """Cria a caixa (rótulo + campo); o campo nasce dentro da caixa (empilhamento correto)."""
        box = ctk.CTkFrame(parent, fg_color="transparent")
        box.grid(row=row, column=col, columnspan=span, sticky="ew",
                 padx=(0, 10 if col + span < 3 else 0), pady=(0, 10))
        box.grid_columnconfigure(0, weight=1)
        caption(box, text).grid(row=0, column=0, sticky="w")
        widget = factory(box)
        widget.grid(row=1, column=0, sticky="ew", pady=(4, 0))
        return widget

    # ------------------------------------------------------------------- dados
    def _prefill(self, appt) -> None:
        if appt:
            self._select(self.client_cb, self._clients, appt.client_id)
            self._fill_vehicles(select_id=appt.vehicle_id)
            self._select(self.service_cb, self._services, appt.service_id)
            self.date_entry.insert(0, format_date_br(appt.date))
            self.time_entry.insert(0, appt.time)
            self.notes.insert("1.0", appt.notes)
            region_label_ = next((k for k, v in self._regions.items() if v == appt.region), None)
            if region_label_:
                self.region_cb.set(region_label_)
        else:
            self._fill_vehicles()
            day, hhmm = self._default_slot()
            self.date_entry.insert(0, format_date_br(day))
            self.time_entry.insert(0, hhmm)
        self._update_summary()

    def _default_slot(self):
        """Próximo intervalo de 30 min livre de 'horário passado' (ou amanhã na abertura)."""
        now = self.repo.now()
        opening = time_to_min(self.repo.meta["open"])
        closing = time_to_min(self.repo.meta["close"])
        minutes = int(math.ceil((now.hour * 60 + now.minute + 1) / 30.0)) * 30
        day = self.repo.today()
        if minutes + 40 > closing:
            return day + timedelta(days=1), min_to_time(opening)
        return day, min_to_time(max(minutes, opening))

    @staticmethod
    def _select(cb, mapping: dict, value_id) -> None:
        for label_, vid in mapping.items():
            if vid == value_id:
                cb.set(label_)
                return

    def _fill_vehicles(self, select_id=None) -> None:
        client_id = self._clients.get(self.client_cb.get())
        vehicles = self.repo.client_vehicles(client_id) if client_id else []
        self._vehicles = unique_labels(
            vehicles, lambda v: f"{v.brand} {v.model} · {format_plate(v.plate)}")
        labels = list(self._vehicles) or ["Cliente sem veículos"]
        self.vehicle_cb.configure(values=labels)
        self.vehicle_cb.set(labels[0])
        if select_id is not None:
            self._select(self.vehicle_cb, self._vehicles, select_id)

    def _update_summary(self) -> None:
        sid = self._services.get(self.service_cb.get())
        svc = self.repo.get_service(sid) if sid else None
        if svc is None:
            self.summary.configure(text="")
            return
        duration = svc.duration_min
        price = svc.price_cents
        if self.appointment and self.appointment.service_id == svc.id:
            duration, price = self.appointment.duration_min, self.appointment.price_cents
        try:
            end = min_to_time(time_to_min(parse_time(self.time_entry.get())) + duration)
            text = f"Duração {format_duration(duration)} · término previsto {end} · valor {brl(price)}"
        except ValueError:
            text = f"Duração {format_duration(duration)} · valor {brl(price)}"
        self.summary.configure(text=text)

    # ------------------------------------------------------------------- envio
    def _on_return(self, event) -> None:
        if event.widget.__class__.__name__ != "Text":
            self.submit()

    def submit(self) -> None:
        data = dict(
            client_id=self._clients.get(self.client_cb.get()),
            vehicle_id=self._vehicles.get(self.vehicle_cb.get()),
            service_id=self._services.get(self.service_cb.get()),
            date=self.date_entry.get().strip(),
            time=self.time_entry.get().strip(),
            region=self._regions.get(self.region_cb.get(), ""),
            notes=self.notes.get("1.0", "end-1c").strip(),
        )
        try:
            appt = self.repo.save_appointment(data, self.appointment.id if self.appointment else None)
        except RepositoryError as exc:
            self.show_error(str(exc))
            return
        self.close()
        if self._on_saved:
            self._on_saved(appt, edited=self.appointment is not None)
