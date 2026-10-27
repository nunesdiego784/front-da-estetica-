"""Testes automatizados da camada de dados (não dependem de interface gráfica).

Execute com:  python -m unittest discover -s tests -v
"""
import json
import sys
import tempfile
import unittest
from datetime import date, datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from data.repository import Repository, ValidationError  # noqa: E402

TODAY = date(2026, 10, 11)
NOW = datetime(2026, 10, 11, 10, 15)


def make_repo(tmp, demo=True):
    repo = Repository(Path(tmp) / "data.json", today_fn=lambda: TODAY, now_fn=lambda: NOW)
    if not demo:
        repo.reset(demo=False)
    return repo


class RepoTests(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.repo = make_repo(self._tmp.name)

    def tearDown(self):
        self._tmp.cleanup()

    def appt(self, **kw):
        base = dict(client_id=1, vehicle_id=7, service_id=1, date="11/10/2026", time="14:30", region="", notes="")
        base.update(kw)
        return base

    # ---------- persistência
    def test_seed_and_reload(self):
        self.assertTrue(self.repo.is_demo)
        again = make_repo(self._tmp.name)
        self.assertEqual(len(again.appointments), len(self.repo.appointments))
        self.repo.save_client(dict(name="Teste Silva", phone="11911112222"))
        self.assertEqual(len(make_repo(self._tmp.name).clients), len(self.repo.clients))

    def test_corrupt_file_is_preserved(self):
        (Path(self._tmp.name) / "data.json").write_text("{ não é json", encoding="utf-8")
        repo = make_repo(self._tmp.name)
        self.assertIsNotNone(repo.load_warning)
        self.assertTrue(list(Path(self._tmp.name).glob("data.json.corrupt-*")))
        self.assertTrue(repo.clients)

    def test_listeners_called(self):
        calls = []
        self.repo.subscribe(lambda: calls.append(1))
        self.repo.save_client(dict(name="Ana Souza", phone="(11) 90000-1111"))
        self.assertEqual(len(calls), 1)

    # ---------- clientes
    def test_client_validation(self):
        for bad in (dict(name="Al", phone="11911112222"), dict(name="Ana Souza", phone="123"),
                    dict(name="Ana Souza", phone="11911112222", email="x@")):
            with self.assertRaises(ValidationError):
                self.repo.save_client(bad)
        with self.assertRaises(ValidationError):  # telefone duplicado
            self.repo.save_client(dict(name="Outra Pessoa", phone="11987654321"))

    def test_delete_client_with_history_is_blocked(self):
        with self.assertRaises(ValidationError) as ctx:
            self.repo.delete_client(1)
        self.assertIn("inativ", str(ctx.exception).lower())
        c = self.repo.save_client(dict(name="Sem Histórico", phone="11922223333"))
        self.repo.delete_client(c.id)
        self.assertIsNone(self.repo.get_client(c.id))

    # ---------- veículos
    def test_vehicle_plate(self):
        base = dict(client_id=1, brand="Ford", model="Ka", year=2018, color="Preto")
        with self.assertRaises(ValidationError):
            self.repo.save_vehicle({**base, "plate": "ABCD123"})
        with self.assertRaises(ValidationError):  # duplicada (LXD3B47 já existe)
            self.repo.save_vehicle({**base, "plate": "lxd-3b47"})
        old = self.repo.save_vehicle({**base, "plate": "abc-1234"})
        self.assertEqual(old.plate, "ABC1234")
        new = self.repo.save_vehicle({**base, "plate": "ABC1D23"})
        self.assertEqual(new.plate, "ABC1D23")

    def test_delete_vehicle_with_history_is_blocked(self):
        with self.assertRaises(ValidationError):
            self.repo.delete_vehicle(1)

    # ---------- serviços
    def test_service_rules(self):
        with self.assertRaises(ValidationError):
            self.repo.save_service(dict(name="Lavagem simples", price="10", duration="30"))  # nome duplicado
        with self.assertRaises(ValidationError):
            self.repo.save_service(dict(name="Novo serviço", price="0", duration="30"))
        with self.assertRaises(ValidationError):
            self.repo.save_service(dict(name="Novo serviço", price="10", duration="5"))
        s = self.repo.save_service(dict(name="Novo serviço", price="1.250,50", duration="60"))
        self.assertEqual(s.price_cents, 125050)
        self.repo.set_service_active(s.id, False)
        with self.assertRaises(ValidationError):
            self.repo.save_appointment(self.appt(service_id=s.id))

    # ---------- agenda
    def test_create_edit_cancel(self):
        a = self.repo.save_appointment(self.appt())
        self.assertEqual((a.price_cents, a.duration_min), (5000, 40))
        edited = self.repo.save_appointment(self.appt(time="17:00"), a.id)
        self.assertEqual(edited.time, "17:00")
        self.repo.cancel_appointment(a.id)
        with self.assertRaises(ValidationError):
            self.repo.cancel_appointment(a.id)

    def test_price_snapshot_survives_service_change(self):
        a = self.repo.save_appointment(self.appt())
        self.repo.save_service(dict(name="Lavagem simples", price="99", duration="40"), 1)
        self.assertEqual(self.repo.get_appointment(a.id).price_cents, 5000)

    def test_schedule_validations(self):
        cases = {
            "data inválida": self.appt(date="31/02/2026"),
            "horário inválido": self.appt(time="25:99"),
            "passado": self.appt(date="10/10/2026"),
            "hoje já passou": self.appt(time="09:00"),
            "antes de abrir": self.appt(date="12/10/2026", time="07:00"),
            "termina depois de fechar": self.appt(date="12/10/2026", time="17:30"),
            "veículo de outro cliente": self.appt(client_id=1, vehicle_id=5),
            "sem cliente": self.appt(client_id=None),
        }
        for name, data in cases.items():
            with self.subTest(name):
                with self.assertRaises(ValidationError):
                    self.repo.save_appointment(data)

    def test_capacity_conflict(self):
        # 14:00-16:00 (id5) e 15:30-17:00 (id6) já existem; capacidade = 2
        self.repo.save_appointment(self.appt(time="14:30"))  # só 1 simultâneo -> permitido
        with self.assertRaises(ValidationError) as ctx:
            self.repo.save_appointment(self.appt(time="15:40"))
        self.assertIn("Capacidade", str(ctx.exception))

    def test_vehicle_double_booking(self):
        with self.assertRaises(ValidationError):
            self.repo.save_appointment(self.appt(client_id=5, vehicle_id=5, time="14:10"))  # veículo 5 já às 14:00

    def test_capacity_counts_real_concurrency(self):
        repo = make_repo(self._tmp.name, demo=False)
        c1 = repo.save_client(dict(name="Cliente Um", phone="11911110001"))
        c2 = repo.save_client(dict(name="Cliente Dois", phone="11911110002"))
        c3 = repo.save_client(dict(name="Cliente Três", phone="11911110003"))
        vs = [repo.save_vehicle(dict(client_id=c.id, brand="Ford", model="Ka", year=2020, color="Preto", plate=p))
              for c, p in ((c1, "AAA1A11"), (c2, "BBB2B22"), (c3, "CCC3C33"))]
        s = repo.save_service(dict(name="Serviço 60", price="10", duration="60"))
        mk = lambda c, v, t: dict(client_id=c.id, vehicle_id=v.id, service_id=s.id, date="12/10/2026", time=t)  # noqa: E731
        repo.save_appointment(mk(c1, vs[0], "08:00"))   # 08:00-09:00
        repo.save_appointment(mk(c2, vs[1], "09:00"))   # 09:00-10:00
        # 08:30-09:30 encosta nos dois, mas nunca há 3 ao mesmo tempo -> permitido
        repo.save_appointment(mk(c3, vs[2], "08:30"))
        self.assertEqual(len(repo.appointments), 3)

    # ---------- andamento e financeiro
    def test_start_requires_capacity_then_flow(self):
        with self.assertRaises(ValidationError):
            self.repo.start_appointment(5)          # já há 2 em andamento
        self.repo.finish_appointment(3)
        self.repo.start_appointment(5)
        a = self.repo.advance_progress(5)
        self.assertEqual((a.status, a.progress), ("in_progress", 25))
        with self.assertRaises(ValidationError):
            self.repo.start_appointment(8)          # amanhã: não pode iniciar hoje

    def test_payment_creates_income_once(self):
        before = self.repo.finance_summary(*self.repo.period_range("today"))["income"]
        self.assertEqual(before, 5000)
        self.repo.register_payment(2, "PIX")        # lavagem completa R$ 90
        after = self.repo.finance_summary(*self.repo.period_range("today"))
        self.assertEqual(after["income"], 14000)
        with self.assertRaises(ValidationError):
            self.repo.register_payment(2, "PIX")    # já pago
        with self.assertRaises(ValidationError):
            self.repo.register_payment(5, "PIX")    # ainda agendado
        with self.assertRaises(ValidationError):
            self.repo.cancel_appointment(2)         # concluído

    def test_forecast_not_counted_as_received(self):
        total = self.repo.finance_summary()["income"]
        paid = sum(e.amount_cents for e in self.repo.finance if e.kind == "income")
        self.assertEqual(total, paid)
        self.assertEqual(self.repo.pending_total(), 9000)   # só o concluído e não pago

    def test_future_entry_rejected_and_balance(self):
        with self.assertRaises(ValidationError):
            self.repo.add_entry("expense", dict(description="Compra", amount="10", date="20/10/2026", method="PIX"))
        self.repo.add_entry("expense", dict(description="Compra de panos", amount="50,00", date="11/10/2026", method="PIX"))
        s = self.repo.finance_summary(*self.repo.period_range("today"))
        self.assertEqual(s["balance"], s["income"] - s["expense"])
        self.assertEqual(s["expense"], 5000)
        only_pix = self.repo.finance_summary(method="Dinheiro")
        self.assertEqual(only_pix["income"], 5000)

    # ---------- estoque
    def test_stock_rules(self):
        p = self.repo.get_product(1)
        with self.assertRaises(ValidationError):
            self.repo.move_stock(1, "out", str(p.quantity + 1))
        with self.assertRaises(ValidationError):
            self.repo.move_stock(1, "out", "0")
        with self.assertRaises(ValidationError):
            self.repo.move_stock(1, "in", "abc")
        self.repo.move_stock(1, "out", "2,5", "uso")
        self.assertAlmostEqual(self.repo.get_product(1).quantity, p.quantity)
        self.repo.move_stock(1, "in", "10")
        self.assertIn(3, [x.id for x in self.repo.low_stock_products()])

    def test_new_product_registers_initial_movement(self):
        n = len(self.repo.movements)
        self.repo.save_product(dict(name="Álcool isopropílico", category="Lavagem", unit="L",
                                    quantity="5", min_stock="2", unit_cost="30,00"))
        self.assertEqual(len(self.repo.movements), n + 1)

    # ---------- painel
    def test_dashboard_stats_are_computed(self):
        s = self.repo.dashboard_stats()
        self.assertEqual(s["total_today"], 7)
        self.assertEqual(s["in_progress"], 2)
        self.assertEqual(s["ready_today"], 2)
        self.assertEqual(s["revenue_today"], 5000)
        self.assertEqual(s["revenue_yesterday"], 60000)
        self.assertEqual(s["receivable_today"], 9000)

    def test_upcoming_and_search(self):
        up = self.repo.upcoming(3)
        self.assertEqual([v.appt.id for v in up], [5, 6, 7])
        self.assertTrue(self.repo.global_search("marcos"))
        self.assertTrue(self.repo.list_vehicles("lxd-3b47"))
        self.assertEqual(self.repo.global_search("a"), [])

    def test_settings(self):
        with self.assertRaises(ValidationError):
            self.repo.update_settings("0", "08:00", "18:00")
        with self.assertRaises(ValidationError):
            self.repo.update_settings("2", "18:00", "08:00")
        self.repo.update_settings("3", "7:30", "19:00")
        self.assertEqual((self.repo.capacity, self.repo.meta["open"]), (3, "07:30"))

    def test_json_is_valid_utf8(self):
        data = json.loads((Path(self._tmp.name) / "data.json").read_text(encoding="utf-8"))
        self.assertIn("appointments", data)


if __name__ == "__main__":
    unittest.main()
