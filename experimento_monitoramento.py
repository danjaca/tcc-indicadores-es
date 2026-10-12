"""Avaliação temporal e simulações; sem consulta externa ou ajuste no período de teste."""
import argparse
from dataclasses import asdict
from pathlib import Path
import hashlib
import json
import platform
import numpy as np
import pandas as pd
from configuracao import DADOS
from modelo import carregar, recortar, INDICADORES, serie_historica, agrupado, cobertura_completa
from monitoramento import ajustar, aplicar, funil, TAXA

SINAIS=['Sinal u','Sinal controle','Sinal EWMA','Sinal CUSUM +','Sinal CUSUM −']
PERIODOS={'Q1':range(1,5),'Q2':range(5,9),'Q3':range(9,13),'Acumulado Q2':range(1,9),'Acumulado Q3':range(1,13)}


def simular(ref, pop, repeticoes, seed):
    rng=np.random.default_rng(seed)
    rows=[]
    for mudanca in [0., .25, -.25]:
        # Shift conhecido depois de quatro períodos estáveis; unidade = anos equivalentes.
        for rep in range(repeticoes):
            taxas=np.full(12,ref.taxa);taxas[4:]*=1+mudanca
            n=rng.poisson(taxas*pop/100000)
            t=pd.DataFrame({'Ano':range(max(ref.anos)+1,max(ref.anos)+13),'Óbitos':n,'População':pop})
            t[TAXA]=n/pop*100000
            out=aplicar(t,ref)
            for sinal in SINAIS:
                flags=out[sinal].to_numpy()
                inicio=0 if mudanca==0 else 4
                hits=np.flatnonzero(flags[inicio:])
                rows.append({'mudanca':mudanca,'repeticao':rep,'metodo':sinal,
                             'sinais':int(flags[inicio:].sum()),'periodos':len(flags)-inicio,
                             'detectou':bool(len(hits)), 'atraso':int(hits[0]+1) if len(hits) else None})
    return pd.DataFrame(rows)


def main():
    ap=argparse.ArgumentParser()
    ap.add_argument('--inicio',type=int,default=2016);ap.add_argument('--fim-referencia',type=int,default=2022)
    ap.add_argument('--simulacoes',type=int,default=200);ap.add_argument('--seed',type=int,default=20261011)
    ap.add_argument('--saida',type=Path,default=Path(__file__).parent/'resultados_monitoramento')
    args=ap.parse_args()
    if not 5<=args.fim_referencia-args.inicio+1<=7:ap.error('Referência deve ter cinco a sete anos.')
    if args.simulacoes<1:ap.error('Simulações deve ser positivo.')
    out=args.saida;out.mkdir(parents=True,exist_ok=True)
    f,p,g,meta=carregar()
    regioes=pd.read_csv(DADOS/'regioes_pdr2024.csv',dtype={'cod_mun_res':str})
    grupos={'Espírito Santo':g.cod_mun_res.tolist()}
    for reg, sub in regioes.groupby('regiao_pdr2024') if 'regiao_pdr2024' in regioes else regioes.groupby('regiao_saude'):
        grupos[str(reg)]=sub.cod_mun_res.tolist()
    registros=[];bases=[];refs=[];sim=[];funis=[];falhas=[]
    fim=max(meta['anos_disponiveis'])
    for indicador in INDICADORES:
        for territorio,codigos in grupos.items():
            nf,npop=recortar(f,p,indicador,codigos)
            for periodo,meses in PERIODOS.items():
                contexto={'indicador':indicador,'territorio':territorio,'periodo':periodo}
                base=serie_historica(nf,npop,range(args.inicio,args.fim_referencia+1),meses)
                try:r=ajustar(base)
                except ValueError as e:falhas.append(dict(**contexto,motivo=str(e)));continue
                bases.append(base.assign(**contexto));refs.append(dict(**contexto,**asdict(r)))
                teste=serie_historica(nf,npop,range(args.fim_referencia+1,fim+1),meses)
                for y in teste.loc[teste[TAXA].isna(),'Ano']:falhas.append(dict(**contexto,ano=int(y),motivo='Período sem cobertura/denominador; não é zero.'))
                teste=teste.dropna(subset=['Óbitos','População',TAXA])
                if not teste.empty:registros.append(aplicar(teste,r).assign(**contexto))
                if territorio=='Espírito Santo':
                    sim.append(simular(r,float(base['População'].iloc[-1]),args.simulacoes,args.seed).assign(**contexto))
                    for y in range(args.fim_referencia+1,fim+1):
                        if cobertura_completa(nf,y,meses):
                            ft=funil(agrupado(nf,npop,y,meses,['cod_mun_res']))
                            funis.append(ft.merge(g[['cod_mun_res','no_municipio']],on='cod_mun_res').assign(ano=y,**contexto))
    for nome,tabelas in [('referencia',bases),('sinais_historicos',registros),('funil',funis),('simulacoes',sim)]:
        if tabelas:pd.concat(tabelas,ignore_index=True).to_csv(out/(nome+'.csv'),index=False)
    if registros:
        tt=pd.concat(registros)
        resumo=tt.groupby(['indicador','territorio','periodo'])[SINAIS].agg(['sum','count','mean'])
        resumo.to_csv(out/'frequencia_sinais.csv')
    if sim:
        tt=pd.concat(sim)
        ss=tt.groupby(['indicador','periodo','mudanca','metodo']).agg(proporcao_sinais=('sinais','sum'),periodos=('periodos','sum'),probabilidade_sinal_na_janela=('detectou','mean'),atraso_medio_condicional=('atraso','mean'))
        ss['proporcao_sinais']/=ss['periodos'];ss.to_csv(out/'avaliacao_simulada.csv')
    pd.DataFrame(falhas).to_csv(out/'periodos_indisponiveis.csv',index=False)
    manifesto=dict(referencia=[args.inicio,args.fim_referencia],fase_II=[args.fim_referencia+1,fim],parametros=dict(peso=.2,largura=3,k=.5,h=5),seed=args.seed,simulacoes=args.simulacoes,referencias=refs,sha256_dataset=hashlib.sha256((DADOS/'dataset.zip').read_bytes()).hexdigest(),python=platform.python_version(),definicao_cid=meta.get('definicao_cid','legada'),metadados=meta,nota='Frequência histórica não é falso alarme: não há verdade epidemiológica rotulada. Simulação Poisson sob controle estima alarmes por período/janela; shifts ±25% avaliam detecção, sem provar validade em dados reais. Resultados preliminares; verificar estabilidade e reprocessar CID legado.')
    (out/'manifesto.json').write_text(json.dumps(manifesto,ensure_ascii=False,indent=2))
    print(f'Resultados: {out}; {len(refs)} referências; {len(falhas)} períodos indisponíveis.')

if __name__=='__main__':main()
