"""O gate de publicação recusa dados incoerentes, sem consultar fontes externas."""
from itertools import product
import json

import pandas as pd
import pytest

from dominio.dados import IDADES, INDICADORES, recortar
from etl import validar as modulo
from etl.definicao_cid import ID_DEFINICAO_CID


@pytest.fixture
def lote(tmp_path, monkeypatch):
    municipios = [f'32{i:04d}' for i in range(78)]
    f = pd.DataFrame(product(municipios, [2024], [1], ['Homicídio', 'Suicídio'],
                             IDADES, ['Masculino', 'Feminino', 'Ignorado']),
                     columns=['cod_mun_res', 'ano', 'mes', 'tipo_causa', 'faixa_etaria', 'sexo'])
    f['dt_obito'] = '2024-01-01'
    f['Obitos'] = 1
    f = f[['cod_mun_res', 'dt_obito', 'mes', 'ano', 'tipo_causa', 'faixa_etaria', 'sexo', 'Obitos']]
    p = pd.DataFrame(product(municipios, [2024], IDADES[:-1], ['Masculino', 'Feminino']),
                     columns=['cod_mun_res', 'ano', 'faixa_etaria', 'sexo'])
    p['populacao'] = 100
    g = pd.DataFrame({'cod_mun_res': municipios})
    meta = {'anos_disponiveis': [2024], 'extracoes': {'2024': {'meses': [1], 'definicao_cid': ID_DEFINICAO_CID}},
            'definicao_cid': {'id': ID_DEFINICAO_CID}}
    for stem, extra in [('raca_cor', 'raca_cor'), ('meios_cid', 'cid')]:
        partes = []
        for indicador, cfg in INDICADORES.items():
            fato, _ = recortar(f, p, indicador, municipios)
            c = fato.groupby(['cod_mun_res', 'ano', 'mes', 'sexo'], as_index=False).Obitos.sum()
            c['indicador'] = indicador
            c[extra] = 'Branca' if stem == 'raca_cor' else ('X60' if cfg['causa'] == 'Suicídio' else 'X93')
            partes.append(c)
        pd.concat(partes).to_csv(tmp_path / f'f_{stem}.csv.gz', index=False)
        (tmp_path / f'{stem}_meta.json').write_text(json.dumps({
            'cobertura': {'2024': [1]}, 'definicao_cid_por_ano': {'2024': ID_DEFINICAO_CID}}))
    monkeypatch.setattr(modulo, 'carregar', lambda: (f, p, g, meta))
    monkeypatch.setattr(modulo, 'DADOS', tmp_path)
    return f, p, meta, tmp_path


def test_validacao_padrao_concilia_todo_historico(lote):
    assert modulo.validar()['anos_complementos_conferidos'] == [2024]
    arq = lote[3] / 'f_meios_cid.csv.gz'
    c = pd.read_csv(arq, dtype={'cod_mun_res': str})
    c.loc[0, 'Obitos'] += 1
    c.to_csv(arq, index=False)
    with pytest.raises(ValueError, match='Complemento diverge'):
        modulo.validar()


def test_data_mensal_deve_corresponder_ao_ano_e_mes(lote):
    lote[0].loc[0, 'dt_obito'] = '2023-12-01'
    with pytest.raises(ValueError, match='Data inválida'):
        modulo.validar()


def test_cobertura_declarada_deve_corresponder_a_fato(lote):
    lote[2]['extracoes']['2024']['meses'] = [1, 2]
    with pytest.raises(ValueError, match='Cobertura declarada'):
        modulo.validar()


@pytest.mark.parametrize('coluna,valor', [('indicador', 'Indicador desconhecido'),
                                        ('cid', 'A00'), ('sexo', 'Desconhecido')])
def test_dominios_complementares_nao_podem_ser_ignorados(lote, coluna, valor):
    arq = lote[3] / 'f_meios_cid.csv.gz'
    c = pd.read_csv(arq, dtype={'cod_mun_res': str})
    indevido = c.iloc[[0]].copy()
    indevido[coluna] = valor
    indevido['Obitos'] = 0
    c = pd.concat([c, indevido], ignore_index=True)
    c.to_csv(arq, index=False)
    with pytest.raises(ValueError, match='Domínio'):
        modulo.validar([2024])


def test_ano_pedido_deve_existir_na_base(lote):
    with pytest.raises(ValueError, match='Anos sem cobertura'):
        modulo.validar([2025])


def test_complemento_nao_admite_zeros_fora_da_cobertura(lote):
    arq = lote[3] / 'f_meios_cid.csv.gz'
    c = pd.read_csv(arq, dtype={'cod_mun_res': str})
    fora = c.iloc[[0]].copy()
    fora['mes'] = 2
    fora['Obitos'] = 0
    pd.concat([c, fora]).to_csv(arq, index=False)
    with pytest.raises(ValueError, match='fora da cobertura'):
        modulo.validar()
