from models import db, Transaction, Payout, AuditLog, TransactionType, PayoutStatus
from utils.security import create_audit_log
from utils.helpers import generate_reference
from datetime import datetime
import json

class PaymentService:
    
    # Конфигурация платежных методов
    PAYMENT_METHODS = {
        'stripe': {'min': 5, 'max': 5000, 'fee_percent': 2.5},
        'paypal': {'min': 10, 'max': 3000, 'fee_percent': 3.0},
        'crypto': {'min': 20, 'max': 10000, 'fee_percent': 1.0}
    }
    
    @staticmethod
    def get_payment_methods():
        """Получение доступных методов оплаты"""
        methods = []
        for method_id, config in PaymentService.PAYMENT_METHODS.items():
            method_name = {
                'stripe': 'Credit Card',
                'paypal': 'PayPal',
                'crypto': 'Cryptocurrency'
            }.get(method_id, method_id)
            
            methods.append({
                'id': method_id,
                'name': method_name,
                'min_amount': config['min'],
                'max_amount': config['max'],
                'fee_percent': config['fee_percent'],
                'processing_time': 'Instant' if method_id in ['stripe', 'paypal'] else '5-30 minutes'
            })
        
        return methods
    
    @staticmethod
    def create_deposit(user, amount, method, request):
        """Создание депозита"""
        if method not in PaymentService.PAYMENT_METHODS:
            return {'success': False, 'error': 'Invalid payment method'}
        
        method_config = PaymentService.PAYMENT_METHODS[method]
        
        # Проверка лимитов
        if amount < method_config['min']:
            return {'success': False, 'error': f'Minimum amount is {method_config["min"]}'}
        if amount > method_config['max']:
            return {'success': False, 'error': f'Maximum amount is {method_config["max"]}'}
        
        # Расчет комиссии
        fee = amount * (method_config['fee_percent'] / 100)
        net_amount = amount - fee
        
        # Создание транзакции
        transaction = Transaction(
            user_id=user.id,
            type=TransactionType.DEPOSIT,
            amount=amount,
            balance_before=user.balance,
            balance_after=user.balance + net_amount,
            status='pending',
            description=f'Deposit via {method}',
            reference=generate_reference('DEP'),
            timestamp=datetime.utcnow()
        )
        
        db.session.add(transaction)
        db.session.commit()
        
        # В реальном приложении здесь была бы интеграция с платежным шлюзом
        # Для демо просто отмечаем как выполненное
        transaction.status = 'completed'
        user.balance += net_amount
        db.session.commit()
        
        # Аудит
        create_audit_log(
            'DEPOSIT',
            f'User deposited {amount} via {method}',
            user.id,
            request
        )
        
        return {
            'success': True,
            'transaction_id': transaction.id,
            'amount': amount,
            'fee': fee,
            'net_amount': net_amount,
            'new_balance': user.balance
        }
    
    @staticmethod
    def request_withdrawal(user, amount, method, account_details, request):
        """Запрос на вывод средств"""
        # Проверка минимальной суммы
        if amount < 20:
            return {'success': False, 'error': 'Minimum withdrawal amount is 20'}
        
        # Проверка баланса
        if amount > user.balance:
            return {'success': False, 'error': 'Insufficient balance'}
        
        # Проверка KYC
        if not user.kyc_verified:
            return {'success': False, 'error': 'KYC verification required'}
        
        # Проверка дневного лимита
        today = datetime.utcnow().date()
        daily_withdrawals = db.session.query(db.func.sum(Payout.amount)).filter(
            Payout.user_id == user.id,
            Payout.status.in_([PayoutStatus.PROCESSING.value, PayoutStatus.COMPLETED.value]),
            db.func.date(Payout.request_date) == today
        ).scalar() or 0
        
        if daily_withdrawals + amount > 10000:
            return {'success': False, 'error': 'Daily withdrawal limit exceeded'}
        
        # Расчет комиссии
        fee = max(1.0, amount * 0.02)
        net_amount = amount - fee
        
        # Создание выплаты
        payout = Payout(
            user_id=user.id,
            amount=amount,
            method=method,
            status=PayoutStatus.PROCESSING,
            account_details=json.dumps(account_details),
            fee=fee,
            request_date=datetime.utcnow()
        )
        
        # Транзакция вывода
        transaction = Transaction(
            user_id=user.id,
            type=TransactionType.WITHDRAWAL,
            amount=amount,
            balance_before=user.balance,
            balance_after=user.balance - amount,
            status='processing',
            description=f'Withdrawal via {method}',
            timestamp=datetime.utcnow()
        )
        
        # Резервирование средств
        user.balance -= amount
        
        db.session.add(payout)
        db.session.add(transaction)
        
        # Аудит
        create_audit_log(
            'WITHDRAWAL_REQUEST',
            f'User requested withdrawal: {amount} via {method}',
            user.id,
            request
        )
        
        db.session.commit()
        
        return {
            'success': True,
            'payout_id': payout.id,
            'amount': amount,
            'fee': fee,
            'net_amount': net_amount,
            'status': 'processing',
            'estimated_time': '1-3 business days'
        }
    
    @staticmethod
    def get_user_transactions(user_id, page=1, per_page=50):
        """История транзакций пользователя"""
        transactions = Transaction.query.filter_by(user_id=user_id)\
            .order_by(Transaction.timestamp.desc())\
            .paginate(page=page, per_page=per_page, error_out=False)
        
        result = []
        for t in transactions.items:
            result.append({
                'id': t.id,
                'type': t.type.value,
                'amount': t.amount,
                'balance_before': t.balance_before,
                'balance_after': t.balance_after,
                'status': t.status,
                'timestamp': t.timestamp.isoformat(),
                'description': t.description
            })
        
        return {
            'transactions': result,
            'total': transactions.total,
            'pages': transactions.pages,
            'page': page
        }
    
    @staticmethod
    def get_user_withdrawals(user_id):
        """История выводов пользователя"""
        payouts = Payout.query.filter_by(user_id=user_id)\
            .order_by(Payout.request_date.desc())\
            .all()
        
        result = []
        for p in payouts:
            result.append({
                'id': p.id,
                'amount': p.amount,
                'method': p.method,
                'status': p.status.value,
                'fee': p.fee,
                'request_date': p.request_date.isoformat(),
                'processed_date': p.processed_date.isoformat() if p.processed_date else None
            })
        
        return result