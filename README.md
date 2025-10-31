# Vila-Caiz

Aplicação em linha de comandos e interface web para gerir o clube de futebol
Vila-Caiz.

## Funcionalidades

* Gestão de jogadores, treinadores e fisioterapeutas.
* Registo clínico com diagnósticos, planos de tratamento e disponibilidade dos atletas.
* Registo de equipas das camadas jovens e associação de jogadores.
* Gestão de sócios e do estado de quotas.
* Registo de receitas e despesas com resumo financeiro automático.
* Painel web com formulários e visualização dos dados do clube.
* Organização das operações por épocas com seleção dinâmica da época ativa.
* Autenticação com perfis configuráveis e personalização de identidade visual.

Os dados são armazenados em `data/club.json` num formato legível (JSON).

## Requisitos

* Python 3.11 ou superior.

## Utilização

Execute os comandos a partir da raiz do projeto:

```bash
python -m app --help
python -m app --version
```

Se não indicar subcomandos (`python -m app`) será aberto um modo interativo
para a consola, no qual pode escrever diretamente os comandos (`players list`,
`finance summary`, etc.). Utilize `help` para ver a ajuda e `exit`/`quit` para
terminar.

### Interface web

Instale as dependências e arranque o servidor Flask com:

```bash
pip install -r requirements.txt
python app.py --port 8000
```

Também pode usar diretamente `python app.py` (sem argumentos) para arrancar o
painel na porta predefinida (`5000`). Depois aceda a `http://localhost:8000`
ou `http://localhost:5000`, consoante a porta escolhida, para utilizar o painel
visual com formulários para todas as secções do clube (plantel, equipa técnica,
tratamentos clínicos, formação, sócios e finanças).

Para deploys em produção (por exemplo no Render ou em qualquer plataforma que
espere um servidor WSGI) utilize o Gunicorn apontando para a aplicação Flask
exposta em `app.web`:

```bash
gunicorn "app.web:app" --bind 0.0.0.0:8000
```

Substitua `8000` pela porta que o ambiente disponibilizar.

### Autenticação e perfis

O painel web requer autenticação. Na primeira execução será apresentada uma
etapa de configuração para criar o utilizador administrador inicial. Depois de
entrar com essa conta, utilize o menu **Administração → Utilizadores** para
criar logins adicionais e atribuir o cargo correto a cada pessoa:

* **Administrador** – acesso total ao painel, incluindo épocas, utilizadores e definições de design.
* **Treinador** – gestão do plantel, planificações de jogo, tratamentos e camadas jovens.
* **Fisioterapeuta** – registo e acompanhamento de tratamentos clínicos.
* **Financeiro** – gestão de receitas, despesas, sócios e relatórios financeiros.

Cada perfil visualiza apenas os menus e formulários que lhe dizem respeito.
Em **Administração → Design do Portal** pode ainda atualizar o nome exibido no
cabeçalho, carregar um logótipo personalizado e ajustar a paleta de cores sem
sair da aplicação.

### Exemplo de fluxo

```bash
python -m app players add "João Silva" "Médio" --squad senior --birthdate 1995-04-02 --shirt-number 8
python -m app coaches add "Carlos Sousa" "Treinador Principal"
python -m app youth add "Sub-17" "Sub-17" --coach-id 1
python -m app youth assign-player 1 1
python -m app finance add-revenue "Bilheteira jogo 1" 1540.50 Bilheteira 2024-09-01
python -m app finance summary
python -m app treatments add 1 "Entorse no tornozelo" "Fisioterapia 3x semana" --start-date 2024-11-20 --expected-return 2024-12-05
```

Consulte os subcomandos específicos com `python -m app <secção> --help`.

## Lançamentos

A release mais recente está identificada como **0.2.0** e encontra-se
documentada no [CHANGELOG](CHANGELOG.md). As notas da estreia (**0.1.0**) continuam disponíveis no mesmo ficheiro para referência histórica. Pode consultar a versão instalada em
qualquer momento com:

```bash
python -m app --version
```

Para instalar o pacote diretamente (por exemplo, numa pipeline CI/CD) execute:

```bash
pip install .
```

Fornecemos também pontos de entrada após a instalação:

```bash
vila-caiz --help      # CLI
vila-caiz-web --help  # Servidor web
```
