"""Formatação e interpretação de valores (moeda, datas, horas, telefone, placa).

Valores monetários são tratados internamente como inteiros em centavos para
evitar erros de arredondamento de ponto flutuante.
"""
import math
import re
import unicodedata
from datetime import date, datetime, timedelta
from decimal import Decimal

MONTHS_PT = ["janeiro", "fevereiro", "março", "abril", "maio", "junho", "julho",
             "agosto", "setembro", "outubro", "novembro", "dezembro"]
WEEKDAYS_PT = ["segunda-feira", "terça-feira", "quarta-feira", "quinta-feira",
               "sexta-feira", "sábado", "domingo"]


# ------------------------------------------------------------------ dinheiro
def brl(cents: int) -> str:
    """Formata centavos como moeda brasileira: 123456 -> 'R$ 1.234,56'."""
    cents = int(cents)
    sign = "-" if cents < 0 else ""
    cents = abs(cents)
    reais = f"{cents // 100:,}".replace(",", ".")
    return f"{sign}R$ {reais},{cents % 100:02d}"


def parse_brl(text: str) -> int:
    """Converte texto como 'R$ 1.234,56', '80' ou '80,5' em centavos.

    Levanta ``ValueError`` se o texto não for um valor monetário válido.
    """
    s = str(text).strip().replace("R$", "").replace(" ", "")
    if not s:
        raise ValueError("valor vazio")
    if "," in s:
        s = s.replace(".", "").replace(",", ".")
    elif s.count(".") == 1 and len(s.split(".")[1]) <= 2:
        pass  # '80.5' -> decimal
    else:
        s = s.replace(".", "")  # '1.234' -> milhar
    if not re.fullmatch(r"\d{1,12}(\.\d+)?", s):
        raise ValueError("valor inválido")
    return int((Decimal(s) * 100).quantize(Decimal("1")))


def parse_quantity(text: str) -> float:
    """Converte '2,5' ou '2.5' em float (3 casas). ``ValueError`` se inválido."""
    s = str(text).strip().replace(",", ".")
    try:
        q = float(s)
    except ValueError:
        raise ValueError("quantidade inválida") from None
    if not math.isfinite(q):
        raise ValueError("quantidade inválida")
    return round(q, 3)


def format_quantity(q: float) -> str:
    """Mostra 3 -> '3' e 2.5 -> '2,5'."""
    if abs(q - round(q)) < 1e-9:
        return str(int(round(q)))
    return f"{q:.3f}".rstrip("0").rstrip(".").replace(".", ",")


# ------------------------------------------------------------------ telefone
def digits(text: str) -> str:
    """Mantém apenas os dígitos."""
    return re.sub(r"\D", "", str(text))


def format_phone(text: str) -> str:
    """Formata telefones de 10 ou 11 dígitos; devolve o texto original se não couber."""
    d = digits(text)
    if len(d) == 11:
        return f"({d[:2]}) {d[2:7]}-{d[7:]}"
    if len(d) == 10:
        return f"({d[:2]}) {d[2:6]}-{d[6:]}"
    return str(text).strip()


# --------------------------------------------------------------------- placa
_PLATE_OLD = re.compile(r"[A-Z]{3}\d{4}")
_PLATE_MERCOSUL = re.compile(r"[A-Z]{3}\d[A-Z]\d{2}")


def normalize_plate(text: str) -> str:
    """Maiúsculas, sem hífen nem espaços."""
    return re.sub(r"[^A-Za-z0-9]", "", str(text)).upper()


def is_valid_plate(text: str) -> bool:
    """Aceita o padrão Mercosul (ABC1D23) e o antigo (ABC-1234)."""
    p = normalize_plate(text)
    return bool(_PLATE_MERCOSUL.fullmatch(p) or _PLATE_OLD.fullmatch(p))


def format_plate(text: str) -> str:
    """Placa antiga recebe hífen (ABC-1234); Mercosul permanece como está."""
    p = normalize_plate(text)
    if _PLATE_OLD.fullmatch(p):
        return f"{p[:3]}-{p[3:]}"
    return p


# ------------------------------------------------------------- datas e horas
def _to_date(value) -> date:
    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, date):
        return value
    return date.fromisoformat(str(value)[:10])


def parse_date_br(text: str) -> date:
    """Lê 'DD/MM/AAAA' (ou 'DDMMAAAA'). ``ValueError`` se inválida."""
    s = str(text).strip()
    if re.fullmatch(r"\d{8}", s):
        s = f"{s[:2]}/{s[2:4]}/{s[4:]}"
    m = re.fullmatch(r"(\d{1,2})/(\d{1,2})/(\d{4})", s)
    if not m:
        raise ValueError("data inválida")
    d, mo, y = map(int, m.groups())
    return date(y, mo, d)  # ValueError para dias inexistentes


def format_date_br(value) -> str:
    """'2026-10-11' ou date -> '11/10/2026'."""
    return _to_date(value).strftime("%d/%m/%Y")


def relative_day_label(value, today: date) -> str:
    """'Hoje', 'Amanhã', 'Ontem' ou 'dd/mm'."""
    d = _to_date(value)
    if d == today:
        return "Hoje"
    if d == today + timedelta(days=1):
        return "Amanhã"
    if d == today - timedelta(days=1):
        return "Ontem"
    return d.strftime("%d/%m")


def date_long_pt(value) -> str:
    """'domingo, 11 de outubro de 2026'."""
    d = _to_date(value)
    return f"{WEEKDAYS_PT[d.weekday()]}, {d.day} de {MONTHS_PT[d.month - 1]} de {d.year}"


def parse_time(text: str) -> str:
    """Normaliza '9:30', '0930' ou '9h30' para 'HH:MM'. ``ValueError`` se inválido."""
    s = str(text).strip().lower().replace("h", ":")
    if re.fullmatch(r"\d{3,4}", s):
        s = s[:-2] + ":" + s[-2:]
    m = re.fullmatch(r"(\d{1,2}):?(\d{2})?", s)
    if not m:
        raise ValueError("horário inválido")
    h, mi = int(m.group(1)), int(m.group(2) or 0)
    if not (0 <= h <= 23 and 0 <= mi <= 59):
        raise ValueError("horário inválido")
    return f"{h:02d}:{mi:02d}"


def time_to_min(hhmm: str) -> int:
    """'09:30' -> 570."""
    h, m = hhmm.split(":")
    return int(h) * 60 + int(m)


def min_to_time(minutes: int) -> str:
    """570 -> '09:30'."""
    return f"{minutes // 60:02d}:{minutes % 60:02d}"


def format_duration(minutes: int) -> str:
    """90 -> '1h30', 40 -> '40 min', 120 -> '2h'."""
    h, m = divmod(int(minutes), 60)
    if h == 0:
        return f"{m} min"
    return f"{h}h{m:02d}" if m else f"{h}h"


# -------------------------------------------------------------------- textos
def truncate(text: str, size: int) -> str:
    """Corta o texto com reticências."""
    text = str(text)
    return text if len(text) <= size else text[: size - 1].rstrip() + "…"


def normalize_text(text: str) -> str:
    """Minúsculas e sem acentos, para buscas tolerantes."""
    nfkd = unicodedata.normalize("NFKD", str(text))
    return "".join(ch for ch in nfkd if not unicodedata.combining(ch)).lower()


def matches(query: str, *fields) -> bool:
    """True se todas as palavras de ``query`` aparecem em algum campo.

    Busca sem acento e sem diferenciar maiúsculas. Placas e telefones também
    casam ignorando hífens, espaços e parênteses.
    """
    q = normalize_text(query).strip()
    if not q:
        return True
    haystack = " ".join(normalize_text(f) for f in fields if f is not None)
    compact = re.sub(r"[^a-z0-9]", "", haystack)
    for token in q.split():
        if token in haystack:
            continue
        t2 = re.sub(r"[^a-z0-9]", "", token)
        if t2 and t2 in compact:
            continue
        return False
    return True
