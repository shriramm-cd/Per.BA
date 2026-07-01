import asyncio
import os
import sys
sys.path.insert(0, r'E:\github\ai accelertor clone 2\BA-Accelerator')
from backend.shared.llm_client import LLMClient

async def main():
    GROQ_API_KEY = os.getenv("GROQ_API_KEY")
    if not GROQ_API_KEY:
        raise ValueError("GROQ_API_KEY environment variable is not set")
    GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
    if not GEMINI_API_KEY:
        raise ValueError("GEMINI_API_KEY environment variable is not set")
    client = LLMClient()
    print('client initialized')
    try:
        result = await asyncio.wait_for(client.generate_json('Return JSON {"ok": true}', system_prompt='You are a test assistant.'), timeout=45)
        print('RESULT', result)
    except Exception as e:
        import traceback
        print('EXC', repr(e))
        traceback.print_exc()

asyncio.run(main())
