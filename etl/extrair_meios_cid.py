import os
from configuracao import DADOS, ESTADO
"""CID-10 por indicador, município, mês e sexo, com controles e cache por revisão."""
from pathlib import Path
import sys,re,json,time,argparse,hashlib
from datetime import datetime,timezone
import pandas as pd
from bs4 import BeautifulSoup
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from modelo import carregar,recortar,INDICADORES
from .nucleo_tabnet import TabnetClient,query_definicao,partes_consulta,make_contract,exact_value,parse_result,count_value,norm,digest,write_json,CID_FIELD,CID3_FIELD,AGE_FIELD,MONTHS,ALL,URL
from .definicao_cid import DEFINICAO_CID,ID_DEFINICAO_CID,LINHA_CATEGORIA,codigos_detalhamento,descricoes_codigos,resumo_definicao

def grupo(cid):
    """Agrupamento analítico do meio registrado; não altera o numerador dos indicadores."""
    if cid in ['Y87.0','Y87.1','Y89.0']:return 'Sequelas (meio não especificado)'
    if cid in ['Y22','Y23','Y24']:return 'Arma de fogo'
    if cid=='Y35':return 'Intervenção legal'
    n=int(cid[1:])
    if cid[0]=='X' and 60<=n<=69 or cid[0]=='X' and 85<=n<=90:return 'Intoxicação e exposição a substâncias'
    if cid in ['X70','X91']:return 'Enforcamento, estrangulamento e sufocação'
    if cid in ['X71','X92']:return 'Afogamento e submersão'
    if cid in ['X72','X73','X74','X93','X94','X95']:return 'Arma de fogo'
    if cid in ['X75','X96']:return 'Explosivos'
    if cid in ['X76','X97']:return 'Fumaça, fogo e chamas'
    if cid in ['X77','X98']:return 'Vapor, gases ou objetos quentes'
    if cid in ['X78','X99']:return 'Objeto cortante ou penetrante'
    if cid in ['X79','Y00']:return 'Objeto contundente'
    if cid in ['X80','Y01']:return 'Precipitação de lugar elevado'
    if cid in ['X81','Y02']:return 'Objeto em movimento'
    if cid in ['X82','Y03']:return 'Impacto de veículo a motor'
    if cid=='Y04':return 'Força corporal'
    if cid=='Y05':return 'Agressão sexual por força física'
    if cid=='Y06':return 'Negligência e abandono'
    if cid=='Y07':return 'Outras síndromes de maus-tratos'
    if cid in ['X83','Y08']:return 'Outros meios especificados'
    if cid in ['X84','Y09']:return 'Meio não especificado'
    raise ValueError('CID não mapeado: '+cid)

def parse_cids(raw,ano,linha):
    """Lê a tabulação categoria (3 caracteres) x mês. `linha` traduz o rótulo da categoria no
    código do detalhamento: 'X85'->'X85'; 'Y87'->'Y87.1' quando só essa subcategoria foi selecionada."""
    parts=partes_consulta(raw)
    if parts is not None:
        parsed=[parse_cids(p['html'],ano,linha) for p in parts]
        return sum((m for m,_ in parsed),parsed[0][0]*0),sorted(set().union(*(months for _,months in parsed)))
    cids=list(linha.values())
    soup=BeautifulSoup(raw,'lxml')
    assert re.search(r'periodo:\s*'+str(ano)+r'\b',norm(soup.get_text(' ',strip=True))), 'Ano divergente'
    tables=[]
    for table in soup.select('table'):
        rows=[[x.get_text(' ',strip=True) for x in tr.find_all(['th','td'],recursive=False)] for tr in table.select('tr')]
        if rows and rows[0] and norm(rows[0][0])=='causas 3 digitos':tables.append(rows)
    assert len(tables)==1,'Tabela CID ausente/ambígua'
    rows=tables[0];header=rows[0]
    assert norm(header[-1])=='total'
    months=[MONTHS.index(norm(x)[:3])+1 for x in header[1:-1]]
    assert len(set(months))==len(months)
    result=pd.DataFrame(0,index=cids,columns=range(1,13),dtype='int64');total=None;seen=set()
    for row in rows[1:]:
        assert len(row)==len(header),'Linha CID incompleta'
        vals=[count_value(x) for x in row[1:]]
        assert sum(vals[:-1])==vals[-1]
        if norm(row[0])=='total':
            assert total is None;total=vals;continue
        match=re.match(r'^([A-Z]\d{2})\b',row[0])
        assert match,'CID inesperado: '+row[0]
        categoria=match[1];assert categoria not in seen;seen.add(categoria)
        if categoria not in linha:assert vals[-1]==0
        else:result.loc[linha[categoria],months]=vals[:-1]
    assert total is not None and result[months].sum().tolist()==total[:-1]
    return result,months

def executar(anos,forcar=False):
    f,p,g,meta=carregar();mun=sorted(g.cod_mun_res);client=TabnetClient(os.environ.get('TCC_TABNET_MOTOR','requests'))
    folder=ESTADO/'meios_cid';folder.mkdir(parents=True,exist_ok=True)
    descricoes=descricoes_codigos(client.form['options'][CID_FIELD],client.form['options'][CID3_FIELD])
    codigos=[cid for causa in DEFINICAO_CID for cid in codigos_detalhamento(causa)]
    dim=[{'cid':cid,'descricao_cid':descricoes[cid],'meio':grupo(cid)} for cid in codigos]
    assert len(dim)==len(set(codigos))==57,'Dimensão de CIDs diverge da definição das fichas'
    out=DADOS/'f_meios_cid.csv.gz';mp=DADOS/'meios_cid_meta.json'
    final=pd.read_csv(out,dtype={'cod_mun_res':str}) if out.exists() else pd.DataFrame(columns=['indicador','cod_mun_res','ano','mes','sexo','cid','Obitos'])
    oldmeta=json.loads(mp.read_text()) if mp.exists() else {'auditoria':[],'cobertura':{}}
    try:
        for ano in anos:
            assert ano in meta['anos_disponiveis'],'Atualize a base principal antes de incluir um ano'
            c=make_contract(client.form,ano,mun);pasta=folder/f"{ano}_{c['fingerprint'][:12]}";pasta.mkdir(parents=True,exist_ok=True)
            write_json(pasta/'contrato.json',c);(pasta/'formulario.html').write_text(client.html)
            def query(sel,fresh=False):
                key=digest(sel);file=pasta/(key+'.html');audit=pasta/(key+'.json')
                cache=audit.exists() and json.loads(audit.read_text()).get('extraido_utc','').startswith(datetime.now(timezone.utc).strftime('%Y-%m'))
                if fresh or forcar or not file.exists() or not cache:
                    for attempt in range(3):
                        try:
                            time.sleep(float(os.environ.get('TCC_INTERVALO_SEGUNDOS','3')))
                            raw=query_definicao(client,sel).replace('\r\n','\n').replace('\r','\n')
                            if sel['Linha']==linha_cid:parse_cids(raw,ano,c['cid_linha'][cfg['causa']])
                            else:parse_result(raw,ano,mun)
                            file.write_text(raw);write_json(audit,{'extraido_utc':datetime.now(timezone.utc).isoformat(),'selections':sel,'sha256':hashlib.sha256(raw.encode()).hexdigest()});break
                        except Exception:
                            if attempt==2:raise
                raw=file.read_text();assert hashlib.sha256(raw.encode()).hexdigest()==json.loads(audit.read_text())['sha256'];return raw
            linha_cid=[exact_value(client.form['options']['Linha'],LINHA_CATEGORIA)]
            parts=[];audits=[];coverage=sorted(f.loc[f.ano.eq(ano),'mes'].unique().tolist())
            for indicador,cfg in INDICADORES.items():
                for sexo in ([cfg['sexo']] if cfg['sexo'] else ['Masculino','Feminino','Ignorado']):
                    sel=dict(c['base']);sel[CID_FIELD]=c['cids'][cfg['causa']];sel[AGE_FIELD]=sum([c['ages'][a] for a in cfg['idades']],[]) if cfg['idades'] else [ALL];sel['SSexo']=c['sexes'][sexo]
                    controle,stats=parse_result(query(sel,fresh=True),ano,mun)
                    assert set(stats['months']).issubset(coverage),'Há meses novos na fonte. Atualize a base principal.'
                    cs=dict(sel);cs['Linha']=linha_cid
                    cmat,months=parse_cids(query(cs),ano,c['cid_linha'][cfg['causa']])
                    assert (cmat.sum().to_numpy()==controle.sum().to_numpy()).all(),'Controle CID diverge do municipal'
                    soma=controle*0
                    for cid in cmat.index[cmat.sum(axis=1).gt(0)]:
                        s=dict(sel);s[CID_FIELD]=c['cid_values'][cfg['causa']][cid]
                        mat,_=parse_result(query(s),ano,mun)
                        assert (mat.sum().to_numpy()==cmat.loc[cid].to_numpy()).all(),'Total mensal por CID divergente'
                        soma+=mat
                        for mcode,mes in zip(*mat.to_numpy().nonzero()):
                            parts.append({'indicador':indicador,'cod_mun_res':mat.index[mcode],'ano':ano,'mes':mes+1,'sexo':sexo,'cid':cid,'Obitos':int(mat.iloc[mcode,mes])})
                    assert soma.equals(controle),'Soma CID não fecha no controle municipal mensal'
                    fim,_=parse_result(query(sel,fresh=True),ano,mun);assert controle.equals(fim),'Fonte alterou durante extração'
                    antigo,_=recortar(f,p,indicador,mun)
                    old=antigo[antigo.ano.eq(ano)&antigo.sexo.eq(sexo)].groupby(['cod_mun_res','mes']).Obitos.sum()
                    atual=controle.rename_axis('mes',axis=1).stack();delta=atual-old.reindex(atual.index,fill_value=0)
                    audits.append({'ano':ano,'indicador':indicador,'sexo':sexo,'total':int(controle.to_numpy().sum()),'cids_positivos':int(cmat.sum(axis=1).gt(0).sum()),'diferenca_base_principal':int(delta.sum()),'celulas_divergentes':int(delta.ne(0).sum())})
                    print(ano,indicador,sexo,'total',audits[-1]['total'],'OK',flush=True)
            lote=pd.DataFrame(parts,columns=final.columns);lote.to_csv(pasta/'f_meios_cid.csv.gz',index=False)
            final=pd.concat([final[~final.ano.eq(ano)],lote],ignore_index=True)
            assert not final.duplicated(['indicador','cod_mun_res','ano','mes','sexo','cid']).any()
            temp=out.with_name('f_meios_cid.tmp.gz');final.to_csv(temp,index=False);temp.replace(out)
            oldmeta['auditoria']=[a for a in oldmeta['auditoria'] if a['ano']!=ano]+audits;oldmeta['cobertura'][str(ano)]=coverage
            oldmeta.setdefault('definicao_cid_por_ano',{})[str(ano)]=ID_DEFINICAO_CID;oldmeta['definicao_cid']=resumo_definicao()
            oldmeta.update({'fonte':URL,'extraido_utc':datetime.now(timezone.utc).isoformat(),'revisao':c['revision'],'dimensao_cid':dim,'grao':['indicador','cod_mun_res','ano','mes','sexo','cid'],'nota':'Fato esparsa: somente contagens positivas. Zeros são válidos apenas dentro dos anos e meses com extração validada. Mesmos recortes de residência, idade elegível e sexo dos indicadores. Grupos de meios são agregações analíticas dos códigos CID-10.'})
            write_json(mp,oldmeta)
            print('ANO PUBLICÁVEL',ano,'linhas acumuladas',len(final),flush=True)
    finally:client.close()

def integrar_banco(raiz):
    import sqlite3,shutil
    raiz=Path(raiz)
    fato=pd.read_csv(DADOS/'f_meios_cid.csv.gz',dtype={'cod_mun_res':str})
    meta=json.loads((DADOS/'meios_cid_meta.json').read_text())
    with sqlite3.connect(raiz/'tcc.sqlite') as con:
        fato.to_sql('f_indicador_meios_cid',con,if_exists='replace',index=False)
        pd.DataFrame(meta['dimensao_cid']).to_sql('d_meios_cid',con,if_exists='replace',index=False)
        con.execute('CREATE UNIQUE INDEX uq_meios_cid ON f_indicador_meios_cid(indicador,cod_mun_res,ano,mes,sexo,cid)')
    destino=raiz/'complementos';destino.mkdir(exist_ok=True)
    for name in ['f_meios_cid.csv.gz','meios_cid_meta.json']:shutil.copy2(DADOS/name,destino/name)
    pd.DataFrame(meta['dimensao_cid']).to_csv(destino/'d_meios_cid.csv',index=False)

if __name__=='__main__':
    ap=argparse.ArgumentParser();ap.add_argument('--inicio',type=int,default=2016);ap.add_argument('--fim',type=int,default=datetime.now().year);ap.add_argument('--forcar',action='store_true');args=ap.parse_args()
    executar(range(args.fim,args.inicio-1,-1),args.forcar)
