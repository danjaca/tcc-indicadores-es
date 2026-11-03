"""Valida o pacote e impede a publicação de complementos recentes divergentes."""
import argparse,json
from pathlib import Path
import numpy as np
import pandas as pd
from dominio.dados import carregar,recortar,INDICADORES,IDADES
from configuracao import DADOS
from .definicao_cid import DEFINICAO_LEGADA,codigos_detalhamento
from .pipeline import validar_fato,validar_pop

def validar(anos_atualizados=None):
    f,p,g,meta=carregar()
    anos_atualizados=sorted(set(meta['anos_disponiveis'] if anos_atualizados is None else anos_atualizados))
    if not set(anos_atualizados).issubset(meta['anos_disponiveis']):raise ValueError('Anos sem cobertura na base principal.')
    chaves=['cod_mun_res','ano','mes','tipo_causa','faixa_etaria','sexo']
    if f.empty or f[chaves+['Obitos']].isna().any().any() or f.duplicated(chaves).any():
        raise ValueError('Fato vazia, duplicada ou com campos obrigatórios nulos.')
    for frame,col in [(f,'Obitos'),(p,'populacao')]:
        v=pd.to_numeric(frame[col],errors='raise')
        if not (np.isfinite(v)&(v>=0)&(v%1==0)).all():raise ValueError(f'{col} contém valores inválidos.')
    if len(g)!=78 or not g.cod_mun_res.is_unique:raise ValueError('Geografia incompatível com os 78 municípios do ES.')
    if set(f.cod_mun_res)!=set(g.cod_mun_res):raise ValueError('Municípios da fato divergentes.')
    if set(f.tipo_causa)!={'Suicídio','Homicídio'} or set(f.faixa_etaria)!=set(IDADES):raise ValueError('Domínios epidemiológicos divergentes.')
    if set(f.sexo)!={'Masculino','Feminino','Ignorado'}:raise ValueError('Domínio de sexo divergente.')
    # Toda a série deve usar a mesma definição de CID (ausência de registro = definição legada).
    definicoes={str(a):meta.get('extracoes',{}).get(str(a),{}).get('definicao_cid',DEFINICAO_LEGADA) for a in meta['anos_disponiveis']}
    if len(set(definicoes.values()))>1:
        raise ValueError('Série com definições de CID diferentes entre os anos; reprocesse todos os anos.')
    popkey=['cod_mun_res','ano','faixa_etaria','sexo']
    if p[popkey+['populacao']].isna().any().any() or p.duplicated(popkey).any():raise ValueError('População duplicada ou nula.')
    for ano in meta['anos_disponiveis']:
        fat=f[f.ano.eq(ano)];meses=sorted(fat.mes.unique().tolist());pop=p[p.ano.eq(ano)]
        if not meses or meses!=list(range(1,max(meses)+1)) or max(meses)>12:raise ValueError('Cobertura mensal não contígua.')
        validar_fato(fat,ano,sorted(g.cod_mun_res),meses)
        validar_pop(pop,ano,sorted(g.cod_mun_res))
        if meta.get('extracoes',{}).get(str(ano),{}).get('meses')!=meses:
            raise ValueError(f'Cobertura declarada diverge da fato principal: {ano}.')
    for stem,extra in [('raca_cor','raca_cor'),('meios_cid','cid')]:
        c=pd.read_csv(DADOS/f'f_{stem}.csv.gz',dtype={'cod_mun_res':str})
        cm=json.loads((DADOS/f'{stem}_meta.json').read_text())
        keys=['indicador','cod_mun_res','ano','mes','sexo']
        v=pd.to_numeric(c.Obitos,errors='raise')
        if c[keys+[extra,'Obitos']].isna().any().any() or c.duplicated(keys+[extra]).any() or not (np.isfinite(v)&(v>=0)&(v%1==0)).all():raise ValueError(f'Complemento inválido: {stem}')
        for col,dominio in [('indicador',INDICADORES),('cod_mun_res',g.cod_mun_res),
                            ('ano',meta['anos_disponiveis']),('mes',range(1,13)),
                            ('sexo',['Masculino','Feminino','Ignorado'])]:
            if not c[col].isin(dominio).all():raise ValueError(f'Domínio inválido no complemento {stem}: {col}.')
        for ano,rec in c.groupby('ano'):
            if not rec.mes.isin(cm.get('cobertura',{}).get(str(ano),[])).all():
                raise ValueError(f'Complemento fora da cobertura declarada: {stem}/{ano}.')
        for indicador,cfg in INDICADORES.items():
            rec=c[c.indicador.eq(indicador)]
            if cfg['sexo'] and not rec.sexo.eq(cfg['sexo']).all():raise ValueError(f'Domínio de sexo inválido: {stem}/{indicador}.')
            if extra=='cid' and not rec.cid.isin(codigos_detalhamento(cfg['causa'])).all():
                raise ValueError(f'Domínio CID inválido: {indicador}.')
        definicoes_comp=cm.get('definicao_cid_por_ano',{})
        for ano,definicao in definicoes.items():
            if ano in cm.get('cobertura',{}) and definicoes_comp.get(ano,DEFINICAO_LEGADA)!=definicao:
                raise ValueError(f'Complemento {stem} extraído com definição de CID diferente da base principal em {ano}.')
        for ano in anos_atualizados:
            expected_months=sorted(f.loc[f.ano.eq(ano),'mes'].unique().tolist())
            if cm['cobertura'].get(str(ano))!=expected_months:raise ValueError(f'Cobertura divergente: {stem}/{ano}')
            for indicador in INDICADORES:
                nf,_=recortar(f,p,indicador,g.cod_mun_res)
                expected=nf[nf.ano.eq(ano)].groupby(['cod_mun_res','mes','sexo']).Obitos.sum()
                actual=c[c.ano.eq(ano)&c.indicador.eq(indicador)].groupby(['cod_mun_res','mes','sexo']).Obitos.sum()
                ix=expected.index.union(actual.index)
                if not expected.reindex(ix,fill_value=0).equals(actual.reindex(ix,fill_value=0)):
                    raise ValueError(f'Complemento diverge da fato principal: {stem}/{ano}/{indicador}')
    report={'status':'validado','anos':meta['anos_disponiveis'],'linhas_obitos':len(f),'municipios':len(g),'anos_complementos_conferidos':list(anos_atualizados),
            'definicao_cid':sorted(set(definicoes.values()))}
    print(json.dumps(report,ensure_ascii=False));return report

if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--anos',type=int,nargs='+',help='Restringe a conciliação; por padrão, confere todos os anos.')
    validar(parser.parse_args().anos)
