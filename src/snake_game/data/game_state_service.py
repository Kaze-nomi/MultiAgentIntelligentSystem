import json
from typing import Dict, Any
from ..interfaces import IGameStorage, GameState
import os

class GameStateService(IGameStorage):
    """Implementation of game state storage using JSON files."""

    def __init__(self, storage_path: str = ".game_storage"):
        self.storage_path = storage_path
        os.makedirs(storage_path, exist_ok=True)

    def save_state(self, state: GameState) -> bool:
        """Save game state to JSON file."""
        try:
            game_id = state.snake_body[0][0], state.snake_body[0][1]
            file_path = os.path.join(self.storage_path, f"{game_id}.json")
            with open(file_path, 'w') as f:
                json.dump(self._state_to_dict(state), f)
            return True
        except Exception as e:
            print(f"Error saving state: {e}")
            return False

    def load_state(self, game_id: str) -> GameState:
        """Load game state from JSON file."""
        try:
            file_path = os.path.join(self.storage_path, f"{game_id}.json")
            with open(file_path, 'r') as f:
                data = json.load(f)
            return self._dict_to_state(data)
        except Exception as e:
            print(f"Error loading state: {e}")
            raise

    def _state_to_dict(self, state: GameState) -> Dict[str, Any]:
        """Convert GameState to dictionary for serialization."""
        return {
            'snake_body': state.snake_body,
            'direction': state.direction,
            'food_position': state.food_position,
            'score': state.score,
            'is_game_over': state.is_game_over,
            'difficulty': state.difficulty
        }

    def _dict_to_state(self, data: Dict[str, Any]) -> GameState:
        """Convert dictionary back to GameState."""
        return GameState(
            snake_body=data['snake_body'],
            direction=data['direction'],
            food_position=data['food_position'],
            score=data['score'],
            is_game_over=data['is_game_over'],
            difficulty=data.get('difficulty', 'medium')
        )
