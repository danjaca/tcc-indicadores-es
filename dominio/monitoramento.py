"""Monitoramento estatístico mensal por gráficos de controle.

Aplica aos indicadores do PES-ES a metodologia de gráficos de controle para
medidas individuais (Montgomery, 2009), na forma usada por Barros (2021) para
taxas mensais de mortalidade:

1. série mensal da taxa (óbitos do mês ÷ população anual elegível × 100 mil);
2. fase I: estatísticas descritivas e verificação dos pressupostos (Lilliefors,
   FAC/FACP e Ljung–Box, Dickey–Fuller aumentado, Cox–Stuart e teste de Fisher);
3. fase I: gráficos de medidas individuais e amplitude móvel (X–AM), com
   exclusão iterativa dos pontos fora de controle até a obtenção dos
   parâmetros do processo em controle (μ0 e σ0 = AM̄/d2);
4. fase II: monitoramento com limites fixos (X–AM) e gráfico EWMA; a fase I
   usa uma janela definida antes da análise, sem seleção por valores-p;
5. leitura quadrimestral: os meses do quadrimestre formam um subgrupo racional;
   a taxa do quadrimestre (soma das taxas mensais do mesmo ano) é comparada com
   m·μ0 ± L·√m·σ0, e o acumulado do ano segue a mesma regra.

O módulo usa apenas numpy, pandas e a biblioteca padrão. As implementações dos
testes seguem as rotinas do R (nortest, Box.test, tseries, randtests) e foram
conferidas com os valores publicados por Barros (2021) (ver tests/test_monitoramento.py).
"""
from __future__ import annotations

from dataclasses import dataclass, field, asdict
from datetime import date
import math
from statistics import NormalDist

import numpy as np
import pandas as pd

TAXA = 'Taxa por 100 mil'
TAXA_OFICIAL = 'Taxa oficial por 100 mil'
D2 = 1.128   # constante d2 para amplitude móvel de duas observações
D3 = 0.0     # constante D3 (n = 2)
D4 = 3.267   # constante D4 (n = 2)
ALFA = 0.05
MESES = ['Jan', 'Fev', 'Mar', 'Abr', 'Mai', 'Jun', 'Jul', 'Ago', 'Set', 'Out', 'Nov', 'Dez']
_NORMAL = NormalDist()


# ---------------------------------------------------------------------------
# Série mensal
# ---------------------------------------------------------------------------
def serie_mensal(f: pd.DataFrame, p: pd.DataFrame) -> pd.DataFrame:
    """Série mensal do recorte já filtrado (indicador, território e sexo).

    Meses sem cobertura não aparecem (não são convertidos em zero). A população
    é a anual elegível do ano do óbito, sem fracionamento nem anualização.
    """
    colunas = ['Período', 'Ano', 'Mês', 'Óbitos', 'População', TAXA]
    if f.empty:
        return pd.DataFrame(columns=colunas)
    obitos = f.groupby(['ano', 'mes'], as_index=False).Obitos.sum()
    populacao = p.groupby('ano').populacao.sum()
    obitos['populacao'] = obitos['ano'].map(populacao)
    obitos = obitos.dropna(subset=['populacao'])
    obitos = obitos[obitos['populacao'] > 0]
    if obitos.empty:
        return pd.DataFrame(columns=colunas)
    s = pd.DataFrame({
        'Período': pd.to_datetime(pd.DataFrame({'year': obitos['ano'], 'month': obitos['mes'], 'day': 1})),
        'Ano': obitos['ano'].astype(int).to_numpy(),
        'Mês': obitos['mes'].astype(int).to_numpy(),
        'Óbitos': obitos['Obitos'].astype(int).to_numpy(),
        'População': obitos['populacao'].astype(float).to_numpy(),
    })
    s[TAXA] = s['Óbitos'] / s['População'] * 100000
    return s.sort_values('Período').reset_index(drop=True)


def ajustar_calendario(serie: pd.DataFrame) -> pd.DataFrame:
    """Cópia com taxa para mês de 30,4375 dias, preservando a taxa oficial.

    O cálculo parte sempre da coluna oficial, inclusive em chamadas repetidas.
    Óbitos e população não mudam; somas da taxa ajustada não são taxas oficiais.
    """
    s = serie.copy()
    periodos = pd.to_datetime(s['Período'])
    oficial = s[TAXA_OFICIAL] if TAXA_OFICIAL in s else s[TAXA]
    valores = np.asarray(oficial, dtype=float)
    if periodos.isna().any() or not (np.isfinite(valores) & (valores >= 0)).all():
        raise ValueError('O ajuste de calendário exige meses válidos e taxas finitas não negativas.')
    s[TAXA_OFICIAL] = oficial
    s['Fator calendário'] = 30.4375 / periodos.dt.days_in_month
    s[TAXA] = s[TAXA_OFICIAL] * s['Fator calendário']
    return s


def rotulo_mes(periodo) -> str:
    periodo = pd.Timestamp(periodo)
    return f'{MESES[periodo.month - 1]}/{periodo.year}'


def _indice(periodo) -> int:
    periodo = pd.Timestamp(periodo)
    return periodo.year * 12 + periodo.month - 1


# ---------------------------------------------------------------------------
# Funções de distribuição (sem dependências externas)
# ---------------------------------------------------------------------------
_erf = np.vectorize(math.erf, otypes=[float])


def normal_cdf(x):
    x = np.asarray(x, dtype=float)
    return 0.5 * (1.0 + _erf(x / math.sqrt(2.0)))


def normal_ppf(q: float) -> float:
    return _NORMAL.inv_cdf(q)


def _gama_regularizada_superior(a: float, x: float) -> float:
    """Q(a, x) = Γ(a, x)/Γ(a), por série ou fração contínua."""
    if x <= 0:
        return 1.0
    if x < a + 1:
        termo = soma = 1.0 / a
        ap = a
        for _ in range(10000):
            ap += 1
            termo *= x / ap
            soma += termo
            if abs(termo) < abs(soma) * 1e-16:
                break
        return max(0.0, 1.0 - soma * math.exp(-x + a * math.log(x) - math.lgamma(a)))
    b = x + 1 - a
    c = 1 / 1e-300
    d = 1 / b
    h = d
    for i in range(1, 10000):
        an = -i * (i - a)
        b += 2
        d = an * d + b
        d = d if abs(d) > 1e-300 else 1e-300
        c = b + an / c
        c = c if abs(c) > 1e-300 else 1e-300
        d = 1 / d
        delta = d * c
        h *= delta
        if abs(delta - 1) < 1e-16:
            break
    return math.exp(-x + a * math.log(x) - math.lgamma(a)) * h


def qui_quadrado_sf(x: float, gl: int) -> float:
    return _gama_regularizada_superior(gl / 2.0, x / 2.0)


# ---------------------------------------------------------------------------
# Estatísticas descritivas e testes dos pressupostos (Barros, 2021)
# ---------------------------------------------------------------------------
def descritivas(x) -> dict:
    x = np.asarray(x, dtype=float)
    q1, q2, q3 = np.quantile(x, [.25, .5, .75])
    media = float(x.mean())
    dp = float(x.std(ddof=1)) if len(x) > 1 else float('nan')
    return {
        'n': int(len(x)), 'Média': media, 'Mediana': float(q2),
        'Variância': float(x.var(ddof=1)) if len(x) > 1 else float('nan'),
        'Desvio-padrão': dp, 'Coeficiente de variação (%)': dp / media * 100 if media else float('nan'),
        'Mínimo': float(x.min()), 'Máximo': float(x.max()), 'Amplitude': float(x.max() - x.min()),
        '1º quartil (Q1)': float(q1), '2º quartil (Q2)': float(q2), '3º quartil (Q3)': float(q3),
    }


def lilliefors(x) -> tuple[float, float]:
    """Teste de Lilliefors (1967) com valor-p de Dallal e Wilkinson (1986).

    Mesma formulação de nortest::lillie.test, usada por Barros (2021).
    """
    x = np.sort(np.asarray(x, dtype=float))
    n = len(x)
    if n < 5:
        raise ValueError('O teste de Lilliefors exige pelo menos cinco observações.')
    dp = x.std(ddof=1)
    if dp == 0:
        raise ValueError('Série constante: normalidade não avaliável.')
    acumulada = normal_cdf((x - x.mean()) / dp)
    i = np.arange(1, n + 1)
    k = float(max(np.max(i / n - acumulada), np.max(acumulada - (i - 1) / n)))
    kd, nd = (k, n) if n <= 100 else (k * (n / 100) ** 0.49, 100)
    p = math.exp(-7.01256 * kd**2 * (nd + 2.78019) + 2.99587 * kd * math.sqrt(nd + 2.78019)
                 - 0.122119 + 0.974598 / math.sqrt(nd) + 1.67997 / nd)
    if p > 0.1:
        kk = (math.sqrt(n) - 0.01 + 0.85 / math.sqrt(n)) * k
        if kk <= 0.302:
            p = 1.0
        elif kk <= 0.5:
            p = 2.76773 - 19.828315 * kk + 80.709644 * kk**2 - 138.55152 * kk**3 + 81.218052 * kk**4
        elif kk <= 0.9:
            p = -4.901232 + 40.662806 * kk - 97.490286 * kk**2 + 94.029866 * kk**3 - 32.355711 * kk**4
        elif kk <= 1.31:
            p = 6.198765 - 19.558097 * kk + 23.186922 * kk**2 - 12.234627 * kk**3 + 2.423045 * kk**4
        else:
            p = 0.0
    return k, float(min(max(p, 0.0), 1.0))


def fac(x, defasagens: int) -> np.ndarray:
    """Função de autocorrelação amostral (defasagens 0 a k)."""
    x = np.asarray(x, dtype=float)
    d = x - x.mean()
    c0 = float(d @ d)
    if c0 == 0:
        return np.r_[1.0, np.zeros(defasagens)]
    return np.array([1.0] + [float(d[k:] @ d[:-k] / c0) for k in range(1, defasagens + 1)])


def facp(x, defasagens: int) -> np.ndarray:
    """Função de autocorrelação parcial (recursão de Durbin–Levinson)."""
    r = fac(x, defasagens)
    saida = [1.0]
    anterior = np.array([])
    for k in range(1, defasagens + 1):
        if k == 1:
            pkk = r[1]
            atual = np.array([pkk])
        else:
            num = r[k] - np.sum(anterior * r[k - 1:0:-1])
            den = 1 - np.sum(anterior * r[1:k])
            pkk = num / den if den else 0.0
            atual = np.append(anterior - pkk * anterior[::-1], pkk)
        saida.append(float(pkk))
        anterior = atual
    return np.array(saida)


def ljung_box(x, defasagens: int = 1) -> tuple[float, int, float]:
    """Teste de Ljung e Box (1978). Defasagem 1 = padrão de Box.test no R."""
    x = np.asarray(x, dtype=float)
    n = len(x)
    if n <= defasagens + 1:
        raise ValueError('Série curta para o número de defasagens.')
    r = fac(x, defasagens)
    q = n * (n + 2) * sum(r[k] ** 2 / (n - k) for k in range(1, defasagens + 1))
    return float(q), int(defasagens), float(qui_quadrado_sf(q, defasagens))


def dickey_fuller_aumentado(x, defasagens: int | None = None) -> tuple[float, int, float]:
    """Teste ADF com constante e tendência (Dickey e Fuller, 1979; Said e Dickey, 1984).

    Segue tseries::adf.test: defasagens trunc((n−1)^(1/3)) e valor-p interpolado
    na tabela de Banerjee et al. (1993). H0: a série possui raiz unitária.
    """
    x = np.asarray(x, dtype=float)
    nx = len(x)
    if defasagens is None:
        defasagens = int(math.trunc((nx - 1) ** (1 / 3)))
    k = defasagens + 1
    y = np.diff(x)
    n = len(y)
    linhas = np.arange(k - 1, n)
    if len(linhas) <= k + 3:
        raise ValueError('Série curta para o teste de Dickey–Fuller aumentado.')
    colunas = [np.ones(len(linhas)), x[linhas], linhas + 1.0] + [y[linhas - j] for j in range(1, k)]
    matriz = np.column_stack(colunas)
    resposta = y[linhas]
    beta = np.linalg.lstsq(matriz, resposta, rcond=None)[0]
    residuo = resposta - matriz @ beta
    variancia = residuo @ residuo / (len(resposta) - matriz.shape[1])
    covariancia = variancia * np.linalg.inv(matriz.T @ matriz)
    estatistica = float(beta[1] / math.sqrt(covariancia[1, 1]))
    tabela = -np.array([
        [4.38, 4.15, 4.04, 3.99, 3.98, 3.96], [3.95, 3.80, 3.73, 3.69, 3.68, 3.66],
        [3.60, 3.50, 3.45, 3.43, 3.42, 3.41], [3.24, 3.18, 3.15, 3.13, 3.13, 3.12],
        [1.14, 1.19, 1.22, 1.23, 1.24, 1.25], [0.80, 0.87, 0.90, 0.92, 0.93, 0.94],
        [0.50, 0.58, 0.62, 0.64, 0.65, 0.66], [0.15, 0.24, 0.28, 0.31, 0.32, 0.33]])
    tamanhos = [25, 50, 100, 250, 500, 100000]
    probabilidades = [0.01, 0.025, 0.05, 0.10, 0.90, 0.95, 0.975, 0.99]
    interpolados = [float(np.interp(n, tamanhos, linha)) for linha in tabela]
    p = float(np.interp(estatistica, interpolados, probabilidades))
    return estatistica, int(defasagens), p


def cox_stuart(x, metodo: str = 'exato') -> tuple[int, int, float]:
    """Teste de Cox e Stuart (1955) para tendência.

    Compara primeiro e último terço, descartando empates. O padrão é o teste
    binomial bilateral exato, sob sinais independentes equiprováveis. O modo
    ``normal`` preserva a reprodução publicada de Barros (2021).
    """
    x = np.asarray(x, dtype=float)
    if metodo not in ('exato', 'normal'):
        raise ValueError('O método de Cox–Stuart deve ser exato ou normal.')
    if x.ndim != 1 or not np.isfinite(x).all():
        raise ValueError('Cox–Stuart exige uma série unidimensional finita.')
    terco = len(x) // 3
    if terco < 3:
        raise ValueError('Série curta para o teste de Cox–Stuart.')
    diferencas = x[len(x) - terco:] - x[:terco]
    n = int(np.sum(diferencas != 0))
    positivos = int(np.sum(diferencas > 0))
    if n == 0:
        return 0, 0, 1.0
    if metodo == 'exato':
        cauda = sum(math.comb(n, k) for k in range(min(positivos, n - positivos) + 1)) / 2**n
        return n, positivos, min(1.0, 2 * cauda)
    z = (positivos - n / 2) / math.sqrt(n / 4)
    return n, positivos, float(2 * (1 - normal_cdf(abs(z))))


def kpss(x, tendencia: bool = True, defasagens: int | None = None) -> tuple[float, int, float]:
    """KPSS complementar, com constante+tendência (padrão) ou somente constante.

    Usa variância de longo prazo com Bartlett e defasagem curta de tseries::
    kpss.test. O valor-p é interpolado na tabela de Kwiatkowski et al. (1992),
    limitado a [0,01; 0,10]: valores nas bordas indicam ≤0,01 ou ≥0,10.
    H0 com tendência: estacionariedade em torno de tendência determinística,
    especificação compatível com o ADF empregado, sem afirmar média constante.
    """
    x = np.asarray(x, dtype=float)
    n = x.size
    if x.ndim != 1 or n < 8 or not np.isfinite(x).all():
        raise ValueError('KPSS exige pelo menos oito observações finitas.')
    if defasagens is None:
        defasagens = math.trunc(4 * (n / 100) ** .25)
    if not isinstance(defasagens, (int, np.integer)) or not 0 <= defasagens < n:
        raise ValueError('A defasagem do KPSS deve ser inteira em [0, n).')
    t = np.arange(n, dtype=float)
    matriz = np.column_stack((np.ones(n), t)) if tendencia else np.ones((n, 1))
    ajuste = matriz @ np.linalg.lstsq(matriz, x, rcond=None)[0]
    residuos = x - ajuste
    if float(residuos @ residuos) <= np.finfo(float).eps * float(x @ x):
        raise ValueError('Ajuste perfeito ou dispersão nula: KPSS não avaliável.')
    s2 = float(residuos @ residuos) / n
    for lag in range(1, defasagens + 1):
        s2 += 2 * (1 - lag / (defasagens + 1)) * float(residuos[lag:] @ residuos[:-lag]) / n
    if s2 <= 0:
        raise ValueError('Variância de longo prazo não positiva no KPSS.')
    estatistica = float(np.sum(np.cumsum(residuos) ** 2) / n**2 / s2)
    criticos = [.119, .146, .176, .216] if tendencia else [.347, .463, .574, .739]
    p = float(np.interp(estatistica, criticos, [.10, .05, .025, .01]))
    return estatistica, int(defasagens), p


def avaliar_residuos_tendencia(x, alfa: float = ALFA, defasagens_lb=(1, 12)) -> pd.DataFrame:
    """Diagnósticos exploratórios após retirar tendência linear por OLS.

    Ajuste e diagnóstico usam a mesma amostra. Os valores-p são aproximações
    descritivas; não validam um modelo nem substituem os limites principais.
    """
    x = np.asarray(x, dtype=float)
    if x.ndim != 1 or len(x) < 12 or not np.isfinite(x).all() or not 0 < alfa < 1:
        raise ValueError('Informe uma série finita com pelo menos 12 meses e alfa em (0, 1).')
    t = np.arange(len(x), dtype=float)
    matriz = np.column_stack((np.ones(len(x)), t))
    beta = np.linalg.lstsq(matriz, x, rcond=None)[0]
    residuos = x - matriz @ beta
    if float(residuos @ residuos) <= np.finfo(float).eps * float(x @ x):
        raise ValueError('Ajuste perfeito ou dispersão nula: resíduos não avaliáveis.')
    d, p = lilliefors(residuos)
    linhas = [{'Teste': 'Lilliefors', 'Estatística': d, 'Valor-p': p, 'Detalhe': ''}]
    for lag in defasagens_lb:
        if len(x) > lag + 2:
            q, _, p = ljung_box(residuos, lag)
            nome = 'Ljung–Box (defasagem 1)' if lag == 1 else f'Ljung–Box (defasagens 1 a {lag})'
            linhas.append({'Teste': nome, 'Estatística': q, 'Valor-p': p, 'Detalhe': f'{lag} defasagens'})
    g, p, periodo = fisher_sazonalidade(residuos)
    linhas.append({'Teste': 'Fisher (periodograma)', 'Estatística': g, 'Valor-p': p,
                   'Detalhe': f'período dominante ≈ {periodo:.1f} meses'})
    tabela = pd.DataFrame(linhas)
    tabela['Decisão'] = np.where(tabela['Valor-p'] < alfa, 'Rejeita H0', 'Não rejeita H0')
    tabela['Inclinação por mês'] = float(beta[1])
    tabela['Contexto'] = 'Resíduos OLS; diagnósticos exploratórios, sem correção por multiplicidade'
    return tabela


def fisher_sazonalidade(x) -> tuple[float, float, float]:
    """Teste g de Fisher (1929) sobre o periodograma.

    Usa as frequências de Fourier 1..⌊(N−1)/2⌋ e o valor-p exato. Retorna
    (g, valor-p, período dominante em meses).
    """
    x = np.asarray(x, dtype=float)
    n = len(x)
    m = (n - 1) // 2
    if m < 3:
        raise ValueError('Série curta para o teste de Fisher.')
    periodograma = np.abs(np.fft.fft(x - x.mean())) ** 2 / n
    ordenadas = periodograma[1:m + 1]
    total = float(ordenadas.sum())
    if total == 0:
        return 0.0, 1.0, float('nan')
    g = float(ordenadas.max() / total)
    limite = int(math.floor(1 / g))
    p = sum((-1) ** (j - 1) * math.comb(m, j) * (1 - j * g) ** (m - 1) for j in range(1, limite + 1))
    periodo = n / (int(np.argmax(ordenadas)) + 1)
    return g, float(min(max(p, 0.0), 1.0)), float(periodo)


def avaliar_pressupostos(x, alfa: float = ALFA, defasagens_lb: tuple = (1, 12),
                         metodo_cox: str = 'exato') -> pd.DataFrame:
    """Tabela de pressupostos da fase I, na ordem adotada por Barros (2021)."""
    x = np.asarray(x, dtype=float)
    linhas = []

    def registrar(teste, hipotese, estatistica, p, rejeita_txt, aceita_txt, detalhe=''):
        linhas.append({'Teste': teste, 'Hipótese nula (H0)': hipotese, 'Estatística': float(estatistica),
                       'Valor-p': float(p), 'Decisão': 'Rejeita H0' if p < alfa else 'Não rejeita H0',
                       'Leitura': rejeita_txt if p < alfa else aceita_txt, 'Detalhe': detalhe})

    d, p = lilliefors(x)
    registrar('Lilliefors', 'Os dados seguem distribuição normal', d, p,
              'Evidência de desvio da normalidade', 'Normalidade não rejeitada')
    for lag in defasagens_lb:
        if len(x) > lag + 2:
            q, gl, p = ljung_box(x, lag)
            nome = 'Ljung–Box (defasagem 1)' if lag == 1 else f'Ljung–Box (defasagens 1 a {lag})'
            registrar(nome, 'As autocorrelações até a defasagem avaliada são nulas', q, p,
                      'Evidência de autocorrelação', 'Autocorrelação não detectada', f'{gl} g.l.')
    est, k, p = dickey_fuller_aumentado(x)
    registrar('Dickey–Fuller aumentado', 'A série possui raiz unitária (não estacionária)', est, p,
              'Raiz unitária rejeitada no modelo com tendência', 'Raiz unitária não rejeitada',
              f'{k} defasagens; constante e tendência; não comprova média constante')
    n, pos, p = cox_stuart(x, metodo=metodo_cox)
    registrar('Cox–Stuart', 'Não existe tendência', float(pos), p,
              'Evidência de tendência', 'Tendência não detectada',
              f'{pos} de {n} pares crescentes (primeiro × último terço); ' +
              ('binomial bilateral exato; pressupõe sinais independentes' if metodo_cox == 'exato' else
               'aproximação normal sem correção de continuidade, para reprodução histórica'))
    g, p, periodo = fisher_sazonalidade(x)
    registrar('Fisher (periodograma)', 'Não há componente periódico dominante sob ruído branco', g, p,
              'Evidência de componente periódico', 'Componente periódico não detectado',
              f'período dominante ≈ {periodo:.1f} meses')
    return pd.DataFrame(linhas)


# ---------------------------------------------------------------------------
# Gráficos de controle X–AM e EWMA
# ---------------------------------------------------------------------------
@dataclass(frozen=True)
class Parametros:
    """Parâmetros estimados da referência, condicionais aos seus pressupostos."""
    inicio: str
    fim: str
    n_inicial: int
    n_controle: int
    mu0: float
    sigma0: float
    am_media: float
    largura: float
    lic_x: float
    lsc_x: float
    lsc_am: float
    excluidos: tuple = field(default_factory=tuple)
    manuais: tuple = field(default_factory=tuple)
    iteracoes: int = 1
    estavel: bool = True

    def como_dict(self) -> dict:
        return asdict(self)


def _limites(valores: np.ndarray, largura: float):
    am = np.abs(np.diff(valores))
    am_media = float(am.mean())
    mu = float(valores.mean())
    sigma = am_media / D2
    return mu, sigma, am_media, mu - largura * sigma, mu + largura * sigma


def fase1(serie: pd.DataFrame, largura: float = 3.0, excluir=(), automatico: bool = False,
          max_exclusao: float = .2):
    """Fase I dos gráficos X–AM com exclusão iterativa (Barros, 2021).

    Em cada iteração, exclui os meses com X fora dos limites; se não houver,
    exclui o mês final das amplitudes móveis acima do LSC. Repete até não haver
    sinais. A amplitude móvel é recalculada sobre a sequência remanescente.
    `excluir` registra exclusões decididas pela vigilância (causa especial).
    Retorna (Parametros, tabela da fase I, histórico das iterações).
    """
    if len(serie) < 12:
        raise ValueError('A fase I exige pelo menos 12 meses completos.')
    if not math.isfinite(largura) or largura <= 0:
        raise ValueError('A largura dos limites deve ser positiva e finita.')
    if not math.isfinite(max_exclusao) or not 0 <= max_exclusao < 1:
        raise ValueError('A fração máxima de exclusões deve estar em [0, 1).')
    base = serie.sort_values('Período').reset_index(drop=True).copy()
    chaves = [pd.Timestamp(v) for v in base['Período']]
    manuais = {mes(v) for v in excluir}
    if not manuais.issubset(chaves):
        raise ValueError('As exclusões documentadas devem pertencer à fase I.')
    if len(manuais) > max_exclusao * len(base):
        raise ValueError('As exclusões documentadas excedem a fração máxima permitida.')
    automaticos: dict = {}
    historico = []
    estavel = True
    iteracao = 0
    while True:
        iteracao += 1
        removidos = manuais | set(automaticos)
        mantidos = base[~base['Período'].isin(removidos)]
        valores = mantidos[TAXA].to_numpy(dtype=float)
        if len(valores) < 10:
            raise ValueError('Exclusões demais na fase I: restaram menos de 10 meses.')
        mu, sigma, am_media, lic, lsc = _limites(valores, largura)
        if not math.isfinite(sigma) or sigma <= 0:
            raise ValueError('Série constante ou dispersão nula: limites de controle não estimáveis.')
        lsc_am = D4 * am_media
        am = np.r_[np.nan, np.abs(np.diff(valores))]
        sinal_x = (valores > lsc) | (valores < lic)
        sinal_am = am > lsc_am
        periodos = list(mantidos['Período'])
        novos = [periodos[i] for i in np.flatnonzero(sinal_x)]
        criterio = 'X fora dos limites'
        if not novos:
            novos = [periodos[i] for i in np.flatnonzero(sinal_am)]
            criterio = 'AM acima do LSC'
        historico.append({'Iteração': iteracao, 'Meses considerados': len(valores), 'μ0': mu, 'σ0': sigma,
                          'AM média': am_media, 'LIC X': max(0.0, lic), 'LSC X': lsc, 'LSC AM': lsc_am,
                          'Sinais': ', '.join(rotulo_mes(v) for v in novos) or 'Nenhum',
                          'Critério': criterio if novos else '—'})
        if not automatico or not novos:
            estavel = not bool(novos)
            break
        if len(manuais) + len(automaticos) + len(novos) > max_exclusao * len(base):
            estavel = False
            break
        for periodo in novos:
            automaticos[pd.Timestamp(periodo)] = (iteracao, criterio)
    excluidos = set(manuais) | set(automaticos)
    params = Parametros(
        inicio=rotulo_mes(base['Período'].iloc[0]), fim=rotulo_mes(base['Período'].iloc[-1]),
        n_inicial=len(base), n_controle=len(base) - len(excluidos), mu0=mu, sigma0=sigma,
        am_media=am_media, largura=largura, lic_x=max(0.0, lic), lsc_x=lsc, lsc_am=lsc_am,
        excluidos=tuple(rotulo_mes(v) for v in sorted(automaticos)),
        manuais=tuple(rotulo_mes(v) for v in sorted(manuais)), iteracoes=iteracao, estavel=estavel)
    tabela = base.copy()
    situacao = []
    for periodo in tabela['Período']:
        periodo = pd.Timestamp(periodo)
        if periodo in manuais:
            situacao.append('Excluído pela vigilância')
        elif periodo in automaticos:
            it, crit = automaticos[periodo]
            situacao.append(f'Excluído na iteração {it} ({crit})')
        else:
            situacao.append('Em controle' if estavel else 'Mantido (fase I instável)')
    tabela['Situação fase I'] = situacao
    mantidos = tabela['Situação fase I'].str.startswith(('Em controle', 'Mantido'))
    am_final = pd.Series(np.nan, index=tabela.index)
    valores_mantidos = tabela.loc[mantidos, TAXA]
    am_final.loc[valores_mantidos.index[1:]] = np.abs(np.diff(valores_mantidos.to_numpy()))
    tabela['AM'] = am_final
    tabela['LIC X'], tabela['LM X'], tabela['LSC X'] = params.lic_x, params.mu0, params.lsc_x
    tabela['LM AM'], tabela['LSC AM'] = params.am_media, params.lsc_am
    return params, tabela, pd.DataFrame(historico)


def ewma(valores, mu0: float, sigma0: float, lam: float = .1, largura: float = 2.701):
    """Estatística EWMA com limites exatos (Roberts, 1959), iniciada em μ0."""
    if not 0 < lam <= 1:
        raise ValueError('λ deve estar em (0, 1].')
    z = mu0
    estat, inferior, superior = [], [], []
    for i, x in enumerate(np.asarray(valores, dtype=float), start=1):
        z = lam * x + (1 - lam) * z
        margem = largura * sigma0 * math.sqrt(lam / (2 - lam) * (1 - (1 - lam) ** (2 * i)))
        estat.append(z)
        inferior.append(mu0 - margem)
        superior.append(mu0 + margem)
    return np.array(estat), np.array(inferior), np.array(superior)


def em_consolidacao(periodos, data_base, dias: int = 60) -> np.ndarray:
    """Meses cujo encerramento ocorreu há menos de `dias` da atualização da base.

    O padrão de 60 dias é uma convenção operacional conservadora. O prazo não
    certifica completude, e registros mais antigos também podem ser revisados.
    """
    periodos = pd.to_datetime(pd.Series(list(periodos)))
    if data_base is None or periodos.empty:
        return np.zeros(len(periodos), dtype=bool)
    data_base = pd.Timestamp(data_base).normalize()
    fins = periodos + pd.offsets.MonthEnd(0)
    return ((data_base - fins).dt.days < dias).to_numpy()


def fase2(serie: pd.DataFrame, params: Parametros, lam: float = .1, largura_ewma: float = 2.701,
          data_base=None, dias_consolidacao: int = 60, anterior=None) -> pd.DataFrame:
    """Fase II: X–AM com limites fixos e EWMA iniciado em μ0 no primeiro mês.

    `anterior` é a taxa do mês imediatamente anterior ao primeiro mês da fase II
    (último mês da fase I), usada na primeira AM, como em Barros (2021). Lacunas
    interrompem a AM e reiniciam o EWMA; meses ausentes não são zeros.
    """
    t = serie.sort_values('Período').reset_index(drop=True).copy()
    t['LIC X'], t['LM X'], t['LSC X'] = params.lic_x, params.mu0, params.lsc_x
    t['LM AM'], t['LSC AM'] = params.am_media, params.lsc_am
    indices = [_indice(v) for v in t['Período']]
    taxas = t[TAXA].to_numpy(dtype=float)
    am = np.full(len(t), np.nan)
    if anterior is not None and len(t):
        am[0] = abs(taxas[0] - float(anterior))
    for i in range(1, len(t)):
        am[i] = abs(taxas[i] - taxas[i - 1]) if indices[i] == indices[i - 1] + 1 else np.nan
    t['AM'] = am
    z = np.full(len(t), np.nan)
    li = np.full(len(t), np.nan)
    ls = np.full(len(t), np.nan)
    inicio = 0
    for i in range(1, len(t) + 1):
        if i == len(t) or indices[i] != indices[i - 1] + 1:
            zz, a, b = ewma(taxas[inicio:i], params.mu0, params.sigma0, lam, largura_ewma)
            z[inicio:i], li[inicio:i], ls[inicio:i] = zz, a, b
            inicio = i
    t['EWMA'], t['LIC EWMA'], t['LSC EWMA'] = z, li, ls
    t['Sinal X'] = np.where(taxas > params.lsc_x, 'Aumento', np.where(taxas < params.lic_x, 'Redução', ''))
    t['Sinal AM'] = np.where(am > params.lsc_am, 'Variabilidade', '')
    t['Sinal EWMA'] = np.where(z > ls, 'Aumento', np.where(z < li, 'Redução', ''))
    t['Em consolidação'] = em_consolidacao(t['Período'], data_base, dias_consolidacao)
    return t


def quadrimestres(fase_ii: pd.DataFrame, params: Parametros, largura: float = 3.0) -> pd.DataFrame:
    """Leitura quadrimestral (isolada e acumulada) com os parâmetros mensais.

    Para m meses do mesmo ano, a taxa do período é a soma das taxas mensais
    (mesma população anual). Sob controle, a soma ~ N(m·μ0, m·σ0²): limites
    m·μ0 ± L·√m·σ0 — gráfico X̄ com subgrupo racional de m meses em escala de soma.
    """
    linhas = []
    if fase_ii.empty:
        return pd.DataFrame()
    for ano, grupo in fase_ii.groupby('Ano'):
        meses = set(int(m) for m in grupo['Mês'])
        for q in (1, 2, 3):
            alvo = list(range(4 * q - 3, 4 * q + 1))
            if not any(m in meses for m in alvo):
                continue
            for tipo, recorte in (('Quadrimestre isolado', alvo), ('Acumulado no ano', list(range(1, 4 * q + 1)))):
                disponiveis = [m for m in recorte if m in meses]
                sub = grupo[grupo['Mês'].isin(disponiveis)]
                m = len(disponiveis)
                taxa = float(sub[TAXA].sum())
                esperado = m * params.mu0
                margem = largura * math.sqrt(m) * params.sigma0
                lic, lsc = max(0.0, esperado - margem), esperado + margem
                completo = m == len(recorte)
                recentes = int(sub['Em consolidação'].sum()) if 'Em consolidação' in sub else 0
                sinal = ('Aumento' if taxa > lsc else 'Redução' if taxa < lic else '') if completo and not recentes else ''
                situacao = ('Suspensa: período parcial' if not completo else 'Suspensa: consolidação' if recentes else
                            'Sinal calculado' if sinal else 'Sem sinal')
                linhas.append({
                    'Ano': int(ano), 'Quadrimestre': f'{q}º', 'Leitura': tipo,
                    'Meses': f'{MESES[min(disponiveis) - 1]}–{MESES[max(disponiveis) - 1]}',
                    'Meses disponíveis': m, 'Completo': completo,
                    'Óbitos': int(sub['Óbitos'].sum()), 'População': float(sub['População'].iloc[0]),
                    TAXA: taxa, 'Esperado (m·μ0)': esperado, 'LIC': lic, 'LSC': lsc,
                    'Razão observado/esperado': taxa / esperado if esperado else float('nan'),
                    'Sinal': sinal,
                    'Situação da sinalização': situacao,
                    'Meses em consolidação': recentes,
                    'Meses com sinal (X, AM ou EWMA)': int(((sub['Sinal X'] != '') | (sub['Sinal AM'] != '') |
                                                           (sub['Sinal EWMA'] != '')).sum()),
                })
    return pd.DataFrame(linhas)


# ---------------------------------------------------------------------------
# Desempenho (ARL) e calibração
# ---------------------------------------------------------------------------
def arl_shewhart(deslocamento: float = 0.0, largura: float = 3.0) -> float:
    p = 1 - float(normal_cdf(largura - deslocamento)) + float(normal_cdf(-largura - deslocamento))
    return 1 / p


def probabilidade_sinal_am() -> float:
    """Probabilidade marginal nominal do AM sob normais iid e σ conhecido.

    AM/σ ~ |N(0,2)| e LSC/σ = D4·D2. Amplitudes consecutivas são
    dependentes; o inverso desta probabilidade não é o ARL do gráfico AM.
    """
    return float(2 * normal_cdf(-D4 * D2 / math.sqrt(2)))


def comparar_poisson(referencia: pd.DataFrame) -> dict:
    """Dispersão observada versus Poisson de taxa constante, sem ajuste de modelo.

    Com E(O_t)=μ·P_t/100000, Var(100000·O_t/P_t)=μ·100000/P_t.
    A média dessas variâncias respeita as populações anuais efetivas. Tendência,
    dependência e exposição por dias não são corrigidas por esta comparação.
    """
    populacao = referencia['População'].to_numpy(dtype=float)
    coluna_taxa = TAXA_OFICIAL if TAXA_OFICIAL in referencia else TAXA
    taxas = referencia[coluna_taxa].to_numpy(dtype=float)
    obitos = referencia['Óbitos'].to_numpy(dtype=float)
    if len(taxas) < 2 or not (np.isfinite(populacao) & (populacao > 0) & np.isfinite(taxas)
                              & (taxas >= 0) & np.isfinite(obitos) & (obitos >= 0)).all():
        raise ValueError('A comparação Poisson exige populações positivas e contagens/taxas não negativas válidas.')
    mu = float(taxas.mean())
    esperado = math.sqrt(float(np.mean(mu * 100000 / populacao)))
    sigma_am = float(np.abs(np.diff(taxas)).mean()) / D2
    return {'Óbitos por mês (média)': float(obitos.mean()), 'Taxa média': mu,
            'σ por AM': sigma_am, 'DP amostral das taxas': float(taxas.std(ddof=1)),
            'DP esperado sob Poisson': esperado,
            'Razão σ AM / DP Poisson': sigma_am / esperado if esperado else float('nan'),
            'Razão variância amostral / Poisson': float(taxas.var(ddof=1)) / esperado**2 if esperado else float('nan'),
            'Interpretação': 'Taxa oficial, sem ajuste por dias; comparação exploratória que não comprova '
                             'Poisson, sobredispersão ou estabilidade'}


def arl_ewma(lam: float, largura: float, deslocamento: float = 0.0, estados: int = 301) -> float:
    """ARL teórico com limites assintóticos fixos e parâmetros conhecidos.

    Cadeia de Markov; não é o ARL exato dos limites transitórios de ``ewma``
    nem incorpora a incerteza da estimação dos parâmetros na fase I.
    """
    if not 0 < lam <= 1 or not math.isfinite(largura) or largura <= 0:
        raise ValueError('O ARL exige λ em (0, 1] e largura positiva e finita.')
    h = largura * math.sqrt(lam / (2 - lam))
    w = 2 * h / estados
    c = -h + w * (np.arange(estados) + .5)
    sup = (c[None, :] + w / 2 - (1 - lam) * c[:, None]) / lam - deslocamento
    inf = (c[None, :] - w / 2 - (1 - lam) * c[:, None]) / lam - deslocamento
    transicao = normal_cdf(sup) - normal_cdf(inf)
    arl = np.linalg.solve(np.eye(estados) - transicao, np.ones(estados))
    return float(arl[estados // 2])


def calibrar_largura_ewma(lam: float, arl0: float = 370.4) -> float:
    """Largura L do EWMA que produz o ARL0 desejado (bisseção)."""
    baixo, alto = 1.0, 4.5
    for _ in range(40):
        meio = (baixo + alto) / 2
        if arl_ewma(lam, meio, estados=151) < arl0:
            baixo = meio
        else:
            alto = meio
    return round((baixo + alto) / 2, 3)


# ---------------------------------------------------------------------------
# Orquestração
# ---------------------------------------------------------------------------
@dataclass
class Resultado:
    serie: pd.DataFrame
    referencia: pd.DataFrame
    descritivas: dict
    pressupostos: pd.DataFrame
    params: Parametros
    fase_i: pd.DataFrame
    iteracoes: pd.DataFrame
    ewma_fase_i: pd.DataFrame
    fase_ii: pd.DataFrame
    quadrimestral: pd.DataFrame
    configuracao: dict


def iteracao_fase1(r: 'Resultado', k: int) -> dict:
    """Meses considerados e limites da iteração k (1 = primeira) da fase I.

    Devolve os limites da iteração, os meses que entraram no cálculo (com a
    amplitude móvel recalculada sobre a sequência remanescente e as marcas de
    pontos fora de controle) e os meses excluídos em iterações anteriores.
    """
    import re
    historico = r.iteracoes.set_index('Iteração')
    if k not in historico.index:
        raise ValueError(f'A fase I tem {len(historico)} iteração(ões); {k} não existe.')
    limites = historico.loc[k].to_dict()
    f1 = r.fase_i

    def nivel(situacao: str):
        if situacao == 'Excluído pela vigilância':
            return 0
        achado = re.match(r'Excluído na iteração (\d+)', situacao)
        return int(achado.group(1)) if achado else None

    niveis = f1['Situação fase I'].map(nivel)
    considerados = f1[niveis.isna() | (niveis >= k)][['Período', 'Óbitos', TAXA]].copy()
    valores = considerados[TAXA].to_numpy(dtype=float)
    considerados['AM'] = np.r_[np.nan, np.abs(np.diff(valores))] if len(valores) else []
    considerados['Sinal X'] = (considerados[TAXA] > limites['LSC X']) | (considerados[TAXA] < limites['LIC X'])
    considerados['Sinal AM'] = considerados['AM'] > limites['LSC AM']
    excluidos = f1[niveis.notna() & (niveis < k)][['Período', TAXA, 'Situação fase I']].copy()
    return dict(limites=limites, considerados=considerados.reset_index(drop=True),
                excluidos_antes=excluidos.reset_index(drop=True))


def analisar(serie: pd.DataFrame, inicio_fase1, fim_fase1, fim_fase2=None, lam: float = .1,
             largura_ewma: float = 2.701, largura: float = 3.0, excluir=(), automatico: bool = False,
             data_base=None, dias_consolidacao: int = 60, defasagens_lb=(1, 12),
             alfa: float = ALFA, max_exclusao: float = .2, metodo_cox: str = 'exato') -> Resultado:
    """Executa o protocolo completo (fases I e II e leitura quadrimestral)."""
    inicio_fase1, fim_fase1 = mes(inicio_fase1), mes(fim_fase1)
    if fim_fase1 < inicio_fase1:
        raise ValueError('O fim da fase I deve ser posterior ao início.')
    if not 0 < alfa < 1:
        raise ValueError('O nível alfa deve estar em (0, 1).')
    if not 0 < lam <= 1 or not math.isfinite(largura_ewma) or largura_ewma <= 0:
        raise ValueError('O EWMA exige λ em (0, 1] e largura positiva e finita.')
    if dias_consolidacao < 0:
        raise ValueError('O prazo de consolidação não pode ser negativo.')
    if not defasagens_lb or any(not isinstance(v, (int, np.integer)) or v < 1 for v in defasagens_lb):
        raise ValueError('Informe defasagens inteiras positivas para Ljung–Box.')
    if fim_fase2 is not None and mes(fim_fase2) <= fim_fase1:
        raise ValueError('O fim da fase II deve ser posterior ao fim da fase I.')
    s = serie.copy()
    s['Período'] = pd.to_datetime(s['Período']).dt.to_period('M').dt.to_timestamp()
    if s['Período'].isna().any() or s['Período'].duplicated().any():
        raise ValueError('A série deve ter exatamente uma observação válida por mês, sem duplicatas.')
    if not (np.isfinite(s[TAXA]) & (s[TAXA] >= 0)).all():
        raise ValueError('As taxas devem ser não negativas e finitas.')
    s = s.sort_values('Período').reset_index(drop=True)
    s['Ano'], s['Mês'] = s['Período'].dt.year, s['Período'].dt.month
    referencia = s[(s['Período'] >= inicio_fase1) & (s['Período'] <= fim_fase1)]
    esperados = (_indice(fim_fase1) - _indice(inicio_fase1)) + 1
    if len(referencia) != esperados:
        raise ValueError('A fase I contém meses sem cobertura; escolha um intervalo completo '
                         '(lacunas não são convertidas em zero).')
    params, tab1, hist = fase1(referencia, largura=largura, excluir=excluir, automatico=automatico,
                              max_exclusao=max_exclusao)
    controle = tab1[tab1['Situação fase I'].str.startswith(('Em controle', 'Mantido'))]
    z, li, ls = ewma(controle[TAXA].to_numpy(dtype=float), params.mu0, params.sigma0, lam, largura_ewma)
    ewma1 = controle[['Período', TAXA]].copy()
    ewma1['EWMA'], ewma1['LIC EWMA'], ewma1['LSC EWMA'] = z, li, ls
    ewma1['Sinal EWMA'] = np.where(z > ls, 'Aumento', np.where(z < li, 'Redução', ''))
    posterior = s[s['Período'] > fim_fase1]
    if fim_fase2 is not None:
        posterior = posterior[posterior['Período'] <= mes(fim_fase2)]
    anterior = None
    if not posterior.empty and _indice(posterior['Período'].iloc[0]) == _indice(fim_fase1) + 1:
        anterior = float(referencia[TAXA].iloc[-1])
    fase_ii = fase2(posterior, params, lam, largura_ewma, data_base, dias_consolidacao, anterior=anterior)
    quad = quadrimestres(fase_ii, params, largura)
    pressupostos = avaliar_pressupostos(referencia[TAXA].to_numpy(dtype=float), alfa=alfa,
                                        defasagens_lb=defasagens_lb, metodo_cox=metodo_cox)
    configuracao = dict(
        protocolo=PROTOCOLO,
        inicio_fase1=rotulo_mes(inicio_fase1), fim_fase1=rotulo_mes(fim_fase1),
        inicio_fase2=rotulo_mes(fim_fase1 + pd.DateOffset(months=1)),
        fim_fase2_planejado=rotulo_mes(mes(fim_fase2)) if fim_fase2 is not None else None,
        fim_fase2=rotulo_mes(fase_ii['Período'].iloc[-1]) if not fase_ii.empty else None,
        lam=lam, largura_ewma=largura_ewma, largura=largura,
        arl0_x=arl_shewhart(0, largura), arl0_ewma=arl_ewma(lam, largura_ewma),
        exclusao_automatica=automatico, exclusoes_vigilancia=[rotulo_mes(v) for v in excluir],
        data_base=str(pd.Timestamp(data_base).date()) if data_base is not None else None,
        dias_consolidacao=dias_consolidacao, sinais_recentes='não interpretados',
        defasagens_ljung_box=list(defasagens_lb),
        alfa=alfa, max_exclusao=max_exclusao, metodo_cox=metodo_cox, d2=D2, d4=D4,
        probabilidade_marginal_am=probabilidade_sinal_am(),
        arl_hipoteses='Normalidade, independência e parâmetros conhecidos; EWMA com limites assintóticos fixos')
    return Resultado(serie=s, referencia=referencia, descritivas=descritivas(referencia[TAXA]),
                     pressupostos=pressupostos, params=params, fase_i=tab1, iteracoes=hist,
                     ewma_fase_i=ewma1, fase_ii=fase_ii, quadrimestral=quad, configuracao=configuracao)


def data_atualizacao(meta: dict, ano: int | None = None):
    """Data de atualização do banco informada pelo TabNet ('Banco atualizado até o dia dd/mm/aaaa')."""
    extracoes = meta.get('extracoes', {})
    anos = [str(ano)] if ano is not None else sorted(extracoes, reverse=True)
    for chave in anos:
        texto = extracoes.get(chave, {}).get('revisao', '')
        marcador = 'atualizado até o dia '
        if marcador in texto:
            trecho = texto.split(marcador, 1)[1][:10]
            try:
                d, m, a = map(int, trecho.split('/'))
                return date(a, m, d)
            except ValueError:
                pass
        data = extracoes.get(chave, {}).get('data')
        if data:
            return pd.Timestamp(data).date()
    return None


# ---------------------------------------------------------------------------
# Protocolo configurável (config.toml) e regra de escolha da fase I
# ---------------------------------------------------------------------------
PROTOCOLO = 'graficos_controle_mensal_v4'
PROTOCOLO_PADRAO = dict(
    protocolo=PROTOCOLO, lambda_ewma=.1, largura_ewma=2.701, largura_x=3.0, metodo_cox='exato',
    alfa=ALFA, dias_consolidacao=60, exclusao_automatica=False, max_exclusao=.2,
    defasagens_ljung_box=[1, 12], meses_minimos_fase1=24, meses_padrao_fase1=48, meses_fase2=12,
    fase1={}, exclusoes={})


def ler_protocolo(caminho) -> dict:
    """Lê o bloco [monitoramento] do config.toml, completando com os padrões."""
    import tomllib
    from pathlib import Path
    cfg = dict(PROTOCOLO_PADRAO)
    arquivo = Path(caminho)
    if arquivo.exists():
        cfg.update(tomllib.loads(arquivo.read_text(encoding='utf-8')).get('monitoramento', {}))
    cfg['fase1'] = dict(cfg.get('fase1') or {})
    cfg['exclusoes'] = dict(cfg.get('exclusoes') or {})
    cfg['justificativas'] = dict(cfg.get('justificativas') or {})
    if cfg['protocolo'] != PROTOCOLO:
        raise ValueError(f'Protocolo incompatível; esta versão aplica {PROTOCOLO}.')
    if cfg['metodo_cox'] not in ('exato', 'normal'):
        raise ValueError('metodo_cox deve ser exato ou normal.')
    for chave in ('meses_minimos_fase1', 'meses_padrao_fase1', 'meses_fase2', 'dias_consolidacao'):
        if type(cfg[chave]) is not int:
            raise ValueError(f'{chave} deve ser um número inteiro.')
    if not 24 <= cfg['meses_minimos_fase1'] <= cfg['meses_padrao_fase1']:
        raise ValueError('A referência padrão deve respeitar o mínimo operacional de pelo menos 24 meses.')
    if cfg['meses_fase2'] < 1 or cfg['dias_consolidacao'] < 0:
        raise ValueError('Use horizonte positivo e prazo de cautela não negativo.')
    if type(cfg['exclusao_automatica']) is not bool:
        raise ValueError('exclusao_automatica deve ser true ou false, sem aspas.')
    for chave in ('lambda_ewma', 'largura_ewma', 'largura_x', 'alfa', 'max_exclusao'):
        v = cfg[chave]
        if isinstance(v, bool) or not isinstance(v, (int, float)) or not math.isfinite(v):
            raise ValueError(f'{chave} deve ser um número finito.')
    if not 0 < cfg['lambda_ewma'] <= 1 or min(cfg['largura_x'], cfg['largura_ewma']) <= 0:
        raise ValueError('Use λ em (0, 1] e larguras positivas.')
    if not 0 < cfg['alfa'] < 1 or not 0 <= cfg['max_exclusao'] < 1:
        raise ValueError('Use alfa em (0, 1) e fração de exclusões em [0, 1).')
    lags = cfg['defasagens_ljung_box']
    if not isinstance(lags, list) or not lags or any(type(v) is not int or v < 1 for v in lags):
        raise ValueError('Informe defasagens inteiras positivas para Ljung–Box.')
    for indicador, periodo in cfg['fase1'].items():
        if not isinstance(periodo, list) or len(periodo) != 2:
            raise ValueError(f'Informe início e fim da referência: {indicador}.')
        inicio, fim = map(mes, periodo)
        if _indice(fim) - _indice(inicio) + 1 < cfg['meses_minimos_fase1']:
            raise ValueError(f'Referência inferior ao mínimo operacional: {indicador}.')
    return cfg


def mes(texto) -> pd.Timestamp:
    """Converte 'AAAA-MM' (ou data) no primeiro dia do mês."""
    return pd.Timestamp(str(texto)[:7] + '-01')


def fim_fase2(fim_fase1, meses: int = 12) -> pd.Timestamp:
    """Último mês da fase II: os `meses` seguintes ao fim da fase I.

    Com a fase I terminando em dezembro, a fase II corresponde ao ano monitorado
    (janeiro a dezembro), como no monitoramento em tempo real de Barros (2021).
    """
    if not isinstance(meses, (int, np.integer)) or meses < 1:
        raise ValueError('A fase II exige um número inteiro positivo de meses.')
    return mes(fim_fase1) + pd.DateOffset(months=int(meses))


def referencia_do_ano(serie: pd.DataFrame, ano_monitorado: int, padrao: int = 48, minimo: int = 24,
                      alfa: float = ALFA, defasagens_lb=(1, 12)) -> dict:
    """Referência fixa anterior ao ano monitorado, sem seleção por valores-p.

    Os argumentos legados ``minimo``, ``alfa`` e ``defasagens_lb`` são mantidos
    para compatibilidade; pressupostos são diagnósticos calculados em analisar.
    A ausência de cobertura é reportada pelo cálculo, sem encurtar a janela.
    """
    if not isinstance(padrao, (int, np.integer)) or padrao < 12:
        raise ValueError('A referência exige um número inteiro de pelo menos 12 meses.')
    fim = mes(f'{int(ano_monitorado) - 1}-12')
    inicio = fim - pd.DateOffset(months=padrao - 1)
    return dict(inicio=inicio, fim=fim, meses=padrao, aprovada=None, tentativas=[])


def sugerir_fase1(serie: pd.DataFrame, fim_fase1, padrao: int = 48, minimo: int = 24, passo: int = 12,
                  alfa: float = ALFA, defasagens_lb=(1, 12)) -> dict:
    """Regra exploratória legada para a referência (fora do protocolo v3).

    Parte dos `padrao` meses que terminam em `fim_fase1` e reduz a janela em
    `passo` meses enquanto Cox–Stuart ou Ljung–Box rejeitarem H0, até `minimo`.
    A normalidade não entra na regra: encurtar a série não a corrige.
    """
    if not all(isinstance(v, (int, np.integer)) for v in (padrao, minimo, passo)) or not 12 <= minimo <= padrao or passo < 1:
        raise ValueError('Use janelas inteiras: padrão ≥ mínimo ≥ 12 e passo positivo.')
    fim = mes(fim_fase1)
    s = serie.set_index('Período')
    tentativas = []
    tamanhos = list(range(padrao, minimo - 1, -passo))
    if tamanhos[-1] != minimo:
        tamanhos.append(minimo)
    for tamanho in tamanhos:
        inicio = fim - pd.DateOffset(months=tamanho - 1)
        janela = s.loc[(s.index >= inicio) & (s.index <= fim), TAXA]
        if len(janela) == tamanho:
            x = janela.to_numpy(dtype=float)
            p_cs = cox_stuart(x)[2]
            p_lb = min(ljung_box(x, lag)[2] for lag in defasagens_lb if len(x) > lag + 2)
            aprovado = p_cs >= alfa and p_lb >= alfa
            tentativas.append({'Início': rotulo_mes(inicio), 'Fim': rotulo_mes(fim), 'Meses': tamanho,
                               'Cox–Stuart (p)': p_cs, 'Ljung–Box (menor p)': p_lb, 'Aprovada': aprovado})
            if aprovado:
                return dict(inicio=inicio, fim=fim, meses=tamanho, aprovada=True, tentativas=tentativas)
    inicio = fim - pd.DateOffset(months=minimo - 1)
    return dict(inicio=inicio, fim=fim, meses=minimo, aprovada=False, tentativas=tentativas)


def sensibilidade(serie: pd.DataFrame, fim_fase1, fim_fase2=None, janelas=(24, 36, 48, 64),
                  **parametros_analisar) -> pd.DataFrame:
    """Compara todas as janelas predefinidas, mantendo a mesma fase II.

    Nenhum cenário é selecionado por significância. Os testes são diagnósticos
    exploratórios, sem ajuste por multiplicidade. Falta de cobertura e outros
    impedimentos ficam visíveis na tabela, em vez de descartar cenários.
    """
    fim = mes(fim_fase1)
    linhas = []
    for tamanho in janelas:
        if not isinstance(tamanho, (int, np.integer)) or tamanho < 12:
            raise ValueError('As janelas de sensibilidade devem ter pelo menos 12 meses inteiros.')
        inicio = fim - pd.DateOffset(months=int(tamanho) - 1)
        opcoes = dict(parametros_analisar)
        opcoes['excluir'] = [mes(v) for v in opcoes.get('excluir', ()) if inicio <= mes(v) <= fim]
        linha = {'Meses': int(tamanho), 'Início': rotulo_mes(inicio), 'Fim': rotulo_mes(fim)}
        try:
            r = analisar(serie, inicio, fim, fim_fase2, **opcoes)
        except (ValueError, np.linalg.LinAlgError) as erro:
            linhas.append({**linha, 'Situação': 'Indisponível', 'Motivo': str(erro)})
            continue
        f2 = r.fase_ii
        consolidados = f2.loc[~f2['Em consolidação']] if not f2.empty else f2
        sinais = {nome: int((consolidados[coluna] != '').sum()) if not consolidados.empty else 0
                  for nome, coluna in [('Sinais X', 'Sinal X'), ('Sinais AM', 'Sinal AM'), ('Sinais EWMA', 'Sinal EWMA')]}
        linhas.append({**linha, 'Situação': 'Calculado', 'Motivo': '', 'μ0': r.params.mu0,
                       'σ0': r.params.sigma0, 'LIC X': r.params.lic_x, 'LSC X': r.params.lsc_x,
                       'LSC AM': r.params.lsc_am, 'Estável': r.params.estavel,
                       'Exclusões': ', '.join(r.params.excluidos + r.params.manuais),
                       'Meses fase II disponíveis': len(f2), 'Meses fase II consolidados': len(consolidados),
                       **sinais, **{f'{l["Teste"]} (p)': l['Valor-p'] for _, l in r.pressupostos.iterrows()}})
    return pd.DataFrame(linhas)


def sensibilidade_calendario(serie: pd.DataFrame, inicio_fase1, fim_fase1, fim_fase2=None,
                             **parametros_analisar) -> pd.DataFrame:
    """Compara taxas originais e ajustadas por 30,4375/dias do mês.

    Mantém fases, filtros e parâmetros iguais e desativa exclusão automática.
    A entrada não muda; taxas e quadrimestres oficiais não são substituídos.
    São contados somente sinais em meses fora da cautela operacional.
    """
    opcoes = dict(parametros_analisar, automatico=False)
    oficial = serie.copy()
    if TAXA_OFICIAL in oficial:
        oficial[TAXA] = oficial[TAXA_OFICIAL]
    linhas = []
    for nome, ajustar in [('Taxa oficial', False), ('Ajustada por dias (30,4375)', True)]:
        s = ajustar_calendario(oficial) if ajustar else oficial.copy()
        r = analisar(s, inicio_fase1, fim_fase1, fim_fase2, **opcoes)
        f2 = r.fase_ii
        avaliados = f2.loc[~f2['Em consolidação']] if not f2.empty else f2
        linha = {'Série': nome, 'μ0': r.params.mu0, 'σ0': r.params.sigma0,
                 'LIC X': r.params.lic_x, 'LSC X': r.params.lsc_x, 'LSC AM': r.params.lsc_am,
                 'Meses fora da cautela': len(avaliados), 'Exclusão automática': False,
                 'Início fase I': r.params.inicio, 'Fim fase I': r.params.fim,
                 'Início fase II': r.configuracao['inicio_fase2'],
                 'Fim fase II planejado': r.configuracao['fim_fase2_planejado']}
        for grafico in ('X', 'AM', 'EWMA'):
            sinais = avaliados.loc[avaliados[f'Sinal {grafico}'] != ''] if not avaliados.empty else avaliados
            linha[f'Sinais {grafico}'] = len(sinais)
            linha[f'Meses com sinal {grafico}'] = ', '.join(rotulo_mes(v) for v in sinais['Período'])
        linhas.append(linha)
    return pd.DataFrame(linhas)
