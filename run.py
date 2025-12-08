from app import app
import os
from models import db, User, Game, UserRole, UserStatus, KYCStatus
from werkzeug.security import generate_password_hash
from datetime import datetime

def create_default_data():
    with app.app_context():
        db.drop_all()
        db.create_all()
        
        try:
            admin = User.query.filter_by(username='admin').first()
            if not admin:
                admin = User(
                    username='admin',
                    email='admin@casino.local',
                    password_hash=generate_password_hash('Admin123!'),
                    role=UserRole.ADMIN,
                    status=UserStatus.ACTIVE,
                    kyc_verified=True,
                    kyc_status=KYCStatus.VERIFIED,
                    balance=10000.00,
                    registered_at=datetime.now()
                )
                db.session.add(admin)
                print("Admin user created")
            
            player = User.query.filter_by(username='testplayer').first()
            if not player:
                player = User(
                    username='testplayer',
                    email='player@casino.local',
                    password_hash=generate_password_hash('Test123!'),
                    role=UserRole.PLAYER,
                    status=UserStatus.ACTIVE,
                    kyc_verified=True,
                    kyc_status=KYCStatus.VERIFIED,
                    balance=1000.00,
                    registered_at=datetime.now()
                )
                db.session.add(player)
                print("✅ Test player created")
            
            support = User.query.filter_by(username='support').first()
            if not support:
                support = User(
                    username='support',
                    email='support@casino.local',
                    password_hash=generate_password_hash('Support123!'),
                    role=UserRole.SUPPORT,
                    status=UserStatus.ACTIVE,
                    kyc_verified=True,
                    kyc_status=KYCStatus.VERIFIED,
                    balance=0.00,
                    registered_at=datetime.now()
                )
                db.session.add(support)
                print("Support user created")
            
            moderator = User.query.filter_by(username='moderator').first()
            if not moderator:
                moderator = User(
                    username='moderator',
                    email='moderator@casino.local',
                    password_hash=generate_password_hash('Moderator123!'),
                    role=UserRole.MODERATOR,
                    status=UserStatus.ACTIVE,
                    kyc_verified=True,
                    kyc_status=KYCStatus.VERIFIED,
                    balance=0.00,
                    registered_at=datetime.now()
                )
                db.session.add(moderator)
                print("Moderator user created")
            
            if Game.query.count() == 0:
                games = [
                    Game(
                        title='Lucky 7 Slots',
                        category='slots',
                        min_bet=1.00,
                        max_bet=100.00,
                        rtp=96.5,
                        provider='CasinoSoft',
                        volatility='medium',
                        description='Classic 3-reel slot machine'
                    ),
                    Game(
                        title='European Roulette',
                        category='roulette',
                        min_bet=5.00,
                        max_bet=500.00,
                        rtp=97.3,
                        provider='RoulettePro',
                        volatility='low',
                        description='Authentic European roulette'
                    ),
                    Game(
                        title='Diamond Mine',
                        category='slots',
                        min_bet=0.50,
                        max_bet=50.00,
                        rtp=95.8,
                        provider='SlotMasters',
                        volatility='high',
                        description='Mining-themed slot'
                    )
                ]
                
                for game in games:
                    db.session.add(game)
                
                print("Games created")
            
            db.session.commit()
            print("Default data created successfully")
            
        except Exception as e:
            db.session.rollback()
            print(f"Error creating default data: {e}")

if __name__ == '__main__':
    directories = ['logs', 'uploads/kyc', 'uploads/avatars', '.flask_session']
    
    for directory in directories:
        os.makedirs(directory, exist_ok=True)
        print(f"Created directory: {directory}")
    
    create_default_data()
    
    print("\nStarting Casino application...")
    print(f"Debug mode: {app.config['DEBUG']}")
    print(f"Database: {app.config['SQLALCHEMY_DATABASE_URI']}")
    print(f"Server: http://localhost:5000")
    print(f"Admin login: admin / Admin123!")
    print(f"Support login: support / Support123!")
    print(f"Moderator login: moderator / Moderator123!")
    print(f"Test player: testplayer / Test123!")
    print("-" * 50)
    
    app.run(
        host='0.0.0.0',
        port=5000,
        debug=app.config['DEBUG']
    )