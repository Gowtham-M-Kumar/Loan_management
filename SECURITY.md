# Security Configuration for Production

When deploying to production, add these security settings to your environment variables or update your deployment platform configuration.

## Required Security Settings

### 1. Basic Security (Required)

```env
DEBUG=False
SECRET_KEY=your-long-random-secret-key-at-least-50-characters-long
ALLOWED_HOSTS=your-domain.com,www.your-domain.com
```

### 2. HTTPS/SSL Configuration (Highly Recommended)

Most deployment platforms (Heroku, Railway, Render) automatically provide HTTPS. Add these settings for enhanced security:

```python
# Add to settings.py or set via environment variables:

# HTTPS/SSL Settings
SECURE_SSL_REDIRECT = True  # Redirect HTTP to HTTPS
SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')

# HSTS (HTTP Strict Transport Security)
SECURE_HSTS_SECONDS = 31536000  # 1 year
SECURE_HSTS_INCLUDE_SUBDOMAINS = True
SECURE_HSTS_PRELOAD = True

# Cookie Security
SESSION_COOKIE_SECURE = True
CSRF_COOKIE_SECURE = True
CSRF_COOKIE_HTTPONLY = True
SESSION_COOKIE_HTTPONLY = True
```

### 3. Content Security

```python
# X-Frame-Options (already enabled by default in Django)
X_FRAME_OPTIONS = 'DENY'

# Content Security Policy (optional, but recommended)
SECURE_CONTENT_TYPE_NOSNIFF = True
SECURE_BROWSER_XSS_FILTER = True
```

## Platform-Specific Configuration

### Heroku / Railway / Render

These platforms handle HTTPS automatically. You only need to set:

```env
DEBUG=False
SECRET_KEY=<generate-strong-key>
ALLOWED_HOSTS=<your-app>.herokuapp.com  # or railway.app, or render.com
```

### PythonAnywhere

Add to your WSGI file or settings:

```python
SECURE_SSL_REDIRECT = True
SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')
```

## Generating a Strong SECRET_KEY

Use this command to generate a secure secret key:

```bash
python -c 'from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())'
```

Example output:
```
django-insecure-#x2$8p3&m9@f0z!%y6h4n&^l*e1q#d5k+j7w$r9t@v8u%b3
```

**Important:** 
- Never commit SECRET_KEY to version control
- Use a different key for each environment (dev, staging, production)
- Store it securely in your deployment platform's environment variables

## Additional Security Measures

### 1. Database Security

If using PostgreSQL (recommended):

```env
DATABASE_URL=postgresql://username:password@host:5432/database?sslmode=require
```

### 2. Admin Panel Protection

Change the admin URL from `/admin/` to something less obvious:

```python
# In gold_loan_project/urls.py
urlpatterns = [
    path("secret-admin-panel/", admin.site.urls),  # Change from "admin/"
    # ...
]
```

### 3. Rate Limiting

Consider adding rate limiting for production:

```bash
pip install django-ratelimit
```

### 4. Dependency Security

Regularly update dependencies:

```bash
pip list --outdated
pip install --upgrade <package-name>
```

### 5. Enable Django's Security Middleware

Already included in this project:
- `SecurityMiddleware` - Various security enhancements
- `CsrfViewMiddleware` - CSRF protection
- `ClickjackingMiddleware` - Clickjacking protection

## Security Checklist for Production

- [ ] `DEBUG=False` in production
- [ ] Strong `SECRET_KEY` (50+ random characters)
- [ ] `ALLOWED_HOSTS` properly configured with your domain
- [ ] HTTPS enabled (automatic on most platforms)
- [ ] `SECURE_SSL_REDIRECT=True` if using HTTPS
- [ ] Secure cookie settings enabled
- [ ] Database credentials stored securely
- [ ] Admin URL changed from default `/admin/`
- [ ] All dependencies up to date
- [ ] Regular backups configured
- [ ] Error monitoring set up (e.g., Sentry)
- [ ] Twilio credentials stored as environment variables
- [ ] Media files storage configured securely
- [ ] CORS settings configured if using APIs

## Monitoring and Logging

### Set up Error Monitoring (Optional)

Consider using [Sentry](https://sentry.io/) for error tracking:

```bash
pip install sentry-sdk
```

Add to settings.py:

```python
import sentry_sdk

if not DEBUG:
    sentry_sdk.init(
        dsn=os.getenv('SENTRY_DSN'),
        traces_sample_rate=1.0,
    )
```

### Check Logs Regularly

- **Heroku**: `heroku logs --tail`
- **Railway**: View in Railway dashboard
- **Render**: View in Render dashboard
- **PythonAnywhere**: Check error log in Web tab

## Running Security Checks

Before deploying, run:

```bash
# Django deployment checks
python manage.py check --deploy

# Security scanning with Bandit
pip install bandit
bandit -r gold_loan gold_loan_project

# Check for known vulnerabilities
pip install safety
safety check
```

## Need Help?

- Django Security Documentation: https://docs.djangoproject.com/en/stable/topics/security/
- OWASP Top 10: https://owasp.org/www-project-top-ten/
- Django Deployment Checklist: https://docs.djangoproject.com/en/stable/howto/deployment/checklist/

---

**Remember**: Security is an ongoing process, not a one-time setup. Regularly review and update your security configuration.
