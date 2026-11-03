"""Relatórios em PDF do painel, gerados com matplotlib, sem serviços externos.

Cada aba oferece um relatório com o contexto dos filtros, as tabelas e os
gráficos principais. O relatório do monitoramento estatístico reúne o resumo do
último mês consolidado, a fase I (pressupostos, gráficos X–AM de cada iteração
e EWMA), a fase II (X, AM e EWMA), a leitura quadrimestral e os parâmetros
necessários para reproduzir a análise.
"""
from __future__ import annotations

import io
import textwrap
from datetime import datetime
from pathlib import Path

import matplotlib
matplotlib.use('Agg')
import matplotlib.dates as mdates
import matplotlib.pyplot as plt
from matplotlib.backends.backend_pdf import PdfPages
from matplotlib.lines import Line2D
from matplotlib.ticker import FuncFormatter, MaxNLocator
import numpy as np
import pandas as pd

from dominio import monitoramento as mon
from dominio.monitoramento import TAXA

A4 = (8.27, 11.69)
M = .075  # margem lateral, em fração da largura da página
AZUL = '#126c83'
CINZA = '#94a3b8'
CINZA_ESCURO = '#475569'
VERMELHO = '#bd4545'
AZUL_SINAL = '#2563eb'
LARANJA = '#d97706'
ROXO = '#7c3aed'
FUNDO = '#f1f5f9'
TEXTO = '#1e293b'
ESTILO = {'font.family': 'DejaVu Sans', 'font.size': 7.5, 'axes.titlesize': 8, 'axes.titleweight': 'bold',
          'axes.labelsize': 7, 'xtick.labelsize': 6.5, 'ytick.labelsize': 6.5, 'legend.fontsize': 6.5,
          'axes.spines.top': False, 'axes.spines.right': False, 'axes.grid': True, 'grid.color': '#e2e8f0',
          'grid.linewidth': .5, 'pdf.fonttype': 42, 'axes.titlelocation': 'left', 'savefig.bbox': 'standard'}


def fmt(valor, casas: int = 2) -> str:
    """Número no padrão brasileiro; textos são devolvidos sem alteração."""
    if valor is None:
        return '—'
    if isinstance(valor, str):
        return valor
    if isinstance(valor, (bool, np.bool_)):
        return 'Sim' if valor else 'Não'
    if isinstance(valor, pd.Timestamp):
        return mon.rotulo_mes(valor)
    if isinstance(valor, (int, np.integer)):
        return f'{int(valor):,}'.replace(',', '.')
    try:
        numero = float(valor)
    except (TypeError, ValueError):
        return str(valor)
    if not np.isfinite(numero):
        return '—'
    return f'{numero:,.{casas}f}'.replace(',', 'X').replace('.', ',').replace('X', '.')


def _virgula(casas: int):
    """Rótulos com vírgula decimal; acrescenta casas quando a marca não é exata (ex.: 4,25)."""
    def rotulo(v, _):
        c = casas
        while c < casas + 2 and abs(round(v, c) - v) > 1e-9:
            c += 1
        return f'{v:.{c}f}'.replace('.', ',')
    return FuncFormatter(rotulo)


def _meses(ax, passo: int = 3) -> None:
    ax.xaxis.set_major_locator(mdates.MonthLocator(bymonth=list(range(1, 13, passo))))
    ax.xaxis.set_major_formatter(FuncFormatter(
        lambda v, _: f'{mon.MESES[mdates.num2date(v).month - 1]}/{mdates.num2date(v):%y}'))


def _casas(valores) -> int:
    valores = pd.Series(valores, dtype=float).dropna()
    return 1 if not valores.empty and valores.abs().max() >= 2 else 2


class Documento:
    """Páginas A4 com fluxo vertical simples de títulos, textos, tabelas e gráficos."""

    def __init__(self, titulo: str, subtitulo: str = '', rodape: str = '', guardar_paginas: bool = False):
        self.titulo, self.subtitulo, self.rodape = titulo, subtitulo, rodape
        self._buf = io.BytesIO()
        self._pdf = PdfPages(self._buf, metadata={'Title': titulo, 'Subject': subtitulo,
                                                  'Author': 'Observatório de mortalidade · ES'})
        self._fig = None
        self._y = 0.
        self._n = 0
        self._guardar = guardar_paginas
        self.paginas: list = []
        self._contexto = plt.rc_context(ESTILO)
        self._contexto.__enter__()

    # -- páginas ---------------------------------------------------------------
    def _fechar_pagina(self) -> None:
        if self._fig is None:
            return
        self._pdf.savefig(self._fig)
        if self._guardar:
            self.paginas.append(self._fig)
        else:
            plt.close(self._fig)
        self._fig = None

    def _nova_pagina(self) -> None:
        self._fechar_pagina()
        self._n += 1
        fig = plt.figure(figsize=A4)
        fig.text(M, .975, self.titulo, fontsize=7, color=CINZA_ESCURO, va='top')
        if self.subtitulo:
            fig.text(1 - M, .975, self.subtitulo, fontsize=7, color=CINZA_ESCURO, va='top', ha='right')
        fig.add_artist(Line2D([M, 1 - M], [.962, .962], color='#cbd5e1', lw=.6))
        fig.text(M, .02, self.rodape, fontsize=6, color=CINZA_ESCURO, va='bottom')
        fig.text(1 - M, .02, f'Página {self._n}', fontsize=6.5, color=CINZA_ESCURO, va='bottom', ha='right')
        self._fig, self._y = fig, .945

    def quebra(self) -> None:
        if self._fig is not None and self._y < .8:
            self._nova_pagina()

    def _reservar(self, altura: float) -> None:
        if self._fig is None or self._y - altura < .05:
            self._nova_pagina()

    def finalizar(self) -> bytes:
        self._fechar_pagina()
        self._pdf.close()
        self._contexto.__exit__(None, None, None)
        return self._buf.getvalue()

    # -- elementos -------------------------------------------------------------
    def capa(self, titulo: str, linhas: list[str], destaques=()) -> None:
        self._nova_pagina()
        fig = self._fig
        partes = textwrap.wrap(titulo, 52)
        fig.text(M, .925, '\n'.join(partes), fontsize=16, weight='bold', color=AZUL, va='top', linespacing=1.2)
        y = .925 - .03 * len(partes) - .012
        for linha in linhas:
            for parte in textwrap.wrap(linha, 105) or ['']:
                fig.text(M, y, parte, fontsize=8.5, color=TEXTO, va='top')
                y -= .019
        y -= .008
        if destaques:
            n = len(destaques)
            largura = (1 - 2 * M - (n - 1) * .012) / n
            for i, item in enumerate(destaques):
                rotulo, valor = item[0], item[1]
                detalhe = item[2] if len(item) > 2 else ''
                ax = fig.add_axes([M + i * (largura + .012), y - .075, largura, .075])
                ax.set_axis_off()
                ax.add_patch(plt.Rectangle((0, 0), 1, 1, transform=ax.transAxes, color=FUNDO, zorder=0))
                ax.text(.06, .85, '\n'.join(textwrap.wrap(rotulo, 30)), fontsize=6.5, color=CINZA_ESCURO,
                        va='top', transform=ax.transAxes)
                ax.text(.06, .42, valor, fontsize=11.5, weight='bold', color='#0f172a', va='center',
                        transform=ax.transAxes)
                if detalhe:
                    ax.text(.06, .13, detalhe, fontsize=6, color=CINZA_ESCURO, va='center', transform=ax.transAxes)
            y -= .09
        self._y = y

    def secao(self, texto: str, minimo: float = .24) -> None:
        self._reservar(minimo)
        self._fig.text(M, self._y, texto, fontsize=11, weight='bold', color=AZUL, va='top')
        self._y -= .028

    def subtitulo_bloco(self, texto: str) -> None:
        self._reservar(.06)
        self._fig.text(M, self._y, texto, fontsize=8.5, weight='bold', color=TEXTO, va='top')
        self._y -= .02

    def paragrafo(self, texto: str, tamanho: float = 8, cor: str = TEXTO, italico: bool = False) -> None:
        largura = int(122 * 8 / tamanho)
        linhas = []
        for bloco in str(texto).split('\n'):
            linhas += textwrap.wrap(bloco, largura) or ['']
        altura_linha = .0142 * tamanho / 8
        while linhas:
            self._reservar(altura_linha * min(len(linhas), 2) + .004)
            cabe = max(1, int((self._y - .05) / altura_linha))
            parte, linhas = linhas[:cabe], linhas[cabe:]
            self._fig.text(M, self._y, '\n'.join(parte), fontsize=tamanho, color=cor, va='top',
                           linespacing=1.38, style='italic' if italico else 'normal')
            self._y -= altura_linha * len(parte) + .007

    def tabela(self, df: pd.DataFrame, titulo: str | None = None, nota: str | None = None,
               larguras=None, fonte: float = 6.8, casas: int = 3) -> None:
        if df is None or df.empty:
            return
        cab = [str(c) for c in df.columns]
        ncol = len(cab)
        if larguras is None:
            tamanhos = [max(max(len(w) for w in cab[j].split()) + 1, len(cab[j]) * .55,
                            *(len(fmt(v, casas)) for v in df.iloc[:, j])) for j in range(ncol)]
            tamanhos = [min(max(t, 4), 38) for t in tamanhos]
            larguras = [t / sum(tamanhos) for t in tamanhos]
        larguras = list(np.asarray(larguras, dtype=float) / np.sum(larguras))
        largura_pt = (1 - 2 * M) * A4[0] * 72
        chars = [max(4, int(w * largura_pt / (fonte * .56))) for w in larguras]
        numericas = [pd.api.types.is_numeric_dtype(df.iloc[:, j]) for j in range(ncol)]

        def quebrar(texto, j, fator=1.):
            return '\n'.join(textwrap.wrap(str(texto), max(4, int(chars[j] * fator)),
                                           break_long_words=False) or [''])

        # O negrito e o padding exigem mais espaço que a estimativa do corpo.
        cabecalho = [quebrar(c, j, .8) for j, c in enumerate(cab)]
        linhas = [[quebrar(fmt(v, casas), j) for j, v in enumerate(linha)] for linha in df.itertuples(index=False)]
        altura_linha = .0128 * fonte / 6.8

        def alt(celulas):
            return max(c.count('\n') + 1 for c in celulas) * altura_linha + .0055

        h_cab = alt(cabecalho)
        i = 0
        primeira = True
        while i < len(linhas):
            extra = .022 if titulo and primeira else 0
            self._reservar(extra + h_cab + alt(linhas[i]) + .01)
            if titulo and primeira:
                self.subtitulo_bloco(titulo)
            disponivel = self._y - .055
            bloco, altura = [], h_cab
            while i < len(linhas) and (not bloco or altura + alt(linhas[i]) <= disponivel):
                bloco.append(linhas[i])
                altura += alt(linhas[i])
                i += 1
            ax = self._fig.add_axes([M, self._y - altura, 1 - 2 * M, altura])
            ax.set_axis_off()
            tb = ax.table(cellText=bloco, colLabels=cabecalho, colWidths=larguras, cellLoc='left',
                          colLoc='left', bbox=[0, 0, 1, 1])
            tb.auto_set_font_size(False)
            tb.set_fontsize(fonte)
            alturas = [h_cab] + [alt(linha) for linha in bloco]
            for (r, c), cel in tb.get_celld().items():
                cel.set_height(alturas[r])
                cel.set_edgecolor('#cbd5e1')
                cel.set_linewidth(.4)
                if r == 0:
                    cel.set_facecolor('#e2e8f0')
                    cel.get_text().set_weight('bold')
                elif numericas[c]:
                    cel.get_text().set_horizontalalignment('right')
                    cel.PAD = .04
            self._y -= altura + .012
            primeira = False
        if nota:
            self.paragrafo(nota, tamanho=6.5, cor=CINZA_ESCURO, italico=True)

    def grafico(self, desenhar, altura: float, titulo: str | None = None, nota: str | None = None) -> None:
        self._reservar(altura + (.022 if titulo else 0) + (.02 if nota else 0))
        if titulo:
            self.subtitulo_bloco(titulo)
        desenhar(self._fig, [M, self._y - altura, 1 - 2 * M, altura])
        self._y -= altura + .014
        if nota:
            self.paragrafo(nota, tamanho=6.5, cor=CINZA_ESCURO, italico=True)


# -----------------------------------------------------------------------------
# Gráficos estáticos
# -----------------------------------------------------------------------------
def _eixos(fig, rect, alturas, folga=.018, esquerda=.07, direita=.01, topo_livre=0.):
    x, y, w, h = rect
    total = sum(alturas)
    util = h - folga * (len(alturas) - 1) - topo_livre
    topo = y + h - topo_livre
    eixos = []
    for a in alturas:
        hh = util * a / total
        eixos.append(fig.add_axes([x + esquerda, topo - hh, w - esquerda - direita, hh]))
        topo -= hh + folga
    return eixos


def _sinais(ax, datas, valores, rotulos) -> None:
    datas, valores, rotulos = np.asarray(datas), np.asarray(valores, dtype=float), np.asarray(rotulos)
    for alvo, cor, marca, nome in (('Aumento', VERMELHO, '^', 'Sinal de aumento'),
                                   ('Redução', AZUL_SINAL, 'v', 'Sinal de redução'),
                                   ('Variabilidade', VERMELHO, '^', 'Sinal de variabilidade')):
        m = rotulos == alvo
        if m.any():
            ax.scatter(datas[m], valores[m], marker=marca, s=26, color=cor, zorder=5, label=nome)


def _consolidacao(ax, f2, coluna) -> None:
    if f2.empty:
        return
    m = f2['Em consolidação'].to_numpy(bool)
    if m.any():
        ax.scatter(f2['Período'][m], f2[coluna][m], s=34, facecolors='white', edgecolors=ROXO, linewidths=1,
                   zorder=6, label='Mês em consolidação')


def _legenda(fig, eixos, rect) -> None:
    alcas, rotulos = [], []
    for ax in eixos:
        for h, l in zip(*ax.get_legend_handles_labels()):
            if l and not l.startswith('_') and l not in rotulos:
                alcas.append(h)
                rotulos.append(l)
    if alcas:
        fig.legend(alcas, rotulos, loc='upper center', ncol=min(5, len(alcas)), frameon=False,
                   bbox_to_anchor=(rect[0] + rect[2] / 2, rect[1] + .002), fontsize=6.3)


def desenho_serie(r: mon.Resultado):
    def desenhar(fig, rect):
        ax, = _eixos(fig, [rect[0], rect[1] + .02, rect[2], rect[3] - .02], [1])
        s = r.serie
        ax.plot(s['Período'], s[TAXA], color=AZUL, lw=1, label='Taxa mensal')
        p0 = r.referencia['Período'].min() - pd.Timedelta(days=15)
        p1 = r.referencia['Período'].max() + pd.Timedelta(days=15)
        ax.axvspan(p0, p1, color='#e2e8f0', alpha=.8, lw=0, label='Fase I (referência)')
        _consolidacao(ax, r.fase_ii, TAXA)
        ax.yaxis.set_major_formatter(_virgula(_casas(s[TAXA])))
        ax.set_ylabel('Taxa mensal por 100 mil')
        ax.xaxis.set_major_locator(mdates.YearLocator())
        ax.xaxis.set_major_formatter(mdates.DateFormatter('%Y'))
        _legenda(fig, [ax], rect)
    return desenhar


def desenho_fase1_iteracao(r: mon.Resultado, k: int):
    """Gráficos X e AM com os limites da iteração k da fase I."""
    def desenhar(fig, rect):
        d = mon.iteracao_fase1(r, k)
        lim, cons, excl = d['limites'], d['considerados'], d['excluidos_antes']
        ax1, ax2 = _eixos(fig, [rect[0], rect[1] + .022, rect[2], rect[3] - .022], [1.25, .9], folga=.04,
                          topo_livre=.016)
        ax1.plot(cons['Período'], cons[TAXA], 'o-', color=CINZA_ESCURO, ms=2.4, lw=.8, label='Meses considerados')
        if not excl.empty:
            ax1.scatter(excl['Período'], excl[TAXA], marker='x', s=24, color=LARANJA, zorder=5,
                        label='Excluído em iteração anterior')
        fora = cons['Sinal X'] | cons['Sinal AM']
        if fora.any():
            ax1.scatter(cons.loc[fora, 'Período'], cons.loc[fora, TAXA], s=34, facecolors='none',
                        edgecolors=VERMELHO, linewidths=1.1, zorder=6, label='Fora de controle nesta iteração')
        for valor, estilo in ((lim['LSC X'], '--'), (lim['μ0'], '-'), (lim['LIC X'], '--')):
            ax1.axhline(valor, color=VERMELHO if estilo == '--' else CINZA_ESCURO, ls=estilo, lw=.8)
        ax1.set_title(f"(a) X · LIC = {fmt(lim['LIC X'], 3)}; LM = {fmt(lim['μ0'], 3)}; LSC = {fmt(lim['LSC X'], 3)}",
                      fontsize=7)
        ax1.set_ylabel('Taxa mensal')
        ax2.plot(cons['Período'], cons['AM'], 'o-', color=CINZA_ESCURO, ms=2.2, lw=.7)
        if cons['Sinal AM'].any():
            ax2.scatter(cons.loc[cons['Sinal AM'], 'Período'], cons.loc[cons['Sinal AM'], 'AM'], s=34,
                        facecolors='none', edgecolors=VERMELHO, linewidths=1.1, zorder=6)
        ax2.axhline(lim['LSC AM'], color=VERMELHO, ls='--', lw=.8)
        ax2.axhline(lim['AM média'], color=CINZA_ESCURO, lw=.8)
        ax2.set_title(f"(b) AM · LM = {fmt(lim['AM média'], 3)}; LSC = {fmt(lim['LSC AM'], 3)}", fontsize=7)
        ax2.set_ylabel('Amplitude móvel')
        casas = _casas(r.referencia[TAXA])
        for ax in (ax1, ax2):
            ax.yaxis.set_major_formatter(_virgula(casas))
            _meses(ax, 6 if len(r.referencia) > 30 else 3)
        ax1.set_xlim(ax2.get_xlim())
        _legenda(fig, [ax1], rect)
    return desenhar


def desenho_ewma_fase1(r: mon.Resultado):
    def desenhar(fig, rect):
        ax, = _eixos(fig, [rect[0], rect[1] + .02, rect[2], rect[3] - .02], [1])
        e1 = r.ewma_fase_i
        ax.plot(e1['Período'], e1['EWMA'], 'o-', color=CINZA_ESCURO, ms=2.2, lw=.8, label='EWMA na fase I')
        ax.plot(e1['Período'], e1['LSC EWMA'], '--', color=VERMELHO, lw=.8, label='LSC / LIC')
        ax.plot(e1['Período'], e1['LIC EWMA'], '--', color=VERMELHO, lw=.8)
        ax.axhline(r.params.mu0, color=CINZA_ESCURO, lw=.8)
        _sinais(ax, e1['Período'], e1['EWMA'], e1['Sinal EWMA'])
        ax.yaxis.set_major_formatter(_virgula(_casas(e1['EWMA'])))
        ax.set_ylabel('EWMA')
        _meses(ax, 6 if len(e1) > 30 else 3)
        _legenda(fig, [ax], rect)
    return desenhar


def desenho_pressupostos(r: mon.Resultado):
    def desenhar(fig, rect):
        x = r.referencia[TAXA].to_numpy(dtype=float)
        n = len(x)
        k = min(24, n // 2)
        X, Y, W, H = rect
        larg = (W - .06) / 3
        eixos = [fig.add_axes([X + .03 + i * (larg + .015), Y + .03, larg - .03, H - .045]) for i in range(3)]
        z = np.sort((x - x.mean()) / x.std(ddof=1))
        teoricos = np.array([mon.normal_ppf((i - .375) / (n + .25)) for i in range(1, n + 1)])
        eixos[0].scatter(teoricos, z, s=9, color=AZUL)
        lim = [min(teoricos.min(), z.min()) - .2, max(teoricos.max(), z.max()) + .2]
        eixos[0].plot(lim, lim, color=VERMELHO, lw=.8)
        eixos[0].set_title('Q-Q normal', fontsize=7)
        eixos[0].set_xlabel('Quantis teóricos')
        limite = 1.96 / np.sqrt(n)
        for ax, valores, nome in ((eixos[1], mon.fac(x, k), 'FAC'), (eixos[2], mon.facp(x, k), 'FACP')):
            ax.bar(np.arange(1, len(valores)), valores[1:], color=AZUL, width=.6)
            ax.axhline(limite, color=VERMELHO, ls='--', lw=.7)
            ax.axhline(-limite, color=VERMELHO, ls='--', lw=.7)
            ax.set_ylim(-.7, .7)
            ax.xaxis.set_major_locator(MaxNLocator(integer=True))
            ax.set_title(nome, fontsize=7)
            ax.set_xlabel('Defasagem (meses)')
            ax.yaxis.set_major_formatter(_virgula(1))
    return desenhar


def desenho_fase2(r: mon.Resultado, lam: float, largura_ewma: float):
    def desenhar(fig, rect):
        p, f1, f2, e1 = r.params, r.fase_i, r.fase_ii, r.ewma_fase_i
        ax1, ax2, ax3 = _eixos(fig, [rect[0], rect[1] + .025, rect[2], rect[3] - .025], [1.2, .8, 1.05], folga=.042,
                               topo_livre=.016)
        controle = f1['Situação fase I'].str.startswith(('Em controle', 'Mantido'))
        inicio = f1['Período'].min() - pd.Timedelta(days=20)
        fim = (f2['Período'].max() if not f2.empty else f1['Período'].max()) + pd.Timedelta(days=20)
        fronteira = f1['Período'].max() + pd.Timedelta(days=15)
        for ax in (ax1, ax2, ax3):
            ax.axvspan(inicio, fronteira, color=FUNDO, lw=0)
            ax.axvline(fronteira, color=CINZA_ESCURO, ls=':', lw=.8)
        ax1.plot(f1['Período'][controle], f1[TAXA][controle], 'o-', color=CINZA, ms=2.2, lw=.7, label='Fase I')
        if (~controle).any():
            ax1.scatter(f1['Período'][~controle], f1[TAXA][~controle], marker='x', s=24, color=LARANJA, zorder=5,
                        label='Excluído na fase I')
        if not f2.empty:
            ax1.plot(f2['Período'], f2[TAXA], 'o-', color=AZUL, ms=2.6, lw=1, label='Fase II')
            _sinais(ax1, f2['Período'], f2[TAXA], f2['Sinal X'])
            _consolidacao(ax1, f2, TAXA)
        for valor, estilo in ((p.lsc_x, '--'), (p.mu0, '-'), (p.lic_x, '--')):
            ax1.axhline(valor, color=VERMELHO if estilo == '--' else CINZA_ESCURO, ls=estilo, lw=.8)
        ax1.set_title(f'(a) Medidas individuais (X) · LIC = {fmt(p.lic_x, 3)}; LM = {fmt(p.mu0, 3)}; '
                      f'LSC = {fmt(p.lsc_x, 3)}', fontsize=7)
        ax1.set_ylabel('Taxa mensal')
        ax2.plot(f1['Período'][controle], f1['AM'][controle], 'o-', color=CINZA, ms=2, lw=.6)
        if not f2.empty:
            ax2.plot(f2['Período'], f2['AM'], 'o-', color=AZUL, ms=2.4, lw=.9)
            _sinais(ax2, f2['Período'], f2['AM'], f2['Sinal AM'])
        ax2.axhline(p.lsc_am, color=VERMELHO, ls='--', lw=.8)
        ax2.axhline(p.am_media, color=CINZA_ESCURO, lw=.8)
        ax2.set_title(f'(b) Amplitude móvel (AM) · LM = {fmt(p.am_media, 3)}; LSC = {fmt(p.lsc_am, 3)}', fontsize=7)
        ax2.set_ylabel('AM')
        ax3.plot(e1['Período'], e1['EWMA'], '-', color=CINZA, lw=.9)
        if not f2.empty:
            ax3.plot(f2['Período'], f2['EWMA'], 'o-', color=AZUL, ms=2.6, lw=1)
            ax3.plot(f2['Período'], f2['LSC EWMA'], '--', color=VERMELHO, lw=.8)
            ax3.plot(f2['Período'], f2['LIC EWMA'], '--', color=VERMELHO, lw=.8)
            _sinais(ax3, f2['Período'], f2['EWMA'], f2['Sinal EWMA'])
            _consolidacao(ax3, f2, 'EWMA')
        ax3.axhline(p.mu0, color=CINZA_ESCURO, lw=.8)
        ax3.set_title(f'(c) EWMA (λ = {fmt(lam, 2)}; L = {fmt(largura_ewma, 3)})', fontsize=7)
        ax3.set_ylabel('EWMA')
        casas = _casas(r.serie[TAXA])
        for ax in (ax1, ax2, ax3):
            ax.yaxis.set_major_formatter(_virgula(casas))
            ax.set_xlim(inicio, fim)
            _meses(ax, 6 if (fim - inicio).days > 900 else 3)
        _legenda(fig, [ax1, ax3], rect)
    return desenhar


def desenho_quadrimestral(q: pd.DataFrame):
    def desenhar(fig, rect):
        ax, = _eixos(fig, [rect[0], rect[1] + .02, rect[2], rect[3] - .02], [1])
        d = q[q['Leitura'] == 'Quadrimestre isolado'].reset_index(drop=True)
        x = np.arange(len(d))
        cores = ['#cbd5e1' if not c else (AZUL_SINAL if s == 'Redução' else VERMELHO if s == 'Aumento' else AZUL)
                 for c, s in zip(d['Completo'], d['Sinal'].fillna(''))]
        ax.bar(x, d[TAXA], color=cores, width=.55, label='Taxa observada')
        ax.errorbar(x, d['Esperado (m·μ0)'], yerr=[d['Esperado (m·μ0)'] - d['LIC'], d['LSC'] - d['Esperado (m·μ0)']],
                    fmt='_', color=CINZA_ESCURO, ecolor=VERMELHO, elinewidth=1.2, capsize=4, ms=14,
                    label='Esperado e limites')
        ax.set_xticks(x, [f'{a}/{b}' + ('' if c else '\n(parcial)') for a, b, c in
                          zip(d['Quadrimestre'], d['Ano'], d['Completo'])])
        ax.yaxis.set_major_formatter(_virgula(_casas(d[TAXA])))
        ax.set_ylabel('Taxa do quadrimestre por 100 mil')
        _legenda(fig, [ax], rect)
    return desenhar


def desenho_linha(df: pd.DataFrame, x: str, y: str, rotulo_y: str, rotulos: bool = True):
    def desenhar(fig, rect):
        ax, = _eixos(fig, rect, [1])
        ax.plot(df[x], df[y], 'o-', color=AZUL, ms=3.5, lw=1.2)
        casas = 2 if 'Taxa' in y else 0
        if rotulos:
            for xi, yi in zip(df[x], df[y]):
                if pd.notna(yi):
                    ax.annotate(fmt(yi, casas), (xi, yi), textcoords='offset points', xytext=(0, 4), ha='center',
                                fontsize=6)
        ax.set_ylabel(rotulo_y)
        ax.xaxis.set_major_locator(MaxNLocator(integer=True))
        ax.yaxis.set_major_formatter(_virgula(casas))
    return desenhar


def desenho_barras_comparadas(categorias, series: dict, rotulo_y: str):
    def desenhar(fig, rect):
        ax, = _eixos(fig, [rect[0], rect[1] + .02, rect[2], rect[3] - .02], [1])
        n = len(series)
        largura = .8 / max(n, 1)
        cores = ['#9db7c4', AZUL, '#E69F00', '#9B65AC']
        x = np.arange(len(categorias))
        for i, (nome, valores) in enumerate(series.items()):
            ax.bar(x + (i - (n - 1) / 2) * largura, np.asarray(valores, dtype=float), width=largura,
                   color=cores[i % 4], label=nome)
        ax.set_xticks(x, categorias)
        ax.set_ylabel(rotulo_y)
        ax.yaxis.set_major_formatter(_virgula(2 if 'Taxa' in rotulo_y else 0))
        _legenda(fig, [ax], rect)
    return desenhar


def desenho_barras_h(nomes, valores, rotulo_x: str, casas: int = 0):
    def desenhar(fig, rect):
        ax, = _eixos(fig, rect, [1], esquerda=.2)
        y = np.arange(len(nomes))
        valores_ = np.asarray(valores, dtype=float)
        ax.barh(y, valores_, color=AZUL, height=.6)
        ax.set_yticks(y, list(nomes))
        for yi, v in zip(y, valores_):
            if np.isfinite(v):
                ax.text(v, yi, ' ' + fmt(v, casas), va='center', fontsize=6)
        ax.set_xlabel(rotulo_x)
        ax.grid(axis='y', visible=False)
        maximo = np.nanmax(valores_) if len(valores_) else 0
        ax.set_xlim(0, maximo * 1.15 if maximo > 0 else 1)
    return desenhar


# -----------------------------------------------------------------------------
# Relatórios
# -----------------------------------------------------------------------------
def _rodape(base) -> str:
    gerado = datetime.now().strftime('%d/%m/%Y %H:%M')
    return f'Observatório de mortalidade · ES · fonte: SIM/SESA-ES · base até {base or "—"} · gerado em {gerado}'


def tabela_sinais(f2: pd.DataFrame) -> pd.DataFrame:
    return pd.DataFrame({
        'Mês': [mon.rotulo_mes(v) for v in f2['Período']], 'Óbitos': [fmt(v, 0) for v in f2['Óbitos']],
        'Taxa': [fmt(v, 3) for v in f2[TAXA]], 'AM': [fmt(v, 3) for v in f2['AM']],
        'EWMA': [fmt(v, 3) for v in f2['EWMA']],
        'Limites EWMA': [f'{fmt(a, 3)} – {fmt(b, 3)}' for a, b in zip(f2['LIC EWMA'], f2['LSC EWMA'])],
        'Sinal X': f2['Sinal X'].replace('', '—').to_numpy(), 'Sinal AM': f2['Sinal AM'].replace('', '—').to_numpy(),
        'Sinal EWMA': f2['Sinal EWMA'].replace('', '—').to_numpy(),
        'Situação': np.where(f2['Em consolidação'], 'Em consolidação', 'Consolidado')})


def tabela_quadrimestral(q: pd.DataFrame) -> pd.DataFrame:
    return pd.DataFrame({
        'Ano': q['Ano'].astype(int).astype(str).to_numpy(), 'Quadrimestre': q['Quadrimestre'].to_numpy(),
        'Leitura': q['Leitura'].to_numpy(), 'Meses': q['Meses'].to_numpy(),
        'Taxa': [fmt(v, 2) for v in q[TAXA]], 'Esperado': [fmt(v, 2) for v in q['Esperado (m·μ0)']],
        'Limites': [f'{fmt(a, 2)} – {fmt(b, 2)}' for a, b in zip(q['LIC'], q['LSC'])],
        'Obs./esp.': [fmt(v, 2) for v in q['Razão observado/esperado']],
        'Sinal': q['Sinal'].fillna('').replace('', '—').to_numpy(),
        'Situação': [('Completo' if c else 'Parcial') + (f'; {m} mês(es) em consolidação' if m else '')
                     for c, m in zip(q['Completo'], q['Meses em consolidação'])]})


def relatorio_monitoramento(r: mon.Resultado, contexto: dict, proto: dict, arl: pd.DataFrame,
                            situacao: tuple[str, str], guardar_paginas: bool = False):
    """PDF do monitoramento estatístico do recorte e do protocolo em uso.

    `contexto`: indicador, territorio, granularidade, sexo, base e consolidacao (textos).
    `proto`: modo, lam, le, lx, dias, automatico e justificativa.
    Retorna os bytes do PDF ou, com `guardar_paginas`, (bytes, figuras das páginas).
    """
    doc = Documento('Relatório do monitoramento estatístico mensal',
                    f"{contexto['indicador']} · {contexto['territorio']}", _rodape(contexto.get('base')),
                    guardar_paginas)
    p, f2 = r.params, r.fase_ii
    consolidados = f2[~f2['Em consolidação']] if not f2.empty else f2
    inicio_f2 = mon.rotulo_mes(f2['Período'].min()) if not f2.empty else '—'
    fim_f2 = mon.rotulo_mes(f2['Período'].max()) if not f2.empty else '—'
    destaques = []
    if not consolidados.empty:
        u = consolidados.iloc[-1]
        destaques = [('Último mês consolidado', mon.rotulo_mes(u['Período']), f"{fmt(u['Óbitos'], 0)} óbitos"),
                     ('Taxa no mês (por 100 mil)', fmt(u[TAXA], 3),
                      f"{fmt((u[TAXA] / p.mu0 - 1) * 100, 1)}% em relação a μ0"),
                     ('Gráfico X no mês', u['Sinal X'] or 'Sem sinal', f'limites {fmt(p.lic_x, 3)} – {fmt(p.lsc_x, 3)}'),
                     ('EWMA no mês', u['Sinal EWMA'] or 'Sem sinal',
                      f"limites {fmt(u['LIC EWMA'], 3)} – {fmt(u['LSC EWMA'], 3)}")]
    doc.capa(contexto['indicador'], [
        f"Território: {contexto['territorio']} ({contexto['granularidade'].lower()}) · sexo: {contexto['sexo']}.",
        f"Base atualizada até {contexto.get('base') or '—'} · meses em consolidação: "
        f"{contexto.get('consolidacao') or 'nenhum'}.",
        f'Fase I (referência): {p.inicio} a {p.fim}, {p.n_controle} de {p.n_inicial} meses mantidos na referência · '
        f'fase II: {inicio_f2} a {fim_f2}.',
        f"Configuração: {proto['modo']} · λ = {fmt(proto['lam'], 2)}; L do EWMA = {fmt(proto['le'], 3)}; "
        f"L do gráfico X = {fmt(proto['lx'], 1)}; consolidação = {proto['dias']} dias; exclusão automática: "
        f"{'sim' if proto['automatico'] else 'não'}.",
    ], destaques)
    doc.paragrafo(f'Aplicabilidade ao recorte: {situacao[0]}. {situacao[1]}')
    if not p.estavel:
        doc.paragrafo('Há sinais X/AM na fase I. Os limites são exploratórios e exigem investigação da estabilidade da referência.')
    doc.grafico(desenho_fase2(r, proto['lam'], proto['le']), .4,
                'Resumo · gráficos X, AM e EWMA (fase I sombreada)')
    doc.quebra()
    doc.grafico(desenho_serie(r), .17, 'Série mensal da taxa por 100 mil (sem anualização)')
    if not f2.empty:
        doc.tabela(tabela_sinais(f2.tail(8))[['Mês', 'Óbitos', 'Taxa', 'EWMA', 'Sinal X', 'Sinal AM', 'Sinal EWMA',
                                              'Situação']], 'Últimos meses da fase II')
    q = r.quadrimestral
    if not q.empty:
        doc.tabela(tabela_quadrimestral(q[q['Ano'] == q['Ano'].max()]), 'Leitura quadrimestral do ano monitorado',
                   larguras=[.05, .12, .14, .08, .07, .08, .12, .08, .08, .18],
                   nota='A taxa do quadrimestre é a soma das taxas mensais; limites m·μ0 ± L·√m·σ0. '
                        'Quadrimestres com meses em consolidação são provisórios.')
    doc.paragrafo('Sinais estatísticos indicam afastamento do comportamento esperado e orientam a investigação '
                  '(qualidade do registro, revisões da base e contexto territorial); não estabelecem causas. '
                  'Meses no prazo de cautela são provisórios. Ultrapassar o prazo não comprova completude; registros antigos também podem ser revistos.',
                  tamanho=7, cor=CINZA_ESCURO, italico=True)

    doc.quebra()
    doc.secao('Fase I · referência')
    exclusoes = ', '.join(p.excluidos + p.manuais) or 'nenhuma'
    doc.paragrafo(f'Período de referência: {p.inicio} a {p.fim} ({p.n_inicial} meses). Exclusões: {exclusoes}. '
                  f'Parâmetros estimados na referência: μ0 = {fmt(p.mu0, 4)} e σ0 = AM̄/1,128 = {fmt(p.sigma0, 4)} '
                  'por 100 mil por mês.' + (f" Justificativa registrada: {proto['justificativa']}."
                                            if proto.get('justificativa') else ''))
    itens = [(k, str(v) if k == 'n' else fmt(v, 4)) for k, v in r.descritivas.items()]
    metade = (len(itens) + 1) // 2
    esquerda, direita = itens[:metade], itens[metade:] + [('', '')] * (2 * metade - len(itens))
    descritivas = pd.DataFrame({'Medida': [a for a, _ in esquerda], 'Valor': [b for _, b in esquerda],
                                'Medida ': [a for a, _ in direita], 'Valor ': [b for _, b in direita]})
    doc.tabela(descritivas, 'Estatísticas descritivas da fase I', larguras=[.32, .18, .32, .18])
    press = r.pressupostos
    doc.tabela(pd.DataFrame({'Teste': press['Teste'].to_numpy(),
                             'Estatística': [fmt(v, 4) for v in press['Estatística']],
                             'Valor-p': [fmt(v, 4) for v in press['Valor-p']], 'Decisão': press['Decisão'].to_numpy()}),
               f'Verificação dos pressupostos (α = {fmt(r.configuracao["alfa"], 2)})', larguras=[.42, .18, .16, .24])
    doc.grafico(desenho_pressupostos(r), .16, 'Gráfico Q-Q normal, FAC e FACP')
    it = r.iteracoes
    doc.tabela(pd.DataFrame({'Iteração': it['Iteração'].astype(int).to_numpy(),
                             'Meses': it['Meses considerados'].astype(int).to_numpy(),
                             'μ0': [fmt(v, 4) for v in it['μ0']], 'σ0': [fmt(v, 4) for v in it['σ0']],
                             'LIC X': [fmt(v, 4) for v in it['LIC X']], 'LSC X': [fmt(v, 4) for v in it['LSC X']],
                             'LSC AM': [fmt(v, 4) for v in it['LSC AM']], 'Fora de controle': it['Sinais'].to_numpy(),
                             'Critério': it['Critério'].to_numpy()}),
               'Iterações da fase I (exclusão de pontos fora de controle)')
    ultima = int(it['Iteração'].max())
    for k in it['Iteração'].astype(int):
        rotulo = f'Gráficos X e AM da fase I · {k}ª iteração' + (' (final)' if k == ultima else '')
        doc.grafico(desenho_fase1_iteracao(r, k), .25, rotulo)
    doc.grafico(desenho_ewma_fase1(r), .14, 'EWMA calculado na fase I',
                nota='Sinais do EWMA na fase I não levam à exclusão de meses: esse gráfico não é usado para estimar '
                     'os parâmetros do processo.')

    doc.secao('Fase II · monitoramento mensal', minimo=.62)
    doc.grafico(desenho_fase2(r, proto['lam'], proto['le']), .5, 'Gráficos X, AM e EWMA (fase I sombreada)',
                nota='Triângulos: sinais de aumento (vermelho) ou de redução (azul); círculos roxos: meses em '
                     'consolidação; X laranja: meses excluídos na fase I.')
    if not f2.empty:
        doc.tabela(tabela_sinais(f2), 'Sinais e limites por mês',
                   larguras=[.08, .06, .07, .07, .07, .13, .1, .1, .1, .13])
    if not q.empty:
        doc.secao('Leitura quadrimestral')
        doc.grafico(desenho_quadrimestral(q), .17, 'Quadrimestres isolados: observado, esperado e limites')
        doc.tabela(tabela_quadrimestral(q), 'Quadrimestres isolados e acumulados no ano',
                   larguras=[.05, .12, .14, .08, .07, .08, .12, .08, .08, .18])
    doc.secao('Parâmetros e reprodução')
    d = p.como_dict()
    parametros = pd.DataFrame([
        ('Fase I', f"{d['inicio']} a {d['fim']} ({d['n_controle']} de {d['n_inicial']} meses mantidos na referência)"),
        ('μ0 e σ0 (taxa mensal por 100 mil)', f"{fmt(d['mu0'], 4)} e {fmt(d['sigma0'], 4)}"),
        ('Gráfico X: LIC – LSC', f"{fmt(d['lic_x'], 4)} – {fmt(d['lsc_x'], 4)}"),
        ('Gráfico AM: LM e LSC', f"{fmt(d['am_media'], 4)} e {fmt(d['lsc_am'], 4)}"),
        ('EWMA', f"λ = {fmt(proto['lam'], 2)}; L = {fmt(proto['le'], 3)}"),
        ('Meses excluídos', ', '.join(list(d['excluidos']) + list(d['manuais'])) or 'Nenhum'),
        ('Iterações e estabilidade', f"{d['iteracoes']} · {'estável' if d['estavel'] else 'instável'}"),
        ('Configuração', proto['modo'])], columns=['Parâmetro', 'Valor'])
    doc.tabela(parametros, 'Parâmetros estimados na referência', larguras=[.38, .62])
    doc.tabela(pd.DataFrame({'Deslocamento (σ0)': [fmt(v, 1) for v in arl.iloc[:, 0]],
                             'Gráfico X': [fmt(v, 1) for v in arl.iloc[:, 1]],
                             'Leitura quadrimestral': [fmt(v, 1) for v in arl.iloc[:, 2]],
                             'EWMA': [fmt(v, 1) for v in arl.iloc[:, 3]]}),
               'ARL teórico com parâmetros conhecidos e EWMA assintótico (meses)')
    doc.paragrafo('Não rejeitar H₀ não demonstra equivalência ou ausência de alteração. Os testes de pressupostos são exploratórios, sem correção de multiplicidade. O ARL teórico pressupõe normalidade, independência e parâmetros conhecidos; o EWMA aplicado usa limites de partida. A configuração completa está no JSON exportado pelo painel.')
    doc.paragrafo('Para reproduzir este recorte, use o JSON exportado pelo painel: selecione os municípios e o sexo '
                  'registrados e aplique as entradas de cálculo à mesma base identificada por hash. O comando '
                  'python -m experimentos.monitoramento --figuras reproduz a avaliação estadual dos três indicadores '
                  'com todos os sexos elegíveis e os parâmetros do config.toml. A metodologia está descrita no documento '
                  'docs/MONITORAMENTO.md.', tamanho=7.2)
    pdf = doc.finalizar()
    return (pdf, doc.paginas) if guardar_paginas else pdf


def relatorio_aba(aba: str, contexto: dict, blocos: list) -> bytes:
    """PDF de uma aba do painel a partir de blocos simples.

    Blocos: ('secao', texto), ('texto', texto), ('tabela', titulo, df[, nota]) e
    ('grafico', titulo, desenho, altura[, nota]), em que `desenho` vem das funções desenho_*.
    """
    doc = Documento(f'Relatório · {aba}', contexto['indicador'], _rodape(contexto.get('base')))
    doc.capa(contexto['indicador'], contexto.get('linhas', []), contexto.get('destaques', ()))
    for bloco in blocos:
        tipo = bloco[0]
        if tipo == 'secao':
            doc.secao(bloco[1])
        elif tipo == 'texto':
            doc.paragrafo(bloco[1])
        elif tipo == 'tabela':
            doc.tabela(bloco[2], bloco[1], nota=bloco[3] if len(bloco) > 3 else None)
        elif tipo == 'grafico':
            doc.grafico(bloco[2], bloco[3], bloco[1], nota=bloco[4] if len(bloco) > 4 else None)
    return doc.finalizar()


def salvar_paginas(paginas: list, pasta: Path, prefixo: str, dpi: int = 160) -> list[Path]:
    """Grava páginas guardadas de um relatório como PNG (documentação e TCC)."""
    pasta.mkdir(parents=True, exist_ok=True)
    arquivos = []
    for i, fig in enumerate(paginas, start=1):
        destino = pasta / f'{prefixo}_p{i}.png'
        with plt.rc_context({'savefig.bbox': 'standard'}):
            fig.savefig(destino, dpi=dpi)
        plt.close(fig)
        arquivos.append(destino)
    return arquivos
