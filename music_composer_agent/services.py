import aiohttp
from typing import Dict, Any
import json
import os
from .constants import VALID_KEYS, VALID_STYLES


class OpenRouterMCPService:
    """Service for interacting with OpenRouter MCP API for LLM-based generation."""

    def __init__(self, api_key: str = None, base_url: str = "https://openrouter.ai/api/v1", model: str = "openai/gpt-3.5-turbo"):
        """Initialize the OpenRouterMCPService.

        Args:
            api_key (str): API key for OpenRouter.
            base_url (str): Base URL for the API.
            model (str): The LLM model to use.
        """
        self.api_key = api_key or os.getenv("OPENROUTER_API_KEY")
        if not self.api_key:
            raise ValueError("API key must be provided via parameter or environment variable OPENROUTER_API_KEY")
        self.base_url = base_url
        self.model = model
        self.session = None

    async def __aenter__(self):
        self.session = aiohttp.ClientSession()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self.session:
            await self.session.close()

    async def generate(self, prompt: str, key: str, style: str) -> Dict[str, Any]:
        """Generate composition data using the LLM.

        Args:
            prompt (str): The prompt for generation.
            key (str): The musical key.
            style (str): The composition style.

        Returns:
            Dict[str, Any]: Generated composition data.

        Raises:
            Exception: If API call fails.
        """
        # Input validation
        if not isinstance(prompt, str) or not prompt.strip():
            raise ValueError("Prompt must be a non-empty string.")
        # Enhanced sanitization: limit length and remove dangerous chars
        prompt = prompt[:1000]  # Max length
        prompt = ''.join(c for c in prompt if c.isalnum() or c in ' .,;!?')  # Basic sanitization
        if key not in VALID_KEYS:
            raise ValueError(f"Invalid key: {key}. Must be one of {VALID_KEYS}")
        if style not in VALID_STYLES:
            raise ValueError(f"Invalid style: {style}. Must be one of {VALID_STYLES}")

        if not self.session:
            raise RuntimeError("Service must be used as async context manager.")
        url = f"{self.base_url}/chat/completions"
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }
        data = {
            "model": self.model,
            "messages": [
                {
                    "role": "user",
                    "content": f"Generate a musical composition in {style} style, key {key}, based on: {prompt}. Provide title, composer, notes as list of strings, tempo, genre, metadata.",
                }
            ],
        }
        async with self.session.post(url, headers=headers, json=data) as response:
            if response.status != 200:
                raise Exception(f"API error: {response.status} {await response.text()}")
            result = await response.json()
            try:
                content = result["choices"][0]["message"]["content"]
                parsed = json.loads(content)
                # Validate structure
                required_keys = ["title", "composer", "notes"]
                if not all(key in parsed for key in required_keys):
                    raise ValueError("Invalid response structure: missing required keys")
                # Additional validation: check types
                if not isinstance(parsed.get("notes"), list):
                    raise ValueError("Notes must be a list")
                return parsed
            except (json.JSONDecodeError, KeyError) as e:
                raise Exception(f"Failed to parse LLM response: {str(e)}") from e
