"""Interface dos métodos previstos nas seções 2.6.5 e 2.7 do TCC."""
from dataclasses import asdict
import json
import hashlib
from configuracao import DADOS
import pandas as pd
import plotly.graph_objects as go
import streamlit as st
from modelo import serie_historica, agrupado, cobertura_completa
from monitoramento import analisar, funil, TAXA


def grafico(t, valor, inferior, superior, titulo, referencia=None):
    fig = go.Figure()
    for col, nome, cor in [(superior, 'Limite superior', '#bd4545'),
                           (inferior, 'Limite inferior', '#bd4545')]:
        fig.add_trace(go.Scatter(x=t['Ano'], y=t[col], name=nome,
                                line=dict(color=cor, dash='dash')))
    if referencia is not None: fig.add_hline(y=referencia, line_dash='dot', annotation_text='Referência')
    fig.add_trace(go.Scatter(x=t['Ano'], y=t[valor], name=valor, mode='lines+markers', line=dict(color='#126c83')))
    fig.update_layout(title=titulo, xaxis_title='Ano · mesmos meses', yaxis_title='Taxa por 100 mil', height=400)
    fig.update_xaxes(dtick=1,tickformat='d')
    st.plotly_chart(fig, width='stretch')


@st.dialog('Como ler esta página',width='large')
def mostrar_guia():
    st.markdown('''Use esta aba para reconhecer resultados que merecem atenção da vigilância. Comece pelo recorte e, depois, observe os sinais nos gráficos.

**Confira o que está sendo comparado**

O indicador, o ano, os meses, os municípios e o sexo vêm dos filtros do painel. A região escolhida nesta aba também é aplicada. A comparação usa os mesmos meses nos diferentes anos.

A **taxa por 100 mil** relaciona os óbitos à população elegível do indicador. O denominador é anual: uma taxa de poucos meses representa aquele período e deve ser comparada com os mesmos meses de outros anos. Para comparar com a meta anual, selecione um ano completo.

**Entenda a referência histórica**

Os anos da fase I definem o padrão de comparação. Os anos posteriores, na fase II, são avaliados com esse padrão. Confira os anos escolhidos e os avisos de estabilidade antes de interpretar os resultados.

**Leia cada gráfico**

- **u / u′:** compare a taxa observada com os limites inferior (LIC) e superior (LSC). Um ponto fora dos limites sinaliza um resultado que se afasta da variação esperada. O u′ amplia os limites quando o histórico mostra variação adicional.
- **EWMA:** acompanha uma taxa suavizada, com mais peso para os resultados recentes. Pode sinalizar mudanças pequenas e persistentes quando a linha ultrapassa seus limites.
- **CUSUM:** a linha **+** acumula desvios na direção de aumento; a linha **−**, na direção de redução. Ao ultrapassar **H**, surge um sinal e a acumulação é reiniciada para a próxima observação.
- **Canal endêmico:** compara um quadrimestre completo ou um acumulado desde janeiro com o mesmo período histórico. Abaixo de Q1: êxito; até a mediana: segurança; até Q3: alerta; acima de Q3: excesso estatístico. Aqui, **Q1 e Q3 são quartis do histórico, não quadrimestres**.
- **Funil municipal:** cada ponto é um município; a posição horizontal mostra sua população e a vertical, sua taxa. Os limites consideram a maior oscilação esperada em populações pequenas. Os limites de 99,8% são mais amplos que os de 95%. Observe os pontos fora dos limites e os avisos de dispersão, sem transformar o gráfico em ranking.

**Use os sinais para orientar a investigação**

Na tabela, uma coluna “Sinal” marcada indica que a regra estatística foi acionada. A análise das causas exige contexto territorial e conferência dos registros. Priorize o estado e as regiões: muitas comparações municipais aumentam a ocorrência de sinais por acaso.

**Confira os avisos e registre a análise**

Resultados identificados como provisórios podem mudar com revisões do SIM ou da população. Períodos sem cobertura aparecem como indisponíveis. Os botões de download permitem guardar as tabelas e os parâmetros utilizados.
''')


def mostrar_monitoramento(f, p, g, meta, ano, meses, indicador=None, sexo_filtro=None):
    titulo, ajuda=st.columns([5,1],vertical_alignment='center')
    with titulo:
        st.subheader('Monitoramento estatístico')
    with ajuda:
        if st.button('Como ler',icon=':material/info:',help='Abra o guia para interpretar esta página.',key='ajuda_monitoramento'):
            mostrar_guia()
    st.write('Compare períodos equivalentes com uma referência histórica declarada. Os sinais orientam investigação pela vigilância e não identificam causas.')
    st.caption('Os filtros de indicador, território e sexo do painel são aplicados ao histórico e à avaliação. A memória acompanha os mesmos meses ao longo dos anos, evitando misturar períodos sazonais diferentes.')
    regioes=sorted(g['regiao_saude'].dropna().unique()) if 'regiao_saude' in g else []
    territorio=st.selectbox('Território do monitoramento',['Recorte do painel']+regioes,key='monitor_territorio',help='A região é combinada com os municípios já selecionados no painel.')
    if territorio!='Recorte do painel':
        codigos=g.loc[g['regiao_saude'].eq(territorio),'cod_mun_res']
        f=f[f.cod_mun_res.isin(codigos)];p=p[p.cod_mun_res.isin(codigos)]
    st.caption('Território de monitoramento: '+territorio+'. Regiões de saúde conforme o PDR 2024; os municípios e o sexo selecionados no painel continuam aplicados.')
    candidatos = [y for y in sorted(meta['anos_disponiveis']) if y < ano and cobertura_completa(f, y, meses)]
    if len(candidatos) < 5:
        st.info('São necessários pelo menos cinco anos completos anteriores ao ano selecionado.'); return
    padrao = candidatos[-6:-1] if len(candidatos) >= 6 else candidatos[-5:]
    with st.expander('Referência histórica e parâmetros', expanded=False):
        anos = st.multiselect('Anos da fase I (cinco a sete consecutivos)', candidatos, default=padrao, key='monitor_anos')
        peso = st.slider('Peso λ do EWMA', .05, 1., .2, .05)
        largura = st.number_input('Largura L dos limites', min_value=1., max_value=6., value=3., step=.1)
        k = st.number_input('Folga K do CUSUM (desvios-padrão)', min_value=.1, value=.5, step=.1)
        h = st.number_input('Intervalo H do CUSUM (desvios-padrão)', min_value=.1, value=5., step=.1)
        st.caption('Parâmetros exploratórios. A calibração deve anteceder a avaliação; escolher parâmetros depois de observar os sinais invalida estimativas de desempenho.')
    try:
        base, t, ref, original = analisar(f, p, anos, ano, meses, peso=peso, largura=largura, k=k, h=h)
    except ValueError as e:
        st.info(str(e)); return
    st.caption(f'Fase I: {min(ref.anos)}–{max(ref.anos)}. Fase II: {max(ref.anos)+1}–{ano}. Meses: '+', '.join(map(str, meses))+'. Limites congelados durante a avaliação.')
    if not meta.get('definicao_cid'):
        st.warning('A base recebida usa a definição anterior de CID. Esta análise é exploratória e deve ser refeita após reprocessamento de toda a série com a definição atual; não misture definições no histórico.')
    provis = [str(y) for y in t['Ano'] if len(meta.get('extracoes', {}).get(str(y), {}).get('meses', list(range(1,13)))) < 12 or meta.get('populacao', {}).get(str(y), {}).get('provisorio') or 'sujeitos a revisão' in meta.get('extracoes', {}).get(str(y), {}).get('revisao', '').lower()]
    t['Situação dados'] = ['Provisório' if str(y) in provis else 'Histórico sujeito a revisão' for y in t['Ano']]
    if provis: st.info('Sinais provisórios nos anos '+', '.join(provis)+': dados recentes ou denominador provisório.')
    if original[TAXA].isna().any(): st.warning('Há períodos indisponíveis na fase II. Foram omitidos dos cálculos e interrompem a memória dos gráficos.')
    if ref.p_sobredispersao < .05:
        st.warning(f'Sobredispersão no histórico (Pearson φ={ref.dispersao:.2f}, p={ref.p_sobredispersao:.4f}); σz={ref.sigma_z:.2f}. '+('Aplicados limites u′ de Laney.' if ref.sigma_z>1 else 'σz não alarga os limites; revisar estabilidade e tendências antes de uso operacional.'))
    st.caption('Cinco a sete anos oferecem uma referência curta: inspecione anos atípicos, tendências e estabilidade antes de adotar os limites em operação.')
    grafico(t, TAXA, 'LIC controle', 'LSC controle', str(t['Método controle'].iloc[0]), ref.taxa)
    grafico(t, 'EWMA', 'LIC EWMA', 'LSC EWMA', 'EWMA · mudanças persistentes', ref.taxa)
    fig = go.Figure()
    for col in ['CUSUM +', 'CUSUM −']: fig.add_trace(go.Scatter(x=t['Ano'], y=t[col], mode='lines+markers', name=col))
    fig.add_hline(y=h, line_dash='dash', annotation_text='H')
    fig.update_layout(title='CUSUM · aumentos e reduções', yaxis_title='Desvios-padrão acumulados', height=400)
    fig.update_xaxes(dtick=1,tickformat='d')
    st.plotly_chart(fig, width='stretch')
    st.caption('CUSUM reiniciado após qualquer sinal. EWMA inicia na média histórica; σ usa a variabilidade das taxas históricas, com piso Poisson. Estes gráficos de memória pressupõem referência estável.')
    canonicos = [list(range(a,b)) for a,b in [(1,5),(5,9),(9,13),(1,9),(1,13)]]
    if list(meses) in canonicos:
        grafico(t, TAXA, 'Q1', 'Q3', 'Canal endêmico · quartis do mesmo período', ref.mediana)
        st.caption('Êxito: abaixo de Q1; segurança: de Q1 à mediana; alerta: acima da mediana até Q3; acima de Q3: excesso estatístico. As zonas não confirmam epidemia e não têm taxa nominal de falso alarme de 0,2%.')
    else:
        t['Zona canal']='Não aplicável ao recorte'
        st.info('O canal endêmico é apresentado para quadrimestres completos ou acumulados desde janeiro. Ajuste a seleção de meses para utilizá-lo.')
    st.dataframe(t, hide_index=True, width='stretch')
    st.download_button('Baixar sinais e limites (CSV)', t.to_csv(index=False,sep=';',decimal=',').encode('utf-8-sig'), 'monitoramento_estatistico.csv','text/csv')
    manifesto = dict(referencia=asdict(ref), meses=list(meses), peso=peso, largura=largura, k=k, h=h,
                     indicador=indicador,sexo_filtro=sexo_filtro,territorio=territorio,
                     municipios=sorted(f.cod_mun_res.unique().tolist()),
                     faixas_etarias=sorted(f.faixa_etaria.unique().tolist()),
                     sha256_dataset=hashlib.sha256((DADOS/'dataset.zip').read_bytes()).hexdigest(),
                     definicao_cid=meta.get('definicao_cid', 'legada'), anos_avaliacao=t['Ano'].tolist(),
                     nota='Sinais exploratórios; não são causas nem validação epidemiológica.')
    st.download_button('Baixar parâmetros (JSON)',json.dumps(manifesto,ensure_ascii=False,indent=2),'parametros_monitoramento.json','application/json')
    st.subheader('Comparação municipal por gráfico de funil')
    st.caption('Referência ponderada do conjunto territorial selecionado. Com todos os municípios, corresponde à taxa estadual. Limites de 95% e 99,8%; municípios em ordem alfabética, sem ranking.')
    municipal = agrupado(f,p,ano,meses,['cod_mun_res']).merge(g[['cod_mun_res','no_municipio']],on='cod_mun_res')
    try: ft = funil(municipal)
    except ValueError as e: st.info(str(e)); return
    ft = ft.sort_values('População')
    fig = go.Figure()
    for nivel in ['95%', '99,8%']:
        for lado in ['LIC','LSC']:
            fig.add_trace(go.Scatter(x=ft['População'],y=ft[lado+' '+nivel],name=lado+' '+nivel,mode='lines',line=dict(dash='dot' if nivel=='95%' else 'dash')))
    fig.add_trace(go.Scatter(x=ft['População'],y=ft[TAXA],mode='markers',name='Municípios',text=ft['no_municipio'],hovertemplate='%{text}<br>População: %{x}<br>Taxa: %{y:.2f}<extra></extra>'))
    fig.add_hline(y=float(ft['Referência'].iloc[0]),line_dash='dot')
    fig.update_layout(height=450,xaxis_title='População anual elegível',yaxis_title='Taxa por 100 mil')
    st.plotly_chart(fig,width='stretch')
    phi = float(ft['Dispersão territorial'].iloc[0])
    if phi>1:
        st.warning(f'Dispersão territorial φ={phi:.2f}. Os limites exatos Poisson podem produzir sinais adicionais por heterogeneidade. A tabela inclui limites ajustados aproximados como análise de sensibilidade; não são limites exatos.')
    st.dataframe(ft.sort_values('no_municipio'),hide_index=True,width='stretch')
    st.download_button('Baixar gráfico de funil (CSV)',ft.sort_values('no_municipio').to_csv(index=False,sep=';',decimal=',').encode('utf-8-sig'),'funil_municipal.csv','text/csv')
    st.caption('Priorize o agregado estadual e regional. Múltiplas comparações ampliam alarmes falsos; 99,8% é limite por comparação, sem controle familiar. Dados agregados não permitem inferir risco individual ou causalidade.')
