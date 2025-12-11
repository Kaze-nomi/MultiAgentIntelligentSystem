import logging
import os
from fastapi import FastAPI, Depends, HTTPException, Security
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel
from .container import Container
from .interfaces import ISpeaker

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(title="Arbuz Speaker API", description="API for outputting the word 'arbuz'.")

# DI Container
container = Container()

# Security
security = HTTPBearer()

# Mock API key for simplicity (in production, use proper secret management)
API_KEY = os.getenv("API_KEY", "secret-key")

def verify_api_key(credentials: HTTPAuthorizationCredentials = Security(security)):
    """Verify the API key for authentication."""
    if credentials.credentials != API_KEY:
        raise HTTPException(status_code=401, detail="Invalid API key")
    return credentials.credentials

class SayArbuzRequest(BaseModel):
    """Request model for say_arbuz endpoint (empty for now, for future validation)."""
    pass

@app.get("/say_arbuz")
def say_arbuz_endpoint(
    request: SayArbuzRequest = Depends(),
    speaker: ISpeaker = Depends(container.speaker),
    api_key: str = Depends(verify_api_key)
):
    """Endpoint for getting the word 'arbuz'.

    Requires valid API key for authentication.

    Returns:
        dict: Dictionary with the message containing the word 'arbuz' or an error.
    """
    try:
        result = speaker.say_arbuz()
        return {"message": result}
    except Exception as e:
        # Log error type without sensitive details
        logger.error(f"Unexpected error in say_arbuz: {type(e).__name__}")
        raise HTTPException(status_code=500, detail="Internal server error")
