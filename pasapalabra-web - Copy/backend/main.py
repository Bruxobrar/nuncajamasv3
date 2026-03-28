import math
import os
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from pydantic import BaseModel
from typing import List, Dict

# ============================================================
# Pasapalabra Host Console - Backend (FastAPI)
# ============================================================

LETTERS = list("ABCDEFGHIJKLMNÑOPQRSTUVWXYZ")
LETTER_COUNT = len(LETTERS)  # 27
INITIAL_TIME = 90

STATE_LABELS = {
    "blue": "Pendiente",
    "green": "Correcta",
    "yellow": "Pasapalabra",
    "red": "Incorrecta",
}


class Player:
    def __init__(self, name: str, total_time: int):
        self.name = name
        self.total_time = total_time
        self.time_left = total_time
        self.states = ["blue"] * LETTER_COUNT
        self.current_index = 0
        self.finished = False

    def reset(self, total_time: int):
        self.total_time = total_time
        self.time_left = total_time
        self.states = ["blue"] * LETTER_COUNT
        self.current_index = 0
        self.finished = False

    def has_pending(self):
        return any(s in ("blue", "yellow") for s in self.states)

    def first_pending(self):
        for target in ("blue", "yellow"):
            for i, s in enumerate(self.states):
                if s == target:
                    return i
        return -1

    def next_pending(self, start_index: int):
        for target in ("blue", "yellow"):
            for offset in range(1, LETTER_COUNT + 1):
                idx = (start_index + offset) % LETTER_COUNT
                if self.states[idx] == target:
                    return idx
        return -1

    def score(self):
        return {
            "green": self.states.count("green"),
            "yellow": self.states.count("yellow"),
            "red": self.states.count("red"),
            "blue": self.states.count("blue"),
        }

    def update_finished(self):
        self.finished = not self.has_pending()
        if self.finished:
            self.current_index = -1

    def to_dict(self):
        return {
            "name": self.name,
            "total_time": self.total_time,
            "time_left": self.time_left,
            "states": self.states,
            "current_index": self.current_index,
            "finished": self.finished,
            "score": self.score(),
        }


class GameState:
    def __init__(self):
        self.players = [
            Player("Jugador 1", INITIAL_TIME),
            Player("Jugador 2", INITIAL_TIME),
        ]
        self.active_player = 0
        self.shown_player = 0
        self.compare_view = False
        self.running = False
        self.finished = False

    def reset(self, names: List[str], total_time: int):
        self.players = [
            Player(names[0] or "Jugador 1", total_time),
            Player(names[1] or "Jugador 2", total_time),
        ]
        self.active_player = 0
        self.shown_player = 0
        self.compare_view = False
        self.running = False
        self.finished = False

    def ensure_active_valid(self):
        if self.players[self.active_player].finished and not self.players[1 - self.active_player].finished:
            self.active_player = 1 - self.active_player

    def tick_timer(self):
        if not self.running or self.finished:
            return
        self.players[self.active_player].time_left -= 1
        if self.players[self.active_player].time_left <= 0:
            self.players[self.active_player].time_left = 0
            self.running = False

    def update_finished(self):
        for p in self.players:
            p.update_finished()
        self.finished = self.players[0].finished and self.players[1].finished
        if self.finished:
            self.running = False
        else:
            self.ensure_active_valid()

    def to_dict(self):
        return {
            "players": [p.to_dict() for p in self.players],
            "active_player": self.active_player,
            "shown_player": self.shown_player,
            "compare_view": self.compare_view,
            "running": self.running,
            "finished": self.finished,
            "letters": LETTERS,
        }


# FastAPI app
app = FastAPI(title="Pasapalabra Host Console")

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Global game state
game = GameState()


# ============================================================
# Models
# ============================================================
class ConfigUpdate(BaseModel):
    player1_name: str
    player2_name: str
    total_time: int


class MarkLetterRequest(BaseModel):
    state: str


# ============================================================
# Routes
# ============================================================

@app.get("/api/state")
def get_state():
    """Get current game state"""
    return game.to_dict()


@app.post("/api/config")
def update_config(config: ConfigUpdate):
    """Update player names and total time"""
    total_time = max(30, min(600, config.total_time))
    game.reset([config.player1_name, config.player2_name], total_time)
    return game.to_dict()


@app.post("/api/start-resume")
def start_or_resume():
    """Start or resume the game"""
    if game.finished:
        return {"error": "Game is finished"}
    
    game.ensure_active_valid()
    if game.players[game.active_player].finished:
        return {"error": "Active player is finished"}
    
    if game.players[game.active_player].current_index < 0:
        game.players[game.active_player].current_index = game.players[game.active_player].first_pending()
    
    game.compare_view = False
    game.shown_player = game.active_player
    game.running = True
    return game.to_dict()


@app.post("/api/pause")
def pause():
    """Pause the game"""
    game.running = False
    return game.to_dict()


@app.post("/api/mark-letter")
def mark_letter(request: MarkLetterRequest):
    """Mark current letter with a state"""
    if not game.running or game.finished:
        return {"error": "Game is not running"}
    
    p = game.players[game.active_player]
    idx = p.current_index
    
    if idx < 0:
        return {"error": "No active letter"}
    
    if request.state not in ["green", "yellow", "red"]:
        return {"error": "Invalid state"}
    
    p.states[idx] = request.state
    p.update_finished()
    
    if not p.finished:
        p.current_index = p.next_pending(idx)
    else:
        p.current_index = -1

    # Cambiar turno tras marcar (pasapalabra / incorrecta / correcta)
    next_player = 1 - game.active_player
    if not game.players[next_player].finished and game.players[next_player].has_pending():
        game.active_player = next_player
    elif not p.finished:
        # Si el otro ya terminó, se mantiene el actual
        game.active_player = game.active_player

    game.compare_view = False
    game.shown_player = game.active_player
    game.running = False
    game.update_finished()
    
    return game.to_dict()


@app.post("/api/toggle-compare")
def toggle_compare():
    """Toggle comparison view"""
    if game.running or game.finished:
        return {"error": "Cannot toggle compare view during play"}
    
    game.compare_view = not game.compare_view
    game.shown_player = 1 - game.active_player if game.compare_view else game.active_player
    return game.to_dict()


@app.post("/api/reset")
def reset():
    """Reset the game"""
    game.reset(
        [game.players[0].name, game.players[1].name],
        game.players[0].total_time
    )
    return game.to_dict()


@app.post("/api/timer-tick")
def timer_tick():
    """Advance timer by 1 second"""
    game.tick_timer()
    return game.to_dict()


# ============================================================
# Servir archivos estáticos (frontend)
# IMPORTANTE: Esto debe ir al final, después de todas las rutas /api
# ============================================================
frontend_path = os.path.join(os.path.dirname(__file__), "..", "frontend")
if os.path.exists(frontend_path):
    app.mount("/", StaticFiles(directory=frontend_path, html=True), name="frontend")
else:
    print(f"⚠️  Advertencia: No se encontró la carpeta frontend en {frontend_path}")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
