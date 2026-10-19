import os
from configuracao import DADOS, ESTADO
"""Valida o lote do ETL e publica um ZIP único por substituição atômica."""
from pathlib import Path
import sys,json,hashlib,os
from zipfile import ZipFile,ZIP_DEFLATED
from datetime import datetime,timezone
import pandas as pd
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from dominio.dados import carregar,DADOS
from .definicao_cid import DEFINICAO_LEGADA,anos_fora_da_definicao,resumo_definicao

def incorporar(raiz):
    pointer=json.loads((raiz/'exportacao_atual.json').read_text())
    lote=Path(pointer['pasta'])
    if pointer['status']!='concluido': raise ValueError('A publicação exige lote concluído, sem erros.')
    manifest=json.loads((lote/'manifesto.json').read_text())
    for nome,item in manifest['arquivos'].items():
        arq=lote/(nome+'.csv')
        if hashlib.sha256(arq.read_bytes()).hexdigest()!=item['sha256']: raise ValueError('Hash divergente: '+nome)
    novo=pd.read_csv(lote/'f_obitos.csv',dtype={'cod_mun_res':str})
    pop=pd.read_csv(lote/'d_populacao.csv',dtype={'cod_mun_res':str})
    geo=pd.read_csv(lote/'d_geografica.csv',dtype={'cod_mun_res':str})
    controle=pd.read_csv(lote/'controle_cargas.csv')
    f,p,g,meta=carregar()
    anos=sorted(int(x) for x in novo.ano.unique())
    for ano in anos:
        c=controle[(controle.dataset=='sim')&(controle.ano==ano)]
        if len(c)!=1: raise ValueError('Controle ausente')
        detalhes=json.loads(c.iloc[0].detalhes)
        fat=novo[novo.ano.eq(ano)]
        meses=sorted(int(x) for x in fat.mes.unique())
        if meses!=detalhes['meses'] or len(fat)!=78*len(meses)*2*12*3: raise ValueError('Cobertura ou grade divergente')
        if set(fat.cod_mun_res)!=set(g.cod_mun_res): raise ValueError('Territórios divergentes')
        if fat.duplicated(['cod_mun_res','ano','mes','tipo_causa','faixa_etaria','sexo']).any():raise ValueError('Fato duplicada')
        pp=pop[pop.ano.eq(ano)]
        if len(pp)!=78*11*2 or pp.duplicated(['cod_mun_res','ano','faixa_etaria','sexo']).any():raise ValueError('População inválida')
        if pp.ano_fonte_populacao.nunique()!=1:raise ValueError('População com anos-fonte misturados')
        meta.setdefault('populacao',{})[str(ano)]={'ano_fonte':int(pp.ano_fonte_populacao.iloc[0]),'provisorio':bool(pp.denominador_provisorio.any())}
        meta.setdefault('extracoes',{})[str(ano)]={'data':str(c.iloc[0].atualizado),'meses':meses,'lote':pointer['id'],'revisao':detalhes.get('revisao'),'fonte':detalhes.get('fonte'),
            'definicao_cid':detalhes.get('definicao_cid',DEFINICAO_LEGADA),
            'selecao':detalhes.get('selecao','subcategorias com equivalência comprovada'),
            'obitos_sem_subcategoria_incluidos':detalhes.get('obitos_sem_subcategoria_incluidos',{'Homicídio':0,'Suicídio':0})}
    f=pd.concat([f[~f.ano.isin(anos)],novo],ignore_index=True)
    if 'ano_fonte_populacao' not in p:
        p=p.assign(ano_fonte_populacao=p.ano,denominador_provisorio=0,metodo_denominador='ano_correspondente')
    p=pd.concat([p[~p.ano.isin(anos)],pop[pop.ano.isin(anos)]],ignore_index=True)
    meta['anos_disponiveis']=sorted(int(x) for x in f.ano.unique())
    # Não mistura numeradores com definições de CID diferentes na mesma série histórica.
    definicoes={str(a):meta.get('extracoes',{}).get(str(a),{}).get('definicao_cid',DEFINICAO_LEGADA) for a in meta['anos_disponiveis']}
    pendentes=anos_fora_da_definicao(definicoes)
    if pendentes:
        raise ValueError('A definição de CID mudou (fichas do PES-ES). Reprocesse também: '+', '.join(map(str,pendentes))
                         +'. Comando: python atualizar.py --inicio 2016 --forcar --publicar-local')
    meta['definicao_cid']=resumo_definicao()
    meta['definicao_cid'].update(campos_tabnet=['SCausas_3_Dígitos','SSubcategorias_(20)'],
                               estrategia='união disjunta de categorias completas e subcategorias isoladas')
    meta['data_preparacao']=datetime.now(timezone.utc).date().isoformat()
    meta['nota']='Confira a cobertura e a data de extração de cada ano. Dados recentes sujeitos a revisão.'
    meta['pacote_atualizado']=datetime.now(timezone.utc).isoformat()
    temp=DADOS/'dataset.tmp.zip'
    with ZipFile(temp,'w',ZIP_DEFLATED) as z:
        for name,df in [('f_obitos',f),('d_populacao',p),('d_geografica',geo)]: z.writestr(name+'.csv',df.to_csv(index=False))
        z.writestr('disponibilidade.json',json.dumps(meta,ensure_ascii=False,indent=2))
    os.replace(temp,DADOS/'dataset.zip')
    print(json.dumps(meta,ensure_ascii=False,indent=2))

if __name__=='__main__':
    incorporar(Path(sys.argv[1]) if len(sys.argv)>1 else ESTADO)
