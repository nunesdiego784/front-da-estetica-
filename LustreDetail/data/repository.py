"""Repositório central: consultas, cadastros, regras de negócio e persistência.

* Persistência local em um único arquivo JSON, gravado de forma atômica
  (arquivo temporário + ``os.replace``). Se o arquivo estiver corrompido ele é
  renomeado para ``*.corrupt-<data>`` e o sistema reinicia com os dados de
  demonstração (``load_warning`` informa a interface).
* A interface nunca mexe nas listas diretamente: tudo passa por aqui, e quem
  quiser ser avisado de mudanças usa ``subscribe``.
* Erros de regra de negócio levantam ``ValidationError`` com mensagem
  pronta para ser exibida ao usuário.
"""
import json
import os
import re
import sys
from datetime import date, datetime, timedelta
from pathlib import Path
from typing import Callable, Optional

from utils.formatting import (brl, digits, format_date_br, format_phone, format_plate,
                              is_valid_plate, matches, min_to_time, normalize_plate,
                              parse_brl, parse_date_br, parse_quantity, parse_time,
                              time_to_min, format_quantity)
from . import mock_data
from .models import (CANCELLED, COLLECTIONS, DONE, IN_PROGRESS, PAYMENT_METHODS, REGIONS,
                     SCHEDULED, Appointment, AppointmentView, Client, FinanceEntry, Product,
                     Service, StockMovement, Vehicle)

_EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")


class RepositoryError(Exception):
    """Erro genérico do repositório (ex.: falha ao gravar arquivo)."""


class ValidationError(RepositoryError):
    """Dado inválido ou regra de negócio violada; a mensagem é para o usuário."""


def default_data_dir() -> Path:
    """Pasta dos dados do usuário (pode ser trocada com LUSTRE_DATA_DIR)."""
    env = os.environ.get("LUSTRE_DATA_DIR")
    if env:
        return Path(env)
    if sys.platform == "win32" and os.environ.get("APPDATA"):
        return Path(os.environ["APPDATA"]) / "LustreDetail"
    return Path.home() / ".lustre_detail"


class Repository:
    """Fonte única de verdade do sistema (em memória + arquivo JSON)."""

    def __init__(self, path=None, today_fn: Callable[[], date] = date.today,
                 now_fn: Callable[[], datetime] = datetime.now):
        self.path = Path(path) if path else default_data_dir() / "lustre_detail.json"
        self._today_fn, self._now_fn = today_fn, now_fn
        self._listeners: list = []
        self.load_warning: Optional[str] = None
        self.meta: dict = dict(mock_data.DEFAULT_SETTINGS)
        self.clients: list = []
        self.vehicles: list = []
        self.services: list = []
        self.appointments: list = []
        self.products: list = []
        self.movements: list = []
        self.finance: list = []
        self._load()

    # ============================================================ persistência
    def today(self) -> date:
        return self._today_fn()

    def now(self) -> datetime:
        return self._now_fn()

    def _load(self) -> None:
        if not self.path.exists():
            self._apply(mock_data.build_seed(self.today()))
            self._save()
            return
        try:
            with open(self.path, "r", encoding="utf-8") as fh:
                raw = json.load(fh)
            self._apply(raw)
        except (OSError, ValueError, TypeError, KeyError) as exc:
            backup = self.path.with_name(
                f"{self.path.name}.corrupt-{self.now():%Y%m%d-%H%M%S}")
            try:
                os.replace(self.path, backup)
            except OSError:
                pass
            self.load_warning = (f"Não foi possível ler os dados salvos ({exc.__class__.__name__}). "
                                 f"O arquivo foi preservado como {backup.name} e os dados de "
                                 f"demonstração foram restaurados.")
            self._apply(mock_data.build_seed(self.today()))
            self._save()

    def _apply(self, raw: dict) -> None:
        """Converte o dicionário lido (ou do seed) nos modelos em memória."""
        meta = dict(mock_data.DEFAULT_SETTINGS)
        meta.update(raw.get("meta", {}))
        parsed = {name: [cls.from_dict(item) for item in raw.get(name, [])]
                  for name, cls in COLLECTIONS.items()}
        self.meta = meta
        for name, items in parsed.items():
            setattr(self, name, items)

    def _save(self) -> None:
        payload = {"version": 1, "meta": self.meta}
        for name in COLLECTIONS:
            payload[name] = [item.to_dict() for item in getattr(self, name)]
        try:
            self.path.parent.mkdir(parents=True, exist_ok=True)
            tmp = self.path.with_suffix(".tmp")
            with open(tmp, "w", encoding="utf-8") as fh:
                json.dump(payload, fh, ensure_ascii=False, indent=2)
            os.replace(tmp, self.path)
        except OSError as exc:
            raise RepositoryError(f"Não foi possível salvar os dados: {exc}") from exc

    def subscribe(self, callback: Callable[[], None]) -> None:
        """Registra uma função chamada após qualquer alteração de dados."""
        self._listeners.append(callback)

    def _commit(self) -> None:
        self._save()
        for cb in list(self._listeners):
            cb()

    def reset(self, demo: bool = True) -> None:
        """Substitui todos os dados: demonstração (``demo=True``) ou sistema vazio."""
        if demo:
            self._apply(mock_data.build_seed(self.today()))
        else:
            empty = {"meta": {**mock_data.DEFAULT_SETTINGS, "demo": False}}
            self._apply(empty)
        self._commit()

    @property
    def is_demo(self) -> bool:
        return bool(self.meta.get("demo"))

    def _next_id(self, items: list) -> int:
        return max((i.id for i in items), default=0) + 1

    # ============================================================== configurações
    @property
    def capacity(self) -> int:
        return int(self.meta.get("capacity", 2))

    def settings(self) -> dict:
        return {"capacity": self.capacity, "open": self.meta["open"], "close": self.meta["close"]}

    def update_settings(self, capacity, open_time, close_time) -> None:
        try:
            cap = int(str(capacity).strip())
        except ValueError:
            raise ValidationError("A capacidade deve ser um número inteiro.") from None
        if not 1 <= cap <= 20:
            raise ValidationError("A capacidade deve estar entre 1 e 20 atendimentos simultâneos.")
        try:
            o, c = parse_time(open_time), parse_time(close_time)
        except ValueError:
            raise ValidationError("Informe os horários de funcionamento no formato HH:MM.") from None
        if time_to_min(o) >= time_to_min(c):
            raise ValidationError("O horário de abertura deve ser anterior ao de fechamento.")
        self.meta.update(capacity=cap, open=o, close=c)
        self._commit()

    # ================================================================== clientes
    def get_client(self, client_id) -> Optional[Client]:
        return next((c for c in self.clients if c.id == client_id), None)

    def list_clients(self, search: str = "", status: str = "all") -> list:
        out = [c for c in self.clients
               if (status == "all" or (status == "active") == c.active)
               and matches(search, c.name, c.phone, c.email)]
        return sorted(out, key=lambda c: c.name.lower())

    def client_vehicles(self, client_id) -> list:
        return [v for v in self.vehicles if v.client_id == client_id]

    def client_appointments(self, client_id) -> list:
        return [a for a in self.appointments if a.client_id == client_id]

    def save_client(self, data: dict, client_id=None) -> Client:
        name = " ".join(str(data.get("name", "")).split())
        if len(name) < 3:
            raise ValidationError("Informe o nome completo do cliente (mínimo de 3 letras).")
        phone_digits = digits(data.get("phone", ""))
        if len(phone_digits) not in (10, 11):
            raise ValidationError("Telefone inválido. Use DDD + número (10 ou 11 dígitos).")
        phone = format_phone(phone_digits)
        email = str(data.get("email", "")).strip()
        if email and not _EMAIL_RE.match(email):
            raise ValidationError("E-mail inválido.")
        for other in self.clients:
            if other.id != client_id and digits(other.phone) == phone_digits:
                raise ValidationError(f"Já existe um cliente com este telefone ({other.name}).")
        notes = str(data.get("notes", "")).strip()
        active = bool(data.get("active", True))
        if client_id is None:
            client = Client(self._next_id(self.clients), name, phone, email, notes, active)
            self.clients.append(client)
        else:
            client = self.get_client(client_id)
            if client is None:
                raise ValidationError("Cliente não encontrado.")
            client.name, client.phone, client.email, client.notes, client.active = \
                name, phone, email, notes, active
        self._commit()
        return client

    def delete_client(self, client_id) -> None:
        """Exclui apenas clientes sem histórico; do contrário orienta a inativar."""
        client = self.get_client(client_id)
        if client is None:
            raise ValidationError("Cliente não encontrado.")
        n_veh = len(self.client_vehicles(client_id))
        n_app = len(self.client_appointments(client_id))
        if n_veh or n_app:
            raise ValidationError(
                f"{client.name} possui {n_veh} veículo(s) e {n_app} agendamento(s) no histórico, "
                f"então não pode ser excluído. Edite o cadastro e desmarque 'Cliente ativo' para inativá-lo.")
        self.clients.remove(client)
        self._commit()

    # ================================================================== veículos
    def get_vehicle(self, vehicle_id) -> Optional[Vehicle]:
        return next((v for v in self.vehicles if v.id == vehicle_id), None)

    def list_vehicles(self, search: str = "") -> list:
        out = []
        for v in self.vehicles:
            owner = self.get_client(v.client_id)
            if matches(search, v.plate, v.brand, v.model, v.color, owner.name if owner else ""):
                out.append(v)
        return sorted(out, key=lambda v: (v.brand.lower(), v.model.lower()))

    def vehicle_appointments(self, vehicle_id) -> list:
        return [a for a in self.appointments if a.vehicle_id == vehicle_id]

    def save_vehicle(self, data: dict, vehicle_id=None) -> Vehicle:
        client_id = data.get("client_id")
        if client_id in (None, "") or self.get_client(client_id) is None:
            raise ValidationError("Selecione o cliente responsável pelo veículo.")
        brand = " ".join(str(data.get("brand", "")).split())
        model = " ".join(str(data.get("model", "")).split())
        color = " ".join(str(data.get("color", "")).split())
        if len(brand) < 2:
            raise ValidationError("Informe a marca do veículo.")
        if not model:
            raise ValidationError("Informe o modelo do veículo.")
        if not color:
            raise ValidationError("Informe a cor do veículo.")
        try:
            year = int(str(data.get("year", "")).strip())
        except ValueError:
            raise ValidationError("O ano deve ser um número (ex.: 2021).") from None
        if not 1950 <= year <= self.today().year + 1:
            raise ValidationError(f"Ano inválido. Use um valor entre 1950 e {self.today().year + 1}.")
        plate_raw = str(data.get("plate", ""))
        if not is_valid_plate(plate_raw):
            raise ValidationError("Placa inválida. Use o padrão Mercosul (ABC1D23) ou o antigo (ABC-1234).")
        plate = normalize_plate(plate_raw)
        for other in self.vehicles:
            if other.id != vehicle_id and other.plate == plate:
                raise ValidationError(f"A placa {format_plate(plate)} já está cadastrada.")
        if vehicle_id is None:
            veh = Vehicle(self._next_id(self.vehicles), int(client_id), brand, model, year, color, plate)
            self.vehicles.append(veh)
        else:
            veh = self.get_vehicle(vehicle_id)
            if veh is None:
                raise ValidationError("Veículo não encontrado.")
            if veh.client_id != int(client_id) and self._has_open_appointments(vehicle_id):
                raise ValidationError("Este veículo possui agendamentos em aberto; "
                                      "conclua ou cancele-os antes de trocar o cliente.")
            veh.client_id, veh.brand, veh.model = int(client_id), brand, model
            veh.year, veh.color, veh.plate = year, color, plate
        self._commit()
        return veh

    def _has_open_appointments(self, vehicle_id) -> bool:
        return any(a.vehicle_id == vehicle_id and a.status in (SCHEDULED, IN_PROGRESS)
                   for a in self.appointments)

    def delete_vehicle(self, vehicle_id) -> None:
        veh = self.get_vehicle(vehicle_id)
        if veh is None:
            raise ValidationError("Veículo não encontrado.")
        n = len(self.vehicle_appointments(vehicle_id))
        if n:
            raise ValidationError(f"O veículo possui {n} agendamento(s) no histórico e não pode ser "
                                  f"excluído, para preservar o histórico de serviços.")
        self.vehicles.remove(veh)
        self._commit()

    # =================================================================== serviços
    def get_service(self, service_id) -> Optional[Service]:
        return next((s for s in self.services if s.id == service_id), None)

    def list_services(self, search: str = "", status: str = "all") -> list:
        out = [s for s in self.services
               if (status == "all" or (status == "active") == s.active)
               and matches(search, s.name, s.description)]
        return sorted(out, key=lambda s: s.name.lower())

    def save_service(self, data: dict, service_id=None) -> Service:
        name = " ".join(str(data.get("name", "")).split())
        if len(name) < 3:
            raise ValidationError("Informe o nome do serviço (mínimo de 3 letras).")
        for other in self.services:
            if other.id != service_id and other.name.lower() == name.lower():
                raise ValidationError("Já existe um serviço com este nome.")
        try:
            price = parse_brl(data.get("price", ""))
        except ValueError:
            raise ValidationError("Preço inválido. Exemplo: 150,00") from None
        if price <= 0:
            raise ValidationError("O preço deve ser maior que zero.")
        try:
            duration = int(str(data.get("duration", "")).strip())
        except ValueError:
            raise ValidationError("A duração deve ser um número inteiro de minutos.") from None
        if not 10 <= duration <= 600:
            raise ValidationError("A duração deve ficar entre 10 e 600 minutos.")
        description = str(data.get("description", "")).strip()
        active = bool(data.get("active", True))
        if service_id is None:
            svc = Service(self._next_id(self.services), name, description, price, duration, active)
            self.services.append(svc)
        else:
            svc = self.get_service(service_id)
            if svc is None:
                raise ValidationError("Serviço não encontrado.")
            svc.name, svc.description, svc.price_cents = name, description, price
            svc.duration_min, svc.active = duration, active
        self._commit()
        return svc

    def set_service_active(self, service_id, active: bool) -> Service:
        svc = self.get_service(service_id)
        if svc is None:
            raise ValidationError("Serviço não encontrado.")
        svc.active = active
        self._commit()
        return svc

    # ============================================================== agendamentos
    def get_appointment(self, appt_id) -> Optional[Appointment]:
        return next((a for a in self.appointments if a.id == appt_id), None)

    def _view(self, a: Appointment) -> AppointmentView:
        return AppointmentView(a, self.get_client(a.client_id), self.get_vehicle(a.vehicle_id),
                               self.get_service(a.service_id))

    def appointment_views(self, search: str = "", date_from: Optional[str] = None,
                          date_to: Optional[str] = None, status: Optional[str] = None,
                          newest_first: bool = False) -> list:
        out = []
        for a in self.appointments:
            if date_from and a.date < date_from:
                continue
            if date_to and a.date > date_to:
                continue
            if status and a.status != status:
                continue
            v = self._view(a)
            if matches(search, v.client_name, v.vehicle_label, v.plate, v.service_name,
                       format_date_br(a.date), a.time):
                out.append(v)
        out.sort(key=lambda v: (v.appt.date, v.appt.time), reverse=newest_first)
        return out

    def vehicle_history(self, vehicle_id) -> list:
        return [self._view(a) for a in sorted(self.vehicle_appointments(vehicle_id),
                                              key=lambda a: (a.date, a.time), reverse=True)]

    def operations_now(self) -> list:
        """Serviços em andamento (mais antigos primeiro)."""
        views = [self._view(a) for a in self.appointments if a.status == IN_PROGRESS]
        return sorted(views, key=lambda v: (v.appt.date, v.appt.started_at or v.appt.time))

    def upcoming(self, limit: int = 6) -> list:
        """Próximos agendamentos 'Agendado' a partir de agora."""
        today, hhmm = self.today().isoformat(), self.now().strftime("%H:%M")
        views = [self._view(a) for a in self.appointments
                 if a.status == SCHEDULED and (a.date, a.time) >= (today, hhmm)]
        views.sort(key=lambda v: (v.appt.date, v.appt.time))
        return views[:limit]

    # --- validação de agenda -------------------------------------------------
    def _first_overload(self, date_iso, start, end, ignore_id) -> Optional[int]:
        """Primeiro minuto em que a capacidade seria excedida, ou ``None``."""
        busy = [(time_to_min(a.time), time_to_min(a.time) + a.duration_min)
                for a in self.appointments
                if a.date == date_iso and a.status != CANCELLED and a.id != ignore_id]
        overlapping = [(s, e) for s, e in busy if s < end and e > start]
        points = {start} | {s for s, _ in overlapping if s > start}
        for t in sorted(points):
            if sum(1 for s, e in overlapping if s <= t < e) + 1 > self.capacity:
                return t
        return None

    def _vehicle_conflict(self, vehicle_id, date_iso, start, end, ignore_id) -> bool:
        for a in self.appointments:
            if (a.vehicle_id == vehicle_id and a.date == date_iso and a.status != CANCELLED
                    and a.id != ignore_id):
                s = time_to_min(a.time)
                if s < end and s + a.duration_min > start:
                    return True
        return False

    def save_appointment(self, data: dict, appointment_id=None) -> Appointment:
        """Cria ou edita um agendamento aplicando todas as validações."""
        existing = self.get_appointment(appointment_id) if appointment_id else None
        if appointment_id and existing is None:
            raise ValidationError("Agendamento não encontrado.")
        if existing and existing.status != SCHEDULED:
            raise ValidationError("Somente agendamentos com status 'Agendado' podem ser editados.")

        client = self.get_client(data.get("client_id"))
        if client is None:
            raise ValidationError("Selecione o cliente.")
        vehicle = self.get_vehicle(data.get("vehicle_id"))
        if vehicle is None:
            raise ValidationError("Selecione o veículo.")
        if vehicle.client_id != client.id:
            raise ValidationError("O veículo selecionado não pertence a este cliente.")
        service = self.get_service(data.get("service_id"))
        if service is None:
            raise ValidationError("Selecione o serviço.")
        keep_service = existing is not None and existing.service_id == service.id
        if not service.active and not keep_service:
            raise ValidationError("Este serviço está desativado e não pode ser agendado.")
        region = str(data.get("region", "") or "")
        if region and region not in REGIONS:
            raise ValidationError("Região do veículo inválida.")

        try:
            day = parse_date_br(data.get("date", ""))
        except ValueError:
            raise ValidationError("Data inválida. Use o formato DD/MM/AAAA.") from None
        try:
            hhmm = parse_time(data.get("time", ""))
        except ValueError:
            raise ValidationError("Horário inválido. Use o formato HH:MM (ex.: 14:30).") from None

        date_iso = day.isoformat()
        changed_slot = existing is None or existing.date != date_iso or existing.time != hhmm
        if changed_slot and day < self.today():
            raise ValidationError("Não é possível agendar em uma data que já passou.")
        if changed_slot and day == self.today() and hhmm < self.now().strftime("%H:%M"):
            raise ValidationError("Este horário de hoje já passou. Escolha um horário posterior.")

        duration = service.duration_min if (existing is None or not keep_service) else existing.duration_min
        price = service.price_cents if (existing is None or not keep_service) else existing.price_cents
        start = time_to_min(hhmm)
        end = start + duration
        opening, closing = time_to_min(self.meta["open"]), time_to_min(self.meta["close"])
        if start < opening or end > closing:
            raise ValidationError(
                f"Fora do horário de funcionamento ({self.meta['open']} às {self.meta['close']}). "
                f"Este serviço dura {duration} min e terminaria às {min_to_time(end)}.")
        ignore = existing.id if existing else None
        if self._vehicle_conflict(vehicle.id, date_iso, start, end, ignore):
            raise ValidationError("Este veículo já possui outro agendamento que se sobrepõe a este horário.")
        overload = self._first_overload(date_iso, start, end, ignore)
        if overload is not None:
            raise ValidationError(
                f"Capacidade de {self.capacity} atendimento(s) simultâneo(s) atingida às "
                f"{min_to_time(overload)}. Escolha outro horário.")

        notes = str(data.get("notes", "")).strip()
        if existing is None:
            appt = Appointment(self._next_id(self.appointments), client.id, vehicle.id, service.id,
                               date_iso, hhmm, SCHEDULED, notes, region, 0, "", "",
                               price, duration)
            self.appointments.append(appt)
        else:
            appt = existing
            appt.client_id, appt.vehicle_id, appt.service_id = client.id, vehicle.id, service.id
            appt.date, appt.time, appt.notes, appt.region = date_iso, hhmm, notes, region
            appt.duration_min, appt.price_cents = duration, price
        self._commit()
        return appt

    def start_appointment(self, appt_id) -> Appointment:
        a = self._require(appt_id)
        if a.status != SCHEDULED:
            raise ValidationError("Só é possível iniciar agendamentos com status 'Agendado'.")
        if a.date != self.today().isoformat():
            raise ValidationError("Só é possível iniciar serviços agendados para hoje.")
        running = sum(1 for x in self.appointments if x.status == IN_PROGRESS)
        if running >= self.capacity:
            raise ValidationError(f"A capacidade de {self.capacity} serviço(s) simultâneo(s) já está em uso. "
                                  f"Conclua um serviço antes de iniciar outro.")
        a.status, a.progress = IN_PROGRESS, 0
        a.started_at = self.now().strftime("%H:%M")
        self._commit()
        return a

    def advance_progress(self, appt_id, step: int = 25) -> Appointment:
        a = self._require(appt_id)
        if a.status != IN_PROGRESS:
            raise ValidationError("Apenas serviços em andamento têm progresso.")
        a.progress = min(100, a.progress + step)
        self._commit()
        return a

    def finish_appointment(self, appt_id) -> Appointment:
        a = self._require(appt_id)
        if a.status != IN_PROGRESS:
            raise ValidationError("Só é possível concluir serviços em andamento.")
        a.status, a.progress = DONE, 100
        a.finished_at = self.now().strftime("%H:%M")
        self._commit()
        return a

    def cancel_appointment(self, appt_id) -> Appointment:
        a = self._require(appt_id)
        if a.status in (DONE, CANCELLED):
            raise ValidationError("Este agendamento já foi concluído ou cancelado.")
        a.status = CANCELLED
        self._commit()
        return a

    def _require(self, appt_id) -> Appointment:
        a = self.get_appointment(appt_id)
        if a is None:
            raise ValidationError("Agendamento não encontrado.")
        return a

    # ================================================================= financeiro
    def register_payment(self, appt_id, method: str, when: Optional[date] = None) -> FinanceEntry:
        """Marca o serviço como pago e lança a receita correspondente."""
        a = self._require(appt_id)
        if a.status != DONE:
            raise ValidationError("Só é possível registrar pagamento de serviços concluídos.")
        if a.paid:
            raise ValidationError("Este serviço já está pago.")
        if method not in PAYMENT_METHODS:
            raise ValidationError("Selecione a forma de pagamento.")
        when = when or self.today()
        v = self._view(a)
        entry = FinanceEntry(self._next_id(self.finance), "income",
                             f"{v.service_name} — {v.client_name}", a.price_cents,
                             when.isoformat(), method, "Serviço", a.id)
        self.finance.append(entry)
        a.paid, a.payment_method, a.paid_date = True, method, when.isoformat()
        self._commit()
        return entry

    def add_entry(self, kind: str, data: dict) -> FinanceEntry:
        """Lança uma receita avulsa (``income``) ou despesa (``expense``)."""
        if kind not in ("income", "expense"):
            raise ValidationError("Tipo de lançamento inválido.")
        desc = " ".join(str(data.get("description", "")).split())
        if len(desc) < 3:
            raise ValidationError("Informe uma descrição (mínimo de 3 letras).")
        try:
            amount = parse_brl(data.get("amount", ""))
        except ValueError:
            raise ValidationError("Valor inválido. Exemplo: 120,00") from None
        if amount <= 0:
            raise ValidationError("O valor deve ser maior que zero.")
        raw_date = str(data.get("date", "")).strip()
        try:
            day = parse_date_br(raw_date) if raw_date else self.today()
        except ValueError:
            raise ValidationError("Data inválida. Use o formato DD/MM/AAAA.") from None
        if day > self.today():
            raise ValidationError("Lançamentos futuros não são aceitos: valores previstos "
                                  "não contam como recebidos nem pagos.")
        method = str(data.get("method", ""))
        if method not in PAYMENT_METHODS:
            raise ValidationError("Selecione a forma de pagamento.")
        entry = FinanceEntry(self._next_id(self.finance), kind, desc, amount, day.isoformat(),
                             method, str(data.get("category", "")), None)
        self.finance.append(entry)
        self._commit()
        return entry

    def period_range(self, key: str):
        """Converte a chave do filtro em (data_inicial, data_final) ISO."""
        t = self.today()
        if key == "today":
            return t.isoformat(), t.isoformat()
        if key == "7d":
            return (t - timedelta(days=6)).isoformat(), t.isoformat()
        if key == "month":
            return t.replace(day=1).isoformat(), t.isoformat()
        return None, None

    def list_entries(self, start=None, end=None, method=None, search: str = "") -> list:
        out = [e for e in self.finance
               if (not start or e.date >= start) and (not end or e.date <= end)
               and (not method or e.method == method)
               and matches(search, e.description, e.category, e.method)]
        return sorted(out, key=lambda e: (e.date, e.id), reverse=True)

    def finance_summary(self, start=None, end=None, method=None) -> dict:
        """Totais **efetivamente** recebidos/pagos no período (nunca valores previstos)."""
        entries = self.list_entries(start, end, method)
        income = sum(e.amount_cents for e in entries if e.kind == "income")
        expense = sum(e.amount_cents for e in entries if e.kind == "expense")
        return {"income": income, "expense": expense, "balance": income - expense,
                "count": len(entries)}

    def pending_receivables(self, search: str = "") -> list:
        """Serviços concluídos ainda não pagos."""
        views = [self._view(a) for a in self.appointments if a.status == DONE and not a.paid]
        views = [v for v in views if matches(search, v.client_name, v.service_name, v.plate)]
        return sorted(views, key=lambda v: (v.appt.date, v.appt.time))

    def pending_total(self) -> int:
        return sum(v.appt.price_cents for v in self.pending_receivables())

    def paid_services(self, start=None, end=None, method=None, search: str = "") -> list:
        views = [self._view(a) for a in self.appointments if a.paid
                 and (not start or a.paid_date >= start) and (not end or a.paid_date <= end)
                 and (not method or a.payment_method == method)]
        views = [v for v in views if matches(search, v.client_name, v.service_name, v.plate)]
        return sorted(views, key=lambda v: v.appt.paid_date, reverse=True)

    # ==================================================================== estoque
    def get_product(self, product_id) -> Optional[Product]:
        return next((p for p in self.products if p.id == product_id), None)

    def list_products(self, search: str = "", only_low: bool = False) -> list:
        out = [p for p in self.products
               if matches(search, p.name, p.category) and (not only_low or self.is_low(p))]
        return sorted(out, key=lambda p: p.name.lower())

    @staticmethod
    def is_low(p: Product) -> bool:
        return p.quantity <= p.min_stock

    def low_stock_products(self) -> list:
        return [p for p in self.products if self.is_low(p)]

    def save_product(self, data: dict, product_id=None) -> Product:
        name = " ".join(str(data.get("name", "")).split())
        if len(name) < 2:
            raise ValidationError("Informe o nome do produto.")
        for other in self.products:
            if other.id != product_id and other.name.lower() == name.lower():
                raise ValidationError("Já existe um produto com este nome.")
        category = str(data.get("category", "")) or "Outros"
        unit = str(data.get("unit", "")) or "un"
        try:
            min_stock = parse_quantity(data.get("min_stock", "0") or "0")
            cost = parse_brl(data.get("unit_cost", "0") or "0")
        except ValueError:
            raise ValidationError("Estoque mínimo ou custo unitário inválido.") from None
        if min_stock < 0:
            raise ValidationError("O estoque mínimo não pode ser negativo.")
        if product_id is None:
            try:
                qty = parse_quantity(data.get("quantity", "0") or "0")
            except ValueError:
                raise ValidationError("Quantidade inicial inválida.") from None
            if qty < 0:
                raise ValidationError("A quantidade inicial não pode ser negativa.")
            prod = Product(self._next_id(self.products), name, category, qty, unit, min_stock, cost)
            self.products.append(prod)
            if qty > 0:
                self.movements.append(StockMovement(self._next_id(self.movements), prod.id, "in", qty,
                                                    self.now().strftime("%Y-%m-%d %H:%M"), "Estoque inicial"))
        else:
            prod = self.get_product(product_id)
            if prod is None:
                raise ValidationError("Produto não encontrado.")
            prod.name, prod.category, prod.unit = name, category, unit
            prod.min_stock, prod.unit_cost_cents = min_stock, cost
        self._commit()
        return prod

    def move_stock(self, product_id, kind: str, quantity_text, note: str = "") -> StockMovement:
        """Entrada (``in``) ou saída (``out``); a saída não pode exceder o disponível."""
        prod = self.get_product(product_id)
        if prod is None:
            raise ValidationError("Produto não encontrado.")
        try:
            qty = parse_quantity(quantity_text)
        except ValueError:
            raise ValidationError("Quantidade inválida. Use números, ex.: 2 ou 1,5.") from None
        if qty <= 0:
            raise ValidationError("A quantidade deve ser maior que zero.")
        if kind == "out" and qty > prod.quantity + 1e-9:
            raise ValidationError(f"Saída maior que o estoque disponível "
                                  f"({format_quantity(prod.quantity)} {prod.unit}).")
        prod.quantity = round(prod.quantity + (qty if kind == "in" else -qty), 3)
        mov = StockMovement(self._next_id(self.movements), prod.id, kind, qty,
                            self.now().strftime("%Y-%m-%d %H:%M"), str(note).strip())
        self.movements.append(mov)
        self._commit()
        return mov

    def list_movements(self, search: str = "") -> list:
        out = []
        for m in self.movements:
            p = self.get_product(m.product_id)
            if matches(search, p.name if p else "", m.note, "entrada" if m.kind == "in" else "saida"):
                out.append(m)
        return sorted(out, key=lambda m: (m.date, m.id), reverse=True)

    # ===================================================== painel e notificações
    def dashboard_stats(self) -> dict:
        today = self.today().isoformat()
        yesterday = (self.today() - timedelta(days=1)).isoformat()
        todays = [a for a in self.appointments if a.date == today and a.status != CANCELLED]
        done = [a for a in todays if a.status == DONE]
        rev_today = sum(e.amount_cents for e in self.finance if e.kind == "income" and e.date == today)
        rev_yest = sum(e.amount_cents for e in self.finance if e.kind == "income" and e.date == yesterday)
        return {
            "total_today": len(todays),
            "done_today": len(done),
            "remaining_today": sum(1 for a in todays if a.status in (SCHEDULED, IN_PROGRESS)),
            "in_progress": sum(1 for a in self.appointments if a.status == IN_PROGRESS),
            "capacity": self.capacity,
            "ready_today": len(done),
            "revenue_today": rev_today,
            "revenue_yesterday": rev_yest,
            "receivable_today": sum(a.price_cents for a in done if not a.paid),
        }

    def notifications(self) -> list:
        """Avisos acionáveis: estoque baixo, pagamentos pendentes e próximo atendimento."""
        notes = []
        low = self.low_stock_products()
        if low:
            names = ", ".join(p.name for p in low[:2]) + (" e outros" if len(low) > 2 else "")
            notes.append({"kind": "warning", "page": "inventory",
                          "text": f"{len(low)} produto(s) com estoque baixo: {names}."})
        pending = self.pending_receivables()
        if pending:
            notes.append({"kind": "warning", "page": "finance",
                          "text": f"{len(pending)} serviço(s) concluído(s) aguardando pagamento "
                                  f"({brl(sum(v.appt.price_cents for v in pending))})."})
        nxt = self.upcoming(1)
        if nxt and nxt[0].appt.date == self.today().isoformat():
            v = nxt[0]
            notes.append({"kind": "info", "page": "agenda",
                          "text": f"Próximo atendimento hoje às {v.appt.time}: {v.service_name} — {v.client_name}."})
        return notes

    def global_search(self, query: str, limit: int = 8) -> list:
        """Busca rápida em clientes, veículos e agendamentos (para a barra superior)."""
        query = query.strip()
        if len(query) < 2:
            return []
        results = []
        for c in self.list_clients(query)[:3]:
            results.append({"kind": "Cliente", "label": f"{c.name} · {c.phone}", "page": "clients", "query": query})
        for v in self.list_vehicles(query)[:3]:
            results.append({"kind": "Veículo", "label": f"{v.brand} {v.model} · {format_plate(v.plate)}",
                            "page": "vehicles", "query": query})
        for av in self.appointment_views(query, newest_first=True)[:3]:
            results.append({"kind": "Agendamento",
                            "label": f"{format_date_br(av.appt.date)} {av.appt.time} · {av.client_name}",
                            "page": "agenda", "query": query})
        return results[:limit]
