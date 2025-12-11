import threading
from .interfaces import ISpeaker
from .models import ArbuzSpeakerModel


class ArbuzSpeaker(ISpeaker):
    """Service class that implements ISpeaker to provide functionality for saying 'arbuz'.

    This class follows the Singleton pattern to ensure a single instance is used throughout the application.
    It uses a simple model to encapsulate the word.
    """

    _instance = None
    _lock = threading.Lock()

    def __new__(cls):
        """Create a new instance if one doesn't exist, ensuring thread-safe singleton behavior."""
        if cls._instance is None:
            with cls._lock:
                # Double-check locking
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
                    cls._instance._model = ArbuzSpeakerModel()
        return cls._instance

    def say_arbuz(self) -> str:
        """Return the word 'arbuz' as a string.

        This method retrieves the word from the model.

        Returns:
            str: The word 'arbuz'.
        """
        return self._model.word
