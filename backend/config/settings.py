# File: config/settings.py
from pathlib import Path
import os
from datetime import timedelta
from dotenv import load_dotenv
import dj_database_url

BASE_DIR = Path(__file__).resolve().parent.parent
load_dotenv(BASE_DIR / ".env")
# ---------------------------------------------------------------------------
# Core
# ---------------------------------------------------------------------------
SECRET_KEY = os.getenv("DJANGO_SECRET_KEY", "dev-secret-key-do-not-use-in-prod")
DEBUG = os.getenv("DEBUG", "True").lower() == "true"
ALLOWED_HOSTS = [h for h in os.getenv("ALLOWED_HOSTS", "*").split(",") if h]
# App 相關設定
LOAN_DAYS_DEFAULT = int(os.getenv("LOAN_DAYS_DEFAULT", 14)) # 預設借期 14 天
LOAN_MAX_RENEWALS = int(os.getenv("LOAN_MAX_RENEWALS", 1)) # 每筆最多續借 1 次
LOAN_RENEW_DAYS = int(os.getenv("LOAN_RENEW_DAYS", 14)) # 每次續借延長 14 天
# CSRF / CORS（前後端分離：預設允許 Vite/localhost:5173）
# 若上線請改成你的網域
CSRF_TRUSTED_ORIGINS = [
    *(o for o in os.getenv("CSRF_TRUSTED_ORIGINS", "http://localhost:5173").split(",") if o),
]

INSTALLED_APPS = [
    # Django core
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "django_extensions", # 額外好用指令
    
    # 第三方
    "rest_framework",
    "rest_framework.authtoken",
    "rest_framework_simplejwt",
    "rest_framework_simplejwt.token_blacklist",
    "django_filters",
    "corsheaders",
    "import_export",

    # 本專案應用（依你的專案目錄）
    "auth_app",
    "users",
    "books",
    "loans",
    "favorites",
    "notifications",
    "chat",
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "whitenoise.middleware.WhiteNoiseMiddleware",  
    "django.contrib.sessions.middleware.SessionMiddleware",
    "corsheaders.middleware.CorsMiddleware",
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
                "django.template.context_processors.debug",
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ],
        },
    }
]

WSGI_APPLICATION = "config.wsgi.application"
ASGI_APPLICATION = "config.asgi.application"

# ---------------------------------------------------------------------------
# Database（PostgreSQL）
# ---------------------------------------------------------------------------
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///db.sqlite3")
DATABASES = {
    "default": dj_database_url.parse(DATABASE_URL, conn_max_age=600),
}

# 自訂使用者模型（建議 users/models.py 定義 User）
AUTH_USER_MODEL = "users.User"

# ---------------------------------------------------------------------------
# Auth / Security
# ---------------------------------------------------------------------------
# 優先使用 Argon2 密碼雜湊
PASSWORD_HASHERS = [
    "django.contrib.auth.hashers.Argon2PasswordHasher",
    "django.contrib.auth.hashers.PBKDF2PasswordHasher",
    "django.contrib.auth.hashers.PBKDF2SHA1PasswordHasher",
    "django.contrib.auth.hashers.BCryptSHA256PasswordHasher",
]

# Django REST framework & JWT
REST_FRAMEWORK = {
    "DEFAULT_AUTHENTICATION_CLASSES": [
        "rest_framework_simplejwt.authentication.JWTAuthentication",
    ],
    "DEFAULT_PERMISSION_CLASSES": [
        "rest_framework.permissions.AllowAny",
    ],
    "DEFAULT_FILTER_BACKENDS": [
        "django_filters.rest_framework.DjangoFilterBackend",
        "rest_framework.filters.SearchFilter",
        "rest_framework.filters.OrderingFilter",
    ],
    "DEFAULT_PAGINATION_CLASS": "rest_framework.pagination.PageNumberPagination",
    "PAGE_SIZE": int(os.getenv("API_PAGE_SIZE", 20)),
}

SIMPLE_JWT = {
    "ACCESS_TOKEN_LIFETIME": timedelta(
        minutes=int(os.getenv("JWT_ACCESS_MIN", 60))
    ),  # 預設 60 分鐘
    "REFRESH_TOKEN_LIFETIME": timedelta(
        days=int(os.getenv("JWT_REFRESH_DAYS", 7))
    ),  # 預設 7 天
    "AUTH_HEADER_TYPES": ("Bearer",),
    "AUTH_TOKEN_CLASSES": ("rest_framework_simplejwt.tokens.AccessToken",),
    "ROTATE_REFRESH_TOKENS": True,  # 每次刷新發新 refresh token
    "BLACKLIST_AFTER_ROTATION": True,  # 搭配黑名單 app 時可啟用登出
}

# CORS 設定（視需求更改）
CORS_ALLOW_CREDENTIALS = True
CORS_ALLOWED_ORIGINS = [
    *(o for o in os.getenv("CORS_ALLOWED_ORIGINS", "http://localhost:5173").split(",") if o),
]

# ---------------------------------------------------------------------------
# I18N / TZ
# ---------------------------------------------------------------------------
LANGUAGE_CODE = "zh-hant"
TIME_ZONE = "Asia/Taipei"
USE_I18N = True
USE_TZ = True

# ---------------------------------------------------------------------------
# Static / Media
# ---------------------------------------------------------------------------

STATIC_URL = "/static/"
STATIC_ROOT = BASE_DIR / "staticfiles"
STATICFILES_DIRS = [BASE_DIR / "static"] if (BASE_DIR / "static").exists() else []
STATICFILES_STORAGE = "whitenoise.storage.CompressedManifestStaticFilesStorage"

MEDIA_URL = "/media/"
MEDIA_ROOT = BASE_DIR / "media"

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

# ---------------------------------------------------------------------------
# Logging（方便除錯與上線監控）
# ---------------------------------------------------------------------------
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")
LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {
        "verbose": {
            "format": "[%(asctime)s] %(levelname)s %(name)s:%(lineno)d — %(message)s",
        },
        "simple": {"format": "%(levelname)s: %(message)s"},
    },
    "handlers": {
        "console": {
            "class": "logging.StreamHandler",
            "formatter": "verbose",
            "level": LOG_LEVEL,
        }
    },
    "root": {"handlers": ["console"], "level": LOG_LEVEL},
    "loggers": {
        "django.request": {
            "handlers": ["console"],
            "level": "ERROR",
            "propagate": False,
        },
    },
}

# 若 DEBUG 為 False，建議加強安全設定（可按需擴充）
if not DEBUG:
    SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")
    SESSION_COOKIE_SECURE = True
    CSRF_COOKIE_SECURE = True
    SECURE_HSTS_SECONDS = int(os.getenv("SECURE_HSTS_SECONDS", 0))
    SECURE_HSTS_INCLUDE_SUBDOMAINS = bool(int(os.getenv("SECURE_HSTS_INCLUDE_SUBDOMAINS", 0)))
    SECURE_HSTS_PRELOAD = bool(int(os.getenv("SECURE_HSTS_PRELOAD", 0)))
