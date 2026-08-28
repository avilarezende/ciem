# Arquitetura — Conversador PoP-SE

## Visão geral

Sistema modular de chatbot com IA gratuita (Ollama por padrão) para atender clientes de conectividade do PoP-SE/RNP em Sergipe.

```
┌─────────────┐  ┌──────────────┐  ┌──────────────┐
│  Web (Apache)│  │ Telegram Bot │  │ Discord Bot  │  ... canais
└──────┬──────┘  └──────┬───────┘  └──────┬───────┘
       │                │                  │
       └────────────────┼──────────────────┘
                        ▼
              ┌─────────────────┐
              │  Engine (FastAPI)│
              │  - Persona PoP-SE│
              │  - Memória (PG)  │
              │  - RAG (Chroma)  │
              │  - LLM (Ollama)  │
              └────────┬────────┘
                       ▲
       ┌───────────────┼───────────────┐
       │               │               │
┌──────┴──────┐ ┌──────┴──────┐ ┌─────┴─────┐
│ Email MS    │ │ Sources     │ │ WhatsApp  │
│ (Graph API) │ │ Zabbix/Cacti│ │ Webhook   │
└─────────────┘ └─────────────┘ └───────────┘
```

## Containers

| Serviço | Função | Profile |
|---------|--------|---------|
| `postgres` | Memória persistente de usuários | `core` |
| `ollama` | LLM gratuito local | `core` |
| `engine` | Núcleo de conversação e RAG | `core` |
| `web` | Apache + página de chat | `core` |
| `module-telegram` | Canal Telegram | `telegram` |
| `module-discord` | Canal Discord | `discord` |
| `module-whatsapp` | Canal WhatsApp | `whatsapp` |
| `module-email-microsoft` | Coleta e-mails 365 | `email` |
| `module-sources` | Coletores de monitoração | `sources` |

## Configuração

- `config/clients.yaml` — instituições clientes e links
- `config/modules.yaml` — ativar/desativar módulos
- `config/sources.yaml` — parâmetros das fontes RAG
- `.env` — credenciais (copiar de `.env.example`)

## Extensibilidade

1. **Novo canal**: criar pasta em `services/modules/<nome>/`, implementar adapter que chama `engine_client.send_chat`.
2. **Nova fonte**: adicionar coletor em `services/modules/sources/main.py` e entrada em `config/sources.yaml`.
3. **Novo cliente**: editar `config/clients.yaml` (montado como volume no Docker).

## Persona

O engine usa prompt fixo em `services/engine/app/persona.py` exigindo tom polido, educado e solícito, sem inventar status operacionais.

## IA gratuita e remota

- **Padrão**: Ollama com `llama3.2:3b` (local, sem custo)
- **Remotos** (via `LLM_PROVIDER` no `.env`):
  - `gemini` — Google Gemini
  - `openai` — OpenAI API
  - `azure` — Azure OpenAI
  - `grok` — xAI Grok

Implementação em `services/engine/app/llm/providers.py`.

## Exemplo de fluxo

1. Usuário: "Bom dia, sou Rodrigo. Sou responsável técnico pelo IFS..."
2. Engine extrai nome e instituição, persiste em PostgreSQL
3. RAG busca manutenções em `manutencoes` e status em `operacional`
4. LLM gera resposta educada com base no contexto recuperado
