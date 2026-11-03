# PROMPT MESTRE — AUDITORIA, EVOLUÇÃO DO SAD, VALIDAÇÃO ESTATÍSTICA E CONSOLIDAÇÃO DO TCC

Quero que você assuma o papel de um pesquisador experiente em Engenharia de Produção, com conhecimentos em Estatística Aplicada, séries temporais, vigilância epidemiológica, Sistemas de Apoio à Decisão (SAD), engenharia de software, Python, Streamlit e normalização de trabalhos acadêmicos segundo as normas ABNT.

Sua missão é realizar uma auditoria completa do meu projeto de TCC, atualizar a aplicação, avaliar criticamente os resultados estatísticos e produzir uma versão final academicamente consistente do trabalho.

Não comece modificando arquivos. Primeiro, estude profundamente o projeto atual, compreenda sua arquitetura, os resultados já produzidos, os parâmetros utilizados, a fundamentação teórica e a redação existente.

A prioridade é preservar a integridade científica do trabalho e garantir que a versão final represente fielmente aquilo que foi desenvolvido e validado.

---

# 1. CONCEPÇÃO CENTRAL DO TCC E CONTRIBUIÇÃO CIENTÍFICA

O trabalho está sendo desenvolvido no contexto da Engenharia de Produção e tem como contribuição central o desenvolvimento de um Sistema de Apoio à Decisão (SAD) para automatizar a extração, o processamento e o monitoramento de indicadores de mortalidade no Espírito Santo.

O objetivo geral que deve orientar a revisão do trabalho é:

**Desenvolver um Sistema de Apoio à Decisão para automatizar a extração, o processamento e o monitoramento de indicadores de mortalidade no Espírito Santo, incorporando recursos de análise estatística parametrizada que permitam aos profissionais da Vigilância explorar diferentes configurações temporais e avaliar o comportamento das séries históricas.**

Esse objetivo deve ser utilizado como referência para avaliar a coerência entre introdução, justificativa, objetivos específicos, metodologia, desenvolvimento, resultados e considerações finais.

É fundamental compreender que o trabalho possui contribuições complementares:

**Dimensão tecnológica e operacional:**
- Automatização da extração de dados;
- Estruturação e processamento dos indicadores;
- Redução da dependência de procedimentos manuais;
- Disponibilização dos resultados em uma aplicação Streamlit;
- Organização de um fluxo reproduzível de atualização e análise.

**Dimensão analítica e estatística:**
- Monitoramento do comportamento das taxas de mortalidade;
- Aplicação de procedimentos estatísticos fundamentados na literatura;
- Configuração de parâmetros temporais;
- Comparação de diferentes períodos de referência;
- Identificação de possíveis alterações nas trajetórias das séries;
- Disponibilização de recursos para análises próprias dos profissionais da Vigilância.

Não reduza o trabalho à aplicação de testes estatísticos. O monitoramento estatístico é uma funcionalidade importante do SAD, mas não representa sozinho a totalidade da contribuição desenvolvida.

Avalie se a caracterização como SAD está devidamente sustentada pelas funcionalidades efetivamente implementadas. Não utilize essa denominação apenas como recurso retórico.

---

# 2. AUDITORIA COMPLETA DO PROJETO ATUAL

Antes de qualquer modificação:

1. Examine a estrutura de diretórios.
2. Identifique os módulos de extração, tratamento, armazenamento, análise estatística e visualização.
3. Identifique o fluxo completo dos dados, desde a fonte até a apresentação na aplicação.
4. Localize todos os parâmetros utilizados nas análises.
5. Identifique os testes estatísticos efetivamente implementados.
6. Examine a metodologia e a fundamentação existentes.
7. Execute os testes existentes, quando possível.
8. Compare os resultados produzidos pelo código com aqueles apresentados no TCC.
9. Identifique inconsistências, limitações e possíveis erros metodológicos.
10. Verifique se a aplicação efetivamente realiza tudo aquilo que o texto afirma.

Produza um diagnóstico técnico contendo:

- Arquitetura atual;
- Funcionalidades implementadas;
- Funcionalidades incompletas;
- Testes executados;
- Resultados encontrados;
- Problemas identificados;
- Correções necessárias;
- Limitações técnicas e metodológicas.

Não considere o código correto apenas porque executa sem apresentar erros.

Diferencie resultados efetivamente reproduzidos de resultados documentados em execuções anteriores.

Não invente resultados nem presuma que arquivos ou funcionalidades existem sem verificá-los.

---

# 3. REVISÃO DA FUNDAMENTAÇÃO METODOLÓGICA

Estou utilizando Barros (2021) e outros autores como referências metodológicas para a construção do monitoramento estatístico, especialmente na aba denominada Monitoramento Estatístico.

Quero que você examine detalhadamente essa relação.

Identifique:

- Quais procedimentos foram reproduzidos de Barros (2021);
- Quais foram adaptados;
- Quais foram desenvolvidos especificamente para este projeto;
- Quais decisões ainda precisam de fundamentação;
- Quais diferenças decorrem das características dos dados utilizados.

Não quero afirmar que estou reproduzindo integralmente a metodologia de Barros se isso não for verdadeiro.

Também não quero transformar o TCC em uma comparação permanente com esse autor.

Mantenha as referências quando fundamentarem efetivamente uma escolha metodológica, mas permita que o texto desenvolva uma narrativa científica própria.

A fundamentação deve explicar por que os métodos são adequados ao problema investigado, e não apenas informar de qual autor foram retirados.

Avalie se é necessário mencionar explicitamente Barros (2021) na descrição de cada procedimento ou se uma apresentação metodológica bem estruturada, com as referências pertinentes, é suficiente.

---

# 4. PARAMETRIZAÇÃO E ANÁLISE DAS FASES TEMPORAIS

Esta é uma das partes mais importantes da revisão.

Quero compreender e justificar todos os parâmetros utilizados no monitoramento estatístico.

A fase 1 representa o período histórico de referência utilizado na análise, enquanto a fase 2 representa o período de monitoramento.

Quero permitir que o profissional da Vigilância escolha a extensão da fase 1, por exemplo:

- Últimos 48 meses;
- Últimos 64 meses;
- Outras extensões temporais metodologicamente justificáveis.

A seleção deve considerar a data inicial da fase 2 e a disponibilidade efetiva de dados anteriores a esse período.

Investigue:

1. Qual é a justificativa estatística para a extensão da fase 1?
2. Como a alteração do tamanho da fase 1 influencia os parâmetros estimados?
3. Como isso afeta a variabilidade, os limites de controle e a identificação de possíveis alterações?
4. Quais são as consequências de períodos de referência muito curtos ou muito longos?
5. Existe recomendação metodológica dos autores utilizados?
6. Quais parâmetros devem ser fixados e quais podem ser disponibilizados ao usuário?
7. Como apresentar análises de sensibilidade sem induzir o usuário a escolher configurações que favoreçam determinado resultado?
8. Como documentar as configurações utilizadas para permitir a reprodução de uma análise?

Não escolha parâmetros simplesmente porque produzem resultados semelhantes aos de Barros (2021).

Quero uma justificativa científica independente para cada decisão metodológica.

Considere também a possibilidade de implementar uma análise de sensibilidade, permitindo comparar diferentes extensões da fase 1 e verificar a estabilidade das conclusões.

Diferencie claramente uma análise de sensibilidade legítima de uma seleção retrospectiva de parâmetros baseada na obtenção de significância estatística.

---

# 5. INTERPRETAÇÃO DOS TESTES DE HIPÓTESES

Quero uma revisão cuidadosa dos testes estatísticos empregados.

Explique e verifique:

- Hipótese nula e hipótese alternativa;
- Estatística de teste;
- Nível de significância;
- Valor-p;
- Pressupostos dos testes;
- Poder estatístico, quando aplicável;
- Interpretação de resultados inconclusivos;
- Consequências de não rejeitar a hipótese nula.

Uma preocupação minha é apresentar resultados nos quais não foi possível rejeitar H₀.

Isso comprometeria o TCC?

Avalie essa questão cientificamente.

Não considere um resultado válido apenas quando ele confirma uma alteração estatisticamente significativa.

Diferencie ausência de evidência de alteração e evidência de ausência de alteração.

Não confunda ausência de significância com equivalência estatística.

Avalie se os testes são adequados ao objetivo do monitoramento e se existe necessidade de complementar a análise.

Não invente resultados, não altere parâmetros para obter significância estatística e não descarte resultados desfavoráveis à hipótese de pesquisa.

Se houver múltiplas configurações, apresente os resultados de maneira transparente e explique suas diferenças.

A qualidade científica deve estar na adequação do procedimento e na interpretação dos resultados, e não na obtenção de um resultado previamente desejado.

---

# 6. ATUALIZAÇÃO DA APLICAÇÃO STREAMLIT

Depois da auditoria, atualize a aplicação.

O sistema deverá permitir que profissionais da Vigilância executem análises próprias, com parâmetros configuráveis e documentação suficiente para compreender suas consequências.

Em particular:

- Permita configurar a extensão temporal da fase 1.
- Permita definir a data inicial da fase 2.
- Garanta coerência temporal entre as fases.
- Considere a disponibilidade real dos dados.
- Atualize automaticamente os cálculos dependentes dos parâmetros.
- Atualize os gráficos e indicadores.
- Apresente os parâmetros utilizados em cada execução.
- Evite configurações estatisticamente inadequadas.
- Disponibilize explicações breves sobre os parâmetros e suas implicações.

A interface deve ser intuitiva para um profissional da Vigilância que não necessariamente possui formação aprofundada em Estatística.

Considere a possibilidade de disponibilizar:

1. Uma configuração de referência, fundamentada na metodologia adotada no TCC.
2. Configurações alternativas para análises próprias.
3. Uma comparação de sensibilidade entre diferentes extensões da fase 1.

A configuração utilizada para gerar os resultados apresentados no TCC deve ser identificável e reproduzível.

Não exponha parâmetros desnecessários apenas para aumentar a quantidade de opções.

Preserve a arquitetura funcional existente sempre que possível. Não reescreva módulos inteiros sem necessidade.

Após as alterações, execute testes e verifique se os resultados são consistentes com os cálculos estatísticos.

---

# 7. REVISÃO INTEGRAL DO TEXTO ACADÊMICO

Quero que você produza a versão final mais coerente possível do TCC, considerando o sistema efetivamente desenvolvido e os resultados realmente encontrados.

A narrativa acadêmica deve deixar claro que se trata do desenvolvimento de um Sistema de Apoio à Decisão, com recursos de automatização e monitoramento estatístico parametrizado.

A dimensão estatística deve ser apresentada como parte da solução desenvolvida, e não como o único propósito do trabalho.

Revise:

- Introdução;
- Justificativa;
- Objetivo geral;
- Objetivos específicos;
- Fundamentação teórica;
- Metodologia;
- Desenvolvimento do sistema;
- Resultados e discussão;
- Considerações finais.

## 7.1. Introdução e justificativa

Apresente o problema operacional e informacional que motiva o desenvolvimento do sistema.

Destaque a importância da automatização da extração e do processamento de indicadores de mortalidade, bem como a necessidade de disponibilizar informações estruturadas para apoiar o monitoramento.

Não antecipe resultados estatísticos na introdução.

Explique a relevância do sistema para o contexto da Vigilância em Saúde e sua contribuição para a Engenharia de Produção.

## 7.2. Objetivos

Utilize o objetivo geral estabelecido neste prompt como referência.

Avalie se os objetivos específicos representam etapas efetivamente desenvolvidas, como:

- Automatização da extração dos indicadores;
- Estruturação e processamento dos dados;
- Desenvolvimento da aplicação;
- Implementação dos recursos de monitoramento estatístico;
- Disponibilização de parâmetros configuráveis para análise.

Não inclua objetivos que não tenham sido efetivamente atendidos.

## 7.3. Metodologia

Explique o processo de desenvolvimento do sistema, a obtenção e o processamento dos dados, a implementação dos indicadores e os procedimentos estatísticos utilizados.

Diferencie claramente a metodologia de desenvolvimento do SAD da metodologia de análise estatística.

Apresente os parâmetros efetivamente utilizados nos resultados demonstrativos.

Explique a fundamentação das escolhas metodológicas sem transformar a seção em uma justificativa repetitiva de cada decisão.

## 7.4. Resultados e discussão

Apresente os resultados do sistema como um todo.

Considere:

- Automatização do processo;
- Funcionamento da extração;
- Estruturação dos indicadores;
- Disponibilização da aplicação;
- Funcionalidades de monitoramento;
- Resultados estatísticos;
- Possibilidade de parametrização;
- Reprodutibilidade das análises.

Não reduza os resultados à apresentação de gráficos e valores-p.

Discuta o que o sistema permite realizar, quais informações oferece e quais são suas limitações.

## 7.5. Considerações finais

Retome o objetivo geral e avalie seu atendimento.

Apresente as contribuições tecnológicas e analíticas, as limitações e as possibilidades de evolução.

Não prometa resultados que o sistema ainda não consegue produzir.

---

# 8. ATUALIZAÇÃO E REVISÃO DOS DADOS

Elimine do texto informações operacionais desnecessárias, como datas específicas da última extração ou da última carga.

Não quero que o trabalho fique desatualizado toda vez que uma nova extração for realizada.

Preserve, entretanto, a explicação de que os dados estão sujeitos a atualizações e revisões.

Considere os possíveis atrasos na disponibilização de informações de mortalidade, decorrentes dos processos de verificação, investigação e consolidação dos registros.

O texto deve explicar que os resultados refletem os dados disponíveis no momento da consulta, podendo sofrer alterações em atualizações posteriores.

Diferencie a data de referência dos dados da data operacional de extração.

Não remova informações temporais que sejam necessárias para definir o recorte metodológico do estudo.

---

# 9. NORMALIZAÇÃO ABNT E REFERÊNCIAS

Faça uma revisão integral da normalização acadêmica.

Verifique as normas ABNT aplicáveis à estrutura do trabalho, citações, referências, tabelas, ilustrações e apresentação dos resultados.

Garanta:

- Citações autor-data consistentes;
- Correspondência entre citações e lista de referências;
- Referências completas e verificáveis;
- Numeração e identificação de figuras e tabelas;
- Padronização das legendas;
- Padronização das unidades de medida;
- Notação estatística consistente;
- Apresentação adequada de equações;
- Identificação das fontes de dados e de elaboração.

Diferencie corretamente:

**Fonte de dados:** origem dos dados utilizados na elaboração do gráfico ou tabela.

**Fonte de elaboração:** indicação de que a figura ou tabela foi elaborada pelo autor, eventualmente a partir de dados de determinada instituição.

Verifique também se a fonte apresentada abaixo dos gráficos corresponde à origem real dos dados e ao procedimento de elaboração.

Não invente referências, DOI, páginas ou informações editoriais.

Se uma referência não puder ser verificada, sinalize isso.

Utilize as versões vigentes das normas aplicáveis.

---

# 10. AVALIAÇÃO CRÍTICA E CONTRIBUIÇÃO PARA A ENGENHARIA DE PRODUÇÃO

Quero que você avalie criticamente se o trabalho apresenta uma contribuição consistente para a Engenharia de Produção.

Considere aspectos como:

- Automatização de processos;
- Redução de atividades manuais;
- Padronização de procedimentos;
- Organização do fluxo de informação;
- Reprodutibilidade;
- Disponibilização de informações para apoio à decisão;
- Flexibilidade operacional;
- Parametrização;
- Aplicabilidade na rotina da Vigilância.

Avalie se o SAD realmente oferece suporte à tomada de decisão ou se, no estado atual, caracteriza-se mais precisamente como uma ferramenta de monitoramento e visualização.

Se necessário, recomende ajustes conceituais ou funcionais para fortalecer essa caracterização.

Não force uma classificação acadêmica que não seja sustentada pelas funcionalidades.

---

# 11. ORGANIZAÇÃO FINAL DO PROJETO NO DESKTOP

Ao final, quero manter apenas uma pasta consolidada do projeto no Desktop.

Antes de qualquer exclusão:

1. Identifique todas as versões existentes.
2. Diferencie versões antigas, backups, arquivos de trabalho e arquivos necessários.
3. Identifique a versão efetivamente atualizada.
4. Faça uma cópia de segurança verificável.
5. Apresente a relação dos diretórios que pretende remover.
6. Aguarde minha autorização explícita antes de excluir qualquer versão.

Não exclua arquivos de maneira irreversível sem confirmação.

A pasta final deve conter apenas os componentes necessários para manutenção, execução e evolução do projeto.

Preserve os arquivos de documentação, referências, código, dados necessários e configurações de ambiente.

---

# 12. ENTREGÁVEIS FINAIS

Quero receber:

1. Diagnóstico técnico do projeto atual.
2. Resumo dos testes estatísticos executados e seus resultados.
3. Discussão metodológica sobre os parâmetros.
4. Análise específica da influência do tamanho da fase 1.
5. Aplicação Streamlit atualizada e testada.
6. Texto integral do TCC revisado e coerente com os resultados reais.
7. Referências bibliográficas verificadas e normalizadas segundo a ABNT.
8. Relação das alterações realizadas no código.
9. Relação dos testes executados e respectivos resultados.
10. Estrutura final recomendada para a pasta do projeto.
11. Avaliação crítica da contribuição do SAD para a Engenharia de Produção.
12. Identificação das limitações que ainda precisam ser reconhecidas na defesa.

---

# 13. CRITÉRIOS FUNDAMENTAIS DE QUALIDADE

Não quero que você simplesmente concorde com minhas escolhas.

Quero uma avaliação crítica e independente.

Se uma decisão estiver metodologicamente incorreta, explique o motivo e apresente uma alternativa fundamentada.

Se os resultados forem inconclusivos, apresente-os como inconclusivos.

Se determinado parâmetro não possuir justificativa suficiente, identifique a lacuna.

Se houver divergência em relação a Barros (2021), explique se ela decorre de uma adaptação metodológica, de diferenças nos dados ou de uma possível inconsistência.

Não tente produzir resultados que confirmem artificialmente a literatura.

Não omita resultados que não apresentem significância estatística.

Não altere dados ou procedimentos para melhorar a aparência dos resultados.

Não declare que o sistema está validado sem apresentar evidências dos testes realizados.

O texto final deve demonstrar que desenvolvi um Sistema de Apoio à Decisão funcional, parametrizado, reproduzível e fundamentado, capaz de automatizar o processamento de indicadores de mortalidade e oferecer recursos de monitoramento estatístico para que profissionais da Vigilância conduzam análises próprias com transparência metodológica.

**A contribuição central do TCC é o desenvolvimento do sistema. Os resultados estatísticos demonstram uma de suas aplicações, e não constituem o único critério de sucesso do trabalho.**

Trabalhe com rigor científico, preserve a integridade dos dados e priorize a coerência entre o que foi desenvolvido, o que foi testado e o que será afirmado no texto acadêmico.