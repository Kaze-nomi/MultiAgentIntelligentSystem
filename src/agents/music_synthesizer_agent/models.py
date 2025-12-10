from pydantic import BaseModel, Field
from typing import List, Dict, Any
import os
import tempfile
import numpy as np
from scipy.io import wavfile
from uuid import uuid4


class MusicStyle(BaseModel):
    """Configuration for music style."""
    genre: str = Field(..., min_length=1, max_length=50)
    bpm: int = Field(120, ge=60, le=200)
    instruments: List[str] = Field(default_factory=list, max_items=10)
    duration_seconds: float = Field(30.0, ge=1.0, le=60.0)
    audio_format: str = Field("wav", regex="^wav$")


class MusicFile(BaseModel):
    """Representation of a music file with metadata and audio data.

    audio_data stores raw PCM bytes (no WAV header).
    """
    name: str = Field(..., min_length=1, max_length=100, regex=r"^[a-zA-Z0-9_-]+$?")
    style: MusicStyle
    audio_data: bytes
    sample_rate: int = 44100
    channels: int = Field(1, ge=1, le=8)
    bits_per_sample: int = Field(16, ge=8, le=32, multiple_of=8)

    def export(self, filepath: str) -> None:
        """Export the music file to a secure temporary location using basename of filepath.

        Uses atomic write to prevent corruption and partial files.
        Files accumulate in tempdir; external cleanup recommended.

        Args:
            filepath: Path whose basename is used for filename (directory ignored for security).

        Raises:
            ValueError: If export fails or invalid format/path.
        """
        if self.style.audio_format != "wav":
            raise ValueError(f"Export only supports WAV format, got {self.style.audio_format}")

        safe_filename = os.path.basename(filepath)
        if ".." in safe_filename or not safe_filename.lower().endswith(".wav"):
            raise ValueError("Invalid or unsafe filename")

        temp_dir = tempfile.gettempdir()
        prefix = uuid4().hex[:8]
        desired_filename = f"{prefix}_{safe_filename}"
        safe_path = os.path.join(temp_dir, desired_filename)
        tmp_path = os.path.join(temp_dir, f"{uuid4().hex[:8]}.tmp")

        dtype_str = f"int{self.bits_per_sample}"
        bytes_per_frame = (self.bits_per_sample // 8) * self.channels
        num_frames = len(self.audio_data) // bytes_per_frame
        audio_data_trunc = self.audio_data[:(num_frames * bytes_per_frame)]
        audio = np.frombuffer(audio_data_trunc, dtype=np.dtype(dtype_str)).reshape((num_frames, self.channels))

        try:
            wavfile.write(tmp_path, self.sample_rate, audio)
            os.rename(tmp_path, safe_path)
        except Exception as e:
            if os.path.exists(tmp_path):
                try:
                    os.unlink(tmp_path)
                except OSError:
                    pass  # Ignore cleanup failure
            raise ValueError(f"Failed to export to {safe_path}: {str(e)}")

    def analyze(self) -> Dict[str, Any]:
        """Analyze the music file.

        Returns:
            Dictionary with analysis results.
        """
        bytes_per_frame = (self.bits_per_sample // 8) * self.channels
        num_frames = len(self.audio_data) // bytes_per_frame
        duration = num_frames / self.sample_rate
        return {
            "duration_seconds": duration,
            "sample_rate": self.sample_rate,
            "channels": self.channels,
            "bits_per_sample": self.bits_per_sample,
            "size_bytes": len(self.audio_data),
            "style": self.style.model_dump(),
        }


class MusicStyleBuilder:
    """Builder pattern for constructing MusicStyle."""

    def __init__(self):
        self._config: Dict[str, Any] = {}

    def genre(self, genre: str) -> "MusicStyleBuilder":
        self._config["genre"] = genre
        return self

    def bpm(self, bpm: int) -> "MusicStyleBuilder":
        self._config["bpm"] = bpm
        return self

    def instruments(self, instruments: List[str]) -> "MusicStyleBuilder":
        self._config["instruments"] = instruments
        return self

    def duration_seconds(self, duration: float) -> "MusicStyleBuilder":
        self._config["duration_seconds"] = duration
        return self

    def audio_format(self, fmt: str) -> "MusicStyleBuilder":
        self._config["audio_format"] = fmt
        return self

    def build(self) -> MusicStyle:
        """Build and validate MusicStyle using Pydantic."""
        return MusicStyle(**self._config)
