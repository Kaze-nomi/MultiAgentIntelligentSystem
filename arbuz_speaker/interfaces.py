from abc import ABC, abstractmethod


class ISpeaker(ABC):
    """Interface for components that can speak words."""

    @abstractmethod
    def say_arbuz(self) -> str:
        """Returns the word 'arbuz'.

        This method should encapsulate the logic for producing the word.
        """
        ...
