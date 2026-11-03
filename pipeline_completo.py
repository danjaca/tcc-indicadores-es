"""Pipeline completo do SAD: atualiza os dados, recalcula o monitoramento e empacota os resultados.

Etapas
  1. confere o ambiente (Python 3.11 ou superior; recomendado 3.12);
  2. (opcional) instala as dependências fixadas em requirements-lock.txt;
  3. executa os testes automatizados sobre o código e os dados atuais;
  4. extrai do TabNet/SIM da SESA-ES, valida todas as camadas e publica os dados em dados/
     (atualizar.py --avaliar --publicar-local);
  5. recalcula o monitoramento estatístico (fase I, fase II, leitura quadrimestral, aplicação
     retrospectiva da regra, ARL e granularidade regional) e gera figuras e relatórios em PDF
     (experimentos.monitoramento --figuras);
  6. compara as contagens mensais com as da base anterior (revisões do SIM);
  7. grava envio/resultados_<data>.zip, o arquivo a ser enviado para atualizar o TCC.

Uso (na pasta do projeto, com o ambiente virtual ativado)
  python pipeline_completo.py                 reextrai os anos recentes (anos_reprocessamento no config.toml)
  python pipeline_completo.py --completo      reextrai toda a série, desde 2016 (mais demorado)
  python pipeline_completo.py --sem-extracao  apenas recalcula com os dados já presentes em dados/
  python pipeline_completo.py --instalar      instala as dependências antes de executar

Se alguma etapa falhar, o pacote de envio é gerado mesmo assim, com o registro da execução,
para que o erro possa ser analisado.
"""
from __future__ import annotations

import argparse
import json
import platform
import shutil
import subprocess
import sys
import time
import zipfile
from datetime import datetime
from pathlib import Path

RAIZ = Path(__file__).resolve().parent
ENVIO = RAIZ / 'envio'
RESULTADOS = RAIZ / 'resultados_monitoramento'


class Registro:
    def __init__(self, caminho: Path):
        self.caminho = caminho
        caminho.parent.mkdir(parents=True, exist_ok=True)
        caminho.write_text(f'Pipeline completo do SAD · início {datetime.now():%d/%m/%Y %H:%M:%S}\n', encoding='utf-8')

    def escrever(self, texto: str, tela: bool = True):
        if tela:
            print(texto, flush=True)
        with self.caminho.open('a', encoding='utf-8') as f:
            f.write(texto + '\n')


def executar(reg: Registro, nome: str, argumentos: list[str]) -> bool:
    """Executa `python <argumentos>` na pasta do projeto, mostrando e registrando a saída."""
    comando = [sys.executable, *argumentos]
    reg.escrever(f'\n=== {nome} ===\n$ {" ".join(comando)}')
    inicio = time.time()
    processo = subprocess.Popen(comando, cwd=RAIZ, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                                text=True, encoding='utf-8', errors='replace')
    for linha in processo.stdout:
        reg.escrever(linha.rstrip('\n'))
    processo.wait()
    duracao = time.time() - inicio
    ok = processo.returncode == 0
    reg.escrever(f'--- {nome}: {"concluída" if ok else "FALHOU (código " + str(processo.returncode) + ")"} '
                 f'em {duracao / 60:.1f} min')
    return ok


def ler_csv(caminho: Path):
    import pandas as pd
    return pd.read_csv(caminho) if caminho.is_file() else None


def comparar_series(anterior: Path, atual: Path, destino: Path) -> int:
    """Grava as contagens mensais que mudaram entre a base anterior e a nova."""
    import pandas as pd
    a, b = ler_csv(anterior), ler_csv(atual)
    if a is None or b is None:
        return -1
    chave = ['Indicador', 'Período']
    m = b[chave + ['Óbitos']].merge(a[chave + ['Óbitos']], on=chave, how='outer', suffixes=(' (nova base)', ' (base anterior)'))
    m['Diferença'] = m['Óbitos (nova base)'].fillna(0) - m['Óbitos (base anterior)'].fillna(0)
    mudou = m[(m['Diferença'] != 0) | m['Óbitos (base anterior)'].isna() | m['Óbitos (nova base)'].isna()]
    mudou.sort_values(chave).to_csv(destino, index=False)
    return int(len(mudou))


def resumo_texto(destino: Path, extras: dict):
    """Resumo legível dos resultados (data da base, referências, sinais e quadrimestres)."""
    linhas = [f'Resumo da execução · {datetime.now():%d/%m/%Y %H:%M}', '']
    manifesto = RESULTADOS / 'manifesto.json'
    if manifesto.is_file():
        m = json.loads(manifesto.read_text(encoding='utf-8'))
        linhas += [f"Data da base de dados: {m.get('data_base')}", f"Protocolo: {m.get('protocolo')}", '', 'Fase I e fase II por indicador:']
        for ind, (ini, fim) in m.get('referencia', {}).items():
            f2 = m.get('fase2', {}).get(ind, ['', ''])
            linhas.append(f'  - {ind}: fase I {ini} a {fim}; fase II {f2[0]} a {f2[1]}')
    sinais = ler_csv(RESULTADOS / 'resumo_sinais.csv')
    if sinais is not None:
        linhas += ['', 'Sinais nos meses consolidados da fase II:']
        for _, l in sinais.iterrows():
            linhas.append(f"  - {l['Indicador']}: X aumento {l['X (aumento)']}, X redução {l['X (redução)']}, AM {l['AM']}, "
                          f"EWMA aumento {l['EWMA (aumento)']}, EWMA redução {l['EWMA (redução)']}; primeiro sinal EWMA: "
                          f"{l['Primeiro sinal EWMA']}; meses avaliados {l['Meses avaliados']} "
                          f"({l['Meses em consolidação']} em consolidação)")
    for chave, valor in extras.items():
        linhas.append(f'{chave}: {valor}')
    destino.write_text('\n'.join(linhas) + '\n', encoding='utf-8')


def empacotar(reg: Registro, carimbo: str, extras: dict) -> Path:
    pasta = ENVIO / f'resultados_{carimbo}'
    pasta.mkdir(parents=True, exist_ok=True)
    resumo_texto(pasta / 'RESUMO.txt', extras)
    ambiente = {'python': sys.version, 'plataforma': platform.platform(), 'executavel': sys.executable,
                'gerado_em': datetime.now().isoformat(timespec='seconds')}
    try:
        congelado = subprocess.run([sys.executable, '-m', 'pip', 'freeze'], capture_output=True, text=True, timeout=120)
        ambiente['pacotes'] = congelado.stdout.splitlines()
    except Exception as exc:  # pragma: no cover - diagnóstico apenas
        ambiente['pacotes'] = [f'indisponível: {exc}']
    (pasta / 'ambiente.json').write_text(json.dumps(ambiente, ensure_ascii=False, indent=2), encoding='utf-8')
    arquivo = ENVIO / f'resultados_{carimbo}.zip'
    incluir = [RAIZ / 'dados', RESULTADOS, RAIZ / 'docs' / 'ATUALIZACAO_DADOS.json', RAIZ / 'config.toml',
               RAIZ / 'var' / 'etl' / 'ultima_execucao.json']
    lotes = sorted((RAIZ / 'var' / 'etl' / 'lotes').glob('*/execucao.json'))
    if lotes:
        incluir.append(lotes[-1])
    with zipfile.ZipFile(arquivo, 'w', zipfile.ZIP_DEFLATED) as z:
        for item in incluir:
            if item.is_file():
                z.write(item, item.relative_to(RAIZ).as_posix())
            elif item.is_dir():
                for f in sorted(item.rglob('*')):
                    if f.is_file() and '__pycache__' not in f.parts:
                        z.write(f, f.relative_to(RAIZ).as_posix())
        for f in sorted(pasta.iterdir()):  # resumo, ambiente, revisões e registro da execução
            z.write(f, f'envio/{f.name}')
    return arquivo


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('--completo', action='store_true', help='Reextrai toda a série desde 2016.')
    ap.add_argument('--sem-extracao', action='store_true', help='Não consulta o TabNet; recalcula com os dados atuais.')
    ap.add_argument('--instalar', action='store_true', help='Instala requirements-lock.txt antes de executar.')
    ap.add_argument('--ignorar-testes', action='store_true', help='Prossegue mesmo se algum teste falhar.')
    args = ap.parse_args()

    carimbo = datetime.now().strftime('%Y%m%d_%H%M')
    reg = Registro(ENVIO / f'resultados_{carimbo}' / f'log_pipeline_{carimbo}.txt')
    reg.escrever(f'Python {sys.version.split()[0]} em {platform.platform()}')
    if sys.version_info < (3, 11):
        reg.escrever('Python 3.11 ou superior é necessário (recomendado 3.12).')
        return 2
    extras: dict = {'modo': 'completo (desde 2016)' if args.completo else ('sem extração' if args.sem_extracao else 'anos recentes')}
    ok = True
    try:
        if args.instalar:
            ok = executar(reg, 'Instalação das dependências', ['-m', 'pip', 'install', '-r', 'requirements-lock.txt'])
        if ok:
            ok_testes = executar(reg, 'Testes do código e dos dados atuais', ['-m', 'pytest', 'tests', '-q'])
            extras['testes'] = 'aprovados' if ok_testes else 'com falhas'
            ok = ok_testes or args.ignorar_testes
        anterior = ENVIO / f'resultados_{carimbo}' / 'serie_mensal_base_anterior.csv'
        if (RESULTADOS / 'serie_mensal.csv').is_file():
            shutil.copy2(RESULTADOS / 'serie_mensal.csv', anterior)
        if ok and not args.sem_extracao:
            comando = ['atualizar.py', '--avaliar', '--publicar-local']
            if args.completo:
                comando += ['--inicio', '2016', '--paralelo']
            ok = executar(reg, 'Extração do TabNet/SIM, validação e publicação dos dados', comando)
            extras['extracao'] = 'concluída e publicada em dados/' if ok else 'falhou (dados anteriores preservados)'
        if ok:
            ok = executar(reg, 'Monitoramento estatístico, figuras e relatórios em PDF',
                          ['-m', 'experimentos.monitoramento', '--figuras'])
        if ok and anterior.is_file():
            n = comparar_series(anterior, RESULTADOS / 'serie_mensal.csv',
                                ENVIO / f'resultados_{carimbo}' / 'revisao_contagens_mensais.csv')
            extras['meses com contagem revista em relação à base anterior'] = n
            reg.escrever(f'\nContagens mensais revistas em relação à base anterior: {n}')
    except KeyboardInterrupt:
        ok = False
        reg.escrever('\nExecução interrompida pelo usuário.')
    arquivo = empacotar(reg, carimbo, extras)
    reg.escrever('\n' + ('Pipeline concluído.' if ok else 'Pipeline interrompido: veja o registro acima.'))
    reg.escrever(f'Arquivo para envio: {arquivo}')
    return 0 if ok else 1


if __name__ == '__main__':
    sys.exit(main())
