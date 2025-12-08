from models import db, User, Game, Bet, Transaction, Payout
from sqlalchemy import func, extract
from datetime import datetime, timedelta

class AdminService:
    
    @staticmethod
    def get_user_total_deposits(user_id):
        result = db.session.query(func.sum(Transaction.amount)).filter(
            Transaction.user_id == user_id,
            Transaction.type == 'deposit',
            Transaction.status == 'completed'
        ).scalar()
        return float(result or 0)
    
    @staticmethod
    def get_user_total_withdrawals(user_id):
        result = db.session.query(func.sum(Payout.amount)).filter(
            Payout.user_id == user_id,
            Payout.status.in_(['completed', 'processing'])
        ).scalar()
        return float(result or 0)
    
    @staticmethod
    def get_user_total_bets(user_id):
        result = db.session.query(func.sum(Bet.amount)).filter(
            Bet.user_id == user_id
        ).scalar()
        return float(result or 0)
    
    @staticmethod
    def get_user_total_wins(user_id):
        result = db.session.query(func.sum(Bet.win_amount)).filter(
            Bet.user_id == user_id,
            Bet.result == 'win'
        ).scalar()
        return float(result or 0)
    
    @staticmethod
    def get_game_total_bets(game_id):
        result = db.session.query(func.sum(Bet.amount)).filter(
            Bet.game_id == game_id
        ).scalar()
        return float(result or 0)
    
    @staticmethod
    def get_game_total_wins(game_id):
        result = db.session.query(func.sum(Bet.win_amount)).filter(
            Bet.game_id == game_id,
            Bet.result == 'win'
        ).scalar()
        return float(result or 0)
    
    @staticmethod
    def get_chart_data(days=30):
        end_date = datetime.now()
        start_date = end_date - timedelta(days=days)
        
        daily_data = []
        for i in range(days):
            date = start_date + timedelta(days=i)
            next_date = date + timedelta(days=1)
            
            deposits = db.session.query(func.sum(Transaction.amount)).filter(
                Transaction.type == 'deposit',
                Transaction.status == 'completed',
                Transaction.timestamp >= date,
                Transaction.timestamp < next_date
            ).scalar() or 0
            
            bets = db.session.query(func.sum(Bet.amount)).filter(
                Bet.timestamp >= date,
                Bet.timestamp < next_date
            ).scalar() or 0
            
            wins = db.session.query(func.sum(Bet.win_amount)).filter(
                Bet.result == 'win',
                Bet.timestamp >= date,
                Bet.timestamp < next_date
            ).scalar() or 0
            
            new_users = User.query.filter(
                User.registered_at >= date,
                User.registered_at < next_date
            ).count()
            
            daily_data.append({
                'date': date.date().isoformat(),
                'deposits': float(deposits),
                'bets': float(bets),
                'wins': float(wins),
                'profit': float(bets - wins),
                'new_users': new_users
            })
        
        games = Game.query.all()
        game_distribution = []
        
        for game in games:
            total_bets = AdminService.get_game_total_bets(game.id)
            if total_bets > 0:
                game_distribution.append({
                    'name': game.title,
                    'value': float(total_bets),
                    'category': game.category
                })
        
        country_distribution = []
        countries = db.session.query(
            User.country,
            func.count(User.id).label('count'),
            func.sum(User.balance).label('total_balance')
        ).filter(
            User.country.isnot(None),
            User.country != ''
        ).group_by(User.country).all()
        
        for country in countries:
            if country[0]:
                country_distribution.append({
                    'country': country[0],
                    'users': country[1],
                    'total_balance': float(country[2] or 0)
                })
        
        return {
            'daily_data': daily_data,
            'game_distribution': game_distribution[:10], 
            'country_distribution': country_distribution[:10]  
        }
    
    @staticmethod
    def get_user_activity(user_id, days=30):
        end_date = datetime.now()
        start_date = end_date - timedelta(days=days)
        
        daily_bets = db.session.query(
            func.date(Bet.timestamp).label('date'),
            func.count(Bet.id).label('bet_count'),
            func.sum(Bet.amount).label('bet_amount'),
            func.sum(Bet.win_amount).label('win_amount')
        ).filter(
            Bet.user_id == user_id,
            Bet.timestamp >= start_date
        ).group_by(func.date(Bet.timestamp)).all()
        
        favorite_games = db.session.query(
            Game.title,
            func.count(Bet.id).label('bet_count'),
            func.sum(Bet.amount).label('bet_amount')
        ).join(Bet, Bet.game_id == Game.id).filter(
            Bet.user_id == user_id
        ).group_by(Game.id).order_by(func.sum(Bet.amount).desc()).limit(5).all()
        
        return {
            'daily_activity': [{
                'date': str(row[0]),
                'bet_count': row[1],
                'bet_amount': float(row[2] or 0),
                'win_amount': float(row[3] or 0)
            } for row in daily_bets],
            'favorite_games': [{
                'game': row[0],
                'bet_count': row[1],
                'bet_amount': float(row[2] or 0)
            } for row in favorite_games]
        }