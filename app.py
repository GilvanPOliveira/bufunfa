"""Home compacta do Bufunfa, desenhada para leitura sem rolagem."""

from __future__ import annotations

from datetime import date

import pandas as pd
import streamlit as st

import db
import ui

st.set_page_config(
    page_title="Bufunfa — Home", page_icon=":material/home:", layout="wide"
)
db.init_db()
ui.aplicar_estilo()

contas = db.listar_contas()
if not contas:
    ui.cabecalho("Home", "Seu painel financeiro pessoal.", ":material/home:")
    st.info(
        "Você ainda não cadastrou nenhum banco ou conta. Comece em **Bancos e Contas**."
    )
    st.stop()

contas_df = pd.DataFrame([dict(conta) for conta in contas])
contas_df["saldo_atual"] = contas_df["id"].apply(db.saldo_atual_conta)
transacoes = db.listar_transacoes()
trans_df = pd.DataFrame([dict(transacao) for transacao in transacoes])

ui.cabecalho("Home", "Seu dinheiro, em uma leitura rápida.", ":material/home:")
with st.container(horizontal=True):
    st.page_link("pages/2_Transacoes.py", label="Nova transação", icon=":material/add:")
    st.page_link(
        "pages/3_Importar_PDF.py", label="Importar PDF", icon=":material/upload_file:"
    )

hoje = date.today()
primeiro_dia = hoje.replace(day=1)
periodo = st.date_input("Período", value=(primeiro_dia, hoje))
if isinstance(periodo, tuple) and len(periodo) == 2:
    data_inicio, data_fim = periodo
else:
    data_inicio, data_fim = primeiro_dia, hoje

if not trans_df.empty:
    trans_df["data_dt"] = pd.to_datetime(trans_df["data"])
    periodo_df = trans_df[
        (trans_df["data_dt"].dt.date >= data_inicio)
        & (trans_df["data_dt"].dt.date <= data_fim)
    ].copy()
else:
    periodo_df = pd.DataFrame()

operacionais = (
    periodo_df[periodo_df["natureza"] == "operacional"]
    if not periodo_df.empty
    else pd.DataFrame()
)
entradas = (
    operacionais.loc[operacionais["valor"] > 0, "valor"].sum()
    if not operacionais.empty
    else 0
)
saidas = (
    operacionais.loc[operacionais["valor"] < 0, "valor"].abs().sum()
    if not operacionais.empty
    else 0
)
resultado = entradas - saidas
por_tipo = contas_df.groupby("tipo")["saldo_atual"].sum().to_dict()
investido_total = (
    trans_df.loc[trans_df["natureza"] == "investimento", "valor"].abs().sum()
    if not trans_df.empty
    else 0
)
patrimonio_total = contas_df["saldo_atual"].sum() + investido_total
saldo_disponivel = contas_df["saldo_atual"].sum()

# Quatro números que respondem o essencial sem ocupar a tela inteira.
ui.metric_grid(
    [
        ("Patrimônio total", db.formatar_moeda(patrimonio_total)),
        ("Disponível", db.formatar_moeda(saldo_disponivel)),
        ("Investido", db.formatar_moeda(investido_total)),
        ("Resultado do período", db.formatar_moeda(resultado)),
    ]
)

main_left, main_right = st.columns([1.1, 1.4])
with main_left:
    st.markdown(
        "<div class='bufunfa-section-title'><b>01</b> Contas</div>",
        unsafe_allow_html=True,
    )
    contas_resumo = contas_df[["banco_nome", "nome", "tipo", "saldo_atual"]].copy()
    contas_resumo["Conta"] = contas_resumo["banco_nome"] + " · " + contas_resumo["nome"]
    contas_resumo = contas_resumo.sort_values(
        ["saldo_atual", "banco_nome", "nome"], ascending=[False, True, True]
    )
    for _, conta in contas_resumo.iterrows():
        classe = "bufunfa-row--in" if conta["saldo_atual"] >= 0 else "bufunfa-row--out"
        st.markdown(
            f"<div class='bufunfa-row {classe}'><div class='bufunfa-main'>"
            f"<span class='bufunfa-label'>{conta['Conta']}</span>"
            f"<span class='bufunfa-sub'>{conta['tipo']}</span></div>"
            f"<strong>{db.formatar_moeda(conta['saldo_atual'])}</strong></div>",
            unsafe_allow_html=True,
        )

with main_right:
    st.markdown(
        "<div class='bufunfa-section-title'><b>02</b> Últimos lançamentos</div>",
        unsafe_allow_html=True,
    )
    if trans_df.empty:
        st.caption("Nenhuma transação registrada.")
    else:
        recentes = (
            trans_df.sort_values(["data_dt", "id"], ascending=False).head(5).copy()
        )
        recentes["categoria_nome"] = recentes["categoria_nome"].fillna("Outros")
        recentes["data"] = recentes["data_dt"].dt.strftime("%d/%m")
        recentes["valor_num"] = recentes["valor"]
        recentes["valor"] = recentes["valor"].apply(db.formatar_moeda)
        recentes = recentes[
            ["data", "descricao", "categoria_nome", "valor", "valor_num"]
        ].rename(
            columns={
                "data": "Data",
                "descricao": "Descrição",
                "categoria_nome": "Categoria",
                "valor": "Valor",
                "valor_num": "valor_num",
            }
        )
        for _, lancamento in recentes.iterrows():
            classe = (
                "bufunfa-row--in"
                if lancamento["valor_num"] >= 0
                else "bufunfa-row--out"
            )
            descricao = lancamento["Descrição"]
            st.markdown(
                f"<div class='bufunfa-row {classe}'><div class='bufunfa-main'>"
                f"<span class='bufunfa-sub'>{lancamento['Data']}</span>"
                f"<span class='bufunfa-label'>{descricao[:34]}</span></div>"
                f"<strong>{lancamento['Valor']}</strong></div>",
                unsafe_allow_html=True,
            )
