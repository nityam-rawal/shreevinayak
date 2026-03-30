import os
import shutil
import datetime
import logging

def backup_database(app=None):
    """Backup the SQLite database if auto_backup is enabled"""
    if app:
        auto_backup = app.config.get('AUTO_BACKUP', 'True').lower() == 'true'
    else:
        # Check from env if app not passed
        auto_backup = os.environ.get('AUTO_BACKUP', 'True').lower() == 'true'

    if not auto_backup:
        return False
        
    db_path = 'accounting_system.db'
    backup_dir = 'backups'
    
    if not os.path.exists(db_path):
        return False
        
    if not os.path.exists(backup_dir):
        os.makedirs(backup_dir)
        
    # Check if backup for today already exists (assuming daily backups as per README)
    today = datetime.datetime.now().strftime('%Y%m%d')
    existing_backups = [f for f in os.listdir(backup_dir) if f.startswith(f'accounting_system_{today}')]
    if existing_backups:
        # Already backed up today
        return True
        
    # Create timestamped backup
    timestamp = datetime.datetime.now().strftime('%Y%m%d_%H%M%S')
    backup_path = os.path.join(backup_dir, f'accounting_system_{timestamp}.db')
    
    try:
        shutil.copy2(db_path, backup_path)
        logging.info(f"Database backed up successfully to {backup_path}")
        
        # Cleanup old backups (keep last 7)
        backups = sorted([f for f in os.listdir(backup_dir) if f.startswith('accounting_system_')])
        if len(backups) > 7:
            for old_backup in backups[:-7]:
                try:
                    os.remove(os.path.join(backup_dir, old_backup))
                except OSError as e:
                    logging.error(f"Error removing old backup {old_backup}: {e}")
                    
        return True
    except Exception as e:
        logging.error(f"Database backup failed: {e}")
        return False
        
if __name__ == '__main__':
    logging.basicConfig(level=logging.INFO)
    backup_database()
