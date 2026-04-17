import os
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

BASE_DIR = Path(__file__).resolve().parent.parent

SECRET_KEY = os.getenv('DJANGO_SECRET_KEY', 'django-insecure-fallback-key')
DEBUG = os.getenv('DEBUG', 'False').lower() in ('true', '1', 'yes')
ALLOWED_HOSTS = ['*']

INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    # Third-party
    'rest_framework',
    'corsheaders',
    # Project apps
    'administration',
    'chatbot',
    'ingestion',
    'analytics',
    'dashboard',
]

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'corsheaders.middleware.CorsMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'marinemind.middleware.LoginRequiredMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

ROOT_URLCONF = 'marinemind.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [BASE_DIR / 'templates'],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
            ],
        },
    },
]

WSGI_APPLICATION = 'marinemind.wsgi.application'

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': BASE_DIR / 'db.sqlite3',
    }
}

AUTH_PASSWORD_VALIDATORS = [
    {'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator'},
    {'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator'},
    {'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator'},
    {'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator'},
]

LANGUAGE_CODE = 'en-us'
TIME_ZONE = 'UTC'
USE_I18N = True
USE_TZ = True

STATIC_URL = '/static/'
STATICFILES_DIRS = [BASE_DIR / 'static']
STATIC_ROOT = BASE_DIR / 'staticfiles'

MEDIA_URL = '/media/'
MEDIA_ROOT = BASE_DIR / 'media'

# Allow same-origin iframes (for PDF viewer modal)
X_FRAME_OPTIONS = 'SAMEORIGIN'

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

# Authentication
# Authentication
LOGIN_URL = '/login/'
LOGIN_REDIRECT_URL = '/'
LOGOUT_REDIRECT_URL = '/login/'

AUTHENTICATION_BACKENDS = [
    'chatbot.backends.EmailBackend',
]

# --- AI / RAG Configuration ---
PINECONE_API_KEY = os.getenv('PINECONE_API_KEY', '')
TAVILY_API_KEY = os.getenv('TAVILY_API_KEY', '')
HUGGINGFACE_API_TOKEN = os.getenv('HUGGINGFACE_API_TOKEN', '')
HUGGINGFACE_API_URL = os.getenv('HUGGINGFACE_API_URL', '')
HUGGINGFACE_MODEL = os.getenv('HUGGINGFACE_MODEL', 'meta-llama/Llama-3.1-8B-Instruct')

PINECONE_INDEX_NAME = 'marinemind-vectors'
PINECONE_DIMENSION = 384  # all-MiniLM-L6-v2 embedding dimension
EMBEDDING_MODEL_NAME = 'all-MiniLM-L6-v2'
RERANKER_MODEL_NAME = 'cross-encoder/ms-marco-MiniLM-L-6-v2'

# Upload settings
FILE_UPLOAD_MAX_MEMORY_SIZE = 50 * 1024 * 1024  # 50 MB
DATA_UPLOAD_MAX_MEMORY_SIZE = 50 * 1024 * 1024

# CORS — allow React dev server & Codespaces
CORS_ALLOWED_ORIGINS = [
    'http://localhost:5173',
    'http://127.0.0.1:5173',
    'http://localhost:5174',
    'http://127.0.0.1:5174',
    'http://localhost:8000',
    'http://127.0.0.1:8000',
]
CORS_ALLOW_CREDENTIALS = True

CSRF_TRUSTED_ORIGINS = [
    'http://localhost:5173',
    'http://127.0.0.1:5173',
    'http://localhost:5174',
    'http://127.0.0.1:5174',
    'http://localhost:8000',
    'http://127.0.0.1:8000',
]

CSRF_COOKIE_HTTPONLY = False  # Allow JS to read CSRF cookie

# In Codespaces, allow any *.app.github.dev origin
CODESPACE_NAME = os.getenv('CODESPACE_NAME', '')
GITHUB_CODESPACES_PORT_FORWARDING_DOMAIN = os.getenv(
    'GITHUB_CODESPACES_PORT_FORWARDING_DOMAIN', 'app.github.dev'
)
if CODESPACE_NAME:
    codespace_backend = f"https://{CODESPACE_NAME}-8000.{GITHUB_CODESPACES_PORT_FORWARDING_DOMAIN}"
    codespace_frontend = f"https://{CODESPACE_NAME}-5173.{GITHUB_CODESPACES_PORT_FORWARDING_DOMAIN}"
    CORS_ALLOWED_ORIGINS += [codespace_backend, codespace_frontend]
    CSRF_TRUSTED_ORIGINS = [codespace_backend, codespace_frontend]
    CORS_ALLOW_ALL_ORIGINS = True

# --- Logging ---
LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'verbose': {
            'format': '[{asctime}] {levelname} {name} — {message}',
            'style': '{',
            'datefmt': '%H:%M:%S',
        },
    },
    'handlers': {
        'console': {
            'class': 'logging.StreamHandler',
            'formatter': 'verbose',
        },
    },
    'loggers': {
        'django.request': {
            'handlers': ['console'],
            'level': 'INFO',
            'propagate': False,
        },
        'ingestion': {
            'handlers': ['console'],
            'level': 'DEBUG',
            'propagate': False,
        },
        'agents': {
            'handlers': ['console'],
            'level': 'DEBUG',
            'propagate': False,
        },
        'chatbot': {
            'handlers': ['console'],
            'level': 'DEBUG',
            'propagate': False,
        },
        'dashboard': {
            'handlers': ['console'],
            'level': 'DEBUG',
            'propagate': False,
        },
        'analytics': {
            'handlers': ['console'],
            'level': 'DEBUG',
            'propagate': False,
        },
        'administration': {
            'handlers': ['console'],
            'level': 'DEBUG',
            'propagate': False,
        },
    },
}

# --- Admin Site Customization ---
ADMIN_SITE_HEADER = 'MarineMind Administration'
ADMIN_SITE_TITLE = 'MarineMind Admin'
ADMIN_INDEX_TITLE = 'Dashboard'
