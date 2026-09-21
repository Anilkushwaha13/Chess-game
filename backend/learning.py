import json
import os

EXPERIENCE_FILE = "experience.json"

def load_experience():
    if os.path.exists(EXPERIENCE_FILE):
        try:
            with open(EXPERIENCE_FILE, 'r') as f:
                return json.load(f)
        except:
            return {}
    return {}

def save_experience(exp):
    with open(EXPERIENCE_FILE, 'w') as f:
        json.dump(exp, f)

def record_game(history, winner_color):
    """
    history: List of dicts like {"fen": "...", "from": (r, c), "to": (r, c), "color": "white"|"black"}
    winner_color: "white" | "black" | "draw"
    """
    if not history: return
    
    exp = load_experience()
    
    for move in history:
        fen = move.get("fen")
        if not fen: continue
        
        # We only record moves made by the players, not standard state fen
        move_str = f"{move['from'][0]},{move['from'][1]}-{move['to'][0]},{move['to'][1]}"
        color = move["color"]
        
        if fen not in exp:
            exp[fen] = {}
            
        if move_str not in exp[fen]:
            exp[fen][move_str] = 0
            
        if winner_color == color:
            exp[fen][move_str] += 1
        elif winner_color == "draw":
            pass # Neutral
        else:
            exp[fen][move_str] -= 1
            
    save_experience(exp)

def get_best_historical_move(fen):
    exp = load_experience()
    if fen in exp:
        moves = exp[fen]
        best_move = None
        best_score = -9999
        
        for m, score in moves.items():
            if score > best_score:
                best_score = score
                best_move = m
                
        # Only return if it actually has a positive track record
        if best_score > 0 and best_move:
            parts = best_move.split('-')
            start = tuple(map(int, parts[0].split(',')))
            end = tuple(map(int, parts[1].split(',')))
            return start, end
            
    return None
