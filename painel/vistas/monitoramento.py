"""Aba de monitoramento estatístico mensal por gráficos de controle (X–AM e EWMA).

Fase I (referência): descritivas, pressupostos e gráficos X–AM com exclusão
iterativa. Fase II: X–AM com limites fixos e EWMA. Leitura quadrimestral com
os mesmos parâmetros. A granularidade territorial é um parâmetro da página;
o protocolo recomenda o nível estadual.
"""
from __future__ import annotations

from functools import partial
import hashlib
import json

import numpy as np
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import streamlit as st

from configuracao import DADOS, RAIZ
from dominio import monitoramento as mon
from dominio.dados import recortar
from dominio.monitoramento import TAXA
from painel.relatorio import relatorio_monitoramento

AZUL = '#126c83'
CINZA = '#94a3b8'
CINZA_ESCURO = '#475569'
VERMELHO = '#bd4545'
AZUL_SINAL = '#2563eb'
LARANJA = '#d97706'
ROXO = '#7c3aed'
GRANULARIDADES = ['Estadual', 'Região de saúde', 'Município']
SECOES = ['Resumo', 'Fase I · referência', 'Fase II · monitoramento mensal', 'Leitura quadrimestral', 'Sensibilidade',
          'Parâmetros e reprodução']


def fmt(valor, casas=2):
    if valor is None or (isinstance(valor, float) and not np.isfinite(valor)):
        return '—'
    return f'{valor:,.{casas}f}'.replace(',', 'X').replace('.', ',').replace('X', '.')


@st.cache_data(show_spinner=False)
def largura_para_arl(lam: float, arl0: float = 370.4) -> float:
    return mon.calibrar_largura_ewma(lam, arl0)


@st.cache_data(show_spinner=False)
def tabela_arl(lam: float, largura_ewma: float, largura: float) -> pd.DataFrame:
    linhas = []
    for delta in (0, .5, 1, 1.5, 2, 3):
        linhas.append({'Deslocamento da média (em σ0)': delta,
                       'Gráfico X (meses até o sinal)': mon.arl_shewhart(delta, largura),
                       'Leitura quadrimestral X̄ (meses)': 4 * mon.arl_shewhart(2 * delta, largura),
                       'EWMA (meses até o sinal)': mon.arl_ewma(lam, largura_ewma, delta)})
    return pd.DataFrame(linhas)


def viabilidade(referencia: pd.DataFrame, pressupostos: pd.DataFrame, alfa=mon.ALFA) -> tuple[str, str]:
    """Classifica a aplicabilidade dos limites baseados na normal ao recorte territorial."""
    media = float(referencia['Óbitos'].mean())
    zeros = float((referencia['Óbitos'] == 0).mean())
    p_normal = float(pressupostos.set_index('Teste').loc['Lilliefors', 'Valor-p'])
    if media < 5 or zeros > .1:
        return 'Não recomendado', (f'Média de {fmt(media, 1)} óbitos por mês e {fmt(zeros * 100, 0)}% de meses sem óbito na fase I. '
                                   'Com contagens tão pequenas, a taxa mensal é discreta e assimétrica e os limites baseados '
                                   'na distribuição normal não se aplicam. Use o nível estadual (ou regional) para o monitoramento.')
    temporal = pressupostos['Teste'].str.startswith(('Cox', 'Ljung', 'Fisher')) & pressupostos['Valor-p'].lt(alfa)
    if media < 10 or zeros > 0 or p_normal < alfa or temporal.any() or not np.isfinite(p_normal):
        return 'Com ressalvas', (f'Média de {fmt(media, 1)} óbitos por mês; Lilliefors p = {fmt(p_normal, 3)}. '
                                 'Confira os pressupostos e a estabilidade da referência. Dependência, tendência, '
                                 'sazonalidade e contagens pequenas podem alterar os falsos alarmes dos três gráficos.')
    return 'Adequado', (f'Média de {fmt(media, 1)} óbitos por mês, sem meses vazios e normalidade não rejeitada '
                        f'(Lilliefors p = {fmt(p_normal, 3)}). Esta triagem não comprova adequação ou completude dos registros.')


def _sinais(fig, datas, valores, rotulos, linha=1, coluna=1, legenda=True):
    for alvo, cor, simbolo, nome in (('Aumento', VERMELHO, 'triangle-up', 'Sinal de aumento'),
                                     ('Redução', AZUL_SINAL, 'triangle-down', 'Sinal de redução'),
                                     ('Variabilidade', VERMELHO, 'triangle-up', 'Sinal de variabilidade')):
        m = np.asarray(rotulos) == alvo
        if m.any():
            fig.add_trace(go.Scatter(x=np.asarray(datas)[m], y=np.asarray(valores, dtype=float)[m], mode='markers',
                                     name=nome, showlegend=legenda,
                                     marker=dict(color=cor, symbol=simbolo, size=12)))


def _consolidacao(fig, f2, coluna):
    m = f2['Em consolidação'].to_numpy(bool)
    if m.any():
        fig.add_trace(go.Scatter(x=f2['Período'][m], y=f2[coluna][m], mode='markers', name='Mês em consolidação',
                                 marker=dict(color='white', size=13, line=dict(color=ROXO, width=2))))


MESES_PT = ('Jan', 'Fev', 'Mar', 'Abr', 'Mai', 'Jun', 'Jul', 'Ago', 'Set', 'Out', 'Nov', 'Dez')


def _eixo_meses(fig, passo=3):
    """Rótulos mensais em português (o Plotly usa nomes de meses em inglês)."""
    datas = []
    for trace in fig.data:
        if trace.x is None or not len(trace.x):
            continue
        valores = pd.to_datetime(pd.Series(list(trace.x)), errors='coerce').dropna()
        datas.extend(valores.tolist())
    if not datas:
        return fig
    inicio = pd.Timestamp(min(datas)).to_period('M').to_timestamp()
    marcas = [m for m in pd.date_range(inicio, max(datas), freq='MS') if (m.month - 1) % passo == 0]
    fig.update_xaxes(tickvals=marcas, ticktext=[f'{MESES_PT[m.month - 1]}/{m:%y}' for m in marcas])
    return fig


def _layout(fig, titulo, eixo_y, altura=430):
    fig.update_layout(title=titulo, yaxis_title=eixo_y, height=altura, hovermode='x unified',
                      legend=dict(orientation='h', yanchor='top', y=-.18, x=0), margin=dict(t=60, b=110),
                      separators=',.')
    return _eixo_meses(fig, 6 if len(fig.data) and fig.data[0].x is not None and len(fig.data[0].x) > 48 else 3)


def figura_serie(r: mon.Resultado) -> go.Figure:
    s = r.serie
    fig = go.Figure()
    p0, p1 = r.referencia['Período'].min(), r.referencia['Período'].max()
    fig.add_vrect(x0=p0 - pd.Timedelta(days=15), x1=p1 + pd.Timedelta(days=15), fillcolor='#e2e8f0', opacity=.5,
                  line_width=0, annotation_text='Fase I · referência', annotation_position='top left')
    fig.add_trace(go.Scatter(x=s['Período'], y=s[TAXA], mode='lines+markers', name='Taxa mensal',
                             line=dict(color=AZUL, width=2), marker=dict(size=4),
                             customdata=s[['Óbitos', 'População']].to_numpy(),
                             hovertemplate='%{x|%b/%Y}<br>Taxa: %{y:.3f}<br>Óbitos: %{customdata[0]}'
                                           '<br>População: %{customdata[1]:,.0f}<extra></extra>'))
    _consolidacao(fig, r.fase_ii, TAXA)
    fig = _layout(fig, 'Série mensal da taxa por 100 mil (sem anualização)', 'Taxa mensal por 100 mil', 400)
    anos = pd.date_range(s['Período'].min().to_period('Y').to_timestamp(), s['Período'].max(), freq='YS')
    fig.update_xaxes(tickvals=list(anos), ticktext=[f'{a:%Y}' for a in anos])
    return fig


def figura_x(r: mon.Resultado, incluir_fase1=True) -> go.Figure:
    p, f1, f2 = r.params, r.fase_i, r.fase_ii
    fig = go.Figure()
    if incluir_fase1:
        controle = f1['Situação fase I'].str.startswith(('Em controle', 'Mantido'))
        fig.add_trace(go.Scatter(x=f1['Período'][controle], y=f1[TAXA][controle], mode='lines+markers',
                                 name='Fase I (meses mantidos)', line=dict(color=CINZA), marker=dict(size=5)))
        if (~controle).any():
            fig.add_trace(go.Scatter(x=f1['Período'][~controle], y=f1[TAXA][~controle], mode='markers',
                                     name='Excluído na fase I', marker=dict(color=LARANJA, symbol='x', size=11),
                                     text=f1['Situação fase I'][~controle], hovertemplate='%{x|%b/%Y}<br>%{text}<extra></extra>'))
        fronteira = f1['Período'].max() + pd.Timedelta(days=15)
        fig.add_vline(x=fronteira, line_dash='dot', line_color=CINZA_ESCURO)
    if not f2.empty:
        fig.add_trace(go.Scatter(x=f2['Período'], y=f2[TAXA], mode='lines+markers', name='Fase II (monitoramento)',
                                 line=dict(color=AZUL, width=2), marker=dict(size=6)))
        _sinais(fig, f2['Período'], f2[TAXA], f2['Sinal X'])
        _consolidacao(fig, f2, TAXA)
    for valor, nome, estilo in ((p.lsc_x, 'LSC', 'dash'), (p.mu0, 'LM (μ0)', 'solid'), (p.lic_x, 'LIC', 'dash')):
        fig.add_hline(y=valor, line_dash=estilo, line_color=VERMELHO if estilo == 'dash' else CINZA_ESCURO,
                      annotation_text=f'{nome} = {fmt(valor, 3)}', annotation_position='top left')
    return _layout(fig, 'Gráfico de medidas individuais (X)', 'Taxa mensal por 100 mil')


def figura_am(r: mon.Resultado, incluir_fase1=True) -> go.Figure:
    p, f1, f2 = r.params, r.fase_i, r.fase_ii
    fig = go.Figure()
    if incluir_fase1:
        fig.add_trace(go.Scatter(x=f1['Período'], y=f1['AM'], mode='lines+markers', name='Fase I',
                                 line=dict(color=CINZA), marker=dict(size=4)))
        fig.add_vline(x=f1['Período'].max() + pd.Timedelta(days=15), line_dash='dot', line_color=CINZA_ESCURO)
    if not f2.empty:
        fig.add_trace(go.Scatter(x=f2['Período'], y=f2['AM'], mode='lines+markers', name='Fase II',
                                 line=dict(color=AZUL, width=2), marker=dict(size=5)))
        _sinais(fig, f2['Período'], f2['AM'], f2['Sinal AM'])
    fig.add_hline(y=p.lsc_am, line_dash='dash', line_color=VERMELHO, annotation_text=f'LSC = {fmt(p.lsc_am, 3)}',
                  annotation_position='top left')
    fig.add_hline(y=p.am_media, line_color=CINZA_ESCURO, annotation_text=f'LM = {fmt(p.am_media, 3)}',
                  annotation_position='top left')
    return _layout(fig, 'Gráfico de amplitude móvel (AM)', 'Amplitude móvel', 360)


def figura_ewma(r: mon.Resultado, lam: float, largura: float, incluir_fase1=True, incluir_fase2=True) -> go.Figure:
    e1, f2, p = r.ewma_fase_i, (r.fase_ii if incluir_fase2 else r.fase_ii.iloc[0:0]), r.params
    fig = go.Figure()
    if incluir_fase1:
        fig.add_trace(go.Scatter(x=e1['Período'], y=e1['EWMA'], mode='lines', name='EWMA na fase I',
                                 line=dict(color=CINZA)))
        for coluna in ('LSC EWMA', 'LIC EWMA'):
            fig.add_trace(go.Scatter(x=e1['Período'], y=e1[coluna], mode='lines', showlegend=False,
                                     line=dict(color=VERMELHO, dash='dot', width=1), opacity=.5))
        fig.add_vline(x=e1['Período'].max() + pd.Timedelta(days=15), line_dash='dot', line_color=CINZA_ESCURO)
    if not f2.empty:
        fig.add_trace(go.Scatter(x=f2['Período'], y=f2['EWMA'], mode='lines+markers', name='EWMA na fase II',
                                 line=dict(color=AZUL, width=2), marker=dict(size=6)))
        fig.add_trace(go.Scatter(x=f2['Período'], y=f2['LSC EWMA'], mode='lines', name='LSC / LIC',
                                 line=dict(color=VERMELHO, dash='dash')))
        fig.add_trace(go.Scatter(x=f2['Período'], y=f2['LIC EWMA'], mode='lines', showlegend=False,
                                 line=dict(color=VERMELHO, dash='dash')))
        _sinais(fig, f2['Período'], f2['EWMA'], f2['Sinal EWMA'])
        _consolidacao(fig, f2, 'EWMA')
    if incluir_fase1 and not incluir_fase2:
        _sinais(fig, e1['Período'], e1['EWMA'], e1['Sinal EWMA'])
    fig.add_hline(y=p.mu0, line_color=CINZA_ESCURO, annotation_text=f'LM (μ0) = {fmt(p.mu0, 3)}',
                  annotation_position='top left')
    titulo = f'Gráfico EWMA (λ = {fmt(lam, 2)}; L = {fmt(largura, 3)})' + ('' if incluir_fase2 else ' · fase I')
    return _layout(fig, titulo, 'EWMA da taxa mensal')


def figura_fase1_iteracao(r: mon.Resultado, k: int) -> go.Figure:
    """Gráficos X e AM com os limites e os meses da iteração k da fase I."""
    d = mon.iteracao_fase1(r, k)
    lim, cons, excl = d['limites'], d['considerados'], d['excluidos_antes']
    fig = make_subplots(rows=2, cols=1, shared_xaxes=True, row_heights=[.58, .42], vertical_spacing=.1,
                        subplot_titles=(f"X · LIC = {fmt(lim['LIC X'], 3)}; LM = {fmt(lim['μ0'], 3)}; "
                                        f"LSC = {fmt(lim['LSC X'], 3)}",
                                        f"AM · LM = {fmt(lim['AM média'], 3)}; LSC = {fmt(lim['LSC AM'], 3)}"))
    fig.add_trace(go.Scatter(x=cons['Período'], y=cons[TAXA], mode='lines+markers', name='Meses considerados',
                             line=dict(color=CINZA_ESCURO, width=1.5), marker=dict(size=5)), 1, 1)
    if not excl.empty:
        fig.add_trace(go.Scatter(x=excl['Período'], y=excl[TAXA], mode='markers', name='Excluído em iteração anterior',
                                 marker=dict(color=LARANJA, symbol='x', size=11), text=excl['Situação fase I'],
                                 hovertemplate='%{x|%b/%Y}<br>%{text}<extra></extra>'), 1, 1)
    fora = cons['Sinal X'] | cons['Sinal AM']
    if fora.any():
        fig.add_trace(go.Scatter(x=cons.loc[fora, 'Período'], y=cons.loc[fora, TAXA], mode='markers',
                                 name='Fora de controle nesta iteração',
                                 marker=dict(color='rgba(0,0,0,0)', size=15, line=dict(color=VERMELHO, width=2))), 1, 1)
    for valor, estilo in ((lim['LSC X'], 'dash'), (lim['μ0'], 'solid'), (lim['LIC X'], 'dash')):
        fig.add_hline(y=valor, line_dash=estilo, line_color=VERMELHO if estilo == 'dash' else CINZA_ESCURO, row=1, col=1)
    fig.add_trace(go.Scatter(x=cons['Período'], y=cons['AM'], mode='lines+markers', name='Amplitude móvel',
                             line=dict(color=CINZA_ESCURO, width=1.2), marker=dict(size=4), showlegend=False), 2, 1)
    if cons['Sinal AM'].any():
        fig.add_trace(go.Scatter(x=cons.loc[cons['Sinal AM'], 'Período'], y=cons.loc[cons['Sinal AM'], 'AM'],
                                 mode='markers', showlegend=False,
                                 marker=dict(color='rgba(0,0,0,0)', size=15, line=dict(color=VERMELHO, width=2))), 2, 1)
    fig.add_hline(y=lim['LSC AM'], line_dash='dash', line_color=VERMELHO, row=2, col=1)
    fig.add_hline(y=lim['AM média'], line_color=CINZA_ESCURO, row=2, col=1)
    fig.update_yaxes(title_text='Taxa mensal', row=1, col=1)
    fig.update_yaxes(title_text='Amplitude móvel', row=2, col=1)
    ultima = int(r.iteracoes['Iteração'].max())
    titulo = f'Fase I · gráficos X e AM na {k}ª iteração' + (' (final)' if k == ultima else '')
    fig.update_layout(title=titulo, height=560, hovermode='x unified', separators=',.',
                      legend=dict(orientation='h', yanchor='top', y=-.12, x=0), margin=dict(t=80, b=90))
    return _eixo_meses(fig, 6 if len(cons) > 30 else 3)


def figura_fac(valores, titulo: str, n: int) -> go.Figure:
    k = np.arange(1, len(valores))
    limite = 1.96 / np.sqrt(n)
    fig = go.Figure(go.Bar(x=k, y=valores[1:], marker_color=AZUL, name=titulo))
    fig.add_hline(y=limite, line_dash='dash', line_color=VERMELHO)
    fig.add_hline(y=-limite, line_dash='dash', line_color=VERMELHO)
    fig.update_layout(title=titulo, height=300, xaxis_title='Defasagem (meses)', yaxis_range=[-.7, .7],
                      margin=dict(t=50, b=40), showlegend=False, separators=',.')
    return fig


def figura_qq(x) -> go.Figure:
    x = np.sort(np.asarray(x, dtype=float))
    n = len(x)
    z = (x - x.mean()) / x.std(ddof=1)
    teoricos = np.array([mon.normal_ppf((i - .375) / (n + .25)) for i in range(1, n + 1)])
    fig = go.Figure(go.Scatter(x=teoricos, y=z, mode='markers', marker=dict(color=AZUL, size=7), name='Observações'))
    lim = [float(min(teoricos.min(), z.min())) - .2, float(max(teoricos.max(), z.max())) + .2]
    fig.add_trace(go.Scatter(x=lim, y=lim, mode='lines', line=dict(color=VERMELHO), name='Referência normal'))
    fig.update_layout(title='Gráfico Q-Q normal', height=300, xaxis_title='Quantis teóricos',
                      yaxis_title='Valores padronizados', margin=dict(t=50, b=40), showlegend=False, separators=',.')
    return fig


def figura_quadrimestral(q: pd.DataFrame) -> go.Figure:
    q = q[q['Leitura'] == 'Quadrimestre isolado'].copy()
    rotulos = [f"{l['Quadrimestre']}/{l['Ano']}" + ('' if l['Completo'] else ' (parcial)') for _, l in q.iterrows()]
    sinal = q['Sinal'].fillna('')
    cores = ['#cbd5e1' if not c else (AZUL_SINAL if s == 'Redução' else VERMELHO if s == 'Aumento' else AZUL)
             for c, s in zip(q['Completo'], sinal)]
    fig = go.Figure(go.Bar(x=rotulos, y=q[TAXA], marker_color=cores, name='Taxa observada no quadrimestre',
                           text=[fmt(v, 2) + (f' · {s.lower()}' if s and c else '') for v, s, c in
                                 zip(q[TAXA], sinal, q['Completo'])],
                           textposition='inside', insidetextanchor='end', textfont=dict(color='white')))
    fig.add_trace(go.Scatter(x=rotulos, y=q['Esperado (m·μ0)'], mode='markers', name='Esperado (m·μ0)',
                             marker=dict(color=CINZA_ESCURO, symbol='line-ew-open', size=26, line=dict(width=3)),
                             error_y=dict(type='data', symmetric=False, array=q['LSC'] - q['Esperado (m·μ0)'],
                                          arrayminus=q['Esperado (m·μ0)'] - q['LIC'], color=VERMELHO, thickness=2,
                                          width=10)))
    fig.update_layout(title='Quadrimestres isolados: observado, esperado e limites', height=420,
                      yaxis_title='Taxa do quadrimestre por 100 mil', legend=dict(orientation='h', y=-.2),
                      margin=dict(t=60, b=90), separators=',.')
    return fig


@st.dialog('Como ler esta página', width='large')
def mostrar_guia():
    st.markdown('''Esta aba aplica ao indicador selecionado a metodologia de **gráficos de controle** (Montgomery, 2009; Barros, 2021):
uma **fase I**, que estima o comportamento esperado a partir dos anos anteriores, e uma **fase II**, que acompanha mês a
mês o ano monitorado com limites fixos.

**Unidade de análise.** Cada ponto é um mês: taxa = óbitos do mês ÷ população anual elegível × 100 mil. A taxa mensal
não é anualizada. O quadrimestre corresponde à soma das taxas dos seus quatro meses.

**Granularidade territorial.** O protocolo recomenda o nível **estadual**. Regiões e municípios podem ser
selecionados, mas, com poucos óbitos por mês, a taxa mensal fica discreta e cheia de zeros, e os limites baseados na
distribuição normal deixam de valer. A página classifica o recorte como adequado, com ressalvas ou não recomendado.

**Fase I · referência.** Confira as estatísticas descritivas e os testes: Lilliefors (normalidade), Ljung–Box e
FAC/FACP (independência), Dickey–Fuller aumentado (estacionariedade), Cox–Stuart (tendência) e Fisher (sazonalidade).
A referência padrão são os 48 meses anteriores ao ano monitorado, definidos antes da leitura dos sinais.
Em Ajuste pela vigilância, escolha o primeiro mês da fase II e a extensão da fase I, incluindo 48 ou 64 meses.
Em Sensibilidade, compare 24, 36, 48 e 64 meses com os demais parâmetros fixos; não escolha uma janela porque
ela produz significância. Exclusões exigem causa especial documentada; a exclusão automática é exploratória e
fica desligada por padrão. O resultado são a média (μ0) e o desvio-padrão (σ0 = AM̄/1,128).

**Fase II · monitoramento.**
- **Gráfico X:** um ponto acima do LSC ou abaixo do LIC indica mudança grande no mês.
- **Gráfico AM:** amplitude móvel acima do LSC indica salto incomum entre meses consecutivos.
- **EWMA:** média ponderada que acumula memória (λ = 0,1); sinaliza mudanças pequenas e persistentes.

Triângulos vermelhos indicam aumento; azuis, redução. Círculos roxos marcam meses **em consolidação** (menos de 60 dias
entre o fim do mês e a atualização da base, por convenção operacional): os registros ainda podem aumentar.
Esse prazo não comprova completude; registros antigos também podem sofrer revisões.

**Leitura quadrimestral.** Nos meses de maio, setembro e fevereiro, compare o quadrimestre isolado e o acumulado no ano
com o esperado (m·μ0) e os limites (m·μ0 ± 3·√m·σ0). Quadrimestres incompletos aparecem como parciais.

**Interpretação.** Um sinal indica afastamento do padrão esperado e orienta a investigação (qualidade do registro,
revisão da base, contexto territorial); não identifica causas nem avalia políticas isoladamente. Ausência de sinal não
significa ausência de problema. Não rejeitar H₀ não demonstra equivalência ou ausência de alteração. Os testes são
diagnósticos exploratórios, com poder limitado em séries curtas e sem correção de multiplicidade. O ARL exibido
pressupõe normalidade, independência e parâmetros conhecidos; não mede o desempenho real deste recorte.''')


def _protocolo(serie: pd.DataFrame, indicador: str, cfg: dict, ultimo: pd.Timestamp):
    """Parâmetros registrados ou análise exploratória definida pela vigilância."""
    with st.expander('Protocolo e parâmetros', expanded=False):
        modo = st.radio('Configuração', ['Protocolo do TCC (config.toml)', 'Ajuste pela vigilância'],
                        key='mon_modo', horizontal=True,
                        help='A configuração de referência é fixa; os testes não escolhem sua extensão.')
        padrao = mon.referencia_do_ano(serie, ultimo.year, int(cfg['meses_padrao_fase1']),
                                      int(cfg['meses_minimos_fase1']))
        inicio, fim = cfg['fase1'].get(indicador, [padrao['inicio'], padrao['fim']])
        inicio, fim = mon.mes(inicio), mon.mes(fim)
        lam, le, lx = float(cfg['lambda_ewma']), float(cfg['largura_ewma']), float(cfg['largura_x'])
        dias, automatico = int(cfg['dias_consolidacao']), bool(cfg['exclusao_automatica'])
        alfa, max_exclusao = float(cfg['alfa']), float(cfg['max_exclusao'])
        excluir = [mon.mes(v) for v in cfg['exclusoes'].get(indicador, [])]
        justificativa = cfg.get('justificativas', {}).get(indicador, '')
        meses_f2 = int(cfg['meses_fase2'])
        if modo == 'Ajuste pela vigilância':
            meses = list(serie['Período'])
            minimo = int(cfg['meses_minimos_fase1'])
            candidatos = [m for m in meses if m >= meses[0] + pd.DateOffset(months=minimo)]
            if not candidatos:
                raise ValueError(f'São necessários {minimo} meses anteriores ao início da fase II.')
            inicio2 = fim + pd.DateOffset(months=1)
            inicio2 = st.select_slider('Primeiro mês da fase II', options=candidatos,
                                       value=inicio2 if inicio2 in candidatos else candidatos[-1],
                                       format_func=mon.rotulo_mes, key='mon_inicio_fase2',
                                       help='A fase I termina no mês imediatamente anterior; não há sobreposição.')
            fim = inicio2 - pd.DateOffset(months=1)
            janela = st.selectbox('Extensão da fase I', [24, 36, 48, 64, 'Outra extensão'], index=2,
                                  key='mon_janela', format_func=lambda n: f'{n} meses' if isinstance(n, int) else n,
                                  help='48 meses cobrem quatro ciclos anuais; 64 ampliam a referência, mas podem misturar patamares. Nenhuma janela garante pressupostos.')
            if janela == 'Outra extensão':
                janela = int(st.number_input('Número de meses da fase I', minimo, 120, max(minimo, 48), 1,
                                              key='mon_meses_f1'))
            inicio = fim - pd.DateOffset(months=int(janela) - 1)
            st.caption('Janelas curtas estimam os limites com maior incerteza; janelas longas podem incorporar mudanças históricas. '
                       'Defina a referência antes de interpretar os sinais; compare todas as janelas em Sensibilidade.')
            meses_f2 = int(st.number_input('Meses monitorados na fase II', 1, 36, meses_f2, 1, key='mon_meses_f2',
                                           help='Horizonte planejado; meses ainda não disponíveis não são convertidos em zero.'))
            lam = st.slider('Peso λ do EWMA', .05, .40, lam, .05, key='mon_lambda',
                            help='Menor λ dá mais memória. A largura deve ser recalibrada ao alterar λ.')
            if st.checkbox('Calibrar L para ARL0 assintótico ≈ 370 meses', value=True, key='mon_calibrar'):
                le = float(cfg['largura_ewma']) if lam == float(cfg['lambda_ewma']) else largura_para_arl(round(lam, 2))
                st.caption(f'L calculado: {fmt(le, 3)}. Aproximação normal com parâmetros conhecidos e limites assintóticos; '
                           'não é o ARL efetivo com limites de partida e parâmetros estimados.')
            else:
                le = st.number_input('Largura L do EWMA', 1.5, 4.0, le, .01, key='mon_largura_ewma')
            lx = st.number_input('Largura L do gráfico X (desvios-padrão)', 2.0, 4.0, lx, .1, key='mon_largura_x',
                                 help='Limites mais estreitos aumentam a sensibilidade e os falsos alarmes.')
            dias = st.number_input('Dias de cautela após o fim do mês', 0, 180, dias, 15, key='mon_dias',
                                   help='Convenção operacional; ultrapassar o prazo não comprova completude. Revisões podem ocorrer depois.')
            automatico = st.toggle('Exclusão automática de pontos fora de controle na fase I', value=automatico,
                                   key='mon_auto', help='Exploratória: um sinal estatístico não comprova causa especial. Requer investigação.')
            opcoes = [m for m in meses if inicio <= m <= fim]
            excluir = st.multiselect('Meses excluídos pela vigilância (causa especial documentada)', opcoes,
                                     default=[m for m in excluir if m in opcoes], format_func=mon.rotulo_mes,
                                     key='mon_excluir')
            justificativa = st.text_input('Justificativa das exclusões', value=justificativa, key='mon_justificativa',
                                          placeholder='Informe a evidência e o motivo de cada exclusão')
            st.caption('Ajustes são exploratórios. O JSON exporta a configuração completa, os filtros e a identificação da base.')
        st.caption(f'Fase I: {mon.rotulo_mes(inicio)} a {mon.rotulo_mes(fim)} · fase II planejada: '
                   f'{mon.rotulo_mes(fim + pd.DateOffset(months=1))} a {mon.rotulo_mes(mon.fim_fase2(fim, meses_f2))} · '
                   f'λ = {fmt(lam, 2)} · L (EWMA) = {fmt(le, 3)} · L (X) = {fmt(lx, 1)} · cautela = {dias} dias · '
                   f'exclusão automática: {"sim" if automatico else "não"}.')
    return dict(modo=modo, inicio=inicio, fim=fim, fim2=mon.fim_fase2(fim, meses_f2), lam=lam, le=le, lx=lx,
                dias=int(dias), automatico=automatico, excluir=list(excluir), justificativa=justificativa,
                alfa=alfa, max_exclusao=max_exclusao)


def _territorio(g: pd.DataFrame, municipios_menu: list):
    col1, col2 = st.columns([1.4, 1])
    with col1:
        granularidade = st.radio('Granularidade territorial', GRANULARIDADES, horizontal=True, key='mon_granularidade',
                                 help='O protocolo recomenda o nível estadual. Regiões e municípios são avaliados quanto '
                                      'à aplicabilidade antes da leitura dos sinais.')
    with col2:
        if granularidade == 'Região de saúde':
            regiao = st.selectbox('Região de saúde (PDR 2024)', sorted(g['regiao_saude'].unique()), key='mon_regiao')
            return granularidade, f'Região {regiao}', g.loc[g['regiao_saude'].eq(regiao), 'cod_mun_res'].tolist()
        if granularidade == 'Município':
            nomes = sorted(g['no_municipio'])
            padrao = nomes.index(municipios_menu[0]) if municipios_menu and municipios_menu[0] in nomes else 0
            municipio = st.selectbox('Município de residência', nomes, index=padrao, key='mon_municipio')
            return granularidade, municipio, g.loc[g['no_municipio'].eq(municipio), 'cod_mun_res'].tolist()
    return granularidade, 'Espírito Santo', g['cod_mun_res'].tolist()


def _tabela_quadrimestral(q: pd.DataFrame) -> pd.DataFrame:
    t = q[['Ano', 'Quadrimestre', 'Leitura', 'Meses', 'Completo', 'Óbitos', TAXA, 'Esperado (m·μ0)', 'LIC', 'LSC',
           'Razão observado/esperado', 'Sinal', 'Meses em consolidação']].copy()
    t['Ano'] = t['Ano'].astype(int).astype(str)
    t['Completo'] = np.where(t['Completo'].astype(bool), 'Sim', 'Não (parcial)')
    t['Sinal'] = t['Sinal'].fillna('').replace('', '—')
    t['Óbitos'] = t['Óbitos'].astype(int)
    return t


def _tabela_parametros(params: mon.Parametros) -> pd.DataFrame:
    d = params.como_dict()
    lista = lambda v: ', '.join(v) if v else 'Nenhum'
    linhas = [('Início da fase I', d['inicio']), ('Fim da fase I', d['fim']),
              ('Meses na fase I', str(d['n_inicial'])), ('Meses mantidos', str(d['n_controle'])),
              ('Média do processo (μ0)', fmt(d['mu0'], 4)), ('Desvio-padrão (σ0 = AM̄/1,128)', fmt(d['sigma0'], 4)),
              ('Amplitude móvel média (AM̄)', fmt(d['am_media'], 4)), ('Largura L do gráfico X', fmt(d['largura'], 2)),
              ('LIC do gráfico X', fmt(d['lic_x'], 4)), ('LSC do gráfico X', fmt(d['lsc_x'], 4)),
              ('LSC do gráfico AM', fmt(d['lsc_am'], 4)), ('Meses excluídos (automático)', lista(d['excluidos'])),
              ('Meses excluídos pela vigilância', lista(d['manuais'])), ('Iterações da fase I', str(d['iteracoes'])),
              ('Fase I estável', 'Sim' if d['estavel'] else 'Não')]
    return pd.DataFrame(linhas, columns=['Parâmetro', 'Valor'])


def _tabela_descritivas(d: dict) -> pd.DataFrame:
    return pd.DataFrame({'Medida': list(d), 'Valor': [str(v) if k == 'n' else fmt(v, 4) for k, v in d.items()]})


def _tabela_sinais(f2: pd.DataFrame) -> pd.DataFrame:
    t = f2[['Período', 'Óbitos', 'População', TAXA, 'AM', 'EWMA', 'LIC X', 'LSC X', 'LIC EWMA', 'LSC EWMA',
            'Sinal X', 'Sinal AM', 'Sinal EWMA', 'Em consolidação']].copy()
    t['Óbitos'] = t['Óbitos'].astype(int)
    t['População'] = t['População'].round().astype('int64')
    t.insert(0, 'Mês', [mon.rotulo_mes(v) for v in t.pop('Período')])
    t['Em consolidação'] = np.where(t['Em consolidação'], 'Sim', 'Não')
    for coluna in ('Sinal X', 'Sinal AM', 'Sinal EWMA'):
        t[coluna] = t[coluna].replace('', '—')
    return t


def mostrar_monitoramento(f, p, g, meta, ano, indicador, sexo_filtro, municipios=None):
    titulo, ajuda = st.columns([5, 1], vertical_alignment='center')
    with titulo:
        st.subheader('Monitoramento estatístico mensal')
    with ajuda:
        if st.button('Como ler', icon=':material/info:', help='Abra o guia para interpretar esta página.',
                     key='ajuda_monitoramento'):
            mostrar_guia()
    st.caption('Gráficos de controle X–AM e EWMA aplicados à taxa mensal: referência anterior ao início da fase II, '
               'com limites congelados no monitoramento. Usa o indicador e o sexo do menu lateral; o ano selecionado define a leitura '
               'quadrimestral em destaque.')
    granularidade, nome_territorio, codigos = _territorio(g, municipios or [])
    nf, npop = recortar(f, p, indicador, codigos)
    if sexo_filtro != 'Todos':
        nf, npop = nf[nf.sexo.eq(sexo_filtro)], npop[npop.sexo.eq(sexo_filtro)]
    serie = mon.serie_mensal(nf, npop)
    if len(serie) < 24:
        st.info('A série mensal deste recorte tem menos de 24 meses com cobertura; não é possível estimar a fase I.')
        return
    base = mon.data_atualizacao(meta)
    ultimo = serie['Período'].max()
    try:
        cfg = mon.ler_protocolo(RAIZ / 'config.toml')
        proto = _protocolo(serie, indicador, cfg, ultimo)
    except ValueError as erro:
        st.info(f'Configuração indisponível: {erro}')
        return
    if proto['excluir'] and proto['modo'] == 'Ajuste pela vigilância' and not proto['justificativa'].strip():
        st.info('Registre a justificativa das exclusões antes de calcular os limites.')
        return

    populacao = meta.get('populacao', {}).get(str(int(ultimo.year)), {})
    consolidacao = mon.em_consolidacao(serie['Período'], base, proto['dias'])
    with st.container(border=True):
        st.markdown(f'**Situação dos dados · {nome_territorio}**')
        st.write(f'Série disponível: {mon.rotulo_mes(serie["Período"].min())} a {mon.rotulo_mes(ultimo)}. '
                 'Os resultados refletem os registros disponíveis; investigação e consolidação podem gerar atrasos e revisões.')
        st.caption('Meses no prazo de cautela: ' + (', '.join(mon.rotulo_mes(v) for v in serie['Período'][consolidacao])
                                                  or 'nenhum identificado') + '. O prazo não certifica completude.')
        if populacao.get('provisorio'):
            st.caption(f"População de {populacao.get('ano_fonte')} aplicada provisoriamente a {int(ultimo.year)}.")
    try:
        r = mon.analisar(serie, proto['inicio'], proto['fim'], proto['fim2'], lam=proto['lam'], largura_ewma=proto['le'],
                         largura=proto['lx'], excluir=proto['excluir'], automatico=proto['automatico'], data_base=base,
                         dias_consolidacao=proto['dias'], defasagens_lb=tuple(cfg['defasagens_ljung_box']),
                         alfa=proto['alfa'], max_exclusao=proto['max_exclusao'])
    except ValueError as erro:
        st.info(f'Não foi possível aplicar o protocolo a este recorte: {erro}')
        return
    inicio_f2 = mon.rotulo_mes(r.fase_ii['Período'].min()) if not r.fase_ii.empty else '—'
    st.caption(f'Fase I: {r.params.inicio}–{r.params.fim} ({r.params.n_controle} de {r.params.n_inicial} meses mantidos). '
               f'Fase II: de {inicio_f2} até {r.configuracao["fim_fase2"] or "—"}, com limites congelados.')
    if ultimo > proto['fim2']:
        st.info(f'A série inclui meses posteriores ao horizonte escolhido ({mon.rotulo_mes(proto["fim2"])}). '
                'Eles não entram nesta fase II.')

    situacao, explicacao = viabilidade(r.referencia, r.pressupostos, proto['alfa'])
    {'Adequado': st.success, 'Com ressalvas': st.warning, 'Não recomendado': st.error}[situacao](
        f'Aplicabilidade ao recorte ({granularidade.lower()}): **{situacao}**. {explicacao}')
    if not r.params.estavel:
        st.warning('Há sinais X/AM na referência. Os limites são exploratórios; investigue as causas e a estabilidade '
                   'antes de usá-los operacionalmente. Não exclua meses apenas para eliminar sinais.')
    rejeitados = r.pressupostos.loc[r.pressupostos['Decisão'] == 'Rejeita H0', 'Teste'].tolist()
    alertas = [t for t in rejeitados if t.startswith(('Cox', 'Ljung'))]
    if alertas:
        st.warning('A referência apresenta indício de ' + ' e '.join(
            sorted({'tendência' if t.startswith('Cox') else 'dependência temporal' for t in alertas})) +
            '. Compare os cenários de sensibilidade e investigue o processo; mudar a janela não garante adequação.')

    contexto = dict(indicador=indicador, territorio=nome_territorio, granularidade=granularidade,
                    sexo=sexo_filtro, base=f'{pd.Timestamp(base):%d/%m/%Y}' if base else None,
                    consolidacao=', '.join(mon.rotulo_mes(v) for v in serie['Período'][consolidacao]))
    manifesto = dict(protocolo=r.configuracao['protocolo'], indicador=indicador, territorio=nome_territorio,
                     granularidade=granularidade, sexo=sexo_filtro, modo=proto['modo'],
                     municipios=sorted(codigos), parametros=r.configuracao, processo=r.params.como_dict(),
                     entrada=dict(inicio_fase1=f'{proto["inicio"]:%Y-%m}', fim_fase1=f'{proto["fim"]:%Y-%m}',
                                  fim_fase2=f'{proto["fim2"]:%Y-%m}', lam=proto['lam'], largura_ewma=proto['le'],
                                  largura=proto['lx'], automatico=proto['automatico'],
                                  excluir=[f'{v:%Y-%m}' for v in proto['excluir']],
                                  data_base=str(base) if base else None, dias_consolidacao=proto['dias'],
                                  alfa=proto['alfa'], max_exclusao=proto['max_exclusao'],
                                  defasagens_lb=list(cfg['defasagens_ljung_box'])),
                     justificativa_exclusoes=proto['justificativa'],
                     janelas_sensibilidade=[24, 36, 48, 64], selecao_por_significancia=False,
                     sha256_dataset=hashlib.sha256((DADOS / 'dataset.zip').read_bytes()).hexdigest(),
                     sha256_regioes=hashlib.sha256((DADOS / 'regioes_pdr2024.csv').read_bytes()).hexdigest(),
                     sha256_codigo={str(p): hashlib.sha256((RAIZ / p).read_bytes()).hexdigest()
                                    for p in ('dominio/monitoramento.py', 'dominio/dados.py',
                                              'painel/vistas/monitoramento.py', 'config.toml')},
                     versoes=dict(numpy=np.__version__, pandas=pd.__version__, streamlit=st.__version__))
    parametros_json = json.dumps(manifesto, ensure_ascii=False, indent=2, default=str)
    arquivo = f"monitoramento_{indicador.split(' ')[0].lower()}_{nome_territorio.replace(' ', '_').lower()}.pdf"
    st.download_button('Baixar relatório do monitoramento (PDF)',
                       data=partial(relatorio_monitoramento, r, contexto, dict(proto),
                                    tabela_arl(proto['lam'], proto['le'], proto['lx']), (situacao, explicacao)),
                       file_name=arquivo, mime='application/pdf', on_click='ignore', icon=':material/picture_as_pdf:',
                       help='Resumo, fase I (pressupostos, gráficos X–AM de cada iteração e EWMA), fase II (X, AM e '
                            'EWMA), leitura quadrimestral e parâmetros, com a configuração em uso nesta página.')
    secao = st.radio('Seção', SECOES, horizontal=True, key='mon_secao', label_visibility='collapsed')
    f2 = r.fase_ii
    if secao == 'Resumo':
        consolidados = f2[~f2['Em consolidação']] if not f2.empty else f2
        if consolidados.empty:
            st.info('Ainda não há meses consolidados na fase II.')
        else:
            u = consolidados.iloc[-1]
            a, b, c, d = st.columns(4)
            a.metric(f'Último mês fora do prazo de cautela · {mon.rotulo_mes(u["Período"])}', fmt(u[TAXA], 3),
                     f'{fmt((u[TAXA] / r.params.mu0 - 1) * 100, 1)}% sobre μ0', delta_color='inverse')
            b.metric('Óbitos no mês', fmt(u['Óbitos'], 0))
            c.metric('Gráfico X', u['Sinal X'] or 'Sem sinal')
            d.metric('EWMA', u['Sinal EWMA'] or 'Sem sinal')
            st.plotly_chart(figura_serie(r), width='stretch')
            st.markdown('**Últimos meses**')
            st.dataframe(_tabela_sinais(f2.tail(8)), hide_index=True, width='stretch',
                         column_config={TAXA: st.column_config.NumberColumn(format='%.3f'),
                                        'EWMA': st.column_config.NumberColumn(format='%.3f'),
                                        'AM': st.column_config.NumberColumn(format='%.3f')})
            q = r.quadrimestral
            if not q.empty:
                atual = q[q['Ano'] == q['Ano'].max()].tail(2)
                st.markdown('**Quadrimestre mais recente**')
                st.dataframe(_tabela_quadrimestral(atual), hide_index=True, width='stretch',
                             column_config={c: st.column_config.NumberColumn(format='%.3f')
                                            for c in (TAXA, 'Esperado (m·μ0)', 'LIC', 'LSC', 'Razão observado/esperado')})
    elif secao == 'Fase I · referência':
        st.markdown('**Estatísticas descritivas da fase I** (taxa mensal por 100 mil)')
        st.dataframe(_tabela_descritivas(r.descritivas), hide_index=True, width='stretch', height=36 * 13 + 3)
        st.markdown(f'**Verificação dos pressupostos** (α = {fmt(proto["alfa"], 2)})')
        st.dataframe(r.pressupostos, hide_index=True, width='stretch',
                     column_config={'Estatística': st.column_config.NumberColumn(format='%.4f'),
                                    'Valor-p': st.column_config.NumberColumn(format='%.4f')})
        st.caption('Cox–Stuart usa aproximação normal. Em 24 meses há no máximo oito pares: o valor-p pode diferir '
                   'de um cálculo binomial exato. Não rejeitar H₀ não confirma o pressuposto nem demonstra equivalência.')
        x = r.referencia[TAXA].to_numpy(dtype=float)
        k = min(24, len(x) // 2)
        c1, c2, c3 = st.columns(3)
        c1.plotly_chart(figura_qq(x), width='stretch')
        c2.plotly_chart(figura_fac(mon.fac(x, k), 'FAC', len(x)), width='stretch')
        c3.plotly_chart(figura_fac(mon.facp(x, k), 'FACP', len(x)), width='stretch')
        st.markdown('**Iterações da fase I (exclusão de pontos fora de controle)**')
        st.dataframe(r.iteracoes, hide_index=True, width='stretch',
                     column_config={c: st.column_config.NumberColumn(format='%.4f')
                                    for c in ('μ0', 'σ0', 'AM média', 'LIC X', 'LSC X', 'LSC AM')})
        ultima = int(r.iteracoes['Iteração'].max())
        k = ultima
        if ultima > 1:
            k = st.select_slider('Iteração exibida nos gráficos X e AM da fase I', options=list(range(1, ultima + 1)),
                                 value=ultima, key='mon_iteracao',
                                 format_func=lambda i: f'{i}ª' + (' (final)' if i == ultima else ''),
                                 help='Cada iteração recalcula os limites sem os meses excluídos nas anteriores.')
        st.plotly_chart(figura_fase1_iteracao(r, k), width='stretch')
        st.plotly_chart(figura_ewma(r, proto['lam'], proto['le'], True, False), width='stretch')
        st.caption('Sinais do EWMA na fase I não levam à exclusão de meses: esse gráfico não é usado para estimar '
                   'os parâmetros do processo.')
    elif secao == 'Fase II · monitoramento mensal':
        st.plotly_chart(figura_x(r), width='stretch')
        st.plotly_chart(figura_am(r), width='stretch')
        st.plotly_chart(figura_ewma(r, proto['lam'], proto['le']), width='stretch')
        st.markdown('**Sinais e limites por mês**')
        st.dataframe(_tabela_sinais(f2), hide_index=True, width='stretch',
                     column_config={c: st.column_config.NumberColumn(format='%.3f')
                                    for c in (TAXA, 'AM', 'EWMA', 'LIC X', 'LSC X', 'LIC EWMA', 'LSC EWMA')})
    elif secao == 'Leitura quadrimestral':
        q = r.quadrimestral
        if q.empty:
            st.info('Não há meses na fase II para a leitura quadrimestral.')
        else:
            anos = sorted(q['Ano'].unique())
            destaque = ano if ano in anos else anos[-1]
            st.caption(f'Ano em destaque: {destaque} (definido no menu lateral). A taxa do quadrimestre é a soma das '
                       'taxas mensais; limites m·μ0 ± L·√m·σ0.')
            st.plotly_chart(figura_quadrimestral(q[q['Ano'] == destaque]), width='stretch')
            st.dataframe(_tabela_quadrimestral(q), hide_index=True, width='stretch',
                         column_config={c: st.column_config.NumberColumn(format='%.3f')
                                        for c in (TAXA, 'Esperado (m·μ0)', 'LIC', 'LSC', 'Razão observado/esperado')})
    elif secao == 'Sensibilidade':
        st.markdown('**Influência da extensão da fase I**')
        st.caption('As quatro janelas usam o mesmo fim da fase I, a mesma fase II e os mesmos parâmetros. '
                   'Todos os cenários são apresentados, inclusive os indisponíveis. Não há seleção por valor-p ou número de sinais.')
        sens = mon.sensibilidade(serie, proto['fim'], proto['fim2'], lam=proto['lam'], largura_ewma=proto['le'],
                                 largura=proto['lx'], excluir=proto['excluir'], automatico=proto['automatico'],
                                 data_base=base, dias_consolidacao=proto['dias'],
                                 defasagens_lb=tuple(cfg['defasagens_ljung_box']), alfa=proto['alfa'],
                                 max_exclusao=proto['max_exclusao']).assign(Indicador=indicador, Território=nome_territorio,
                                                                         Sexo=sexo_filtro)
        st.dataframe(sens, hide_index=True, width='stretch')
        st.download_button('Baixar sensibilidade (CSV)', sens.to_csv(index=False, sep=';', decimal=',').encode('utf-8-sig'),
                           'sensibilidade_fase1.csv', 'text/csv')
        st.download_button('Baixar configuração da sensibilidade (JSON)', parametros_json,
                           'configuracao_sensibilidade.json', 'application/json')
        st.caption('Sinais são contados somente fora do prazo de cautela. A concordância entre janelas não demonstra '
                   'equivalência e divergências não justificam escolher retrospectivamente um resultado favorável.')
    else:
        st.markdown('**Parâmetros estimados na referência**')
        st.dataframe(_tabela_parametros(r.params), hide_index=True, width='stretch', height=36 * 16 + 3)
        st.markdown('**Desempenho teórico (ARL: número médio de meses até o sinal)**')
        st.dataframe(tabela_arl(proto['lam'], proto['le'], proto['lx']), hide_index=True, width='stretch',
                     column_config={c: st.column_config.NumberColumn(format='%.1f') for c in
                                    ('Gráfico X (meses até o sinal)', 'Leitura quadrimestral X̄ (meses)',
                                     'EWMA (meses até o sinal)')})
        st.caption('Deslocamento 0 = processo sob controle (alarmes falsos). Valores obtidos por cadeia de Markov '
                   '(EWMA com limites assintóticos) e pela distribuição normal (X e X̄), sob independência e parâmetros '
                   'conhecidos. O EWMA aplicado tem limites de partida; o ARL exibido não é seu desempenho efetivo.')
        st.download_button('Baixar parâmetros (JSON)', parametros_json,
                           'parametros_monitoramento.json', 'application/json')
        st.download_button('Baixar sinais mensais (CSV)', _tabela_sinais(f2).to_csv(index=False, sep=';', decimal=',')
                           .encode('utf-8-sig'), 'monitoramento_mensal.csv', 'text/csv')
        if not r.quadrimestral.empty:
            st.download_button('Baixar leitura quadrimestral (CSV)', r.quadrimestral.to_csv(index=False, sep=';', decimal=',')
                               .encode('utf-8-sig'), 'monitoramento_quadrimestral.csv', 'text/csv')
        trecho = (f'[monitoramento]\nlambda_ewma = {proto["lam"]}\nlargura_ewma = {proto["le"]}\n'
                  f'largura_x = {proto["lx"]}\nalfa = {proto["alfa"]}\nmax_exclusao = {proto["max_exclusao"]}\n'
                  f'dias_consolidacao = {proto["dias"]}\nmeses_fase2 = {int((proto["fim2"].year-proto["fim"].year)*12 + proto["fim2"].month-proto["fim"].month)}\n'
                  f'exclusao_automatica = {str(proto["automatico"]).lower()}\n'
                  f'defasagens_ljung_box = {list(cfg["defasagens_ljung_box"])}\n\n'
                  f'[monitoramento.fase1]\n"{indicador}" = ["{pd.Timestamp(proto["inicio"]):%Y-%m}", '
                  f'"{pd.Timestamp(proto["fim"]):%Y-%m}"]\n')
        trecho += ('\n[monitoramento.exclusoes]\n"' + indicador + '" = [' +
                   ', '.join(f'"{pd.Timestamp(v):%Y-%m}"' for v in proto['excluir']) + ']\n'
                   '\n[monitoramento.justificativas]\n"' + indicador + '" = ' +
                   json.dumps(proto['justificativa'], ensure_ascii=False) + '\n')
        st.markdown('**Para tornar o ajuste permanente**, atualize as chaves existentes no config.toml (não duplique seções):')
        st.code(trecho, language='toml')
    st.caption('Sinais estatísticos orientam a investigação; não estabelecem causas. Dados agregados não permitem '
               'inferir risco individual.')
