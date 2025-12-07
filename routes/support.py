from flask import Blueprint, request, jsonify
from flask_login import login_required, current_user
from services.support_service import SupportService
from models import db, SupportTicket, SupportMessage, TicketStatus, TicketPriority
from datetime import datetime

support_bp = Blueprint('support', __name__)

@support_bp.route('/tickets', methods=['GET'])
@login_required
def get_tickets():
    """Получение тикетов пользователя"""
    limit = request.args.get('limit', 20, type=int)
    
    tickets = SupportService.get_user_tickets(current_user.id, limit)
    
    return jsonify({'tickets': tickets})

@support_bp.route('/tickets', methods=['POST'])
@login_required
def create_ticket():
    """Создание тикета"""
    data = request.get_json()
    
    subject = data.get('subject')
    message = data.get('message')
    category = data.get('category', 'general')
    
    if not subject or not message:
        return jsonify({'error': 'Subject and message are required'}), 400
    
    result = SupportService.create_ticket(current_user.id, subject, message, category)
    
    if not result['success']:
        return jsonify({'error': result['error']}), 400
    
    return jsonify({
        'message': 'Support ticket created successfully',
        'ticket_id': result['ticket_id']
    }), 201

@support_bp.route('/tickets/<int:ticket_id>', methods=['GET'])
@login_required
def get_ticket(ticket_id):
    """Получение тикета и сообщений"""
    ticket = SupportTicket.query.get_or_404(ticket_id)
    
    # Проверяем доступ
    if ticket.user_id != current_user.id and current_user.role.value not in ['admin', 'moderator']:
        return jsonify({'error': 'Access denied'}), 403
    
    messages = SupportService.get_ticket_messages(ticket_id, current_user.id)
    
    return jsonify({
        'ticket': {
            'id': ticket.id,
            'subject': ticket.subject,
            'message': ticket.message,
            'status': ticket.status.value,
            'priority': ticket.priority.value,
            'category': ticket.category,
            'created_at': ticket.created_at.isoformat(),
            'updated_at': ticket.updated_at.isoformat(),
            'closed_at': ticket.closed_at.isoformat() if ticket.closed_at else None
        },
        'messages': messages
    })

@support_bp.route('/tickets/<int:ticket_id>/reply', methods=['POST'])
@login_required
def reply_to_ticket(ticket_id):
    """Ответ на тикет"""
    ticket = SupportTicket.query.get_or_404(ticket_id)
    
    # Проверяем доступ
    if ticket.user_id != current_user.id and current_user.role.value not in ['admin', 'moderator']:
        return jsonify({'error': 'Access denied'}), 403
    
    data = request.get_json()
    message = data.get('message')
    
    if not message:
        return jsonify({'error': 'Message is required'}), 400
    
    is_admin = current_user.role.value in ['admin', 'moderator']
    
    result = SupportService.add_message(ticket_id, current_user.id, message, is_admin)
    
    if not result['success']:
        return jsonify({'error': result['error']}), 400
    
    return jsonify({
        'message': 'Reply sent successfully',
        'message_id': result['message_id']
    })

@support_bp.route('/tickets/<int:ticket_id>/close', methods=['POST'])
@login_required
def close_ticket(ticket_id):
    """Закрытие тикета"""
    ticket = SupportTicket.query.get_or_404(ticket_id)
    
    # Проверяем доступ
    if ticket.user_id != current_user.id and current_user.role.value not in ['admin', 'moderator']:
        return jsonify({'error': 'Access denied'}), 403
    
    # Закрываем тикет
    ticket.status = TicketStatus.CLOSED
    ticket.closed_at = datetime.utcnow()
    
    if current_user.role.value in ['admin', 'moderator']:
        ticket.admin_id = current_user.id
    
    ticket.updated_at = datetime.utcnow()
    
    db.session.commit()
    
    return jsonify({'message': 'Ticket closed successfully'})

@support_bp.route('/unread-count', methods=['GET'])
@login_required
def get_unread_count():
    """Количество непрочитанных сообщений"""
    count = SupportService.get_user_unread_count(current_user.id)
    
    return jsonify({'count': count})

@support_bp.route('/search', methods=['GET'])
@login_required
def search_tickets():
    """Поиск тикетов"""
    query = request.args.get('q', '')
    
    tickets = SupportService.search_tickets(query, current_user.id)
    
    return jsonify({'tickets': tickets})

@support_bp.route('/categories', methods=['GET'])
@login_required
def get_categories():
    """Получение категорий поддержки"""
    categories = [
        {'id': 'deposit', 'name': 'Deposit Issues', 'icon': '💰'},
        {'id': 'withdrawal', 'name': 'Withdrawal Issues', 'icon': '🏧'},
        {'id': 'account', 'name': 'Account Issues', 'icon': '👤'},
        {'id': 'technical', 'name': 'Technical Problems', 'icon': '🔧'},
        {'id': 'game', 'name': 'Game Issues', 'icon': '🎮'},
        {'id': 'bonus', 'name': 'Bonuses & Promotions', 'icon': '🎁'},
        {'id': 'security', 'name': 'Security Concerns', 'icon': '🔒'},
        {'id': 'other', 'name': 'Other Questions', 'icon': '❓'}
    ]
    
    return jsonify({'categories': categories})