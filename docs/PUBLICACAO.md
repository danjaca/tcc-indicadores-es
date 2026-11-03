# Publicação do SAD

O aplicativo é publicado a partir de `main` no repositório privado `danjaca/tcc-indicadores-es`, com entrada `app.py` no Streamlit Community Cloud. A atualização do código foi autorizada pelo autor em 3 de novembro de 2026.

Esta publicação reúne as correções auditadas do monitoramento mensal parametrizável, a análise de sensibilidade, a validação dos dados e os relatórios PDF. O resumo do relatório apresenta os gráficos X, AM e EWMA; o histórico completo e as análises detalhadas permanecem nas páginas seguintes. Os parâmetros e as contagens da base preservada não foram alterados para a publicação.

Foram incluídos os módulos de execução, configurações, dependências, testes e documentação operacional. O workflow mensal permanece ativo, com os três arquivos adicionais de cálculo e relatórios incluídos no artifact de auditoria. A atualização do aplicativo não dispara uma nova extração de mortalidade.

Os documentos Word, capturas, versões anteriores e evidências detalhadas de `docs/auditoria/` permanecem no acervo local. Os relatórios de auditoria em Markdown descrevem também essas evidências locais; seus caminhos não significam que os arquivos tenham sido publicados. O conjunto histórico rastreado em `resultados_monitoramento/` foi preservado, sem enviar seu manifesto local modificado isoladamente.

Validação local anterior à publicação: 79 testes aprovados, 77 avisos de depreciação sem falhas, dependências verificadas com `pip check`. A base também passa por `python -m etl.validar`. O comando para reproduzir os relatórios está em [MONITORAMENTO.md](MONITORAMENTO.md).

Após o push, conferir o carregamento do aplicativo, os parâmetros mensais e o download do relatório PDF em [daniel-breda-indicadores-es.streamlit.app](https://daniel-breda-indicadores-es.streamlit.app/). A publicação do código e a conferência do aplicativo são registradas separadamente; não se presume sucesso apenas pelo envio ao GitHub.
