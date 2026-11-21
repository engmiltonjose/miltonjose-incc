# miltonjose-incc

Robô que mantém atualizado o **INCC** (Índice Nacional de Custo da Construção, FGV IBRE), para uso nas ferramentas do miltonjose.com (Quantify, skills Pilar, biblioteca, paramétrico).

## Fonte

FGV IBRE, republicado pelo **Ipeadata** (API pública do Ipea): `http://www.ipeadata.gov.br/api/odata4/`.

| Arquivo | Série | Unidade | Código Ipeadata |
|---|---|---|---|
| `dados/incc-m.csv` | INCC-M | % ao mês | IGP12_INCCMG12 |
| `dados/incc-di.csv` | INCC-DI | % ao mês | IGP12_INCCG12 |
| `dados/incc-di-indice.csv` | INCC-DI — número-índice | ago/1994 = 100 | IGP12_INCC12 |
| `dados/incc-10-indice.csv` | INCC-10 — número-índice | ago/1994 = 100 | IGP12_INCC1012 |

`dados/incc.json` reúne tudo, com um **resumo** por série (último mês, acumulado no ano e em 12 meses).

## Como usar nas ferramentas

```
https://raw.githubusercontent.com/engmiltonjose/miltonjose-incc/main/dados/incc.json
https://cdn.jsdelivr.net/gh/engmiltonjose/miltonjose-incc@main/dados/incc.json
```

## Funcionamento

- Roda **todo dia às 09:15** (Brasília) — a FGV divulga o INCC-DI por volta do dia 10, o INCC-10 por volta do dia 20 e o INCC-M no fim do mês.
- Só faz commit quando algo muda; abre uma *issue* (e-mail) quando entra mês novo, quando a FGV revisa um valor ou quando falha.
