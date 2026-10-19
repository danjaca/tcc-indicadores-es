"""Modelos de monitoramento: ajuste apenas na fase I; aplicação na fase II.

Taxas por 100 mil; denominadores anuais, inclusive em períodos parciais.
Os modelos recebem uma série de períodos comparáveis (mesmos meses).
"""
from dataclasses import dataclass, asdict
import numpy as np
import pandas as pd
from scipy.stats import chi2, poisson, norm
from .dados import serie_historica

TAXA = 'Taxa por 100 mil'

@dataclass(frozen=True)
class Referencia:
    anos: tuple
    taxa: float
    sigma: float
    sigma_z: float
    dispersao: float
    p_sobredispersao: float
    q1: float
    mediana: float
    q3: float


def validar(t):
    if t.empty or t[['Óbitos', 'População', TAXA]].isna().any().any():
        raise ValueError('Série sem cobertura ou denominador completo; não preencher lacunas com zero.')
    if (t['População'] <= 0).any() or (t['Óbitos'] < 0).any():
        raise ValueError('População deve ser positiva e óbitos não negativos.')
    if not np.isfinite(t[['Óbitos', 'População', TAXA]].to_numpy(dtype=float)).all():
        raise ValueError('Valores não finitos na série.')
    if not np.allclose(t[TAXA], t['Óbitos'] / t['População'] * 100000):
        raise ValueError('Taxas incoerentes com contagens e população.')
    if t['Ano'].duplicated().any() or not t['Ano'].is_monotonic_increasing:
        raise ValueError('Anos devem ser únicos e cronológicos.')


def ajustar(t):
    validar(t)
    if not 5 <= len(t) <= 7:
        raise ValueError('Selecione de cinco a sete anos de referência completos.')
    if np.any(np.diff(t['Ano']) != 1):
        raise ValueError('A referência deve conter anos consecutivos; lacunas não são zeros.')
    taxa = float(t['Óbitos'].sum() / t['População'].sum() * 100000)
    if taxa <= 0:
        raise ValueError('Referência sem eventos: não é possível calibrar estes gráficos.')
    n = t['População'].to_numpy() / 100000
    z = (t[TAXA].to_numpy() - taxa) / np.sqrt(taxa / n)
    phi = float(np.sum(z*z) / (len(t)-1))
    sz = float(np.mean(np.abs(np.diff(z))) / 1.128)
    sigma = float(t[TAXA].std(ddof=1))
    # Com série constante, usa a variância Poisson média como escala de memória.
    sigma = max(sigma, float(np.sqrt(np.mean(taxa / n))))
    q1, med, q3 = map(float, t[TAXA].quantile([.25, .5, .75]))
    return Referencia(tuple(map(int, t['Ano'])), taxa, sigma, sz, phi,
                      float(chi2.sf(phi*(len(t)-1), len(t)-1)), q1, med, q3)


def aplicar(t, ref, peso=.2, largura=3., k=.5, h=5.):
    validar(t)
    if (t['Ano'] <= max(ref.anos)).any():
        raise ValueError('Fase II deve ser posterior à referência, sem sobreposição.')
    if not 0 < peso <= 1 or min(largura, k, h) <= 0:
        raise ValueError('Parâmetros inválidos.')
    out = t.copy()
    n = out['População'].to_numpy() / 100000
    sd = np.sqrt(ref.taxa / n)
    # Diagnóstico Pearson; alarga, sem estreitar limites por subdispersão.
    fator = max(1., ref.sigma_z) if ref.p_sobredispersao < .05 else 1.
    out['Método controle'] = 'u′ (Laney)' if fator > 1 else 'u (Poisson)'
    out['Referência'] = ref.taxa
    out['LIC u'] = np.maximum(0, ref.taxa - largura*sd)
    out['LSC u'] = ref.taxa + largura*sd
    out['LIC controle'] = np.maximum(0, ref.taxa - largura*sd*fator)
    out['LSC controle'] = ref.taxa + largura*sd*fator
    out['Sinal u'] = (out[TAXA] < out['LIC u']) | (out[TAXA] > out['LSC u'])
    out['Sinal controle'] = (out[TAXA] < out['LIC controle']) | (out[TAXA] > out['LSC controle'])
    ewma, cp, cm = ref.taxa, 0., 0.
    out['Q1'], out['Mediana'], out['Q3'] = ref.q1, ref.mediana, ref.q3
    rows = []
    anterior = max(ref.anos)
    passo = 0
    for ano, taxa in zip(t['Ano'], t[TAXA]):
        ano, taxa = int(ano), float(taxa)
        if ano != anterior+1:
            # Lacuna interrompe a memória: não simula observações ausentes.
            ewma, cp, cm, passo = ref.taxa, 0., 0., 0
        passo += 1
        ewma = peso*taxa + (1-peso)*ewma
        margem = largura*ref.sigma*np.sqrt(peso/(2-peso)*(1-(1-peso)**(2*passo)))
        li, ls = max(0., ref.taxa-margem), ref.taxa+margem
        cp = max(0., cp+(taxa-ref.taxa)/ref.sigma-k)
        cm = max(0., cm+(ref.taxa-taxa)/ref.sigma-k)
        sup, inf = cp > h, cm > h
        zona = ('Êxito' if taxa < ref.q1 else 'Segurança' if taxa <= ref.mediana
                else 'Alerta' if taxa <= ref.q3 else 'Acima do Q3')
        rows.append([ewma, li, ls, ewma < li or ewma > ls, cp, cm, sup, inf, zona])
        if sup or inf: cp, cm = 0., 0.
        anterior = ano
    cols = ['EWMA', 'LIC EWMA', 'LSC EWMA', 'Sinal EWMA', 'CUSUM +', 'CUSUM −',
            'Sinal CUSUM +', 'Sinal CUSUM −', 'Zona canal']
    for i, col in enumerate(cols): out[col] = [r[i] for r in rows]
    return out


def funil(t, referencia=None):
    """Limites exatos Poisson centrais; referência estadual ou do conjunto declarado."""
    out = t.copy()
    if out.empty or out[['Óbitos', 'População', TAXA]].isna().any().any() or (out['População'] <= 0).any():
        raise ValueError('Funil exige cobertura completa e população positiva para cada município.')
    if (out['Óbitos'] < 0).any() or not np.allclose(out[TAXA], out['Óbitos']/out['População']*100000):
        raise ValueError('Contagens ou taxas inválidas no funil.')
    theta = float(out['Óbitos'].sum()/out['População'].sum()*100000) if referencia is None else float(referencia)
    if not np.isfinite(theta) or theta < 0: raise ValueError('Referência territorial inválida.')
    n = out['População'].to_numpy()/100000
    esperado = theta*n
    phi = float(np.sum((out['Óbitos'].to_numpy()-esperado)**2/esperado)/(len(out)-1)) if theta > 0 and len(out)>1 else 1.
    out['Referência'] = theta
    out['Dispersão territorial'] = phi
    for nivel in [.95, .998]:
        rotulo = '95%' if nivel == .95 else '99,8%'
        alfa = (1-nivel)/2
        inferior, superior = poisson.ppf(alfa, esperado), poisson.ppf(1-alfa, esperado)
        out['LIC '+rotulo] = inferior/n
        out['LSC '+rotulo] = superior/n
        # A decisão exata usa contagens: taxas equivalentes podem diferir em
        # um último dígito binário e fabricar um sinal na própria fronteira.
        out['Sinal '+rotulo] = (out['Óbitos'] < inferior) | (out['Óbitos'] > superior)
        # Sensibilidade aproximada: distinta dos limites exatos Poisson.
        margem = norm.ppf(1-alfa)*np.sqrt(theta/n*max(1., phi))
        out['LIC ajustado '+rotulo] = np.maximum(0, theta-margem)
        out['LSC ajustado '+rotulo] = theta+margem
        out['Sinal ajustado '+rotulo] = (out[TAXA] < out['LIC ajustado '+rotulo]) | (out[TAXA] > out['LSC ajustado '+rotulo])
    return out


def analisar(f, p, anos_ref, ano_fim, meses, **parametros):
    anos_ref = sorted(anos_ref)
    base = serie_historica(f, p, anos_ref, meses)
    ref = ajustar(base)
    teste = serie_historica(f, p, range(max(anos_ref)+1, ano_fim+1), meses)
    # Mantém ausências na saída original; modelos aplicam-se só aos períodos completos.
    validos = teste.dropna(subset=['Óbitos', 'População', TAXA])
    if validos.empty: raise ValueError('Não há período completo de avaliação posterior à referência.')
    return base, aplicar(validos, ref, **parametros), ref, teste
