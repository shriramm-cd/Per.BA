import asyncio
import json
import os
import re
import time
from typing import Dict, Any, Optional

try:
    import google.generativeai as genai
    from google.generativeai.types import GenerationConfig
except Exception:  # pragma: no cover - fallback for environments without the deprecated package
    genai = None
    GenerationConfig = None
from groq import AsyncGroq

from backend.config import settings
from backend.shared.logger import get_logger

logger = get_logger(__name__)


class LLMClient:
    """
    Unified LLM Client providing JSON structured output capability.
    Uses Groq as the primary provider and Gemini as the fallback provider.
    """
    _groq_blocked = False
    _gemini_blocked_models = set()

    def __init__(self):
        self.groq_primary_key = settings.GROQ_API_KEY_PRIMARY or settings.GROQ_API_KEY
        self.groq_fallback_key = settings.GROQ_API_KEY_FALLBACK
        self.gemini_primary_key = (
            settings.GEMINI_API_KEY_PRIMARY
            or settings.GEMINI_API_KEY
            or os.getenv("GOOGLE_API_KEY")
            or os.getenv("GEMINI_API_KEY")
        )
        self.gemini_fallback_key = settings.GEMINI_API_KEY_FALLBACK or os.getenv("GOOGLE_API_KEY_FALLBACK")
        self.model_name = None
        self.last_provider = None

        self.groq_keys = [key for key in [self.groq_primary_key, self.groq_fallback_key] if key]
        self.gemini_keys = [key for key in [self.gemini_primary_key, self.gemini_fallback_key] if key]
        self.gemini_model = None

    @staticmethod
    def _mask_secret(value: Optional[str]) -> str:
        if not value:
            return "<missing>"
        if len(value) <= 8:
            return "*" * len(value)
        return f"{value[:4]}...{value[-4:]}"

    async def validate_provider_keys(self) -> Dict[str, Any]:
        status: Dict[str, Any] = {"providers": {}}
        if self.groq_primary_key:
            status["providers"]["groq_primary"] = {"active": True, "masked_key": self._mask_secret(self.groq_primary_key)}
        if self.groq_fallback_key:
            status["providers"]["groq_fallback"] = {"active": True, "masked_key": self._mask_secret(self.groq_fallback_key)}
        if self.gemini_primary_key:
            status["providers"]["gemini_primary"] = {"active": True, "masked_key": self._mask_secret(self.gemini_primary_key)}
        if self.gemini_fallback_key:
            status["providers"]["gemini_fallback"] = {"active": True, "masked_key": self._mask_secret(self.gemini_fallback_key)}
        return status

    @staticmethod
    def _estimate_tokens(text: str) -> int:
        return max(1, int(len(text.split()) * 1.3))

    @classmethod
    def _extract_json_candidate(cls, content: Any) -> str:
        if content is None:
            raise ValueError("LLM returned no content")

        text = str(content).strip()
        if not text:
            raise ValueError("LLM returned an empty response")

        try:
            json.loads(text)
            return text
        except json.JSONDecodeError:
            pass

        fenced = re.sub(r"^```(?:json)?\s*", "", text, flags=re.IGNORECASE)
        fenced = re.sub(r"\s*```$", "", fenced, flags=re.IGNORECASE).strip()
        if fenced:
            try:
                json.loads(fenced)
                return fenced
            except json.JSONDecodeError:
                pass

        for start_char, end_char in (("{", "}"), ("[", "]")):
            start_index = fenced.find(start_char)
            if start_index == -1:
                continue
            depth = 0
            in_string = False
            escaped = False
            for idx in range(start_index, len(fenced)):
                char = fenced[idx]
                if in_string:
                    if escaped:
                        escaped = False
                    elif char == "\\":
                        escaped = True
                    elif char == '"':
                        in_string = False
                    continue

                if char == '"':
                    in_string = True
                elif char == start_char:
                    depth += 1
                elif char == end_char:
                    depth -= 1
                    if depth == 0:
                        candidate = fenced[start_index:idx + 1].strip()
                        try:
                            json.loads(candidate)
                            return candidate
                        except json.JSONDecodeError:
                            break

        raise ValueError("LLM returned content that was not parseable as JSON")

    async def validate_provider_keys(self) -> Dict[str, Any]:
        status: Dict[str, Any] = {"groq": {}, "gemini": {}}

        for provider_name, keys, model_name in [
            ("groq", self.groq_keys, "llama-3.3-70b-versatile"),
            ("gemini", self.gemini_keys, "gemini-2.0-flash"),
        ]:
            for key in keys:
                masked_key = self._mask_secret(key)
                try:
                    if provider_name == "groq":
                        client = AsyncGroq(api_key=key, max_retries=0)
                        await client.chat.completions.create(
                            model=model_name,
                            messages=[{"role": "user", "content": "ping"}],
                            temperature=0.0,
                            timeout=20.0,
                        )
                    else:
                        if genai is None or GenerationConfig is None:
                            raise RuntimeError("google-generativeai is not available")
                        genai.configure(api_key=key)
                        model_instance = genai.GenerativeModel(model_name)
                        await model_instance.generate_content_async(
                            contents="Reply with OK",
                            generation_config=GenerationConfig(response_mime_type="text/plain", temperature=0.0),
                        )
                    status[provider_name][masked_key] = {"active": True}
                    logger.info("Startup validation succeeded provider=%s key=%s", provider_name, masked_key)
                except Exception as exc:
                    status[provider_name][masked_key] = {"active": False, "reason": str(exc)}
                    logger.warning("Startup validation failed provider=%s key=%s reason=%s", provider_name, masked_key, exc)

        return status

    async def generate_json(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        groq_model: str = "llama-3.3-70b-versatile"
    ) -> Dict[str, Any]:
        """
        Submits prompt to Groq first and falls back to Gemini.
        Ensures output is JSON-compliant.
        """
        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": prompt})

        prompt_chars = len(prompt)
        system_chars = len(system_prompt or "")
        logger.info(
            "LLM request started provider=auto prompt_chars=%s system_chars=%s prompt_tokens_est=%s",
            prompt_chars,
            system_chars,
            self._estimate_tokens(prompt + (system_prompt or "")),
        )

        logger.debug(f"Submitting prompt:\n{prompt}")

        logger.info(
            "LLM request provider=auto groq_primary_key=%s groq_fallback_key=%s gemini_primary_key=%s gemini_fallback_key=%s",
            self._mask_secret(self.groq_primary_key),
            self._mask_secret(self.groq_fallback_key),
            self._mask_secret(self.gemini_primary_key),
            self._mask_secret(self.gemini_fallback_key),
        )

        groq_error = None
        if self.groq_keys and not LLMClient._groq_blocked:
            models_to_try = [groq_model, "llama-3.1-8b-instant", "llama-3.2-3b-preview"]
            for model in models_to_try:
                for key in self.groq_keys:
                    started_at = time.perf_counter()
                    try:
                        logger.info(
                            "Submitting LLM request provider=groq model=%s key=%s",
                            model,
                            self._mask_secret(key),
                        )
                        client = AsyncGroq(api_key=key, max_retries=0)
                        response = await client.chat.completions.create(
                            model=model,
                            messages=messages,
                            response_format={"type": "json_object"},
                            temperature=0.2,
                            timeout=120.0,
                        )
                        raw_content = response.choices[0].message.content
                        elapsed = time.perf_counter() - started_at
                        logger.info("Groq response received model=%s elapsed_seconds=%.2f", model, elapsed)
                        logger.info("Raw Groq Response (%s):\n%s", model, raw_content)

                        cleaned = self._extract_json_candidate(raw_content)
                        parsed = json.loads(cleaned)
                        self.model_name = model
                        self.last_provider = "groq"
                        logger.info("Groq structured JSON parsed successfully model=%s", model)
                        return parsed
                    except json.JSONDecodeError as je:
                        groq_error = je
                        logger.error(
                            "Groq JSON parsing failed for model %s with key %s. Error: %s\nRaw response content:\n%s",
                            model,
                            self._mask_secret(key),
                            str(je),
                            raw_content if "raw_content" in locals() else "<no response>",
                        )
                        break
                    except Exception as e:
                        groq_error = e
                        error_msg = str(e).lower()
                        if "429" in error_msg or "rate limit" in error_msg or "tpm" in error_msg or "limit exceeded" in error_msg:
                            logger.warning(
                                "Groq rate limit hit provider=groq model=%s key=%s reason=%s",
                                model,
                                self._mask_secret(key),
                                str(e),
                            )
                            continue
                        if "auth" in error_msg or "unauthorized" in error_msg or "forbidden" in error_msg:
                            logger.warning(
                                "Groq authentication failed provider=groq model=%s key=%s reason=%s",
                                model,
                                self._mask_secret(key),
                                str(e),
                            )
                            continue
                        logger.warning(
                            "Groq invocation failed provider=groq model=%s key=%s reason=%s",
                            model,
                            self._mask_secret(key),
                            str(e),
                        )
                        continue
                if LLMClient._groq_blocked:
                    break
            if not LLMClient._groq_blocked:
                logger.warning("All Groq providers failed. Falling back to Gemini.")
        elif LLMClient._groq_blocked:
            logger.info("Groq is currently blocked. Bypassing straight to Gemini.")
        else:
            logger.info("Groq client not available. Bypassing to Gemini.")

        if self.gemini_keys:
            gemini_error = None
            for g_model in ["gemini-2.5-flash", "gemini-2.0-flash", "gemini-1.5-flash"]:
                if g_model in LLMClient._gemini_blocked_models:
                    continue
                for key in self.gemini_keys:
                    try:
                        logger.info(
                            "Submitting LLM request provider=gemini model=%s key=%s",
                            g_model,
                            self._mask_secret(key),
                        )
                        if genai is None or GenerationConfig is None:
                            raise RuntimeError("google-generativeai is not available")
                        genai.configure(api_key=key)
                        model_instance = genai.GenerativeModel(g_model)
                        full_prompt = prompt
                        if system_prompt:
                            full_prompt = f"System Context:\n{system_prompt}\n\nUser Request:\n{prompt}"

                        response = await model_instance.generate_content_async(
                            contents=full_prompt,
                            generation_config=GenerationConfig(response_mime_type="application/json", temperature=0.2),
                        )
                        raw_text = response.text
                        logger.info("Raw Gemini Response (%s):\n%s", g_model, raw_text)

                        cleaned = self._extract_json_candidate(raw_text)
                        parsed = json.loads(cleaned)
                        self.model_name = g_model
                        self.last_provider = "gemini"
                        logger.info("Gemini structured JSON parsed successfully model=%s", g_model)
                        return parsed
                    except json.JSONDecodeError as je:
                        gemini_error = je
                        logger.error("Gemini JSON parsing failed for model %s with key %s. Error: %s\nRaw response text:\n%s", g_model, self._mask_secret(key), str(je), raw_text if "raw_text" in locals() else "<no response>")
                        break
                    except Exception as e:
                        gemini_error = e
                        logger.warning(
                            "Gemini invocation failed provider=gemini model=%s key=%s reason=%s",
                            g_model,
                            self._mask_secret(key),
                            str(e),
                        )
                        error_msg = str(e).lower()
                        if "429" in error_msg or "quota" in error_msg or "limit" in error_msg:
                            logger.warning(
                                "Gemini quota limit exceeded provider=gemini model=%s key=%s",
                                g_model,
                                self._mask_secret(key),
                            )
                            LLMClient._gemini_blocked_models.add(g_model)
                            break

            if gemini_error:
                raise RuntimeError(
                    f"All LLM providers failed to return valid JSON. Groq error: {groq_error}. Gemini error: {gemini_error}"
                ) from gemini_error
            raise RuntimeError(
                f"All Groq providers failed and no Gemini fallback succeeded. Groq error: {groq_error}"
            )

        if groq_error:
            raise RuntimeError(f"Groq execution failed and no Gemini fallback is configured: {groq_error}") from groq_error
        raise RuntimeError("No LLM clients configured. Please verify your keys in .env.")

    @classmethod
    def reset_circuit_breaker(cls):
        cls._groq_blocked = False
        logger.info("LLM Client circuit breakers have been reset.")


# INTEGRATION NOTE
# Shared LLM wrapper. Agents 1, 2, 3 and the Validation agent MUST call `LLMClient().generate_json`
# for consistent structured outputs and automated resilience.
