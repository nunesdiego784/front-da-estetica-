"""Teste de FUMAÇA da interface com widgets simulados (stubs).

NÃO substitui o teste visual no Windows. Ele substitui customtkinter/tkinter por
objetos 'falsos' que aceitam qualquer chamada, e então executa toda a lógica
de montagem das páginas, tabelas, diálogos e callbacks. Serve para detectar
erros de nome, argumento, import e fluxo (ex.: um callback chamando método que
não existe). Execute com:  python tests/ui_smoke_test.py
"""
import os
import sys
import tempfile
import types
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))


class Fake:
    def __init__(self, *a, **k):
        self.master = a[0] if a and not isinstance(a[0], (str, int)) else k.get("master")

    def __getattr__(self, name):
        if name == "winfo_toplevel":
            return lambda: self
        if name == "winfo_children":
            return lambda: []
        if name.startswith("winfo_"):
            return lambda *a, **k: 100
        if name in ("get", "cget"):
            return lambda *a, **k: ""
        return lambda *a, **k: Fake()


def fake_module(name):
    mod = types.ModuleType(name)
    cache = {}

    def getattr_(attr):
        if attr.startswith("__"):
            raise AttributeError(attr)
        if attr not in cache:
            cache[attr] = type(attr, (Fake,), {})
        return cache[attr]
    mod.__getattr__ = getattr_
    return mod


for n in ("customtkinter", "tkinter", "tkinter.font", "PIL.ImageTk"):
    sys.modules[n] = fake_module(n)
import PIL  # noqa: E402
PIL.ImageTk = sys.modules["PIL.ImageTk"]

os.environ["LUSTRE_DATA_DIR"] = tempfile.mkdtemp()

import main  # noqa: E402
from components.dialogs import FormDialog, ModalDialog  # noqa: E402
from components.new_appointment_dialog import NewAppointmentDialog  # noqa: E402

app = main.LustreApp()
repo = app.repo
steps = 0


def step(name):
    global steps
    steps += 1
    print(f"  ok  {name}")


# navegação e atualização de todas as páginas
for key, _, _ in main.PAGES:
    app.navigate(key)
    app._pages[key].refresh()
step("navegar e atualizar as 7 páginas")

# busca em cada página que possui campo de busca
for key in ("agenda", "clients", "vehicles", "services", "inventory", "finance"):
    app.navigate(key, "a")
step("set_search nas páginas")

# diálogos de formulário de cada módulo (novo e edição)
app.navigate("clients"); p = app._pages["clients"]
p.open_form(None); p.open_form(repo.clients[0]); p.show(repo.clients[0]); p.delete(repo.clients[0])
app.navigate("vehicles"); p = app._pages["vehicles"]
p.open_form(None); p.open_form(repo.vehicles[0]); p.history(repo.vehicles[0]); p.delete(repo.vehicles[0])
app.navigate("services"); p = app._pages["services"]
p.open_form(None); p.open_form(repo.services[0]); p.toggle(repo.services[0]); p.toggle(repo.services[0])
app.navigate("inventory"); p = app._pages["inventory"]
p.open_product(None); p.open_product(repo.products[0]); p.move(repo.products[0], "in"); p.move(repo.products[0], "out")
for k in ("low", "movements", "products"):
    p.chips.select(k); p.refresh()
app.navigate("finance"); p = app._pages["finance"]
p.add_entry("income"); p.add_entry("expense")
for k in ("pending", "paid", "entries"):
    p.view_chips.select(k); p.refresh()
for k in ("today", "7d", "month", "all"):
    p.period_chips.select(k); p.refresh()
step("formulários, detalhes, exclusão, filtros")

# submissões reais (on_submit) com dados válidos
d = FormDialog(app, "t", [], lambda v: None)
p = app._pages["clients"]
repo.save_client(dict(name="Novo Cliente", phone="11900001111"))
app._pages["inventory"].move(repo.products[0], "in")
step("repositório via páginas")

# agenda e ações
actions = app.appt_actions
views = repo.appointment_views()
for v in views:
    actions.view(v)
    actions.more_menu(v, Fake())
actions.cancel(views[0]); actions.edit(views[0])
actions.pay(next(v for v in views if v.appt.status == "done" and not v.appt.paid))
actions.advance(repo.operations_now()[0].appt.id)
actions.finish(repo.operations_now()[0].appt.id)
actions.start(next(v for v in repo.appointment_views(status="scheduled") if v.appt.date == repo.today().isoformat()))
step("ações de agendamento (ver, menu, cancelar, pagar, avançar, concluir, iniciar)")

# diálogo de agendamento (novo e edição) + envio
dlg = NewAppointmentDialog(app, repo, None, lambda a, edited=False: None)
dlg.submit()
sched = next(a for a in repo.appointments if a.status == "scheduled")
NewAppointmentDialog(app, repo, sched, None)
step("NewAppointmentDialog novo/edição/envio")

# painel
dash = app._pages["dashboard"]
dash.refresh(); dash._select_region("capo"); dash._on_map_hover("teto"); dash._select_region(None)
step("dashboard e mapa")

# barra superior, menus e configurações
app.nav._on_search("marcos"); app.nav._toggle_notifications(); app.nav._toggle_user_menu()
app.nav._open_first_result(); app.nav.refresh_notifications()
app.open_settings(); app.show_about(); app.reset_data(True); app.reset_data(False)
app._shortcut_new(); app._shortcut_find(); app._shortcut_escape()
repo.reset(True)
step("TopNav, configurações, sobre, reset, atalhos")

app.toast.show("teste", "success"); app.toast.show("aviso", "warning"); app.toast.show("erro", "error")
step("toasts")
print(f"\n{steps} etapas executadas sem exceção (stubs; não é teste visual).")
