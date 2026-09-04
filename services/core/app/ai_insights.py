"""Geração de insights de IA a partir de alarmes e logs agregados do CIEM."""

from __future__ import annotations

import json
import logging
import time
from datetime import UTC, datetime
from typing import Any

import httpx

from ciem_common.config_loader import AiConfig, load_ai_config

from .aggregators import aggregate_alarms, aggregate_history

logger = logging.getLogger(__name__)

_CACHE: dict[str, Any] = {
    "generated_at": None,
    "expires_at": 0.0,
    "payload": None,
}


def clear_insights_cache() -> None:
    """Limpa o cache em memória de insights."""
    _CACHE["generated_at"] = None
    _CACHE["expires_at"] = 0.0
    _CACHE["payload"] = None


def _disabled_payload(reason: str = "Insights de IA desabilitados.") -> dict[str, Any]:
    return {
        "enabled": False,
        "status": "disabled",
        "message": reason,
        "summary": "",
        "insights": [],
        "charts": [],
        "provider": None,
        "model": None,
        "generated_at": None,
        "source_counts": {"alarms": 0, "history": 0},
    }


def _heuristic_insights(
    alarms: list[dict[str, Any]], history: list[dict[str, Any]]
) -> dict[str, Any]:
    """Gera insights locais sem chamar LLM (fallback / sem API key)."""
    by_sev: dict[str, int] = {}
    by_source: dict[str, int] = {}
    for alarm in alarms:
        sev = str(alarm.get("severity") or "info").lower()
        by_sev[sev] = by_sev.get(sev, 0) + 1
        src = str(alarm.get("source_module") or alarm.get("source") or "desconhecido")
        by_source[src] = by_source.get(src, 0) + 1

    insights: list[dict[str, Any]] = []
    critical = by_sev.get("critical", 0) + by_sev.get("high", 0)
    if critical:
        insights.append(
            {
                "title": "Concentração de severidade alta",
                "severity": "critical" if by_sev.get("critical") else "high",
                "detail": (
                    f"{critical} alarme(s) crítico(s)/alto(s) ativos "
                    "exigem atenção imediata."
                ),
                "recommendation": (
                    "Priorize os alarmes críticos no painel e abra "
                    "sessões de manutenção nos alvos afetados."
                ),
            }
        )
    if by_source:
        top_src, top_n = max(by_source.items(), key=lambda item: item[1])
        insights.append(
            {
                "title": f"Fonte dominante: {top_src}",
                "severity": "warning" if top_n >= 3 else "info",
                "detail": f"{top_n} alarme(s) originados em «{top_src}».",
                "recommendation": "Revise filtros e saúde do coletor correspondente.",
            }
        )
    if history:
        insights.append(
            {
                "title": "Atividade recente no histórico",
                "severity": "info",
                "detail": f"{len(history)} evento(s) recentes agregados dos módulos.",
                "recommendation": (
                    "Correlacione picos de histórico com mudanças de "
                    "configuração ou janelas de manutenção."
                ),
            }
        )
    if not insights:
        insights.append(
            {
                "title": "Ambiente estável",
                "severity": "info",
                "detail": "Nenhum alarme ativo nem padrão relevante identificado nos dados atuais.",
                "recommendation": (
                    "Mantenha o monitoramento; ative um provedor LLM "
                    "para análises narrativas mais ricas."
                ),
            }
        )

    charts = [
        {
            "id": "severity_distribution",
            "title": "Distribuição por severidade",
            "type": "pie",
            "labels": list(by_sev.keys()) or ["none"],
            "values": list(by_sev.values()) or [0],
        },
        {
            "id": "source_distribution",
            "title": "Alarmes por fonte",
            "type": "bar",
            "labels": list(by_source.keys()) or ["none"],
            "values": list(by_source.values()) or [0],
        },
    ]

    summary = (
        f"Análise heurística: {len(alarms)} alarme(s) ativo(s), "
        f"{len(history)} evento(s) no histórico. "
        f"{'Há severidades elevadas.' if critical else 'Sem concentração crítica.'}"
    )
    return {
        "summary": summary,
        "insights": insights,
        "charts": charts,
        "mode": "heuristic",
    }


def _build_prompt(
    cfg: AiConfig, alarms: list[dict[str, Any]], history: list[dict[str, Any]]
) -> list[dict[str, str]]:
    system = cfg.system_prompt.strip() or (
        "Você é um analista NOC do CIEM (Centro Integrado de Estatística e Manutenção). "
        "Analise alarmes e eventos de log agregados e produza insights acionáveis. "
        f"Responda em {cfg.language}. "
        "Retorne APENAS JSON válido com as chaves: "
        "summary (string), "
        "insights (lista de objetos com title, severity, detail, recommendation), "
        "charts (lista de objetos com id, title, type [pie|bar], labels[], values[])."
    )
    payload = {
        "alarms": alarms[: cfg.max_alarms],
        "history": history[: cfg.max_history],
        "counts": {"alarms": len(alarms), "history": len(history)},
    }
    user = (
        "Dados atuais do CIEM (JSON):\n"
        f"{json.dumps(payload, ensure_ascii=False, default=str)}\n\n"
        "Identifique padrões relevantes, possíveis causas e recomendações operacionais."
    )
    return [
        {"role": "system", "content": system},
        {"role": "user", "content": user},
    ]


def _extract_json(text: str) -> dict[str, Any]:
    text = text.strip()
    if text.startswith("```"):
        lines = text.splitlines()
        if lines and lines[0].startswith("```"):
            lines = lines[1:]
        if lines and lines[-1].strip().startswith("```"):
            lines = lines[:-1]
        text = "\n".join(lines).strip()
    try:
        data = json.loads(text)
        if isinstance(data, dict):
            return data
    except json.JSONDecodeError:
        pass
    start = text.find("{")
    end = text.rfind("}")
    if start >= 0 and end > start:
        data = json.loads(text[start : end + 1])
        if isinstance(data, dict):
            return data
    raise ValueError("Resposta do modelo não contém JSON válido")


async def _call_llm(cfg: AiConfig, messages: list[dict[str, str]]) -> dict[str, Any]:
    base = cfg.base_url.rstrip("/")
    path = cfg.chat_path if cfg.chat_path.startswith("/") else f"/{cfg.chat_path}"
    url = f"{base}{path}"
    headers = {
        "Content-Type": "application/json",
        cfg.auth_header: f"{cfg.auth_scheme} {cfg.api_key}".strip()
        if cfg.auth_scheme
        else cfg.api_key,
    }
    if cfg.organization:
        headers["OpenAI-Organization"] = cfg.organization

    body = {
        "model": cfg.model,
        "temperature": cfg.temperature,
        "max_tokens": cfg.max_tokens,
        "messages": messages,
        "response_format": {"type": "json_object"},
    }

    async with httpx.AsyncClient(timeout=cfg.timeout_seconds, verify=cfg.verify_ssl) as client:
        resp = await client.post(url, headers=headers, json=body)
        resp.raise_for_status()
        data = resp.json()

    # OpenAI-compatible
    choices = data.get("choices") or []
    if choices:
        content = choices[0].get("message", {}).get("content") or ""
        return _extract_json(content)
    # Alguns provedores retornam content na raiz
    if isinstance(data.get("content"), str):
        return _extract_json(data["content"])
    raise ValueError("Formato de resposta do provedor não suportado")


def _normalize_model_result(raw: dict[str, Any], fallback: dict[str, Any]) -> dict[str, Any]:
    insights = raw.get("insights")
    if not isinstance(insights, list):
        insights = fallback["insights"]
    charts = raw.get("charts")
    if not isinstance(charts, list) or not charts:
        charts = fallback["charts"]
    summary = str(raw.get("summary") or fallback["summary"])
    clean_insights = []
    for item in insights[:12]:
        if not isinstance(item, dict):
            continue
        clean_insights.append(
            {
                "title": str(item.get("title") or "Insight"),
                "severity": str(item.get("severity") or "info").lower(),
                "detail": str(item.get("detail") or item.get("description") or ""),
                "recommendation": str(item.get("recommendation") or ""),
            }
        )
    clean_charts = []
    for chart in charts[:6]:
        if not isinstance(chart, dict):
            continue
        labels = chart.get("labels") if isinstance(chart.get("labels"), list) else []
        values = chart.get("values") if isinstance(chart.get("values"), list) else []
        clean_charts.append(
            {
                "id": str(chart.get("id") or "chart"),
                "title": str(chart.get("title") or "Gráfico"),
                "type": str(chart.get("type") or "bar"),
                "labels": [str(x) for x in labels],
                "values": [float(x) if isinstance(x, int | float) else 0 for x in values],
            }
        )
    return {
        "summary": summary,
        "insights": clean_insights or fallback["insights"],
        "charts": clean_charts or fallback["charts"],
        "mode": "llm",
    }


async def generate_insights(*, force: bool = False) -> dict[str, Any]:
    """Gera ou devolve do cache o pacote de insights."""
    cfg = load_ai_config()
    if not cfg.enabled:
        return _disabled_payload()

    now = time.time()
    if not force and _CACHE["payload"] is not None and now < float(_CACHE["expires_at"]):
        cached = dict(_CACHE["payload"])
        cached["cached"] = True
        return cached

    async with httpx.AsyncClient(timeout=60.0) as client:
        alarms = await aggregate_alarms(client)
        history = await aggregate_history(client)

    heuristic = _heuristic_insights(alarms, history)
    mode = "heuristic"
    analysis = heuristic

    if cfg.api_key.strip() and cfg.base_url.strip() and cfg.model.strip():
        try:
            messages = _build_prompt(cfg, alarms, history)
            raw = await _call_llm(cfg, messages)
            analysis = _normalize_model_result(raw, heuristic)
            mode = "llm"
        except Exception as exc:  # noqa: BLE001 — fallback operacional
            logger.warning("Falha ao consultar provedor de IA (%s); usando heurística.", exc)
            analysis = heuristic
            mode = "heuristic_fallback"
            analysis = {**heuristic, "mode": mode, "error": str(exc)}

    generated_at = datetime.now(UTC).isoformat()
    payload = {
        "enabled": True,
        "status": "ok",
        "message": "Insights disponíveis.",
        "summary": analysis["summary"],
        "insights": analysis["insights"],
        "charts": analysis["charts"],
        "provider": cfg.provider,
        "model": cfg.model if mode.startswith("llm") else None,
        "mode": analysis.get("mode", mode),
        "generated_at": generated_at,
        "source_counts": {"alarms": len(alarms), "history": len(history)},
        "cached": False,
        "error": analysis.get("error"),
    }
    _CACHE["payload"] = payload
    _CACHE["generated_at"] = generated_at
    _CACHE["expires_at"] = now + max(30, cfg.refresh_interval_seconds)
    return payload


async def get_insights_public(*, force: bool = False) -> dict[str, Any]:
    """Versão pública (sem api_key) para portal/Grafana."""
    return await generate_insights(force=force)
