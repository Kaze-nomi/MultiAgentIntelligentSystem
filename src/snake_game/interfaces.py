from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import List, Tuple, Optional, Dict, Any
from fastapi import FastAPI

@dataclass
class GameState:
    """Represent the state of the snake game."""
    snake_body: List[Tuple[int, int]]
    direction: str
    food_position: Tuple[int, int]
    score: int
    is_game_over: bool
    difficulty: str = 'medium'

@dataclass
class RenderingResult:
    """Represent the result of rendering."""
    frame_data: str

class ISnakeGame(ABC):
    @abstractmethod
    def start_game(self, difficulty: Optional[str] = None) -> GameState:
        """Start a new game."""
        pass

    @abstractmethod
    def move_snake(self, direction: str) -> GameState:
        """Move the snake in the specified direction."""
        pass

class IAIMoveProvider(ABC):
    @abstractmethod
    def get_ai_move(self, game_state: GameState) -> str:
        """Get the AI-determined move."""
        pass

class IRenderer(ABC):
    @abstractmethod
    def render_frame(self, game_state: GameState) -> RenderingResult:
        """Render the current game frame."""
        pass

class IGameStorage(ABC):
    @abstractmethod
    def save_state(self, state: GameState) -> bool:
        """Save the game state."""
        pass

    @abstractmethod
    def load_state(self, game_id: str) -> GameState:
        """Load the game state."""
        pass

class IGameAPI(ABC):
    @abstractmethod
    def register_endpoints(self, app: FastAPI) -> None:
        """Register API endpoints with FastAPI app."""
        pass
