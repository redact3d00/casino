import re
import bcrypt
import hashlib
import secrets
from datetime import datetime
from flask import request
from models import db, AuditLog

def validate_password(password):
    """Валидация пароля"""
    if len(password) < 8:
        return False, "Password must be at least 8 characters"
    
    if not re.search(r"[A-Z]", password):
        return False, "Password must contain at least one uppercase letter"
    
    if not re.search(r"[a-z]", password):
        return False, "Password must contain at least one lowercase letter"
    
    if not re.search(r"\d", password):
        return False, "Password must contain at least one digit"
    
    if not re.search(r"[!@#$%^&*(),.?\":{}|<>]", password):
        return False, "Password must contain at least one special character"
    
    return True, "Password is valid"

def validate_email(email):
    """Валидация email"""
    pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    return re.match(pattern, email) is not None

def generate_password_hash(password):
    """Генерация хеша пароля"""
    return bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')

def check_password_hash(password_hash, password):
    """Проверка пароля"""
    return bcrypt.checkpw(password.encode('utf-8'), password_hash.encode('utf-8'))

def create_audit_log(action, description, user_id=None, request_obj=None):
    """Создание записи аудита"""
    try:
        ip_address = request_obj.remote_addr if request_obj else 'unknown'
        user_agent = request_obj.user_agent.string if request_obj else 'unknown'
        
        log = AuditLog(
            actor_id=user_id,
            action=action,
            description=description,
            ip_address=ip_address,
            user_agent=user_agent,
            timestamp=datetime.now()
        )
        db.session.add(log)
        db.session.commit()
        return True
    except Exception as e:
        print(f"Failed to create audit log: {e}")
        return False

def generate_secure_random():
    """Генерация криптографически безопасного случайного числа"""
    return secrets.randbelow(10000) / 10000.0

def hash_string(input_string):
    """Хеширование строки"""
    return hashlib.sha256(input_string.encode()).hexdigest()