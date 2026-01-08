# Deployment Guide - Gold Loan Management System

This guide covers deploying the Gold Loan Management System to various cloud platforms directly from GitHub.

## 🚀 Quick Start

### One-Click Deployments

The fastest way to deploy this project is using one-click deployment buttons:

**Railway** (Recommended for beginners)
1. Click the "Deploy on Railway" button in the README
2. Sign in with GitHub
3. Configure environment variables
4. Deploy automatically

**Render** (Free tier available)
1. Click the "Deploy to Render" button in the README
2. Sign in with GitHub
3. Configure environment variables
4. Deploy with zero configuration

### What Gets Deployed?

When you deploy from GitHub, the platform automatically:
- ✅ Installs all Python dependencies from `requirements.txt`
- ✅ Sets up the Django application with Gunicorn
- ✅ Configures static file serving with WhiteNoise
- ✅ Runs database migrations
- ✅ Collects static files
- ✅ Provides a public URL for your application

## Table of Contents
- [Prerequisites](#prerequisites)
- [Environment Variables](#environment-variables)
- [Platform-Specific Deployments](#platform-specific-deployments)
  - [Heroku](#deploy-to-heroku)
  - [Railway](#deploy-to-railway)
  - [Render](#deploy-to-render)
  - [PythonAnywhere](#deploy-to-pythonanywhere)
- [GitHub Actions CI/CD](#github-actions-cicd)
- [Post-Deployment Steps](#post-deployment-steps)

---

## Prerequisites

Before deploying, ensure you have:
1. A GitHub account with this repository
2. An account on your chosen deployment platform
3. Required environment variables (see below)

## Environment Variables

Create a `.env` file based on `.env.example`. Required variables:

```env
DEBUG=False
SECRET_KEY=your-production-secret-key-generate-a-strong-one
ALLOWED_HOSTS=yourdomain.com,www.yourdomain.com

# Optional: Database URL (if not using SQLite)
DATABASE_URL=postgresql://user:password@host:5432/database

# Twilio Configuration (for OTP functionality)
TWILIO_ACCOUNT_SID=your-twilio-sid
TWILIO_AUTH_TOKEN=your-twilio-token
TWILIO_VERIFY_SERVICE_SID=your-verify-service-sid
OTP_ADMIN_MOBILE=+1234567890
```

### Generating a Strong SECRET_KEY

```python
python -c 'from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())'
```

---

## Platform-Specific Deployments

### Deploy to Heroku

#### Via Heroku Dashboard:

1. **Create a New App**
   - Go to [Heroku Dashboard](https://dashboard.heroku.com/)
   - Click "New" → "Create new app"
   - Enter app name and region

2. **Connect GitHub**
   - In "Deployment method" section, select "GitHub"
   - Search for and connect this repository
   - Enable "Automatic deploys" from main branch (optional)

3. **Configure Environment Variables**
   - Go to "Settings" → "Config Vars"
   - Add all required environment variables from above
   - Heroku automatically sets `DATABASE_URL` if you add a Postgres addon

4. **Add PostgreSQL (Optional but recommended)**
   - Go to "Resources" tab
   - Search for "Heroku Postgres" in Add-ons
   - Select a plan (Hobby Dev is free)

5. **Deploy**
   - Go to "Deploy" tab
   - Click "Deploy Branch" or wait for automatic deployment

#### Via Heroku CLI:

```bash
# Login to Heroku
heroku login

# Create a new app
heroku create your-app-name

# Set environment variables
heroku config:set DEBUG=False
heroku config:set SECRET_KEY=your-secret-key
heroku config:set ALLOWED_HOSTS=your-app-name.herokuapp.com

# Add PostgreSQL
heroku addons:create heroku-postgresql:hobby-dev

# Push to Heroku
git push heroku main

# Run migrations
heroku run python manage.py migrate

# Create superuser
heroku run python manage.py createsuperuser
```

---

### Deploy to Railway

Railway offers automatic deployment from GitHub with zero configuration.

1. **Sign Up / Login**
   - Go to [Railway.app](https://railway.app/)
   - Sign in with GitHub

2. **Create New Project**
   - Click "New Project"
   - Select "Deploy from GitHub repo"
   - Choose this repository

3. **Configure Environment Variables**
   - Railway auto-detects Django
   - Go to your project → Variables
   - Add environment variables:
     ```
     DEBUG=False
     SECRET_KEY=your-secret-key
     ALLOWED_HOSTS=${{RAILWAY_PUBLIC_DOMAIN}}
     ```

4. **Add PostgreSQL (Optional)**
   - Click "New" → "Database" → "PostgreSQL"
   - Railway automatically sets `DATABASE_URL`

5. **Run Initial Migration**
   - After first deployment, open the project terminal
   - Run: `python manage.py migrate`
   - Run: `python manage.py createsuperuser`

6. **Generate Domain**
   - Go to Settings → Networking
   - Click "Generate Domain"

6. **Deploy**
   - Railway automatically deploys on every push to main branch

---

### Deploy to Render

Render provides free hosting for web apps with automatic deployment.

1. **Sign Up / Login**
   - Go to [Render.com](https://render.com/)
   - Sign in with GitHub

2. **Create Web Service**
   - Click "New +" → "Web Service"
   - Connect this repository
   - Render auto-detects the `render.yaml` configuration

3. **Configure**
   - Name: Choose a name for your service
   - Environment: Python 3
   - Build Command: `pip install -r requirements.txt && python manage.py collectstatic --no-input && python manage.py migrate`
   - Start Command: `gunicorn gold_loan_project.wsgi`

4. **Environment Variables**
   - Add in "Environment" section:
     ```
     DEBUG=False
     SECRET_KEY=your-secret-key
     PYTHON_VERSION=3.12.0
     ```
   - Render provides `RENDER_EXTERNAL_URL` which is automatically added to ALLOWED_HOSTS

5. **Add PostgreSQL (Optional)**
   - Click "New +" → "PostgreSQL"
   - Copy the "Internal Database URL"
   - Add as `DATABASE_URL` environment variable in your web service

6. **Deploy**
   - Click "Create Web Service"
   - Render automatically deploys

---

### Deploy to PythonAnywhere

PythonAnywhere is great for simple Django hosting.

1. **Sign Up**
   - Go to [PythonAnywhere.com](https://www.pythonanywhere.com/)
   - Create a free account

2. **Clone Repository**
   - Open a Bash console
   ```bash
   git clone https://github.com/Gowtham-M-Kumar/Loan_management.git
   cd Loan_management
   ```

3. **Create Virtual Environment**
   ```bash
   mkvirtualenv --python=/usr/bin/python3.10 loan_env
   pip install -r requirements.txt
   ```

4. **Configure Web App**
   - Go to Web tab → "Add a new web app"
   - Choose "Manual configuration" → Python 3.10
   - Set source code directory: `/home/yourusername/Loan_management`
   - Set working directory: `/home/yourusername/Loan_management`

5. **Configure WSGI File**
   - Click on WSGI configuration file link
   - Replace content with:
   ```python
   import os
   import sys
   
   path = '/home/yourusername/Loan_management'
   if path not in sys.path:
       sys.path.append(path)
   
   os.environ['DJANGO_SETTINGS_MODULE'] = 'gold_loan_project.settings'
   
   from django.core.wsgi import get_wsgi_application
   application = get_wsgi_application()
   ```

6. **Environment Variables**
   - In WSGI file, add before imports:
   ```python
   os.environ['DEBUG'] = 'False'
   os.environ['SECRET_KEY'] = 'your-secret-key'
   os.environ['ALLOWED_HOSTS'] = 'yourusername.pythonanywhere.com'
   ```

7. **Static Files**
   - In Web tab, set static files:
     - URL: `/static/`
     - Directory: `/home/yourusername/Loan_management/staticfiles`

8. **Run Migrations**
   ```bash
   cd ~/Loan_management
   python manage.py migrate
   python manage.py collectstatic
   python manage.py createsuperuser
   ```

9. **Reload Web App**
   - Click green "Reload" button in Web tab

---

## GitHub Actions CI/CD

This repository includes a GitHub Actions workflow (`.github/workflows/django.yml`) that automatically:
- Tests the application on Python 3.11 and 3.12
- Runs migrations
- Runs tests
- Checks for security issues with Bandit
- Collects static files

The workflow runs on:
- Every push to `main`, `master`, or `develop` branches
- Every pull request to these branches

To view workflow runs:
1. Go to the "Actions" tab in GitHub
2. Click on "Django CI" workflow
3. View individual run details

---

## Post-Deployment Steps

After deploying to any platform:

### 1. Run Migrations
```bash
python manage.py migrate
```

### 2. Create Superuser
```bash
python manage.py createsuperuser
```

### 3. Collect Static Files
```bash
python manage.py collectstatic --no-input
```

### 4. Test the Deployment
- Visit `https://your-domain.com/health/` - Should return `{"status": "healthy"}`
- Visit `https://your-domain.com/admin/` - Should show Django admin login
- Login with superuser credentials
- Test creating a customer and loan

### 5. Configure Twilio (for OTP)
- Sign up at [Twilio.com](https://www.twilio.com/)
- Get Account SID, Auth Token, and Verify Service SID
- Add to environment variables
- Test OTP functionality

### 6. Security Checklist
- [ ] `DEBUG=False` in production
- [ ] Strong `SECRET_KEY` generated
- [ ] `ALLOWED_HOSTS` properly configured
- [ ] Environment variables stored securely
- [ ] HTTPS enabled (most platforms do this automatically)
- [ ] Database backups configured
- [ ] Media files storage configured (consider AWS S3 for production)

---

## Troubleshooting

### Static Files Not Loading
```bash
python manage.py collectstatic --no-input
```
Ensure `STATIC_ROOT` and `STATICFILES_STORAGE` are configured correctly.

### Database Errors
- Check `DATABASE_URL` environment variable
- Ensure migrations have run: `python manage.py migrate`

### 500 Internal Server Error
- Check application logs (each platform has a logs viewer)
- Ensure all environment variables are set
- Verify `DEBUG=False` and `ALLOWED_HOSTS` includes your domain

### OTP Not Working
- Verify Twilio credentials are correct
- Check Twilio console for SMS delivery status
- Ensure phone number format includes country code (e.g., +91 for India)

---

## Support

For issues or questions:
- Check application logs on your deployment platform
- Review Django deployment documentation: https://docs.djangoproject.com/en/stable/howto/deployment/
- Open an issue on GitHub repository

---

## License

This project is proprietary. All rights reserved.
