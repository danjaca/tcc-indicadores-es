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

## Organização

- `app.py`, `modelo.py`, `mapa.py`, `meios.py`, `piramide.py`: interface, regras dos indicadores e visualizações.
- `configuracao.py`, `config.toml`: caminhos portáveis e parâmetros de atualização.
- `etl/`: aquisição, tratamento, persistência, incorporação e validação.
- `dados/`: conjunto utilizado pelo aplicativo, com metadados de cobertura e proveniência.
- `tests/`: testes permanentes de regressão, integridade, calendário e falhas. São controles de qualidade, não experimentos temporários.
- `.github/workflows/atualizacao-mensal.yml`: execução mensal e publicação dos dados validados no repositório.
- `var/etl/`: criada durante a execução; contém estado SQLite, evidências e lotes. Não é incluída na entrega nem no Git.

## Atualização mensal

```bash
python atualizar.py --planejar
python atualizar.py
```

O primeiro comando não consulta fontes externas. O segundo executa o processo em um lote isolado e conserva os dados publicados. Após validação, para atualizar os arquivos do checkout:

```bash
python atualizar.py --publicar-local
```

Usar `--publicar-local` com a aplicação local parada. A substituição de cada arquivo é atômica, mas a cópia do conjunto inteiro não constitui uma transação de sistema de arquivos. No GitHub Actions, a atualização ocorre em um checkout isolado e os arquivos são enviados juntos em um único commit, após a validação.

O intervalo padrão é o ano vigente e o anterior, calculado no fuso `America/Sao_Paulo`. Em janeiro, o ano novo não participa dos complementos enquanto não houver mês encerrado. `--inicio`, `--fim` e `--forcar` permitem reprocessamento explícito. O histórico fora da janela é preservado no pacote; solicitar anos que o TabNet não anuncia causa falha, nunca criação de zeros. O histórico entregue é necessário para reproduzir a série completa quando os anos antigos não estiverem acessíveis na fonte.

A configuração `anos_reprocessamento` controla a janela. `motor` aceita `requests` ou `selenium`; o projeto recebido usava `requests` nos executores, embora o núcleo ofereça Selenium. Mantém-se esse padrão. Para Selenium é necessário Chrome/Chromium compatível, acesso para o Selenium Manager obter o driver e instalação das dependências de ETL. O modo Selenium não foi executado nesta entrega.

As variáveis `TCC_ETL_RAIZ` e `TCC_DADOS_DIR` permitem usar diretórios específicos. O estado persistente controla revisões mensais e retomadas. No runner efêmero do GitHub, os dois anos são reextraídos a cada execução; não se depende de cache entre meses. Falhas, resultados parciais, cobertura regressiva e divergências dos complementos interrompem a publicação.

Os recortes históricos por raça/cor e meios podem ter datas de extração diferentes da fato principal. Os avisos existentes do painel foram mantidos. Os anos atualizados passam a exigir concordância por município, mês, sexo e indicador antes de publicação.

## Definição de CID e reprocessamento integral

As fichas incluem códigos de quatro caracteres (Y87.0, Y87.1 e Y89.0) que o campo "Causas 3 Dígitos" do TabNet não separa: Y87 também contém Y87.2 (intenção indeterminada) e Y89 contém Y89.1 e Y89.9. Por isso, o numerador é selecionado no campo "Subcategorias (20)" (capítulo XX), com todas as subcategorias das categorias completas e apenas as subcategorias exigidas de Y87 e Y89. A definição tem um identificador gravado nos metadados de cada ano.

Controles acrescentados:

- **Equivalência:** a cada ano, as subcategorias das categorias completas precisam somar o mesmo que as próprias categorias de três dígitos; diferença indica óbito sem subcategoria e interrompe a extração (4 consultas a mais por ano).
- **Série sem mistura:** `etl.incorporar_lote` recusa incorporar anos com a nova definição se outros anos da série ainda estiverem com a anterior; `etl.validar` recusa publicar base ou complementos (raça/cor e meios) com definições diferentes.
- **Meios:** Y22–Y24 entram em "Arma de fogo"; Y35 forma "Intervenção legal"; Y87.0, Y87.1 e Y89.0 formam "Sequelas (meio não especificado)". A dimensão passa de 50 para 57 códigos.

Primeira execução após esta mudança (local, com rede; pode levar várias horas):

```bash
python atualizar.py --inicio 2016 --forcar --publicar-local
python -m etl.gerar_referencias   # conferir os números com o TabNet/SESA
python -m pytest tests -q
python -m etl.validar
```

Depois de conferir os valores impressos por `etl.gerar_referencias` com o TabNet/SESA, registre-os em `tests/referencias.json`, na chave da nova definição (hoje `null`). Enquanto isso, os testes numéricos do painel são pulados com aviso. Em seguida, versionar código e `dados/` no mesmo commit. Uma atualização parcial (apenas a janela de dois anos) com a definição nova é bloqueada antes da publicação.

## Aprendizado de máquina (opcional)

A aba experimental fica desligada por padrão em `config.toml` (`[painel] aprendizado_de_maquina = false`). Os resultados de `dados_ml/` foram produzidos com a base e a definição de CID anteriores; não são atualizados pela rotina mensal. Para reativar, refazer os experimentos com a base publicada e mudar a opção para `true` (o teste correspondente volta a exigir que o manifesto aponte para a base atual).

## Agendamento e publicação

O workflow está configurado para o dia 15 de cada mês, às 09h17 UTC (06h17 em São Paulo, UTC−3), e pode ser disparado manualmente em Actions. O processamento pode durar horas em razão dos recortes municipais e intervalos entre consultas. O workflow tem limite de 330 minutos; se falhar ou expirar, o commit de dados não ocorre. Pode haver atraso de execução do agendamento do GitHub.

Publicar o conteúdo de `dashboard_streamlit` na raiz do repositório `danjaca/tcc-indicadores-es`, incluindo `.github` e `.streamlit`, preservando o histórico Git. O agendamento só fica ativo quando o workflow estiver na branch padrão e Actions estiver habilitado. Para o commit automático, o token do workflow precisa de escrita em conteúdo; regras de proteção da branch podem exigir adaptação para pull request. Não inserir credenciais nos arquivos.

O aplicativo indicado na documentação recebida é `https://daniel-breda-indicadores-es.streamlit.app/`, com entrada `app.py`. Esta entrega não confirma atualização desse endereço. Após o push, conferir implantação e logs; se uma mudança somente de dados não for detectada, reiniciar o app no Streamlit Community Cloud.

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

O pacote recebido contém 2016–2025 e janeiro–agosto de 2026, para 78 municípios de residência no Espírito Santo. Regiões: classificação fixa PDR 2024. Homicídios/agressões: CID-10 X85–Y09, Y22–Y24, Y35, Y87.1 e Y89.0; suicídios: X60–X84 e Y87.0, conforme as fichas de qualificação 1.8.15, 1.8.16 e 1.8.17 do PES-ES 2024–2027 (regra única em `etl/definicao_cid.py`). Os arquivos de `dados/` desta entrega ainda foram extraídos com a definição anterior (X85–Y09; X60–X84) e precisam do reprocessamento integral descrito abaixo. Indicadores: suicídio geral; homicídios aos 15–29 anos; homicídios de mulheres aos 10–59 anos.

A população é anual, filtrada pelo território, sexo e faixa etária elegíveis. Taxas quadrimestrais não são anualizadas. A população do ano anterior só é usada provisoriamente quando a fonte do ano correspondente não está disponível, com tolerância máxima de um ano e identificação no painel. Meses não disponíveis não equivalem a zeros. O projeto continua específico para o Espírito Santo; aplicá-lo a outro estado exige rever fontes, geografia, domínios e indicadores.

## Limpeza

Foram excluídos da distribuição caches, logs locais, respostas temporárias de conferência, binários de túnel, duplicatas de publicação, CSVs legados substituídos por `dataset.zip` e executores fixos de 2025/2026. Os núcleos de extração foram integrados em `etl/`; não há dependência de `proposta_etl_incremental` nem execução dinâmica de células de notebook. A documentação de modelagem segue as fases de preparação, modelagem e avaliação do CRISP-DM descritas no referencial teórico.

## Monitoramento estatístico

A aba **Monitoramento estatístico** implementa os métodos das seções 2.6.5 e 2.7 do TCC: u/u′, EWMA, CUSUM, canal endêmico e funil municipal. Referência e avaliação são separadas; limites e parâmetros podem ser exportados. Execute `python experimento_monitoramento.py` para reproduzir a avaliação temporal e simulada. Consulte [docs/MONITORAMENTO.md](docs/MONITORAMENTO.md) para o desenho de teste e as limitações. O snapshot recebido ainda usa CID legado; os resultados são exploratórios e devem ser refeitos após reprocessamento integral com a definição atual.
