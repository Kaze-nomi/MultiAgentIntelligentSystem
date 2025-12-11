# music_composer_agent/__init__.py

"""Music Composer Agent package.

This package provides tools for generating and validating musical compositions
using a composer agent that leverages language models for creative output.
"""

from .models import MusicalComposition
from .server import MusicComposerAgent
from .interfaces import IMusicComposer
from .exceptions import CompositionGenerationError
from .services import OpenRouterMCPService
from .config import setup_logging

__all__ = [
    "MusicalComposition",
    "MusicComposerAgent",
    "IMusicComposer",
    "CompositionGenerationError",
    "OpenRouterMCPService",
    "setup_logging",
]
