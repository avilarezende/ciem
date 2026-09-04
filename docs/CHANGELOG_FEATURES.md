# Novidades — funções recentes do portal

Resumo das capacidades adicionadas ao CIEM para operação pelo portal (administração) e consumo por toda a equipe NOC.

## 1. Autenticação: usuários locais + LDAP opcional

| Capacidade | Detalhe |
|------------|---------|
| Usuários locais | Sempre disponíveis; prioridade no login |
| Admin padrão | `admin` / `admin123` — independente do LDAP |
| LDAP / AD | Admin configura servidor, porta, SSL, domínio, UID, filtros, bind e certificados |
| Gestão no portal | Criar usuário, alterar senha, habilitar/desabilitar, excluir (último admin protegido) |

**Documentação:** [AUTH.md](AUTH.md)

## 2. Módulos coletores com switch e formulário

| Capacidade | Detalhe |
|------------|---------|
| Switch ON/OFF | Admin ativa/desativa cada coletor em **Configuração** |
| Formulário de opções | Com o módulo ativo, aparecem URL, credenciais e opções específicas |
| Persistência | Valores gravados em `config/modules.yaml` |
| Grafana embutido | Aba Grafana no portal com visão NOC via API |

**Documentação:** [MODULES.md](MODULES.md), [PORTAL.md](PORTAL.md)

## 3. Insights de Inteligência Artificial

| Capacidade | Detalhe |
|------------|---------|
| Config só admin | URL do provedor, API key, modelo, temperatura, etc. |
| Resultados para todos | Com a função habilitada, observer e admin veem insights |
| Superfícies | Portal (aba Insights IA), dashboard Grafana `ciem-insights`, painel na Visão Geral NOC |
| Fallback | Sem API key ou falha do provedor → análise heurística local |

**Documentação:** [AI.md](AI.md)

## Papéis em uma frase

- **admin** — configura LDAP, usuários, módulos e IA; inicia sessões Guacamole  
- **observer** — monitora alarmes, histórico, Grafana e (se ativo) insights de IA  

## Arquivos YAML envolvidos

| Arquivo | Quem edita no portal |
|---------|----------------------|
| `config/auth.yaml` | Admin (usuários + LDAP) |
| `config/modules.yaml` | Admin (switch + opções) |
| `config/ai.yaml` | Admin (provedor de IA) |
| `config/main.yaml` | Em geral via repositório / ConfigMap |
| `config/targets.yaml` | Em geral via repositório / ConfigMap |
