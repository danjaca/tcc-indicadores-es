from pathlib import Path
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st
from modelo import carregar,recortar,medidas,agrupado,INDICADORES,IDADES,meses_disponiveis,cobertura_completa,serie_historica,comparacao_mensal

st.set_page_config(page_title='Observatório de mortalidade | ES',page_icon='📊',layout='wide')
st.markdown('''<style>.block-container{padding-top:2rem} [data-testid="stMetric"]{background:#f1f5f9;border-radius:12px;padding:18px} h1{letter-spacing:-1px}</style>''',unsafe_allow_html=True)
@st.cache_data
def dados(versao):
    return carregar()
arquivos=list((Path(__file__).parent/'dados').glob('dataset.zip')) or list((Path(__file__).parent/'dados').iterdir())
versao=tuple((p.name,p.stat().st_mtime_ns) for p in arquivos if p.is_file())
f,p,g,meta=dados(versao)
fmt=lambda n,dec=0: f'{n:,.{dec}f}'.replace(',','X').replace('.',',').replace('X','.') if n is not None and pd.notna(n) else 'Sem denominador'
with st.sidebar:
    st.title('Observatório • ES')
    st.caption('TCC · Engenharia de Produção · UFES\n\nDaniel Breda Bigossi')
    with st.form('filtros_painel'):
        indicador=st.selectbox('Indicador',list(INDICADORES))
        ano=st.selectbox('Ano',sorted(meta['anos_disponiveis'],reverse=True))
        periodo=st.radio('Período',['Acumulado disponível','Ano completo','1º quadrimestre','2º quadrimestre','3º quadrimestre','Meses personalizados'])
        meses_personalizados=st.multiselect('Meses personalizados',list(range(1,13)),default=list(range(1,13)),help='Utilizado somente quando o período escolhido é Meses personalizados.')
        municipios=st.multiselect('Municípios',sorted(g.no_municipio),placeholder='Todos os municípios do ES')
        st.form_submit_button('Atualizar',type='primary',width='stretch')
    st.caption('Escolha os filtros e clique em Atualizar para aplicá-los ao painel. Sem seleção municipal = todo o Espírito Santo.')
    st.caption('A base não contém agrupamento por região de saúde.')
    st.info(meta['nota'])
cobertura=meses_disponiveis(f,ano)
op={'Acumulado disponível':cobertura,'Ano completo':list(range(1,13)),'1º quadrimestre':list(range(1,5)),'2º quadrimestre':list(range(5,9)),'3º quadrimestre':list(range(9,13)),'Meses personalizados':meses_personalizados}
meses=sorted(op[periodo])
if not meses:
    st.info('Selecione pelo menos um mês para analisar.'); st.stop()
if not cobertura_completa(f,ano,meses):
    st.warning(f'O período selecionado contém meses ainda não disponíveis em {ano}. Meses disponíveis: '+', '.join(map(str,cobertura))+'. Selecione Acumulado disponível ou um período já coberto.')
    st.stop()
codigos=g[g.no_municipio.isin(municipios)].cod_mun_res.tolist() if municipios else g.cod_mun_res.tolist()
nf,np=recortar(f,p,indicador,codigos)
n,den,taxa=medidas(nf,np,ano,meses)
anterior=cobertura_completa(nf,ano-1,meses)
na,da,ta=medidas(nf,np,ano-1,meses) if anterior else (None,None,None)
delta=((taxa/ta)-1)*100 if ta and taxa is not None else None
st.title(indicador)
st.caption(f'{ano} · {periodo} · '+(', '.join(municipios) if municipios else 'Espírito Santo · 78 municípios'))
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
    fig.update_traces(connectgaps=False); fig.update_xaxes(dtick=1); st.plotly_chart(fig,width='stretch')
    st.caption('Anos ou períodos sem cobertura completa aparecem como lacunas na série. O acumulado usa os mesmos meses do ano selecionado em todos os anos.')
    st.subheader('Ano anterior × ano selecionado')
    comparativo=comparacao_mensal(nf,np,ano,meses)
    anterior_m=comparativo[comparativo.Ano.eq(ano-1)]
    atual_m=comparativo[comparativo.Ano.eq(ano)]
    nomes_meses=['Jan','Fev','Mar','Abr','Mai','Jun','Jul','Ago','Set','Out','Nov','Dez']
    eixo=[nomes_meses[m-1] for m in meses]
    combinado=go.Figure()
    combinado.add_trace(go.Bar(x=eixo,y=anterior_m[met],name=f'{ano-1} · ano anterior',marker_color='#9db7c4',customdata=anterior_m[['Óbitos','População']].values,hovertemplate='%{x}<br>'+met+': %{y:.2f}<br>Óbitos: %{customdata[0]}<br>População: %{customdata[1]:,.0f}<extra>%{fullData.name}</extra>'))
    combinado.add_trace(go.Scatter(x=eixo,y=atual_m[met],name=f'{ano} · ano selecionado',mode='lines+markers',line={'color':'#126c83','width':3},connectgaps=False,customdata=atual_m[['Óbitos','População']].values,hovertemplate='%{x}<br>'+met+': %{y:.2f}<br>Óbitos: %{customdata[0]}<br>População: %{customdata[1]:,.0f}<extra>%{fullData.name}</extra>'))
    combinado.update_layout(xaxis_title='Mês',yaxis_title=met,hovermode='x unified',legend={'orientation':'h','y':1.15},yaxis={'rangemode':'tozero'},xaxis={'type':'category','categoryorder':'array','categoryarray':eixo})
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
    st.plotly_chart(px.bar(top,x=ordem,y='no_municipio',orientation='h',hover_data=['Óbitos','População','Taxa por 100 mil'],labels={'no_municipio':'Município'},color_discrete_sequence=['#126c83']),width='stretch')
    mapa=territorial[territorial['Óbitos']>0].copy()
    if not mapa.empty:
        st.plotly_chart(px.scatter_map(mapa,lat='latitude',lon='longitude',size='Óbitos',color='Taxa por 100 mil',hover_name='no_municipio',hover_data=['Óbitos','População'],zoom=6,center={'lat':-19.6,'lon':-40.5},map_style='carto-positron',color_continuous_scale='OrRd',size_max=35),width='stretch')
    st.caption('Municípios sem óbitos não recebem bolhas. O mapa exige internet. Taxas em populações pequenas podem oscilar com poucos eventos; interprete contagem e população em conjunto.')
    st.dataframe(territorial[['no_municipio','Óbitos','População','Taxa por 100 mil']].sort_values(ordem,ascending=False),hide_index=True,width='stretch',column_config={'Taxa por 100 mil':st.column_config.NumberColumn(format='%.2f')})
with tabs[2]:
    st.subheader('Como os óbitos se distribuem por idade e sexo?')
    st.caption('Os filtros abaixo alteram apenas esta análise exploratória; os cartões acima preservam a definição do indicador.')
    elegiveis=INDICADORES[indicador]['idades'] or IDADES
    idades=st.multiselect('Faixas etárias da análise',elegiveis,default=elegiveis)
    ef=nf[nf.faixa_etaria.isin(idades)]; ep=np[np.faixa_etaria.isin(idades)]
    dem=agrupado(ef,ep,ano,meses,['faixa_etaria','sexo'])
    metdem=st.radio('Medida demográfica',['Óbitos','Taxa por 100 mil'],horizontal=True)
    st.plotly_chart(px.bar(dem,x='faixa_etaria',y=metdem,color='sexo',barmode='group',category_orders={'faixa_etaria':IDADES},labels={'faixa_etaria':'Faixa etária','sexo':'Sexo'},hover_data=['Óbitos','População']),width='stretch')
    st.caption('As faixas têm amplitudes diferentes. Idade ou sexo ignorado não possui denominador correspondente e, portanto, não recebe taxa.')
    pir=dem[dem.sexo.isin(['Masculino','Feminino'])].copy()
    pir['Óbitos espelhados']=pir['Óbitos'].where(pir.sexo=='Feminino',-pir['Óbitos'])
    st.plotly_chart(px.bar(pir,y='faixa_etaria',x='Óbitos espelhados',color='sexo',orientation='h',barmode='relative',category_orders={'faixa_etaria':IDADES},hover_data={'Óbitos':True,'Óbitos espelhados':False},labels={'faixa_etaria':'Faixa etária','sexo':'Sexo'}),width='stretch')
    st.caption('Distribuição espelhada de óbitos: o sinal negativo apenas posiciona os homens à esquerda. Este gráfico não é uma pirâmide da população residente.')
with tabs[3]:
    st.subheader('Definições e disponibilidade')
    st.write('Fonte dos arquivos locais: SIM/DATASUS e base populacional utilizada no ETL do TCC. Recorte por município de residência no Espírito Santo.')
    st.warning(meta['nota'])
    st.markdown('**Taxa = óbitos do período ÷ população anual elegível × 100.000.** Cada registro da fato representa município, mês, causa, faixa etária e sexo. A granularidade mensal permite consolidar os três quadrimestres e investigar variações dentro de cada período.')
    st.write('As populações não são somadas entre meses. Os indicadores de homicídio de jovens e mulheres podem se sobrepor: não some seus totais. A disponibilidade desta cópia não comprova a completude de toda a fonte administrativa.')
    st.write('Esta versão usa arquivos locais e não executa automaticamente o ETL. Atualização do aplicativo e atualização dos dados são processos distintos.')
    st.download_button('Baixar comparação mensal (CSV)',comparativo.to_csv(index=False,sep=';',decimal=',').encode('utf-8-sig'),'comparacao_mensal.csv','text/csv')
    st.download_button('Baixar série analisada (CSV)',serie.to_csv(index=False,sep=';',decimal=',').encode('utf-8-sig'),'serie_indicador.csv','text/csv')
    st.download_button('Baixar comparação municipal (CSV)',territorial[['no_municipio','Óbitos','População','Taxa por 100 mil']].to_csv(index=False,sep=';',decimal=',').encode('utf-8-sig'),'municipios_indicador.csv','text/csv')
    st.caption('Protótipo acadêmico · Daniel Breda Bigossi · UFES. Os resultados descrevem os registros disponíveis e não estabelecem relações causais.')
