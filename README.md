# Vila-Caiz

Aplicação em linha de comandos para gerir o clube de futebol Vila-Caiz.

## Funcionalidades

* Gestão de jogadores, treinadores e fisioterapeutas.
* Registo de equipas das camadas jovens e associação de jogadores.
* Gestão de sócios e do estado de quotas.
* Registo de receitas e despesas com resumo financeiro automático.

Os dados são armazenados em `data/club.json` num formato legível (JSON).

## Requisitos

* Python 3.11 ou superior.

## Utilização

Execute os comandos a partir da raiz do projeto:

```bash
python -m app --help
```

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
