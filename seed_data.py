"""
Seed data for materials and sample parties for the accounting system
"""
import os
import sys

# Add the app directory to the path
sys.path.insert(0, os.path.dirname(__file__))

from app import create_app
from app.database.models import db, Material, Party

def seed_materials():
    """Add all materials"""
    materials = [
        # Generic Items
        {'name': 'Item 1', 'unit': 'Piece', 'rate_per_unit': 100},
        {'name': 'Item 2', 'unit': 'Kg', 'rate_per_unit': 50},
    ]
    
    for mat_data in materials:
        existing = Material.query.filter_by(name=mat_data['name']).first()
        if not existing:
            material = Material(
                name=mat_data['name'],
                unit=mat_data['unit'],
                rate_per_unit=mat_data['rate_per_unit'],
                created_by=1  # Admin user
            )
            db.session.add(material)
            print(f"✓ Added material: {mat_data['name']}")
        else:
            print(f"⚠ Material already exists: {mat_data['name']}")
    
    db.session.commit()


def seed_parties():
    """Add sample parties (suppliers, buyers, staff)"""
    parties = [
        # Generic Parties
        {'name': 'Cash Customer', 'phone': '0000000000', 'address': 'Local'},
        {'name': 'General Supplier', 'phone': '1111111111', 'address': 'Local'},
    ]
    
    for party_data in parties:
        existing = Party.query.filter_by(name=party_data['name']).first()
        if not existing:
            party = Party(
                name=party_data['name'],
                phone=party_data['phone'],
                address=party_data['address'],
                created_by=1  # Admin user
            )
            db.session.add(party)
            print(f"✓ Added party: {party_data['name']}")
        else:
            print(f"⚠ Party already exists: {party_data['name']}")
    
    db.session.commit()


if __name__ == '__main__':
    app = create_app()
    with app.app_context():
        print("\n" + "="*60)
        print("🌱 SEEDING DATABASE WITH MATERIALS AND PARTIES")
        print("="*60 + "\n")
        
        print("Adding Materials...")
        seed_materials()
        
        print("\nAdding Parties...")
        seed_parties()
        
        print("\n" + "="*60)
        print("✅ Database seeding completed!")
        print("="*60)
