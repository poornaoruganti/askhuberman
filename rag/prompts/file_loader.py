import os
import yaml
from jinja2 import Environment, BaseLoader
from typing import Dict, Any, Tuple

from rag.prompts.base import PromptLoaderBase
from rag.core.exceptions import ConfigurationError
from rag.utils.logging import setup_rag_logger

logger = setup_rag_logger(__name__)

class FilePromptLoader(PromptLoaderBase):
    def __init__(self, prompt_dir: str = "rag/prompts/templates"):
        self.prompt_dir = prompt_dir
        self.env = Environment(loader=BaseLoader())

    def load_full_config(self, filename: str) -> Dict[str, Any]:
        """
        Loads the raw YAML to access model_config, description, etc.
        """
        path = os.path.join(self.prompt_dir, filename)
        if not os.path.exists(path):
            raise ConfigurationError(f"Prompt file '{filename}' not found.")
        
        with open(path, "r", encoding="utf-8") as f:
            return yaml.safe_load(f)

    def render(self, template_name: str, **kwargs: Any) -> Tuple[str, str]:
        """
        Returns a tuple: (system_prompt, user_prompt)
        """
        config = self.load_full_config(template_name)
        
        try:
            # 1. Extract the raw strings
            system_raw = config["prompts"]["system"]
            user_raw = config["prompts"]["user"]
            
            # 2. Compile and Render
            # System prompt usually has no variables, but we render it just in case
            system_tmpl = self.env.from_string(system_raw)
            user_tmpl = self.env.from_string(user_raw)
            
            return (
                system_tmpl.render(**kwargs), 
                user_tmpl.render(**kwargs)
            )
            
        except KeyError:
            raise ConfigurationError(f"Prompt '{template_name}' is missing 'prompts.system' or 'prompts.user' keys.")