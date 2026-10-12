"""Concilia referências de regressão com tabulações independentes da SESA.

A extração principal particiona idade e sexo. Esta conferência consulta diretamente
os públicos elegíveis dos indicadores, sem somar os mesmos estratos de extração.
Só registra referências após concordância dos totais anuais, quadrimestrais e
municipal com a fonte, e validação do denominador anual já extraído.
"""
import argparse
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import time
from configuracao import RAIZ, ESTADO
from modelo import carregar, INDICADORES
from .definicao_cid import ID_DEFINICAO_CID
from .gerar_referencias import calcular
from .nucleo_tabnet import TabnetClient, query_definicao, URL, make_contract, parse_result, CID_FIELD, AGE_FIELD, ALL


def conferir(registrar=False):
    f, p, g, meta = carregar()
    if meta.get('definicao_cid', {}).get('id') != ID_DEFINICAO_CID:
        raise ValueError('Conferência requer toda a base reprocessada com os CIDs atuais.')
    referencia = calcular()[ID_DEFINICAO_CID]
    client = TabnetClient('requests')
    pasta = ESTADO / 'referencias' / datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S')
    pasta.mkdir(parents=True, exist_ok=False)
    contrato = make_contract(client.form, 2024, sorted(g.cod_mun_res))
    evidencias = []
    try:
        for indicador, cfg in INDICADORES.items():
            selecao = dict(contrato['base'])
            selecao[CID_FIELD] = contrato['cids'][cfg['causa']]
            selecao[AGE_FIELD] = sum([contrato['ages'][a] for a in cfg['idades']], []) if cfg['idades'] else [ALL]
            selecao['SSexo'] = contrato['sexes'][cfg['sexo']] if cfg['sexo'] else [ALL]
            time.sleep(3)
            raw = query_definicao(client,selecao)
            tabela, stats = parse_result(raw, 2024, sorted(g.cod_mun_res))
            if stats['months'] != list(range(1, 13)):
                raise ValueError('Conferência de 2024 exige doze meses disponíveis.')
            anual = int(tabela.to_numpy().sum())
            quadrimestre = int(tabela[list(range(5, 9))].to_numpy().sum())
            if anual != referencia['anual_2024'][indicador][0] or quadrimestre != referencia['segundo_quadrimestre_2024'][indicador][0]:
                raise ValueError(f'Tabulação independente diverge da base: {indicador}.')
            if indicador == 'Suicídio geral':
                codigo = g.loc[g.no_municipio.eq('Jerônimo Monteiro'), 'cod_mun_res'].iloc[0]
                if int(tabela.loc[codigo].sum()) != referencia['suicidio_jeronimo_monteiro_2024'][0]:
                    raise ValueError('Total de Jerônimo Monteiro divergente da fonte.')
                if int(tabela[list(range(1, 9))].to_numpy().sum()) != referencia['suicidio_jan_ago_2024']:
                    raise ValueError('Acumulado janeiro–agosto divergente da fonte.')
            nome = f'controle_{len(evidencias)+1}.html'
            (pasta / nome).write_text(raw, encoding='utf-8')
            evidencias.append(dict(indicador=indicador, anual=anual, segundo_quadrimestre=quadrimestre,
                                   selecao=selecao, html=nome, sha256=hashlib.sha256(raw.encode()).hexdigest()))
        # Reconsulta os totais para detectar revisão durante a própria conferência.
        for evidencia in evidencias:
            time.sleep(3)
            raw = query_definicao(client,evidencia['selecao'])
            antes, _ = parse_result((pasta / evidencia['html']).read_text(), 2024, sorted(g.cod_mun_res))
            depois, _ = parse_result(raw, 2024, sorted(g.cod_mun_res))
            if not antes.equals(depois): raise ValueError('A fonte mudou durante a conferência.')
        relatorio = dict(fonte=URL, status='conferido', extraido_utc=datetime.now(timezone.utc).isoformat(),
                         definicao_cid=contrato['definicao_cid'], revisao=contrato['revision'],
                         referencias=referencia, evidencias=evidencias,
                         nota='Conciliação com tabulações SIM/SESA; não atesta completude epidemiológica nem concordância com publicação fechada do PES.')
        (pasta / 'conferencia.json').write_text(json.dumps(relatorio, ensure_ascii=False, indent=2))
        if registrar:
            arq = RAIZ / 'tests' / 'referencias.json'
            conteudo = json.loads(arq.read_text())
            conteudo[ID_DEFINICAO_CID] = referencia
            arq.write_text(json.dumps(conteudo, ensure_ascii=False, indent=2)+'\n')
            (RAIZ / 'docs' / 'CONFERENCIA_REFERENCIAS.json').write_text(json.dumps(relatorio, ensure_ascii=False, indent=2)+'\n')
        print(json.dumps(dict(status='conferido', evidencias=str(pasta), referencias=referencia), ensure_ascii=False, indent=2))
    finally:
        client.close()


if __name__ == '__main__':
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--registrar', action='store_true', help='Registra somente após concordância com a fonte.')
    conferir(ap.parse_args().registrar)
