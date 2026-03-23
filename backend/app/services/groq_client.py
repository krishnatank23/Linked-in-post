import json
import logging
from typing import Any

import httpx

from app.core.config import get_settings
from app.utils.retry import retry_on_exception

logger = logging.getLogger(__name__)


class GroqClient:
    def __init__(self) -> None:
        settings = get_settings()
        self._model = settings.groq_model
        self._timeout = settings.groq_timeout_seconds
        self._api_key = settings.groq_api_key
        self._base_url = "https://api.groq.com/openai/v1/chat/completions"

    @retry_on_exception(attempts=3, exception_type=httpx.HTTPError)
    def complete(self, system_prompt: str, user_prompt: str, temperature: float = 0.2) -> str:
        if not self._api_key:
            raise ValueError("GROQ_API_KEY is missing. Set it in backend/.env before running AI analysis.")

        payload = {
            "model": self._model,
            "temperature": temperature,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
        }
        headers = {
            "Authorization": f"Bearer {self._api_key}",
            "Content-Type": "application/json",
        }

        with httpx.Client(timeout=self._timeout) as client:
            response = client.post(self._base_url, headers=headers, json=payload)
            response.raise_for_status()
            data = response.json()

        try:
            return data["choices"][0]["message"]["content"]
        except (KeyError, IndexError, TypeError) as exc:
            logger.exception("Unexpected Groq response shape")
            raise ValueError("Invalid response from Groq API") from exc

    def complete_json(
        self,
        system_prompt: str,
        user_prompt: str,
        fallback: dict[str, Any] | list[Any],
    ) -> Any:
        try:
            completion = self.complete(system_prompt=system_prompt, user_prompt=user_prompt)
        except Exception:
            logger.warning("LLM request failed; returning fallback JSON payload", exc_info=True)
            return fallback
        cleaned = completion.strip()

        if "```" in cleaned:
            cleaned = cleaned.replace("```json", "").replace("```", "").strip()

        try:
            return json.loads(cleaned)
        except json.JSONDecodeError:
            logger.warning("LLM output was not valid JSON; returning fallback")
            return fallback
