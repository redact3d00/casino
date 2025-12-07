// Основные функции JavaScript для Casino

class CasinoApp {
    constructor() {
        this.csrfToken = this.getCsrfToken();
        this.init();
    }
    
    init() {
        this.setupEventListeners();
        this.checkAuthStatus();
        this.setupAjax();
    }
    
    getCsrfToken() {
        const meta = document.querySelector('meta[name="csrf-token"]');
        return meta ? meta.content : '';
    }
    
    setupEventListeners() {
        // Формы с AJAX
        document.querySelectorAll('form[data-ajax]').forEach(form => {
            form.addEventListener('submit', (e) => this.handleAjaxForm(e));
        });
        
        // Кнопки с подтверждением
        document.querySelectorAll('[data-confirm]').forEach(button => {
            button.addEventListener('click', (e) => {
                if (!confirm(e.target.dataset.confirm)) {
                    e.preventDefault();
                }
            });
        });
        
        // Кнопки выхода
        document.querySelectorAll('[data-logout]').forEach(button => {
            button.addEventListener('click', (e) => {
                e.preventDefault();
                this.logout();
            });
        });
    }
    
    checkAuthStatus() {
        fetch('/auth/status')
            .then(response => response.json())
            .then(data => {
                if (data.authenticated) {
                    this.updateUIForAuthUser(data.user);
                } else {
                    this.updateUIForGuest();
                }
            })
            .catch(error => console.error('Auth check failed:', error));
    }
    
    updateUIForAuthUser(user) {
        // Обновить UI для авторизованного пользователя
        document.querySelectorAll('[data-auth]').forEach(el => {
            el.style.display = '';
        });
        document.querySelectorAll('[data-guest]').forEach(el => {
            el.style.display = 'none';
        });
        
        // Обновить информацию о пользователе
        if (user.balance !== undefined) {
            const balanceEls = document.querySelectorAll('[data-user-balance]');
            balanceEls.forEach(el => {
                el.textContent = `$${user.balance.toFixed(2)}`;
            });
        }
    }
    
    updateUIForGuest() {
        document.querySelectorAll('[data-auth]').forEach(el => {
            el.style.display = 'none';
        });
        document.querySelectorAll('[data-guest]').forEach(el => {
            el.style.display = '';
        });
    }
    
    async handleAjaxForm(event) {
        event.preventDefault();
        
        const form = event.target;
        const formData = new FormData(form);
        const url = form.action;
        const method = form.method || 'POST';
        
        try {
            const response = await fetch(url, {
                method: method,
                body: JSON.stringify(Object.fromEntries(formData)),
                headers: {
                    'Content-Type': 'application/json'
                },
                credentials: 'include'
            });
            
            const result = await response.json();
            
            if (response.ok) {
                this.showAlert(result.message || 'Success!', 'success');
                
                // Обновление баланса если есть
                if (result.new_balance !== undefined) {
                    this.updateBalance(result.new_balance);
                }
                
                // Редирект если указан
                if (result.redirect) {
                    setTimeout(() => {
                        window.location.href = result.redirect;
                    }, 1500);
                }
            } else {
                this.showAlert(result.error || 'Error occurred', 'error');
            }
            
        } catch (error) {
            console.error('Form submission error:', error);
            this.showAlert('Network error occurred', 'error');
        }
    }
    
    setupAjax() {
        // Установка CSRF токена для всех AJAX запросов
        if (window.jQuery) {
            $.ajaxSetup({
                headers: {
                    'X-CSRF-Token': this.csrfToken
                }
            });
        }
    }
    
    showAlert(message, type = 'info') {
        const alert = document.createElement('div');
        alert.className = `alert alert-${type}`;
        alert.textContent = message;
        
        const container = document.querySelector('.alerts') || document.querySelector('main .container');
        if (container) {
            container.prepend(alert);
            
            // Автоудаление через 5 секунд
            setTimeout(() => {
                alert.remove();
            }, 5000);
        }
    }
    
    updateBalance(newBalance) {
        document.querySelectorAll('[data-user-balance]').forEach(el => {
            el.textContent = `$${parseFloat(newBalance).toFixed(2)}`;
        });
    }
    
    async logout() {
        try {
            const response = await fetch('/auth/logout', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                credentials: 'include'
            });
            
            if (response.ok) {
                window.location.href = '/';
            }
        } catch (error) {
            console.error('Logout error:', error);
            this.showAlert('Logout failed', 'error');
        }
    }
    
    // Игровые функции
    async playGame(gameId, amount) {
        try {
            const response = await fetch(`/games/${gameId}/play`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({ amount: amount }),
                credentials: 'include'
            });
            
            const result = await response.json();
            
            if (response.ok) {
                this.showAlert(`Result: ${result.result.toUpperCase()}! Win: $${result.win_amount}`, 'success');
                this.updateBalance(result.new_balance);
                
                // Анимация выигрыша
                if (result.result === 'win') {
                    this.animateWin(result.win_amount);
                }
                
                return result;
            } else {
                this.showAlert(result.error, 'error');
                return null;
            }
            
        } catch (error) {
            console.error('Game play error:', error);
            this.showAlert('Game play failed', 'error');
            return null;
        }
    }
    
    animateWin(amount) {
        const winPopup = document.createElement('div');
        winPopup.className = 'win-popup';
        winPopup.innerHTML = `
            <div class="win-content">
                <h3>🎉 YOU WIN! 🎉</h3>
                <div class="win-amount">$${amount.toFixed(2)}</div>
            </div>
        `;
        
        document.body.appendChild(winPopup);
        
        setTimeout(() => {
            winPopup.remove();
        }, 3000);
    }
}

// Инициализация при загрузке страницы
document.addEventListener('DOMContentLoaded', () => {
    window.casinoApp = new CasinoApp();
    
    // Стили для всплывающего окна выигрыша
    const style = document.createElement('style');
    style.textContent = `
        .win-popup {
            position: fixed;
            top: 50%;
            left: 50%;
            transform: translate(-50%, -50%);
            background: linear-gradient(135deg, #ffd700, #ff8c00);
            color: #000;
            padding: 2rem;
            border-radius: 15px;
            z-index: 10000;
            animation: winPopup 0.5s ease-out;
            box-shadow: 0 0 50px rgba(255, 215, 0, 0.5);
        }
        
        @keyframes winPopup {
            0% { transform: translate(-50%, -50%) scale(0); opacity: 0; }
            70% { transform: translate(-50%, -50%) scale(1.1); }
            100% { transform: translate(-50%, -50%) scale(1); opacity: 1; }
        }
        
        .win-content {
            text-align: center;
        }
        
        .win-amount {
            font-size: 3rem;
            font-weight: bold;
            margin: 1rem 0;
            animation: pulse 1s infinite;
        }
        
        @keyframes pulse {
            0% { transform: scale(1); }
            50% { transform: scale(1.1); }
            100% { transform: scale(1); }
        }
    `;
    document.head.appendChild(style);
});