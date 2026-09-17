"""Cadastro de categorias e regras de categorização automática."""

from __future__ import annotations

import streamlit as st

import db
import ui

st.set_page_config(page_title="Categorias e Regras", page_icon="🏷️", layout="wide")
db.init_db()
ui.aplicar_estilo()

ui.cabecalho(
    "Categorias e regras",
    "Personalize como as descrições dos lançamentos são classificadas.",
    ":material/label:",
)

col_nova_cat, col_lista_cat = st.columns([1, 2])

with col_nova_cat:
    st.subheader("Nova categoria")
    with st.form("nova_categoria", clear_on_submit=True):
        nome_categoria = st.text_input("Nome", placeholder="Ex: Educação")
        tipo_categoria = st.selectbox("Tipo", options=db.TIPOS_CATEGORIA)
        enviado = st.form_submit_button("Adicionar categoria", width="stretch")
        if enviado:
            if nome_categoria.strip():
                try:
                    db.criar_categoria(nome_categoria, tipo_categoria)
                    st.success("Categoria adicionada.")
                    st.rerun()
                except Exception:
                    st.error("Essa categoria já existe.")
            else:
                st.warning("Informe um nome válido.")

categorias = db.listar_categorias()

with col_lista_cat:
    st.subheader("Categorias cadastradas")
    for categoria in categorias:
        c1, c2, c3 = st.columns([3, 2, 1])
        c1.write(f"**{categoria['nome']}**")
        c2.write(categoria["tipo"])
        if c3.button("Remover", key=f"rm_cat_{categoria['id']}"):
            db.remover_categoria(categoria["id"])
            st.rerun()

st.divider()

st.subheader("Nova regra de categorização")
if not categorias:
    st.info("Cadastre uma categoria antes de criar regras.")
else:
    with st.form("nova_regra", clear_on_submit=True):
        c1, c2, c3 = st.columns([2, 3, 1])
        categoria_regra = c1.selectbox(
            "Categoria", options=categorias, format_func=lambda c: c["nome"]
        )
        palavra_chave = c2.text_input(
            "Palavra-chave (contida na descrição)",
            placeholder="Ex: ifood, uber, supermercado...",
        )
        prioridade = c3.number_input(
            "Prioridade", value=0, step=1, help="Maior valor é aplicado primeiro."
        )
        enviado_regra = st.form_submit_button("Adicionar regra", width="stretch")
        if enviado_regra:
            if palavra_chave.strip():
                db.criar_regra(categoria_regra["id"], palavra_chave, prioridade)
                st.success("Regra adicionada.")
                st.rerun()
            else:
                st.warning("Informe uma palavra-chave.")

st.subheader("Regras cadastradas")
regras = db.listar_regras()
if not regras:
    st.info("Nenhuma regra cadastrada ainda.")
else:
    for regra in regras:
        c1, c2, c3 = st.columns([2, 3, 1])
        c1.write(f"**{regra['categoria_nome']}**")
        c2.write(f"contém: `{regra['palavra_chave']}`")
        if c3.button("Remover", key=f"rm_regra_{regra['id']}"):
            db.remover_regra(regra["id"])
            st.rerun()
