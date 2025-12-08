import re
from datetime import datetime
from flask import current_app
from models import Bet, db

def sanitize_input(input_string):
    if not input_string:
        return ''
    
    sanitized = re.sub(r'<[^>]*>', '', input_string)
    sanitized = re.sub(r'[;\"\']', '', sanitized)
    sanitized = sanitized.strip()
    
    return sanitized

def validate_bet_amount(user, game, amount):
    if amount < float(game.min_bet):
        return False, f"Bet amount below minimum ({game.min_bet})"
    
    if amount > float(game.max_bet):
        return False, f"Bet amount above maximum ({game.max_bet})"
    
    if user.bet_limit and amount > float(user.bet_limit):
        return False, f"Exceeds personal bet limit ({user.bet_limit})"
    
    if amount > float(user.balance):
        return False, "Insufficient balance"
    
    today = datetime.now().date()
    today_loss = Bet.query.with_entities(
        db.func.sum(Bet.amount - Bet.win_amount)
    ).filter(
        Bet.user_id == user.id,
        Bet.timestamp >= today,
        Bet.result != 'return'
    ).scalar() or 0
    
    if today_loss + amount > current_app.config.get('DAILY_LOSS_LIMIT', 1000):
        return False, "Daily loss limit exceeded"
    
    return True, "Valid bet"

def validate_username(username):
    if len(username) < 3:
        return False, "Username must be at least 3 characters"
    if len(username) > 20:
        return False, "Username must be at most 20 characters"
    if not re.match(r'^[a-zA-Z0-9_]+$', username):
        return False, "Username can only contain letters, numbers and underscores"
    return True, "Valid username"

def validate_amount(amount, min_amount=0, max_amount=10000):
    try:
        amount_float = float(amount)
        if amount_float < min_amount:
            return False, f"Amount must be at least {min_amount}"
        if amount_float > max_amount:
            return False, f"Amount must be at most {max_amount}"
        return True, "Valid amount"
    except ValueError:
        return False, "Invalid amount format"