from app import app
import os
from models import db, User, Game, UserRole, UserStatus
from flask_bcrypt import generate_password_hash
from datetime import datetime

def create_default_data():
    with app.app_context():
        # Создаем таблицы, если они не существуют
        db.create_all()
        
        try:
            # Проверяем и создаем администратора
            admin = User.query.filter_by(username='admin').first()
            if not admin:
                # Проверяем, не занят ли email
                existing_email = User.query.filter_by(email='admin@casino.local').first()
                if existing_email:
                    # Если email занят, используем уникальный
                    admin_email = f'admin_{int(datetime.now().timestamp())}@casino.local'
                    print(f"⚠️  Original admin email already exists. Using: {admin_email}")
                else:
                    admin_email = 'admin@casino.local'
                
                admin = User(
                    username='admin',
                    email=admin_email,
                    password_hash=generate_password_hash('Admin123!').decode('utf-8'),
                    role=UserRole.ADMIN,
                    status=UserStatus.ACTIVE,
                    kyc_verified=True,
                    balance=10000.00,
                    registered_at=datetime.utcnow()
                )
                db.session.add(admin)
                print("✅ Admin user created")
            
            # Проверяем и создаем тестового игрока
            player = User.query.filter_by(username='testplayer').first()
            if not player:
                player = User(
                    username='testplayer',
                    email='player@casino.local',
                    password_hash=generate_password_hash('Test123!').decode('utf-8'),
                    role=UserRole.PLAYER,
                    status=UserStatus.ACTIVE,
                    kyc_verified=True,
                    balance=1000.00,
                    registered_at=datetime.utcnow()
                )
                db.session.add(player)
                print("✅ Test player created")
            
            # Проверяем и создаем игры
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
                
                print("✅ Games created")
            
            db.session.commit()
            print("✅ Default data verified successfully")
            
        except Exception as e:
            db.session.rollback()
            print(f"❌ Error creating default data: {e}")

if __name__ == '__main__':
    # Создаем необходимые директории
    directories = ['logs', 'uploads/kyc', 'uploads/avatars', '.flask_session', 'templates', 'templates/admin']
    
    for directory in directories:
        os.makedirs(directory, exist_ok=True)
        print(f"📁 Created directory: {directory}")
    
    if not os.path.exists('templates/games.html'):
        with open('templates/games.html', 'w') as f:
            f.write("""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Games - BeaversCasino</title>
</head>
<body>
    <h1>🎮 Available Games</h1>
    <div id="games-container" class="games-grid">
        <!-- Games will be loaded by JavaScript -->
    </div>
    
    <h2>🎲 Game History</h2>
    <div id="game-history">
        <!-- History will be loaded by JavaScript -->
    </div>
    
    <script src="/static/js/main.js"></script>
    <script src="/static/js/games.js"></script>
</body>
</html>""")
        print("📄 Created games.html template")
    
    create_default_data()
    
    print("\n🚀 Starting Casino application...")
    print(f"🔧 Debug mode: {app.config['DEBUG']}")
    print(f"💾 Database: {app.config['SQLALCHEMY_DATABASE_URI']}")
    print(f"🌐 Server: http://localhost:5000")
    print(f"🔑 Admin login: admin / Admin123!")
    print(f"👤 Test player: testplayer / Test123!")
    print("-" * 50)
    
    app.run(
        host='0.0.0.0',
        port=5000,
        debug=app.config['DEBUG']
    )