# Changelog

Todas as alterações notáveis deste projeto serão documentadas neste ficheiro.

## [0.1.0] - 2024-11-24
### Adicionado
- Primeira versão pública da aplicação Vila-Caiz com linha de comandos interativa e painel web.
- Gestão completa de jogadores, equipa técnica, fisioterapeutas, camadas jovens e sócios com suporte a épocas.
- Módulos financeiros para receitas, despesas, quotas de sócios e propinas/kit de formação com sincronização automática.
- Upload de fotografias, seleção de época ativa e interface em amarelo/preto alinhada com o clube.

### Infraestrutura
- Publicação do pacote Python via `pyproject.toml`, entrada de consola (`vila-caiz`) e servidor web (`vila-caiz-web`).
- Indicador de versão (`0.1.0`) exposto na biblioteca e acessível através da flag `--version` na CLI.
