"""Executa a extração principal sem dependência de notebooks."""
import argparse
from pathlib import Path
import tomllib
from datetime import datetime
from zoneinfo import ZoneInfo
from configuracao import RAIZ, ESTADO
from . import pipeline

def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--inicio',type=int,required=True)
    parser.add_argument('--fim',type=int,required=True)
    parser.add_argument('--forcar',action='store_true')
    args=parser.parse_args()
    cfg=tomllib.loads((RAIZ/'config.toml').read_text())['atualizacao']
    import os
    pipeline.RAIZ=ESTADO
    pipeline.HOJE=datetime.now(ZoneInfo('America/Sao_Paulo')).date()
    if not cfg['ano_inicial_historico'] <= args.inicio <= args.fim <= pipeline.HOJE.year:
        parser.error('Intervalo inválido; confira o início histórico e o ano atual.')
    pipeline.ANO_INICIAL=args.inicio;pipeline.ANO_FINAL=args.fim
    pipeline.ANOS_FORCADOS=set(range(args.inicio,args.fim+1)) if args.forcar else set()
    pipeline.MOTOR=os.environ.get('TCC_TABNET_MOTOR',cfg['motor'])
    pipeline.INTERVALO_SEGUNDOS=cfg['intervalo_segundos']
    pipeline.PERMITIR_POP_ANTERIOR=cfg['permitir_populacao_anterior']
    pipeline.JANELA_REVISAO=cfg['anos_reprocessamento']
    pipeline.executar()

if __name__=='__main__':main()
