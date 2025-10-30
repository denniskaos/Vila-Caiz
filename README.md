# Vila-Caiz

Aplicação em linha de comandos e interface web para gerir o clube de futebol
Vila-Caiz.

## Funcionalidades

* Gestão de jogadores, treinadores e fisioterapeutas.
* Registo de equipas das camadas jovens e associação de jogadores.
* Gestão de sócios e do estado de quotas.
* Registo de receitas e despesas com resumo financeiro automático.
* Painel web com formulários e visualização dos dados do clube.

Os dados são armazenados em `data/club.json` num formato legível (JSON).

## Requisitos

* Python 3.11 ou superior.

## Utilização

Execute os comandos a partir da raiz do projeto:

```bash
python -m app --help
```

Também é possível iniciar um modo interativo simples com:

```bash
python app.py
```

No modo interativo escreva os mesmos comandos que usaria na linha de comandos
(`players list`, `finance summary`, etc.). Utilize `help` para ver a ajuda e
`exit`/`quit` para terminar.

### Interface web

Instale as dependências e arranque o servidor Flask com:

```bash
pip install -r requirements.txt
python -m app.web --port 8000
```

Depois aceda a `http://localhost:8000` para utilizar o painel visual com
formulários para todas as secções do clube (plantel, equipa técnica, saúde,
formação, sócios e finanças).

### Exemplo de fluxo

```bash
python -m app players add "João Silva" "Médio" --squad senior --birthdate 1995-04-02 --shirt-number 8
python -m app coaches add "Carlos Sousa" "Treinador Principal"
python -m app youth add "Sub-17" "Sub-17" --coach-id 1
python -m app youth assign-player 1 1
python -m app finance add-revenue "Bilheteira jogo 1" 1540.50 Bilheteira 2024-09-01
python -m app finance summary
```

Consulte os subcomandos específicos com `python -m app <secção> --help`.
