"""Interface dos métodos previstos nas seções 2.6.5 e 2.7 do TCC."""
from dataclasses import asdict
import json
import hashlib
from configuracao import DADOS
import pandas as pd
import plotly.graph_objects as go
import streamlit as st
from dominio.dados import agrupado, cobertura_completa
from dominio.monitoramento import analisar, funil, TAXA


def direcao(valores, inferior, superior):
    resultado = pd.Series('Sem sinal', index=valores.index)
    resultado.loc[valores > superior] = 'Aumento'
    resultado.loc[valores < inferior] = 'Redução'
    return resultado


def figura_historica(t, valor, inferior, superior, titulo, referencia=None, base=None,
                     destacar=True):
    fig = go.Figure()
    if base is not None:
        fig.add_trace(go.Scatter(x=base['Ano'], y=base[TAXA], name='Fase I · taxa histórica',
                                mode='lines+markers', line=dict(color='#64748b')))
        fronteira = float(base['Ano'].max()) + .5
        fig.add_vrect(x0=float(base['Ano'].min())-.5, x1=fronteira,
                      fillcolor='#e2e8f0', opacity=.3, line_width=0,
                      annotation_text='Fase I · referência', annotation_position='top left')
        fig.add_vline(x=fronteira, line_dash='dot', line_color='#64748b')
    for col, nome, cor in [(superior, 'Limite superior', '#bd4545'),
                           (inferior, 'Limite inferior', '#bd4545')]:
        if col in ['Q1', 'Q3']: nome = 'Quartil '+col
        fig.add_trace(go.Scatter(x=t['Ano'], y=t[col], name=nome,
                                line=dict(color=cor, dash='dash')))
    if referencia is not None:
        fig.add_hline(y=referencia, line_dash='dot', annotation_text='Mediana histórica' if inferior=='Q1' else 'Referência')
    fig.add_trace(go.Scatter(x=t['Ano'], y=t[valor], name='Fase II · '+valor, mode='lines+markers', line=dict(color='#126c83')))
    if destacar:
        sinais = direcao(t[valor], t[inferior], t[superior])
        for sentido, cor, simbolo in [('Aumento','#bd4545','triangle-up'),
                                     ('Redução','#2563eb','triangle-down')]:
            sub = t.loc[sinais.eq(sentido)]
            fig.add_trace(go.Scatter(x=sub['Ano'], y=sub[valor], name='Sinal de '+sentido.lower(),
                                    mode='markers', marker=dict(color=cor, symbol=simbolo, size=13)))
    fig.update_layout(title=titulo, xaxis_title='Ano · mesmos meses', yaxis_title='Taxa por 100 mil', height=500,
                      legend=dict(orientation='h', yanchor='top', y=-.3, x=0), margin=dict(b=140))
    fig.update_xaxes(dtick=1,tickformat='d')
    return fig


def grafico(*args, **kwargs):
    st.plotly_chart(figura_historica(*args, **kwargs), width='stretch')


@st.dialog('Como ler esta página',width='large')
def mostrar_guia():
    st.markdown('''Use esta aba para reconhecer resultados que merecem atenção da vigilância. Comece pelo recorte e, depois, observe os sinais nos gráficos.

**Confira o que está sendo comparado**

O indicador, o ano, os meses, os municípios e o sexo vêm dos filtros do painel. A região escolhida nesta aba também é aplicada. A comparação usa os mesmos meses nos diferentes anos.

A **taxa por 100 mil** relaciona os óbitos à população elegível do indicador. O denominador é anual: uma taxa de poucos meses representa aquele período e deve ser comparada com os mesmos meses de outros anos. Para comparar com a meta anual, selecione um ano completo.

**Entenda a referência histórica**

Os anos da fase I definem o padrão de comparação e aparecem em cinza nos gráficos de taxas. Os anos posteriores, na fase II, são avaliados com esse padrão. A separação vertical marca o fim da referência; a fase I não recebe sinais de avaliação. Confira tendências e anos atípicos: ampliar os limites não torna uma referência estável.

O modo **Protocolo do TCC** fixa 2016–2022, λ=0,20, L=3, K=0,5 e H=5. O modo exploratório permite outras escolhas. Os recortes também precisam coincidir para reproduzir os resultados do experimento. Cada passo da memória é um ano com os mesmos meses, não um mês sucessivo.

**Leia cada gráfico**

- **u / u′:** compare a taxa observada com os limites inferior (LIC) e superior (LSC). Um ponto fora dos limites sinaliza um resultado que se afasta da variação esperada. O u′ amplia os limites quando o histórico mostra variação adicional.
- **EWMA:** acompanha uma taxa suavizada, com mais peso para os resultados recentes. Pode sinalizar mudanças pequenas e persistentes quando a linha ultrapassa seus limites.
- **CUSUM:** a linha **+** acumula desvios na direção de aumento; a linha **−**, na direção de redução. Ao ultrapassar **H**, surge um sinal e a acumulação é reiniciada para a próxima observação.
- **Canal histórico por quartis:** compara um quadrimestre completo ou um acumulado desde janeiro com o mesmo período histórico. As zonas descrevem a posição em relação a Q1, mediana e Q3. Aqui, **Q1 e Q3 são quartis do histórico, não quadrimestres**. A posição não comprova sucesso de uma política nem ausência de problema.
- **Funil municipal:** cada ponto é um município; a posição horizontal mostra sua população e a vertical, sua taxa. Os limites consideram a maior oscilação esperada em populações pequenas. Os limites de 99,8% são mais amplos que os de 95%. Observe os pontos fora dos limites e os avisos de dispersão, sem transformar o gráfico em ranking.

**Use os sinais para orientar a investigação**

Triângulos vermelhos marcam sinais de aumento; azuis, de redução. No CUSUM, a linha “−” subir indica evidência acumulada de redução. O resumo mantém os métodos separados: eles usam os mesmos dados e não são confirmações independentes. Sem sinal não significa ausência de necessidade de atenção.

O histórico compara o território consigo mesmo. O funil compara municípios com o conjunto selecionado no período atual. Comece pelo ES e pelas regiões; depois localize municípios no funil e selecione um município para examinar seu histórico. Com apenas um município, o funil não oferece comparação entre territórios.

**Contagens e comparabilidade**

Óbitos esperados são uma expectativa do modelo sob a referência territorial, não uma quantidade aceitável de mortes. Poucos eventos podem alterar muito uma taxa e reduzir a capacidade de detectar mudanças. As taxas municipais não ajustam todas as diferenças demográficas e sociais. Confira contagens, população e contexto antes de investigar causas.

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
    extracao = meta.get('extracoes', {}).get(str(ano), {})
    populacao = meta.get('populacao', {}).get(str(ano), {})
    disponiveis = extracao.get('meses', [])
    data_extracao = pd.to_datetime(extracao.get('data'), errors='coerce', utc=True)
    data_texto = data_extracao.strftime('%d/%m/%Y %H:%M UTC') if pd.notna(data_extracao) else 'Não informada'
    with st.container(border=True):
        st.markdown(f'**Situação dos dados · {ano}**')
        st.write('Meses disponíveis: '+(', '.join(map(str, disponiveis)) or 'Não informados')+'. Extração: '+data_texto+'.')
        st.write('População de '+str(populacao.get('ano_fonte', 'ano não informado'))+' · '+
                 ('denominador provisório.' if populacao.get('provisorio') else 'sem indicação de provisoriedade.'))
        st.caption(extracao.get('revisao', 'Situação de revisão dos registros não informada.'))
    candidatos = [y for y in sorted(meta['anos_disponiveis']) if y < ano and cobertura_completa(f, y, meses)]
    if len(candidatos) < 5:
        st.info('São necessários pelo menos cinco anos completos anteriores ao ano selecionado.'); return
    padrao = candidatos[-6:-1] if len(candidatos) >= 6 else candidatos[-5:]
    with st.expander('Referência histórica e parâmetros', expanded=False):
        protocolo = st.radio('Configuração da análise', ['Exploratória', 'Protocolo do TCC'],
                             key='monitor_protocolo', horizontal=True)
        if protocolo == 'Protocolo do TCC':
            anos = list(range(2016, 2023))
            peso, largura, k, h = .2, 3., .5, 5.
            st.caption('Referência fixa 2016–2022 · λ=0,20 · L=3 · K=0,5 · H=5. '
                       'A comparação com o experimento requer também indicador, território, sexo e meses equivalentes.')
        else:
            anos = st.multiselect('Anos da fase I (cinco a sete consecutivos)', candidatos, default=padrao, key='monitor_anos')
            peso = st.slider('Peso λ do EWMA', .05, 1., .2, .05,
                             help='Menor peso preserva mais memória; maior peso privilegia a taxa recente.')
            largura = st.number_input('Largura L dos limites', min_value=1., max_value=6., value=3., step=.1,
                                      help='Amplia ou estreita os limites de u/u′ e EWMA. Não altera o funil nem H do CUSUM.')
            k = st.number_input('Folga K do CUSUM (desvios-padrão)', min_value=.1, value=.5, step=.1,
                                help='Folga descontada em cada passo. Maior K dificulta acumular desvios pequenos.')
            h = st.number_input('Intervalo H do CUSUM (desvios-padrão)', min_value=.1, value=5., step=.1,
                                help='Limiar da soma acumulada; não representa quantidade de óbitos ou anos.')
        st.caption('Parâmetros exploratórios. A calibração deve anteceder a avaliação; escolher parâmetros depois de observar os sinais invalida estimativas de desempenho.')
    if any(y not in candidatos for y in anos):
        st.info('A referência escolhida exige anos completos anteriores ao ano avaliado. '
                'Para o protocolo do TCC, selecione um ano posterior a 2022 com cobertura de 2016–2022.'); return
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
    t['Direção controle'] = direcao(t[TAXA], t['LIC controle'], t['LSC controle'])
    t['Direção EWMA'] = direcao(t['EWMA'], t['LIC EWMA'], t['LSC EWMA'])
    ultimo = t.iloc[-1]
    st.markdown(f'**Sinais do último período disponível · {int(ultimo["Ano"])}**')
    st.dataframe(pd.DataFrame([
        {'Método': ultimo['Método controle'], 'Resultado': ultimo['Direção controle']},
        {'Método': 'EWMA', 'Resultado': ultimo['Direção EWMA']},
        {'Método': 'CUSUM +', 'Resultado': 'Aumento acumulado' if ultimo['Sinal CUSUM +'] else 'Sem sinal'},
        {'Método': 'CUSUM −', 'Resultado': 'Redução acumulada' if ultimo['Sinal CUSUM −'] else 'Sem sinal'},
    ]).assign(**{
        'Taxa observada': float(ultimo[TAXA]),
        'Óbitos observados': int(ultimo['Óbitos']),
        'População (denominador anual)': int(ultimo['População']),
    }), hide_index=True, width='stretch', column_config={
        'Taxa observada': st.column_config.NumberColumn(format='%.2f'),
        'Óbitos observados': st.column_config.NumberColumn(format='%d'),
        'População (denominador anual)': st.column_config.NumberColumn(format='%d'),
    })
    st.caption('A taxa, os óbitos observados e o denominador anual correspondem ao mesmo período e recorte em todas as linhas.')
    st.caption('Métodos apresentados separadamente, sem pontuação de risco. Concordância não é confirmação independente. '
               'Reduções também exigem conferir revisões dos registros; sem sinal não significa ausência de problema.')
    with st.expander('Consultar os anos usados como referência'):
        st.dataframe(base, hide_index=True, width='stretch')
        st.download_button('Baixar referência histórica (CSV)', base.to_csv(index=False,sep=';',decimal=',').encode('utf-8-sig'),
                           'referencia_historica.csv', 'text/csv')
    grafico(t, TAXA, 'LIC controle', 'LSC controle', str(t['Método controle'].iloc[0]), ref.taxa, base=base)
    grafico(t, 'EWMA', 'LIC EWMA', 'LSC EWMA', 'EWMA · mudanças persistentes', ref.taxa, base=base)
    st.caption('Em cinza, taxas observadas da fase I; EWMA calculado somente na fase II. '
               'Triângulos vermelhos: aumento; azuis: redução. Um passo corresponde aos mesmos meses de um ano.')
    fig = go.Figure()
    for col, cor, simbolo in [('CUSUM +','#bd4545','triangle-up'), ('CUSUM −','#2563eb','triangle-down')]:
        fig.add_trace(go.Scatter(x=t['Ano'], y=t[col], mode='lines+markers', name=col, line=dict(color=cor)))
        sub = t.loc[t['Sinal '+col]]
        fig.add_trace(go.Scatter(x=sub['Ano'],y=sub[col],mode='markers',name='Sinal '+col,
                                marker=dict(color=cor,symbol=simbolo,size=13)))
    fig.add_hline(y=h, line_dash='dash', annotation_text='H')
    fig.update_layout(title='CUSUM · aumentos e reduções', yaxis_title='Desvios-padrão acumulados', height=400)
    fig.update_xaxes(dtick=1,tickformat='d')
    st.plotly_chart(fig, width='stretch')
    st.caption('CUSUM reiniciado após qualquer sinal. EWMA inicia na média histórica; σ usa a variabilidade das taxas históricas, com piso Poisson. Estes gráficos de memória pressupõem referência estável.')
    st.caption('CUSUM − crescente significa evidência acumulada de redução. H mede desvios-padrão acumulados, não óbitos.')
    canonicos = [list(range(a,b)) for a,b in [(1,5),(5,9),(9,13),(1,9),(1,13)]]
    if list(meses) in canonicos:
        t['Zona canal'] = t['Zona canal'].replace({'Êxito':'Abaixo de Q1', 'Segurança':'De Q1 à mediana',
                                                 'Alerta':'Acima da mediana até Q3'})
        grafico(t, TAXA, 'Q1', 'Q3', 'Canal histórico por quartis · mesmo período', ref.mediana, base=base, destacar=False)
        st.caption('Adaptação do canal endêmico: as zonas descrevem a posição histórica, sem confirmar epidemia, '
                   'sucesso de políticas ou ausência de problema. Quartis não são limites de controle e não têm taxa nominal de falso alarme de 0,2%.')
    else:
        t['Zona canal']='Não aplicável ao recorte'
        st.info('O canal histórico por quartis é apresentado para quadrimestres completos ou acumulados desde janeiro. Ajuste a seleção de meses para utilizá-lo.')
    st.dataframe(t, hide_index=True, width='stretch')
    st.download_button('Baixar sinais e limites (CSV)', t.to_csv(index=False,sep=';',decimal=',').encode('utf-8-sig'), 'monitoramento_estatistico.csv','text/csv')
    manifesto = dict(referencia=asdict(ref), meses=list(meses), peso=peso, largura=largura, k=k, h=h,
                     indicador=indicador,sexo_filtro=sexo_filtro,territorio=territorio,configuracao=protocolo,
                     unidade_temporal='anos de períodos equivalentes',
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
    if len(ft) < 2:
        st.info('Com apenas um município, ele compõe sozinho a referência do funil. '
                'Selecione mais municípios ou a região inteira para comparar territórios; use os gráficos acima para o histórico individual.')
        return
    ft['Óbitos esperados'] = ft['Referência'] * ft['População'] / 100000
    ft['Diferença observado − esperado'] = ft['Óbitos'] - ft['Óbitos esperados']
    for nivel in ['95%', '99,8%']:
        ft['Direção '+nivel] = direcao(ft[TAXA], ft['LIC '+nivel], ft['LSC '+nivel])
        # A decisão exata já foi feita em contagens; preserve-a nas fronteiras de ponto flutuante.
        ft.loc[~ft['Sinal '+nivel], 'Direção '+nivel] = 'Sem sinal'
        ft['Direção ajustada '+nivel] = direcao(ft[TAXA], ft['LIC ajustado '+nivel], ft['LSC ajustado '+nivel])
    ft = ft.sort_values('População')
    st.caption('O histórico compara o território consigo mesmo; o funil compara municípios entre si no período atual. '
               'Óbitos esperados são uma expectativa estatística sob a referência, não uma quantidade aceitável de mortes. '
               'As taxas não ajustam todas as diferenças demográficas e sociais entre municípios.')
    st.info('Poucos óbitos podem produzir grandes mudanças na taxa. Ausência de sinal também pode refletir baixa capacidade '
            'de detectar alterações. Não há corte universal de contagem: confira população, eventos e contexto territorial.')
    fig = go.Figure()
    for nivel in ['95%', '99,8%']:
        for lado in ['LIC','LSC']:
            fig.add_trace(go.Scatter(x=ft['População'],y=ft[lado+' '+nivel],name=lado+' '+nivel,mode='lines',line=dict(dash='dot' if nivel=='95%' else 'dash')))
    for sentido, cor, simbolo in [('Sem sinal','#126c83','circle'), ('Aumento','#bd4545','triangle-up'), ('Redução','#2563eb','triangle-down')]:
        sub = ft.loc[ft['Direção 99,8%'].eq(sentido)]
        fig.add_trace(go.Scatter(x=sub['População'],y=sub[TAXA],mode='markers',name=sentido+' · 99,8%',
                                marker=dict(color=cor,symbol=simbolo,size=11),text=sub['no_municipio'],
                                customdata=sub[['Óbitos','Óbitos esperados','Diferença observado − esperado','Direção 95%','Direção ajustada 99,8%']],
                                hovertemplate='%{text}<br>População: %{x}<br>Taxa: %{y:.2f}<br>Óbitos observados: %{customdata[0]}'
                                '<br>Esperados pelo modelo: %{customdata[1]:.2f}<br>Observado − esperado: %{customdata[2]:.2f}'
                                '<br>Limites de 95%: %{customdata[3]}<br>Ajustado aproximado 99,8%: %{customdata[4]}<extra></extra>'))
    fig.add_hline(y=float(ft['Referência'].iloc[0]),line_dash='dot')
    fig.update_layout(height=450,xaxis_title='População anual elegível',yaxis_title='Taxa por 100 mil')
    st.plotly_chart(fig,width='stretch')
    phi = float(ft['Dispersão territorial'].iloc[0])
    if phi>1:
        st.warning(f'Dispersão territorial φ={phi:.2f}. Os limites exatos Poisson podem produzir sinais adicionais por heterogeneidade. A tabela inclui limites ajustados aproximados como análise de sensibilidade; não são limites exatos.')
    principais = ['no_municipio','Óbitos','Óbitos esperados','Diferença observado − esperado','População',TAXA,
                  'Direção 95%','Direção 99,8%','Direção ajustada 99,8%']
    ft = ft[principais + [c for c in ft if c not in principais]]
    st.dataframe(ft.sort_values('no_municipio'),hide_index=True,width='stretch', column_config={
        'no_municipio': st.column_config.TextColumn('Município'),
        'Óbitos esperados': st.column_config.NumberColumn(format='%.2f'),
        'Diferença observado − esperado': st.column_config.NumberColumn(format='%.2f'),
        TAXA: st.column_config.NumberColumn(format='%.2f'),
    })
    st.download_button('Baixar gráfico de funil (CSV)',ft.sort_values('no_municipio').to_csv(index=False,sep=';',decimal=',').encode('utf-8-sig'),'funil_municipal.csv','text/csv')
    st.caption('Priorize o agregado estadual e regional. Múltiplas comparações ampliam alarmes falsos; 99,8% é limite por comparação, sem controle familiar. Dados agregados não permitem inferir risco individual ou causalidade.')
