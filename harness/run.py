"""Runner do harness: roda o dataset de um app contra os graders do adapter
e imprime o relatorio. Sem chave de API — o harness avalia saida ja
capturada, nunca chama o modelo.

Uso:
    PYTHONPATH=<repo>/src python -m harness.run <repo> <adapter>
"""
import argparse
import importlib.util
import inspect
import json
import sys
from pathlib import Path


def carregar_casos(cases_path):
    return [json.loads(linha) for linha in cases_path.read_text().splitlines() if linha.strip()]


def carregar_app(repo):
    """Carrega o adapter do app sem saber nada do dominio dele.

    O runner nao importa `insight`, `carrinho` nem nenhum modulo de app: ele
    recebe um arquivo e um contrato minimo (`CONTEXTO` e `GRADERS`). Se este
    runner precisar conhecer o dominio de um app para funcionar, o metodo
    voltou a ser copia — que e exatamente o que o ADR-004 diz para nao fazer.

    Contrato esperado em `<repo>/evals/graders.py`:
      - `GRADERS`: lista de (nome, fn(saida, ctx) -> bool)
      - `CONTEXTO`: str ou callable(dicionario) -> objeto de contexto
    """
    caminho = repo / "evals" / "graders.py"
    if not caminho.exists():
        raise SystemExit(
            f"adapter do app nao encontrado: {caminho}\n"
            "O app precisa de evals/graders.py expondo CONTEXTO e GRADERS."
        )

    # Antes de executar: o adapter do app importa do proprio src/ dele.
    sys.path.insert(0, str(repo / "src"))

    spec = importlib.util.spec_from_file_location(f"app_{repo.name}_graders", caminho)
    mod = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = mod
    spec.loader.exec_module(mod)

    for atributo in ("CONTEXTO", "GRADERS"):
        if not hasattr(mod, atributo):
            raise SystemExit(f"{caminho} nao define {atributo} (contrato do adapter)")

    # `CONTEXTO` pode ser a classe do contexto (instanciada por kwargs) ou uma
    # funcao que ja recebe o dicionario. Classe e dataclass sao `callable`,
    # entao `callable()` sozinho nao distingue os dois casos.
    if inspect.isclass(mod.CONTEXTO):
        return (lambda dados: mod.CONTEXTO(**dados)), mod.GRADERS
    if callable(mod.CONTEXTO):
        return mod.CONTEXTO, mod.GRADERS
    raise SystemExit(f"{caminho}: CONTEXTO precisa ser classe ou callable")


def avaliar(case, saida, ctx, graders):
    return {nome: bool(fn(saida, ctx)) for nome, fn in graders}


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("repo", help="caminho do repo do app (contem evals/ e src/)")
    args = ap.parse_args(argv)

    repo = Path(args.repo).resolve()
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

    build_ctx, graders = carregar_app(repo)
    casos = carregar_casos(repo / "evals" / "cases.jsonl")

    print(f"dataset: {len(casos)} casos | app: {repo.name} | {len(graders)} graders")
    print()

    totais = {nome: {"esperado": 0, "contra_rejeitado": 0, "contra_total": 0} for nome, _ in graders}
    problemas = []

    for caso in casos:
        ctx = build_ctx(caso["contexto"])

        res = avaliar(caso, caso["esperado"], ctx, graders)
        for nome, ok in res.items():
            totais[nome]["esperado"] += ok
        falhou = [n for n, ok in res.items() if not ok]
        if falhou:
            problemas.append(f"REGRESSAO {caso['id']}: caso bom reprovado por {falhou}")
        print(f"{'OK ' if not falhou else '!! '}{caso['id']:<22} esperado    "
              f"{'pass' if not falhou else 'falha: ' + ','.join(falhou)}")

        # contra-exemplo direcionado por grader: o dataset carrega, para cada
        # grader, a saida que ele existe para rejeitar. Um grader que reprova
        # o caso bom OU aceita o contra-exemplo dele esta quebrado.
        for nome, saida in (caso.get("contra") or {}).items():
            ok = dict(graders)[nome](saida, ctx)
            totais[nome]["contra_total"] += 1
            totais[nome]["contra_rejeitado"] += not ok
            print(f"{'OK ' if not ok else '!! '}{'':<22} contra:{nome:<12} "
                  f"{'rejeitado' if not ok else 'ACEITOU — grader nao discrimina'}")

    print()
    print("discriminacao por grader:")
    nao_discrimina = []
    for nome, _ in graders:
        t = totais[nome]
        total_esp = sum(1 for c in casos if "esperado" in c)
        if t["esperado"] < total_esp:
            status = "REGRESSAO — reprova caso bom"
            problemas.append(f"REGRESSAO {nome}: reprova {total_esp - t['esperado']} caso(s) bom(ns)")
        elif t["contra_total"] == 0:
            # Grader sem contra-exemplo nao foi provado: pode estar medindo nada
            # e ainda assim parecer verde. Nao e "ok", e ausência de prova.
            status = "SEM CONTRA-EXEMPLO — nao testado"
            nao_discrimina.append(nome)
        elif t["contra_rejeitado"] < t["contra_total"]:
            status = "NAO DISCRIMINA — aceita o contra-exemplo dele"
            nao_discrimina.append(nome)
        else:
            status = "ok"
        print(f"  {nome:<22} {t['esperado']}/{total_esp} bons | "
              f"rejeita {t['contra_rejeitado']}/{t['contra_total']} contra-exemplos | {status}")

    # Um grader que aprova tudo nao esta medindo nada (method/grader.md). Isso
    # e falha do harness, nao aviso: precisa derrubar o gate, senao o CI verde
    # significa apenas que ninguem olhou.
    for nome in nao_discrimina:
        t = totais[nome]
        detalhe = ("o contra-exemplo deste grader foi aceito" if t["contra_total"]
                   else "nao ha contra-exemplo deste grader no dataset")
        print(f"NAO DISCRIMINA {nome}: {detalhe}")

    if problemas or nao_discrimina:
        print()
        print(f"FALHA: {len(problemas)} regressao(oes), {len(nao_discrimina)} grader(s) sem prova de discriminacao")
        return 1

    print()
    print("OK: todo caso bom passa em todos os graders, e cada grader rejeita seu contra-exemplo")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
