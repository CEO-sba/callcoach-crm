#!/bin/bash
set -e
LOG=/opt/callcoach-crm/deploy.log
exec > >(tee -a $LOG) 2>&1
echo "=== DEPLOY START $(date) ==="
cd /opt/callcoach-crm

echo "--- Step 1: Install pip dependencies ---"
source venv/bin/activate
pip install -r requirements.txt --quiet
echo "DONE: pip install"

echo "--- Step 2: Check .env ---"
if [ -f .env ]; then echo ".env exists"; cat .env | grep -v KEY | grep -v SECRET | grep -v PASSWORD | head -5; else echo "WARNING: No .env file!"; fi

echo "--- Step 3: Install systemd service ---"
cp deploy/callcoach.service /etc/systemd/system/callcoach.service
systemctl daemon-reload
systemctl enable callcoach
echo "DONE: systemd configured"

echo "--- Step 4: Install nginx config ---"
cp deploy/nginx.conf /etc/nginx/sites-available/callcoach
ln -sf /etc/nginx/sites-available/callcoach /etc/nginx/sites-enabled/callcoach
rm -f /etc/nginx/sites-enabled/default
nginx -t
echo "DONE: nginx configured"

echo "--- Step 5: Run alembic migration ---"
cd /opt/callcoach-crm
alembic upgrade head 2>&1 || echo "WARN: alembic migration failed (may need DATABASE_URL)"

echo "--- Step 6: Restart services ---"
systemctl restart callcoach
systemctl restart nginx
sleep 2

echo "--- Step 7: Check status ---"
systemctl status callcoach --no-pager -l | head -20
echo ""
curl -s -o /dev/null -w "HTTP Status: %{http_code}\n" http://localhost:8000/health || echo "Health check failed"
echo "=== DEPLOY COMPLETE $(date) ==="
