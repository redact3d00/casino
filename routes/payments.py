from flask import Blueprint, request, jsonify
from flask_login import login_required, current_user
from services.payment_service import PaymentService

payments_bp = Blueprint('payments', __name__)

@payments_bp.route('/methods', methods=['GET'])
@login_required
def get_payment_methods():
    """Получение доступных методов оплаты"""
    methods = PaymentService.get_payment_methods()
    return jsonify({'methods': methods})

@payments_bp.route('/deposit', methods=['POST'])
@login_required
def create_deposit():
    """Создание депозита"""
    data = request.get_json()
    
    amount = float(data.get('amount', 0))
    method = data.get('method')
    
    if amount <= 0 or not method:
        return jsonify({'error': 'Invalid amount or method'}), 400
    
    result = PaymentService.create_deposit(current_user, amount, method, request)
    
    if not result['success']:
        return jsonify({'error': result['error']}), 400
    
    return jsonify(result)

@payments_bp.route('/withdraw', methods=['POST'])
@login_required
def request_withdrawal():
    """Запрос на вывод средств"""
    data = request.get_json()
    
    amount = float(data.get('amount', 0))
    method = data.get('method')
    account_details = data.get('account_details', {})
    
    if amount <= 0 or not method:
        return jsonify({'error': 'Invalid amount or method'}), 400
    
    result = PaymentService.request_withdrawal(current_user, amount, method, account_details, request)
    
    if not result['success']:
        return jsonify({'error': result['error']}), 400
    
    return jsonify(result)

@payments_bp.route('/withdraw/history', methods=['GET'])
@login_required
def get_withdrawal_history():
    """История выводов"""
    withdrawals = PaymentService.get_user_withdrawals(current_user.id)
    return jsonify({'withdrawals': withdrawals})