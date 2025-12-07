from models import db, User, Session, AuditLog, UserRole, UserStatus
from utils.security import validate_password, validate_email, create_audit_log
from flask_bcrypt import generate_password_hash, check_password_hash
from datetime import datetime
import jwt

class AuthService:
    
    @staticmethod
    def register_user(username, email, password, request):
        """Регистрация нового пользователя"""
        # Валидация данных
        if not username or not email or not password:
            return {'success': False, 'error': 'Missing required fields'}
        
        if not validate_email(email):
            return {'success': False, 'error': 'Invalid email format'}
        
        is_valid, message = validate_password(password)
        if not is_valid:
            return {'success': False, 'error': message}
        
        # Проверка существующего пользователя
        if User.query.filter_by(username=username).first():
            return {'success': False, 'error': 'Username already exists'}
        
        if User.query.filter_by(email=email).first():
            return {'success': False, 'error': 'Email already registered'}
        
        # Создание пользователя
        user = User(
            username=username,
            email=email,
            password_hash=generate_password_hash(password).decode('utf-8'),
            role=UserRole.PLAYER,
            status=UserStatus.VERIFICATION,
            registered_at=datetime.utcnow()
        )
        
        db.session.add(user)
        db.session.commit()
        
        # Создание сессии
        session = AuthService._create_session(user.id, request)
        
        # Аудит
        create_audit_log('REGISTER', f'User {username} registered', user.id, request)
        
        return {
            'success': True,
            'user': user,
            'session': session
        }
    
    @staticmethod
    def login_user(username, password, request):
        """Аутентификация пользователя"""
        user = User.query.filter_by(username=username).first()
        
        if not user or not check_password_hash(user.password_hash, password):
            return {'success': False, 'error': 'Invalid credentials'}
        
        if user.status == UserStatus.BLOCKED:
            return {'success': False, 'error': 'Account is blocked'}
        
        if user.status == UserStatus.VERIFICATION:
            return {'success': False, 'error': 'Account pending verification'}
        
        # Обновление последнего входа
        user.last_login = datetime.utcnow()
        
        # Создание новой сессии
        session = AuthService._create_session(user.id, request)
        
        db.session.commit()
        
        # Аудит
        create_audit_log('LOGIN', f'User {user.username} logged in', user.id, request)
        
        return {
            'success': True,
            'user': user,
            'session': session
        }
    
    @staticmethod
    def logout_user(user_id, request):
        """Выход пользователя"""
        # Завершение активной сессии
        session = Session.query.filter_by(
            user_id=user_id,
            active=True
        ).order_by(Session.login_time.desc()).first()
        
        if session:
            session.active = False
            session.logout_time = datetime.utcnow()
            db.session.commit()
        
        # Аудит
        create_audit_log('LOGOUT', 'User logged out', user_id, request)
        
        return {'success': True}
    
    @staticmethod
    def _create_session(user_id, request):
        """Создание новой сессии"""
        session = Session(
            user_id=user_id,
            ip_address=request.remote_addr,
            user_agent=request.user_agent.string,
            login_time=datetime.utcnow(),
            active=True
        )
        
        # Генерация JWT токена
        token = jwt.encode({
            'user_id': user_id,
            'exp': datetime.now().timestamp() + 86400  # 24 часа
        }, 'secret-key', algorithm='HS256')
        
        session.token = token
        db.session.add(session)
        db.session.commit()
        
        return session
    
    @staticmethod
    def get_user_profile(user_id):
        """Получение профиля пользователя"""
        user = User.query.get(user_id)
        if not user:
            return None
        
        return {
            'id': user.id,
            'username': user.username,
            'email': user.email,
            'role': user.role.value,
            'balance': user.balance,
            'status': user.status.value,
            'registered_at': user.registered_at.isoformat(),
            'last_login': user.last_login.isoformat() if user.last_login else None,
            'kyc_verified': user.kyc_verified
        }
    
    @staticmethod
    def update_user_profile(user_id, data):
        """Обновление профиля пользователя"""
        user = User.query.get(user_id)
        if not user:
            return {'success': False, 'error': 'User not found'}
        
        changes = []
        
        if 'email' in data and data['email'] != user.email:
            from utils.validators import validate_email
            if not validate_email(data['email']):
                return {'success': False, 'error': 'Invalid email format'}
            user.email = data['email']
            changes.append('email updated')
        
        if 'bet_limit' in data:
            user.bet_limit = max(1, min(float(data['bet_limit']), 10000))
            changes.append('bet limit updated')
        
        db.session.commit()
        
        return {
            'success': True,
            'changes': changes
        }