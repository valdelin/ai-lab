"""Graders deterministicos do `cycling-coach` para o insight.

Camada 1 (schema) vive em `src/insight/contract.py`. Aqui e a camada 2:
invariantes semanticas — as regras que o prompt nao consegue garantir e
que o LLM tem motivo real de violar.

Nenhum grader aqui chama LLM. Se um dia precisar, vira `llm_judge` e passa
a contar custo e latencia no relatorio.
"""
import re

NUMERO = re.compile(r"-?\d+(?:[.,]\d+)?")

# Tokens que o LLM usa para arredondar e que nao precisam estar no contexto.
TOLERANCIA_ROUNDING = {"0", "1"}


def _numeros(texto):
    return {m.group(0).replace(",", ".") for m in NUMERO.finditer(texto or "")}


def _contexto_numeros(ctx_raw):
    return {n.rstrip("0").rstrip(".") if "." in n else n for n in _numeros(ctx_raw)}


def contrato_ok(payload, ctx):
    """Grader 1: saida conforme o schema do contrato."""
    from insight.contract import contract_errors
    return not contract_errors(payload, ctx)


def foco_igual_ao_motor(payload, ctx):
    """Grader 2: o LLM nao pode mudar a decisao do motor."""
    return payload.get("foco") == ctx.foco_motor


def duracao_coerente(payload, ctx):
    """Grader 3: nao alonga/encurta a sessao prescrita alem do razoavel."""
    return abs(payload.get("duracao_min", -999) - ctx.tl_duracao_min) <= 10


def sem_numero_inventado(payload, ctx):
    """Grader 4: todo numero citado na `acao` tem que existir nos dados.

    Este e o grader que protege o atleta de ler uma carga/power que o
    motor nunca produziu."""
    citados = _numeros(payload.get("acao", ""))
    conhecidos = _contexto_numeros(ctx.raw)
    return citados <= conhecidos


def alerta_so_quando_gatilho(payload, ctx):
    """Grader 5: alerta so com TSB <= -20. Ceder aqui treina o atleta a
    ignorar alerta."""
    tem_alerta = payload.get("alerta") is not None
    gatilho = ctx.tsb <= -20
    return tem_alerta == gatilho


GRADERS = [
    ("contrato", contrato_ok),
    ("foco_do_motor", foco_igual_ao_motor),
    ("duracao", duracao_coerente),
    ("sem_numero_inventado", sem_numero_inventado),
    ("alerta_gatilho", alerta_so_quando_gatilho),
]
