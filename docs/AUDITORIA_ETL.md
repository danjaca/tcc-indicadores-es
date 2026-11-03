# Auditoria de dados, extração e atualização

Auditoria local de 30 de outubro de 2026. Os resultados deste documento referem-se ao snapshot identificado em [AUDITORIA_ETL.json](AUDITORIA_ETL.json). Nenhum arquivo de `dados/` foi alterado, nenhuma extração foi executada e nenhuma alteração foi publicada.

## Arquitetura examinada

Foram lidos os módulos de `etl/`, `dominio/dados.py`, `atualizar.py`, `pipeline_completo.py`, as vistas de mapa, meios e pirâmide, seus consumidores em `app.py`, testes, configurações, dependências e workflow. O grafo de revisão foi consultado para delimitar os consumidores; os achados foram verificados no código e com testes.

| Camada | Responsabilidade e controles existentes |
|---|---|
| `dominio/dados.py` | Lê o pacote local; define os três indicadores, elegibilidade por idade/sexo, taxas com denominador anual e cobertura mensal. Não depende do Streamlit. |
| `etl/definicao_cid.py` | Fonte única dos códigos dos numeradores. Separa categorias completas e subcategorias isoladas, sem incorporar integralmente Y87/Y89. |
| `etl/nucleo_tabnet.py` | Cliente HTTP/Selenium, contrato do formulário, consultas compostas disjuntas, parsing e evidências com hashes. Erro, coluna ausente ou contagem desconhecida não se tornam automaticamente zero. |
| `etl/pipeline.py` | Extração principal por município, mês, causa, idade e sexo; controles antes/depois; SQLite transacional, checkpoints com hash, bloqueio de execução concorrente e exportação imutável. |
| `etl/incorporar_lote.py` | Confere manifesto e grade antes de substituir o ZIP do lote; preserva histórico e recusa mistura de definições de CID. |
| `etl/extrair_raca_cor.py` | Detalhamento de raça/cor, controles e diferença residual explicitamente classificada como sem classificação disponível. Não estima população por raça/cor. |
| `etl/extrair_meios_cid.py` | Detalhamento esparso de contagens positivas por CID; conciliação de totais por município, mês, sexo e indicador. Ausência de linha representa zero somente dentro de cobertura validada. |
| `etl/validar.py` | Gate de integridade e conciliação das camadas antes da publicação. Reutiliza os validadores da extração principal. |
| `atualizar.py` | Cria um lote isolado, atualiza as camadas, valida e, quando solicitado, calcula o monitoramento antes de copiar dados para o checkout. Registra falhas e mantém backup local. |
| `pipeline_completo.py` | Coordena testes, atualização, experimentos, figuras/PDFs e pacote de envio. A atualização de dados e a geração das figuras são etapas distintas. |
| `painel/vistas/` | Apresenta dados locais; mapa usa malhas/PDR locais, meios usam total do próprio detalhamento e pirâmide preserva o denominador declarado. |
| `.github/workflows/atualizacao-mensal.yml` | Usa Ubuntu/Python 3.12, dependências fixadas, testes, validação e lote isolado; somente após sucesso realiza commit dos dados. Guarda diagnóstico em artifact por 90 dias. O workflow não foi disparado nesta auditoria. |

A aplicação não consulta o TabNet ao abrir. O Streamlit e o ETL compartilham caminhos portáveis de `configuracao.py`, com isolamento por `TCC_DADOS_DIR` e `TCC_ETL_RAIZ`. As dependências da interface continuam separadas das de extração. Nenhuma dependência foi acrescentada.

## Falhas corrigidas no gate de publicação

1. **Conciliação histórica omitida no comando padrão.** Antes, `python -m etl.validar` recebia uma lista vazia e não executava a comparação de complementos contra a fato principal. Agora a ausência de `--anos` confere todos os anos disponíveis; `--anos AAAA ...` restringe explicitamente essa comparação. Um ano solicitado sem cobertura é recusado.
2. **Datas e domínios por ano insuficientemente verificados.** Uma data em `dt_obito` incompatível com `ano`/`mes` podia passar. O gate agora reutiliza `validar_fato` e `validar_pop`, que também verificam a grade, os domínios e os valores de cada ano. A cobertura mensal registrada nos metadados deve coincidir com as linhas da fato.
3. **Categorias estranhas nos complementos.** Linhas de indicador, município, ano, mês, sexo ou CID fora do domínio podiam escapar da comparação quando não alteravam os totais. Agora são recusadas inclusive quando contêm zero. Os CIDs são verificados contra a causa elegível de cada indicador; o indicador de mulheres aceita apenas sexo feminino. Linhas fora da cobertura declarada do complemento também são recusadas.

Esses controles interrompem a publicação; não corrigem, preenchem nem excluem dados. A janela de atualização recente e os parâmetros estatísticos não foram alterados por esta parte da auditoria.

## Resultado observado no snapshot

- 724.464 linhas da fato de óbitos, com os 78 municípios e definição de CID `8d8be8e86012`.
- Cobertura de janeiro a dezembro em 2016–2025 e de janeiro a setembro em 2026.
- Conciliação de raça/cor e meios com a fato principal aprovada para todos os 11 anos, por município, mês, sexo e indicador.
- População de 2026 proveniente de 2025, identificada como provisória. O procedimento não projeta crescimento; mantém a população anterior por no máximo um ano, conforme configuração existente.
- SHA-256 do `dataset.zip`: `671c47f5bd4643ddf6802da7c6732b06de6631f6218ad313775b571a60951518`.

Controles de cálculo para 2024, com 12 meses e todos os municípios:

| Indicador | Óbitos | População anual elegível | Taxa por 100 mil |
|---|---:|---:|---:|
| Suicídio geral | 354 | 4.102.129 | 8,629665 |
| Homicídios — jovens de 15 a 29 anos | 483 | 874.575 | 55,226824 |
| Homicídios — mulheres de 10 a 59 anos | 90 | 1.454.086 | 6,189455 |

Esses números resultam dos arquivos locais e do cálculo do sistema. Não constituem uma nova extração ou nova conferência independente com a fonte. As referências externas preexistentes permanecem em `tests/referencias.json` e `docs/CONFERENCIA_REFERENCIAS.json`.

## Consistência dos gráficos descritivos

As taxas usam população anual elegível; recortes de quatro meses não são anualizados. Idade ou sexo ignorado não recebem denominador populacional inventado. O painel bloqueia meses indisponíveis antes de montar as tabelas e o mapa.

A pirâmide representa a proporção de óbitos, não uma taxa populacional: ocultar uma idade não redefine seu denominador. Idade/sexo ignorados permanecem no total, mas não são desenhados. Os dois lados juntos podem somar menos de 100%. Os testes adicionais verificam esse comportamento e a omissão de anos sem cobertura completa.

O detalhamento de meios calcula a frequência relativa sobre o próprio total e avisa quando ele diverge da base principal. A comparação com um ano sem cobertura mantém valores ausentes, sem desenhá-los como zero. Os testes adicionais verificam total, soma dos percentuais e ausência de cobertura. A linha que conecta meios é uma comparação entre categorias, não uma série temporal.

## Verificação executada

Ambiente aproveitado em modo de leitura: Python 3.13.3 do ambiente virtual existente na pasta vizinha `dashboard_streamlit4`; pandas 2.2.3, numpy 2.5.3, Streamlit 1.63.0, Plotly 6.9.0 e pytest 8.4.2. Nenhum pacote foi instalado nesse ambiente.

```bash
python -m pytest tests/test_validacao.py tests/test_dados_visuais.py tests/test_pipeline.py tests/test_atualizacao.py tests/test_definicao_cid.py -q
python -m etl.validar
python atualizar.py --planejar
```

Resultado do recorte de testes: **31 aprovados** (20 existentes e 11 novos), em 3,61 segundos. A validação CLI, sem `--anos`, aprovou todos os 11 anos. O planejamento não acessou a rede e mostrou a janela recente configurada com motor `requests` e publicação local desativada. A suíte completa e a verificação das telas constam no relatório geral da auditoria.

Os testes novos usam dados sintéticos em diretórios temporários; nenhum teste altera a base entregue. Cobrem divergência de contagens, data mensal incoerente, metadados de cobertura, domínios complementares, ano inexistente, zero fora de cobertura e denominadores das vistas.

## Identificação das pastas e rastreabilidade

No início da auditoria, `dashboard_streamlit` e `dashboard_streamlit4` não continham `.git`, e os comandos Git não identificaram repositório em nenhuma delas. Os 45 arquivos de código/documentação/configuração comparados eram idênticos; `agents.md` existia apenas na pasta atual. Entretanto, `dataset.zip`, complementos e seus metadados diferiam; malhas e PDR eram idênticos. A pasta vizinha não foi modificada. Essa comparação não identifica a branch `main` nem a versão implantada.

`docs/ATUALIZACAO_DADOS.json` registra uma execução histórica e um SHA-256 diferente do snapshot atual. Foi preservado como evidência dessa execução, sem ser apresentado como manifesto da base auditada. [AUDITORIA_ETL.json](AUDITORIA_ETL.json) identifica os arquivos atuais, hashes, cobertura, ambiente e o resultado da validação offline.

## Limitações e pendências

- A extração completa, Selenium, FTP/TabNet e a implantação efetiva no Streamlit Cloud não foram executados nesta parte da auditoria. Os testes com fonte simulada verificam orquestração, rollback, falha, checkpoints, cobertura e publicação condicionada.
- A configuração de produção declara Python 3.12; os testes locais desta parte usaram 3.13.3. O workflow não foi executado para validar um runner limpo de produção.
- A cópia local de vários arquivos é atômica por arquivo, não pelo conjunto; executar `--publicar-local` com o aplicativo local parado, conforme instrução existente. O checkout isolado do Actions envia os dados em um único commit após a validação.
- Consistência de totais não atesta completude epidemiológica. Meses recentes podem receber registros tardios, correções e reclassificações; o histórico também pode ser retificado.
- O intervalo de 60 dias é uma regra operacional de consolidação, não garantia de encerramento do SIM. A discussão metodológica e legal está no relatório geral.
- O mapa usa a malha e a classificação PDR documentadas no pacote. Reclassificações territoriais exigem preparação explícita para manter comparabilidade.
- Os artifacts do workflow expiram após 90 dias; a preservação de longo prazo das respostas originais requer arquivo externo. Commits dos dados não substituem essas evidências.
