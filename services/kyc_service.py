from models import db, KYCDocument, KYCStatus, User
from datetime import datetime

class KYCService:
    
    @staticmethod
    def submit_document(user_id, document_type, document_number, 
                       front_image_path, back_image_path, selfie_image_path):
        pending_doc = KYCDocument.query.filter_by(
            user_id=user_id,
            status=KYCStatus.PENDING
        ).first()
        
        if pending_doc:
            return {
                'success': False,
                'error': 'You already have a pending KYC submission'
            }
        
        document = KYCDocument(
            user_id=user_id,
            document_type=document_type,
            document_number=document_number,
            front_image=front_image_path,
            back_image=back_image_path,
            selfie_image=selfie_image_path,
            status=KYCStatus.PENDING,
            submitted_at=datetime.now()
        )
        
        db.session.add(document)
        
        user = User.query.get(user_id)
        user.kyc_status = KYCStatus.PENDING
        user.kyc_verified = False
        
        db.session.commit()
        
        return {
            'success': True,
            'document_id': document.id
        }
    
    @staticmethod
    def verify_document(document_id, admin_id, approved=True, notes=''):
        document = KYCDocument.query.get(document_id)
        if not document:
            return {'success': False, 'error': 'Document not found'}
        
        if approved:
            document.status = KYCStatus.VERIFIED
            document.verified_at = datetime.utcnow()
            document.verified_by = admin_id
            
            document.user.kyc_verified = True
            document.user.kyc_status = KYCStatus.VERIFIED
            
            bonus_amount = 10.00
            document.user.balance += bonus_amount
            
            from models import Transaction, TransactionType
            transaction = Transaction(
                user_id=document.user.id,
                type=TransactionType.BONUS,
                amount=bonus_amount,
                description='KYC verification bonus',
                timestamp=datetime.now(),
                status='completed'
            )
            db.session.add(transaction)
            
        else:
            document.status = KYCStatus.REJECTED
            document.verified_at = datetime.now()
            document.verified_by = admin_id
            document.rejection_reason = notes
            
            document.user.kyc_status = KYCStatus.REJECTED
            document.user.kyc_verified = False
        
        db.session.commit()
        
        return {
            'success': True,
            'document_id': document.id,
            'status': document.status.value
        }
    
    @staticmethod
    def get_user_documents(user_id):
        documents = KYCDocument.query.filter_by(user_id=user_id)\
            .order_by(KYCDocument.submitted_at.desc())\
            .all()
        
        return [{
            'id': doc.id,
            'document_type': doc.document_type,
            'document_number': doc.document_number,
            'status': doc.status.value,
            'submitted_at': doc.submitted_at.isoformat(),
            'verified_at': doc.verified_at.isoformat() if doc.verified_at else None,
            'verified_by': doc.verified_by,
            'rejection_reason': doc.rejection_reason
        } for doc in documents]
    
    @staticmethod
    def check_kyc_required(user_id, deposit_amount):
        user = User.query.get(user_id)
        if not user:
            return True
        
        if user.kyc_verified:
            return False
        
        from models import Transaction
        total_deposits = db.session.query(
            db.func.sum(Transaction.amount)
        ).filter(
            Transaction.user_id == user_id,
            Transaction.type == 'deposit',
            Transaction.status == 'completed'
        ).scalar() or 0
        
        KYC_THRESHOLD = 1000.00
        
        if total_deposits + deposit_amount >= KYC_THRESHOLD:
            return True
        
        return False
    
    @staticmethod
    def get_pending_count():
        return KYCDocument.query.filter_by(status=KYCStatus.PENDING).count()