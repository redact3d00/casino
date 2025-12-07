from flask import Blueprint, request, jsonify, make_response, render_template
from flask_login import login_user, logout_user, current_user, login_required
from services.auth_service import AuthService
from services.kyc_service import KYCService
from models import UserRole, db, User, KYCDocument, KYCStatus
import jwt
from datetime import datetime, timedelta
from functools import wraps
import os
from werkzeug.utils import secure_filename

auth_bp = Blueprint('auth', __name__)

# ========== HTML СТРАНИЦЫ ==========

@auth_bp.route('/login', methods=['GET'])
def show_login_form():
    """Показать HTML форму входа"""
    if current_user.is_authenticated:
        return render_template('dashboard.html')
    return render_template('login.html')

@auth_bp.route('/register', methods=['GET'])
def show_register_form():
    """Показать HTML форму регистрации"""
    if current_user.is_authenticated:
        return render_template('dashboard.html')
    return render_template('register.html')

# ========== API ЭНДПОИНТЫ ==========

@auth_bp.route('/login', methods=['POST'])
def login():
    """API: Вход пользователя"""
    data = request.get_json()
    
    if not data:
        return jsonify({'error': 'No data provided'}), 400
    
    username = data.get('username')
    password = data.get('password')
    
    result = AuthService.login_user(username, password, request)
    
    if not result['success']:
        return jsonify({'error': result['error']}), 401
    
    user = result['user']
    
    # Вход через Flask-Login
    login_user(user, remember=True)
    
    # Генерация JWT токена
    token = jwt.encode({
        'user_id': user.id,
        'exp': datetime.utcnow() + timedelta(hours=24)
    }, 'secret-key', algorithm='HS256')
    
    response = make_response(jsonify({
        'message': 'Login successful',
        'user': {
            'id': user.id,
            'username': user.username,
            'role': user.role.value,
            'balance': user.balance,
            'kyc_verified': user.kyc_verified
        },
        'redirect': '/dashboard'
    }))
    
    # Установка cookie
    response.set_cookie(
        'session_token',
        token,
        httponly=True,
        secure=False,
        samesite='Strict',
        max_age=86400
    )
    
    return response

@auth_bp.route('/register', methods=['POST'])
def register():
    """API: Регистрация пользователя"""
    data = request.get_json()
    
    if not data:
        return jsonify({'error': 'No data provided'}), 400
    
    username = data.get('username')
    email = data.get('email')
    password = data.get('password')
    
    result = AuthService.register_user(username, email, password, request)
    
    if not result['success']:
        return jsonify({'error': result['error']}), 400
    
    user = result['user']
    
    # Вход пользователя после регистрации
    login_user(user, remember=True)
    
    # Генерация JWT токена
    token = jwt.encode({
        'user_id': user.id,
        'exp': datetime.utcnow() + timedelta(hours=24)
    }, 'secret-key', algorithm='HS256')
    
    response = make_response(jsonify({
        'message': 'Registration successful',
        'user': {
            'id': user.id,
            'username': user.username,
            'role': user.role.value,
            'balance': user.balance,
            'kyc_verified': user.kyc_verified
        },
        'redirect': '/dashboard'
    }), 201)
    
    # Установка HTTP-only cookie
    response.set_cookie(
        'session_token',
        token,
        httponly=True,
        secure=False,
        samesite='Strict',
        max_age=86400
    )
    
    return response

@auth_bp.route('/logout', methods=['POST'])
@login_required
def logout():
    """API: Выход пользователя"""
    result = AuthService.logout_user(current_user.id, request)
    
    logout_user()
    
    response = make_response(jsonify({'message': 'Logged out'}))
    response.delete_cookie('session_token')
    
    return response

@auth_bp.route('/profile', methods=['GET'])
@login_required
def get_profile():
    """API: Получение профиля пользователя"""
    profile = AuthService.get_user_profile(current_user.id)
    
    if not profile:
        return jsonify({'error': 'User not found'}), 404
    
    return jsonify(profile)

@auth_bp.route('/profile', methods=['PUT'])
@login_required
def update_profile():
    """API: Обновление профиля"""
    data = request.get_json()
    
    result = AuthService.update_user_profile(current_user.id, data)
    
    if not result['success']:
        return jsonify({'error': result['error']}), 400
    
    return jsonify({'message': 'Profile updated successfully', 'changes': result['changes']})

@auth_bp.route('/change-password', methods=['POST'])
@login_required
def change_password():
    """API: Смена пароля"""
    data = request.get_json()
    
    current_password = data.get('current_password')
    new_password = data.get('new_password')
    
    if not current_password or not new_password:
        return jsonify({'error': 'Current and new password required'}), 400
    
    result = AuthService.change_password(current_user.id, current_password, new_password)
    
    if not result['success']:
        return jsonify({'error': result['error']}), 400
    
    return jsonify({'message': 'Password changed successfully'})

@auth_bp.route('/status', methods=['GET'])
def check_auth_status():
    """API: Проверка статуса аутентификации"""
    if current_user.is_authenticated:
        return jsonify({
            'authenticated': True,
            'user': {
                'id': current_user.id,
                'username': current_user.username,
                'role': current_user.role.value,
                'balance': current_user.balance,
                'kyc_verified': current_user.kyc_verified
            }
        })
    return jsonify({'authenticated': False})

# ========== KYC ЭНДПОИНТЫ ==========

@auth_bp.route('/kyc/status', methods=['GET'])
@login_required
def get_kyc_status():
    """API: Получение статуса KYC"""
    documents = KYCDocument.query.filter_by(user_id=current_user.id).all()
    
    return jsonify({
        'kyc_verified': current_user.kyc_verified,
        'kyc_status': current_user.kyc_status.value,
        'documents': [{
            'id': doc.id,
            'document_type': doc.document_type,
            'status': doc.status.value,
            'submitted_at': doc.submitted_at.isoformat() if doc.submitted_at else None,
            'verified_at': doc.verified_at.isoformat() if doc.verified_at else None,
            'rejection_reason': doc.rejection_reason
        } for doc in documents]
    })

@auth_bp.route('/kyc/submit', methods=['POST'])
@login_required
def submit_kyc():
    """API: Отправка KYC документов"""
    if not request.files:
        return jsonify({'error': 'No files provided'}), 400
    
    document_type = request.form.get('document_type')
    document_number = request.form.get('document_number')
    
    if not document_type:
        return jsonify({'error': 'Document type required'}), 400
    
    # Проверяем лимиты файлов
    ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'pdf'}
    MAX_FILE_SIZE = 5 * 1024 * 1024  # 5MB
    
    front_image = request.files.get('front_image')
    back_image = request.files.get('back_image')
    selfie_image = request.files.get('selfie_image')
    
    if not front_image or not selfie_image:
        return jsonify({'error': 'Front image and selfie are required'}), 400
    
    # Проверка размера файлов
    for file in [front_image, back_image, selfie_image]:
        if file and file.content_length > MAX_FILE_SIZE:
            return jsonify({'error': f'File {file.filename} is too large. Max 5MB.'}), 400
        
        if file and not ('.' in file.filename and file.filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS):
            return jsonify({'error': f'File {file.filename} has invalid extension'}), 400
    
    # Сохраняем файлы
    upload_folder = 'uploads/kyc'
    os.makedirs(upload_folder, exist_ok=True)
    
    def save_file(file):
        if not file:
            return None
        filename = secure_filename(f"{current_user.id}_{document_type}_{datetime.now().timestamp()}_{file.filename}")
        filepath = os.path.join(upload_folder, filename)
        file.save(filepath)
        return filepath
    
    front_path = save_file(front_image)
    back_path = save_file(back_image) if back_image else None
    selfie_path = save_file(selfie_image)
    
    # Создаем запись KYC
    kyc_doc = KYCDocument(
        user_id=current_user.id,
        document_type=document_type,
        document_number=document_number,
        front_image=front_path,
        back_image=back_path,
        selfie_image=selfie_path,
        status=KYCStatus.PENDING
    )
    
    db.session.add(kyc_doc)
    
    # Обновляем статус пользователя
    current_user.kyc_status = KYCStatus.PENDING
    current_user.kyc_verified = False
    
    db.session.commit()
    
    # Аудит
    from utils.security import create_audit_log
    create_audit_log(
        'KYC_SUBMIT',
        f'User {current_user.username} submitted KYC documents',
        current_user.id,
        request
    )
    
    return jsonify({
        'message': 'KYC documents submitted successfully',
        'kyc_id': kyc_doc.id,
        'status': 'pending'
    })

@auth_bp.route('/kyc/history', methods=['GET'])
@login_required
def get_kyc_history():
    """API: История KYC заявок"""
    documents = KYCDocument.query.filter_by(user_id=current_user.id)\
        .order_by(KYCDocument.submitted_at.desc())\
        .all()
    
    return jsonify({
        'documents': [{
            'id': doc.id,
            'document_type': doc.document_type,
            'document_number': doc.document_number,
            'status': doc.status.value,
            'submitted_at': doc.submitted_at.isoformat() if doc.submitted_at else None,
            'verified_at': doc.verified_at.isoformat() if doc.verified_at else None,
            'verified_by': doc.verified_by,
            'rejection_reason': doc.rejection_reason
        } for doc in documents]
    })

# ========== ЛИМИТЫ И САМОИСКЛЮЧЕНИЕ ==========

@auth_bp.route('/limits', methods=['GET'])
@login_required
def get_limits():
    """API: Получение лимитов пользователя"""
    return jsonify({
        'daily_deposit_limit': current_user.daily_deposit_limit,
        'daily_loss_limit': current_user.daily_loss_limit,
        'session_time_limit': current_user.session_time_limit,
        'cool_off_period': current_user.cool_off_period,
        'self_excluded_until': current_user.self_excluded_until.isoformat() if current_user.self_excluded_until else None
    })

@auth_bp.route('/limits', methods=['PUT'])
@login_required
def update_limits():
    """API: Обновление лимитов"""
    data = request.get_json()
    
    changes = []
    
    if 'daily_deposit_limit' in data:
        current_user.daily_deposit_limit = max(0, float(data['daily_deposit_limit']))
        changes.append(f"Daily deposit limit set to ${current_user.daily_deposit_limit}")
    
    if 'daily_loss_limit' in data:
        current_user.daily_loss_limit = max(0, float(data['daily_loss_limit']))
        changes.append(f"Daily loss limit set to ${current_user.daily_loss_limit}")
    
    if 'session_time_limit' in data:
        current_user.session_time_limit = max(0, int(data['session_time_limit']))
        changes.append(f"Session time limit set to {current_user.session_time_limit} minutes")
    
    if 'cool_off_period' in data:
        current_user.cool_off_period = max(0, int(data['cool_off_period']))
        changes.append(f"Cool-off period set to {current_user.cool_off_period} days")
    
    db.session.commit()
    
    return jsonify({
        'message': 'Limits updated successfully',
        'changes': changes
    })

@auth_bp.route('/self-exclude', methods=['POST'])
@login_required
def self_exclude():
    """API: Самоисключение"""
    data = request.get_json()
    
    duration_days = int(data.get('duration', 30))
    reason = data.get('reason', '')
    
    if duration_days not in [1, 7, 30, 90, 180, 365, 9999]:
        return jsonify({'error': 'Invalid duration'}), 400
    
    # Устанавливаем дату окончания самоисключения
    from datetime import datetime, timedelta
    if duration_days == 9999:  # Permanent
        exclude_until = datetime.utcnow() + timedelta(days=36500)  # 100 лет
    else:
        exclude_until = datetime.utcnow() + timedelta(days=duration_days)
    
    current_user.self_excluded_until = exclude_until
    current_user.status = 'blocked'
    
    # Завершение всех активных сессий
    from models import Session
    active_sessions = Session.query.filter_by(
        user_id=current_user.id,
        active=True
    ).all()
    
    for session in active_sessions:
        session.active = False
        session.logout_time = datetime.utcnow()
    
    # Аудит
    from utils.security import create_audit_log
    create_audit_log(
        'SELF_EXCLUDE',
        f'User {current_user.username} self-excluded for {duration_days} days. Reason: {reason}',
        current_user.id,
        request
    )
    
    db.session.commit()
    
    return jsonify({
        'message': f'Account self-excluded for {duration_days} days',
        'reactivation_date': exclude_until.isoformat()
    })

@auth_bp.route('/sessions', methods=['GET'])
@login_required
def get_sessions():
    """API: История сессий"""
    from models import Session
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

# ========== ДЕКОРАТОРЫ ДЛЯ ПРОВЕРКИ РОЛЕЙ ==========

def admin_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated or current_user.role != UserRole.ADMIN:
            return jsonify({'error': 'Admin access required'}), 403
        return f(*args, **kwargs)
    return decorated_function

def moderator_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated or current_user.role not in [UserRole.ADMIN, UserRole.MODERATOR]:
            return jsonify({'error': 'Moderator access required'}), 403
        return f(*args, **kwargs)
    return decorated_function

def token_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated:
            return jsonify({'error': 'Authentication required'}), 401
        return f(*args, **kwargs)
    return decorated_function