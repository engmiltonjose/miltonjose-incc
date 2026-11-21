"""
Robô do INCC (FGV) — baixa as séries do INCC republicadas pelo Ipeadata (API pública) e grava em dados/.

Séries (fonte original: FGV IBRE, via Ipeadata):
  INCC-M   variação % mensal                 IGP12_INCCMG12
  INCC-DI  variação % mensal                 IGP12_INCCG12
  INCC-DI  número-índice (ago/1994 = 100)    IGP12_INCC12
  INCC-10  número-índice (ago/1994 = 100)    IGP12_INCC1012

Saídas:
  dados/incc.json       todas as séries + resumo (último mês, acumulado no ano e em 12 meses)
  dados/{serie}.csv     uma planilha simples por série (mes;valor)
  saida/novidades.md    só quando entrou mês novo ou um valor foi revisado (vira aviso por e-mail)
"""

import csv
import json
import sys
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
RAIZ = Path(__file__).resolve().parent.parent
DADOS, SAIDA = RAIZ / "dados", RAIZ / "saida"
DADOS.mkdir(exist_ok=True)
SAIDA.mkdir(exist_ok=True)

SERIES = {
    "incc-m": {"codigo": "IGP12_INCCMG12", "nome": "INCC-M", "unidade": "% ao mês", "tipo": "variacao"},
    "incc-di": {"codigo": "IGP12_INCCG12", "nome": "INCC-DI", "unidade": "% ao mês", "tipo": "variacao"},
    "incc-di-indice": {"codigo": "IGP12_INCC12", "nome": "INCC-DI — número-índice", "unidade": "ago/1994 = 100", "tipo": "indice"},
    "incc-10-indice": {"codigo": "IGP12_INCC1012", "nome": "INCC-10 — número-índice", "unidade": "ago/1994 = 100", "tipo": "indice"},
}
URL = "http://www.ipeadata.gov.br/api/odata4/ValoresSerie(SERCODIGO='{}')"


def baixar(codigo):
    req = urllib.request.Request(URL.format(codigo), headers={"User-Agent": "robo-incc-miltonjose"})
    with urllib.request.urlopen(req, timeout=120) as r:
        vals = json.loads(r.read().decode("utf-8"))["value"]
    out = {}
    for v in vals:
        if v.get("VALVALOR") is None:
            continue
        out[v["VALDATA"][:7]] = round(float(v["VALVALOR"]), 4)   # "2026-10-01T00:00:00-03:00" → "2026-10"
    return dict(sorted(out.items()))


def acumulado(valores, meses):
    """Acumula variações % mensais (composição)."""
    fator = 1.0
    for m in meses:
        fator *= 1 + valores[m] / 100
    return round((fator - 1) * 100, 2)


def resumo(serie, valores):
    meses = list(valores)
    ult = meses[-1]
    r = {"ultimo_mes": ult, "ultimo_valor": valores[ult]}
    if serie["tipo"] == "variacao":
        ano = [m for m in meses if m[:4] == ult[:4]]
        r["acumulado_ano_pct"] = acumulado(valores, ano)
        if len(meses) >= 12:
            r["acumulado_12_meses_pct"] = acumulado(valores, meses[-12:])
    else:
        if len(meses) >= 13:
            r["variacao_12_meses_pct"] = round((valores[ult] / valores[meses[-13]] - 1) * 100, 2)
        if len(meses) >= 2:
            r["variacao_mes_pct"] = round((valores[ult] / valores[meses[-2]] - 1) * 100, 2)
    return r


def main():
    arq = DADOS / "incc.json"
    anterior = json.loads(arq.read_text(encoding="utf-8")) if arq.exists() else {"series": {}}
    novo = {"fonte": "FGV IBRE (Índice Nacional de Custo da Construção), via Ipeadata — www.ipeadata.gov.br",
            "atualizado_em": anterior.get("atualizado_em"), "series": {}}
    novidades, erros = [], []
    for chave, s in SERIES.items():
        try:
            valores = baixar(s["codigo"])
        except Exception as e:
            erros.append(f"{s['nome']} ({s['codigo']}): {e}")
            if chave in anterior.get("series", {}):
                novo["series"][chave] = anterior["series"][chave]    # mantém o que já havia
            continue
        if not valores:
            erros.append(f"{s['nome']}: série veio vazia")
            continue
        velhos = anterior.get("series", {}).get(chave, {}).get("valores", {})
        meses_novos = [m for m in valores if m not in velhos]
        revisados = [m for m in valores if m in velhos and velhos[m] != valores[m]]
        if velhos and meses_novos:
            novidades.append((s, "novo", meses_novos, valores))
        if revisados:
            novidades.append((s, "revisado", revisados, valores))
        novo["series"][chave] = {**{k: s[k] for k in ("codigo", "nome", "unidade", "tipo")},
                                 "resumo": resumo(s, valores), "valores": valores}
        with open(DADOS / f"{chave}.csv", "w", newline="", encoding="utf-8") as f:
            w = csv.writer(f, delimiter=";")
            w.writerow(["mes", "valor"])
            for m, v in valores.items():
                w.writerow([m, str(v).replace(".", ",")])
        print(f"{s['nome']}: {len(valores)} meses, último {list(valores)[-1]} = {valores[list(valores)[-1]]}")

    mudou = json.dumps(novo["series"], sort_keys=True) != json.dumps(anterior.get("series", {}), sort_keys=True)
    if mudou:
        novo["atualizado_em"] = datetime.now(timezone.utc).isoformat(timespec="seconds")
        arq.write_text(json.dumps(novo, ensure_ascii=False, indent=1), encoding="utf-8")

    if novidades or erros:
        L = []
        if novidades:
            L += ["## ✅ INCC atualizado", "", "| Série | O que mudou | Mês | Valor | Resumo |", "|---|---|---|---|---|"]
            for s, tipo, meses, valores in novidades:
                r = resumo(s, valores)
                extra = (f"ano {r.get('acumulado_ano_pct')}% · 12 meses {r.get('acumulado_12_meses_pct')}%"
                         if s["tipo"] == "variacao" else f"12 meses {r.get('variacao_12_meses_pct')}%")
                for m in meses[-6:]:
                    L.append(f"| {s['nome']} | {'mês novo' if tipo == 'novo' else 'valor revisado pela FGV'} | {m} | "
                             f"{valores[m]} {s['unidade']} | {extra} |")
            L += ["", "Dados em `dados/incc.json` e nos CSVs de `dados/`. "
                  "Endereço para as ferramentas: https://raw.githubusercontent.com/engmiltonjose/miltonjose-incc/main/dados/incc.json"]
        if erros:
            L += ["", "## ❌ O que não deu certo", ""] + [f"- {e}" for e in erros] + [
                "", "**Causa provável:** o Ipeadata estava fora do ar ou mudou a API. **O que fazer:** nada — o robô "
                "tenta de novo amanhã e mantém os dados anteriores. Se repetir por 3 dias, peça ao Claude para olhar."]
        (SAIDA / "novidades.md").write_text("\n".join(L), encoding="utf-8")
        t = "❌ Robô do INCC com falha" if erros and not novidades else "✅ INCC atualizado — " + ", ".join(
            sorted({f"{s['nome']} {m[-1]}" for s, _, m, _ in novidades}))
        (SAIDA / "titulo.txt").write_text(t, encoding="utf-8")
    if erros and not novo["series"]:
        sys.exit(1)


if __name__ == "__main__":
    main()
