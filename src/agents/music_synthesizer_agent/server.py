from fastapi import FastAPI, HTTPException, Path, Depends, Query
from typing import List
import os
import base64
import re
from fastapi.security import APIKeyHeader

from .models import MusicStyle, MusicFile
from .agent import MusicSynthesizerAgent


class MusicSynthesizerServer:
    """Server for handling music synthesis requests with FastAPI integration."""

    def __init__(self):
        self.app = FastAPI(title="Music Synthesizer Server")
        self.agent = MusicSynthesizerAgent()
        self.host = os.getenv("SERVER_HOST", "127.0.0.1")
        self.port = int(os.getenv("SERVER_PORT", "8000"))
        self._api_keys_to_users = {}
        demo_key = os.getenv("DEMO_API_KEY")
        if demo_key:
            self._api_keys_to_users[demo_key] = "demo_user"
        classical_key = os.getenv("CLASSICAL_API_KEY")
        if classical_key:
            self._api_keys_to_users[classical_key] = "classical_user"
        rock_key = os.getenv("ROCK_API_KEY")
        if rock_key:
            self._api_keys_to_users[rock_key] = "rock_user"
        self.api_key_scheme = APIKeyHeader(
            name="X-API-Key", description="API Key for authentication"
        )
        self._setup_routes()

    def _get_user_id(self, api_key: str) -> str:
        """Get user_id from API key."""
        user_id = self._api_keys_to_users.get(api_key)
        if user_id is None:
            raise HTTPException(status_code=401, detail="Invalid API Key")
        return user_id

    def _setup_routes(self) -> None:
        @self.app.post("/synthesize")
        async def synthesize(
            api_key: str = Depends(self.api_key_scheme),
            style: MusicStyle,
            include_audio: bool = Query(False, description="Whether to include base64 encoded audio data")
        ) -> dict:
            user_id = self._get_user_id(api_key)
            try:
                music_file = self.agent.synthesize_music(style, user_id)
                analysis = music_file.analyze()
                resp = {
                    "success": True,
                    "file_name": music_file.name,
                    "analysis": analysis,
                }
                if include_audio:
                    resp["audio_b64"] = base64.b64encode(music_file.audio_data).decode("utf-8")
                return resp
            except ValueError as e:
                raise HTTPException(status_code=400, detail=str(e))
            except Exception as e:
                raise HTTPException(status_code=500, detail=str(e))

        @self.app.get("/files")
        async def list_files(
            api_key: str = Depends(self.api_key_scheme)
        ) -> List[dict]:
            user_id = self._get_user_id(api_key)
            files = self.agent.repo.list(user_id)
            return [
                {
                    "name": f.name,
                    "duration": f.analyze()["duration_seconds"],
                    "genre": f.style.genre,
                }
                for f in files
            ]

        @self.app.get("/files/{name}")
        async def get_file(
            name: str = Path(..., description="Music file name"),
            api_key: str = Depends(self.api_key_scheme),
            include_audio: bool = Query(False, description="Whether to include base64 encoded audio data")
        ) -> dict:
            if not re.match(r"^[a-zA-Z0-9_-]+$", name):
                raise HTTPException(status_code=400, detail="Invalid filename format")
            user_id = self._get_user_id(api_key)
            file_ = self.agent.repo.get(user_id, name)
            if not file_:
                raise HTTPException(status_code=404, detail="File not found")
            analysis = file_.analyze()
            resp = {
                "name": file_.name,
                "analysis": analysis,
            }
            if include_audio:
                resp["audio_b64"] = base64.b64encode(file_.audio_data).decode("utf-8")
            return resp

        @self.app.get("/health")
        async def health() -> dict:
            return {"status": "healthy"}

    def run(self) -> None:
        """Run the FastAPI server."""
        import uvicorn
        uvicorn.run(
            self.app, host=self.host, port=self.port, log_level="info", reload=False
        )
