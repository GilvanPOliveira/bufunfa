"""Parser dedicado para extratos do Banco do Brasil.

Cobre dois formatos vistos no app do BB:

1) "Extrato de Conta Corrente": cada lançamento tem uma linha-âncora com
   data + valor + sinal entre parênteses ("3,00 (-)"), seguida de 1+
   linhas de descrição, até a próxima âncora ou um rótulo de saldo.

2) "Extrato de Poupança": cada lançamento tem data e valor na mesma linha
   ("14/07/2026 R$ 400,73" ou "15/07/2026 -R$ 3,00"), seguida de uma linha
   de descrição ("Aplicacao Automatica Poupanca" / "Resgate Automático").
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

LINHA_CABECALHO_RE = re.compile(
    r"^(\d{2}/\d{2}/\d{4})\s+(.*?)(\d{1,3}(?:\.\d{3})*,\d{2})\s*\(([+-])\)\s*(.*)$"
)
LINHA_POUPANCA_RE = re.compile(r"^(\d{2}/\d{2}/\d{4})\s+(-?R\$\s?[\d.,]+)\s*$")

TRECHOS_IGNORAR = (
    "saldo anterior",
    "saldo do dia",
    "s a l d o",
    "total aplica",
    "saldos por dia",
    "sujeitos a confirma",
    "saldos por período",
    "saldos por database",
)


def _eh_linha_ignoravel(linha_lower: str) -> bool:
    return any(trecho in linha_lower for trecho in TRECHOS_IGNORAR)


def _parse_poupanca(texto: str, ano: int) -> list[TransacaoExtraida]:
    linhas = [l.strip() for l in texto.splitlines() if l.strip()]
    transacoes: list[TransacaoExtraida] = []

    for i, linha in enumerate(linhas):
        match = LINHA_POUPANCA_RE.match(linha)
        if not match:
            continue

        data_str, valor_str = match.groups()
        valor = parse_valor_sinal(valor_str)
        if valor == 0.0:
            continue

        proxima = linhas[i + 1] if i + 1 < len(linhas) else None
        if (
            proxima
            and not LINHA_POUPANCA_RE.match(proxima)
            and not _eh_linha_ignoravel(proxima.lower())
        ):
            descricao = proxima
        else:
            descricao = "(sem descrição)"

        transacoes.append(
            TransacaoExtraida(
                data=normalizar_data(data_str, ano),
                descricao=descricao,
                valor=valor,
            )
        )

    return transacoes


def _limpar_meio(meio: str) -> str:
    """Remove tokens puramente numéricos (números de lote/documento) do
    trecho entre a data e o valor, mantendo qualquer texto descritivo
    embutido na mesma linha (ex.: horário + nome do favorecido)."""
    tokens = [tok for tok in meio.split() if not tok.isdigit()]
    return " ".join(tokens)


def _linha_valida(linha: str | None) -> bool:
    if not linha:
        return False
    if LINHA_CABECALHO_RE.match(linha):
        return False
    return not _eh_linha_ignoravel(linha.lower())


def _parse_conta_corrente(texto: str, ano: int) -> list[TransacaoExtraida]:
    linhas = [l.strip() for l in texto.splitlines() if l.strip()]
    transacoes: list[TransacaoExtraida] = []
    ocorrencias: dict[tuple[str, str, float], int] = {}

    for i, linha in enumerate(linhas):
        match = LINHA_CABECALHO_RE.match(linha)
        if not match:
            continue
        if _eh_linha_ignoravel(linha.lower()):
            continue

        data_str, meio, valor_str, sinal, resto = match.groups()
        valor = parse_valor_sinal(valor_str, sinal)
        if valor == 0.0:
            continue

        antes = linhas[i - 1] if i > 0 else None
        depois = linhas[i + 1] if i + 1 < len(linhas) else None

        partes = []
        if _linha_valida(antes):
            partes.append(antes)
        meio_limpo = _limpar_meio(meio)
        if meio_limpo:
            partes.append(meio_limpo)
        if resto:
            partes.append(resto)
        if _linha_valida(depois):
            partes.append(depois)

        descricao = " ".join(p.strip() for p in partes if p.strip()).strip()
        if not descricao:
            descricao = "(sem descrição)"

        data_normalizada = normalizar_data(data_str, ano)
        chave = (data_normalizada, descricao, valor)
        ocorrencias[chave] = ocorrencias.get(chave, 0) + 1
        if ocorrencias[chave] > 1:
            descricao = f"{descricao} (lançamento {ocorrencias[chave]})"

        transacoes.append(
            TransacaoExtraida(
                data=data_normalizada,
                descricao=descricao,
                valor=valor,
            )
        )

    return transacoes


def parse(arquivo, ano_referencia: int | None = None) -> list[TransacaoExtraida]:
    ano = resolver_ano_referencia(arquivo, ano_referencia or date.today().year)
    arquivo.seek(0)
    texto = extrair_texto(arquivo)

    if "extrato de poupança" in texto.lower():
        transacoes = _parse_poupanca(texto, ano)
        if transacoes:
            return transacoes

    transacoes = _parse_conta_corrente(texto, ano)
    if transacoes:
        return transacoes

    transacoes = _parse_poupanca(texto, ano)
    if transacoes:
        return transacoes

    return parse_generico(texto, ano)
