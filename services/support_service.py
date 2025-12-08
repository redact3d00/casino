from models import db, SupportTicket, SupportMessage, TicketStatus, TicketPriority, UserRole
from datetime import datetime
from sqlalchemy import or_

class SupportService:
    
    @staticmethod
    def create_ticket(user_id, subject, message, category='general'):
        ticket = SupportTicket(
            user_id=user_id,
            subject=subject,
            message=message,
            category=category,
            status=TicketStatus.OPEN,
            priority=TicketPriority.MEDIUM,
            created_at=datetime.now(),
            updated_at=datetime.now()
        )
        
        db.session.add(ticket)
        db.session.commit()
        
        return {
            'success': True,
            'ticket_id': ticket.id
        }
    
    @staticmethod
    def add_message(ticket_id, user_id, message, is_admin=False):
        ticket = SupportTicket.query.get(ticket_id)
        if not ticket:
            return {'success': False, 'error': 'Ticket not found'}
        
        support_message = SupportMessage(
            ticket_id=ticket_id,
            user_id=user_id,
            message=message,
            is_admin=is_admin,
            read=False,
            created_at=datetime.now()
        )
        
        ticket.updated_at = datetime.now()
        ticket.last_reply_by = UserRole.ADMIN if is_admin else UserRole.PLAYER
        
        if ticket.status == TicketStatus.CLOSED and not is_admin:
            ticket.status = TicketStatus.OPEN
            ticket.admin_id = None
            ticket.closed_at = None
        
        db.session.add(support_message)
        db.session.commit()
        
        return {
            'success': True,
            'message_id': support_message.id
        }
    
    @staticmethod
    def get_user_tickets(user_id, limit=20):
        tickets = SupportTicket.query.filter_by(user_id=user_id)\
            .order_by(SupportTicket.updated_at.desc())\
            .limit(limit)\
            .all()
        
        return [{
            'id': t.id,
            'subject': t.subject,
            'status': t.status.value,
            'priority': t.priority.value,
            'category': t.category,
            'created_at': t.created_at.isoformat(),
            'updated_at': t.updated_at.isoformat(),
            'last_reply_by': t.last_reply_by.value if t.last_reply_by else None,
            'unread_messages': SupportService.get_unread_count(t.id, user_id)
        } for t in tickets]
    
    @staticmethod
    def get_ticket_messages(ticket_id, user_id=None):
        query = SupportMessage.query.filter_by(ticket_id=ticket_id)\
            .order_by(SupportMessage.created_at.asc())
        
        if user_id:
            messages = query.all()
            for message in messages:
                if message.is_admin and not message.read:
                    message.read = True
            
            db.session.commit()
        
        messages = query.all()
        
        return [{
            'id': m.id,
            'user_id': m.user_id,
            'username': m.user.username,
            'is_admin': m.is_admin,
            'message': m.message,
            'created_at': m.created_at.isoformat(),
            'read': m.read
        } for m in messages]
    
    @staticmethod
    def get_unread_count(ticket_id, user_id):
        return SupportMessage.query.filter_by(
            ticket_id=ticket_id,
            is_admin=True,
            read=False
        ).count()
    
    @staticmethod
    def get_user_unread_count(user_id):
        user_tickets = SupportTicket.query.filter_by(user_id=user_id).all()
        ticket_ids = [t.id for t in user_tickets]
        
        if not ticket_ids:
            return 0
        
        return SupportMessage.query.filter(
            SupportMessage.ticket_id.in_(ticket_ids),
            SupportMessage.is_admin == True,
            SupportMessage.read == False
        ).count()
    
    @staticmethod
    def search_tickets(query, user_id=None):
        search_query = SupportTicket.query
        
        if user_id:
            search_query = search_query.filter_by(user_id=user_id)
        
        if query:
            search_filter = or_(
                SupportTicket.subject.ilike(f'%{query}%'),
                SupportTicket.message.ilike(f'%{query}%')
            )
            search_query = search_query.filter(search_filter)
        
        tickets = search_query.order_by(SupportTicket.updated_at.desc()).limit(20).all()
        
        return [{
            'id': t.id,
            'subject': t.subject,
            'status': t.status.value,
            'created_at': t.created_at.isoformat(),
            'user_id': t.user_id,
            'username': t.user.username if t.user else 'Unknown'
        } for t in tickets]