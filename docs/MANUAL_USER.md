# Manual do usuário (observer)

Guia para operadores de NOC que **monitoram** o CIEM sem alterar a configuração do sistema.

| Credencial de desenvolvimento | Valor |
|-------------------------------|-------|
| Usuário | `observador` |
| Senha | `observer123` |

Admin padrão (referência): `admin` / `admin123` — ver [MANUAL_ADMIN.md](MANUAL_ADMIN.md).

## O que o observer pode fazer

| Pode | Não pode |
|------|----------|
| Ver Visão geral, **Navegador**, Alarmes, Histórico e Análise | Abrir Sessões / Guacamole |
| Usar **Lembretes / Anotações** flutuantes, aba **Calendário** e **Wiki** de serviços | Configurar LDAP, usuários, módulos ou IA |
| Ver insights de IA **quando habilitados pelo admin** | Criar ou excluir usuários |
| Abrir Grafana no navegador integrado ou em `/grafana/` | — |

## Login

1. Abra `https://<seu-dominio>/`  
2. Informe usuário e senha (local ou LDAP, se o admin tiver habilitado)  
3. Use **Sair** na sidebar para encerrar a sessão  

![Login](assets/ciem-portal-login.jpg)

## Navegação (sidebar)

| Item | Função |
|------|--------|
| **Visão geral** | KPIs, gráfico de severidade, preview de insights e status dos coletores |
| **Navegador** | Browser HTML5 no portal: Grafana, URLs e atalhos (Ctrl/Cmd+L foca a barra) |
| **Alarmes** | Lista de problemas ativos (priorize critical / high) |
| **Histórico** | Últimos eventos agregados dos módulos |
| **Análise** | Gráficos + detalhe por aba (resumo, insights IA, alarmes, módulos, histórico) |

Os itens **Sessões** e **Configuração** ficam ocultos para o papel observer.

## Fluxo diário sugerido

```
1. Login
2. Visão geral → conferir KPIs, coletores e chip de alarmes
3. Alarmes → triagem (critical primeiro)
4. Análise → Insights IA (se ativo) ou abas de detalhe
5. Navegador → Grafana embutido (ou /grafana/ em nova aba)
```

![Visão geral](assets/ciem-portal-dashboard.jpg)

## Visão geral

- **Chip de alarmes** no topo: atalho para a lista de alarmes  
- **KPIs**: críticos, warnings, total, módulos online  
- **Gráfico de severidade** e legenda  
- **Insights**: resumo curto; botão para abrir a Análise completa  
- **Coletores**: online / indisponível / desabilitado  

## Alarmes e histórico

![Alarmes](assets/ciem-portal-alarms.jpg)

- Severidades: `critical`, `high`, `warning`, `info`  
- Cada item mostra mensagem, módulo de origem e horário  
- O Histórico lista eventos recentes (não só alarmes abertos)  

## Análise

![Análise](assets/ciem-portal-analysis.jpg)

Abas disponíveis ao observer:

| Aba | Conteúdo |
|-----|----------|
| Resumo | Visão consolidada + status de IA |
| Insights IA | Recomendações e gráficos sugeridos (se IA ativa) |
| Alarmes | Distribuição + lista |
| Módulos | Saúde dos coletores |
| Histórico | Volume e eventos recentes |

Se Insights estiverem desabilitados, a aba informa que um administrador precisa ativar o provedor em Configuração.

## Lembretes, calendário e wiki

- **Lembretes / Anotações**: painel flutuante arrastável — tarefas e notas rápidas do turno; arraste pelo título; recolher/ocultar  
- **Calendário**: aba vertical à direita (ou botão **Calendário**) com agenda compartilhada Google/Outlook  
- **Wiki**: aba vertical à esquerda (ou botão **Wiki**) com páginas Markdown dos serviços da instituição — todos autenticados podem editar; só admin exclui  

![Wiki](assets/ciem-portal-wiki.jpg)

## Navegador HTML5

![Navegador HTML5](assets/ciem-portal-browser.jpg)

Disponível para **todos** os papéis desde o login:

- Sidebar **Navegador** (barra de endereço, voltar/avançar, recarregar, início)
- Atalhos: Grafana (`/grafana/`), URLs recentes
- Teclado: **Ctrl/Cmd+L** foca a barra de endereço
- Sites que bloqueiam iframe: use **↗** (nova aba) ou o aviso na área de conteúdo
- Atalhos também na Visão geral (**Abrir navegador**) e em Análise → **No navegador**

## Grafana

- Preferência: painel **Navegador** → atalho Grafana  
- Alternativa: link **Grafana ↗** na Análise, ou URL `/grafana/` em nova aba  
- Dashboards NOC e, se provisionado, painel de Insights IA  

## Problemas comuns

| Sintoma | O que fazer |
|---------|-------------|
| Não vejo Sessões/Configuração | Esperado para observer — peça a um admin |
| Página em branco no Navegador | Destino bloqueia iframe — use Abrir em nova aba (↗) |
| Insights “desabilitados” | Admin precisa ativar IA |
| Módulo “desabilitado” | Admin precisa ligar o coletor |
| Sem alarmes | Ambiente saudável ou coletor off — confirme na Visão geral |

Documentação relacionada: [USAGE.md](USAGE.md) · [PORTAL.md](PORTAL.md) · [AI.md](AI.md) · [DASHBOARDS.md](DASHBOARDS.md)
