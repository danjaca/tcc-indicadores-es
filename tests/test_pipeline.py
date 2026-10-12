"""Testes locais com CSVs de referência e fonte simulada. Não fazem requisições externas."""
import unittest,tempfile,json
from pathlib import Path
from datetime import date
from unittest.mock import patch
import pandas as pd
from etl import pipeline
from modelo import carregar
NS=vars(pipeline)
F,POP,GEO,META=carregar()
MUN=sorted(GEO.cod_mun_res.tolist())
POP=POP[POP.ano.eq(2025)].copy()
NS['HOJE']=date(2026,9,11)

def fact(year=2026,months=range(1,9)):
    from itertools import product
    df=pd.DataFrame(product(MUN,months,NS['CAUSAS'],NS['FAIXAS'],NS['SEXOS']),columns=['cod_mun_res','mes','tipo_causa','faixa_etaria','sexo'])
    df['ano']=year;df['dt_obito']=pd.to_datetime(dict(year=df.ano,month=df.mes,day=1));df['Obitos']=1
    return df[NS['COLUNAS']]

class Tests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.path=Path(self.tmp.name)
        self.db=NS['sqlite3'].connect(self.path/'test.sqlite');self.db.executescript(NS['SCHEMA'])
    def tearDown(self):self.db.close();self.tmp.cleanup()
    def test_incremental_calendar(self):
        f=NS['precisa_atualizar'];now=date(2026,9,11)
        st={'assinatura':'v','ciclo':'2026-09','atualizado':'2026-08-11T00:00:00'}
        self.assertFalse(f(st,2025,now,'v'));self.assertFalse(f(st,2020,now,'v'))
        self.assertTrue(f(st,2025,date(2026,10,1),'v'))
        self.assertTrue(f(st,2020,date(2027,9,1),'v'))
        self.assertTrue(f(st,2020,now,'mudou'));self.assertTrue(f(None,2020,now,'v'))
    def test_idempotence_rollback_and_corruption(self):
        df=fact();NS['validar_fato'](df,2026,MUN,list(range(1,9)))
        save=NS['gravar_ano'];args=(self.db,'sim',2026,df,'sig',{'meses':list(range(1,9))},date(2026,9,11))
        save(*args);save(*args)
        self.assertEqual(self.db.execute('SELECT COUNT(*) FROM f_obitos').fetchone()[0],len(df))
        self.assertIsNotNone(NS['estado'](self.db,'sim',2026))
        with self.assertRaises(NS['sqlite3'].IntegrityError):
            save(self.db,'sim',2026,pd.concat([df,df.iloc[:1]]),'sig',{},date(2026,9,11))
        self.assertEqual(self.db.execute('SELECT SUM(Obitos) FROM f_obitos').fetchone()[0],len(df))
        with self.db:self.db.execute('UPDATE f_obitos SET Obitos=2 WHERE rowid=1')
        self.assertIsNone(NS['estado'](self.db,'sim',2026))
    def test_population_fallback_and_upgrade(self):
        NS['validar_pop'](POP,2025,MUN)
        NS['gravar_ano'](self.db,'pop',2025,POP,'s',{},date(2026,9,11))
        self.assertIsNotNone(NS['estado'](self.db,'pop',2025))
        r=NS['resolver_populacao'](self.db,[2026],{2025:'x'},MUN)
        self.assertTrue(r.ano.eq(2026).all());self.assertTrue(r.ano_fonte_populacao.eq(2025).all())
        self.assertTrue(r.denominador_provisorio.eq(1).all());self.assertAlmostEqual(r.populacao.sum(),POP.populacao.sum())
        with self.assertRaises(ValueError):NS['resolver_populacao'](self.db,[2027],{2025:'x'},MUN)
        # Uma publicação anunciada, mas ainda não carregada, não pode usar o fallback.
        with self.assertRaises(ValueError):NS['resolver_populacao'](self.db,[2026],{2025:'x',2026:'y'},MUN)
        newer=POP.copy();newer.ano=2026;newer.populacao+=1
        NS['gravar_ano'](self.db,'pop',2026,newer,'s',{},date(2026,9,11))
        r=NS['resolver_populacao'](self.db,[2026],{2025:'x',2026:'y'},MUN)
        self.assertTrue(r.denominador_provisorio.eq(0).all());self.assertTrue(r.ano_fonte_populacao.eq(2026).all())
    def test_parser_rejects_error_and_checks_totals(self):
        parse=NS['parse_result']
        html='<p>Período: 2026</p><table><tr><th>Município Resid</th><th>Jan</th><th>Total</th></tr><tr><td>320530 Vitória</td><td>2</td><td>2</td></tr><tr><td>Total</td><td>2</td><td>2</td></tr></table>'
        mat,stats=parse(html,2026,MUN);self.assertEqual(mat.to_numpy().sum(),2)
        with self.assertRaises(ValueError):parse('<h1>Servidor indisponível</h1>',2026,MUN)
        with self.assertRaises(ValueError):parse(html.replace('<td>Total</td><td>2','<td>Total</td><td>3'),2026,MUN)
        with self.assertRaises(ValueError):parse(html,2025,MUN)
    def test_partial_extraction_no_future_and_controls(self):
        cls=NS['ExtracaoIncremental'];obj=cls.__new__(cls)
        vazio={'subcategorias':[],'categorias':[]}
        obj.contract={'year':2026,'municipalities':MUN,'revision':'teste','fingerprint':'teste',
                      'cid_equivalencia':{'Homicídio':vazio,'Suicídio':vazio}}
        obj.directory=self.path
        def query(cause,age=None,sex=None,tag='',fresh=False,cid=None):
            return pd.DataFrame(36 if age is None else 1,index=MUN,columns=range(1,13),dtype='int64').rename_axis('cod_mun_res'),{'months':list(range(1,10))}
        obj.run_query=query
        df,meta=obj.extract_partial(8)
        self.assertEqual(len(df),78*8*2*12*3);self.assertEqual(df.mes.max(),8)
        def broken(*args,**kwargs):
            mat,stats=query(*args,**kwargs)
            if kwargs.get('tag')=='controle_fim':mat.iloc[0,0]+=1
            return mat,stats
        obj.run_query=broken
        with self.assertRaises(AssertionError):obj.extract_partial(8)
        def sem_subcategoria(*args,**kwargs):
            # Óbito com categoria de três dígitos, mas sem subcategoria: não pode sumir do numerador.
            mat,stats=query(*args,**kwargs)
            if kwargs.get('tag')=='equivalencia_categorias':mat.iloc[0,0]+=1
            return mat,stats
        obj.run_query=sem_subcategoria
        with self.assertRaisesRegex(ValueError,'subcategorias'):obj.extract_partial(8)
    def test_dimensions_and_atomic_export(self):
        pop=POP.copy();pop['ano_fonte_populacao']=2025;pop['denominador_provisorio']=0
        tables=NS['dimensoes'](GEO,pop,2016,2026,date(2026,9,11))
        self.assertEqual(len(tables['d_tempo']),132);self.assertTrue(tables['d_tempo'].dt_obito.is_unique)
        NS['persistir_dimensoes'](self.db,tables)
        self.assertEqual(self.db.execute('SELECT COUNT(*) FROM d_sexo').fetchone()[0],3)
        dest=NS['exportar'](self.db,self.path,tables,{'id':'teste','status':'parcial'})
        ptr=json.loads((self.path/'exportacao_atual.json').read_text());self.assertEqual(ptr['pasta'],str(dest.resolve()))
        self.assertEqual(len(json.loads((dest/'manifesto.json').read_text())['arquivos']),10)
    def test_full_orchestration_two_runs_and_failure(self):
        calls={'sim':0,'pop':0};fail={'sim':False}
        class Client:
            def __init__(self,*a):self.form={'options':{'Arquivos':[{'label':'2026'}]}}
            def close(self):pass
        class Extract:
            def __init__(self,*a):pass
            def extract_partial(self,limit):
                calls['sim']+=1
                if fail['sim']:raise ValueError('falha simulada')
                return fact(),{'meses':list(range(1,9))}
        def download(*args):calls['pop']+=1;return POP.copy(),{}
        config={'RAIZ':self.path/'execucao','HOJE':date(2026,9,11),'ANO_INICIAL':2026,
                'ANOS_FORCADOS':set(),'PERMITIR_POP_ANTERIOR':True,'INTERVALO_SEGUNDOS':0,
                'geografia':lambda *a:(GEO.copy(),{}),'catalogo_pop':lambda:{2025:'pops.zip'},
                'baixar_pop':download,'TabnetClient':Client,'ExtracaoIncremental':Extract,
                'make_contract':lambda *a:{'fingerprint':'constante'}}
        from contextlib import redirect_stdout
        from io import StringIO
        with patch.dict(NS,config),redirect_stdout(StringIO()):
            one=NS['executar']();two=NS['executar']()
            self.assertEqual(one['status'],'concluido');self.assertEqual(two['status'],'concluido')
            self.assertEqual(calls,{'sim':1,'pop':1})
            fail['sim']=True;NS['ANOS_FORCADOS']={2026}
            with self.assertRaises(RuntimeError):NS['executar']()
        db=NS['sqlite3'].connect(config['RAIZ']/'tcc.sqlite')
        self.assertEqual(db.execute('SELECT SUM(Obitos) FROM f_obitos').fetchone()[0],78*8*2*12*3)
        self.assertEqual(db.execute('SELECT DISTINCT ano_fonte_populacao FROM d_populacao').fetchone()[0],2025)
        db.close()

    def test_lock(self):
        with NS['trava'](self.path):
            with self.assertRaises(FileExistsError):
                with NS['trava'](self.path):pass
        self.assertFalse((self.path/'execucao.lock').exists())

if __name__=='__main__':unittest.main(verbosity=2)
