"""Mapa Leaflet: malha local, rótulos no zoom e limites PDR 2024."""
from pathlib import Path
import gzip,json
from functools import lru_cache
import pandas as pd

@lru_cache(maxsize=1)
def malhas():
    with gzip.open(Path(__file__).parent/'dados/mapa_pdr2024.json.gz','rt') as f:return json.load(f)

def mapa_html(territorial,medida):
    valores={str(r.cod_mun_res):{'nome':r.no_municipio,'valor':None if pd.isna(r[medida]) else float(r[medida]),'obitos':int(r['Óbitos']),'populacao':None if pd.isna(r['População']) else int(r['População'])} for _,r in territorial.iterrows()}
    payload=json.dumps({'malhas':malhas(),'valores':valores,'medida':medida},ensure_ascii=False).replace('</','<\\/')
    template='''<!doctype html><html lang="pt-BR"><head><meta charset="utf-8">
<link rel="stylesheet" href="https://unpkg.com/leaflet@1.9.4/dist/leaflet.css">
<style>body{margin:0;font:14px Arial;color:#183247}#map{height:710px;background:#f3f6f9;border-radius:12px}.label{background:transparent;border:0;box-shadow:none;font-weight:600;color:#183247;text-shadow:1px 1px white,-1px -1px white,1px -1px white,-1px 1px white;white-space:nowrap;font-size:12px}.label:before{display:none}.regiao{font-weight:700;font-size:14px;letter-spacing:1px;color:#183247}.legenda,.ajuda{padding:12px;background:rgba(255,255,255,.96);border-radius:8px;box-shadow:0 1px 5px #0002;line-height:1.6}.legenda i{display:inline-block;width:20px;height:12px;margin-right:6px}.leaflet-control button{background:white;border:0;padding:8px;cursor:pointer;color:#183247}</style></head><body><div id="map" aria-label="Mapa municipal do Espírito Santo e regiões do PDR 2024"></div>
<script src="https://unpkg.com/leaflet@1.9.4/dist/leaflet.js"></script><script>
const data=__DATA__,map=L.map('map',{minZoom:6,maxZoom:14,scrollWheelZoom:true,zoomSnap:.25});
const bounds=[[-21.35,-42],[-17.75,-39.4]];map.fitBounds(bounds,{padding:[20,20]});
let enquadrado=false;new ResizeObserver(()=>{if(map.getContainer().clientWidth>0){map.invalidateSize();if(!enquadrado){map.fitBounds(bounds,{padding:[20,20]});enquadrado=true}}}).observe(map.getContainer());
const colors=['#ffffcc','#fed976','#fd8d3c','#f03b20','#bd0026'];
const vals=Object.values(data.valores).map(x=>x.valor).filter(x=>x!==null),max=Math.max(1,...vals);
const fmt=(v,d=0)=>v===null?'Sem denominador':v.toLocaleString('pt-BR',{minimumFractionDigits:d,maximumFractionDigits:d});
const color=v=>v===null?'#e2e8f0':colors[Math.min(4,Math.floor(v/max*5))];
const munlabels=L.layerGroup(),reglabels=L.layerGroup();
L.geoJSON(data.malhas.municipios,{style:f=>{const d=data.valores[f.properties.cod_mun_res];return{color:'#8b98a5',weight:.7,fillColor:color(d?.valor??null),fillOpacity:.88}},onEachFeature:(f,l)=>{
 const p=f.properties,d=data.valores[p.cod_mun_res],nome=d?.nome??p.nome??p.NM_MUN??p.name??p.cod_mun_res;
 l.bindTooltip('<b>'+nome+'</b><br>Região '+p.regiao_saude+(d?'<br>'+data.medida+': '+fmt(d.valor,data.medida==='Óbitos'?0:2)+'<br>Óbitos: '+fmt(d.obitos)+'<br>População anual: '+fmt(d.populacao):'<br>Fora do recorte'));
 l.on('click',()=>{const b=p.bounds;map.fitBounds(b?[[b[1],b[0]],[b[3],b[2]]]:l.getBounds(),{maxZoom:11,padding:[30,30]})});
 L.marker([p.lat,p.lon],{opacity:0,interactive:false,keyboard:false}).bindTooltip(nome,{permanent:true,direction:'center',className:'label'}).addTo(munlabels);
}}).addTo(map);
const limites=L.geoJSON(data.malhas.regioes,{style:{color:'#183247',weight:2.7,fill:false},interactive:false}).addTo(map);
for(const f of data.malhas.regioes.features){const p=f.properties;L.marker([p.lat,p.lon],{opacity:0,interactive:false,keyboard:false}).bindTooltip(p.regiao_saude.toUpperCase(),{permanent:true,direction:'center',className:'label regiao'}).addTo(reglabels)}
function labels(){if(map.getZoom()>=9){map.addLayer(munlabels);map.removeLayer(reglabels)}else{map.removeLayer(munlabels);map.addLayer(reglabels)}}map.on('zoomend',labels);labels();
L.control.layers(null,{'Divisas regionais · PDR 2024':limites},{collapsed:false}).addTo(map);
const reset=L.control({position:'topleft'});reset.onAdd=()=>{let el=L.DomUtil.create('div','leaflet-bar');let b=L.DomUtil.create('button','',el);b.textContent='Ver todo o ES';b.onclick=()=>map.fitBounds(bounds,{padding:[20,20]});L.DomEvent.disableClickPropagation(el);return el};reset.addTo(map);
const legend=L.control({position:'bottomright'});legend.onAdd=()=>{let el=L.DomUtil.create('div','legenda');el.innerHTML='<b>'+data.medida+'</b><br>';for(let i=0;i<5;i++)el.innerHTML+='<i style="background:'+colors[i]+'"></i>'+fmt(i*max/5,2)+' '+(i===4?'a':'a <')+' '+fmt((i+1)*max/5,2)+'<br>';el.innerHTML+='<i style="background:#e2e8f0"></i>Fora do recorte / sem taxa<br><span style="border-top:3px solid #183247;display:inline-block;width:20px"></span> Divisa regional';return el};legend.addTo(map);
L.control.scale({imperial:false}).addTo(map);map.attributionControl.addAttribution('Malha IBGE 2025 · Regiões SESA/PDR 2024');
</script></body></html>'''
    return template.replace('__DATA__',payload)
