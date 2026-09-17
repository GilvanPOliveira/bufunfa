"""Parser dedicado para extratos Santander "Extrato Consolidado Inteligente".

O extrato NÃO usa uma tabela real (pdfplumber não detecta bordas) — é texto
alinhado por espaços. Cada lançamento é uma linha no formato:

    [DD/MM ]DESCRIÇÃO [Nº_DOC|-] VALOR[-] [SALDO]

Nº_DOC é um número de documento, ou "-" quando não há. O sinal de débito
vem colado no fim do valor (ex.: "9,99-"), nunca no início. A data e o
saldo às vezes só aparecem no primeiro/último lançamento de um grupo de
transações do mesmo dia. Linhas sem nenhum valor são continuação da
descrição do lançamento anterior (ex.: a data da compra, diferente da
data de lançamento).
"""

from __future__ import annotations

import re
from datetime import date

from .common import (
    TransacaoExtraida,
    extrair_texto,
    normalizar_data,
    parse_generico,
    parse_valor_sinal,
    resolver_ano_referencia,
)

LINHA_LANCAMENTO_RE = re.compile(
    r"^(?:(\d{2}/\d{2})\s+)?(.*?)\s*(?:\d{4,10}|-)\s*(\d{1,3}(?:\.\d{3})*,\d{2}-?)"
    r"(?:\s+(\d{1,3}(?:\.\d{3})*,\d{2}))?\s*$"
)

INICIO_MOVIMENTACAO = "data descrição"
FINS_MOVIMENTACAO = (
    "se você não tem limite",
    "saldos por período",
    "sevocênãotemlimite",
    "conta corrente bloqueio",
    "investimentos",
    "comprovantes de pagamento",
    "movimentacoes de conta",
)
PREFIXOS_IGNORAR = ("saldo em",)


def _dentro_da_secao(texto: str) -> list[str]:
    """Recorta apenas as linhas da seção de Movimentação da Conta Corrente
    (pode se repetir por mês/página no mesmo PDF)."""
    linhas_utilizaveis: list[str] = []
    dentro = False
    for linha_bruta in texto.splitlines():
        linha = linha_bruta.strip()
        if not linha:
            continue
        linha_lower = linha.lower()
        if (
            not dentro
            and INICIO_MOVIMENTACAO in linha_lower
            and "movimento" in linha_lower
        ):
            dentro = True
            continue
        if dentro and any(
            fim in linha_lower.replace(" ", "") for fim in FINS_MOVIMENTACAO
        ):
            dentro = False
            continue
        if dentro:
            linhas_utilizaveis.append(linha)
    return linhas_utilizaveis


def _processar_linhas(linhas: list[str], ano: int) -> list[TransacaoExtraida]:
    transacoes: list[TransacaoExtraida] = []
    ultima_data: str | None = None
    ocorrencias: dict[tuple[str, str, float], int] = {}

    for linha in linhas:
        linha_lower = linha.lower()
        if linha_lower.startswith(PREFIXOS_IGNORAR):
            continue

        match = LINHA_LANCAMENTO_RE.match(linha)
        if not match:
            # Linha sem valor: continuação da descrição do lançamento anterior.
            if transacoes:
                transacoes[-1].descricao = f"{transacoes[-1].descricao} {linha}".strip()
            continue

        data_linha, descricao, valor_str, _saldo = match.groups()
        if data_linha:
            ultima_data = data_linha
        if not ultima_data:
            continue

        valor = parse_valor_sinal(valor_str)
        if valor == 0.0:
            continue

        chave = (normalizar_data(ultima_data, ano), descricao.strip(), valor)
        ocorrencias[chave] = ocorrencias.get(chave, 0) + 1
        if ocorrencias[chave] > 1:
            descricao = f"{descricao.strip()} (lançamento {ocorrencias[chave]})"

        transacoes.append(
            TransacaoExtraida(
                data=chave[0],
                descricao=descricao.strip() or "(sem descrição)",
                valor=valor,
            )
        )

    return transacoes


def parse(arquivo, ano_referencia: int | None = None) -> list[TransacaoExtraida]:
    ano = resolver_ano_referencia(arquivo, ano_referencia or date.today().year)
    arquivo.seek(0)
    texto = extrair_texto(arquivo)

    linhas = _dentro_da_secao(texto)
    transacoes = _processar_linhas(linhas, ano)

    if not transacoes:
        transacoes = parse_generico(texto, ano)

    return transacoes
