from pathlib import Path
from decimal import Decimal, ROUND_HALF_UP
import gzip,json
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st
import streamlit.components.v1 as components
from mapa import mapa_html
from modelo import carregar,recortar,medidas,agrupado,INDICADORES,IDADES,meses_disponiveis,cobertura_completa,serie_historica,comparacao_mensal

st.set_page_config(page_title='Observatório de mortalidade | ES',page_icon='📊',layout='wide')
st.markdown('''<style>.block-container{padding-top:2rem} [data-testid="stMetric"]{background:#f1f5f9;border-radius:12px;padding:18px} h1{letter-spacing:-1px}</style>''',unsafe_allow_html=True)
@st.cache_data
def dados(versao):
    return carregar()
arquivos=list((Path(__file__).parent/'dados').glob('dataset.zip')) or list((Path(__file__).parent/'dados').iterdir())
versao=tuple((p.name,p.stat().st_mtime_ns) for p in arquivos if p.is_file())
f,p,g,meta=dados(versao)
g=g.merge(pd.read_csv(Path(__file__).parent/'dados/regioes_pdr2024.csv',dtype={'cod_mun_res':str}),on='cod_mun_res',validate='one_to_one')
fmt=lambda n,dec=0: f'{n:,.{dec}f}'.replace(',','X').replace('.',',').replace('X','.') if n is not None and pd.notna(n) else 'Sem denominador'
def rotulos(valores,medida):
    return [fmt(float(v),2 if medida=='Taxa por 100 mil' else 0) if pd.notna(v) else '' for v in valores]

CORES_SEXO = {'Masculino':'#2878B5','Feminino':'#D45479','Ignorado':'#8A9099'}
ORDEM_SEXO = ['Masculino','Feminino','Ignorado']
def fmt_razao(v):
    return fmt(Decimal(str(v)).quantize(Decimal('0.01'),rounding=ROUND_HALF_UP),2) if pd.notna(v) else 'Não definida'

with st.sidebar:
    st.title('Observatório • ES')
    st.caption('TCC · Engenharia de Produção · UFES\n\nDaniel Breda Bigossi')
    with st.form('filtros_painel'):
        indicador=st.selectbox('Indicador',list(INDICADORES))
        ano=st.selectbox('Ano',sorted(meta['anos_disponiveis'],reverse=True))
        quadrimestres=st.multiselect('Quadrimestres da análise',[1,2,3],default=sorted({(m-1)//4+1 for m in meses_disponiveis(f,max(meta['anos_disponiveis']))}),format_func=lambda q:f'{q}º quadrimestre',help='Selecione um, dois ou três quadrimestres e refine os meses abaixo.')
        meses_personalizados=st.multiselect('Meses personalizados',list(range(1,13)),default=list(range(1,13)),format_func=lambda m: ['Janeiro','Fevereiro','Março','Abril','Maio','Junho','Julho','Agosto','Setembro','Outubro','Novembro','Dezembro'][m-1],help='Sempre disponível. Entram na análise os meses marcados que pertencem aos quadrimestres selecionados. Mantenha todos para analisar os quadrimestres completos.')
        municipios=st.multiselect('Municípios',sorted(g.no_municipio),placeholder='Todos os municípios do ES')
        sexo_filtro=st.selectbox('Sexo',['Todos','Masculino','Feminino'],help='Filtra óbitos e população pelo mesmo sexo. Masculino não se aplica ao indicador de homicídios de mulheres.')
        st.form_submit_button('Atualizar',type='primary',width='stretch')
    st.caption('Escolha os filtros e clique em Atualizar para aplicá-los ao painel. Sem seleção municipal = todo o Espírito Santo.')
    st.caption('Regiões de saúde: PDR 2024, classificação fixa para comparar todos os anos.')
    st.info(meta['nota'])
cobertura=meses_disponiveis(f,ano)
meses_quadrimestres={m for q in quadrimestres for m in range((q-1)*4+1,q*4+1)}
meses=sorted(meses_quadrimestres & set(meses_personalizados))
periodo=' + '.join(f'{q}º quadrimestre' for q in sorted(quadrimestres)) or 'Nenhum quadrimestre'
nomes_meses_completos=['Janeiro','Fevereiro','Março','Abril','Maio','Junho','Julho','Agosto','Setembro','Outubro','Novembro','Dezembro']
if not meses:
    st.info('Selecione pelo menos um mês pertencente ao período e aos quadrimestres escolhidos.'); st.stop()
if not cobertura_completa(f,ano,meses):
    st.warning(f'O período selecionado contém meses ainda não disponíveis em {ano}. Meses disponíveis: '+', '.join(map(str,cobertura))+'. Escolha meses já disponíveis em Meses personalizados.')
    st.stop()
codigos=g[g.no_municipio.isin(municipios)].cod_mun_res.tolist() if municipios else g.cod_mun_res.tolist()
nf,np=recortar(f,p,indicador,codigos)
if INDICADORES[indicador]['sexo']=='Feminino' and sexo_filtro=='Masculino':
    st.title(indicador)
    st.info('Não aplicável: o filtro Masculino é incompatível com o indicador de homicídios de mulheres. Resultados nulos; selecione Feminino ou Todos.')
    for coluna,label in zip(st.columns(3),['Óbitos no período','Taxa por 100 mil','População anual de referência']):
        coluna.metric(label,'—')
    st.stop()
if sexo_filtro!='Todos':
    nf=nf[nf.sexo.eq(sexo_filtro)]
    np=np[np.sexo.eq(sexo_filtro)]
n,den,taxa=medidas(nf,np,ano,meses)
anterior=cobertura_completa(nf,ano-1,meses)
na,da,ta=medidas(nf,np,ano-1,meses) if anterior else (None,None,None)
delta=((taxa/ta)-1)*100 if ta and taxa is not None else None
st.title(indicador)
st.caption(f'{ano} · {periodo} · '+(', '.join(municipios) if municipios else 'Espírito Santo · 78 municípios'))
st.caption('Sexo: '+('Feminino' if INDICADORES[indicador]['sexo']=='Feminino' else sexo_filtro))
st.caption('Meses efetivamente analisados: '+', '.join(nomes_meses_completos[m-1] for m in meses)+'.')
st.write(INDICADORES[indicador]['descricao'])
if len(cobertura)<12:
    st.warning(f'{ano}: dados parciais, com cobertura de janeiro até o mês {max(cobertura)}. Meses seguintes não são zeros. Registros sujeitos a revisão.')
fonte=meta.get('populacao',{}).get(str(ano),{})
if fonte.get('provisorio'):
    st.info(f"Denominador provisório: população de {fonte['ano_fonte']} aplicada a {ano}, mantida constante, sem projeção.")
extracao=meta.get('extracoes',{}).get(str(ano),{})
if extracao:
    st.caption('Extração: '+str(extracao.get('data',''))+' · Fonte: SIM/SESA-ES · Sujeita a revisão.')
a,b,c=st.columns(3)
a.metric('Óbitos no período',fmt(n),f'{n-na:+d} versus {ano-1}' if anterior else None,delta_color='inverse')
b.metric('Taxa por 100 mil',fmt(taxa,2),f'{fmt(delta,1)}% sobre o ano anterior' if delta is not None else None,delta_color='inverse')
c.metric('População anual de referência',fmt(den))
st.caption('O denominador é anual, filtrado pelo município e pelo público do indicador. Taxas de períodos menores que um ano não são anualizadas. A variação compara os mesmos meses do ano anterior.')
tabs=st.tabs(['Evolução temporal','Distribuição territorial','Perfil demográfico','Dados e metodologia'])
with tabs[0]:
    st.subheader('Como o indicador evoluiu no mesmo período?')
    serie=serie_historica(nf,np,range(min(meta['anos_disponiveis']),max(meta['anos_disponiveis'])+1),meses)
    st.caption(f'Período aplicado em todos os anos: {periodo}. Meses: '+', '.join(map(str,meses))+'.')
    met=st.radio('Medida da série',['Taxa por 100 mil','Óbitos'],horizontal=True)
    fig=px.line(serie,x='Ano',y=met,markers=True,hover_data=['Óbitos','População'],color_discrete_sequence=['#126c83'])
    fig.update_traces(connectgaps=False,text=rotulos(serie[met],met),mode='lines+markers+text',textposition='top center',textfont={'size':12},cliponaxis=False); fig.update_xaxes(dtick=1); st.plotly_chart(fig,width='stretch')
    st.caption('Anos ou períodos sem cobertura completa aparecem como lacunas na série. O acumulado usa os mesmos meses do ano selecionado em todos os anos.')
    st.subheader('Ano anterior × ano selecionado')
    comparativo=comparacao_mensal(nf,np,ano,meses)
    anterior_m=comparativo[comparativo.Ano.eq(ano-1)]
    atual_m=comparativo[comparativo.Ano.eq(ano)]
    nomes_meses=['Jan','Fev','Mar','Abr','Mai','Jun','Jul','Ago','Set','Out','Nov','Dez']
    eixo=[nomes_meses[m-1] for m in meses]
    combinado=go.Figure()
    combinado.add_trace(go.Bar(x=eixo,y=anterior_m[met],name=f'{ano-1} · ano anterior',text=rotulos(anterior_m[met],met),textposition='inside',insidetextanchor='end',textfont={'size':12,'color':'#153147'},cliponaxis=False,marker_color='#9db7c4',customdata=anterior_m[['Óbitos','População']].values,hovertemplate='%{x}<br>'+met+': %{y:.2f}<br>Óbitos: %{customdata[0]}<br>População: %{customdata[1]:,.0f}<extra>%{fullData.name}</extra>'))
    combinado.add_trace(go.Scatter(x=eixo,y=atual_m[met],name=f'{ano} · ano selecionado',mode='lines+markers+text',text=rotulos(atual_m[met],met),textposition='top center',textfont={'size':12,'color':'#126c83'},cliponaxis=False,line={'color':'#126c83','width':3},connectgaps=False,customdata=atual_m[['Óbitos','População']].values,hovertemplate='%{x}<br>'+met+': %{y:.2f}<br>Óbitos: %{customdata[0]}<br>População: %{customdata[1]:,.0f}<extra>%{fullData.name}</extra>'))
    combinado.update_layout(xaxis_title='Mês',yaxis_title=met,hovermode='x unified',legend={'orientation':'h','y':1.15},yaxis={'rangemode':'tozero'},margin={'t':65,'b':55},xaxis={'type':'category','categoryorder':'array','categoryarray':eixo})
    st.plotly_chart(combinado,width='stretch')
    st.caption(f'Barras: {ano-1}. Linha: {ano}. Medida: {met}. Somente os meses selecionados, na mesma escala. Nas taxas mensais, cada ano utiliza sua população anual elegível.')
    if not anterior:
        st.info('O ano anterior não possui cobertura completa para esta comparação. Meses ausentes são lacunas, nunca zeros.')
    quad=[]
    for q in range(3):
        recorte=sorted(set(meses)&set(range(q*4+1,q*4+5)))
        if not recorte: continue
        nn,dd,tt=medidas(nf,np,ano,recorte)
        quad.append({'Quadrimestre':f'{q+1}º','Meses selecionados':', '.join(map(str,recorte)),'Óbitos':nn,'Taxa por 100 mil':tt,'Cobertura do recorte':'Meses disponíveis' if nn is not None else 'Indisponível ou incompleto'})
    st.dataframe(pd.DataFrame(quad),hide_index=True,width='stretch',column_config={'Taxa por 100 mil':st.column_config.NumberColumn(format='%.2f')})
with tabs[1]:
    st.subheader('Onde se concentram os óbitos e as maiores taxas?')
    territorial=agrupado(nf,np,ano,meses,['cod_mun_res']).merge(g,on='cod_mun_res',how='left')
    ordem=st.radio('Ordenar municípios por',['Óbitos','Taxa por 100 mil'],horizontal=True)
    top=territorial.sort_values(ordem,ascending=False).head(15).sort_values(ordem)
    top['Rótulo']=rotulos(top[ordem],ordem)
    st.plotly_chart(px.bar(top,x=ordem,y='no_municipio',orientation='h',text='Rótulo',hover_data=['Óbitos','População','Taxa por 100 mil'],labels={'no_municipio':'Município'},color_discrete_sequence=['#126c83']).update_traces(textposition='outside',cliponaxis=False).update_layout(margin={'r':90}),width='stretch')
    st.subheader('Mapa municipal do Espírito Santo')
    medida_mapa=st.radio('Medida do mapa',['Taxa por 100 mil','Óbitos'],horizontal=True)
    st.caption('Amplie com +, com a roda do mouse ou com dois dedos. Os nomes municipais aparecem ao ampliar; clique em um município para aproximar. As linhas escuras delimitam as regiões de saúde.')
    components.html(mapa_html(territorial,medida_mapa),height=720,scrolling=False)
    st.caption('Malha municipal: IBGE 2025. Divisas regionais: união dos municípios classificados no PDR 2024 pela SESA. Enquadramento continental. Cinza = fora do recorte ou sem taxa; zero permanece na escala. Taxas em populações pequenas podem oscilar com poucos eventos.')
    st.subheader('Participação dos óbitos por região de saúde')
    regional=territorial.groupby('regiao_saude',as_index=False)['Óbitos'].sum().rename(columns={'regiao_saude':'Região de saúde'})
    regional['Frequência relativa (%)']=regional['Óbitos']/n*100 if n else float('nan')
    regtab,regpie=st.columns([1,1.2])
    with regtab: st.dataframe(regional,hide_index=True,width='stretch',column_config={'Frequência relativa (%)':st.column_config.NumberColumn(format='%.1f%%')})
    with regpie:
        if n:
            figreg=px.pie(regional,names='Região de saúde',values='Óbitos',hole=.35,color='Região de saúde',color_discrete_map={'Norte':'#2878B5','Central':'#E69F00','Metropolitana':'#009E73','Sul':'#9B65AC'})
            figreg.update_traces(textinfo='label+percent',hovertemplate='%{label}<br>Óbitos: %{value}<br>Participação: %{percent}<extra></extra>')
            st.plotly_chart(figreg,width='stretch')
        else: st.info('Sem óbitos no recorte: frequência relativa não definida.')
    st.caption('Óbitos da região ÷ óbitos do indicador no recorte × 100. Respeita ano, meses, municípios e sexo. A participação descreve a distribuição dos óbitos, não o risco de morrer. PDR 2024 aplicado a toda a série.')
    st.dataframe(territorial[['no_municipio','Óbitos','População','Taxa por 100 mil']].sort_values(ordem,ascending=False),hide_index=True,width='stretch',column_config={'Taxa por 100 mil':st.column_config.NumberColumn(format='%.2f')})
with tabs[2]:
    st.subheader('Como os óbitos se distribuem por idade e sexo?')
    faixa_total = ('15 a 29 anos' if INDICADORES[indicador]['sexo'] is None else 'mulheres de 10 a 59 anos') if INDICADORES[indicador]['idades'] else 'todas as idades'
    st.markdown(f'**Indicador completo · {faixa_total}**')
    resumo=agrupado(nf,np,ano,meses,['faixa_etaria'])
    resumo=resumo.set_index('faixa_etaria').reindex(INDICADORES[indicador]['idades'] or IDADES).reset_index()
    resumo=resumo.rename(columns={'faixa_etaria':'Faixa etária'})
    resumo['Frequência relativa (%)']=resumo['Óbitos']/n*100 if n else float('nan')
    setores=resumo[resumo['Óbitos'].gt(0)].copy()
    resumo=pd.concat([resumo,pd.DataFrame([{'Faixa etária':f'TOTAL · {faixa_total}','Óbitos':n,'População':den,'Taxa por 100 mil':taxa,'Frequência relativa (%)':100.0 if n else float('nan')}])],ignore_index=True)
    altura_resumo=max(450,38+35*len(resumo))
    tabela_col,setores_col=st.columns([1.25,1],gap='large')
    with tabela_col:
        st.dataframe(resumo,hide_index=True,width='stretch',height=altura_resumo,row_height=35,column_config={'Óbitos':st.column_config.NumberColumn(format='%d'),'População':st.column_config.NumberColumn(format='%d'),'Taxa por 100 mil':st.column_config.NumberColumn(format='%.2f'),'Frequência relativa (%)':st.column_config.NumberColumn(format='%.1f%%')})
    with setores_col:
        st.markdown('**Participação das faixas etárias nos óbitos**')
        if n:
            pizza=px.pie(setores,names='Faixa etária',values='Óbitos',color='Faixa etária',color_discrete_map=dict(zip(IDADES,px.colors.qualitative.Safe+['#8A9099'])),hole=0.35)
            pizza.update_traces(textinfo='percent',textposition='inside',sort=False,hovertemplate='%{label}<br>Óbitos: %{value}<br>Participação: %{percent}<extra></extra>')
            pizza.update_layout(height=altura_resumo-25,margin={'l':5,'r':5,'t':10,'b':10},legend={'orientation':'h','y':-0.12,'x':0},uniformtext_minsize=10,uniformtext_mode='hide')
            st.plotly_chart(pizza,width='stretch')
        else:
            st.info('Sem óbitos no recorte: a frequência relativa não é definida.')
    st.caption('Frequência relativa = óbitos da faixa ÷ total de óbitos do indicador no recorte × 100. A tabela e os setores respeitam ano, meses, municípios e sexo. O total mantém todas as idades elegíveis. A taxa total usa a soma das populações anuais elegíveis; não é a soma das taxas por idade.')
    st.caption('Os filtros de idade abaixo alteram apenas os gráficos exploratórios; o total do indicador permanece completo. Cores fixas: masculino em azul, feminino em rosa e sexo ignorado em cinza.')
    elegiveis=INDICADORES[indicador]['idades'] or IDADES
    idades=st.multiselect('Faixas etárias da análise',elegiveis,default=elegiveis)
    ef=nf[nf.faixa_etaria.isin(idades)]; ep=np[np.faixa_etaria.isin(idades)]
    dem=agrupado(ef,ep,ano,meses,['faixa_etaria','sexo'])
    metdem=st.radio('Medida demográfica',['Óbitos','Taxa por 100 mil'],horizontal=True)
    dem['Rótulo']=rotulos(dem[metdem],metdem)
    st.plotly_chart(px.bar(dem,x='faixa_etaria',y=metdem,text='Rótulo',color='sexo',color_discrete_map=CORES_SEXO,barmode='group',category_orders={'faixa_etaria':IDADES,'sexo':ORDEM_SEXO},labels={'faixa_etaria':'Faixa etária','sexo':'Sexo'},hover_data=['Óbitos','População']).update_traces(textposition='outside',cliponaxis=False,textfont={'size':10}).update_layout(height=500),width='stretch')
    st.caption('As faixas têm amplitudes diferentes. Idade ou sexo ignorado não possui denominador correspondente e, portanto, não recebe taxa.')
    pir=dem[dem.sexo.isin(['Masculino','Feminino'])].copy()
    pir['Óbitos espelhados']=pir['Óbitos'].where(pir.sexo=='Feminino',-pir['Óbitos'])
    pir['Rótulo']=rotulos(pir['Óbitos'],'Óbitos')
    st.plotly_chart(px.bar(pir,y='faixa_etaria',x='Óbitos espelhados',text='Rótulo',color='sexo',color_discrete_map=CORES_SEXO,orientation='h',barmode='relative',category_orders={'faixa_etaria':IDADES,'sexo':ORDEM_SEXO},hover_data={'Óbitos':True,'Óbitos espelhados':False},labels={'faixa_etaria':'Faixa etária','sexo':'Sexo'}).update_traces(textposition='outside',cliponaxis=False).update_layout(margin={'l':80,'r':80}),width='stretch')
    st.caption('Distribuição espelhada de óbitos: o sinal negativo apenas posiciona os homens à esquerda. Este gráfico não é uma pirâmide da população residente.')
    if indicador=='Suicídio geral':
        st.subheader('Razão entre os sexos nos óbitos por suicídio')
        if sexo_filtro!='Todos':
            st.info('Selecione Sexo = Todos para calcular a razão entre masculino e feminino.')
        else:
            cont=nf[nf.ano.eq(ano)&nf.mes.isin(meses)&nf.faixa_etaria.isin(idades)].groupby(['faixa_etaria','sexo']).Obitos.sum().unstack(fill_value=0)
            cont=cont.reindex(idades,fill_value=0)
            cont['Masculino']=cont.get('Masculino',0);cont['Feminino']=cont.get('Feminino',0)
            cont['Razão M/F']=cont['Masculino'].div(cont['Feminino'].where(cont['Feminino'].gt(0)))
            razoes=cont.reset_index().rename(columns={'faixa_etaria':'Faixa etária'})
            validas=razoes[razoes['Razão M/F'].notna()].sort_values('Razão M/F')
            if not validas.empty:
                figsexo=px.bar(validas,x='Razão M/F',y='Faixa etária',orientation='h',text=[fmt_razao(v) for v in validas['Razão M/F']],hover_data=['Masculino','Feminino'],color_discrete_sequence=['#2878B5'])
                figsexo.update_traces(textposition='outside',cliponaxis=False)
                figsexo.add_vline(x=1,line_dash='dot',line_color='#687787',annotation_text='1 = igualdade',annotation_position='top')
                figsexo.update_layout(height=max(420,len(validas)*42+90),margin={'r':90,'t':50},xaxis_title='Óbitos masculinos por óbito feminino',yaxis_title='Faixa etária',xaxis_range=[0,max(1.25,float(validas['Razão M/F'].max())*1.2)])
                st.plotly_chart(figsexo,width='stretch')
            else: st.info('Não há óbitos femininos nas faixas selecionadas: razão não definida.')
            razoes['Razão M/F']=razoes['Razão M/F'].apply(fmt_razao)
            st.dataframe(razoes[['Faixa etária','Masculino','Feminino','Razão M/F']],hide_index=True,width='stretch')
            st.caption('Razão = óbitos masculinos ÷ óbitos femininos da mesma faixa etária. 7 = sete óbitos masculinos para cada feminino; 0,50 = um masculino para cada dois femininos. 1 indica igualdade entre contagens. Respeita ano, meses, municípios e as faixas etárias da análise. Sexo ignorado excluído. Sem óbitos femininos, inclusive 0/0, a razão não é definida. Não é uma razão de taxas ou uma comparação de risco.')
    st.subheader('Distribuição dos óbitos por raça/cor')
    arquivo_raca=Path(__file__).parent/'dados/f_raca_cor.csv.gz'
    if arquivo_raca.exists():
        @st.cache_data
        def carregar_raca(versao_raca):
            return pd.read_csv(arquivo_raca,dtype={'cod_mun_res':str})
        rcmeta=json.loads((Path(__file__).parent/'dados/raca_cor_meta.json').read_text())
        st.caption('Fonte: SIM/SESA-ES · Extração de raça/cor: '+rcmeta['extraido_utc'][:10]+' · Sujeita a revisão.')
        rc=carregar_raca(arquivo_raca.stat().st_mtime_ns)
        rc=rc[rc.indicador.eq(indicador)&rc.ano.eq(ano)&rc.mes.isin(meses)&rc.cod_mun_res.isin(codigos)]
        if sexo_filtro!='Todos': rc=rc[rc.sexo.eq(sexo_filtro)]
        if rc.empty or not set(meses).issubset(set(rc.mes)):
            st.info('Raça/cor ainda sem cobertura completa para este recorte.')
        else:
            rct=rc.groupby('raca_cor',as_index=False).Obitos.sum().rename(columns={'raca_cor':'Raça/cor','Obitos':'Óbitos'})
            totalrc=int(rct['Óbitos'].sum());rct['Frequência relativa (%)']=rct['Óbitos']/totalrc*100 if totalrc else float('nan')
            if totalrc!=n: st.warning(f'Esta extração de raça/cor soma {totalrc} óbitos; a base anterior do indicador soma {n}. Há divergência entre as bases, registrada na auditoria. As proporções abaixo usam o total desta extração.')
            residual=int(rct.loc[rct['Raça/cor'].eq('Sem classificação disponível na tabulação'),'Óbitos'].sum())
            if residual: st.info(f'{residual} óbito(s) não aparecem nas sete categorias de raça/cor tabuladas pela fonte. A diferença para o total sem filtro racial é exibida separadamente, sem atribuir raça/cor.')
            figrc=px.bar(rct.sort_values('Óbitos'),y='Raça/cor',x='Óbitos',orientation='h',text='Óbitos',hover_data=['Frequência relativa (%)'],color_discrete_sequence=['#126c83']).update_layout(height=460,margin={'r':70})
            figrc.update_traces(textposition='outside',cliponaxis=False);st.plotly_chart(figrc,width='stretch')
            st.dataframe(rct,hide_index=True,width='stretch',column_config={'Frequência relativa (%)':st.column_config.NumberColumn(format='%.1f%%')})
            st.caption('Raça/cor registrada no SIM/SESA-ES. Frequência relativa sobre todos os óbitos do indicador nesta extração, incluindo Não informado, Ignorado e o residual sem classificação na tabulação. O residual é calculado por diferença, não é uma categoria racial atribuída. Respeita ano, meses, municípios e sexo; mantém todas as idades elegíveis do indicador. Não se calcula taxa por raça/cor sem população correspondente.')
    else:
        st.info('Extração de raça/cor em preparação; nenhum valor ausente foi convertido em zero.')
with tabs[3]:
    st.subheader('Definições e disponibilidade')
    st.write('Fonte dos arquivos locais: SIM/DATASUS e base populacional utilizada no ETL do TCC. Recorte por município de residência no Espírito Santo.')
    st.warning(meta['nota'])
    st.markdown('**Taxa = óbitos do período ÷ população anual elegível × 100.000.** Cada registro da fato representa município, mês, causa, faixa etária e sexo. A granularidade mensal permite consolidar os três quadrimestres e investigar variações dentro de cada período.')
    st.write('Raça/cor usa uma fato complementar por indicador, município, mês e sexo, com idades elegíveis selecionadas na extração. Cada categoria é reconciliada com controles do TabNet; diferenças contra a base anterior são sinalizadas. Não possui população por raça/cor para cálculo de taxas.')
    st.markdown('Regiões: [PDR 2024 — SESA](https://saude.es.gov.br/GrupodeArquivos/plano-diretor-de-regionalizacao_pdr-es-2024). A classificação dos municípios do PDR 2024 é fixa em toda a série, para comparabilidade territorial.')
    st.write('As populações não são somadas entre meses. Os indicadores de homicídio de jovens e mulheres podem se sobrepor: não some seus totais. A disponibilidade desta cópia não comprova a completude de toda a fonte administrativa.')
    st.write('Esta versão usa arquivos locais e não executa automaticamente o ETL. Atualização do aplicativo e atualização dos dados são processos distintos.')
    st.download_button('Baixar comparação mensal (CSV)',comparativo.to_csv(index=False,sep=';',decimal=',').encode('utf-8-sig'),'comparacao_mensal.csv','text/csv')
    st.download_button('Baixar série analisada (CSV)',serie.to_csv(index=False,sep=';',decimal=',').encode('utf-8-sig'),'serie_indicador.csv','text/csv')
    st.download_button('Baixar comparação municipal (CSV)',territorial[['no_municipio','Óbitos','População','Taxa por 100 mil']].to_csv(index=False,sep=';',decimal=',').encode('utf-8-sig'),'municipios_indicador.csv','text/csv')
    st.caption('Protótipo acadêmico · Daniel Breda Bigossi · UFES. Os resultados descrevem os registros disponíveis e não estabelecem relações causais.')
