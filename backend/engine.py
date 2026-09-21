from typing import List, Tuple
from models import Board, Piece

class GameEngine:
    def __init__(self, room_code: str, game_mode: str = "power"):
        self.room_code = room_code
        self.board = Board()
        self.turn = "white"
        self.history = []
        self.game_mode = game_mode
        self.turn_count = 0
        self.en_passant_target = None # (row, col)

    def clone(self):
        new_engine = GameEngine(self.room_code, self.game_mode)
        for r in range(8):
            for c in range(8):
                p = self.board.grid[r][c]
                if p:
                    new_p = p.__class__(p.color)
                    new_p.__dict__ = p.__dict__.copy()
                    new_engine.board.grid[r][c] = new_p
        new_engine.turn = self.turn
        new_engine.turn_count = self.turn_count
        new_engine.en_passant_target = self.en_passant_target
        return new_engine

    def switch_turn(self):
        self.turn = "black" if self.turn == "white" else "white"
        self.turn_count += 1
        self.update_global_powers()

    def get_valid_moves(self, start_row: int, start_col: int) -> List[Tuple[int, int]]:
        piece = self.board.get_piece(start_row, start_col)
        if not piece or piece.color != self.turn:
            return []

        moves = self._get_pseudo_legal_moves(start_row, start_col, piece)
        
        if self.game_mode == "power" and piece.power_active:
            moves.extend(self._get_power_moves(start_row, start_col, piece))
            
        valid_moves = []
        for (r, c) in moves:
            if self._does_move_cause_check(start_row, start_col, r, c, piece.color):
                continue
                    
            if self.game_mode == "power" and self._is_adjacent_to_powered_enemy_queen(r, c, piece.color):
                target = self.board.get_piece(r, c)
                if not (target and target.piece_type == "queen" and target.power_active):
                    continue
            
            if (r, c) not in valid_moves:
                valid_moves.append((r, c))
                
        return valid_moves

    def _is_adjacent_to_powered_enemy_queen(self, r: int, c: int, my_color: str) -> bool:
        for dr in [-1, 0, 1]:
            for dc in [-1, 0, 1]:
                nr, nc = r + dr, c + dc
                if 0 <= nr < 8 and 0 <= nc < 8:
                    p = self.board.get_piece(nr, nc)
                    if p and p.piece_type == "queen" and p.color != my_color and p.power_active:
                        return True
        return False

    def _get_pseudo_legal_moves(self, r: int, c: int, piece: Piece, check_castling: bool = True) -> List[Tuple[int, int]]:
        moves = []
        if piece.piece_type == "pawn":
            direction = -1 if piece.color == "white" else 1
            if 0 <= r + direction < 8 and self.board.get_piece(r + direction, c) is None:
                moves.append((r + direction, c))
                if not piece.has_moved and 0 <= r + 2*direction < 8 and self.board.get_piece(r + 2*direction, c) is None:
                    moves.append((r + 2*direction, c))
            for dc in [-1, 1]:
                if 0 <= c + dc < 8 and 0 <= r + direction < 8:
                    target = self.board.get_piece(r + direction, c + dc)
                    if target and target.color != piece.color:
                        moves.append((r + direction, c + dc))
                    elif self.en_passant_target == (r + direction, c + dc):
                        moves.append((r + direction, c + dc)) # En Passant
        elif piece.piece_type == "knight":
            for dr, dc in [(-2,-1), (-2,1), (-1,-2), (-1,2), (1,-2), (1,2), (2,-1), (2,1)]:
                nr, nc = r + dr, c + dc
                if 0 <= nr < 8 and 0 <= nc < 8:
                    target = self.board.get_piece(nr, nc)
                    if not target or target.color != piece.color:
                        moves.append((nr, nc))
        elif piece.piece_type in ["bishop", "rook", "queen"]:
            dirs = []
            if piece.piece_type in ["bishop", "queen"]: dirs.extend([(-1,-1), (-1,1), (1,-1), (1,1)])
            if piece.piece_type in ["rook", "queen"]: dirs.extend([(-1,0), (1,0), (0,-1), (0,1)])
            for dr, dc in dirs:
                nr, nc = r + dr, c + dc
                while 0 <= nr < 8 and 0 <= nc < 8:
                    t = self.board.get_piece(nr, nc)
                    if not t: moves.append((nr, nc))
                    elif t.color != piece.color: moves.append((nr, nc)); break
                    else: break
                    nr, nc = nr + dr, nc + dc
        elif piece.piece_type == "king":
            for dr in [-1, 0, 1]:
                for dc in [-1, 0, 1]:
                    if dr == 0 and dc == 0: continue
                    nr, nc = r + dr, c + dc
                    if 0 <= nr < 8 and 0 <= nc < 8:
                        t = self.board.get_piece(nr, nc)
                        if not t or t.color != piece.color:
                            moves.append((nr, nc))
            # Castling
            if check_castling and not piece.has_moved and not self._is_king_in_check(piece.color):
                # Kingside
                if not self.board.get_piece(r, c + 1) and not self.board.get_piece(r, c + 2):
                    rook = self.board.get_piece(r, 7)
                    if rook and rook.piece_type == "rook" and not rook.has_moved:
                        if not self._does_move_cause_check(r, c, r, c + 1, piece.color):
                            moves.append((r, c + 2))
                # Queenside
                if not self.board.get_piece(r, c - 1) and not self.board.get_piece(r, c - 2) and not self.board.get_piece(r, c - 3):
                    rook = self.board.get_piece(r, 0)
                    if rook and rook.piece_type == "rook" and not rook.has_moved:
                        if not self._does_move_cause_check(r, c, r, c - 1, piece.color):
                            moves.append((r, c - 2))
        return moves

    def _get_power_moves(self, r: int, c: int, piece: Piece) -> List[Tuple[int, int]]:
        moves = []
        if piece.piece_type == "pawn":
            direction = -1 if piece.color == "white" else 1
            for dc in [-1, 1]:
                nr, nc = r + direction, c + dc
                if 0 <= nr < 8 and 0 <= nc < 8 and self.board.get_piece(nr, nc) is None:
                    moves.append((nr, nc))
        elif piece.piece_type == "knight" and not piece.power_used:
            for nr in range(max(0, r-3), min(8, r+4)):
                for nc in range(max(0, c-3), min(8, c+4)):
                    if self.board.get_piece(nr, nc) is None:
                        moves.append((nr, nc))
        elif piece.piece_type == "bishop" and not piece.power_used:
            dirs = [(-1,-1), (-1,1), (1,-1), (1,1)]
            for dr, dc in dirs:
                nr, nc = r + dr, c + dc
                while 0 <= nr < 8 and 0 <= nc < 8:
                    t = self.board.get_piece(nr, nc)
                    if t and t.color != piece.color:
                        moves.append((nr, nc))
                    nr, nc = nr + dr, nc + dc
        elif piece.piece_type == "rook" and not piece.power_used:
            dirs = [(-1,0), (1,0), (0,-1), (0,1)]
            for dr, dc in dirs:
                nr, nc = r + dr, c + dc
                if 0 <= nr < 8 and 0 <= nc < 8:
                    t = self.board.get_piece(nr, nc)
                    # Bulldozer only pushes FRIENDLY pieces. Enemies are captured normally.
                    if t and t.color == piece.color and t.piece_type != "king": 
                        br, bc = nr + dr, nc + dc
                        if 0 <= br < 8 and 0 <= bc < 8 and self.board.get_piece(br, bc) is None:
                            moves.append((nr, nc))
        return moves

    def _does_move_cause_check(self, sr: int, sc: int, er: int, ec: int, color: str) -> bool:
        op = self.board.grid[er][ec]
        p = self.board.grid[sr][sc]
        self.board.grid[er][ec] = p
        self.board.grid[sr][sc] = None
        
        # En passant simulation check
        ep_pawn = None
        if p.piece_type == "pawn" and (er, ec) == self.en_passant_target:
            ep_r = sr
            ep_c = ec
            ep_pawn = self.board.grid[ep_r][ep_c]
            self.board.grid[ep_r][ep_c] = None
            
        in_check = self._is_king_in_check(color)
        
        self.board.grid[sr][sc] = p
        self.board.grid[er][ec] = op
        if ep_pawn:
            self.board.grid[ep_r][ep_c] = ep_pawn
            
        return in_check

    def _is_king_in_check(self, color: str) -> bool:
        kr, kc = -1, -1
        for r in range(8):
            for c in range(8):
                p = self.board.get_piece(r, c)
                if p and p.piece_type == "king" and p.color == color:
                    kr, kc = r, c; break
            if kr != -1: break
        if kr == -1: return False
        
        enemy = "black" if color == "white" else "white"
        for r in range(8):
            for c in range(8):
                p = self.board.get_piece(r, c)
                if p and p.color == enemy:
                    if (kr, kc) in self._get_pseudo_legal_moves(r, c, p, check_castling=False): return True
        return False

    def check_game_over(self) -> str:
        import learning
        if hasattr(self, 'resigned_by') and self.resigned_by:
            winner = "black" if self.resigned_by == "white" else "white"
            learning.record_game(self.history, winner)
            return f"{winner.capitalize()} wins by Resignation!"
            
        if not self.get_all_valid_moves_dict():
            if self._is_king_in_check(self.turn):
                winner = "black" if self.turn == "white" else "white"
                learning.record_game(self.history, winner)
                return f"{winner.capitalize()} wins by Checkmate!"
            learning.record_game(self.history, "draw")
            return "Draw by Stalemate!"
        return None
        
    def resign(self, color: str):
        self.resigned_by = color

    def execute_move(self, start_row: int, start_col: int, end_row: int, end_col: int, promotion: str = "queen") -> bool:
        valid_moves = self.get_valid_moves(start_row, start_col)
        if (end_row, end_col) not in valid_moves: return False
            
        piece = self.board.get_piece(start_row, start_col)
        target = self.board.get_piece(end_row, end_col)
        
        if target and target.piece_type == "king": return False # Safety net
        
        pre_move_fen = self.board_to_fen()
        
        is_bulldozer = False
        if self.game_mode == "power" and piece.power_active:
            if piece.piece_type == "knight":
                dr, dc = abs(end_row - start_row), abs(end_col - start_col)
                if not ((dr == 2 and dc == 1) or (dr == 1 and dc == 2)):
                    piece.power_used = True; piece.power_active = False
            elif piece.piece_type == "bishop":
                if (end_row, end_col) not in self._get_pseudo_legal_moves(start_row, start_col, piece):
                    piece.power_used = True; piece.power_active = False
            elif piece.piece_type == "rook":
                if target and target.color == piece.color:
                    is_bulldozer = True
                else:
                    piece.power_used = True; piece.power_active = False
        
        new_ep_target = None
        if is_bulldozer:
            dr, dc = end_row - start_row, end_col - start_col
            dr = dr // abs(dr) if dr != 0 else 0
            dc = dc // abs(dc) if dc != 0 else 0
            br, bc = end_row + dr, end_col + dc
            self.board.grid[br][bc] = target
            self.board.grid[end_row][end_col] = piece
            self.board.grid[start_row][start_col] = None
            piece.has_moved = True
            piece.move_count += 1
            piece.power_used = True; piece.power_active = False
        else:
            is_castling = piece.piece_type == "king" and abs(end_col - start_col) == 2
            is_en_passant = piece.piece_type == "pawn" and (end_row, end_col) == self.en_passant_target
            
            if piece.piece_type == "pawn" and abs(end_row - start_row) == 2:
                new_ep_target = (start_row + (end_row - start_row)//2, start_col)
                
            self.board.move_piece(start_row, start_col, end_row, end_col)
            
            if is_castling:
                if end_col > start_col: # Kingside
                    self.board.move_piece(start_row, 7, start_row, end_col - 1)
                else: # Queenside
                    self.board.move_piece(start_row, 0, start_row, end_col + 1)
            elif is_en_passant:
                self.board.grid[start_row][end_col] = None # Remove captured pawn
            elif piece.piece_type == "pawn" and (end_row == 0 or end_row == 7):
                import models
                promoted_class = getattr(models, promotion.capitalize(), models.Queen)
                promoted = promoted_class(piece.color)
                promoted.has_moved = True
                self.board.grid[end_row][end_col] = promoted
                piece = promoted
                
        self.en_passant_target = new_ep_target
        self.history.append({
            "fen": pre_move_fen,
            "piece": piece.piece_type, 
            "color": piece.color, 
            "from": (start_row, start_col), 
            "to": (end_row, end_col),
            "board_state": self.board.to_dict()
        })
        self.evaluate_powers(piece, end_row, end_col)
        self.switch_turn()
        return True

    def get_all_valid_moves_dict(self):
        moves_dict = {}
        for r in range(8):
            for c in range(8):
                p = self.board.get_piece(r, c)
                if p and p.color == self.turn:
                    v_moves = self.get_valid_moves(r, c)
                    if v_moves:
                        moves_dict[f"{r},{c}"] = v_moves
        return moves_dict

    def evaluate_powers(self, piece, r, c):
        if self.game_mode != "power": return
        if piece.piece_type == "pawn":
            if piece.capture_count >= 1 or (piece.color == "white" and r == 3) or (piece.color == "black" and r == 4):
                piece.power_active = True
        elif piece.piece_type == "queen" and piece.capture_count >= 2:
            piece.power_active = True
        elif piece.piece_type == "knight" and piece.move_count >= 3 and not piece.power_used:
            piece.power_active = True

    def get_all_valid_moves(self, color: str):
        moves = []
        for r in range(8):
            for c in range(8):
                p = self.board.get_piece(r, c)
                if p and p.color == color:
                    for mr, mc in self.get_valid_moves(r, c):
                        moves.append(((r, c), (mr, mc)))
        return moves

    def board_to_fen(self) -> str:
        fen_rows = []
        for r in range(8):
            empty_count = 0
            row_str = ""
            for c in range(8):
                p = self.board.get_piece(r, c)
                if not p:
                    empty_count += 1
                else:
                    if empty_count > 0:
                        row_str += str(empty_count)
                        empty_count = 0
                    symbol = {'pawn':'p', 'knight':'n', 'bishop':'b', 'rook':'r', 'queen':'q', 'king':'k'}[p.piece_type]
                    if p.color == 'white': symbol = symbol.upper()
                    row_str += symbol
            if empty_count > 0:
                row_str += str(empty_count)
            fen_rows.append(row_str)
        fen = "/".join(fen_rows)
        turn_char = 'w' if self.turn == 'white' else 'b'
        
        # Determine castling roughly based on original positions and has_moved
        castling = ""
        wk = self.board.get_piece(7, 4)
        if wk and wk.piece_type == "king" and wk.color == "white" and not wk.has_moved:
            kr = self.board.get_piece(7, 7)
            qr = self.board.get_piece(7, 0)
            if kr and kr.piece_type == "rook" and not kr.has_moved: castling += "K"
            if qr and qr.piece_type == "rook" and not qr.has_moved: castling += "Q"
        bk = self.board.get_piece(0, 4)
        if bk and bk.piece_type == "king" and bk.color == "black" and not bk.has_moved:
            kr = self.board.get_piece(0, 7)
            qr = self.board.get_piece(0, 0)
            if kr and kr.piece_type == "rook" and not kr.has_moved: castling += "k"
            if qr and qr.piece_type == "rook" and not qr.has_moved: castling += "q"
        if not castling: castling = "-"
        
        ep = "-"
        if self.en_passant_target:
            er, ec = self.en_passant_target
            ep = f"{chr(ord('a') + ec)}{8 - er}"
            
        return f"{fen} {turn_char} {castling} {ep} 0 {self.turn_count//2 + 1}"

    def evaluate_board(self) -> float:
        # Advanced Evaluation for Power Mode
        vals = {"pawn": 100, "knight": 320, "bishop": 330, "rook": 500, "queen": 900, "king": 20000}
        
        # Simplified Piece Square Table (Central focus)
        pst_center = [
            [ -20, -10, -10, -10, -10, -10, -10, -20],
            [ -10,   0,   0,   0,   0,   0,   0, -10],
            [ -10,   0,  10,  15,  15,  10,   0, -10],
            [ -10,   0,  15,  25,  25,  15,   0, -10],
            [ -10,   0,  15,  25,  25,  15,   0, -10],
            [ -10,   0,  10,  15,  15,  10,   0, -10],
            [ -10,   0,   0,   0,   0,   0,   0, -10],
            [ -20, -10, -10, -10, -10, -10, -10, -20]
        ]
        
        score = 0
        for r in range(8):
            for c in range(8):
                p = self.board.get_piece(r, c)
                if p:
                    val = vals.get(p.piece_type, 100)
                    pst_bonus = pst_center[r][c]
                    
                    if p.piece_type == "pawn":
                        if p.color == "white": pst_bonus += (6 - r) * 10
                        else: pst_bonus += (r - 1) * 10
                        
                    power_bonus = 0
                    if self.game_mode == "power" and getattr(p, 'power_active', False):
                        if p.piece_type == "rook": power_bonus = 300
                        if p.piece_type == "queen": power_bonus = 400
                        if p.piece_type == "pawn": power_bonus = 50
                        if p.piece_type == "knight": power_bonus = 200
                            
                    piece_eval = val + pst_bonus + power_bonus
                    if p.color == "black": score += piece_eval
                    else: score -= piece_eval
        return score

    def get_ai_move(self):
        import math, random, os
        
        # Build history of piece placements to prevent loops
        past_layouts = [h['fen'].split()[0] for h in self.history]
        
        # 1. Stockfish Engine for Classic Mode
        if self.game_mode == "classic":
            try:
                from stockfish import Stockfish
                import chess
                sf_path = os.environ.get("STOCKFISH_PATH", os.path.join(os.path.dirname(__file__), "stockfish_bin", "stockfish", "stockfish-windows-x86-64-avx2.exe"))
                stockfish = Stockfish(path=sf_path, depth=12, parameters={"Skill Level": 20})
                fen = self.board_to_fen()
                if stockfish.is_fen_valid(fen):
                    stockfish.set_fen_position(fen)
                    top_moves = stockfish.get_top_moves(5)
                    best_move = None
                    
                    for move_info in top_moves:
                        m_str = move_info["Move"]
                        # Filter out moves causing a repetition
                        try:
                            cb = chess.Board(fen)
                            cb.push_uci(m_str)
                            next_layout = cb.fen().split()[0]
                            if past_layouts.count(next_layout) >= 1:
                                continue # Skip repetition
                        except Exception:
                            pass
                        
                        best_move = m_str
                        break
                        
                    if not best_move and top_moves:
                        best_move = top_moves[0]["Move"] # Fallback
                        
                    if best_move:
                        sc = ord(best_move[0]) - ord('a')
                        sr = 8 - int(best_move[1])
                        ec = ord(best_move[2]) - ord('a')
                        er = 8 - int(best_move[3])
                        prom = "queen"
                        if len(best_move) == 5:
                            prom = {'q':'queen', 'r':'rook', 'b':'bishop', 'n':'knight'}.get(best_move[4], "queen")
                        
                        # Validate the move translates correctly to our grid
                        valid = self.get_valid_moves(sr, sc)
                        if (er, ec) in valid:
                            return ((sr, sc), (er, ec), prom)
            except Exception as e:
                print(f"Stockfish fallback due to error: {e}")
                pass
                
        # 2. Advanced Custom Alpha-Beta for Power Mode (or fallback)
        import learning
        current_fen = self.board_to_fen()
        best_learned = learning.get_best_historical_move(current_fen)
        if best_learned:
            print(f"Playing learned move from experience DB! {best_learned}")
            return (best_learned[0], best_learned[1], "queen")
            
        moves = self.get_all_valid_moves("black")
        if not moves: return None
        
        # Filter moves that cause repetition if possible
        non_repeating_moves = []
        for start, end in moves:
            sim = self.clone()
            sim.execute_move(start[0], start[1], end[0], end[1], "queen")
            layout = sim.board_to_fen().split()[0]
            if past_layouts.count(layout) < 1:
                non_repeating_moves.append((start, end))
                
        # If all moves repeat, just allow them
        if non_repeating_moves:
            moves = non_repeating_moves
        
        # Move Ordering: Prioritize captures to optimize alpha-beta pruning
        def score_move(move):
            sr, sc = move[0]
            er, ec = move[1]
            target = self.board.get_piece(er, ec)
            return 1000 if target else 0
            
        moves.sort(key=score_move, reverse=True)
        
        best_move = moves[0]
        max_score = -math.inf
        
        def alpha_beta(engine_state, depth, alpha, beta, is_maximizing):
            if depth == 0:
                return engine_state.evaluate_board()
                
            valid_moves = engine_state.get_all_valid_moves(engine_state.turn)
            if not valid_moves:
                if engine_state._is_king_in_check(engine_state.turn):
                    return -99999 if is_maximizing else 99999
                return 0
                
            if is_maximizing:
                max_eval = -math.inf
                for start, end in valid_moves:
                    sim = engine_state.clone()
                    sim.execute_move(start[0], start[1], end[0], end[1], "queen")
                    ev = alpha_beta(sim, depth - 1, alpha, beta, False)
                    max_eval = max(max_eval, ev)
                    alpha = max(alpha, ev)
                    if beta <= alpha: break
                return max_eval
            else:
                min_eval = math.inf
                for start, end in valid_moves:
                    sim = engine_state.clone()
                    sim.execute_move(start[0], start[1], end[0], end[1], "queen")
                    ev = alpha_beta(sim, depth - 1, alpha, beta, True)
                    min_eval = min(min_eval, ev)
                    beta = min(beta, ev)
                    if beta <= alpha: break
                return min_eval

        # Depth 3 means 3 plies ahead (Black -> White -> Black)
        for start, end in moves:
            sim = self.clone()
            sim.execute_move(start[0], start[1], end[0], end[1], "queen")
            score = alpha_beta(sim, 2, -math.inf, math.inf, False)
            if score > max_score:
                max_score = score
                best_move = (start, end)
                
        return (best_move[0], best_move[1], "queen")

    def update_global_powers(self):
        if self.game_mode != "power": return
        for r in range(8):
            for c in range(8):
                p = self.board.get_piece(r, c)
                if p:
                    if p.piece_type == "bishop":
                        if (r, c) in [(3,3), (3,4), (4,3), (4,4)]: p.turns_in_center += 1
                        else: p.turns_in_center = 0
                        if p.turns_in_center >= 2 and not p.power_used: p.power_active = True
                    elif p.piece_type == "rook" and not p.has_moved and self.turn_count >= 10 and not p.power_used:
                        p.power_active = True
