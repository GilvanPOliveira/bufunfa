"""Registro de parsers por banco.

Bradesco, Santander e Banco do Brasil têm parsers dedicados (parsers/bradesco.py,
parsers/santander.py, parsers/banco_brasil.py) baseados em layouts reais de
extrato. Itaú e "Genérico" usam o motor de texto genérico (parsers/common.py),
que pode ser menos preciso — sempre revise antes de confirmar a importação.

Há também a opção "Detectar automaticamente", que testa todos os parsers
dedicados e usa o texto do PDF para identificar o banco, escolhendo o
resultado com mais transações reconhecidas.
"""

from __future__ import annotations

from datetime import date

from . import banco_brasil, bradesco, santander
from .common import TransacaoExtraida, extrair_texto, parse_generico

DETECTAR_AUTOMATICAMENTE = "Detectar automaticamente"

BANCOS_SUPORTADOS = [
    DETECTAR_AUTOMATICAMENTE,
    "Bradesco",
    "Itaú",
    "Santander",
    "Banco do Brasil",
    "Genérico (outro banco)",
]

MARCADORES_BANCO = {
    "Bradesco": ("bradesco celular", "bradesco"),
    "Santander": ("extrato consolidado inteligente", "santander"),
    "Itaú": ("itau", "itaú", "itaú unibanco"),
    "Banco do Brasil": (
        "banco do brasil",
        "extrato de conta corrente",
        "extrato de poupança",
    ),
}


def _parse_por_nome(
    arquivo, banco: str, ano_referencia: int
) -> list[TransacaoExtraida]:
    if banco == "Bradesco":
        return bradesco.parse(arquivo, ano_referencia)
    if banco == "Santander":
        return santander.parse(arquivo, ano_referencia)
    if banco == "Banco do Brasil":
        return banco_brasil.parse(arquivo, ano_referencia)
    # Itaú e Genérico usam o parser de texto genérico.
    arquivo.seek(0)
    return parse_generico(extrair_texto(arquivo), ano_referencia)


def detectar_banco(arquivo) -> str | None:
    """Tenta identificar o banco pelo texto do PDF (usado como dica inicial)."""
    arquivo.seek(0)
    texto_lower = extrair_texto(arquivo).lower()
    arquivo.seek(0)
    for banco, marcadores in MARCADORES_BANCO.items():
        if any(marcador in texto_lower for marcador in marcadores):
            return banco
    return None


def detectar_tipo_conta(arquivo) -> str:
    """Detecta o tipo usando marcadores de cabeçalho, não palavras no rodapé."""
    arquivo.seek(0)
    texto_lower = extrair_texto(arquivo).lower()[:2500]
    arquivo.seek(0)

    if "extrato de poupança" in texto_lower or "extrato de poupanca" in texto_lower:
        return "Poupança"
    if "extrato de conta corrente" in texto_lower:
        return "Corrente"
    if (
        "agência conta corrente" in texto_lower
        or "agencia conta corrente" in texto_lower
    ):
        return "Corrente"
    if (
        "tipo de conta: poupança" in texto_lower
        or "tipo de conta: poupanca" in texto_lower
    ):
        return "Poupança"
    return "Corrente"


def parse_arquivo(
    arquivo, banco: str, ano_referencia: int | None = None
) -> list[TransacaoExtraida]:
    ano_referencia = ano_referencia or date.today().year

    if banco != DETECTAR_AUTOMATICAMENTE:
        return _parse_por_nome(arquivo, banco, ano_referencia)

    # Detecção automática: tenta o banco sugerido pelo texto primeiro e,
    # se render poucas transações, testa os demais parsers dedicados e
    # fica com o resultado que reconheceu mais lançamentos.
    candidatos = ["Bradesco", "Santander", "Banco do Brasil", "Itaú"]
    sugerido = detectar_banco(arquivo)
    if sugerido:
        candidatos.remove(sugerido)
        candidatos.insert(0, sugerido)

    melhor_resultado: list[TransacaoExtraida] = []
    for candidato in candidatos:
        arquivo.seek(0)
        try:
            resultado = _parse_por_nome(arquivo, candidato, ano_referencia)
        except Exception:
            resultado = []
        if len(resultado) > len(melhor_resultado):
            melhor_resultado = resultado

    if melhor_resultado:
        return melhor_resultado

    arquivo.seek(0)
    return parse_generico(extrair_texto(arquivo), ano_referencia)
