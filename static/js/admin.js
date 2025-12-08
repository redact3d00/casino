class SupportDashboard {
    constructor() {
        this.init();
    }
    
    init() {
        if (!this.isSupportPage()) return;
        
        this.loadSupportDashboard();
        this.setupSupportEventListeners();
        this.setupSupportRealTimeUpdates();
    }
    
    isSupportPage() {
        return window.location.pathname.includes('/admin/support');
    }
    
    async loadSupportDashboard() {
        try {
            const response = await fetch('/api/admin/support/dashboard', {
                credentials: 'include'
            });
            
            if (response.ok) {
                const data = await response.json();
                this.updateSupportDashboard(data);
            }
        } catch (error) {
            console.error('Failed to load support dashboard:', error);
        }
    }
    
    updateSupportDashboard(data) {
        if (data.stats) {
            this.updateStatElement('total-tickets', data.stats.total_tickets);
            this.updateStatElement('open-tickets', data.stats.open_tickets);
            this.updateStatElement('my-tickets', data.stats.my_tickets);
        }
        
        if (data.recent_tickets) {
            this.displayRecentTickets(data.recent_tickets);
        }
    }
    
    updateStatElement(elementId, value) {
        const element = document.getElementById(elementId);
        if (element) {
            element.textContent = value;
            element.classList.add('stat-update');
            setTimeout(() => {
                element.classList.remove('stat-update');
            }, 500);
        }
    }
    
    displayRecentTickets(tickets) {
        const container = document.getElementById('recent-tickets-table');
        if (!container) return;
        
        if (tickets.length === 0) {
            container.innerHTML = '<tr><td colspan="7" class="text-center">No recent tickets</td></tr>';
            return;
        }
        
        let html = '';
        tickets.forEach(ticket => {
            html += `
                <tr>
                    <td>#${ticket.id}</td>
                    <td><strong>${ticket.subject}</strong></td>
                    <td>${ticket.username}</td>
                    <td><span class="badge ${this.getStatusBadgeClass(ticket.status)}">${ticket.status}</span></td>
                    <td><span class="badge ${this.getPriorityBadgeClass(ticket.priority)}">${ticket.priority}</span></td>
                    <td>${this.formatTimeAgo(ticket.updated_at)}</td>
                    <td>
                        <button class="btn btn-sm btn-primary" onclick="supportDashboard.viewTicket(${ticket.id})">
                            <i class="fas fa-eye"></i>
                        </button>
                        ${ticket.assigned_to_me ? '' : `
                            <button class="btn btn-sm btn-success" onclick="supportDashboard.assignToMe(${ticket.id})">
                                <i class="fas fa-user-plus"></i>
                            </button>
                        `}
                    </td>
                </tr>
            `;
        });
        
        container.innerHTML = html;
    }
    
    getStatusBadgeClass(status) {
        switch(status) {
            case 'open': return 'bg-warning';
            case 'in_progress': return 'bg-info';
            case 'closed': return 'bg-success';
            default: return 'bg-secondary';
        }
    }
    
    getPriorityBadgeClass(priority) {
        switch(priority) {
            case 'low': return 'bg-success';
            case 'medium': return 'bg-warning';
            case 'high': return 'bg-danger';
            case 'urgent': return 'bg-dark';
            default: return 'bg-secondary';
        }
    }
    
    formatTimeAgo(dateString) {
        const date = new Date(dateString);
        const now = new Date();
        const diff = now - date;
        
        if (diff < 60000) return 'Just now';
        if (diff < 3600000) return `${Math.floor(diff / 60000)}m ago`;
        if (diff < 86400000) return `${Math.floor(diff / 3600000)}h ago`;
        return date.toLocaleDateString();
    }
    
    async assignToMe(ticketId) {
        try {
            const response = await fetch('/api/admin/support/tickets/assign', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({ ticket_id: ticketId }),
                credentials: 'include'
            });
            
            if (response.ok) {
                this.showAlert('Ticket assigned to you', 'success');
                this.loadSupportDashboard();
            } else {
                const error = await response.json();
                this.showAlert(error.error, 'error');
            }
        } catch (error) {
            console.error('Assign error:', error);
            this.showAlert('Failed to assign ticket', 'error');
        }
    }
    
    viewTicket(ticketId) {
        window.location.href = `/admin/support/tickets/${ticketId}`;
    }
    
    setupSupportEventListeners() {
        document.getElementById('quick-reply-btn')?.addEventListener('click', () => {
            this.showQuickReplyModal();
        });
        
        document.getElementById('bulk-assign-btn')?.addEventListener('click', () => {
            this.bulkAssignTickets();
        });
        
        document.querySelectorAll('.quick-template').forEach(btn => {
            btn.addEventListener('click', (e) => {
                const template = e.target.dataset.template;
                this.useQuickTemplate(template);
            });
        });
    }
    
    showQuickReplyModal() {
        const modal = document.createElement('div');
        modal.className = 'modal fade';
        modal.id = 'quickReplyModal';
        modal.innerHTML = `
            <div class="modal-dialog">
                <div class="modal-content">
                    <div class="modal-header">
                        <h5 class="modal-title">Quick Reply</h5>
                        <button type="button" class="btn-close" data-bs-dismiss="modal"></button>
                    </div>
                    <div class="modal-body">
                        <form id="quick-reply-form">
                            <div class="mb-3">
                                <label class="form-label">Ticket ID</label>
                                <input type="number" id="quick-ticket-id" class="form-control" required>
                            </div>
                            <div class="mb-3">
                                <label class="form-label">Template</label>
                                <select id="quick-template" class="form-control">
                                    <option value="">Custom Message</option>
                                    <option value="welcome">Welcome</option>
                                    <option value="deposit">Deposit Issue</option>
                                    <option value="withdrawal">Withdrawal</option>
                                    <option value="kyc">KYC</option>
                                    <option value="close">Close Ticket</option>
                                </select>
                            </div>
                            <div class="mb-3">
                                <label class="form-label">Message</label>
                                <textarea id="quick-message" class="form-control" rows="4" required></textarea>
                            </div>
                        </form>
                    </div>
                    <div class="modal-footer">
                        <button type="button" class="btn btn-secondary" data-bs-dismiss="modal">Cancel</button>
                        <button type="button" class="btn btn-primary" id="send-quick-reply">Send</button>
                    </div>
                </div>
            </div>
        `;
        
        document.body.appendChild(modal);
        
        const modalInstance = new bootstrap.Modal(modal);
        modalInstance.show();
        
        document.getElementById('send-quick-reply').addEventListener('click', async () => {
            await this.sendQuickReply();
            modalInstance.hide();
            modal.remove();
        });
        
        modal.addEventListener('hidden.bs.modal', () => {
            modal.remove();
        });
    }
    
    async sendQuickReply() {
        const ticketId = document.getElementById('quick-ticket-id').value;
        const template = document.getElementById('quick-template').value;
        const message = document.getElementById('quick-message').value;
        
        if (!ticketId || !message) {
            this.showAlert('Ticket ID and message are required', 'error');
            return;
        }
        
        try {
            const response = await fetch(`/api/admin/support/tickets/${ticketId}/quick-reply`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({
                    template: template || undefined,
                    custom_message: template ? undefined : message
                }),
                credentials: 'include'
            });
            
            if (response.ok) {
                this.showAlert('Reply sent successfully', 'success');
            } else {
                const error = await response.json();
                this.showAlert(error.error, 'error');
            }
        } catch (error) {
            console.error('Quick reply error:', error);
            this.showAlert('Failed to send reply', 'error');
        }
    }
    
    useQuickTemplate(template) {
        const templates = {
            'welcome': 'Hello! Thank you for contacting support. How can I help you today?',
            'deposit': 'Regarding your deposit: please ensure you are using one of our supported payment methods. Deposits are usually instant.',
            'withdrawal': 'Regarding your withdrawal: withdrawals are processed within 1-3 business days after KYC verification.',
            'kyc': 'To complete KYC verification, please upload your documents in the KYC section of your profile.',
            'close': 'Thank you for contacting us. If you have any further questions, please don\'t hesitate to create a new ticket.'
        };
        
        if (templates[template]) {
            document.getElementById('quick-message').value = templates[template];
        }
    }
    
    async bulkAssignTickets() {
        if (!confirm('Assign all unassigned tickets to yourself?')) return;
        
        try {
            const response = await fetch('/api/admin/support/tickets/bulk-action', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({
                    action: 'assign_to_me',
                    ticket_ids: [] 
                }),
                credentials: 'include'
            });
            
            if (response.ok) {
                const data = await response.json();
                this.showAlert(`Assigned ${data.updated_count} tickets to you`, 'success');
                this.loadSupportDashboard();
            } else {
                const error = await response.json();
                this.showAlert(error.error, 'error');
            }
        } catch (error) {
            console.error('Bulk assign error:', error);
            this.showAlert('Failed to assign tickets', 'error');
        }
    }
    
    setupSupportRealTimeUpdates() {
        setInterval(() => {
            this.loadSupportDashboard();
        }, 30000);
    }
    
    showAlert(message, type = 'info') {
        const alert = document.createElement('div');
        alert.className = `alert alert-${type} alert-dismissible fade show`;
        alert.innerHTML = `
            ${this.getAlertIcon(type)} ${message}
            <button type="button" class="btn-close" data-bs-dismiss="alert"></button>
        `;
        
        const container = document.querySelector('.alerts') || document.querySelector('.admin-content');
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
    if (window.location.pathname.includes('/admin/support')) {
        window.supportDashboard = new SupportDashboard();
    }
    
    if (window.location.pathname.includes('/admin') && !window.location.pathname.includes('/admin/support')) {
        window.adminDashboard = new AdminDashboard();
    }
});