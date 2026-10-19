from configuracao import DADOS
"""Apresentação dos meios por CID-10, com cobertura e denominador de frequência explícitos."""
from pathlib import Path
import json
import textwrap
import pandas as pd
import plotly.graph_objects as go
import streamlit as st

@st.cache_data
def carregar_meios(arquivo,versao):
    return pd.read_csv(arquivo,dtype={'cod_mun_res':str})

def resumo_meios(fato,meta,indicador,ano,meses,codigos,sexo):
    if not set(meses).issubset(meta['cobertura'].get(str(ano),[])) or not meses:
        return None,None
    recorte=fato[fato.indicador.eq(indicador)&fato.ano.eq(ano)&fato.mes.isin(meses)&fato.cod_mun_res.isin(codigos)]
    if sexo!='Todos':recorte=recorte[recorte.sexo.eq(sexo)]
    detalhe=recorte.groupby('cid',as_index=False).Obitos.sum().merge(pd.DataFrame(meta['dimensao_cid']),on='cid',validate='one_to_one')
    total=int(detalhe.Obitos.sum())
    detalhe['Frequência relativa (%)']=detalhe.Obitos/total*100 if total else float('nan')
    grupos=detalhe.groupby('meio',as_index=False).agg(Obitos=('Obitos','sum'),CIDs=('cid',lambda s:', '.join(sorted(s))))
    grupos['Frequência relativa (%)']=grupos.Obitos/total*100 if total else float('nan')
    return grupos.sort_values(['Obitos','meio'],ascending=[False,True]),detalhe.sort_values(['Obitos','cid'],ascending=[False,True])

def comparacao_meios(atual,anterior):
    """Alinha categorias dos dois anos; zero só dentro de cobertura validada."""
    comp=atual[['meio','Obitos']].rename(columns={'Obitos':'Atual'})
    if anterior is None:
        comp['Anterior']=float('nan')
    else:
        comp=comp.merge(anterior[['meio','Obitos']].rename(columns={'Obitos':'Anterior'}),on='meio',how='outer').fillna(0)
    return comp.sort_values(['Atual','Anterior','meio'],ascending=[False,False,True])

def grafico_comparacao(comp,ano):
    nomes=comp.meio.tolist()
    fig=go.Figure()
    if comp.Anterior.notna().any():
        fig.add_bar(x=nomes,y=comp.Anterior.tolist(),name=f'{ano-1} · ano anterior',marker_color='#b2c4d0',text=comp.Anterior.astype(int).astype(str).tolist(),textposition='outside',textangle=0,cliponaxis=False,textfont={'color':'#455b6a','size':12},hovertemplate='%{x}<br>Óbitos: %{y}<extra>%{fullData.name}</extra>')
    fig.add_scatter(x=nomes,y=comp.Atual.tolist(),name=f'{ano} · ano selecionado',mode='lines+markers+text',line={'color':'#126c83','width':3},marker={'size':9},text=comp.Atual.astype(int).astype(str).tolist(),textposition='bottom center',textfont={'color':'#126c83','size':12},cliponaxis=False,hovertemplate='%{x}<br>Óbitos: %{y}<extra>%{fullData.name}</extra>')
    maior=float(comp[['Atual','Anterior']].max().max())
    fig.update_layout(height=620,margin={'l':45,'r':25,'t':70,'b':185},legend={'orientation':'h','x':0,'y':1.16},showlegend=True,yaxis={'title':'Óbitos','range':[0,max(1,maior*1.2)]},xaxis={'title':'Meio registrado','tickmode':'array','tickvals':nomes,'ticktext':['<br>'.join(textwrap.wrap(n,18)) for n in nomes],'tickangle':-35,'tickfont':{'size':11},'ticklabelstandoff':20,'automargin':True},hovermode='x unified')
    return fig

def mostrar_meios(indicador,ano,meses,codigos,sexo,total_principal):
    st.subheader('Quais meios estão registrados nos óbitos?')
    pasta=DADOS;arquivo=pasta/'f_meios_cid.csv.gz';metafile=pasta/'meios_cid_meta.json'
    if not arquivo.exists() or not metafile.exists():
        st.info('Detalhamento por CID-10 ainda sem extração disponível.');return
    meta=json.loads(metafile.read_text())
    fato=carregar_meios(str(arquivo),arquivo.stat().st_mtime_ns)
    grupos,detalhe=resumo_meios(fato,meta,indicador,ano,meses,codigos,sexo)
    if grupos is None:
        st.info('Meios por CID-10 ainda sem cobertura para o período selecionado.');return
    total=int(detalhe.Obitos.sum())
    st.caption('SIM/SESA-ES · CID-10 da causa básica · Extração: '+meta['extraido_utc'][:10]+'. Respeita ano, meses, municípios e sexo. Mantém todas as idades elegíveis do indicador.')
    if total!=total_principal:
        st.warning(f'Esta extração por CID soma {total} óbitos; a base principal soma {total_principal}. As frequências abaixo usam o total da extração por CID. Registros históricos podem divergir entre versões da fonte.')
    if not total:
        st.info('Sem óbitos no recorte da extração por CID: frequência relativa não definida.')
    fmt=lambda v,d=0:f'{v:,.{d}f}'.replace(',','X').replace('.',',').replace('X','.')
    if total:
        lideres=grupos.loc[grupos.Obitos.eq(grupos.Obitos.max())]
        st.write('Maior frequência no recorte: **'+'; '.join(lideres.meio)+'** — **'+fmt(lideres.Obitos.iloc[0])+' óbito(s)** por grupo ('+fmt(lideres['Frequência relativa (%)'].iloc[0],1)+'% do total).')
    anterior,_=resumo_meios(fato,meta,indicador,ano-1,meses,codigos,sexo)
    comp=comparacao_meios(grupos,anterior)
    st.markdown('**Meios registrados · ano anterior × ano selecionado**')
    if anterior is None:st.info(f'{ano-1}: sem cobertura completa por CID para os mesmos meses; a série anterior não é apresentada como zero.')
    if not comp.empty:
        st.plotly_chart(grafico_comparacao(comp,ano),width='stretch',key='meios_cid_comparacao')
    st.caption(f'Barras: {ano-1}. Linha: {ano}. Meses aplicados aos dois anos: '+', '.join(str(m) for m in sorted(meses))+'. Mesmos municípios, sexo e idades elegíveis. Cada ano usa sua extração por CID. A linha conecta categorias de meios, não representa passagem do tempo.')
    if total:
        st.markdown(f'**Participação dos meios registrados nos óbitos · {ano}**')
        pie=go.Figure(go.Pie(labels=grupos.meio.tolist(),values=grupos.Obitos.tolist(),sort=False,text=[fmt(n)+' · '+fmt(p,1)+'%' for n,p in zip(grupos.Obitos,grupos['Frequência relativa (%)'])],textinfo='text',textposition='outside',hovertemplate='%{label}<br>%{value} óbitos<br>%{percent}<extra></extra>',marker={'colors':['#126c83','#e6a23c','#697ea5','#ab728e','#709c82','#a18a64','#9b8271','#789ba3','#b98c93','#828b96']},showlegend=True))
        pie.update_layout(height=max(520,370+len(grupos)*23),margin={'l':15,'r':15,'t':15,'b':15},legend={'orientation':'h','x':0,'y':-0.08,'font':{'size':12}},uniformtext={'minsize':11,'mode':'show'})
        st.plotly_chart(pie,width='stretch',key='meios_cid_setores')
    st.caption('Participação = óbitos do grupo de meios ÷ total de óbitos desta extração × 100. Grupos não se sobrepõem. Meios não especificados permanecem no total. A análise descreve registros de óbitos, não todas as tentativas de suicídio ou ocorrências de violência.')
    if not total:return
    st.markdown('**Detalhamento por código CID-10**')
    tab=detalhe.rename(columns={'cid':'CID-10','descricao_cid':'Descrição na fonte','meio':'Grupo de meios','Obitos':'Óbitos'})[['CID-10','Descrição na fonte','Grupo de meios','Óbitos','Frequência relativa (%)']]
    tab=pd.concat([tab,pd.DataFrame([{'CID-10':'TOTAL','Descrição na fonte':'Todos os códigos do indicador no recorte','Grupo de meios':'','Óbitos':total,'Frequência relativa (%)':100.0}])],ignore_index=True)
    st.dataframe(tab,hide_index=True,width='stretch',row_height=35,height=46+35*len(tab),column_config={'Frequência relativa (%)':st.column_config.NumberColumn(format='%.1f%%'),'Óbitos':st.column_config.NumberColumn(format='%d')})
    st.download_button('Baixar meios por CID-10 (CSV)',tab.to_csv(index=False,sep=';',decimal=',').encode('utf-8-sig'),'meios_cid.csv','text/csv')
