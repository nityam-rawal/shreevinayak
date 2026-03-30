from flask_sqlalchemy import SQLAlchemy
from flask_login import UserMixin
from datetime import datetime
import hashlib
import os

db = SQLAlchemy()

class User(UserMixin, db.Model):
    __tablename__ = 'users'
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    password_hash = db.Column(db.String(255), nullable=False)
    role = db.Column(db.String(20), nullable=False, default='staff')  # admin, staff
    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    last_login = db.Column(db.DateTime)
    two_factor_enabled = db.Column(db.Boolean, default=False)
    two_factor_secret = db.Column(db.String(255))

    def set_password(self, password):
        """Hash password using PBKDF2 with SHA256 and store salt+hash together"""
        salt = os.urandom(32)  # 32 bytes of salt
        password_hash = hashlib.pbkdf2_hmac('sha256', password.encode(), salt, 100000)
        # Store salt + hash concatenated (salt is 32 bytes = 64 hex chars, hash is 32 bytes = 64 hex chars)
        combined = salt.hex() + password_hash.hex()
        print(f"[DEBUG] set_password: salt_hex_len={len(salt.hex())}, hash_hex_len={len(password_hash.hex())}, combined_len={len(combined)}")
        self.password_hash = combined

    def check_password(self, password):
        """Verify password by extracting salt and recomputing hash"""
        try:
            stored = self.password_hash
            if len(stored) < 128:  # Must be at least 64 (salt) + 64 (hash) = 128 hex chars
                return False
            
            # Extract salt (first 64 hex chars = first 32 bytes)
            salt = bytes.fromhex(stored[:64])
            # Extract stored hash (next 64 hex chars)
            stored_hash = stored[64:128]
            
            # Compute hash of provided password with extracted salt
            computed_hash = hashlib.pbkdf2_hmac('sha256', password.encode(), salt, 100000).hex()
            
            # Compare
            return computed_hash == stored_hash
        except Exception as e:
            logger = __import__('logging').getLogger(__name__)
            logger.error(f"Password check error: {e}")
            return False


class Party(db.Model):
    __tablename__ = 'parties'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    phone = db.Column(db.String(20))
    address = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    created_by = db.Column(db.Integer, db.ForeignKey('users.id'))
    balance = db.Column(db.Float, default=0.0)
    
    transactions = db.relationship('Transaction', backref='party', lazy=True)


class Material(db.Model):
    __tablename__ = 'materials'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    unit = db.Column(db.String(50), default='ton')
    rate_per_unit = db.Column(db.Float, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    created_by = db.Column(db.Integer, db.ForeignKey('users.id'))
    
    transactions = db.relationship('Transaction', backref='material', lazy=True)


class Vehicle(db.Model):
    __tablename__ = 'vehicles'
    id = db.Column(db.Integer, primary_key=True)
    registration_no = db.Column(db.String(50), unique=True, nullable=False)
    vehicle_type = db.Column(db.String(50))  # Tractor, Truck, etc.
    owner = db.Column(db.String(100))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    created_by = db.Column(db.Integer, db.ForeignKey('users.id'))
    
    transactions = db.relationship('Transaction', backref='vehicle', lazy=True)


class Transaction(db.Model):
    __tablename__ = 'transactions'
    id = db.Column(db.Integer, primary_key=True)
    party_id = db.Column(db.Integer, db.ForeignKey('parties.id'), nullable=False)
    material_id = db.Column(db.Integer, db.ForeignKey('materials.id'), nullable=False)
    vehicle_id = db.Column(db.Integer, db.ForeignKey('vehicles.id'))
    quantity = db.Column(db.Float, nullable=False)
    rate = db.Column(db.Float, nullable=False)
    amount = db.Column(db.Float, nullable=False)
    payment_status = db.Column(db.String(20), default='pending')  # pending, paid, partial
    payment_amount = db.Column(db.Float, default=0.0)
    trips = db.Column(db.Integer, default=1)
    notes = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    created_by = db.Column(db.Integer, db.ForeignKey('users.id'))
    voice_text = db.Column(db.Text)  # Original voice command text
    
    # Transaction type: buy, sell, advance, udhar (credit), aay (income), vayay (expense)
    transaction_type = db.Column(db.String(20), default='sell')  # sell, buy, advance, udhar, aay, vayay
    
    creator = db.relationship('User', backref='transactions', foreign_keys=[created_by])


class Payment(db.Model):
    __tablename__ = 'payments'
    id = db.Column(db.Integer, primary_key=True)
    transaction_id = db.Column(db.Integer, db.ForeignKey('transactions.id'), nullable=False)
    amount = db.Column(db.Float, nullable=False)
    payment_date = db.Column(db.DateTime, default=datetime.utcnow)
    payment_method = db.Column(db.String(50))  # cash, check, bank_transfer
    created_by = db.Column(db.Integer, db.ForeignKey('users.id'))
    notes = db.Column(db.Text)
    
    transaction = db.relationship('Transaction', backref='payments')


class AuditLog(db.Model):
    __tablename__ = 'audit_logs'
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'))
    action = db.Column(db.String(255), nullable=False)
    resource_type = db.Column(db.String(50))
    resource_id = db.Column(db.Integer)
    ip_address = db.Column(db.String(50))
    details = db.Column(db.Text)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow, index=True)
    
    user = db.relationship('User', backref='audit_logs')


class Expense(db.Model):
    __tablename__ = 'expenses'
    id = db.Column(db.Integer, primary_key=True)
    category = db.Column(db.String(50), nullable=False)
    amount = db.Column(db.Float, nullable=False)
    description = db.Column(db.Text)
    expense_date = db.Column(db.DateTime, default=datetime.utcnow)
    created_by = db.Column(db.Integer, db.ForeignKey('users.id'))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    creator = db.relationship('User', backref='expenses')
