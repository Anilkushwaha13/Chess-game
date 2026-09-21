import os
import asyncio
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from typing import Dict, List
import uvicorn
from engine import GameEngine

# Load .env file manually to avoid pip dependencies
if os.path.exists(".env"):
    with open(".env", "r") as f:
        for line in f:
            if line.strip() and not line.startswith("#"):
                k, v = line.strip().split("=", 1)
                os.environ[k] = v

app = FastAPI(title="Power Chess API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

class Room:
    def __init__(self, code: str, mode: str, password: str = None):
        self.code = code
        self.mode = mode
        self.password = password
        self.game = GameEngine(code, mode)
        self.white_player = None
        self.black_player = None
        self.spectators = []

class ConnectionManager:
    def __init__(self):
        self.rooms: Dict[str, Room] = {}

    def disconnect(self, websocket: WebSocket, room_code: str):
        if room_code in self.rooms:
            room = self.rooms[room_code]
            if room.white_player == websocket: room.white_player = None
            if room.black_player == websocket: room.black_player = None
            if websocket in room.spectators: room.spectators.remove(websocket)
            
            if not room.white_player and not room.black_player and not room.spectators:
                del self.rooms[room_code]

    async def broadcast(self, message: dict, room_code: str):
        room = self.rooms.get(room_code)
        if room:
            clients = [room.white_player, room.black_player] + room.spectators
            for connection in clients:
                if connection:
                    try:
                        await connection.send_json(message)
                    except:
                        pass

manager = ConnectionManager()

@app.get("/")
def read_root():
    return {"status": "Power Chess API is running"}

@app.get("/stats")
def get_stats():
    total_players = 0
    ai_games = 0
    for room in manager.rooms.values():
        if room.white_player: total_players += 1
        if room.black_player: total_players += 1
        total_players += len(room.spectators)
        if room.code.startswith("ai-") and (room.white_player or room.black_player):
            ai_games += 1
            
    return {"players_online": total_players, "ai_games": ai_games}

@app.websocket("/ws/{room_code}")
async def websocket_endpoint(
    websocket: WebSocket, 
    room_code: str, 
    mode: str = "power", 
    is_ai: str = "false", 
    is_local: str = "false",
    role: str = "play",
    password: str = ""
):
    await websocket.accept()
    
    # Enforce AI Limits
    if is_ai == "true":
        enable_limit = os.environ.get("ENABLE_AI_LIMIT", "false").lower() == "true"
        max_ai = int(os.environ.get("MAX_AI_CONCURRENCY", "4"))
        
        if enable_limit:
            ai_games = sum(1 for r in manager.rooms.values() if r.code.startswith("ai-") and (r.white_player or r.black_player))
            if ai_games >= max_ai and room_code not in manager.rooms:
                await websocket.send_json({"type": "error", "message": f"Server is at maximum AI capacity ({max_ai}/{max_ai}). Please try again later."})
                await websocket.close()
                return
    
    if room_code not in manager.rooms:
        manager.rooms[room_code] = Room(room_code, mode, password if password else None)
        
    room = manager.rooms[room_code]
    game = room.game
    
    if room.password and room.password != password:
        await websocket.send_json({"type": "error", "message": "Incorrect password for private room!"})
        await websocket.close()
        return
        
    assigned_color = "spectator"
    if is_local == "true":
        assigned_color = "both"
        room.white_player = websocket
    elif role == "play":
        if not room.white_player:
            assigned_color = "white"
            room.white_player = websocket
        elif not room.black_player:
            assigned_color = "black"
            room.black_player = websocket
        else:
            assigned_color = "spectator"
            room.spectators.append(websocket)
            await websocket.send_json({"type": "info", "message": "Room is full. You are spectating."})
    else:
        assigned_color = "spectator"
        room.spectators.append(websocket)
        
    try:
        await websocket.send_json({
            "type": "init", 
            "color": assigned_color, 
            "board": game.board.to_dict(), 
            "turn": game.turn,
            "valid_moves": game.get_all_valid_moves_dict(),
            "game_over": game.check_game_over(),
            "in_check": game.turn if game._is_king_in_check(game.turn) else None
        })
        
        while True:
            data = await websocket.receive_json()
            if data["type"] == "resign":
                if assigned_color in ["white", "black", "both"]:
                    resigning_color = game.turn if assigned_color == "both" else assigned_color
                    game.resign(resigning_color)
                    payload = {
                        "type": "game_state",
                        "board": game.board.to_dict(),
                        "turn": game.turn,
                        "history": game.history[-1] if game.history else None,
                        "valid_moves": {},
                        "game_over": game.check_game_over(),
                        "in_check": None,
                        "full_history": game.history
                    }
                    await manager.broadcast(payload, room_code)
                continue
                
            if data["type"] == "move":
                if assigned_color != "both" and assigned_color != game.turn:
                    await websocket.send_json({"type": "error", "message": "It is not your turn, or you are spectating!"})
                    continue
                    
                sr, sc = data["from"][0], data["from"][1]
                er, ec = data["to"][0], data["to"][1]
                promotion = data.get("promotion", "queen")
                
                success = game.execute_move(sr, sc, er, ec, promotion)
                if success:
                    payload = {
                        "type": "game_state",
                        "board": game.board.to_dict(),
                        "turn": game.turn,
                        "history": game.history[-1] if game.history else None,
                        "valid_moves": game.get_all_valid_moves_dict(),
                        "game_over": game.check_game_over(),
                        "in_check": game.turn if game._is_king_in_check(game.turn) else None,
                        "full_history": game.history if game.check_game_over() else None
                    }
                    await manager.broadcast(payload, room_code)
                    
                    if is_ai == "true" and game.turn == "black" and not game.check_game_over():
                        await asyncio.sleep(0.5)
                        ai_move = game.get_ai_move()
                        if ai_move:
                            game.execute_move(ai_move[0][0], ai_move[0][1], ai_move[1][0], ai_move[1][1], "queen")
                            ai_payload = {
                                "type": "game_state",
                                "board": game.board.to_dict(),
                                "turn": game.turn,
                                "history": game.history[-1] if game.history else None,
                                "valid_moves": game.get_all_valid_moves_dict(),
                                "game_over": game.check_game_over(),
                                "in_check": game.turn if game._is_king_in_check(game.turn) else None,
                                "full_history": game.history if game.check_game_over() else None
                            }
                            await manager.broadcast(ai_payload, room_code)
                else:
                    await websocket.send_json({"type": "error", "message": "Invalid move"})
                    
    except WebSocketDisconnect:
        manager.disconnect(websocket, room_code)

if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
