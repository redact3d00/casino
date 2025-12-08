from flask import Blueprint, request, jsonify
from flask_login import login_required, current_user
from services.game_service import GameService

games_bp = Blueprint('games', __name__)

@games_bp.route('/available', methods=['GET'])
@login_required
def get_available_games():
    games = GameService.get_available_games()
    return jsonify({'games': games})

@games_bp.route('/<int:game_id>/play', methods=['POST'])
@login_required
def play_game(game_id):
    data = request.get_json()
    bet_amount = float(data.get('amount', 0))
    
    if bet_amount <= 0:
        return jsonify({'error': 'Invalid bet amount'}), 400
    
    result = GameService.play_game(current_user, game_id, bet_amount, request)
    
    if not result['success']:
        return jsonify({'error': result['error']}), 400
    
    return jsonify(result)

@games_bp.route('/history', methods=['GET'])
@login_required
def get_game_history():
    page = request.args.get('page', 1, type=int)
    per_page = request.args.get('per_page', 20, type=int)
    
    result = GameService.get_user_game_history(current_user.id, page, per_page)
    return jsonify(result)