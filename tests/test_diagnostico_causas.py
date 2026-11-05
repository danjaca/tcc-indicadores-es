from pathlib import Path
from urllib.parse import parse_qs
import hashlib
import json

from bs4 import BeautifulSoup
import pandas as pd

from etl import diagnostico_causas as dc
from etl.nucleo_tabnet import CID3_FIELD, parse_form


class Resposta:
    status_code = 200
    encoding = 'iso-8859-1'

    def __init__(self, texto):
        self.text = texto
        self.content = texto.encode('utf-8')

    def raise_for_status(self):
        pass


def fonte_simulada(monkeypatch, falhar=False):
    soup = BeautifulSoup((Path(__file__).parent / 'fixtures' / 'formulario_tabnet_reduzido.html').read_text(), 'lxml')
    campo = soup.find('select', attrs={'name': CID3_FIELD})
    existentes = {o.get_text(' ', strip=True).split()[0] for o in campo.select('option')}
    for cid in dc.CODIGOS:
        if cid not in existentes:
            opcao = soup.new_tag('option', value='diag_' + cid)
            opcao.string = cid + ' descrição diagnóstica'
            campo.append(opcao)
    formulario = str(soup)
    form = parse_form(formulario)
    anos = {o['value']: o['label'] for o in form['options']['Arquivos']}
    municipio = '320010'
    chamadas = []

    class Sessao:
        def request(self, metodo, url, **kwargs):
            chamadas.append((metodo, kwargs))
            if metodo == 'GET':
                return Resposta(formulario)
            if falhar:
                return Resposta('<html>Fonte sem tabulação válida</html>')
            s = parse_qs(kwargs['data'].decode('ascii'), encoding='iso-8859-1')
            ano = anos[s['Arquivos'][0]]
            diagnostico = s['Linha'] != form['defaults']['Linha'] and s[CID3_FIELD] != [dc.ALL]
            titulo = 'Causas 3 Dígitos' if diagnostico else 'Município Resid'
            corpo = '<html>Período: ' + ano + '<table><tr><th>' + titulo + '</th><th>Jan</th><th>Fev</th><th>Total</th></tr>'
            linhas = [('Y10 evento', 1), ('Y22 disparo', 2), ('R99 indefinida', 3)] if diagnostico else [(municipio + ' Município', 20)]
            for rotulo, n in linhas:
                corpo += f'<tr><td>{rotulo}</td><td>{n}</td><td>{n}</td><td>{n*2}</td></tr>'
            total = sum(n for _, n in linhas)
            return Resposta(corpo + f'<tr><td>Total</td><td>{total}</td><td>{total}</td><td>{total*2}</td></tr></table></html>')

        def close(self):
            pass

    monkeypatch.setattr(dc.requests, 'Session', Sessao)
    return chamadas


def test_consulta_causas_preserva_evidencias_e_recortes(tmp_path, monkeypatch):
    chamadas = fonte_simulada(monkeypatch)
    meta = dc.consultar([2026], tmp_path / 'dados', tmp_path / 'evidencias', intervalo=0)
    assert meta['status'] == 'disponivel', meta.get('erro')
    assert meta['requisicoes_http'] == len(chamadas) == 6
    d = pd.read_csv(tmp_path / 'dados' / 'diagnostico_causas.csv')
    assert len(d) == 3 * 2 * 26
    assert d[d.CID.eq('Y10')]['Óbitos'].eq(1).all()
    assert d[d.CID.eq('Y11')]['Óbitos'].eq(0).all()
    assert meta['cobertura']['2026'] == [1, 2]
    assert meta['recortes']['Homicídios — mulheres de 10 a 59 anos']['sexo'] == 'Feminino'
    assert len(list((tmp_path / 'evidencias').glob('*_resposta.html'))) == 6


def test_erro_de_consulta_nao_publica_zeros(tmp_path, monkeypatch):
    fonte_simulada(monkeypatch, falhar=True)
    meta = dc.consultar([2026], tmp_path / 'dados', tmp_path / 'evidencias', intervalo=0)
    assert meta['status'] == 'indisponivel'
    assert 'erro' in meta
    assert not (tmp_path / 'dados' / 'diagnostico_causas.csv').exists()
    assert (tmp_path / 'dados' / 'diagnostico_causas_meta.json').exists()


def test_reconsulta_parcial_preserva_historico_e_falha_marca_obsoleto(tmp_path, monkeypatch):
    fonte_simulada(monkeypatch)
    saida = tmp_path / 'dados'
    assert dc.consultar([2025, 2026], saida, tmp_path / 'coleta1', intervalo=0)['status'] == 'disponivel'
    anterior = pd.read_csv(saida / 'diagnostico_causas.csv')
    origem_2025 = json.loads((saida / 'diagnostico_causas_meta.json').read_text())['origem_por_ano']['2025']
    atual = dc.consultar([2026], saida, tmp_path / 'coleta2', intervalo=0)
    assert atual['anos'] == [2025, 2026] and atual['anos_consultados'] == [2026]
    assert atual['origem_por_ano']['2025'] == origem_2025
    novo = pd.read_csv(saida / 'diagnostico_causas.csv')
    pd.testing.assert_frame_equal(anterior[anterior.Ano.eq(2025)].reset_index(drop=True),
                                  novo[novo.Ano.eq(2025)].reset_index(drop=True))
    hash_csv = hashlib.sha256((saida / 'diagnostico_causas.csv').read_bytes()).hexdigest()
    fonte_simulada(monkeypatch, falhar=True)
    assert dc.consultar([2026], saida, tmp_path / 'coleta3', intervalo=0)['status'] == 'indisponivel'
    meta = json.loads((saida / 'diagnostico_causas_meta.json').read_text())
    assert meta['status'] == 'obsoleto' and meta['sha256_csv'] == hash_csv
    assert hashlib.sha256((saida / 'diagnostico_causas.csv').read_bytes()).hexdigest() == hash_csv
