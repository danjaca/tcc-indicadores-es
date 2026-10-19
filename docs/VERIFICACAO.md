# Verificação de 11 de outubro de 2026

O projeto foi atualizado a partir do ZIP refatorado e do documento de introdução/referencial teórico fornecido. A pasta operacional única é `/Users/danbreda/Desktop/tcc`; o aplicativo e o ambiente Python ficam em `dashboard_streamlit`. As cópias antigas do Desktop foram removidas a pedido do usuário.

## Extração e validação

- Série completa 2016–2026 reextraída do SIM/TabNet SESA-ES. Revisão anunciada: 09/10/2026. Anos históricos com doze meses; 2026 com janeiro–setembro.
- 724.464 linhas da fato principal, 78 municípios, grade populacional validada. População 2026 provisoriamente baseada em 2025, sem projeção.
- Definição única `8d8be8e86012`: homicídios/agressões X85–Y09, Y22–Y24, Y35, Y87.1, Y89.0; suicídio X60–X84, Y87.0.
- Categorias completas consultadas por três dígitos e subcategorias isoladas consultadas separadamente, como união disjunta. Seis óbitos de homicídio de 2026 registrados sem quarto dígito foram incluídos. O filtro de Y87/Y89 continua específico.
- Complementos por raça/cor e CID/meio reextraídos; concordância exata com a base por ano, indicador, município, mês e sexo em toda a série. Raça/cor: 563.472 linhas; CID/meio: 6.486 linhas esparsas positivas.
- `python -m etl.validar --anos 2016 2017 2018 2019 2020 2021 2022 2023 2024 2025 2026`: aprovado. O lote só substituiu os arquivos publicados após essa validação.
- Consulta independente ao TabNet confirmou totais anuais, segundo quadrimestre, janeiro–agosto e referência municipal de 2024; reconsulta confirmou estabilidade. Evidência: `CONFERENCIA_REFERENCIAS.json`. Referências numéricas registradas em `tests/referencias.json`.
- Relatório da atualização e hash do dataset: `ATUALIZACAO_DADOS.json`. Evidências HTML originais, estado SQLite e contratos disponíveis localmente em `var/etl`.

## Monitoramento estatístico e interface

- u/u′ de Laney, EWMA, CUSUM bilateral com reinício após sinal, canal endêmico por quartis e funil municipal Poisson de 95%/99,8% implementados.
- Cinco a sete anos de referência separados dos anos de avaliação; comparação do mesmo período entre anos. Região de saúde combinada com o recorte municipal do painel.
- Funil compara contagens com quantis inteiros, evitando sinais falsos por arredondamento de taxas exatamente no limite.
- Anos nos eixos aparecem como inteiros. Canal endêmico exibido somente para quadrimestres completos ou acumulados previstos.
- Botão ⓘ Como ler abre diálogo com interpretação de filtros, taxas, referência histórica, limites, métodos e sinais. Abertura e texto verificados no navegador local.
- Experimento refeito com a base atual: 75 configurações de referência (525 observações históricas), fase I 2016–2022, fase II 2023–2026, 45.000 resultados simulados, 200 repetições e semente 20261011. Trinta recortes de 2026 indisponíveis correspondem ao terceiro quadrimestre e ao acumulado anual incompletos.
- SHA-256 do manifesto estatístico confere com `dados/dataset.zip` do checkout publicado localmente.
- `python -m pytest tests -q`: **34 aprovados**.

## Limites da verificação

A conciliação refere-se ao TabNet/SIM, e não a uma publicação fechada do PES. Não certifica completude epidemiológica. A validação operacional com profissionais da vigilância, revisão de períodos atípicos e calibração antes de adoção permanecem etapas de avaliação externa. Dados 2025/2026 sujeitos a revisão. O motor requests foi usado; Selenium e o próximo ciclo agendado do GitHub Actions não foram executados nesta atualização.
