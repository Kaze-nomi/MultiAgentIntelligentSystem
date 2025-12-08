import logging

from models import WatermelonMessage


logger = logging.getLogger(__name__)


class SayerService:
    """Service responsible for outputting the watermelon message."""

    def say_watermelon(self, message: WatermelonMessage) -> None:
        """
        Outputs the watermelon message via logging.

        Args:
            message: The WatermelonMessage instance to output.
        """
        logger.info("Saying: %s", message.text)
