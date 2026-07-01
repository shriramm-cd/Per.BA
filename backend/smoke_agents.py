import asyncio
import os
import sys
sys.path.insert(0, r'E:\github\ai accelertor clone 2\BA-Accelerator')
from backend.agents.agent3_user_story_generator import UserStoryGenerator
from backend.validation_export.agent4_validation_engine import run as run_agent4

class StubLLM:
    async def generate_json(self, prompt, system_prompt=None):
        return {
            'story_id': 'US-001',
            'traceability': {'requirement_id': 'REQ-1', 'epic_id': 'EP-1', 'feature_id': 'FT-1'},
            'epic': 'Auth',
            'feature': 'Login',
            'user_story': {'actor': 'User', 'goal': 'log in', 'benefit': 'access the system'},
            'acceptance_criteria': ['Given valid credentials'],
            'definition_of_done': ['Implemented'],
            'summary': 'Login story',
            'priority': 'High',
            'version': 1,
        }

async def main():
    generator = UserStoryGenerator(llm_client=StubLLM())
    stories = await generator.generate({'story_contexts':[{'story_context_id':'ctx-1','story_id':'US-001','requirement_id':'REQ-1','requirement':{'id':'REQ-1','text':'Allow login'},'epic':{'id':'EP-1','name':'Auth'},'feature':{'id':'FT-1','name':'Login'},'actor':'User'}]})
    print('agent3_ok', len(stories), stories[0].story_id)
    result = await run_agent4({'job_id':'smoke','user_stories':[{'id':'US-001','title':'Login','user_story_text':'As a user I want to log in so that I can access the system','acceptance_criteria':['Given valid credentials when the user submits the form then they are authenticated'],'epic_id':'EP-1','feature_id':'FT-1','trace_mappings':['REQ-1']}],'requirements':[{'id':'REQ-1','text':'Allow login'}]})
    print('agent4_ok', result.is_approved, result.quality_score)

asyncio.run(main())
