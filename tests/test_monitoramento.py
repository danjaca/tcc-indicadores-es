import numpy as np
import pandas as pd
import pytest
from monitoramento import ajustar, aplicar, funil, TAXA


def serie(anos, obitos, pop=100000):
    t = pd.DataFrame({'Ano': list(anos), 'Óbitos': obitos, 'População': pop})
    t[TAXA] = t['Óbitos']/t['População']*100000
    return t


def test_referencia_ponderada_e_limites_populacao():
    t=serie(range(2016,2021),[10,20,10,20,10])
    t['População']=[100000,200000,100000,200000,100000];t[TAXA]=10.
    r=ajustar(t)
    assert r.taxa==10
    out=aplicar(serie([2021,2022],[10,20],[100000,200000]),r)
    assert out['LSC u'].iloc[0]==pytest.approx(10+3*np.sqrt(10))
    assert out['LSC u'].iloc[1]==pytest.approx(10+3*np.sqrt(5))


def test_sem_vazamento_ewma_cusum_reset_e_quartis():
    r=ajustar(serie(range(2016,2021),[10,10,10,10,10]))
    out=aplicar(serie([2021,2022],[100,100]),r)
    assert r.taxa==10
    assert out['EWMA'].iloc[0]==28
    assert out['EWMA'].iloc[1]==pytest.approx(42.4)
    assert out['Sinal CUSUM +'].all()
    assert out['CUSUM +'].iloc[0]==out['CUSUM +'].iloc[1]
    with pytest.raises(ValueError,match='sobreposição'):aplicar(serie([2020],[100]),r)


def test_sobredispersao_laney():
    r=ajustar(serie(range(2016,2023),[5,100,5,100,5,100,5],1000000))
    assert r.p_sobredispersao<.05 and r.sigma_z>1
    out=aplicar(serie([2023],[40],1000000),r)
    assert out['LSC controle'].iloc[0]>out['LSC u'].iloc[0]


def test_lacunas_nao_viram_zero_e_memoria_reinicia():
    r=ajustar(serie(range(2016,2021),[10]*5))
    t=serie([2021,2023],[100,10]);out=aplicar(t,r)
    assert out['EWMA'].iloc[1]==10
    with pytest.raises(ValueError):ajustar(serie([2016,2017,2018,2020,2021],[10]*5))
    with pytest.raises(ValueError):ajustar(serie(range(2016,2021),[10,10,np.nan,10,10]))
    with pytest.raises(ValueError):ajustar(serie(range(2016,2021),[0]*5))
    with pytest.raises(ValueError):funil(serie([2021],[1],0))


def test_funil_exato_pequenas_contagens_e_zero():
    from scipy.stats import poisson
    t=serie([2021,2022],[0,10],[1000,100000])
    out=funil(t,referencia=10)
    assert out['LSC 99,8%'].iloc[0]==poisson.ppf(.999,.1)/.01
    assert out['LIC 99,8%'].ge(0).all()
    assert (out['LSC 99,8%']>=out['LSC 95%']).all()
    assert funil(serie([2021],[0]),referencia=0)['LSC 99,8%'].iloc[0]==0


def test_interface_monitoramento_indicadores_e_parametros():
    from pathlib import Path
    from streamlit.testing.v1 import AppTest
    from modelo import INDICADORES
    at=AppTest.from_file(str(Path(__file__).resolve().parents[1]/'app.py'),default_timeout=40).run()
    assert not at.exception
    assert 'Monitoramento estatístico' in [x.label for x in at.tabs]
    assert any('Fase I:' in x.value for x in at.caption)
    for nome in INDICADORES:
        at.sidebar.selectbox[0].select(nome)
        at.sidebar.button[0].click().run()
        assert not at.exception
    at.selectbox(key='monitor_territorio').select('Norte').run()
    assert not at.exception
    assert any('Território de monitoramento: Norte' in x.value for x in at.caption)
    at.slider[0].set_value(.4).run()
    assert not at.exception
    at.multiselect(key='monitor_anos').set_value([2020]).run()
    assert not at.exception
    assert any('cinco a sete' in x.value for x in at.info)


def test_funil_na_fronteira_nao_sinaliza_por_arredondamento():
    # População não múltipla de 100 mil: a mesma taxa pode ter diferenças
    # de representação binária quando obtida por duas divisões equivalentes.
    from scipy.stats import poisson
    populacao=103363
    for nivel in [.95,.998]:
        alfa=(1-nivel)/2
        inferior=int(poisson.ppf(alfa,4*populacao/100000))
        superior=int(poisson.ppf(1-alfa,4*populacao/100000))
        out=funil(serie([2024,2025],[inferior,superior],populacao),referencia=4)
        coluna='Sinal 95%' if nivel==.95 else 'Sinal 99,8%'
        assert not out[coluna].any()
        fora=funil(serie([2024],[superior+1],populacao),referencia=4)
        assert fora[coluna].iloc[0]
