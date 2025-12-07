from typing import Optional, List, Tuple
from ..interfaces import ISnakeGame, GameState
import random

class SnakeGameService(ISnakeGame):
    """Implementation of the Snake game logic."""

    def __init__(self):
        self.grid_size = 20

    def start_game(self, difficulty: Optional[str] = None) -> GameState:
        """Start a new game with optional difficulty setting."""
        if difficulty not in ['easy', 'medium', 'hard']:
            difficulty = 'medium'

        # Initialize snake at the center
        start_pos = (self.grid_size // 2, self.grid_size // 2)
        snake_body = [start_pos]

        # Generate first food position
        food_position = self._generate_food(snake_body)

        return GameState(
            snake_body=snake_body,
            direction='right',
            food_position=food_position,
            score=0,
            is_game_over=False,
            difficulty=difficulty
        )

    def move_snake(self, direction: str) -> GameState:
        """Move the snake in the specified direction and return updated game state."""
        # Validate direction
        valid_directions = ['up', 'down', 'left', 'right']
        if direction not in valid_directions:
            raise ValueError(f"Invalid direction: {direction}")

        # Get current state (this is a simplified example; in real impl, we'd have state management)
        current_state = self._get_current_state()

        if current_state.is_game_over:
            return current_state

        # Calculate new head position
        head_x, head_y = current_state.snake_body[0]
        if direction == 'up':
            new_head = (head_x, head_y - 1)
        elif direction == 'down':
            new_head = (head_x, head_y + 1)
        elif direction == 'left':
            new_head = (head_x - 1, head_y)
        else:  # right
            new_head = (head_x + 1, head_y)

        # Check for collisions
        if self._is_collision(new_head, current_state.snake_body):
            return GameState(
                snake_body=current_state.snake_body,
                direction=current_state.direction,
                food_position=current_state.food_position,
                score=current_state.score,
                is_game_over=True,
                difficulty=current_state.difficulty
            )

        # Update snake body
        new_body = [new_head] + current_state.snake_body

        # Check for food consumption
        if new_head == current_state.food_position:
            new_score = current_state.score + 1
            new_body = new_body  # Grow by keeping the head
            new_food = self._generate_food(new_body)
        else:
            new_body = new_body[:-1]  # Remove tail if no food eaten
            new_score = current_state.score
            new_food = current_state.food_position

        return GameState(
            snake_body=new_body,
            direction=direction,
            food_position=new_food,
            score=new_score,
            is_game_over=False,
            difficulty=current_state.difficulty
        )

    def _generate_food(self, snake_body: List[Tuple[int, int]]) -> Tuple[int, int]:
        """Generate a new food position not on the snake body."""
        while True:
            food_x = random.randint(0, self.grid_size - 1)
            food_y = random.randint(0, self.grid_size - 1)
            food_pos = (food_x, food_y)
            if food_pos not in snake_body:
                return food_pos

    def _is_collision(self, position: Tuple[int, int], snake_body: List[Tuple[int, int]]) -> bool:
        """Check if position collides with snake body or boundaries."""
        x, y = position
        if x < 0 or x >= self.grid_size or y < 0 or y >= self.grid_size:
            return True
        if position in snake_body[1:]:  # Exclude head since we handle it separately
            return True
        return False

    def _get_current_state(self) -> GameState:
        """Placeholder to get current state (in real impl, this would come from state management)."""
        # This is a simplified example; real implementation would maintain state
        return GameState(
            snake_body=[(10, 10)],
            direction='right',
            food_position=(5, 5),
            score=0,
            is_game_over=False
        )
