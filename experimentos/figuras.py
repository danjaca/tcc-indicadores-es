"""Figuras do monitoramento estatístico mensal (PNG), geradas a partir dos resultados.

As figuras não têm título interno: a identificação segue a NBR 14724 no texto.
Os números usam vírgula decimal.
"""
from __future__ import annotations

from pathlib import Path

import matplotlib
matplotlib.use('Agg')
import matplotlib.dates as mdates
import matplotlib.pyplot as plt
from matplotlib.ticker import FuncFormatter, MaxNLocator
import numpy as np
import pandas as pd

from dominio import monitoramento as mon
from dominio.monitoramento import TAXA

AZUL = '#126c83'
CINZA = '#94a3b8'
CINZA_ESCURO = '#475569'
VERMELHO = '#bd4545'
AZUL_SINAL = '#2563eb'
LARANJA = '#d97706'
ROXO = '#7c3aed'
LARGURA = 6.3  # polegadas (16 cm)
NOMES = {'Suicídio geral': 'Suicídio (geral)', 'Homicídios — jovens de 15 a 29 anos': 'Homicídio de jovens de 15 a 29 anos',
         'Homicídios — mulheres de 10 a 59 anos': 'Homicídio de mulheres de 10 a 59 anos'}
ARQ = {'Suicídio geral': 'suicidio', 'Homicídios — jovens de 15 a 29 anos': 'homicidio_jovens',
       'Homicídios — mulheres de 10 a 59 anos': 'homicidio_mulheres'}

plt.rcParams.update({
    'font.family': ['Liberation Sans', 'DejaVu Sans'], 'font.size': 8.5, 'axes.titlesize': 9, 'axes.labelsize': 8.5,
    'legend.fontsize': 7.5, 'xtick.labelsize': 7.5, 'ytick.labelsize': 7.5, 'axes.spines.top': False,
    'axes.spines.right': False, 'axes.grid': True, 'grid.color': '#e2e8f0', 'grid.linewidth': .6,
    'savefig.dpi': 220, 'savefig.bbox': 'tight', 'savefig.pad_inches': .04})


def _virgula(casas=2):
    def rotulo(v, _):
        c = casas
        while c < casas + 2 and abs(round(v, c) - v) > 1e-9:
            c += 1
        return f'{v:.{c}f}'.replace('.', ',')
    return FuncFormatter(rotulo)


def _eixo_y(ax, casas):
    """Marcas em múltiplos de 1, 2 ou 5 (evita quartos arredondados) com vírgula decimal."""
    ax.yaxis.set_major_locator(MaxNLocator(nbins=6, steps=[1, 2, 5, 10]))
    ax.yaxis.set_major_formatter(_virgula(casas))


def _meses(ax, intervalo=6):
    ax.xaxis.set_major_locator(mdates.MonthLocator(bymonth=[1] if intervalo >= 12 else [1, 7]))
    ax.xaxis.set_major_formatter(FuncFormatter(
        lambda v, _: f"{mon.MESES[mdates.num2date(v).month - 1]}/{str(mdates.num2date(v).year)[2:]}"))


def _sinais(ax, datas, valores, rotulos):
    datas, valores, rotulos = np.asarray(datas), np.asarray(valores, dtype=float), np.asarray(rotulos)
    for alvo, cor, marca, nome in (('Aumento', VERMELHO, '^', 'Sinal de aumento'),
                                   ('Redução', AZUL_SINAL, 'v', 'Sinal de redução'),
                                   ('Variabilidade', VERMELHO, '^', 'Sinal de variabilidade')):
        m = rotulos == alvo
        if m.any():
            ax.scatter(datas[m], valores[m], marker=marca, s=34, color=cor, zorder=5, label=nome)


def _consolidacao(ax, f2, coluna):
    m = f2['Em consolidação'].to_numpy(bool)
    if m.any():
        ax.scatter(f2['Período'][m], f2[coluna][m], s=46, facecolors='white', edgecolors=ROXO, linewidths=1.2,
                   zorder=6, label='Mês em consolidação')


def series(destino: Path, resultados: dict) -> None:
    fig, eixos = plt.subplots(3, 1, figsize=(LARGURA, 6.6), sharex=True)
    for ax, (ind, r) in zip(eixos, resultados.items()):
        s = r.serie
        ax.plot(s['Período'], s[TAXA], color=AZUL, lw=1.1)
        p0 = pd.Timestamp(r.referencia['Período'].min())
        p1 = pd.Timestamp(r.referencia['Período'].max()) + pd.offsets.MonthEnd(0)
        ax.axvspan(p0, p1, color='#e2e8f0', alpha=.8, lw=0, label='Fase I (referência)')
        ax.axvline(p1, color=CINZA_ESCURO, ls=':', lw=.9)
        f2 = r.fase_ii
        _consolidacao(ax, f2, TAXA)
        ax.set_title(NOMES[ind], loc='left', fontweight='bold')
        _eixo_y(ax, 1 if s[TAXA].max() > 2 else 2)
        ax.set_ylabel('Taxa mensal\npor 100 mil')
        _meses(ax, 12)
    eixos[0].legend(loc='lower right', bbox_to_anchor=(1, 1.0), ncol=2, frameon=False)
    eixos[-1].set_xlabel('Mês do óbito')
    fig.tight_layout()
    fig.savefig(destino / 'fig_series_mensais.png')
    plt.close(fig)


def pressupostos(destino: Path, resultados: dict) -> None:
    fig, eixos = plt.subplots(3, 3, figsize=(LARGURA, 6.4))
    for linha, (ind, r) in enumerate(resultados.items()):
        x = r.referencia[TAXA].to_numpy(dtype=float)
        n = len(x)
        z = (np.sort(x) - x.mean()) / x.std(ddof=1)
        teoricos = np.array([mon.normal_ppf((i - .375) / (n + .25)) for i in range(1, n + 1)])
        ax = eixos[linha, 0]
        ax.scatter(teoricos, z, s=9, color=AZUL)
        lim = [min(teoricos.min(), z.min()) - .2, max(teoricos.max(), z.max()) + .2]
        ax.plot(lim, lim, color=VERMELHO, lw=.9)
        ax.set_ylabel(NOMES[ind].replace(' de ', '\nde ', 1), fontsize=7.5)
        ax.xaxis.set_major_formatter(_virgula(0)); ax.yaxis.set_major_formatter(_virgula(0))
        k = min(24, n // 2)
        limite = 1.96 / np.sqrt(n)
        for col, (valores, nome) in enumerate(((mon.fac(x, k)[1:], 'FAC'), (mon.facp(x, k)[1:], 'FACP')), start=1):
            ax = eixos[linha, col]
            ax.vlines(range(1, k + 1), 0, valores, color=AZUL, lw=1.4)
            ax.axhline(0, color=CINZA_ESCURO, lw=.6)
            ax.axhline(limite, color=VERMELHO, ls='--', lw=.8); ax.axhline(-limite, color=VERMELHO, ls='--', lw=.8)
            ax.set_ylim(-.6, .6)
            ax.yaxis.set_major_formatter(_virgula(1))
            ax.xaxis.set_major_locator(MaxNLocator(integer=True, nbins=6))
            if linha == 0:
                ax.set_title(nome)
            if linha == 2:
                ax.set_xlabel('Defasagem (meses)')
    eixos[0, 0].set_title('Q-Q normal')
    eixos[2, 0].set_xlabel('Quantis teóricos')
    fig.tight_layout()
    fig.savefig(destino / 'fig_pressupostos_fase1.png')
    plt.close(fig)


def graficos_controle(destino: Path, ind: str, r: mon.Resultado) -> None:
    p = r.params
    f1, f2, e1 = r.fase_i, r.fase_ii, r.ewma_fase_i
    controle = f1['Situação fase I'].str.startswith(('Em controle', 'Mantido'))
    fig, (ax1, ax2, ax3) = plt.subplots(3, 1, figsize=(LARGURA, 7.2), sharex=True,
                                        gridspec_kw={'height_ratios': [1.25, .8, 1.1]})
    inicio = f1['Período'].min() - pd.offsets.MonthBegin(1)
    fim = f2['Período'].max() + pd.offsets.MonthBegin(1)
    fronteira = f1['Período'].max() + pd.Timedelta(days=16)
    for ax in (ax1, ax2, ax3):
        ax.axvspan(inicio, fronteira, color='#f1f5f9', lw=0)
        ax.axvline(fronteira, color=CINZA_ESCURO, ls=':', lw=.9)
    # (a) X
    ax1.plot(f1['Período'][controle], f1[TAXA][controle], 'o-', color=CINZA, ms=3, lw=.9, label='Fase I (referência mantida)')
    if (~controle).any():
        ax1.scatter(f1['Período'][~controle], f1[TAXA][~controle], marker='x', s=36, color=LARANJA, zorder=5,
                    label='Excluído na fase I')
    ax1.plot(f2['Período'], f2[TAXA], 'o-', color=AZUL, ms=3.2, lw=1.1, label='Fase II (monitoramento)')
    for valor, estilo, nome in ((p.lsc_x, '--', 'LSC / LIC'), (p.mu0, '-', 'LM (μ0)'), (p.lic_x, '--', None)):
        ax1.axhline(valor, color=VERMELHO if estilo == '--' else CINZA_ESCURO, ls=estilo, lw=.9, label=nome)
    _sinais(ax1, f2['Período'], f2[TAXA], f2['Sinal X'])
    _consolidacao(ax1, f2, TAXA)
    ax1.set_ylabel('Taxa mensal\npor 100 mil')
    ax1.set_title('(a) Medidas individuais (X)', loc='left')
    # (b) AM
    ax2.plot(f1['Período'][controle], f1['AM'][controle], 'o-', color=CINZA, ms=2.6, lw=.8)
    ax2.plot(f2['Período'], f2['AM'], 'o-', color=AZUL, ms=2.8, lw=1)
    ax2.axhline(p.lsc_am, color=VERMELHO, ls='--', lw=.9)
    ax2.axhline(p.am_media, color=CINZA_ESCURO, lw=.9)
    _sinais(ax2, f2['Período'], f2['AM'], f2['Sinal AM'])
    ax2.set_ylabel('Amplitude\nmóvel')
    ax2.set_title('(b) Amplitude móvel (AM)', loc='left')
    # (c) EWMA
    ax3.plot(e1['Período'], e1['EWMA'], '-', color=CINZA, lw=1)
    ax3.plot(e1['Período'], e1['LSC EWMA'], '--', color=VERMELHO, lw=.7, alpha=.6)
    ax3.plot(e1['Período'], e1['LIC EWMA'], '--', color=VERMELHO, lw=.7, alpha=.6)
    ax3.plot(f2['Período'], f2['EWMA'], 'o-', color=AZUL, ms=3, lw=1.1)
    ax3.plot(f2['Período'], f2['LSC EWMA'], '--', color=VERMELHO, lw=.9)
    ax3.plot(f2['Período'], f2['LIC EWMA'], '--', color=VERMELHO, lw=.9)
    ax3.axhline(p.mu0, color=CINZA_ESCURO, lw=.9)
    _sinais(ax3, f2['Período'], f2['EWMA'], f2['Sinal EWMA'])
    _consolidacao(ax3, f2, 'EWMA')
    ax3.set_ylabel('EWMA')
    ax3.set_title(f'(c) EWMA (λ = {r.configuracao["lam"]:g}; L = {r.configuracao["largura_ewma"]:g})'.replace('.', ','),
                  loc='left')
    for ax in (ax1, ax2, ax3):
        casas = 1 if r.serie[TAXA].max() > 2 else 2
        _eixo_y(ax, casas)
        _meses(ax, 6)
    ax3.set_xlim(inicio, fim)
    handles, labels = [], []
    for ax in (ax1, ax3):
        h, l = ax.get_legend_handles_labels()
        for hh, ll in zip(h, l):
            if ll and ll not in labels:
                handles.append(hh); labels.append(ll)
    fig.legend(handles, labels, loc='lower center', ncol=4, frameon=False, bbox_to_anchor=(.5, -.01))
    fig.tight_layout(rect=(0, .05, 1, 1))
    fig.savefig(destino / f'fig_controle_{ARQ[ind]}.png')
    plt.close(fig)


def quadrimestral(destino: Path, resultados: dict) -> None:
    fig, eixos = plt.subplots(1, 3, figsize=(LARGURA, 2.9))
    for ax, (ind, r) in zip(eixos, resultados.items()):
        q = r.quadrimestral[(r.quadrimestral['Leitura'] == 'Quadrimestre isolado') & r.quadrimestral['Completo']]
        q = q.reset_index(drop=True)
        x = np.arange(len(q))
        cores = [AZUL if c else '#cbd5e1' for c in q['Completo']]
        ax.bar(x, q[TAXA], color=cores, width=.62)
        ax.errorbar(x, q['Esperado (m·μ0)'], yerr=[q['Esperado (m·μ0)'] - q['LIC'], q['LSC'] - q['Esperado (m·μ0)']],
                    fmt='_', color=VERMELHO, ms=10, capsize=3, lw=1, label='Esperado e limites')
        for i, (_, l) in enumerate(q.iterrows()):
            if l['Sinal']:
                ax.annotate('▼' if l['Sinal'] == 'Redução' else '▲', (i, l[TAXA]), ha='center', va='bottom',
                            color=AZUL_SINAL if l['Sinal'] == 'Redução' else VERMELHO, fontsize=9)
            if l['Meses em consolidação']:
                ax.annotate('*', (i, max(l[TAXA], l['LSC'])), ha='center', va='bottom', color=ROXO, fontsize=11)
        ax.set_xticks(x, [f"{l['Quadrimestre']}\n{l['Ano']}" for _, l in q.iterrows()], fontsize=6.8)
        ax.set_title(NOMES[ind].replace(' de ', '\nde ', 1), fontsize=8)
        ax.yaxis.set_major_formatter(_virgula(1))
    eixos[0].set_ylabel('Taxa do quadrimestre por 100 mil')
    h, l = eixos[0].get_legend_handles_labels()
    fig.legend(h, l, loc='lower center', frameon=False, fontsize=7.5, bbox_to_anchor=(.5, -.02))
    fig.tight_layout(rect=(0, .06, 1, 1))
    fig.savefig(destino / 'fig_quadrimestral.png')
    plt.close(fig)


def retrospectiva_homicidio(destino: Path, r: mon.Resultado) -> None:
    it = r.iteracoes.iloc[0]
    s = r.referencia
    fig, ax = plt.subplots(figsize=(LARGURA, 2.6))
    ax.plot(s['Período'], s[TAXA], 'o-', color=AZUL, ms=3, lw=1)
    ax.axhline(it['LSC X'], color=VERMELHO, ls='--', lw=.9, label='LSC / LIC (iteração 1)')
    ax.axhline(it['LIC X'], color=VERMELHO, ls='--', lw=.9)
    ax.axhline(it['μ0'], color=CINZA_ESCURO, lw=.9, label='LM (iteração 1)')
    fora = (s[TAXA] > it['LSC X']) | (s[TAXA] < it['LIC X'])
    ax.scatter(s['Período'][fora], s[TAXA][fora], marker='^', s=40, color=VERMELHO, zorder=5, label='Sinal de aumento')
    fev = s[s['Período'] == '2017-02-01']
    ax.annotate('fev./2017: paralisação da Polícia Militar', (fev['Período'].iloc[0], fev[TAXA].iloc[0]),
                xytext=(14, -4), textcoords='offset points', fontsize=7.5, va='center')
    ax.set_ylabel('Taxa mensal\npor 100 mil')
    ax.yaxis.set_major_formatter(_virgula(0))
    _meses(ax, 6)
    h, l = ax.get_legend_handles_labels()
    fig.legend(h, l, loc='lower center', frameon=False, ncol=3, bbox_to_anchor=(.5, -.02))
    fig.tight_layout(rect=(0, .1, 1, 1))
    fig.savefig(destino / 'fig_retro_homicidio_2016_2019.png')
    plt.close(fig)


def retrospectiva_suicidio(destino: Path, r: mon.Resultado) -> None:
    f2, e1, p = r.fase_ii, r.ewma_fase_i, r.params
    fig, ax = plt.subplots(figsize=(LARGURA, 2.8))
    fronteira = e1['Período'].max() + pd.Timedelta(days=16)
    ax.axvspan(e1['Período'].min() - pd.offsets.MonthBegin(1), fronteira, color='#f1f5f9', lw=0)
    ax.plot(e1['Período'], e1['EWMA'], color=CINZA, lw=1, label='EWMA na fase I (2019–2022)')
    ax.plot(f2['Período'], f2['EWMA'], 'o-', color=AZUL, ms=2.8, lw=1, label='EWMA na fase II (2023–2026)')
    ax.plot(f2['Período'], f2['LSC EWMA'], '--', color=VERMELHO, lw=.9, label='LSC / LIC')
    ax.plot(f2['Período'], f2['LIC EWMA'], '--', color=VERMELHO, lw=.9)
    ax.plot(e1['Período'], e1['LSC EWMA'], '--', color=VERMELHO, lw=.7, alpha=.5)
    ax.plot(e1['Período'], e1['LIC EWMA'], '--', color=VERMELHO, lw=.7, alpha=.5)
    ax.axhline(p.mu0, color=CINZA_ESCURO, lw=.9)
    _sinais(ax, f2['Período'], f2['EWMA'], f2['Sinal EWMA'])
    _consolidacao(ax, f2, 'EWMA')
    ax.set_ylabel('EWMA da taxa\nmensal por 100 mil')
    ax.yaxis.set_major_formatter(_virgula(2))
    _meses(ax, 12)
    ax.legend(loc='upper left', frameon=False, ncol=2)
    fig.tight_layout()
    fig.savefig(destino / 'fig_retro_suicidio_2019_2022.png')
    plt.close(fig)


def barros(destino: Path, r: mon.Resultado) -> None:
    f1, f2, p = r.fase_i, r.fase_ii, r.params
    controle = f1['Situação fase I'].str.startswith('Em controle')
    fig, ax = plt.subplots(figsize=(LARGURA, 2.5))
    ax.plot(f1['Período'][controle], f1[TAXA][controle], 'o-', color=CINZA, ms=3, lw=.9, label='Fase I (46 meses em controle)')
    ax.scatter(f1['Período'][~controle], f1[TAXA][~controle], marker='x', s=36, color=LARANJA, label='Excluídos (jun. e jul./2020)')
    ax.plot(f2['Período'], f2[TAXA], 'o-', color=AZUL, ms=3, lw=1, label='Fase II (jan.–jun./2021)')
    ax.axhline(p.lsc_x, color=VERMELHO, ls='--', lw=.9); ax.axhline(p.lic_x, color=VERMELHO, ls='--', lw=.9)
    ax.axhline(p.mu0, color=CINZA_ESCURO, lw=.9)
    _sinais(ax, f2['Período'], f2[TAXA], f2['Sinal X'])
    ax.set_ylabel('Taxa (X)')
    ax.yaxis.set_major_formatter(_virgula(0))
    _meses(ax, 6)
    ax.legend(loc='upper left', frameon=False, ncol=2, fontsize=7)
    fig.tight_layout()
    fig.savefig(destino / 'fig_verificacao_barros.png')
    plt.close(fig)


def gerar(destino: Path, resultados: dict, r_barros, r_greve, s_hom, cfg) -> None:
    destino.mkdir(parents=True, exist_ok=True)
    series(destino, resultados)
    pressupostos(destino, resultados)
    for ind, r in resultados.items():
        graficos_controle(destino, ind, r)
    quadrimestral(destino, resultados)
    retrospectiva_homicidio(destino, r_greve)
    barros(destino, r_barros)
