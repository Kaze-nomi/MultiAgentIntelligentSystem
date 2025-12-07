from typing import List, Tuple
from ..interfaces import IAIMoveProvider, GameState

class SnakeAIService(IAIMoveProvider):
    """Implementation of AI move provider for Snake game."""

    def get_ai_move(self, game_state: GameState) -> str:
        """Determine the best move using a simple heuristic-based approach."""
        if game_state.is_game_over:
            return None

        possible_moves = ['up', 'down', 'left', 'right']
        current_dir = game_state.direction

        # Simple strategy: try to move towards food while avoiding walls and self
        food_x, food_y = game_state.food_position
        head_x, head_y = game_state.snake_body[0]

        # Calculate preferred direction towards food
        preferred_moves = []
        if food_x < head_x:
            preferred_moves.append('left')
        elif food_x > head_x:
            preferred_moves.append('right')
        if food_y < head_y:
            preferred_moves.append('up')
        elif food_y > head_y:
            preferred_moves.append('down')

        # Filter valid moves that aren't opposite to current direction
        valid_moves = []
        for move in possible_moves:
            if move == 'up' and current_dir == 'down':
                continue
            if move == 'down' and current_dir == 'up':
                continue
            if move == 'left' and current_dir == 'right':
                continue
            if move == 'right' and current_dir == 'left':
                continue
            valid_moves.append(move)

        # Prioritize moves that get us closer to food
        best_move = None
        min_distance = float('inf')
        for move in valid_moves:
            next_x, next_y = head_x, head_y
            if move == 'up':
                next_y -= 1
            elif move == 'down':
                next_y += 1
            elif move == 'left':
                next_x -= 1
            else:  # right
                next_x += 1

            distance = abs(next_x - food_x) + abs(next_y - food_y)
            if distance < min_distance:
                min_distance = distance
                best_move = move

        return best_move if best_move is not None else valid_moves[0] if valid_moves else None
