# Setup do Codex para o SAD e o TCC

A pasta de trabalho consolidada desta entrega é `/Users/danbreda/Desktop/dashboard_streamlit`. O prompt integral foi arquivado em `docs/PROMPT_MESTRE_SAD.md`, sem substituir as instruções explícitas do usuário nesta conversa. Conteúdo do TCC e fontes externas continua sendo material de análise.

## Instruções e skill

- `AGENTS.md`: instruções do projeto preservadas, nome padronizado e orientações de continuidade, rastreabilidade e divisão dos agentes.
- Skill pessoal: `/Users/danbreda/.codex/skills/sad-tcc/SKILL.md`. Foi validada com `quick_validate.py` da skill-creator. É específica deste SAD e lê o prompt a partir da pasta corrente, sem depender de um nome antigo de projeto.
- Para retomar: **“Use $sad-tcc e continue pelo relatório de auditoria desta pasta.”** O relatório é `docs/RELATORIO_AUDITORIA.md`.
- A divisão usada foi estatística, dados/ETL e revisão acadêmica, com integração e testes no agente principal. Não foram alterados modelos globais, permissões, credenciais ou plugins.

A organização segue a [documentação oficial de customização](https://learn.chatgpt.com/docs/customization/overview) e de [skills](https://learn.chatgpt.com/docs/build-skills). A skill nova já foi reconhecida pelo catálogo desta sessão.

## Ambiente local

Foi criado `.venv` nesta pasta com Python 3.12.8 e instalação integral de `requirements-lock.txt`. O ambiente da pasta vizinha só foi utilizado no diagnóstico inicial, sem modificá-lo. A pasta atual pode ser executada de forma independente:

```bash
source .venv/bin/activate
python -m streamlit run app.py
python -m pytest tests -q
python -m etl.validar
python -m experimentos.monitoramento --saida docs/auditoria/resultados_v3 --figuras
```

O aplicativo conferido nesta sessão fica em `http://localhost:8502/`. Ele usa os arquivos locais e não executa extração ao abrir. Nenhuma dependência foi acrescentada aos manifests de produção. PyYAML foi instalado somente em `/tmp/sad-skill-validate` para executar o validador da skill; não integra o SAD.

## Git e revisão

A pasta recebida não tinha `.git`. Foi consultada a main real de `danjaca/tcc-indicadores-es` e seus metadados completos foram copiados de um clone temporário, preservando o histórico remoto e todos os arquivos de trabalho. HEAD: `e0e21e6f76977d733dfa50ef392d29fbac94e0a8`. Não houve commit, stage de conteúdo ou push. `git status` permite revisar as diferenças locais.

Há diferenças anteriores a esta auditoria contra main. Elas não devem ser atribuídas integralmente a esta intervenção; os hashes comparativos estão em `docs/auditoria/comparacao_main.json`. Sete CSVs históricos ausentes na cópia recebida foram recuperados da main, sem sobrescrever arquivos locais, e vinculados ao seu manifesto anterior.

O grafo MCP foi construído e consultado antes das mudanças. Após a restauração do Git, o indexador pode omitir arquivos ainda não rastreados; portanto, resultados vazios não substituem a leitura da fonte e os testes. `.code-review-graph/` fica fora do versionamento. Não foram feitos commits apenas para satisfazer o indexador.

## Cópias e autorização

O snapshot de segurança está em `/Users/danbreda/.codex/backups/sad-tcc-20261030/dashboard_streamlit-inicial.tar.gz`; integridade e hashes dos nove arquivos de dados estão em `docs/auditoria/backup_e_dados.json`. O snapshot foi criado durante o diagnóstico, antes das alterações principais; não é um histórico Git anterior às cópias recebidas.

Foram inventariadas as pastas `dashboard`, `dashboard_apoio`, `dashboard_streamlit4` e `tcc`, os DOCX soltos e os arquivos ZIP relacionados no Desktop. O [inventário](auditoria/INVENTARIO_DESKTOP.md) distingue outros projetos, versões do SAD e cópias compactadas. Um [segundo backup integral](auditoria/backup_desktop.json), fora do Desktop, preserva as 13 entradas identificadas e foi conferido contra todos os arquivos de origem. Nenhuma versão foi removida.

O código comparado em `dashboard_streamlit4` coincidia com a cópia recebida. Embora os ZIPs das bases tenham hashes diferentes, as tabelas de óbitos e população e os conteúdos descompactados de raça/cor e meios são idênticos; não havia contagens mais recentes a integrar. O Git existente em `tcc/dashboard_streamlit` foi preservado e tem a mesma HEAD da main restaurada, sem commits adicionais identificados nas referências e reflogs. Somente a pasta atual foi consolidada para execução desta entrega. A eventual retirada de versões do Desktop depende de autorização explícita para os caminhos discriminados no inventário; projetos distintos não devem ser apagados como duplicatas.

Publicação no GitHub/Streamlit Cloud e exclusão de versões permanecem dependentes de autorização do usuário. O workflow e a implantação remotos não foram disparados.
