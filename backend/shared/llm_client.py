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
            self.gemini_model = genai.GenerativeModel("gemini-1.5-flash")
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
        groq_error = None
        if self.groq_client:
            models_to_try = [groq_model] + ["llama-3.3-70b-specdec", "llama3-70b-8192", "mixtral-8x7b-32768", "llama-3.1-8b-instant"]
            for model in models_to_try:
                try:
                    logger.info(f"Submitting LLM request to Groq model: {model}")
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
                except Exception as e:
                    logger.warning(f"Groq invocation failed for model {model}: {str(e)}. Trying next model...")
                    groq_error = e
            logger.warning("All Groq models failed. Falling back to Gemini.")
        else:
            logger.info("Groq client not available. Bypassing to Gemini.")


        # Fallback to Gemini
        if self.gemini_model:
            try:
                logger.info("Submitting LLM request to Gemini model: gemini-1.5-flash")
                full_prompt = prompt
                if system_prompt:
                    full_prompt = f"System Context:\n{system_prompt}\n\nUser Request:\n{prompt}"
                
                response = await self.gemini_model.generate_content_async(
                    contents=full_prompt,
                    generation_config=GenerationConfig(
                        response_mime_type="application/json",
                        temperature=0.2
                    )
                )
                raw_text = response.text
                logger.info(f"Raw Gemini Response:\n{raw_text}")
                
                cleaned = clean_json_content(raw_text)
                return json.loads(cleaned)
            except json.JSONDecodeError as je:
                logger.error(f"Gemini JSON parsing failed. Error: {str(je)}\nRaw response text:\n{raw_text}")
                raise RuntimeError(f"Gemini returned invalid JSON: {str(je)}. Raw response:\n{raw_text}") from je
            except Exception as e:
                logger.error(f"Gemini fallback failure: {str(e)}")
                raise RuntimeError(f"All LLM clients failed to return valid JSON. Groq error: {str(groq_error)}. Gemini error: {str(e)}") from e
        else:
            if groq_error:
                raise RuntimeError(f"Groq execution failed and no Gemini fallback is configured: {str(groq_error)}") from groq_error
            raise RuntimeError("No LLM clients configured. Please verify your keys in .env.")


# INTEGRATION NOTE
# Shared LLM wrapper. Agents 1, 2, 3 and the Validation agent MUST call `LLMClient().generate_json`
# for consistent structured outputs and automated resilience.
