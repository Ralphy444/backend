@echo off
echo Resetting database and migrations...
echo.
echo Step 1: Delete migration files (except __init__.py)
del /q accounts\migrations\*.py 2>nul
echo from django.db import migrations > accounts\migrations\__init__.py
echo.
echo Step 2: Run this SQL in phpMyAdmin:
echo DROP DATABASE IF EXISTS foodordering;
echo CREATE DATABASE foodordering;
echo.
echo Step 3: After running SQL, press any key to continue...
pause
echo.
echo Step 4: Creating new migrations...
python manage.py makemigrations
echo.
echo Step 5: Applying migrations...
python manage.py migrate
echo.
echo Done! You can now create a superuser with: python manage.py createsuperuser
pause
