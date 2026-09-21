import React, { useState, useRef, useEffect } from 'react';
import './App.css';

function App() {
  const [view, setView] = useState('menu'); 
  const [gameMode, setGameMode] = useState('classic'); 
  const [roomCodeInput, setRoomCodeInput] = useState('');
  const [roomPassword, setRoomPassword] = useState('');
  const [roomRole, setRoomRole] = useState('play');
  
  const [activeRoom, setActiveRoom] = useState('');
  const [myColor, setMyColor] = useState(null);
  const [board, setBoard] = useState(null);
  const [turn, setTurn] = useState('white');
  const [selectedSq, setSelectedSq] = useState(null);
  const [validMoves, setValidMoves] = useState({});
  const [gameOver, setGameOver] = useState(null);
  const [promotionPending, setPromotionPending] = useState(null);
  
  // Visual smooth states
  const [lastMove, setLastMove] = useState(null);
  const [inCheck, setInCheck] = useState(null);
  
  // Review Mode states
  const [fullHistory, setFullHistory] = useState([]);
  const [reviewMode, setReviewMode] = useState(false);
  const [reviewIndex, setReviewIndex] = useState(0);
  
  // Server stats
  const [serverStats, setServerStats] = useState({ players_online: 0, ai_games: 0 });

  useEffect(() => {
    const fetchStats = async () => {
        try {
            const backendHttp = import.meta.env.VITE_BACKEND_URL || "http://localhost:8000";
            const res = await fetch(`${backendHttp}/stats`);
            const data = await res.json();
            setServerStats(data);
        } catch(e) {}
    };
    fetchStats();
    const interval = setInterval(fetchStats, 5000);
    return () => clearInterval(interval);
  }, []);
  
  const ws = useRef(null);

  const startGame = (playMode) => {
    let code = roomCodeInput;
    if (playMode === 'local') code = `local-${Math.floor(Math.random()*10000)}`;
    if (playMode === 'ai') code = `ai-${Math.floor(Math.random()*10000)}`;
    if (playMode === 'online' && !code) {
        alert("Please enter a room code first.");
        return;
    }
    
    setActiveRoom(code);
    
    const backendWs = (import.meta.env.VITE_BACKEND_URL || "http://localhost:8000").replace(/^http/, 'ws');
    const url = `${backendWs}/ws/${code}?mode=${gameMode}&is_ai=${playMode==='ai'}&is_local=${playMode==='local'}&role=${roomRole}&password=${encodeURIComponent(roomPassword)}`;
    ws.current = new WebSocket(url);
    
    ws.current.onmessage = (event) => {
      const data = JSON.parse(event.data);
      if (data.type === 'init') {
        setMyColor(data.color);
        setBoard(data.board);
        setTurn(data.turn);
        setValidMoves(data.valid_moves || {});
        setGameOver(data.game_over || null);
        setInCheck(data.in_check || null);
        setView('game');
      } else if (data.type === 'game_state') {
        setBoard(data.board);
        setTurn(data.turn);
        setValidMoves(data.valid_moves || {});
        setGameOver(data.game_over || null);
        setInCheck(data.in_check || null);
        if (data.history) setLastMove(data.history);
        if (data.full_history) {
            setFullHistory(data.full_history);
            setReviewIndex(data.full_history.length - 1);
        }
        setSelectedSq(null);
      } else if (data.type === 'error') {
        alert(data.message);
        setSelectedSq(null);
      } else if (data.type === 'info') {
        alert(data.message);
      }
    };
  };

  const executeMove = (r, c, promotion = 'queen') => {
    ws.current.send(JSON.stringify({
      type: 'move',
      from: selectedSq,
      to: [r, c],
      promotion: promotion
    }));
    setPromotionPending(null);
  };

  const handleSquareClick = (r, c) => {
    if (gameOver || reviewMode || myColor === 'spectator') return;

    if (selectedSq) {
      const key = `${selectedSq[0]},${selectedSq[1]}`;
      const isSquareValid = validMoves[key]?.some(m => m[0] === r && m[1] === c);
      
      if (isSquareValid) {
        const piece = board[selectedSq[0]][selectedSq[1]];
        if (piece && piece.type === 'pawn' && (r === 0 || r === 7)) {
          setPromotionPending({ r, c });
          return;
        }

        executeMove(r, c);
        return;
      }
      
      if (selectedSq[0] === r && selectedSq[1] === c) {
        setSelectedSq(null);
        return;
      }
    }
    
    if (board && board[r][c]) {
      if (myColor !== 'both' && board[r][c].color !== myColor) return;
      if (board[r][c].color !== turn) return;
      setSelectedSq([r, c]);
    } else {
      setSelectedSq(null);
    }
  };

  if (view === 'menu') {
    return (
      <div className="menu-container">
        <div className="player-count-badge">
          🟢 {serverStats.players_online} Players Online
        </div>
        <h1>⚡ Power Chess ⚡</h1>
        
        <div className="menu-section">
          <h3>1. Select Ruleset</h3>
          <div className="button-group">
            <button className={`mode-btn ${gameMode === 'classic' ? 'active' : ''}`} onClick={() => setGameMode('classic')}>
              ♟️ Classic Chess
            </button>
            <button className={`mode-btn ${gameMode === 'power' ? 'active' : ''}`} onClick={() => setGameMode('power')}>
              ⚡ Power Chess
            </button>
          </div>
        </div>

        <div className="menu-section">
          <h3>2. Select Game Mode</h3>
          <button className="big-btn" onClick={() => startGame('local')}>🤝 Pass & Play (Local 1v1)</button>
          <button className="big-btn ai-btn" onClick={() => startGame('ai')}>🤖 Play vs Robot AI</button>
          
          <div className="online-box" style={{display: 'flex', flexDirection: 'column', gap: '10px', marginTop: '20px'}}>
            <input 
              value={roomCodeInput} 
              onChange={e => setRoomCodeInput(e.target.value)} 
              placeholder="Enter Room Code (e.g. 1234)"
            />
            <input 
              value={roomPassword} 
              onChange={e => setRoomPassword(e.target.value)} 
              placeholder="Password (leave empty for public room)"
              type="password"
            />
            <select value={roomRole} onChange={e => setRoomRole(e.target.value)} style={{padding: '10px', borderRadius: '8px'}}>
              <option value="play">Play Match</option>
              <option value="watch">Spectate Only</option>
            </select>
            <button className="big-btn online-btn" onClick={() => startGame('online')}>🌐 Join / Create Online Room</button>
          </div>
        </div>
      </div>
    );
  }

  const renderBoard = reviewMode ? fullHistory[reviewIndex]?.board_state : board;

  return (
    <div className="game-container">
      {gameOver && !reviewMode && (
        <div className="modal-overlay">
          <div className="modal-content game-over">
            <h2>🏆 {gameOver} 🏆</h2>
            <div style={{display: 'flex', gap: '10px', justifyContent: 'center'}}>
                <button className="big-btn" onClick={() => window.location.reload()}>Play Again</button>
                {fullHistory.length > 0 && (
                    <button className="big-btn" style={{backgroundColor: '#6600ff'}} onClick={() => setReviewMode(true)}>Review Game</button>
                )}
            </div>
          </div>
        </div>
      )}

      {promotionPending && (
        <div className="modal-overlay">
          <div className="modal-content">
            <h3>Choose Promotion</h3>
            <div className="promo-buttons">
              <button onClick={() => executeMove(promotionPending.r, promotionPending.c, 'queen')}>♛ Queen</button>
              <button onClick={() => executeMove(promotionPending.r, promotionPending.c, 'rook')}>♜ Rook</button>
              <button onClick={() => executeMove(promotionPending.r, promotionPending.c, 'bishop')}>♝ Bishop</button>
              <button onClick={() => executeMove(promotionPending.r, promotionPending.c, 'knight')}>♞ Knight</button>
            </div>
          </div>
        </div>
      )}

      <div className="header-info">
        <span className="badge">Room: {activeRoom}</span>
        <span className="badge" style={{color: '#00ffcc'}}>Playing as: {myColor === 'both' ? 'ANY' : myColor.toUpperCase()}</span>
        <span className="badge">Mode: {gameMode.toUpperCase()}</span>
      </div>
      
      {!reviewMode && <h3>Current Turn: <span className={turn === 'white' ? 'white-turn' : 'black-turn'}>{turn.toUpperCase()}</span></h3>}
      {reviewMode && <h3 style={{color: 'yellow'}}>Review Mode: Move {reviewIndex + 1}</h3>}
      
      <div className="board">
        {renderBoard && renderBoard.map((row, rIdx) => {
          const r = myColor === 'black' ? 7 - rIdx : rIdx;
          const displayRow = myColor === 'black' ? [...row].reverse() : row;
          
          return (
            <div key={r} className="board-row">
              {displayRow.map((cell, cIdx) => {
                const c = myColor === 'black' ? 7 - cIdx : cIdx;
                const isBlackSq = (r + c) % 2 === 1;
                const isSelected = selectedSq && selectedSq[0] === r && selectedSq[1] === c;
                const isKingInCheck = !reviewMode && inCheck && cell && cell.type === 'king' && cell.color === inCheck;
                
                let isLastMove = false;
                if (reviewMode) {
                    const revMove = fullHistory[reviewIndex];
                    isLastMove = revMove && ((r === revMove.from[0] && c === revMove.from[1]) || (r === revMove.to[0] && c === revMove.to[1]));
                } else if (lastMove) {
                    isLastMove = ((r === lastMove.from[0] && c === lastMove.from[1]) || (r === lastMove.to[0] && c === lastMove.to[1]));
                }
                
                let isValidTarget = false;
                if (selectedSq && !reviewMode) {
                   const key = `${selectedSq[0]},${selectedSq[1]}`;
                   isValidTarget = validMoves[key]?.some(m => m[0] === r && m[1] === c);
                }
                
                return (
                  <div 
                    key={c} 
                    className={`square ${isBlackSq ? 'black-sq' : 'white-sq'} ${isSelected ? 'selected' : ''} ${isLastMove ? 'last-move' : ''} ${isKingInCheck ? 'in-check' : ''}`}
                    onClick={() => handleSquareClick(r, c)}
                  >
                    {isValidTarget && <div className="valid-move-dot" />}
                    {cell && (
                      <span className={`piece ${cell.color}`}>
                        {cell.color === 'white' ? 
                          {'king': '♔', 'queen': '♕', 'rook': '♖', 'bishop': '♗', 'knight': '♘', 'pawn': '♙'}[cell.type] : 
                          {'king': '♚', 'queen': '♛', 'rook': '♜', 'bishop': '♝', 'knight': '♞', 'pawn': '♟'}[cell.type]
                        }
                      </span>
                    )}
                  </div>
                );
              })}
            </div>
          );
        })}
      </div>
      
      {reviewMode && (
          <div className="review-controls" style={{display: 'flex', gap: '15px', justifyContent: 'center', marginTop: '20px'}}>
              <button className="big-btn" onClick={() => setReviewIndex(Math.max(0, reviewIndex - 1))}>&lt; Prev</button>
              <button className="big-btn" onClick={() => setReviewMode(false)}>Exit Review</button>
              <button className="big-btn" onClick={() => setReviewIndex(Math.min(fullHistory.length - 1, reviewIndex + 1))}>Next &gt;</button>
          </div>
      )}
      
      <div style={{display: 'flex', gap: '15px', justifyContent: 'center', marginTop: '20px'}}>
        {!gameOver && !reviewMode && myColor !== 'spectator' && (
          <button className="leave-btn" style={{backgroundColor: '#e63946'}} onClick={() => ws.current.send(JSON.stringify({type: 'resign'}))}>Resign</button>
        )}
        <button className="leave-btn" onClick={() => window.location.reload()}>Leave Game</button>
      </div>
    </div>
  );
}

export default App;
