import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'backend.settings')
django.setup()

from django.db import connection

with connection.cursor() as cursor:
    cursor.execute("SET FOREIGN_KEY_CHECKS = 0")
    cursor.execute("TRUNCATE TABLE django_migrations")
    
    # Drop all tables
    tables = [
        'auth_user', 'auth_group', 'auth_permission', 'django_content_type',
        'django_session', 'auth_user_groups', 'auth_user_user_permissions',
        'auth_group_permissions', 'django_admin_log', 'accounts_user',
        'accounts_user_groups', 'accounts_user_user_permissions'
    ]
    
    for table in tables:
        try:
            cursor.execute(f"DROP TABLE IF EXISTS {table}")
        except:
            pass
    
    cursor.execute("SET FOREIGN_KEY_CHECKS = 1")
    print("Database reset complete!")
