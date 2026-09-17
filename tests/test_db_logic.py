from pathlib import Path

import db


def test_atualizar_transacao_reclassifica_natureza(tmp_path):
    db.DB_PATH = tmp_path / "bufunfa.db"
    db.init_db()

    banco_id = db.criar_banco("Teste")
    conta_id = db.criar_conta(banco_id, "Conta", "Corrente", 0)
    transacao_id, inserida = db.inserir_transacao(
        conta_id,
        "2026-09-17",
        "PIX ENVIADO cliente",
        -100,
        None,
    )

    assert inserida is True
    assert transacao_id is not None

    db.atualizar_transacao(
        transacao_id,
        descricao="APLICACAO CDB/RDB",
        valor=-100,
    )

    transacao = db.listar_transacoes(conta_id)[0]
    assert transacao["natureza"] == "investimento"
