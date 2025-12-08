import logging
import sys
from pydantic import ValidationError

from models import WatermelonMessage

from services import SayerService


# Configure logging at application entry point
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def run_application() -> None:
    """
    Entry point function to run the watermelon sayer application.

    Creates a message instance, initializes the service, and says the watermelon.
    Handles any exceptions gracefully.
    """
    try:
        message = WatermelonMessage()
        service = SayerService()
        service.say_watermelon(message)
    except (ValueError, ValidationError) as exc:
        logger.error("Validation error: %s", exc)
    except Exception as exc:
        logger.error("Unexpected error: %s", exc, exc_info=True)


if __name__ == "__main__":
    run_application()
