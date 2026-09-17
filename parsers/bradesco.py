"""Parser dedicado para extratos Bradesco (app "Bradesco Celular").

O extrato não é uma tabela real (pdfplumber não detecta bordas) — é texto
alinhado por espaços. Cada lançamento aparece em 3 linhas:

    TÍTULO (histórico resumido)
    [DATA ]DOCTO VALOR SALDO
    DETALHE (complemento do histórico)

A coluna Data só aparece no primeiro lançamento de cada dia. O texto não
diferencia crédito de débito diretamente (a coluna vem em branco quando
não se aplica) — o sinal é inferido pela variação do saldo em relação ao
lançamento anterior (saldo sobe = crédito, desce = débito).
"""

from __future__ import annotations

import re
from datetime import date

from .common import (
    PALAVRAS_ENTRADA,
    PALAVRAS_SAIDA,
    TransacaoExtraida,
    extrair_texto,
    normalizar_data,
    parse_generico,
    parse_valor_sinal,
    resolver_ano_referencia,
)

LINHA_ANCORA_RE = re.compile(
    r"^(?:(\d{2}/\d{2}/\d{4})\s+)?(.*?)\s*(\d{4,10})\s+(\d{1,3}(?:\.\d{3})*,\d{2})\s+"
    r"(\d{1,3}(?:\.\d{3})*,\d{2})\s*$"
)


def _linha_valida(linha: str | None) -> bool:
    if not linha:
        return False
    if LINHA_ANCORA_RE.match(linha):
        return False
    linha_lower = linha.lower()
    return not linha_lower.startswith(("data", "total", "folha", "extrato"))


def _processar_linhas(linhas: list[str], ano: int) -> list[TransacaoExtraida]:
    transacoes: list[TransacaoExtraida] = []
    ultima_data: str | None = None
    saldo_anterior: float | None = None

    for i, linha in enumerate(linhas):
        match = LINHA_ANCORA_RE.match(linha)
        if not match:
            continue

        data_linha, meio, _docto, valor_str, saldo_str = match.groups()
        if data_linha:
            ultima_data = data_linha
        if not ultima_data:
            continue

        valor_absoluto = parse_valor_sinal(valor_str)
        saldo_atual = parse_valor_sinal(saldo_str)

        antes = linhas[i - 1] if i > 0 else None
        depois = linhas[i + 1] if i + 1 < len(linhas) else None
        titulo = antes if _linha_valida(antes) else ""
        detalhe = depois if _linha_valida(depois) else ""
        descricao = (
            " ".join(p for p in (titulo, meio, detalhe) if p).strip()
            or "(sem descrição)"
        )

        if saldo_anterior is None:
            # Sem saldo anterior conhecido: tenta inferir pelo texto do título.
            descricao_lower = descricao.lower()
            if any(p in descricao_lower for p in PALAVRAS_SAIDA):
                valor = -valor_absoluto
            elif any(p in descricao_lower for p in PALAVRAS_ENTRADA):
                valor = valor_absoluto
            else:
                valor = valor_absoluto
        else:
            valor = valor_absoluto if saldo_atual >= saldo_anterior else -valor_absoluto

        saldo_anterior = saldo_atual

        if valor == 0.0:
            continue

        transacoes.append(
            TransacaoExtraida(
                data=normalizar_data(ultima_data, ano),
                descricao=descricao,
                valor=valor,
            )
        )

    return transacoes


def parse(arquivo, ano_referencia: int | None = None) -> list[TransacaoExtraida]:
    ano = resolver_ano_referencia(arquivo, ano_referencia or date.today().year)
    arquivo.seek(0)
    texto = extrair_texto(arquivo)
    linhas = [l.strip() for l in texto.splitlines() if l.strip()]

    transacoes = _processar_linhas(linhas, ano)

    if not transacoes:
        transacoes = parse_generico(texto, ano)

    return transacoes
