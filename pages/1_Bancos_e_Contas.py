"""Gestão de bancos e contas do Bufunfa."""

from __future__ import annotations

import streamlit as st

import db
import ui

st.set_page_config(
    page_title="Bufunfa — Bancos e contas",
    page_icon=":material/account_balance:",
    layout="wide",
)
db.init_db()
ui.aplicar_estilo(compacto=True)
st.markdown(
    """
    <style>
    [data-testid="stMainBlockContainer"] { max-width: 1040px; margin: 0 auto; padding-top: 0.2rem; padding-bottom: 0.2rem; }
    [data-testid="stHorizontalBlock"] { gap: 0.35rem; }
    div[data-testid="stForm"] { padding: 0.3rem 0.45rem; min-height: 145px; }
    div[data-testid="stForm"] label { font-size: 0.7rem; }
    div[data-testid="stForm"] input { min-height: 1.55rem; }
    div[data-testid="stForm"] button { min-height: 1.6rem; padding: 0.08rem 0.35rem; }
    .bufunfa-section-title { margin-top: 0; margin-bottom: 0.15rem; }
    </style>
    """,
    unsafe_allow_html=True,
)
ui.cabecalho(
    "Bancos e contas",
    "Cadastre suas contas e mantenha os saldos organizados.",
    ":material/account_balance:",
)

bancos = db.listar_bancos()
contas = db.listar_contas()

_, coluna_esquerda, coluna_direita, _ = st.columns([0.08, 1, 1, 0.08])

with coluna_esquerda:
    with st.container(border=True, height=190):
        st.markdown(
            "<div class='bufunfa-section-title'><b>01</b> Adicionar banco</div>",
            unsafe_allow_html=True,
        )
        st.caption("Use o nome que aparece no extrato.")
        with st.form("novo_banco", clear_on_submit=True):
            nome_banco = st.text_input(
                "Nome do banco", placeholder="Ex: Nubank, Itaú..."
            )
            enviado = st.form_submit_button("Adicionar banco", width="stretch")
            if enviado:
                if not nome_banco.strip():
                    st.warning("Informe um nome válido.")
                else:
                    try:
                        db.criar_banco(nome_banco)
                        st.toast("Banco adicionado.", icon=":material/check:")
                        st.rerun()
                    except Exception:
                        st.error("Esse banco já existe.")

    with st.container(border=True, height=190):
        st.markdown(
            "<div class='bufunfa-section-title'><b>02</b> Adicionar conta</div>",
            unsafe_allow_html=True,
        )
        st.caption("Associe a conta ao banco e informe o saldo inicial.")
        if not bancos:
            st.caption("Adicione um banco primeiro.")
        else:
            with st.form("nova_conta", clear_on_submit=True):
                c1, c2 = st.columns(2)
                banco_escolhido = c1.selectbox(
                    "Banco", options=bancos, format_func=lambda banco: banco["nome"]
                )
                nome_conta = c2.text_input("Nome da conta", placeholder="Ex: Principal")
                c3, c4 = st.columns(2)
                tipo_conta = c3.selectbox("Tipo", options=db.TIPOS_CONTA)
                saldo_inicial = c4.number_input(
                    "Saldo inicial", step=0.01, format="%.2f"
                )
                enviado_conta = st.form_submit_button(
                    "Adicionar conta", type="primary", width="stretch"
                )
                if enviado_conta:
                    if not nome_conta.strip():
                        st.warning("Informe um nome para a conta.")
                    else:
                        db.criar_conta(
                            banco_escolhido["id"], nome_conta, tipo_conta, saldo_inicial
                        )
                        st.toast("Conta adicionada.", icon=":material/check:")
                        st.rerun()

with coluna_direita:
    with st.container(border=True, height=190):
        st.markdown(
            "<div class='bufunfa-section-title'><b>03</b> Bancos cadastrados</div>",
            unsafe_allow_html=True,
        )
        st.caption("Saldo consolidado por instituição.")
        if not bancos:
            st.caption("Nenhum banco cadastrado ainda.")
        for banco in bancos:
            contas_banco = [
                conta for conta in contas if conta["banco_id"] == banco["id"]
            ]
            saldo_banco = sum(
                db.saldo_atual_conta(conta["id"]) for conta in contas_banco
            )
            nome, saldo, acao = st.columns([1.5, 0.95, 0.22])
            nome.markdown(
                f"<div class='bufunfa-list-title'><strong>{banco['nome']}</strong> "
                f"<small>{len(contas_banco)} conta(s)</small></div>",
                unsafe_allow_html=True,
            )
            saldo.markdown(
                f"<div class='bufunfa-list-value'>{db.formatar_moeda(saldo_banco)}</div>",
                unsafe_allow_html=True,
            )
            if acao.button(
                ":material/delete:", key=f"rm_banco_{banco['id']}", help="Remover banco"
            ):
                db.remover_banco(banco["id"])
                st.rerun()

    with st.container(border=True, height=190):
        st.markdown(
            "<div class='bufunfa-section-title'><b>04</b> Contas cadastradas</div>",
            unsafe_allow_html=True,
        )
        st.caption("Saldo atual por conta, com tipo e banco identificados.")
        if not contas:
            st.caption("Nenhuma conta cadastrada ainda.")
        for conta in contas:
            saldo = db.saldo_atual_conta(conta["id"])
            nome, saldo_col, acao = st.columns([1.5, 0.9, 0.25])
            nome.markdown(
                f"<div class='bufunfa-list-title'><strong>{conta['banco_nome']} · "
                f"{conta['nome']}</strong> <small>{conta['tipo']}</small></div>",
                unsafe_allow_html=True,
            )
            saldo_col.markdown(
                f"<div class='bufunfa-list-value'>{db.formatar_moeda(saldo)}</div>",
                unsafe_allow_html=True,
            )
            if acao.button(
                ":material/power_settings_new:",
                key=f"rm_conta_{conta['id']}",
                help="Desativar conta",
            ):
                db.desativar_conta(conta["id"])
                st.rerun()
