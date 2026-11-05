# Publicação do SAD

O aplicativo é publicado a partir de `main` no repositório privado `danjaca/tcc-indicadores-es`, com entrada `app.py` no Streamlit Community Cloud. A atualização do código foi autorizada pelo autor em 3 de novembro de 2026.

Esta publicação reúne as correções auditadas do monitoramento mensal parametrizável, a análise de sensibilidade, a validação dos dados e os relatórios PDF. O resumo do relatório apresenta os gráficos X, AM e EWMA; o histórico completo e as análises detalhadas permanecem nas páginas seguintes. Os parâmetros e as contagens da base preservada não foram alterados para a publicação.

Foram incluídos os módulos de execução, configurações, dependências, testes e documentação operacional. O workflow mensal permanece ativo, com os três arquivos adicionais de cálculo e relatórios incluídos no artifact de auditoria. A atualização do aplicativo não dispara uma nova extração de mortalidade.

Os documentos Word, capturas, versões anteriores e evidências detalhadas de `docs/auditoria/` permanecem no acervo local. Os relatórios de auditoria em Markdown descrevem também essas evidências locais; seus caminhos não significam que os arquivos tenham sido publicados. O conjunto histórico rastreado em `resultados_monitoramento/` foi preservado, sem enviar seu manifesto local modificado isoladamente.

Validação local anterior à publicação: 79 testes aprovados, 77 avisos de depreciação sem falhas, dependências verificadas com `pip check`. A base também passa por `python -m etl.validar`. O comando para reproduzir os relatórios está em [MONITORAMENTO.md](MONITORAMENTO.md).

Após o push, conferir o carregamento do aplicativo, os parâmetros mensais e o download do relatório PDF em [daniel-breda-indicadores-es.streamlit.app](https://daniel-breda-indicadores-es.streamlit.app/). A publicação do código e a conferência do aplicativo são registradas separadamente; não se presume sucesso apenas pelo envio ao GitHub.

## Revisão publicada em 5 de novembro de 2026

A publicação foi novamente autorizada pelo autor e o código funcional foi enviado ao `main` no commit `3bd6ca88a5f3fe2fbffee91a75179d097a42925e`. O remoto confirmou esse SHA. O Streamlit carregou a opção de ajuste por dias do mês, a comparação identificada com a escala oficial e o diagnóstico de causas inespecíficas. A opção foi ativada em produção para o indicador de jovens e o relatório foi baixado pelo próprio aplicativo: oito páginas, com X, AM e EWMA na capa, escala ajustada identificada, parâmetros quadrimestrais oficiais separados e suspensão dos sinais recentes. A captura e o PDF dessa verificação estão no acervo local de auditoria.

Validação final: 104 testes aprovados, 113 avisos de depreciação, 44,55 s no projeto; 104 aprovados, 113 avisos, 44,72 s em uma cópia isolada dos arquivos preparados para publicação. `pip check` passou e `python -m etl.validar` conciliou a base. O workflow `Atualização mensal dos indicadores` permanece ativo, com o agendamento preservado. Não foi disparada uma extração mensal completa nem se presume o êxito de uma execução futura. A consulta auxiliar foi independente e não substituiu o pacote principal.

O TCC final em DOCX e PDF tem 72 páginas e 75 localizadores de listas e sumário conferidos contra a renderização de entrega. As versões das principais bibliotecas estão no Quadro 2 e na metodologia. Arquivos acadêmicos e evidências locais continuam fora da implantação. A lista completa de recomendações, arquivos modificados, verificações, resultados e pendências está em [REVISAO_FINAL_20261105.md](REVISAO_FINAL_20261105.md).
