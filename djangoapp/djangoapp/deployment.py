import os
from .settings import *
from .settings import BASE_DIR

# SECURITY WARNING: keep the secret key used in production secret!
SECRET_KEY = os.environ['SECRET']

DEBUG = True
ALLOWED_HOSTS = [os.environ['djangoiot.azurewebsites.net']]
CSRF_TRUSTED_ORIGIN = ['https://'+ os.environ['djangoiot.azurewebsites.net']]


# Application definition
INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'whitenoise.runserver_nostatic',
    'AppIoT',
]

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'whitenoise.middleware.WhiteNoiseMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

#STATIC_URL = os.environ.get("DJANGO_STATIC_URL", "/static/")
#STATIC_ROOT = os.environ.get("DJANGO_STATIC_ROOT", "./static/")

STATIC_URL = os.environ.get(BASE_DIR, "/static")
STATICFILES_STORAGE = 'whitenoise.storage.CompressedManifestStaticFilesStorage'
STATIC_ROOT = os.path.join(BASE_DIR, "/static")

#cosmosDB
DATABASES = {
    'default': {
        'ENGINE': 'django_cosmosdb.backends.CosmosDB',
        'HOST': 'https://cosmosiot.documents.azure.com:443/',
        'PORT': 10255,  # Porta predefinita per Cosmos DB
        'OPTIONS': {
            'masterkey': 't7ulPQLXlfAYTG0QTpbojHpEnYJQkcnY1PE8CTB0PK4jH7yiZUH9drJoKkuTuFf64ntb4Hs1NUsxACDbp3WATg==',
            'database': 'cosmosiot',
            'collection': 'YOUR_COLLECTION_NAME',
        },
    }
}


# Default primary key field type
# https://docs.djangoproject.com/en/5.0/ref/settings/#default-auto-field

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'
