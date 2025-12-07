from fastapi import FastAPI, HTTPException
from ..interfaces import IGameAPI, ISnakeGame, IAIMoveProvider, IRenderer, IGameStorage
from ..business.snake_game_service import SnakeGameService
from ..business.snake_ai_service import SnakeAIService
from ..presentation.three_d_renderer_service import ThreeDRendererService
from ..data.game_state_service import GameStateService
from ..interfaces import GameState

class SnakeGameAPI(IGameAPI):
    """API implementation for Snake game."""

    def __init__(self):
        self.game_service = SnakeGameService()
        self.ai_service = SnakeAIService()
        self.renderer_service = ThreeDRendererService()
        self.state_service = GameStateService()

    def register_endpoints(self, app: FastAPI) -> None:
        """Register API endpoints with FastAPI app."""

        @app.post("/start-game")
        async def start_game(difficulty: str = None):
            try:
                game_state = self.game_service.start_game(difficulty)
                return {"status": "success", "game_state": self._state_to_dict(game_state)}
            except Exception as e:
                raise HTTPException(status_code=500, detail=str(e))

        @app.post("/move")
        async def move_snake(direction: str):
            try:
                game_state = self.game_service.move_snake(direction)
                return {"status": "success", "game_state": self._state_to_dict(game_state)}
            except ValueError as e:
                raise HTTPException(status_code=400, detail=str(e))
            except Exception as e:
                raise HTTPException(status_code=500, detail=str(e))

        @app.post("/ai-move")
        async def get_ai_move():
            try:
                current_state = self.game_service._get_current_state()  # Simplified for demo
                move = self.ai_service.get_ai_move(current_state)
                return {"status": "success", "move": move}
            except Exception as e:
                raise HTTPException(status_code=500, detail=str(e))

        @app.post("/render")
        async def render_frame():
            try:
                current_state = self.game_service._get_current_state()  # Simplified for demo
                render_result = self.renderer_service.render_frame(current_state)
                return {"status": "success", "frame": render_result.frame_data}
            except Exception as e:
                raise HTTPException(status_code=500, detail=str(e))

        @app.post("/save-state")
        async def save_game_state():
            try:
                current_state = self.game_service._get_current_state()  # Simplified for demo
                success = self.state_service.save_state(current_state)
                if success:
                    return {"status": "success"}
                else:
                    raise HTTPException(status_code=500, detail="Failed to save state")
            except Exception as e:
                raise HTTPException(status_code=500, detail=str(e))

        @app.get("/load-state/{game_id}")
        async def load_game_state(game_id: str):
            try:
                game_state = self.state_service.load_state(str(game_id))
                return {"status": "success", "game_state": self._state_to_dict(game_state)}
            except Exception as e:
                raise HTTPException(status_code=404, detail=str(e))

    def _state_to_dict(self, state: GameState) -> Dict:
        """Convert GameState to dictionary for JSON response."""
        return {
            'snake_body': state.snake_body,
            'direction': state.direction,
            'food_position': state.food_position,
            'score': state.score,
            'is_game_over': state.is_game_over,
            'difficulty': state.difficulty
        }
