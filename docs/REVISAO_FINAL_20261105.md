# Plano de revisão final do SAD e do TCC — 5 de novembro de 2026

Este registro relaciona as recomendações do plano de revisão de 18 páginas às alterações realizadas, às verificações disponíveis e aos limites que permanecem. O desenvolvimento e a verificação funcional do SAD continuam sendo a contribuição central. A obtenção de sinais ou de valores-p menores não é critério de sucesso.

O documento acadêmico final é [TCC_Daniel_Breda_Bigossi_Final_ABNT.docx](TCC_Daniel_Breda_Bigossi_Final_ABNT.docx). A cópia anterior foi preservada em `auditoria/revisao_20261105/TCC_antes_revisao_20261105.docx`, com hashes de entrada. A revisão do texto usa a voz do autor, as fontes originais e os resultados reproduzidos; o material de revisão externa não foi convertido em referência bibliográfica do TCC.

Este relatório distingue **implementação**, **verificação computacional**, **interpretação estatística** e **validação operacional**. Não declara adequação dos limites apenas porque o programa executou. A suíte global resultou em **104 passed, 113 warnings in 44.55s**. A cópia isolada dos 26 arquivos preparados para publicação e dos demais arquivos rastreados também passou nos 104 testes (113 avisos; 44,72 s). A versão acadêmica tem 71 páginas, 87 referências, 20 objetos de imagem (incluindo equações) e 22 tabelas de estrutura (incluindo listas e quadros). Os 75 localizadores das listas e do sumário foram conferidos contra o PDF final. O código funcional foi publicado e verificado no Streamlit, com remoto GitHub confirmado no commit `3bd6ca88a5f3fe2fbffee91a75179d097a42925e`. O download real do PDF ajustado confirmou oito páginas e X/AM/EWMA na capa; detalhes estão em [PUBLICACAO.md](PUBLICACAO.md).

## Evidências e localizadores

Os caminhos são relativos à raiz do projeto, salvo os links deste documento. As seções do TCC são usadas como localizadores estáveis, e os 75 números das listas/sumário também foram verificados contra a paginação final.

| ID | Evidência verificável | Alcance |
|---|---|---|
| E01 | `docs/auditoria/revisao_20261105/parecer_extraido.txt` e `tcc_extraido.txt` | Conteúdo integral do plano de revisão e da versão acadêmica de entrada, incluindo referências e apêndices. |
| E02 | `docs/auditoria/revisao_20261105/resultados_definitivos/`: `pressupostos.csv`, `parametros.csv`, `fase2.csv`, `ewma_fase1.csv`, `resumo_sinais.csv`, `quadrimestral.csv`, `manifesto.json` | Execução identificada do protocolo `graficos_controle_mensal_v4`, com parâmetros efetivos e hashes. Os resultados intermediários estão preservados em `resultados_estatisticos/`; os legados anteriores continuam em suas pastas próprias. |
| E03 | Na mesma pasta: `kpss_complementar.csv`, `diagnosticos_residuos_tendencia.csv`, `comparacao_poisson.csv`, `sensibilidade_calendario.csv`, `sensibilidade_fase1.csv`, `sensibilidade_janelas_longas.csv`, `resumo_complementar.csv` | Complementos exploratórios identificados, com fases e hipóteses explícitas; não substituem os limites oficiais nem selecionam uma janela. |
| E04 | `docs/auditoria/revisao_20261105/verificar_metodos.R`, `conferencia_R.log` e arquivos `conferencia_R*` em `resultados_estatisticos/` | Conferência independente com R base: `binom.test` para Cox e cálculo KPSS por regressão e Bartlett. Não foi executado o pacote tseries, que não estava instalado. |
| E05 | `docs/auditoria/revisao_20261105/qualidade_causas/consulta_20261105/`: `execucao.json`, HTMLs e seleções originais, `diagnostico_causas.csv`, `serie_mensal_grupos.csv`, `comparacao_periodos.csv`, `comparacao_mes_calendario.csv`, `manifesto_comparacoes.json` | Consulta auxiliar independente com 22 requisições e 4.446 linhas. A conciliação de Y22–Y24 comparou 342 células sem divergência. A fonte ainda declarava atualização de 09/10/2026; a data da consulta não foi tratada como nova atualização dos registros. |
| E06 | `dominio/monitoramento.py`, `experimentos/monitoramento.py`, `experimentos/figuras.py`, `painel/vistas/monitoramento.py`, `painel/relatorio.py`, `app.py` e `config.toml` | Cálculos, configuração, apresentação neutra de meses recentes, escala ajustada opcional, relatórios e ranking. |
| E07 | `etl/diagnostico_causas.py`, `etl/revisoes.py` e `atualizar.py` | Atualização auxiliar, catálogo com hashes e comparação entre snapshots; separação de indisponibilidade, mudança de definição, cobertura e revisão quantitativa. |
| E08 | `tests/test_monitoramento.py`, `test_revisao_calendario.py`, `test_revisao_vigilancia.py`, `test_diagnostico_causas.py`, `test_revisoes.py`, `test_parametrizacao_vigilancia.py`, `test_relatorio_resumo.py` e demais testes existentes | Regressões dos métodos, transformações, interface, relatórios e ETL. Resultado global: **104 passed, 113 warnings in 44.55s**; logs anteriores permanecem preservados. |
| E09 | `docs/auditoria/revisao_20261105/consolidar_tcc.py`, `alteracoes_textuais.json`, `plano_academico.md` e renderizações identificadas | Integração editorial, localização dos parágrafos alterados e conferência visual. Uma renderização intermediária não equivale à aprovação da versão final. |
| E10 | `docs/auditoria/revisao_20261105/plano_academico.md`, `adendo_referencias.md`, `ajustes_minimos_7_referencias.md` e metadados de APIs/páginas | Fontes primárias novas, correções de metadados e limites de acesso. Verificar metadados não equivale à leitura integral de todas as obras. |

## Matriz A — correções prioritárias de texto e interpretação

A numeração A01–A20 desdobra o item composto sobre sobreposição dos diagnósticos e multiplicidade em duas verificações, para tornar explícita a cobertura do plano.

| ID / prioridade | Recomendação | Status e localização | Evidência | Limite que permanece |
|---|---|---|---|---|
| A01 — Prioritário | Discutir sinais EWMA na fase I dos jovens. | **Aplicado.** TCC 4.2 e Apêndice D: aumento em março/abril de 2023 e redução em setembro/novembro de 2025; meses mantidos. | E02 `ewma_fase1.csv`; E03 `resumo_complementar.csv`; E09. | Sinais e diagnósticos não sustentam a interpretação convencional de uma referência sob controle. Ausência de pontos X/AM não supera tendência ou dependência. |
| A02 — Prioritário | Não interpretar a redução de 2026 como mudança adicional demonstrada. | **Aplicado.** TCC 4.3 distingue afastamento do histórico de continuidade da trajetória anterior; acrescenta comparação descritiva com 2025. | E03: jovens, média janeiro–julho/2025 de 4,003821 e janeiro–julho/2026 de 3,064653; ano completo/2025 de 4,007940. | A comparação não identifica causa, início de mudança, efeito de política ou completude das causas. |
| A03 — Prioritário | Discutir possível atraso de classificação e verificar causas inespecíficas. | **Aplicado e ampliado com consulta.** TCC 3.2, 4.3, POP A.1 e Apêndice D.4; painel/PDF mostram contagens auxiliares no recorte compatível. | E05; E07. | Aumento agregado de códigos não demonstra migração individual para homicídio/suicídio. R99 não identifica por si só causa externa. Y22–Y24 já integra homicídios e não é somado novamente. |
| A04 — Prioritário | Explicar efeito da estimação dos parâmetros no ARL. | **Aplicado.** TCC 2.5.6 e 4.4, guia e PDF distinguem desempenho nominal de efetivo; referência a Jensen et al. (2006). | E06; E09–E10. | Não foi estimada a distribuição do desempenho do SAD sob referências amostrais, revisões e dependência reais. |
| A05 — Prioritário | Explicitar poder limitado dos testes em referências curtas. | **Aplicado.** TCC 2.5.5 e interpretação da sensibilidade; não rejeição não confirma pressupostos. | E09; referência DeJong et al. e E10. | A potência depende do teste, tamanho, violação e estrutura temporal; não foi calculada uma curva de poder própria. |
| A06 — Recomendado | Informar probabilidade marginal do AM. | **Implementado e documentado.** TCC 2.5.3 e nota da Tabela 4; função `probabilidade_sinal_am`, guia e PDF. | E06: `2·Φ(−3,267·1,128/√2)=0,0091656503`; E08. | Aproximadamente 0,9166% sob normais independentes e σ conhecido. Amplitudes consecutivas são dependentes: seu inverso não é ARL nem taxa empírica do SAD. |
| A07 — Recomendado | Explicar valores quadrimestrais fora dos limites sem sinal. | **Implementado e aplicado.** Coluna `Situação da sinalização`: suspensão por período parcial ou consolidação; legenda e PDF explicam a regra. | E02 `quadrimestral.csv`; E06 `quadrimestres`; E08. | Os limites continuam visíveis e exploratórios. Suspensão da interpretação não significa observação dentro dos limites. |
| A08 — Recomendado | Explicar impossibilidade de sinal X inferior nas mulheres. | **Aplicado.** TCC 4.2 após Tabela 2; interpretação da baixa contagem e alternativas de contagem. | E02: LIC X truncado em zero; E09. | Taxa não negativa não cruza LIC=0. EWMA não resolve por si só baixa contagem, dependência ou desempenho não validado. |
| A09 — Recomendado | Separar tendência de autocorrelação/periodicidade na série bruta. | **Aplicado e complementado.** TCC 2.5.5 e Apêndice D.1; testes após retirada de tendência OLS em quadro separado. | E03 `diagnosticos_residuos_tendencia.csv`; E06 `avaliar_residuos_tendencia`. | Retirar tendência e testar na mesma amostra produz diagnósticos exploratórios; não demonstra resíduos brancos ou modelo validado. Fisher com período de 48 meses não prova ciclo anual. |
| A10 — Recomendado | Explicitar multiplicidade dos diagnósticos. | **Aplicado.** TCC 2.5.5 e notas da sensibilidade/PDF; seis linhas principais por indicador, sem ajuste automático. | E02 `pressupostos.csv`; E06; E09. | Sob 18 nulas verdadeiras e testes calibrados, a esperança é 0,9 rejeição; isso não é probabilidade de ao menos uma rejeição. Complementos ampliam a família. Não foi aplicado FDR ou outra correção. |
| A11 — Recomendado | Registrar efeito do número de dias e decisão sobre taxa oficial. | **Aplicado e implementado como opção ativa.** TCC 2.1 e D.3; botão `mon_calendario` no painel; helper idempotente preserva coluna oficial. | E03 `sensibilidade_calendario.csv`; E06 `ajustar_calendario`; E08. | `x* = x·30,4375/dias` é outra escala mensal. Contagens, população, taxas oficiais e quadrimestres oficiais são preservados; ajuste não é selecionado pelos sinais. |
| A12 — Recomendado | Explicar direção possível do viés populacional de 2026. | **Aplicado.** TCC 1.1 e limitações: denominador maior que o real subestima taxa; menor superestima. | E09; metadados populacionais em E07. | Não se presume queda/crescimento de um grupo em 2026 nem magnitude do viés sem denominador correspondente verificado. |
| A13 — Recomendado | Não interpretar sinais de meses recentes. | **Implementado e aplicado.** Triângulos interpretativos suprimidos; círculos/estado recente preservados; tabelas indicam espera. Valores e sinais brutos continuam nos arquivos de auditoria. | E02 `fase2.csv`; E06 UI/PDF/figuras; E08. | O prazo de 60 dias é cautela operacional, não certificação. Meses anteriores continuam sujeitos a revisão. |
| A14 — Recomendado | Tratar instabilidade do ranking municipal por taxa. | **Implementado.** Aba territorial permite mínimo de óbitos, padrão cinco; nota segue no PDF. Mapa e tabela completa conservam todos os municípios. | E06 `app.py`, campo `ranking_minimo`; E08. | Corte descritivo e configurável, sem garantia de precisão ou identificação de áreas de risco. Não foram implementados intervalos Poisson, funnel plot ou suavização bayesiana. |
| A15 — Recomendado | Explicar limites quadrimestrais sob autocorrelação. | **Aplicado.** TCC 3.4 explicita covariâncias positivas na soma e possível subestimação do desvio marginal pela AM. | E09; fórmula/hipóteses em E06. | O fator gaussiano `sqrt(1−ρ1)` não foi generalizado a qualquer distribuição. Não foram recalibrados os limites para dependência. |
| A16 — Recomendado | Informar incompatibilidades da referência no resumo/abstract. | **Aplicado.** Mantida a centralidade do SAD; inclusão curta sobre tendência/autocorrelação e limitação da leitura dos sinais. | E09 `alteracoes_textuais.json`, parágrafos de resumo/abstract. | O resumo não apresenta a ocorrência de sinais como sucesso do sistema nem antecipa eficácia epidemiológica. |
| A17 — Recomendado | Ampliar limitações e especificar trabalhos futuros. | **Aplicado.** TCC 5: tendência, EWMA na fase I, reclassificação plausível, parâmetros estimados, conjunto de gráficos e validação com profissionais/prospectiva. | E09. | Permanecem por desenvolver modelos de resíduos/contagem, nowcasting/completude e avaliação operacional efetiva. |
| A18 — Ajuste de redação | Harmonizar número de meses nas somas parciais. | **Aplicado.** TCC 3.4 e D; `m` corresponde aos meses efetivamente incluídos, não apenas 4/8/12. | E02 `quadrimestral.csv`; E06; E09. | Acumulado parcial não representa cobertura de todo o ano e não emite sinal interpretável. |
| A19 — Ajuste de redação | Acrescentar repertório de métodos para contagens/vigilância. | **Aplicado com fontes verificadas.** Referencial inclui Benneyan (1998), Unkel et al. (2012), Spiegelhalter (2005) e distingue seus contextos. | E09–E10. | Referências não equivalem a implementar ou validar métodos no SAD; vigilância infecciosa não é tratada como prova de desempenho para violência. |
| A20 — Ajuste de redação | Corrigir pontuação do objetivo específico d. | **Aplicado.** TCC 1.3.2 termina com ponto final, preservando objetivo de verificação funcional e vedação de seleção por significância. | E09. | Não se criou objetivo de comprovar redução da mortalidade ou utilidade junto a profissionais sem avaliação. |

## Matriz B — sete verificações complementares

| ID | Verificação | Status e localização | Evidência | Limite que permanece |
|---|---|---|---|---|
| B01 | Consultar Y10–Y34 e R99 em 2026 e na referência. | **Executada.** Série 2022–2026 por mesmos recortes populacionais; grupos sobrepostos e exclusivos separados; comparações de mesmos meses. TCC D.4/Tabela 10, painel e PDF. | E05: 22 requisições, 4.446 linhas, 342 células Y22–Y24 conciliadas. | Consulta transversal não demonstra reclassificação nem curva de completude. R99 agregado não permite isolar atestante IML. Camada auxiliar não altera o numerador oficial. |
| B02 | Guardar extrações e estimar completude. | **Infraestrutura implementada; estimação não realizada.** Catálogo de snapshots/hashes e comparação de versões integra o ciclo mensal. Preservação de lotes já existente foi mantida. | E07 `registrar_ciclo`, `inventario`, `comparar`; E08 `test_revisoes.py`. | Faltam sucessivas versões comparáveis e referência de encerramento para estimar curva de completude. Não há reconstrução de snapshots históricos ausentes nem garantia de retenção perpétua de artifacts remotos. |
| B03 | Comparar σAM ao desvio esperado sob Poisson. | **Executada.** TCC D.2/Tabela 8, UI/PDF e CSV. Populações anuais variáveis entram em `Var(x_t)=μ·100000/P_t`. | E03 `comparacao_poisson.csv`; E06 `comparar_poisson`. | Usa taxa oficial, inclusive se a entrada carregar escala ajustada. Não é teste formal de sobredispersão; não ajusta tendência/dependência/exposição por dias nem seleciona modelo. |
| B04 | KPSS e testes nos resíduos após tendência. | **Executada como complemento.** KPSS com constante+tendência e Bartlett curto, compatível com ADF; Lilliefors/Ljung–Box/Fisher nos resíduos OLS. | E03; E04; E06 `kpss` e `avaliar_residuos_tendencia`; TCC D.1/Tabela 7. | Valores-p KPSS interpolados e limitados à tabela [0,01; 0,10]; nas bordas, ≤0,01/≥0,10. Não rejeição não prova estacionariedade; resíduos não substituem monitoramento principal. |
| B05 | Cox–Stuart binomial exato. | **Implementado como diagnóstico principal.** Método registrado no protocolo v4 e manifestos. Aproximação normal explícita somente na reprodução histórica de Barros. | E02 `pressupostos.csv`; E04; E06; E08. | Mesmos pares em terços; empates removidos. Exatidão binomial pressupõe sinais independentes equiprováveis e não corrige dependência temporal. |
| B06 | Taxa ajustada pelo número de dias no monitoramento. | **Implementada e disponível na interface.** Ativação recalcula fases I/II na escala de 30,4375 dias; helper preserva oficial e impede duplicação do ajuste. | E06 `mon_calendario`, `ajustar_calendario`, `sensibilidade_calendario`; E08 `test_revisao_calendario.py`. | O padrão continua oficial. Quadrimestres vêm da análise oficial e seus próprios parâmetros são registrados; somas ajustadas não são apresentadas como indicadores oficiais. |
| B07 | Suprimir ou neutralizar sinais recentes. | **Implementada.** UI/PDF/figuras exibem recentes sem triângulos de aumento/redução; estado recente e dados brutos são preservados. | E06; E08; TCC 4.3, legendas e Apêndice C. | Neutralização de apresentação não remove valores, não certifica meses anteriores e não corrige atraso/classificação. |

## Matriz C — demais recomendações e aspectos conferidos

| ID / seção do plano | Item adicional | Status/localização e evidência | Limite |
|---|---|---|---|
| C01 — 2.1/1.3 | Preservar referência predefinida, sem seleção por p e sem exclusão automática. | **Preservado.** `config.toml`, `referencia_do_ano`, TCC 1.3/3.4; E02/E06. | 48 meses não garante estabilidade. 64 meses permanece cenário exploratório, não recomendação de Barros. |
| C02 — 2.1/3.5 | Separar funcionamento do SAD e adequação estatística. | **Preservado e reforçado.** TCC 3.5, resultados e conclusão; E09. | Testes de software e reprodução numérica não medem utilidade/impacto epidemiológico. |
| C03 — 2.1/3.3 | Calcular taxas após agregar numeradores e denominadores. | **Conferido e preservado.** `dominio/dados.py`, regras de idade/sexo/território; E06/E08. | Taxas territoriais não são somadas; população anual não é somada entre anos. |
| C04 — 3 | Substituir expressão defensiva sobre significância por contribuição funcional. | **Aplicado.** Resumo/abstract e objetivos permanecem centrados em SAD reproduzível e parametrizável; E09. | A contribuição não depende da ocorrência de sinais; não afirma eficácia na redução de óbitos. |
| C05 — 4.1/4.2 | Qualificar causas comuns/especiais e afastamentos improváveis. | **Aplicado.** TCC 1.1/1.2/2.5.1 e avisos UI/PDF condicionam interpretação ao modelo e à referência; E06/E09. | Referência incompatível com estabilidade descreve histórico; não certifica causas comuns. |
| C06 — 5.1 | Preservar Y22–Y24 e definição epidemiológica do PES. | **Conferido.** Fichas oficiais, `etl/definicao_cid.py`, TCC Quadro 1 e consulta auxiliar; E05/E09/E10. | Outros Y10–Y34 e R99 são auxiliares; não se infere causa jurídica/feminicídio ou se redefine indicador para alterar sinais. |
| C07 — 5.2 | Admitir referência histórica sem estado convencional de controle. | **Aplicado.** TCC 2.5.1/4.2; classificação temporal reforçada na UI/PDF; E06/E09. | Fase II exploratória não passa a ter desempenho nominal garantido. |
| C08 — 5.3/6.4 | Diferenciar Barros, adaptação epidemiológica e contribuição própria. | **Conferido e mantido.** TCC 2.5.2/3.5; `verificacao_barros2021.csv` e sinais; E02/E09. | Série publicada de óbitos/AIH×100 difere de SIM/população×100 mil. Reprodução não certifica origem dos dados da autora nem transferência de pressupostos. |
| C09 — 5.5 | Explicar sensibilidade do EWMA à autocorrelação. | **Aplicado.** Referencial e discussão com Lu/Reynolds; guia/PDF; E06/E09/E10. | Não se garante que a robustez à não normalidade cubra tendência, dependência e contagens escassas. Não foram ajustados limites para autocorrelação. |
| C10 — 5.6 | Não tratar Lilliefors p≈0,055 nas mulheres como prova de normalidade. | **Aplicado.** TCC 2.5.5/4.2 e ressalvas de baixa contagem/discretização; E02/E09. | Muitos valores repetidos e poucos óbitos limitam a interpretação do valor-p. |
| C11 — 5.7 | Explicar ARL como média até primeiro sinal e não periodicidade fixa. | **Aplicado.** TCC 2.5.6/4.4; ARL teórico separado de probabilidade marginal; E06/E09. | Não há alegação de um falso alarme a cada 370 meses, mediana igual à média ou desempenho empírico validado. |
| C12 — 5.7 | Explicitar nove gráficos simultâneos e dependência. | **Aplicado.** TCC e PDF especificam três indicadores×X/AM/EWMA; E06/E09. | Não foram multiplicadas probabilidades como se fossem independentes nem calculado ARL conjunto. Territórios e exploração aumentam o universo de análises. |
| C13 — 5.8 | Registrar configurações exploratórias e exportar histórico. | **Implementado.** `mon_historico`, assinatura e instante UTC; JSON com entradas/hashes; tabela histórica no PDF; E06/E08. | Histórico é desta sessão, temporário no Cloud. Exportação preserva o que foi registrado, não todas as análises de todos os acessos/usuários. |
| C14 — 6.1 | Distinguir fato de revisão, mecanismo plausível e evidência necessária. | **Aplicado.** TCC 3.2/4.3/D.4/POP e notas da camada auxiliar; E05/E09. | Uma consulta ou aumento de inespecíficos não demonstra a magnitude do atraso; não se afirma que todo R99 se tornará causa externa. |
| C15 — 6.2 | Informar versão/proveniência das populações 2022–2025. | **Conferido até o alcance dos metadados.** TCC 3.3; inventário registra anos, flags provisórias e hash de `d_populacao.csv`; E07/E09. | Metadados não fornecem release suficiente para afirmar “revisão editorial mais recente”. Não se fabrica essa confirmação. |
| C16 — 6.3 | Fortalecer compromisso metodológico da duração da referência. | **Aplicado.** TCC 2.5.7/3.4: precisão versus heterogeneidade histórica; cenários 24 a 120 meses explícitos; E03/E09. | Quantidade e composição variam juntas; resultados não isolam efeito da pandemia nem elegem janela superior. |
| C17 — 6.3 | Qualificar cortes territoriais de 5/10 óbitos e alternativas. | **Aplicado e preservado.** UI/TCC descrevem heurísticas; corte do ranking é separado da classificação de aplicabilidade; E06/E09. | Não são limiares validados nem substituem modelo para pequenas contagens. Poisson/funnel/Bayes são alternativas não implementadas como novos limites. |
| C18 — 7.1 | Apresentar contagens ao lado das taxas, sobretudo mulheres. | **Preservado/reforçado.** Tabelas de fase II, PDF e diagnóstico complementar; E02/E06/E09. | Cerca de 6,7 óbitos/mês na referência torna a discretização visível; não elimina incerteza. |
| C19 — 7.2 | Reconhecer legitimidade e limites da taxa contínua versus contagens. | **Aplicado.** TCC 4.2/conclusão e D.2 descrevem alternativa Poisson/binomial negativa com exposição e pressupostos; E03/E09. | A comparação Poisson é descritiva; não houve ajuste de modelo, teste de adequação completo ou escolha de distribuição. |
| C20 — 7.2 | Registrar possível relação entre variância e nível. | **Aplicado como limitação.** Discussão de contagens e mudança de patamar; E09. | Não se assume σ constante comprovado nem se conclui sobredispersão apenas da razão calculada. |
| C21 — 7.3 | Interpretar AM das mulheres com cautela. | **Aplicado.** TCC 4.3: passagem de 13 para 3 óbitos em maio/junho, baixa contagem, ausência de X/EWMA correspondente e frequência marginal nominal do AM; E02/E09. | Não identifica causa especial nem comprova mudança persistente. |
| C22 — 7.3/7.4 | Preservar resultados em todas as janelas, sem relato seletivo. | **Conferido.** Todos os cenários 24/36/48/64 e 72/96/120 estão nos CSVs e tabelas; E03. | A persistência dos sinais dos jovens não distingue continuação de tendência de mudança adicional. |
| C23 — 7.5 | Não calcular taxas raciais sem denominador ou tratar razão de sexos como razão de taxas. | **Conferido e preservado.** TCC 4.5, `app.py` e abas demográficas; E06/E09. | Frequências de óbitos descrevem distribuição dos registros; não estimam risco racial relativo. |
| C24 — 8/9 | Manter POP e comandos reprodutíveis, atualizar imagens de relatório. | **Aplicado e conferido.** Apêndices A–D, comandos com saída identificada, relatórios/figuras de E02 e arquivo anterior preservado; E09. | A inspeção e a verificação de localizadores usam a renderização de entrega; os arquivos anteriores e as renderizações intermediárias permanecem preservados. |
| C25 — 11.1 | Preparar defesa sem presumir perguntas da banca. | **Coberto pelo mapa abaixo.** Temas ligados a hipóteses, dados, artefato e limites; nomes/atos de aprovação não foram inventados. | Composição formal da banca, folha de aprovação e eventuais elementos institucionais dependem da confirmação do autor/instituição. |
| C26 — 2.1/6.2 | Manter validações da extração, cobertura e idempotência. | **Preservado.** ETL e testes conciliam estratos/totais, mantêm ausência distinta de zero e publicam só após validação; E07/E08. | Consistência com a fonte não assegura completude epidemiológica ou correção de cada causa básica. |

## Cobertura das perguntas de preparação para a defesa

As respostas devem usar os resultados arquivados e as ressalvas acima. O mapa não presume quais questões serão formuladas nem substitui a avaliação dos orientadores.

| Pergunta do plano | Cobertura e evidência |
|---|---|
| 1 — Redução pode decorrer de atraso? | A03/B01/B02/C14: mecanismo plausível, consulta auxiliar e limites da comparação; sem efeito demonstrado. |
| 2 — SIM representa toda a mortalidade real? | C26: validação extrativa não é garantia de completude ou causa correta. |
| 3 — Por que SIM e não SINAN? | C06/C08: fichas definem o numerador; distinção do indicador de Barros preservada. |
| 4 — Residência ou ocorrência? | C03/C06: município de residência alinha numerador e população; não identifica local da violência. |
| 5 — Indicador feminino mede feminicídio? | C06: não há classificação jurídica no indicador nem nova fonte policial integrada. |
| 6 — Por que Y22–Y24, mas não todos os indeterminados? | C06/B01: definição das fichas; demais códigos monitorados separadamente, sem soma duplicada. |
| 7 — Revisões populacionais? | A12/C15: direção condicional do viés e metadados/hashes; release mais recente não certificado. |
| 8 — Ajuste pelos dias do mês? | A11/B06: opção ativa e comparação transparente, preservando escala oficial e quadrimestres. |
| 9 — O que representa a média com tendência? | A01/C07: referência histórica exploratória, não processo sob controle certificado. |
| 10 — Sinal dos jovens não continua tendência? | A02: não separa essas hipóteses; comparações descritivas de mesmos meses arquivadas. |
| 11 — Por que 48 meses? | C01/C16: escolha prévia e compromisso metodológico, sem garantia de estabilidade. |
| 12 — Poder suficiente com 48? | A05/B04: limitações de potência e diagnósticos gráficos/complementares, sem confirmação por não rejeição. |
| 13 — ARL 370 é do SAD? | A04/A06/C11/C12: nominal individual, parâmetros estimados e conjunto dependente. |
| 14 — Por que EWMA além de X/AM? | C09: memória para afastamentos persistentes, com sensibilidade também a tendência/dependência. |
| 15 — Houve correção de multiplicidade? | A10: não; caráter diagnóstico/exploratório explicitado, sem seleção automática. |
| 16 — Por que não séries temporais/aprendizado de máquina? | C19/A17: SAD compara histórico; modelos são alternativas próprias e não foram falsamente declarados implementados. |
| 17 — Como se calcula ARL EWMA? | A04/C11: cadeia de Markov com limites assintóticos e parâmetros conhecidos, distinta dos transitórios usados no gráfico. |
| 18 — Normalidade com poucos óbitos? | A08/C10/C17/C18/C19: discretização, cortes heurísticos e alternativas de contagem. |
| 19 — Por que X não reduz nas mulheres? | A08: LIC=0, impossível excedência inferior para taxa não negativa. |
| 20 — Ranking privilegia municípios pequenos? | A14: filtro mínimo configurável e nota, sem inferência de risco ou suavização implícita. |
| 21 — Mapa identifica áreas de risco? | A14/C17: mapa descritivo, sem Moran, varredura ou modelo espacial. |
| 22 — Queda estadual vale para todos? | C03/C23: agregados não implicam uniformidade municipal nem inferência individual. |
| 23 — Utilidade sem avaliação com usuários? | C02: verificação funcional executável; utilidade na rotina e efeito decisório permanecem não avaliados. |
| 24 — Parametrização permite escolha seletiva? | C01/C13: protocolo prévio, cenários completos e histórico da sessão exportável; limite de outros acessos explícito. |
| 25 — Revisões mudam resultados sem registro? | B02/C15: snapshots, hashes e comparação; não se reconstrói histórico inexistente nem curva de completude. |
| 26 — Que decisão e quais critérios CRISP-DM? | C02/C26: priorização de conferência/investigação; integração, conciliação, testes e reprodução, sem decisão automática prescrita. |
| 27 — Contribuição para Engenharia de Produção? | C02/C03: processo informacional padronizado, rastreável e parametrizável; não se quantifica ganho de tempo ou impacto sem estudo. |

## Fontes, referências e normalização

O plano editorial e os adendos E10 distinguem leitura de conteúdo, confirmação de metadados, fontes substituídas e campos não identificados. Foram incorporadas fontes para estimação de parâmetros (Jensen et al.), autocorrelação/EWMA (Lu e Reynolds), modelos/resíduos (Montgomery e Mastrangelo), AM (Rigdon et al.), contagens/vigilância (Benneyan; Unkel et al.), comparações territoriais (Spiegelhalter), KPSS (Kwiatkowski et al.) e revisões/nowcasting (Höhle e an der Heiden), apenas no alcance sustentado pelos materiais consultados. Citar uma alternativa não significa tê-la implementado. A sugestão de controle de multiplicidade por Benjamini e Hochberg foi considerada como alternativa não adotada: o texto declara a ausência de correção e seus limites, sem apresentar o método como aplicado nem acrescentar uma referência sem uso específico.

As correções de metadados e atribuição incluem:

- Ano editorial do PES corrigido para 2023, distinto do período 2024–2027; fichas SESA e sufixos autor-data revistos conjuntamente.
- Dados nacionais do Atlas atribuídos ao livro primário; percentual de jovens explicitamente nacional. Definição do Atlas não foi equiparada automaticamente à das fichas do SAD.
- Data da página ABEPRO verificada pela API institucional; data editorial/atualização de painéis DATASUS separada do ano de acesso.
- Dados Populacionais substituídos pela subpágina oficial datada; isso não altera os anos dos denominadores usados no cálculo.
- Fonte genérica do SIM substituída pelo manual ministerial de 2024, que sustenta a afirmação correspondente. Os metadados eletrônicos DATASUS da CID-10 foram substituídos pela [fonte primária WHO, versão 2008](https://icd.who.int/browse10/2008/en), preservando a edição e sem deduzir local editorial não demonstrado; as fichas SESA continuam sustentando os grupos operacionais.
- Referência de Python substituída por documentação oficial datada da família 3.12, sem alterar a versão efetivamente executada. Streamlit identificado com data de copirraite quando pertinente, sem tratá-la como publicação demonstrada.
- Jesus et al. preserva autoria/evento/ano confirmados e assinala editora não identificada; não se deduz editora a partir de afiliação. A fonte redundante Wirth/Hipp não teve cabeçalho dos anais inventado; Chapman sustenta a descrição das fases do CRISP-DM.
- Título de Jensen conferido como *a review* e título de DeJong preservado conforme a editora. As datas de acesso novas não foram apresentadas como se tivessem ocorrido na análise anterior.

As convenções verificadas seguem NBR 6023:2025 (referências), NBR 14724:2024 (apresentação), NBR 10520:2023 (citações) e NBR 6028:2021 (resumos), conforme a conferência da Biblioteca UFES. Os procedimentos para local/editora desconhecidos, copirraite e datas inferidas são diferentes; não foram usados para fabricar metadados. Os detalhes e fontes primárias estão em E10. A revisão não declara leitura integral ou validação de todas as obras apenas por existir DOI ou catálogo.

## Resultados confirmados e pendências reais

Na referência oficial de 48 meses, Cox exato mantém indícios de tendência nos três indicadores; os valores-p são aproximadamente 0,00418 nos jovens e 0,02127 nos outros dois. Os sinais oficiais fora do prazo operacional permanecem: nenhum em suicídio, dois EWMA de redução nos jovens e um AM nas mulheres. O ajuste de calendário modifica as saídas dos jovens para um X e três EWMA, demonstrando dependência da escala; não substitui o protocolo oficial nem foi declarado superior. KPSS/resíduos, comparação Poisson, janelas longas e causas inespecíficas estão identificados como complementares.

A consulta auxiliar encontrou Y10–Y34 em janeiro–julho/2026 acima da média dos mesmos meses de 2022–2025 nos três recortes; os valores estão em E05/Tabela 10. Isso justifica investigação, sem demonstrar que os óbitos migraram para os numeradores ou explicar quanto do sinal decorre de atraso. A atualização auxiliar e a infraestrutura de snapshots permitem acompanhar próximas revisões, mas ainda não estimam completude.

Permanecem fora do que foi demonstrado nesta revisão:

- desempenho prospectivo/efetivo dos alarmes, probabilidade conjunta de sinais e variabilidade decorrente da estimação;
- curva de completude ou efeito quantitativo da reclassificação, dependentes de versões sucessivas comparáveis;
- limites novos de resíduos, modelos Poisson/binomial negativo com exposição, CUSUM de contagem, nowcasting e métodos espaciais/Bayes;
- avaliação da utilidade com profissionais, impacto sobre decisões ou mortalidade e mensuração do ganho de tempo;
- certificação de um release populacional mais recente quando os metadados não o identificam;
- data, membros adicionais e assinaturas da folha de aprovação, dependentes da confirmação do autor/instituição;
- execução de um novo ciclo completo de extração: o workflow foi preservado e está ativo, mas não foi disparado nesta revisão.

Os três relatórios PDF de monitoramento em `resultados_definitivos/relatorios/` foram renderizados independentemente com Poppler e tiveram suas 24 páginas inspecionadas visualmente. Cada capa contém X, AM e EWMA; tabelas, complementos e rodapés permanecem legíveis, sem sobreposição observada. As leituras quadrimestrais explicam a suspensão em períodos parciais ou com meses recentes. A comparação por calendário está identificada separadamente e mantém os parâmetros e quadrimestres oficiais nestes relatórios do protocolo principal. O DOCX foi renderizado e os ajustes visuais foram verificados em suas páginas, incluindo resumos, listas, fontes, notas, tabelas, equações, figuras e apêndices. Não se afirma verificação visual de todos os recortes possíveis do painel.

A implementação evita exclusões ou mudanças de janela para eliminar sinais. Os originais, resultados legados e evidências foram preservados. O código funcional foi publicado e conferido no Streamlit; o documento acadêmico entregue foi renderizado após os ajustes, com paginação e localizadores conferidos. A folha de aprovação continua preparada para data, membros ainda não confirmados e assinaturas.

## Versões do ambiente e conferências de entrega

O Quadro 2 e a seção 3.6 registram as versões verificadas com `importlib.metadata` e no `requirements-lock.txt`: Python 3.12.8; pandas 2.2.3; NumPy 2.5.3; Streamlit 1.63.0; Plotly 6.9.0; Matplotlib 3.11.2; Selenium 4.50.0; requests 2.34.2; BeautifulSoup 4.15.0; lxml 6.1.3; dbfread 2.0.7; geopandas 1.2.0; shapely 2.1.2; pytest 8.4.2. SQLite 3.49.1 foi conferido na biblioteca padrão. São versões do ambiente da validação; serviços hospedados não recebem número de versão inventado. O painel usa `requirements.txt`, e a atualização automatizada usa o lock. Não foi acrescentada dependência.

A execução final dos experimentos em `resultados_definitivos/` terminou com a maior diferença de 0,0099047 na reprodução numérica de Barros. Os 104 testes de entrega e os 104 da cópia isolada passaram. `pip check` não encontrou dependências quebradas; a validação da base conciliou os 11 anos, 78 municípios e 724.464 linhas, sem alterar o pacote principal. Os avisos de depreciação não foram tratados como falhas ou omitidos dos logs. A correção de formatação do ano no PDF mantém 2026 sem separador e preserva separadores em quantidades.

## Lista de arquivos modificados e entregáveis

Os 27 arquivos do projeto relacionados abaixo foram modificados ou acrescentados nesta revisão e publicados. Os documentos acadêmicos e as evidências detalhadas permanecem no acervo local.

| Arquivo | Alteração principal |
|---|---|
| `.github/workflows/atualizacao-mensal.yml` | Preservação dos snapshots, diferenças e consulta auxiliar nos artifacts; agendamento preservado. |
| `.gitignore` | PDFs acadêmicos locais excluídos da implantação, junto aos DOCX. |
| `app.py` | Mínimo de óbitos configurável no ranking por taxa, sem retirar municípios da tabela/mapa. |
| `atualizar.py` | Integração não destrutiva do diagnóstico auxiliar e do catálogo de versões. |
| `config.toml` | Protocolo v4 e Cox exato explícitos. |
| `dominio/dados.py` | Carregamento auxiliar com conferência de status, hashes e cobertura. |
| `dominio/monitoramento.py` | Cox exato, KPSS, resíduos, Poisson descritivo, ajuste idempotente de calendário e motivo de suspensão. |
| `etl/diagnostico_causas.py` | Consulta independente, conciliação, cobertura, atualização incremental e metadados auxiliares. |
| `etl/revisoes.py` | Catálogo de snapshots e diferenças entre versões com compatibilidade de definição/cobertura. |
| `experimentos/monitoramento.py` | Execução e arquivos complementares reproduzíveis, manifestos e relatórios atualizados. |
| `experimentos/figuras.py` | Representação neutra dos meses recentes. |
| `painel/vistas/monitoramento.py` | Opção ativa de calendário; diagnósticos, sensibilidade, dados auxiliares, histórico da sessão, JSON e apresentação dos sinais. |
| `painel/relatorio.py` | Três gráficos na capa; escalas e parâmetros separados; complementos; sinais suspensos; fluxo dos parágrafos e ano sem separador. |
| `dados/diagnostico_causas.csv` | 4.446 linhas agregadas da consulta auxiliar, sem substituir a base principal. |
| `dados/diagnostico_causas_meta.json` | Procedência, seleções, status, cobertura e hashes da consulta. |
| `tests/test_atualizacao.py` | Regressões da atualização auxiliar e do catálogo. |
| `tests/test_monitoramento.py` | Métodos e diagnósticos adicionais, exatidão e limites dos cálculos. |
| `tests/test_diagnostico_causas.py` | Cobertura, conciliação, atualização incremental e falhas da consulta auxiliar. |
| `tests/test_revisoes.py` | Catálogo e revisões, incluindo definição e cobertura incompatíveis. |
| `tests/test_revisao_calendario.py` | Calendário bissexto/idempotência, gráficos ativos, quadrimestre oficial, reprodução JSON e PDF de produção equivalente. |
| `tests/test_revisao_vigilancia.py` | Neutralização visual, sinais brutos preservados, razões de suspensão, histórico, ranking, qualidade e fluxo do PDF. |
| `README.md` | Recursos novos e acesso à revisão completa. |
| `COMO_ATUALIZAR.md` | Atualização auxiliar, snapshots, retenção e cuidado com meses recentes. |
| `docs/MONITORAMENTO.md` | Parâmetros, métodos, escalas, complementos, limites e reprodução. |
| `docs/RELATORIO_AUDITORIA.md` | Identificação do relatório anterior como histórico e ponte para esta revisão. |
| `docs/REVISAO_FINAL_20261105.md` | Matriz completa de recomendações, verificações, resultados, arquivos e pendências. |
| `docs/PUBLICACAO.md` | Registro separado da publicação e da verificação real no Streamlit. |

Entregáveis acadêmicos locais:

- `docs/TCC_Daniel_Breda_Bigossi_Final_ABNT.docx`: trabalho revisado, versões no Quadro 2 e em 3.6, referências e apêndices atualizados.
- `docs/TCC_Daniel_Breda_Bigossi_Final_ABNT.pdf`: renderização correspondente de 71 páginas, com 75 localizadores conferidos.
- `docs/auditoria/revisao_20261105/manifesto_entrega_academica.json`: hashes dos entregáveis, contagem de páginas e da estrutura.
- `docs/auditoria/revisao_20261105/consolidar_tcc.py`, `atualizar_localizadores.py` e `alteracoes_textuais.json`: integração e rastreabilidade editorial.
- `docs/auditoria/revisao_20261105/resultados_definitivos/`: tabelas, figuras, três relatórios e manifesto da execução final; os resultados anteriores foram preservados.
- `docs/auditoria/revisao_20261105/monitoramento_cloud_ajustado.pdf`, `verificacao_cloud_pdf.json` e `streamlit_publicado_ajuste_calendario.png`: evidência da aplicação publicada.

Os originais de entrada e a versão revisada anterior não foram sobrescritos. A modificação preexistente de `resultados_monitoramento/manifesto.json` permaneceu local e não entrou na publicação. Nenhum dado principal foi excluído ou alterado.

A inspeção final de paginação manteve a Tabela 5 completa em uma página e retirou a quebra manual antes de 4.5 que deixava duas linhas isoladas. O espaçamento dos apêndices A–C foi uniformizado em 1,5 e as alíneas receberam recuo. A renderização definitiva tem 71 páginas; os 75 localizadores foram verificados novamente após esses ajustes.
