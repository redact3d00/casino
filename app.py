from flask import Flask, render_template, jsonify, request, send_from_directory
from flask_login import LoginManager, current_user, login_required
from flask_bcrypt import Bcrypt
from flask_wtf.csrf import CSRFProtect, generate_csrf
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from flask_migrate import Migrate
from config import Config
import logging
import os
from datetime import datetime

# Импорт моделей
from models import db, User, UserRole

# Инициализация расширений
bcrypt = Bcrypt()
csrf = CSRFProtect()
login_manager = LoginManager()
limiter = Limiter(key_func=get_remote_address)
migrate = Migrate()

def create_app():
    app = Flask(__name__)
    app.config.from_object(Config)
    
    # Инициализация расширений
    db.init_app(app)
    bcrypt.init_app(app)
    csrf.init_app(app)
    login_manager.init_app(app)
    limiter.init_app(app)
    migrate.init_app(app, db)
    
    # Настройка Flask-Login
    login_manager.login_view = 'auth.show_login_form'
    login_manager.session_protection = "strong"
    
    @login_manager.user_loader
    def load_user(user_id):
        return User.query.get(int(user_id))
    
    @login_manager.unauthorized_handler
    def unauthorized():
        if request.path.startswith('/api/') or request.path.startswith('/auth/') or request.path.startswith('/admin/'):
            return jsonify({'error': 'Unauthorized'}), 401
        return render_template('login.html')
    
    # Импорт и регистрация Blueprints
    from routes.auth import auth_bp
    from routes.admin import admin_bp
    from routes.games import games_bp
    from routes.user import user_bp
    from routes.payments import payments_bp
    from routes.support import support_bp

    # Отключите CSRF для API endpoints
    csrf.exempt(auth_bp)
    csrf.exempt(admin_bp)
    csrf.exempt(games_bp)
    csrf.exempt(user_bp)
    csrf.exempt(payments_bp)
    
    app.register_blueprint(auth_bp, url_prefix='/auth')
    app.register_blueprint(admin_bp, url_prefix='/admin')
    app.register_blueprint(games_bp, url_prefix='/games')
    app.register_blueprint(user_bp, url_prefix='/user')
    app.register_blueprint(payments_bp, url_prefix='/payments')
    app.register_blueprint(support_bp, url_prefix='/support')
    
    # HTML маршруты (с CSRF)
    @app.route('/')
    def index():
        return render_template('index.html')
    
    @app.route('/dashboard')
    @login_required
    def dashboard():
        return render_template('dashboard.html')
    
    @app.route('/games')
    @login_required
    def games_page():
        return render_template('games.html')
    
    @app.route('/admin')
    @login_required
    def admin_panel():
        if current_user.role != UserRole.ADMIN:
            return jsonify({'error': 'Access denied'}), 403
        return render_template('admin/dashboard.html')
    
    @app.route('/api/health')
    def health_check():
        return jsonify({
            'status': 'healthy',
            'timestamp': datetime.now().isoformat(),
            'version': '1.0.0'
        })
    
    @app.route('/api/csrf-token', methods=['GET'])
    def get_csrf_token():
        token = generate_csrf()
        return jsonify({'csrf_token': token})
    
    # Для отладки - просмотр пользователей
    @app.route('/debug/users')
    @login_required
    def debug_users():
        users = User.query.all()
        return jsonify({
            'users': [{
                'id': u.id,
                'username': u.username,
                'email': u.email,
                'role': u.role.value,
                'status': u.status.value,
                'balance': u.balance
            } for u in users]
        })
    
    @app.route('/uploads/kyc/<filename>')
    @login_required
    def serve_kyc_file(filename):
        """Сервинг KYC файлов (с проверкой доступа)"""
        # В реальном приложении нужно проверять, что пользователь имеет доступ к файлу
        return send_from_directory('uploads/kyc', filename)

    # Обработка ошибок
    @app.errorhandler(404)
    def not_found_error(error):
        if request.path.startswith('/api/'):
            return jsonify({'error': 'Not found'}), 404
        return render_template('404.html'), 404
    
    @app.errorhandler(405)
    def method_not_allowed(error):
        if request.path.startswith('/api/'):
            return jsonify({'error': 'Method not allowed'}), 405
        return render_template('405.html'), 405
    
    @app.errorhandler(500)
    def internal_error(error):
        db.session.rollback()
        app.logger.error(f'Server error: {error}')
        if request.path.startswith('/api/'):
            return jsonify({'error': 'Internal server error'}), 500
        return render_template('500.html'), 500
    
    # Middleware для безопасности
    @app.after_request
    def add_security_headers(response):
        response.headers['X-Content-Type-Options'] = 'nosniff'
        response.headers['X-Frame-Options'] = 'DENY'
        response.headers['X-XSS-Protection'] = '1; mode=block'
        if 'Cache-Control' not in response.headers:
            response.headers['Cache-Control'] = 'no-store, no-cache, must-revalidate, max-age=0'
        return response
    
    # Настройка логирования
    setup_logging(app)
    
    return app

def setup_logging(app):
    if not app.debug:
        import logging
        from logging.handlers import RotatingFileHandler
        
        if not os.path.exists('logs'):
            os.mkdir('logs')
        
        file_handler = RotatingFileHandler(
            'logs/casino.log',
            maxBytes=10240,
            backupCount=10
        )
        file_handler.setFormatter(logging.Formatter(
            '%(asctime)s %(levelname)s: %(message)s [in %(pathname)s:%(lineno)d]'
        ))
        file_handler.setLevel(logging.INFO)
        app.logger.addHandler(file_handler)
        app.logger.setLevel(logging.INFO)

app = create_app()

if __name__ == '__main__':
    app.run(debug=app.config['DEBUG'])