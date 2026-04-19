import json
import logging

from openai import AsyncOpenAI

from app.core.config import settings

from .schemas import ClassificationResult

logger = logging.getLogger(__name__)


class AIClient:
    def __init__(self, api_key: str | None = None, model: str | None = None):
        resolved_api_key = api_key or settings.OPENROUTER_API_KEY
        # Fail fast with a clear error if the API key is not configured properly.
        if (
            not resolved_api_key
            or not str(resolved_api_key).strip()
            or "your_openrouter_api_key" in str(resolved_api_key).lower()
            or "changeme" in str(resolved_api_key).lower()
            or "not set" in str(resolved_api_key).lower()
        ):
            raise RuntimeError(
                "OPENROUTER_API_KEY is not configured. Set a valid key in "
                "settings.OPENROUTER_API_KEY or pass api_key to AIClient."
            )
        self._client = AsyncOpenAI(
            api_key=resolved_api_key,
            base_url="https://openrouter.ai/api/v1",
        )
        self._model = model or settings.AI_MODEL

    async def generate_summaries(
        self,
        system_prompt: str,
        user_prompt: str,
        model: str | None = None,
        temperature: float = 0.3,
        max_retries: int = 2,
    ) -> dict | None:
        """Generate patient-friendly summary fields via LLM.

        Returns a dict of custom_* field values on success, or None on failure.
        Callers (ai_generate_summaries) treat None as a fail-safe and set all
        custom_* fields to None so the admin can fill them in manually.
        """
        last_error: Exception | None = None

        for attempt in range(1 + max_retries):
            try:
                response = await self._client.chat.completions.create(
                    model=model or self._model,
                    temperature=temperature,
                    response_format={"type": "json_object"},
                    messages=[
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": user_prompt},
                    ],
                )
                raw = response.choices[0].message.content
                return json.loads(raw)
            except Exception as e:
                last_error = e
                logger.warning(
                    "generate_summaries attempt %d failed: %s", attempt + 1, e
                )

        logger.error(
            "generate_summaries failed after %d attempts: %s", 1 + max_retries, last_error
        )
        return None

    async def classify_trial(
        self,
        system_prompt: str,
        user_prompt: str,
        model: str | None = None,
        temperature: float = 0.1,
        max_retries: int = 2,
    ) -> ClassificationResult:
        """Classify a trial via LLM. Returns a safe default on failure (never loses a trial)."""
        last_error: Exception | None = None

        for attempt in range(1 + max_retries):
            try:
                response = await self._client.chat.completions.create(
                    model=model or self._model,
                    temperature=temperature,
                    response_format={"type": "json_object"},
                    messages=[
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": user_prompt},
                    ],
                )
                raw = response.choices[0].message.content
                data = json.loads(raw)
                return ClassificationResult(**data)
            except Exception as e:
                last_error = e
                logger.warning(
                    "classify_trial attempt %d failed: %s", attempt + 1, e
                )

        # Never lose a trial — default to relevant
        logger.error(
            "classify_trial failed after %d attempts: %s", 1 + max_retries, last_error
        )
        return ClassificationResult(
            is_relevant=True,
            confidence=0.0,
            reason="AI evaluation failed -- needs manual review",
            relevance_tier="secondary",
            matching_criteria=["none"],
        )
