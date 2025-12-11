# arbuz_speaker/__init__.py

"""Module arbuz_speaker for outputting the word 'arbuz'.

This module provides access to the main components of the package,
including the ArbuzSpeaker service, ISpeaker interface, and ArbuzSpeakerModel.
"""

from .arbuz_speaker import ArbuzSpeaker
from .interfaces import ISpeaker
from .models import ArbuzSpeakerModel

__all__ = [
    "ArbuzSpeaker",
    "ISpeaker",
    "ArbuzSpeakerModel",
]
