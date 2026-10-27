"""Janelas secundárias reutilizáveis: base modal, formulário genérico, confirmação e detalhes."""
from dataclasses import dataclass
from typing import Callable, Optional

import customtkinter as ctk

from data.repository import RepositoryError
from utils import colors as C
from utils.theme import scaling

from .widgets import button, caption, checkbox, combo, entry, label, textbox


class ModalDialog(ctk.CTkToplevel):
    """Janela modal centralizada sobre a janela principal.

    * Esc fecha.
    * ``ModalDialog.open_count`` permite que os atalhos globais saibam que há
      um diálogo aberto.
    """

    open_count = 0

    def __init__(self, master, title: str, width: int = 460, height: int = 300):
        super().__init__(master, fg_color=C.SURFACE)
        ModalDialog.open_count += 1
        self._destroyed = False
        self.dialog_width = width
        self.title(title)
        self.resizable(False, False)
        root = master.winfo_toplevel()
        self.transient(root)
        self._center(root, width, height)
        self.bind("<Escape>", lambda e: self.close())
        self.protocol("WM_DELETE_WINDOW", self.close)
        self.after(120, self._activate)

    def _center(self, root, width: int, height: int) -> None:
        root.update_idletasks()
        s = scaling(root)
        x = root.winfo_rootx() + (root.winfo_width() - width * s) / 2
        y = root.winfo_rooty() + (root.winfo_height() - height * s) / 3
        self.geometry(f"{int(width)}x{int(height)}+{int(max(0, x))}+{int(max(0, y))}")

    def _activate(self) -> None:
        try:
            self.lift()
            self.focus_force()
            self.grab_set()
        except Exception:
            pass  # janela fechada antes de ativar

    def close(self) -> None:
        try:
            self.grab_release()
        except Exception:
            pass
        self.destroy()

    def destroy(self) -> None:
        if not self._destroyed:
            self._destroyed = True
            ModalDialog.open_count = max(0, ModalDialog.open_count - 1)
        super().destroy()

    # -------------------------------------------------------- estrutura comum
    def shell(self, title: str, subtitle: str = ""):
        """Cria cabeçalho, área principal, linha de erro e rodapé de botões."""
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(1, weight=1)
        head = ctk.CTkFrame(self, fg_color="transparent")
        head.grid(row=0, column=0, sticky="ew", padx=24, pady=(20, 8))
        label(head, title, 26, C.TEXT, "bold", display=True, height=32).pack(anchor="w")
        if subtitle:
            label(head, subtitle, 12, C.TEXT_SECONDARY, height=18, wraplength=self.dialog_width - 48,
                  justify="left").pack(anchor="w")
        main = ctk.CTkFrame(self, fg_color="transparent")
        main.grid(row=1, column=0, sticky="nsew", padx=24)
        main.grid_columnconfigure(0, weight=1)
        self.error_label = label(self, "", 12, C.DANGER, height=40, wraplength=self.dialog_width - 48,
                                 justify="left")
        self.error_label.grid(row=2, column=0, sticky="ew", padx=24)
        footer = ctk.CTkFrame(self, fg_color="transparent")
        footer.grid(row=3, column=0, sticky="e", padx=24, pady=(4, 20))
        return main, footer

    def show_error(self, message: str) -> None:
        self.error_label.configure(text=message)


@dataclass
class Field:
    """Descrição de um campo de ``FormDialog``.

    ``kind``: text, multiline, choice ou check. Em ``choice``, ``options`` é uma lista
    de ``(valor, rótulo)`` (o valor devolvido é o primeiro item da tupla).
    """
    key: str
    label: str
    kind: str = "text"
    options: Optional[list] = None
    required: bool = True
    placeholder: str = ""
    hint: str = ""


class FormDialog(ModalDialog):
    """Formulário genérico: monta os campos, valida obrigatórios e chama ``on_submit(valores)``.

    ``on_submit`` pode levantar ``RepositoryError`` (mensagem mostrada no próprio
    diálogo, sem fechar). Se concluir sem erro, o diálogo fecha.
    """

    MAX_HEIGHT = 660

    def __init__(self, master, title: str, fields, on_submit: Callable, initial: Optional[dict] = None,
                 submit_text: str = "Salvar", subtitle: str = "", width: int = 480):
        body_h = sum({"multiline": 130, "check": 40}.get(f.kind, 70) + (16 if f.hint else 0) for f in fields)
        total = 150 + (22 if subtitle else 0) + body_h + 40
        height = min(total, self.MAX_HEIGHT)
        super().__init__(master, title, width, height)
        self.fields, self._on_submit = fields, on_submit
        initial = initial or {}
        main, footer = self.shell(title, subtitle)
        if total > self.MAX_HEIGHT:
            holder = ctk.CTkScrollableFrame(main, fg_color="transparent", corner_radius=0)
            holder.pack(fill="both", expand=True)
            main.grid_rowconfigure(0, weight=1)
            holder.grid_columnconfigure(0, weight=1)
            parent = holder
        else:
            parent = main
        self._widgets: dict = {}
        self._choice_maps: dict = {}
        first = None
        for i, f in enumerate(fields):
            wdg = self._make_field(parent, i, f, initial.get(f.key))
            if first is None and f.kind in ("text", "multiline"):
                first = wdg
        self._first = first
        button(footer, "Cancelar", self.close, "ghost").pack(side="left", padx=(0, 8))
        button(footer, submit_text, self.submit, "primary").pack(side="left")
        self.bind("<Return>", self._on_return)
        if first is not None:
            self.after(220, self._focus_first)

    def _focus_first(self) -> None:
        try:
            self._first.focus_set()
        except Exception:
            pass

    def _on_return(self, event) -> None:
        if event.widget.__class__.__name__ == "Text":   # Enter em campo multilinha = nova linha
            return
        self.submit()

    def _make_field(self, parent, row: int, f: Field, value):
        holder = ctk.CTkFrame(parent, fg_color="transparent")
        holder.grid(row=row, column=0, sticky="ew", pady=(0, 10))
        holder.grid_columnconfigure(0, weight=1)
        if f.kind == "check":
            w = checkbox(holder, f.label)
            w.grid(row=0, column=0, sticky="w")
            if value if value is not None else True:
                w.select()
            self._widgets[f.key] = w
            return w
        caption(holder, f.label + ("" if f.required else "  (opcional)")).grid(row=0, column=0, sticky="w")
        if f.kind == "multiline":
            w = textbox(holder, height=80)
            if value:
                w.insert("1.0", str(value))
        elif f.kind == "choice":
            options = f.options or []
            self._choice_maps[f.key] = {label_: val for val, label_ in options}
            labels = [label_ for _, label_ in options]
            w = combo(holder, labels or ["—"], width=200)
            current = next((label_ for val, label_ in options if val == value), None)
            if current:
                w.set(current)
        else:
            w = entry(holder, f.placeholder, width=200)
            if value not in (None, ""):
                w.insert(0, str(value))
        w.grid(row=1, column=0, sticky="ew", pady=(4, 0))
        if f.hint:
            label(holder, f.hint, 11, C.TEXT_MUTED, height=16).grid(row=2, column=0, sticky="w")
        self._widgets[f.key] = w
        return w

    def values(self) -> dict:
        """Lê os valores atuais do formulário (texto limpo, bool ou valor da opção)."""
        out = {}
        for f in self.fields:
            w = self._widgets[f.key]
            if f.kind == "check":
                out[f.key] = bool(w.get())
            elif f.kind == "multiline":
                out[f.key] = w.get("1.0", "end-1c").strip()
            elif f.kind == "choice":
                out[f.key] = self._choice_maps[f.key].get(w.get())
            else:
                out[f.key] = w.get().strip()
        return out

    def submit(self) -> None:
        vals = self.values()
        for f in self.fields:
            if f.required and f.kind in ("text", "multiline", "choice") and vals[f.key] in (None, ""):
                if f.kind != "choice" or not f.options:
                    self.show_error(f"Preencha o campo: {f.label}.")
                    return
        try:
            self._on_submit(vals)
        except RepositoryError as exc:
            self.show_error(str(exc))
            return
        self.close()


class ConfirmDialog(ModalDialog):
    """Pergunta de confirmação (ex.: cancelar agendamento, excluir cadastro)."""

    def __init__(self, master, title: str, message: str, on_confirm: Callable,
                 confirm_text: str = "Confirmar", danger: bool = True, cancel_text: str = "Voltar"):
        lines = max(2, -(-len(message) // 52))
        super().__init__(master, title, 440, 150 + lines * 20)
        main, footer = self.shell(title)
        label(main, message, 13, C.TEXT_SECONDARY, height=lines * 20, wraplength=392,
              justify="left", anchor="nw").grid(row=0, column=0, sticky="ew")
        self._on_confirm = on_confirm
        button(footer, cancel_text, self.close, "ghost").pack(side="left", padx=(0, 8))
        button(footer, confirm_text, self._confirm, "danger" if danger else "primary").pack(side="left")

    def _confirm(self) -> None:
        self.close()
        self._on_confirm()


class InfoDialog(ModalDialog):
    """Detalhes somente leitura: linhas 'rótulo: valor' e, opcionalmente, conteúdo extra."""

    def __init__(self, master, title: str, rows, subtitle: str = "",
                 extra: Optional[Callable] = None, extra_height: int = 0, width: int = 500):
        row_h = [max(1, -(-len(str(v)) // 46)) * 20 + 10 for _, v in rows]
        height = min(640, 140 + (22 if subtitle else 0) + sum(row_h) + extra_height + 20)
        super().__init__(master, title, width, height)
        main, footer = self.shell(title, subtitle)
        main.grid_columnconfigure(1, weight=1)
        main.grid_columnconfigure(0, weight=0)
        for i, (k, v) in enumerate(rows):
            caption(main, k).grid(row=i, column=0, sticky="nw", pady=(6, 0), padx=(0, 16))
            label(main, str(v) or "—", 13, C.TEXT, height=row_h[i] - 8, wraplength=width - 48 - 150,
                  justify="left", anchor="nw").grid(row=i, column=1, sticky="nw", pady=(2, 0))
        if extra:
            holder = ctk.CTkFrame(main, fg_color="transparent")
            holder.grid(row=len(rows), column=0, columnspan=2, sticky="nsew", pady=(14, 0))
            holder.grid_columnconfigure(0, weight=1)
            extra(holder)
        button(footer, "Fechar", self.close, "ghost").pack()
