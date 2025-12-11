from dataclasses import dataclass, field
from typing import List, Optional, Dict, Any


@dataclass
class MusicalComposition:
    """Represents a musical composition with metadata and notes.

    Attributes:
        title (str): The title of the composition.
        composer (str): The composer of the composition.
        key (str): The key of the composition (e.g., 'C major', 'E minor').
        tempo (Optional[int]): The tempo in BPM, if specified.
        genre (Optional[str]): The genre of the composition, if specified.
        notes (List[str]): A list of notes or musical elements in textual representation.
        metadata (dict): Additional metadata as key-value pairs.
    """
    title: str
    composer: str
    key: str
    tempo: Optional[int] = None
    genre: Optional[str] = None
    notes: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)

    def __post_init__(self):
        """Post-initialization validation.

        Raises:
            ValueError: If required fields are invalid or notes are empty.
        """
        self._validate()

    def _validate(self):
        """Validate the composition fields.

        Raises:
            ValueError: If validation fails.
        """
        if not self.title or not isinstance(self.title, str):
            raise ValueError("Title must be a non-empty string.")
        if not self.composer or not isinstance(self.composer, str):
            raise ValueError("Composer must be a non-empty string.")
        if not self.key or not isinstance(self.key, str):
            raise ValueError("Key must be a non-empty string.")
        if self.tempo is not None and (not isinstance(self.tempo, int) or self.tempo <= 0):
            raise ValueError("Tempo must be a positive integer if provided.")
        if self.genre is not None and not isinstance(self.genre, str):
            raise ValueError("Genre must be a string if provided.")
        if not isinstance(self.notes, list):
            raise ValueError("Notes must be a list.")
        if not self.notes:
            raise ValueError("Notes cannot be empty.")
        if not all(isinstance(note, str) for note in self.notes):
            raise ValueError("All notes must be strings.")
        if not isinstance(self.metadata, dict):
            raise ValueError("Metadata must be a dictionary.")

    def add_note(self, note: str):
        """Adds a note to the composition.

        Args:
            note (str): The note to add.

        Raises:
            ValueError: If note is not a string.
        """
        if not isinstance(note, str):
            raise ValueError("Note must be a string.")
        self.notes.append(note)
        # Optimized validation: only check notes-related fields
        if not self.notes or not all(isinstance(n, str) for n in self.notes):
            raise ValueError("Notes must be a non-empty list of strings.")

    def get_notes_as_string(self) -> str:
        """Returns the notes as a single concatenated string.

        Returns:
            str: The notes joined by spaces.
        """
        return ' '.join(self.notes)

    def to_dict(self) -> Dict[str, Any]:
        """Convert the composition to a dictionary.

        Returns:
            Dict[str, Any]: Dictionary representation of the composition.
        """
        return {
            "title": self.title,
            "composer": self.composer,
            "key": self.key,
            "tempo": self.tempo,
            "genre": self.genre,
            "notes": self.notes,
            "metadata": self.metadata,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'MusicalComposition':
        """Create a composition from a dictionary.

        Args:
            data (Dict[str, Any]): Dictionary with composition data.

        Returns:
            MusicalComposition: The created composition.

        Raises:
            ValueError: If data is invalid.
        """
        required_keys = {"title", "composer", "key"}
        if not required_keys.issubset(data.keys()):
            raise ValueError(f"Missing required keys: {required_keys - set(data.keys())}")
        instance = cls(
            title=data["title"],
            composer=data["composer"],
            key=data["key"],
            tempo=data.get("tempo"),
            genre=data.get("genre"),
            notes=data.get("notes", []),
            metadata=data.get("metadata", {}),
        )
        # Enhanced validation as per medium remark
        instance._validate()
        return instance
