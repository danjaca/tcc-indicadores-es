> Registro histórico preservado. As verificações abaixo pertencem às execuções e versões indicadas, não comprovam o estado atual. A auditoria vigente está em [RELATORIO_AUDITORIA.md](RELATORIO_AUDITORIA.md), com protocolo v3, dados identificados por hash e limites da verificação. Nesta auditoria nenhuma pasta foi removida ou alteração publicada.

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

## Monitoramento estatístico mensal e interface (24 de outubro de 2026)

- Métodos anteriores (u/u′, CUSUM, canal endêmico e funil) substituídos pelo protocolo mensal de Barros (2021): `dominio/monitoramento.py`, sem dependência de SciPy.
- Verificação com os dados publicados por Barros (2021): estatísticas descritivas, valores-p (Lilliefors 0,07903; Ljung–Box 0,857; Dickey–Fuller aumentado 0,04679; Cox–Stuart 0,6171; Fisher 0,8663829), limites das três iterações, exclusões (jun. e jul./2020) e sinais (X em mar./2021; AM em abr./2021; EWMA sem sinal) reproduzidos; maior diferença 0,0099, devida ao arredondamento da publicação.
- ARL do EWMA conferida com a tabela de Montgomery (λ = 0,1; L = 2,814 → 500).
- Base atualizada até 09/10/2026; agosto e setembro de 2026 em consolidação. Fase I: homicídio de jovens e de mulheres jan./2021–dez./2024; suicídio jan./2023–dez./2024 (regra 48 → 36 → 24 meses).
- Interface conferida em navegador local: todas as seções, granularidade estadual/regional/municipal, ajuste pela vigilância e downloads, sem exceções.
- `python -m pytest tests -q`: **34 aprovados**. Neste ambiente de conferência não havia `pyarrow`; para os testes de interface, `st.dataframe` foi substituído apenas no ambiente de teste. No ambiente do projeto (`requirements-lock.txt`) o `pyarrow` está incluído.

## Limites da verificação

A conciliação refere-se ao TabNet/SIM, e não a uma publicação fechada do PES. Não certifica completude epidemiológica. A avaliação do uso pela vigilância epidemiológica e a revisão anual do período de referência permanecem etapas posteriores à implantação. Dados 2025/2026 sujeitos a revisão. O motor requests foi usado; Selenium e o próximo ciclo agendado do GitHub Actions não foram executados nesta atualização.

## Fase II no ano corrente, regra da fase I e relatórios em PDF (29 de outubro de 2026)

- Protocolo `graficos_controle_mensal_v2`: fase I com os anos anteriores ao ano monitorado (48 → 36 → 24 meses
  terminando em dez./2025) e fase II com os meses de 2026. Referências adotadas: suicídio jan./2023–dez./2025;
  homicídios jan./2024–dez./2025 (mulheres com ressalva, Cox–Stuart p = 0,034). Nenhuma exclusão na fase I.
- Aplicação retrospectiva da regra (2020–2026, variação nos meses consolidados): sinais do EWMA em 8 de 21
  combinações de indicador e ano, com variação média absoluta de 22,3%, contra 4,8% nas 13 sem sinal.
- Iterações da fase I (`dominio.monitoramento.iteracao_fase1`) reproduzem as exclusões de Barros (2021)
  (jun./2020 pelos gráficos X e AM; jul./2020 pelo AM).
- Relatórios em PDF (`painel/relatorio.py`, matplotlib): monitoramento (resumo, fase I com testes e gráficos de cada
  iteração, fase II, quadrimestral, parâmetros e ARL) e um relatório por aba do painel.
- Comando único `pipeline_completo.py` (testes → extração/validação/publicação → monitoramento, figuras e PDFs →
  comparação com a base anterior → pacote `envio/resultados_*.zip`), testado neste ambiente no modo
  `--sem-extracao` (sem acesso à rede); a extração deve ser executada em ambiente com acesso ao TabNet.
- `python -m pytest tests -q`: **37 aprovados**.
