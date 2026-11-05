# Monitoramento estatístico mensal dos indicadores

O protocolo `graficos_controle_mensal_v4` implementa X–AM e EWMA sobre taxas mensais de mortalidade. A contribuição central do TCC é o SAD e sua validação funcional. Sinais e valores-p são resultados da aplicação, não critérios de sucesso do sistema.

## Referência metodológica e alcance da validação

Barros (2021) utilizou 48 meses na fase I, seis meses posteriores na fase II, gráficos X–AM com exclusões iterativas e EWMA com λ = 0,1 e largura próxima de 2,7. Sua taxa usa óbitos por autorizações de internação hospitalar aprovadas, multiplicados por 100 (p. 17); o SAD usa óbitos do SIM por população elegível, multiplicados por 100 mil. A adaptação é da estrutura dos gráficos, não da definição epidemiológica. A série publicada é usada exclusivamente para verificar os cálculos. Reproduzir seus números não valida automaticamente a adequação do método a todo indicador ou território do Espírito Santo. A regra adaptativa anterior de reduzir a referência até obter valores-p maiores não é atribuída a Barros e saiu do protocolo principal.

Referência verificada na fonte primária: BARROS, Veronica Aparecida Souza. *Monitoramento da taxa de mortalidade por câncer de mama no Brasil*. 2021. 67 f. Trabalho de Conclusão de Curso (Graduação em Estatística) – Universidade Federal de Uberlândia, Uberlândia, 2021. Disponível em: https://repositorio.ufu.br/handle/123456789/33585. Acesso em: 30 out. 2026.

## Unidade de análise e indicadores

A taxa mensal é `x_t = óbitos do mês / população anual elegível × 100 000`, sem anualização. A soma das taxas mensais do mesmo ano reproduz a taxa do período, pois o denominador é comum. O denominador respeita território, sexo e faixa etária do indicador. População provisória e revisões da fonte devem continuar identificadas. Meses sem cobertura não são zeros.

O nível estadual é a aplicação principal. As categorias de aplicabilidade territorial baseadas em contagens médias, zeros e normalidade são alertas operacionais, não uma calibração epidemiológica validada. Séries municipais esparsas podem ser inadequadas a limites normais. Não há comprovação de desempenho para todo recorte nem garantia de que EWMA corrige qualquer desvio da normalidade.

## Parâmetros predefinidos

| Parâmetro | Padrão | Justificativa e limite |
|---|---:|---|
| Janela da fase I | 48 meses | Quatro ciclos anuais e comparabilidade de extensão com Barros; escolha predefinida, sem otimização por sinais. |
| Sensibilidade da fase I | 24, 36, 48, 64 meses | Expõe o compromisso entre quantidade de dados e mudanças históricas. 64 é um cenário exploratório, não recomendação publicada por Barros. |
| Fase II | 12 meses | Horizonte operacional após o fim da fase I; início pode ser qualquer mês. |
| λ do EWMA | 0,1 | Dá memória a mudanças persistentes; valores menores retêm mais história. |
| L do EWMA | 2,701 | Referência de ARL sob controle próximo de 370 sob normalidade, independência, limites assintóticos e parâmetros conhecidos. |
| L do X | 3 | Limites de três desvios; ARL normal teórico ≈ 370,4 para um gráfico isolado. |
| α dos diagnósticos | 0,05 | Nível nominal; não determina a janela nem exclui observações. |
| Exclusão automática | Desativada | Um sinal sozinho não comprova causa especial; preserva observações até investigação. |
| Fração máxima de exclusões | 0,20 | Salvaguarda operacional registrada, não valor ótimo estatisticamente demonstrado. |
| Prazo operacional | 60 dias | Marca meses recentes como em consolidação; não certifica completude e não impede revisões anteriores. |
| Ljung–Box | 1 e 12 | Avalia dependência imediata e conjunta até um ciclo anual. |

Os parâmetros vêm de `[monitoramento]` em `config.toml`. Sem referência explícita em `[monitoramento.fase1]`, a fase I fixa termina em dezembro do ano anterior ao último ano disponível. A falta de cobertura interrompe o cálculo, sem reduzir silenciosamente a janela. A interface permite ajustar o início mensal da fase II e a referência precedente; a configuração escolhida deve ser documentada antes de interpretar sinais.

A atualização não troca automaticamente a referência em função de valores-p. Alterações permanentes precisam ser justificadas e registradas no protocolo. `sugerir_fase1` é mantida somente por compatibilidade com a avaliação exploratória legada; seus resultados não definem o protocolo atual.

## Fase I e pressupostos

A referência deve ter uma observação por mês, cobertura completa e taxas finitas não negativas. Séries constantes não permitem estimar dispersão e são recusadas com mensagem explícita.

Os diagnósticos usam a série completa da referência, antes das exclusões:

- Lilliefors: hipótese de distribuição normal; não rejeitar não prova normalidade.
- Ljung–Box: autocorrelações nulas até as defasagens avaliadas; não rejeitar não prova independência.
- Dickey–Fuller aumentado: raiz unitária no modelo com constante e tendência; rejeição não comprova média constante nem ausência de tendência determinística.
- Cox–Stuart: tendência, comparando primeiro e último terço; teste binomial bilateral exato sobre pares não empatados. A aproximação normal é usada explicitamente apenas na reprodução numérica de Barros.
- Fisher: componente periódico dominante no periodograma sob ruído branco; não é um teste exclusivo de sazonalidade anual. Dependência e tendência limitam sua interpretação.
- FAC/FACP e Q-Q: diagnósticos visuais complementares.

Os valores-p dos vários diagnósticos e cenários são exploratórios, sem correção por multiplicidade. Não servem para procurar a janela que “passa”. Pressupostos rejeitados são mantidos visíveis e limitam a interpretação dos sinais e do ARL teórico.

Estimam-se `μ0` pela média da referência mantida e `σ0 = AM̄ / 1,128`. O limite do AM é `3,267·AM̄`. Se permanecem sinais X ou AM, a referência é rotulada instável, inclusive quando a exclusão automática está desativada. Os parâmetros são então descritivos da referência, não evidência de processo em controle.

Exclusões manuais devem pertencer à fase I e ter causa documentada. Quando a reprodução exploratória ativa exclusão automática, primeiro são retirados pontos fora dos limites do X e depois os meses finais das amplitudes fora do limite; a sequência remanescente é ligada novamente, como na verificação com Barros. Esse procedimento altera as adjacências e não demonstra a causa dos pontos excluídos. Todas as exclusões e iterações são registradas; ultrapassar a fração máxima não permite declarar estabilidade.

## Fase II

Os parâmetros ficam congelados. A fase II começa no mês imediatamente posterior ao fim da fase I e pode terminar no horizonte escolhido, mesmo que ainda não haja dados para todos os meses planejados.

| Gráfico | Estatística | Limites |
|---|---|---|
| X | `x_t` | `max(0, μ0 − L·σ0)` e `μ0 + L·σ0` |
| AM | `abs(x_t − x_(t−1))` | zero e `3,267·AM̄` |
| EWMA | `z_t = λ·x_t + (1−λ)·z_(t−1)`, com `z_0 = μ0` | `μ0 ± L·σ0·sqrt(λ/(2−λ)·[1−(1−λ)^(2t)])` |

A primeira amplitude usa o último mês da fase I somente se os meses forem adjacentes. Uma lacuna na fase II interrompe a amplitude e reinicia o EWMA em μ0; meses ausentes continuam ausentes. Meses recentes recebem marca de consolidação e ficam fora das contagens resumidas de sinais interpretáveis. Os sinais brutos são preservados nos CSV técnicos; gráficos e tabelas da interface/PDF exibem os meses de forma neutra, com sinalização suspensa. Sem data da base, o prazo não pode ser verificado: a ausência de marca não certifica consolidação, e o uso operacional exige conferir os metadados.

Um sinal orienta investigação da qualidade dos registros e do contexto. Não identifica causas, não mede efeito causal de políticas e não autoriza afirmar ausência de problema quando nenhum gráfico sinaliza.

## Leitura quadrimestral

Para `m` meses disponíveis do mesmo ano, `S = Σ x_t`, esperado `m·μ0` e limites `max(0, m·μ0 − L·sqrt(m)·σ0)` e `m·μ0 + L·sqrt(m)·σ0`. A variância `m·σ0²` pressupõe independência e estabilidade; autocorrelação ou mudanças estruturais invalidam essa referência nominal.

Quadrimestres e acumulados incompletos são marcados como parciais e não emitem sinais. Se a fase II começa durante o ano, o acumulado considera somente seus meses disponíveis e não deve ser apresentado como cobertura de todo o ano. A leitura com meses em consolidação continua provisória e também não emite sinal quadrimestral.

## Sensibilidade e desempenho teórico

`dominio.monitoramento.sensibilidade` compara todas as janelas de 24, 36, 48 e 64 meses com o mesmo fim da fase I, a mesma fase II e os demais parâmetros iguais. Exibe cobertura, impedimentos, μ0, σ0, limites, estabilidade, exclusões, diagnósticos e contagens de sinais em meses fora da consolidação. Não escolhe cenário vencedor nem altera o protocolo. Exclusões documentadas são aplicadas quando pertencem à janela correspondente. A avaliação não é prospectiva independente e não estima taxa empírica de alarmes falsos.

O ARL de X assume observações normais independentes e parâmetros conhecidos. O ARL do EWMA usa cadeia de Markov com limites assintóticos constantes, enquanto o gráfico implementa limites transitórios. Logo, o ARL exibido é referência teórica aproximada para o sistema; não incorpora incerteza da fase I, referência instável, recortes esparsos, revisões nem uso simultâneo de vários gráficos. A calibração de L preserva esse ARL teórico de referência, não um desempenho empiricamente validado.

## Procedimento operacional

1. Conferir cobertura, denominador provisório, metadados e meses em consolidação.
2. Registrar o protocolo antes de interpretar sinais; manter a referência fixa durante o acompanhamento.
3. Consultar diagnósticos e estabilidade; diante de violação, apresentar resultados com ressalva em vez de procurar significância.
4. Examinar sinais fora da consolidação e investigar registros, revisões e contexto territorial.
5. Comparar todas as janelas de sensibilidade e documentar decisões, inclusive ausência de sinais.
6. Arquivar parâmetros, hashes, CSVs e relatório junto ao snapshot de dados do ciclo.

## Reprodução

```bash
python -m pytest tests -q
python -m experimentos.monitoramento --saida docs/auditoria/resultados_relatorio_x_am_ewma_final --figuras
```

O experimento não consulta fontes externas. Produz `verificacao_barros2021.csv`, séries, diagnósticos, parâmetros, iterações, fase II, quadrimestres, `sensibilidade_fase1.csv`, retrospectivas exploratórias, ARL, boletim, figuras e relatórios. `manifesto.json` registra versão do protocolo, parâmetros efetivamente aplicados, janelas, ambiente e hashes de dados/código. O resultado legado em `resultados_monitoramento/` permanece identificado pelo seu próprio manifesto.

O resumo do relatório PDF apresenta os gráficos X, AM e EWMA com a referência da fase I sombreada e a fase II disponível. A série histórica completa e as tabelas continuam nas páginas seguintes, seguidas dos diagnósticos, gráficos detalhados e parâmetros de reprodução. Essa organização usa os mesmos resultados calculados para a configuração em uso. A execução anterior em `docs/auditoria/resultados_v3/` permanece preservada como evidência histórica.

A atualização automatizada executa a análise sobre um lote isolado antes da publicação local. Falhas estatísticas ou de integridade não autorizam alterar os dados para satisfazer testes. A reextração e a publicação externa não fazem parte da verificação local do cálculo.

### Cox–Stuart exato e complementos exploratórios

O protocolo v4 usa `metodo_cox = "exato"`. A distribuição binomial bilateral evita a aproximação normal em poucos pares; não corrige dependência entre sinais nem assegura poder para detectar violações moderadas. A versão normal permanece identificada na replicação de Barros, preservando a comparação com os números publicados. Os seis diagnósticos principais não receberam ajuste de multiplicidade: não rejeitar suas hipóteses não demonstra validade da referência. Tendência pode contribuir para Ljung–Box e para componentes de baixa frequência no periodograma.

Os complementos separados incluem KPSS com constante e tendência, Bartlett e defasagem curta, e diagnósticos nos resíduos de tendência linear OLS na mesma amostra. Valores-p do KPSS são tabelados/interpolados e censurados em 0,01 e 0,10; valores-p dos resíduos são aproximados, exploratórios e sem correção de multiplicidade. Não recalibram os gráficos principais. A comparação da dispersão com Poisson considera a exposição populacional de cada mês, sem constituir teste formal de sobredispersão.

### Escala ajustada pelo número de dias

A opção `Ajustar monitoramento pelo número de dias do mês` aplica `taxa oficial × 30,4375 / dias do mês` à referência e à fase II, incluindo fevereiro bissexto. `ajustar_calendario` retorna cópia e preserva `Taxa oficial por 100 mil`, óbitos e população; é idempotente. Os gráficos mensais e seus limites são recalculados na escala identificada. A leitura quadrimestral permanece oficial e conserva seus próprios parâmetros, registrados no JSON/PDF.

Para reproduzir a opção ativa: calcular `r_oficial = analisar(serie_original, **entrada)`; calcular `r = analisar(ajustar_calendario(serie_original), **entrada)`; usar `r.quadrimestral = r_oficial.quadrimestral` e registrar os parâmetros oficiais. O manifesto identifica a transformação e as duas escalas. A sensibilidade de calendário compara as duas escalas com fases/parâmetros iguais e exclusão automática desligada em ambas; não substitui o indicador do PES nem escolhe a escala pelos sinais.

### Frequência nominal e histórico das escolhas

A probabilidade marginal nominal do AM é cerca de 0,9166% por ponto sob normais independentes e desvio conhecido; amplitudes consecutivas são dependentes, e seu inverso não é ARL. A estimação dos parâmetros, a dependência temporal e o uso dos nove gráficos nos três indicadores afastam o desempenho efetivo da referência nominal próxima de 370 do X isolado e do EWMA assintótico. Não há ARL conjunta validada.

O JSON/PDF inclui a sequência das configurações calculadas na sessão, com entradas completas, hashes e instante UTC. Reruns consecutivos idênticos não duplicam a entrada. O registro é temporário no Streamlit Cloud e deve ser exportado; não garante capturar análises de outras sessões ou todos os usuários.

### Qualidade das causas e versões dos dados

`python -m etl.diagnostico_causas --anos 2022 2023 2024 2025 2026 --saida dados --evidencias var/etl/qualidade_causas` consulta Y10–Y34 e R99 em três recortes estaduais. O painel só apresenta o complemento quando os hashes correspondem à base atual e o estado é disponível. Os recortes populacionais não são novos indicadores; Y22–Y24 já integra homicídios e não deve ser somado novamente. R99 não identifica por si só uma causa externa. Variações agregadas não demonstram reclassificação individual ou sua contribuição às taxas.

A rotina mensal atualiza os anos reprocessados e preserva os demais com proveniência por ano. Falha auxiliar não invalida a base principal já validada: preserva o CSV anterior e marca indisponibilidade/obsolescência. `etl.revisoes` cataloga snapshots e separa diferenças de cobertura, numerador e população. Lotes, cópias anteriores e artefatos remotos são preservados; a retenção remota é limitada e uma única versão não permite estimar completude.
