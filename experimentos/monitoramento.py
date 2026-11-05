"""Experimento reprodutível do monitoramento estatístico mensal por gráficos de controle.

Executa, sem consultar fontes externas e com os parâmetros do config.toml:

1. verificação da implementação com a série e os resultados publicados por Barros (2021);
2. fase I (pressupostos, X–AM com exclusão iterativa, parâmetros) e fase II
   (X–AM e EWMA nos meses do ano monitorado) dos três indicadores no Espírito Santo;
3. leitura quadrimestral (isolada e acumulada) da fase II;
4. sensibilidade da fase I: todas as janelas predefinidas de 24, 36, 48 e 64 meses;
5. aplicação retrospectiva da referência fixa, ano a ano, de 2020 ao ano monitorado,
   e evento conhecido (fevereiro de 2017) como exemplo de exclusão na fase I;
6. viabilidade nas regiões de saúde (pressupostos e contagens mensais);
7. desempenho teórico (ARL) dos gráficos X, X̄ quadrimestral e EWMA;
8. boletim em Markdown para a vigilância e, com --figuras, as figuras em PNG.

Uso: python -m experimentos.monitoramento [--saida PASTA] [--figuras]
"""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import hashlib
import json
import math
from pathlib import Path
import platform

import numpy as np
import pandas as pd

from configuracao import DADOS, RAIZ
from dominio.dados import carregar, recortar, INDICADORES, diagnostico_causas
from dominio import monitoramento as mon
from dominio.monitoramento import TAXA

CURTOS = {'Suicídio geral': 'Suicídio', 'Homicídios — jovens de 15 a 29 anos': 'Homicídio 15–29',
          'Homicídios — mulheres de 10 a 59 anos': 'Homicídio mulheres 10–59'}
ARQUIVOS = {'Suicídio geral': 'suicidio', 'Homicídios — jovens de 15 a 29 anos': 'homicidio_jovens',
            'Homicídios — mulheres de 10 a 59 anos': 'homicidio_mulheres'}

# Valores publicados por Barros (2021), usados para verificar a implementação.
PUBLICADO_BARROS = [
    ('Descritiva', 'Média (fase I, 48 meses)', 42.60), ('Descritiva', 'Mediana', 42.47),
    ('Descritiva', 'Variância', 10.27), ('Descritiva', 'Desvio-padrão', 3.20),
    ('Descritiva', 'Coeficiente de variação (%)', 7.52), ('Descritiva', 'Amplitude', 18.44),
    ('Descritiva', '1º quartil', 40.64), ('Descritiva', '3º quartil', 44.10),
    ('Pressuposto', 'Lilliefors (valor-p)', 0.07903), ('Pressuposto', 'Ljung–Box, defasagem 1 (valor-p)', 0.857),
    ('Pressuposto', 'Dickey–Fuller aumentado (valor-p)', 0.04679), ('Pressuposto', 'Cox–Stuart (valor-p)', 0.6171),
    ('Pressuposto', 'Fisher (valor-p)', 0.8663829),
    ('X–AM, iteração 1 (48 meses)', 'LIC X', 34.02), ('X–AM, iteração 1 (48 meses)', 'LM X', 42.60),
    ('X–AM, iteração 1 (48 meses)', 'LSC X', 51.19), ('X–AM, iteração 1 (48 meses)', 'LM AM', 3.22),
    ('X–AM, iteração 1 (48 meses)', 'LSC AM', 10.54),
    ('X–AM, iteração 2 (47 meses)', 'LIC X', 34.57), ('X–AM, iteração 2 (47 meses)', 'LM X', 42.34),
    ('X–AM, iteração 2 (47 meses)', 'LSC X', 50.11), ('X–AM, iteração 2 (47 meses)', 'LM AM', 2.92),
    ('X–AM, iteração 2 (47 meses)', 'LSC AM', 9.54),
    ('X–AM, iteração 3 (46 meses)', 'LIC X', 34.78), ('X–AM, iteração 3 (46 meses)', 'LM X (μ0)', 42.26),
    ('X–AM, iteração 3 (46 meses)', 'LSC X', 49.73), ('X–AM, iteração 3 (46 meses)', 'LM AM', 2.80),
    ('X–AM, iteração 3 (46 meses)', 'LSC AM', 9.17), ('X–AM, iteração 3 (46 meses)', 'σ0', 2.49),
]


def _sha(caminho: Path) -> str:
    return hashlib.sha256(caminho.read_bytes()).hexdigest()


def serie_barros() -> pd.DataFrame:
    b = pd.read_csv(Path(__file__).with_name('dados_barros2021.csv'))
    s = pd.DataFrame({'Período': pd.to_datetime(b['periodo'] + '-01'), TAXA: b['taxa'].astype(float)})
    s['Ano'], s['Mês'] = s['Período'].dt.year, s['Período'].dt.month
    s['Óbitos'], s['População'] = np.nan, np.nan
    return s


def verificar_barros(saida: Path) -> pd.DataFrame:
    """Reproduz os resultados de Barros (2021) e compara com os valores publicados."""
    s = serie_barros()
    r = mon.analisar(s, '2017-01-01', '2020-12-01', lam=.1, largura_ewma=2.701,
                     defasagens_lb=(1,), automatico=True, metodo_cox='normal')
    d = r.descritivas
    p = r.pressupostos.set_index('Teste')['Valor-p']
    it = r.iteracoes
    reproduzido = [d['Média'], d['Mediana'], d['Variância'], d['Desvio-padrão'], d['Coeficiente de variação (%)'],
                   d['Amplitude'], d['1º quartil (Q1)'], d['3º quartil (Q3)'],
                   p['Lilliefors'], p['Ljung–Box (defasagem 1)'], p['Dickey–Fuller aumentado'], p['Cox–Stuart'],
                   p['Fisher (periodograma)']]
    for i in range(3):
        linha = it.iloc[i]
        reproduzido += [linha['LIC X'], linha['μ0'], linha['LSC X'], linha['AM média'], linha['LSC AM']]
    reproduzido.append(r.params.sigma0)
    tabela = pd.DataFrame(PUBLICADO_BARROS, columns=['Grupo', 'Medida', 'Publicado'])
    tabela['Reproduzido'] = reproduzido
    tabela['Diferença absoluta'] = (tabela['Reproduzido'] - tabela['Publicado']).abs()
    sinais = {
        'Exclusões na fase I': ', '.join(r.params.excluidos),
        'Sinais X na fase II': ', '.join(mon.rotulo_mes(a) for a, b in zip(r.fase_ii['Período'], r.fase_ii['Sinal X']) if b),
        'Sinais AM na fase II': ', '.join(mon.rotulo_mes(a) for a, b in zip(r.fase_ii['Período'], r.fase_ii['Sinal AM']) if b),
        'Sinais EWMA na fase I': ', '.join(mon.rotulo_mes(a) for a, b in zip(r.ewma_fase_i['Período'], r.ewma_fase_i['Sinal EWMA']) if b),
        'Sinais EWMA na fase II': ', '.join(mon.rotulo_mes(a) for a, b in zip(r.fase_ii['Período'], r.fase_ii['Sinal EWMA']) if b) or 'Nenhum',
    }
    tabela.to_csv(saida / 'verificacao_barros2021.csv', index=False)
    (saida / 'verificacao_barros2021_sinais.json').write_text(json.dumps(sinais, ensure_ascii=False, indent=2), encoding='utf-8')
    return tabela, sinais, r


def tabela_arl(lam: float, largura_ewma: float, largura: float) -> pd.DataFrame:
    linhas = []
    for delta in (0, .5, 1, 1.5, 2, 3):
        x = mon.arl_shewhart(delta, largura)
        q = mon.arl_shewhart(2 * delta, largura)  # X̄ com subgrupo de 4 meses: deslocamento em σ/√4
        e = mon.arl_ewma(lam, largura_ewma, delta)
        linhas.append({'Deslocamento (σ0)': delta, 'ARL gráfico X (meses)': x,
                       'ARL quadrimestral X̄, n = 4 (meses)': 4 * q, 'ARL EWMA (meses)': e})
    return pd.DataFrame(linhas)


def primeiro(df: pd.DataFrame, coluna: str) -> str:
    sub = df[df[coluna] != '']
    return mon.rotulo_mes(sub['Período'].iloc[0]) if not sub.empty else 'Sem sinal'


def resumo_sinais(r: mon.Resultado) -> dict:
    f2 = r.fase_ii
    consolidados = f2[~f2['Em consolidação']]
    return {
        'X (aumento)': int((consolidados['Sinal X'] == 'Aumento').sum()),
        'X (redução)': int((consolidados['Sinal X'] == 'Redução').sum()),
        'AM': int((consolidados['Sinal AM'] != '').sum()),
        'EWMA (aumento)': int((consolidados['Sinal EWMA'] == 'Aumento').sum()),
        'EWMA (redução)': int((consolidados['Sinal EWMA'] == 'Redução').sum()),
        'Primeiro sinal EWMA': primeiro(consolidados, 'Sinal EWMA'),
        'Primeiro sinal X': primeiro(consolidados, 'Sinal X'),
        'Meses avaliados': int(len(f2)), 'Meses em consolidação': int(f2['Em consolidação'].sum()),
    }


def executar(saida: Path, figuras: bool = False) -> dict:
    saida.mkdir(parents=True, exist_ok=True)
    cfg = mon.ler_protocolo(RAIZ / 'config.toml')
    lam, le, lx = float(cfg['lambda_ewma']), float(cfg['largura_ewma']), float(cfg['largura_x'])
    dias, lags = int(cfg['dias_consolidacao']), tuple(cfg['defasagens_ljung_box'])
    metodo_cox = cfg['metodo_cox']
    f, p, g, meta = carregar()
    base = mon.data_atualizacao(meta)
    regioes = pd.read_csv(DADOS / 'regioes_pdr2024.csv', dtype={'cod_mun_res': str})
    estado = g.cod_mun_res.tolist()

    tab_barros, sinais_barros, r_barros = verificar_barros(saida)

    series, press, params, fase1, iters, ewma1, fase2, quads, resumo = [], [], [], [], [], [], [], [], []
    resultados, periodos, serie_estado = {}, {}, {}
    padrao, minimo, meses_f2 = int(cfg['meses_padrao_fase1']), int(cfg['meses_minimos_fase1']), int(cfg['meses_fase2'])
    for indicador in INDICADORES:
        nf, npop = recortar(f, p, indicador, estado)
        s = mon.serie_mensal(nf, npop)
        serie_estado[indicador] = s
        series.append(s.assign(Indicador=indicador))
        if indicador in cfg['fase1']:
            inicio, fim = cfg['fase1'][indicador]
        else:  # referência fixa anterior ao ano do último mês disponível
            regra = mon.referencia_do_ano(s, int(s['Período'].max().year), padrao, minimo, float(cfg['alfa']), lags)
            inicio, fim = f"{regra['inicio']:%Y-%m}", f"{regra['fim']:%Y-%m}"
        fim2 = mon.fim_fase2(fim, meses_f2)
        periodos[indicador] = (inicio, fim, fim2)
        excluir = [mon.mes(v) for v in cfg['exclusoes'].get(indicador, [])]
        r = mon.analisar(s, mon.mes(inicio), mon.mes(fim), fim2, lam=lam, largura_ewma=le, largura=lx,
                         excluir=excluir, automatico=bool(cfg['exclusao_automatica']), data_base=base,
                         dias_consolidacao=dias, defasagens_lb=lags,
                         alfa=float(cfg['alfa']), max_exclusao=float(cfg['max_exclusao']), metodo_cox=metodo_cox)
        resultados[indicador] = r
        ctx = {'Indicador': indicador}
        press.append(r.pressupostos.assign(**ctx))
        params.append({**ctx, **r.params.como_dict(), 'óbitos médios por mês (fase I)': float(r.referencia['Óbitos'].mean()),
                       'definição da fase I': 'Período explícito' if indicador in cfg['fase1'] else f'Janela fixa de {padrao} meses',
                       **{f'descritiva: {k}': v for k, v in r.descritivas.items()}})
        fase1.append(r.fase_i.assign(**ctx))
        iters.append(r.iteracoes.assign(**ctx))
        ewma1.append(r.ewma_fase_i.assign(**ctx))
        fase2.append(r.fase_ii.assign(**ctx))
        quads.append(r.quadrimestral.assign(**ctx))
        resumo.append({**ctx, **resumo_sinais(r)})

    # Mesma fase II e mesmos parâmetros em todos os cenários; nenhuma seleção por valores-p.
    janelas = []
    for indicador in INDICADORES:
        s = serie_estado[indicador]
        _, fim, fim2 = periodos[indicador]
        tab = mon.sensibilidade(s, fim, fim2, lam=lam, largura_ewma=le, largura=lx, data_base=base,
                                dias_consolidacao=dias, defasagens_lb=lags, alfa=float(cfg['alfa']),
                                max_exclusao=float(cfg['max_exclusao']), automatico=bool(cfg['exclusao_automatica']),
                                excluir=cfg['exclusoes'].get(indicador, []), metodo_cox=metodo_cox)
        janelas.append(tab.assign(Indicador=indicador))
    pd.concat(janelas, ignore_index=True).to_csv(saida / 'sensibilidade_fase1.csv', index=False)

    # Complementos exploratórios: não selecionam a referência nem alteram os indicadores oficiais.
    tab_kpss, residuos, poisson, calendario, longas, complementar = [], [], [], [], [], []
    for indicador, r in resultados.items():
        inicio, fim, fim2 = periodos[indicador]
        estat, lag, valor_p = mon.kpss(r.referencia[TAXA])
        tab_kpss.append({'Indicador': indicador, 'Teste': 'KPSS (constante e tendência)',
                         'Hipótese nula (H0)': 'Estacionariedade em torno de tendência determinística',
                         'Estatística': estat, 'Defasagens Bartlett': lag, 'Valor-p tabelado': valor_p,
                         'Leitura do valor-p': '≤ 0,01' if valor_p == .01 else '≥ 0,10' if valor_p == .10 else 'Interpolado',
                         'Decisão': 'Rejeita H0' if valor_p < float(cfg['alfa']) else 'Não rejeita H0',
                         'Nota': 'Complementar ao ADF com constante e tendência; valor-p limitado à tabela'})
        residuos.append(mon.avaliar_residuos_tendencia(r.referencia[TAXA], float(cfg['alfa']), lags)
                         .assign(Indicador=indicador))
        poisson.append({'Indicador': indicador, **mon.comparar_poisson(r.referencia)})
        opcoes = dict(lam=lam, largura_ewma=le, largura=lx, data_base=base, dias_consolidacao=dias,
                       defasagens_lb=lags, alfa=float(cfg['alfa']), max_exclusao=float(cfg['max_exclusao']),
                       metodo_cox=metodo_cox, excluir=cfg['exclusoes'].get(indicador, []))
        calendario.append(mon.sensibilidade_calendario(serie_estado[indicador], inicio, fim, fim2, **opcoes)
                           .assign(Indicador=indicador))
        longas.append(mon.sensibilidade(serie_estado[indicador], fim, fim2, janelas=(72, 96, 120),
                                        automatico=bool(cfg['exclusao_automatica']), **opcoes).assign(Indicador=indicador))
        sinais1 = r.ewma_fase_i.loc[r.ewma_fase_i['Sinal EWMA'] != '']
        ano_anterior = mon.mes(fim).year
        s = serie_estado[indicador]
        antes = s.loc[s['Ano'] == ano_anterior]
        avaliados = r.fase_ii.loc[~r.fase_ii['Em consolidação']]
        meses_iguais = antes.loc[antes['Mês'].isin(avaliados['Mês'])]
        complementar.append({'Indicador': indicador, 'Ano anterior': ano_anterior,
                              'Média mensal ano anterior completo': float(antes[TAXA].mean()),
                              'Média mensal mesmos meses ano anterior': float(meses_iguais[TAXA].mean()),
                              'Média mensal fase II fora cautela': float(avaliados[TAXA].mean()),
                              'Meses fase II fora cautela': ', '.join(mon.rotulo_mes(v) for v in avaliados['Período']),
                              'Sinais EWMA fase I': len(sinais1),
                              'Meses com sinais EWMA fase I': ', '.join(mon.rotulo_mes(v) for v in sinais1['Período']),
                              'Sinais EWMA últimos 6 meses fase I': ', '.join(mon.rotulo_mes(v) for v in
                                  sinais1.loc[sinais1['Período'] >= mon.mes(fim) - pd.DateOffset(months=5), 'Período']),
                              'Probabilidade marginal AM': mon.probabilidade_sinal_am(),
                              'Nota': 'Comparações descritivas; prazo operacional não comprova completude ou mudança adicional'})
    pd.DataFrame(tab_kpss).to_csv(saida / 'kpss_complementar.csv', index=False)
    pd.concat(residuos, ignore_index=True).to_csv(saida / 'diagnosticos_residuos_tendencia.csv', index=False)
    pd.DataFrame(poisson).to_csv(saida / 'comparacao_poisson.csv', index=False)
    pd.concat(calendario, ignore_index=True).to_csv(saida / 'sensibilidade_calendario.csv', index=False)
    pd.concat(longas, ignore_index=True).to_csv(saida / 'sensibilidade_janelas_longas.csv', index=False)
    pd.DataFrame(complementar).to_csv(saida / 'resumo_complementar.csv', index=False)

    # Viabilidade regional
    viabilidade = []
    for indicador in INDICADORES:
        inicio, fim, fim2 = periodos[indicador]
        for regiao, sub in regioes.groupby('regiao_saude'):
            nf, npop = recortar(f, p, indicador, sub.cod_mun_res.tolist())
            s = mon.serie_mensal(nf, npop)
            r = mon.analisar(s, mon.mes(inicio), mon.mes(fim), fim2, lam=lam, largura_ewma=le, largura=lx, data_base=base,
                             dias_consolidacao=dias, defasagens_lb=lags, alfa=float(cfg['alfa']),
                             max_exclusao=float(cfg['max_exclusao']), automatico=bool(cfg['exclusao_automatica']),
                             excluir=[mon.mes(v) for v in cfg['exclusoes'].get(indicador, [])], metodo_cox=metodo_cox)
            pv = r.pressupostos.set_index('Teste')['Valor-p']
            viabilidade.append({'Indicador': indicador, 'Região de saúde': regiao,
                                'Óbitos por mês (média fase I)': float(r.referencia['Óbitos'].mean()),
                                'Meses sem óbito na fase I': int((r.referencia['Óbitos'] == 0).sum()),
                                'Lilliefors (p)': float(pv['Lilliefors']),
                                'Ljung–Box defasagem 1 (p)': float(pv['Ljung–Box (defasagem 1)']),
                                'Ljung–Box defasagens 1–12 (p)': float(pv.get('Ljung–Box (defasagens 1 a 12)', np.nan)),
                                'Cox–Stuart (p)': float(pv['Cox–Stuart']),
                                'Meses excluídos na fase I': len(r.params.excluidos),
                                'Recomendação': ('Sem impedimento detectado na triagem; não comprova adequação'
                                                 if r.params.estavel and r.referencia['Óbitos'].mean() >= 10
                                                 and not (r.referencia['Óbitos'] == 0).any()
                                                 and not r.pressupostos.loc[r.pressupostos['Teste'].str.startswith(('Lilliefors', 'Ljung', 'Cox', 'Fisher')), 'Valor-p'].lt(cfg['alfa']).any()
                                                 else 'Com ressalvas; investigar contagens e pressupostos')})
    pd.DataFrame(viabilidade).to_csv(saida / 'viabilidade_regional.csv', index=False)

    # Avaliações retrospectivas
    retro = {}
    nf, npop = recortar(f, p, 'Homicídios — jovens de 15 a 29 anos', estado)
    s_hom = mon.serie_mensal(nf, npop)
    r_greve = mon.analisar(s_hom, '2016-01-01', '2019-12-01', '2020-12-01', lam=lam, largura_ewma=le, largura=lx,
                           data_base=base, dias_consolidacao=dias, defasagens_lb=lags, automatico=True,
                           alfa=float(cfg['alfa']), max_exclusao=float(cfg['max_exclusao']), metodo_cox=metodo_cox)
    r_greve.iteracoes.to_csv(saida / 'retrospectiva_homicidio_2016_2019_iteracoes.csv', index=False)
    r_greve.pressupostos.to_csv(saida / 'retrospectiva_homicidio_2016_2019_pressupostos.csv', index=False)
    retro['evento_conhecido'] = {
        'carater': 'Exemplo retrospectivo exploratório com exclusão automática; não define o protocolo prospectivo',
        'indicador': 'Homicídios — jovens de 15 a 29 anos', 'fase_I': 'Jan/2016–Dez/2019',
        'primeira_iteracao_sinais': r_greve.iteracoes.iloc[0]['Sinais'],
        'fevereiro_2017_taxa': float(s_hom.loc[s_hom['Período'] == '2017-02-01', TAXA].iloc[0]),
        'fevereiro_2017_obitos': int(s_hom.loc[s_hom['Período'] == '2017-02-01', 'Óbitos'].iloc[0]),
        'lsc_iteracao_1': float(r_greve.iteracoes.iloc[0]['LSC X']),
        'mu0_iteracao_1': float(r_greve.iteracoes.iloc[0]['μ0']),
        'fase_I_estavel': bool(r_greve.params.estavel), 'excluidos': list(r_greve.params.excluidos),
        'pressupostos_rejeitados': r_greve.pressupostos.loc[r_greve.pressupostos['Decisão'] == 'Rejeita H0', 'Teste'].tolist(),
    }
    # Retrospectivas exploratórias com referência fixa anterior a cada ano monitorado
    retro_regra = []
    ano_final = max(int(mon.mes(v[1]).year) + 1 for v in periodos.values())
    for indicador in INDICADORES:
        s = serie_estado[indicador]
        for ano_mon in range(2020, ano_final + 1):
            regra = mon.referencia_do_ano(s, ano_mon, padrao, minimo, float(cfg['alfa']), lags)
            rr = mon.analisar(s, regra['inicio'], regra['fim'], mon.fim_fase2(regra['fim'], 12), lam=lam,
                              largura_ewma=le, largura=lx, data_base=base, dias_consolidacao=dias, defasagens_lb=lags,
                              alfa=float(cfg['alfa']), max_exclusao=float(cfg['max_exclusao']),
                              automatico=bool(cfg['exclusao_automatica']),
                              excluir=[mon.mes(v) for v in cfg['exclusoes'].get(indicador, [])
                                       if regra['inicio'] <= mon.mes(v) <= regra['fim']], metodo_cox=metodo_cox)
            f2r = rr.fase_ii
            cons = f2r[~f2r['Em consolidação']]
            qr = rr.quadrimestral
            qi = qr[(qr['Leitura'] == 'Quadrimestre isolado') & (qr['Sinal'] != '')]
            retro_regra.append({
                'Indicador': indicador, 'Ano monitorado': ano_mon,
                'Fase I': f"{mon.rotulo_mes(regra['inicio'])}–{mon.rotulo_mes(regra['fim'])}", 'Meses na fase I': regra['meses'],
                'Referência fixa predefinida': True, 'Meses excluídos': ', '.join(rr.params.excluidos) or 'Nenhum',
                'μ0 × 12': 12 * rr.params.mu0, 'Taxa média mensal × 12 no ano': 12 * float(cons[TAXA].mean()),
                'Variação em relação a μ0 (%)': 100 * (float(cons[TAXA].mean()) / rr.params.mu0 - 1),
                'Meses avaliados': int(len(cons)), 'Meses em consolidação': int(len(f2r) - len(cons)),
                'Primeiro sinal EWMA (consolidado)': primeiro(cons, 'Sinal EWMA'),
                'Sentido do EWMA': (cons.loc[cons['Sinal EWMA'] != '', 'Sinal EWMA'].iloc[0]
                                    if (cons['Sinal EWMA'] != '').any() else ''),
                'Meses com sinal EWMA': int((cons['Sinal EWMA'] != '').sum()),
                'Sinais X ou AM': '; '.join(f"{mon.rotulo_mes(a)} ({b or c})" for a, b, c in
                                            cons.loc[(cons['Sinal X'] != '') | (cons['Sinal AM'] != ''),
                                                    ['Período', 'Sinal X', 'Sinal AM']].itertuples(index=False)) or 'Nenhum',
                'Quadrimestres isolados com sinal': '; '.join(f"{a} ({b})" for a, b in zip(qi['Quadrimestre'], qi['Sinal']))
                                                    or 'Nenhum'})
    tab_regra = pd.DataFrame(retro_regra)
    tab_regra.to_csv(saida / 'aplicacao_retrospectiva_regra.csv', index=False)
    retro['regra_anual'] = {
        'anos_avaliados': int(len(tab_regra)),
        'anos_com_sinal_ewma': int((tab_regra['Meses com sinal EWMA'] > 0).sum()),
        'variacao_media_abs_com_sinal': float(tab_regra.loc[tab_regra['Meses com sinal EWMA'] > 0,
                                                            'Variação em relação a μ0 (%)'].abs().mean()),
        'variacao_media_abs_sem_sinal': float(tab_regra.loc[tab_regra['Meses com sinal EWMA'] == 0,
                                                            'Variação em relação a μ0 (%)'].abs().mean()),
    }
    (saida / 'retrospectivas.json').write_text(json.dumps(retro, ensure_ascii=False, indent=2, default=str), encoding='utf-8')

    arl = tabela_arl(lam, le, lx)
    arl.to_csv(saida / 'arl.csv', index=False)

    for nome, tabelas in [('serie_mensal', series), ('pressupostos', press), ('fase1', fase1),
                          ('iteracoes_fase1', iters), ('ewma_fase1', ewma1), ('fase2', fase2), ('quadrimestral', quads)]:
        pd.concat(tabelas, ignore_index=True).to_csv(saida / f'{nome}.csv', index=False)
    pd.DataFrame(params).to_csv(saida / 'parametros.csv', index=False)
    pd.DataFrame(resumo).to_csv(saida / 'resumo_sinais.csv', index=False)

    boletim(saida, resultados, base, cfg)
    if figuras:
        from experimentos import figuras as fig
        fig.gerar(saida / 'figuras', resultados, r_barros, r_greve, s_hom, cfg)
        # Relatórios em PDF do painel (nível estadual, protocolo do config.toml), com as páginas em PNG
        from painel.relatorio import relatorio_monitoramento, salvar_paginas
        pasta = saida / 'relatorios'
        pasta.mkdir(parents=True, exist_ok=True)
        for indicador, r in resultados.items():
            consol = r.fase_ii.loc[r.fase_ii['Em consolidação'], 'Período'] if not r.fase_ii.empty else []
            contexto = dict(indicador=indicador, territorio='Espírito Santo', granularidade='Estadual', sexo='Todos',
                            base=f'{pd.Timestamp(base):%d/%m/%Y}', consolidacao=', '.join(mon.rotulo_mes(v) for v in consol))
            try:
                causas, nota_causas = diagnostico_causas(indicador)
                contexto.update(diagnostico_causas=causas.to_dict('records'), nota_causas=nota_causas)
            except (OSError, ValueError, KeyError):
                contexto['diagnostico_causas'] = []
            proto = dict(modo='Protocolo do TCC (config.toml)', lam=lam, le=le, lx=lx, dias=dias,
                         automatico=bool(cfg['exclusao_automatica']), justificativa='')
            media = float(r.referencia['Óbitos'].mean())
            pdf, paginas = relatorio_monitoramento(r, contexto, proto, tabela_arl(lam, le, lx),
                                                   ('Nível estadual', f'Média de {media:.1f} óbitos por mês na fase I.'.replace('.', ',', 1)),
                                                   guardar_paginas=True)
            (pasta / f'monitoramento_{ARQUIVOS[indicador]}.pdf').write_bytes(pdf)
            salvar_paginas(paginas, pasta, f'monitoramento_{ARQUIVOS[indicador]}', dpi=170)

    fontes = ['experimentos/monitoramento.py', 'experimentos/figuras.py', 'experimentos/dados_barros2021.csv',
              'dominio/monitoramento.py', 'dominio/dados.py', 'painel/relatorio.py', 'configuracao.py',
              'config.toml', 'etl/definicao_cid.py', 'requirements-lock.txt']
    entradas = ['dataset.zip', 'regioes_pdr2024.csv', 'pdr_meta.json',
                'diagnostico_causas.csv', 'diagnostico_causas_meta.json']
    manifesto = dict(
        protocolo=cfg['protocolo'], unidade_temporal='mês', gerado_utc=datetime.now(timezone.utc).isoformat(),
        referencia={k: [v[0], v[1]] for k, v in periodos.items()},
        fase2={k: [f"{mon.mes(v[1]) + pd.DateOffset(months=1):%Y-%m}", f'{v[2]:%Y-%m}'] for k, v in periodos.items()},
        exclusoes=cfg['exclusoes'],
        parametros=dict(lambda_ewma=lam, largura_ewma=le, largura_x=lx, alfa=cfg['alfa'],
                        metodo_cox=metodo_cox, probabilidade_marginal_am=mon.probabilidade_sinal_am(),
                        dias_consolidacao=dias, defasagens_ljung_box=list(lags),
                        exclusao_automatica=cfg['exclusao_automatica'], max_exclusao=cfg['max_exclusao'],
                        meses_fase2=meses_f2, meses_padrao_fase1=padrao,
                        janelas_sensibilidade=[24, 36, 48, 64], selecao_por_significancia=False,
                        complementos_exploratorios=['KPSS com tendência e Bartlett curto', 'Resíduos de tendência OLS',
                                                   'Dispersão Poisson', 'Calendário 30,4375/dias',
                                                   'Janelas de 72, 96 e 120 meses'],
                        arl_hipoteses='Normalidade, independência e parâmetros conhecidos; EWMA com limites assintóticos fixos'),
        data_base=str(base), sha256_dataset=_sha(DADOS / 'dataset.zip'),
        sha256_codigo={n: _sha(RAIZ / n) for n in fontes if (RAIZ / n).exists()},
        sha256_entradas={n: _sha(DADOS / n) for n in entradas if (DADOS / n).exists()},
        python=platform.python_version(), numpy=np.__version__, pandas=pd.__version__,
        definicao_cid=meta.get('definicao_cid', 'legada'),
        verificacao_barros2021=dict(maior_diferenca=float(tab_barros['Diferença absoluta'].max()), **sinais_barros),
        nota=('Sinais estatísticos orientam a investigação pela vigilância; não identificam causas. '
              f'Meses em consolidação usam convenção operacional de {dias} dias; o prazo não certifica completude. '
              'Pressupostos rejeitados limitam a interpretação; não provocam troca automática da referência.'))
    (saida / 'manifesto.json').write_text(json.dumps(manifesto, ensure_ascii=False, indent=2, default=str), encoding='utf-8')
    return manifesto


def boletim(saida: Path, resultados: dict, base, cfg: dict) -> None:
    """Resumo em Markdown do último mês e dos quadrimestres, para a rotina da vigilância."""
    linhas = [f'# Boletim do monitoramento estatístico mensal', '',
              f'Base atualizada até {pd.Timestamp(base):%d/%m/%Y}. Protocolo {cfg["protocolo"]}: '
              f'X–AM (L = {cfg["largura_x"]}) e EWMA (λ = {cfg["lambda_ewma"]}, L = {cfg["largura_ewma"]}).', '']
    for indicador, r in resultados.items():
        f2 = r.fase_ii
        linhas += [f'## {indicador}', '',
                   f'Fase I: {r.params.inicio}–{r.params.fim} ({r.params.n_controle} de {r.params.n_inicial} meses mantidos; '
                   f'exclusões: {", ".join(r.params.excluidos + r.params.manuais) or "nenhuma"}). '
                   f'μ0 = {r.params.mu0:.3f} e σ0 = {r.params.sigma0:.3f} por 100 mil por mês.', '',
                   '| Mês | Óbitos | Taxa | X | AM | EWMA | Situação |', '|---|---:|---:|---|---|---|---|']
        for _, l in f2.tail(6).iterrows():
            sinais = ['Suspenso'] * 3 if l['Em consolidação'] else [l[f'Sinal {c}'] or '—' for c in ('X', 'AM', 'EWMA')]
            linhas.append(f"| {mon.rotulo_mes(l['Período'])} | {int(l['Óbitos'])} | {l[TAXA]:.3f} | {sinais[0]} | "
                          f"{sinais[1]} | {sinais[2]} | "
                          f"{'Em consolidação' if l['Em consolidação'] else 'Fora da cautela'} |")
        q = r.quadrimestral
        if not q.empty:
            linhas += ['', '| Ano | Quadrimestre | Leitura | Meses | Taxa | Esperado | Limites | Sinal |',
                       '|---|---|---|---|---:|---:|---|---|']
            for _, l in q.tail(6).iterrows():
                linhas.append(f"| {l['Ano']} | {l['Quadrimestre']} | {l['Leitura']} | {l['Meses']} | {l[TAXA]:.2f} | "
                              f"{l['Esperado (m·μ0)']:.2f} | {l['LIC']:.2f}–{l['LSC']:.2f} | {l['Sinal'] or l['Situação da sinalização']} |")
        linhas.append('')
    linhas.append('Sinais indicam afastamento do comportamento esperado e devem ser investigados; não estabelecem causas.')
    (saida / 'boletim.md').write_text('\n'.join(linhas), encoding='utf-8')


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument('--saida', type=Path, default=RAIZ / 'resultados_monitoramento')
    ap.add_argument('--figuras', action='store_true', help='Gera as figuras em PNG (requer matplotlib).')
    args = ap.parse_args()
    manifesto = executar(args.saida, args.figuras)
    print(f'Resultados em {args.saida}. Maior diferença na verificação de Barros (2021): '
          f"{manifesto['verificacao_barros2021']['maior_diferenca']:.4f}.")


if __name__ == '__main__':
    main()
