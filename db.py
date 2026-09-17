"""Camada de acesso a dados (SQLite local) do Bufunfa.

Todo o dado do usuário fica em um único arquivo .db dentro de data/,
sem nenhuma comunicação externa.
"""

from __future__ import annotations

import hashlib
import re
import sqlite3
import unicodedata
from contextlib import contextmanager
from pathlib import Path

DB_PATH = Path(__file__).parent / "data" / "bufunfa.db"

TIPOS_CONTA = [
    "Corrente",
    "Poupança",
    "Investimento",
    "Carteira/Dinheiro",
    "Cartão de Crédito",
]
TIPOS_CATEGORIA = ["Receita", "Despesa"]
NATUREZAS_TRANSACAO = ["operacional", "transferência", "investimento"]


def formatar_moeda(valor: float) -> str:
    """Formata um número no padrão monetário brasileiro: R$ 1.234,56 / -R$ 1.234,56."""
    valor_arredondado = round(float(valor), 2)
    sinal = "-" if valor_arredondado < 0 else ""
    inteiro, centavos = f"{abs(valor_arredondado):.2f}".split(".")
    grupos = []
    while inteiro:
        grupos.append(inteiro[-3:])
        inteiro = inteiro[:-3]
    milhares = ".".join(reversed(grupos)) or "0"
    return f"{sinal}R$ {milhares},{centavos}"


def ler_moeda(valor: object) -> float:
    """Converte moeda brasileira exibida ou número em float para persistência."""
    if isinstance(valor, (int, float)):
        return float(valor)
    texto = str(valor).strip().replace("R$", "").replace(" ", "")
    if "," in texto:
        texto = texto.replace(".", "").replace(",", ".")
    return float(texto)


@contextmanager
def get_conn():
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    try:
        yield conn
        conn.commit()
    finally:
        conn.close()


def init_db() -> None:
    with get_conn() as conn:
        conn.executescript("""
            CREATE TABLE IF NOT EXISTS bancos (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                nome TEXT NOT NULL UNIQUE
            );

            CREATE TABLE IF NOT EXISTS contas (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                banco_id INTEGER NOT NULL REFERENCES bancos(id) ON DELETE CASCADE,
                nome TEXT NOT NULL,
                tipo TEXT NOT NULL,
                saldo_inicial REAL NOT NULL DEFAULT 0,
                ativo INTEGER NOT NULL DEFAULT 1
            );

            CREATE TABLE IF NOT EXISTS categorias (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                nome TEXT NOT NULL UNIQUE,
                tipo TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS regras_categorizacao (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                categoria_id INTEGER NOT NULL REFERENCES categorias(id) ON DELETE CASCADE,
                palavra_chave TEXT NOT NULL,
                prioridade INTEGER NOT NULL DEFAULT 0
            );

            CREATE TABLE IF NOT EXISTS transacoes (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                conta_id INTEGER NOT NULL REFERENCES contas(id) ON DELETE CASCADE,
                data TEXT NOT NULL,
                descricao TEXT NOT NULL,
                valor REAL NOT NULL,
                categoria_id INTEGER REFERENCES categorias(id) ON DELETE SET NULL,
                origem TEXT NOT NULL DEFAULT 'manual',
                natureza TEXT NOT NULL DEFAULT 'operacional',
                hash_dedup TEXT,
                UNIQUE(conta_id, hash_dedup)
            );

            CREATE INDEX IF NOT EXISTS idx_transacoes_conta ON transacoes(conta_id);
            CREATE INDEX IF NOT EXISTS idx_transacoes_data ON transacoes(data);
            """)
        colunas_transacoes = {
            row["name"]
            for row in conn.execute("PRAGMA table_info(transacoes)").fetchall()
        }
        if "natureza" not in colunas_transacoes:
            conn.execute(
                "ALTER TABLE transacoes ADD COLUMN natureza TEXT NOT NULL DEFAULT 'operacional'"
            )
        conn.execute("""
            UPDATE transacoes
            SET natureza = CASE
                WHEN lower(descricao) LIKE '%aplicacao cdb%'
                  OR lower(descricao) LIKE '%aplicação cdb%'
                  OR lower(descricao) LIKE '%aplicacao rdb%'
                  OR lower(descricao) LIKE '%aplicação rdb%'
                  OR lower(descricao) LIKE '%resgate cdb%'
                  OR lower(descricao) LIKE '%resgate rdb%'
                THEN 'investimento'
                WHEN lower(descricao) LIKE '%aplicacao poupanca%'
                  OR lower(descricao) LIKE '%aplicação poupança%'
                  OR lower(descricao) LIKE '%resgate poupanca%'
                  OR lower(descricao) LIKE '%resgate poupança%'
                THEN 'transferência'
                ELSE natureza
            END
            WHERE natureza = 'operacional'
            """)
        _seed_categorias(conn)
        _preencher_categorias_vazias(conn)
        _preencher_naturezas(conn)


def _preencher_categorias_vazias(conn: sqlite3.Connection) -> None:
    """Aplica regras às transações antigas que foram importadas sem categoria."""
    regras = conn.execute("""
        SELECT regras_categorizacao.palavra_chave, regras_categorizacao.categoria_id
        FROM regras_categorizacao
        ORDER BY prioridade DESC, LENGTH(palavra_chave) DESC
        """).fetchall()
    transacoes = conn.execute(
        "SELECT id, descricao FROM transacoes WHERE categoria_id IS NULL"
    ).fetchall()
    for transacao in transacoes:
        descricao = normalizar_texto(transacao["descricao"])
        categoria_id = next(
            (
                regra["categoria_id"]
                for regra in regras
                if regra["palavra_chave"]
                and normalizar_texto(regra["palavra_chave"]) in descricao
            ),
            None,
        )
        if categoria_id is not None:
            conn.execute(
                "UPDATE transacoes SET categoria_id = ? WHERE id = ?",
                (categoria_id, transacao["id"]),
            )


def _seed_categorias(conn: sqlite3.Connection) -> None:
    padrao = [
        ("Salário", "Receita", ["salario", "pagamento salario", "provento"]),
        (
            "Transferência recebida",
            "Receita",
            ["pix recebido", "ted recebida", "transferencia recebida"],
        ),
        ("Rendimentos", "Receita", ["rendimento", "juros", "dividendo"]),
        (
            "Mercado",
            "Despesa",
            ["supermercado", "mercado", "atacadao", "carrefour", "pao de acucar"],
        ),
        (
            "Transporte",
            "Despesa",
            ["uber", "99app", "combustivel", "posto", "estacionamento"],
        ),
        (
            "Moradia",
            "Despesa",
            ["aluguel", "condominio", "iptu", "energia", "luz", "agua", "gas"],
        ),
        ("Saúde", "Despesa", ["farmacia", "drogaria", "hospital", "plano de saude"]),
        ("Lazer", "Despesa", ["cinema", "netflix", "spotify", "restaurante", "ifood"]),
        ("Cartão de Crédito", "Despesa", ["fatura cartao", "pagamento fatura"]),
        (
            "Transferência enviada",
            "Despesa",
            ["pix enviado", "ted enviada", "transferencia enviada"],
        ),
        ("Outros", "Despesa", []),
        (
            "Investimentos",
            "Investimento",
            ["aplicacao cdb", "aplicação cdb", "aplicacao rdb", "aplicação rdb"],
        ),
        (
            "Transferência interna",
            "Transferência",
            [
                "aplicacao poupanca",
                "aplicação poupança",
                "aplicacao automatica poupanca",
                "aplicação automática poupança",
                "resgate poupanca",
                "resgate poupança",
                "resgate automatico",
                "resgate automático",
            ],
        ),
    ]
    for nome, tipo, palavras in padrao:
        cur = conn.execute(
            "INSERT OR IGNORE INTO categorias (nome, tipo) VALUES (?, ?)", (nome, tipo)
        )
        row = conn.execute(
            "SELECT id FROM categorias WHERE nome = ?", (nome,)
        ).fetchone()
        categoria_id = row["id"]
        for palavra in palavras:
            existe = conn.execute(
                "SELECT 1 FROM regras_categorizacao WHERE categoria_id = ? AND palavra_chave = ?",
                (categoria_id, palavra),
            ).fetchone()
            if not existe:
                conn.execute(
                    "INSERT INTO regras_categorizacao (categoria_id, palavra_chave) VALUES (?, ?)",
                    (categoria_id, palavra),
                )


def make_hash(data: str, descricao: str, valor: float) -> str:
    base = f"{data}|{descricao.strip().lower()}|{valor:.2f}"
    return hashlib.sha256(base.encode("utf-8")).hexdigest()


def normalizar_texto(texto: str) -> str:
    """Normaliza acentos e espaços para comparar descrições com regras."""
    sem_acentos = unicodedata.normalize("NFKD", texto)
    sem_acentos = "".join(
        caractere for caractere in sem_acentos if not unicodedata.combining(caractere)
    )
    return " ".join(sem_acentos.lower().split())


# ---------- Bancos ----------


def listar_bancos():
    with get_conn() as conn:
        return [
            dict(r)
            for r in conn.execute("SELECT * FROM bancos ORDER BY nome").fetchall()
        ]


def criar_banco(nome: str) -> int:
    with get_conn() as conn:
        cur = conn.execute("INSERT INTO bancos (nome) VALUES (?)", (nome.strip(),))
        return cur.lastrowid


def obter_ou_criar_banco(nome: str) -> tuple[int, bool]:
    """Retorna (id, criado), comparando nomes sem diferenciar maiúsculas."""
    nome_limpo = nome.strip()
    with get_conn() as conn:
        row = conn.execute(
            "SELECT id FROM bancos WHERE lower(nome) = lower(?)", (nome_limpo,)
        ).fetchone()
        if row:
            return row["id"], False
        cur = conn.execute("INSERT INTO bancos (nome) VALUES (?)", (nome_limpo,))
        return cur.lastrowid, True


def remover_banco(banco_id: int) -> None:
    with get_conn() as conn:
        conn.execute("DELETE FROM bancos WHERE id = ?", (banco_id,))


# ---------- Contas ----------


def listar_contas(apenas_ativas: bool = True):
    query = """
        SELECT contas.*, bancos.nome AS banco_nome
        FROM contas JOIN bancos ON bancos.id = contas.banco_id
    """
    if apenas_ativas:
        query += " WHERE contas.ativo = 1"
    query += " ORDER BY bancos.nome, contas.nome"
    with get_conn() as conn:
        return [dict(r) for r in conn.execute(query).fetchall()]


def criar_conta(banco_id: int, nome: str, tipo: str, saldo_inicial: float) -> int:
    with get_conn() as conn:
        cur = conn.execute(
            "INSERT INTO contas (banco_id, nome, tipo, saldo_inicial) VALUES (?, ?, ?, ?)",
            (banco_id, nome.strip(), tipo, saldo_inicial),
        )
        return cur.lastrowid


def obter_ou_criar_conta(banco_id: int, tipo: str) -> tuple[int, bool]:
    """Reutiliza a primeira conta ativa do tipo ou cria uma conta automática."""
    nome = "Poupança" if tipo == "Poupança" else "Conta corrente"
    with get_conn() as conn:
        row = conn.execute(
            """
            SELECT id FROM contas
            WHERE banco_id = ? AND tipo = ? AND ativo = 1
            ORDER BY id
            LIMIT 1
            """,
            (banco_id, tipo),
        ).fetchone()
        if row:
            return row["id"], False
        cur = conn.execute(
            """
            INSERT INTO contas (banco_id, nome, tipo, saldo_inicial)
            VALUES (?, ?, ?, 0)
            """,
            (banco_id, nome, tipo),
        )
        return cur.lastrowid, True


def desativar_conta(conta_id: int) -> None:
    with get_conn() as conn:
        conn.execute("UPDATE contas SET ativo = 0 WHERE id = ?", (conta_id,))


def saldo_atual_conta(conta_id: int) -> float:
    with get_conn() as conn:
        row = conn.execute(
            "SELECT saldo_inicial FROM contas WHERE id = ?", (conta_id,)
        ).fetchone()
        saldo_inicial = row["saldo_inicial"] if row else 0
        soma = conn.execute(
            "SELECT COALESCE(SUM(valor), 0) AS total FROM transacoes WHERE conta_id = ?",
            (conta_id,),
        ).fetchone()["total"]
        return round(saldo_inicial + soma, 2)


def definir_saldo_inicial_se_vazia(conta_id: int, saldo_inicial: float | None) -> None:
    """Aplica o saldo do extrato apenas quando a conta ainda não tem lançamentos."""
    if saldo_inicial is None:
        return
    with get_conn() as conn:
        existe = conn.execute(
            "SELECT 1 FROM transacoes WHERE conta_id = ? LIMIT 1", (conta_id,)
        ).fetchone()
        if not existe:
            conn.execute(
                "UPDATE contas SET saldo_inicial = ? WHERE id = ?",
                (saldo_inicial, conta_id),
            )


# ---------- Categorias ----------


def listar_categorias():
    with get_conn() as conn:
        return [
            dict(r)
            for r in conn.execute(
                "SELECT * FROM categorias ORDER BY tipo, nome"
            ).fetchall()
        ]


def criar_categoria(nome: str, tipo: str) -> int:
    with get_conn() as conn:
        cur = conn.execute(
            "INSERT INTO categorias (nome, tipo) VALUES (?, ?)", (nome.strip(), tipo)
        )
        return cur.lastrowid


def remover_categoria(categoria_id: int) -> None:
    with get_conn() as conn:
        conn.execute("DELETE FROM categorias WHERE id = ?", (categoria_id,))


def listar_regras():
    with get_conn() as conn:
        rows = conn.execute("""
            SELECT regras_categorizacao.*, categorias.nome AS categoria_nome, categorias.tipo AS categoria_tipo
            FROM regras_categorizacao JOIN categorias ON categorias.id = regras_categorizacao.categoria_id
            ORDER BY categorias.nome, palavra_chave
            """).fetchall()
        return [dict(r) for r in rows]


def criar_regra(categoria_id: int, palavra_chave: str, prioridade: int = 0) -> int:
    with get_conn() as conn:
        cur = conn.execute(
            "INSERT INTO regras_categorizacao (categoria_id, palavra_chave, prioridade) VALUES (?, ?, ?)",
            (categoria_id, palavra_chave.strip().lower(), prioridade),
        )
        return cur.lastrowid


def remover_regra(regra_id: int) -> None:
    with get_conn() as conn:
        conn.execute("DELETE FROM regras_categorizacao WHERE id = ?", (regra_id,))


def sugerir_categoria(descricao: str) -> int | None:
    descricao_normalizada = normalizar_texto(descricao)
    with get_conn() as conn:
        regras = conn.execute("""
            SELECT regras_categorizacao.palavra_chave,
                   regras_categorizacao.prioridade,
                   categorias.id AS categoria_id,
                   categorias.nome AS categoria_nome
            FROM regras_categorizacao
            JOIN categorias ON categorias.id = regras_categorizacao.categoria_id
            ORDER BY regras_categorizacao.prioridade DESC,
                     LENGTH(regras_categorizacao.palavra_chave) DESC
            """).fetchall()
        melhor = None
        for regra in regras:
            palavra_normalizada = normalizar_texto(regra["palavra_chave"])
            if palavra_normalizada and palavra_normalizada in descricao_normalizada:
                pontuacao = regra["prioridade"] * 1000 + len(palavra_normalizada)
                if melhor is None or pontuacao > melhor[0]:
                    melhor = (pontuacao, regra["categoria_id"])
        if melhor is not None:
            return melhor[1]

        palavras_descricao = {
            palavra
            for palavra in re.findall(r"[a-z0-9]+", descricao_normalizada)
            if len(palavra) >= 4
        }
        exemplos = conn.execute("""
            SELECT transacoes.descricao, transacoes.categoria_id
            FROM transacoes
            JOIN categorias ON categorias.id = transacoes.categoria_id
            WHERE transacoes.categoria_id IS NOT NULL
              AND categorias.nome <> 'Outros'
            """).fetchall()
        pontuacao_por_categoria: dict[int, int] = {}
        for exemplo in exemplos:
            palavras_exemplo = set(
                re.findall(r"[a-z0-9]+", normalizar_texto(exemplo["descricao"]))
            )
            coincidencias = len(palavras_descricao & palavras_exemplo)
            if coincidencias:
                pontuacao_por_categoria[exemplo["categoria_id"]] = (
                    pontuacao_por_categoria.get(exemplo["categoria_id"], 0)
                    + coincidencias
                )
        if pontuacao_por_categoria:
            return max(pontuacao_por_categoria, key=pontuacao_por_categoria.get)

        # Quando não há regra explícita, aproveita palavras relevantes do nome
        # da categoria para dar uma sugestão útil sem obrigar o usuário a editar.
        for categoria in conn.execute("SELECT id, nome FROM categorias").fetchall():
            if normalizar_texto(categoria["nome"]) == "outros":
                continue
            palavras = normalizar_texto(categoria["nome"]).split()
            if any(
                len(palavra) >= 4 and palavra in descricao_normalizada
                for palavra in palavras
            ):
                return categoria["id"]
        padrao = conn.execute(
            "SELECT id FROM categorias WHERE nome = 'Outros' LIMIT 1"
        ).fetchone()
        return padrao["id"] if padrao else None


def classificar_natureza(descricao: str, conta_tipo: str | None = None) -> str:
    """Classifica aplicações/resgates e transferências antes de calcular despesas."""
    texto = descricao.strip().lower()
    texto_normalizado = normalizar_texto(texto)

    if any(
        palavra in texto_normalizado
        for palavra in ("cdb", "rdb", "fundo", "investimento")
    ):
        return "investimento"

    if any(
        palavra in texto_normalizado
        for palavra in (
            "aplicacao poupanca",
            "aplicacao automatica poupanca",
            "resgate poupanca",
            "resgate automatico",
            "transferencia recebida",
            "transferencia enviada",
            "transferencia pix",
            "transferencia bancaria",
            "ted recebida",
            "ted enviada",
            "pix recebido",
            "pix enviado",
        )
    ):
        return "transferência"

    if "transferencia" in texto_normalizado or "pix" in texto_normalizado:
        return "transferência"

    return "operacional"


def _preencher_naturezas(conn: sqlite3.Connection) -> None:
    """Atualiza naturezas de lançamentos antigos após ampliar as descrições conhecidas."""
    transacoes = conn.execute(
        "SELECT id, descricao, natureza FROM transacoes"
    ).fetchall()
    for transacao in transacoes:
        natureza = classificar_natureza(transacao["descricao"])
        if natureza != transacao["natureza"]:
            conn.execute(
                "UPDATE transacoes SET natureza = ? WHERE id = ?",
                (natureza, transacao["id"]),
            )


# ---------- Transações ----------


def inserir_transacao(
    conta_id: int,
    data: str,
    descricao: str,
    valor: float,
    categoria_id: int | None,
    origem: str = "manual",
    natureza: str | None = None,
) -> tuple[int | None, bool]:
    """Insere uma transação. Retorna (id, inserida). Ignora duplicatas (mesmo hash na mesma conta)."""
    hash_dedup = make_hash(data, descricao, valor)
    natureza = natureza or classificar_natureza(descricao)
    with get_conn() as conn:
        try:
            cur = conn.execute(
                """
                INSERT INTO transacoes (conta_id, data, descricao, valor, categoria_id, origem, natureza, hash_dedup)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    conta_id,
                    data,
                    descricao.strip(),
                    valor,
                    categoria_id,
                    origem,
                    natureza,
                    hash_dedup,
                ),
            )
            return cur.lastrowid, True
        except sqlite3.IntegrityError:
            return None, False


def atualizar_transacao(transacao_id: int, **campos) -> None:
    if not campos:
        return

    with get_conn() as conn:
        row = conn.execute(
            "SELECT conta_id, descricao, valor, natureza, categoria_id FROM transacoes WHERE id = ?",
            (transacao_id,),
        ).fetchone()
        if row is None:
            return

        dados = dict(row)
        nova_descricao = campos.get("descricao", dados["descricao"])
        novo_valor = campos.get("valor", dados["valor"])

        if "descricao" in campos or "valor" in campos:
            campos = dict(campos)
            campos["natureza"] = classificar_natureza(str(nova_descricao), None)
            campos["categoria_id"] = campos.get(
                "categoria_id",
                dados["categoria_id"],
            )
            if campos["categoria_id"] is None:
                categoria_sugerida = sugerir_categoria(str(nova_descricao))
                if categoria_sugerida is not None:
                    campos["categoria_id"] = categoria_sugerida

        colunas = ", ".join(f"{chave} = ?" for chave in campos)
        valores = list(campos.values()) + [transacao_id]
        conn.execute(f"UPDATE transacoes SET {colunas} WHERE id = ?", valores)


def remover_transacao(transacao_id: int) -> None:
    with get_conn() as conn:
        conn.execute("DELETE FROM transacoes WHERE id = ?", (transacao_id,))


def listar_transacoes(
    conta_id: int | None = None,
    categoria_id: int | None = None,
    data_inicio: str | None = None,
    data_fim: str | None = None,
    banco_id: int | None = None,
):
    query = """
        SELECT transacoes.*, contas.nome AS conta_nome, contas.tipo AS conta_tipo,
               bancos.nome AS banco_nome, categorias.nome AS categoria_nome,
               categorias.tipo AS categoria_tipo
        FROM transacoes
        JOIN contas ON contas.id = transacoes.conta_id
        JOIN bancos ON bancos.id = contas.banco_id
        LEFT JOIN categorias ON categorias.id = transacoes.categoria_id
        WHERE 1 = 1
    """
    params: list = []
    if conta_id:
        query += " AND transacoes.conta_id = ?"
        params.append(conta_id)
    if banco_id:
        query += " AND contas.banco_id = ?"
        params.append(banco_id)
    if categoria_id:
        query += " AND transacoes.categoria_id = ?"
        params.append(categoria_id)
    if data_inicio:
        query += " AND transacoes.data >= ?"
        params.append(data_inicio)
    if data_fim:
        query += " AND transacoes.data <= ?"
        params.append(data_fim)
    query += " ORDER BY transacoes.data DESC, transacoes.id DESC"
    with get_conn() as conn:
        return [dict(r) for r in conn.execute(query, params).fetchall()]
