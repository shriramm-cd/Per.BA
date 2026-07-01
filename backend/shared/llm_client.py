import json
from typing import Dict, Any, Optional
from groq import AsyncGroq
import google.generativeai as genai
from google.generativeai.types import GenerationConfig
from backend.config import settings
from backend.shared.logger import get_logger

logger = get_logger(__name__)

class LLMClient:
    """
    Unified LLM Client providing JSON structured output capability.
    Utilizes Groq as the primary LLM engine and falls back to Gemini.
    """
    def __init__(self):
        self.groq_key = settings.GROQ_API_KEY
        self.gemini_key = settings.GEMINI_API_KEY
        
        self.groq_client = AsyncGroq(api_key=self.groq_key) if self.groq_key else None
        
        if self.gemini_key:
            genai.configure(api_key=self.gemini_key)
            self.gemini_model = genai.GenerativeModel("gemini-3.5-flash")
        else:
            self.gemini_model = None

    async def generate_json(
        self, 
        prompt: str, 
        system_prompt: Optional[str] = None, 
        groq_model: str = "llama-3.3-70b-versatile"
    ) -> Dict[str, Any]:
        """
        Submits prompt to Groq. In case of API failure, retries via Google Gemini.
        Ensures output is JSON-compliant.
        """
        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": prompt})

        logger.debug(f"Submitting prompt:\n{prompt}")

        def clean_json_content(content: str) -> str:
            content = content.strip()
            if content.startswith("```json"):
                content = content[7:]
            elif content.startswith("```"):
                content = content[3:]
            if content.endswith("```"):
                content = content[:-3]
            return content.strip()

        # Try Groq with automatic model fallback
        import asyncio
        groq_error = None
        if self.groq_client:
            models_to_try = [groq_model] + ["llama-3.1-8b-instant", "llama-3.2-3b-preview"]
            for model in models_to_try:
                for attempt in range(3):
                    try:
                        logger.info(f"Submitting LLM request to Groq model: {model} (attempt {attempt+1}/3)")
                        response = await self.groq_client.chat.completions.create(
                            model=model,
                            messages=messages,
                            response_format={"type": "json_object"},
                            temperature=0.2,
                            timeout=120.0
                        )
                        raw_content = response.choices[0].message.content
                        logger.info(f"Raw Groq Response ({model}):\n{raw_content}")
                        
                        cleaned = clean_json_content(raw_content)
                        return json.loads(cleaned)
                    except json.JSONDecodeError as je:
                        logger.error(f"Groq JSON parsing failed for model {model}. Error: {str(je)}\nRaw response content:\n{raw_content}")
                        groq_error = je
                        break  # Parsing failure means model returned text, no need to retry rate limits
                    except Exception as e:
                        groq_error = e
                        error_msg = str(e).lower()
                        if "429" in error_msg or "rate limit" in error_msg or "tpm" in error_msg or "limit exceeded" in error_msg:
                            logger.warning(f"Groq rate limit hit for model {model}. Sleeping for 5s before retry... Error: {str(e)}")
                            await asyncio.sleep(5.0)
                            continue
                        else:
                            logger.warning(f"Groq invocation failed for model {model}: {str(e)}. Trying next model...")
                            break
            logger.warning("All Groq models failed. Falling back to Gemini.")
        else:
            logger.info("Groq client not available. Bypassing to Gemini.")


        # Fallback to Gemini
        if self.gemini_key:
            gemini_models = ["gemini-3.5-flash", "gemini-2.5-flash", "gemini-2.0-flash"]
            gemini_error = None
            for g_model in gemini_models:
                try:
                    logger.info(f"Submitting LLM request to Gemini model: {g_model}")
                    model_instance = genai.GenerativeModel(g_model)
                    full_prompt = prompt
                    if system_prompt:
                        full_prompt = f"System Context:\n{system_prompt}\n\nUser Request:\n{prompt}"
                    
                    response = await model_instance.generate_content_async(
                        contents=full_prompt,
                        generation_config=GenerationConfig(
                            response_mime_type="application/json",
                            temperature=0.2
                        )
                    )
                    raw_text = response.text
                    logger.info(f"Raw Gemini Response ({g_model}):\n{raw_text}")
                    
                    cleaned = clean_json_content(raw_text)
                    return json.loads(cleaned)
                except json.JSONDecodeError as je:
                    logger.error(f"Gemini JSON parsing failed for model {g_model}. Error: {str(je)}\nRaw response text:\n{raw_text}")
                    gemini_error = je
                    break
                except Exception as e:
                    logger.warning(f"Gemini invocation failed for model {g_model}: {str(e)}")
                    gemini_error = e

            if gemini_error:
                raise RuntimeError(f"All LLM clients failed to return valid JSON. Groq error: {str(groq_error)}. Gemini error: {str(gemini_error)}")
            else:
                raise RuntimeError(f"All Groq models failed and no Gemini fallback succeeded. Groq error: {str(groq_error)}")
        else:
            if groq_error:
                raise RuntimeError(f"Groq execution failed and no Gemini fallback is configured: {str(groq_error)}") from groq_error
            raise RuntimeError("No LLM clients configured. Please verify your keys in .env.")


# INTEGRATION NOTE
# Shared LLM wrapper. Agents 1, 2, 3 and the Validation agent MUST call `LLMClient().generate_json`
# for consistent structured outputs and automated resilience.
