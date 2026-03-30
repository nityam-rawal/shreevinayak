from flask import Blueprint, jsonify
from flask_login import login_required, current_user
from app.database.models import db, Transaction, Party, Material, Vehicle
from sqlalchemy import func
from datetime import datetime, timedelta

dashboard_bp = Blueprint('dashboard', __name__, url_prefix='/api/dashboard')

@dashboard_bp.route('/summary')
@login_required
def get_summary():
    """API endpoint for dashboard summary statistics"""
    total_transactions = Transaction.query.count()
    total_amount = db.session.query(func.sum(Transaction.amount)).scalar() or 0
    pending_amount = db.session.query(func.sum(Transaction.amount)).filter(
        Transaction.payment_status == 'pending'
    ).scalar() or 0
    paid_amount = db.session.query(func.sum(Transaction.amount)).filter(
        Transaction.payment_status == 'paid'
    ).scalar() or 0
    
    total_parties = Party.query.count()
    total_materials = Material.query.count()
    total_vehicles = Vehicle.query.count()
    
    # Top parties
    top_parties = db.session.query(
        Party.name,
        func.count(Transaction.id).label('count'),
        func.sum(Transaction.amount).label('total')
    ).join(Transaction).group_by(Party.id).order_by(
        func.sum(Transaction.amount).desc()
    ).limit(5).all()
    
    top_parties_data = [{'name': p.name, 'count': p.count, 'total': float(p.total) if p.total else 0} for p in top_parties]
    
    return jsonify({
        'total_transactions': total_transactions,
        'total_amount': float(total_amount),
        'pending_amount': float(pending_amount),
        'paid_amount': float(paid_amount),
        'total_parties': total_parties,
        'total_materials': total_materials,
        'total_vehicles': total_vehicles,
        'top_parties': top_parties_data
    })

@dashboard_bp.route('/recent-transactions')
@login_required
def get_recent_transactions():
    """API endpoint for recent transactions"""
    transactions = Transaction.query.order_by(
        Transaction.created_at.desc()
    ).limit(10).all()
    
    data = []
    for txn in transactions:
        data.append({
            'id': txn.id,
            'party': txn.party.name,
            'material': txn.material.name,
            'quantity': txn.quantity,
            'rate': float(txn.rate) if txn.rate else 0,
            'amount': float(txn.amount) if txn.amount else 0,
            'status': txn.payment_status,
            'date': txn.created_at.strftime('%Y-%m-%d %H:%M:%S'),
        })
    return jsonify(data)

@dashboard_bp.route('/monthly-data')
@login_required
def get_monthly_data():
    """API endpoint for monthly statistics"""
    data = []
    for i in range(5, -1, -1):
        date = datetime.utcnow() - timedelta(days=30*i)
        month_str = date.strftime('%b %Y')
        
        amount = db.session.query(func.sum(Transaction.amount)).filter(
            db.func.strftime('%Y-%m', Transaction.created_at) == date.strftime('%Y-%m')
        ).scalar() or 0
        
        count = Transaction.query.filter(
            db.func.strftime('%Y-%m', Transaction.created_at) == date.strftime('%Y-%m')
        ).count()
        
        data.append({
            'month': month_str,
            'amount': float(amount),
            'count': count,
        })
    return jsonify(data)

@dashboard_bp.route('/ledger')
@login_required
def get_ledger():
    """API endpoint for full ledger view"""
    parties = Party.query.all()
    
    total_debit = db.session.query(func.sum(Transaction.amount)).filter(
        Transaction.transaction_type == 'sell'
    ).scalar() or 0
    
    total_credit = db.session.query(func.sum(Transaction.amount)).filter(
        Transaction.transaction_type == 'buy'
    ).scalar() or 0
    
    total_outstanding = db.session.query(func.sum(Transaction.amount)).filter(
        Transaction.payment_status == 'pending'
    ).scalar() or 0
    
    ledger_data = []
    for party in parties:
        txns = Transaction.query.filter_by(party_id=party.id).count()
        if txns > 0:
            ledger_data.append({
                'party_id': party.id,
                'party_name': party.name,
                'party_phone': party.phone,
                'balance': float(party.balance) if party.balance else 0,
                'total_transactions': txns
            })
    
    return jsonify({
        'total_debit': float(total_debit),
        'total_credit': float(total_credit),
        'total_outstanding': float(total_outstanding),
        'total_parties': len(parties),
        'ledger_data': ledger_data
    })
