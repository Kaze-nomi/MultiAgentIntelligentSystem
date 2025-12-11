from dependency_injector import containers, providers
from .arbuz_speaker import ArbuzSpeaker


class Container(containers.DeclarativeContainer):
    """DI Container for managing dependencies."""

    speaker = providers.Singleton(ArbuzSpeaker)
