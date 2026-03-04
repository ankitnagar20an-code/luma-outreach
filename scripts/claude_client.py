"""Groq API wrapper for AI content generation (Llama 3.3 70B)."""

from __future__ import annotations

import json
import logging
import os
from pathlib import Path
from typing import Any

import httpx

logger = logging.getLogger(__name__)

PROMPTS_DIR = Path(__file__).parent.parent / "prompts"


def _load_prompt(name: str) -> str:
    path = PROMPTS_DIR / f"{name}.md"
    if not path.exists():
        raise FileNotFoundError(f"Prompt file not found: {path}")
    return path.read_text(encoding="utf-8")


def _load_rules() -> str:
    return _load_prompt("rules")


class ClaudeClient:
    """Generate content using Groq API (Llama 3.3 70B). Class name kept for compatibility."""

    def __init__(self, model: str = "llama-3.3-70b-versatile"):
        self.model = model
        self.api_key = os.environ.get("GROQ_API_KEY", "")
        if not self.api_key:
            logger.warning("GROQ_API_KEY not set — AI generation will fail")

    def _call_llm(self, prompt: str) -> dict[str, Any]:
        if not self.api_key:
            return {"error": "GROQ_API_KEY not set", "confidence_score": 0.0}

        try:
            resp = httpx.post(
                "https://api.groq.com/openai/v1/chat/completions",
                headers={
                    "Authorization": f"Bearer {self.api_key}",
                    "Content-Type": "application/json",
                },
                json={
                    "model": self.model,
                    "messages": [
                        {"role": "system", "content": "You are a professional outreach assistant. Always respond with ONLY valid JSON as specified. No markdown fences, no extra text."},
                        {"role": "user", "content": prompt},
                    ],
                    "temperature": 0.7,
                    "max_tokens": 2000,
                },
                timeout=120,
            )
            resp.raise_for_status()
        except httpx.TimeoutException:
            logger.error("Groq API timed out after 120s")
            return {"error": "timeout", "confidence_score": 0.0}
        except httpx.HTTPStatusError as e:
            logger.error("Groq API error (%d): %s", e.response.status_code, e.response.text[:500])
            return {"error": str(e), "confidence_score": 0.0}

        data = resp.json()
        text = data["choices"][0]["message"]["content"].strip()

        # Strip markdown fences if present
        if text.startswith("```json"):
            text = text[7:]
        if text.startswith("```"):
            text = text[3:]
        if text.endswith("```"):
            text = text[:-3]
        text = text.strip()

        try:
            return json.loads(text)
        except json.JSONDecodeError:
            logger.error("Failed to parse LLM output as JSON: %s", text[:300])
            return {"error": "invalid_json", "raw": text[:500], "confidence_score": 0.0}

    def _build_prompt(self, template_name: str, variables: dict[str, str]) -> str:
        rules = _load_rules()
        template = _load_prompt(template_name)
        var_block = "\n".join(f"**{k}**: {v}" for k, v in variables.items())

        return f"""<rules>
{rules}
</rules>

<instructions>
{template}
</instructions>

<input>
{var_block}
</input>

Respond with ONLY the JSON object as specified in the output schema. No other text."""

    def generate_post(self, topic: str, research: str) -> dict[str, Any]:
        prompt = self._build_prompt("post", {"topic": topic, "research": research})
        return self._call_llm(prompt)

    def generate_comment(self, post_url: str, post_content: str, topic: str, research: str) -> dict[str, Any]:
        prompt = self._build_prompt("comment", {
            "post_url": post_url, "post_content": post_content,
            "topic": topic, "research": research,
        })
        return self._call_llm(prompt)

    def generate_reply(self, sender_name: str, sender_url: str, message_text: str, research: str) -> dict[str, Any]:
        prompt = self._build_prompt("reply", {
            "sender_name": sender_name, "sender_url": sender_url,
            "message_text": message_text, "research": research,
        })
        return self._call_llm(prompt)

    def generate_connection_note(self, prospect_name: str, company: str, title: str, research: str) -> dict[str, Any]:
        prompt = self._build_prompt("connection", {
            "prospect_name": prospect_name, "company": company,
            "title": title, "research": research,
        })
        return self._call_llm(prompt)

    def generate_inmail(self, prospect_name: str, company: str, title: str, research: str) -> dict[str, Any]:
        prompt = self._build_prompt("inmail", {
            "prospect_name": prospect_name, "company": company,
            "title": title, "research": research,
        })
        return self._call_llm(prompt)

    def generate_dm(self, prospect_name: str, company: str, title: str, research: str, previous_interaction: str) -> dict[str, Any]:
        prompt = self._build_prompt("dm", {
            "prospect_name": prospect_name, "company": company,
            "title": title, "research": research,
            "previous_interaction": previous_interaction,
        })
        return self._call_llm(prompt)

    def generate_email(self, prospect_name: str, company: str, title: str, email: str, research: str) -> dict[str, Any]:
        prompt = self._build_prompt("email", {
            "prospect_name": prospect_name, "company": company,
            "title": title, "email": email, "research": research,
        })
        return self._call_llm(prompt)

    def synthesize_research(self, prospect_name: str, company: str, title: str, search_results: str) -> dict[str, Any]:
        prompt = self._build_prompt("research", {
            "prospect_name": prospect_name, "company": company,
            "title": title, "search_results": search_results,
        })
        return self._call_llm(prompt)
