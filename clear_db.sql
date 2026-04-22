-- Run this in phpMyAdmin SQL tab

-- Step 1: Clear migration history
TRUNCATE TABLE django_migrations;

-- Step 2: Drop all tables
SET FOREIGN_KEY_CHECKS = 0;
DROP TABLE IF EXISTS auth_user;
DROP TABLE IF EXISTS auth_group;
DROP TABLE IF EXISTS auth_permission;
DROP TABLE IF EXISTS django_content_type;
DROP TABLE IF EXISTS django_session;
DROP TABLE IF EXISTS auth_user_groups;
DROP TABLE IF EXISTS auth_user_user_permissions;
DROP TABLE IF EXISTS auth_group_permissions;
DROP TABLE IF EXISTS django_admin_log;
DROP TABLE IF EXISTS accounts_user;
DROP TABLE IF EXISTS accounts_user_groups;
DROP TABLE IF EXISTS accounts_user_user_permissions;
SET FOREIGN_KEY_CHECKS = 1;
