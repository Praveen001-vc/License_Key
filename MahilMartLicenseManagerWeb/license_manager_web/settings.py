import os
from pathlib import Path

# Build paths inside the project like this: BASE_DIR / 'subdir'.
BASE_DIR = Path(__file__).resolve().parent.parent


SECRET_KEY = os.environ.get(
    "LICENSE_MANAGER_SECRET_KEY",
    "django-insecure-license-manager-separate-project-key",
)
DEBUG = os.environ.get("LICENSE_MANAGER_DEBUG", "1") == "1"
ALLOWED_HOSTS = [
    host.strip()
    for host in (
        os.environ.get("LICENSE_MANAGER_ALLOWED_HOSTS", "127.0.0.1,localhost,testserver")
    ).split(",")
    if host.strip()
]


# Application definition

INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'licenses',
    'django.contrib.staticfiles',
]

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

ROOT_URLCONF = 'license_manager_web.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [BASE_DIR / "templates"],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
            ],
        },
    },
]

WSGI_APPLICATION = 'license_manager_web.wsgi.application'


# Database
# https://docs.djangoproject.com/en/5.2/ref/settings/#databases

db_path_override = (os.environ.get("MAHILMART_LICENSE_DB_PATH") or "").strip()
if db_path_override:
    DATABASES = {
        'default': {
            'ENGINE': 'django.db.backends.sqlite3',
            'NAME': db_path_override,
        }
    }
else:
    DATABASES = {
        'default': {
            'ENGINE': 'django.db.backends.postgresql',
            'NAME': os.environ.get("MAHILMART_LICENSE_DB_NAME", "license"),
            'USER': os.environ.get("MAHILMART_LICENSE_DB_USER", "postgres"),
            'PASSWORD': os.environ.get("MAHILMART_LICENSE_DB_PASSWORD", "admin@123"),
            'HOST': os.environ.get("MAHILMART_LICENSE_DB_HOST", "localhost"),
            'PORT': os.environ.get("MAHILMART_LICENSE_DB_PORT", "5432"),
        }
    }


# Password validation
# https://docs.djangoproject.com/en/5.2/ref/settings/#auth-password-validators

AUTH_PASSWORD_VALIDATORS = [
    {
        'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator',
    },
]


# Internationalization
# https://docs.djangoproject.com/en/5.2/topics/i18n/

LANGUAGE_CODE = 'en-us'
TIME_ZONE = os.environ.get("LICENSE_MANAGER_TIMEZONE", "Asia/Kolkata")

USE_I18N = True

USE_TZ = True


# Static files (CSS, JavaScript, Images)
# https://docs.djangoproject.com/en/5.2/howto/static-files/

STATIC_URL = '/static/'
STATICFILES_DIRS = []
_static_dir = BASE_DIR / "static"
if _static_dir.exists():
    STATICFILES_DIRS.append(_static_dir)
STATIC_ROOT = BASE_DIR / "staticfiles"

LICENSE_EMAIL = (os.environ.get("MAHILMARTPOS_LICENSE_EMAIL") or "mahiltechlab.ops@gmail.com").strip().lower()
LICENSE_SOURCE = (os.environ.get("MAHILMARTPOS_LICENSE_SOURCE") or "license_manager_page").strip()
LICENSE_MONGO_URI = (
    os.environ.get("MAHILMARTPOS_LICENSE_MONGO_URI")
    or "mongodb+srv://praveenv_db_user:ytf8RxoQPEn3tUSD@cluster0.ezhfgp1.mongodb.net/?appName=Cluster0"
).strip()
LICENSE_MONGO_DB = (os.environ.get("MAHILMARTPOS_LICENSE_MONGO_DB") or "mahilmart_pos").strip()
LICENSE_MONGO_COLLECTION = (
    os.environ.get("MAHILMARTPOS_LICENSE_MONGO_COLLECTION")
    or "license_keys"
).strip()
try:
    LICENSE_KEY_VALIDITY_MINUTES = int(
        (os.environ.get("MAHILMARTPOS_LICENSE_KEY_VALIDITY_MINUTES") or "10").strip()
    )
except ValueError:
    LICENSE_KEY_VALIDITY_MINUTES = 10
LICENSE_KEY_SEED_MODE = (
    os.environ.get("MAHILMARTPOS_LICENSE_KEY_SEED_MODE") or "windowed"
).strip().lower()

LOGIN_URL = "licenses:login"
LOGIN_REDIRECT_URL = "licenses:dashboard"
LOGOUT_REDIRECT_URL = "licenses:login"

# Default primary key field type
# https://docs.djangoproject.com/en/5.2/ref/settings/#default-auto-field

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'
