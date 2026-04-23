import os
import django

os.environ['DATABASE_URL'] = 'postgresql://foodsorderings_user:k2nFVOqJuIWn9zTWPnzrd8oXkazbzWrT@dpg-d7kca99j2pic739geng0-a.oregon-postgres.render.com/foodsorderings'
os.environ['DEBUG'] = 'True'
os.environ['SECRET_KEY'] = 'django-insecure-x(^6($apr$g(4s_t+6it6_rosz6d#rz*m=vukd!aa9r+3-re85'
os.environ['ALLOWED_HOSTS'] = 'localhost'
os.environ['DJANGO_SETTINGS_MODULE'] = 'backend.settings'

django.setup()

from django.contrib.auth import get_user_model
User = get_user_model()

username = input('Username: ')
email = input('Email: ')
password = input('Password: ')

if User.objects.filter(username=username).exists():
    print(f'User "{username}" already exists!')
else:
    User.objects.create_superuser(username=username, email=email, password=password)
    print(f'Superuser "{username}" created successfully!')
