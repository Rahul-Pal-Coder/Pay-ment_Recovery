import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent

env_path = BASE_DIR / ".env"
if env_path.exists():
    for raw_line in env_path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        os.environ.setdefault(key.strip(), value.strip().strip('"').strip("'"))

SECRET_KEY = os.getenv(
    "DJANGO_SECRET_KEY",
    "django-insecure-9e3o(lh23onj7#j=4@#luarr9qagby0ml=cb%b^+b(^b0^&l^s",
)
DEBUG = os.getenv("DJANGO_DEBUG", "True").lower() == "true"
ALLOWED_HOSTS = [host.strip() for host in os.getenv("DJANGO_ALLOWED_HOSTS", "*").split(",") if host.strip()]

INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "notifications",
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

ROOT_URLCONF = "config.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [BASE_DIR / "templates"],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ],
        },
    },
]

WSGI_APPLICATION = "config.wsgi.application"

# DATABASES = {
#     "default": {
#         "ENGINE": "django.db.backends.sqlite3",
#         "NAME": BASE_DIR / "db.sqlite3",
#     }
# }

DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.mysql",
        "NAME": "datadb",
        "USER": "root",
        "PASSWORD": "mahima123@",
        "HOST": "localhost",
        "PORT": "3306",
    }
}

AUTH_PASSWORD_VALIDATORS = [
    {
        "NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator",
    },
    {
        "NAME": "django.contrib.auth.password_validation.MinimumLengthValidator",
    },
    {
        "NAME": "django.contrib.auth.password_validation.CommonPasswordValidator",
    },
    {
        "NAME": "django.contrib.auth.password_validation.NumericPasswordValidator",
    },
]

LANGUAGE_CODE = "en-in"
TIME_ZONE = "Asia/Kolkata"
USE_I18N = True
USE_TZ = True

STATIC_URL = "static/"
STATICFILES_DIRS = [BASE_DIR / "static"]
STATIC_ROOT = BASE_DIR / "staticfiles"

EMAIL_BACKEND = "django.core.mail.backends.smtp.EmailBackend"
EMAIL_HOST = os.getenv("EMAIL_HOST", "smtp.gmail.com")
EMAIL_PORT = int(os.getenv("EMAIL_PORT", "587"))
EMAIL_HOST_USER = os.getenv("EMAIL_HOST_USER", "")
EMAIL_HOST_PASSWORD = os.getenv("EMAIL_HOST_PASSWORD", "").replace(" ", "")
EMAIL_USE_TLS = os.getenv("EMAIL_USE_TLS", "True").lower() == "true"
DEFAULT_FROM_EMAIL = os.getenv("DEFAULT_FROM_EMAIL", EMAIL_HOST_USER or "noreply@example.com")

TWILIO_ACCOUNT_SID = os.getenv("TWILIO_ACCOUNT_SID", "")
TWILIO_AUTH_TOKEN = os.getenv("TWILIO_AUTH_TOKEN", "")
TWILIO_WHATSAPP_FROM = os.getenv("TWILIO_WHATSAPP_FROM", "whatsapp:+14155238886")

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"


# Celery settings
from urllib.parse import quote_plus
_db_default = DATABASES['default']
_db_user = quote_plus(_db_default.get('USER', ''))
_db_pass = quote_plus(_db_default.get('PASSWORD', ''))
_db_host = _db_default.get('HOST', 'localhost')
_db_port = _db_default.get('PORT', '3306')
_db_name = _db_default.get('NAME', '')

CELERY_BROKER_URL = f'sqla+mysql://{_db_user}:{_db_pass}@{_db_host}:{_db_port}/{_db_name}'
CELERY_RESULT_BACKEND = f'db+mysql://{_db_user}:{_db_pass}@{_db_host}:{_db_port}/{_db_name}'
CELERY_ACCEPT_CONTENT = ['json']
CELERY_TASK_SERIALIZER = 'json'
CELERY_RESULT_SERIALIZER = 'json'
CELERY_TIMEZONE = 'Asia/Kolkata'
CELERY_TASK_ALWAYS_EAGER = False

# Add at the bottom of settings.py
LOGIN_URL = 'notifications:login'
LOGIN_REDIRECT_URL = 'notifications:dashboard'
LOGOUT_REDIRECT_URL = 'notifications:login'



# ============================================
# MAHIMA LIFE SCIENCES - Configuration
# ============================================
MAHIMA_EMAIL_HOST = os.getenv("MAHIMA_EMAIL_HOST", "smtp.gmail.com")
MAHIMA_EMAIL_PORT = int(os.getenv("MAHIMA_EMAIL_PORT", "587"))
MAHIMA_EMAIL_HOST_USER = os.getenv("MAHIMA_EMAIL_HOST_USER", "")
MAHIMA_EMAIL_HOST_PASSWORD = os.getenv("MAHIMA_EMAIL_HOST_PASSWORD", "").replace(" ", "")
MAHIMA_EMAIL_USE_TLS = os.getenv("MAHIMA_EMAIL_USE_TLS", "True").lower() == "true"
MAHIMA_DEFAULT_FROM_EMAIL = os.getenv("MAHIMA_DEFAULT_FROM_EMAIL", "Mahima Life Sciences <Info@mahimalife.com>")

MAHIMA_TWILIO_ACCOUNT_SID = os.getenv("MAHIMA_TWILIO_ACCOUNT_SID", "")
MAHIMA_TWILIO_AUTH_TOKEN = os.getenv("MAHIMA_TWILIO_AUTH_TOKEN", "")
MAHIMA_TWILIO_WHATSAPP_FROM = os.getenv("MAHIMA_TWILIO_WHATSAPP_FROM", "whatsapp:+9310406109")

# ============================================
# VINCIT LABS - Configuration
# ============================================
VINCIT_EMAIL_HOST = os.getenv("VINCIT_EMAIL_HOST", "smtp.gmail.com")
VINCIT_EMAIL_PORT = int(os.getenv("VINCIT_EMAIL_PORT", "587"))
VINCIT_EMAIL_HOST_USER = os.getenv("VINCIT_EMAIL_HOST_USER", "")
VINCIT_EMAIL_HOST_PASSWORD = os.getenv("VINCIT_EMAIL_HOST_PASSWORD", "").replace(" ", "")
VINCIT_EMAIL_USE_TLS = os.getenv("VINCIT_EMAIL_USE_TLS", "True").lower() == "true"
VINCIT_DEFAULT_FROM_EMAIL = os.getenv("VINCIT_DEFAULT_FROM_EMAIL", "Vincit Labs <sales@vincitlabs.com>")

VINCIT_TWILIO_ACCOUNT_SID = os.getenv("VINCIT_TWILIO_ACCOUNT_SID", "")
VINCIT_TWILIO_AUTH_TOKEN = os.getenv("VINCIT_TWILIO_AUTH_TOKEN", "")
VINCIT_TWILIO_WHATSAPP_FROM = os.getenv("VINCIT_TWILIO_WHATSAPP_FROM", "whatsapp:+14155238887")