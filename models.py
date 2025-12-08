from pydantic import BaseModel, Field


class WatermelonMessage(BaseModel):
    """Pydantic model representing the watermelon message."""

    text: str = Field(default="арбуз", min_length=1)
