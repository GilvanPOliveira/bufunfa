# Bufunfa — Controle Financeiro Pessoal Local

Aplicativo local (Streamlit + SQLite) para organizar todas as suas contas
bancárias, poupanças e investimentos em um só lugar, com totais cruzados
entre bancos, contas e categorias. Nenhum dado sai do seu computador.

## Funcionalidades

- Cadastro de quantos bancos e contas quiser (corrente, poupança, investimento, carteira, cartão de crédito).
- Lançamento manual de transações.
- Importação de extratos em PDF (Bradesco, Itaú, Santander, Banco do Brasil ou layout genérico), com revisão antes de confirmar.
- Categorização automática por regras de palavra-chave (editáveis), aplicável tanto no lançamento manual quanto na importação.
- Dashboard com patrimônio total, saldo por banco, por tipo de conta e despesas por categoria no mês.
- Deduplicação automática de transações repetidas (mesma conta, data, descrição e valor).

## Como rodar

```bash
python -m venv .venv
.venv\Scripts\activate        # Windows
pip install -r requirements.txt
streamlit run app.py
```

O navegador abrirá automaticamente em `http://localhost:8501`.

## Onde ficam os dados

Tudo é salvo em `data/bufunfa.db` (SQLite), criado automaticamente na
primeira execução. Basta fazer backup desse arquivo para preservar seu
histórico financeiro.

## Estrutura do projeto

```
app.py                      # Página inicial (dashboard)
db.py                       # Acesso a dados (SQLite)
parsers/                    # Extração de transações de PDFs bancários
pages/
  1_Bancos_e_Contas.py
  2_Transacoes.py
  3_Importar_PDF.py
  4_Categorias_e_Regras.py
data/                       # Banco de dados local (gerado automaticamente)
```

## Sobre a importação de PDF

Extratos bancários têm layouts diferentes entre bancos e podem mudar ao
longo do tempo. O parser tenta reconhecer linhas no formato
`DATA  DESCRIÇÃO  VALOR`, mas **sempre mostra uma tela de revisão** antes
de gravar qualquer coisa, permitindo corrigir data, descrição, valor ou
categoria, e desmarcar linhas que não devem ser importadas.

Se o PDF for uma imagem escaneada (sem texto selecionável), a extração
automática não funciona — nesse caso, lance as transações manualmente.
