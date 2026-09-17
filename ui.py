"""Componentes visuais compartilhados do Bufunfa."""

from __future__ import annotations

import streamlit as st


def aplicar_estilo(compacto: bool = False) -> None:
    """Adiciona pequenos refinamentos consistentes sobre o tema nativo."""
    st.markdown(
        """
        <style>
        input, textarea { border-radius: 7px !important; }
        [data-baseweb="select"] > div { border-radius: 7px; }
        [data-testid="stAlert"] { border-radius: 8px; }
        button[kind="primary"], button[kind="secondary"] { border-radius: 7px; }
        </style>
        """,
        unsafe_allow_html=True,
    )
    estilo_compacto = (
        """
        [data-testid="stMainBlockContainer"] { padding-top: 0.75rem; }
        h1 { font-size: 1.9rem; }
        h2, h3 { margin-top: 0.5rem; margin-bottom: 0.35rem; }
        [data-testid="stCaptionContainer"] { font-size: 0.76rem; }
        div[data-testid="stForm"] { padding: 0.55rem 0.7rem; }
        div[data-testid="stForm"] label { font-size: 0.76rem; }
        div[data-testid="stForm"] input { min-height: 1.9rem; }
        div[data-testid="stForm"] button { min-height: 1.9rem; padding: 0.2rem 0.55rem; }
        [data-testid="stHorizontalBlock"] { gap: 0.45rem; }
        .bufunfa-row { min-height: 1.8rem; padding: 0.16rem 0.35rem; }
        .bufunfa-metrics { margin-bottom: 0.5rem; }
        """
        if compacto
        else ""
    )
    st.markdown(
        """
        <style>
        :root {
            --bufunfa-bg: #0d1417;
            --bufunfa-bg-alt: #101c21;
            --bufunfa-panel: #132128;
            --bufunfa-panel-soft: #172a30;
            --bufunfa-border: #2a3d45;
            --bufunfa-text: #ecf5f6;
            --bufunfa-muted: #9db2b8;
            --bufunfa-accent: #6dd8ca;
            --bufunfa-success: #34d399;
            --bufunfa-warning: #fbbf24;
            --bufunfa-danger: #f87171;
            --bufunfa-danger-soft: rgba(248, 113, 113, 0.12);
            --bufunfa-success-soft: rgba(52, 211, 153, 0.12);
        }
        html, body, [data-testid="stAppViewContainer"] { background: linear-gradient(180deg, var(--bufunfa-bg) 0%, var(--bufunfa-bg-alt) 100%); }
        [data-testid="stHeader"] { background: rgba(13, 20, 23, 0.82); }
        [data-testid="stSidebar"] { border-right: 1px solid var(--bufunfa-border); }
        [data-testid="stSidebar"] > div:first-child { background: #111d22; }
        [data-testid="stMainBlockContainer"] { max-width: 1180px; padding-top: 1.25rem; }
        h1 { letter-spacing: -0.04em; margin: 0 0 0.15rem; font-size: 2.35rem; }
        h2, h3 { letter-spacing: -0.02em; margin-top: 0.85rem; }
        [data-testid="stCaptionContainer"] { color: var(--bufunfa-muted); }
        [data-testid="stMetric"] {
            background: linear-gradient(180deg, var(--bufunfa-panel) 0%, #101a1f 100%);
            border: 1px solid var(--bufunfa-border);
            border-radius: 14px;
            padding: 0.78rem 0.8rem;
            box-shadow: 0 10px 24px rgba(0, 0, 0, 0.18);
        }
        [data-testid="stMetricLabel"] { color: var(--bufunfa-muted); font-size: 0.72rem; letter-spacing: 0.02em; }
        [data-testid="stMetricValue"] { color: var(--bufunfa-text); font-size: 1.35rem; font-weight: 700; }
        [data-testid="stMetricDelta"] { font-size: 0.7rem; }
        .bufunfa-metrics { display: grid; grid-template-columns: repeat(4, minmax(0, 1fr)); gap: 0.65rem; margin: 0.35rem 0 0.9rem; }
        .bufunfa-metric { min-width: 0; padding: 0.72rem 0.8rem; border: 1px solid var(--bufunfa-border); border-radius: 12px; background: linear-gradient(180deg, var(--bufunfa-panel) 0%, #101c22 100%); box-shadow: inset 0 1px 0 rgba(255,255,255,0.02); }
        .bufunfa-metric span { display: block; color: var(--bufunfa-muted); font-size: 0.7rem; margin-bottom: 0.22rem; letter-spacing: 0.04em; text-transform: uppercase; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
        .bufunfa-metric strong { display: block; color: var(--bufunfa-text); font-size: clamp(1rem, 2.2vw, 1.42rem); line-height: 1.15; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
        .bufunfa-row {
            display: flex; justify-content: space-between; align-items: center; gap: 0.55rem;
            min-height: 2.2rem; padding: 0.42rem 0.5rem; border: 1px solid transparent;
            border-bottom: 1px solid var(--bufunfa-border); color: var(--bufunfa-text); font-size: 0.8rem;
            background: rgba(255,255,255,0.01); border-radius: 10px 10px 0 0;
        }
        .bufunfa-row:hover { border-color: rgba(109, 216, 202, 0.18); background: rgba(109, 216, 202, 0.04); }
        .bufunfa-main { display: flex; flex-direction: column; min-width: 0; gap: 0.1rem; }
        .bufunfa-label { display: block; font-weight: 600; color: var(--bufunfa-text); white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
        .bufunfa-sub { color: var(--bufunfa-muted); font-size: 0.68rem; letter-spacing: 0.02em; }
        .bufunfa-row strong { flex: 0 0 auto; font-size: 0.8rem; }
        .bufunfa-row--in strong { color: var(--bufunfa-success); }
        .bufunfa-row--out strong { color: var(--bufunfa-danger); }
        .bufunfa-list-title { min-height: 1.9rem; padding: 0.28rem 0; color: var(--bufunfa-text); font-size: 0.8rem; line-height: 1.2; border-bottom: 1px solid var(--bufunfa-border); }
        .bufunfa-list-title small { color: var(--bufunfa-muted); font-size: 0.68rem; }
        .bufunfa-list-value { min-height: 1.9rem; padding: 0.28rem 0; color: var(--bufunfa-text); font-size: 0.78rem; font-weight: 700; text-align: right; border-bottom: 1px solid var(--bufunfa-border); }
        .bufunfa-list-title strong { font-weight: 600; }
        [data-testid="stButton"] button { min-height: 1.9rem; padding: 0.2rem 0.55rem; font-size: 0.74rem; }
        [data-testid="stDataFrame"] { border: 1px solid var(--bufunfa-border); border-radius: 12px; overflow: hidden; }
        [data-testid="stDataFrame"] [role="gridcell"] { min-height: 1.8rem; }
        [data-testid="stHorizontalBlock"] { gap: 0.65rem; }
        [data-testid="stColumn"] { min-width: 0; }
        [data-testid="stColumn"] > div { min-width: 0; }
        .bufunfa-list-title, .bufunfa-list-value { overflow: hidden; }
        .bufunfa-section-title { display: flex; align-items: center; gap: 0.55rem; margin: 0.15rem 0 0.35rem; color: var(--bufunfa-text); font-size: 0.88rem; font-weight: 700; letter-spacing: 0.01em; }
        .bufunfa-section-title b { display: inline-grid; place-items: center; width: 1.35rem; height: 1.35rem; border-radius: 50%; background: rgba(109, 216, 202, 0.14); color: var(--bufunfa-accent); font-size: 0.68rem; }
        div[data-testid="stForm"] { border: 1px solid var(--bufunfa-border); border-radius: 12px; background: linear-gradient(180deg, var(--bufunfa-panel) 0%, var(--bufunfa-panel-soft) 100%); padding: 0.9rem; }
        [data-testid="stColumn"] > div > div > div[data-testid="stMarkdownContainer"] > p > strong { color: var(--bufunfa-text); font-size: 0.82rem; letter-spacing: 0.01em; }
        button[kind="primary"] { box-shadow: 0 8px 18px rgba(52, 211, 153, 0.18); }
        a[data-testid="stPageLink-NavLink"] { border-radius: 10px; background: rgba(109, 216, 202, 0.06); border: 1px solid rgba(109, 216, 202, 0.18); }
        [data-testid="stDateInput"] input { min-height: 2.15rem; }
        [data-testid="stPageLink-NavLink"] { padding: 0.35rem 0.7rem; }
        @media (max-width: 640px) {
            [data-testid="stMainBlockContainer"] { padding: 0.7rem 0.7rem 1rem; }
            h1 { font-size: 1.85rem; }
            h2, h3 { font-size: 1rem; margin-top: 0.6rem; }
            [data-testid="stMetric"] { padding: 0.38rem 0.55rem; }
            [data-testid="stMetricValue"] { font-size: 1.12rem; }
            [data-testid="stDataFrame"] { font-size: 0.76rem; }
            [data-testid="stHorizontalBlock"] { gap: 0.4rem; }
            .bufunfa-metrics { grid-template-columns: repeat(2, minmax(0, 1fr)); gap: 0.45rem; }
            .bufunfa-metric { padding: 0.5rem 0.6rem; }
            .bufunfa-row { min-height: 1.85rem; padding: 0.2rem 0.35rem; }
        }
        </style>
        """,
        unsafe_allow_html=True,
    )
    if estilo_compacto:
        st.markdown(f"<style>{estilo_compacto}</style>", unsafe_allow_html=True)


def cabecalho(titulo: str, descricao: str, icone: str) -> None:
    st.title(f"{icone}  {titulo}")
    st.caption(descricao)


def metric_grid(metricas: list[tuple[str, str]]) -> None:
    itens = "".join(
        f'<div class="bufunfa-metric"><span>{rotulo}</span><strong>{valor}</strong></div>'
        for rotulo, valor in metricas
    )
    st.markdown(f'<div class="bufunfa-metrics">{itens}</div>', unsafe_allow_html=True)
