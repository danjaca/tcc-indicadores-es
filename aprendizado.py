"""Quarta aba: avaliação de previsões versionadas, sem treinamento na interface."""
from pathlib import Path
import hashlib,json
import numpy as np
import pandas as pd
import plotly.graph_objects as go
import streamlit as st
from configuracao import DADOS

RESULTADOS=Path(__file__).resolve().parent/'dados_ml'

@st.cache_data
def carregar_resultados(assinatura):
    frames={name:pd.read_csv(RESULTADOS/(name+'.csv')) for name in ['previsoes','metricas','buscas','proximo_mes']}
    for name in ['previsoes','proximo_mes']:frames[name]['date']=pd.to_datetime(frames[name]['date'])
    frames['decisoes']=json.loads((RESULTADOS/'decisoes.json').read_text())
    frames['manifesto']=json.loads((RESULTADOS/'manifesto.json').read_text())
    frames['configuracoes']=json.loads((RESULTADOS/'configuracoes.json').read_text())
    return frames

@st.cache_data
def hash_base(path,mtime,size):return hashlib.sha256(Path(path).read_bytes()).hexdigest()

def agregar(frame,regiao):
    if regiao!='Espírito Santo':frame=frame[frame.region.eq(regiao)]
    return frame.groupby('date',as_index=False)[['y','prediction']].sum()

def mostrar_machine_learning(indicador):
    st.subheader('Machine learning · esperado e observado')
    st.write('Modelos experimentais para estimar os óbitos registrados no próximo mês, por região de saúde. Compare as estimativas com uma referência simples e confira o desempenho fora do ajuste.')
    required=['previsoes.csv','metricas.csv','buscas.csv','proximo_mes.csv','decisoes.json','manifesto.json','configuracoes.json']
    if not all((RESULTADOS/f).exists() for f in required):
        st.info('Os resultados dos experimentos ainda não estão disponíveis nesta instalação.');return
    signature=tuple((n,(RESULTADOS/n).stat().st_mtime_ns) for n in required)
    res=carregar_resultados(signature);manifest=res['manifesto']
    decision=next((d for d in res['decisoes'] if d['indicator']==indicador),None)
    if decision is None:st.info('Indicador sem experimento publicado.');return
    source=DADOS/'dataset.zip';stat=source.stat();atual=hash_base(str(source),stat.st_mtime_ns,stat.st_size)
    stale=atual!=manifest['source_sha256']
    if stale:st.warning('A base do painel mudou após estes experimentos. A avaliação abaixo pertence ao snapshot anterior; a estimativa do próximo mês foi suspensa até reprocessamento.')
    st.caption('Histórico dos modelos: janeiro/2021 em diante. Validação: 2023–2024. Avaliação temporal: 2025. Dados de 2026 são suplementares e sujeitos a revisão.')
    st.info('Nesta aba, o indicador acompanha o seletor lateral. Ano, meses, municípios e sexo da barra lateral não alteram os modelos. Use o período e a região abaixo; cada modelo inclui toda a população elegível de seu indicador.')
    if decision['ci_high']<0:st.success(f"{decision['status']}. Candidato escolhido na validação: {decision['ml']}.")
    elif decision['gain_percent']>0:st.info(f"{decision['status']}. Candidato escolhido na validação: {decision['ml']}.")
    else:st.warning(f"{decision['status']}. O candidato {decision['ml']} permanece experimental; a referência {decision['baseline']} continua disponível.")
    df=res['previsoes'];df=df[df.indicator.eq(indicador)]
    models=list(df.method.unique());models.remove(decision['ml']);models=[decision['ml']]+models
    c1,c2,c3=st.columns([1,1,1.2])
    with c1:period=st.selectbox('Período de avaliação',['avaliação 2025','validação','suplementar 2026'],key='ml_periodo')
    with c2:region=st.selectbox('Região do modelo',['Espírito Santo']+sorted(df.region.unique()),key='ml_regiao')
    with c3:method=st.selectbox('Modelo em análise',models,key='ml_modelo')
    if method!=decision['ml']:st.caption('Comparação exploratória: mudar este seletor não altera o candidato escolhido pelo protocolo.')
    chosen=agregar(df[df.method.eq(method)&df.period.eq(period)],region)
    reference=agregar(df[df.method.eq(decision['baseline'])&df.period.eq(period)],region)
    validation=agregar(df[df.method.eq(method)&df.period.eq('validação')],region)
    if chosen.empty:st.info('Sem resultados para esta seleção.');return
    mae=(chosen.prediction-chosen.y).abs().mean();base_mae=(reference.prediction-reference.y).abs().mean()
    gain=100*(base_mae-mae)/base_mae if base_mae else None
    a,b,c=st.columns(3)
    a.metric('Erro médio absoluto · modelo',f'{mae:.2f} óbitos')
    b.metric('Erro médio absoluto · referência',f'{base_mae:.2f} óbitos')
    c.metric('Redução do erro',f'{gain:+.1f}%' if gain is not None else 'Não definida')
    st.caption('Erros no território e período selecionados. No estado, somam-se as quatro previsões regionais. A seleção do modelo usou o erro regional médio, não este filtro.')
    q=float(np.quantile((validation.prediction-validation.y).abs(),.9,method='higher'))
    fig=go.Figure()
    fig.add_trace(go.Scatter(x=chosen.date,y=chosen.prediction+q,mode='lines',line={'width':0},showlegend=False,hoverinfo='skip'))
    fig.add_trace(go.Scatter(x=chosen.date,y=np.maximum(0,chosen.prediction-q),mode='lines',line={'width':0},fill='tonexty',fillcolor='rgba(18,108,131,.12)',name='Faixa empírica de erro',hoverinfo='skip'))
    fig.add_trace(go.Scatter(x=chosen.date,y=chosen.y,mode='lines+markers',name='Óbitos observados',line={'color':'#24455f','width':3}))
    fig.add_trace(go.Scatter(x=chosen.date,y=chosen.prediction,mode='lines+markers',name=method,line={'color':'#168777','width':3}))
    fig.add_trace(go.Scatter(x=reference.date,y=reference.prediction,mode='lines',name=decision['baseline'],line={'color':'#bb7a31','dash':'dot'}))
    fig.update_layout(xaxis_title='Mês previsto',yaxis_title='Óbitos registrados',hovermode='x unified',legend={'orientation':'h'},yaxis={'rangemode':'tozero'},height=430)
    st.plotly_chart(fig,width='stretch',key='ml_previsoes')
    st.caption('Cada ponto estima um mês usando somente meses anteriores. A faixa usa o percentil 90 do erro absoluto de validação; não é garantia de cobertura nem limite de alerta epidemiológico. A retrospectiva usa uma base revisada, sem reconstruir o atraso de registro histórico.')
    st.markdown('**Leitura quadrimestral das estimativas mensais**')
    quad=chosen.copy();quad['Ano']=quad.date.dt.year;quad['Quadrimestre']=((quad.date.dt.month-1)//4+1)
    quad=quad.groupby(['Ano','Quadrimestre']).agg(Observado=('y','sum'),Estimado=('prediction','sum'),Meses=('date','size')).reset_index()
    quad['Diferença']=quad.Estimado-quad.Observado
    st.dataframe(quad,hide_index=True,width='stretch')
    st.caption('Soma de previsões mensais atualizadas. Não representa previsão de quatro meses feita no início do quadrimestre. Confira a quantidade de meses de cada linha.')
    st.markdown('**Comparação dos métodos**')
    m=res['metricas'];m=m[m.indicator.eq(indicador)]
    table=m.pivot(index='method',columns='period',values='mae').reset_index().rename(columns={'method':'Método','validação':'MAE validação 2023–2024','avaliação 2025':'MAE avaliação 2025','suplementar 2026':'MAE suplementar 2026'})
    table['Escolhido na validação']=table['Método'].eq(decision['ml'])
    st.dataframe(table.sort_values('MAE validação 2023–2024'),hide_index=True,width='stretch')
    st.caption('MAE em óbitos por região–mês, para todas as regiões. Menor é melhor. ELM e MLP foram comparadas com busca aleatória e PSO de 24 avaliações cada. A rede “pesos PSO” ajusta os próprios pesos pelo enxame.')
    with st.expander('Parâmetros, confiabilidade e referências'):
        cfg=next(c['config'] for c in res['configuracoes'] if c['indicator']==indicador and c['method']==method)
        st.json(cfg)
        st.write(f"Diferença de MAE do candidato escolhido menos a referência em 2025: intervalo exploratório de 95% [{decision['ci_low']:.2f}; {decision['ci_high']:.2f}], obtido com blocos de três meses. Apenas 12 meses de teste; não constitui validação prospectiva.")
        st.write('ELM: pesos ocultos aleatórios e saída ajustada por regressão regularizada. MLP: pesos ajustados por L-BFGS; PSO busca tamanho da camada, regularização e modo de estimar o nível ou corrigir a média móvel. Treinar pesos com PSO é outro experimento. Nenhum modelo estima risco individual ou identifica causas.')
        st.markdown('[ELM — Huang et al. (2006)](https://doi.org/10.1016/j.neucom.2005.12.126) · [PSO — Kennedy e Eberhart (1995)](https://doi.org/10.1109/ICNN.1995.488968) · [Busca aleatória — Bergstra e Bengio (2012)](https://jmlr.org/papers/v13/bergstra12a.html) · [Validação temporal — Hyndman e Athanasopoulos](https://otexts.com/fpp3/tscv.html)')
        st.caption(f"Experimento gerado em {manifest['created']}. Snapshot até {manifest['last']}. Avisos de convergência registrados: {manifest['convergence_warnings']}. Resultados não são atualizados automaticamente junto com o ETL.")
    with st.expander('Estimativa experimental após o último mês da base'):
        if stale:st.info('Reprocesse os experimentos com a versão atual da base para habilitar esta estimativa.')
        else:
            future=res['proximo_mes'];future=future[future.indicator.eq(indicador)].copy()
            if region!='Espírito Santo':future=future[future.region.eq(region)]
            st.warning('Dados recentes sujeitos a atraso de registro. Esta estimativa é experimental e não substitui o indicador observado. Para métodos sem ganho no teste, priorize a referência simples.')
            if region=='Espírito Santo':
                future=future.groupby(['date','method'],as_index=False).prediction.sum()
            else:future=future[['date','region','method','prediction','lower','upper']]
            st.dataframe(future.rename(columns={'date':'Mês','region':'Região','method':'Método','prediction':'Estimativa','lower':'Limite empírico inferior','upper':'Limite empírico superior'}),hide_index=True,width='stretch')
    ensemble_file=RESULTADOS/'ensemble_metricas.csv'
    if ensemble_file.exists():
        with st.expander('Estudo adicional · combinação adaptativa de previsões'):
            additional=pd.read_csv(ensemble_file);additional=additional[additional.indicator.eq(indicador)]
            st.write('Combinação de ELM, outros modelos e médias móveis. Os pesos aprendem com erros dos meses anteriores; cada previsão é calculada antes de incorporar o observado daquele mês.')
            st.warning('Estudo exploratório iniciado após observar a primeira rodada de 2025. Não substitui a seleção original nem constitui confirmação independente de ganho.')
            st.dataframe(additional[['year','mae','baseline','gain_percent','ci_low','ci_high']].rename(columns={'year':'Ano','mae':'MAE combinação','baseline':'MAE referência','gain_percent':'Redução do erro (%)','ci_low':'Diferença · limite inferior','ci_high':'Diferença · limite superior'}),hide_index=True,width='stretch')
            st.markdown('[Fundamentação: Prediction, Learning, and Games — Cesa-Bianchi e Lugosi](https://cesa-bianchi.di.unimi.it/predbook/)')
    st.download_button('Baixar avaliação de machine learning',df.to_csv(index=False).encode('utf-8-sig'),'avaliacao_ml.csv','text/csv',key='ml_download')
