from flask_sqlalchemy import SQLAlchemy
from flask_login import UserMixin
from datetime import datetime
import enum

db = SQLAlchemy()

# ========== ПЕРЕЧИСЛЕНИЯ ==========
class UserRole(enum.Enum):
    PLAYER = 'player'
    ADMIN = 'admin'
    MODERATOR = 'moderator'

class UserStatus(enum.Enum):
    ACTIVE = 'active'
    BLOCKED = 'blocked'
    VERIFICATION = 'verification'

class TransactionType(enum.Enum):
    DEPOSIT = 'deposit'
    BET = 'bet'
    WIN = 'win'
    BONUS = 'bonus'
    WITHDRAWAL = 'withdrawal'
    FEE = 'fee'
    ADJUSTMENT = 'adjustment'

class PayoutStatus(enum.Enum):
    PROCESSING = 'processing'
    COMPLETED = 'completed'
    REJECTED = 'rejected'
    PENDING = 'pending'

class BonusStatus(enum.Enum):
    ACTIVE = 'active'
    WAGERED = 'wagered'
    EXPIRED = 'expired'

class TicketStatus(enum.Enum):
    OPEN = 'open'
    IN_PROGRESS = 'in_progress'
    CLOSED = 'closed'
    RESOLVED = 'resolved'

class TicketPriority(enum.Enum):
    LOW = 'low'
    MEDIUM = 'medium'
    HIGH = 'high'
    URGENT = 'urgent'

class KYCStatus(enum.Enum):
    PENDING = 'pending'
    VERIFIED = 'verified'
    REJECTED = 'rejected'
    UNDER_REVIEW = 'under_review'

# ========== МОДЕЛИ ==========
class User(db.Model, UserMixin):
    __tablename__ = 'users'
    
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(200), nullable=False)
    role = db.Column(db.Enum(UserRole), default=UserRole.PLAYER, nullable=False)
    balance = db.Column(db.Float, default=0.00, nullable=False)
    status = db.Column(db.Enum(UserStatus), default=UserStatus.VERIFICATION, nullable=False)
    registered_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    loyalty_level = db.Column(db.String(20), default='standard')
    bet_limit = db.Column(db.Float)
    time_limit = db.Column(db.Integer)
    kyc_verified = db.Column(db.Boolean, default=False)
    kyc_status = db.Column(db.Enum(KYCStatus), default=KYCStatus.PENDING)
    last_login = db.Column(db.DateTime)
    phone = db.Column(db.String(20))
    first_name = db.Column(db.String(50))
    last_name = db.Column(db.String(50))
    country = db.Column(db.String(50))
    address = db.Column(db.String(200))
    city = db.Column(db.String(50))
    state = db.Column(db.String(50))
    zip_code = db.Column(db.String(20))
    birth_date = db.Column(db.Date)
    daily_deposit_limit = db.Column(db.Float, default=1000.00)
    daily_loss_limit = db.Column(db.Float, default=500.00)
    session_time_limit = db.Column(db.Integer, default=120)
    cool_off_period = db.Column(db.Integer, default=0)
    self_excluded_until = db.Column(db.DateTime)
    
    # Связи
    sessions = db.relationship('Session', backref='user', lazy=True, cascade='all, delete-orphan')
    bets = db.relationship('Bet', backref='user', lazy=True, cascade='all, delete-orphan')
    transactions = db.relationship('Transaction', backref='user', lazy=True, cascade='all, delete-orphan')
    payouts = db.relationship('Payout', backref='user', lazy=True, cascade='all, delete-orphan')
    bonuses = db.relationship('Bonus', backref='user', lazy=True, cascade='all, delete-orphan')
    kyc_documents = db.relationship('KYCDocument', backref='user', lazy=True, cascade='all, delete-orphan')
    support_tickets = db.relationship('SupportTicket', foreign_keys='SupportTicket.user_id', backref='user', lazy=True)
    assigned_tickets = db.relationship('SupportTicket', foreign_keys='SupportTicket.admin_id', backref='admin', lazy=True)
    
    def __repr__(self):
        return f'<User {self.username}>'

class Game(db.Model):
    __tablename__ = 'games'
    
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(100), nullable=False)
    category = db.Column(db.String(50), nullable=False)
    description = db.Column(db.Text)
    min_bet = db.Column(db.Float, nullable=False)
    max_bet = db.Column(db.Float, nullable=False)
    rtp = db.Column(db.Float, nullable=False)
    active = db.Column(db.Boolean, default=True)
    maintenance = db.Column(db.Boolean, default=False)
    added_at = db.Column(db.DateTime, default=datetime.utcnow)
    provider = db.Column(db.String(100))
    volatility = db.Column(db.String(20))
    image_url = db.Column(db.String(200))
    popularity = db.Column(db.Integer, default=0)
    
    bets = db.relationship('Bet', backref='game', lazy=True, cascade='all, delete-orphan')
    
    def __repr__(self):
        return f'<Game {self.title}>'

class Bet(db.Model):
    __tablename__ = 'bets'
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    game_id = db.Column(db.Integer, db.ForeignKey('games.id'), nullable=False)
    amount = db.Column(db.Float, nullable=False)
    multiplier = db.Column(db.Float)
    result = db.Column(db.String(20))
    win_amount = db.Column(db.Float, default=0.00)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)
    game_data = db.Column(db.Text)  # JSON как текст для SQLite
    ip_address = db.Column(db.String(45))
    
    def __repr__(self):
        return f'<Bet {self.id}>'

class Transaction(db.Model):
    __tablename__ = 'transactions'
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    type = db.Column(db.Enum(TransactionType), nullable=False)
    amount = db.Column(db.Float, nullable=False)
    balance_before = db.Column(db.Float)
    balance_after = db.Column(db.Float)
    status = db.Column(db.String(20), default='completed')
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)
    reference = db.Column(db.String(100), unique=True)
    description = db.Column(db.Text)
    
    def __repr__(self):
        return f'<Transaction {self.id} {self.type.value}>'

class Payout(db.Model):
    __tablename__ = 'payouts'
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    amount = db.Column(db.Float, nullable=False)
    method = db.Column(db.String(50), nullable=False)
    status = db.Column(db.Enum(PayoutStatus), default=PayoutStatus.PENDING)
    request_date = db.Column(db.DateTime, default=datetime.utcnow)
    processed_date = db.Column(db.DateTime)
    account_details = db.Column(db.Text)  # JSON как текст
    fee = db.Column(db.Float, default=0.00)
    admin_notes = db.Column(db.Text)
    
    def __repr__(self):
        return f'<Payout {self.id}>'

class Bonus(db.Model):
    __tablename__ = 'bonuses'
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    type = db.Column(db.String(50), nullable=False)
    amount = db.Column(db.Float)
    spins = db.Column(db.Integer)
    wager_requirement = db.Column(db.Float)
    activated_at = db.Column(db.DateTime, default=datetime.utcnow)
    expires_at = db.Column(db.DateTime)
    status = db.Column(db.Enum(BonusStatus), default=BonusStatus.ACTIVE)
    wagered_amount = db.Column(db.Float, default=0.00)
    
    def __repr__(self):
        return f'<Bonus {self.id} {self.type}>'

class Session(db.Model):
    __tablename__ = 'sessions'
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    ip_address = db.Column(db.String(45), nullable=False)
    device = db.Column(db.String(200))
    browser = db.Column(db.String(100))
    login_time = db.Column(db.DateTime, default=datetime.utcnow)
    logout_time = db.Column(db.DateTime)
    active = db.Column(db.Boolean, default=True)
    token = db.Column(db.String(500))
    user_agent = db.Column(db.Text)
    
    def __repr__(self):
        return f'<Session {self.id} user:{self.user_id}>'

class AuditLog(db.Model):
    __tablename__ = 'audit_log'
    
    id = db.Column(db.Integer, primary_key=True)
    actor_id = db.Column(db.Integer, db.ForeignKey('users.id'))
    action = db.Column(db.String(100), nullable=False)
    description = db.Column(db.Text)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)
    ip_address = db.Column(db.String(45))
    user_agent = db.Column(db.Text)
    changed_data = db.Column(db.Text)  # JSON как текст
    
    actor = db.relationship('User', foreign_keys=[actor_id])
    
    def __repr__(self):
        return f'<AuditLog {self.id} {self.action}>'

# ========== НОВЫЕ МОДЕЛИ ==========

class KYCDocument(db.Model):
    __tablename__ = 'kyc_documents'
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    document_type = db.Column(db.String(50), nullable=False)  # passport, id_card, driver_license, utility_bill
    document_number = db.Column(db.String(100))
    front_image = db.Column(db.String(200))  # путь к файлу
    back_image = db.Column(db.String(200))
    selfie_image = db.Column(db.String(200))
    status = db.Column(db.Enum(KYCStatus), default=KYCStatus.PENDING)
    submitted_at = db.Column(db.DateTime, default=datetime.utcnow)
    verified_at = db.Column(db.DateTime)
    verified_by = db.Column(db.Integer, db.ForeignKey('users.id'))
    rejection_reason = db.Column(db.Text)
    
    verifier = db.relationship('User', foreign_keys=[verified_by])
    
    def __repr__(self):
        return f'<KYCDocument {self.id} {self.document_type}>'

class SupportTicket(db.Model):
    __tablename__ = 'support_tickets'
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    subject = db.Column(db.String(200), nullable=False)
    message = db.Column(db.Text, nullable=False)
    status = db.Column(db.Enum(TicketStatus), default=TicketStatus.OPEN)
    priority = db.Column(db.Enum(TicketPriority), default=TicketPriority.MEDIUM)
    category = db.Column(db.String(50))  # deposit, withdrawal, technical, account, game
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    closed_at = db.Column(db.DateTime)
    admin_id = db.Column(db.Integer, db.ForeignKey('users.id'))  # кто закрыл
    last_reply_by = db.Column(db.Enum(UserRole))
    
    # Связи
    messages = db.relationship('SupportMessage', backref='ticket', lazy=True, cascade='all, delete-orphan')
    
    def __repr__(self):
        return f'<SupportTicket {self.id} {self.subject}>'

class SupportMessage(db.Model):
    __tablename__ = 'support_messages'
    
    id = db.Column(db.Integer, primary_key=True)
    ticket_id = db.Column(db.Integer, db.ForeignKey('support_tickets.id'), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    message = db.Column(db.Text, nullable=False)
    is_admin = db.Column(db.Boolean, default=False)
    read = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    user = db.relationship('User')
    
    def __repr__(self):
        return f'<SupportMessage {self.id}>'

class Announcement(db.Model):
    __tablename__ = 'announcements'
    
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200), nullable=False)
    content = db.Column(db.Text, nullable=False)
    type = db.Column(db.String(50))  # info, warning, success, maintenance
    active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    expires_at = db.Column(db.DateTime)
    created_by = db.Column(db.Integer, db.ForeignKey('users.id'))
    
    creator = db.relationship('User')
    
    def __repr__(self):
        return f'<Announcement {self.id} {self.title}>'