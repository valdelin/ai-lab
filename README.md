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
│   └── method/grader.md         #   como escrever e testar uma pergunta de conferência
│
├── cycling-coach/               # git worktree do coach, branch lab/*
│   ├── src/insight/contract.py  #   schema + versão + hash do prompt (dados do app)
│   ├── src/insight/prompt.md    #   o prompt como arquivo versionado
│   ├── evals/graders.py         #   invariantes do domínio (TSB ≤ −20, foco do motor)
│   └── evals/cases.jsonl        #   casos bons + contra-exemplo por grader
│
├── amazon-inventory/            # diretório de trabalho isolado (transferência)
└── yomi-hub/                    # projeto novo (transferência, Fase 1+)
```

Nenhum `adapters/` aqui. O adapter **é** o `evals/graders.py` do app: o runner
carrega esse arquivo por caminho e não importa nada do domínio dele. Um `adapters/`
central seria a fronteira furada — o CI passaria a testar as invariantes de um app
que ele não acompanha, e trocar `TSB <= -20` no coach não mudaria nada no gate.

## Contrato do adapter

O app expõe duas coisas em `evals/graders.py`, e o runner só precisa delas:

| Símbolo | Tipo | O que é |
|---|---|---|
| `CONTEXTO` | classe ou callable | transforma o dicionário `contexto` do caso num objeto |
| `GRADERS` | lista de `(nome, fn)` | `fn(saida, ctx) -> bool` |

Nada mais. Se o runner precisar conhecer o domínio de um app para funcionar, o
método voltou a ser cópia — que é o que o ADR-004 diz para não acontecer.

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
| Invariantes | `evals/graders.py` (app) | "isto está **verdade**?" |
| Dataset | `evals/cases.jsonl` (app) | casos bons + contra-exemplo por grader |
| Método | `method/grader.md` (**aqui**) | "esta pergunta mede o que diz medir?" |
| Runner | `harness/run.py` (**aqui**) | "todos os graders concordam?" |

## Rodar

```bash
cd ~/Work/lab/ai-lab
./check.sh ~/Work/lab/cycling-coach      # 2º argumento saiu: o adapter é o arquivo do app
```

Roda **offline, sem chave de API**: o harness avalia saída já capturada, nunca chama o
modelo. Para avaliar saída real, o app grava a resposta em `evals/captures/`.

## Relatório: as três saídas de um grader

- `ok` — aprova o caso bom e rejeita o contra-exemplo.
- `REGRESSÃO` — reprova um caso bom (prompt/regra mudou errado).
- `NÃO DISCRIMINA` — aceita o próprio contra-exemplo (não mede o que diz medir).
- `SEM CONTRA-EXEMPLO` — não há contra-exemplo desse grader no dataset: não foi
  testado, e não testado não é `ok`.

Todas as três últimas derrubam o gate (`exit 1`). Um relatório que mostra um grader
sem prova e ainda imprime `OK` no fim é o pior resultado possível: verde sem
verificação.

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
