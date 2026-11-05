from datetime import date
import json,sys
import subprocess
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


def test_falha_em_complemento_paralelo_impede_publicacao(tmp_path,monkeypatch):
    dados=tmp_path/'dados';dados.mkdir();(dados/'dataset.zip').write_bytes(b'pacote-anterior')
    estado=tmp_path/'estado'
    monkeypatch.setattr(atualizar,'DADOS',dados);monkeypatch.setattr(atualizar,'ESTADO',estado)
    monkeypatch.setattr(sys,'argv',['atualizar.py','--inicio','2016','--fim','2024','--paralelo','--publicar-local'])
    consultados=[]
    def executar(args,**kwargs):
        modulo=args[2];consultados.append(modulo)
        if modulo=='etl.extrair_raca_cor':raise RuntimeError('Complemento divergente')
    monkeypatch.setattr(atualizar.subprocess,'run',executar)
    with pytest.raises(RuntimeError,match='Complemento divergente'):atualizar.main()
    assert set(consultados)=={'etl.executar_base','etl.extrair_raca_cor','etl.extrair_meios_cid'}
    assert (dados/'dataset.zip').read_bytes()==b'pacote-anterior'
    assert not (estado/'atualizacao.lock').exists()
    assert json.loads(next(estado.glob('lotes/*/execucao.json')).read_text())['status']=='falhou'


def test_retomada_reutiliza_historico_e_valida_antes_de_publicar(tmp_path,monkeypatch):
    dados=tmp_path/'dados';dados.mkdir();(dados/'dataset.zip').write_bytes(b'anterior')
    estado=tmp_path/'estado';seed=estado/'lotes'/'interrompido';(seed/'dados').mkdir(parents=True)
    (seed/'execucao.json').write_text('{"status":"falhou"}')
    (seed/'dados'/'dataset.zip').write_bytes(b'historico-reextraido')
    camada={'definicao_cid_por_ano':{str(a):atualizar.ID_DEFINICAO_CID for a in range(2016,2026)},
            'cobertura':{str(a):list(range(1,13)) for a in range(2016,2026)}}
    for nome in ['raca_cor_meta.json','meios_cid_meta.json']:(seed/'dados'/nome).write_text(json.dumps(camada))
    monkeypatch.setattr(atualizar,'DADOS',dados);monkeypatch.setattr(atualizar,'ESTADO',estado)
    monkeypatch.setattr(sys,'argv',['atualizar.py','--inicio','2016','--fim','2026','--retomar-lote',str(seed),'--publicar-local'])
    comandos=[]
    def executar(args,**kwargs):
        # Dados publicados só podem mudar depois da validação conjunta.
        assert (dados/'dataset.zip').read_bytes()==b'anterior'
        comandos.append(args[2:])
    monkeypatch.setattr(atualizar.subprocess,'run',executar)
    catalogos=[]
    def registrar(lote,raiz):
        assert (dados/'dataset.zip').read_bytes()==b'anterior'
        assert (lote/'dados_anteriores'/'dataset.zip').read_bytes()==b'anterior'
        assert (lote/'dados'/'dataset.zip').read_bytes()==b'historico-reextraido'
        assert any(c[0]=='etl.validar' for c in comandos)
        catalogos.append(lote.name)
        return {'manifesto':str(lote/'snapshot.json')}
    monkeypatch.setattr(atualizar,'registrar_ciclo',registrar)
    atualizar.main()
    complementos=[c for c in comandos if c[0].startswith('etl.extrair_')]
    assert len(complementos)==2 and all(c[1:]==['--inicio','2026','--fim','2026'] for c in complementos)
    assert ['etl.validar','--anos',*[str(a) for a in range(2016,2027)]] in comandos
    assert comandos[-1][0]=='etl.diagnostico_causas'
    assert (dados/'dataset.zip').read_bytes()==b'historico-reextraido'
    assert len(catalogos)==1


def test_falha_diagnostica_marca_obsoleto_sem_bloquear_base_validada(tmp_path,monkeypatch):
    dados=tmp_path/'dados';dados.mkdir()
    (dados/'dataset.zip').write_bytes(b'base-anterior')
    (dados/'diagnostico_causas.csv').write_bytes(b'contagens-diagnosticas-anteriores')
    (dados/'diagnostico_causas_meta.json').write_text('{"status":"disponivel"}')
    estado=tmp_path/'estado'
    monkeypatch.setattr(atualizar,'DADOS',dados);monkeypatch.setattr(atualizar,'ESTADO',estado)
    monkeypatch.setattr(sys,'argv',['atualizar.py','--publicar-local'])
    def executar(args,**kwargs):
        if args[2]=='etl.incorporar_lote':
            (Path(kwargs['env']['TCC_DADOS_DIR'])/'dataset.zip').write_bytes(b'base-validada-nova')
        if args[2]=='etl.diagnostico_causas':
            raise subprocess.CalledProcessError(1,args)
    def registrar(lote,raiz):
        assert (lote/'dados_anteriores'/'dataset.zip').read_bytes()==b'base-anterior'
        assert (lote/'dados'/'dataset.zip').read_bytes()==b'base-validada-nova'
        return {'manifesto':str(lote/'snapshot.json')}
    monkeypatch.setattr(atualizar.subprocess,'run',executar)
    monkeypatch.setattr(atualizar,'registrar_ciclo',registrar)
    atualizar.main()
    assert (dados/'dataset.zip').read_bytes()==b'base-validada-nova'
    assert (dados/'diagnostico_causas.csv').read_bytes()==b'contagens-diagnosticas-anteriores'
    assert json.loads((dados/'diagnostico_causas_meta.json').read_text())['status']=='obsoleto'
    report=json.loads(next(estado.glob('lotes/*/execucao.json')).read_text())
    assert report['status']=='publicado_no_checkout'
    assert report['diagnostico_causas']['status']=='indisponivel_ou_obsoleto'
