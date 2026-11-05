"""Testes do monitoramento estatístico mensal por gráficos de controle (X–AM e EWMA)."""
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from configuracao import RAIZ
from dominio import monitoramento as mon
from dominio.monitoramento import TAXA

BARROS = Path(__file__).resolve().parents[1] / 'experimentos' / 'dados_barros2021.csv'


def serie_barros():
    b = pd.read_csv(BARROS)
    s = pd.DataFrame({'Período': pd.to_datetime(b['periodo'] + '-01'), TAXA: b['taxa'].astype(float)})
    s['Ano'], s['Mês'], s['Óbitos'], s['População'] = s['Período'].dt.year, s['Período'].dt.month, np.nan, np.nan
    return s


def serie_sintetica(valores, inicio='2020-01-01', populacao=1_000_000):
    periodos = pd.date_range(inicio, periods=len(valores), freq='MS')
    s = pd.DataFrame({'Período': periodos, 'Ano': periodos.year, 'Mês': periodos.month,
                      'Óbitos': np.asarray(valores, dtype=int), 'População': float(populacao)})
    s[TAXA] = s['Óbitos'] / s['População'] * 100000
    return s


def test_testes_reproduzem_valores_publicados_por_barros_2021():
    x = serie_barros()[TAXA].to_numpy()[:48]
    assert mon.lilliefors(x)[1] == pytest.approx(0.07903, abs=1e-5)
    assert mon.ljung_box(x, 1)[2] == pytest.approx(0.857, abs=1e-3)
    assert mon.dickey_fuller_aumentado(x)[2] == pytest.approx(0.04679, abs=1e-5)
    assert mon.cox_stuart(x, metodo='normal')[2] == pytest.approx(0.6171, abs=1e-4)
    assert mon.fisher_sazonalidade(x)[1] == pytest.approx(0.8663829, abs=1e-6)


def test_graficos_reproduzem_barros_2021():
    r = mon.analisar(serie_barros(), '2017-01-01', '2020-12-01', lam=.1, largura_ewma=2.701,
                     defasagens_lb=(1,), automatico=True)
    assert r.params.excluidos == ('Jun/2020', 'Jul/2020')
    assert r.params.mu0 == pytest.approx(42.26, abs=.01)
    assert r.params.sigma0 == pytest.approx(2.49, abs=.01)
    assert r.params.lsc_x == pytest.approx(49.73, abs=.01)
    assert r.params.lsc_am == pytest.approx(9.17, abs=.01)
    assert r.iteracoes.iloc[0]['LSC X'] == pytest.approx(51.19, abs=.01)
    sinais_x = [mon.rotulo_mes(p) for p, s in zip(r.fase_ii['Período'], r.fase_ii['Sinal X']) if s]
    sinais_am = [mon.rotulo_mes(p) for p, s in zip(r.fase_ii['Período'], r.fase_ii['Sinal AM']) if s]
    assert sinais_x == ['Mar/2021'] and sinais_am == ['Abr/2021']
    assert (r.fase_ii['Sinal EWMA'] == '').all()
    assert list(r.ewma_fase_i.loc[r.ewma_fase_i['Sinal EWMA'] != '', 'Período'].dt.strftime('%Y-%m')) == ['2017-01']


def test_arl_e_calibracao():
    assert mon.arl_shewhart(0, 3) == pytest.approx(370.4, abs=.1)
    assert mon.arl_ewma(.1, 2.701) == pytest.approx(370, abs=3)
    assert mon.arl_ewma(.1, 2.814) == pytest.approx(500, abs=3)
    assert mon.arl_ewma(.1, 2.701, 1) < mon.arl_shewhart(1, 3)
    assert mon.calibrar_largura_ewma(.2) == pytest.approx(2.86, abs=.01)


def test_quadrimestre_usa_soma_das_taxas_e_limites_de_subgrupo():
    rng = np.random.default_rng(1)
    s = serie_sintetica(rng.poisson(100, 60))
    r = mon.analisar(s, '2020-01-01', '2023-12-01')
    q = r.quadrimestral
    linha = q[(q['Ano'] == 2024) & (q['Quadrimestre'] == '1º') & (q['Leitura'] == 'Quadrimestre isolado')].iloc[0]
    meses = s[(s['Ano'] == 2024) & s['Mês'].between(1, 4)]
    assert linha[TAXA] == pytest.approx(meses[TAXA].sum())
    assert linha['LSC'] == pytest.approx(4 * r.params.mu0 + 3 * 2 * r.params.sigma0)
    acumulado = q[(q['Ano'] == 2024) & (q['Quadrimestre'] == '3º') & (q['Leitura'] == 'Acumulado no ano')].iloc[0]
    assert acumulado['Meses disponíveis'] == 12
    assert acumulado['LSC'] == pytest.approx(12 * r.params.mu0 + 3 * np.sqrt(12) * r.params.sigma0)


def test_quadrimestre_parcial_ou_em_consolidacao_nao_emite_sinal():
    s = serie_sintetica(np.r_[np.random.default_rng(42).poisson(100, 48), np.full(4, 1000)])
    recente = mon.analisar(s, '2020-01', '2023-12', data_base='2024-05-01')
    assert (recente.quadrimestral['Meses em consolidação'] > 0).all()
    assert recente.quadrimestral['Sinal'].eq('').all()
    assert recente.quadrimestral['Situação da sinalização'].eq('Suspensa: consolidação').all()
    parcial = mon.analisar(s.iloc[:-1], '2020-01', '2023-12', data_base='2025-01-01')
    assert not parcial.quadrimestral['Completo'].any()
    assert parcial.quadrimestral['Sinal'].eq('').all()
    assert parcial.quadrimestral['Situação da sinalização'].eq('Suspensa: período parcial').all()
    completo = mon.analisar(s, '2020-01', '2023-12', data_base='2025-01-01')
    assert completo.quadrimestral['Sinal'].eq('Aumento').all()
    assert completo.quadrimestral['Situação da sinalização'].eq('Sinal calculado').all()


def test_lacunas_nao_viram_zero():
    s = serie_sintetica(np.full(48, 100)).drop(index=10)
    with pytest.raises(ValueError, match='sem cobertura'):
        mon.analisar(s, '2020-01-01', '2023-12-01')
    vazia = mon.serie_mensal(pd.DataFrame(columns=['ano', 'mes', 'Obitos']), pd.DataFrame(columns=['ano', 'populacao']))
    assert vazia.empty


def test_meses_em_consolidacao():
    periodos = pd.to_datetime(['2026-06-01', '2026-07-01', '2026-08-01', '2026-09-01'])
    assert mon.em_consolidacao(periodos, '2026-10-09', 60).tolist() == [False, False, True, True]
    assert not mon.em_consolidacao(periodos, None).any()


def test_cox_exato_descarta_empates_e_preserva_replicacao_normal():
    x = np.r_[np.arange(8), np.zeros(8), np.arange(8) + 1]
    assert mon.cox_stuart(x) == (8, 8, pytest.approx(2 / 2**8))
    x[-1] = x[7]
    assert mon.cox_stuart(x) == (7, 7, pytest.approx(2 / 2**7))
    assert mon.cox_stuart(np.ones(24)) == (0, 0, 1)
    with pytest.raises(ValueError, match='método'):
        mon.cox_stuart(x, metodo='desconhecido')


def test_cox_muda_apenas_diagnostico_e_registra_metodo():
    s = serie_barros()
    exato = mon.analisar(s, '2017-01', '2020-12')
    normal = mon.analisar(s, '2017-01', '2020-12', metodo_cox='normal')
    assert exato.params == normal.params
    pd.testing.assert_frame_equal(exato.fase_ii, normal.fase_ii)
    assert exato.configuracao['metodo_cox'] == 'exato'
    assert normal.configuracao['metodo_cox'] == 'normal'
    a, b = (r.pressupostos.set_index('Teste') for r in (exato, normal))
    assert a.loc['Cox–Stuart', 'Valor-p'] != b.loc['Cox–Stuart', 'Valor-p']
    pd.testing.assert_frame_equal(a.drop('Cox–Stuart'), b.drop('Cox–Stuart'))


def test_kpss_constante_contra_calculo_manual_e_fronteiras():
    x = np.array([1, 3, 2, 4, 2, 1, 3, 5, 2, 4, 1, 3.])
    e = x - x.mean()
    esperado = np.cumsum(e) @ np.cumsum(e) / (len(x) * (e @ e))
    estat, lag, p = mon.kpss(x, tendencia=False, defasagens=0)
    assert estat == pytest.approx(esperado)
    assert lag == 0 and p == .1
    for v in (np.ones(24), np.arange(24), np.r_[np.ones(23), np.nan]):
        with pytest.raises(ValueError):
            mon.kpss(v)
    with pytest.raises(ValueError, match='defasagem'):
        mon.kpss(x, defasagens=len(x))


def test_residuos_retiram_tendencia_sem_mudar_os_dados():
    base = np.random.default_rng(42).normal(size=48)
    tendencia = 3 * np.arange(48)
    antes = base.copy()
    a = mon.avaliar_residuos_tendencia(base)
    b = mon.avaliar_residuos_tendencia(base + tendencia)
    np.testing.assert_allclose(a['Valor-p'], b['Valor-p'], atol=1e-10)
    assert b['Inclinação por mês'].iloc[0] - a['Inclinação por mês'].iloc[0] == pytest.approx(3)
    np.testing.assert_array_equal(base, antes)


def test_poisson_respeita_populacoes_diferentes_e_am_nao_e_arl():
    s = serie_sintetica(np.full(24, 10))
    s.loc[12:, 'População'] *= 2
    s[TAXA] = s['Óbitos'] / s['População'] * 100000
    tab = mon.comparar_poisson(s)
    esperado = np.sqrt(s[TAXA].mean() * 100000 * np.mean(1 / s['População']))
    assert tab['DP esperado sob Poisson'] == pytest.approx(esperado)
    assert mon.probabilidade_sinal_am() == pytest.approx(.009165650309243878)
    assert mon.probabilidade_sinal_am() > 1 / mon.arl_shewhart()


def test_calendario_nao_muda_taxas_ou_limites_do_protocolo_principal():
    s = serie_sintetica(np.random.default_rng(42).poisson(40, 60))
    antes = s.copy(deep=True)
    comparacao = mon.sensibilidade_calendario(s, '2020-01', '2023-12', '2024-12', automatico=True)
    pd.testing.assert_frame_equal(s, antes)
    assert comparacao['Exclusão automática'].eq(False).all()
    assert comparacao['Meses fora da cautela'].tolist() == [12, 12]
    original = mon.analisar(s, '2020-01', '2023-12', '2024-12')
    assert comparacao.iloc[0]['μ0'] == pytest.approx(original.params.mu0)
    ajustadas = s[TAXA] * 30.4375 / s['Período'].dt.days_in_month
    assert comparacao.iloc[1]['μ0'] == pytest.approx(ajustadas.iloc[:48].mean())


def test_ajuste_calendario_e_copia_idempotente_com_fevereiro_bissexto():
    s = serie_sintetica([100, 100, 100, 100], inicio='2023-01-01')
    s['Período'] = pd.to_datetime(['2023-01-01', '2023-02-01', '2024-02-01', '2024-04-01'])
    antes = s.copy(deep=True)
    ajustada = mon.ajustar_calendario(s)
    pd.testing.assert_frame_equal(s, antes)
    pd.testing.assert_frame_equal(ajustada, mon.ajustar_calendario(ajustada))
    np.testing.assert_allclose(ajustada['Fator calendário'], 30.4375 / np.array([31, 28, 29, 30]))
    pd.testing.assert_series_equal(ajustada[mon.TAXA_OFICIAL], s[TAXA], check_names=False)
    pd.testing.assert_frame_equal(ajustada[['Óbitos', 'População']], s[['Óbitos', 'População']])
    np.testing.assert_allclose(ajustada[TAXA], s[TAXA] * ajustada['Fator calendário'])


def test_sensibilidade_e_poisson_usam_oficial_quando_entrada_ja_esta_ajustada():
    s = serie_sintetica(np.random.default_rng(42).poisson(40, 60))
    ajustada = mon.ajustar_calendario(s)
    a = mon.sensibilidade_calendario(s, '2020-01', '2023-12', '2024-12')
    b = mon.sensibilidade_calendario(ajustada, '2020-01', '2023-12', '2024-12')
    pd.testing.assert_frame_equal(a, b)
    assert mon.comparar_poisson(s) == mon.comparar_poisson(ajustada)


def test_ajuste_calendario_recusa_data_e_taxa_invalidas():
    s = serie_sintetica([10, 20, 30])
    s.loc[0, 'Período'] = pd.NaT
    with pytest.raises(ValueError, match='meses válidos'):
        mon.ajustar_calendario(s)
    s = serie_sintetica([10, 20, 30])
    s.loc[0, TAXA] = np.inf
    with pytest.raises(ValueError, match='taxas finitas'):
        mon.ajustar_calendario(s)


def test_regra_da_fase1_reduz_janela_com_tendencia():
    rng = np.random.default_rng(7)
    tendencia = np.r_[rng.poisson(60, 24), rng.poisson(100, 24)]
    s = serie_sintetica(tendencia, '2021-01-01')
    regra = mon.sugerir_fase1(s, '2024-12')
    assert regra['meses'] < 48
    assert regra['tentativas'][0]['Aprovada'] is False


def test_protocolo_registrado_no_config():
    cfg = mon.ler_protocolo(RAIZ / 'config.toml')
    assert cfg['lambda_ewma'] == .1 and cfg['largura_ewma'] == 2.701 and cfg['dias_consolidacao'] == 60
    assert cfg['fase1'] == {} and cfg['exclusao_automatica'] is False
    assert cfg['meses_padrao_fase1'] == 48
    assert cfg['meses_fase2'] == 12 and cfg['protocolo'] == mon.PROTOCOLO
    assert all(fim.endswith('-12') for _, fim in cfg['fase1'].values())


def test_interface_monitoramento():
    from streamlit.testing.v1 import AppTest
    at = AppTest.from_file(str(Path(__file__).resolve().parents[1] / 'app.py'), default_timeout=60).run()
    assert not at.exception
    assert 'Monitoramento estatístico' in [x.label for x in at.tabs]
    assert any(x.value.startswith('Fase I:') for x in at.caption)
    radio = next(x for x in at.radio if x.label == 'Granularidade territorial')
    assert radio.value == 'Estadual'
    radio.set_value('Município').run()
    assert not at.exception


def test_iteracoes_da_fase1_reproduzem_as_exclusoes_de_barros_2021():
    r = mon.analisar(serie_barros(), '2017-01-01', '2020-12-01', defasagens_lb=(1,), automatico=True)
    it1, it2, it3 = (mon.iteracao_fase1(r, k) for k in (1, 2, 3))
    assert len(it1['considerados']) == 48 and it1['excluidos_antes'].empty
    fora1 = it1['considerados'].loc[it1['considerados']['Sinal X'], 'Período'].dt.strftime('%Y-%m').tolist()
    assert fora1 == ['2020-06']
    assert len(it2['considerados']) == 47
    assert it2['excluidos_antes']['Período'].dt.strftime('%Y-%m').tolist() == ['2020-06']
    assert it2['considerados'].loc[it2['considerados']['Sinal AM'], 'Período'].dt.strftime('%Y-%m').tolist() == ['2020-07']
    assert len(it3['considerados']) == 46
    assert not (it3['considerados']['Sinal X'] | it3['considerados']['Sinal AM']).any()
    with pytest.raises(ValueError):
        mon.iteracao_fase1(r, 4)


def test_fase2_corresponde_ao_ano_seguinte_a_fase1():
    assert mon.fim_fase2('2025-12') == pd.Timestamp('2026-12-01')
    s = serie_sintetica(np.random.default_rng(7).poisson(40, 84), '2020-01-01')  # jan./2020 a dez./2026
    r = mon.analisar(s, '2022-01-01', '2025-12-01', mon.fim_fase2('2025-12'))
    assert r.fase_ii['Período'].min() == pd.Timestamp('2026-01-01')
    assert r.fase_ii['Período'].max() == pd.Timestamp('2026-12-01')
    regra = mon.referencia_do_ano(s, 2026)
    assert regra['fim'] == pd.Timestamp('2025-12-01') and regra['meses'] == 48


def test_referencia_fixa_nao_muda_por_tendencia_e_aceita_64_meses():
    s = serie_sintetica(np.arange(1, 85), '2020-01-01')
    regra = mon.referencia_do_ano(s, 2026)
    assert regra['meses'] == 48 and regra['inicio'] == pd.Timestamp('2022-01-01')
    assert regra['tentativas'] == []
    assert mon.referencia_do_ano(s, 2026, padrao=64)['inicio'] == pd.Timestamp('2020-09-01')


def test_alfa_max_exclusao_e_instabilidade_sao_efetivamente_aplicados():
    s = serie_barros()
    r = mon.analisar(s, '2017-01', '2020-12', alfa=.9, max_exclusao=0)
    assert r.params.excluidos == () and not r.params.estavel
    assert r.fase_i['Situação fase I'].str.contains('instável').all()
    assert r.configuracao['alfa'] == .9 and r.configuracao['max_exclusao'] == 0
    assert (r.pressupostos['Decisão'] == np.where(r.pressupostos['Valor-p'] < .9,
                                                'Rejeita H0', 'Não rejeita H0')).all()
    automatico = mon.analisar(s, '2017-01', '2020-12', automatico=True, max_exclusao=0)
    assert not automatico.params.estavel and automatico.params.excluidos == ()


def test_lacuna_nao_pode_ser_mascarada_por_duplicata():
    s = serie_barros().iloc[:48].copy()
    s.iloc[10] = s.iloc[11]
    with pytest.raises(ValueError, match='duplicatas'):
        mon.analisar(s, '2017-01', '2020-12')


@pytest.mark.parametrize('opcoes', [{'lam': 0}, {'largura': -1}, {'largura_ewma': float('nan')},
                                    {'alfa': 1}, {'max_exclusao': 1}, {'dias_consolidacao': -1},
                                    {'defasagens_lb': (0,)}])
def test_parametros_invalidos_sao_recusados(opcoes):
    with pytest.raises(ValueError):
        mon.analisar(serie_barros(), '2017-01', '2020-12', **opcoes)


def test_taxas_invalidas_e_serie_constante_nao_geram_limites_enganosos():
    for valor in [np.nan, np.inf, -1]:
        s = serie_barros()
        s.loc[0, TAXA] = valor
        with pytest.raises(ValueError, match='finitas'):
            mon.analisar(s, '2017-01', '2020-12')
    with pytest.raises(ValueError, match='dispersão nula'):
        mon.analisar(serie_sintetica(np.full(48, 100)), '2020-01', '2023-12')


def test_regra_exploratoria_64_testa_minimo_mesmo_fora_do_passo(monkeypatch):
    monkeypatch.setattr(mon, 'cox_stuart', lambda x, **kwargs: (len(x), 0, 0.001))
    s = serie_sintetica(np.arange(1, 85), '2020-01-01')
    regra = mon.sugerir_fase1(s, '2025-12', padrao=64)
    assert [v['Meses'] for v in regra['tentativas']] == [64, 52, 40, 28, 24]
    assert regra['meses'] == 24 and not regra['aprovada']


def test_sensibilidade_reporta_todos_cenarios_sem_alterar_fase2():
    s = serie_sintetica(np.random.default_rng(42).poisson(40, 60), '2020-01-01')
    tab = mon.sensibilidade(s, '2023-12', '2024-12')
    assert tab['Meses'].tolist() == [24, 36, 48, 64]
    assert tab['Situação'].tolist() == ['Calculado'] * 3 + ['Indisponível']
    assert (tab.loc[tab['Situação'] == 'Calculado', 'Meses fase II disponíveis'] == 12).all()
    assert 'sem cobertura' in tab.iloc[-1]['Motivo']
    assert tab.loc[tab['Meses'] == 48, 'μ0'].iloc[0] == pytest.approx(
        mon.analisar(s, '2020-01', '2023-12', '2024-12').params.mu0)


def test_fase2_com_inicio_mensal_e_lacuna_reinicia_memoria():
    s = serie_sintetica(np.random.default_rng(42).poisson(40, 84), '2020-01-01')
    s = s[s['Período'] != pd.Timestamp('2026-03-01')]
    r = mon.analisar(s, '2021-05', '2025-04', '2026-04')
    assert r.fase_ii['Período'].min() == pd.Timestamp('2025-05-01')
    abril = r.fase_ii.loc[r.fase_ii['Período'] == '2026-04-01'].iloc[0]
    assert pd.isna(abril['AM'])
    assert abril['EWMA'] == pytest.approx(.1 * abril[TAXA] + .9 * r.params.mu0)


def test_relatorios_em_pdf():
    from painel.relatorio import relatorio_monitoramento, relatorio_aba, desenho_linha
    r = mon.analisar(serie_barros(), '2017-01-01', '2020-12-01', defasagens_lb=(1,))
    arl = pd.DataFrame({'Deslocamento': [0, 1], 'X': [370.4, 43.9], 'Quadrimestral': [1481.6, 25.2],
                        'EWMA': [369.8, 9.7]})
    contexto = dict(indicador='Série de Barros (2021)', territorio='Brasil', granularidade='Nacional',
                    sexo='Feminino', base='30/06/2021', consolidacao='')
    proto = dict(modo='Teste', lam=.1, le=2.701, lx=3.0, dias=60, automatico=True, justificativa='')
    pdf, paginas = relatorio_monitoramento(r, contexto, proto, arl, ('Adequado', 'Teste.'), guardar_paginas=True)
    assert pdf.startswith(b'%PDF') and len(paginas) >= 3
    serie = pd.DataFrame({'Ano': [2024, 2025], 'Óbitos': [10, 12], 'Taxa por 100 mil': [1.0, 1.2]})
    pdf_aba = relatorio_aba('Evolução temporal', dict(indicador='Teste', linhas=['Linha'], destaques=[('A', '1')]),
                            [('grafico', 'Série', desenho_linha(serie, 'Ano', 'Taxa por 100 mil', 'Taxa'), .2),
                             ('tabela', 'Tabela', serie)])
    assert pdf_aba.startswith(b'%PDF')
