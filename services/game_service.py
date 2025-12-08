from models import db, Game, Bet, Transaction, AuditLog, TransactionType
from utils.security import create_audit_log
from datetime import datetime
import random
import json
import math

class GameService:
    
    @staticmethod
    def get_available_games():
        games = Game.query.filter_by(active=True, maintenance=False).all()
        
        return [{
            'id': g.id,
            'title': g.title,
            'category': g.category,
            'description': g.description,
            'min_bet': g.min_bet,
            'max_bet': g.max_bet,
            'rtp': g.rtp,
            'volatility': g.volatility,
            'provider': g.provider,
            'image_url': g.image_url,
            'has_bonus': g.has_bonus,
            'jackpot': g.jackpot,
            'popularity': g.popularity or 0
        } for g in games]
    
    @staticmethod
    def play_game(user, game_id, bet_amount, request):
        game = Game.query.get(game_id)
        if not game:
            return {'success': False, 'error': 'Game not found'}
        
        if not game.active:
            return {'success': False, 'error': 'Game is not active'}
        if game.maintenance:
            return {'success': False, 'error': 'Game is under maintenance'}
        
        if bet_amount < game.min_bet:
            return {'success': False, 'error': f'Bet amount below minimum (${game.min_bet})'}
        if bet_amount > game.max_bet:
            return {'success': False, 'error': f'Bet amount above maximum (${game.max_bet})'}
        if bet_amount > user.balance:
            return {'success': False, 'error': 'Insufficient balance'}
        
        if user.bet_limit and bet_amount > user.bet_limit:
            return {'success': False, 'error': f'Exceeds your bet limit (${user.bet_limit})'}
        
        is_win, multiplier, win_amount = GameService._calculate_game_result(game, bet_amount)
        
        transaction_bet = Transaction(
            user_id=user.id,
            type=TransactionType.BET,
            amount=bet_amount,
            balance_before=user.balance,
            balance_after=user.balance - bet_amount,
            status='completed',
            description=f'Bet on {game.title}',
            timestamp=datetime.now(),
            reference=f'BET_{datetime.now().strftime("%Y%m%d%H%M%S")}_{random.randint(1000, 9999)}'
        )
        
        user.balance -= bet_amount
        db.session.add(transaction_bet)
        
        game_data = {
            'random_seed': random.random(),
            'timestamp': datetime.now().isoformat(),
            'game_type': game.category,
            'volatility': game.volatility,
            'result_type': 'win' if is_win else 'loss',
            'multiplier': multiplier,
            'rtp': game.rtp,
            'bet_amount': bet_amount
        }
        
        bet = Bet(
            user_id=user.id,
            game_id=game.id,
            amount=bet_amount,
            multiplier=multiplier,
            result='win' if is_win else 'loss',
            win_amount=win_amount,
            ip_address=request.remote_addr,
            game_data=json.dumps(game_data)
        )
        db.session.add(bet)
        
        if is_win:
            transaction_win = Transaction(
                user_id=user.id,
                type=TransactionType.WIN,
                amount=win_amount,
                balance_before=user.balance,
                balance_after=user.balance + win_amount,
                status='completed',
                description=f'Win from {game.title} (x{multiplier})',
                timestamp=datetime.now(),
                reference=f'WIN_{datetime.now().strftime("%Y%m%d%H%M%S")}_{random.randint(1000, 9999)}'
            )
            user.balance += win_amount
            db.session.add(transaction_win)
            
            if game.jackpot > 0 and multiplier >= 50:
                jackpot_contribution = win_amount * 0.01  
                game.jackpot += jackpot_contribution
        
        create_audit_log(
            'GAME_PLAY',
            f'User {user.username} played {game.title}, bet: ${bet_amount}, {"win" if is_win else "loss"}: ${win_amount}',
            user.id,
            request
        )
        
        game.popularity = (game.popularity or 0) + 1
        
        db.session.commit()
        
        return {
            'success': True,
            'result': 'win' if is_win else 'loss',
            'bet_amount': bet_amount,
            'win_amount': win_amount,
            'multiplier': multiplier,
            'new_balance': user.balance,
            'game_data': game_data,
            'timestamp': datetime.now().isoformat(),
            'game_title': game.title
        }
    
    @staticmethod
    def _calculate_game_result(game, bet_amount):
        base_win_prob = game.rtp / 100
        
        random_factor = random.uniform(0.95, 1.05) 
        actual_win_prob = min(0.95, max(0.05, base_win_prob * random_factor))
        
        rng = random.SystemRandom()
        
        if rng.random() < actual_win_prob:
            if game.category == 'slots':
                multiplier = GameService._calculate_slot_multiplier(game.volatility)
            elif game.category == 'roulette':
                multiplier = GameService._calculate_roulette_multiplier()
            elif game.category == 'blackjack':
                multiplier = 1.5  
            elif game.category == 'poker':
                multiplier = GameService._calculate_poker_multiplier()
            else:
                multiplier = rng.choice([1.5, 2, 3, 5])
            
            max_multiplier = 10000  
            multiplier = min(multiplier, max_multiplier)
            
            win_amount = bet_amount * multiplier
            
            win_amount = round(win_amount, 2)
            
            return True, multiplier, win_amount
        else:
            return False, 0, 0
    
    @staticmethod
    def _calculate_slot_multiplier(volatility):
        rng = random.SystemRandom()
        
        if volatility == 'low':
            weights = [0.4, 0.3, 0.2, 0.08, 0.02]  
            multipliers = [1.2, 1.5, 2, 3, 5]
        elif volatility == 'high':
            weights = [0.2, 0.3, 0.25, 0.15, 0.1]
            multipliers = [1.5, 2, 5, 10, 20]
        else:
            weights = [0.3, 0.35, 0.2, 0.1, 0.05]
            multipliers = [1.5, 2, 3, 5, 10]
        
        return rng.choices(multipliers, weights=weights)[0]
    
    @staticmethod
    def _calculate_roulette_multiplier():
        rng = random.SystemRandom()
        
        outcomes = {
            1.1: 0.4865, 
            2: 0.3243,    
            3: 0.1622,    
            8: 0.0811,    
            11: 0.0541,   
            17: 0.0270,   
            35: 0.0270    
        }
        
        multipliers = list(outcomes.keys())
        probabilities = list(outcomes.values())
        
        return rng.choices(multipliers, weights=probabilities)[0]
    
    @staticmethod
    def _calculate_poker_multiplier():
        rng = random.SystemRandom()
        
        hand_strength = rng.random()
        
        if hand_strength > 0.95:  
            return rng.choice([10, 20, 50])
        elif hand_strength > 0.8: 
            return rng.choice([3, 5, 8])
        elif hand_strength > 0.5:
            return rng.choice([1.5, 2, 2.5])
        else:  
            return 1  
    
    @staticmethod
    def get_user_game_history(user_id, page=1, per_page=20):
        bets = Bet.query.filter_by(user_id=user_id)\
            .order_by(Bet.timestamp.desc())\
            .paginate(page=page, per_page=per_page, error_out=False)
        
        history = []
        for bet in bets.items:
            game_data = {}
            try:
                game_data = json.loads(bet.game_data) if bet.game_data else {}
            except:
                pass
            
            history.append({
                'id': bet.id,
                'game_title': bet.game.title if bet.game else 'Unknown Game',
                'game_category': bet.game.category if bet.game else '',
                'amount': bet.amount,
                'multiplier': bet.multiplier,
                'result': bet.result,
                'win_amount': bet.win_amount,
                'timestamp': bet.timestamp.isoformat(),
                'game_data': game_data,
                'ip_address': bet.ip_address
            })
        
        total_bets_result = db.session.query(
            db.func.count(Bet.id).label('count'),
            db.func.sum(Bet.amount).label('total_bets'),
            db.func.sum(Bet.win_amount).label('total_wins'),
            db.func.sum(db.case((Bet.result == 'win', 1), else_=0)).label('wins_count')
        ).filter_by(user_id=user_id).first()
        
        return {
            'bets': history,
            'total': bets.total,
            'pages': bets.pages,
            'page': page,
            'stats': {
                'total_bets': float(total_bets_result.total_bets or 0),
                'total_wins': float(total_bets_result.total_wins or 0),
                'total_games': total_bets_result.count or 0,
                'wins_count': total_bets_result.wins_count or 0,
                'losses_count': (total_bets_result.count or 0) - (total_bets_result.wins_count or 0),
                'net_profit': float((total_bets_result.total_wins or 0) - (total_bets_result.total_bets or 0))
            }
        }
    
    @staticmethod
    def get_game_statistics(game_id):
        game = Game.query.get(game_id)
        if not game:
            return None
        
        stats = db.session.query(
            db.func.count(Bet.id).label('total_bets'),
            db.func.sum(Bet.amount).label('total_wagered'),
            db.func.sum(Bet.win_amount).label('total_paid'),
            db.func.avg(Bet.amount).label('avg_bet'),
            db.func.max(Bet.win_amount).label('biggest_win')
        ).filter_by(game_id=game_id).first()
        
        total_wagered = stats.total_wagered or 0
        total_paid = stats.total_paid or 0
        
        return {
            'game': {
                'id': game.id,
                'title': game.title,
                'rtp': game.rtp
            },
            'stats': {
                'total_bets': stats.total_bets or 0,
                'total_wagered': float(total_wagered),
                'total_paid': float(total_paid),
                'house_edge': float((total_wagered - total_paid) / total_wagered * 100) if total_wagered > 0 else 0,
                'actual_rtp': float(total_paid / total_wagered * 100) if total_wagered > 0 else 0,
                'avg_bet': float(stats.avg_bet or 0),
                'biggest_win': float(stats.biggest_win or 0),
                'popularity': game.popularity or 0
            }
        }