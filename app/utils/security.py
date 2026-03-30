from flask_login import LoginManager, login_required, current_user
from functools import wraps
from datetime import datetime, timedelta
import secrets
import hashlib
from flask import request, abort, session
import logging

class SecurityManager:
    """Security management for the application"""
    
    def __init__(self, app=None):
        self.app = app
        self.login_manager = LoginManager()
        self.logger = logging.getLogger(__name__)
        
        if app:
            self.init_app(app)
    
    def init_app(self, app):
        """Initialize with Flask app"""
        self.app = app
        self.login_manager.init_app(app)
        self.login_manager.login_view = 'auth.login'
        self.setup_security_headers()
    
    def setup_security_headers(self):
        """Setup security headers middleware"""
        @self.app.after_request
        def set_security_headers(response):
            # Prevent clickjacking
            response.headers['X-Frame-Options'] = 'SAMEORIGIN'
            response.headers['X-Content-Type-Options'] = 'nosniff'
            response.headers['X-XSS-Protection'] = '1; mode=block'
            # Content Security Policy
            response.headers['Content-Security-Policy'] = "default-src 'self'"
            response.headers['Strict-Transport-Security'] = 'max-age=31536000; includeSubDomains'
            return response
    
    @staticmethod
    def require_role(*roles):
        """Decorator to require specific roles"""
        def decorator(f):
            @wraps(f)
            def decorated_function(*args, **kwargs):
                if not current_user.is_authenticated:
                    abort(401)
                if current_user.role not in roles:
                    abort(403)
                return f(*args, **kwargs)
            return decorated_function
        return decorator
    
    @staticmethod
    def require_admin(f):
        """Decorator to require admin role"""
        @wraps(f)
        def decorated_function(*args, **kwargs):
            if not current_user.is_authenticated:
                abort(401)
            if current_user.role != 'admin':
                abort(403)
            return f(*args, **kwargs)
        return decorated_function
    
    @staticmethod
    def validate_password(password):
        """
        Validate password strength
        - Minimum 8 characters
        - At least one uppercase letter
        - At least one lowercase letter
        - At least one digit
        - At least one special character
        """
        errors = []
        
        if len(password) < 8:
            errors.append('Password must be at least 8 characters long')
        
        if not any(c.isupper() for c in password):
            errors.append('Password must contain at least one uppercase letter')
        
        if not any(c.islower() for c in password):
            errors.append('Password must contain at least one lowercase letter')
        
        if not any(c.isdigit() for c in password):
            errors.append('Password must contain at least one digit')
        
        special_chars = '!@#$%^&*()_+-=[]{}|;:,.<>?'
        if not any(c in special_chars for c in password):
            errors.append('Password must contain at least one special character')
        
        return {
            'valid': len(errors) == 0,
            'errors': errors
        }
    
    @staticmethod
    def check_session_timeout(timeout_minutes=30):
        """Check and enforce session timeout"""
        session.permanent = True
        session['last_activity'] = datetime.utcnow()
        
        if 'last_activity' in session:
            last_activity = session.get('last_activity')
            if last_activity:
                elapsed = datetime.utcnow() - last_activity
                if elapsed > timedelta(minutes=timeout_minutes):
                    session.clear()
                    return False
        return True
    
    @staticmethod
    def check_ip_restriction(trusted_ips):
        """Verify request comes from trusted IP"""
        client_ip = request.remote_addr
        if client_ip not in trusted_ips:
            return False
        return True
    
    @staticmethod
    def check_rate_limit(user_id, max_requests=100, time_window=3600):
        """Rate limiting to prevent abuse"""
        # This should be implemented with Redis or similar
        # For now, basic implementation
        return True
    
    @staticmethod
    def log_audit(db, user_id, action, resource_type=None, 
                 resource_id=None, details=None):
        """Log audit trail for compliance"""
        from app.database.models import AuditLog
        
        try:
            audit_log = AuditLog(
                user_id=user_id,
                action=action,
                resource_type=resource_type,
                resource_id=resource_id,
                ip_address=request.remote_addr,
                details=details,
                timestamp=datetime.utcnow()
            )
            db.session.add(audit_log)
            db.session.commit()
        except Exception as e:
            logging.error(f"Failed to log audit: {str(e)}")


class RateLimiter:
    """Simple rate limiter for API requests"""
    
    def __init__(self):
        self.requests = {}
    
    def is_allowed(self, identifier, max_requests=10, time_window=60):
        """Check if request is allowed"""
        current_time = datetime.utcnow()
        
        if identifier not in self.requests:
            self.requests[identifier] = []
        
        # Clean old requests
        self.requests[identifier] = [
            req_time for req_time in self.requests[identifier]
            if (current_time - req_time).total_seconds() < time_window
        ]
        
        if len(self.requests[identifier]) < max_requests:
            self.requests[identifier].append(current_time)
            return True
        
        return False


def sanitize_input(data):
    """Sanitize user input to prevent SQL injection and XSS"""
    if isinstance(data, str):
        # Remove potentially harmful characters
        dangerous_chars = ['<', '>', '"', "'", ';', '--', '/*', '*/']
        for char in dangerous_chars:
            data = data.replace(char, '')
        return data.strip()
    return data


def validate_input(data, field_type='string', required=True):
    """Validate input based on type"""
    if not data and required:
        return False, "Field is required"
    
    if field_type == 'email':
        import re
        pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
        if not re.match(pattern, data):
            return False, "Invalid email format"
    
    elif field_type == 'phone':
        import re
        pattern = r'^[0-9]{10,}$'
        if not re.match(pattern, data.replace('-', '').replace(' ', '')):
            return False, "Invalid phone number"
    
    elif field_type == 'number':
        try:
            float(data)
        except:
            return False, "Invalid number"
    
    return True, "Valid"
