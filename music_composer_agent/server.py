import asyncio
import aiohttp
from typing import List
import os

from music_composer_agent.models import MusicalComposition
from music_composer_agent.interfaces import IMusicComposer
from music_composer_agent.services import OpenRouterMCPService
from music_composer_agent.exceptions import CompositionGenerationError


class MusicComposerAgent(IMusicComposer):
    """Service for generating and validating musical compositions using LLM-based approaches.

    This agent uses an LLM service to generate compositions dynamically.
    """

    def __init__(self, llm_service: OpenRouterMCPService, composition_style: str = "classical", api_key: str = None):
        """Initialize the MusicComposerAgent.

        Args:
            llm_service (OpenRouterMCPService): The LLM service for generation.
            composition_style (str): The default composition style.
            api_key (str): API key for authentication.
        """
        self.llm_service = llm_service
        self.composition_style = composition_style
        self.api_key = api_key or os.getenv("MUSIC_COMPOSER_API_KEY")
        if not self.api_key:
            raise ValueError("API key must be provided via parameter or environment variable MUSIC_COMPOSER_API_KEY")

    async def generate_composition(self, prompt: str, key: str = "C minor") -> MusicalComposition:
        """Generate a musical composition based on the given prompt.

        Args:
            prompt (str): The user's request for a composition.
            key (str): The key for the composition.

        Returns:
            MusicalComposition: The generated composition object.

        Raises:
            CompositionGenerationError: If generation fails.
        """
        # Authentication check
        if not self.api_key:
            raise CompositionGenerationError("Authentication failed: API key not provided")
        # Note: For production, implement user authentication (e.g., JWT) in addition to API key.
        # Assuming client provides key in headers or something, but for simplicity, check if provided

        try:
            # Use LLM service to generate composition data
            generation_result = await self.llm_service.generate(prompt, key, self.composition_style)
            # Assuming generation_result is a dict with keys: title, composer, notes, etc.
            return MusicalComposition(
                title=generation_result.get("title", "Generated Composition"),
                composer=generation_result.get("composer", "AI Composer"),
                key=key,
                tempo=generation_result.get("tempo"),
                genre=generation_result.get("genre"),
                notes=generation_result.get("notes", []),
                metadata=generation_result.get("metadata", {}),
            )
        except aiohttp.ClientError as e:
            raise CompositionGenerationError(f"Network error during composition generation: {str(e)}") from e
        except ValueError as e:
            raise CompositionGenerationError(f"Validation error: {str(e)}") from e
        except Exception as e:
            raise CompositionGenerationError(f"Failed to generate composition: {str(e)}") from e

    def validate_composition(self, composition: MusicalComposition) -> bool:
        """Validate the given musical composition for completeness.

        Args:
            composition (MusicalComposition): The composition to validate.

        Returns:
            bool: True if the composition is valid, False otherwise.

        Raises:
            TypeError: If the input is not a MusicalComposition.
        """
        if not isinstance(composition, MusicalComposition):
            raise TypeError("Input must be a MusicalComposition instance.")
        try:
            composition._validate()
            return True
        except ValueError:
            return False
