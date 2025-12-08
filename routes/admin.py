from flask import Blueprint, request, jsonify, send_file
from flask_login import login_required, current_user
from routes.auth import admin_required, moderator_required, support_required, staff_required
from services.admin_service import AdminService
from services.kyc_service import KYCService
from services.support_service import SupportService
from utils.helpers import export_to_csv, generate_reference
from models import (
    db, User, Game, Bet, Transaction, Payout, 
    AuditLog, UserRole, UserStatus, PayoutStatus,
    SupportTicket, TicketStatus, TicketPriority, SupportMessage,
    KYCDocument, KYCStatus, Bonus, Session, Announcement
)
from datetime import datetime, timedelta
from sqlalchemy import func, desc, or_
from io import StringIO
import csv
import json
from werkzeug.security import generate_password_hash

admin_bp = Blueprint('admin', __name__)

@admin_bp.route('/staff/create', methods=['POST'])
@admin_required
def create_staff_user():
    data = request.get_json()
    
    required_fields = ['username', 'email', 'password', 'role']
    for field in required_fields:
        if field not in data:
            return jsonify({'error': f'Missing required field: {field}'}), 400
    
    try:
        role = UserRole(data['role'])
        if role not in [UserRole.SUPPORT, UserRole.MODERATOR]:
            return jsonify({'error': 'Invalid role for staff user'}), 400
    except ValueError:
        return jsonify({'error': 'Invalid role'}), 400
    
    if User.query.filter_by(username=data['username']).first():
        return jsonify({'error': 'Username already exists'}), 400
    
    if User.query.filter_by(email=data['email']).first():
        return jsonify({'error': 'Email already registered'}), 400
    
    from utils.security import validate_password
    is_valid, message = validate_password(data['password'])
    if not is_valid:
        return jsonify({'error': message}), 400
    
    user = User(
        username=data['username'],
        email=data['email'],
        password_hash=generate_password_hash(data['password']),
        role=role,
        status=UserStatus.ACTIVE,
        balance=0.00,
        kyc_verified=True,
        kyc_status=KYCStatus.VERIFIED,
        registered_at=datetime.now(),
        last_login=datetime.now()
    )
    
    db.session.add(user)
    db.session.commit()
    
    from utils.security import create_audit_log
    create_audit_log(
        'STAFF_CREATE',
        f'Admin {current_user.username} created staff user {user.username} with role {role.value}',
        current_user.id,
        request
    )
    
    return jsonify({
        'success': True,
        'message': f'Staff user created successfully',
        'user': {
            'id': user.id,
            'username': user.username,
            'email': user.email,
            'role': user.role.value,
            'status': user.status.value
        }
    }), 201

@admin_bp.route('/staff/list', methods=['GET'])
@admin_required
def list_staff_users():
    page = request.args.get('page', 1, type=int)
    per_page = request.args.get('per_page', 20, type=int)
    
    staff_users = User.query.filter(
        User.role.in_([UserRole.ADMIN, UserRole.MODERATOR, UserRole.SUPPORT])
    ).order_by(User.registered_at.desc()).paginate(page=page, per_page=per_page, error_out=False)
    
    return jsonify({
        'staff': [{
            'id': u.id,
            'username': u.username,
            'email': u.email,
            'role': u.role.value,
            'status': u.status.value,
            'last_login': u.last_login.isoformat() if u.last_login else None,
            'registered_at': u.registered_at.isoformat(),
            'kyc_verified': u.kyc_verified
        } for u in staff_users.items],
        'total': staff_users.total,
        'pages': staff_users.pages,
        'page': page
    })

@admin_bp.route('/support/dashboard', methods=['GET'])
@staff_required
def support_dashboard():
    if current_user.role == UserRole.SUPPORT:
        tickets = SupportTicket.query.filter(
            or_(
                SupportTicket.admin_id == current_user.id,
                SupportTicket.status == TicketStatus.OPEN
            )
        ).order_by(desc(SupportTicket.updated_at)).limit(20).all()
    else:
        tickets = SupportTicket.query.order_by(desc(SupportTicket.updated_at)).limit(20).all()
    
    total_tickets = SupportTicket.query.count()
    open_tickets = SupportTicket.query.filter_by(status=TicketStatus.OPEN).count()
    my_tickets = SupportTicket.query.filter_by(admin_id=current_user.id).count() if current_user.role == UserRole.SUPPORT else 0
    
    return jsonify({
        'stats': {
            'total_tickets': total_tickets,
            'open_tickets': open_tickets,
            'my_tickets': my_tickets,
            'role': current_user.role.value
        },
        'recent_tickets': [{
            'id': t.id,
            'subject': t.subject,
            'user_id': t.user_id,
            'username': t.user.username,
            'status': t.status.value,
            'priority': t.priority.value,
            'category': t.category,
            'created_at': t.created_at.isoformat(),
            'updated_at': t.updated_at.isoformat(),
            'last_reply_by': t.last_reply_by.value if t.last_reply_by else None,
            'assigned_to_me': t.admin_id == current_user.id
        } for t in tickets]
    })

@admin_bp.route('/support/tickets/assign', methods=['POST'])
@support_required
def assign_ticket_to_self():
    data = request.get_json()
    ticket_id = data.get('ticket_id')
    
    ticket = SupportTicket.query.get_or_404(ticket_id)
    
    if ticket.admin_id and ticket.admin_id != current_user.id:
        return jsonify({'error': 'Ticket already assigned to another staff member'}), 400
    
    ticket.admin_id = current_user.id
    ticket.status = TicketStatus.IN_PROGRESS
    ticket.updated_at = datetime.now()
    
    from utils.security import create_audit_log
    create_audit_log(
        'TICKET_ASSIGN',
        f'Staff {current_user.username} assigned ticket #{ticket.id} to themselves',
        current_user.id,
        request
    )
    
    db.session.commit()
    
    return jsonify({
        'success': True,
        'message': 'Ticket assigned to you',
        'ticket': {
            'id': ticket.id,
            'admin_id': ticket.admin_id
        }
    })

@admin_bp.route('/support/tickets/<int:ticket_id>/assign', methods=['PUT'])
@moderator_required
def assign_ticket_to_staff(ticket_id):
    data = request.get_json()
    staff_id = data.get('staff_id')
    
    ticket = SupportTicket.query.get_or_404(ticket_id)
    staff = User.query.get_or_404(staff_id)
    
    if staff.role not in [UserRole.SUPPORT, UserRole.MODERATOR, UserRole.ADMIN]:
        return jsonify({'error': 'Can only assign tickets to staff members'}), 400
    
    old_admin_id = ticket.admin_id
    ticket.admin_id = staff_id
    ticket.status = TicketStatus.IN_PROGRESS
    ticket.updated_at = datetime.now()
    
    from utils.security import create_audit_log
    create_audit_log(
        'TICKET_ASSIGN',
        f'Staff {current_user.username} assigned ticket #{ticket.id} to {staff.username}',
        current_user.id,
        request
    )
    
    db.session.commit()
    
    return jsonify({
        'success': True,
        'message': f'Ticket assigned to {staff.username}',
        'ticket': {
            'id': ticket.id,
            'admin_id': ticket.admin_id,
            'admin_username': staff.username
        }
    })

@admin_bp.route('/support/tickets/<int:ticket_id>/quick-reply', methods=['POST'])
@support_required
def quick_reply_to_ticket(ticket_id):
    ticket = SupportTicket.query.get_or_404(ticket_id)
    
    if current_user.role == UserRole.SUPPORT and ticket.admin_id != current_user.id:
        return jsonify({'error': 'Ticket not assigned to you'}), 403
    
    data = request.get_json()
    template = data.get('template')
    custom_message = data.get('custom_message')
    
    if not template and not custom_message:
        return jsonify({'error': 'Either template or custom message is required'}), 400
    
    templates = {
        'welcome': 'Добрый день! Спасибо за обращение. Наша служба поддержки уже работает над вашим вопросом.',
        'deposit': 'По вопросам депозитов: пожалуйста, проверьте, что вы используете один из наших поддерживаемых методов оплаты. Обычно депозиты проходят мгновенно.',
        'withdrawal': 'По вопросам вывода средств: выплаты обрабатываются в течение 1-3 рабочих дней после верификации KYC.',
        'kyc': 'Для завершения KYC верификации, пожалуйста, загрузите документы в соответствующем разделе вашего профиля.',
        'bonus': 'Бонусы активируются автоматически при выполнении условий. Пожалуйста, проверьте раздел "Бонусы" в вашем профиле.',
        'close': 'Спасибо за обращение! Если у вас возникнут дополнительные вопросы, не стесняйтесь создавать новый тикет.'
    }
    
    if template in templates:
        message = templates[template]
    else:
        message = custom_message
    
    support_message = SupportMessage(
        ticket_id=ticket.id,
        user_id=current_user.id,
        message=message,
        is_admin=True,
        read=True,
        created_at=datetime.now()
    )
    
    ticket.updated_at = datetime.now()
    ticket.last_reply_by = UserRole.SUPPORT if current_user.role == UserRole.SUPPORT else UserRole.MODERATOR
    
    db.session.add(support_message)
    db.session.commit()
    
    return jsonify({
        'success': True,
        'message': 'Quick reply sent',
        'message_id': support_message.id
    })

@admin_bp.route('/support/tickets/bulk-action', methods=['POST'])
@support_required
def bulk_ticket_action():
    data = request.get_json()
    ticket_ids = data.get('ticket_ids', [])
    action = data.get('action')
    
    if not ticket_ids or not action:
        return jsonify({'error': 'Ticket IDs and action are required'}), 400
    
    if action not in ['assign_to_me', 'close', 'change_priority']:
        return jsonify({'error': 'Invalid action'}), 400
    
    tickets = SupportTicket.query.filter(SupportTicket.id.in_(ticket_ids)).all()
    
    updated_count = 0
    for ticket in tickets:
        if current_user.role == UserRole.SUPPORT:
            if ticket.admin_id and ticket.admin_id != current_user.id:
                continue
        
        if action == 'assign_to_me':
            ticket.admin_id = current_user.id
            ticket.status = TicketStatus.IN_PROGRESS
        elif action == 'close':
            ticket.status = TicketStatus.CLOSED
            ticket.closed_at = datetime.now()
            ticket.admin_id = current_user.id
        elif action == 'change_priority':
            new_priority = data.get('priority')
            if new_priority:
                ticket.priority = TicketPriority(new_priority)
        
        ticket.updated_at = datetime.now()
        updated_count += 1
    
    db.session.commit()
    
    from utils.security import create_audit_log
    create_audit_log(
        'TICKET_BULK_ACTION',
        f'Staff {current_user.username} performed bulk action "{action}" on {updated_count} tickets',
        current_user.id,
        request
    )
    
    return jsonify({
        'success': True,
        'message': f'Updated {updated_count} tickets',
        'updated_count': updated_count
    })

@admin_bp.route('/support/performance', methods=['GET'])
@moderator_required
def support_performance():
    thirty_days_ago = datetime.now() - timedelta(days=30)
    
    staff_users = User.query.filter(
        User.role.in_([UserRole.SUPPORT, UserRole.MODERATOR, UserRole.ADMIN])
    ).all()
    
    performance_data = []
    
    for staff in staff_users:
        closed_tickets = SupportTicket.query.filter(
            SupportTicket.admin_id == staff.id,
            SupportTicket.status == TicketStatus.CLOSED,
            SupportTicket.closed_at >= thirty_days_ago
        ).all()
        
        response_times = []
        for ticket in closed_tickets:
            if ticket.created_at and ticket.closed_at:
                response_time = (ticket.closed_at - ticket.created_at).total_seconds() / 3600  # в часах
                response_times.append(response_time)
        
        avg_response_time = sum(response_times) / len(response_times) if response_times else 0
        
        performance_data.append({
            'staff_id': staff.id,
            'username': staff.username,
            'role': staff.role.value,
            'tickets_closed': len(closed_tickets),
            'avg_response_time_hours': round(avg_response_time, 2),
            'last_activity': staff.last_login.isoformat() if staff.last_login else None
        })
    
    performance_data.sort(key=lambda x: x['tickets_closed'], reverse=True)
    
    return jsonify({
        'performance': performance_data,
        'period_days': 30
    })

@admin_bp.route('/support/tickets/<int:ticket_id>/reply', methods=['POST'])
@support_required
def reply_to_ticket(ticket_id):
    ticket = SupportTicket.query.get_or_404(ticket_id)
    
    if current_user.role == UserRole.SUPPORT:
        if ticket.admin_id and ticket.admin_id != current_user.id:
            return jsonify({'error': 'Ticket not assigned to you'}), 403
    
    data = request.get_json()
    message_text = data.get('message')
    close_ticket = data.get('close_ticket', False)
    
    if not message_text:
        return jsonify({'error': 'Message is required'}), 400
    
    message = SupportMessage(
        ticket_id=ticket.id,
        user_id=current_user.id,
        message=message_text,
        is_admin=True,
        read=True,
        created_at=datetime.now()
    )
    
    ticket.updated_at = datetime.now()
    ticket.last_reply_by = current_user.role
    
    if not ticket.admin_id:
        ticket.admin_id = current_user.id
        ticket.status = TicketStatus.IN_PROGRESS
    
    if close_ticket:
        ticket.status = TicketStatus.CLOSED
        ticket.closed_at = datetime.now()
    
    db.session.add(message)
    db.session.commit()
    
    return jsonify({
        'success': True,
        'message': 'Reply sent successfully',
        'message_id': message.id,
        'ticket_status': ticket.status.value
    })

@admin_bp.route('/support/kyc/pending', methods=['GET'])
@support_required
def get_pending_kyc_for_support():
    page = request.args.get('page', 1, type=int)
    per_page = request.args.get('per_page', 20, type=int)
    
    documents = KYCDocument.query.filter_by(status=KYCStatus.PENDING)\
        .order_by(KYCDocument.submitted_at.asc())\
        .paginate(page=page, per_page=per_page, error_out=False)
    
    return jsonify({
        'documents': [{
            'id': doc.id,
            'user_id': doc.user_id,
            'username': doc.user_doc.username,
            'email': doc.user_doc.email,
            'document_type': doc.document_type,
            'document_number': doc.document_number,
            'status': doc.status.value,
            'submitted_at': doc.submitted_at.isoformat(),
            'front_image': doc.front_image,
            'back_image': doc.back_image,
            'selfie_image': doc.selfie_image
        } for doc in documents.items],
        'total': documents.total,
        'pages': documents.pages,
        'page': page
    })


@admin_bp.route('/support/tickets', methods=['GET'])
@support_required
def get_support_tickets():
    page = request.args.get('page', 1, type=int)
    per_page = request.args.get('per_page', 20, type=int)
    status = request.args.get('status')
    priority = request.args.get('priority')
    
    query = SupportTicket.query
    
    if current_user.role == UserRole.SUPPORT:
        query = query.filter(
            or_(
                SupportTicket.admin_id == current_user.id,
                SupportTicket.status == TicketStatus.OPEN
            )
        )
    
    if status:
        query = query.filter_by(status=TicketStatus(status))
    
    if priority:
        query = query.filter_by(priority=TicketPriority(priority))
    
    tickets = query.order_by(desc(SupportTicket.updated_at))\
        .paginate(page=page, per_page=per_page, error_out=False)
    
    return jsonify({
        'tickets': [{
            'id': t.id,
            'user_id': t.user_id,
            'username': t.user.username,
            'subject': t.subject,
            'status': t.status.value,
            'priority': t.priority.value,
            'category': t.category,
            'created_at': t.created_at.isoformat(),
            'updated_at': t.updated_at.isoformat(),
            'last_reply_by': t.last_reply_by.value if t.last_reply_by else None,
            'message_count': len(t.messages),
            'assigned_to': t.admin_id,
            'assigned_username': t.admin.username if t.admin else None,
            'assigned_to_me': t.admin_id == current_user.id
        } for t in tickets.items],
        'total': tickets.total,
        'pages': tickets.pages,
        'page': page,
        'user_role': current_user.role.value
    })

@admin_bp.route('/support/tickets/<int:ticket_id>', methods=['GET'])
@support_required 
def get_support_ticket(ticket_id):
    ticket = SupportTicket.query.get_or_404(ticket_id)
    
    if current_user.role == UserRole.SUPPORT:
        if ticket.admin_id and ticket.admin_id != current_user.id:
            return jsonify({'error': 'Access denied. Ticket not assigned to you.'}), 403
    
    return jsonify({
        'id': ticket.id,
        'user': {
            'id': ticket.user.id,
            'username': ticket.user.username,
            'email': ticket.user.email,
            'kyc_verified': ticket.user.kyc_verified,
            'kyc_status': ticket.user.kyc_status.value
        },
        'subject': ticket.subject,
        'message': ticket.message,
        'status': ticket.status.value,
        'priority': ticket.priority.value,
        'category': ticket.category,
        'created_at': ticket.created_at.isoformat(),
        'updated_at': ticket.updated_at.isoformat(),
        'closed_at': ticket.closed_at.isoformat() if ticket.closed_at else None,
        'admin_id': ticket.admin_id,
        'admin_username': ticket.admin.username if ticket.admin else None,
        'last_reply_by': ticket.last_reply_by.value if ticket.last_reply_by else None,
        'messages': [{
            'id': m.id,
            'user_id': m.user_id,
            'username': m.user.username,
            'is_admin': m.is_admin,
            'message': m.message,
            'created_at': m.created_at.isoformat(),
            'read': m.read
        } for m in ticket.messages],
        'can_edit': current_user.role in [UserRole.ADMIN, UserRole.MODERATOR] or 
                   (current_user.role == UserRole.SUPPORT and ticket.admin_id == current_user.id)
    })

@admin_bp.route('/support/tickets/<int:ticket_id>', methods=['PUT'])
@support_required
def update_support_ticket(ticket_id):
    ticket = SupportTicket.query.get_or_404(ticket_id)
    data = request.get_json()
    
    if current_user.role == UserRole.SUPPORT:
        if ticket.admin_id and ticket.admin_id != current_user.id:
            return jsonify({'error': 'Cannot update ticket not assigned to you'}), 403
    
    changes = []
    
    if 'status' in data:
        old_status = ticket.status.value
        new_status = data['status']
        
        if current_user.role == UserRole.SUPPORT:
            if new_status not in [TicketStatus.IN_PROGRESS.value, TicketStatus.CLOSED.value]:
                return jsonify({'error': 'Support can only change status to in_progress or closed'}), 403
        
        ticket.status = TicketStatus(new_status)
        changes.append(f"Status: {old_status} → {new_status}")
        
        if new_status == 'closed':
            ticket.closed_at = datetime.now()
            ticket.admin_id = current_user.id
    
    if 'priority' in data:
        if current_user.role == UserRole.SUPPORT:
            return jsonify({'error': 'Support cannot change priority'}), 403
        old_priority = ticket.priority.value
        ticket.priority = TicketPriority(data['priority'])
        changes.append(f"Priority: {old_priority} → {ticket.priority.value}")
    
    if 'category' in data:
        if current_user.role == UserRole.SUPPORT:
            return jsonify({'error': 'Support cannot change category'}), 403
        ticket.category = data['category']
        changes.append(f"Category updated")
    
    ticket.updated_at = datetime.now()
    
    from utils.security import create_audit_log
    create_audit_log(
        'SUPPORT_UPDATE',
        f'Staff {current_user.username} updated ticket #{ticket.id}. Changes: {", ".join(changes)}',
        current_user.id,
        request
    )
    
    db.session.commit()
    
    return jsonify({
        'message': 'Ticket updated successfully',
        'changes': changes,
        'ticket': {
            'id': ticket.id,
            'status': ticket.status.value,
            'priority': ticket.priority.value
        }
    })