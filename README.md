# ai-lab — harness compartilhado

Harness de prompt engineering (trilha `01-Projetos/engenharia-de-prompt/`). Um repo,
vários apps: o **mecanismo** e o **método** moram aqui; o **contrato**, o **dataset** e
as **invariantes** de cada app moram no diretório de trabalho do app.

Método aplicável a qualquer app com superfície de LLM — o app que traz o **grader** é
o que valida, não este repo.

## Estrutura

```
~/Work/lab/
├── ai-lab/                      # ESTE repo — mecanismo + método, nunca duplicado
│   ├── harness/run.py           #   runner: dataset x graders → relatório + exit code
│   ├── method/grader.md         #   como escrever e testar uma pergunta de conferência
│   └── adapters/               #   (vazio até o 2º app; cada app traz suas invariantes)
│
├── cycling-coach/               # git worktree do coach, branch lab/*
│   ├── src/insight/contract.py  #   schema + versão + hash do prompt (dados do app)
│   ├── src/insight/prompt.md    #   o prompt como arquivo versionado
│   └── evals/cases.jsonl        #   casos bons + contra-exemplo por grader
│
├── amazon-inventory/            # diretório de trabalho isolado (transferência)
└── yomi-hub/                    # projeto novo (transferência, Fase 1+)
```

## Por que um harness só

O POC achou um bug no método: o grader de contrato aceitou uma saída que trocava o
foco do motor, porque o valor trocado era válido no enum. O conserto é um
contra-exemplo direcionado por grader — conhecimento de **método**, não de app.

Três cadernos (fork por app) triplicariam esse conhecimento: o mesmo erro
reaparece três vezes, em dias diferentes, com formatos diferentes, e a correção
não chega nos outros dois. O teste de transferência (o mesmo método funcionando
fora do coach) deixa de existir — porque nunca se testa o mesmo método duas vezes,
sempre uma cópia.

O corte mínimo, então: **o que é do app, fica no app. O que é do método, fica aqui.**

## Divisão

| Camada | Onde | Pergunta que responde |
|---|---|---|
| Contrato | `src/<módulo>/contract.py` (app) | "isto está bem formado?" |
| Invariantes | `adapters/<app>/graders.py` (app) | "isto está **verdade**?" |
| Dataset | `evals/cases.jsonl` (app) | casos bons + contra-exemplo por grader |
| Método | `method/grader.md` (**aqui**) | "esta pergunta mede o que diz medir?" |
| Runner | `harness/run.py` (**aqui**) | "todos os graders concordam?" |

## Rodar

```bash
cd ~/Work/lab/ai-lab
PYTHONPATH=~/Work/lab/cycling-coach/src python3 -m harness.run ~/Work/lab/cycling-coach cycling-coach
```

Roda **offline, sem chave de API**: o harness avalia saída já capturada, nunca chama o
modelo. Para avaliar saída real, o app grava a resposta em `evals/captures/`.

## Relatório: as três saídas de um grader

- `ok` — aprova o caso bom e rejeita o contra-exemplo.
- `REGRESSÃO` — reprova um caso bom (prompt/regra mudou errado).
- `NÃO DISCRIMINA` — aceita o próprio contra-exemplo (não mede o que diz medir).

## Isolamento dos experimentos

O código do app nunca entra neste repo. Experimento descartável = worktree:

```bash
git -C ~/Work/cycling-coach worktree add ~/Work/lab/cycling-coach -b lab/<hipotese>
git -C ~/Work/cycling-coach worktree remove ~/Work/lab/cycling-coach   # descarta tudo
```

## Quando um app ganha repo próprio

Se um braço de LLM ganhar ciclo de release próprio (ex.: o `insight` virando serviço
consumido pelo portal), ele sai em repo próprio. Isso é **extração**, não fork — e o
`ai-lab` continua sendo importado, não copiado.
