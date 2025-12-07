from flask import Blueprint, request, jsonify
from flask_login import login_required, current_user
from services.payment_service import PaymentService
from services.auth_service import AuthService
from models import db, Session, Bonus
from datetime import datetime, timedelta

user_bp = Blueprint('user', __name__)

@user_bp.route('/profile', methods=['GET'])
@login_required
def get_profile():
    """Получение профиля пользователя"""
    profile = AuthService.get_user_profile(current_user.id)
    return jsonify(profile)

@user_bp.route('/profile', methods=['PUT'])
@login_required
def update_profile():
    """Обновление профиля"""
    data = request.get_json()
    
    result = AuthService.update_user_profile(current_user.id, data)
    
    if not result['success']:
        return jsonify({'error': result['error']}), 400
    
    return jsonify({'message': 'Profile updated successfully'})

@user_bp.route('/transactions', methods=['GET'])
@login_required
def get_transactions():
    """История транзакций пользователя"""
    page = request.args.get('page', 1, type=int)
    per_page = request.args.get('per_page', 50, type=int)
    
    result = PaymentService.get_user_transactions(current_user.id, page, per_page)
    return jsonify(result)

@user_bp.route('/sessions', methods=['GET'])
@login_required
def get_sessions():
    """История сессий пользователя"""
    sessions = Session.query.filter_by(user_id=current_user.id)\
        .order_by(Session.login_time.desc())\
        .limit(20)\
        .all()
    
    return jsonify({
        'sessions': [{
            'id': s.id,
            'ip_address': s.ip_address,
            'device': s.device,
            'browser': s.browser,
            'login_time': s.login_time.isoformat(),
            'logout_time': s.logout_time.isoformat() if s.logout_time else None,
            'active': s.active
        } for s in sessions]
    })

@user_bp.route('/bonuses', methods=['GET'])
@login_required
def get_bonuses():
    """Бонусы пользователя"""
    bonuses = Bonus.query.filter_by(user_id=current_user.id)\
        .order_by(Bonus.activated_at.desc())\
        .all()
    
    return jsonify({
        'bonuses': [{
            'id': b.id,
            'type': b.type,
            'amount': b.amount,
            'spins': b.spins,
            'wager_requirement': b.wager_requirement,
            'wagered_amount': b.wagered_amount,
            'activated_at': b.activated_at.isoformat(),
            'expires_at': b.expires_at.isoformat() if b.expires_at else None,
            'status': b.status.value
        } for b in bonuses]
    })

@user_bp.route('/self-exclude', methods=['POST'])
@login_required
def self_exclude():
    """Самоисключение"""
    data = request.get_json()
    duration_days = data.get('duration', 30)
    
    if duration_days not in [1, 7, 30, 90, 180, 365]:
        return jsonify({'error': 'Invalid duration'}), 400
    
    from models import UserStatus
    
    # Блокировка аккаунта
    current_user.status = UserStatus.BLOCKED
    
    # Завершение всех активных сессий
    active_sessions = Session.query.filter_by(
        user_id=current_user.id,
        active=True
    ).all()
    
    for session in active_sessions:
        session.active = False
        session.logout_time = datetime.now()
    
    db.session.commit()
    
    return jsonify({
        'message': f'Account self-excluded for {duration_days} days',
        'reactivation_date': (datetime.now() + timedelta(days=duration_days)).isoformat()
    })