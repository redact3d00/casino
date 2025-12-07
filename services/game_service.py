from models import db, Game, Bet, Transaction, AuditLog, TransactionType
from utils.security import create_audit_log
from datetime import datetime
import random
import json

class GameService:
    
    @staticmethod
    def get_available_games():
        """Получение доступных игр"""
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
            'image_url': g.image_url
        } for g in games]
    
    @staticmethod
    def play_game(user, game_id, bet_amount, request):
        """Игра в выбранную игру"""
        game = Game.query.get(game_id)
        if not game:
            return {'success': False, 'error': 'Game not found'}
        
        # Проверка доступности игры
        if not game.active:
            return {'success': False, 'error': 'Game is not active'}
        if game.maintenance:
            return {'success': False, 'error': 'Game is under maintenance'}
        
        # Валидация ставки
        if bet_amount < game.min_bet:
            return {'success': False, 'error': f'Bet amount below minimum ({game.min_bet})'}
        if bet_amount > game.max_bet:
            return {'success': False, 'error': f'Bet amount above maximum ({game.max_bet})'}
        if bet_amount > user.balance:
            return {'success': False, 'error': 'Insufficient balance'}
        
        # Генерация результата игры
        is_win, multiplier, win_amount = GameService._calculate_game_result(game, bet_amount)
        
        # Транзакция ставки
        transaction_bet = Transaction(
            user_id=user.id,
            type=TransactionType.BET,
            amount=bet_amount,
            balance_before=user.balance,
            balance_after=user.balance - bet_amount,
            status='completed',
            description=f'Bet on {game.title}',
            timestamp=datetime.utcnow()
        )
        
        # Обновление баланса
        user.balance -= bet_amount
        db.session.add(transaction_bet)
        
        # Создание записи о ставке
        bet = Bet(
            user_id=user.id,
            game_id=game.id,
            amount=bet_amount,
            multiplier=multiplier,
            result='win' if is_win else 'loss',
            win_amount=win_amount,
            ip_address=request.remote_addr,
            game_data=json.dumps({
                'random_seed': random.random(),
                'timestamp': datetime.utcnow().isoformat()
            })
        )
        db.session.add(bet)
        
        if is_win:
            # Транзакция выигрыша
            transaction_win = Transaction(
                user_id=user.id,
                type=TransactionType.WIN,
                amount=win_amount,
                balance_before=user.balance,
                balance_after=user.balance + win_amount,
                status='completed',
                description=f'Win from {game.title}',
                timestamp=datetime.utcnow()
            )
            user.balance += win_amount
            db.session.add(transaction_win)
        
        # Аудит
        create_audit_log(
            'GAME_PLAY',
            f'User {user.username} played {game.title}, bet: {bet_amount}, win: {win_amount}',
            user.id,
            request
        )
        
        db.session.commit()
        
        return {
            'success': True,
            'result': 'win' if is_win else 'loss',
            'bet_amount': bet_amount,
            'win_amount': win_amount,
            'multiplier': multiplier,
            'new_balance': user.balance,
            'timestamp': datetime.utcnow().isoformat()
        }
    
    @staticmethod
    def _calculate_game_result(game, bet_amount):
        """Расчет результата игры"""
        # Базовый расчет на основе RTP
        win_probability = game.rtp / 100
        random_result = random.random()
        
        if random_result < win_probability:
            # Выигрыш
            if game.category == 'slots':
                # Для слотов разные множители
                multipliers = {
                    'low': [1.5, 2, 3],
                    'medium': [2, 3, 5, 10],
                    'high': [3, 5, 10, 20, 50]
                }
                multiplier = random.choice(multipliers.get(game.volatility, [2, 3]))
            elif game.category == 'roulette':
                # Для рулетки стандартные выплаты
                multiplier = random.choice([2, 3, 5, 10, 35])
            else:
                multiplier = 2
            
            win_amount = bet_amount * multiplier
            return True, multiplier, win_amount
        else:
            # Проигрыш
            return False, 0, 0
    
    @staticmethod
    def get_user_game_history(user_id, page=1, per_page=20):
        """История игр пользователя"""
        bets = Bet.query.filter_by(user_id=user_id)\
            .order_by(Bet.timestamp.desc())\
            .paginate(page=page, per_page=per_page, error_out=False)
        
        history = []
        for bet in bets.items:
            history.append({
                'id': bet.id,
                'game_title': bet.game.title,
                'amount': bet.amount,
                'multiplier': bet.multiplier,
                'result': bet.result,
                'win_amount': bet.win_amount,
                'timestamp': bet.timestamp.isoformat()
            })
        
        return {
            'bets': history,
            'total': bets.total,
            'pages': bets.pages,
            'page': page
        }
    
    @staticmethod
    def create_game(data):
        """Создание новой игры"""
        game = Game(
            title=data['title'],
            category=data['category'],
            min_bet=data.get('min_bet', 1),
            max_bet=data.get('max_bet', 100),
            rtp=data.get('rtp', 95.0),
            description=data.get('description'),
            provider=data.get('provider'),
            volatility=data.get('volatility', 'medium')
        )
        
        db.session.add(game)
        db.session.commit()
        
        return {
            'success': True,
            'game_id': game.id
        }