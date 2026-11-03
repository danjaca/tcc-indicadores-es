# Auditoria e consolidação do SAD de mortalidade do Espírito Santo

Entrega local de 30 de outubro de 2026. O código, a configuração, a interface e a redação foram alinhados ao objetivo central: desenvolver e verificar funcionalmente o SAD. Significância estatística não foi adotada como critério de sucesso. O prompt completo foi lido e arquivado em [PROMPT_MESTRE_SAD.md](PROMPT_MESTRE_SAD.md).

A [prévia local do SAD](http://localhost:8502/) está aberta; a [captura da janela de 64 meses](auditoria/telas/ajuste_64_meses.jpg) documenta a configuração testada.

O original do TCC e os nove arquivos de `dados/` foram preservados. Não houve nova extração de mortalidade, commit, push, implantação ou exclusão de pastas. Há um snapshot de segurança verificável fora do Desktop, identificado em [backup_e_dados.json](auditoria/backup_e_dados.json). Um segundo [backup integral do Desktop relacionado ao projeto](auditoria/backup_desktop.json) preserva as quatro pastas identificadas, três DOCX históricos, `tcc.zip` e suas cinco partes: 65.262 membros, com conteúdo de 58.556 arquivos regulares e destinos de dez links conferidos contra os originais, sem divergências.

## Entregas

| Pedido | Resultado e evidência |
|---|---|
| Arquitetura Python/Streamlit | Auditoria das camadas de interface, domínio, ETL, orquestração, experimentos, relatórios, dependências e workflow; [auditoria de ETL](AUDITORIA_ETL.md) |
| Monitoramento e Barros | Protocolo v3, verificação com a série publicada, distinção entre reprodução computacional e adaptação epidemiológica; [metodologia](MONITORAMENTO.md) |
| Fases parametrizáveis | Início mensal da fase II, referência anterior de 24/36/48/64 meses ou outra extensão, horizonte, EWMA/X, prazo de cautela e exclusões justificadas |
| Sensibilidade | 12 cenários estaduais, todos apresentados com a mesma fase II e os demais parâmetros fixos; [CSV](auditoria/resultados_v3/sensibilidade_fase1.csv) |
| Indicadores/gráficos/tabelas | Conciliação de todos os anos, testes das taxas, filtros, pirâmide/meios, interface, PDFs e saídas estatísticas |
| Datas operacionais na interface | Removidas datas de extração do cabeçalho, raça/cor e meios; mantidas cobertura, população provisória e cautela com atrasos/revisões. Datas técnicas continuam nos metadados e exportações para rastreabilidade |
| Texto acadêmico | [DOCX revisado](TCC_Daniel_Breda_Bigossi_Revisado.docx) e [auditoria acadêmica](AUDITORIA_ACADEMICA.md), com resultados recalculados, sensibilidade e limites metodológicos |
| ABNT e bibliografia | Estrutura, autor-data, fontes, títulos/listas/sumário revisados com orientação institucional vigente; pendências formais e limites bibliográficos explicitados na auditoria acadêmica |
| Atualização e Cloud | Preservados o lote isolado, validação pré-publicação, workflow e dependências separadas; instalação limpa e testes locais em Python 3.12.8 |
| Setup Codex/Git | `AGENTS.md` padronizado, prompt arquivado, skill pessoal `sad-tcc` validada, ambiente próprio e histórico Git real restaurado; [setup](SETUP_CODEX.md) |

## Diagnóstico e correções

A arquitetura recebida já separava `app.py` e `painel/vistas/` das regras em `dominio/`, com extração em `etl/`, atualização em `atualizar.py`, experimentos fora da abertura do painel e PDFs em `painel/relatorio.py`. Essa separação foi preservada. Não foi feita reescrita integral do sistema nem acrescentada dependência de produção.

A auditoria encontrou divergência entre TCC, configuração e resultados: o texto descrevia referência fixa de 48 meses e exclusões no indicador de mulheres, enquanto o código usava referências reduzidas por valores-p. Parâmetros como alfa e fração máxima de exclusões eram registrados sem serem efetivamente repassados ao cálculo. A fase I podia ser rotulada estável mesmo mantendo sinais, e uma contagem de linhas podia mascarar duplicatas e meses ausentes. O cenário de fase II vazia quebrava tabelas e exportações. Essas situações receberam correções e regressões automatizadas.

O protocolo principal agora mantém a referência definida antes da leitura dos sinais. A redução adaptativa 48 → 36 → 24 saiu do fluxo principal; a função legada permanece identificada como exploratória. Exclusões automáticas ficam desativadas. Pontos sinalizados são preservados e não passam a ser causas especiais comprovadas. Os sinais da leitura quadrimestral são omitidos em períodos parciais ou com meses no prazo de cautela.

O gate de publicação passou a comparar os complementos com toda a fato principal por padrão, a verificar datas mensais contra ano/mês, grades e cobertura declarada, e a recusar domínios/CIDs indevidos mesmo com contagem zero. Esses controles não corrigem nem apagam registros para satisfazer testes.

## Parametrização para profissionais da Vigilância

Em **Monitoramento estatístico → Protocolo e parâmetros**, o modo de referência lê `config.toml`. O modo **Ajuste pela vigilância** permite:

1. Selecionar o primeiro mês da fase II entre os meses disponíveis com histórico anterior mínimo.
2. Definir a extensão da fase I em 24, 36, 48, 64 ou outra quantidade de meses a partir de 24. O fim da fase I é automaticamente o mês anterior ao início da fase II. A falta de cobertura gera aviso e impede o cálculo; não encurta a referência nem preenche lacunas com zero.
3. Escolher o horizonte de monitoramento e ajustar λ, L do EWMA, largura do X e prazo operacional de cautela. A calibração de L é uma aproximação de ARL assintótica, devidamente identificada.
4. Registrar meses excluídos e a justificativa, ou ativar explicitamente a exclusão automática exploratória. Uma justificativa vazia bloqueia o cálculo de exclusões manuais feitas na tela.
5. Consultar todos os cenários em **Sensibilidade**, sem classificação de vencedor, e baixar CSV e JSON.

Alfa, defasagens diagnósticas, mínimo operacional e fração máxima de exclusões permanecem registrados no arquivo de protocolo e são efetivamente aplicados. Não foram multiplicadas opções de testes na tela. Alterações de arquivo com tipos ou intervalos inválidos são recusadas, inclusive `"false"` como texto e horizontes fracionários.

A exportação JSON contém entradas em formato AAAA-MM, indicador, municípios, sexo, território, janelas, parâmetros, justificativas, versões e hashes. Um teste reproduz exatamente μ0 e σ0 de um recorte regional usando esse JSON. O trecho TOML inclui todos os ajustes, exclusões vazias quando removidas e a justificativa. Atualize chaves existentes sem duplicar seções. O experimento CLI reproduz a aplicação estadual aos três indicadores; recortes por território/sexo devem usar os filtros do JSON.

## Justificativas estatísticas e limites

| Parâmetro | Referência principal | Justificativa e limite |
|---|---|---|
| Fase I | 48 meses | Quatro ciclos anuais, predefinidos; mesma extensão da aplicação de Barros. Não assegura média estável ou independência |
| Alternativa de 64 meses | Sensibilidade | Mais informação histórica e possível menor incerteza amostral, porém maior risco de misturar patamares e pesos desiguais dos meses do calendário. Não é recomendação atribuída a Barros |
| Janelas de 24/36 meses | Sensibilidade | Menor distância histórica, mas estimativas mais incertas e menor poder diagnóstico. Não são escolhidas para tornar testes não significativos |
| Fase II | 12 meses planejados | Horizonte operacional; somente os meses disponíveis são avaliados. Pode começar em qualquer mês no modo ajustável |
| EWMA | λ = 0,1; L = 2,701 | Retém memória de desvios persistentes. ARL aproximada de 370 refere-se a limites assintóticos sob normalidade, independência e parâmetros conhecidos |
| X e AM | X em 3σ; d2 = 1,128; D4 = 3,267 | Estima dispersão pela amplitude móvel de dois pontos; a adequação depende da referência. O LIC de uma taxa não fica negativo |
| Diagnósticos | α = 0,05; Ljung–Box em 1 e 12 | Nível nominal exploratório, sem ajuste de multiplicidade. Não seleciona janela nem decide exclusão |
| Exclusões | Automática desligada; teto 20% quando usadas | Regra operacional de proteção, não recomendação epidemiológica universal. O sinal exige investigação |
| Cautela | 60 dias após o fim do mês, em relação à atualização da fonte | Convenção operacional. Não certifica completude nem impede retificações posteriores |

A triagem territorial baseada em contagens, zeros e pressupostos é heurística. Não valida os limites normais em todos os municípios. A autocorrelação altera a variância da soma quadrimestral; acumulados sobrepostos e vários gráficos não constituem testes independentes. ARL não equivale a poder estatístico calculado para as séries reais, e não foi estimado poder para alegar equivalência ou ausência de alteração.

## Testes de hipóteses

| Diagnóstico | H0 | Alternativa e interpretação |
|---|---|---|
| Lilliefors | Distribuição normal com média/variância estimadas | Desvio da normalidade; não rejeição não confirma normalidade |
| Ljung–Box | Autocorrelações até a defasagem avaliada são nulas | Alguma autocorrelação não nula; não prova independência completa |
| Dickey–Fuller aumentado | Raiz unitária no modelo com constante e tendência | Rejeição da raiz unitária nessa especificação; não comprova média constante |
| Cox–Stuart | Ausência de tendência na comparação implementada | Tendência; aproximação normal em pares não empatados, conforme rotina reproduzida |
| Fisher | Ruído branco sem componente periódico dominante | Componente periódico; período dominante não é automaticamente sazonalidade anual |

A aproximação normal de Cox–Stuart requer cautela nas janelas curtas: 24 meses oferecem no máximo oito pares. Um ou sete pares crescentes em oito resultam em p aproximado de 0,0339, contra 0,0703125 na cauda binomial exata; a decisão a 5% pode diferir. O método reproduzido foi mantido e a limitação foi documentada, sem selecionar o cálculo pela significância.

Os CSV registram estatística, hipótese, valor-p, decisão e detalhes. Não rejeitar H0 é ausência de evidência suficiente nas condições do teste, não equivalência ou evidência de ausência. Isso não compromete o objetivo de desenvolvimento do SAD; limita a inferência substantiva possível. A leitura dos valores-p segue os pressupostos e o contexto, sem promover um resultado previamente desejado.

## Resultados reproduzidos

A execução local final usa o [manifesto v3](auditoria/resultados_v3/manifesto.json), Python 3.12.8 e `dataset.zip` SHA-256 `671c47f5bd4643ddf6802da7c6732b06de6631f6218ad313775b571a60951518`. Cobertura: 12 meses disponíveis por ano em 2016–2025 e janeiro–setembro de 2026; 724.464 linhas de óbitos, 78 municípios. Disponibilidade mensal não certifica completude dos registros. As camadas de raça/cor e meios concordaram com a fato nos 11 anos. A população de 2026 continua provisoriamente baseada em 2025.

A aplicação principal usa janeiro/2022–dezembro/2025, sem exclusões, e janeiro–dezembro/2026 como horizonte planejado. Há nove meses disponíveis na fase II; agosto e setembro estão no prazo operacional de cautela. Os resultados abaixo contam somente janeiro–julho, sem certificar a completude desses meses.

| Indicador | μ0 mensal por 100 mil | σ0 | Sinais fora do prazo de cautela |
|---|---:|---:|---|
| Suicídio | 0,627790 | 0,117529 | Nenhum X, AM ou EWMA |
| Homicídios de jovens | 4,871693 | 1,167301 | Dois EWMA de redução, em junho e julho |
| Homicídios de mulheres | 0,458741 | 0,181644 | Um AM em junho; referência já contém sinal de AM |

Cox–Stuart detecta tendência nos três indicadores na referência de 48 meses; Ljung–Box até 12 detecta autocorrelação nos jovens e no suicídio. Os sinais são exploratórios em relação a uma referência que não atende integralmente aos pressupostos. Não atribuem causalidade, efetividade de política ou mudança iniciada necessariamente em 2026.

A sensibilidade apresenta todos os 12 cenários. O número de sinais EWMA no suicídio é 1/1/0/0 para 24/36/48/64 meses; nos jovens, 1/2/2/3. Nos jovens, a referência de 64 também apresenta um sinal X. Nas mulheres há um sinal AM em 48/64 e nenhum em 24/36. A mudança de sinais demonstra dependência da referência; não autoriza escolher retrospectivamente a janela que favoreça uma conclusão.

A verificação da série publicada por Barros reproduziu os valores-p e a sequência de exclusões/sinais, com maior diferença absoluta de 0,0099047 entre os números comparados. Isso é compatível com a precisão de publicação, mas não constitui nova validação da fonte epidemiológica da autora. O indicador descrito por Barros é diferente da taxa populacional deste SAD; a relação está detalhada na auditoria acadêmica.

## Verificação executada

| Comando/controle | Resultado |
|---|---|
| Suíte recebida, antes das mudanças | 37 testes aprovados em Python 3.13.3 |
| Instalação limpa de `requirements-lock.txt` | Concluída em `.venv`, Python 3.12.8 |
| `python -m pip check` | Nenhuma dependência quebrada |
| `python -m pytest tests -q` final | 76 aprovados; 50 avisos de depreciação NumPy/Plotly, sem falhas; 25,02 s |
| `python -m etl.validar` | 11 anos, 724.464 linhas, 78 municípios; complementos conciliados |
| `python atualizar.py --planejar` | Sem consulta externa; janela móvel recente e publicação desativada |
| `python -m experimentos.monitoramento --saida docs/auditoria/resultados_v3 --figuras` | Concluído; CSV, manifesto, figuras, boletim e três relatórios PDF gerados |
| Hashes do manifesto | Conferidos contra o código efetivo e as entradas |
| Hashes dos nove arquivos de dados | Idênticos ao snapshot preservado |
| DOCX revisado após os ajustes solicitados | 60 páginas verificadas; 66 localizadores; oito equações, quatro figuras de arquitetura e oito imagens estatísticas; hashes em `auditoria/revisao_docx.json` |
| `git diff --check` | Sem erros de whitespace |
| Skill `sad-tcc` | Validador oficial de estrutura aprovado |

Os testes adicionais cobrem parâmetros efetivos, duplicatas/lacunas, série constante, exclusões e estabilidade, mínimos de janela, quadrimestres parciais/recentes, referência fixa sem seleção por p, sensibilidade, início intermediário da fase II, janela de 64 meses, falta de cobertura/população, fase II vazia, exportação/reprodução, validação de dados e denominadores das vistas. Logs estão em `docs/auditoria/testes_finais.log` e `experimento_v3.log`. A interface local também foi aberta em navegador e o modo de ajuste foi conferido visualmente.

## Arquivos alterados e acrescentados

Esta relação distingue alterações desta auditoria de diferenças já existentes entre a cópia recebida e a main.

- Estatística/configuração: `dominio/monitoramento.py`, `config.toml`, `experimentos/monitoramento.py`, `experimentos/figuras.py`.
- Interface/exportação: `app.py`, `painel/vistas/monitoramento.py`, `painel/vistas/meios.py`, `painel/relatorio.py`.
- Integridade de dados: `etl/validar.py`.
- Testes: `tests/test_monitoramento.py`; novos `tests/test_configuracao_monitoramento.py`, `tests/test_validacao.py`, `tests/test_dados_visuais.py`, `tests/test_parametrizacao_vigilancia.py`.
- Orientação e operação: `README.md`, `COMO_ATUALIZAR.md`, `AGENTS.md` (nome anteriormente em minúsculas), `.gitignore`, `docs/MONITORAMENTO.md`, aviso de contexto histórico em `docs/VERIFICACAO.md`.
- Novas entregas: `docs/RELATORIO_AUDITORIA.md`, `docs/SETUP_CODEX.md`, `docs/PROMPT_MESTRE_SAD.md`, auditorias ETL/acadêmica, DOCX revisado e evidências em `docs/auditoria/`.
- Setup pessoal: `/Users/danbreda/.codex/skills/sad-tcc/SKILL.md`; `.venv` próprio; `.git` com histórico remoto real, sem commit/push.
- Preservação: sete CSVs ausentes na cópia recebida recuperados da main, `resultados_monitoramento/manifesto_main_anterior.json` e `LEIA_ANTES.md`. Os resultados v2 recebidos foram preservados; os resultados v3 ficam em pasta separada.

`requirements.txt` e `requirements-lock.txt` já diferiam da main antes desta auditoria; não foram alterados nesta intervenção. A comparação detalhada está em `docs/auditoria/comparacao_main.json`; os arquivos modificados contra o snapshot local estão em `arquivos_modificados.json`.

## Contribuição para Engenharia de Produção

O artefato organiza aquisição, transformação, validação, cálculo e apresentação em um processo reproduzível. Oferece dados, modelos, filtros e comparação de cenários para apoiar decisões de investigação e acompanhamento da Vigilância. Essa combinação sustenta a caracterização de SAD analítico, com responsabilidade decisória humana. Não há modelo de otimização, prescrição automática ou validação de impacto sobre decisões reais.

A automação reduz etapas manuais necessárias no fluxo implementado, mas o trabalho não mediu tempo economizado nem avaliou adoção por profissionais. Esses benefícios potenciais não foram apresentados como resultados empíricos comprovados. A validação entregue é funcional e computacional, com limitações de adequação estatística explicitadas.

## Conferência bibliográfica

Foram confirmados metadados de 64 das 77 referências originais; as 13 pendências específicas estão identificadas. A revisão posterior acrescentou três referências verificadas, totalizando 80 registros na bibliografia revisada, sem resolver artificialmente as pendências anteriores. O [inventário original](auditoria/REFERENCIAS_VERIFICADAS.md) e o [complemento desta revisão](auditoria/REFERENCIAS_REVISAO_SENSIBILIDADE.md) registram os campos confirmados, as divergências corrigidas, as pendências e as fontes primárias. Os 35 DOIs do inventário original foram examinados por Crossref ou pela própria revista. A checagem de metadados não substitui a leitura integral das obras nem confirma automaticamente cada afirmação citada. Datas editoriais não demonstradas em páginas atualizadas continuamente e campos de edições/anais permanecem discriminados; bloqueio de acesso não foi tratado como inexistência.

## Estrutura final e pendências

A pasta operacional recomendada é a atual, com código, `dados/`, testes, configurações, documentação e entregas acadêmicas. `var/`, `.venv`, logs e caches ficam fora do Git; os backups permanecem fora do Desktop. O [inventário do Desktop](auditoria/INVENTARIO_DESKTOP.md) identifica projetos distintos, versões históricas e arquivos compactados, com recomendações por caminho. Nenhuma pasta foi apagada. O backup integral está verificado; retirar versões do Desktop ainda depende da autorização específica do usuário.

Na comparação com `dashboard_streamlit4`, os arquivos ZIP diferem, mas as tabelas de óbitos e população e os conteúdos descompactados de raça/cor e meios são idênticos. Não havia contagens mais recentes a integrar dessa cópia. O histórico Git preservado em `tcc/dashboard_streamlit` tem a mesma HEAD da main restaurada, sem commits adicionais nas referências e reflogs examinados. Os projetos de trauma e os materiais de apoio/Power BI não foram tratados como duplicatas descartáveis do SAD.

Permanecem: avaliação com profissionais, desempenho prospectivo dos alarmes, tratamento/modelos específicos de tendência e pequenas contagens, conferência institucional final da ABNT e dos elementos formais ausentes no original (banca/folha de aprovação/ficha catalográfica), publicação autorizada e verificação de um ciclo real do GitHub Actions/Streamlit Cloud. Selenium e nova extração não foram executados. Os avisos de depreciação não quebram esta instalação, mas deverão ser reavaliados ao atualizar NumPy/Plotly.

A normalização seguiu as edições informadas pela [Biblioteca da UFES](https://biblioteca.ufes.br/normalizacao). O alcance da verificação das referências é discriminado na auditoria acadêmica e no inventário bibliográfico; ausência de acesso a uma obra não foi tratada como confirmação. O DOCX é uma cópia revisada para avaliação do autor e orientadores, não uma certificação institucional.

## Revisão posterior solicitada pelo autor

Os objetivos receberam os ajustes de redação solicitados: inclusão de “um” antes de “monitoramento estatístico” no objetivo geral e retirada da duração de 48 meses do objetivo específico b. O resumo e o abstract passaram a destacar o SAD parametrizável, sem mencionar Barros e sem descrever as configurações ou o procedimento da sensibilidade; essa análise é citada como funcionalidade. Os detalhes permanecem na metodologia e nos resultados.

Foi corrigida a formatação divergente do parágrafo de sensibilidade, dos títulos, fontes e notas da seção 4.4. A origem dos dados da Tabela 5 foi explicitada, retirando a expressão “protocolo v3 sobre a base local” e separando Fonte e Nota. A Tabela 4 descreve cálculos teóricos, e sua fonte não é o SIM. As capturas completas das abas Evolução temporal, Distribuição territorial e Perfil demográfico foram acrescentadas à seção 4.5, divididas em partes; os originais e os filtros estão em [telas_tcc/capturas.json](auditoria/telas_tcc/capturas.json).

A sensibilidade recebeu fundamentação explícita no referencial teórico e descrição do procedimento na metodologia. Foram verificadas três referências adicionais: Steegen et al. (2016), NIST/SEMATECH (2012) e a cronologia oficial da OMS (2020). As evidências, os limites de aplicação das fontes e a distinção em relação às 77 referências originais constam em [REFERENCIAS_REVISAO_SENSIBILIDADE.md](auditoria/REFERENCIAS_REVISAO_SENSIBILIDADE.md).

Em resposta à questão sobre histórico anterior à pandemia, foram definidas antes da execução complementar três durações: 72, 96 e 120 meses, encerradas em dezembro de 2025. As nove linhas adicionais mantêm os filtros, a fase II e todos os demais parâmetros da execução principal; os 12 cenários anteriores foram reproduzidos, com maior diferença numérica de 2,22 × 10⁻¹⁶. Nenhuma janela foi escolhida por significância ou número de sinais. O [experimento complementar](auditoria/sensibilidade_janelas_longas/ANALISE.md) registra os valores e seu manifesto próprio. Essa extensão não altera a configuração principal nem o conjunto de quatro janelas disponível na interface.

| Indicador | Sinais X/AM/EWMA: 48 meses | 72 meses | 96 meses | 120 meses |
|---|---|---|---|---|
| Suicídio | 0/0/0 | 0/0/0 | 0/0/0 | 0/0/0 |
| Homicídios de jovens | 0/0/2 | 1/0/3 | 2/0/4 | 2/0/4 |
| Homicídios de mulheres | 0/1/0 | 0/1/0 | 0/1/0 | 0/0/0 |

Contagens de janeiro a julho de 2026, fora da convenção operacional de cautela, sem certificação de completude. As referências maiores de jovens e mulheres conservam sinais na fase I; a de 120 meses de suicídio também. Duração e composição temporal mudam juntas: as comparações não isolam o efeito da pandemia, não demonstram uma quebra causada pela COVID-19 e não identificam uma janela superior.

Não houve mudança do código de produção, dos dados ou dos parâmetros principais nesta revisão editorial. Os 76 testes da entrega anterior continuam como evidência daquele código; não foram repetidos por mudanças de texto e imagens. Foram feitos controles adicionais de reprodução numérica, integridade das capturas e renderização do DOCX. A versão anterior do documento foi preservada em `docs/auditoria/versoes/`.

## Substituição das capturas das três abas por texto

A pedido do autor, a revisão seguinte retirou da seção 4.5 as 16 partes das capturas de Evolução temporal, Distribuição territorial e Perfil demográfico, com suas legendas e fontes. As funcionalidades dessas três abas passaram a ser descritas em três parágrafos, conferidos com a implementação. O texto distingue taxas, contagens e proporções, esclarece que a pirâmide compara a distribuição dos óbitos e inclui o detalhamento dos meios por CID-10. As imagens de monitoramento e o restante do texto aprovado foram preservados; as remissões e a numeração das figuras posteriores foram ajustadas. As capturas originais continuam arquivadas, fora do corpo do TCC.

O Quadro 1 continua contendo os numeradores e recortes dos três indicadores. Um parágrafo complementar na seção 2.1 explicita as denominações de X85–Y09, Y22–Y24, Y35, Y87.1, Y89.0, X60–X84 e Y87.0, com as referências já utilizadas, sem alterar a definição dos indicadores.

A versão final possui 61 páginas, 13 figuras numeradas e 67 localizadores nas listas e no sumário. Todas as páginas da renderização final foram inspecionadas; a sequência dos números de página também foi conferida automaticamente. Não foram encontrados cortes, sobreposições ou glifos ausentes. As 21 imagens restantes preservam conteúdo e formatação; as oito equações, os 18 quadros/tabelas do DOCX, as 80 referências e os resultados estatísticos permanecem preservados. A versão anterior de 70 páginas foi guardada com hash verificável em `docs/auditoria/versoes/`. Esta revisão não altera código ou dados e não requer repetir os testes do sistema.

## Atualização do gerador PDF e das figuras do monitoramento

O gerador em `painel/relatorio.py` passou a exibir X, AM e EWMA no resumo do relatório. A série histórica completa e as tabelas foram preservadas na continuação, assim como os diagnósticos e as análises detalhadas. Cabeçalhos cortados foram corrigidos com largura e quebra de linha adequadas. O novo `tests/test_relatorio_resumo.py` cobre os três gráficos na capa, a fase II vazia, a manutenção do histórico e a geometria dos cabeçalhos no relatório de mulheres. `README.md` e `docs/MONITORAMENTO.md` apontam a reprodução para a nova saída, preservando a v3.

Validação final: `.venv/bin/python -m pytest -q` resultou em **79 passed, 77 warnings in 29.15s**. Os avisos são de depreciação, sem falha. A execução `.venv/bin/python -m experimentos.monitoramento --saida docs/auditoria/resultados_relatorio_x_am_ewma_final --figuras` terminou com os mesmos parâmetros e dados; os **16 CSVs são idênticos byte a byte** aos da v3. Os manifestos e hashes do código atual foram conferidos. Logs: `docs/auditoria/testes_relatorio_x_am_ewma_final.log` e `experimento_relatorio_x_am_ewma_final.log`; conferência: `revisao_relatorio_x_am_ewma.json`. Os três PDFs finais possuem sete páginas cada; todas as 21 páginas foram renderizadas e inspecionadas. A saída intermediária também foi preservada.

No TCC, a antiga Figura 7 foi retirada. A antiga Figura 8, agora Figura 7, mostra o resumo real com os três gráficos; as demais páginas de relatório do corpo e do Apêndice C usam a mesma execução atual. O documento ficou com 60 páginas, 12 figuras, 20 desenhos e 66 localizadores conferidos. Onze páginas alteradas foram reinspecionadas; as outras 49 preservam corpos de página idênticos à versão anterior integralmente inspecionada. Todas as posições do sumário/listas e os números de página foram conferidos no PDF. A versão de 61 páginas e seu manifesto foram guardados em `docs/auditoria/versoes/`. Nenhuma publicação, exclusão de dados ou nova extração foi executada. O grafo foi reconstruído, mas o gerador não apareceu no índice; os chamadores da interface, da CLI e dos testes foram verificados diretamente no código, sem tratar o resultado vazio como ausência de dependências.
