"""DADOS DE DEMONSTRAÇÃO do Lustre Detail.

Todos os nomes, telefones, placas, preços e movimentações abaixo são
FICTÍCIOS e servem apenas para o sistema abrir já com conteúdo. O usuário
pode editá-los, apagá-los ('Limpar todos os dados') ou restaurá-los pelo menu
do usuário. As datas são geradas em relação ao dia atual.
"""
from datetime import date, timedelta

DEFAULT_SETTINGS = {"capacity": 2, "open": "08:00", "close": "18:00", "demo": True}


def build_seed(today: date) -> dict:
    """Devolve um dicionário no mesmo formato do arquivo JSON do repositório."""
    d = lambda n: (today + timedelta(days=n)).isoformat()   # noqa: E731

    clients = [
        dict(id=1, name="Marcos Andrade", phone="(11) 98765-4321", email="marcos@exemplo.com", notes="Prefere atendimento pela manhã.", active=True),
        dict(id=2, name="Juliana Ferreira", phone="(11) 97654-3210", email="", notes="", active=True),
        dict(id=3, name="Ricardo Menezes", phone="(11) 96543-2109", email="ricardo.m@exemplo.com", notes="", active=True),
        dict(id=4, name="Patrícia Lacerda", phone="(11) 95432-1098", email="", notes="Cliente de contrato mensal.", active=True),
        dict(id=5, name="Eduardo Nogueira", phone="(11) 94321-0987", email="", notes="", active=True),
        dict(id=6, name="Camila Rocha", phone="(11) 93210-9876", email="camila@exemplo.com", notes="", active=True),
    ]
    vehicles = [
        dict(id=1, client_id=1, brand="BMW", model="320i", year=2021, color="Preto", plate="LXD3B47"),
        dict(id=2, client_id=2, brand="Jeep", model="Compass", year=2022, color="Cinza", plate="FHK5J82"),
        dict(id=3, client_id=3, brand="Honda", model="Civic", year=2019, color="Prata", plate="PQR1234"),
        dict(id=4, client_id=4, brand="Toyota", model="Corolla", year=2023, color="Branco", plate="GTA8C09"),
        dict(id=5, client_id=5, brand="Volkswagen", model="Golf GTI", year=2020, color="Vermelho", plate="MNO5B67"),
        dict(id=6, client_id=6, brand="Audi", model="A3", year=2022, color="Azul", plate="RJK2D45"),
        dict(id=7, client_id=1, brand="Fiat", model="Toro", year=2021, color="Cinza", plate="KYT6H31"),
    ]
    services = [
        dict(id=1, name="Lavagem simples", description="Lavagem externa com secagem.", price_cents=5000, duration_min=40, active=True),
        dict(id=2, name="Lavagem completa", description="Lavagem externa e aspiração interna.", price_cents=9000, duration_min=90, active=True),
        dict(id=3, name="Lavagem premium", description="Lavagem completa com cera líquida e acabamento.", price_cents=15000, duration_min=120, active=True),
        dict(id=4, name="Higienização interna", description="Limpeza profunda de bancos, carpetes e painel.", price_cents=28000, duration_min=180, active=True),
        dict(id=5, name="Polimento", description="Correção de riscos leves e restauração do brilho.", price_cents=45000, duration_min=240, active=True),
        dict(id=6, name="Enceramento", description="Proteção da pintura com cera de carnaúba.", price_cents=16000, duration_min=90, active=True),
        dict(id=7, name="Vitrificação", description="Proteção cerâmica de longa duração.", price_cents=120000, duration_min=300, active=True),
    ]

    def appt(i, cid, vid, sid, day, time, status, price, dur, **kw):
        base = dict(id=i, client_id=cid, vehicle_id=vid, service_id=sid, date=d(day), time=time,
                    status=status, notes="", region="", progress=0, started_at="", finished_at="",
                    price_cents=price, duration_min=dur, paid=False, payment_method="", paid_date="")
        base.update(kw)
        return base

    appointments = [
        # hoje
        appt(1, 3, 3, 1, 0, "08:00", "done", 5000, 40, progress=100, started_at="08:00", finished_at="08:40",
             paid=True, payment_method="PIX", paid_date=d(0)),
        appt(2, 2, 2, 2, 0, "08:30", "done", 9000, 90, progress=100, started_at="08:30", finished_at="10:00"),
        appt(3, 1, 1, 5, 0, "10:00", "in_progress", 45000, 240, region="capo", progress=50, started_at="10:05",
             notes="Atenção a riscos no capô."),
        appt(4, 4, 4, 4, 0, "10:30", "in_progress", 28000, 180, region="teto", progress=25, started_at="10:30"),
        appt(5, 5, 5, 3, 0, "14:00", "scheduled", 15000, 120),
        appt(6, 6, 6, 6, 0, "15:30", "scheduled", 16000, 90, region="porta_malas"),
        appt(7, 3, 3, 1, 0, "16:30", "scheduled", 5000, 40),
        # amanhã
        appt(8, 1, 7, 7, 1, "09:00", "scheduled", 120000, 300, notes="Aplicar em toda a pintura."),
        appt(9, 2, 2, 2, 1, "14:30", "scheduled", 9000, 90),
        # ontem e anteontem (concluídos e pagos)
        appt(10, 4, 4, 3, -1, "09:00", "done", 15000, 120, progress=100, started_at="09:00", finished_at="11:00",
             paid=True, payment_method="PIX", paid_date=d(-1)),
        appt(11, 5, 5, 5, -1, "14:00", "done", 45000, 240, progress=100, started_at="14:00", finished_at="18:00",
             paid=True, payment_method="Cartão de crédito", paid_date=d(-1)),
        appt(12, 6, 6, 1, -2, "10:00", "done", 5000, 40, progress=100, started_at="10:00", finished_at="10:40",
             paid=True, payment_method="Dinheiro", paid_date=d(-2)),
    ]

    finance = [
        dict(id=1, kind="income", description="Lavagem simples — Ricardo Menezes", amount_cents=5000, date=d(0), method="PIX", category="Serviço", appointment_id=1),
        dict(id=2, kind="income", description="Lavagem premium — Patrícia Lacerda", amount_cents=15000, date=d(-1), method="PIX", category="Serviço", appointment_id=10),
        dict(id=3, kind="income", description="Polimento — Eduardo Nogueira", amount_cents=45000, date=d(-1), method="Cartão de crédito", category="Serviço", appointment_id=11),
        dict(id=4, kind="income", description="Lavagem simples — Camila Rocha", amount_cents=5000, date=d(-2), method="Dinheiro", category="Serviço", appointment_id=12),
        dict(id=5, kind="expense", description="Reposição de shampoo e cera", amount_cents=38000, date=d(-3), method="PIX", category="Produtos", appointment_id=None),
        dict(id=6, kind="expense", description="Conta de água", amount_cents=21000, date=d(-4), method="Dinheiro", category="Energia/Água", appointment_id=None),
    ]

    products = [
        dict(id=1, name="Shampoo automotivo neutro", category="Lavagem", quantity=18, unit="L", min_stock=10, unit_cost_cents=2400),
        dict(id=2, name="Cera de carnaúba", category="Proteção", quantity=6, unit="un", min_stock=4, unit_cost_cents=11000),
        dict(id=3, name="Vitrificante cerâmico", category="Proteção", quantity=450, unit="mL", min_stock=500, unit_cost_cents=95),
        dict(id=4, name="Microfibra 40x40", category="Acessórios", quantity=32, unit="un", min_stock=20, unit_cost_cents=1100),
        dict(id=5, name="Polidor composto", category="Polimento", quantity=3, unit="L", min_stock=2, unit_cost_cents=14500),
        dict(id=6, name="Limpador de estofados", category="Interior", quantity=7, unit="L", min_stock=5, unit_cost_cents=3200),
        dict(id=7, name="Pretinho para pneus", category="Lavagem", quantity=9, unit="L", min_stock=4, unit_cost_cents=2800),
        dict(id=8, name="Aplicador de espuma", category="Acessórios", quantity=4, unit="un", min_stock=10, unit_cost_cents=600),
    ]
    stamp = lambda n, h: f"{d(n)} {h}"   # noqa: E731
    movements = [
        dict(id=1, product_id=1, kind="in", quantity=20, date=stamp(-6, "09:00"), note="Estoque inicial"),
        dict(id=2, product_id=1, kind="out", quantity=2, date=stamp(-1, "11:10"), note="Uso em lavagens"),
        dict(id=3, product_id=3, kind="in", quantity=500, date=stamp(-6, "09:05"), note="Estoque inicial"),
        dict(id=4, product_id=3, kind="out", quantity=50, date=stamp(-2, "15:20"), note="Aplicação de vitrificação"),
        dict(id=5, product_id=8, kind="out", quantity=6, date=stamp(0, "09:40"), note="Reposição da bancada"),
    ]

    return {
        "version": 1, "meta": dict(DEFAULT_SETTINGS),
        "clients": clients, "vehicles": vehicles, "services": services,
        "appointments": appointments, "products": products,
        "movements": movements, "finance": finance,
    }
