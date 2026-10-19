# Sistema de apoio à decisão para indicadores de mortalidade do Espírito Santo

Projeto de Daniel Breda Bigossi, Engenharia de Produção, UFES. A aplicação consulta dados locais e o processo de atualização é executado separadamente. Esta versão incorpora o projeto refatorado e os métodos estatísticos de monitoramento previstos no referencial teórico.

## Execução

Python 3.12. Na pasta `dashboard_streamlit`:

```bash
python -m venv .venv
# macOS/Linux
source .venv/bin/activate
# Windows PowerShell: .venv\Scripts\Activate.ps1
python -m pip install -r requirements-lock.txt
python -m streamlit run app.py
```

`requirements.txt` contém as dependências da interface. `requirements-etl.txt` acrescenta as de extração; `requirements-dev.txt`, as de teste. `requirements-lock.txt` registra as versões instaladas e utilizadas na verificação desta entrega. Não distribuir nem versionar ambientes virtuais.

## Organização do projeto

O projeto segue uma arquitetura em camadas: `app.py` é o ponto de entrada do Streamlit; `painel/vistas/` monta as seções visuais; `dominio/` contém cálculos e regras sem dependência da interface; `etl/` extrai, transforma e valida os dados; e `experimentos/` guarda avaliações reproduzíveis que não rodam ao abrir o painel. `atualizar.py` coordena o ciclo mensal e continua sendo o comando público de atualização.

```text
app.py                         Entrada do Streamlit; filtros e composição das abas
atualizar.py                   Comando que coordena atualização, validação e publicação
configuracao.py                Caminhos de dados e estado; compartilhado pelo painel e ETL
config.toml                    Opções de atualização e recursos do painel
dominio/
  dados.py                     Leitura do pacote, indicadores, filtros, taxas e séries
  monitoramento.py             u/u′, EWMA, CUSUM, quartis e limites do funil
painel/vistas/
  monitoramento.py             Interface e guia de leitura do monitoramento estatístico
  mapa.py                      Mapa municipal e regional
  meios.py                     Composição por meio e CID-10
  piramide.py                  Perfil demográfico
etl/
  definicao_cid.py             Códigos CID-10 e seleção dos numeradores
  nucleo_tabnet.py             Cliente HTTP, consultas, parsing e utilitários TabNet
  pipeline.py                  Extração principal, estado e persistência incremental
  executar_base.py             Entrada CLI para executar a extração principal
  extrair_raca_cor.py          Extração complementar de raça/cor
  extrair_meios_cid.py         Extração complementar de meios/CID
  incorporar_lote.py           Incorpora resultados extraídos ao pacote do lote
  preparar_pdr.py              Prepara geografia e regiões do PDR
  validar.py                   Valida integridade e concordância das camadas
  gerar_referencias.py         Gera valores de regressão para conferência
  conferir_referencias.py      Confronta valores calculados com referências externas
experimentos/monitoramento.py  Avaliação estatística reproduzível, fora da interface
.github/workflows/             Agendamento e publicação mensal no GitHub
docs/                           Documentação operacional e metodológica
  MONITORAMENTO.md             Protocolo, reprodução e limitações estatísticas
  VERIFICACAO.md               Registro dos controles e verificações do projeto
  ATUALIZACAO_DADOS.json       Metadados da atualização de dados
  CONFERENCIA_REFERENCIAS.json Evidências de conferência externa
tests/                          Testes permanentes de regressão e integridade
  test_dashboard.py            Indicadores, filtros e visualizações principais
  test_monitoramento.py        Métodos estatísticos e interface de monitoramento
  test_pipeline.py             Extração, lotes e validação de dados
  test_definicao_cid.py        Regras dos numeradores CID-10
  test_atualizacao.py          Planejamento e publicação do ciclo mensal
  referencias.json             Valores de regressão conferidos para a base
dados/                          Pacote de dados, geografia e metadados de cobertura
resultados_monitoramento/       Resultados da avaliação estatística de referência
var/etl/                        Estado, lotes e evidências locais; criado durante a execução
```

Os módulos `etl/extrair_*.py` representam camadas de dados diferentes (base principal, raça/cor e meios), não cópias do projeto para cada mês. `atualizar.py` coordena essas camadas e aplica validação conjunta antes de publicar. Resultados temporários e estado de execução ficam em `var/etl/`, criados localmente e fora do Git.

## Atualização mensal

```bash
python atualizar.py --planejar
python atualizar.py
```

O primeiro comando não consulta fontes externas. O segundo executa o processo em um lote isolado e conserva os dados publicados. Após validação, para atualizar os arquivos do checkout:

```bash
python atualizar.py --avaliar --publicar-local
```

A opção `--avaliar` refaz o experimento estatístico sobre o lote isolado, depois da validação e antes da publicação. Se a análise falhar ou seu manifesto apontar para outro dataset, os dados publicados são preservados. Resultados e parâmetros ficam em `var/etl/lotes/<execução>/monitoramento/`; o snapshot de entrada fica em `dados/` dentro do mesmo lote. A opção sem `--avaliar` continua disponível para atualização apenas dos dados.

Usar `--publicar-local` com a aplicação local parada. A substituição de cada arquivo é atômica, mas a cópia do conjunto inteiro não constitui uma transação de sistema de arquivos. No GitHub Actions, a atualização ocorre em um checkout isolado e os arquivos são enviados juntos em um único commit, após a validação.

O intervalo padrão é o ano vigente e o anterior, calculado no fuso `America/Sao_Paulo`. Em janeiro, o ano novo não participa dos complementos enquanto não houver mês encerrado. `--inicio`, `--fim` e `--forcar` permitem reprocessamento explícito. O histórico fora da janela é preservado no pacote; solicitar anos que o TabNet não anuncia causa falha, nunca criação de zeros. O histórico entregue é necessário para reproduzir a série completa quando os anos antigos não estiverem acessíveis na fonte.

A configuração `anos_reprocessamento` controla a janela. `motor` aceita `requests` ou `selenium`; o projeto recebido usava `requests` nos executores, embora o núcleo ofereça Selenium. Mantém-se esse padrão. Para Selenium é necessário Chrome/Chromium compatível, acesso para o Selenium Manager obter o driver e instalação das dependências de ETL. O modo Selenium não foi executado nesta entrega.

As variáveis `TCC_ETL_RAIZ` e `TCC_DADOS_DIR` permitem usar diretórios específicos. O estado persistente controla revisões mensais e retomadas. `--paralelo` consulta base e complementos históricos em paralelo; o ano corrente depende da cobertura da base atualizada. Após uma falha, `--retomar-lote var/etl/lotes/IDENTIFICADOR` recupera as camadas históricas concluídas e reconsulta o ano corrente. Toda a série solicitada passa pela validação conjunta antes da publicação. No runner efêmero do GitHub, os dois anos são reextraídos a cada execução; não se depende de cache entre meses. Falhas, resultados parciais, cobertura regressiva e divergências dos complementos interrompem a publicação.

Os recortes históricos por raça/cor e meios podem ter datas de extração diferentes da fato principal. Os avisos existentes do painel foram mantidos. Os anos atualizados passam a exigir concordância por município, mês, sexo e indicador antes de publicação.

## Definição de CID e reprocessamento integral

As fichas incluem códigos de quatro caracteres (Y87.0, Y87.1 e Y89.0) que o campo "Causas 3 Dígitos" do TabNet não separa: Y87 também contém Y87.2 (intenção indeterminada) e Y89 contém Y89.1 e Y89.9. Por isso, o numerador é selecionado no campo "Subcategorias (20)" (capítulo XX), com todas as subcategorias das categorias completas e apenas as subcategorias exigidas de Y87 e Y89. A definição tem um identificador gravado nos metadados de cada ano.

Controles acrescentados:

- **Registros sem quarto dígito:** categorias completas são consultadas no campo de três dígitos e somadas, sem sobreposição, às subcategorias isoladas. Os HTMLs originais e os filtros de cada parte ficam conservados em uma evidência composta. O controle categoria/subcategoria registra os óbitos sem quarto dígito; estes são incluídos no numerador. Subcategorias que excedam suas categorias interrompem a extração.
- **Série sem mistura:** `etl.incorporar_lote` recusa incorporar anos com a nova definição se outros anos da série ainda estiverem com a anterior; `etl.validar` recusa publicar base ou complementos (raça/cor e meios) com definições diferentes.
- **Meios:** Y22–Y24 entram em "Arma de fogo"; Y35 forma "Intervenção legal"; Y87.0, Y87.1 e Y89.0 formam "Sequelas (meio não especificado)". A dimensão passa de 50 para 57 códigos.

Primeira execução após esta mudança (local, com rede; pode levar várias horas):

```bash
python atualizar.py --inicio 2016 --forcar --publicar-local
python -m etl.gerar_referencias   # conferir os números com o TabNet/SESA
python -m pytest tests -q
python -m etl.validar
```

Execute `python -m etl.conferir_referencias --registrar` para confrontar os valores calculados com consultas independentes ao TabNet/SESA. O comando registra referências numéricas somente após concordância e estabilidade dos retornos; grava a evidência em `docs/CONFERENCIA_REFERENCIAS.json`. Em seguida, versionar código e `dados/` no mesmo commit. Uma atualização parcial (apenas a janela de dois anos) com a definição nova é bloqueada antes da publicação.

## Agendamento e publicação

O workflow está configurado para o dia 15 de cada mês, às 09h17 UTC (06h17 em São Paulo, UTC−3), e pode ser disparado manualmente em Actions. O processamento pode durar horas em razão dos recortes municipais e intervalos entre consultas. O workflow tem limite de 330 minutos; se falhar ou expirar, o commit de dados não ocorre. Pode haver atraso de execução do agendamento do GitHub.

Publicar o conteúdo de `dashboard_streamlit` na raiz do repositório `danjaca/tcc-indicadores-es`, incluindo `.github` e `.streamlit`, preservando o histórico Git. O agendamento só fica ativo quando o workflow estiver na branch padrão e Actions estiver habilitado. Para o commit automático, o token do workflow precisa de escrita em conteúdo; regras de proteção da branch podem exigir adaptação para pull request. Não inserir credenciais nos arquivos.

O aplicativo publicado e conferido em 11/10/2026 é `https://daniel-breda-indicadores-es.streamlit.app/`, com entrada `app.py`. Após cada novo push, conferir implantação e logs; se uma mudança somente de dados não for detectada, reiniciar o app no Streamlit Community Cloud.

Referências operacionais:
- https://docs.github.com/en/actions/reference/workflows-and-actions/events-that-trigger-workflows
- https://docs.streamlit.io/deploy/streamlit-community-cloud/manage-your-app

## Verificação

```bash
python -m pytest tests -q
python -m etl.validar
python -m etl.validar --anos 2026
```

O último comando exige concordância dos complementos para o ano informado. As referências numéricas de 2024 nos testes ficam em `tests/referencias.json`, separadas por definição de CID; são uma base de regressão e devem ser revistas com evidência quando a fonte histórica for retificada; não ajustar dados para satisfazer testes.

## Escopo e regras epidemiológicas

O pacote atualizado contém 2016–2025 e janeiro–setembro de 2026, para 78 municípios de residência no Espírito Santo. Regiões: classificação fixa PDR 2024. Homicídios/agressões: CID-10 X85–Y09, Y22–Y24, Y35, Y87.1 e Y89.0; suicídios: X60–X84 e Y87.0, conforme as fichas de qualificação 1.8.15, 1.8.16 e 1.8.17 do PES-ES 2024–2027 (regra única em `etl/definicao_cid.py`). A série inteira e os complementos por raça/cor e meios foram reextraídos com essa mesma definição. A população de 2026 utiliza provisoriamente a estimativa de 2025, até a disponibilidade da estimativa correspondente na fonte. Indicadores: suicídio geral; homicídios aos 15–29 anos; homicídios de mulheres aos 10–59 anos.

A população é anual, filtrada pelo território, sexo e faixa etária elegíveis. Taxas quadrimestrais não são anualizadas. A população do ano anterior só é usada provisoriamente quando a fonte do ano correspondente não está disponível, com tolerância máxima de um ano e identificação no painel. Meses não disponíveis não equivalem a zeros. O projeto continua específico para o Espírito Santo; aplicá-lo a outro estado exige rever fontes, geografia, domínios e indicadores.

## Limpeza

Foram excluídos da distribuição caches, logs locais, respostas temporárias de conferência, binários de túnel, duplicatas de publicação, CSVs legados substituídos por `dataset.zip` e executores fixos de 2025/2026. Os núcleos de extração foram integrados em `etl/`; não há dependência de `proposta_etl_incremental` nem execução dinâmica de células de notebook. A documentação de modelagem segue as fases de preparação, modelagem e avaliação do CRISP-DM descritas no referencial teórico.

## Monitoramento estatístico

A aba **Monitoramento estatístico** implementa os métodos das seções 2.6.5 e 2.7 do TCC: u/u′, EWMA, CUSUM, canal endêmico e funil municipal. Referência e avaliação são separadas; limites e parâmetros podem ser exportados. Execute `python -m experimentos.monitoramento` para reproduzir a avaliação temporal e simulada. Consulte [docs/MONITORAMENTO.md](docs/MONITORAMENTO.md) para o desenho de teste e as limitações. Os resultados foram recalculados com a série reextraída e a definição CID atual. O botão **ⓘ Como ler** abre o guia dos indicadores, filtros, limites e sinais. A escolha de região aplica o PDR 2024 juntamente com os municípios selecionados. A calibração e a avaliação epidemiológica para uso operacional permanecem necessárias.

## Reprodução do ciclo mensal

O agendamento usa `python atualizar.py --avaliar --publicar-local`. Cada ciclo gera e valida os dados, reproduz o experimento interanual e publica os dados somente após sucesso. O workflow guarda o snapshot de entrada, evidências de aquisição, resultados, parâmetros e os arquivos necessários ao cálculo em um artifact de auditoria por execução. O commit automático contém somente `dados/`; CSVs de avaliação, caches e evidências não entram no Git.

A retenção do artifact é de 90 dias. Para manter a evidência durante todo o TCC e comparar revisões entre meses, arquive os artifacts antes de expirarem em um armazenamento persistente. Os commits de dados preservam as versões publicadas, mas não substituem o arquivo dos retornos originais das fontes.

`resultados_monitoramento/` contém o experimento de referência já entregue, não o resultado de cada atualização futura. Para consultar um ciclo novo, use a pasta `monitoramento/` do seu lote/artifact. Para repetir o cálculo sem consultar as fontes, aponte `TCC_DADOS_DIR` para o snapshot desse ciclo e execute:

```bash
TCC_DADOS_DIR=/caminho/do/snapshot/dados python -m experimentos.monitoramento --saida /caminho/da/reproducao
```

O manifesto registra anos da referência, parâmetros efetivamente aplicados, períodos, semente, versões das bibliotecas e hashes das entradas e do código de cálculo. Para reproduzir um protocolo alterado, use os argumentos e a versão de código correspondentes ao manifesto. A data de geração do manifesto muda em cada execução; os CSVs devem coincidir quando entradas, protocolo e ambiente forem os mesmos.
