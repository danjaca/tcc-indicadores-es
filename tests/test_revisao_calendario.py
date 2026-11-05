"""O ajuste ativo muda os gráficos mensais, preservando a apuração oficial."""
import json

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import pytest
import streamlit as st
from streamlit.testing.v1 import AppTest

from configuracao import RAIZ
from dominio import monitoramento as mon
from painel.vistas import monitoramento as vista


def test_ajuste_calendario_idempotente_preserva_taxa_oficial_e_ano_bissexto():
    serie = pd.DataFrame({'Período': pd.to_datetime(['2023-02-01', '2024-02-01', '2024-03-01']),
                          mon.TAXA: [2., 2., 2.], 'Óbitos': [2, 2, 2], 'População': [100000] * 3})
    antes = serie.copy(deep=True)
    ajustada = mon.ajustar_calendario(serie)
    np.testing.assert_allclose(ajustada[mon.TAXA], 2 * 30.4375 / np.array([28, 29, 31]))
    pd.testing.assert_frame_equal(mon.ajustar_calendario(ajustada), ajustada)
    pd.testing.assert_frame_equal(serie, antes)
    pd.testing.assert_series_equal(ajustada[mon.TAXA_OFICIAL], serie[mon.TAXA], check_names=False)
    for coluna in ('Óbitos', 'População'):
        pd.testing.assert_series_equal(ajustada[coluna], serie[coluna])


@pytest.fixture
def ajuste_ativo(monkeypatch):
    capturados = {}
    original = st.download_button

    def capturar(label, data, *args, **kwargs):
        if label == 'Baixar relatório do monitoramento (PDF)':
            capturados['pdf'] = data
        if label == 'Baixar parâmetros (JSON)':
            capturados['manifesto'] = json.loads(data)
        return original(label, data, *args, **kwargs)

    monkeypatch.setattr(st, 'download_button', capturar)
    at = AppTest.from_file(str(RAIZ / 'app.py'), default_timeout=80).run()
    assert not at.exception
    oficial = capturados['pdf'].args[0]
    at.toggle(key='mon_calendario').set_value(True).run()
    at.radio(key='mon_secao').set_value('Parâmetros e reprodução').run()
    assert not at.exception
    return at, oficial, capturados


def test_toggle_recalcula_mensal_preserva_quadrimestre_e_json_reproduz(ajuste_ativo):
    at, oficial, capturados = ajuste_ativo
    ajustada = capturados['pdf'].args[0]
    manifesto = capturados['manifesto']
    assert manifesto['transformacao_de_entrada']['ajuste_calendario'] is True
    assert manifesto['parametros']['escala_taxa'] == 'ajustada_30_4375'
    assert manifesto['parametros']['parametros_quadrimestrais_oficiais'] == json.loads(json.dumps(oficial.params.como_dict()))
    assert ajustada.params.mu0 != oficial.params.mu0
    pd.testing.assert_frame_equal(ajustada.quadrimestral, oficial.quadrimestral)
    np.testing.assert_allclose(ajustada.serie[mon.TAXA],
                               oficial.serie[mon.TAXA] * 30.4375 / oficial.serie['Período'].dt.days_in_month)
    pd.testing.assert_frame_equal(ajustada.serie[['Óbitos', 'População']], oficial.serie[['Óbitos', 'População']])
    reproduzido = mon.analisar(mon.ajustar_calendario(oficial.serie), **manifesto['entrada'])
    assert json.loads(json.dumps(reproduzido.params.como_dict())) == manifesto['processo']
    pd.testing.assert_frame_equal(reproduzido.fase_ii, ajustada.fase_ii)
    quad_oficial = mon.analisar(oficial.serie, **manifesto['entrada'])
    pd.testing.assert_frame_equal(quad_oficial.quadrimestral, ajustada.quadrimestral)
    assert any('próprios parâmetros' in item.value for item in at.info)
    for fig in (vista.figura_x(ajustada), vista.figura_am(ajustada), vista.figura_ewma(ajustada, .1, 2.701)):
        rotulos = f'{fig.layout.title.text} {fig.layout.yaxis.title.text}'.lower()
        assert 'ajustada' in rotulos


def test_pdf_ajustado_identifica_escala_e_mantem_tres_graficos_na_capa(ajuste_ativo):
    _, _, capturados = ajuste_ativo
    chamada = capturados['pdf']
    chamada.args[1]['diagnostico_causas'] = [{'Ano': 2026, 'Mês': 1, 'Y10–Y34': 2026,
                                            'Y22–Y24 (subconjunto)': 2, 'R99': 3}]
    pdf, paginas = chamada.func(*chamada.args, **chamada.keywords, guardar_paginas=True)
    try:
        assert pdf.startswith(b'%PDF')
        textos = [t.get_text() for p in paginas for t in p.texts]
        assert any('taxa oficial × 30,4375/dias' in t for t in textos)
        assert any('Escala oficial, com parâmetros próprios' in t for t in textos)
        graficos = [ax for ax in paginas[0].axes if ax.get_title(loc='left')]
        assert len(graficos) == 3
        assert all(nome in ax.get_title(loc='left') for nome, ax in zip(('(a)', '(b)', '(c)'), graficos))
        auxiliares = [t for p in paginas for ax in p.axes for t in ax.tables
                      if t.get_celld().get((0, 2)) is not None and 'Y10' in t[0, 2].get_text().get_text()]
        assert len(auxiliares) == 1
        assert auxiliares[0][1, 0].get_text().get_text() == '2026'
        assert auxiliares[0][1, 2].get_text().get_text() == '2.026'
        r = chamada.args[0]
        comparacao = mon.sensibilidade_calendario(r.serie, '2022-01', '2025-12', '2026-12')
        assert comparacao.iloc[1]['μ0'] == pytest.approx(r.params.mu0)
    finally:
        for pagina in paginas:
            plt.close(pagina)
