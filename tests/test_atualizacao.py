from datetime import date
import json,sys
from pathlib import Path
import pytest
import atualizar

def test_janela_movel():
    cfg={'ano_inicial_historico':2016,'anos_reprocessamento':2}
    assert atualizar.intervalo(date(2026,10,2),cfg)==(2025,2026)
    assert atualizar.intervalo(date(2027,1,1),cfg)==(2026,2027)
    with pytest.raises(ValueError):atualizar.intervalo(date(2026,10,2),cfg,2027,2028)

def test_falha_na_extracao_preserva_dados_publicados(tmp_path,monkeypatch):
    dados=tmp_path/'dados';dados.mkdir();(dados/'dataset.zip').write_bytes(b'pacote-anterior')
    estado=tmp_path/'estado'
    monkeypatch.setattr(atualizar,'DADOS',dados);monkeypatch.setattr(atualizar,'ESTADO',estado)
    monkeypatch.setattr(sys,'argv',['atualizar.py','--publicar-local'])
    def falhar(*args,**kwargs):raise RuntimeError('Fonte indisponível')
    monkeypatch.setattr(atualizar.subprocess,'run',falhar)
    with pytest.raises(RuntimeError,match='Fonte indisponível'):atualizar.main()
    assert (dados/'dataset.zip').read_bytes()==b'pacote-anterior'
    assert not (estado/'atualizacao.lock').exists()
    relatorio=json.loads(next(estado.glob('lotes/*/execucao.json')).read_text())
    assert relatorio['status']=='falhou'
