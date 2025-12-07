from ..interfaces import IRenderer, GameState, RenderingResult

class ThreeDRendererService(IRenderer):
    """Implementation of 3D renderer for Snake game."""

    def render_frame(self, game_state: GameState) -> RenderingResult:
        """Render the current game state into a 3D frame representation."""
        if game_state.is_game_over:
            return RenderingResult(frame_data="Game Over")

        # Simplified 3D representation - in a real implementation,
        # this would interface with a 3D graphics library
        frame_data = self._generate_3d_representation(game_state)
        return RenderingResult(frame_data=frame_data)

    def _generate_3d_representation(self, game_state: GameState) -> str:
        """Generate a text-based 3D representation for demonstration."""
        representation = "3D Frame Representation:\n"
        representation += f"Snake Position: {game_state.snake_body}\n"
        representation += f"Food Position: {game_state.food_position}\n"
        representation += f"Score: {game_state.score}\n"
        representation += f"Difficulty: {game_state.difficulty}\n"
        return representation
