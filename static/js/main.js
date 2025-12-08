class CasinoApp {
    constructor() {
        this.currentUser = null;
        this.currentGame = null;
        this.slotMachine = null;
        this.init();
    }
    
    async init() {
        await this.checkAuth();
        
        this.initComponents();
        
        if (window.location.pathname.includes('/games') || 
            window.location.pathname === '/dashboard') {
            await this.loadGames();
        }
        
        if (this.currentUser) {
            await this.loadUserStats();
        }
        
        this.setupEventListeners();
        
        console.log('Casino App initialized');
    }
    
    async checkAuth() {
        try {
            const response = await fetch('/api/auth/status', {
                credentials: 'include'
            });
            
            if (response.ok) {
                const data = await response.json();
                if (data.authenticated) {
                    this.currentUser = data.user;
                    this.updateUIForLoggedInUser();
                } else {
                    this.updateUIForGuest();
                }
            }
        } catch (error) {
            console.error('Auth check failed:', error);
            this.updateUIForGuest();
        }
    }
    
    updateUIForLoggedInUser() {
        const balanceElements = document.querySelectorAll('[data-user-balance]');
        balanceElements.forEach(el => {
            el.textContent = `$${this.currentUser.balance.toFixed(2)}`;
        });
        
        document.querySelectorAll('.user-only').forEach(el => {
            el.style.display = 'block';
        });
        
        document.querySelectorAll('.guest-only').forEach(el => {
            el.style.display = 'none';
        });
        
        document.querySelectorAll('[data-username]').forEach(el => {
            el.textContent = this.currentUser.username;
        });
    }
    
    updateUIForGuest() {
        document.querySelectorAll('.user-only').forEach(el => {
            el.style.display = 'none';
        });
        
        document.querySelectorAll('.guest-only').forEach(el => {
            el.style.display = 'block';
        });
    }
    
    initComponents() {
        const slotContainer = document.getElementById('slot-machine');
        if (slotContainer) {
            this.slotMachine = new SlotMachine('slot-machine', {
                reels: 5,
                rows: 3,
                duration: 2000
            });
        }
        
        this.initChart();
    }
    
    async loadGames() {
        try {
            const response = await fetch('/api/games/available', {
                credentials: 'include'
            });
            
            if (response.ok) {
                const data = await response.json();
                this.displayGames(data.games);
            }
        } catch (error) {
            console.error('Failed to load games:', error);
            this.showAlert('Failed to load games', 'error');
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
                ${game.image_url ? 
                    `<img src="${game.image_url}" alt="${game.title}" onerror="this.src='/static/images/game-placeholder.jpg'">` : 
                    `<div class="game-image-placeholder">${game.category.charAt(0).toUpperCase()}</div>`
                }
                ${game.has_bonus ? '<span class="game-bonus-badge">🎁 BONUS</span>' : ''}
                ${game.jackpot > 0 ? `<span class="game-jackpot-badge">💰 $${game.jackpot.toFixed(2)}</span>` : ''}
            </div>
            <div class="game-content">
                <h3 class="game-title">${game.title}</h3>
                <div class="game-stats">
                    <span class="game-rtp" title="Return to Player">
                        <i class="fas fa-chart-line"></i> ${game.rtp}% RTP
                    </span>
                    <span class="game-bet-range">
                        <i class="fas fa-coins"></i> $${game.min_bet} - $${game.max_bet}
                    </span>
                    <span class="game-volatility">
                        <i class="fas fa-bolt"></i> ${game.volatility}
                    </span>
                </div>
                <p class="game-description">${game.description || 'Exciting casino game with fair play'}</p>
                <div class="game-provider">
                    <small>By ${game.provider || 'Beavers Gaming'}</small>
                </div>
                <div class="game-actions">
                    <div class="bet-input-group">
                        <input type="number" 
                               class="form-control bet-amount" 
                               placeholder="Bet amount" 
                               min="${game.min_bet}" 
                               max="${game.max_bet}"
                               value="${game.min_bet}"
                               step="0.10">
                        <div class="bet-buttons">
                            <button class="btn btn-sm bet-half">½</button>
                            <button class="btn btn-sm bet-double">2×</button>
                            <button class="btn btn-sm bet-max">MAX</button>
                        </div>
                    </div>
                    <button class="btn btn-primary play-btn" data-game-id="${game.id}">
                        <i class="fas fa-play"></i> Play Now
                    </button>
                    ${game.category === 'slots' ? 
                        `<button class="btn btn-info demo-btn" data-game-id="${game.id}">
                            <i class="fas fa-eye"></i> Demo
                        </button>` : ''
                    }
                </div>
            </div>
        `;
        
        return card;
    }
    
    async loadUserStats() {
        try {
            const response = await fetch('/api/user/profile', {
                credentials: 'include'
            });
            
            if (response.ok) {
                const data = await response.json();
                this.updateUserStats(data);
            }
        } catch (error) {
            console.error('Failed to load user stats:', error);
        }
    }
    
    updateUserStats(stats) {
        const statsElements = {
            'total-bets': stats.total_bets || 0,
            'total-wins': stats.total_wins || 0,
            'total-deposits': stats.total_deposits || 0,
            'total-withdrawals': stats.total_withdrawals || 0,
            'win-rate': stats.win_rate || 0,
            'net-profit': stats.net_profit || 0
        };
        
        Object.entries(statsElements).forEach(([id, value]) => {
            const element = document.getElementById(id);
            if (element) {
                if (id.includes('profit')) {
                    element.textContent = value >= 0 ? `+$${value.toFixed(2)}` : `-$${Math.abs(value).toFixed(2)}`;
                    element.className = value >= 0 ? 'text-success' : 'text-danger';
                } else if (id.includes('rate')) {
                    element.textContent = `${value}%`;
                } else if (typeof value === 'number') {
                    element.textContent = `$${value.toFixed(2)}`;
                }
            }
        });
    }
    
    async playGame(gameId, betAmount) {
        if (!this.currentUser) {
            this.showAlert('Please login to play games', 'error');
            return false;
        }
        
        if (!betAmount || betAmount <= 0) {
            this.showAlert('Please enter a valid bet amount', 'error');
            return false;
        }
        
        try {
            const response = await fetch(`/api/games/${gameId}/play`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({ amount: betAmount }),
                credentials: 'include'
            });
            
            const result = await response.json();
            
            if (response.ok) {
                this.currentUser.balance = result.new_balance;
                this.updateUIForLoggedInUser();
                
                this.showGameResult(result);
                
                if (result.game_data?.game_type === 'slots' && this.slotMachine) {
                    await this.animateSlotResult(result);
                }
                
                return result;
            } else {
                this.showAlert(result.error || 'Failed to play game', 'error');
                return false;
            }
        } catch (error) {
            console.error('Game play error:', error);
            this.showAlert('Network error occurred', 'error');
            return false;
        }
    }
    
    async animateSlotResult(gameResult) {
        if (!this.slotMachine) return;
        
        const slotSymbols = [
            { icon: '🍒', name: 'Cherry', value: 2 },
            { icon: '🍋', name: 'Lemon', value: 3 },
            { icon: '🍊', name: 'Orange', value: 4 },
            { icon: '🍇', name: 'Grape', value: 5 },
            { icon: '💎', name: 'Diamond', value: 10 },
            { icon: '7️⃣', name: 'Seven', value: 20 },
            { icon: '🔔', name: 'Bell', value: 15 },
            { icon: '⭐', name: 'Star', value: 12 },
            { icon: '💰', name: 'Money Bag', value: 25 },
            { icon: '👑', name: 'Crown', value: 50 }
        ];
        
        const result = [];
        const multiplier = gameResult.multiplier || 1;
        
        if (gameResult.result === 'win') {
            const winSymbol = slotSymbols[Math.floor(Math.random() * slotSymbols.length)];
            for (let i = 0; i < 5; i++) {
                if (multiplier >= 10 && i < 3) {
                    result.push(winSymbol);
                } else if (multiplier >= 5 && i < 2) {
                    result.push(winSymbol); 
                } else {
                    result.push(slotSymbols[Math.floor(Math.random() * slotSymbols.length)]);
                }
            }
        } else {
            for (let i = 0; i < 5; i++) {
                result.push(slotSymbols[Math.floor(Math.random() * slotSymbols.length)]);
            }
        }
        
        const spinResult = await this.slotMachine.spin(result);
        
        if (gameResult.result === 'win') {
            this.showAlert(`🎉 You won $${gameResult.win_amount.toFixed(2)}! (x${gameResult.multiplier})`, 'success');
        } else {
            this.showAlert('💔 No win this time. Try again!', 'info');
        }
    }
    
    showGameResult(result) {
        const modal = document.createElement('div');
        modal.className = 'game-result-modal';
        modal.innerHTML = `
            <div class="modal-content">
                <div class="modal-header">
                    <h3>${result.result === 'win' ? '🎉 You Won!' : '💔 No Win'}</h3>
                    <button class="close-btn">&times;</button>
                </div>
                <div class="modal-body">
                    <div class="result-details">
                        <div class="result-item">
                            <span>Bet Amount:</span>
                            <strong>$${result.bet_amount.toFixed(2)}</strong>
                        </div>
                        ${result.result === 'win' ? `
                            <div class="result-item">
                                <span>Win Amount:</span>
                                <strong class="text-success">$${result.win_amount.toFixed(2)}</strong>
                            </div>
                            <div class="result-item">
                                <span>Multiplier:</span>
                                <strong class="text-warning">x${result.multiplier}</strong>
                            </div>
                        ` : ''}
                        <div class="result-item">
                            <span>New Balance:</span>
                            <strong>$${result.new_balance.toFixed(2)}</strong>
                        </div>
                    </div>
                    <div class="game-info">
                        <small>Game: ${result.game_title || 'Unknown'}</small>
                        <small>Time: ${new Date(result.timestamp).toLocaleTimeString()}</small>
                    </div>
                </div>
                <div class="modal-footer">
                    <button class="btn btn-primary" id="play-again-btn">Play Again</button>
                    <button class="btn btn-secondary" id="close-result-btn">Close</button>
                </div>
            </div>
        `;
        
        document.body.appendChild(modal);
        
        modal.querySelector('.close-btn').addEventListener('click', () => {
            modal.remove();
        });
        
        modal.querySelector('#close-result-btn').addEventListener('click', () => {
            modal.remove();
        });
        
        modal.querySelector('#play-again-btn').addEventListener('click', () => {
            modal.remove();
        });
        
        setTimeout(() => {
            if (document.body.contains(modal)) {
                modal.remove();
            }
        }, 5000);
    }
    
    initChart() {
        const chartCanvas = document.getElementById('profit-chart');
        if (!chartCanvas) return;
        
        const ctx = chartCanvas.getContext('2d');
        
        const data = {
            labels: ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun'],
            datasets: [{
                label: 'Daily Profit',
                data: [120, 190, 300, 250, 200, 350, 400],
                borderColor: '#ffd700',
                backgroundColor: 'rgba(255, 215, 0, 0.1)',
                tension: 0.4,
                fill: true
            }]
        };
        
        const config = {
            type: 'line',
            data: data,
            options: {
                responsive: true,
                plugins: {
                    legend: {
                        display: false
                    },
                    tooltip: {
                        callbacks: {
                            label: function(context) {
                                return `Profit: $${context.parsed.y}`;
                            }
                        }
                    }
                },
                scales: {
                    y: {
                        beginAtZero: true,
                        grid: {
                            color: 'rgba(255, 255, 255, 0.1)'
                        },
                        ticks: {
                            color: '#ccc',
                            callback: function(value) {
                                return '$' + value;
                            }
                        }
                    },
                    x: {
                        grid: {
                            color: 'rgba(255, 255, 255, 0.1)'
                        },
                        ticks: {
                            color: '#ccc'
                        }
                    }
                }
            }
        };
        
        new Chart(ctx, config);
    }
    
    setupEventListeners() {
        document.addEventListener('click', async (e) => {
            if (e.target.closest('.play-btn')) {
                const gameId = e.target.closest('.play-btn').dataset.gameId;
                const card = e.target.closest('.game-card');
                const amountInput = card?.querySelector('.bet-amount');
                const amount = amountInput ? parseFloat(amountInput.value) : 1;
                
                await this.playGame(gameId, amount);
            }
            
            if (e.target.closest('.demo-btn')) {
                const gameId = e.target.closest('.demo-btn').dataset.gameId;
                await this.playDemo(gameId);
            }
            
            if (e.target.closest('.bet-half')) {
                const input = e.target.closest('.bet-input-group').querySelector('.bet-amount');
                input.value = (parseFloat(input.value) / 2).toFixed(2);
            }
            
            if (e.target.closest('.bet-double')) {
                const input = e.target.closest('.bet-input-group').querySelector('.bet-amount');
                input.value = (parseFloat(input.value) * 2).toFixed(2);
            }
            
            if (e.target.closest('.bet-max')) {
                const card = e.target.closest('.game-card');
                const input = card.querySelector('.bet-amount');
                const maxBet = parseFloat(input.max);
                input.value = maxBet.toFixed(2);
            }
            
            if (e.target.closest('[data-logout]')) {
                e.preventDefault();
                await this.logout();
            }
        });
        
        document.addEventListener('input', (e) => {
            if (e.target.classList.contains('bet-amount')) {
                const min = parseFloat(e.target.min);
                const max = parseFloat(e.target.max);
                let value = parseFloat(e.target.value) || min;
                
                if (value < min) {
                    e.target.value = min;
                } else if (value > max) {
                    e.target.value = max;
                } else if (isNaN(value)) {
                    e.target.value = min;
                }
            }
        });
        
        this.setupBalanceUpdates();
    }
    
    async playDemo(gameId) {
        // на всякий оставлю
        this.showAlert('🎮 Starting demo mode...', 'info');
        
    }
    
    async logout() {
        try {
            const response = await fetch('/api/auth/logout', {
                method: 'POST',
                credentials: 'include'
            });
            
            if (response.ok) {
                this.currentUser = null;
                this.updateUIForGuest();
                window.location.href = '/';
            }
        } catch (error) {
            console.error('Logout error:', error);
            this.showAlert('Logout failed', 'error');
        }
    }
    
    setupBalanceUpdates() {
        setInterval(async () => {
            if (this.currentUser) {
                await this.checkAuth();
            }
        }, 30000); 
    }
    
    showAlert(message, type = 'info') {
        const alert = document.createElement('div');
        alert.className = `alert alert-${type} alert-dismissible fade show`;
        alert.innerHTML = `
            ${this.getAlertIcon(type)} ${message}
            <button type="button" class="btn-close" data-bs-dismiss="alert"></button>
        `;
        
        const container = document.querySelector('.alerts') || document.querySelector('main');
        if (container) {
            container.prepend(alert);
            
            setTimeout(() => {
                if (document.body.contains(alert)) {
                    alert.remove();
                }
            }, 5000);
        }
    }
    
    getAlertIcon(type) {
        const icons = {
            'success': '✅',
            'error': '❌',
            'warning': '⚠️',
            'info': 'ℹ️'
        };
        return icons[type] || 'ℹ️';
    }
}

document.addEventListener('DOMContentLoaded', () => {
    window.casinoApp = new CasinoApp();
});

function formatCurrency(amount) {
    return new Intl.NumberFormat('en-US', {
        style: 'currency',
        currency: 'USD',
        minimumFractionDigits: 2
    }).format(amount);
}

function formatDate(dateString) {
    const date = new Date(dateString);
    return date.toLocaleDateString() + ' ' + date.toLocaleTimeString();
}

if (typeof module !== 'undefined' && module.exports) {
    module.exports = { CasinoApp, formatCurrency, formatDate };
}