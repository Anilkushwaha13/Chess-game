from typing import Optional, List, Tuple

class Piece:
    def __init__(self, color: str, piece_type: str):
        self.color = color  # 'white' or 'black'
        self.piece_type = piece_type
        
        # State tracking for powers
        self.has_moved = False
        self.move_count = 0
        self.capture_count = 0
        self.turns_in_center = 0
        self.has_been_in_check = False
        
        # Power activation state
        self.power_active = False
        self.power_used = False
        
    def to_dict(self):
        return {
            "color": self.color,
            "type": self.piece_type,
            "has_moved": self.has_moved,
            "power_active": self.power_active,
            "power_used": self.power_used
        }

class Pawn(Piece):
    def __init__(self, color: str):
        super().__init__(color, "pawn")

class Knight(Piece):
    def __init__(self, color: str):
        super().__init__(color, "knight")

class Bishop(Piece):
    def __init__(self, color: str):
        super().__init__(color, "bishop")

class Rook(Piece):
    def __init__(self, color: str):
        super().__init__(color, "rook")

class Queen(Piece):
    def __init__(self, color: str):
        super().__init__(color, "queen")

class King(Piece):
    def __init__(self, color: str):
        super().__init__(color, "king")


class Board:
    def __init__(self):
        # 8x8 grid. Row 0 = rank 8 (Black's side), Row 7 = rank 1 (White's side)
        self.grid: List[List[Optional[Piece]]] = [[None for _ in range(8)] for _ in range(8)]
        self.setup_board()

    def setup_board(self):
        # Black Pieces
        placement = [Rook, Knight, Bishop, Queen, King, Bishop, Knight, Rook]
        for col in range(8):
            self.grid[0][col] = placement[col]("black")
            self.grid[1][col] = Pawn("black")
            
        # White Pieces
        for col in range(8):
            self.grid[6][col] = Pawn("white")
            self.grid[7][col] = placement[col]("white")

    def get_piece(self, row: int, col: int) -> Optional[Piece]:
        if 0 <= row < 8 and 0 <= col < 8:
            return self.grid[row][col]
        return None

    def move_piece(self, start_row: int, start_col: int, end_row: int, end_col: int):
        """Moves a piece from start to end without validation (validation happens in Game Engine)"""
        piece = self.grid[start_row][start_col]
        target = self.grid[end_row][end_col]
        
        if piece:
            if target:
                piece.capture_count += 1 # Track captures for powers
                
            self.grid[end_row][end_col] = piece
            self.grid[start_row][start_col] = None
            piece.has_moved = True
            piece.move_count += 1
            
    def to_dict(self):
        return [
            [piece.to_dict() if piece else None for piece in row]
            for row in self.grid
        ]
