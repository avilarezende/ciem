"""Fachada unificada para geração de respostas via LLM."""

from app.llm.providers import get_provider

FALLBACK_MESSAGE = (
    "Peço desculpas, não foi possível gerar uma resposta no momento. "
    "Por favor, tente novamente ou contate o PoP-SE em info@pop-se.rnp.br."
)


async def generate_reply(system: str, user_message: str, context: str = "") -> str:
    prompt = user_message
    if context:
        prompt = f"Contexto recuperado das fontes:\n{context}\n\nPergunta do usuário:\n{user_message}"

    try:
        provider = get_provider()
        reply = await provider.generate(system, prompt)
        return reply.strip() or FALLBACK_MESSAGE
    except Exception as exc:
        print(f"[LLM] Erro no provedor: {exc}")
        return FALLBACK_MESSAGE
