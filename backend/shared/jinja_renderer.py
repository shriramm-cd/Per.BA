import os
from jinja2 import Environment, FileSystemLoader
from backend.shared.exceptions import TemplateNotFoundError

class JinjaRenderer:
    """
    Renders Jinja2 prompts for the agents and validators modules.
    """
    def __init__(self, search_paths=None):
        if search_paths is None:
            # Detect backend absolute directories automatically
            base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
            search_paths = [
                os.path.join(base_dir, "agents", "prompts"),
                os.path.join(base_dir, "validation_export", "prompts")
            ]
        
        # Verify paths existence to facilitate fallback setups
        existing_paths = [p for p in search_paths if os.path.isdir(p)]
        self.env = Environment(loader=FileSystemLoader(existing_paths))

    def render(self, template_name: str, context: dict) -> str:
        """
        Renders template context variables inside the designated prompt markdown files.
        """
        try:
            template = self.env.get_template(template_name)
            return template.render(context)
        except Exception as e:
            raise TemplateNotFoundError(f"Could not load or render prompt template '{template_name}': {str(e)}")

# INTEGRATION NOTE
# Make sure template folders exist. Member 2 (agents) and Member 5 (validation_export)
# rely on this renderer to generate markdown text prompts dynamically.
