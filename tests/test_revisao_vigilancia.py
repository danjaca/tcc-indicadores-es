"""Regressões da apresentação prudente e do registro das análises exploratórias."""
import pandas as pd
import pytest
from streamlit.testing.v1 import AppTest

from configuracao import RAIZ
from dominio import monitoramento as mon
from dominio.dados import carregar, recortar
from painel import relatorio
from painel.vistas import monitoramento as vista


@pytest.fixture(scope='module')
def jovens():
    f, p, g, _ = carregar()
    nf, npop = recortar(f, p, 'Homicídios — jovens de 15 a 29 anos', g.cod_mun_res)
    return mon.analisar(mon.serie_mensal(nf, npop), '2022-01', '2025-12', '2026-12',
                        data_base='2026-10-09')


def test_sinais_recentes_preservados_no_calculo_e_neutros_na_apresentacao(jovens):
    f2 = jovens.fase_ii
    recentes = f2['Em consolidação']
    assert (f2.loc[recentes, 'Sinal EWMA'] == 'Redução').all()
    assert jovens.fase_ii.iloc[-1]['Sinal X'] == 'Redução'
    ui, pdf = vista._tabela_sinais(f2), relatorio.tabela_sinais(f2)
    for coluna in ('Sinal X', 'Sinal AM', 'Sinal EWMA'):
        assert ui.loc[recentes, coluna].eq('Aguardando consolidação').all()
        assert pdf.loc[recentes, coluna].eq('Suspenso').all()
    assert ui.loc[5, 'Sinal EWMA'] == pdf.loc[5, 'Sinal EWMA'] == 'Redução'
    for fig in (vista.figura_x(jovens), vista.figura_am(jovens), vista.figura_ewma(jovens, .1, 2.701)):
        sinais = [t for t in fig.data if t.name and t.name.startswith('Sinal')]
        datas = {pd.Timestamp(d) for t in sinais for d in t.x}
        assert not datas.intersection(set(f2.loc[recentes, 'Período']))
        assert any(t.name == 'Mês em consolidação' for t in fig.data)


def test_quadrimestre_fora_dos_limites_explicita_sinalizacao_suspensa(jovens):
    q = jovens.quadrimestral
    segundo = q.loc[q['Quadrimestre'].eq('2º') & q['Leitura'].eq('Quadrimestre isolado')].iloc[0]
    assert segundo[mon.TAXA] < segundo['LIC']
    assert segundo['Sinal'] == ''
    assert segundo['Situação da sinalização'] == 'Suspensa: consolidação'
    t = relatorio.tabela_quadrimestral(q)
    assert t.loc[segundo.name, 'Sinal'] == 'Suspenso'


def test_historico_sessao_preserva_alternativas_sem_duplicar_rerun():
    at = AppTest.from_file(str(RAIZ / 'app.py'), default_timeout=80).run()
    assert not at.exception
    inicial = len(at.session_state['mon_historico'])
    at.run()
    assert len(at.session_state['mon_historico']) == inicial
    at.radio(key='mon_modo').set_value('Ajuste pela vigilância').run()
    at.selectbox(key='mon_janela').set_value(64).run()
    assert not at.exception
    historico = at.session_state['mon_historico']
    assert len(historico) == inicial + 2
    assert historico[-2]['configuracao']['processo']['n_inicial'] == 48
    assert historico[-1]['configuracao']['processo']['n_inicial'] == 64
    assert all('historico_sessao' not in item['configuracao'] for item in historico)
    assert all(item['instante_utc'].endswith('+00:00') for item in historico)


def test_ranking_municipal_aceita_corte_sem_retirar_municipios_da_tabela():
    at = AppTest.from_file(str(RAIZ / 'app.py'), default_timeout=80).run()
    at.radio[1].set_value('Taxa por 100 mil').run()
    assert not at.exception
    at.number_input(key='ranking_minimo').set_value(100000).run()
    assert not at.exception
    assert any('Nenhum município atende' in item.value for item in at.info)
    tabelas = [item.value for item in at.dataframe if 'no_municipio' in item.value]
    assert any(len(tabela) == 78 for tabela in tabelas)


def test_pdf_preserva_paragrafo_curto_inteiro_ao_mudar_pagina():
    import matplotlib.pyplot as plt
    doc = relatorio.Documento('Relatório', guardar_paginas=True)
    doc.paragrafo('Abertura')
    doc._y = .09
    texto = 'Texto de interpretação dos limites. ' * 15
    doc.paragrafo(texto)
    doc.finalizar()
    try:
        ocorrencias = [(i, t.get_text()) for i, pg in enumerate(doc.paginas) for t in pg.texts
                       if t.get_text().startswith('Texto de interpretação')]
        assert len(ocorrencias) == 1 and ocorrencias[0][0] == 1
        assert ' '.join(ocorrencias[0][1].split()) == texto.strip()
    finally:
        for pg in doc.paginas:
            plt.close(pg)


def test_diagnostico_causas_identifica_subconjunto_e_recusa_dados_obsoletos(tmp_path, monkeypatch):
    import hashlib
    import json
    from dominio import dados
    monkeypatch.setattr(dados, 'DADOS', tmp_path)
    (tmp_path / 'dataset.zip').write_bytes(b'base de teste')
    codigos = [f'Y{i}' for i in range(10, 35)] + ['R99']
    df = pd.DataFrame({'Recorte': 'Suicídio geral', 'Ano': 2026, 'Mês': 1, 'CID': codigos,
                       'Óbitos': [dict(Y10=2, Y22=3, R99=4).get(c, 0) for c in codigos]})
    arquivo = tmp_path / 'diagnostico_causas.csv'
    df.to_csv(arquivo, index=False)
    meta = dict(status='disponivel', sha256_csv=hashlib.sha256(arquivo.read_bytes()).hexdigest(),
                sha256_dataset_principal=hashlib.sha256(b'base de teste').hexdigest())
    metadados = tmp_path / 'diagnostico_causas_meta.json'
    metadados.write_text(json.dumps(meta))
    tabela, _ = dados.diagnostico_causas('Suicídio geral')
    assert tabela[['Y10–Y34', 'Y22–Y24 (subconjunto)', 'R99']].iloc[0].tolist() == [5, 3, 4]
    meta['status'] = 'obsoleto'
    metadados.write_text(json.dumps(meta))
    with pytest.raises(ValueError, match='precisa de atualização'):
        dados.diagnostico_causas('Suicídio geral')
    meta.update(status='disponivel', sha256_csv='incorreto')
    metadados.write_text(json.dumps(meta))
    with pytest.raises(ValueError, match='não corresponde'):
        dados.diagnostico_causas('Suicídio geral')
