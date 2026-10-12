"""Calcula, para a base atual, os valores de regressão usados em tests/test_dashboard.py.

Uso: python -m etl.gerar_referencias

Os números devem ser conferidos com o TabNet/SESA (mesmos códigos, anos e recortes) antes de
serem registrados em tests/referencias.json, na chave da definição de CID impressa. Não ajuste
dados para satisfazer testes: a referência documenta uma conferência externa.
"""
import json

from modelo import INDICADORES, carregar, medidas, recortar
from .definicao_cid import DEFINICAO_LEGADA


def calcular():
    obitos, populacao, geografia, meta = carregar()
    todos = geografia.cod_mun_res
    anual, quadrimestre = {}, {}
    for nome in INDICADORES:
        fato, pop = recortar(obitos, populacao, nome, todos)
        anual[nome] = list(medidas(fato, pop, 2024, range(1, 13))[:2])
        quadrimestre[nome] = list(medidas(fato, pop, 2024, range(5, 9))[:2])
    municipio = geografia.loc[geografia.no_municipio == 'Jerônimo Monteiro', 'cod_mun_res']
    fato, pop = recortar(obitos, populacao, 'Suicídio geral', municipio)
    jeronimo = list(medidas(fato, pop, 2024, range(1, 13))[:2])
    fato, pop = recortar(obitos, populacao, 'Suicídio geral', todos)
    janeiro_agosto = medidas(fato, pop, 2024, range(1, 9))[0]
    definicao = meta.get('definicao_cid', {}).get('id', DEFINICAO_LEGADA)
    return {definicao: {'anual_2024': anual,
                        'segundo_quadrimestre_2024': quadrimestre,
                        'suicidio_jeronimo_monteiro_2024': jeronimo,
                        'suicidio_jan_ago_2024': janeiro_agosto}}


if __name__ == '__main__':
    print(json.dumps(calcular(), ensure_ascii=False, indent=2))
