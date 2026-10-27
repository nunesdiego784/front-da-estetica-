"""Ações sobre agendamentos compartilhadas por Dashboard, Agenda e Financeiro."""
from data.models import PAYMENT_METHODS
from data.repository import RepositoryError
from utils import colors as C
from utils.data_labels import region_label
from utils.formatting import brl, format_date_br, format_duration, format_plate
from utils.theme import STATUS_STYLES

from .dialogs import ConfirmDialog, Field, FormDialog, InfoDialog


class AppointmentActions:
    """Visualizar, editar, cancelar, iniciar, avançar, concluir e registrar pagamento."""

    def __init__(self, app):
        self.app = app
        self.repo = app.repo

    # ------------------------------------------------------------- utilitários
    def _run(self, fn, success: str) -> bool:
        try:
            fn()
        except RepositoryError as exc:
            self.app.toast.show(str(exc), "error")
            return False
        if success:
            self.app.toast.show(success, "success")
        return True

    # --------------------------------------------------------------- consultas
    def view(self, v) -> None:
        a = v.appt
        status = STATUS_STYLES[a.status][0].replace("● ", "")
        if a.paid:
            pay = f"Pago em {format_date_br(a.paid_date)} · {a.payment_method}"
        elif a.status == "done":
            pay = "Pendente de pagamento"
        else:
            pay = "—"
        veh = v.vehicle
        rows = [
            ("Cliente", f"{v.client_name} · {v.client.phone if v.client else ''}"),
            ("Veículo", f"{veh.brand} {veh.model} {veh.year} · {veh.color}" if veh else "—"),
            ("Placa", format_plate(v.plate)),
            ("Serviço", f"{v.service_name} ({format_duration(a.duration_min)})"),
            ("Data", format_date_br(a.date)),
            ("Horário", f"{a.time} às {v.end_time}"),
            ("Região", region_label(a.region)),
            ("Status", status + (f" · {a.progress}%" if a.status == "in_progress" else "")),
            ("Valor", brl(a.price_cents)),
            ("Pagamento", pay),
            ("Observações", a.notes or "—"),
        ]
        InfoDialog(self.app, "Detalhes do agendamento", rows)

    def edit(self, v) -> None:
        if v.appt.status != "scheduled":
            self.app.toast.show("Somente agendamentos com status 'Agendado' podem ser editados.", "warning")
            return
        self.app.open_appointment_dialog(v.appt)

    # ------------------------------------------------------------------ ações
    def cancel(self, v) -> None:
        ConfirmDialog(
            self.app, "Cancelar agendamento",
            f"Cancelar o agendamento de {v.client_name} ({v.service_name}) em "
            f"{format_date_br(v.appt.date)} às {v.appt.time}? O horário será liberado.",
            on_confirm=lambda: self._run(lambda: self.repo.cancel_appointment(v.appt.id),
                                         "Agendamento cancelado."),
            confirm_text="Cancelar agendamento", cancel_text="Manter")

    def start(self, v) -> None:
        self._run(lambda: self.repo.start_appointment(v.appt.id), "Serviço iniciado.")

    def advance(self, appt_id) -> None:
        self._run(lambda: self.repo.advance_progress(appt_id, 25), "")

    def finish(self, appt_id) -> None:
        self._run(lambda: self.repo.finish_appointment(appt_id), "Serviço concluído. Pagamento pendente.")

    def pay(self, v) -> None:
        """Pede a forma de pagamento e registra a receita (somente valor efetivamente recebido)."""
        def submit(vals):
            self.repo.register_payment(v.appt.id, vals["method"])
            self.app.toast.show(f"Pagamento de {brl(v.appt.price_cents)} registrado.", "success")
        FormDialog(self.app, "Registrar pagamento",
                   [Field("method", "Forma de pagamento", "choice", [(m, m) for m in PAYMENT_METHODS])],
                   submit, submit_text="Confirmar recebimento",
                   subtitle=f"{v.service_name} — {v.client_name} · {brl(v.appt.price_cents)}")

    # -------------------------------------------------------------------- menu
    def more_menu(self, v, anchor) -> None:
        items = []
        status = v.appt.status
        if status == "scheduled":
            items.append(("Iniciar serviço", lambda: self.start(v)))
        if status == "in_progress":
            items.append(("Avançar progresso (+25%)", lambda: self.advance(v.appt.id)))
            items.append(("Concluir serviço", lambda: self.finish(v.appt.id)))
        if status == "done" and not v.appt.paid:
            items.append(("Registrar pagamento", lambda: self.pay(v)))
        if not items:
            items.append(("Sem ações disponíveis", lambda: None))
        self.app.popovers.show_menu(anchor, items, width=230)
