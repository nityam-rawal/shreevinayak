from flask import Blueprint, request, jsonify
from flask_login import login_required, current_user
from app.database.models import db, Party, Material, Vehicle
from app.utils.security import sanitize_input, SecurityManager
import logging

api_bp = Blueprint('api', __name__, url_prefix='/api')
logger = logging.getLogger(__name__)


# PARTY ENDPOINTS
@api_bp.route('/parties', methods=['GET'])
@login_required
def get_parties():
    """Get all parties"""
    try:
        parties = Party.query.all()
        data = [{'id': p.id, 'name': p.name, 'phone': p.phone, 'address': p.address} 
                for p in parties]
        return jsonify(data)
    except Exception as e:
        logger.error(str(e))
        return jsonify({'error': str(e)}), 500


@api_bp.route('/parties', methods=['POST'])
@login_required
def create_party():
    """Create new party"""
    try:
        data = request.get_json()
        name = sanitize_input(data.get('name', ''))
        phone = sanitize_input(data.get('phone', ''))
        address = sanitize_input(data.get('address', ''))
        
        if not name:
            return jsonify({'error': 'Party name required'}), 400
        
        # Check if already exists
        if Party.query.filter_by(name=name).first():
            return jsonify({'error': 'Party already exists'}), 400
        
        party = Party(name=name, phone=phone, address=address, created_by=current_user.id)
        db.session.add(party)
        db.session.commit()
        
        SecurityManager.log_audit(db, current_user.id, 'CREATE_PARTY', 'Party', party.id)
        
        return jsonify({'id': party.id, 'name': party.name}), 201
    
    except Exception as e:
        logger.error(str(e))
        return jsonify({'error': str(e)}), 500


@api_bp.route('/parties/<int:id>', methods=['PUT'])
@login_required
def update_party(id):
    """Update party"""
    try:
        party = Party.query.get_or_404(id)
        data = request.get_json()
        
        if 'name' in data:
            party.name = sanitize_input(data['name'])
        if 'phone' in data:
            party.phone = sanitize_input(data['phone'])
        if 'address' in data:
            party.address = sanitize_input(data['address'])
        
        db.session.commit()
        SecurityManager.log_audit(db, current_user.id, 'UPDATE_PARTY', 'Party', id)
        
        return jsonify({'success': True})
    except Exception as e:
        logger.error(str(e))
        return jsonify({'error': str(e)}), 500


@api_bp.route('/parties/<int:id>', methods=['DELETE'])
@login_required
def delete_party(id):
    """Delete party"""
    try:
        party = Party.query.get_or_404(id)
        db.session.delete(party)
        db.session.commit()
        
        SecurityManager.log_audit(db, current_user.id, 'DELETE_PARTY', 'Party', id)
        
        return jsonify({'success': True})
    except Exception as e:
        logger.error(str(e))
        return jsonify({'error': str(e)}), 500


# MATERIAL ENDPOINTS
@api_bp.route('/materials', methods=['GET'])
@login_required
def get_materials():
    """Get all materials"""
    try:
        materials = Material.query.all()
        data = [{'id': m.id, 'name': m.name, 'unit': m.unit, 'rate_per_unit': m.rate_per_unit} 
                for m in materials]
        return jsonify(data)
    except Exception as e:
        logger.error(str(e))
        return jsonify({'error': str(e)}), 500


@api_bp.route('/materials', methods=['POST'])
@login_required
def create_material():
    """Create new material"""
    try:
        data = request.get_json()
        name = sanitize_input(data.get('name', ''))
        unit = sanitize_input(data.get('unit', 'ton'))
        rate_per_unit = float(data.get('rate_per_unit', 0))
        
        if not name:
            return jsonify({'error': 'Material name required'}), 400
        
        if Material.query.filter_by(name=name).first():
            return jsonify({'error': 'Material already exists'}), 400
        
        material = Material(name=name, unit=unit, rate_per_unit=rate_per_unit,
                           created_by=current_user.id)
        db.session.add(material)
        db.session.commit()
        
        SecurityManager.log_audit(db, current_user.id, 'CREATE_MATERIAL', 'Material', material.id)
        
        return jsonify({'id': material.id, 'name': material.name}), 201
    
    except Exception as e:
        logger.error(str(e))
        return jsonify({'error': str(e)}), 500


@api_bp.route('/materials/<int:id>', methods=['PUT'])
@login_required
def update_material(id):
    """Update material"""
    try:
        material = Material.query.get_or_404(id)
        data = request.get_json()
        
        if 'name' in data:
            material.name = sanitize_input(data['name'])
        if 'unit' in data:
            material.unit = sanitize_input(data['unit'])
        if 'rate_per_unit' in data:
            material.rate_per_unit = float(data['rate_per_unit'])
        
        db.session.commit()
        SecurityManager.log_audit(db, current_user.id, 'UPDATE_MATERIAL', 'Material', id)
        
        return jsonify({'success': True})
    except Exception as e:
        logger.error(str(e))
        return jsonify({'error': str(e)}), 500


@api_bp.route('/materials/<int:id>', methods=['DELETE'])
@login_required
def delete_material(id):
    """Delete material"""
    try:
        material = Material.query.get_or_404(id)
        db.session.delete(material)
        db.session.commit()
        
        SecurityManager.log_audit(db, current_user.id, 'DELETE_MATERIAL', 'Material', id)
        
        return jsonify({'success': True})
    except Exception as e:
        logger.error(str(e))
        return jsonify({'error': str(e)}), 500


# VEHICLE ENDPOINTS
@api_bp.route('/vehicles', methods=['GET'])
@login_required
def get_vehicles():
    """Get all vehicles"""
    try:
        vehicles = Vehicle.query.all()
        data = [{'id': v.id, 'registration_no': v.registration_no, 'vehicle_type': v.vehicle_type,
                 'owner': v.owner} for v in vehicles]
        return jsonify(data)
    except Exception as e:
        logger.error(str(e))
        return jsonify({'error': str(e)}), 500


@api_bp.route('/vehicles', methods=['POST'])
@login_required
def create_vehicle():
    """Create new vehicle"""
    try:
        data = request.get_json()
        registration_no = sanitize_input(data.get('registration_no', ''))
        vehicle_type = sanitize_input(data.get('vehicle_type', ''))
        owner = sanitize_input(data.get('owner', ''))
        
        if not registration_no:
            return jsonify({'error': 'Registration number required'}), 400
        
        if Vehicle.query.filter_by(registration_no=registration_no).first():
            return jsonify({'error': 'Vehicle already exists'}), 400
        
        vehicle = Vehicle(registration_no=registration_no, vehicle_type=vehicle_type,
                         owner=owner, created_by=current_user.id)
        db.session.add(vehicle)
        db.session.commit()
        
        SecurityManager.log_audit(db, current_user.id, 'CREATE_VEHICLE', 'Vehicle', vehicle.id)
        
        return jsonify({'id': vehicle.id, 'registration_no': vehicle.registration_no}), 201
    
    except Exception as e:
        logger.error(str(e))
        return jsonify({'error': str(e)}), 500


@api_bp.route('/vehicles/<int:id>', methods=['PUT'])
@login_required
def update_vehicle(id):
    """Update vehicle"""
    try:
        vehicle = Vehicle.query.get_or_404(id)
        data = request.get_json()
        
        if 'registration_no' in data:
            vehicle.registration_no = sanitize_input(data['registration_no'])
        if 'vehicle_type' in data:
            vehicle.vehicle_type = sanitize_input(data['vehicle_type'])
        if 'owner' in data:
            vehicle.owner = sanitize_input(data['owner'])
        
        db.session.commit()
        SecurityManager.log_audit(db, current_user.id, 'UPDATE_VEHICLE', 'Vehicle', id)
        
        return jsonify({'success': True})
    except Exception as e:
        logger.error(str(e))
        return jsonify({'error': str(e)}), 500


@api_bp.route('/vehicles/<int:id>', methods=['DELETE'])
@login_required
def delete_vehicle(id):
    """Delete vehicle"""
    try:
        vehicle = Vehicle.query.get_or_404(id)
        db.session.delete(vehicle)
        db.session.commit()
        
        SecurityManager.log_audit(db, current_user.id, 'DELETE_VEHICLE', 'Vehicle', id)
        
        return jsonify({'success': True})
    except Exception as e:
        logger.error(str(e))
        return jsonify({'error': str(e)}), 500
