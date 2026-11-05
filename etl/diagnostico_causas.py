"""Consulta complementar estadual de Y10–Y34 e R99, sem alterar os indicadores.

As contagens agregadas não comprovam reclassificações individuais ou completude.
Respostas e filtros são preservados em uma pasta exclusiva de evidências.
"""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import time
from urllib.parse import urlencode

import pandas as pd
import requests

from configuracao import DADOS
from dominio.dados import INDICADORES, carregar
from .extrair_meios_cid import parse_cids
from .nucleo_tabnet import (URL, ALL, AGE_FIELD, CID_FIELD, CID3_FIELD, parse_form,
                           make_contract, exact_value, parse_result, write_json)

CODIGOS = [f'Y{i:02d}' for i in range(10, 35)] + ['R99']
GRUPOS = {'Y10–Y34': CODIGOS[:-1],
          'Y10–Y21 e Y25–Y34': [c for c in CODIGOS[:-1] if c not in ['Y22', 'Y23', 'Y24']],
          'Y22–Y24': ['Y22', 'Y23', 'Y24'], 'R99': ['R99']}


def consultar(anos, saida: Path, evidencias: Path, intervalo: float = 3.) -> dict:
    anos = sorted(set(int(a) for a in anos))
    if not anos or min(anos) < 2016 or max(anos) > datetime.now().year or 4 * len(anos) + 2 > 30:
        raise ValueError('Informe até sete anos disponíveis desde 2016; limite de 30 requisições.')
    saida, evidencias = Path(saida), Path(evidencias)
    evidencias.mkdir(parents=True, exist_ok=False)
    saida.mkdir(parents=True, exist_ok=True)
    _, _, geo, principal = carregar()
    meta = {'status': 'executando', 'fonte': URL, 'anos': anos,
            'consultado_utc': datetime.now(timezone.utc).isoformat(),
            'escala': 'Espírito Santo, município de residência; agregação estadual',
            'codigos': CODIGOS, 'grupos': GRUPOS, 'recortes': {}, 'cobertura': {}, 'respostas': [],
            'sha256_dataset_principal': hashlib.sha256((DADOS / 'dataset.zip').read_bytes()).hexdigest(),
            'revisao_principal': principal.get('extracoes', {}).get(str(max(principal['anos_disponiveis'])), {}).get('revisao'),
            'nota': 'Consulta complementar independente da extração do pacote principal. '
                    'Y22–Y24 já integram os numeradores de homicídios e não são somados novamente. '
                    'R99 não identifica por si só uma causa externa; não há filtro de atestante IML. '
                    'Variações agregadas não demonstram reclassificação individual, atraso ou completude.'}
    sessao = requests.Session()
    anterior_meta = None

    def requisitar(metodo, url, selecao=None):
        if len(meta['respostas']) >= 30:
            raise ValueError('Limite de requisições alcançado.')
        numero = len(meta['respostas']) + 1
        registro = {'id': numero, 'metodo': metodo, 'url': url, 'selecao': selecao,
                    'consultado_utc': datetime.now(timezone.utc).isoformat()}
        meta['respostas'].append(registro)
        try:
            kwargs = {'timeout': (10, 45)}
            if selecao is not None:
                campos = [(k, v) for k, vs in selecao.items() for v in vs]
                campos += [('formato', 'table'), ('zeradas', 'exibirlz'), ('mostre', 'Mostra')]
                kwargs.update(data=urlencode(campos, encoding='iso-8859-1').encode('ascii'),
                              headers={'Content-Type': 'application/x-www-form-urlencoded', 'Referer': URL})
            resposta = sessao.request(metodo, url, **kwargs)
            nome = f'{numero:02d}_resposta.html'
            (evidencias / nome).write_bytes(resposta.content)
            registro.update(status_http=resposta.status_code, arquivo=nome,
                            sha256=hashlib.sha256(resposta.content).hexdigest())
            resposta.raise_for_status()
            resposta.encoding = 'iso-8859-1'
            return resposta.text
        finally:
            write_json(evidencias / f'{numero:02d}_consulta.json', registro)

    try:
        meta['sha256_codigo_coleta'] = {}
        for nome in ['etl/diagnostico_causas.py', 'etl/extrair_meios_cid.py', 'etl/nucleo_tabnet.py',
                     'etl/definicao_cid.py', 'dominio/dados.py', 'configuracao.py']:
            arq = Path(__file__).resolve().parents[1] / nome
            copia = evidencias / 'codigo' / nome
            copia.parent.mkdir(parents=True, exist_ok=True)
            copia.write_bytes(arq.read_bytes())
            meta['sha256_codigo_coleta'][nome] = hashlib.sha256(copia.read_bytes()).hexdigest()
        arquivo = saida / 'diagnostico_causas.csv'
        if arquivo.exists():
            candidato = json.loads((saida / 'diagnostico_causas_meta.json').read_text())
            if hashlib.sha256(arquivo.read_bytes()).hexdigest() != candidato.get('sha256_csv'):
                raise ValueError('Hash do diagnóstico anterior diverge dos metadados.')
            anterior_meta = candidato
            anterior = pd.read_csv(arquivo)
            if anterior.duplicated(['Recorte', 'Ano', 'Mês', 'CID']).any():
                raise ValueError('Diagnóstico anterior contém chaves duplicadas.')
            meta['cobertura'] = dict(anterior_meta['cobertura'])
        meta['anos_consultados'] = anos
        meta['origem_por_ano'] = dict(anterior_meta.get('origem_por_ano', {}) if anterior_meta else {})
        if anterior_meta:
            for ano in anterior_meta['cobertura']:
                meta['origem_por_ano'].setdefault(ano, {
                    'revisao': anterior_meta.get('revisao_fim'),
                    'consultado_utc': anterior_meta['consultado_utc'],
                    'sha256_csv_origem': anterior_meta['sha256_csv']})
        formulario = requisitar('GET', URL)
        form = parse_form(formulario)
        meta['revisao_inicio'] = form['revision']
        opcoes_cid = {o['label'].split()[0]: o['value'] for o in form['options'][CID3_FIELD]
                      if o['label'].split()}
        if not set(CODIGOS).issubset(opcoes_cid):
            raise ValueError('O formulário não oferece todos os códigos diagnósticos.')
        linhas = []
        for ano in anos:
            contrato = make_contract(form, ano, sorted(geo.cod_mun_res))
            controle = dict(contrato['base'])
            controle[CID_FIELD] = controle[CID3_FIELD] = [ALL]
            controle[AGE_FIELD] = controle['SSexo'] = [ALL]
            time.sleep(intervalo)
            matriz, stats = parse_result(requisitar('POST', form['action'], controle), ano, contrato['municipalities'])
            meses = sorted(stats['months'])
            if not meses:
                raise ValueError(f'Cobertura mensal não demonstrada para {ano}.')
            meta['cobertura'][str(ano)] = meses
            for recorte, cfg in INDICADORES.items():
                selecao = dict(controle)
                selecao['Linha'] = [exact_value(form['options']['Linha'], 'Causas 3 Dígitos')]
                selecao[CID3_FIELD] = [opcoes_cid[c] for c in CODIGOS]
                selecao[AGE_FIELD] = sum([contrato['ages'][a] for a in cfg['idades']], []) if cfg['idades'] else [ALL]
                selecao['SSexo'] = contrato['sexes'][cfg['sexo']] if cfg['sexo'] else [ALL]
                meta['recortes'][recorte] = {'idades': cfg['idades'] or 'Todas, inclusive ignorada',
                                             'sexo': cfg['sexo'] or 'Todos, inclusive ignorado'}
                time.sleep(intervalo)
                tabela, cobertura = parse_cids(requisitar('POST', form['action'], selecao), ano,
                                               {c: c for c in CODIGOS})
                if not set(cobertura).issubset(meses) or (tabela.sum() > matriz.sum()).any():
                    raise ValueError('Diagnóstico diverge da cobertura ou controle de todas as causas.')
                for mes in meses:
                    for cid in CODIGOS:
                        linhas.append({'Recorte': recorte, 'Ano': ano, 'Mês': mes, 'CID': cid,
                                       'Óbitos': int(tabela.at[cid, mes])})
                print(ano, recorte, 'OK', flush=True)
        form_final = parse_form(requisitar('GET', URL))
        meta['revisao_fim'] = form_final['revision']
        if meta['revisao_inicio'] != meta['revisao_fim']:
            raise ValueError('A atualização declarada da fonte mudou durante a consulta.')
        resultado = pd.DataFrame(linhas)
        if anterior_meta:
            if anterior_meta['recortes'] != meta['recortes']:
                raise ValueError('Recortes diagnósticos mudaram; reconsultar toda a referência.')
            resultado = pd.concat([anterior[~anterior.Ano.isin(anos)], resultado], ignore_index=True)
        resultado = resultado.sort_values(['Recorte', 'Ano', 'Mês', 'CID']).reset_index(drop=True)
        nome = 'diagnostico_causas.csv'
        resultado.to_csv(evidencias / nome, index=False)
        destino = saida / nome
        temp = destino.with_suffix('.tmp.csv')
        temp.write_bytes((evidencias / nome).read_bytes())
        temp.replace(destino)
        meta['sha256_csv'] = hashlib.sha256(destino.read_bytes()).hexdigest()
        for ano in anos:
            meta['origem_por_ano'][str(ano)] = {'revisao': meta['revisao_fim'],
                                              'consultado_utc': meta['consultado_utc'],
                                              'sha256_csv_origem': meta['sha256_csv']}
        meta['anos'] = sorted(int(a) for a in meta['cobertura'])
        meta['status'] = 'disponivel'
        meta['linhas'] = len(resultado)
    except Exception as exc:
        meta.update(status='indisponivel', erro=f'{type(exc).__name__}: {exc}')
    finally:
        sessao.close()
        meta['requisicoes_http'] = len(meta['respostas'])
        write_json(evidencias / 'execucao.json', meta)
        publico = meta
        if meta['status'] == 'indisponivel' and anterior_meta:
            publico = dict(anterior_meta)
            publico.update(status='obsoleto', ultima_tentativa_utc=meta['consultado_utc'],
                           erro=meta['erro'], requisicoes_ultima_tentativa=meta['requisicoes_http'])
        write_json(saida / 'diagnostico_causas_meta.json', publico)
    return meta


if __name__ == '__main__':
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--anos', nargs='+', type=int, default=list(range(2022, 2027)))
    ap.add_argument('--saida', type=Path, default=DADOS)
    ap.add_argument('--evidencias', type=Path, required=True, help='Pasta nova; nunca sobrescreve evidências.')
    args = ap.parse_args()
    estado = consultar(args.anos, args.saida, args.evidencias)
    print(json.dumps({k: v for k, v in estado.items() if k != 'respostas'}, ensure_ascii=False, indent=2))
    raise SystemExit(0 if estado['status'] == 'disponivel' else 1)
