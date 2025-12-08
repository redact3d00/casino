class AuthManager {
    constructor() {
        this.init();
    }
    
    init() {
        this.setupLoginForm();
        this.setupRegisterForm();
    }
    
    setupLoginForm() {
        const form = document.getElementById('login-form');
        if (!form) return;
        
        form.addEventListener('submit', async (e) => {
            e.preventDefault();
            
            const username = document.getElementById('username').value;
            const password = document.getElementById('password').value;
            
            try {
                const response = await fetch('/api/auth/login', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json'
                    },
                    body: JSON.stringify({ username, password }),
                    credentials: 'include' 
                });
                
                const result = await response.json();
                
                if (response.ok) {
                    this.showAlert('Login successful! Redirecting...', 'success');
                    
                    setTimeout(() => {
                        window.location.href = result.redirect || '/dashboard';
                    }, 1000);
                } else {
                    this.showAlert(result.error || 'Login failed', 'error');
                }
            } catch (error) {
                console.error('Login error:', error);
                this.showAlert('Network error occurred', 'error');
            }
        });
    }
    
    setupRegisterForm() {
        const form = document.getElementById('register-form');
        if (!form) return;
        
        form.addEventListener('submit', async (e) => {
            e.preventDefault();
            
            const username = document.getElementById('reg-username').value;
            const email = document.getElementById('reg-email').value;
            const password = document.getElementById('reg-password').value;
            const confirmPassword = document.getElementById('reg-confirm-password').value;
            
            if (password !== confirmPassword) {
                this.showAlert('Passwords do not match', 'error');
                return;
            }
            
            if (password.length < 8) {
                this.showAlert('Password must be at least 8 characters', 'error');
                return;
            }
            
            const hasUpperCase = /[A-Z]/.test(password);
            const hasLowerCase = /[a-z]/.test(password);
            const hasNumbers = /\d/.test(password);
            const hasSpecialChar = /[!@#$%^&*(),.?":{}|<>]/.test(password);
            
            if (!hasUpperCase || !hasLowerCase || !hasNumbers || !hasSpecialChar) {
                this.showAlert('Password must contain uppercase, lowercase, number and special character', 'error');
                return;
            }
            
            try {
                const response = await fetch('/api/auth/register', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json'
                    },
                    body: JSON.stringify({ username, email, password }),
                    credentials: 'include'
                });
                
                const result = await response.json();
                
                if (response.ok) {
                    this.showAlert('Registration successful! Redirecting...', 'success');
                    
                    setTimeout(() => {
                        window.location.href = result.redirect || '/dashboard';
                    }, 1500);
                } else {
                    this.showAlert(result.error || 'Registration failed', 'error');
                }
            } catch (error) {
                console.error('Registration error:', error);
                this.showAlert('Network error occurred', 'error');
            }
        });
    }
    
    showAlert(message, type = 'info') {
        if (window.casinoApp && window.casinoApp.showAlert) {
            window.casinoApp.showAlert(message, type);
            return;
        }
        
        const alert = document.createElement('div');
        alert.className = `alert alert-${type}`;
        alert.textContent = message;
        alert.style.cssText = `
            padding: 1rem;
            margin: 1rem 0;
            border-radius: 5px;
            color: white;
            background: ${type === 'error' ? '#dc3545' : type === 'success' ? '#28a745' : '#17a2b8'};
        `;
        
        const container = document.querySelector('.alerts') || document.querySelector('main') || document.body;
        container.prepend(alert);
        
        setTimeout(() => {
            alert.remove();
        }, 5000);
    }
}

document.addEventListener('DOMContentLoaded', () => {
    window.authManager = new AuthManager();
});