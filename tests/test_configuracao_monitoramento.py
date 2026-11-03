"""Configurações incorretas não devem ser truncadas ou reinterpretadas silenciosamente."""
import pytest

from dominio.monitoramento import ler_protocolo


@pytest.mark.parametrize('ajuste', [
    'meses_fase2 = 12.5',
    'meses_minimos_fase1 = 12',
    'exclusao_automatica = "false"',
    'lambda_ewma = 0',
    'alfa = 1',
    'max_exclusao = 1',
    'defasagens_ljung_box = [0]',
])
def test_configuracao_invalida_e_recusada(tmp_path, ajuste):
    arquivo = tmp_path / 'config.toml'
    arquivo.write_text('[monitoramento]\n' + ajuste)
    with pytest.raises(ValueError):
        ler_protocolo(arquivo)


def test_referencia_explicita_respeita_minimo_operacional(tmp_path):
    arquivo = tmp_path / 'config.toml'
    arquivo.write_text('[monitoramento.fase1]\n"Suicídio geral" = ["2025-01", "2025-12"]')
    with pytest.raises(ValueError, match='mínimo operacional'):
        ler_protocolo(arquivo)
    arquivo.write_text('[monitoramento]\nmeses_padrao_fase1 = 64\nmeses_fase2 = 18\n')
    cfg = ler_protocolo(arquivo)
    assert cfg['meses_padrao_fase1'] == 64 and cfg['meses_fase2'] == 18
