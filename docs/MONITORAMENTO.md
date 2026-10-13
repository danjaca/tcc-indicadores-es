# Modelagem estatística dos indicadores

Implementa as seções 2.6.5 e 2.7 do documento de introdução e referencial teórico de Daniel Breda. O cálculo determinístico mantém as regras existentes. O monitoramento usa u/u′ de Laney, EWMA, CUSUM bilateral com reinício após sinal, canais por quartis e funil municipal com limites exatos de Poisson de 95% e 99,8%.

## Desenho de teste definido antes da execução

O experimento padrão ajusta exclusivamente 2016–2022 (fase I) e avalia 2023–2026 (fase II), sem usar anos de teste na estimação. Analisa os três indicadores no estado e nas quatro regiões, separadamente para cada quadrimestre e para acumulados janeiro–agosto e janeiro–dezembro. Cada sequência compara os mesmos meses entre anos. O painel permite declarar cinco a sete anos consecutivos de referência; por padrão reserva o último ano anterior para avaliação adicional. O uso operacional exige revisão da estabilidade da referência e de anos atípicos.

Taxas usam população anual elegível; períodos parciais não são anualizados. A referência u é soma dos óbitos dividida pela soma das populações, multiplicada por 100 mil. Diagnóstico Pearson usa qui-quadrado com n−1 graus de liberdade, nível 5%; quando há sobredispersão, u′ aplica σz estimado por amplitude móvel dos resíduos Poisson padronizados dividida por 1,128, com piso 1. Tendências podem causar sobredispersão: alargar limites não substitui avaliar estabilidade.

EWMA: λ=0,2, L=3, início na taxa de referência, limites transitórios. CUSUM: K=0,5σ e H=5σ, bilateral, reinício de ambas as somas após qualquer sinal. A escala σ é o desvio-padrão amostral das taxas históricas, com piso na raiz da variância Poisson média. São gráficos de taxas para períodos equivalentes; não são gráficos Poisson especializados com memória. Lacunas não viram zeros e interrompem a memória.

Canal por quartis calculado sobre cinco a sete taxas históricas do mesmo período. Êxito abaixo de Q1, segurança até a mediana, alerta até Q3, excesso acima de Q3. Apenas quadrimestres completos e acumulados desde janeiro são apresentados como canais. Não implementa a alternativa de média geométrica. Uma zona acima da mediana não é alarme com probabilidade nominal de 0,2%, e excesso não confirma epidemia.

Funil: referência ponderada do conjunto municipal selecionado, estadual quando todos são selecionados. Intervalos centrais de quantis Poisson são limites preditivos de contagens, convertidos em taxas; são discretos, especialmente para contagens pequenas. O valor de referência é estimado do conjunto atual e não ajusta diferenças de composição ou risco. Dispersão territorial Pearson aparece na tabela; limites normais alargados por √max(1,φ) são uma sensibilidade aproximada, identificada separadamente dos limites exatos. Nenhum ranking é produzido.

## Execução e evidências

Na pasta `dashboard_streamlit`, com dependências instaladas:

```bash
python -m pytest tests -q
python experimento_monitoramento.py --simulacoes 200 --seed 20261011
```

`resultados_monitoramento` recebe séries de referência, limites/sinais por ano, frequências por método, funis municipais, períodos indisponíveis, simulações e manifesto com SHA-256 do dataset, referência e parâmetros. As simulações são repetíveis: sequências de 12 períodos Poisson com população fixa, sem mudança ou com mudança de ±25% depois de quatro períodos. Medem sinais por período, probabilidade de sinal na janela e atraso médio condicional à detecção. Sob o cenário sem mudança, sinais são falsos alarmes simulados. Esse cenário Poisson não reproduz heterogeneidade real; nenhum resultado prova validade epidemiológica ou utilidade operacional. A frequência histórica de sinais não é chamada de falso alarme, pois não há eventos rotulados pela vigilância. Não foi estimado ARL ilimitado.

## Cobertura e limites da base atualizada

A série 2016–2026 foi reextraída do TabNet/SIM da SESA com os códigos das fichas do PES: X85–Y09, Y22–Y24, Y35, Y87.1 e Y89.0 para homicídios/agressões; X60–X84 e Y87.0 para suicídios. As categorias completas incluem registros ainda sem quarto dígito; as sequelas permanecem selecionadas individualmente. Os complementos de raça/cor e meios precisam fechar com a fato principal por indicador, município, mês e sexo. Não foram alterados óbitos ou populações para produzir sinais. Os dados de 2025 e 2026 são sujeitos a revisão; 2026 tem janeiro–setembro e população provisória de 2025. A conferência de totais anuais, segundo quadrimestre e referências municipais de 2024 está documentada em `CONFERENCIA_REFERENCIAS.json`. Anos ausentes aparecem como indisponíveis. O painel sinaliza essas condições.

A avaliação de alterações reais conhecidas, revisão dos anos atípicos e teste de utilidade com profissionais da vigilância continuam dependendo de evidências externas. Limites 99,8% são por comparação e não controlam simultaneamente todos os municípios/indicadores. Dados agregados não demonstram causalidade nem risco individual. Proporções por raça/cor e meios permanecem proporções, sem denominadores para taxas.

## Referências de implementação

- NIST, EWMA: https://www.itl.nist.gov/div898/handbook/pmc/section3/pmc314.htm
- NIST, CUSUM: https://www.itl.nist.gov/div898/handbook/pmc/section3/pmc323.htm
- Minitab, métodos do gráfico u′ de Laney: https://support.minitab.com/en-us/minitab/help-and-how-to/quality-and-process-improvement/control-charts/how-to/attributes-charts/laney-u-chart/methods-and-formulas/methods-and-formulas/
- SciPy, distribuição Poisson: https://docs.scipy.org/doc/scipy/reference/generated/scipy.stats.poisson.html
- Bortman (1999) e Spiegelhalter (2005), conforme o referencial teórico fornecido.

## Guia de leitura no painel

O botão **ⓘ Como ler**, junto ao título, abre um diálogo com o significado dos filtros, taxa por 100 mil, referência histórica, u/u′, EWMA, CUSUM, canal endêmico, funil e sinais. A explicação distingue quartis de quadrimestres, sinal estatístico de investigação de causas e taxa parcial de meta anual. A região escolhida combina-se com o recorte do painel.

A página exibe a situação dos dados antes dos resultados: meses disponíveis, data da extração, ano e provisoriedade do denominador e informação de revisão dos registros. Não estima completude nem corrige atraso de registro a partir desses metadados.

O modo **Protocolo do TCC** fixa a fase I em 2016–2022 e λ=0,2, L=3, K=0,5, H=5; exige avaliação posterior a 2022 e cobertura da referência. O modo **Exploratória** mantém os controles livres. Coincidência com o experimento exige também os mesmos recortes; selecionar o protocolo não valida sua estabilidade. A referência pode ser consultada e baixada em CSV.

Nos gráficos de taxas, a fase I aparece em cinza, separada da fase II; apenas a fase II recebe sinais. No EWMA, os pontos cinza são taxas observadas, não valores históricos de EWMA. Triângulos vermelhos e azuis distinguem sinais de aumento e redução; no CUSUM, a linha negativa crescente acumula evidência de redução. O resumo do último período disponível mantém os métodos separados, sem pontuação de risco ou confirmação independente.

Na interface e no CSV do painel, o canal recebe o título **Canal histórico por quartis** e as zonas “Abaixo de Q1”, “De Q1 à mediana”, “Acima da mediana até Q3” e “Acima do Q3”. As fórmulas e os resultados do experimento permanecem iguais. Quartis descrevem posição histórica e não acionam marcadores de alarme de controle.

O funil acrescenta óbitos esperados sob a taxa do conjunto, diferença observado menos esperado e direção dos sinais exatos e ajustados aproximados. A decisão exata original em contagens é preservada. O destaque dos pontos usa 99,8%; o texto ao passar sobre o ponto também informa 95% e a sensibilidade ajustada de 99,8%. Um único município não gera comparação territorial e recebe orientação para ampliar a seleção. Contagens pequenas não recebem um corte arbitrário de validade. A página explicita a menor capacidade de detecção, a instabilidade de taxas e a ausência de ajuste completo para composição demográfica e social.

Esses complementos de interpretação consideram Bédubourg e Le Strat (2017), DOI 10.1371/journal.pone.0181227; Verburg et al. (2018), DOI 10.1177/0962280217700169; Noufaily et al. (2019), DOI 10.1093/bioinformatics/bty997; Craig et al. (2023), DOI 10.1016/j.ijregi.2023.08.007; Baker et al. (2023), DOI 10.1093/cid/ciac923; e o capítulo *Analysis of Surveillance Data* do CDC (2025). Aplicações a doenças infecciosas ou hospitais não comprovam calibração para mortalidade por causas externas no ES. Não foram acrescentados modelos, monitoramento mensal sucessivo, correção de atraso ou comparações experimentais de algoritmos.
