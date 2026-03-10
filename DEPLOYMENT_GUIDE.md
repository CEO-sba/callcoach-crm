# CallCoach CRM - Hostinger Cloud Deployment Guide

Step-by-step guide to deploy CallCoach CRM on Hostinger Cloud VPS.

---

## Prerequisites

1. A GitHub account (https://github.com)
2. A Hostinger Cloud VPS (Ubuntu 22.04 recommended)
3. Your Anthropic API key (from https://console.anthropic.com)
4. Domain pointed to your server (callcoachsba.com)
5. SSH access to your server

---

## Step 1: Push Code to GitHub

```bash
cd /path/to/callcoach-crm
git add .
git commit -m "CallCoach CRM update"
git push origin main
```

---

## Step 2: Server Setup (First Time Only)

SSH into your Hostinger Cloud VPS and run the setup script:

```bash
ssh root@your-server-ip

# Clone the repo
cd /tmp
git clone https://github.com/CEO-sba/callcoach-crm.git

# Run setup
bash /tmp/callcoach-crm/deploy/setup.sh
```

This installs Python 3.11, PostgreSQL, Nginx, ffmpeg, and configures the systemd service.

---

## Step 3: Configure Environment

Edit the .env file on the server:

```bash
nano /opt/callcoach-crm/.env
```

Set these values:

```
ENV=production
DATABASE_URL=postgresql://callcoach:YOUR_SECURE_DB_PASSWORD@localhost:5432/callcoach_db
ANTHROPIC_API_KEY=sk-ant-your-actual-key
SECRET_KEY=your-random-64-char-string
ANTHROPIC_MODEL=claude-sonnet-4-20250514
GROQ_API_KEY=your-groq-key
```

Generate a secure SECRET_KEY:

```bash
python3 -c "import secrets; print(secrets.token_hex(32))"
```

---

## Step 4: Run Database Migrations

```bash
cd /opt/callcoach-crm
source venv/bin/activate
alembic upgrade head
deactivate
```

---

## Step 5: SSL Certificate

```bash
certbot --nginx -d callcoachsba.com -d www.callcoachsba.com
```

---

## Step 6: Start the Service

```bash
systemctl restart callcoach
systemctl status callcoach
```

Check health:

```
https://callcoachsba.com/health
```

---

## Step 7: Bootstrap Super Admin

After the app is running, create the first super admin:

```bash
curl -X POST https://callcoachsba.com/api/admin/bootstrap \
  -H "Content-Type: application/json" \
  -d '{"secret_key": "YOUR_SECRET_KEY", "email": "admin@callcoachsba.com", "password": "your-secure-password", "full_name": "Admin"}'
```

Then access the admin portal at: https://callcoachsba.com/admin

---

## Updating the App

SSH into the server and pull latest changes:

```bash
ssh root@your-server-ip
cd /opt/callcoach-crm
git pull origin main
source venv/bin/activate
pip install -r requirements.txt
alembic upgrade head
deactivate
systemctl restart callcoach
```

---

## Useful Commands

```bash
# Check service status
systemctl status callcoach

# View live logs
journalctl -u callcoach -f

# Restart service
systemctl restart callcoach

# Check Nginx
nginx -t
systemctl reload nginx

# PostgreSQL
sudo -u postgres psql -d callcoach_db
```

---

## Troubleshooting

**App won't start:** Check logs with `journalctl -u callcoach -f`

**Database connection failed:** Verify DATABASE_URL in .env and that PostgreSQL is running

**502 Bad Gateway:** App hasn't started yet or crashed. Check service logs.

**SSL issues:** Re-run certbot or check certificate renewal with `certbot renew --dry-run`

---

## Security Checklist

- [ ] Change PostgreSQL password from default
- [ ] Set a strong SECRET_KEY (not default)
- [ ] Set ANTHROPIC_API_KEY as env variable (never in code)
- [ ] GitHub repo set to Private
- [ ] SSL enabled via certbot
- [ ] Firewall configured (ports 22, 80, 443 only)
- [ ] Strong admin password
