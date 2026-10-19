import unittest,json
from pathlib import Path
from dominio.dados import carregar,recortar,medidas,agrupado,INDICADORES,meses_disponiveis,serie_historica,comparacao_mensal
from etl.definicao_cid import DEFINICAO_LEGADA
from streamlit.testing.v1 import AppTest
# Referências de regressão conferidas externamente, separadas por definição de CID (ver referencias.json).
REFERENCIAS=json.loads((Path(__file__).with_name('referencias.json')).read_text(encoding='utf-8'))
AVISO=('Referências da definição de CID atual ainda não conferidas: rode python -m etl.gerar_referencias, '
       'confira com o TabNet/SESA e registre em tests/referencias.json.')
def numero(n):return f'{n:,}'.replace(',','.')
class TestDashboard(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.f,cls.p,cls.g,cls.meta=carregar()
        cls.ref=REFERENCIAS.get(cls.meta.get('definicao_cid',{}).get('id',DEFINICAO_LEGADA))
    def referencia(self):
        if self.ref is None:self.skipTest(AVISO)
        return self.ref
    def test_referencias_2024(self):
        ref=self.referencia()['anual_2024']
        for nome in INDICADORES:
            n,den=ref[nome]
            f,p=recortar(self.f,self.p,nome,self.g.cod_mun_res)
            a,b,t=medidas(f,p,2024,range(1,13))
            self.assertEqual((a,b),(n,den));self.assertAlmostEqual(t,n/den*100000)
    def test_quadrimestre_serie_e_comparacao(self):
        ref=self.referencia()['segundo_quadrimestre_2024']
        for nome in INDICADORES:
            n,den=ref[nome]
            f,p=recortar(self.f,self.p,nome,self.g.cod_mun_res)
            serie=serie_historica(f,p,[2023,2024],range(5,9));linha=serie[serie.Ano.eq(2024)].iloc[0]
            self.assertEqual((linha['Óbitos'],linha['População']),(n,den))
            mensal=comparacao_mensal(f,p,2024,range(5,9))
            self.assertEqual(set(mensal['Mês']),{5,6,7,8})
            self.assertEqual(mensal[mensal.Ano.eq(2024)]['Óbitos'].sum(),n)
            self.assertAlmostEqual(mensal[mensal.Ano.eq(2024)]['Taxa por 100 mil'].sum(),linha['Taxa por 100 mil'])
            self.assertEqual(mensal[mensal.Ano.eq(2023)]['Óbitos'].sum(),medidas(f,p,2023,range(5,9))[0])
    def test_municipio_e_ignorados(self):
        ref=self.referencia()
        cod=self.g.loc[self.g.no_municipio=='Jerônimo Monteiro','cod_mun_res']
        f,p=recortar(self.f,self.p,'Suicídio geral',cod)
        self.assertEqual(medidas(f,p,2024,range(1,13))[:2],tuple(ref['suicidio_jeronimo_monteiro_2024']))
        f,p=recortar(self.f,self.p,'Suicídio geral',self.g.cod_mun_res)
        t=agrupado(f,p,2024,range(1,13),['faixa_etaria','sexo'])
        self.assertTrue(t.loc[(t.faixa_etaria=='Ignorado')|(t.sexo=='Ignorado'),'Taxa por 100 mil'].isna().all())
    def test_cobertura_sem_zeros_artificiais(self):
        f,p=recortar(self.f,self.p,'Suicídio geral',self.g.cod_mun_res)
        self.assertEqual(medidas(f,p,int(f.ano.max())+1,range(1,13)),(None,None,None))
        parcial=f[~((f.ano==2024)&(f.mes>8))]
        self.assertEqual(medidas(parcial,p,2024,range(9,13)),(None,None,None))
        if self.ref is not None:self.assertEqual(medidas(parcial,p,2024,range(1,9))[0],self.ref['suicidio_jan_ago_2024'])
    def test_interface_filtros_e_grafico(self):
        at=AppTest.from_file(str(Path(__file__).resolve().parents[1]/'app.py'),default_timeout=40).run()
        self.assertFalse(at.exception);self.assertEqual(at.sidebar.button[0].label,'Atualizar')
        self.assertEqual(at.sidebar.multiselect[1].value,meses_disponiveis(self.f,max(self.meta['anos_disponiveis'])))
        at.sidebar.selectbox[1].select(2024);at.sidebar.multiselect[0].set_value([1,2,3]);at.sidebar.multiselect[1].set_value(list(range(1,13)));at.sidebar.button[0].click().run()
        if self.ref is not None:self.assertEqual(at.metric[0].value,numero(self.ref['anual_2024'][list(INDICADORES)[0]][0]))
        for nome in INDICADORES:
            at.sidebar.selectbox[0].select(nome);at.sidebar.multiselect[0].set_value([2]);at.sidebar.button[0].click().run()
            self.assertFalse(at.exception)
            if self.ref is not None:self.assertEqual(at.metric[0].value,numero(self.ref['segundo_quadrimestre_2024'][nome][0]))
            graf=json.loads(at.get('plotly_chart')[1].proto.spec)
            self.assertEqual([x['type'] for x in graf['data']],['bar','scatter'])
            for trace in graf['data']:self.assertEqual(trace['x'],['Mai','Jun','Jul','Ago'])
            self.assertIn('2023',graf['data'][0]['name']);self.assertIn('2024',graf['data'][1]['name'])
        at.sidebar.multiselect[2].set_value(['Vitória']);at.sidebar.button[0].click().run();self.assertFalse(at.exception)
        at.sidebar.multiselect[0].set_value([1,2,3]);at.sidebar.multiselect[1].set_value([1,4,8]);at.sidebar.button[0].click().run()
        self.assertFalse(at.exception)
        graf=json.loads(at.get('plotly_chart')[1].proto.spec);self.assertEqual(graf['data'][0]['x'],['Jan','Abr','Ago'])
        at.sidebar.multiselect[1].set_value([]);at.sidebar.button[0].click().run();self.assertFalse(at.exception);self.assertEqual(len(at.metric),0)


if __name__=='__main__':unittest.main(verbosity=2)
