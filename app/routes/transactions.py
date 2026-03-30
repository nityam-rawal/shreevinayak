from flask import Blueprint, request, jsonify, send_file
from flask_login import login_required, current_user
from app.database.models import db, Transaction, Party, Material, Vehicle
from app.utils.voice_parser import VoiceParser
from app.utils.invoice_generator import InvoiceGenerator
from app.utils.security import SecurityManager, sanitize_input
from datetime import datetime
import logging
import os

transactions_bp = Blueprint('transactions', __name__, url_prefix='/api/transactions')
logger = logging.getLogger(__name__)

@transactions_bp.route('/', methods=['GET'])
@login_required
def index():
    """Get all transactions API"""
    party_id = request.args.get('party_id')
    start_date = request.args.get('start_date')
    end_date = request.args.get('end_date')
    
    query = Transaction.query
    
    if party_id:
        query = query.filter_by(party_id=party_id)
    if start_date:
        try:
            date_obj = datetime.strptime(start_date, '%Y-%m-%d')
            query = query.filter(Transaction.created_at >= date_obj)
        except ValueError:
            pass
    if end_date:
        try:
            date_obj = datetime.strptime(end_date, '%Y-%m-%d')
            # Add one day to include the end date fully
            from datetime import timedelta
            date_obj = date_obj + timedelta(days=1)
            query = query.filter(Transaction.created_at < date_obj)
        except ValueError:
            pass
            
    transactions = query.order_by(Transaction.created_at.desc()).all()
    
    data = []
    for txn in transactions:
        data.append({
            'id': txn.id,
            'party': {
                'id': txn.party.id,
                'name': txn.party.name
            },
            'material': {
                'id': txn.material.id,
                'name': txn.material.name,
                'unit': txn.material.unit
            },
            'vehicle': {'id': txn.vehicle.id, 'type': txn.vehicle.type} if txn.vehicle else None,
            'quantity': txn.quantity,
            'rate': float(txn.rate) if txn.rate else 0,
            'amount': float(txn.amount) if txn.amount else 0,
            'payment_status': txn.payment_status,
            'transaction_type': txn.transaction_type,
            'date': txn.created_at.strftime('%Y-%m-%dT%H:%M:%S'),
            'notes': txn.notes
        })
    return jsonify({'transactions': data})

@transactions_bp.route('/', methods=['POST'])
@login_required
def create():
    """Create new transaction API"""
    try:
        data = request.get_json() or {}
        party_id = data.get('party_id')
        material_id = data.get('material_id')
        vehicle_id = data.get('vehicle_id')
        quantity = data.get('quantity')
        rate = data.get('rate')
        trips = data.get('trips', 1)
        payment_status = data.get('payment_status', 'pending')
        transaction_type = data.get('transaction_type', 'sell')
        notes = sanitize_input(data.get('notes', ''))
        
        if not party_id or not material_id or quantity is None or rate is None:
            return jsonify({'error': 'Missing required fields'}), 400
        
        try:
            quantity = float(quantity)
            rate = float(rate)
            trips = int(trips) if trips else 1
        except ValueError:
            return jsonify({'error': 'Invalid number format'}), 400
        
        party = Party.query.get(party_id)
        material = Material.query.get(material_id)
        
        if not party or not material:
            return jsonify({'error': 'Invalid party or material'}), 404
        
        amount = quantity * rate
        transaction = Transaction(
            party_id=party_id,
            material_id=material_id,
            vehicle_id=vehicle_id,
            transaction_type=transaction_type,
            quantity=quantity,
            rate=rate,
            amount=amount,
            trips=trips,
            payment_status=payment_status,
            notes=notes,
            created_by=current_user.id
        )
        
        db.session.add(transaction)
        db.session.commit()
        
        SecurityManager.log_audit(
            db, current_user.id, 'CREATE_TRANSACTION',
            'Transaction', transaction.id,
            f'Created transaction: {party.name} - {material.name}'
        )
        
        logger.info(f"Transaction {transaction.id} created by {current_user.username}")
        
        return jsonify({
            'success': True,
            'id': transaction.id,
            'message': 'Transaction created successfully'
        }), 201
        
    except Exception as e:
        logger.error(f"Error creating transaction: {e}")
        return jsonify({'error': str(e)}), 500

@transactions_bp.route('/batch', methods=['POST'])
@login_required
def create_batch():
    """Create multiple transactions API"""
    try:
        data = request.get_json() or {}
        party_name = sanitize_input(data.get('party_name', '').strip())
        items = data.get('items', [])
        
        if not party_name or not items:
            return jsonify({'error': 'Missing party name or items'}), 400
            
        party = Party.query.filter_by(name=party_name).first()
        if not party:
            party = Party(name=party_name, created_by=current_user.id)
            db.session.add(party)
            db.session.flush()
            
        total_amount = 0
        transaction_ids = []
        
        for item in items:
            material_id = item.get('material_id')
            quantity = float(item.get('quantity', 1))
            txn_type = item.get('type', 'sell')
            
            material = Material.query.get(material_id)
            if not material:
                continue
                
            rate = material.rate_per_unit
            amount = quantity * rate
            total_amount += amount
            
            transaction = Transaction(
                party_id=party.id,
                material_id=material_id,
                quantity=quantity,
                rate=rate,
                amount=amount,
                payment_status='pending',
                transaction_type=txn_type,
                created_by=current_user.id
            )
            
            db.session.add(transaction)
            db.session.flush()
            transaction_ids.append(transaction.id)
            
        db.session.commit()
        
        SecurityManager.log_audit(
            db, current_user.id, 'CREATE_BATCH_TRANSACTIONS',
            'Transaction', party.id,
            f'Created {len(transaction_ids)} transactions for {party.name}'
        )
        
        return jsonify({
            'success': True,
            'count': len(transaction_ids),
            'total_amount': float(total_amount),
            'ids': transaction_ids
        }), 201
        
    except Exception as e:
        logger.error(f"Error creating batch transactions: {e}")
        return jsonify({'error': str(e)}), 500

@transactions_bp.route('/<int:id>', methods=['GET'])
@login_required
def view(id):
    """View transaction details API"""
    txn = Transaction.query.get_or_404(id)
    return jsonify({
        'id': txn.id,
        'party': {'id': txn.party.id, 'name': txn.party.name, 'phone': txn.party.phone, 'address': txn.party.address},
        'material': {'id': txn.material.id, 'name': txn.material.name, 'unit': txn.material.unit},
        'vehicle': {'id': txn.vehicle.id, 'type': txn.vehicle.type, 'charges': float(txn.vehicle.charges) if txn.vehicle.charges else 0} if txn.vehicle else None,
        'quantity': txn.quantity,
        'rate': float(txn.rate) if txn.rate else 0,
        'amount': float(txn.amount) if txn.amount else 0,
        'payment_status': txn.payment_status,
        'transaction_type': txn.transaction_type,
        'date': txn.created_at.strftime('%Y-%m-%dT%H:%M:%S'),
        'notes': txn.notes,
        'voice_text': txn.voice_text
    })

@transactions_bp.route('/<int:id>', methods=['PUT'])
@login_required
def edit(id):
    """Edit transaction API"""
    transaction = Transaction.query.get_or_404(id)
    
    try:
        data = request.get_json() or {}
        
        if 'party_id' in data: transaction.party_id = data['party_id']
        if 'material_id' in data: transaction.material_id = data['material_id']
        if 'vehicle_id' in data: transaction.vehicle_id = data['vehicle_id']
        if 'transaction_type' in data: transaction.transaction_type = data['transaction_type']
        
        if 'quantity' in data: transaction.quantity = float(data['quantity'])
        if 'rate' in data: transaction.rate = float(data['rate'])
        
        transaction.amount = transaction.quantity * transaction.rate
        
        if 'payment_status' in data: transaction.payment_status = data['payment_status']
        if 'notes' in data: transaction.notes = sanitize_input(data['notes'])
        
        db.session.commit()
        
        SecurityManager.log_audit(
            db, current_user.id, 'EDIT_TRANSACTION',
            'Transaction', transaction.id
        )
        
        return jsonify({'success': True, 'message': 'Transaction updated'})
        
    except Exception as e:
        logger.error(f"Error editing transaction {id}: {e}")
        return jsonify({'error': str(e)}), 500

@transactions_bp.route('/<int:id>', methods=['DELETE'])
@login_required
def delete(id):
    """Delete transaction API"""
    transaction = Transaction.query.get_or_404(id)
    try:
        db.session.delete(transaction)
        db.session.commit()
        
        SecurityManager.log_audit(
            db, current_user.id, 'DELETE_TRANSACTION',
            'Transaction', id
        )
        return jsonify({'success': True, 'message': 'Transaction deleted'})
    except Exception as e:
        logger.error(f"Error deleting transaction {id}: {e}")
        return jsonify({'error': str(e)}), 500

@transactions_bp.route('/<int:id>/invoice', methods=['GET'])
@login_required
def download_invoice(id):
    """Download invoice PDF API"""
    transaction = Transaction.query.get_or_404(id)
    try:
        invoice_gen = InvoiceGenerator('invoices')
        invoice_path = invoice_gen.generate_invoice(transaction)
        
        return send_file(
            invoice_path,
            as_attachment=True,
            download_name=f"invoice_{transaction.id}.pdf"
        )
    except Exception as e:
        logger.error(f"Error downloading invoice: {e}")
        return jsonify({'error': str(e)}), 500
