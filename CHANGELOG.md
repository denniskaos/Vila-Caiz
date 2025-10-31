# Changelog

Todas as alterações notáveis deste projeto serão documentadas neste ficheiro.

## [Unreleased]
### Adicionado
- Campo "Sócio desde" para registar a data de adesão, visível na gestão e no cartão imprimível.
- Sistema de autenticação com configuração inicial do administrador, criação manual de utilizadores e atribuição de cargos com salvaguarda do último administrador.
- Definições de identidade visual para atualizar cores, logótipo e nome do clube diretamente no painel.

## [0.2.0] - 2024-11-25
### Adicionado
- Gestão clínica de jogadores com registo de diagnósticos, planos de tratamento, datas de regresso e disponibilidade.
- Página web dedicada aos tratamentos com alertas visuais no plantel, planos de jogo e versão para impressão.
- Comandos `treatments` na CLI para criar, listar, atualizar e remover tratamentos por época.

## [0.1.0] - 2024-11-24
### Adicionado
- Primeira versão pública da aplicação Vila-Caiz com linha de comandos interativa e painel web.
- Gestão completa de jogadores, equipa técnica, fisioterapeutas, camadas jovens e sócios com suporte a épocas.
- Módulos financeiros para receitas, despesas, quotas de sócios e propinas/kit de formação com sincronização automática.
- Upload de fotografias, seleção de época ativa e interface em amarelo/preto alinhada com o clube.

### Infraestrutura
- Publicação do pacote Python via `pyproject.toml`, entrada de consola (`vila-caiz`) e servidor web (`vila-caiz-web`).
- Indicador de versão (`0.1.0`) exposto na biblioteca e acessível através da flag `--version` na CLI.
