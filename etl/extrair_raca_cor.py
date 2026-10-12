import os
from configuracao import DADOS, ESTADO
"""Extração auditável por indicador, município, mês, sexo e raça/cor; retomável por revisão."""
from pathlib import Path
import sys,json,time,hashlib,sqlite3,argparse
from datetime import datetime,timezone
import pandas as pd
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from modelo import INDICADORES,carregar,recortar
from .definicao_cid import DEFINICAO_LEGADA,ID_DEFINICAO_CID,resumo_definicao

def normalizar_grade(tabela,f,g):
    partes=[]
    categorias=['Branca','Preta','Amarela','Parda','Indígena','Não informado','Ignorado','Sem classificação disponível na tabulação']
    chave=['indicador','cod_mun_res','ano','mes','sexo','raca_cor']
    for ano in sorted(tabela.ano.unique()):
        meses=sorted(f.loc[f.ano.eq(ano),'mes'].unique())
        assert meses, 'Atualize a fato principal antes de incorporar um novo ano'
        assert set(tabela.loc[tabela.ano.eq(ano),'mes']).issubset(meses), 'Há meses novos na fonte; atualize a fato principal'
        for indicador,cfg in INDICADORES.items():
            sexos=[cfg['sexo']] if cfg['sexo'] else ['Masculino','Feminino','Ignorado']
            grade=pd.MultiIndex.from_product([[indicador],sorted(g.cod_mun_res),[ano],meses,sexos,categorias],names=chave)
            atual=tabela[tabela.ano.eq(ano)&tabela.indicador.eq(indicador)].set_index(chave)
            assert not atual.index.duplicated().any()
            assert set(atual.index).issubset(set(grade))
            partes.append(atual.reindex(grade,fill_value=0).reset_index())
    return pd.concat(partes,ignore_index=True)

def executar(anos=None,forcar=False):
    anos=list(anos if anos is not None else range(2016,datetime.now().year+1))
    from . import nucleo_tabnet
    ns=vars(nucleo_tabnet)
    client=ns['TabnetClient'](os.environ.get('TCC_TABNET_MOTOR','requests'))
    f,p,g,meta=carregar(); codigos=sorted(g.cod_mun_res)
    racas=[o for o in client.form['options']['SRaça/Cor'] if o['value']!=ns['ALL']]
    assert len(racas)==7, 'Rever categorias de raça/cor'
    saida=ESTADO/'raca_cor';saida.mkdir(parents=True,exist_ok=True)
    lotes=[];auditoria=[]
    arquivo_final=DADOS/'f_raca_cor.csv.gz'
    meta_final=DADOS/'raca_cor_meta.json'
    if arquivo_final.exists():
        previo=pd.read_csv(arquivo_final,dtype={'cod_mun_res':str})
        lotes.append(previo[~previo.ano.isin(anos)])
        if meta_final.exists(): auditoria=[a for a in json.loads(meta_final.read_text())['auditoria'] if a['ano'] not in anos]
    definicoes_anteriores=json.loads(meta_final.read_text()).get('definicao_cid_por_ano',{}) if meta_final.exists() else {}
    try:
        for ano in anos:
            c=ns['make_contract'](client.form,ano,codigos)
            pasta=saida/f"{ano}_{c['fingerprint'][:12]}";pasta.mkdir(parents=True,exist_ok=True)
            ns['write_json'](pasta/'contrato.json',c)
            (pasta/'formulario.html').write_text(client.html)
            linhas=[]
            def consultar(selections,fresh=False):
                key=ns['digest'](selections); html=pasta/(key+'.html'); audit=pasta/(key+'.json')
                cache_mes_atual=audit.exists() and json.loads(audit.read_text()).get('extraido_utc','').startswith(datetime.now(timezone.utc).strftime('%Y-%m'))
                if forcar or fresh or not html.exists() or not cache_mes_atual:
                    for tentativa in range(3):
                        try:
                            time.sleep(float(os.environ.get('TCC_INTERVALO_SEGUNDOS','3')))
                            raw=client.query(selections).replace('\r\n','\n').replace('\r','\n')
                            (pasta/(key+'_resposta.html')).write_text(raw)
                            mat,stats=ns['parse_result'](raw,ano,codigos)
                            html.write_text(raw)
                            ns['write_json'](audit,{'extraido_utc':datetime.now(timezone.utc).isoformat(),'selections':selections,'stats':stats,'sha256':hashlib.sha256(raw.encode()).hexdigest()})
                            break
                        except Exception:
                            if tentativa==2: raise
                raw=html.read_text();a=json.loads(audit.read_text())
                assert hashlib.sha256(raw.encode()).hexdigest()==a['sha256']
                return ns['parse_result'](raw,ano,codigos)
            for indicador,cfg in INDICADORES.items():
                for sexo in ([cfg['sexo']] if cfg['sexo'] else ns['SEXOS']):
                    sel=dict(c['base']);sel[ns['CID_FIELD']]=c['cids'][cfg['causa']]
                    sel[ns['AGE_FIELD']]=sum([c['ages'][a] for a in cfg['idades']],[]) if cfg['idades'] else [ns['ALL']]
                    sel['SSexo']=c['sexes'][sexo];sel['SRaça/Cor']=[ns['ALL']]
                    controle,stats=consultar(sel,fresh=True)
                    soma=controle*0
                    for r in racas:
                        sm=dict(sel);sm['SRaça/Cor']=[r['value']]
                        matriz,st=consultar(sm);soma+=matriz
                        for mun in codigos:
                            for mes in stats['months']:
                                linhas.append({'indicador':indicador,'cod_mun_res':mun,'ano':ano,'mes':mes,'sexo':sexo,'raca_cor':r['label'],'Obitos':int(matriz.loc[mun,mes])})
                    fim,_=consultar(sel,fresh=True)
                    assert controle.equals(fim),'Fonte mudou durante extração; reexecute com nova revisão'
                    residuo=controle-soma
                    assert (residuo.to_numpy()>=0).all(),f'Categorias sobrepostas: {ano} {indicador} {sexo}'
                    for mun in codigos:
                        for mes in stats['months']:
                            linhas.append({'indicador':indicador,'cod_mun_res':mun,'ano':ano,'mes':mes,'sexo':sexo,'raca_cor':'Sem classificação disponível na tabulação','Obitos':int(residuo.loc[mun,mes])})
                    assert (soma+residuo).equals(controle)
                    antigo,_=recortar(f,p,indicador,codigos)
                    antigo=antigo[(antigo.ano==ano)&(antigo.sexo==sexo)].groupby(['cod_mun_res','mes']).Obitos.sum()
                    atual=controle.rename_axis('mes',axis=1).stack()
                    diferencas=(atual-antigo.reindex(atual.index,fill_value=0)).loc[lambda s:s.ne(0)]
                    auditoria.append({'ano':ano,'indicador':indicador,'sexo':sexo,'total':int(controle.to_numpy().sum()),'total_categorias_fonte':int(soma.to_numpy().sum()),'sem_classificacao_tabulacao':int(residuo.to_numpy().sum()),'meses':stats['months'],'celulas_divergentes_base_anterior':len(diferencas),'diferenca_obitos':int(diferencas.sum()),'revisao':c['revision']})
                    print(ano,indicador,sexo,'OK',int(controle.to_numpy().sum()),'divergências',len(diferencas),flush=True)
            lote=normalizar_grade(pd.DataFrame(linhas),f,g)
            lote.to_csv(pasta/'f_raca_cor.csv.gz',index=False)
            lotes.append(lote)
            ns['write_json'](saida/'auditoria.json',auditoria)
        final=pd.concat(lotes,ignore_index=True)
        chave=['indicador','cod_mun_res','ano','mes','sexo','raca_cor']
        assert not final.duplicated(chave).any()
        temp=DADOS/'f_raca_cor.tmp.gz';final.to_csv(temp,index=False);temp.replace(DADOS/'f_raca_cor.csv.gz')
        with sqlite3.connect(saida/'raca_cor.sqlite') as con:
            final.to_sql('f_raca_cor',con,if_exists='replace',index=False)
            pd.DataFrame(racas+[{'value':'residual_calculado','label':'Sem classificação disponível na tabulação'}]).rename(columns={'value':'codigo','label':'raca_cor'}).to_sql('d_raca_cor',con,if_exists='replace',index=False)
        definicoes={str(int(a)):(ID_DEFINICAO_CID if int(a) in anos else definicoes_anteriores.get(str(int(a)),DEFINICAO_LEGADA)) for a in final.ano.unique()}
        ns['write_json'](DADOS/'raca_cor_meta.json',{'definicao_cid':resumo_definicao(),'definicao_cid_por_ano':definicoes,'cobertura':{str(int(a)):sorted(int(m) for m in final.loc[final.ano.eq(a),'mes'].unique()) for a in final.ano.unique()},'fonte':ns['URL'],'extraido_utc':datetime.now(timezone.utc).isoformat(),'anos':sorted(final.ano.unique().tolist()),'auditoria':auditoria,'grao':chave,'nota':'Frequências de óbitos; sem população por raça/cor. Sem classificação disponível na tabulação é a diferença não negativa entre o total sem filtro racial e a soma das sete categorias da fonte; não se atribui raça aos registros residuais. Indicadores podem se sobrepor.'})
        print('CONCLUÍDO',len(final),flush=True)
    finally: client.close()

def integrar_banco(raiz):
    """Acrescenta tabelas complementares ao banco do pipeline após validação."""
    import shutil
    raiz=Path(raiz)
    fato=pd.read_csv(DADOS/'f_raca_cor.csv.gz',dtype={'cod_mun_res':str})
    with sqlite3.connect(ESTADO/'raca_cor/raca_cor.sqlite') as origem:
        dimensao=pd.read_sql_query('SELECT * FROM d_raca_cor',origem)
    regioes=pd.read_csv(DADOS/'regioes_pdr2024.csv',dtype={'cod_mun_res':str})
    assert not fato.duplicated(['indicador','cod_mun_res','ano','mes','sexo','raca_cor']).any()
    with sqlite3.connect(raiz/'tcc.sqlite') as con:
        fato.to_sql('f_indicador_raca_cor',con,if_exists='replace',index=False)
        dimensao.to_sql('d_raca_cor',con,if_exists='replace',index=False)
        regioes.to_sql('d_regiao_saude_municipio',con,if_exists='replace',index=False)
        con.execute('CREATE UNIQUE INDEX uq_raca_cor ON f_indicador_raca_cor(indicador,cod_mun_res,ano,mes,sexo,raca_cor)')
        con.execute('CREATE UNIQUE INDEX uq_regiao_municipio ON d_regiao_saude_municipio(cod_mun_res)')
    destino=raiz/'complementos';destino.mkdir(exist_ok=True)
    dimensao.to_csv(destino/'d_raca_cor.csv',index=False)
    for nome in ['f_raca_cor.csv.gz','raca_cor_meta.json','regioes_pdr2024.csv','pdr_meta.json']:
        shutil.copy2(DADOS/nome,destino/nome)

if __name__=='__main__':
    ap=argparse.ArgumentParser();ap.add_argument('--inicio',type=int,default=2016);ap.add_argument('--fim',type=int,default=datetime.now().year);ap.add_argument('--forcar',action='store_true');args=ap.parse_args()
    executar(range(args.inicio,args.fim+1),forcar=args.forcar)
