// JavaScript для игр

class GameManager {
    constructor() {
        this.currentGame = null;
        this.init();
    }
    
    init() {
        this.loadGames();
        this.setupGameListeners();
    }
    
    async loadGames() {
        try {
            const response = await fetch('/games/available', {
                credentials: 'include'
            });
            
            if (response.ok) {
                const data = await response.json();
                this.displayGames(data.games);
            }
        } catch (error) {
            console.error('Failed to load games:', error);
        }
    }
    
    displayGames(games) {
        const container = document.getElementById('games-container');
        if (!container) return;
        
        container.innerHTML = '';
        
        games.forEach(game => {
            const gameCard = this.createGameCard(game);
            container.appendChild(gameCard);
        });
    }
    
    createGameCard(game) {
        const card = document.createElement('div');
        card.className = 'game-card';
        card.innerHTML = `
            <div class="game-image">
                <img src="${game.image_url || '/static/images/game-placeholder.jpg'}" alt="${game.title}">
            </div>
            <div class="game-content">
                <h3 class="game-title">${game.title}</h3>
                <div class="game-stats">
                    <span>RTP: ${game.rtp}%</span>
                    <span>Bet: $${game.min_bet} - $${game.max_bet}</span>
                </div>
                <p>${game.description || 'Exciting casino game'}</p>
                <div class="game-actions">
                    <input type="number" 
                           class="form-control bet-amount" 
                           placeholder="Bet amount" 
                           min="${game.min_bet}" 
                           max="${game.max_bet}"
                           value="${game.min_bet}">
                    <button class="btn btn-primary play-btn" data-game-id="${game.id}">
                        Play Now
                    </button>
                </div>
            </div>
        `;
        
        return card;
    }
    
    setupGameListeners() {
        // Делегирование событий для кнопок play
        document.addEventListener('click', (e) => {
            if (e.target.classList.contains('play-btn')) {
                const gameId = e.target.dataset.gameId;
                const amountInput = e.target.closest('.game-actions').querySelector('.bet-amount');
                const amount = parseFloat(amountInput.value);
                
                this.playGame(gameId, amount);
            }
        });
        
        // Валидация суммы ставки
        document.addEventListener('input', (e) => {
            if (e.target.classList.contains('bet-amount')) {
                const min = parseFloat(e.target.min);
                const max = parseFloat(e.target.max);
                let value = parseFloat(e.target.value);
                
                if (value < min) {
                    e.target.value = min;
                } else if (value > max) {
                    e.target.value = max;
                }
            }
        });
    }
    
    async playGame(gameId, amount) {
        const result = await window.casinoApp.playGame(gameId, amount);
        
        if (result) {
            // Обновление истории игр если на странице есть контейнер
            this.updateGameHistory();
        }
    }
    
    async updateGameHistory() {
        const container = document.getElementById('game-history');
        if (!container) return;
        
        try {
            const response = await fetch('/games/history', {
                credentials: 'include'
            });
            
            if (response.ok) {
                const data = await response.json();
                this.displayGameHistory(data.bets);
            }
        } catch (error) {
            console.error('Failed to load game history:', error);
        }
    }
    
    displayGameHistory(bets) {
        const container = document.getElementById('game-history');
        if (!container || !bets) return;
        
        container.innerHTML = '';
        
        if (bets.length === 0) {
            container.innerHTML = '<p class="text-muted">No games played yet</p>';
            return;
        }
        
        const table = document.createElement('table');
        table.className = 'table';
        table.innerHTML = `
            <thead>
                <tr>
                    <th>Game</th>
                    <th>Bet Amount</th>
                    <th>Result</th>
                    <th>Win Amount</th>
                    <th>Time</th>
                </tr>
            </thead>
            <tbody>
                ${bets.map(bet => `
                    <tr>
                        <td>${bet.game_title}</td>
                        <td>$${bet.amount.toFixed(2)}</td>
                        <td><span class="badge ${bet.result === 'win' ? 'badge-success' : 'badge-danger'}">${bet.result}</span></td>
                        <td>$${bet.win_amount.toFixed(2)}</td>
                        <td>${new Date(bet.timestamp).toLocaleString()}</td>
                    </tr>
                `).join('')}
            </tbody>
        `;
        
        container.appendChild(table);
    }
}

// Инициализация при загрузке страницы
document.addEventListener('DOMContentLoaded', () => {
    window.gameManager = new GameManager();
});