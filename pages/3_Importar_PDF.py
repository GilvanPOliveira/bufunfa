"""Importação de extratos bancários em PDF."""

from __future__ import annotations

from datetime import date

import pandas as pd
import streamlit as st

import db
import ui
from parsers import (
    DETECTAR_AUTOMATICAMENTE,
    detectar_banco,
    detectar_tipo_conta,
    parse_arquivo,
)
from parsers.common import (
    extrair_saldo_anterior,
    extrair_texto,
    resolver_ano_referencia,
)

st.set_page_config(page_title="Importar PDF", page_icon="📄", layout="wide")
db.init_db()
ui.aplicar_estilo()

ui.cabecalho(
    "Importar extratos",
    "Envie um ou vários PDFs e revise os lançamentos antes de salvar.",
    ":material/upload_file:",
)
st.caption(
    "Envie o PDF do extrato. O banco, o ano, o tipo de conta e as datas serão "
    "identificados automaticamente antes da importação."
)

if "preview_df" not in st.session_state:
    st.session_state.preview_df = None
if "import_context" not in st.session_state:
    st.session_state.import_context = None
if "pdf_uploader_key" not in st.session_state:
    st.session_state.pdf_uploader_key = 0
if "importacao_em_andamento" not in st.session_state:
    st.session_state.importacao_em_andamento = False
if "confirmando_importacao" not in st.session_state:
    st.session_state.confirmando_importacao = False
if "resultado_importacao" not in st.session_state:
    st.session_state.resultado_importacao = None

if st.session_state.resultado_importacao:
    st.success(st.session_state.resultado_importacao)
    st.session_state.resultado_importacao = None

arquivo_pdf = st.file_uploader(
    "Arquivos PDF dos extratos",
    type=["pdf"],
    accept_multiple_files=True,
    key=f"pdf_uploader_{st.session_state.pdf_uploader_key}",
    help=(
        "Você pode selecionar um ou vários PDFs com texto selecionável. Fotos/prints "
        "(JPG, PNG) e PDFs escaneados ainda não são suportados."
    ),
)

if arquivo_pdf and st.button(
    (
        "Processando PDFs..."
        if st.session_state.importacao_em_andamento
        else "Extrair transações dos PDFs"
    ),
    width="stretch",
    disabled=st.session_state.importacao_em_andamento,
):
    st.session_state.importacao_em_andamento = True
    linhas = []
    arquivos_com_erro = []
    deteccoes = []
    with st.status("Processando PDFs", expanded=True) as status:
        status.write("Detectando banco, conta e período...")
        for arquivo in arquivo_pdf:
            banco_detectado = detectar_banco(arquivo)
            ano_detectado = resolver_ano_referencia(arquivo, date.today().year)
            tipo_conta_detectado = detectar_tipo_conta(arquivo)
            arquivo.seek(0)
            saldo_anterior = extrair_saldo_anterior(extrair_texto(arquivo))
            if not banco_detectado:
                arquivos_com_erro.append(f"{arquivo.name}: banco não identificado")
                continue

            deteccoes.append(
                f"{arquivo.name}: {banco_detectado} · {tipo_conta_detectado} · "
                f"{ano_detectado} · saldo inicial {db.formatar_moeda(saldo_anterior or 0)}"
            )
            transacoes_extraidas = parse_arquivo(
                arquivo, DETECTAR_AUTOMATICAMENTE, ano_detectado
            )
            if not transacoes_extraidas:
                arquivos_com_erro.append(
                    f"{arquivo.name}: nenhuma transação reconhecida"
                )
                continue

            categorias = db.listar_categorias()
            mapa_categoria_nome = {c["id"]: c["nome"] for c in categorias}
            for transacao in transacoes_extraidas:
                categoria_sugerida_id = db.sugerir_categoria(transacao.descricao)
                linhas.append(
                    {
                        "importar": True,
                        "banco": banco_detectado,
                        "conta_tipo": tipo_conta_detectado,
                        "saldo_anterior": saldo_anterior,
                        "data": transacao.data,
                        "descricao": transacao.descricao,
                        "tipo": "Entrada" if transacao.valor > 0 else "Saída",
                        "valor": db.formatar_moeda(transacao.valor),
                        "categoria": mapa_categoria_nome.get(
                            categoria_sugerida_id, "Sem categoria"
                        ),
                    }
                )
        status.update(label="PDFs processados", state="complete", expanded=False)

    st.session_state.importacao_em_andamento = False

    if not linhas:
        st.error(
            "Nenhuma transação foi reconhecida. Verifique se os PDFs têm texto "
            "selecionável e pertencem a bancos suportados."
        )
        st.session_state.preview_df = None
        st.session_state.import_context = None
    else:
        st.session_state.preview_df = pd.DataFrame(linhas)
        st.session_state.import_context = deteccoes
        if arquivos_com_erro:
            st.warning(
                "Alguns arquivos não entraram:\n\n- " + "\n- ".join(arquivos_com_erro)
            )
        st.success(
            f"{len(linhas)} transações encontradas em {len(arquivo_pdf)} PDF(s). "
            "Revise abaixo antes de confirmar."
        )

if st.session_state.preview_df is not None:
    categorias = db.listar_categorias()
    nomes_categoria = ["Sem categoria"] + [c["nome"] for c in categorias]
    nome_para_id = {c["nome"]: c["id"] for c in categorias}

    st.subheader("Revisar transações antes de importar")
    st.info(
        "Cada linha já contém o banco e o tipo de conta detectados. Se algum banco "
        "ainda não existir, ele será criado ao confirmar."
    )
    st.caption(
        "Confira a coluna **Tipo**: Entrada = dinheiro que entrou na conta, "
        "Saída = dinheiro que saiu. O valor negativo (-) indica saída; edite a coluna "
        "Valor se algo estiver incorreto (use número negativo para saída)."
    )
    df_editado = st.data_editor(
        st.session_state.preview_df,
        width="stretch",
        hide_index=True,
        num_rows="dynamic",
        column_config={
            "importar": st.column_config.CheckboxColumn("Importar?"),
            "banco": st.column_config.TextColumn("Banco"),
            "conta_tipo": st.column_config.TextColumn("Tipo de conta"),
            "saldo_anterior": None,
            "data": st.column_config.TextColumn("Data (AAAA-MM-DD)"),
            "descricao": st.column_config.TextColumn("Descrição"),
            "tipo": st.column_config.SelectboxColumn(
                "Tipo", options=["Entrada", "Saída"]
            ),
            "valor": st.column_config.TextColumn("Valor (R$)"),
            "categoria": st.column_config.SelectboxColumn(
                "Categoria", options=nomes_categoria
            ),
        },
        key="editor_preview",
    )

    valores_editados = df_editado["valor"].apply(db.ler_moeda)
    total_entradas = valores_editados.loc[valores_editados > 0].sum()
    total_saidas = valores_editados.loc[valores_editados < 0].abs().sum()
    m1, m2, m3 = st.columns(3)
    m1.metric("Total de entradas nesta importação", db.formatar_moeda(total_entradas))
    m2.metric("Total de saídas nesta importação", db.formatar_moeda(total_saidas))
    m3.metric("Resultado", db.formatar_moeda(total_entradas - total_saidas))

    col_confirmar, col_cancelar = st.columns(2)
    confirmar = col_confirmar.button(
        (
            "Importando..."
            if st.session_state.get("confirmando_importacao", False)
            else "Confirmar importação"
        ),
        type="primary",
        width="stretch",
        disabled=st.session_state.get("confirmando_importacao", False),
    )
    cancelar = col_cancelar.button("Cancelar", width="stretch")

    if cancelar:
        st.session_state.preview_df = None
        st.session_state.import_context = None
        st.session_state.pdf_uploader_key += 1
        st.info("Importação cancelada. Nenhuma transação foi salva.")
        st.rerun()

    if confirmar:
        st.session_state.confirmando_importacao = True
        inseridas, duplicadas = 0, 0
        destinos = []
        linhas_importadas = df_editado[df_editado["importar"]]
        with st.status("Importando transações", expanded=True) as status:
            for (nome_banco, tipo_conta), grupo in linhas_importadas.groupby(
                ["banco", "conta_tipo"]
            ):
                banco_id, banco_criado = db.obter_ou_criar_banco(nome_banco)
                conta_id, conta_criada = db.obter_ou_criar_conta(banco_id, tipo_conta)
                saldo_anterior = (
                    grupo["saldo_anterior"].dropna().iloc[0]
                    if grupo["saldo_anterior"].notna().any()
                    else None
                )
                db.definir_saldo_inicial_se_vazia(conta_id, saldo_anterior)
                destinos.append(
                    f"{nome_banco} ({'conta criada' if conta_criada else 'conta existente'})"
                )
                status.write(f"Salvando {nome_banco} · {tipo_conta}...")
                for _, linha in grupo.iterrows():
                    categoria_id = nome_para_id.get(linha["categoria"])
                    if categoria_id is None:
                        categoria_id = db.sugerir_categoria(linha["descricao"])
                    valor_final = db.ler_moeda(linha["valor"])
                    if linha["tipo"] == "Entrada":
                        valor_final = abs(valor_final)
                    else:
                        valor_final = -abs(valor_final)
                    _, inserida = db.inserir_transacao(
                        conta_id,
                        linha["data"],
                        linha["descricao"],
                        valor_final,
                        categoria_id,
                        origem="pdf",
                    )
                    if inserida:
                        inseridas += 1
                    else:
                        duplicadas += 1
            status.update(
                label="Importação concluída", state="complete", expanded=False
            )

        st.session_state.preview_df = None
        st.session_state.import_context = None
        st.session_state.pdf_uploader_key += 1
        st.session_state.confirmando_importacao = False
        st.session_state.resultado_importacao = (
            f"{inseridas} transações importadas para {len(destinos)} destino(s). "
            f"{duplicadas} ignoradas por já existirem (duplicadas)."
        )
        st.rerun()
