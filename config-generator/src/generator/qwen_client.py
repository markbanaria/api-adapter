import httpx
from typing import Optional
import logging

logger = logging.getLogger(__name__)


class QwenClient:
    """Client for local Qwen 7B model"""

    def __init__(
        self,
        base_url: str = "http://localhost:11434",  # Ollama default
        model: str = "qwen2.5:7b",  # Same as your existing project
        timeout: float = 120.0
    ):
        self.base_url = base_url
        self.model = model
        self.timeout = timeout
        self.client = httpx.Client(timeout=timeout)

    def generate(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        temperature: float = 0.1,  # Low temp for consistent config generation
        max_tokens: int = 4096
    ) -> str:
        """
        Generate completion from Qwen model

        Args:
            prompt: User prompt
            system_prompt: System prompt (optional)
            temperature: Sampling temperature (0.0-1.0)
            max_tokens: Maximum tokens to generate

        Returns:
            Generated text
        """
        url = f"{self.base_url}/api/generate"

        payload = {
            "model": self.model,
            "prompt": prompt,
            "system": system_prompt,
            "temperature": temperature,
            "stream": False,
            "options": {
                "num_predict": max_tokens
            }
        }

        logger.info(f"Calling Qwen model: {self.model}")
        logger.debug(f"Prompt length: {len(prompt)} chars")

        try:
            response = self.client.post(url, json=payload)
            response.raise_for_status()

            data = response.json()
            generated_text = data.get("response", "")

            logger.info(f"Generated {len(generated_text)} characters")
            return generated_text

        except httpx.HTTPError as e:
            logger.error(f"Qwen API error: {e}")
            raise RuntimeError(f"Failed to call Qwen model: {e}")

    def close(self):
        """Close HTTP client"""
        self.client.close()