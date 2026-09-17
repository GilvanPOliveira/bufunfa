"""Utilitários compartilhados para extração de extratos bancários em PDF.

Contém: extração de texto/tabelas via pdfplumber, normalização de datas e
valores em formato brasileiro, e um parser genérico de última instância
(linha única "DATA DESCRIÇÃO VALOR") usado quando não há um parser
dedicado para o layout do banco.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import date

import pdfplumber

DATA_RE = re.compile(r"^(\d{2}/\d{2}/\d{4}|\d{2}/\d{2})\b")
VALOR_RE = re.compile(
    r"([+-]?\s?R?\$?\s?-?(?:\d{1,3}(?:\.\d{3})+|\d+),\d{2})\s*([CD])?\s*$"
)
ANO_RE = re.compile(r"\b(20\d{2})\b")

PALAVRAS_SAIDA = (
    "compra",
    "pagamento",
    "debito",
    "débito",
    "saque",
    "tarifa",
    "envio",
    "enviado",
    "boleto",
    "fatura",
    "encargo",
    "iof",
    "juros cobrados",
)
PALAVRAS_ENTRADA = (
    "recebido",
    "recebida",
    "credito",
    "crédito",
    "deposito",
    "depósito",
    "salario",
    "salário",
    "rendimento",
    "estorno",
)

LINHAS_IGNORAR = (
    "saldo anterior",
    "saldo do dia",
    "saldo disponivel",
    "saldo disponível",
    "extrato de",
    "lançamentos",
    "lancamentos",
    "data movimento historico",
    "página",
    "pagina",
    "agencia",
    "agência",
    "cnpj",
    "ouvidoria",
)


@dataclass
class TransacaoExtraida:
    data: str  # ISO yyyy-mm-dd
    descricao: str
    valor: float


def extrair_texto(arquivo) -> str:
    texto_paginas = []
    with pdfplumber.open(arquivo) as pdf:
        for pagina in pdf.pages:
            texto = pagina.extract_text() or ""
            texto_paginas.append(texto)
    # Alguns PDFs bancários têm fontes com mapeamento quebrado que geram bytes
    # nulos no meio de números (ex.: "2\x00566,57" em vez de "2566,57").
    return "\n".join(texto_paginas).replace("\x00", "")


def extrair_tabelas(arquivo) -> list[list[list[str]]]:
    """Retorna todas as tabelas (linhas x colunas) de todas as páginas do PDF."""
    tabelas: list[list[list[str]]] = []
    with pdfplumber.open(arquivo) as pdf:
        for pagina in pdf.pages:
            for tabela in pagina.extract_tables() or []:
                tabelas.append(tabela)
    return tabelas


def detectar_ano(texto: str) -> int | None:
    """Tenta descobrir o ano de referência do extrato a partir do cabeçalho."""
    match = ANO_RE.search(texto[:1500])
    return int(match.group(1)) if match else None


def extrair_saldo_anterior(texto: str) -> float | None:
    """Lê o saldo inicial impresso no cabeçalho de extratos BR suportados."""
    padroes = (
        r"saldo anterior\s+(-?R?\$?\s?[\d.]+,\d{2})\s*\(([+-])\)",
        r"saldo em \d{2}/\d{2}/\d{4}\s+R?\$?\s*(-?[\d.]+,\d{2})",
        r"saldo de conta corrente em \d{2}/\d{2}\s+(-?[\d.]+,\d{2})",
    )
    texto_cabecalho = texto[:5000].lower()
    for indice, padrao in enumerate(padroes):
        match = re.search(padrao, texto_cabecalho, re.IGNORECASE)
        if not match:
            continue
        valor_str = match.group(1)
        sinal = match.group(2) if indice == 0 and len(match.groups()) > 1 else None
        return parse_valor_sinal(valor_str, sinal)
    return None


def resolver_ano_referencia(arquivo, ano_padrao: int) -> int:
    """Detecta o ano no texto do PDF; se não achar, usa o ano informado pelo usuário."""
    try:
        arquivo.seek(0)
        ano = detectar_ano(extrair_texto(arquivo))
    finally:
        arquivo.seek(0)
    return ano or ano_padrao


def normalizar_data(data_str: str, ano_referencia: int | None = None) -> str:
    ano_referencia = ano_referencia or date.today().year
    partes = data_str.strip().split("/")
    if len(partes) == 2:
        dia, mes = partes
        ano = ano_referencia
    else:
        dia, mes, ano = partes
        ano = int(ano)
    try:
        return date(int(ano), int(mes), int(dia)).isoformat()
    except ValueError:
        return date.today().isoformat()


def parse_valor_sinal(numero_str: str, sinal: str | None = None) -> float:
    """Converte um número em formato BR ('1.234,56', '-1.234,56' ou '1.234,56-')
    para float, considerando também um indicador explícito de sinal
    ('+', '-', 'C' para crédito ou 'D' para débito), quando disponível.
    """
    limpo = numero_str.strip().replace("R$", "").replace(" ", "")
    negativo = False
    if limpo.startswith("-"):
        negativo = True
        limpo = limpo[1:]
    if limpo.endswith("-"):
        negativo = True
        limpo = limpo[:-1]
    limpo = limpo.replace(".", "").replace(",", ".")
    try:
        valor = float(limpo)
    except ValueError:
        return 0.0

    if sinal in ("D", "-"):
        negativo = True
    elif sinal in ("C", "+"):
        negativo = False

    return -valor if negativo else valor


def _parse_valor_generico(
    valor_str: str, indicador: str | None, descricao: str
) -> float:
    """Usada apenas pelo parser genérico: quando não há indicador C/D explícito,
    tenta inferir o sinal por palavras-chave na descrição."""
    limpo = valor_str.replace("R$", "").replace(" ", "")
    negativo = limpo.startswith("-")
    limpo = limpo.lstrip("+-")
    limpo = limpo.replace(".", "").replace(",", ".")
    try:
        valor = float(limpo)
    except ValueError:
        return 0.0

    if indicador == "D":
        negativo = True
    elif indicador == "C":
        negativo = False
    elif not negativo:
        descricao_lower = descricao.lower()
        if any(p in descricao_lower for p in PALAVRAS_SAIDA):
            negativo = True
        elif any(p in descricao_lower for p in PALAVRAS_ENTRADA):
            negativo = False

    return -valor if negativo else valor


def parse_generico(
    texto: str, ano_referencia: int | None = None
) -> list[TransacaoExtraida]:
    """Último recurso: procura linhas soltas no padrão 'DATA DESCRIÇÃO VALOR [C/D]'."""
    ano_referencia = ano_referencia or date.today().year
    transacoes: list[TransacaoExtraida] = []

    for linha_bruta in texto.splitlines():
        linha = linha_bruta.strip()
        if not linha:
            continue
        linha_lower = linha.lower()
        if any(ignorar in linha_lower for ignorar in LINHAS_IGNORAR):
            continue

        match_data = DATA_RE.match(linha)
        if not match_data:
            continue
        match_valor = VALOR_RE.search(linha)
        if not match_valor:
            continue

        data_str = match_data.group(1)
        valor_str, indicador = match_valor.groups()
        descricao = linha[match_data.end() : match_valor.start()].strip(" -\t")
        if not descricao:
            continue

        valor = _parse_valor_generico(valor_str, indicador, descricao)
        if valor == 0.0:
            continue

        transacoes.append(
            TransacaoExtraida(
                data=normalizar_data(data_str, ano_referencia),
                descricao=descricao,
                valor=valor,
            )
        )

    return transacoes
