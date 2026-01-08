# Deploy to Railway - Quick Start Guide

This guide will help you deploy the Gold Loan Management System to Railway in minutes.

## Prerequisites
- GitHub account
- Railway account (sign up at [railway.app](https://railway.app) with GitHub)

## Deployment Steps

### Step 1: Deploy from GitHub

1. **Go to Railway**
   - Visit [railway.app](https://railway.app)
   - Click "Login" and sign in with GitHub

2. **Create New Project**
   - Click "New Project"
   - Select "Deploy from GitHub repo"
   - Choose `Gowtham-M-Kumar/Loan_management` repository
   - Railway will automatically detect it's a Django project

3. **Wait for Initial Deployment**
   - Railway will automatically build and deploy
   - This may take 2-3 minutes
   - You'll see build logs in real-time

### Step 2: Configure Environment Variables

1. **Add Required Variables**
   - In your Railway project, click on your service
   - Go to "Variables" tab
   - Add these variables:

   ```
   DEBUG=False
   SECRET_KEY=<paste-generated-key-here>
   ALLOWED_HOSTS=${{RAILWAY_PUBLIC_DOMAIN}}
   ```

2. **Generate SECRET_KEY**
   - Run locally or in Railway terminal:
   ```bash
   python -c 'from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())'
   ```
   - Copy the output and paste as SECRET_KEY value

### Step 3: Add PostgreSQL Database (Recommended)

1. **Add Database**
   - In Railway dashboard, click "New"
   - Select "Database" → "PostgreSQL"
   - Railway automatically creates and links it

2. **Verify DATABASE_URL**
   - Go to your service → "Variables"
   - You should see `DATABASE_URL` automatically added
   - This is set by Railway when you add PostgreSQL

### Step 4: Run Migrations

1. **Open Railway Terminal**
   - Go to your service
   - Click on "..." (three dots) → "Terminal"

2. **Run Migration Commands**
   ```bash
   python manage.py migrate
   ```

3. **Create Admin User**
   ```bash
   python manage.py createsuperuser
   ```
   - Enter username, email, and password when prompted

### Step 5: Generate Public Domain

1. **Get Your URL**
   - Go to your service → "Settings" → "Networking"
   - Click "Generate Domain"
   - Your app will be live at: `your-project-name.railway.app`

2. **Update ALLOWED_HOSTS (if needed)**
   - If you generated a domain, it should already work with `${{RAILWAY_PUBLIC_DOMAIN}}`
   - If using a custom domain, add it to ALLOWED_HOSTS variable

### Step 6: Verify Deployment

1. **Test Health Endpoint**
   - Visit: `https://your-app.railway.app/health/`
   - You should see: `{"status": "healthy", "service": "Gold Loan Management System"}`

2. **Access Admin Panel**
   - Visit: `https://your-app.railway.app/admin/`
   - Login with the superuser credentials you created

3. **Test the Application**
   - Navigate through the app
   - Create a test customer
   - Verify all functionality works

## Optional: Add Twilio for OTP

If you want OTP functionality:

1. **Get Twilio Credentials**
   - Sign up at [twilio.com](https://www.twilio.com/)
   - Get your Account SID, Auth Token, and Verify Service SID

2. **Add to Railway Variables**
   ```
   TWILIO_ACCOUNT_SID=your-account-sid
   TWILIO_AUTH_TOKEN=your-auth-token
   TWILIO_VERIFY_SERVICE_SID=your-verify-service-sid
   OTP_ADMIN_MOBILE=+1234567890
   ```

3. **Redeploy**
   - Railway will automatically redeploy when you add variables
   - Or manually trigger: Click "..." → "Redeploy"

## Automatic Deployments

Railway automatically deploys when you push to the main branch:
- Every git push triggers a new deployment
- Old deployments are kept for rollback
- Zero downtime deployments

## View Logs

To troubleshoot issues:
1. Go to your service in Railway
2. Click "Deployments"
3. Click on the latest deployment
4. Click "View Logs"

Or use Railway CLI:
```bash
npm i -g @railway/cli
railway login
railway logs
```

## Cost & Limits

- **Free Tier**: $5 credit per month
- **Usage**: Charged based on resource usage
- **PostgreSQL**: Included in usage calculations
- **Estimates**: Small Django app typically uses $1-3/month

## Troubleshooting

### Build Fails
- Check logs for specific error
- Ensure all dependencies in requirements.txt
- Verify Python version (3.12) is supported

### Static Files Not Loading
```bash
# In Railway terminal
python manage.py collectstatic --no-input
```

### Database Connection Error
- Ensure PostgreSQL addon is added
- Check that DATABASE_URL variable exists
- Verify migrations have run

### 500 Internal Server Error
- Check logs: Service → Deployments → View Logs
- Ensure DEBUG=False
- Verify ALLOWED_HOSTS includes your domain
- Check SECRET_KEY is set

### App Not Accessible
- Ensure domain is generated: Settings → Networking
- Check that service is running (green status)
- Verify ALLOWED_HOSTS includes `${{RAILWAY_PUBLIC_DOMAIN}}`

## Support

- **Railway Docs**: [docs.railway.app](https://docs.railway.app)
- **Repository Issues**: Open an issue on GitHub
- **Deployment Guide**: See `DEPLOYMENT.md` for more details
- **Security**: See `SECURITY.md` for production best practices

## Next Steps

After successful deployment:
1. ✅ Review `SECURITY.md` for production hardening
2. ✅ Set up regular database backups
3. ✅ Configure custom domain (optional)
4. ✅ Set up monitoring/alerts
5. ✅ Test all functionality thoroughly

---

**Ready to Deploy?** Click the "Deploy on Railway" button in the README.md!
