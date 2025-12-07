from flask import Blueprint, request, jsonify, send_file
from flask_login import login_required, current_user
from routes.auth import admin_required, moderator_required
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

admin_bp = Blueprint('admin', __name__)

# ========== СТАТИСТИКА И ДАШБОРД ==========

@admin_bp.route('/dashboard/stats', methods=['GET'])
@admin_required
def dashboard_stats():
    """Статистика для админ панели"""
    # За последние 30 дней
    thirty_days_ago = datetime.utcnow() - timedelta(days=30)
    
    # Статистика пользователей
    total_users = User.query.count()
    new_users = User.query.filter(User.registered_at >= thirty_days_ago).count()
    active_users = User.query.filter_by(status=UserStatus.ACTIVE).count()
    pending_kyc = User.query.filter_by(kyc_status=KYCStatus.PENDING).count()
    
    # Финансовая статистика
    total_deposits = db.session.query(func.sum(Transaction.amount)).filter(
        Transaction.type == 'deposit',
        Transaction.status == 'completed',
        Transaction.timestamp >= thirty_days_ago
    ).scalar() or 0
    
    total_withdrawals = db.session.query(func.sum(Payout.amount)).filter(
        Payout.status.in_([PayoutStatus.COMPLETED.value, PayoutStatus.PROCESSING.value]),
        Payout.request_date >= thirty_days_ago
    ).scalar() or 0
    
    total_bets = db.session.query(func.sum(Bet.amount)).filter(
        Bet.timestamp >= thirty_days_ago
    ).scalar() or 0
    
    total_wins = db.session.query(func.sum(Bet.win_amount)).filter(
        Bet.result == 'win',
        Bet.timestamp >= thirty_days_ago
    ).scalar() or 0
    
    # Прибыль
    gross_revenue = (total_bets or 0) - (total_wins or 0)
    net_profit = gross_revenue - (total_withdrawals or 0)
    
    # Поддержка
    open_tickets = SupportTicket.query.filter_by(status=TicketStatus.OPEN).count()
    pending_payouts = Payout.query.filter_by(status=PayoutStatus.PENDING).count()
    
    return jsonify({
        'users': {
            'total': total_users,
            'new': new_users,
            'active': active_users,
            'pending_kyc': pending_kyc
        },
        'financial': {
            'deposits': float(total_deposits or 0),
            'withdrawals': float(total_withdrawals or 0),
            'bets': float(total_bets or 0),
            'wins': float(total_wins or 0),
            'gross_revenue': float(gross_revenue),
            'net_profit': float(net_profit)
        },
        'support': {
            'open_tickets': open_tickets,
            'pending_payouts': pending_payouts
        }
    })

@admin_bp.route('/dashboard/chart-data', methods=['GET'])
@admin_required
def dashboard_chart_data():
    """Данные для графиков"""
    days = int(request.args.get('days', 30))
    
    data = AdminService.get_chart_data(days)
    return jsonify(data)

# ========== УПРАВЛЕНИЕ ПОЛЬЗОВАТЕЛЯМИ ==========

@admin_bp.route('/users', methods=['GET'])
@admin_required
def get_users():
    """Получение списка пользователей"""
    page = request.args.get('page', 1, type=int)
    per_page = request.args.get('per_page', 20, type=int)
    status = request.args.get('status')
    role = request.args.get('role')
    search = request.args.get('search', '')
    
    query = User.query
    
    if status:
        query = query.filter_by(status=UserStatus(status))
    if role:
        query = query.filter_by(role=UserRole(role))
    
    if search:
        search_filter = or_(
            User.username.ilike(f'%{search}%'),
            User.email.ilike(f'%{search}%'),
            User.first_name.ilike(f'%{search}%'),
            User.last_name.ilike(f'%{search}%')
        )
        query = query.filter(search_filter)
    
    users = query.order_by(User.registered_at.desc()).paginate(page=page, per_page=per_page, error_out=False)
    
    result = {
        'users': [{
            'id': u.id,
            'username': u.username,
            'email': u.email,
            'role': u.role.value,
            'status': u.status.value,
            'balance': u.balance,
            'kyc_verified': u.kyc_verified,
            'kyc_status': u.kyc_status.value,
            'registered_at': u.registered_at.isoformat(),
            'last_login': u.last_login.isoformat() if u.last_login else None,
            'country': u.country,
            'total_deposits': AdminService.get_user_total_deposits(u.id),
            'total_bets': AdminService.get_user_total_bets(u.id),
            'total_wins': AdminService.get_user_total_wins(u.id)
        } for u in users.items],
        'total': users.total,
        'pages': users.pages,
        'page': page
    }
    
    return jsonify(result)

@admin_bp.route('/users/<int:user_id>', methods=['GET'])
@admin_required
def get_user(user_id):
    """Получение информации о пользователе"""
    user = User.query.get_or_404(user_id)
    
    # Получаем статистику пользователя
    total_deposits = AdminService.get_user_total_deposits(user_id)
    total_withdrawals = AdminService.get_user_total_withdrawals(user_id)
    total_bets = AdminService.get_user_total_bets(user_id)
    total_wins = AdminService.get_user_total_wins(user_id)
    
    return jsonify({
        'id': user.id,
        'username': user.username,
        'email': user.email,
        'role': user.role.value,
        'status': user.status.value,
        'balance': user.balance,
        'registered_at': user.registered_at.isoformat(),
        'last_login': user.last_login.isoformat() if user.last_login else None,
        'kyc_verified': user.kyc_verified,
        'kyc_status': user.kyc_status.value,
        'phone': user.phone,
        'first_name': user.first_name,
        'last_name': user.last_name,
        'country': user.country,
        'address': user.address,
        'city': user.city,
        'state': user.state,
        'zip_code': user.zip_code,
        'birth_date': user.birth_date.isoformat() if user.birth_date else None,
        'limits': {
            'daily_deposit_limit': user.daily_deposit_limit,
            'daily_loss_limit': user.daily_loss_limit,
            'session_time_limit': user.session_time_limit,
            'cool_off_period': user.cool_off_period
        },
        'statistics': {
            'total_deposits': total_deposits,
            'total_withdrawals': total_withdrawals,
            'total_bets': total_bets,
            'total_wins': total_wins,
            'net_loss': total_bets - total_wins
        }
    })

@admin_bp.route('/users/<int:user_id>', methods=['PUT'])
@admin_required
def update_user(user_id):
    """Обновление пользователя"""
    user = User.query.get_or_404(user_id)
    data = request.get_json()
    
    changes = []
    
    # Проверяем, что админ не редактирует сам себя (кроме некоторых полей)
    if user.id == current_user.id and 'role' in data:
        return jsonify({'error': 'Cannot change your own role'}), 400
    
    if 'balance' in data:
        old_balance = user.balance
        new_balance = float(data['balance'])
        user.balance = new_balance
        changes.append(f"Balance changed from {old_balance} to {new_balance}")
        
        # Создание транзакции для аудита
        from models import TransactionType
        transaction = Transaction(
            user_id=user.id,
            type=TransactionType.ADJUSTMENT,
            amount=new_balance - old_balance,
            balance_before=old_balance,
            balance_after=new_balance,
            status='completed',
            description=f'Balance adjustment by admin {current_user.username}'
        )
        db.session.add(transaction)
    
    if 'status' in data:
        old_status = user.status.value
        new_status = data['status']
        user.status = UserStatus(new_status)
        changes.append(f"Status changed from {old_status} to {new_status}")
    
    if 'role' in data:
        old_role = user.role.value
        new_role = data['role']
        user.role = UserRole(new_role)
        changes.append(f"Role changed from {old_role} to {new_role}")
    
    if 'kyc_verified' in data:
        user.kyc_verified = bool(data['kyc_verified'])
        if data['kyc_verified']:
            user.kyc_status = KYCStatus.VERIFIED
        changes.append(f"KYC verification set to {user.kyc_verified}")
    
    # Обновление личных данных
    personal_fields = ['phone', 'first_name', 'last_name', 'country', 
                      'address', 'city', 'state', 'zip_code', 'birth_date']
    
    for field in personal_fields:
        if field in data:
            old_value = getattr(user, field)
            new_value = data[field]
            setattr(user, field, new_value)
            changes.append(f"{field.replace('_', ' ').title()} changed")
    
    # Обновление лимитов
    limit_fields = ['daily_deposit_limit', 'daily_loss_limit', 
                   'session_time_limit', 'cool_off_period']
    
    for field in limit_fields:
        if field in data:
            setattr(user, field, float(data[field]) if 'limit' in field else int(data[field]))
            changes.append(f"{field.replace('_', ' ').title()} updated")
    
    # Аудит
    from utils.security import create_audit_log
    create_audit_log(
        'USER_UPDATE',
        f'Admin {current_user.username} updated user {user.username}. Changes: {", ".join(changes)}',
        current_user.id,
        request
    )
    
    db.session.commit()
    
    return jsonify({
        'message': 'User updated successfully',
        'changes': changes,
        'user': {
            'id': user.id,
            'username': user.username,
            'role': user.role.value,
            'status': user.status.value,
            'balance': user.balance,
            'kyc_verified': user.kyc_verified
        }
    })

@admin_bp.route('/users/<int:user_id>', methods=['DELETE'])
@admin_required
def delete_user(user_id):
    """Удаление пользователя"""
    user = User.query.get_or_404(user_id)
    
    # Нельзя удалить себя
    if user.id == current_user.id:
        return jsonify({'error': 'Cannot delete your own account'}), 400
    
    username = user.username
    
    # Аудит перед удалением
    from utils.security import create_audit_log
    create_audit_log(
        'USER_DELETE',
        f'Admin {current_user.username} deleted user {username}',
        current_user.id,
        request
    )
    
    db.session.delete(user)
    db.session.commit()
    
    return jsonify({'message': f'User {username} deleted successfully'})

@admin_bp.route('/users/<int:user_id>/transactions', methods=['GET'])
@admin_required
def get_user_transactions(user_id):
    """Транзакции пользователя"""
    page = request.args.get('page', 1, type=int)
    per_page = request.args.get('per_page', 50, type=int)
    
    transactions = Transaction.query.filter_by(user_id=user_id)\
        .order_by(desc(Transaction.timestamp))\
        .paginate(page=page, per_page=per_page, error_out=False)
    
    return jsonify({
        'transactions': [{
            'id': t.id,
            'type': t.type.value,
            'amount': t.amount,
            'balance_before': t.balance_before,
            'balance_after': t.balance_after,
            'status': t.status,
            'timestamp': t.timestamp.isoformat(),
            'description': t.description
        } for t in transactions.items],
        'total': transactions.total,
        'pages': transactions.pages,
        'page': page
    })

@admin_bp.route('/users/<int:user_id>/bets', methods=['GET'])
@admin_required
def get_user_bets(user_id):
    """Ставки пользователя"""
    page = request.args.get('page', 1, type=int)
    per_page = request.args.get('per_page', 50, type=int)
    
    bets = Bet.query.filter_by(user_id=user_id)\
        .order_by(desc(Bet.timestamp))\
        .paginate(page=page, per_page=per_page, error_out=False)
    
    return jsonify({
        'bets': [{
            'id': b.id,
            'game_title': b.game.title if b.game else 'Unknown',
            'amount': b.amount,
            'multiplier': b.multiplier,
            'result': b.result,
            'win_amount': b.win_amount,
            'timestamp': b.timestamp.isoformat(),
            'ip_address': b.ip_address
        } for b in bets.items],
        'total': bets.total,
        'pages': bets.pages,
        'page': page
    })

# ========== УПРАВЛЕНИЕ ИГРАМИ ==========

@admin_bp.route('/games', methods=['GET'])
@admin_required
def get_games():
    """Получение списка игр"""
    games = Game.query.order_by(Game.added_at.desc()).all()
    
    return jsonify({
        'games': [{
            'id': g.id,
            'title': g.title,
            'category': g.category,
            'description': g.description,
            'min_bet': g.min_bet,
            'max_bet': g.max_bet,
            'rtp': g.rtp,
            'active': g.active,
            'maintenance': g.maintenance,
            'added_at': g.added_at.isoformat(),
            'provider': g.provider,
            'volatility': g.volatility,
            'popularity': g.popularity,
            'image_url': g.image_url,
            'total_bets': AdminService.get_game_total_bets(g.id),
            'total_wins': AdminService.get_game_total_wins(g.id)
        } for g in games]
    })

@admin_bp.route('/games', methods=['POST'])
@admin_required
def create_game():
    """Создание новой игры"""
    data = request.get_json()
    
    required_fields = ['title', 'category', 'min_bet', 'max_bet', 'rtp']
    for field in required_fields:
        if field not in data:
            return jsonify({'error': f'Missing required field: {field}'}), 400
    
    try:
        game = Game(
            title=data['title'],
            category=data['category'],
            min_bet=float(data['min_bet']),
            max_bet=float(data['max_bet']),
            rtp=float(data['rtp']),
            description=data.get('description', ''),
            provider=data.get('provider', 'BeaversCasino'),
            volatility=data.get('volatility', 'medium'),
            image_url=data.get('image_url', ''),
            active=data.get('active', True)
        )
        
        db.session.add(game)
        db.session.commit()
        
        # Аудит
        from utils.security import create_audit_log
        create_audit_log(
            'GAME_CREATE',
            f'Admin {current_user.username} created game: {game.title}',
            current_user.id,
            request
        )
        
        return jsonify({
            'message': 'Game created successfully',
            'game': {
                'id': game.id,
                'title': game.title,
                'category': game.category
            }
        }), 201
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': f'Failed to create game: {str(e)}'}), 500

@admin_bp.route('/games/<int:game_id>', methods=['PUT'])
@admin_required
def update_game(game_id):
    """Обновление игры"""
    game = Game.query.get_or_404(game_id)
    data = request.get_json()
    
    changes = []
    
    updatable_fields = ['title', 'category', 'description', 'min_bet', 'max_bet',
                       'rtp', 'active', 'maintenance', 'provider', 'volatility',
                       'image_url']
    
    for field in updatable_fields:
        if field in data:
            old_value = getattr(game, field)
            new_value = data[field]
            
            # Конвертация типов
            if field in ['min_bet', 'max_bet', 'rtp']:
                new_value = float(new_value)
            elif field in ['active', 'maintenance']:
                new_value = bool(new_value)
            
            setattr(game, field, new_value)
            changes.append(f"{field.replace('_', ' ').title()}: {old_value} → {new_value}")
    
    # Аудит
    from utils.security import create_audit_log
    create_audit_log(
        'GAME_UPDATE',
        f'Admin {current_user.username} updated game {game.title}. Changes: {", ".join(changes)}',
        current_user.id,
        request
    )
    
    db.session.commit()
    
    return jsonify({
        'message': 'Game updated successfully',
        'changes': changes,
        'game': {
            'id': game.id,
            'title': game.title,
            'active': game.active,
            'maintenance': game.maintenance
        }
    })

@admin_bp.route('/games/<int:game_id>', methods=['DELETE'])
@admin_required
def delete_game(game_id):
    """Удаление игры"""
    game = Game.query.get_or_404(game_id)
    game_title = game.title
    
    # Проверяем, есть ли активные ставки на игру
    active_bets = Bet.query.filter_by(game_id=game_id).first()
    if active_bets:
        return jsonify({'error': 'Cannot delete game with existing bets'}), 400
    
    # Аудит
    from utils.security import create_audit_log
    create_audit_log(
        'GAME_DELETE',
        f'Admin {current_user.username} deleted game: {game_title}',
        current_user.id,
        request
    )
    
    db.session.delete(game)
    db.session.commit()
    
    return jsonify({'message': f'Game {game_title} deleted successfully'})

@admin_bp.route('/games/<int:game_id>/toggle', methods=['POST'])
@admin_required
def toggle_game_status(game_id):
    """Включение/выключение игры"""
    game = Game.query.get_or_404(game_id)
    
    action = request.json.get('action')
    
    if action == 'activate':
        game.active = True
        game.maintenance = False
        status = 'activated'
    elif action == 'deactivate':
        game.active = False
        status = 'deactivated'
    elif action == 'maintenance':
        game.maintenance = True
        status = 'put in maintenance'
    else:
        return jsonify({'error': 'Invalid action'}), 400
    
    # Аудит
    from utils.security import create_audit_log
    create_audit_log(
        'GAME_TOGGLE',
        f'Admin {current_user.username} {status} game: {game.title}',
        current_user.id,
        request
    )
    
    db.session.commit()
    
    return jsonify({
        'message': f'Game {status}',
        'game': {
            'id': game.id,
            'title': game.title,
            'active': game.active,
            'maintenance': game.maintenance
        }
    })

# ========== ТРАНЗАКЦИИ ==========

@admin_bp.route('/transactions', methods=['GET'])
@admin_required
def get_transactions():
    """Получение всех транзакций"""
    page = request.args.get('page', 1, type=int)
    per_page = request.args.get('per_page', 50, type=int)
    transaction_type = request.args.get('type')
    user_id = request.args.get('user_id')
    date_from = request.args.get('date_from')
    date_to = request.args.get('date_to')
    
    query = Transaction.query
    
    if transaction_type:
        query = query.filter_by(type=transaction_type)
    
    if user_id:
        query = query.filter_by(user_id=user_id)
    
    if date_from:
        try:
            date_from_obj = datetime.fromisoformat(date_from.replace('Z', '+00:00'))
            query = query.filter(Transaction.timestamp >= date_from_obj)
        except ValueError:
            pass
    
    if date_to:
        try:
            date_to_obj = datetime.fromisoformat(date_to.replace('Z', '+00:00'))
            query = query.filter(Transaction.timestamp <= date_to_obj)
        except ValueError:
            pass
    
    transactions = query.order_by(desc(Transaction.timestamp))\
        .paginate(page=page, per_page=per_page, error_out=False)
    
    return jsonify({
        'transactions': [{
            'id': t.id,
            'user_id': t.user_id,
            'username': t.user.username if t.user else 'Unknown',
            'type': t.type.value,
            'amount': t.amount,
            'balance_before': t.balance_before,
            'balance_after': t.balance_after,
            'status': t.status,
            'timestamp': t.timestamp.isoformat(),
            'description': t.description,
            'reference': t.reference
        } for t in transactions.items],
        'total': transactions.total,
        'pages': transactions.pages,
        'page': page
    })

# ========== ВЫПЛАТЫ ==========

@admin_bp.route('/payouts', methods=['GET'])
@admin_required
def get_payouts():
    """Получение всех выплат"""
    page = request.args.get('page', 1, type=int)
    per_page = request.args.get('per_page', 50, type=int)
    status = request.args.get('status')
    
    query = Payout.query
    
    if status:
        query = query.filter_by(status=PayoutStatus(status))
    
    payouts = query.order_by(desc(Payout.request_date))\
        .paginate(page=page, per_page=per_page, error_out=False)
    
    return jsonify({
        'payouts': [{
            'id': p.id,
            'user_id': p.user_id,
            'username': p.user.username if p.user else 'Unknown',
            'amount': p.amount,
            'method': p.method,
            'status': p.status.value,
            'request_date': p.request_date.isoformat(),
            'processed_date': p.processed_date.isoformat() if p.processed_date else None,
            'fee': p.fee,
            'account_details': json.loads(p.account_details) if p.account_details else {},
            'admin_notes': p.admin_notes
        } for p in payouts.items],
        'total': payouts.total,
        'pages': payouts.pages,
        'page': page
    })

@admin_bp.route('/payouts/<int:payout_id>', methods=['GET'])
@admin_required
def get_payout(payout_id):
    """Получение информации о выплате"""
    payout = Payout.query.get_or_404(payout_id)
    
    return jsonify({
        'id': payout.id,
        'user': {
            'id': payout.user.id,
            'username': payout.user.username,
            'email': payout.user.email,
            'kyc_verified': payout.user.kyc_verified
        },
        'amount': payout.amount,
        'method': payout.method,
        'status': payout.status.value,
        'request_date': payout.request_date.isoformat(),
        'processed_date': payout.processed_date.isoformat() if payout.processed_date else None,
        'fee': payout.fee,
        'account_details': json.loads(payout.account_details) if payout.account_details else {},
        'admin_notes': payout.admin_notes
    })

@admin_bp.route('/payouts/<int:payout_id>', methods=['PUT'])
@admin_required
def update_payout(payout_id):
    """Обновление статуса выплаты"""
    payout = Payout.query.get_or_404(payout_id)
    data = request.get_json()
    
    if 'status' not in data:
        return jsonify({'error': 'Status is required'}), 400
    
    old_status = payout.status.value
    new_status = data['status']
    
    try:
        payout.status = PayoutStatus(new_status)
    except ValueError:
        return jsonify({'error': 'Invalid status'}), 400
    
    if new_status == 'completed':
        payout.processed_date = datetime.utcnow()
        # Создаем транзакцию вывода
        transaction = Transaction(
            user_id=payout.user_id,
            type='withdrawal',
            amount=payout.amount,
            balance_before=payout.user.balance,
            balance_after=payout.user.balance,
            status='completed',
            description=f'Withdrawal processed via {payout.method}',
            timestamp=datetime.utcnow()
        )
        db.session.add(transaction)
    
    if 'admin_notes' in data:
        payout.admin_notes = data['admin_notes']
    
    # Аудит
    from utils.security import create_audit_log
    create_audit_log(
        'PAYOUT_UPDATE',
        f'Admin {current_user.username} updated payout #{payout.id} status: {old_status} → {new_status}',
        current_user.id,
        request
    )
    
    db.session.commit()
    
    return jsonify({
        'message': f'Payout status updated to {new_status}',
        'payout': {
            'id': payout.id,
            'status': payout.status.value,
            'processed_date': payout.processed_date.isoformat() if payout.processed_date else None
        }
    })

@admin_bp.route('/payouts/<int:payout_id>/reject', methods=['POST'])
@admin_required
def reject_payout(payout_id):
    """Отклонение выплаты"""
    payout = Payout.query.get_or_404(payout_id)
    data = request.get_json()
    
    reason = data.get('reason', 'No reason provided')
    
    # Возвращаем средства пользователю
    payout.user.balance += payout.amount
    payout.status = PayoutStatus.REJECTED
    payout.processed_date = datetime.utcnow()
    payout.admin_notes = f"Rejected: {reason}"
    
    # Создаем транзакцию возврата
    transaction = Transaction(
        user_id=payout.user_id,
        type='adjustment',
        amount=payout.amount,
        balance_before=payout.user.balance - payout.amount,
        balance_after=payout.user.balance,
        status='completed',
        description=f'Withdrawal rejected, funds returned. Reason: {reason}',
        timestamp=datetime.utcnow()
    )
    
    db.session.add(transaction)
    
    # Аудит
    from utils.security import create_audit_log
    create_audit_log(
        'PAYOUT_REJECT',
        f'Admin {current_user.username} rejected payout #{payout.id}. Reason: {reason}',
        current_user.id,
        request
    )
    
    db.session.commit()
    
    return jsonify({
        'message': 'Payout rejected and funds returned to user',
        'payout': {
            'id': payout.id,
            'status': payout.status.value
        }
    })

# ========== KYC ВЕРИФИКАЦИЯ ==========

@admin_bp.route('/kyc/pending', methods=['GET'])
@admin_required
def get_pending_kyc():
    """Получение ожидающих KYC заявок"""
    page = request.args.get('page', 1, type=int)
    per_page = request.args.get('per_page', 20, type=int)
    
    documents = KYCDocument.query.filter_by(status=KYCStatus.PENDING)\
        .order_by(KYCDocument.submitted_at.asc())\
        .paginate(page=page, per_page=per_page, error_out=False)
    
    return jsonify({
        'documents': [{
            'id': doc.id,
            'user_id': doc.user_id,
            'username': doc.user.username,
            'email': doc.user.email,
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

@admin_bp.route('/kyc/<int:document_id>', methods=['GET'])
@admin_required
def get_kyc_document(document_id):
    """Получение информации о KYC документе"""
    document = KYCDocument.query.get_or_404(document_id)
    
    return jsonify({
        'id': document.id,
        'user': {
            'id': document.user.id,
            'username': document.user.username,
            'email': document.user.email,
            'first_name': document.user.first_name,
            'last_name': document.user.last_name,
            'birth_date': document.user.birth_date.isoformat() if document.user.birth_date else None,
            'country': document.user.country
        },
        'document_type': document.document_type,
        'document_number': document.document_number,
        'status': document.status.value,
        'submitted_at': document.submitted_at.isoformat(),
        'verified_at': document.verified_at.isoformat() if document.verified_at else None,
        'verified_by': document.verified_by,
        'rejection_reason': document.rejection_reason,
        'front_image': document.front_image,
        'back_image': document.back_image,
        'selfie_image': document.selfie_image
    })

@admin_bp.route('/kyc/<int:document_id>/verify', methods=['POST'])
@admin_required
def verify_kyc(document_id):
    """Верификация KYC документа"""
    document = KYCDocument.query.get_or_404(document_id)
    data = request.get_json()
    
    action = data.get('action')  # 'approve' or 'reject'
    notes = data.get('notes', '')
    
    if action not in ['approve', 'reject']:
        return jsonify({'error': 'Invalid action'}), 400
    
    if action == 'approve':
        document.status = KYCStatus.VERIFIED
        document.verified_at = datetime.utcnow()
        document.verified_by = current_user.id
        
        # Обновляем пользователя
        document.user.kyc_verified = True
        document.user.kyc_status = KYCStatus.VERIFIED
        
        message = f'KYC document approved by {current_user.username}'
        
        # Даем бонус за верификацию (опционально)
        if data.get('give_bonus', True):
            bonus_amount = 10.00
            document.user.balance += bonus_amount
            
            bonus_transaction = Transaction(
                user_id=document.user.id,
                type='bonus',
                amount=bonus_amount,
                balance_before=document.user.balance - bonus_amount,
                balance_after=document.user.balance,
                status='completed',
                description='KYC verification bonus',
                timestamp=datetime.utcnow()
            )
            db.session.add(bonus_transaction)
            
            bonus = Bonus(
                user_id=document.user.id,
                type='kyc_verification',
                amount=bonus_amount,
                activated_at=datetime.utcnow()
            )
            db.session.add(bonus)
            
            message += f' with ${bonus_amount} bonus'
    
    else:  # reject
        document.status = KYCStatus.REJECTED
        document.verified_at = datetime.utcnow()
        document.verified_by = current_user.id
        document.rejection_reason = notes
        
        document.user.kyc_status = KYCStatus.REJECTED
        
        message = f'KYC document rejected by {current_user.username}. Reason: {notes}'
    
    # Аудит
    from utils.security import create_audit_log
    create_audit_log(
        'KYC_' + action.upper(),
        f'Admin {current_user.username} {action}ed KYC for user {document.user.username}',
        current_user.id,
        request
    )
    
    db.session.commit()
    
    return jsonify({
        'message': f'KYC document {action}d',
        'document': {
            'id': document.id,
            'status': document.status.value,
            'verified_at': document.verified_at.isoformat() if document.verified_at else None
        }
    })

@admin_bp.route('/kyc/user/<int:user_id>', methods=['GET'])
@admin_required
def get_user_kyc_history(user_id):
    """История KYC пользователя"""
    documents = KYCDocument.query.filter_by(user_id=user_id)\
        .order_by(KYCDocument.submitted_at.desc())\
        .all()
    
    return jsonify({
        'documents': [{
            'id': doc.id,
            'document_type': doc.document_type,
            'status': doc.status.value,
            'submitted_at': doc.submitted_at.isoformat(),
            'verified_at': doc.verified_at.isoformat() if doc.verified_at else None,
            'verified_by': doc.verified_by,
            'rejection_reason': doc.rejection_reason
        } for doc in documents]
    })

# ========== ПОДДЕРЖКА ==========

@admin_bp.route('/support/tickets', methods=['GET'])
@admin_required
def get_support_tickets():
    """Получение тикетов поддержки"""
    page = request.args.get('page', 1, type=int)
    per_page = request.args.get('per_page', 20, type=int)
    status = request.args.get('status')
    priority = request.args.get('priority')
    
    query = SupportTicket.query
    
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
            'message_count': len(t.messages)
        } for t in tickets.items],
        'total': tickets.total,
        'pages': tickets.pages,
        'page': page
    })

@admin_bp.route('/support/tickets/<int:ticket_id>', methods=['GET'])
@admin_required
def get_support_ticket(ticket_id):
    """Получение информации о тикете"""
    ticket = SupportTicket.query.get_or_404(ticket_id)
    
    return jsonify({
        'id': ticket.id,
        'user': {
            'id': ticket.user.id,
            'username': ticket.user.username,
            'email': ticket.user.email
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
        'last_reply_by': ticket.last_reply_by.value if ticket.last_reply_by else None,
        'messages': [{
            'id': m.id,
            'user_id': m.user_id,
            'username': m.user.username,
            'is_admin': m.is_admin,
            'message': m.message,
            'created_at': m.created_at.isoformat(),
            'read': m.read
        } for m in ticket.messages]
    })

@admin_bp.route('/support/tickets/<int:ticket_id>', methods=['PUT'])
@admin_required
def update_support_ticket(ticket_id):
    """Обновление тикета поддержки"""
    ticket = SupportTicket.query.get_or_404(ticket_id)
    data = request.get_json()
    
    changes = []
    
    if 'status' in data:
        old_status = ticket.status.value
        ticket.status = TicketStatus(data['status'])
        changes.append(f"Status: {old_status} → {ticket.status.value}")
        
        if data['status'] == 'closed':
            ticket.closed_at = datetime.now()
            ticket.admin_id = current_user.id
    
    if 'priority' in data:
        old_priority = ticket.priority.value
        ticket.priority = TicketPriority(data['priority'])
        changes.append(f"Priority: {old_priority} → {ticket.priority.value}")
    
    if 'category' in data:
        ticket.category = data['category']
        changes.append(f"Category updated")
    
    ticket.updated_at = datetime.now()
    
    # Аудит
    from utils.security import create_audit_log
    create_audit_log(
        'SUPPORT_UPDATE',
        f'Admin {current_user.username} updated ticket #{ticket.id}. Changes: {", ".join(changes)}',
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

@admin_bp.route('/support/tickets/<int:ticket_id>/reply', methods=['POST'])
@admin_required
def reply_to_ticket(ticket_id):
    """Ответ на тикет поддержки"""
    ticket = SupportTicket.query.get_or_404(ticket_id)
    data = request.get_json()
    
    message_text = data.get('message')
    if not message_text:
        return jsonify({'error': 'Message is required'}), 400
    
    # Создаем сообщение
    message = SupportMessage(
        ticket_id=ticket.id,
        user_id=current_user.id,
        message=message_text,
        is_admin=True,
        read=True
    )
    
    # Обновляем тикет
    ticket.updated_at = datetime.now()
    ticket.last_reply_by = UserRole.ADMIN
    
    db.session.add(message)
    db.session.commit()
    
    return jsonify({
        'message': 'Reply sent successfully',
        'message_id': message.id
    })

@admin_bp.route('/support/stats', methods=['GET'])
@admin_required
def support_stats():
    """Статистика поддержки"""
    total_tickets = SupportTicket.query.count()
    open_tickets = SupportTicket.query.filter_by(status=TicketStatus.OPEN).count()
    in_progress_tickets = SupportTicket.query.filter_by(status=TicketStatus.IN_PROGRESS).count()
    closed_tickets = SupportTicket.query.filter_by(status=TicketStatus.CLOSED).count()
    
    # Распределение по приоритетам
    low_priority = SupportTicket.query.filter_by(priority=TicketPriority.LOW).count()
    medium_priority = SupportTicket.query.filter_by(priority=TicketPriority.MEDIUM).count()
    high_priority = SupportTicket.query.filter_by(priority=TicketPriority.HIGH).count()
    urgent_priority = SupportTicket.query.filter_by(priority=TicketPriority.URGENT).count()
    
    # Среднее время ответа (за последние 7 дней)
    seven_days_ago = datetime.utcnow() - timedelta(days=7)
    recent_tickets = SupportTicket.query.filter(
        SupportTicket.created_at >= seven_days_ago,
        SupportTicket.closed_at.isnot(None)
    ).all()
    
    avg_response_time = 0
    if recent_tickets:
        total_time = sum((t.closed_at - t.created_at).total_seconds() for t in recent_tickets)
        avg_response_time = total_time / len(recent_tickets) / 3600  # в часах
    
    return jsonify({
        'total_tickets': total_tickets,
        'open_tickets': open_tickets,
        'in_progress_tickets': in_progress_tickets,
        'closed_tickets': closed_tickets,
        'priority_distribution': {
            'low': low_priority,
            'medium': medium_priority,
            'high': high_priority,
            'urgent': urgent_priority
        },
        'avg_response_time_hours': round(avg_response_time, 2)
    })

# ========== АУДИТ ЛОГ ==========

@admin_bp.route('/audit', methods=['GET'])
@admin_required
def get_audit_log():
    """Получение лога аудита"""
    page = request.args.get('page', 1, type=int)
    per_page = request.args.get('per_page', 100, type=int)
    user_id = request.args.get('user_id')
    action = request.args.get('action')
    
    query = AuditLog.query
    
    if user_id:
        query = query.filter_by(actor_id=user_id)
    
    if action:
        query = query.filter_by(action=action)
    
    logs = query.order_by(desc(AuditLog.timestamp))\
        .paginate(page=page, per_page=per_page, error_out=False)
    
    return jsonify({
        'logs': [{
            'id': l.id,
            'actor_id': l.actor_id,
            'actor_username': l.actor.username if l.actor else 'System',
            'action': l.action,
            'description': l.description,
            'timestamp': l.timestamp.isoformat(),
            'ip_address': l.ip_address,
            'user_agent': l.user_agent,
            'changed_data': json.loads(l.changed_data) if l.changed_data else None
        } for l in logs.items],
        'total': logs.total,
        'pages': logs.pages,
        'page': page
    })

# ========== ОТЧЕТЫ ==========

@admin_bp.route('/reports/export', methods=['GET'])
@admin_required
def export_report():
    """Экспорт отчета"""
    report_type = request.args.get('type', 'users')
    
    if report_type == 'users':
        users = User.query.all()
        data = [{
            'id': u.id,
            'username': u.username,
            'email': u.email,
            'role': u.role.value,
            'status': u.status.value,
            'balance': u.balance,
            'kyc_verified': u.kyc_verified,
            'registered_at': u.registered_at.isoformat(),
            'last_login': u.last_login.isoformat() if u.last_login else None,
            'country': u.country,
            'total_deposits': AdminService.get_user_total_deposits(u.id),
            'total_withdrawals': AdminService.get_user_total_withdrawals(u.id),
            'total_bets': AdminService.get_user_total_bets(u.id),
            'total_wins': AdminService.get_user_total_wins(u.id)
        } for u in users]
        
        csv_data = export_to_csv(data)
        output = StringIO(csv_data)
        output.seek(0)
        
        return send_file(
            output,
            mimetype='text/csv',
            as_attachment=True,
            download_name=f'users_report_{datetime.now().date()}.csv'
        )
    
    elif report_type == 'transactions':
        transactions = Transaction.query.order_by(desc(Transaction.timestamp)).limit(1000).all()
        data = [{
            'id': t.id,
            'user_id': t.user_id,
            'username': t.user.username if t.user else 'Unknown',
            'type': t.type.value,
            'amount': t.amount,
            'balance_before': t.balance_before,
            'balance_after': t.balance_after,
            'status': t.status,
            'timestamp': t.timestamp.isoformat(),
            'description': t.description
        } for t in transactions]
        
        csv_data = export_to_csv(data)
        output = StringIO(csv_data)
        output.seek(0)
        
        return send_file(
            output,
            mimetype='text/csv',
            as_attachment=True,
            download_name=f'transactions_report_{datetime.now().date()}.csv'
        )
    
    elif report_type == 'financial':
        # Финансовый отчет за последние 30 дней
        thirty_days_ago = datetime.utcnow() - timedelta(days=30)
        
        daily_data = []
        for i in range(30):
            date = thirty_days_ago + timedelta(days=i)
            next_date = date + timedelta(days=1)
            
            deposits = db.session.query(func.sum(Transaction.amount)).filter(
                Transaction.type == 'deposit',
                Transaction.status == 'completed',
                Transaction.timestamp >= date,
                Transaction.timestamp < next_date
            ).scalar() or 0
            
            withdrawals = db.session.query(func.sum(Payout.amount)).filter(
                Payout.status.in_(['completed', 'processing']),
                Payout.request_date >= date,
                Payout.request_date < next_date
            ).scalar() or 0
            
            bets = db.session.query(func.sum(Bet.amount)).filter(
                Bet.timestamp >= date,
                Bet.timestamp < next_date
            ).scalar() or 0
            
            wins = db.session.query(func.sum(Bet.win_amount)).filter(
                Bet.result == 'win',
                Bet.timestamp >= date,
                Bet.timestamp < next_date
            ).scalar() or 0
            
            profit = bets - wins
            
            daily_data.append({
                'date': date.date().isoformat(),
                'deposits': float(deposits),
                'withdrawals': float(withdrawals),
                'bets': float(bets),
                'wins': float(wins),
                'profit': float(profit),
                'net_profit': float(profit - withdrawals)
            })
        
        csv_data = export_to_csv(daily_data)
        output = StringIO(csv_data)
        output.seek(0)
        
        return send_file(
            output,
            mimetype='text/csv',
            as_attachment=True,
            download_name=f'financial_report_{datetime.now().date()}.csv'
        )
    
    elif report_type == 'games':
        games = Game.query.all()
        data = []
        
        for game in games:
            total_bets = AdminService.get_game_total_bets(game.id)
            total_wins = AdminService.get_game_total_wins(game.id)
            actual_rtp = (total_wins / total_bets * 100) if total_bets > 0 else 0
            
            data.append({
                'id': game.id,
                'title': game.title,
                'category': game.category,
                'min_bet': game.min_bet,
                'max_bet': game.max_bet,
                'target_rtp': game.rtp,
                'actual_rtp': round(actual_rtp, 2),
                'active': game.active,
                'maintenance': game.maintenance,
                'total_bets': float(total_bets),
                'total_wins': float(total_wins),
                'profit': float(total_bets - total_wins),
                'popularity': game.popularity
            })
        
        csv_data = export_to_csv(data)
        output = StringIO(csv_data)
        output.seek(0)
        
        return send_file(
            output,
            mimetype='text/csv',
            as_attachment=True,
            download_name=f'games_report_{datetime.now().date()}.csv'
        )
    
    return jsonify({'error': 'Invalid report type'}), 400

# ========== АНОНСЫ ==========

@admin_bp.route('/announcements', methods=['GET'])
@admin_required
def get_announcements():
    """Получение анонсов"""
    announcements = Announcement.query.order_by(desc(Announcement.created_at)).all()
    
    return jsonify({
        'announcements': [{
            'id': a.id,
            'title': a.title,
            'content': a.content,
            'type': a.type,
            'active': a.active,
            'created_at': a.created_at.isoformat(),
            'expires_at': a.expires_at.isoformat() if a.expires_at else None,
            'created_by': a.creator.username if a.creator else None
        } for a in announcements]
    })

@admin_bp.route('/announcements', methods=['POST'])
@admin_required
def create_announcement():
    """Создание анонса"""
    data = request.get_json()
    
    required_fields = ['title', 'content']
    for field in required_fields:
        if field not in data:
            return jsonify({'error': f'Missing required field: {field}'}), 400
    
    try:
        announcement = Announcement(
            title=data['title'],
            content=data['content'],
            type=data.get('type', 'info'),
            active=data.get('active', True),
            created_by=current_user.id
        )
        
        if 'expires_at' in data:
            announcement.expires_at = datetime.fromisoformat(data['expires_at'].replace('Z', '+00:00'))
        
        db.session.add(announcement)
        db.session.commit()
        
        # Аудит
        from utils.security import create_audit_log
        create_audit_log(
            'ANNOUNCEMENT_CREATE',
            f'Admin {current_user.username} created announcement: {announcement.title}',
            current_user.id,
            request
        )
        
        return jsonify({
            'message': 'Announcement created successfully',
            'announcement': {
                'id': announcement.id,
                'title': announcement.title
            }
        }), 201
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': f'Failed to create announcement: {str(e)}'}), 500

@admin_bp.route('/announcements/<int:announcement_id>', methods=['PUT'])
@admin_required
def update_announcement(announcement_id):
    """Обновление анонса"""
    announcement = Announcement.query.get_or_404(announcement_id)
    data = request.get_json()
    
    if 'title' in data:
        announcement.title = data['title']
    
    if 'content' in data:
        announcement.content = data['content']
    
    if 'type' in data:
        announcement.type = data['type']
    
    if 'active' in data:
        announcement.active = bool(data['active'])
    
    if 'expires_at' in data:
        announcement.expires_at = datetime.fromisoformat(data['expires_at'].replace('Z', '+00:00'))
    
    db.session.commit()
    
    return jsonify({
        'message': 'Announcement updated successfully',
        'announcement': {
            'id': announcement.id,
            'title': announcement.title,
            'active': announcement.active
        }
    })

@admin_bp.route('/announcements/<int:announcement_id>', methods=['DELETE'])
@admin_required
def delete_announcement(announcement_id):
    """Удаление анонса"""
    announcement = Announcement.query.get_or_404(announcement_id)
    
    db.session.delete(announcement)
    db.session.commit()
    
    return jsonify({'message': 'Announcement deleted successfully'})

# ========== СИСТЕМНЫЕ НАСТРОЙКИ ==========

@admin_bp.route('/settings', methods=['GET'])
@admin_required
def get_settings():
    """Получение системных настроек"""
    return jsonify({
        'system': {
            'site_name': 'BeaversCasino',
            'site_url': 'http://localhost:5000',
            'contact_email': 'support@beaverscasino.com',
            'support_phone': '+1-800-CASINO',
            'min_deposit': 10.00,
            'max_deposit': 10000.00,
            'min_withdrawal': 20.00,
            'max_withdrawal': 5000.00,
            'kyc_required': True,
            'kyc_threshold': 1000.00,  # Требовать KYC после этого депозита
            'welcome_bonus': 10.00,
            'referral_bonus': 25.00
        },
        'games': {
            'default_rtp': 96.5,
            'min_bet': 0.10,
            'max_bet': 1000.00,
            'max_multiplier': 10000
        },
        'security': {
            'login_attempts': 5,
            'lockout_time': 15,  # минут
            'session_timeout': 30,  # минут
            'password_min_length': 8,
            'require_2fa': False
        }
    })

@admin_bp.route('/settings', methods=['PUT'])
@admin_required
def update_settings():
    
    return jsonify({
        'message': 'Settings updated successfully',
        'note': 'In a real application, settings would be saved to database'
    })