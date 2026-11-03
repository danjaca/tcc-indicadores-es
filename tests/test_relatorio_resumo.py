"""O resumo do PDF reúne os três gráficos e preserva a série histórica."""
import matplotlib.pyplot as plt
import pandas as pd
import pytest

from dominio import monitoramento as mon
from dominio.dados import carregar, recortar
from painel.relatorio import relatorio_monitoramento


@pytest.mark.parametrize('com_fase_ii', [True, False], ids=['estadual_jovens', 'sem_fase_ii'])
def test_resumo_pdf_tem_tres_graficos_na_primeira_pagina(com_fase_ii):
    indicador = 'Homicídios — jovens de 15 a 29 anos'
    f, p, g, _ = carregar()
    nf, npop = recortar(f, p, indicador, g.cod_mun_res)
    serie = mon.serie_mensal(nf, npop)
    if not com_fase_ii:
        serie = serie[serie['Período'].lt('2026-01-01')]
    r = mon.analisar(serie, '2022-01', '2025-12', '2026-12', data_base='2026-10-09')
    contexto = dict(indicador=indicador, territorio='Espírito Santo', granularidade='Estadual',
                    sexo='Todos', base='09/10/2026', consolidacao='Ago/2026, Set/2026' if com_fase_ii else '')
    proto = dict(modo='Protocolo do TCC (config.toml)', lam=.1, le=2.701, lx=3.0, dias=60,
                 automatico=False, justificativa='')
    arl = pd.DataFrame({'Deslocamento': [0], 'X': [370.4], 'Quadrimestral': [1481.6], 'EWMA': [369.8]})
    pdf, paginas = relatorio_monitoramento(r, contexto, proto, arl,
                                         ('Nível estadual', 'Média de 42,9 óbitos por mês na fase I.'),
                                         guardar_paginas=True)
    try:
        assert pdf.startswith(b'%PDF')
        capa = paginas[0]
        graficos = [ax for ax in capa.axes if ax.get_title(loc='left')]
        assert [ax.get_title(loc='left') for ax in graficos] == [
            '(a) Medidas individuais (X) · LIC = 1,370; LM = 4,872; LSC = 8,374',
            '(b) Amplitude móvel (AM) · LM = 1,317; LSC = 4,302',
            '(c) EWMA (λ = 0,10; L = 2,701)',
        ]
        capa.canvas.draw()
        renderer = capa.canvas.get_renderer()
        limites = [ax.get_tightbbox(renderer) for ax in graficos]
        assert all(capa.bbox.contains(b.x0, b.y0) and capa.bbox.contains(b.x1, b.y1) for b in limites)
        assert all(acima.y0 > abaixo.y1 for acima, abaixo in zip(limites, limites[1:]))
        historico = [ax for pagina in paginas[1:] for ax in pagina.axes
                     if ax.get_ylabel() == 'Taxa mensal por 100 mil']
        assert len(historico) == 1
        datas = pd.to_datetime(historico[0].lines[0].get_xdata())
        assert len(datas) == len(serie)
        assert datas.min() == serie['Período'].min() == pd.Timestamp('2016-01-01')
        assert datas.max() == serie['Período'].max()
        assert any(t.get_text() == 'Fase I · referência' for pagina in paginas for t in pagina.texts)
        assert any(t.get_text() == 'Fase II · monitoramento mensal' for pagina in paginas for t in pagina.texts)
    finally:
        for pagina in paginas:
            plt.close(pagina)


def test_cabecalhos_pdf_mulheres_cabem_nas_celulas():
    indicador = 'Homicídios — mulheres de 10 a 59 anos'
    f, p, g, _ = carregar()
    nf, npop = recortar(f, p, indicador, g.cod_mun_res)
    r = mon.analisar(mon.serie_mensal(nf, npop), '2022-01', '2025-12', '2026-12',
                     data_base='2026-10-09')
    contexto = dict(indicador=indicador, territorio='Espírito Santo', granularidade='Estadual',
                    sexo='Todos', base='09/10/2026', consolidacao='Ago/2026, Set/2026')
    proto = dict(modo='Protocolo do TCC (config.toml)', lam=.1, le=2.701, lx=3.0, dias=60,
                 automatico=False, justificativa='')
    arl = pd.DataFrame({'Deslocamento': [0], 'X': [370.4], 'Quadrimestral': [1481.6], 'EWMA': [369.8]})
    _, paginas = relatorio_monitoramento(r, contexto, proto, arl, ('Nível estadual', ''),
                                       guardar_paginas=True)
    esperados = {'Sinal EWMA', 'Fora de controle', 'Quadrimestre'}
    encontrados = set()
    try:
        for pagina in paginas:
            pagina.canvas.draw()
            renderer = pagina.canvas.get_renderer()
            for ax in pagina.axes:
                for tabela in ax.tables:
                    for (linha, _), celula in tabela.get_celld().items():
                        texto = celula.get_text()
                        rotulo = ' '.join(texto.get_text().split())
                        if linha != 0 or rotulo not in esperados:
                            continue
                        encontrados.add(rotulo)
                        t = texto.get_window_extent(renderer)
                        c = celula.get_window_extent(renderer)
                        assert t.x0 >= c.x0 - .5 and t.x1 <= c.x1 + .5, rotulo
                        assert t.y0 >= c.y0 - .5 and t.y1 <= c.y1 + .5, rotulo
        assert encontrados == esperados
    finally:
        for pagina in paginas:
            plt.close(pagina)
