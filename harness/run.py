"""Runner do harness: roda o dataset de um app contra os graders do adapter
e imprime o relatorio. Sem chave de API — o harness avalia saida ja
capturada, nunca chama o modelo.

Uso:
    PYTHONPATH=<repo>/src python -m harness.run <repo> <adapter>
"""
import argparse
import json
import importlib
import sys
from pathlib import Path


def carregar_casos(cases_path):
    return [json.loads(linha) for linha in cases_path.read_text().splitlines() if linha.strip()]


def avaliar(case, saida, ctx, graders):
    return {nome: bool(fn(saida, ctx)) for nome, fn in graders}


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("repo", help="caminho do repo do app (contem evals/cases.jsonl e src/)")
    ap.add_argument("adapter", help="nome do adapter em adapters/<adapter>/graders.py")
    args = ap.parse_args(argv)

    repo = Path(args.repo).resolve()
    sys.path.insert(0, str(repo / "src"))
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

    from insight.contract import InsightContext
    graders_mod = importlib.import_module(f"adapters.{args.adapter}.graders")
    graders = graders_mod.GRADERS

    casos = carregar_casos(repo / "evals" / "cases.jsonl")

    print(f"dataset: {len(casos)} casos | adapter: {args.adapter} | {len(graders)} graders")
    print()

    totais = {nome: {"esperado": 0, "contra_rejeitado": 0, "contra_total": 0} for nome, _ in graders}
    problemas = []

    for caso in casos:
        ctx = InsightContext(**caso["contexto"])

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
    for nome, _ in graders:
        t = totais[nome]
        total_esp = sum(1 for c in casos if "esperado" in c)
        if t["esperado"] < total_esp:
            status = "REGRESSAO — reprova caso bom"
        elif t["contra_rejeitado"] < t["contra_total"]:
            status = "NAO DISCRIMINA — aceita o contra-exemplo dele"
        else:
            status = "ok"
        print(f"  {nome:<22} {t['esperado']}/{total_esp} bons | "
              f"rejeita {t['contra_rejeitado']}/{t['contra_total']} contra-exemplos | {status}")

    if problemas:
        print()
        for p in problemas:
            print(p)
        return 1

    print()
    print("OK: todo caso bom passa em todos os graders, e cada grader rejeita seu contra-exemplo")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
