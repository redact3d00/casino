import os
from flask import Flask, send_from_directory, jsonify, render_template, request, redirect, url_for
from flask_cors import CORS
from flask_login import LoginManager, current_user, login_required
from flask_wtf.csrf import CSRFProtect
from flask_migrate import Migrate
from models import db, User
from config import Config

def create_app():
    app = Flask(__name__, static_folder='static', template_folder='templates')
    app.config.from_object(Config)
    CORS(app, supports_credentials=True)

    db.init_app(app)
    login_manager = LoginManager()
    login_manager.init_app(app)
    login_manager.login_view = 'login_page'

    csrf = CSRFProtect(app)
    migrate = Migrate(app, db)

    @login_manager.user_loader
    def load_user(user_id):
        try:
            return User.query.get(int(user_id))
        except:
            return None

    from routes.auth import auth_bp, admin_required, moderator_required, support_required, staff_required
    from routes.games import games_bp
    from routes.admin import admin_bp
    from routes.payments import payments_bp
    from routes.support import support_bp
    from routes.user import user_bp

    app.register_blueprint(auth_bp, url_prefix='/api/auth')
    app.register_blueprint(games_bp, url_prefix='/api/games')
    app.register_blueprint(admin_bp, url_prefix='/api/admin')
    app.register_blueprint(payments_bp, url_prefix='/api/payments')
    app.register_blueprint(support_bp, url_prefix='/api/support')
    app.register_blueprint(user_bp, url_prefix='/api/user')

    csrf.exempt('routes.auth.logout')
    csrf.exempt(games_bp)    
    csrf.exempt(admin_bp)      
    csrf.exempt(payments_bp)   
    csrf.exempt(support_bp)    
    csrf.exempt(user_bp)       
    csrf.exempt(auth_bp)

    @app.route('/')
    def index():
        return render_template('index.html')

    @app.route('/games')
    @login_required
    def games_page():
        return render_template('games.html')

    @app.route('/dashboard')
    @login_required
    def dashboard():
        return render_template('dashboard.html')

    @app.route('/admin')
    @login_required
    def admin_dashboard():
        if current_user.role.value not in ['admin', 'moderator', 'support']:
            return redirect(url_for('index'))
        return render_template('admin/dashboard.html')

    @app.route('/admin/support-dashboard')
    @login_required
    def support_dashboard_page():
        if current_user.role.value not in ['admin', 'moderator', 'support']:
            return redirect(url_for('index'))
        return render_template('admin/support_dashboard.html')

    @app.route('/admin/users')
    @login_required
    def admin_users():
        if current_user.role.value not in ['admin', 'moderator']:
            return redirect(url_for('index'))
        return render_template('admin/users.html')

    @app.route('/admin/create-staff')
    @login_required
    def admin_create_staff():
        if current_user.role.value != 'admin':
            return redirect(url_for('index'))
        return render_template('admin/create-staff.html')

    @app.route('/login')
    def login_page():
        if current_user.is_authenticated:
            return redirect(url_for('dashboard'))
        return render_template('login.html')

    @app.route('/register')
    def register_page():
        if current_user.is_authenticated:
            return redirect(url_for('dashboard'))
        return render_template('register.html')

    @app.route('/support')
    @login_required
    def support_page():
        return render_template('support.html')

    @app.route('/static/<path:filename>')
    def static_files(filename):
        return send_from_directory('static', filename)

    @app.route('/health')
    def health_check():
        return jsonify({'status': 'ok', 'service': 'casino'})

    @app.route('/api/auth/status')
    def auth_status():
        if current_user.is_authenticated:
            return jsonify({
                'authenticated': True,
                'user': {
                    'id': current_user.id,
                    'username': current_user.username,
                    'role': current_user.role.value,
                    'balance': current_user.balance
                }
            })
        return jsonify({'authenticated': False})

    @app.route('/profile')
    @login_required
    def profile():
        return render_template('profile.html')

    @app.route('/edit-profile')
    @login_required
    def edit_profile():
        return render_template('edit_profile.html')

    @app.route('/payments')
    @login_required
    def payments():
        return render_template('payments.html')

    @app.route('/deposit')
    @login_required
    def deposit():
        return render_template('deposit.html')

    @app.route('/request-withdrawal')
    @login_required
    def request_withdrawal():
        return render_template('request_withdrawal.html')

    @app.route('/support/ticket/<int:ticket_id>')
    @login_required
    def support_ticket(ticket_id):
        return render_template('support_ticket.html', ticket_id=ticket_id)

    @app.route('/admin/transactions')
    @login_required
    @admin_required
    def admin_transactions():
        return render_template('admin/transactions.html')

    @app.route('/admin/payouts')
    @login_required
    @admin_required
    def admin_payouts():
        return render_template('admin/payouts.html')

    @app.route('/admin/kyc')
    @login_required
    @support_required
    def admin_kyc():
        return render_template('admin/kyc.html')

    @app.route('/admin/audit')
    @login_required
    @admin_required
    def admin_audit():
        return render_template('admin/audit.html')

    @app.route('/admin/reports')
    @login_required
    @admin_required
    def admin_reports():
        return render_template('admin/reports.html')

    @app.route('/admin/games')
    @login_required
    @moderator_required
    def admin_games():
        return render_template('admin/games.html')

    @app.route('/admin/staff')
    @login_required
    @admin_required
    def admin_staff():
        return render_template('admin/staff.html')

    @app.errorhandler(400)
    def bad_request(error):
        if request.path.startswith('/api/'):
            return jsonify({'error': 'Bad Request'}), 400
        return render_template('400.html'), 400

    @app.errorhandler(404)
    def not_found(error):
        return render_template('404.html'), 404

    @app.errorhandler(401)
    def unauthorized(error):
        if request.path.startswith('/api/'):
            return jsonify({'error': 'Unauthorized'}), 401
        return redirect(url_for('login_page'))

    @app.errorhandler(403)
    def forbidden(error):
        if request.path.startswith('/api/'):
            return jsonify({'error': 'Forbidden'}), 403
        return render_template('403.html'), 403

    @app.errorhandler(500)
    def internal_error(error):
        if request.path.startswith('/api/'):
            return jsonify({'error': 'Internal server error'}), 500
        return render_template('500.html'), 500

    @app.context_processor
    def inject_user():
        return dict(current_user=current_user)

    return app

app = create_app()

if __name__ == '__main__':
    with app.app_context():
        db.create_all()
        print("✅ Database tables created")
    print("Casino Server starting...")
    print(f"http://localhost:5000")
    print("-" * 50)
    app.run(host='0.0.0.0', port=5000, debug=True)