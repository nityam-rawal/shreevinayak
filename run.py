#!/usr/bin/env python3
"""
Voice Accounting System - Main Entry Point
A secure, private web-based voice accounting system for tracking transactions,
parties, materials, vehicles, and generating invoices.
"""

import os
import sys
from app import create_app, db

# Create Flask app
app = create_app()

if __name__ == '__main__':
    # Create database if it doesn't exist
    with app.app_context():
        db.create_all()
        
        # Perform automatic backup check
        from app.utils.backup import backup_database
        backup_database(app)
        
        print("\n" + "="*60)
        print("VOICE ACCOUNTING SYSTEM")
        print("="*60)
        print("\n* Database initialized")
        print("* Auto-backup check completed")
        print("* Default users created:")
        print("  - Admin: admin / Admin@1234")
        print("  - Staff: staff / Staff@1234")
        print("\n! IMPORTANT: Change default passwords immediately!")
        print("\n> Starting development server...")
        print("> Visit: http://localhost:5000")
        print("> Use HTTPS in production!")
        print("\nPress Ctrl+C to stop the server\n")
        print("="*60 + "\n")
    
    # Run the application
    app.run(
        host='0.0.0.0',  # Listen on all interfaces
        port=5000,
        debug=True,  # Set to True for hot-reloading templates locally
        use_reloader=True
    )
