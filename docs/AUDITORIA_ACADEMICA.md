# Auditoria acadêmica e revisão do TCC

A revisão preserva o desenvolvimento e a verificação funcional do SAD como contribuição central. O documento revisado é `docs/TCC_Daniel_Breda_Bigossi_Revisado.docx`; o original em Downloads e a cópia original na raiz do projeto foram preservados. A leitura cobriu os 327 parágrafos acessíveis do corpo original, 16 tabelas, os elementos pré-textuais, as referências e os apêndices. As figuras e as oito equações foram examinadas também na renderização.

## Problemas corrigidos

- O original descrevia fase I fixa de 48 meses, enquanto o projeto continha referências escolhidas pela regra 48 → 36 → 24. A revisão usa o protocolo v3: 48 meses definidos antes de examinar valores-p e sinais; exclusão automática desativada; fase II parametrizável.
- O resumo e as conclusões destacavam reduções em agosto e setembro de 2026, meses próximos da atualização da fonte. Agora distinguem os resultados provisórios dos sinais dos meses fora do intervalo operacional de cautela.
- As duas exclusões de homicídios de mulheres descritas no original deixaram de fazer parte do protocolo principal. Todos os 48 meses são mantidos e o ponto de amplitude móvel sinalizado na referência é explicitado como limitação.
- A não rejeição de normalidade e de autocorrelação era apresentada como confirmação dos pressupostos. A redação diferencia ausência de evidência, hipótese nula e adequação substantiva da referência.
- A hipótese do Ljung–Box foi corrigida para ausência de autocorrelações até as defasagens especificadas. O teste não demonstra independência completa.
- Fisher é descrito como diagnóstico de componente periódico dominante sob ruído branco. Um período dominante de 48 meses não comprova sazonalidade anual.
- O Dickey–Fuller aumentado com constante e tendência não comprova média constante. A não rejeição de raiz unitária não é confirmação de sua presença.
- Cox–Stuart preserva a aproximação normal sem correção de continuidade aplicada ao primeiro e ao último terço, para reprodução do método. A janela de 24 meses contém no máximo oito pares; seus valores-p podem diferir do teste binomial exato. Essa limitação de pequena amostra foi explicitada sem substituir os resultados ou selecionar configurações.
- A ARL foi qualificada como referência teórica com parâmetros conhecidos. O cálculo assintótico do EWMA não valida empiricamente o gráfico com limites transitórios e parâmetros estimados.
- Os limites da soma quadrimestral exigem ausência de covariância entre meses. A sobreposição dos acumulados e a multiplicidade de indicadores/gráficos não foram tratadas como comparações independentes.
- O prazo de 60 dias deixou de ser descrito como prazo individual de registro ou garantia de fechamento do SIM. É uma convenção operacional de cautela; revisões posteriores continuam possíveis.
- Resumo, abstract, objetivos, modelagem, avaliação, resultados, conclusões e procedimento operacional foram alinhados. O parágrafo deslocado sobre a taxa, que estava oculto em branco e com fonte de 1 ponto sob CRISP-DM, foi removido da cópia revisada.
- As tabelas numéricas foram atualizadas diretamente dos CSV da execução v3. Foi acrescentada uma tabela de sensibilidade com os 12 cenários. Figuras e reproduções de relatórios incompatíveis foram substituídas por saídas da mesma execução.
- Listas de figuras, quadros, tabelas e sumário foram reconstruídos a partir dos títulos existentes; havia entradas de seções ausentes e numerações antigas. O cache automático antigo do sumário foi removido para não reaparecer sobre a lista atualizada.

## Relação com Barros 2021

A fonte primária foi consultada integralmente: [registro da UFU](https://repositorio.ufu.br/handle/123456789/33585) e [PDF oficial](https://repositorio.ufu.br/bitstreams/70d5f272-f723-4f2c-b893-00c9142bba50/download). O PDF contém 67 páginas. A metodologia apresenta 48 meses na fase I, seis meses na fase II, exclusões de junho e julho de 2020 e os gráficos X–AM e EWMA. Os apêndices utilizam λ = 0,1 e L = 2,701, apesar do arredondamento para 2,7 na exposição.

Há uma distinção epidemiológica material: na página impressa 17 (página 37 do PDF), Barros define a taxa como óbitos por autorizações de internação hospitalar aprovadas, multiplicada por 100, e atribui os dados ao SINAN. O SAD usa óbitos do SIM e população residente, multiplicados por 100 mil. A revisão declara essa diferença e limita a transferência à estrutura dos gráficos e à verificação numérica da série publicada. A reprodução de seus números não valida a origem ou a definição epidemiológica da série da autora.

Barros não fundamenta a regra adaptativa 48 → 36 → 24 nem uma recomendação específica de 64 meses. A referência de 64 meses é identificada como exploratória: ela preserva mais histórico, mas dá pesos diferentes aos meses do calendário e pode misturar patamares. Não é apresentada como configuração superior ou recomendação bibliográfica.

## Parâmetros e resultados confirmados na execução local

Fonte: `docs/auditoria/resultados_v3/manifesto.json`, `parametros.csv`, `pressupostos.csv`, `fase2.csv` e `sensibilidade_fase1.csv`. Base analítica identificada pelo SHA-256 `671c47f5bd4643ddf6802da7c6732b06de6631f6218ad313775b571a60951518`.

| Parâmetro | Configuração principal | Interpretação |
|---|---|---|
| Fase I | 48 meses, janeiro de 2022 a dezembro de 2025 | Referência definida antes dos testes; não garante estabilidade |
| Fase II | 12 meses previstos em 2026; nove disponíveis | O horizonte configurado não cria meses ausentes |
| Exclusão automática | Desativada | Pontos sinalizados permanecem para investigação |
| X | 3σ | Referência nominal normal independente com parâmetros conhecidos |
| EWMA | λ = 0,1; L = 2,701 | Combinação usada para comparação; ARL assintótica aproximada de 370 |
| Testes | α = 0,05 | Diagnósticos exploratórios sem correção de multiplicidade |
| Meses recentes | 60 dias após fim do mês, relativos à atualização da fonte | Convenção operacional; não certifica completude |
| Sensibilidade | 24, 36, 48 e 64 meses, com mesmo fim de referência | Mantém os demais parâmetros; não escolhe o cenário pelos sinais |

| Indicador | μ da referência | σ por AM/1,128 | Sinais de janeiro a julho de 2026 |
|---|---:|---:|---|
| Homicídios de jovens | 4,871693 | 1,167301 | EWMA de redução em junho e julho |
| Homicídios de mulheres | 0,458741 | 0,181644 | AM em junho; referência apresenta sinal AM em abril de 2024 |
| Suicídio | 0,627790 | 0,117529 | Nenhum sinal X, AM ou EWMA |

As taxas são mensais por 100 mil. A referência de 48 meses apresenta tendência nos três indicadores e autocorrelação detectável até 12 defasagens nos jovens e no suicídio. Portanto, os sinais são exploratórios em relação a essa referência e não atribuem causalidade. Agosto e setembro são recentes segundo a convenção adotada e têm sinais provisórios.

A sensibilidade produz diferentes números de sinais: no suicídio, EWMA sinaliza um mês em referências de 24/36 meses e nenhum em 48/64; nos jovens, um, dois, dois e três, respectivamente; nas mulheres, AM sinaliza em 48/64. Nenhum desses cenários foi selecionado para obter significância. A variação entre cenários não prova equivalência ou superioridade.

## Normalização e fontes verificadas

A [Biblioteca da UFES](https://biblioteca.ufes.br/normalizacao) informa as edições NBR 14724:2024, NBR 10520:2023 e NBR 6023:2025, além da NBR 6028:2021, NBR 6027:2012 e NBR 6024:2012. A revisão conserva a estrutura acadêmica, papel A4, margens de 3 cm à esquerda e acima e 2 cm à direita e abaixo, títulos hierárquicos, referências autor-data, equações e fontes das ilustrações. Resumo e abstract foram concentrados no objetivo, método, contribuição e limitações. As seis tabelas numéricas da versão atual adotam linhas horizontais de abertura, cabeçalho e fechamento, sem grades verticais; os quadros conservam a grade. Os cabeçalhos foram alinhados para evitar espaçamentos artificiais. As referências foram uniformizadas à esquerda.

O [art. 34 da Portaria 116/2009, no Ministério da Saúde](https://bvsms.saude.gov.br/bvs/saudelegis/svs/2009/prt0116_11_02_2009.html), foi consultado para corrigir a interpretação do prazo de transferência. Não foi realizada certificação jurídica de vigência de todo o regulamento.

A referência [Atlas da Violência 2026 do Ipea](https://repositorio.ipea.gov.br/handle/11058/20521) foi confirmada no PDF oficial, inclusive os 42.590 homicídios, taxa nacional de 20,1 em 2024, taxa de 26,0 no Espírito Santo e participação de jovens de 46,5%. A [publicação da OMS de 2021](https://www.who.int/publications/i/item/9789240026643) sustenta os números globais de suicídio de 2019, mantidos como contexto histórico.

A auditoria complementar examinou os 77 registros da bibliografia original: 64 tiveram metadados confirmados no escopo descrito e 13 mantêm campos pendentes. Quatro links do Planalto estavam bloqueados ou indisponíveis e foram conferidos em fontes oficiais alternativas do Senado e da Câmara. Foram consultados os 35 DOI, combinando Crossref e editoras. Bloqueio de acesso não significa inexistência da obra. Foram corrigidos o título de DeJong et al. (1992), que emprega o singular “unit root test”, e o número 366a do artigo de Dickey e Fuller (1979), ambos confirmados nas editoras. As demais referências preexistentes foram preservadas sem criar novos autores, títulos ou resultados. O detalhamento está em `docs/auditoria/REFERENCIAS_VERIFICADAS.csv` e em [REFERENCIAS_VERIFICADAS.md](auditoria/REFERENCIAS_VERIFICADAS.md). A auditoria não certifica leitura integral de todas as obras citadas, nem conformidade de cada registro com o exemplar físico correspondente. Essa conferência bibliográfica final permanece necessária, especialmente para livros, anais e páginas que mudam ao longo do tempo.

## Revisão posterior solicitada pelo autor que originou a versão de 70 páginas

A versão entregue anteriormente foi preservada em `docs/auditoria/versoes/TCC_Daniel_Breda_Bigossi_Revisado_entregue_20261030_140106.docx`, com SHA-256 `d8cfebc109f410871378edacd41e301ca0cea69ddf8df800816c24e611ceea9a`. A revisão posterior contém os seguintes ajustes:

- O objetivo geral passou a empregar “disponibilize um monitoramento estatístico”. O objetivo específico 1.3.2b mantém a parametrização e a sensibilidade, sem fixar uma duração de referência no enunciado do objetivo.
- Resumo e abstract foram reescritos com foco no desenvolvimento e na verificação funcional do SAD parametrizável. Não contêm citação a Barros, durações de janelas ou descrição do procedimento da sensibilidade; mencionam a análise como recurso do sistema.
- A seção 4.4 recebeu formatação coerente: corpo em Times New Roman 12, entrelinha 1,5 e recuo inicial de 1,25 cm; títulos de tabelas, fontes, notas e células em Times New Roman 10, entrelinha simples e sem recuo inicial. As fontes e as notas das Tabelas 4 e 5 foram separadas. A Tabela 4 identifica cálculos teóricos, com σ₀ conhecido; a Tabela 5 atribui corretamente os dados ao SIM disponibilizado pela SESA/ES e às estimativas populacionais do Ministério da Saúde.
- A subseção 2.5.7 fundamenta a representatividade da referência histórica e a transparência na comparação de escolhas plausíveis. Foram acrescentadas três referências verificadas: NIST/SEMATECH (2012), Steegen et al. (2016) e a cronologia oficial da OMS (2020). A documentação das fontes está em [REFERENCIAS_REVISAO_SENSIBILIDADE.md](auditoria/REFERENCIAS_REVISAO_SENSIBILIDADE.md). A comparação do SAD é restrita à duração e à composição da referência; não corresponde a um multiverso completo.
- A metodologia distingue a comparação inicial de 24, 36, 48 e 64 meses da análise complementar de 72, 96 e 120 meses. As três durações complementares foram definidas nesta revisão antes da execução dos novos cenários, em resposta à questão sobre o histórico anterior; não representam pré-registro do TCC original. A fase II e os demais parâmetros permanecem iguais, com recálculo dos parâmetros e limites da referência. Não houve exclusão de 2020 nem seleção posterior por valores-p ou sinais.
- A Tabela 6 acrescenta os nove cenários complementares, todos encerrados em dezembro de 2025: 72 meses desde janeiro de 2020, 96 desde janeiro de 2018 e 120 desde janeiro de 2016. Nos sete meses de janeiro a julho de 2026 fora do prazo operacional de cautela, o suicídio não apresentou sinais X, AM ou EWMA nessas três referências. Os jovens apresentaram, respectivamente, 1/0/3, 2/0/4 e 2/0/4 sinais X/AM/EWMA; as mulheres, 0/1/0, 0/1/0 e 0/0/0. Esses resultados não demonstram que uma janela seja superior. As referências longas dos jovens e das mulheres apresentam instabilidade na fase I; no suicídio, a referência de 120 meses também apresenta sinal X–AM. Duração e composição histórica mudam simultaneamente, portanto a comparação não isola o efeito da pandemia. Os dados completos e as limitações estão em [ANALISE.md](auditoria/sensibilidade_janelas_longas/ANALISE.md).
- As três abas solicitadas foram incluídas na seção 4.5 como Figuras 7, 8 e 9, com continuações: Evolução temporal, Distribuição territorial e Perfil demográfico. São 16 partes distribuídas em nove páginas, preservando os gráficos, as tabelas, o mapa e os painéis de raça/cor. As imagens provêm de trechos reais contínuos da interface local; a montagem mecânica e os filtros estão documentados em `docs/auditoria/telas_tcc/capturas.json`. Foram omitidos apenas cabeçalhos comuns repetidos e preenchimento branco final. Não foram criados elementos artificiais da interface.
- As capturas usam o recorte Suicídio geral, 2026, janeiro a setembro, todos os sexos e os 78 municípios. A população de 2026 é provisoriamente a de 2025, conforme aviso da interface. As capturas ilustram o funcionamento e não constituem uma nova extração ou um novo resultado epidemiológico.
- As figuras posteriores foram renumeradas, as remissões ajustadas e as listas e o sumário repaginados. A formatação do primeiro parágrafo de 2.2 foi normalizada e a seção 4.5 deixou de afirmar que a comparação dos mesmos meses garante comparabilidade dos dados.

A verificação desta revisão confirmou os 12 cenários iniciais e os nove complementares contra os CSV, respeitando o arredondamento mostrado nas tabelas. Os 12 cenários de controle foram reproduzidos na análise complementar com tolerância de 10⁻¹². A versão final tem 70 páginas, 70 localizadores conferidos contra a paginação renderizada, 16 figuras numeradas, seis tabelas numéricas e 80 referências. As oito equações e as quatro figuras de arquitetura mantêm os arquivos de imagem originais. As figuras estatísticas correspondem exatamente aos arquivos da execução v3; os hashes da base e dos manifestos principal, complementar e das capturas constam em `docs/auditoria/revisao_docx.json`.

Todas as 70 páginas daquela versão foram inspecionadas visualmente em PNG, com reinspeção das páginas alteradas nas renderizações sucessivas. Não foram identificados cortes, sobreposições, gráficos partidos, glifos ausentes ou localizadores divergentes na entrega. O programa de validação também conferiu a integridade dos originais e do backup, os valores exibidos e os arquivos das imagens. Essa etapa alterou apenas o documento e sua documentação; não exigiu repetir os 76 testes de produção já aprovados em Python 3.12.8.

## Substituição das capturas por descrição acadêmica

Por solicitação posterior do autor, a seção 4.5 deixou de apresentar as capturas de Evolução temporal, Distribuição territorial e Perfil demográfico. Foram retiradas somente as 16 partes das antigas Figuras 7 a 9, acompanhadas de suas legendas, subdivisões e fontes. As três abas passaram a ser explicadas em parágrafos acadêmicos, com suas medidas, comparações, tabelas, mapas e exportações. A pirâmide é identificada como distribuição proporcional dos óbitos entre anos; a razão entre sexos é uma razão de contagens; raça/cor permanece sem taxa por ausência do denominador correspondente. A descrição foi conferida com as funcionalidades implementadas.

Todas as imagens estatísticas do corpo e do Apêndice C foram preservadas. As figuras posteriores foram renumeradas em sequência, de modo que o documento atual contém 13 figuras numeradas. A lista de figuras, as remissões e o sumário foram atualizados. A versão anterior de 70 páginas permanece em `docs/auditoria/versoes/TCC_Daniel_Breda_Bigossi_Revisado_70p_20261030_143951.docx`, com SHA-256 `39fd279215e7e56c76d675ade87edb54fc4099a839716b60bc4e4dfb43f11ff9`; seu manifesto também foi arquivado. Os arquivos originais das capturas e os dados do projeto não foram apagados.

O Quadro 1 já apresentava todos os grupos CID-10 dos numeradores. Foi acrescentado um único parágrafo em 2.1 para caracterizá-los: X85–Y09, agressões; Y22–Y24, disparos de arma de fogo de intenção não determinada; Y35, intervenção legal; Y87.1, sequelas de agressão; Y89.0, sequelas de intervenção legal; X60–X84, lesões autoprovocadas intencionalmente; e Y87.0, sequelas dessas lesões. A seleção coincide com a regra do ETL e com as fichas 1.8.15, 1.8.16 e 1.8.17, cujas referências, assim como OMS/DATASUS (2008), já constavam do trabalho. Os recortes etários e de sexo e os códigos não foram modificados; a definição operacional não substitui a classificação jurídica das ocorrências. Não houve ampliação da bibliografia.

Essa versão tinha 61 páginas e 67 localizadores conferidos contra a paginação renderizada. O controle de integridade confirmou 21 desenhos preservados: oito equações, quatro figuras de arquitetura e nove imagens estatísticas. Os conteúdos das 80 referências, das tabelas numéricas e dos 21 cenários de sensibilidade permanecem idênticos à versão anterior. Os arquivos das imagens estatísticas continuam correspondendo exatamente à execução v3. A retirada de elementos visuais e a revisão da prosa não alteraram código, dados, cálculos ou parâmetros e não exigiram nova execução dos testes de produção. Todas as 61 páginas foram abertas e inspecionadas em PNG na renderização final, sem cortes, sobreposições ou glifos ausentes. A cobertura por revisor e os hashes finais são registrados em `docs/auditoria/revisao_docx.json`.

## Pendências e limites

- A folha de aprovação e a ficha catalográfica não constam do documento original. Dados de banca, data de aprovação e ficha oficial devem ser inseridos pelo autor conforme exigência da UFES; não foram inventados.
- O texto revisado é uma consolidação editorial e metodológica, sujeita à revisão do orientador e às exigências específicas do curso. Não representa certificação institucional integral de ABNT.
- A reprodução numérica e os testes demonstram propriedades computacionais. Uso por profissionais, tempo economizado, desempenho prospectivo dos alarmes e impacto na mortalidade exigem estudos próprios.
- Os gráficos de baixa contagem, os pressupostos rejeitados e os denominadores provisórios continuam como limitações explícitas. A ferramenta não transforma sinais em comprovação causal.
- Nenhuma nova extração de mortalidade foi atribuída a esta revisão acadêmica. Os resultados usam a base local identificada no manifesto; o histórico original foi preservado.

A integridade do original, a preservação das equações e o hash da cópia revisada são registrados em `docs/auditoria/revisao_docx.json`. A entrega do DOCX inclui renderização e inspeção de todas as páginas; as imagens de conferência permanecem temporárias.

## Resumo do relatório com X, AM e EWMA

Na revisão seguinte, a antiga Figura 7 foi retirada e a antiga Figura 8 passou a apresentar a nova página de resumo do relatório, gerada pelo script com os gráficos X, AM e EWMA. Após a renumeração, essa imagem é a Figura 7. As seis inserções de páginas de relatório no corpo e no Apêndice C foram atualizadas para a mesma execução em `docs/auditoria/resultados_relatorio_x_am_ewma_final/`. A série histórica completa permanece no PDF, em página seguinte ao resumo. Foram corrigidos também cortes nos cabeçalhos das tabelas do gerador.

O documento final tem 60 páginas, 66 localizadores, 12 figuras e 20 desenhos, preservando oito equações, quatro figuras de arquitetura, tabelas, bibliografia e resultados. Onze páginas alteradas foram reinspecionadas pelo root; os corpos das outras 49 páginas são idênticos pixel a pixel à versão de 61 páginas já revisada integralmente. A paginação e todos os localizadores foram conferidos separadamente no PDF. Os três relatórios finais tiveram suas 21 páginas abertas e aprovadas visualmente. A suíte final passou com 79 testes; os 16 CSVs produzidos permaneceram idênticos byte a byte aos da execução v3. A versão de 61 páginas e seu manifesto estão preservados em `docs/auditoria/versoes/`.
