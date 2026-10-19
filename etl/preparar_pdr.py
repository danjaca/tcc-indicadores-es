import os
from configuracao import DADOS, ESTADO
from pathlib import Path
import json,gzip,re,sys
import pandas as pd
from shapely.geometry import shape,mapping
from shapely.ops import unary_union
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from dominio.dados import carregar

def executar():
 from . import nucleo_tabnet
 ns=vars(nucleo_tabnet)
 client=ns['TabnetClient'](os.environ.get('TCC_TABNET_MOTOR','requests'))
 try:
  rows=[];regiao=None
  for o in client.form['options']['SReg_PDR2024/Mun_res']:
   label=o['label']
   match=re.match(r'^00000[1-4]\s+[1-4]\s*-\s*(.+)',label)
   if match: regiao=match[1].title()
   m=re.match(r'^(32\d{4})\b',label)
   if m and m[1]!='320000':rows.append({'cod_mun_res':m[1],'regiao_saude':regiao})
  df=pd.DataFrame(rows)
  assert len(df)==78 and df.cod_mun_res.nunique()==78 and df.regiao_saude.notna().all(),df
  assert df.regiao_saude.value_counts().to_dict()=={'Sul':26,'Metropolitana':23,'Central':15,'Norte':14}
  df.to_csv(DADOS/'regioes_pdr2024.csv',index=False)
  with gzip.open(DADOS/'municipios_es.geojson.gz','rt') as file:malha=json.load(file)
  nomes=carregar()[2].set_index('cod_mun_res').no_municipio.to_dict()
  lookup=df.set_index('cod_mun_res').regiao_saude.to_dict();features=[]
  for regiao in sorted(df.regiao_saude.unique()):
   polys=[shape(f['geometry']) for f in malha['features'] if lookup[str(f['properties']['cod_mun_res'])]==regiao]
   unido=unary_union(polys)
   continental=max(unido.geoms,key=lambda x:x.area) if unido.geom_type=='MultiPolygon' else unido
   point=continental.representative_point()
   features.append({'type':'Feature','properties':{'regiao_saude':regiao,'lat':point.y,'lon':point.x},'geometry':mapping(unido)})
  for feat in malha['features']:
   geom=shape(feat['geometry']);continental=max(geom.geoms,key=lambda x:x.area) if geom.geom_type=='MultiPolygon' else geom
   point=continental.representative_point();feat['properties'].update(bounds=list(continental.bounds),nome=nomes[str(feat['properties']['cod_mun_res'])],regiao_saude=lookup[str(feat['properties']['cod_mun_res'])],lat=point.y,lon=point.x)
  with gzip.open(DADOS/'mapa_pdr2024.json.gz','wt') as file:json.dump({'municipios':malha,'regioes':{'type':'FeatureCollection','features':features}},file,separators=(',',':'))
  ns['write_json'](DADOS/'pdr_meta.json',{'fonte_agrupamento':ns['URL'],'campo':'SReg_PDR2024/Mun_res','revisao':client.form['revision'],'fonte_pdr':'https://saude.es.gov.br/GrupodeArquivos/plano-diretor-de-regionalizacao_pdr-es-2024','malha':'IBGE 2025','quantidades':df.regiao_saude.value_counts().to_dict(),'nota':'Limites regionais derivados da união dos municípios do PDR 2024; classificação fixa aplicada a todos os anos para comparabilidade.'})
  print(df.regiao_saude.value_counts())
 finally:client.close()
if __name__=='__main__':executar()
