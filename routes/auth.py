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


@auth_bp.route('/login', methods=['GET'])
def show_login_form():
    if current_user.is_authenticated:
        return render_template('dashboard.html')
    return render_template('login.html')

@auth_bp.route('/register', methods=['GET'])
def show_register_form():
    if current_user.is_authenticated:
        return render_template('dashboard.html')
    return render_template('register.html')


@auth_bp.route('/login', methods=['POST'])
def login():
    data = request.get_json()
    
    if not data:
        return jsonify({'error': 'No data provided'}), 400
    
    username = data.get('username')
    password = data.get('password')
    
    result = AuthService.login_user(username, password, request)
    
    if not result['success']:
        return jsonify({'error': result['error']}), 401
    
    user = result['user']
    
    login_user(user, remember=True)
    
    token = jwt.encode({
        'user_id': user.id,
        'exp': datetime.now() + timedelta(hours=24)
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
    
    login_user(user, remember=True)
    
    token = jwt.encode({
        'user_id': user.id,
        'exp': datetime.now() + timedelta(hours=24)
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
    result = AuthService.logout_user(current_user.id, request)
    
    logout_user()
    
    response = make_response(jsonify({'message': 'Logged out'}))
    response.delete_cookie('session_token')
    
    return response

@auth_bp.route('/profile', methods=['GET'])
@login_required
def get_profile():
    profile = AuthService.get_user_profile(current_user.id)
    
    if not profile:
        return jsonify({'error': 'User not found'}), 404
    
    return jsonify(profile)

@auth_bp.route('/profile', methods=['PUT'])
@login_required
def update_profile():
    data = request.get_json()
    
    result = AuthService.update_user_profile(current_user.id, data)
    
    if not result['success']:
        return jsonify({'error': result['error']}), 400
    
    return jsonify({'message': 'Profile updated successfully', 'changes': result['changes']})

@auth_bp.route('/change-password', methods=['POST'])
@login_required
def change_password():
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

@auth_bp.route('/kyc/status', methods=['GET'])
@login_required
def get_kyc_status():
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
    if not request.files:
        return jsonify({'error': 'No files provided'}), 400
    
    document_type = request.form.get('document_type')
    document_number = request.form.get('document_number')
    
    if not document_type:
        return jsonify({'error': 'Document type required'}), 400
    
    ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'pdf'}
    MAX_FILE_SIZE = 5 * 1024 * 1024 
    
    front_image = request.files.get('front_image')
    back_image = request.files.get('back_image')
    selfie_image = request.files.get('selfie_image')
    
    if not front_image or not selfie_image:
        return jsonify({'error': 'Front image and selfie are required'}), 400
    
    for file in [front_image, back_image, selfie_image]:
        if file and file.content_length > MAX_FILE_SIZE:
            return jsonify({'error': f'File {file.filename} is too large. Max 5MB.'}), 400
        
        if file and not ('.' in file.filename and file.filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS):
            return jsonify({'error': f'File {file.filename} has invalid extension'}), 400
    
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
    
    current_user.kyc_status = KYCStatus.PENDING
    current_user.kyc_verified = False
    
    db.session.commit()
    
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

def support_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated or current_user.role not in [UserRole.ADMIN, UserRole.MODERATOR, UserRole.SUPPORT]:
            return jsonify({'error': 'Support access required'}), 403
        return f(*args, **kwargs)
    return decorated_function

def staff_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated or current_user.role not in [UserRole.ADMIN, UserRole.MODERATOR, UserRole.SUPPORT]:
            return jsonify({'error': 'Staff access required'}), 403
        return f(*args, **kwargs)
    return decorated_function

def token_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated:
            return jsonify({'error': 'Authentication required'}), 401
        return f(*args, **kwargs)
    return decorated_function