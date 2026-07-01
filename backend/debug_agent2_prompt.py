import asyncio
import os
import sys
sys.path.insert(0, r'E:\github\ai accelertor clone 2\BA-Accelerator')
from backend.shared.llm_client import LLMClient
from backend.shared.jinja_renderer import JinjaRenderer

async def main():
    GROQ_API_KEY = os.getenv("GROQ_API_KEY")
    if not GROQ_API_KEY:
        raise ValueError("GROQ_API_KEY environment variable is not set")
    GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
    if not GEMINI_API_KEY:
        raise ValueError("GEMINI_API_KEY environment variable is not set")
    renderer = JinjaRenderer()
    requirements = []
    for i in range(30):
        requirements.append({
            'id': f'REQ-{i+1:03d}',
            'content': f'This requirement describes feature {i+1} for the leave management workflow and includes business rules for approvals and audit logging.',
            'actors': ['Employee'],
            'business_rules': ['Rule 1', 'Rule 2']
        })
    prompt = renderer.render('agent2.jinja2', {'requirements': requirements})
    print('prompt length', len(prompt))
    llm = LLMClient()
    try:
        result = await asyncio.wait_for(llm.generate_json(prompt, system_prompt='You are an expert Enterprise Agile Architect. Organize requirements into epics and features. Output ONLY valid JSON.'), timeout=60)
        print('result keys', list(result.keys())[:10])
    except Exception as e:
        import traceback
        traceback.print_exc()

asyncio.run(main())
