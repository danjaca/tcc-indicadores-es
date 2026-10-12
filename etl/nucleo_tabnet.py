from pathlib import Path
from io import StringIO, BytesIO
from itertools import product
from datetime import datetime, timezone
from urllib.parse import urljoin, urlencode
import re, json, hashlib, time, unicodedata, zipfile, shutil
import pandas as pd
import numpy as np
import requests
from bs4 import BeautifulSoup
from .definicao_cid import CAMPO_CATEGORIA, CAMPO_SUBCATEGORIA, montar_selecao, resumo_definicao
URL = 'http://tabnet.saude.es.gov.br/cgi/deftohtm.exe?tabnet/SIM/SIM2006/sim2006.def'
ALL = 'TODAS_AS_CATEGORIAS__'
FAIXAS = ['0 a 4 anos','5 a 9 anos','10 a 14 anos','15 a 19 anos',
          '20 a 29 anos','30 a 39 anos','40 a 49 anos','50 a 59 anos',
          '60 a 69 anos','70 a 79 anos','80 anos ou mais','Ignorado']
SEXOS = ['Masculino','Feminino','Ignorado']
CAUSAS = ['Homicídio','Suicídio']
COLUNAS = ['cod_mun_res','dt_obito','mes','ano','tipo_causa','faixa_etaria','sexo','Obitos']
CHAVE = COLUNAS[:-1]
AGE_FIELD = 'SFaixa_Etária_det'
# Numeradores selecionados por subcategoria (4 caracteres), conforme as fichas do PES-ES.
# O campo de três dígitos fica para o controle de equivalência e para a tabulação por categoria.
CID_FIELD = CAMPO_SUBCATEGORIA
CID3_FIELD = CAMPO_CATEGORIA
MUN_FIELD = 'SMunicípio_Resid'
MONTHS = ['jan','fev','mar','abr','mai','jun','jul','ago','set','out','nov','dez']
def norm(s):
    s = unicodedata.normalize('NFKD', str(s)).encode('ascii','ignore').decode().lower()
    return re.sub(r'\s+', ' ', s).strip()
def digest(obj):
    return hashlib.sha256(json.dumps(obj,ensure_ascii=False,sort_keys=True).encode()).hexdigest()
def write_json(path, obj):
    path = Path(path)
    temp = path.with_suffix(path.suffix+'.tmp')
    temp.write_text(json.dumps(obj,ensure_ascii=False,indent=2),encoding='utf-8')
    temp.replace(path)
def parse_form(html):
    soup = BeautifulSoup(html,'lxml')
    form = next((f for f in soup.select('form') if f.find('select',attrs={'name':'Linha'})),None)
    if form is None:
        raise ValueError('Formulário TabNet não encontrado: verificar conexão e URL.')
    options = {}
    defaults = {}
    for sel in form.select('select[name]'):
        opts = [{'value':o.get('value',o.get_text(strip=True)),
                 'label':o.get_text(' ',strip=True)} for o in sel.select('option')]
        options[sel['name']] = opts
        chosen = [o.get('value',o.get_text(strip=True)) for o in sel.select('option[selected]')]
        defaults[sel['name']] = chosen or [opts[0]['value']]
    txt = soup.get_text(' ',strip=True)
    revision = re.search(r'Última Atualização.*',txt,re.I)
    return {'options':options,'defaults':defaults,
            'action':urljoin(URL,form.get('action',URL)),
            'revision':revision.group(0) if revision else 'Atualização não informada'}
def exact_value(options, label):
    matches = [o['value'] for o in options if norm(o['label']) == norm(label)]
    if len(matches)!=1:
        raise ValueError(f'Rótulo ausente/ambíguo no formulário: {label!r}. Não usar índices fixos.')
    return matches[0]
def make_contract(form, year, municipalities):
    opt = form['options']
    required = ['Linha','Coluna','Incremento','Arquivos',AGE_FIELD,CID_FIELD,CID3_FIELD,MUN_FIELD,'SSexo']
    if any(k not in opt for k in required):
        raise ValueError('A estrutura do formulário mudou. Revise os campos requeridos.')
    base = {k:([ALL] if any(o['value']==ALL for o in v) else form['defaults'][k])
            for k,v in opt.items()}
    base.update({'Linha':[exact_value(opt['Linha'],'Município Resid')],
                 'Coluna':[exact_value(opt['Coluna'],'Mês do Óbito')],
                 'Incremento':[exact_value(opt['Incremento'],'Óbito')],
                 'Arquivos':[exact_value(opt['Arquivos'],str(year))]})
    mun_values = {}
    for o in opt[MUN_FIELD]:
        m = re.match(r'^(\d{6,7})\b',o['label'])
        if m and m.group(1)[:6] in municipalities:
            code = m.group(1)[:6]
            if code in mun_values: raise ValueError('Código municipal duplicado no formulário.')
            mun_values[code] = o['value']
    if set(mun_values)!=set(municipalities) or len(mun_values)!=78:
        raise ValueError('Os municípios do formulário não correspondem aos 78 da dimensão enviada.')
    base[MUN_FIELD] = [mun_values[m] for m in sorted(municipalities)]
    labels = [
        ['0 a 6 dias','7 a 27 dias','28 dias a <1 ano','Menor de 1 ano (ign)','1 a 4 anos'],
        ['5 a 9 anos'],['10 a 14 anos'],['15 a 19 anos'],
        ['20 a 24 anos','25 a 29 anos'],['30 a 34 anos','35 a 39 anos'],
        ['40 a 44 anos','45 a 49 anos'],['50 a 54 anos','55 a 59 anos'],
        ['60 a 64 anos','65 a 69 anos'],['70 a 74 anos','75 a 79 anos'],
        ['80 anos e mais'],['Idade ignorada']]
    ages = {f:[exact_value(opt[AGE_FIELD],v) for v in vs] for f,vs in zip(FAIXAS,labels)}
    flat = sum(ages.values(),[])
    if len(flat)!=len(set(flat)) or set(flat)!={o['value'] for o in opt[AGE_FIELD] if o['value']!=ALL}:
        raise ValueError('Faixas devem formar uma partição completa, sem sobreposição.')
    sexes = {s:[exact_value(opt['SSexo'],v)] for s,v in zip(SEXOS,['Masc','Fem','Ign'])}
    if set(sum(sexes.values(),[]))!={o['value'] for o in opt['SSexo'] if o['value']!=ALL}:
        raise ValueError('Sexo contém categorias novas. Rever equivalência com Ignorado.')
    # Fichas 1.8.15/1.8.16/1.8.17: ver etl/definicao_cid.py (fonte única da regra).
    selecao = montar_selecao(opt[CID_FIELD], opt[CID3_FIELD])
    if set(selecao) != set(CAUSAS):
        raise ValueError('A definição de CID deve cobrir exatamente as causas extraídas.')
    contract = {'version':'2.0','url':URL,'year':int(year),'revision':form['revision'],
                'municipalities':sorted(municipalities),'base':base,
                'ages':ages,'sexes':sexes,
                'cids':{k:v['valores'] for k,v in selecao.items()},
                'cid_codes':{k:v['codigos'] for k,v in selecao.items()},
                'cid_values':{k:v['valores_por_codigo'] for k,v in selecao.items()},
                'cid_linha':{k:v['linha_categoria'] for k,v in selecao.items()},
                'cid_equivalencia':{k:v['equivalencia'] for k,v in selecao.items()},
                'definicao_cid':resumo_definicao(),
                'age_labels':dict(zip(FAIXAS,labels))}
    contract['fingerprint'] = digest(contract)
    return contract
def count_value(value):
    value = str(value).replace('\xa0',' ').strip()
    if value in ['-','–']: return 0  # convenção de célula sem frequência do TabNet
    if re.fullmatch(r'\d+',value): return int(value)
    if re.fullmatch(r'\d{1,3}(?:\.\d{3})+',value): return int(value.replace('.',''))
    raise ValueError(f'Contagem desconhecida/suprimida: {value!r}. Não converter para zero.')
def parse_result(html, year, municipalities):
    soup = BeautifulSoup(html,'lxml')
    text = norm(soup.get_text(' ',strip=True))
    if soup.find('select',attrs={'name':'Linha'}):
        raise ValueError('O servidor retornou o formulário, não uma tabulação.')
    tables = []
    for table in soup.select('table'):
        rows = [[c.get_text(' ',strip=True) for c in tr.find_all(['th','td'],recursive=False)]
                for tr in table.select('tr')]
        if rows and rows[0] and norm(rows[0][0])=='municipio resid': tables.append(rows)
    if len(tables)!=1:
        # Mensagem de ausência é inconclusiva sem tabela/total; nunca fabricar zeros.
        raise ValueError('Tabela municipal ausente/ambígua. Erro ou consulta vazia não vira zero; ver HTML salvo.')
    period = re.search(r'periodo:\s*(\d{4})(?!\d)',text)
    if not period or int(period.group(1))!=year:
        raise ValueError('Período retornado não corresponde ao ano solicitado.')
    rows = tables[0]
    header = [norm(v) for v in rows[0]]
    if header[-1]!='total': raise ValueError('Coluna Total ausente.')
    month_ids = []
    for col in header[1:-1]:
        key = col[:3]
        if key not in MONTHS: raise ValueError(f'Coluna inesperada: {col}.')
        month_ids.append(MONTHS.index(key)+1)
    if len(set(month_ids))!=len(month_ids):
        raise ValueError('Meses inválidos/duplicados.')
    matrix = pd.DataFrame(0,index=sorted(municipalities),columns=range(1,13),dtype='int64')
    matrix.index.name='cod_mun_res'
    seen, total, excluded = set(), None, []
    for row in rows[1:]:
        if len(row)!=len(header): raise ValueError('Linha incompleta na tabela.')
        values = [count_value(v) for v in row[1:]]
        if sum(values[:-1])!=values[-1]: raise ValueError('Total da linha difere da soma dos meses.')
        label = norm(row[0])
        if label=='total':
            if total is not None: raise ValueError('Linha TOTAL duplicada.')
            total = values
            continue
        m = re.match(r'^(\d{6,7})\b',row[0])
        if not m: raise ValueError(f'Linha municipal não reconhecida: {row[0]!r}')
        code = m.group(1)[:6]
        if code in seen: raise ValueError('Município duplicado na tabela.')
        seen.add(code)
        if code not in matrix.index:
            # Com "linhas zeradas", o TabNet pode exibir 320000 fora da seleção.
            if values[-1]!=0: raise ValueError('Contagem fora dos 78 municípios selecionados.')
            excluded.append(code)
            continue
        matrix.loc[code,month_ids] = values[:-1]
    if total is None: raise ValueError('TOTAL não encontrado.')
    if matrix[month_ids].sum().tolist()!=total[:-1] or int(matrix.to_numpy().sum())!=total[-1]:
        raise ValueError('Soma municipal diverge do TOTAL publicado.')
    return matrix, {'total':total[-1],'months':month_ids,'municipal_rows':len(seen & set(municipalities)),
                    'zero_rows_outside_selection':excluded}
class TabnetClient:
    def __init__(self, motor='selenium'):
        self.motor = motor
        self.driver = None
        self.session = requests.Session()
        if motor=='selenium':
            from selenium import webdriver
            from selenium.webdriver.common.by import By
            from selenium.webdriver.support.ui import WebDriverWait
            options = webdriver.ChromeOptions()
            for arg in ['--headless=new','--no-sandbox','--disable-dev-shm-usage','--window-size=1440,1000']:
                options.add_argument(arg)
            # Selenium Manager instala Chrome/driver quando necessário.
            self.driver = webdriver.Chrome(options=options)
            self.driver.set_page_load_timeout(180)
            self.driver.get(URL)
            WebDriverWait(self.driver,180).until(lambda d:d.find_elements(By.NAME,'Linha'))
            self.main = self.driver.current_window_handle
            self.html = self.driver.page_source
        elif motor=='requests':
            r = self.session.get(URL,timeout=(20,180));r.raise_for_status()
            r.encoding='iso-8859-1';self.html=r.text
        else: raise ValueError('MOTOR deve ser selenium ou requests.')
        self.form = parse_form(self.html)
    def query(self, selections):
        if self.motor=='requests':
            payload = [(k,v) for k,vs in selections.items() for v in vs]
            payload += [('formato','table'),('zeradas','exibirlz'),('mostre','Mostra')]
            # O formulário original usa ISO-8859-1, não UTF-8 no POST.
            r = self.session.post(self.form['action'],
                data=urlencode(payload,encoding='iso-8859-1').encode('ascii'),
                headers={'Content-Type':'application/x-www-form-urlencoded','Referer':URL},
                timeout=(20,180))
            r.raise_for_status();r.encoding='iso-8859-1'
            return r.text
        from selenium.webdriver.common.by import By
        from selenium.webdriver.support.ui import WebDriverWait
        d = self.driver
        d.switch_to.window(self.main)
        # Atualiza opções do formulário real em lote, evitando milhares de chamadas WebDriver.
        # Todos os filtros são redefinidos a cada consulta para não acumular seleções.
        d.execute_script('''
          const fields = arguments[0];
          for (const [name, values] of Object.entries(fields)) {
            const el = document.getElementsByName(name)[0];
            if (!el || el.tagName !== 'SELECT') throw Error('Campo ausente: '+name);
            const available = new Set(Array.from(el.options,o=>o.value));
            if (values.some(v=>!available.has(v))) throw Error('Opção ausente: '+name);
            if (!el.multiple && values.length!==1) throw Error('Seleção inválida: '+name);
            for (const o of el.options) o.selected=values.includes(o.value);
            el.dispatchEvent(new Event('change',{bubbles:true}));
            const actual=Array.from(el.selectedOptions,o=>o.value).sort();
            if(JSON.stringify(actual)!==JSON.stringify([...values].sort())) throw Error('Falha: '+name);
          }
          for (const el of document.getElementsByName('formato')) el.checked=el.value==='table';
          document.getElementsByName('zeradas')[0].checked=true;
          for (const el of document.getElementsByName('opcoes')) el.checked=false;
          document.getElementsByName('mostre')[0].form.target='_blank';
        ''',selections)
        before=set(d.window_handles)
        try:
            d.find_element(By.NAME,'mostre').click()
            WebDriverWait(d,180).until(lambda x:len(set(x.window_handles)-before)==1)
            result=(set(d.window_handles)-before).pop()
            d.switch_to.window(result)
            WebDriverWait(d,180).until(lambda x:x.execute_script('return document.readyState')=='complete'
                and x.find_elements(By.TAG_NAME,'body') and len(x.find_element(By.TAG_NAME,'body').text)>50)
            return d.page_source
        finally:
            for handle in set(d.window_handles)-before:
                d.switch_to.window(handle);d.close()
            d.switch_to.window(self.main)
    def close(self):
        if self.driver is not None: self.driver.quit()
        self.session.close()
class Extraction:
    def __init__(self, client, contract, directory, interval=3):
        self.client, self.contract = client, contract
        self.directory = Path(directory)/f"{contract['year']}_{contract['fingerprint'][:12]}"
        self.directory.mkdir(parents=True,exist_ok=True)
        self.interval = interval
        self.audit=[]
        write_json(self.directory/'contrato.json',contract)
        self.client_html_saved = self.directory/'formulario.html'
        if hasattr(client,'html'):
            self.client_html_saved.write_text(client.html,encoding='utf-8')
    def run_query(self, cause, age=None, sex=None, tag='estrato', fresh=False, cid=None):
        """Consulta município x mês. `cid=(campo, valores)` substitui a seleção padrão da causa
        (usado apenas no controle de equivalência entre subcategorias e categorias)."""
        c=self.contract
        spec={'cause':cause,'age':age,'sex':sex,'tag':tag,'fingerprint':c['fingerprint']}
        if cid is not None: spec['cid']=[cid[0],list(cid[1])]
        key=digest(spec)[:20]
        path=self.directory/f'{key}.html'
        meta_path=self.directory/f'{key}.json'
        selections=dict(c['base'])
        if cid is None:
            selections[CID_FIELD]=c['cids'][cause]
        else:
            selections[cid[0]]=list(cid[1])
        selections[AGE_FIELD]=[ALL] if age is None else c['ages'][age]
        selections['SSexo']=[ALL] if sex is None else c['sexes'][sex]
        cached=False
        if not fresh and path.exists() and meta_path.exists():
            meta=json.loads(meta_path.read_text(encoding='utf-8'))
            raw=path.read_text(encoding='utf-8')
            cached=(meta.get('spec')==spec and meta.get('html_sha256')==hashlib.sha256(raw.encode()).hexdigest())
        if not cached:
            for attempt in range(3):
                try:
                    time.sleep(self.interval if attempt==0 else 10*(attempt+1))
                    raw=self.client.query(selections)
                    # Salva evidência, mas somente cria checkpoint de sucesso após validar.
                    (self.directory/f'{key}_ultima_resposta.html').write_text(raw,encoding='utf-8')
                    matrix,stats=parse_result(raw,c['year'],c['municipalities'])
                    meta={'spec':spec,'selections':selections,'stats':stats,
                          'extracted_utc':datetime.now(timezone.utc).isoformat(),
                          'motor':self.client.motor,'html_sha256':hashlib.sha256(raw.encode()).hexdigest()}
                    temp=path.with_suffix('.tmp');temp.write_text(raw,encoding='utf-8');temp.replace(path)
                    write_json(meta_path,meta)
                    break
                except Exception as error:
                    write_json(self.directory/f'{key}_erro.json',
                               {'spec':spec,'attempt':attempt+1,'error':repr(error)})
                    if attempt==2:
                        raise RuntimeError(f'Consulta interrompida: {cause}, {age}, {sex}. '
                                           f'Reexecute para retomar. Evidência: {self.directory}') from error
        # Revalida inclusive respostas de cache; não confia em CSV intermediário.
        matrix,stats=parse_result(raw,c['year'],c['municipalities'])
        self.audit.append({**spec,**stats,'cache':cached,'extracted_utc':meta['extracted_utc'],
                           'html_file':path.name})
        write_json(self.directory/'auditoria_consultas.json',self.audit)
        return matrix,stats
