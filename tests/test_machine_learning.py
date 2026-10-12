import hashlib,json
from pathlib import Path
import pandas as pd
import pytest
from streamlit.testing.v1 import AppTest
from aprendizado import RESULTADOS,agregar
from configuracao import DADOS,MOSTRAR_APRENDIZADO

# A aba é opcional ([painel] aprendizado_de_maquina em config.toml). Ligada, exige resultados
# refeitos com a base publicada (o hash da base precisa coincidir com o manifesto).
pytestmark=pytest.mark.skipif(not MOSTRAR_APRENDIZADO,reason='Aba de aprendizado de máquina desligada em config.toml.')

def test_resultados_coerentes_com_base_e_metricas():
    manifest=json.loads((RESULTADOS/'manifesto.json').read_text())
    assert manifest['source_sha256']==hashlib.sha256((DADOS/'dataset.zip').read_bytes()).hexdigest()
    pred=pd.read_csv(RESULTADOS/'previsoes.csv')
    assert not pred.duplicated(['indicator','method','period','date','region']).any()
    for d in json.loads((RESULTADOS/'decisoes.json').read_text()):
        p=pred[pred.indicator.eq(d['indicator'])&pred.method.eq(d['ml'])&pred.period.eq('avaliação 2025')]
        assert len(p)==48
        assert abs((p.y-p.prediction).abs().mean()-d['mae_ml'])<1e-10
        state=agregar(p,'Espírito Santo')
        assert abs(state.y.sum()-p.y.sum())<1e-10

def test_quarta_aba_e_tres_indicadores():
    at=AppTest.from_file(str(Path(__file__).resolve().parents[1]/'app.py'),default_timeout=40).run()
    assert not at.exception
    assert [t.label for t in at.tabs]==['Evolução temporal','Distribuição territorial','Perfil demográfico','Machine learning','Dados e metodologia']
    indicators=list(at.sidebar.selectbox[0].options)
    for indicator in indicators:
        at.sidebar.selectbox[0].select(indicator);at.sidebar.button[0].click().run()
        assert not at.exception
        controls={x.key:x for x in at.selectbox}
        controls['ml_regiao'].select('Sul');at.run();assert not at.exception
        controls={x.key:x for x in at.selectbox}
        controls['ml_periodo'].select('suplementar 2026');at.run();assert not at.exception
        assert any('Erro médio absoluto' in m.label for m in at.metric)
