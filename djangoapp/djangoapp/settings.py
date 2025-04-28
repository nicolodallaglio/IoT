import os
from pathlib import Path

# Build paths inside the project like this: BASE_DIR / 'subdir'.
BASE_DIR = Path(__file__).resolve().parent.parent

ADAFRUIT_AIO_USERNAME = "nicodalla99"
ADAFRUIT_AIO_KEY      = "aio_Nmgf31z2Sd530yAMLfe6o8Xs31gm"

# Quick-start development settings - unsuitable for production
# See https://docs.djangoproject.com/en/5.0/howto/deployment/checklist/

# SECURITY WARNING: keep the secret key used in production secret!
SECRET_KEY = '+=qcplywafira(ydri0pz4^pe&w)-p$305c8kyy_)5bt#q&-=-'

# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = False
ALLOWED_HOSTS = ['127.0.0.1', 'localhost', '95.251.170.96','smartrooms.ddns.net', "109.54.166.184", "192.168.1.210", "87.17.47.6", "172.20.10.11","192.168.1.62"]

# Application definition

INSTALLED_APPS = [
    'django.contrib.admin',
    'rest_framework',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'corsheaders',
    'AppIoT',
]

MIDDLEWARE = [
    'corsheaders.middleware.CorsMiddleware',
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

CORS_ALLOWED_ORIGINS = [
    "http://localhost:8000",  # Il dominio o indirizzo IP da cui l'app Flutter farà richieste
    "http://localhost:8080",
    "http://127.0.0.1:8000",
      # Se l'app Flutter è in esecuzione su un altro porto "http://109.54.26.124:8000",
    "http://192.168.1.62:8000",
    "http://37.161.226.9",
    "http://smartrooms.ddns.net",
    "http://109.54.166.184",
    "http://87.17.47.6",
    "http://172.20.10.11",
]

ROOT_URLCONF = 'djangoapp.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': ['Project/djangoapp/AppIoT/templates'],  # Inserisci il percorso della tua directory dei template qui C:\Users\dalla\Desktop\Project\djangoapp\AppIoT\templates
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


WSGI_APPLICATION = 'djangoapp.wsgi.application'


#Database locale
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': BASE_DIR / 'db_IoT.sqlite3',
    }
}


# Password validation
# https://docs.djangoproject.com/en/5.0/ref/settings/#auth-password-validators

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
# https://docs.djangoproject.com/en/5.0/topics/i18n/

LANGUAGE_CODE = 'it-it'   # Lingua italiana

TIME_ZONE = 'Europe/Rome'  # Fuso orario italiano

USE_I18N = True
USE_L10N = True  # Aggiungi anche questa per la localizzazione
USE_TZ = True


# Static files (CSS, JavaScript, Images)
# https://docs.djangoproject.com/en/5.0/howto/static-files/
# Imposta la directory dei file statici
STATIC_ROOT = os.path.join(BASE_DIR, 'staticfiles')
# Imposta la directory dei file statici Django
STATIC_URL = '/static/'
# Default primary key field type
# https://docs.djangoproject.com/en/5.0/ref/settings/#default-auto-field

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'
