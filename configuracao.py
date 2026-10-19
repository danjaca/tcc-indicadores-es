"""Caminhos portáveis. A aplicação e o ETL podem usar conjuntos isolados de dados."""
from pathlib import Path
import os
RAIZ = Path(__file__).resolve().parent
DADOS = Path(os.environ.get('TCC_DADOS_DIR', str(RAIZ / 'dados'))).expanduser().resolve()
ESTADO = Path(os.environ.get('TCC_ETL_RAIZ', str(RAIZ / 'var' / 'etl'))).expanduser().resolve()
