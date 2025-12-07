import os
from datetime import timedelta
from dotenv import load_dotenv

load_dotenv()

class Config:
    # Безопасность
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'dev-secret-key'
    WTF_CSRF_SECRET_KEY = os.environ.get('CSRF_SECRET_KEY') or 'csrf-key'
    WTF_CSRF_ENABLED = True  # Включить CSRF
    
    # База данных SQLite (для курсового)
    basedir = os.path.abspath(os.path.dirname(__file__))
    SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASE_URL') or \
        'sqlite:///' + os.path.join(basedir, 'casino.db')
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    
    # Сессии
    SESSION_TYPE = 'filesystem'
    SESSION_FILE_DIR = './.flask_session/'
    SESSION_PERMANENT = False
    SESSION_USE_SIGNER = True
    PERMANENT_SESSION_LIFETIME = timedelta(hours=1)
    
    # JWT
    JWT_SECRET_KEY = os.environ.get('JWT_SECRET_KEY') or 'jwt-secret'
    JWT_ACCESS_TOKEN_EXPIRES = timedelta(hours=1)
    
    # Безопасность
    SECURITY_PASSWORD_SALT = os.environ.get('SECURITY_PASSWORD_SALT') or 'salt'
    BCRYPT_LOG_ROUNDS = 13
    
    # Flask-Limiter конфигурация
    RATELIMIT_STORAGE_URI = 'memory://'
    
    # Игровые лимиты
    MAX_BET = 10000
    MIN_BET = 1
    DAILY_LOSS_LIMIT = 1000
    SESSION_TIME_LIMIT = 1800  # 30 минут
    
    # Загрузка файлов
    MAX_CONTENT_LENGTH = 5 * 1024 * 1024  # 5MB
    UPLOAD_FOLDER = './uploads'
    ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'pdf'}
    
    # Отладка
    DEBUG = os.environ.get('DEBUG', 'True').lower() == 'true'
    ENV = os.environ.get('ENV', 'development')