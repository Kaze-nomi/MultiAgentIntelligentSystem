from abc import ABC, abstractmethod
from typing import Dict, List, Optional
import threading
import re
import numpy as np
from uuid import uuid4

from .models import MusicStyle, MusicFile


class SynthesisStrategy(ABC):
    """Abstract strategy for music synthesis."""

    @abstractmethod
    def synthesize(self, style: MusicStyle, sample_rate: int) -> bytes:
        """Synthesize raw PCM audio bytes (no WAV header)."""
        ...


class ClassicalStrategy(SynthesisStrategy):
    """Strategy for classical music synthesis."""

    def synthesize(self, style: MusicStyle, sample_rate: int) -> bytes:
        duration = style.duration_seconds
        base_freq = 440  # A4
        freq = base_freq * (style.bpm / 120)
        t = np.linspace(0, duration, int(sample_rate * duration), endpoint=False)
        wave = 0.5 * np.sin(2 * np.pi * freq * t) + 0.3 * np.sin(2 * np.pi * 2 * freq * t)
        audio = (wave * 32767).astype(np.int16)
        return audio.tobytes()


class RockStrategy(SynthesisStrategy):
    """Strategy for rock music synthesis."""

    def synthesize(self, style: MusicStyle, sample_rate: int) -> bytes:
        duration = style.duration_seconds
        base_freq = 220
        freq = base_freq * (style.bpm / 120) ** 0.5
        t = np.linspace(0, duration, int(sample_rate * duration), endpoint=False)
        wave = np.sin(2 * np.pi * freq * t)
        distorted = np.tanh(wave * 3)  # Simple distortion
        audio = (distorted * 32767).astype(np.int16)
        return audio.tobytes()


class MusicRepository:
    """In-memory thread-safe repository for MusicFile using Repository pattern, scoped by user_id.

    Limits: max 10 files, 100MB per user.
    """

    def __init__(self):
        self._storage: Dict[str, Dict[str, MusicFile]] = {}  # user_id -> {name: MusicFile}
        self._user_sizes: Dict[str, int] = {}  # user_id -> total_bytes
        self._lock = threading.Lock()

    def save(self, music_file: MusicFile, user_id: str) -> str:
        """Save a music file for a user.

        Raises:
            ValueError: If limits exceeded.

        Returns:
            The storage key (name).
        """
        with self._lock:
            if user_id not in self._storage:
                self._storage[user_id] = {}
                self._user_sizes[user_id] = 0
            user_store = self._storage[user_id]
            if len(user_store) >= 10:
                raise ValueError("Maximum 10 files per user reached")
            file_size = len(music_file.audio_data)
            if self._user_sizes[user_id] + file_size > 100 * 1024 * 1024:
                raise ValueError("Storage limit exceeded (100MB per user)")
            key = music_file.name
            self._storage[user_id][key] = music_file
            self._user_sizes[user_id] += file_size
            return key

    def get(self, user_id: str, key: str) -> Optional[MusicFile]:
        """Retrieve a music file by user and key."""
        with self._lock:
            return self._storage.get(user_id, {}).get(key)

    def delete(self, user_id: str, key: str) -> bool:
        """Delete a music file by user and key."""
        with self._lock:
            user_store = self._storage.get(user_id)
            if user_store and key in user_store:
                file_size = len(user_store[key].audio_data)
                del user_store[key]
                self._user_sizes[user_id] -= file_size
                if self._user_sizes[user_id] == 0:
                    del self._user_sizes[user_id]
                if not user_store:
                    del self._storage[user_id]
                return True
            return False

    def list(self, user_id: str) -> List[MusicFile]:
        """List all stored music files for a user."""
        with self._lock:
            return list(self._storage.get(user_id, {}).values())


class MusicSynthesizerAgent:
    """Facade for music synthesis using Strategy and Repository patterns."""

    def __init__(self):
        self._strategies: Dict[str, SynthesisStrategy] = {
            "classical": ClassicalStrategy(),
            "rock": RockStrategy(),
            "default": ClassicalStrategy(),
        }
        self.repo = MusicRepository()
        self.SAMPLE_RATE = 44100

    def synthesize_music(self, style: MusicStyle, user_id: str) -> MusicFile:
        """Synthesize music based on the given style for a user.

        Args:
            style: Music style configuration.
            user_id: User identifier.

        Returns:
            Synthesized MusicFile.

        Raises:
            ValueError: If synthesis fails or repo limits exceeded.
        """
        try:
            strategy_key = style.genre.lower()
            strategy = self._strategies.get(strategy_key, self._strategies["default"])
            audio_data = strategy.synthesize(style, sample_rate=self.SAMPLE_RATE)
            raw_name = f"{style.genre}_{style.bpm}bpm"
            sanitized_name = re.sub(r'[^a-zA-Z0-9_-]', '_', raw_name)
            name = f"{sanitized_name}_{uuid4().hex[:8]}"
            music_file = MusicFile(
                name=name,
                style=style,
                audio_data=audio_data,
                sample_rate=self.SAMPLE_RATE,
                channels=1,
                bits_per_sample=16
            )
            self.repo.save(music_file, user_id)
            return music_file
        except Exception as e:
            raise ValueError(f"Synthesis failed for genre '{style.genre}': {str(e)}")
