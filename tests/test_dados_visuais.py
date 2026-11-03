"""Denominadores e cobertura dos gráficos descritivos, com dados sintéticos."""
import pandas as pd
import pytest

from painel.vistas.meios import resumo_meios, comparacao_meios
from painel.vistas.piramide import preparar_piramide


def test_piramide_mantem_ignorados_e_idades_ocultas_no_denominador():
    f = pd.DataFrame({'ano': [2024] * 4, 'mes': [1] * 4,
                      'faixa_etaria': ['30 a 39 anos', '30 a 39 anos', 'Ignorado', '60 a 69 anos'],
                      'sexo': ['Masculino', 'Feminino', 'Feminino', 'Ignorado'], 'Obitos': [10, 8, 7, 5]})
    t, auditoria = preparar_piramide(f, [2024], [1], ['30 a 39 anos'], ['Masculino', 'Feminino'])
    assert t['Total do indicador'].tolist() == [30, 30]
    assert t['Percentual dos óbitos (%)'].sum() == pytest.approx(60)
    assert auditoria['Idade ignorada'].iloc[0] == 7
    assert auditoria['Sexo ignorado'].iloc[0] == 5


def test_piramide_nao_converte_cobertura_incompleta_em_zero():
    f = pd.DataFrame({'ano': [2023, 2024, 2024], 'mes': [1, 1, 2],
                      'faixa_etaria': ['30 a 39 anos'] * 3, 'sexo': ['Feminino'] * 3, 'Obitos': [1, 2, 3]})
    t, auditoria = preparar_piramide(f, [2023, 2024], [1, 2], ['30 a 39 anos'], ['Feminino'])
    assert t.Ano.tolist() == [2024]
    assert t['Óbitos'].tolist() == [5]
    assert auditoria.loc[auditoria.Ano.eq(2023), 'Situação'].iloc[0] == 'Sem cobertura completa'


def test_meios_fecham_total_e_distinguem_cobertura_ausente():
    f = pd.DataFrame({'indicador': ['Suicídio geral'] * 2, 'ano': [2024] * 2, 'mes': [1] * 2,
                      'cod_mun_res': ['320530'] * 2, 'sexo': ['Masculino'] * 2,
                      'cid': ['X60', 'X70'], 'Obitos': [2, 3]})
    meta = {'cobertura': {'2024': [1]}, 'dimensao_cid': [
        {'cid': 'X60', 'meio': 'Intoxicação', 'descricao_cid': 'Código sintético 1'},
        {'cid': 'X70', 'meio': 'Enforcamento', 'descricao_cid': 'Código sintético 2'}]}
    grupos, detalhe = resumo_meios(f, meta, 'Suicídio geral', 2024, [1], ['320530'], 'Todos')
    assert grupos.Obitos.sum() == detalhe.Obitos.sum() == 5
    assert grupos['Frequência relativa (%)'].sum() == pytest.approx(100)
    assert resumo_meios(f, meta, 'Suicídio geral', 2023, [1], ['320530'], 'Todos') == (None, None)
    assert comparacao_meios(grupos, None).Anterior.isna().all()
