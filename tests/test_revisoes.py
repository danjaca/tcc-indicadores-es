import hashlib
import json
from zipfile import ZipFile

import pandas as pd
import pytest

from etl.revisoes import comparar, registrar_ciclo


def versao(pasta, meses, jovens=10, populacao=1000, cid='mesma-regra'):
    pasta.mkdir(parents=True)
    linhas = []
    for mes in meses:
        for causa, idade, sexo, n in [('Homicídio', '20 a 29 anos', 'Masculino', jovens),
                                      ('Homicídio', '30 a 39 anos', 'Feminino', 2),
                                      ('Suicídio', '70 a 79 anos', 'Masculino', 3)]:
            linhas.append(['320010', 2026, mes, causa, idade, sexo, n])
    f = pd.DataFrame(linhas, columns=['cod_mun_res', 'ano', 'mes', 'tipo_causa', 'faixa_etaria', 'sexo', 'Obitos'])
    p = pd.DataFrame([['320010', 2026, '20 a 29 anos', 'Masculino', populacao],
                      ['320010', 2026, '30 a 39 anos', 'Feminino', 800],
                      ['320010', 2026, '70 a 79 anos', 'Masculino', 500]],
                     columns=['cod_mun_res', 'ano', 'faixa_etaria', 'sexo', 'populacao'])
    with ZipFile(pasta / 'dataset.zip', 'w') as z:
        z.writestr('f_obitos.csv', f.to_csv(index=False))
        z.writestr('d_populacao.csv', p.to_csv(index=False))
        z.writestr('disponibilidade.json', json.dumps({'anos_disponiveis': [2026], 'definicao_cid': {'id': cid},
                                                     'extracoes': {'2026': {'meses': meses}},
                                                     'populacao': {'2026': {'ano_fonte': 2025, 'provisorio': True}}}))


def test_comparacao_separa_revisao_cobertura_e_denominador(tmp_path):
    a, b = tmp_path / 'anterior', tmp_path / 'atual'
    versao(a, [1, 3])
    versao(b, [1, 2], jovens=12, populacao=1200)
    r = comparar(a, b)
    j = r[r.Indicador.str.contains('jovens')].set_index('Período')
    assert j.at['2026-01', 'Diferença Óbitos'] == 2
    assert j.at['2026-01', 'Diferença População'] == 200
    assert j.at['2026-01', 'Variação óbitos (%)'] == 20
    assert j.at['2026-01', 'Diferença Taxa por 100 mil'] == 0
    assert j.at['2026-02', 'Situação'] == 'Novo mês disponível'
    assert pd.isna(j.at['2026-02', 'Óbitos anterior'])
    assert pd.isna(j.at['2026-02', 'Diferença Óbitos'])
    assert j.at['2026-03', 'Situação'] == 'Ausente na versão atual'
    assert pd.isna(j.at['2026-03', 'Óbitos atual'])


def test_definicao_cid_diferente_nao_vira_revisao_de_contagem(tmp_path):
    a, b = tmp_path / 'anterior', tmp_path / 'atual'
    versao(a, [1])
    versao(b, [1], jovens=20, cid='regra-alterada')
    r = comparar(a, b)
    assert r['Situação'].eq('Definição CID diferente ou não identificada').all()
    assert r['Diferença Óbitos'].isna().all()


def test_catalogo_preserva_snapshots_e_registra_hashes(tmp_path):
    estado = tmp_path / 'estado'
    lote = estado / 'lotes' / 'ciclo1'
    versao(lote / 'dados_anteriores', [1])
    versao(lote / 'dados', [1, 2], jovens=12)
    antes = {str(p): hashlib.sha256(p.read_bytes()).hexdigest() for p in lote.rglob('dataset.zip')}
    registrar_ciclo(lote, estado)
    manifesto = json.loads((lote / 'snapshot.json').read_text())
    catalogo = json.loads((estado / 'catalogo_snapshots.json').read_text())
    assert manifesto['anterior']['populacao']['2026']['provisorio'] is True
    assert manifesto['anterior']['arquivos']['dataset.zip']['sha256'] == antes[str(lote / 'dados_anteriores' / 'dataset.zip')]
    assert catalogo[0]['sha256_manifesto'] == hashlib.sha256((lote / 'snapshot.json').read_bytes()).hexdigest()
    with pytest.raises(FileExistsError):
        registrar_ciclo(lote, estado)
    assert antes == {str(p): hashlib.sha256(p.read_bytes()).hexdigest() for p in lote.rglob('dataset.zip')}
