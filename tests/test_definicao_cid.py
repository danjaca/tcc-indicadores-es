"""Numeradores conforme as fichas 1.8.15, 1.8.16 e 1.8.17 do PES-ES 2024–2027.

Usa um recorte do formulário real do TabNet da SESA (tests/fixtures); não acessa a rede.
"""
import re
import unittest
from pathlib import Path

from etl.definicao_cid import (DEFINICAO_LEGADA, ID_DEFINICAO_CID, anos_fora_da_definicao,
                               codigos_detalhamento)
from etl.extrair_meios_cid import grupo, parse_cids
from etl.nucleo_tabnet import make_contract, parse_form
from modelo import carregar

FORMULARIO = (Path(__file__).with_name('fixtures') / 'formulario_tabnet_reduzido.html').read_text(encoding='utf-8')
MUNICIPIOS = sorted(carregar()[2].cod_mun_res)


def faixa(letra, inicio, fim):
    return [f'{letra}{n:02d}' for n in range(inicio, fim + 1)]


class TestDefinicaoCid(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.form = parse_form(FORMULARIO)
        cls.contrato = make_contract(cls.form, 2024, MUNICIPIOS)
        cls.rotulos = {o['value']: o['label'] for o in cls.form['options']['SSubcategorias_(20)']}

    def codigos_selecionados(self, causa):
        return {re.match(r'^(\S+)', self.rotulos[v]).group(1) for v in self.contrato['cids'][causa]}

    def test_codigos_conforme_as_fichas(self):
        c = self.contrato
        self.assertEqual(c['cid_codes']['Homicídio'],
                         faixa('X', 85, 99) + faixa('Y', 0, 9) + ['Y22', 'Y23', 'Y24', 'Y35', 'Y87.1', 'Y89.0'])
        self.assertEqual(c['cid_codes']['Suicídio'], faixa('X', 60, 84) + ['Y87.0'])
        homicidio, suicidio = self.codigos_selecionados('Homicídio'), self.codigos_selecionados('Suicídio')
        self.assertEqual(len(homicidio), 281)  # 279 subcategorias de categorias completas + Y87.1 + Y89.0
        self.assertEqual(len(suicidio), 251)   # 250 subcategorias de X60–X84 + Y87.0
        self.assertTrue({'X85.0', 'Y09.9', 'Y22.4', 'Y35.0', 'Y87.1', 'Y89.0'} <= homicidio)
        self.assertTrue({'X60.0', 'X84.9', 'Y87.0'} <= suicidio)
        for excluido in ['Y87.2', 'Y89.1', 'Y89.9', 'Y10.0', 'V01.0']:
            self.assertNotIn(excluido, homicidio | suicidio)
        self.assertFalse(homicidio & suicidio)
        self.assertEqual(c['definicao_cid']['id'], ID_DEFINICAO_CID)

    def test_tabulacao_por_categoria_aponta_para_a_subcategoria(self):
        self.assertEqual(self.contrato['cid_linha']['Homicídio']['Y87'], 'Y87.1')
        self.assertEqual(self.contrato['cid_linha']['Homicídio']['Y89'], 'Y89.0')
        self.assertEqual(self.contrato['cid_linha']['Suicídio']['Y87'], 'Y87.0')
        html = ('<p>Período: 2024</p><table><tr><th>Causas 3 Dígitos</th><th>Jan</th><th>Total</th></tr>'
                '<tr><td>X93   Agressao disparo arma de fogo de mao</td><td>3</td><td>3</td></tr>'
                '<tr><td>Y87   Seq lesao autopr inten agress fato int indet</td><td>2</td><td>2</td></tr>'
                '<tr><td>A00   Colera</td><td>0</td><td>0</td></tr>'
                '<tr><td>Total</td><td>5</td><td>5</td></tr></table>')
        tabela, meses = parse_cids(html, 2024, self.contrato['cid_linha']['Homicídio'])
        self.assertEqual(meses, [1])
        self.assertEqual(int(tabela.loc['Y87.1', 1]), 2)
        self.assertEqual(int(tabela.loc['X93', 1]), 3)
        self.assertEqual(int(tabela.to_numpy().sum()), 5)

    def test_controle_de_equivalencia_usa_os_dois_campos(self):
        eq = self.contrato['cid_equivalencia']
        self.assertEqual(len(eq['Homicídio']['categorias']), 29)
        self.assertEqual(len(eq['Homicídio']['subcategorias']), 279)
        self.assertEqual(len(eq['Suicídio']['categorias']), 25)
        self.assertEqual(len(eq['Suicídio']['subcategorias']), 250)

    def test_falha_se_o_formulario_nao_tiver_a_subcategoria(self):
        sem_y871 = re.sub(r'<option[^>]*>Y87\.1[^<]*</option>', '', FORMULARIO)
        with self.assertRaisesRegex(ValueError, 'Y87.1'):
            make_contract(parse_form(sem_y871), 2024, MUNICIPIOS)

    def test_grupos_de_meios_cobrem_todos_os_codigos(self):
        for causa in ['Homicídio', 'Suicídio']:
            for codigo in codigos_detalhamento(causa):
                self.assertTrue(grupo(codigo))
        self.assertEqual(grupo('Y22'), 'Arma de fogo')
        self.assertEqual(grupo('Y35'), 'Intervenção legal')
        self.assertEqual(grupo('Y87.0'), 'Sequelas (meio não especificado)')

    def test_anos_com_definicao_diferente(self):
        anos = {'2023': DEFINICAO_LEGADA, '2024': ID_DEFINICAO_CID}
        self.assertEqual(anos_fora_da_definicao(anos), [2023])


if __name__ == '__main__':
    unittest.main(verbosity=2)


def test_uniao_preserva_categoria_incompleta_sem_ampliar_sequelas(monkeypatch):
    from etl.nucleo_tabnet import query_definicao, parse_result, CID_FIELD, CID3_FIELD, ALL
    import etl.nucleo_tabnet as nucleo
    monkeypatch.setattr(nucleo.time,'sleep',lambda _:None)
    form=parse_form(FORMULARIO);c=make_contract(form,2026,MUNICIPIOS)
    chamadas=[]
    class Fonte:
        def __init__(self):self.form=form
        def query(self,s):
            chamadas.append(s)
            # Cinco registros da categoria, incluindo dois sem quarto dígito;
            # somente um registro de Y87.1. Y87 inteiro incluiria outros desfechos.
            valor=5 if s[CID3_FIELD]!=[ALL] else 1
            return ('<p>Período: 2026</p><table><tr><th>Município Resid</th><th>Jan</th><th>Total</th></tr>'
                    f'<tr><td>320530 Vitória</td><td>{valor}</td><td>{valor}</td></tr>'
                    f'<tr><td>Total</td><td>{valor}</td><td>{valor}</td></tr></table>')
    sel=dict(c['base']);sel[CID_FIELD]=c['cid_values']['Homicídio']['X93']+c['cid_values']['Homicídio']['Y87.1']
    raw=query_definicao(Fonte(),sel);mat,stats=parse_result(raw,2026,MUNICIPIOS)
    assert int(mat.to_numpy().sum())==6 and stats['months']==[1]
    assert len(chamadas)==2
    cat={o['value']:o['label'][:3] for o in form['options'][CID3_FIELD]}
    assert [cat[v] for v in chamadas[0][CID3_FIELD]]==['X93']
    assert chamadas[1][CID_FIELD]==c['cid_values']['Homicídio']['Y87.1']
    assert chamadas[1][CID3_FIELD]==[ALL]


def test_uniao_aceita_total_zero_explicitado_sem_colunas_mensais():
    import json
    from etl.nucleo_tabnet import MARCADOR_CONSULTA_COMPOSTA,parse_result
    positivo=('<p>Período: 2026</p><table><tr><th>Município Resid</th><th>Jan</th><th>Total</th></tr>'
              '<tr><td>320530 Vitória</td><td>5</td><td>5</td></tr><tr><td>Total</td><td>5</td><td>5</td></tr></table>')
    zero=('<p>Período: 2026</p><table><tr><th>Município Resid</th><th>Total</th></tr>'
          '<tr><td>320530 Vitória</td><td>0</td></tr><tr><td>Total</td><td>0</td></tr></table>')
    raw=json.dumps({'formato':MARCADOR_CONSULTA_COMPOSTA,'partes':[{'html':positivo},{'html':zero}]})
    tabela,stats=parse_result(raw,2026,MUNICIPIOS)
    assert stats['months']==[1] and stats['total']==5 and tabela.loc['320530',1]==5
