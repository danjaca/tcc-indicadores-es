"""Apresentação dos meios por CID-10, com cobertura e denominador de frequência explícitos."""
from pathlib import Path
import json
import pandas as pd
import plotly.express as px
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

def mostrar_meios(indicador,ano,meses,codigos,sexo,total_principal):
    st.subheader('Quais meios estão registrados nos óbitos?')
    pasta=Path(__file__).parent/'dados';arquivo=pasta/'f_meios_cid.csv.gz';metafile=pasta/'meios_cid_meta.json'
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
        st.info('Sem óbitos no recorte da extração por CID: frequência relativa não definida.');return
    lideres=grupos.loc[grupos.Obitos.eq(grupos.Obitos.max())]
    fmt=lambda v,d=0:f'{v:,.{d}f}'.replace(',','X').replace('.',',').replace('X','.')
    st.write('Maior frequência no recorte: **'+'; '.join(lideres.meio)+'** — **'+fmt(lideres.Obitos.iloc[0])+' óbito(s)** por grupo ('+fmt(lideres['Frequência relativa (%)'].iloc[0],1)+'% do total).')
    graf=grupos.sort_values('Obitos').rename(columns={'meio':'Meio registrado','Obitos':'Óbitos'})
    graf['Rótulo']=[fmt(n)+' ('+fmt(p,1)+'%)' for n,p in zip(graf['Óbitos'],graf['Frequência relativa (%)'])]
    fig=px.bar(graf,x='Óbitos',y='Meio registrado',orientation='h',text='Rótulo',hover_data=['CIDs','Frequência relativa (%)'],color_discrete_sequence=['#126c83'])
    fig.update_traces(textposition='outside',cliponaxis=False)
    fig.update_layout(height=max(350,len(graf)*48+100),margin={'l':10,'r':130,'t':20,'b':45},xaxis={'range':[0,float(graf['Óbitos'].max())*1.35]})
    st.plotly_chart(fig,width='stretch',key='meios_cid')
    st.caption('Participação = óbitos do grupo de meios ÷ total de óbitos desta extração × 100. Grupos não se sobrepõem. Meios não especificados permanecem no total. A análise descreve registros de óbitos, não todas as tentativas de suicídio ou ocorrências de violência.')
    st.markdown('**Detalhamento por código CID-10**')
    tab=detalhe.rename(columns={'cid':'CID-10','descricao_cid':'Descrição na fonte','meio':'Grupo de meios','Obitos':'Óbitos'})[['CID-10','Descrição na fonte','Grupo de meios','Óbitos','Frequência relativa (%)']]
    tab=pd.concat([tab,pd.DataFrame([{'CID-10':'TOTAL','Descrição na fonte':'Todos os códigos do indicador no recorte','Grupo de meios':'','Óbitos':total,'Frequência relativa (%)':100.0}])],ignore_index=True)
    st.dataframe(tab,hide_index=True,width='stretch',row_height=35,height=46+35*len(tab),column_config={'Frequência relativa (%)':st.column_config.NumberColumn(format='%.1f%%'),'Óbitos':st.column_config.NumberColumn(format='%d')})
    st.download_button('Baixar meios por CID-10 (CSV)',tab.to_csv(index=False,sep=';',decimal=',').encode('utf-8-sig'),'meios_cid.csv','text/csv')
