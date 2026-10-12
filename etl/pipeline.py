from .nucleo_tabnet import *
from .definicao_cid import DESCRICAO_CID, ID_DEFINICAO_CID
# Valores padrão abaixo; etl/executar_base.py os ajusta antes de executar. Importar não acessa a rede.
import sqlite3, os, uuid, tempfile, sys, platform
from datetime import date
from zoneinfo import ZoneInfo
from ftplib import FTP
from contextlib import contextmanager

VERSAO = '1.2.0'  # 1.2.0: numeradores conforme as fichas (subcategorias Y87.0, Y87.1, Y89.0 etc.)
HOJE = datetime.now(ZoneInfo('America/Sao_Paulo')).date()
ANO_INICIAL = HOJE.year - 1
ANO_FINAL = HOJE.year
RAIZ = Path('var/etl')
ANOS_FORCADOS = set()
PERMITIR_POP_ANTERIOR = True
INTERVALO_SEGUNDOS = 3
JANELA_REVISAO = 2
MOTOR = 'requests'
POPKEY = ['cod_mun_res','ano','faixa_etaria','sexo']
SCHEMA = '''
CREATE TABLE IF NOT EXISTS estado(dataset TEXT, ano INTEGER, atualizado TEXT,
 ciclo TEXT, assinatura TEXT, linhas INTEGER, soma REAL, detalhes TEXT,
 PRIMARY KEY(dataset,ano));
CREATE TABLE IF NOT EXISTS execucoes(id TEXT PRIMARY KEY,inicio TEXT,fim TEXT,status TEXT,detalhes TEXT);
CREATE TABLE IF NOT EXISTS f_obitos(cod_mun_res TEXT,dt_obito TEXT,mes INTEGER,ano INTEGER,
 tipo_causa TEXT,faixa_etaria TEXT,sexo TEXT,Obitos INTEGER NOT NULL CHECK(Obitos>=0),
 PRIMARY KEY(cod_mun_res,dt_obito,tipo_causa,faixa_etaria,sexo));
CREATE TABLE IF NOT EXISTS populacao_fonte(cod_mun_res TEXT,ano INTEGER,faixa_etaria TEXT,
 sexo TEXT,populacao REAL NOT NULL CHECK(populacao>=0),
 PRIMARY KEY(cod_mun_res,ano,faixa_etaria,sexo));
'''

def utc(): return datetime.now(timezone.utc).isoformat()
def ciclo_mensal(hoje): return hoje.strftime('%Y-%m')
def assinatura_config(municipios):
    return digest({'versao':VERSAO,'municipios':municipios,'faixas':FAIXAS,
                   'sexos':SEXOS,'causas':CAUSAS,'url':URL,'definicao_cid':ID_DEFINICAO_CID})

def hash_frame(df):
    df=df.copy()
    if 'dt_obito' in df:df['dt_obito']=pd.to_datetime(df.dt_obito).dt.strftime('%Y-%m-%d')
    if 'populacao' in df:df['populacao']=df.populacao.astype(float)
    df=df.sort_values(list(df.columns)).reset_index(drop=True)
    return hashlib.sha256(df.to_csv(index=False,lineterminator='\n').encode()).hexdigest()

def estado(con,dataset,ano):
    row=con.execute('SELECT atualizado,ciclo,assinatura,linhas,soma,detalhes FROM estado WHERE dataset=? AND ano=?',(dataset,ano)).fetchone()
    if row is None:return None
    st=dict(zip(['atualizado','ciclo','assinatura','linhas','soma','detalhes'],row))
    table='f_obitos' if dataset=='sim' else 'populacao_fonte'
    df=pd.read_sql_query(f'SELECT * FROM {table} WHERE ano=?',con,params=(ano,))
    if len(df)!=st['linhas'] or hash_frame(df)!=json.loads(st['detalhes']).get('dados_sha256'):
        return None  # checkpoint sem conteúdo íntegro não permite pular a extração
    return st

def precisa_atualizar(st,ano,hoje,assinatura,forcar=False):
    if forcar or st is None or st['assinatura']!=assinatura: return True
    if ano >= hoje.year-JANELA_REVISAO+1: return st['ciclo'] != ciclo_mensal(hoje)
    # Anos antigos também podem ser retificados: revisão anual, sem recarga mensal completa.
    return (hoje-date.fromisoformat(st['atualizado'][:10])).days >= 365

@contextmanager
def trava(raiz):
    # Não apagar automaticamente trava de execução interrompida: conferir processo antes de removê-la.
    path=raiz/'execucao.lock'
    fd=os.open(path,os.O_CREAT|os.O_EXCL|os.O_WRONLY)
    try:
        os.write(fd,json.dumps({'pid':os.getpid(),'inicio':utc()}).encode());os.close(fd)
        yield
    finally: path.unlink(missing_ok=True)

def validar_fato(df,ano,municipios,meses):
    if list(df.columns)!=COLUNAS: raise ValueError('Esquema da fato divergente')
    if df.isna().any().any() or df.duplicated(CHAVE).any(): raise ValueError('Nulos/duplicações na fato')
    expected=len(municipios)*len(meses)*len(CAUSAS)*len(FAIXAS)*len(SEXOS)
    if len(df)!=expected or not df.ano.eq(ano).all(): raise ValueError('Grade/ano divergente')
    for c,dom in [('cod_mun_res',municipios),('mes',meses),('tipo_causa',CAUSAS),('faixa_etaria',FAIXAS),('sexo',SEXOS)]:
        if set(df[c])!=set(dom): raise ValueError('Domínio inválido: '+c)
    d=pd.to_datetime(df.dt_obito,errors='raise');v=pd.to_numeric(df.Obitos,errors='raise')
    if not ((d.dt.day==1)&(d.dt.month==df.mes)&(d.dt.year==df.ano)).all(): raise ValueError('Data inválida')
    if not (np.isfinite(v)&(v>=0)&(v%1==0)).all(): raise ValueError('Contagem inválida')

class ExtracaoIncremental(Extraction):
    def extract_partial(self,limite_mes):
        c=self.contract;controls={};coberturas=[]
        for causa in CAUSAS:
            mat,stats=self.run_query(causa,tag='controle_inicio',fresh=True)
            controls[causa]=mat
            coberturas.append(set(stats['months']))
        # Exige meses explícitos e contíguos nos dois controles. Ausência de coluna não vira zero.
        comuns=set.intersection(*coberturas)&set(range(1,limite_mes+1))
        if not comuns: raise ValueError('Nenhum mês fechado confirmado nos controles')
        meses=list(range(1,max(comuns)+1))
        if set(meses)!=comuns: raise ValueError('Lacuna na cobertura mensal da fonte')
        if c['year']<HOJE.year and meses!=list(range(1,13)):
            raise ValueError('Ano histórico sem os 12 meses explícitos; requer conferência')
        # Controle de equivalência: as subcategorias das categorias completas devem somar o mesmo
        # que as categorias de três dígitos. Diferença indica óbito sem subcategoria registrada,
        # que a seleção por subcategorias deixaria fora do numerador.
        for causa in CAUSAS:
            eq=c['cid_equivalencia'][causa]
            sub,_=self.run_query(causa,tag='equivalencia_subcategorias',fresh=True,cid=(CID_FIELD,eq['subcategorias']))
            cat,_=self.run_query(causa,tag='equivalencia_categorias',fresh=True,cid=(CID3_FIELD,eq['categorias']))
            if not sub[meses].equals(cat[meses]):
                raise ValueError(f'{causa}: subcategorias e categorias de três dígitos divergem em {c["year"]}; '
                                 'há óbitos sem subcategoria que ficariam fora do numerador.')
        pieces=[]
        for i,(causa,idade,sexo) in enumerate(product(CAUSAS,FAIXAS,SEXOS),1):
            # Todo ano devido é relido integralmente; cache serve como evidência, nunca congela revisões.
            mat,stats=self.run_query(causa,idade,sexo,fresh=True)
            frame=mat[meses].rename_axis(columns='mes').stack().rename('Obitos').reset_index()
            frame['ano']=c['year'];frame['dt_obito']=pd.to_datetime(dict(year=frame.ano,month=frame.mes,day=1))
            frame['tipo_causa']=causa;frame['faixa_etaria']=idade;frame['sexo']=sexo
            pieces.append(frame[COLUNAS]);print(f"{c['year']} | {i}/72 | {causa} | {idade} | {sexo}",flush=True)
        fact=pd.concat(pieces,ignore_index=True)
        validar_fato(fact,c['year'],c['municipalities'],meses)
        for causa in CAUSAS:
            after,stats=self.run_query(causa,tag='controle_fim',fresh=True)
            pd.testing.assert_frame_equal(controls[causa],after,obj='Fonte mudou durante extração')
            total=fact[fact.tipo_causa==causa].groupby(['cod_mun_res','mes']).Obitos.sum().unstack()
            pd.testing.assert_frame_equal(total.reindex(index=after.index,columns=meses),after[meses],check_names=False)
        return fact,{'meses':meses,'revisao':c['revision'],'contrato':c['fingerprint'],
                     'fonte':URL,'status_fonte':'sujeito_a_revisao',
                     'cobertura':'meses presentes no retorno; não certifica completude epidemiológica',
                     'evidencias':str(self.directory),'consultas':80,
                     'definicao_cid':ID_DEFINICAO_CID,'codigos_cid':DESCRICAO_CID}

def gravar_ano(con,dataset,ano,df,assinatura,detalhes,hoje):
    tabelas={'sim':('f_obitos',COLUNAS,'Obitos'),'pop':('populacao_fonte',POPKEY+['populacao'],'populacao')}
    tabela,cols,valor=tabelas[dataset]
    frame=df[cols].copy()
    if dataset=='sim':frame['dt_obito']=pd.to_datetime(frame.dt_obito).dt.strftime('%Y-%m-%d')
    records=list(frame.itertuples(index=False,name=None))
    detalhes={**detalhes,"dados_sha256":hash_frame(frame)}
    # DELETE + INSERT + checkpoint pertencem à mesma transação. Erro reverte tudo.
    with con:
        con.execute(f'DELETE FROM {tabela} WHERE ano=?',(ano,))
        con.executemany(f'INSERT INTO {tabela} ({",".join(cols)}) VALUES ({",".join("?" for _ in cols)})',records)
        con.execute('INSERT OR REPLACE INTO estado VALUES (?,?,?,?,?,?,?,?)',
            (dataset,ano,utc(),ciclo_mensal(hoje),assinatura,len(frame),float(frame[valor].sum()),json.dumps(detalhes,ensure_ascii=False)))

def geografia(raiz,hoje):
    import geopandas as gpd
    pasta=raiz/'geografia';pasta.mkdir(exist_ok=True)
    meta_path=pasta/'meta.json';csv=pasta/'d_geografica.csv'
    if meta_path.exists() and csv.exists():
        m=json.loads(meta_path.read_text())
        if m['ciclo']==ciclo_mensal(hoje) and hashlib.sha256(csv.read_bytes()).hexdigest()==m['sha256']:
            return pd.read_csv(csv,dtype={'cod_mun_res':str}),m
    # Usa a edição mais recente publicada entre o ano corrente e 2020.
    for ano in range(hoje.year,2019,-1):
        url=f'https://geoftp.ibge.gov.br/organizacao_do_territorio/malhas_territoriais/malhas_municipais/municipio_{ano}/UFs/ES/ES_Municipios_{ano}.zip'
        r=requests.get(url,timeout=(20,180))
        if r.status_code==404:continue
        r.raise_for_status()
        with tempfile.TemporaryDirectory() as tmp:
            z=Path(tmp)/'malha.zip';z.write_bytes(r.content)
            g=gpd.read_file('zip://'+str(z)).to_crs(4326)
        required=['CD_MUN','NM_MUN','SIGLA_UF','NM_UF','NM_REGIAO']
        if not set(required)<=set(g.columns):raise ValueError('Esquema da malha mudou')
        g=g[g.SIGLA_UF.eq('ES')].copy();g['cod_mun_res']=g.CD_MUN.astype(str).str[:6]
        if len(g)!=78 or not g.cod_mun_res.is_unique:raise ValueError('Municípios divergentes; revisar série histórica')
        if g.geometry.isna().any() or g.geometry.is_empty.any() or not g.geometry.is_valid.all():raise ValueError('Geometria inválida')
        point=g.to_crs(31984).representative_point().to_crs(4326)
        geo=g.rename(columns={'NM_MUN':'no_municipio','SIGLA_UF':'sg_uf','NM_UF':'no_uf','NM_REGIAO':'no_regiao'})
        geo['latitude']=point.y;geo['longitude']=point.x
        geo=geo[['cod_mun_res','no_municipio','sg_uf','no_uf','no_regiao','latitude','longitude']].sort_values('cod_mun_res')
        region=raiz/'regioes_saude.csv'
        if region.exists():
            reg=pd.read_csv(region,dtype=str)
            if set(reg.columns)!={'cod_mun_res','regiao_saude'} or reg.isna().any().any() or not reg.cod_mun_res.is_unique or set(reg.cod_mun_res)!=set(geo.cod_mun_res):
                raise ValueError('Mapeamento de regiões deve cobrir cada município exatamente uma vez')
            geo=geo.merge(reg,on='cod_mun_res',validate='one_to_one')
        geo.to_csv(csv.with_suffix('.tmp'),index=False,encoding='utf-8-sig');csv.with_suffix('.tmp').replace(csv)
        # GeoJSON é opcional para o mapa; nenhuma simplificação de polígonos.
        (pasta/f'malha_{ano}.geojson').write_text(g[['cod_mun_res','geometry']].to_json(),encoding='utf-8')
        m={'ano_malha':ano,'url':url,'ciclo':ciclo_mensal(hoje),'sha256':hashlib.sha256(csv.read_bytes()).hexdigest()}
        write_json(meta_path,m);return geo,m
    raise RuntimeError('Malha municipal não encontrada entre 2020 e ano atual')

def catalogo_pop():
    # Falha de conexão/listagem NÃO equivale a ano inexistente.
    with FTP('ftp.datasus.gov.br',timeout=90) as ftp:
        ftp.login();ftp.cwd('dissemin/publicos/IBGE/POPSVS');nomes=ftp.nlst()
    found={}
    for nome in nomes:
        base=nome.rsplit('/',1)[-1];m=re.fullmatch(r'POPSBR(\d{2})\.zip',base,re.I)
        if m:found[2000+int(m.group(1))]=base
    if not found:raise RuntimeError('Listagem POPSVS inesperada/vazia')
    return found

def ler_populacao_zip(path,ano,municipios):
    from dbfread import DBF
    with tempfile.TemporaryDirectory() as tmp:
        with zipfile.ZipFile(path) as z:
            names=[n for n in z.namelist() if n.lower().endswith('.dbf')]
            if len(names)!=1:raise ValueError('Esperado um DBF no ZIP POPSVS')
            db=Path(tmp)/'pop.dbf';db.write_bytes(z.read(names[0]))
        records=[]
        for row in DBF(str(db),encoding='latin-1'):
            r={str(k).strip().lower():v for k,v in row.items()}
            if not {'cod_mun','ano','sexo','idade','pop'}<=set(r):raise ValueError('Esquema POPSVS mudou')
            code=str(r['cod_mun']).strip().removesuffix('.0')
            if not re.fullmatch(r'\d{6,7}',code):raise ValueError('Código municipal inválido')
            code=code[:6]
            if not code.startswith('32'):continue
            if code not in municipios:raise ValueError('Município inesperado na população')
            if int(r['ano'])!=ano:raise ValueError('Ano interno do DBF diverge do arquivo')
            sx=str(r['sexo']).strip().removesuffix('.0');age=str(r['idade']).strip().removesuffix('.0')
            if sx not in ['1','2'] or not re.fullmatch(r'\d+',age):raise ValueError('Sexo/idade incompatível; não descartar silenciosamente')
            idade=int(age)
            if not 0<=idade<=80:raise ValueError('Esperada idade simples 0–79 e categoria 80+')
            val=float(r['pop'])
            if not np.isfinite(val) or val<0:raise ValueError('População inválida')
            faixa=next(f for limite,f in zip([4,9,14,19,29,39,49,59,69,79,80],FAIXAS[:-1]) if idade<=limite)
            records.append((code,ano,idade,faixa,SEXOS[int(sx)-1],val))
    df=pd.DataFrame(records,columns=['cod_mun_res','ano','idade','faixa_etaria','sexo','populacao'])
    if df.duplicated(['cod_mun_res','ano','idade','sexo']).any():raise ValueError('População duplicada na origem')
    if len(df)!=len(municipios)*81*2:raise ValueError('Grade de idades simples incompleta')
    pop=df.groupby(POPKEY,as_index=False).populacao.sum();validar_pop(pop,ano,municipios);return pop

def validar_pop(df,ano,municipios):
    if df.empty or df.isna().any().any() or df.duplicated(POPKEY).any():raise ValueError('População ausente/inválida')
    if len(df)!=len(municipios)*11*2 or not df.ano.eq(ano).all():raise ValueError('Grade populacional inválida')
    for col,values in [('cod_mun_res',municipios),('faixa_etaria',FAIXAS[:-1]),('sexo',SEXOS[:2])]:
        if set(df[col])!=set(values):raise ValueError('Domínio populacional inválido: '+col)
    if not (np.isfinite(df.populacao)&df.populacao.ge(0)).all() or df.populacao.sum()<=0:raise ValueError('Valores populacionais inválidos')

def baixar_pop(ano,nome,raiz,municipios):
    pasta=raiz/'populacao_bruta';pasta.mkdir(exist_ok=True)
    path=pasta/(uuid.uuid4().hex+'_'+nome);temp=path.with_suffix('.part')
    with FTP('ftp.datasus.gov.br',timeout=90) as ftp:
        ftp.login();ftp.cwd('dissemin/publicos/IBGE/POPSVS')
        with temp.open('wb') as f:ftp.retrbinary('RETR '+nome,f.write)
    temp.replace(path)
    pop=ler_populacao_zip(path,ano,municipios)
    return pop,{'fonte':'ftp://ftp.datasus.gov.br/dissemin/publicos/IBGE/POPSVS/'+nome,
                'sha256':hashlib.sha256(path.read_bytes()).hexdigest(),'arquivo':str(path),'ano_fonte':ano}

def resolver_populacao(con,anos,catalogo,municipios,permitir=True):
    partes=[]
    for ano in anos:
        fonte=ano
        if ano not in catalogo:
            if not permitir or ano-1 not in catalogo:raise ValueError(f'Sem população compatível para {ano}; tolerância máxima de um ano')
            fonte=ano-1
        df=pd.read_sql_query('SELECT * FROM populacao_fonte WHERE ano=?',con,params=(fonte,))
        validar_pop(df,fonte,municipios)
        df['ano_fonte_populacao']=fonte;df['ano']=ano
        df['denominador_provisorio']=int(fonte!=ano)
        df['metodo_denominador']='ano_correspondente' if fonte==ano else 'carregamento_ano_anterior_sem_projecao'
        partes.append(df)
    return pd.concat(partes,ignore_index=True)

def dimensoes(geo,pop,inicio,fim,hoje):
    t=pd.DataFrame({'dt_obito':pd.date_range(f'{inicio}-01-01',f'{fim}-12-01',freq='MS')})
    t['ano']=t.dt_obito.dt.year;t['mes']=t.dt_obito.dt.month
    t['mes_nome']=t.mes.map(dict(enumerate(['Janeiro','Fevereiro','Março','Abril','Maio','Junho','Julho','Agosto','Setembro','Outubro','Novembro','Dezembro'],1)))
    t['mes_ano']=t.mes_nome.str[:3]+'/'+t.ano.astype(str);t['ordem_mes_ano']=t.ano*100+t.mes
    t['quadrimestre']=(t.mes-1)//4+1;t['quadrimestre_nome']=t.quadrimestre.astype(str)+'º Quadrimestre'
    t['ano_quadrimestre']=t.ano.astype(str)+' - Q'+t.quadrimestre.astype(str)
    t['ordem_ano_quadrimestre']=t.ano*10+t.quadrimestre
    t['mes_encerrado']=(t.dt_obito<pd.Timestamp(hoje.year,hoje.month,1)).astype(int)
    t['dt_obito']=t.dt_obito.dt.strftime('%Y-%m-%d')
    return {'d_geografica':geo,'d_populacao':pop,'d_tempo':t,
      'd_ano':pd.DataFrame({'ano':range(inicio,fim+1)}),
      'd_sexo':pd.DataFrame({'sexo':SEXOS,'ordem_sexo':range(1,4)}),
      'd_faixa_etaria':pd.DataFrame({'faixa_etaria':FAIXAS,'ordem_faixa_etaria':range(1,13)}),
      'd_causa':pd.DataFrame({'tipo_causa':CAUSAS,'cid10':[DESCRICAO_CID[c] for c in CAUSAS]}),
      'd_indicador':pd.DataFrame({'indicador':['Homicídio 15 a 29 anos','Homicídio mulheres 10 a 59 anos','Suicídio Geral'],
         'tipo_causa':['Homicídio','Homicídio','Suicídio'],'idade_min':[15,10,0],'idade_max':[29,59,None],
         'sexo_alvo':['Todos','Feminino','Todos']})}

def persistir_dimensoes(con,tabelas):
    with con:
        con.execute('BEGIN IMMEDIATE')
        for name,df in tabelas.items():
            # Nomes vêm apenas do dicionário interno dimensoes(), nunca de entrada livre.
            types={c:('INTEGER' if pd.api.types.is_integer_dtype(df[c]) else 'REAL' if pd.api.types.is_numeric_dtype(df[c]) else 'TEXT') for c in df.columns}
            con.execute(f'DROP TABLE IF EXISTS "{name}"')
            fields=','.join(f'"{c}" {t}' for c,t in types.items())
            con.execute(f'CREATE TABLE "{name}" ({fields})')
            values=df.astype(object).where(pd.notna(df),None)
            con.executemany(f'INSERT INTO "{name}" VALUES ({",".join("?" for _ in df.columns)})',values.itertuples(index=False,name=None))

def exportar(con,raiz,tabelas,relatorio):
    # Lote imutável + ponteiro único. Uma falha não publica metade dos CSVs.
    dest=raiz/'exportacoes'/relatorio['id'];dest.mkdir(parents=True,exist_ok=False)
    tabelas={**tabelas,'f_obitos':pd.read_sql_query('SELECT * FROM f_obitos WHERE ano BETWEEN ? AND ? ORDER BY ano,mes,cod_mun_res,tipo_causa,faixa_etaria,sexo',con,params=(ANO_INICIAL,ANO_FINAL)),
             'controle_cargas':pd.read_sql_query('SELECT * FROM estado',con)}
    manifest={'id':relatorio['id'],'gerado':utc(),'status':relatorio['status'],'arquivos':{}}
    for name,df in tabelas.items():
        p=dest/(name+'.csv');df.to_csv(p,index=False,encoding='utf-8-sig')
        manifest['arquivos'][name]={'linhas':len(df),'sha256':hashlib.sha256(p.read_bytes()).hexdigest()}
    write_json(dest/'manifesto.json',manifest);write_json(dest/'relatorio_execucao.json',relatorio)
    write_json(raiz/'exportacao_atual.json',{'pasta':str(dest.resolve()),'id':relatorio['id'],'status':relatorio['status']})
    return dest

def executar():
    raiz=RAIZ.expanduser().resolve();raiz.mkdir(parents=True,exist_ok=True)
    with trava(raiz):
        con=sqlite3.connect(raiz/'tcc.sqlite',timeout=60);con.executescript(SCHEMA)
        run={'id':datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S')+'_'+uuid.uuid4().hex[:8],
             'inicio':utc(),'status':'executando','acoes':[],'erros':[],
             'python':sys.version,'plataforma':platform.platform(),'versao':VERSAO}
        con.execute('INSERT INTO execucoes VALUES (?,?,?,?,?)',(run['id'],run['inicio'],None,'executando','{}'));con.commit()
        client=None
        try:
            geo,geometa=geografia(raiz,HOJE);municipios=sorted(geo.cod_mun_res.tolist())
            sig=assinatura_config(municipios)
            cat=catalogo_pop();run['anos_pop_fonte']=sorted(cat);run['geografia']=geometa
            # Atualiza população antes do SIM; arquivo recém-publicado substitui aproximação na exportação.
            needed=set()
            for ano in range(ANO_INICIAL,ANO_FINAL+1):
                fonte=ano if ano in cat else ano-1
                if fonte not in cat or (fonte!=ano and not PERMITIR_POP_ANTERIOR):raise ValueError(f'Sem fonte de população para {ano}')
                needed.add(fonte)
            for ano in sorted(needed):
                st=estado(con,'pop',ano)
                if precisa_atualizar(st,ano,HOJE,sig,ano in ANOS_FORCADOS):
                    pop,meta=baixar_pop(ano,cat[ano],raiz,municipios)
                    gravar_ano(con,'pop',ano,pop,sig,meta,HOJE);run['acoes'].append(f'pop {ano}: atualizado')
                else:run['acoes'].append(f'pop {ano}: preservado')
            client=TabnetClient(MOTOR)
            disponiveis={int(o['label'].strip()) for o in client.form['options']['Arquivos'] if re.fullmatch(r'\d{4}',o['label'].strip())}
            run['anos_sim_disponiveis']=sorted(disponiveis)
            for ano in range(ANO_INICIAL,ANO_FINAL+1):
                try:
                    if ano == HOJE.year and HOJE.month == 1:
                        run['acoes'].append(f'SIM {ano}: sem mês encerrado');continue
                    if ano not in disponiveis:
                        run['erros'].append(f'SIM {ano}: ano não anunciado pela fonte; nenhum zero criado');continue
                    limite=HOJE.month-1 if ano==HOJE.year else 12
                    if limite==0:run['acoes'].append(f'SIM {ano}: sem mês encerrado');continue
                    contract=make_contract(client.form,ano,municipios)
                    # Mudança estrutural invalida checkpoint; a revisão global é registrada, mas não recarrega todo o histórico a cada mês.
                    estrutura={k:v for k,v in contract.items() if k not in ['fingerprint','revision']}
                    ano_sig=digest({'config':sig,'contrato':estrutura})
                    st=estado(con,'sim',ano)
                    if not precisa_atualizar(st,ano,HOJE,ano_sig,ano in ANOS_FORCADOS):
                        run['acoes'].append(f'SIM {ano}: preservado');continue
                    ex=ExtracaoIncremental(client,contract,raiz/'evidencias'/run['id'],INTERVALO_SEGUNDOS)
                    fact,meta=ex.extract_partial(limite)
                    if st and max(meta['meses'])<max(json.loads(st['detalhes'])['meses']):raise ValueError('Cobertura regrediu; preservado lote anterior')
                    gravar_ano(con,'sim',ano,fact,ano_sig,meta,HOJE);run['acoes'].append(f'SIM {ano}: atualizado')
                except Exception as exc:
                    run['erros'].append(f'SIM {ano}: {type(exc).__name__}: {exc}')
            pop=resolver_populacao(con,list(range(ANO_INICIAL,ANO_FINAL+1)),cat,municipios,PERMITIR_POP_ANTERIOR)
            run['status']='parcial' if run['erros'] else 'concluido';run['fim']=utc()
            tables=dimensoes(geo,pop,ANO_INICIAL,ANO_FINAL,HOJE)
            persistir_dimensoes(con,tables)
            dest=exportar(con,raiz,tables,run)
            run['exportacao']=str(dest);print(json.dumps(run,ensure_ascii=False,indent=2))
        except Exception as exc:
            run['status']='falhou';run['erros'].append(f'{type(exc).__name__}: {exc}');raise
        finally:
            if client is not None:client.close()
            run['fim']=utc();write_json(raiz/'ultima_execucao.json',run)
            with con:con.execute('UPDATE execucoes SET fim=?,status=?,detalhes=? WHERE id=?',(run['fim'],run['status'],json.dumps(run,ensure_ascii=False),run['id']))
            con.close()
        if run['erros']:raise RuntimeError('Execução parcial. Consulte ultima_execucao.json; lotes anteriores preservados para os anos que falharam.')
        return run
