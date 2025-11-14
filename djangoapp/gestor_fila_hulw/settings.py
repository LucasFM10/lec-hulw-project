import os
from pathlib import Path

# BASE_DIR aponta para a raiz do seu projeto (onde está manage.py)
BASE_DIR = Path(__file__).resolve().parent.parent

# ---------- Basic env-driven settings ----------
SECRET_KEY = os.getenv("SECRET_KEY", "mude_essa_chave_em_producao")
DEBUG = os.getenv("DEBUG", "0") in ("1", "true", "True")

# ALLOWED_HOSTS via env, separado por vírgula
ALLOWED_HOSTS = [
    h.strip() for h in os.getenv("ALLOWED_HOSTS", "localhost,127.0.0.1").split(",") if h.strip()
]

# Base URL da API de fila cirúrgica (usada em fila_cirurgica/api_helpers.py)
# Em Docker, o serviço da API expõe a porta 8000; o Django fala com ela via rede do compose.
API_BASE_URL = os.getenv("API_BASE_URL", "http://fila_api:8000")

# ---------- Installed apps (adapte listagem de apps do seu projeto) ----------
INSTALLED_APPS = [
    # Django default apps
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    
    'unfold',
    'unfold.contrib.forms',
    'unfold.contrib.filters',
    'unfold.contrib.simple_history',

    # Your apps:
    "aih",
    "anexos_judiciais",
    "externo",
    "fila_cirurgica",
    "gestor_fila_hulw",
    "lec_legado",
    "portal",
]

# ---------- Middleware (WhiteNoise logo após SecurityMiddleware) ----------
MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    # WhiteNoise para servir staticfiles em produção
    "whitenoise.middleware.WhiteNoiseMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

ROOT_URLCONF = "gestor_fila_hulw.urls" 

# ---------- Templates ----------
TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [BASE_DIR / "templates"],  # mantenha templates na raiz/templates
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

WSGI_APPLICATION = "gestor_fila_hulw.wsgi.application"

# ---------- Database: Postgres via env, fallback para sqlite (dev) ----------
if os.getenv("POSTGRES_HOST"):
    DATABASES = {
        "default": {
            "ENGINE": os.getenv("DB_ENGINE", "django.db.backends.postgresql"),
            "NAME": os.getenv("POSTGRES_DB", "postgres"),
            "USER": os.getenv("POSTGRES_USER", "postgres"),
            "PASSWORD": os.getenv("POSTGRES_PASSWORD", ""),
            "HOST": os.getenv("POSTGRES_HOST", "db"),
            "PORT": os.getenv("POSTGRES_PORT", "5432"),
        }
    }
else:
    # fallback rápido para desenvolvimento local (se quiser usar sqlite)
    DATABASES = {
        "default": {
            "ENGINE": "django.db.backends.sqlite3",
            "NAME": str(BASE_DIR / "db.sqlite3"),
        }
    }

# ---------- Password validation (padrão Django) ----------
AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator"},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]

# ---------- Internationalization ----------
LANGUAGE_CODE = "pt-br"
TIME_ZONE = os.getenv("TIME_ZONE", "America/Recife")
USE_I18N = True
USE_L10N = True
USE_TZ = True
LOCALE_PATHS = [BASE_DIR / "locale"]

# ---------- Static & Media (configuradas para Docker + WhiteNoise) ----------
STATIC_URL = "/static/"
# Diretório onde collectstatic colocará os arquivos (fora do código)
STATIC_ROOT = Path("/data/web/static")

# Armazenamento otimizado para produção com WhiteNoise
STATICFILES_STORAGE = "whitenoise.storage.CompressedManifestStaticFilesStorage"

# Media uploads
MEDIA_URL = "/media/"
MEDIA_ROOT = Path("/data/web/media")

# ---------- Security (togglable via env) ----------
SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")
SESSION_COOKIE_SECURE = os.getenv("SESSION_COOKIE_SECURE", "0") in ("1", "true", "True")
CSRF_COOKIE_SECURE = os.getenv("CSRF_COOKIE_SECURE", "0") in ("1", "true", "True")
SECURE_SSL_REDIRECT = os.getenv("SECURE_SSL_REDIRECT", "0") in ("1", "true", "True")

# ---------- Logging para docker (stdout) ----------
LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "handlers": {"console": {"class": "logging.StreamHandler"}},
    "root": {"handlers": ["console"], "level": os.getenv("DJANGO_LOG_LEVEL", "INFO")},
}

# ---------- Email (exemplo básico via env; ajuste conforme necessário) ----------
EMAIL_BACKEND = os.getenv("EMAIL_BACKEND", "django.core.mail.backends.smtp.EmailBackend")
EMAIL_HOST = os.getenv("EMAIL_HOST", "smtp.gmail.com")
EMAIL_PORT = int(os.getenv("EMAIL_PORT", "587"))
EMAIL_HOST_USER = os.getenv("EMAIL_HOST_USER", "")
EMAIL_HOST_PASSWORD = os.getenv("EMAIL_HOST_PASSWORD", "")
EMAIL_USE_TLS = os.getenv("EMAIL_USE_TLS", "1") in ("1", "true", "True")
DEFAULT_FROM_EMAIL = os.getenv("DEFAULT_FROM_EMAIL", EMAIL_HOST_USER)

# ---------- Outros ajustes úteis ----------
# tempo de sessão (opcional)
SESSION_COOKIE_AGE = int(os.getenv("SESSION_COOKIE_AGE", 1209600))  # 2 semanas por padrão

# se você tiver apps que exigem configurações extras, adicione aqui
# EX: TAILWIND_APP_NAME = os.getenv("TAILWIND_APP_NAME", "theme")

# ---------- Fim do arquivo ----------
