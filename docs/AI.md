# Inteligência Artificial — Insights CIEM

O CIEM pode usar **provedores de IA** (APIs compatíveis com OpenAI Chat Completions) para analisar alarmes e eventos de log agregados e apresentar **insights, recomendações e gráficos sugeridos** no portal e no Grafana.

## Princípios de acesso

| Quem | O que pode fazer |
|------|------------------|
| **Administrador** | Ativar/desativar, preencher URL, API key, modelo e demais opções; forçar regeneração |
| **Todos os usuários** (observer incluso) | Ver os insights **somente quando a função estiver habilitada** |

A tela de configuração aparece apenas na sidebar **Configuração** (somente admin).

## Configuração no portal

1. Login como `admin`
2. Sidebar **Configuração** → seção **Inteligência Artificial**
3. Marque **Habilitar Insights de IA**
4. Preencha os campos que ficam habilitados:
   - **URL base da API** (ex.: `https://api.openai.com/v1` ou endpoint interno)
   - **API Key**
   - **Modelo** (ex.: `gpt-4o-mini`)
   - Temperatura, tokens, intervalo de refresh, idioma, etc.
5. **Salvar IA**
6. Opcional: **Gerar insights agora**

Valores são persistidos em `config/ai.yaml`.

## Comportamento

- Com `enabled: false` (padrão): ninguém vê insights; endpoints retornam status `disabled`.
- Com `enabled: true` e API key válida: o Core chama o provedor, interpreta JSON e cacheia o resultado.
- Sem API key (ou falha no provedor): usa **análise heurística** local sobre alarmes/histórico (ainda útil no NOC).
- Cache respeita `refresh_interval_seconds` (padrão 300s).

## Onde os resultados aparecem

| Superfície | Detalhe |
|------------|---------|
| Portal → **Análise → Insights IA** (e preview na Visão geral) | Resumo, lista de insights e gráficos sugeridos |
| Portal → Visão Geral | Linha de status dos insights |
| Grafana → dashboard `ciem-insights` | Tabelas via Infinity (`/grafana/insights/table` e `/charts`) |
| Grafana → Visão Geral NOC | Painel “Insights de IA” |

## Arquivo `config/ai.yaml`

```yaml
ai:
  enabled: false
  provider: openai_compatible
  base_url: "https://api.openai.com/v1"
  api_key: ""
  model: "gpt-4o-mini"
  temperature: 0.2
  max_tokens: 1200
  refresh_interval_seconds: 300
  max_alarms: 40
  max_history: 60
  language: "pt-BR"
  verify_ssl: true
  chat_path: "/chat/completions"
```

> Não versionar API keys reais. Prefira segredos do ambiente / vault em produção.

## API

| Método | Caminho | Quem |
|--------|---------|------|
| `GET` | `/config/ai` | admin |
| `PUT` | `/config/ai` | admin |
| `GET` | `/insights` | qualquer autenticado |
| `POST` | `/insights/refresh` | admin |
| `GET` | `/grafana/insights` | token Grafana |
| `GET` | `/grafana/insights/table` | token Grafana |
| `GET` | `/grafana/insights/charts` | token Grafana |

A API key é mascarada nas respostas de `GET /config/ai`. Enviar `api_key` vazio ou mascarado (`****`) no `PUT` **não** sobrescreve a chave existente.

## Provedores compatíveis

Qualquer endpoint que implemente `POST {base_url}{chat_path}` no estilo OpenAI:

```json
{
  "model": "...",
  "messages": [{"role":"system","content":"..."},{"role":"user","content":"..."}],
  "temperature": 0.2,
  "max_tokens": 1200,
  "response_format": {"type": "json_object"}
}
```

Exemplos: OpenAI, Azure OpenAI (ajuste URL/path), gateways internos LiteLLM/Ollama com camada compatível, etc.

## Segurança

- Credenciais só na configuração admin
- Observer não acessa `/config/ai`
- Insights públicos **não** incluem a API key
- Prefira `verify_ssl: true` e redes internas para provedores on-prem
