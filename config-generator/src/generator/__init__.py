"""Insurance API Config Generator using Qwen 7B"""

from .config_generator import ConfigGenerator
from .qwen_client import QwenClient
from .prompt_templates import SYSTEM_PROMPT, create_mapping_prompt

__version__ = "1.0.0"
__all__ = [
    "ConfigGenerator",
    "QwenClient",
    "SYSTEM_PROMPT",
    "create_mapping_prompt"
]