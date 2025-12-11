from abc import ABC, abstractmethod
from .models import MusicalComposition
from .exceptions import CompositionGenerationError


class IMusicComposer(ABC):
    """Interface for music composer.

    This interface defines methods for generating and validating musical compositions.
    """

    @abstractmethod
    async def generate_composition(self, prompt: str, key: str = "C minor") -> MusicalComposition:
        """Generate a musical composition based on the given prompt.

        Args:
            prompt (str): Textual description or request for generating the composition.
            key (str): The key for the composition.

        Returns:
            MusicalComposition: The generated musical composition.

        Raises:
            CompositionGenerationError: If the prompt is invalid or generation is impossible.
        """
        pass

    @abstractmethod
    def validate_composition(self, composition: MusicalComposition) -> bool:
        """Validate the musical composition.

        Args:
            composition (MusicalComposition): Composition to validate.

        Returns:
            bool: True if the composition is valid, otherwise False.

        Raises:
            TypeError: If the passed object is not a MusicalComposition.
        """
        pass
