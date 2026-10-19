from configuracao import DADOS
"""Comparação do perfil etário por sexo, com denominador anual explícito."""
import math
import pandas as pd
import plotly.graph_objects as go
import streamlit as st
from dominio.dados import IDADES, INDICADORES, cobertura_completa

PALETA_ANOS=['#7457A6','#B05D44','#428C69','#B54D77','#6B8297','#288D91','#8D6D4B','#AA5AA8','#AA850E','#2878B5','#E07827','#5B9560']

def cor_ano(ano):
    return PALETA_ANOS[(int(ano)-2016)%len(PALETA_ANOS)]

def preparar_piramide(fato,anos,meses,idades,sexos):
    """Fato já filtrada por indicador, municípios e sexo; idades não rebasedas.

    O denominador inclui todas as idades elegíveis e os registros ignorados
    presentes no recorte. Idade/sexo ignorados não recebem posição na pirâmide.
    """
    faixas=[i for i in IDADES if i in idades and i!='Ignorado']
    linhas=[];auditoria=[]
    for ano in sorted(set(anos)):
        if not cobertura_completa(fato,ano,meses):
            auditoria.append({'Ano':ano,'Situação':'Sem cobertura completa','Total do indicador':None,'Óbitos representados':None,'Idade ignorada':None,'Sexo ignorado':None})
            continue
        rec=fato[fato.ano.eq(ano)&fato.mes.isin(meses)]
        total=int(rec.Obitos.sum())
        soma=rec.groupby(['faixa_etaria','sexo']).Obitos.sum()
        representados=0
        for sexo in sexos:
            for idade in faixas:
                n=int(soma.get((idade,sexo),0));representados+=n
                linhas.append({'Ano':ano,'Faixa etária':idade,'Sexo':sexo,'Óbitos':n,'Total do indicador':total,'Percentual dos óbitos (%)':n/total*100 if total else float('nan')})
        auditoria.append({'Ano':ano,'Situação':'Disponível' if total else 'Sem óbitos: percentual não definido','Total do indicador':total,'Óbitos representados':representados,'Idade ignorada':int(rec.loc[rec.faixa_etaria.eq('Ignorado'),'Obitos'].sum()),'Sexo ignorado':int(rec.loc[rec.sexo.eq('Ignorado'),'Obitos'].sum())})
    return pd.DataFrame(linhas,columns=['Ano','Faixa etária','Sexo','Óbitos','Total do indicador','Percentual dos óbitos (%)']),pd.DataFrame(auditoria)

def grafico_piramide(tabela,ano_destaque,faixas,sexos):
    validos=tabela[tabela['Percentual dos óbitos (%)'].notna()]
    anos=sorted(validos.Ano.unique())
    fig=go.Figure()
    fmt=lambda v:f'{v:.1f}'.replace('.',',')+'%'
    for ano in anos:
        # A mesma cor e a mesma entrada da legenda controlam os dois lados.
        fig.add_trace(go.Scatter(x=[None],y=[None],mode='lines',name=str(ano),legendgroup=str(ano),line={'color':cor_ano(ano),'dash':'solid','width':3},hoverinfo='skip',showlegend=True))
        for sexo in sexos:
            parte=validos[validos.Ano.eq(ano)&validos.Sexo.eq(sexo)]
            if parte.empty:continue
            sinal=-1 if sexo=='Masculino' else 1
            fig.add_trace(go.Scatter(
                x=(parte['Percentual dos óbitos (%)']*sinal).tolist(),y=parte['Faixa etária'].tolist(),
                name=f'{ano} · {sexo}',legendgroup=str(ano),showlegend=False,
                mode='lines+markers+text' if ano==ano_destaque else 'lines+markers',
                line={'color':cor_ano(ano),'dash':'solid','width':3.5 if ano==ano_destaque else 2},
                marker={'size':7 if ano==ano_destaque else 5},
                text=[fmt(v) for v in parte['Percentual dos óbitos (%)']] if ano==ano_destaque else None,
                textposition='middle left' if sexo=='Masculino' else 'middle right',textfont={'size':11,'color':cor_ano(ano)},
                cliponaxis=False,customdata=parte[['Óbitos','Total do indicador','Percentual dos óbitos (%)']].values.tolist(),
                hovertemplate='%{y}<br>Óbitos: %{customdata[0]}<br>Total do indicador: %{customdata[1]}<br>Percentual: %{customdata[2]:.2f}%<extra>%{fullData.name}</extra>'))
    maior=float(validos['Percentual dos óbitos (%)'].max()) if not validos.empty else 0
    passo=5 if maior<=25 else 10
    limite=max(passo,math.ceil(maior*1.2/passo)*passo)
    esquerda=-limite if 'Masculino' in sexos else 0
    direita=limite if 'Feminino' in sexos else 0
    marcas=list(range(esquerda,direita+1,passo))
    fig.update_layout(height=max(480,44*len(faixas)+160),margin={'l':105,'r':70,'t':70,'b':90},
        legend={'title':{'text':'Ano'},'orientation':'h','y':-0.12,'groupclick':'togglegroup'},
        xaxis={'title':'Percentual do total de óbitos do indicador no recorte','range':[esquerda,direita],'tickvals':marcas,'ticktext':[f'{abs(m)}%' for m in marcas],'zeroline':False},
        yaxis={'title':'Faixa etária','type':'category','categoryorder':'array','categoryarray':faixas},hovermode='closest')
    fig.add_vline(x=0,line_color='#aab7c3',line_width=1)
    for sexo in sexos:
        pos=(0.25 if sexo=='Masculino' else 0.75) if len(sexos)==2 else .5
        fig.add_annotation(x=pos,y=1.08,xref='paper',yref='paper',text=f'<b>{sexo.upper()}</b>',font={'color':'#526476','size':14},showarrow=False)
    return fig

def mostrar_piramide(fato,indicador,ano,meses,idades,sexo_filtro,anos_disponiveis):
    st.subheader('Como o perfil etário dos óbitos mudou entre os anos?')
    opcoes=sorted(anos_disponiveis)
    padrao=[a for a in [ano-1,ano] if a in opcoes]
    anos=st.multiselect('Anos da pirâmide etária',opcoes,default=padrao,max_selections=4,key=f'piramide_anos_{indicador}_{ano}',help='Compare até quatro anos com os mesmos meses, municípios, sexo e faixas etárias da análise.')
    if not anos:
        st.info('Selecione pelo menos um ano para a pirâmide etária.');return
    sexos=[INDICADORES[indicador]['sexo']] if INDICADORES[indicador]['sexo'] else ([sexo_filtro] if sexo_filtro!='Todos' else ['Masculino','Feminino'])
    faixas=[i for i in IDADES if i in idades and i!='Ignorado']
    if not faixas:
        st.info('Selecione ao menos uma faixa etária conhecida para este gráfico.');return
    tabela,auditoria=preparar_piramide(fato,anos,meses,idades,sexos)
    faltantes=auditoria.loc[auditoria['Situação'].eq('Sem cobertura completa'),'Ano'].tolist()
    if faltantes:st.info('Sem cobertura completa para os mesmos meses: '+', '.join(map(str,faltantes))+'. Esses anos foram omitidos, sem substituir dados ausentes por zero.')
    disponiveis=sorted(tabela.loc[tabela['Percentual dos óbitos (%)'].notna(),'Ano'].unique())
    if not disponiveis:
        st.info('Não há total positivo de óbitos com cobertura suficiente para calcular os percentuais.');return
    destaque=ano if ano in disponiveis else max(disponiveis)
    st.caption('Mesmos meses em todos os anos: '+', '.join(map(str,meses))+'. Cada ano tem uma cor, igual nos lados masculino e feminino. Todas as linhas são contínuas. Rótulos visíveis: '+str(destaque)+'.')
    st.plotly_chart(grafico_piramide(tabela,destaque,faixas,sexos),width='stretch',key='piramide_etaria_anos')
    st.caption('Percentual = óbitos da faixa etária e sexo ÷ total de óbitos do indicador naquele ano, nos meses, municípios e sexo filtrados × 100. O denominador mantém todas as faixas elegíveis, mesmo ao ocultar idades neste gráfico. Com Sexo = Todos, todas as faixas exibidas e sem registros ignorados, os dois lados juntos representam 100%; não se calcula 100% para cada lado. Ao filtrar um sexo, o denominador também fica restrito a esse sexo. Idade ou sexo ignorado permanecem no denominador, mas não são desenhados; por isso os pontos podem somar menos de 100%. Os valores à esquerda também são percentuais positivos: o espelhamento é apenas visual.')
    st.caption('Esta é uma distribuição proporcional dos óbitos do indicador, não uma taxa populacional nem a mortalidade por todas as causas. Mudanças na forma não comprovam envelhecimento da população ou mudança de risco. As faixas têm amplitudes diferentes; não foram desagregadas em intervalos de cinco anos. Os filtros deste gráfico são aplicados ao alterá-los.')
    if len(faixas)<3:st.caption('Este indicador possui poucas faixas agregadas; a linha conecta as categorias disponíveis e não estima idades intermediárias.')
    with st.expander('Ver percentuais, contagens e denominadores da pirâmide'):
        for a in sorted(tabela.Ano.unique()):
            rec=tabela[tabela.Ano.eq(a)]
            resumo=rec.pivot(index='Faixa etária',columns='Sexo',values=['Óbitos','Percentual dos óbitos (%)']).reindex(faixas)
            resumo.columns=[f'{medida} · {sexo}' for medida,sexo in resumo.columns]
            st.markdown(f'**{a} · denominador: {int(rec["Total do indicador"].iloc[0])} óbitos**')
            st.dataframe(resumo.reset_index(),hide_index=True,width='stretch',height=46+35*len(resumo),row_height=35,column_config={c:st.column_config.NumberColumn(format='%.1f%%' if c.startswith('Percentual') else '%d') for c in resumo.columns})
        st.dataframe(auditoria,hide_index=True,width='stretch',height=46+35*len(auditoria),row_height=35)
        st.caption('As contagens de idade e sexo ignorados podem se sobrepor; não some essas duas colunas.')
        st.download_button('Baixar dados da pirâmide (CSV)',tabela.to_csv(index=False,sep=';',decimal=',').encode('utf-8-sig'),'piramide_etaria.csv','text/csv')
