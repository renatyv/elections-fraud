# Методологический запрос — FGV CEPESP

**Para:** cepesp@fgv.br  
**Assunto:** Pedido de comentário metodológico: inferência de transferências com dados por seção

Olá, equipe do CEPESP,

Sou autor de uma análise independente dos dados eleitorais por seção do TSE. Gostaria de pedir um comentário metodológico ou a indicação de alguém da equipe que trabalhe com inferência ecológica e comportamento eleitoral.

Ajustei uma matriz de transferências entre os dois turnos de 2022 em 472.075 seções pareadas, por mínimos quadrados não negativos, com normalização das linhas. O ajuste agregado nas seções reservadas para validação tem R² de 0,976; a estimativa agregada da participação de Lula nessa amostra fica 0,7 ponto acima da observada.

Entendo que isso não identifica trajetórias individuais e que um bom ajuste agregado não valida, por si, cada taxa de transferência. Uma aplicação exploratória a 2026 também depende de mapear candidatos distintos — inclusive Flávio Bolsonaro a Jair Bolsonaro — e supor estabilidade entre eleições. Apresento essa aplicação como cenário condicional; o intervalo bootstrap não cobre toda essa incerteza.

Minha dúvida principal é: que validação adicional vocês considerariam mais informativa para avaliar a identificabilidade dessas transferências e a estabilidade regional do modelo? Por exemplo, validação por blocos geográficos ou comparação com evidência externa sobre transições individuais.

Resumo: [URL_DA_ANALISE]
Código: https://github.com/renatyv/elections-fraud/blob/main/brazil-oct-2026-round-1/scripts/run_paradox_analysis.py

Agradeço qualquer indicação de leitura, crítica ou encaminhamento.

[SEU_NOME]
