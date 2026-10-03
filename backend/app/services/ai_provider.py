"""Provider-agnostic LLM client: Groq (primary native tool calling), Ollama (/api/chat), and grounded fallback."""

import json
import logging
import re
import time
from typing import Any

import httpx
from pydantic import BaseModel, Field

from app.config import get_settings

log = logging.getLogger(__name__)


class ToolCall(BaseModel):
    id: str = ""
    name: str
    args: dict[str, Any] = Field(default_factory=dict)


class AIProvider:
    def __init__(self):
        self.settings = get_settings()

    def get_active_provider_name(self) -> str:
        if self.settings.groq_api_key and self.settings.llm_provider in {"groq", "auto"}:
            return "groq"
        if self.settings.openai_api_key and self.settings.llm_provider in {"openai", "auto"}:
            return "openai"
        if self.settings.ollama_enabled:
            return "ollama"
        return "grounded_rules"

    # --- Groq / OpenAI-compatible API ---

    def _call_groq_or_openai(
        self,
        messages: list[dict[str, Any]],
        tools: list[dict[str, Any]] | None = None,
        model: str | None = None,
    ) -> dict[str, Any]:
        settings = self.settings
        is_groq = bool(settings.groq_api_key)

        base_url = "https://api.groq.com/openai/v1" if is_groq else settings.openai_base_url
        api_key = settings.groq_api_key if is_groq else settings.openai_api_key
        target_model = model or (settings.groq_model if is_groq else settings.openai_model)

        url = f"{base_url.rstrip('/')}/chat/completions"
        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        }

        payload: dict[str, Any] = {
            "model": target_model,
            "messages": messages,
            "temperature": 0.2,
            "stream": False,
        }
        if tools:
            payload["tools"] = tools
            payload["tool_choice"] = "auto"

        with httpx.Client(timeout=30.0) as client:
            resp = client.post(url, headers=headers, json=payload)
            if resp.status_code == 404 and is_groq:
                # If target model 404s, try fallback fast model or gpt-oss-20b
                fallback_model = settings.groq_fast_model or "openai/gpt-oss-20b"
                if target_model != fallback_model:
                    log.warning("Groq model %s 404'd, retrying with %s", target_model, fallback_model)
                    payload["model"] = fallback_model
                    resp = client.post(url, headers=headers, json=payload)
            resp.raise_for_status()
            data = resp.json()
            choice = data.get("choices", [{}])[0]
            message = choice.get("message", {})

            content = message.get("content", "") or ""
            raw_tool_calls = message.get("tool_calls", [])
            tool_calls = []
            for tc in raw_tool_calls:
                fn = tc.get("function", {})
                try:
                    args = json.loads(fn.get("arguments", "{}"))
                except Exception:
                    args = {}
                tool_calls.append({
                    "id": tc.get("id", f"call_{int(time.time()*1000)}"),
                    "name": fn.get("name", ""),
                    "args": args,
                })

            return {
                "content": content,
                "tool_calls": tool_calls,
                "raw_tool_calls": raw_tool_calls,
                "provider": "groq" if is_groq else "openai",
            }

    # --- Ollama /api/chat Fallback ---

    def _call_ollama_chat(
        self,
        messages: list[dict[str, Any]],
        temperature: float = 0.2,
    ) -> str:
        """Call local Ollama using /api/chat with a messages array (NOT /api/generate text blob)."""
        url = f"{self.settings.ollama_url.rstrip('/')}/api/chat"
        # Sanitize messages for Ollama /api/chat (only role and content accepted)
        chat_messages = []
        for m in messages:
            chat_messages.append({
                "role": m.get("role", "user"),
                "content": str(m.get("content", "") or ""),
            })

        payload = {
            "model": self.settings.ollama_model,
            "messages": chat_messages,
            "stream": False,
            "options": {
                "temperature": temperature,
            },
        }
        with httpx.Client(timeout=30.0) as client:
            resp = client.post(url, json=payload)
            resp.raise_for_status()
            data = resp.json()
            return data.get("message", {}).get("content", "")

    # --- Universal Dispatcher ---

    def chat_step(
        self,
        messages: list[dict[str, Any]],
        tools: list[dict[str, Any]] | None = None,
    ) -> dict[str, Any]:
        """Execute one turn of conversation with tool call support and graceful fallback."""
        start_time = time.perf_counter()

        # 1. Try Groq or OpenAI
        if self.settings.groq_api_key or self.settings.openai_api_key:
            try:
                res = self._call_groq_or_openai(messages, tools)
                res["latency_ms"] = round((time.perf_counter() - start_time) * 1000, 2)
                return res
            except Exception as err:
                log.warning(
                    "Primary LLM (%s) failed: %s; trying Ollama fallback",
                    "groq" if self.settings.groq_api_key else "openai",
                    err,
                )

        # 2. Try Ollama local
        if self.settings.ollama_enabled:
            try:
                content = self._call_ollama_chat(messages)
                return {
                    "content": content,
                    "tool_calls": [],
                    "provider": "ollama",
                    "latency_ms": round((time.perf_counter() - start_time) * 1000, 2),
                }
            except Exception as err:
                log.warning("Ollama fallback failed: %s; using grounded rules", err)

        # 3. Grounded rules fallback
        last_msg = ""
        for m in reversed(messages):
            if m.get("role") == "user":
                last_msg = m.get("content", "")
                break
        fallback_text = self._grounded_fallback(last_msg, "")
        return {
            "content": fallback_text,
            "tool_calls": [],
            "provider": "grounded_rules",
            "latency_ms": round((time.perf_counter() - start_time) * 1000, 2),
        }

    def generate(self, prompt: str, system: str = "") -> dict[str, Any]:
        """Generate text synchronously with token and latency tracking."""
        start_time = time.perf_counter()
        messages = []
        if system:
            messages.append({"role": "system", "content": system})
        messages.append({"role": "user", "content": prompt})

        step = self.chat_step(messages, tools=None)
        latency_ms = round((time.perf_counter() - start_time) * 1000, 2)
        text_out = step.get("content", "")
        tokens_est = max(1, len(text_out.split()) + len(prompt.split()))

        return {
            "text": text_out,
            "provider": step.get("provider", "grounded_rules"),
            "tokens_used": tokens_est,
            "latency_ms": latency_ms,
        }

    def _grounded_fallback(self, prompt: str, system: str) -> str:
        """Deterministic grounded response generator when external LLMs are unreachable."""
        clean = prompt.casefold()

        if "cover letter" in clean:
            return (
                "Dear Hiring Team,\n\n"
                "I am writing to express my strong interest in this position. Based on my technical background "
                "and hands-on software development experience, I am confident in my ability to contribute "
                "meaningfully to your team.\n\n"
                "My experience directly aligns with the core requirements of the role. I have developed practical "
                "proficiency across core engineering fundamentals, collaborative version control, and scalable "
                "system design. I thrive in problem-solving environments where code quality, observability, and "
                "delivering dependable value are prioritized.\n\n"
                "I look forward to discussing how my skills and engineering discipline align with your company's mission.\n\n"
                "Sincerely,\nCandidate"
            )

        if "why this match" in clean or "match analysis" in clean:
            return (
                "### Match Analysis\n\n"
                "- **Strong Skill Alignment**: Your verified profile matches the critical competencies requested for this role.\n"
                "- **Experience Relevance**: Your documented experience level meets the role's baseline expectations.\n"
                "- **Actionable Growth**: Reviewing the remaining optional or emerging skills will further strengthen your application.\n"
            )

        return (
            "I'm your SkillMatch Career Assistant. I can help you search for jobs, analyze match breakdowns, "
            "track applications on your Kanban board, and identify curated learning resources to close skill gaps. "
            "How can I assist your job search today?"
        )


_provider_instance: AIProvider | None = None


def get_ai_provider() -> AIProvider:
    global _provider_instance
    if _provider_instance is None:
        _provider_instance = AIProvider()
    return _provider_instance
