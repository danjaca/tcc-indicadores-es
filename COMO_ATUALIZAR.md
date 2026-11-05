# Como atualizar todos os dados e enviar os resultados

Este roteiro executa, em outro computador com acesso à internet, o pipeline completo do SAD: extrai os óbitos do TabNet/SIM da SESA-ES, valida todas as camadas, publica a nova base em `dados/`, recalcula o monitoramento estatístico (fase I, fase II, leitura quadrimestral, análise de sensibilidade e retrospectivas exploratórias, ARL e granularidade regional), gera as figuras e os relatórios em PDF e empacota tudo em um único arquivo para envio.

## 1. Preparar o ambiente (uma vez)

Requisitos: Python 3.12 (3.11 também funciona) e acesso a `http://tabnet.saude.es.gov.br`.

Na pasta `dashboard_streamlit`:

```bash
python -m venv .venv
# Windows (PowerShell):   .venv\Scripts\Activate.ps1
# macOS/Linux:            source .venv/bin/activate
python -m pip install -r requirements-lock.txt
```

## 2. Executar o pipeline

```bash
python pipeline_completo.py
```

- Por padrão, reextrai o ano corrente e o anterior, calculados no fuso de São Paulo. O histórico fora dessa janela permanece no pacote e também pode receber retificações; não é considerado definitivamente fechado.
- Para reextrair toda a série desde 2016: `python pipeline_completo.py --completo` (pode levar algumas horas, pois o TabNet é consultado com intervalo entre as requisições).
- Para apenas recalcular com os dados já presentes: `python pipeline_completo.py --sem-extracao`.

O comando mostra o andamento de cada etapa: testes → extração e validação → publicação em `dados/` → monitoramento, figuras e relatórios em PDF → comparação com a base anterior → pacote de envio. Se a extração falhar (por exemplo, TabNet fora do ar), os dados publicados anteriormente são preservados e o pacote é gerado mesmo assim, com o registro do erro.

## 3. O que enviar

Ao final, o terminal mostra o caminho do arquivo:

```
envio/resultados_AAAAMMDD_HHMM.zip
```

Envie esse arquivo. Ele contém:

| Conteúdo | Uso na atualização do TCC |
|---|---|
| `dados/` | nova base publicada (dataset, camadas de raça/cor e meios, geografia) para refazer as telas do painel |
| `resultados_monitoramento/` | tabelas (CSV), `manifesto.json`, figuras e relatórios em PDF usados nos resultados |
| `envio/RESUMO.txt` | data da base, fases I e II e sinais de cada indicador |
| `envio/revisao_contagens_mensais.csv` | meses cujas contagens mudaram em relação à base anterior (revisões do SIM) |
| `envio/log_pipeline_*.txt` e `var/etl/.../execucao.json` | registro completo da execução, para auditoria ou diagnóstico |

## 4. Conferir o painel com os dados novos (opcional)

```bash
python -m streamlit run app.py
```

## Observações

- Os meses dentro do prazo de cautela configurado (padrão de 60 dias após o fim do mês, em relação à atualização da fonte) aparecem como "em consolidação". Trata-se de convenção operacional, não de prazo legal que assegure registro ou completude. Sua sinalização aparece suspensa e neutra na interface/PDF; os cálculos brutos são preservados e o histórico também pode ser revisto.
- Com `[monitoramento.fase1]` vazio, a referência padrão usa os 48 meses anteriores ao ano do último mês disponível. Períodos registrados explicitamente permanecem fixos até revisão responsável. Confira as fases, a cobertura e o manifesto a cada ciclo; não altere a referência apenas para mudar os sinais.
- Para um painel no Streamlit Community Cloud com código e protocolo já sincronizados, publique a pasta `dados/` validada no repositório (ou aguardar a rotina mensal do GitHub Actions, que executa o mesmo processo no dia 15).

A atualização também consulta causas inespecíficas nos anos reprocessados e cataloga snapshots/diferenças. O complemento possui estado disponível, obsoleto ou indisponível; falha não transforma ausência em zero nem bloqueia a base principal já validada. Preserve o artifact de auditoria e o histórico Git para acompanhar revisões: os 90 dias de retenção do serviço não são um arquivo permanente.
