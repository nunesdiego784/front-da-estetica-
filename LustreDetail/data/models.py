"""Modelos de dados (dataclasses) e constantes de domínio.

Convenções:
* datas em ISO ('AAAA-MM-DD') e horários em 'HH:MM' (texto), o que facilita
  salvar em JSON e ordenar;
* valores monetários em **centavos** (inteiros).
"""
from dataclasses import asdict, dataclass, fields
from typing import Optional

# --------------------------------------------------------------- constantes
SCHEDULED, IN_PROGRESS, DONE, CANCELLED = "scheduled", "in_progress", "done", "cancelled"

REGIONS = {
    "capo": "Capô",
    "teto": "Teto",
    "porta_malas": "Porta-malas",
    "esquerdo": "Lado esquerdo",
    "direito": "Lado direito",
}
PAYMENT_METHODS = ["Dinheiro", "PIX", "Cartão de débito", "Cartão de crédito", "Outro"]
PRODUCT_CATEGORIES = ["Lavagem", "Polimento", "Proteção", "Interior", "Acessórios", "Outros"]
UNITS = ["un", "L", "mL", "kg", "g"]
EXPENSE_CATEGORIES = ["Produtos", "Equipamentos", "Aluguel", "Energia/Água", "Salários", "Outros"]


def _build(cls, data: dict):
    """Cria o modelo ignorando chaves desconhecidas (tolerante a versões antigas)."""
    names = {f.name for f in fields(cls)}
    return cls(**{k: v for k, v in data.items() if k in names})


class Record:
    """Base com (de)serialização para dicionários."""

    def to_dict(self) -> dict:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict):
        return _build(cls, data)


# ------------------------------------------------------------------ entidades
@dataclass
class Client(Record):
    id: int
    name: str
    phone: str
    email: str = ""
    notes: str = ""
    active: bool = True


@dataclass
class Vehicle(Record):
    id: int
    client_id: int
    brand: str
    model: str
    year: int
    color: str
    plate: str  # sempre normalizada (sem hífen)


@dataclass
class Service(Record):
    id: int
    name: str
    description: str
    price_cents: int
    duration_min: int
    active: bool = True


@dataclass
class Appointment(Record):
    id: int
    client_id: int
    vehicle_id: int
    service_id: int
    date: str                      # AAAA-MM-DD
    time: str                      # HH:MM
    status: str = SCHEDULED
    notes: str = ""
    region: str = ""               # chave de REGIONS ou '' (veículo inteiro)
    progress: int = 0              # 0..100 (somente em andamento/concluído)
    started_at: str = ""
    finished_at: str = ""
    price_cents: int = 0           # "foto" do preço no momento do agendamento
    duration_min: int = 0          # "foto" da duração
    paid: bool = False
    payment_method: str = ""
    paid_date: str = ""


@dataclass
class Product(Record):
    id: int
    name: str
    category: str
    quantity: float
    unit: str
    min_stock: float
    unit_cost_cents: int


@dataclass
class StockMovement(Record):
    id: int
    product_id: int
    kind: str                      # 'in' ou 'out'
    quantity: float
    date: str                      # AAAA-MM-DD HH:MM
    note: str = ""


@dataclass
class FinanceEntry(Record):
    id: int
    kind: str                      # 'income' ou 'expense'
    description: str
    amount_cents: int
    date: str                      # AAAA-MM-DD
    method: str = ""
    category: str = ""
    appointment_id: Optional[int] = None


@dataclass
class AppointmentView:
    """Agendamento já combinado com cliente, veículo e serviço (para exibição)."""
    appt: Appointment
    client: Optional[Client]
    vehicle: Optional[Vehicle]
    service: Optional[Service]

    @property
    def client_name(self) -> str:
        return self.client.name if self.client else "—"

    @property
    def vehicle_label(self) -> str:
        return f"{self.vehicle.brand} {self.vehicle.model}" if self.vehicle else "—"

    @property
    def plate(self) -> str:
        return self.vehicle.plate if self.vehicle else ""

    @property
    def service_name(self) -> str:
        return self.service.name if self.service else "—"

    @property
    def end_time(self) -> str:
        from utils.formatting import min_to_time, time_to_min
        return min_to_time(time_to_min(self.appt.time) + self.appt.duration_min)


COLLECTIONS = {
    "clients": Client, "vehicles": Vehicle, "services": Service,
    "appointments": Appointment, "products": Product,
    "movements": StockMovement, "finance": FinanceEntry,
}
