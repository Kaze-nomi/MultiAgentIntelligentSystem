from fastapi import FastAPI, HTTPException
import pygame
import uvicorn
import os
from typing import Optional
from pydantic import BaseModel

app = FastAPI()

# Инициализация Pygame
pygame.init()
pygame.mixer.init()

# Конфигурация игры
SCREEN_WIDTH = 800
SCREEN_HEIGHT = 600
GRID_SIZE = 20
GRID_WIDTH = SCREEN_WIDTH // GRID_SIZE
GRID_HEIGHT = SCREEN_HEIGHT // GRID_SIZE

class GameState:
    def __init__(self):
        self.screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT))
        pygame.display.set_caption('Змейка')
        self.clock = pygame.time.Clock()
        self.snake = [(GRID_WIDTH // 2, GRID_HEIGHT // 2)]
        self.direction = (1, 0)
        self.food = self.generate_food()
        self.score = 0
        self.game_over = False
        self.speed = 10
        
        # Загрузка звуков
        try:
            self.eat_sound = pygame.mixer.Sound('sounds/eat.wav')
            self.game_over_sound = pygame.mixer.Sound('sounds/game_over.wav')
        except:
            print("Warning: Sound files not found")
            self.eat_sound = None
            self.game_over_sound = None
    
    def generate_food(self):
        import random
        while True:
            food = (random.randint(0, GRID_WIDTH - 1), random.randint(0, GRID_HEIGHT - 1))
            if food not in self.snake:
                return food
    
    def update(self):
        if self.game_over:
            return
            
        head_x, head_y = self.snake[0]
        dir_x, dir_y = self.direction
        new_head = ((head_x + dir_x) % GRID_WIDTH, (head_y + dir_y) % GRID_HEIGHT)
        
        if new_head in self.snake[1:]:
            self.game_over = True
            if self.game_over_sound:
                self.game_over_sound.play()
            return
        
        self.snake.insert(0, new_head)
        
        if new_head == self.food:
            self.score += 1
            if self.eat_sound:
                self.eat_sound.play()
            self.food = self.generate_food()
        else:
            self.snake.pop()
    
    def draw(self):
        self.screen.fill((0, 0, 0))
        
        # Рисуем змейку
        for segment in self.snake:
            pygame.draw.rect(self.screen, (0, 255, 0), 
                            (segment[0] * GRID_SIZE, segment[1] * GRID_SIZE, 
                             GRID_SIZE, GRID_SIZE))
        
        # Рисуем еду
        pygame.draw.rect(self.screen, (255, 0, 0), 
                        (self.food[0] * GRID_SIZE, self.food[1] * GRID_SIZE, 
                         GRID_SIZE, GRID_SIZE))
        
        # Рисуем счет
        font = pygame.font.SysFont(None, 36)
        score_text = font.render(f'Score: {self.score}', True, (255, 255, 255))
        self.screen.blit(score_text, (10, 10))
        
        if self.game_over:
            game_over_text = font.render('GAME OVER! Press R to restart', True, (255, 255, 255))
            text_rect = game_over_text.get_rect(center=(SCREEN_WIDTH//2, SCREEN_HEIGHT//2))
            self.screen.blit(game_over_text, text_rect)
        
        pygame.display.flip()

# Глобальное состояние игры
game_state = GameState()

class DirectionInput(BaseModel):
    direction: str

@app.post("/direction")
async def set_direction(direction_input: DirectionInput):
    direction_map = {
        "up": (0, -1),
        "down": (0, 1),
        "left": (-1, 0),
        "right": (1, 0)
    }
    
    if direction_input.direction in direction_map:
        # Проверка на противоположное направление
        current_dir = game_state.direction
        new_dir = direction_map[direction_input.direction]
        if (current_dir[0] * -1, current_dir[1] * -1) != new_dir:
            game_state.direction = new_dir
        return {"status": "success"}
    
    raise HTTPException(status_code=400, detail="Invalid direction")

@app.get("/status")
async def get_status():
    return {
        "score": game_state.score,
        "game_over": game_state.game_over,
        "snake_length": len(game_state.snake),
        "food_position": game_state.food
    }

@app.post("/restart")
async def restart_game():
    global game_state
    game_state = GameState()
    return {"status": "restarted"}

@app.post("/speed")
async def set_speed(speed: int):
    if 1 <= speed <= 20:
        game_state.speed = speed
        return {"status": "success"}
    raise HTTPException(status_code=400, detail="Speed must be between 1 and 20")

# Функция для запуска игрового цикла в отдельном потоке
def game_loop():
    import threading
    def loop():
        while True:
            game_state.update()
            game_state.draw()
            game_state.clock.tick(game_state.speed)
    
    thread = threading.Thread(target=loop, daemon=True)
    thread.start()

# Запускаем игровой цикл при старте сервера
game_loop()

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)