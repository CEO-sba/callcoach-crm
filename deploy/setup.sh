#!/bin/bash
# CallCoach CRM - Hostinger Cloud Setup Script
# Run as root on your Hostinger Cloud server
# Usage: bash setup.sh

set -e

echo "========================================"
echo "  CallCoach CRM - Hostinger Setup"
echo "========================================"

# 1. System updates and dependencies
echo "[1/8] Installing system dependencies..."
apt-get update
apt-get install -y python3.11 python3.11-venv python3.11-dev python3-pip \
    nginx certbot python3-certbot-nginx \
    ffmpeg git curl postgresql postgresql-contrib \
    build-essential libpq-dev

# 2. Start and configure PostgreSQL
echo "[2/8] Setting up PostgreSQL..."
systemctl enable postgresql
systemctl start postgresql

# Create database and user
sudo -u postgres psql -c "CREATE USER callcoach WITH PASSWORD 'CHANGE_THIS_PASSWORD';" 2>/dev/null || echo "User already exists"
sudo -u postgres psql -c "CREATE DATABASE callcoach_db OWNER callcoach;" 2>/dev/null || echo "Database already exists"
sudo -u postgres psql -c "GRANT ALL PRIVILEGES ON DATABASE callcoach_db TO callcoach;"

# 3. Create app user
echo "[3/8] Creating app user..."
useradd -r -m -s /bin/bash callcoach 2>/dev/null || echo "User already exists"

# 4. Set up application directory
echo "[4/8] Setting up application..."
mkdir -p /opt/callcoach-crm
# Copy code (assumes you've uploaded it to /tmp/callcoach-crm or cloned from git)
if [ -d "/tmp/callcoach-crm" ]; then
    cp -r /tmp/callcoach-crm/* /opt/callcoach-crm/
    cp -r /tmp/callcoach-crm/.env /opt/callcoach-crm/ 2>/dev/null || true
fi

# 5. Python virtual environment
echo "[5/8] Setting up Python environment..."
cd /opt/callcoach-crm
python3.11 -m venv venv
source venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt
pip install gunicorn
deactivate

# 6. Create data directories
echo "[6/8] Creating data directories..."
mkdir -p /opt/callcoach-crm/uploads
mkdir -p /opt/callcoach-crm/data
chown -R callcoach:callcoach /opt/callcoach-crm

# 7. Install systemd service
echo "[7/8] Installing systemd service..."
cp /opt/callcoach-crm/deploy/callcoach.service /etc/systemd/system/callcoach.service
systemctl daemon-reload
systemctl enable callcoach
systemctl start callcoach

# 8. Configure Nginx
echo "[8/8] Configuring Nginx..."
cp /opt/callcoach-crm/deploy/nginx.conf /etc/nginx/sites-available/callcoach
ln -sf /etc/nginx/sites-available/callcoach /etc/nginx/sites-enabled/callcoach
rm -f /etc/nginx/sites-enabled/default

# Test nginx config (will fail until SSL is set up, that's ok)
nginx -t 2>/dev/null && systemctl reload nginx || echo "Nginx config test failed - SSL certs needed. Run: certbot --nginx -d callcoachsba.com -d www.callcoachsba.com"

echo ""
echo "========================================"
echo "  Setup Complete!"
echo "========================================"
echo ""
echo "NEXT STEPS:"
echo "1. Edit /opt/callcoach-crm/.env with your real values"
echo "2. Change the PostgreSQL password in this script AND in .env"
echo "3. Point callcoachsba.com DNS to this server's IP"
echo "4. Run: certbot --nginx -d callcoachsba.com -d www.callcoachsba.com"
echo "5. Restart: systemctl restart callcoach"
echo "6. Check status: systemctl status callcoach"
echo "7. View logs: journalctl -u callcoach -f"
echo ""
