import os
import sys
from pathlib import Path
from decouple import config
from django.contrib.messages import constants as messages

# -----------------------
# BASE DIRECTORY
# -----------------------
BASE_DIR = Path(__file__).resolve().parent.parent

# -----------------------
# SECURITY
# -----------------------
SECRET_KEY = config("SECRET_KEY")

DEBUG = config("DEBUG", cast=bool, default=False)

# ALLOWED_HOSTS = [
#     host for host in config("ALLOWED_HOSTS", default="").split(",") if host
# ]

ALLOWED_HOSTS = ['*']  # temporary for Render

# Toggle for production security (HTTPS, cookies, etc.)
SECURE_MODE = config("SECURE_MODE", cast=bool, default=False)

# -----------------------
# APPLICATIONS
# -----------------------
INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "django.contrib.humanize",

    "bursary.apps.BursaryConfig",

    "widget_tweaks",
    "import_export",
]

# -----------------------
# MIDDLEWARE
# -----------------------
MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "whitenoise.middleware.WhiteNoiseMiddleware",

    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",

    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",

    "bursary.middleware.TenantMiddleware",

    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

# -----------------------
# URLS & WSGI
# -----------------------
ROOT_URLCONF = "bursary_management_system.urls"
WSGI_APPLICATION = "bursary_management_system.wsgi.application"

# -----------------------
# TEMPLATES
# -----------------------
TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [BASE_DIR / "bursary" / "templates"],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",

                "bursary.context_processors.site_branding",
                "bursary.context_processors.officer_context",
                "bursary.context_processors.unresolved_support_count",
                "bursary.context_processors.student_support_feedback_count",
            ],
        },
    },
]

# -----------------------
# DATABASE (MySQL)
# -----------------------
# DATABASES = {
#     "default": {
#         "ENGINE": "django.db.backends.mysql",
#         "NAME": config("DB_NAME"),
#         "USER": config("DB_USER"),
#         "PASSWORD": config("DB_PASSWORD"),
#         "HOST": config("DB_HOST", default="localhost"),
#         "PORT": config("DB_PORT", cast=int, default=3306),
#         "OPTIONS": {
#             "init_command": "SET sql_mode='STRICT_TRANS_TABLES'"
#         },
#     }
# }


# -----------------------
# DATABASE (SQLite)
# -----------------------

import dj_database_url

DATABASE_URL = config("DATABASE_URL", default=None)

if DATABASE_URL:
    DATABASES = {
        "default": dj_database_url.parse(DATABASE_URL)
    }
else:
    DATABASES = {
        "default": {
            "ENGINE": "django.db.backends.sqlite3",
            "NAME": BASE_DIR / "db.sqlite3",
        }
    }

# -----------------------
# REDIS (OPTIONAL CACHE)
# -----------------------
REDIS_URL = config("REDIS_URL", default=None)

if REDIS_URL:
    CACHES = {
        "default": {
            "BACKEND": "django_redis.cache.RedisCache",
            "LOCATION": REDIS_URL,
            "OPTIONS": {
                "CLIENT_CLASS": "django_redis.client.DefaultClient",
            },
        }
    }
    SESSION_ENGINE = "django.contrib.sessions.backends.cache"
    SESSION_CACHE_ALIAS = "default"
else:
    CACHES = {
        "default": {
            "BACKEND": "django.core.cache.backends.locmem.LocMemCache",
        }
    }
    SESSION_ENGINE = "django.contrib.sessions.backends.db"

# -----------------------
# AUTHENTICATION
# -----------------------
AUTHENTICATION_BACKENDS = [
    "bursary.auth_backends.StudentIDorNEMISBackend",
    "django.contrib.auth.backends.ModelBackend",
]

AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator"},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]

# -----------------------
# INTERNATIONALIZATION
# -----------------------
LANGUAGE_CODE = "en-us"
TIME_ZONE = "Africa/Nairobi"
USE_I18N = True
USE_TZ = True

# -----------------------
# STATIC FILES
# -----------------------
STATIC_URL = "/static/"
STATICFILES_DIRS = [os.path.join(BASE_DIR, "static")]
STATIC_ROOT = os.path.join(BASE_DIR, "staticfiles")

STATICFILES_STORAGE = "whitenoise.storage.CompressedManifestStaticFilesStorage"

# -----------------------
# MEDIA FILES (LOCAL STORAGE)
# -----------------------
MEDIA_URL = "/media/"
MEDIA_ROOT = os.path.join(BASE_DIR, "media")

# -----------------------
# EMAIL (OPTIONAL)
# -----------------------
EMAIL_BACKEND = "django.core.mail.backends.smtp.EmailBackend"
EMAIL_HOST = "smtp.gmail.com"
EMAIL_PORT = 587
EMAIL_USE_TLS = True
EMAIL_HOST_USER = config("EMAIL_HOST_USER", default="")
EMAIL_HOST_PASSWORD = config("EMAIL_HOST_PASSWORD", default="")
DEFAULT_FROM_EMAIL = EMAIL_HOST_USER

# -----------------------
# SMS (OPTIONAL)
# -----------------------
AT_USERNAME = config("AT_USERNAME", default="")
AT_API_KEY = config("AT_API_KEY", default="")

# -----------------------
# SECURITY SETTINGS
# -----------------------
CSRF_COOKIE_SECURE = SECURE_MODE
SESSION_COOKIE_SECURE = SECURE_MODE
SECURE_SSL_REDIRECT = SECURE_MODE

SECURE_HSTS_SECONDS = 31536000 if SECURE_MODE else 0
SECURE_HSTS_INCLUDE_SUBDOMAINS = SECURE_MODE
SECURE_HSTS_PRELOAD = SECURE_MODE

SECURE_BROWSER_XSS_FILTER = True
SECURE_CONTENT_TYPE_NOSNIFF = True

# -----------------------
# LOGIN REDIRECTS
# -----------------------
LOGIN_URL = "/officer/login/"
LOGIN_REDIRECT_URL = "/officer/dashboard/"
LOGOUT_REDIRECT_URL = "/"

# -----------------------
# MESSAGES (BOOTSTRAP)
# -----------------------
MESSAGE_TAGS = {
    messages.DEBUG: "secondary",
    messages.INFO: "info",
    messages.SUCCESS: "success",
    messages.WARNING: "warning",
    messages.ERROR: "danger",
}

# -----------------------
# LOGGING
# -----------------------
LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "handlers": {
        "console": {
            "class": "logging.StreamHandler",
            "stream": sys.stdout,
        },
    },
    "root": {
        "handlers": ["console"],
        "level": "INFO",
    },
}

# -----------------------
# DEFAULT PRIMARY KEY
# -----------------------
DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"


