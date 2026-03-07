# CallCoach CRM - Railway Deployment Guide

Step-by-step guide to deploy CallCoach CRM live using Railway.

---

## Prerequisites

Before you start, make sure you have:

1. A GitHub account (https://github.com)
2. A Railway account (https://railway.com) - sign up with GitHub for easiest setup
3. Your Anthropic API key (from https://console.anthropic.com)
4. Git installed on your computer

---

## Step 1: Push Code to GitHub

Open Terminal on your computer and navigate to the callcoach-crm folder.

```bash
cd /path/to/callcoach-crm

# Initialize git repo (skip if already done)
git init

# Add all files
git add .

# Make first commit
git commit -m "CallCoach CRM - initial deployment"
```

Now create a repo on GitHub:

1. Go to https://github.com/new
2. Repository name: `callcoach-crm`
3. Set it to **Private**
4. Do NOT initialize with README (you already have code)
5. Click "Create repository"

GitHub will show you commands. Run the ones under "push an existing repository":

```bash
git remote add origin https://github.com/YOUR_USERNAME/callcoach-crm.git
git branch -M main
git push -u origin main
```

Replace YOUR_USERNAME with your actual GitHub username.

---

## Step 2: Create Railway Project

1. Go to https://railway.com and sign in with GitHub
2. Click **"New Project"** (top right)
3. Select **"Deploy from GitHub Repo"**
4. Find and select your `callcoach-crm` repo
5. Railway will detect the Dockerfile and start building

**Do NOT click deploy yet.** You need to set environment variables first.

---

## Step 3: Set Environment Variables

In your Railway project dashboard:

1. Click on the service (it should show your repo name)
2. Go to the **"Variables"** tab
3. Click **"Raw Editor"** and paste these variables:

```
ANTHROPIC_API_KEY=sk-ant-your-actual-key-here
SECRET_KEY=generate-a-random-string-here-at-least-64-characters-long
ANTHROPIC_MODEL=claude-sonnet-4-20250514
WHISPER_MODEL=base
PORT=8000
```

**Important:**

- Replace `sk-ant-your-actual-key-here` with your real Anthropic API key
- For SECRET_KEY, generate a random string. You can use this command in Terminal:

```bash
python3 -c "import secrets; print(secrets.token_hex(32))"
```

4. Click **"Update Variables"**

---

## Step 4: Add Persistent Storage (Critical)

SQLite needs persistent disk storage. Without this, your database resets on every deploy.

1. In your Railway project, click **"+ New"** (top right)
2. Select **"Volume"**
3. Mount path: `/app/data`
4. Name: `callcoach-data`
5. Click **"Add"**
6. Also add another volume for uploads:
   - Mount path: `/app/uploads`
   - Name: `callcoach-uploads`

This ensures your database and audio uploads survive redeploys.

---

## Step 5: Deploy

1. Click on your service
2. Go to **"Settings"** tab
3. Under **"Networking"**, click **"Generate Domain"**
   - This gives you a URL like `callcoach-crm-production.up.railway.app`
4. Railway should auto-deploy from your GitHub push
5. If not, click **"Deploy"** manually

Watch the build logs. It should:
- Pull the Docker image
- Install Python dependencies
- Install ffmpeg
- Start the uvicorn server

Build takes about 2-3 minutes the first time.

---

## Step 6: Verify

1. Open your Railway-generated URL in browser
2. You should see the CallCoach CRM login page
3. Register a new account (first user becomes admin)
4. Log in and verify:
   - Dashboard loads
   - Calls page works
   - Pipeline with drag-and-drop works
   - AI Coach responds (if Anthropic key is set correctly)

Check the /health endpoint to confirm the server is running:

```
https://your-app.up.railway.app/health
```

Should return: `{"status": "healthy", "app": "CallCoach CRM", "version": "1.0.0"}`

---

## Step 7: Custom Domain (Optional)

To use your own domain like crm.skinbusinessaccelerator.services:

1. In Railway, go to **Settings > Networking**
2. Click **"Custom Domain"**
3. Enter: `crm.skinbusinessaccelerator.services`
4. Railway shows you a CNAME record
5. Go to your domain DNS settings (wherever you manage your domain)
6. Add a CNAME record:
   - **Host/Name:** `crm`
   - **Value/Target:** The value Railway gives you (looks like `xxx.up.railway.app`)
   - **TTL:** 300
7. Wait 5-10 minutes for DNS propagation
8. Railway auto-provisions SSL (HTTPS) for your domain

---

## Updating the App

Every time you push to GitHub, Railway auto-deploys:

```bash
cd /path/to/callcoach-crm
git add .
git commit -m "description of changes"
git push
```

Railway picks up the push and redeploys in ~2 minutes.

---

## Railway Pricing

- Free trial: $5 credit (enough for ~2-3 weeks)
- Hobby plan: $5/month + usage (typically $5-7/month total for this app)
- No credit card needed to start with the trial

---

## Troubleshooting

**Build fails:**
- Check build logs in Railway dashboard
- Most common: missing dependency in requirements.txt

**App crashes on start:**
- Check deploy logs for Python errors
- Verify environment variables are set correctly
- Make sure ANTHROPIC_API_KEY is valid

**Database resets after deploy:**
- You forgot to add the volume (Step 4)
- Volume mount path must be exactly `/app/data`

**Audio upload/playback not working:**
- Volume for `/app/uploads` must be added
- Check that file size is under 500MB

**AI Coach not responding:**
- Check ANTHROPIC_API_KEY is correct in Variables tab
- Check deploy logs for API errors

**502 Bad Gateway:**
- App is still starting, wait 30 seconds
- Check if PORT variable is set to 8000

---

## Security Checklist Before Going Live

- [ ] Change SECRET_KEY to a strong random value (not the default)
- [ ] Set ANTHROPIC_API_KEY as environment variable (never in code)
- [ ] Remove any test users from the database
- [ ] Set repository to Private on GitHub
- [ ] Enable HTTPS (Railway does this automatically)
- [ ] Use a strong password for your admin account
