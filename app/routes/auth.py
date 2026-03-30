from flask import Blueprint, request, jsonify, session
from flask_login import login_user, logout_user, login_required, current_user
from app.database.models import db, User
from app.utils.security import SecurityManager, sanitize_input
from datetime import datetime
import logging

auth_bp = Blueprint('auth', __name__, url_prefix='/api/auth')
logger = logging.getLogger(__name__)

@auth_bp.route('/check', methods=['GET'])
def check_auth():
    """Check if user is authenticated"""
    if current_user.is_authenticated:
        return jsonify({
            'authenticated': True,
            'user': {
                'id': current_user.id,
                'username': current_user.username,
                'role': current_user.role
            }
        })
    return jsonify({'authenticated': False}), 401

@auth_bp.route('/login', methods=['POST'])
def login():
    """User login route (JSON)"""
    if current_user.is_authenticated:
        return jsonify({'success': True, 'message': 'Already logged in'})
    
    data = request.get_json() or {}
    username = sanitize_input(data.get('username', ''))
    password = data.get('password', '')
    
    if not username or not password:
        return jsonify({'error': 'Username and password are required'}), 400
    
    user = User.query.filter_by(username=username).first()
    
    if user and user.check_password(password) and user.is_active:
        login_user(user)
        user.last_login = datetime.utcnow()
        db.session.commit()
        
        logger.info(f"User {username} logged in successfully from {request.remote_addr}")
        return jsonify({
            'success': True,
            'user': {
                'id': user.id,
                'username': user.username,
                'role': user.role
            }
        })
    else:
        logger.warning(f"Failed login attempt for user {username} from {request.remote_addr}")
        return jsonify({'error': 'Invalid username or password'}), 401

@auth_bp.route('/logout', methods=['POST'])
@login_required
def logout():
    """User logout route (JSON)"""
    logger.info(f"User {current_user.username} logged out")
    logout_user()
    return jsonify({'success': True, 'message': 'Logged out successfully'})

@auth_bp.route('/register', methods=['POST'])
@login_required
def register():
    """User registration route (JSON) - Admin only"""
    if current_user.role != 'admin':
        return jsonify({'error': 'Unauthorized access'}), 403
    
    data = request.get_json() or {}
    username = sanitize_input(data.get('username', ''))
    password = data.get('password', '')
    role = data.get('role', 'staff')
    
    if not username or not password:
        return jsonify({'error': 'Username and password are required'}), 400
    
    if len(username) < 3:
        return jsonify({'error': 'Username must be at least 3 characters'}), 400
    
    validation = SecurityManager.validate_password(password)
    if not validation['valid']:
        return jsonify({'error': 'Password not strong enough: ' + ', '.join(validation['errors'])}), 400
    
    if User.query.filter_by(username=username).first():
        return jsonify({'error': 'Username already exists'}), 400
    
    user = User(username=username, role=role, is_active=True)
    user.set_password(password)
    db.session.add(user)
    db.session.commit()
    
    logger.info(f"New user {username} created by {current_user.username}")
    return jsonify({'success': True, 'user_id': user.id}), 201

@auth_bp.route('/change-password', methods=['POST'])
@login_required
def change_password():
    """Change user password (JSON)"""
    data = request.get_json() or {}
    current_password = data.get('current_password', '')
    new_password = data.get('new_password', '')
    
    if not current_user.check_password(current_password):
        return jsonify({'error': 'Current password is incorrect'}), 400
    
    validation = SecurityManager.validate_password(new_password)
    if not validation['valid']:
        return jsonify({'error': 'New password not strong enough: ' + ', '.join(validation['errors'])}), 400
    
    current_user.set_password(new_password)
    db.session.commit()
    
    logger.info(f"Password changed for user {current_user.username}")
    return jsonify({'success': True, 'message': 'Password changed successfully'})
