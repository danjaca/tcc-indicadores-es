"""Fluxo de ajuste, sensibilidade e exportação do monitoramento no Streamlit."""
import json
import tomllib

import pandas as pd
from streamlit.testing.v1 import AppTest

from configuracao import RAIZ
from dominio import monitoramento as mon


def ajuste():
    at = AppTest.from_file(str(RAIZ / 'app.py'), default_timeout=80).run()
    assert not at.exception
    at.radio(key='mon_modo').set_value('Ajuste pela vigilância').run()
    assert not at.exception
    return at


def test_64_meses_inicio_fase2_intermediario_e_sensibilidade():
    at = ajuste()
    at.selectbox(key='mon_janela').set_value(64).run()
    assert not at.exception
    assert any('64 de 64 meses mantidos' in c.value for c in at.caption)
    at.select_slider(key='mon_inicio_fase2').set_value(pd.Timestamp('2025-07-01'))
    at.number_input(key='mon_meses_f2').set_value(18).run()
    assert not at.exception
    assert any('Mar/2020–Jun/2025 (64 de 64' in c.value for c in at.caption)
    at.radio(key='mon_secao').set_value('Sensibilidade').run()
    assert not at.exception
    tab = next(d.value for d in at.dataframe if 'Meses fase II disponíveis' in d.value)
    assert tab['Meses'].tolist() == [24, 36, 48, 64]
    assert tab['Situação'].eq('Calculado').all()
    assert tab['Meses fase II disponíveis'].eq(15).all()


def test_janela_indisponivel_e_cenarios_sem_cobertura_ficam_visiveis():
    at = ajuste()
    at.select_slider(key='mon_inicio_fase2').set_value(pd.Timestamp('2018-01-01'))
    at.selectbox(key='mon_janela').set_value(64).run()
    assert not at.exception
    assert any('fase I contém meses sem cobertura' in i.value for i in at.info)
    at.selectbox(key='mon_janela').set_value(24).run()
    at.radio(key='mon_secao').set_value('Sensibilidade').run()
    assert not at.exception
    tab = next(d.value for d in at.dataframe if 'Situação' in d.value and 'Meses' in d.value)
    assert tab['Meses'].tolist() == [24, 36, 48, 64]
    assert tab['Situação'].tolist() == ['Calculado', 'Indisponível', 'Indisponível', 'Indisponível']
    assert tab.loc[tab['Situação'].eq('Indisponível'), 'Motivo'].str.contains('cobertura').all()


def test_json_preserva_parametros_territorio_sexo_e_horizonte(monkeypatch):
    import streamlit as st
    capturados = {}
    original = st.download_button

    def capturar(label, data, *args, **kwargs):
        if label == 'Baixar parâmetros (JSON)':
            capturados['manifesto'] = json.loads(data)
        return original(label, data, *args, **kwargs)

    monkeypatch.setattr(st, 'download_button', capturar)
    at = ajuste()
    at.radio(key='mon_granularidade').set_value('Região de saúde').run()
    at.selectbox(key='mon_regiao').set_value('Sul').run()
    at.select_slider(key='mon_inicio_fase2').set_value(pd.Timestamp('2025-07-01'))
    at.selectbox(key='mon_janela').set_value(64)
    at.number_input(key='mon_meses_f2').set_value(18)
    at.number_input(key='mon_dias').set_value(45)
    at.number_input(key='mon_largura_x').set_value(2.7).run()
    at.radio(key='mon_secao').set_value('Parâmetros e reprodução').run()
    assert not at.exception
    m = capturados['manifesto']
    assert (m['territorio'], m['granularidade'], m['sexo']) == ('Região Sul', 'Região de saúde', 'Todos')
    assert len(m['municipios']) == 26
    assert len(m['sha256_dataset']) == len(m['sha256_regioes']) == 64
    p = m['parametros']
    assert p['inicio_fase2'] == 'Jul/2025' and p['fim_fase2_planejado'] == 'Dez/2026'
    assert p['dias_consolidacao'] == 45 and p['largura'] == 2.7
    assert p['alfa'] == .05 and p['max_exclusao'] == .2
    assert p['defasagens_ljung_box'] == [1, 12] and p['exclusao_automatica'] is False
    assert m['processo']['n_inicial'] == 64
    assert m['entrada']['inicio_fase1'] == '2020-03' and m['entrada']['fim_fase1'] == '2025-06'
    assert m['entrada']['largura_ewma'] == 2.701
    from dominio.dados import carregar, recortar
    f, pop, _, _ = carregar()
    nf, npop = recortar(f, pop, m['indicador'], m['municipios'])
    reproduzido = mon.analisar(mon.serie_mensal(nf, npop), **m['entrada'])
    assert reproduzido.params.mu0 == m['processo']['mu0']
    assert reproduzido.params.sigma0 == m['processo']['sigma0']
    assert len(reproduzido.fase_ii) == 15
    trecho = next(tomllib.loads(c.value) for c in at.code if '[monitoramento.exclusoes]' in c.value)
    assert trecho['monitoramento']['exclusoes']['Suicídio geral'] == []


SEM_FASE_II = '''
import numpy as np
import pandas as pd
from dominio import monitoramento as mon
from painel.vistas.monitoramento import mostrar_monitoramento
from configuracao import RAIZ
periodos = pd.date_range('2022-01-01', periods=48, freq='MS')
f = pd.DataFrame({'cod_mun_res': '320530', 'ano': periodos.year, 'mes': periodos.month,
 'tipo_causa': 'Suicídio', 'faixa_etaria': '30 a 39 anos', 'sexo': 'Feminino',
 'Obitos': np.random.default_rng(7).integers(20,40,len(periodos))})
p = pd.DataFrame({'cod_mun_res': '320530', 'ano': sorted(f.ano.unique()),
 'faixa_etaria': '30 a 39 anos', 'sexo': 'Feminino', 'populacao': 1000000})
g = pd.DataFrame({'cod_mun_res':['320530'],'no_municipio':['Vitória'],'regiao_saude':['Metropolitana']})
cfg=mon.ler_protocolo(RAIZ/'config.toml');cfg['fase1']={'Suicídio geral':['2022-01','2025-12']}
original=mon.ler_protocolo
mon.ler_protocolo=lambda _:cfg
try:
 mostrar_monitoramento(f,p,g,{'extracoes':{'2025':{'data':'2026-02-01'}}},2025,'Suicídio geral','Todos')
finally:
 mon.ler_protocolo=original
'''


def test_fase2_vazia_mantem_esquema_para_tabelas_e_exportacao():
    s = pd.DataFrame(columns=['Período', 'Ano', 'Mês', 'Óbitos', 'População', mon.TAXA])
    p = mon.Parametros('Jan/2022', 'Dez/2025', 48, 48, 3, .5, .564, 3, 1.5, 4.5, 1.843,
                       (), (), 1, True)
    f2 = mon.fase2(s, p, anterior=3)
    assert f2.empty
    assert {'AM', 'EWMA', 'LIC X', 'LSC X', 'LIC EWMA', 'LSC EWMA',
            'Sinal X', 'Sinal AM', 'Sinal EWMA', 'Em consolidação'}.issubset(f2)
    at = AppTest.from_string(SEM_FASE_II, default_timeout=80).run()
    assert not at.exception
    assert any('Ainda não há meses consolidados na fase II' in i.value for i in at.info)
    at.radio(key='mon_secao').set_value('Fase II · monitoramento mensal').run()
    assert not at.exception
    assert any(d.value.empty and 'Sinal EWMA' in d.value for d in at.dataframe)
    at.radio(key='mon_secao').set_value('Parâmetros e reprodução').run()
    assert not at.exception


def test_populacao_ausente_na_referencia_nao_gera_taxa_ou_limites_artificiais():
    script = SEM_FASE_II.replace('original=mon.ler_protocolo',
                                 'p=p[p.ano.ne(2023)]\noriginal=mon.ler_protocolo')
    at = AppTest.from_string(script, default_timeout=80).run()
    assert not at.exception
    assert any('fase I contém meses sem cobertura' in i.value for i in at.info)
