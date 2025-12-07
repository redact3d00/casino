// JavaScript для админ панели

class AdminDashboard {
    constructor() {
        this.init();
    }
    
    init() {
        if (!this.isAdminPage()) return;
        
        this.loadDashboardStats();
        this.setupEventListeners();
        this.setupRealTimeUpdates();
    }
    
    isAdminPage() {
        return window.location.pathname.includes('/admin');
    }
    
    async loadDashboardStats() {
        try {
            const response = await fetch('/admin/dashboard/stats', {
                credentials: 'include'
            });
            
            if (response.ok) {
                const data = await response.json();
                this.updateDashboard(data);
            }
        } catch (error) {
            console.error('Failed to load dashboard stats:', error);
        }
    }
    
    updateDashboard(data) {
        // Обновление статистики
        if (data.users) {
            document.getElementById('total-users')?.textContent = data.users.total;
            document.getElementById('new-users')?.textContent = data.users.new;
            document.getElementById('active-users')?.textContent = data.users.active;
        }
        
        if (data.financial) {
            document.getElementById('total-deposits')?.textContent = `$${data.financial.deposits.toFixed(2)}`;
            document.getElementById('total-withdrawals')?.textContent = `$${data.financial.withdrawals.toFixed(2)}`;
            document.getElementById('net-profit')?.textContent = `$${data.financial.net_profit.toFixed(2)}`;
        }
    }
    
    setupEventListeners() {
        // Загрузка пользователей
        document.getElementById('load-users')?.addEventListener('click', () => {
            this.loadUsers();
        });
        
        // Экспорт отчетов
        document.getElementById('export-report')?.addEventListener('click', () => {
            this.exportReport();
        });
        
        // Поиск пользователей
        document.getElementById('user-search')?.addEventListener('input', (e) => {
            this.searchUsers(e.target.value);
        });
    }
    
    async loadUsers(page = 1) {
        try {
            const response = await fetch(`/admin/users?page=${page}`, {
                credentials: 'include'
            });
            
            if (response.ok) {
                const data = await response.json();
                this.displayUsers(data.users);
                this.setupPagination(data);
            }
        } catch (error) {
            console.error('Failed to load users:', error);
        }
    }
    
    displayUsers(users) {
        const container = document.getElementById('users-container');
        if (!container) return;
        
        container.innerHTML = '';
        
        users.forEach(user => {
            const row = document.createElement('tr');
            row.innerHTML = `
                <td>${user.id}</td>
                <td>${user.username}</td>
                <td>${user.email}</td>
                <td><span class="badge badge-${user.status === 'active' ? 'success' : 'warning'}">${user.status}</span></td>
                <td>$${user.balance.toFixed(2)}</td>
                <td>
                    <button class="btn btn-sm btn-primary" onclick="adminDashboard.editUser(${user.id})">
                        Edit
                    </button>
                    <button class="btn btn-sm btn-info" onclick="adminDashboard.viewUser(${user.id})">
                        View
                    </button>
                </td>
            `;
            container.appendChild(row);
        });
    }
    
    setupPagination(data) {
        const pagination = document.getElementById('pagination');
        if (!pagination) return;
        
        pagination.innerHTML = '';
        
        for (let i = 1; i <= data.pages; i++) {
            const li = document.createElement('li');
            li.className = `page-item ${i === data.page ? 'active' : ''}`;
            li.innerHTML = `<a class="page-link" href="#" onclick="adminDashboard.loadUsers(${i})">${i}</a>`;
            pagination.appendChild(li);
        }
    }
    
    async searchUsers(query) {
        if (query.length < 2) return;
        
        try {
            const response = await fetch(`/admin/users?search=${encodeURIComponent(query)}`, {
                credentials: 'include'
            });
            
            if (response.ok) {
                const data = await response.json();
                this.displayUsers(data.users);
            }
        } catch (error) {
            console.error('Search error:', error);
        }
    }
    
    async exportReport() {
        const type = document.getElementById('report-type')?.value || 'users';
        const format = document.getElementById('report-format')?.value || 'csv';
        
        window.open(`/admin/reports/export?type=${type}&format=${format}`, '_blank');
    }
    
    editUser(userId) {
        window.location.href = `/admin/users/${userId}/edit`;
    }
    
    viewUser(userId) {
        window.location.href = `/admin/users/${userId}`;
    }
    
    setupRealTimeUpdates() {
        // Обновление статистики каждые 30 секунд
        setInterval(() => {
            this.loadDashboardStats();
        }, 30000);
    }
}

// Инициализация при загрузке страницы
document.addEventListener('DOMContentLoaded', () => {
    window.adminDashboard = new AdminDashboard();
});