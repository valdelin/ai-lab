# Método — como escrever e testar uma pergunta de conferência (grader)

Este arquivo é o motivo de o harness ser único. É o conhecimento que o POC já
pagou para achar; triplicá-lo num fork por app significa pagar de novo.

## A regra

> Uma pergunta de conferência só funciona se for testada com **o erro que ela existe
> para pegar**. Testada com "uma resposta ruim" qualquer, ela aprova o erro errado.

## Como isso aconteceu (não é teórico)

Primeiro draft do `contract` (grader 1 do coach). Ele respondia "válido" para uma
saída que trocava o foco do motor: o robô dizia `vo2` quando o motor tinha dito
`z2`. O `vo2` é um valor **válido** do enum. Resposta bem formada, veredito errado.

Se o único contra-exemplo do dataset é "resposta ruim genérica", o dataset está
testando a pergunta errada. Foi o que aconteceu: o dataset tinha um caso `ruim` com
várias violações, e cada grader passava porque a violação era de outro.

## O procedimento

1. **Nomeie a falha que o grader existe para pegar.** Uma frase. "Inverte o foco do
   motor", "inventa número", "alerta sem gatilho". Se a frase não cabe em uma linha,
   são dois graders.
2. **Escreva o contra-exemplo para essa frase** — a saída que viola *aquela* regra e
   só ela. Mutação mínima: mude um campo, deixe o resto igual ao caso bom.
3. **Coloque no dataset** como `contra[<nome-do-grader>]`, pareado com o caso bom.
4. **Rode o harness e leia o relatório.** Três saídas possíveis:
   - `ok` — aprova o caso bom e rejeita o contra-exemplo.
   - `REGRESSÃO` — reprova um caso bom. Prompt ou regra mudou errado.
   - `NÃO DISCRIMINA` — aceita o próprio contra-exemplo. O grader não está medindo
     o que diz medir; ou está medindo outra coisa, ou não mede nada.

## O que o `contrato` é, e o que ele não é

O `contrato` (schema) pega **forma**: campo faltando, valor fora do enum, tipo
errado, texto grande demais. Ele é o portão de entrada e roda em toda saída.

Ele **não** pega verdade. Um `foco: "vo2"` bem formado continua errado. Isso não é
bug do `contrato` — é o escopo dele. Cada app declara essa separação no adapter: o
schema fica em `src/<módulo>/contract.py`, as invariantes ficam em
`adapters/<app>/graders.py`.

## Duas camadas, sempre

| Camada | Pergunta que responde | Onde | Chama LLM |
|---|---|---|---|
| Contrato | "isto está bem formado?" | `src/<módulo>/contract.py` | não |
| Invariante | "isto está **verdade**?" | `adapters/<app>/graders.py` | não |

Regra de ouro: **o prompt nunca é um grader.** Se dá para verificar sem chamar o
modelo, é invariant do harness. Grader que precisa de LLM vira `llm_judge` — e aí
passa a custar tokens e latência, o que é comentário de M4, não de M1.

## Ao adicionar um app

Copie o **formato**, não o harness. O app novo precisa de:

- `contract.py` (ou equivalente) com o schema da saída e a versão do prompt
- `cases.jsonl` com ≥ 1 caso bom por padrão de contexto e um `contra` por grader
- `adapters/<app>/graders.py` com as invariantes, cada uma com sua frase de falha

O runner é o mesmo. Se o app novo exigir mudança no runner, provavelmente é sinal
de que o caso é específico demais para o método — anote como exceção em vez de
bifurcar o harness.
