# Quick Deployment Reference

## Environment Variables Required for All Platforms

```env
DEBUG=False
SECRET_KEY=your-production-secret-key-here
ALLOWED_HOSTS=your-domain.com
```

## Optional Environment Variables

```env
# Database (PostgreSQL recommended for production)
DATABASE_URL=postgresql://user:password@host:5432/database

# Twilio OTP (Required for OTP functionality)
TWILIO_ACCOUNT_SID=ACxxxxxxxxxxxxx
TWILIO_AUTH_TOKEN=your-auth-token
TWILIO_VERIFY_SERVICE_SID=VAxxxxxxxxxxxxx
OTP_ADMIN_MOBILE=+1234567890
```

---

## Platform Comparison

| Platform | Free Tier | Database | Auto Deploy | Best For |
|----------|-----------|----------|-------------|----------|
| **Railway** | ✅ $5/month credit | PostgreSQL included | ✅ Yes | Beginners |
| **Render** | ✅ Yes | PostgreSQL included | ✅ Yes | Free hosting |
| **Heroku** | ❌ Paid only | Add-on required | ✅ Yes | Enterprise |
| **PythonAnywhere** | ✅ Yes | MySQL/SQLite | ❌ Manual | Simple apps |

---

## Quick Commands

### Generate Secret Key
```bash
python -c 'from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())'
```

### Test Locally Before Deploy
```bash
# Set environment variables
export DEBUG=False
export SECRET_KEY=test-key
export ALLOWED_HOSTS=localhost,127.0.0.1

# Run checks
python manage.py check --deploy
python manage.py migrate
python manage.py collectstatic --no-input
python manage.py test

# Test with gunicorn
gunicorn gold_loan_project.wsgi
```

### Verify Health Endpoint
```bash
curl http://localhost:8000/health/
# Should return: {"status": "healthy", "service": "Gold Loan Management System"}
```

---

## Troubleshooting Quick Fixes

### Static Files Not Loading
```bash
python manage.py collectstatic --no-input
```
Ensure `STATIC_ROOT` is set in settings and WhiteNoise is in MIDDLEWARE.

### Database Connection Issues
- Check `DATABASE_URL` is properly formatted
- For SQLite: ensure the file path is writable
- For PostgreSQL: verify connection string and credentials

### Import Errors
```bash
pip install -r requirements.txt
```

### 500 Errors in Production
- Set `DEBUG=False`
- Add your domain to `ALLOWED_HOSTS`
- Check platform logs for details

---

## Post-Deployment Checklist

- [ ] Run migrations: `python manage.py migrate`
- [ ] Create superuser: `python manage.py createsuperuser`
- [ ] Collect static files: `python manage.py collectstatic`
- [ ] Test health endpoint: `/health/`
- [ ] Test admin panel: `/admin/`
- [ ] Configure Twilio for OTP functionality
- [ ] Set up proper database (PostgreSQL recommended)
- [ ] Enable HTTPS (usually automatic on platforms)
- [ ] Configure domain name (optional)
- [ ] Set up database backups
- [ ] Monitor application logs

---

## Links

- **Full Deployment Guide**: See [DEPLOYMENT.md](DEPLOYMENT.md)
- **Environment Setup**: See [.env.example](.env.example)
- **CI/CD Workflow**: See [.github/workflows/django.yml](.github/workflows/django.yml)
