from models import db, User, Session, AuditLog, UserRole, UserStatus
from utils.security import validate_password, validate_email, create_audit_log
from flask_bcrypt import generate_password_hash, check_password_hash  # Фикс: Импорт bcrypt
from datetime import datetime
import jwt

class AuthService:
    @staticmethod
    def register_user(username, email, password, request):
        if not username or not email or not password:
            return {'success': False, 'error': 'Missing required fields'}
        if not validate_email(email):  
            return {'success': False, 'error': 'Invalid email format'}
        is_valid, message = validate_password(password)
        if not is_valid:
            return {'success': False, 'error': message}
        if User.query.filter_by(username=username).first():
            return {'success': False, 'error': 'Username already exists'}
        if User.query.filter_by(email=email).first():
            return {'success': False, 'error': 'Email already registered'}

        user = User(
            username=username,
            email=email,
            password_hash=generate_password_hash(password).decode('utf-8'),
            role=UserRole.PLAYER,
            status=UserStatus.VERIFICATION,
            registered_at=datetime.now()
        )
        db.session.add(user)
        db.session.commit()

        session = AuthService._create_session(user.id, request)
        create_audit_log('REGISTER', f'User {username} registered', user.id, request)
        return {'success': True, 'user': user, 'session': session}

    @staticmethod
    def login_user(username, password, request):
        user = User.query.filter_by(username=username).first()
        if not user or not check_password_hash(user.password_hash, password):
            return {'success': False, 'error': 'Invalid credentials'}
        if user.status == UserStatus.BLOCKED:
            return {'success': False, 'error': 'Account is blocked'}
        if user.status == UserStatus.VERIFICATION:
            return {'success': False, 'error': 'Account pending verification'}

        user.last_login = datetime.now()
        session = AuthService._create_session(user.id, request)
        db.session.commit()
        create_audit_log('LOGIN', f'User {user.username} logged in', user.id, request)
        return {'success': True, 'user': user, 'session': session}

    
    @staticmethod
    def logout_user(user_id, request):
        session = Session.query.filter_by(
            user_id=user_id,
            active=True
        ).order_by(Session.login_time.desc()).first()
        
        if session:
            session.active = False
            session.logout_time = datetime.now()
            db.session.commit()
        
        create_audit_log('LOGOUT', 'User logged out', user_id, request)
        
        return {'success': True}
    
    @staticmethod
    def _create_session(user_id, request):
        session = Session(
            user_id=user_id,
            ip_address=request.remote_addr,
            user_agent=request.user_agent.string,
            login_time=datetime.now(),
            active=True
        )
        
        token = jwt.encode({
            'user_id': user_id,
            'exp': datetime.now().timestamp() + 86400 
        }, 'secret-key', algorithm='HS256')
        
        session.token = token
        db.session.add(session)
        db.session.commit()
        
        return session
    
    @staticmethod
    def get_user_profile(user_id):
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