from pydantic import BaseModel


class ArbuzSpeakerModel(BaseModel):
    """Model representing the arbuz speaker data.

    This model encapsulates the word to be spoken.
    """
    word: str = "arbuz"
