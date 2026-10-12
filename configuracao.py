"""Caminhos portáveis. A aplicação e o ETL podem usar conjuntos isolados de dados."""
from pathlib import Path
import os
RAIZ = Path(__file__).resolve().parent
DADOS = Path(os.environ.get('TCC_DADOS_DIR', str(RAIZ / 'dados'))).expanduser().resolve()
ESTADO = Path(os.environ.get('TCC_ETL_RAIZ', str(RAIZ / 'var' / 'etl'))).expanduser().resolve()


def opcoes_painel():
    """Opções da seção [painel] de config.toml (ausente = valores padrão)."""
    try:
        import tomllib
    except ImportError:  # Python < 3.11: mantém os valores padrão
        return {}
    arquivo = RAIZ / 'config.toml'
    return tomllib.loads(arquivo.read_text(encoding='utf-8')).get('painel', {}) if arquivo.exists() else {}


# Aba experimental de aprendizado de máquina: desligada por padrão. Os resultados em dados_ml/
# foram gerados com a base anterior e precisam ser refeitos antes de qualquer reativação.
MOSTRAR_APRENDIZADO = bool(opcoes_painel().get('aprendizado_de_maquina', False))
