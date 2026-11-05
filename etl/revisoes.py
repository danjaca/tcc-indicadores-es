"""Catálogo de snapshots e comparação descritiva entre duas versões da base.

Uma diferença entre versões não identifica sua causa nem estima completude.
"""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
from zipfile import ZipFile

import pandas as pd

from dominio.dados import INDICADORES, recortar
from .nucleo_tabnet import write_json


def inventario(pasta: Path) -> dict:
    pasta = Path(pasta)
    arquivos = {p.name: {'bytes': p.stat().st_size,
                         'sha256': hashlib.sha256(p.read_bytes()).hexdigest()}
                for p in sorted(pasta.iterdir()) if p.is_file()}
    with ZipFile(pasta / 'dataset.zip') as z:
        meta = json.loads(z.read('disponibilidade.json'))
        hash_populacao = hashlib.sha256(z.read('d_populacao.csv')).hexdigest()
    return {'arquivos': arquivos, 'definicao_cid': meta.get('definicao_cid'),
            'sha256_d_populacao_csv': hash_populacao,
            'extracoes': meta.get('extracoes', {}), 'populacao': meta.get('populacao', {}),
            'pacote_atualizado': meta.get('pacote_atualizado'),
            'nota_populacao': 'Ano da estimativa e uso provisório conforme o pacote; '
                              'não certifica a revisão editorial mais recente da fonte.'}


def serie_snapshot(pasta: Path) -> tuple[pd.DataFrame, str | None]:
    """Mesmo numerador/denominador do SAD; ausência de cobertura não vira zero."""
    with ZipFile(Path(pasta) / 'dataset.zip') as z:
        meta = json.loads(z.read('disponibilidade.json'))
        with z.open('f_obitos.csv') as arq:
            f = pd.read_csv(arq, dtype={'cod_mun_res': str})
        with z.open('d_populacao.csv') as arq:
            p = pd.read_csv(arq, dtype={'cod_mun_res': str})
    f = f[f.ano.isin(meta['anos_disponiveis'])]
    municipios = sorted(set(f.cod_mun_res) | set(p.cod_mun_res))
    linhas = []
    for indicador in INDICADORES:
        nf, npop = recortar(f, p, indicador, municipios)
        den = npop.groupby('ano').populacao.sum(min_count=1)
        for (ano, mes), n in nf.groupby(['ano', 'mes']).Obitos.sum(min_count=1).items():
            d = den.get(ano, float('nan'))
            linhas.append({'Indicador': indicador, 'Período': f'{ano:04d}-{mes:02d}',
                           'Óbitos': n, 'População': d,
                           'Taxa por 100 mil': n / d * 100000 if pd.notna(d) and d > 0 else float('nan')})
    definicao = meta.get('definicao_cid')
    if isinstance(definicao, dict):
        definicao = definicao.get('id')
    return pd.DataFrame(linhas, columns=['Indicador', 'Período', 'Óbitos', 'População',
                                         'Taxa por 100 mil']), definicao


def comparar(anterior: Path, atual: Path) -> pd.DataFrame:
    a, cid_a = serie_snapshot(anterior)
    b, cid_b = serie_snapshot(atual)
    r = a.merge(b, on=['Indicador', 'Período'], how='outer', validate='one_to_one',
                suffixes=(' anterior', ' atual'), indicator=True)
    r['Situação'] = r.pop('_merge').astype(str).map(
        {'both': 'Comparável', 'left_only': 'Ausente na versão atual',
         'right_only': 'Novo mês disponível'})
    comparavel = r['Situação'].eq('Comparável')
    if cid_a is None or cid_b is None or cid_a != cid_b:
        r.loc[comparavel, 'Situação'] = 'Definição CID diferente ou não identificada'
        comparavel[:] = False
    for medida in ['Óbitos', 'População', 'Taxa por 100 mil']:
        r[f'Diferença {medida}'] = (r[f'{medida} atual'] - r[f'{medida} anterior']).where(comparavel)
    r['Variação óbitos (%)'] = (100 * r['Diferença Óbitos'] /
                                r['Óbitos anterior'].where(r['Óbitos anterior'] > 0))
    return r.sort_values(['Indicador', 'Período']).reset_index(drop=True)


def registrar_ciclo(lote: Path, estado: Path) -> dict:
    """Indexa cópias já preservadas pelo atualizador; não modifica seus dados."""
    lote, estado = Path(lote), Path(estado)
    manifesto = lote / 'snapshot.json'
    if manifesto.exists():
        raise FileExistsError(f'Snapshot já registrado: {lote.name}')
    anterior, atual = lote / 'dados_anteriores', lote / 'dados'
    revisoes = comparar(anterior, atual)
    revisoes.to_csv(lote / 'revisoes_mensais.csv', index=False)
    registro = {'id': lote.name, 'registrado_utc': datetime.now(timezone.utc).isoformat(),
                'anterior': inventario(anterior), 'atual': inventario(atual),
                'comparacao': 'revisoes_mensais.csv',
                'nota': 'Comparação de versões disponíveis, não curva de completude. '
                        'Diferenças podem envolver registros, classificação, cobertura ou denominadores; '
                        'não demonstram reclassificação individual nem completude definitiva.'}
    write_json(manifesto, registro)
    catalogo = estado / 'catalogo_snapshots.json'
    entradas = json.loads(catalogo.read_text()) if catalogo.exists() else []
    entradas.append({'id': lote.name, 'manifesto': f'lotes/{lote.name}/snapshot.json',
                     'sha256_manifesto': hashlib.sha256(manifesto.read_bytes()).hexdigest(),
                     'registrado_utc': registro['registrado_utc']})
    write_json(catalogo, entradas)
    return {'manifesto': str(manifesto), 'revisoes': str(lote / 'revisoes_mensais.csv')}


if __name__ == '__main__':
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--anterior', type=Path, required=True, help='Diretório contendo o dataset.zip anterior.')
    ap.add_argument('--atual', type=Path, required=True, help='Diretório contendo o dataset.zip atual.')
    ap.add_argument('--saida', type=Path, required=True, help='Novo CSV; não sobrescreve comparação anterior.')
    args = ap.parse_args()
    with args.saida.open('x', encoding='utf-8') as arquivo:
        comparar(args.anterior, args.atual).to_csv(arquivo, index=False)
