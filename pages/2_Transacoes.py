"""Lançamento manual, listagem, filtro e edição de transações."""

from __future__ import annotations

from datetime import date

import pandas as pd
import streamlit as st

import db
import ui

st.set_page_config(page_title="Transações", page_icon="📒", layout="wide")
db.init_db()
ui.aplicar_estilo()

ui.cabecalho(
    "Transações",
    "Registre, filtre e revise o movimento do seu dinheiro.",
    ":material/receipt_long:",
)

contas = db.listar_contas()
categorias = db.listar_categorias()

if not contas:
    st.warning(
        "Cadastre ao menos uma conta na página **Bancos e Contas** antes de lançar transações."
    )
    st.stop()

with st.container(border=True):
    st.subheader("Lançar transação manual")
    formulario_nova_transacao = st.form("nova_transacao", clear_on_submit=True)

with formulario_nova_transacao:
    c1, c2, c3 = st.columns(3)
    conta_escolhida = c1.selectbox(
        "Conta",
        options=contas,
        format_func=lambda c: f"{c['banco_nome']} — {c['nome']}",
    )
    data_transacao = c2.date_input("Data", value=date.today())
    tipo_lancamento = c3.radio("Tipo", options=["Despesa", "Receita"], horizontal=True)

    c4, c5 = st.columns(2)
    descricao = c4.text_input("Descrição", placeholder="Ex: Supermercado, Salário...")
    valor_absoluto = c5.number_input(
        "Valor (R$)", min_value=0.0, step=0.01, format="%.2f"
    )

    categoria_sugerida_id = db.sugerir_categoria(descricao) if descricao else None
    opcoes_categoria = [None] + list(categorias)
    indice_padrao = 0
    if categoria_sugerida_id is not None:
        for indice, categoria in enumerate(opcoes_categoria):
            if categoria is not None and categoria["id"] == categoria_sugerida_id:
                indice_padrao = indice
                break

    categoria_escolhida = st.selectbox(
        "Categoria",
        options=opcoes_categoria,
        index=indice_padrao,
        format_func=lambda c: "Sem categoria" if c is None else c["nome"],
    )

    enviado = st.form_submit_button("Adicionar transação", width="stretch")
    if enviado:
        if not descricao.strip() or valor_absoluto == 0:
            st.warning("Preencha a descrição e um valor maior que zero.")
        else:
            valor_final = (
                valor_absoluto if tipo_lancamento == "Receita" else -valor_absoluto
            )
            categoria_id = categoria_escolhida["id"] if categoria_escolhida else None
            _, inserida = db.inserir_transacao(
                conta_escolhida["id"],
                data_transacao.isoformat(),
                descricao,
                valor_final,
                categoria_id,
                origem="manual",
            )
            if inserida:
                st.success("Transação adicionada.")
                st.rerun()
            else:
                st.warning(
                    "Já existe uma transação idêntica nesta conta (mesma data, descrição e valor)."
                )

st.divider()

st.subheader("Filtrar transações")
f1, f2, f3, f4 = st.columns(4)
filtro_conta = f1.selectbox(
    "Conta",
    options=[None] + list(contas),
    format_func=lambda c: "Todas" if c is None else f"{c['banco_nome']} — {c['nome']}",
)
filtro_categoria = f2.selectbox(
    "Categoria",
    options=[None] + list(categorias),
    format_func=lambda c: "Todas" if c is None else c["nome"],
)
filtro_inicio = f3.date_input("De", value=None, key="filtro_inicio")
filtro_fim = f4.date_input("Até", value=None, key="filtro_fim")

transacoes = db.listar_transacoes(
    conta_id=filtro_conta["id"] if filtro_conta else None,
    categoria_id=filtro_categoria["id"] if filtro_categoria else None,
    data_inicio=filtro_inicio.isoformat() if filtro_inicio else None,
    data_fim=filtro_fim.isoformat() if filtro_fim else None,
)

if not transacoes:
    st.info("Nenhuma transação encontrada com esses filtros.")
    st.stop()

df = pd.DataFrame([dict(t) for t in transacoes])
df["categoria_nome"] = df["categoria_nome"].fillna("Sem categoria")
df["tipo"] = df["valor"].apply(lambda v: "Entrada" if v > 0 else "Saída")


def estilizar_valores(tabela: pd.DataFrame, colunas_monetarias):
    def cor_do_valor(valor):
        if valor > 0:
            return "color: #16803c; font-weight: 600"
        if valor < 0:
            return "color: #c2413b; font-weight: 600"
        return "color: #64748b"

    def cor_do_tipo(tipo):
        if tipo == "Entrada":
            return "color: #16803c; font-weight: 600"
        if tipo == "Saída":
            return "color: #c2413b; font-weight: 600"
        return "color: #64748b"

    estilo = tabela.style.format(
        {coluna: db.formatar_moeda for coluna in colunas_monetarias}
    )
    for coluna in colunas_monetarias:
        estilo = estilo.map(cor_do_valor, subset=[coluna])
    if "Saídas" in tabela:
        estilo = estilo.map(
            lambda valor: "color: #c2413b; font-weight: 600",
            subset=["Saídas"],
        )
    if "Tipo" in tabela:
        estilo = estilo.map(cor_do_tipo, subset=["Tipo"])
    return estilo


operacionais = df[df["natureza"] == "operacional"]
total_receitas = operacionais.loc[operacionais["valor"] > 0, "valor"].sum()
total_despesas = operacionais.loc[operacionais["valor"] < 0, "valor"].abs().sum()
c1, c2, c3 = st.columns(3)
c1.metric("Receitas no filtro", db.formatar_moeda(total_receitas), border=True)
c2.metric("Despesas no filtro", db.formatar_moeda(total_despesas), border=True)
c3.metric(
    "Saldo no filtro",
    db.formatar_moeda(total_receitas - total_despesas),
    border=True,
)

investimentos = df[df["natureza"] == "investimento"]
transferencias = df[df["natureza"] == "transferência"]
i1, i2 = st.columns(2)
i1.metric(
    "Investimentos no filtro",
    db.formatar_moeda(investimentos["valor"].abs().sum()),
    border=True,
)
i2.metric(
    "Transferências no filtro",
    db.formatar_moeda(transferencias["valor"].abs().sum()),
    border=True,
)

if filtro_conta is None and df["conta_nome"].nunique() > 1:
    st.markdown("**Entradas e saídas por conta (dentro do filtro atual)**")
    st.caption(
        "Entradas, saídas e movimentação líquida respeitam os filtros acima. "
        "O saldo atual considera todo o histórico da conta e o saldo inicial."
    )
    df["conta_label"] = df["banco_nome"] + " — " + df["conta_nome"]
    por_conta = (
        df.groupby("conta_label")
        .apply(
            lambda d: pd.Series(
                {
                    "Entradas": d.loc[d["valor"] > 0, "valor"].sum(),
                    "Saídas": d.loc[d["valor"] < 0, "valor"].abs().sum(),
                    "Operacional": d.loc[d["natureza"] == "operacional", "valor"].sum(),
                    "Investimentos": d.loc[
                        d["natureza"] == "investimento", "valor"
                    ].sum(),
                    "Transferências": d.loc[
                        d["natureza"] == "transferência", "valor"
                    ].sum(),
                }
            ),
            include_groups=False,
        )
        .reset_index()
    )
    por_conta["Resultado líquido"] = por_conta["Entradas"] - por_conta["Saídas"]
    contas_por_label = {
        f"{conta['banco_nome']} — {conta['nome']}": conta for conta in contas
    }
    por_conta["Saldo inicial"] = por_conta["conta_label"].map(
        lambda label: contas_por_label[label]["saldo_inicial"]
    )
    por_conta["Saldo atual"] = por_conta["conta_label"].map(
        lambda label: db.saldo_atual_conta(contas_por_label[label]["id"])
    )
    tabela_por_conta = por_conta.rename(columns={"conta_label": "Conta"})
    st.dataframe(
        estilizar_valores(
            tabela_por_conta,
            [
                "Entradas",
                "Saídas",
                "Operacional",
                "Investimentos",
                "Transferências",
                "Resultado líquido",
                "Saldo inicial",
                "Saldo atual",
            ],
        ),
        width="stretch",
        hide_index=True,
    )

tabela_transacoes = df[
    [
        "data",
        "banco_nome",
        "conta_nome",
        "descricao",
        "categoria_nome",
        "tipo",
        "natureza",
        "valor",
        "origem",
    ]
].copy()
tabela_transacoes = tabela_transacoes.rename(
    columns={
        "data": "Data",
        "banco_nome": "Banco",
        "conta_nome": "Conta",
        "descricao": "Descrição",
        "categoria_nome": "Categoria",
        "tipo": "Tipo",
        "natureza": "Natureza",
        "valor": "Valor",
        "origem": "Origem",
    }
)
st.dataframe(
    estilizar_valores(tabela_transacoes, ["Valor"]),
    width="stretch",
    hide_index=True,
    column_config={
        "Data": st.column_config.DateColumn("Data", format="DD/MM/YYYY"),
        "Natureza": st.column_config.TextColumn("Natureza"),
    },
)

st.divider()
st.subheader("Editar ou excluir uma transação")
mapa_transacoes = {
    f"#{t['id']} — {t['data']} — {t['descricao']} — {db.formatar_moeda(t['valor'])}": t
    for t in transacoes
}
chave_escolhida = st.selectbox(
    "Selecione a transação", options=list(mapa_transacoes.keys())
)
transacao_selecionada = mapa_transacoes[chave_escolhida]

with st.form("editar_transacao"):
    e1, e2, e3 = st.columns(3)
    nova_descricao = e1.text_input(
        "Descrição", value=transacao_selecionada["descricao"]
    )
    novo_valor = e2.number_input(
        "Valor (positivo = receita, negativo = despesa)",
        value=float(transacao_selecionada["valor"]),
        step=0.01,
        format="%.2f",
    )
    categorias_opcoes = [None] + list(categorias)
    indice_atual = 0
    for indice, categoria in enumerate(categorias_opcoes):
        if (
            categoria is not None
            and categoria["id"] == transacao_selecionada["categoria_id"]
        ):
            indice_atual = indice
            break
    nova_categoria = e3.selectbox(
        "Categoria",
        options=categorias_opcoes,
        index=indice_atual,
        format_func=lambda c: "Sem categoria" if c is None else c["nome"],
    )

    col_salvar, col_excluir = st.columns(2)
    salvar = col_salvar.form_submit_button("Salvar alterações", width="stretch")
    excluir = col_excluir.form_submit_button("Excluir transação", width="stretch")

    if salvar:
        db.atualizar_transacao(
            transacao_selecionada["id"],
            descricao=nova_descricao,
            valor=novo_valor,
            categoria_id=nova_categoria["id"] if nova_categoria else None,
        )
        st.success("Transação atualizada.")
        st.rerun()

    if excluir:
        db.remover_transacao(transacao_selecionada["id"])
        st.success("Transação excluída.")
        st.rerun()
