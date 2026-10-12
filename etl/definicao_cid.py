"""Definição dos numeradores conforme as fichas de qualificação do PES-ES 2024–2027.

Fichas 1.8.15 e 1.8.16 (homicídios/agressões): causa básica X85–Y09, Y22–Y24, Y35,
Y87.1 e Y89.0. Ficha 1.8.17 (suicídio): causa básica X60–X84 e Y87.0.

Uma categoria de três caracteres inclui todas as suas subcategorias. Y87.0, Y87.1 e
Y89.0 são subcategorias de quatro caracteres; por isso, a seleção no TabNet da SESA usa o
campo de subcategorias do capítulo XX, e não o campo de causas com três dígitos, que não
consegue separar Y87.0 de Y87.1/Y87.2 nem Y89.0 de Y89.1/Y89.9.

Este módulo não depende de rede nem de bibliotecas externas: é a fonte única da regra,
usada pelo ETL, pela validação e pelo painel.
"""
import hashlib
import json
import re

CAMPO_SUBCATEGORIA = 'SSubcategorias_(20)'
CAMPO_CATEGORIA = 'SCausas_3_Dígitos'
LINHA_CATEGORIA = 'Causas 3 Dígitos'
FONTE_DEFINICAO = ('Fichas de qualificação dos indicadores 1.8.15, 1.8.16 e 1.8.17 '
                   'do Plano Estadual de Saúde do Espírito Santo 2024–2027 (SESA/ES)')
DEFINICAO_LEGADA = 'legada_X85-Y09_X60-X84'


def _intervalo(letra, inicio, fim):
    return [f'{letra}{numero:02d}' for numero in range(inicio, fim + 1)]


DEFINICAO_CID = {
    'Homicídio': {
        'categorias': _intervalo('X', 85, 99) + _intervalo('Y', 0, 9) + ['Y22', 'Y23', 'Y24', 'Y35'],
        'subcategorias': ['Y87.1', 'Y89.0'],
    },
    'Suicídio': {
        'categorias': _intervalo('X', 60, 84),
        'subcategorias': ['Y87.0'],
    },
}
DESCRICAO_CID = {
    'Homicídio': 'X85–Y09, Y22–Y24, Y35, Y87.1 e Y89.0',
    'Suicídio': 'X60–X84 e Y87.0',
}
ID_DEFINICAO_CID = hashlib.sha256(
    json.dumps({'campo': CAMPO_SUBCATEGORIA, 'definicao': DEFINICAO_CID},
               ensure_ascii=False, sort_keys=True).encode()
).hexdigest()[:12]

_ROTULO_SUBCATEGORIA = re.compile(r'^([A-Z]\d{2})(?:\.(\d))?(?:\s|$)')
_ROTULO_CATEGORIA = re.compile(r'^([A-Z]\d{2})(?:\s|$)')


def resumo_definicao():
    """Metadados gravados junto aos dados para rastrear a regra aplicada."""
    return {'id': ID_DEFINICAO_CID, 'codigos': DESCRICAO_CID, 'campo_tabnet': CAMPO_SUBCATEGORIA,
            'fonte': FONTE_DEFINICAO}


def codigos_detalhamento(causa):
    """Códigos usados no detalhamento por CID: categorias completas e subcategorias isoladas."""
    regra = DEFINICAO_CID[causa]
    return regra['categorias'] + regra['subcategorias']


def montar_selecao(opcoes_subcategoria, opcoes_categoria):
    """Traduz a definição em valores dos campos do formulário do TabNet.

    Recebe as opções ({'value', 'label'}) dos campos de subcategorias e de três dígitos.
    Para cada causa, devolve:
      valores            -> valores do campo de subcategorias que compõem o numerador;
      codigos            -> códigos do detalhamento (ex.: 'X85', 'Y35', 'Y87.1');
      valores_por_codigo -> valores do formulário correspondentes a cada código;
      linha_categoria    -> rótulo de três caracteres da tabulação -> código do detalhamento;
      equivalencia       -> valores das categorias completas nos dois campos, para o controle
                            que confirma que nenhum óbito fica sem subcategoria.
    Falha, em vez de seguir com seleção incompleta, se algum código exigido não existir.
    """
    por_categoria, por_subcategoria = {}, {}
    for opcao in opcoes_subcategoria:
        achado = _ROTULO_SUBCATEGORIA.match(opcao['label'])
        if not achado:
            continue
        categoria, digito = achado.group(1), achado.group(2)
        por_categoria.setdefault(categoria, []).append(opcao['value'])
        if digito is not None:
            codigo = f'{categoria}.{digito}'
            if codigo in por_subcategoria:
                raise ValueError(f'Subcategoria duplicada no formulário: {codigo}.')
            por_subcategoria[codigo] = opcao['value']
    categorias = {}
    for opcao in opcoes_categoria:
        achado = _ROTULO_CATEGORIA.match(opcao['label'])
        if achado:
            if achado.group(1) in categorias:
                raise ValueError('CID de três dígitos duplicado no formulário.')
            categorias[achado.group(1)] = opcao['value']

    selecao, usados = {}, {}
    for causa, regra in DEFINICAO_CID.items():
        valores_por_codigo, linha = {}, {}
        for categoria in regra['categorias']:
            if categoria not in por_categoria or categoria not in categorias:
                raise ValueError(f'Categoria {categoria} ausente no formulário; rever a definição de {causa}.')
            valores_por_codigo[categoria] = por_categoria[categoria]
            linha[categoria] = categoria
        for subcategoria in regra['subcategorias']:
            if subcategoria not in por_subcategoria:
                raise ValueError(f'Subcategoria {subcategoria} ausente no formulário; rever a definição de {causa}.')
            categoria = subcategoria[:3]
            if categoria in linha:
                raise ValueError(f'{subcategoria} conflita com outro código da categoria {categoria}.')
            valores_por_codigo[subcategoria] = [por_subcategoria[subcategoria]]
            linha[categoria] = subcategoria
        valores = [valor for lista in valores_por_codigo.values() for valor in lista]
        for valor in valores:
            if valor in usados:
                raise ValueError(f'O mesmo código não pode compor {usados[valor]} e {causa}.')
            usados[valor] = causa
        selecao[causa] = {
            'valores': valores,
            'codigos': list(valores_por_codigo),
            'valores_por_codigo': valores_por_codigo,
            'linha_categoria': linha,
            'equivalencia': {
                'subcategorias': [v for categoria in regra['categorias'] for v in por_categoria[categoria]],
                'categorias': [categorias[categoria] for categoria in regra['categorias']],
            },
        }
    return selecao


def descricoes_codigos(opcoes_subcategoria, opcoes_categoria):
    """Descrição publicada no TabNet para cada código do detalhamento."""
    descricoes = {}
    for opcao in opcoes_categoria:
        achado = re.match(r'^([A-Z]\d{2})\s+(.*)$', opcao['label'])
        if achado:
            descricoes[achado.group(1)] = achado.group(2).strip()
    for opcao in opcoes_subcategoria:
        achado = re.match(r'^([A-Z]\d{2}\.\d)\s+(.*)$', opcao['label'])
        if achado:
            descricoes[achado.group(1)] = achado.group(2).strip()
    return descricoes


def anos_fora_da_definicao(definicoes_por_ano, definicao=ID_DEFINICAO_CID):
    """Anos cuja extração não usou a definição informada (ausência = definição legada)."""
    return sorted(int(ano) for ano, valor in definicoes_por_ano.items() if valor != definicao)
