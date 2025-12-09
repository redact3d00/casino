class AuthManager {
    constructor() {
        this.init();
    }

    init() {
        this.setupLoginForm();
        this.setupRegisterForm();
    }

    getCsrfToken() {
        const meta = document.querySelector('meta[name="csrf-token"]');
        if (meta) return meta.getAttribute('content');

        const input = document.querySelector('input[name="csrf_token"]');
        if (input) return input.value;

        const match = document.cookie.match(/csrf_token=([^;]+)/);
        return match ? match[1] : '';
    }

    async sendAuthRequest(url, data) {
        const token = this.getCsrfToken();
        if (!token) {
            this.showAlert('CSRF token not found!', 'error');
            return null;
        }

        try {
            const response = await fetch(url, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'X-CSRFToken': token  
                },
                body: JSON.stringify(data),
                credentials: 'include'
            });

            const result = await response.json();
            if (response.ok) {
                return result;
            } else {
                this.showAlert(result.error || 'Server error', 'error');
                return null;
            }
        } catch (err) {
            console.error(err);
            this.showAlert('Network error', 'error');
            return null;
        }
    }

    setupRegisterForm() {
        const form = document.getElementById('register-form');
        if (!form) return;

        form.addEventListener('submit', async (e) => {
            e.preventDefault();

            const username = document.getElementById('reg-username').value.trim();
            const email = document.getElementById('reg-email').value.trim();
            const password = document.getElementById('reg-password').value;
            const confirm = document.getElementById('reg-confirm-password').value;

            if (password !== confirm) {
                this.showAlert('Пароли не совпадают!', 'error');
                return;
            }

            const result = await this.sendAuthRequest('/api/auth/register', {
                username, email, password
            });

            if (result) {
                this.showAlert('Регистрация успешна! Перенаправляем...', 'success');
                setTimeout(() => {
                    window.location.href = result.redirect || '/dashboard';
                }, 1000);
            }
        });
    }

    setupLoginForm() {
        const form = document.getElementById('login-form');
        if (!form) return;

        form.addEventListener('submit', async (e) => {
            e.preventDefault();

            const username = document.getElementById('username').value.trim();
            const password = document.getElementById('password').value;

            const result = await this.sendAuthRequest('/api/auth/login', {
                username, password
            });

            if (result) {
                this.showAlert('Вход успешен! Перенаправляем...', 'success');
                setTimeout(() => {
                    window.location.href = result.redirect || '/dashboard';
                }, 1000);
            }
        });
    }

    showAlert(message, type = 'info') {
        const alert = document.createElement('div');
        alert.className = `alert alert-${type}`;
        alert.textContent = message;
        alert.style.cssText = `
            position: fixed; top: 20px; left: 50%; transform: translateX(-50%);
            z-index: 9999; padding: 15px 30px; border-radius: 8px; color: white;
            background: ${type === 'error' ? '#dc3545' : '#28a745'};
            box-shadow: 0 4px 12px rgba(0,0,0,0.3);
        `;
        document.body.appendChild(alert);
        setTimeout(() => alert.remove(), 4000);
    }
}

document.addEventListener('DOMContentLoaded', () => {
    window.authManager = new AuthManager();
});