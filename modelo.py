from pathlib import Path
import json
from zipfile import ZipFile
import pandas as pd

DADOS = Path(__file__).parent / 'dados'
IDADES = ['0 a 4 anos','5 a 9 anos','10 a 14 anos','15 a 19 anos','20 a 29 anos','30 a 39 anos','40 a 49 anos','50 a 59 anos','60 a 69 anos','70 a 79 anos','80 anos ou mais','Ignorado']
INDICADORES = {
 'Suicídio geral': {'causa':'Suicídio','idades':None,'sexo':None,'descricao':'Óbitos por suicídio, em todas as idades e sexos, por 100 mil habitantes.'},
 'Homicídios — jovens de 15 a 29 anos': {'causa':'Homicídio','idades':['15 a 19 anos','20 a 29 anos'],'sexo':None,'descricao':'Óbitos por homicídio de residentes de 15 a 29 anos, por 100 mil habitantes da mesma faixa etária.'},
 'Homicídios — mulheres de 10 a 59 anos': {'causa':'Homicídio','idades':IDADES[2:8],'sexo':'Feminino','descricao':'Óbitos por homicídio de mulheres de 10 a 59 anos, por 100 mil mulheres da mesma faixa etária.'},
}

def carregar():
    pacote=DADOS/'dataset.zip'
    if pacote.exists():
        with ZipFile(pacote) as z:
            meta=json.loads(z.read('disponibilidade.json'))
            with z.open('f_obitos.csv') as arq: f=pd.read_csv(arq,dtype={'cod_mun_res':str})
            with z.open('d_populacao.csv') as arq: p=pd.read_csv(arq,dtype={'cod_mun_res':str})
            with z.open('d_geografica.csv') as arq: g=pd.read_csv(arq,dtype={'cod_mun_res':str})
    else:
        meta=json.loads((DADOS/'disponibilidade.json').read_text())
        f=pd.read_csv(DADOS/'f_obitos_es_2016_2025.csv.gz',dtype={'cod_mun_res':str})
        p=pd.read_csv(DADOS/'d_populacao_es_2016_2025.csv.gz',dtype={'cod_mun_res':str})
        g=pd.read_csv(DADOS/'d_geografica_es.csv.gz',dtype={'cod_mun_res':str})
    f=f[f.ano.isin(meta['anos_disponiveis'])].copy()
    return f,p,g,meta

def recortar(f,p,indicador,codigos):
    cfg=INDICADORES[indicador]
    f=f[(f.tipo_causa==cfg['causa']) & f.cod_mun_res.isin(codigos)]
    p=p[p.cod_mun_res.isin(codigos)]
    if cfg['idades']:
        f=f[f.faixa_etaria.isin(cfg['idades'])]; p=p[p.faixa_etaria.isin(cfg['idades'])]
    if cfg['sexo']:
        f=f[f.sexo==cfg['sexo']]; p=p[p.sexo==cfg['sexo']]
    return f,p

def medidas(f,p,ano,meses):
    if not cobertura_completa(f,ano,meses): return None,None,None
    n=int(f.loc[(f.ano==ano)&f.mes.isin(meses),'Obitos'].sum())
    den=int(p.loc[p.ano==ano,'populacao'].sum())
    return n,den,n/den*100000 if den else None

def agrupado(f,p,ano,meses,chaves):
    num=f[(f.ano==ano)&f.mes.isin(meses)].groupby(chaves,observed=True).Obitos.sum().rename('Óbitos')
    den=p[p.ano==ano].groupby(chaves,observed=True).populacao.sum().rename('População')
    t=pd.concat([num,den],axis=1).reset_index()
    t['Óbitos']=t['Óbitos'].fillna(0)
    t['Taxa por 100 mil']=t['Óbitos'].div(t['População'].where(t['População']>0))*100000
    return t

def meses_disponiveis(f,ano):
    return sorted(int(x) for x in f.loc[f.ano.eq(ano),'mes'].unique())

def cobertura_completa(f,ano,meses):
    return bool(meses) and set(meses).issubset(meses_disponiveis(f,ano))

def serie_historica(f,p,anos,meses):
    linhas=[]
    for ano in anos:
        n,d,t=medidas(f,p,ano,meses)
        linhas.append({'Ano':ano,'Óbitos':n,'População':d,'Taxa por 100 mil':t})
    return pd.DataFrame(linhas)

def comparacao_mensal(f,p,ano,meses):
    linhas=[]
    for y in [ano-1,ano]:
        for mes in sorted(meses):
            n,d,t=medidas(f,p,y,[mes])
            linhas.append({'Ano':y,'Mês':mes,'Óbitos':n,'População':d,'Taxa por 100 mil':t})
    return pd.DataFrame(linhas)
