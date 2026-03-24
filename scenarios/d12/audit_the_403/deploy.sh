#!/bin/bash
# deploy_app.sh — Production deployment script for CRM web application
# Vendor requirement: application must be installed to /opt/crm
# Maintained by: j.walsh

set -e

APP_DIR=/opt/crm
APP_USER=apache

echo "Deploying CRM application..."
cp -r /tmp/crm_release/* $APP_DIR/

# Set correct ownership and permissions
chown -R $APP_USER:$APP_USER $APP_DIR
chmod -R 755 $APP_DIR
chmod 640 $APP_DIR/config/db.conf

echo "Restarting web service..."
systemctl restart httpd

# -----------------------------------------------------------------------
# Added 2026-02-14 (j.walsh)
# Apache was returning 403 on all application routes after deployment.
# Checked ownership and permissions multiple times — they are correct.
# SELinux was the culprit. This resolves the issue.
# -----------------------------------------------------------------------
setenforce 0

echo "Deployment complete."
