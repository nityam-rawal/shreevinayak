import os
import logging
from flask import Flask, jsonify
from flask_cors import CORS
from flask_login import LoginManager, current_user
from app.database.models import db, User
from app.utils.security import SecurityManager
from datetime import datetime

def create_app(config=None):
    """Application factory"""
    app = Flask(__name__)
    
    # Configuration
    app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'your-secret-key-change-in-production')
    app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///accounting_system.db'
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
    app.config['PERMANENT_SESSION_LIFETIME'] = 1800  # 30 minutes
    app.config['SESSION_COOKIE_SECURE'] = False  # Set True for HTTPS in production
    app.config['SESSION_COOKIE_HTTPONLY'] = True
    app.config['SESSION_COOKIE_SAMESITE'] = 'Lax'
    
    # Enable CORS for Next.js frontend
    CORS(app, supports_credentials=True, origins=["http://localhost:3000", "http://127.0.0.1:3000"])
    
    # Additional config from parameter
    if config:
        app.config.update(config)
    
    # Initialize extensions
    db.init_app(app)
    
    # Initialize security
    security = SecurityManager(app)
    
    # Initialize login manager
    login_manager = LoginManager()
    login_manager.init_app(app)
    
    # For JSON API, we don't redirect to a login view, we return 401
    @login_manager.unauthorized_handler
    def unauthorized():
        return jsonify({'error': 'Unauthorized', 'code': 401}), 401
    
    @login_manager.user_loader
    def load_user(user_id):
        return User.query.get(int(user_id))
    
    # Setup logging
    setup_logging(app)
    
    # Register blueprints
    from app.routes.auth import auth_bp
    from app.routes.dashboard import dashboard_bp
    from app.routes.transactions import transactions_bp
    from app.routes.api import api_bp
    
    app.register_blueprint(auth_bp)
    app.register_blueprint(dashboard_bp)
    app.register_blueprint(transactions_bp)
    app.register_blueprint(api_bp)
    
    # Root route handler for API check
    @app.route('/')
    def index():
        """Root API Health Check"""
        return jsonify({
            'status': 'online',
            'version': '2.0.0',
            'api_type': 'JSON REST',
            'authenticated': current_user.is_authenticated
        })
    
    # Create database tables
    with app.app_context():
        db.create_all()
        create_default_user(db)
    
    return app


def setup_logging(app):
    """Setup application logging"""
    log_dir = 'logs'
    if not os.path.exists(log_dir):
        os.makedirs(log_dir)
    
    # File handler
    file_handler = logging.FileHandler(f'{log_dir}/accounting_system.log')
    file_handler.setFormatter(logging.Formatter(
        '%(asctime)s %(levelname)s: %(message)s [in %(pathname)s:%(lineno)d]'
    ))
    file_handler.setLevel(logging.INFO)
    
    # App logger
    app.logger.addHandler(file_handler)
    app.logger.setLevel(logging.INFO)
    app.logger.info('API Application started')


def create_default_user(db):
    """Create default admin user if not exists"""
    try:
        admin = User.query.filter_by(username='admin').first()
        if not admin:
            admin = User(username='admin', role='admin', is_active=True)
            admin.set_password('Admin@1234')  # CHANGE THIS IN PRODUCTION!
            db.session.add(admin)
            
            # Create default staff user
            staff = User(username='staff', role='staff', is_active=True)
            staff.set_password('Staff@1234')  # CHANGE THIS IN PRODUCTION!
            db.session.add(staff)
            
            db.session.commit()
            print("✓ Default users created: admin / Admin@1234, staff / Staff@1234")
    except Exception as e:
        print(f"Error creating default users: {e}")
