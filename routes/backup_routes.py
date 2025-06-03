from flask import Blueprint, Response, current_app
import os
import subprocess
import logging
from datetime import datetime
from routes.auth_routes import require_auth

# Create a Blueprint for backup routes
backup_bp = Blueprint('backup', __name__)

@backup_bp.route('/admin/backup/database', methods=['GET'])
@require_auth
def backup_database():
    """
    Creates a complete database backup and downloads it as a .sql file
    
    What it does:
    - Uses PostgreSQL's pg_dump tool to create a full database backup
    - Includes all tables, data, indexes, and schema
    - Returns the backup as a downloadable .sql file
    - Filename includes timestamp for organization
    """
    try:
        # Get database URL from environment
        database_url = os.getenv('DATABASE_URL')
        if not database_url:
            return "DATABASE_URL not set", 500
        
        # Create a timestamp for the filename
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        filename = f"recovery_manager_backup_{timestamp}.sql"
        
        # Use pg_dump to create a complete backup
        process = subprocess.Popen(
            ['pg_dump', database_url, '--verbose', '--clean', '--no-owner', '--no-privileges'],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE
        )
        
        stdout, stderr = process.communicate()
        
        if process.returncode != 0:
            logging.error(f"Backup failed: {stderr.decode()}")
            return f"Backup failed: {stderr.decode()}", 500
        
        # Return the SQL dump as a downloadable file
        return Response(
            stdout,
            mimetype='application/sql',
            headers={
                'Content-Disposition': f'attachment; filename={filename}',
                'Content-Type': 'application/octet-stream'
            }
        )
        
    except Exception as e:
        logging.error(f"Backup error: {e}")
        return f"Error creating backup: {str(e)}", 500

@backup_bp.route('/admin/backup/users', methods=['GET'])
@require_auth
def backup_users_table():
    """
    Creates a backup of ONLY the users table
    
    What it does:
    - Backs up just the users table (not the entire database)
    - Smaller file size, faster download
    - Good for regular user data backups
    - Includes all user data: names, numbers, locations, Stripe IDs, etc.
    """
    try:
        # Get database URL from environment
        database_url = os.getenv('DATABASE_URL')
        if not database_url:
            return "DATABASE_URL not set", 500
        
        # Create a timestamp for the filename
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        filename = f"users_backup_{timestamp}.sql"
        
        # Use pg_dump to create a backup of just the users table
        process = subprocess.Popen(
            ['pg_dump', database_url, '-t', 'users', '--data-only', '--column-inserts'],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE
        )
        
        stdout, stderr = process.communicate()
        
        if process.returncode != 0:
            logging.error(f"Users backup failed: {stderr.decode()}")
            return f"Users backup failed: {stderr.decode()}", 500
        
        # Return the SQL dump as a downloadable file
        return Response(
            stdout,
            mimetype='application/sql',
            headers={
                'Content-Disposition': f'attachment; filename={filename}',
                'Content-Type': 'application/octet-stream'
            }
        )
        
    except Exception as e:
        logging.error(f"Users backup error: {e}")
        return f"Error creating users backup: {str(e)}", 500

@backup_bp.route('/admin/backup/export-csv', methods=['GET'])
@require_auth
def export_users_csv():
    """
    Export users as CSV file for easy viewing in Excel/Google Sheets
    
    What it does:
    - Exports user data in CSV format
    - Easy to open in spreadsheet applications
    - Good for sharing user lists or analysis
    """
    try:
        from app import user_manager
        import csv
        from io import StringIO
        
        if user_manager is None:
            return "Service not ready", 503
        
        # Get all users
        users = user_manager.get_users(active_only=False)
        
        # Create CSV in memory
        output = StringIO()
        writer = csv.writer(output)
        
        # Write header
        writer.writerow([
            'Name', 'Phone Number', 'Location', 'Range (Miles)', 
            'Status', 'Stripe Customer ID', 'Subscription ID', 
            'Created Date', 'Updated Date'
        ])
        
        # Write user data
        for user in users:
            writer.writerow([
                user.name,
                user.number,
                user.location,
                user.range_miles,
                'Active' if getattr(user, 'active', True) else 'Inactive',
                user.stripe_customer_id or '',
                user.subscription_id or '',
                user.created_at,
                user.updated_at
            ])
        
        # Create filename with timestamp
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        filename = f"users_export_{timestamp}.csv"
        
        # Return CSV file
        return Response(
            output.getvalue(),
            mimetype='text/csv',
            headers={
                'Content-Disposition': f'attachment; filename={filename}'
            }
        )
        
    except Exception as e:
        logging.error(f"CSV export error: {e}")
        return f"Error exporting CSV: {str(e)}", 500
