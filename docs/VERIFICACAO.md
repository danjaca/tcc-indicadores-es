# Revisão de 11 de outubro de 2026 — numeradores conforme as fichas do PES-ES

- Definição de CID centralizada em `etl/definicao_cid.py`: homicídios X85–Y09, Y22–Y24, Y35, Y87.1 e Y89.0; suicídio X60–X84 e Y87.0 (fichas 1.8.15, 1.8.16 e 1.8.17).
- Seleção no TabNet pelo campo de subcategorias do capítulo XX; contrato versão 2.0; pipeline 1.2.0. Formulário real salvo pelo projeto confere todas as subcategorias exigidas (homicídio: 281 valores; suicídio: 251).
- Novos controles: equivalência subcategorias × categorias, bloqueio de série com definições misturadas (incorporação e validação) e definição registrada por ano na base e nos complementos.
- Executados neste ambiente, sem rede: testes de `tests/test_definicao_cid.py` (6) e `tests/test_pipeline.py` (8), testes numéricos de `tests/test_dashboard.py` (4) com a base atual, `python -m etl.validar` com a base atual, simulações de incorporação parcial (recusada) e completa (aceita) e de validação com séries misturadas (recusada).
- Não executados neste ambiente: testes que dependem de Streamlit e pytest (interface do painel, `tests/test_atualizacao.py`) e a extração real, por falta de acesso à rede. Rodar `python -m pytest tests -q` localmente antes do push.
- Os dados de `dados/` não foram alterados: continuam com a definição anterior até o reprocessamento integral (ver README).
- A aba de aprendizado de máquina ficou desligada por configuração; nenhum arquivo de experimento foi apagado.

# Verificação da entrega de 2 de outubro de 2026

- 15 testes automatizados locais aprovados: cálculos, filtros da interface, integridade, idempotência, rollback, calendário e preservação dos dados publicados quando a extração falha.
- Pacote de dados validado: 718.848 linhas da fato, 78 municípios, anos 2016 a 2026; cobertura de 2026 até agosto.
- Complementos de 2026 conferidos por município, mês, sexo e indicador.
- Formulário público do TabNet consultado: contrato de 2026 construído com os 78 municípios. Revisão anunciada pela fonte: 09/09/2026. O formulário anuncia 2006 a 2026; dois anos é a janela de reprocessamento escolhida, não o total de anos listados.
- Os bytes dos dados publicados foram preservados; esta entrega não representa uma nova extração epidemiológica.
- O processamento mensal completo contra SIM, POPSVS e IBGE não foi executado nesta revisão. O modo Selenium e o workflow hospedado precisam de validação operacional.
- Não houve push ao GitHub nem alteração confirmada do aplicativo hospedado.

A implantação em produção permanece pendente de validação integral da rotina e acesso ao repositório. Uma falha impede o commit de novos dados. A revisão do código e os testes locais não substituem o primeiro ciclo supervisionado em ambiente de execução.
