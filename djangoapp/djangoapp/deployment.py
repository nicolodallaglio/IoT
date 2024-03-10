import os
from .settings import *
from .settings import BASE_DIR

# SECURITY WARNING: keep the secret key used in production secret!
SECRET_KEY = os.environ['SECRET']

DEBUG = False
ALLOWED_HOSTS = [os.environ['WEBSITE_HOSTNAME']]
CSRF_TRUSTED_ORIGIN = ['https://'+ os.environ['WEBSITE_HOSTNAME']]


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
    # Add whitenoise middleware after the security middleware
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

#STATIC_URL = os.environ.get(BASE_DIR, "static")
#SESSION_ENGINE = "django.contrib.sessions.backends.cache"

STATICFILES_STORAGE = 'whitenoise.storage.CompressedManifestStaticFilesStorage'
STATIC_ROOT = os.path.join(BASE_DIR, "static")


#DBforPostgreSQL
import psycopg2

# Update connection string information

host = "databaseiot.postgres.database.azure.com"
dbname = "postgres"
user = "nico99"
password = "lollipop99!"
sslmode = "require"

# Construct connection string

conn_string = "host={0} user={1} dbname={2} password={3} sslmode={4}".format(host, user, dbname, password, sslmode)
conn = psycopg2.connect(conn_string)
print("Connection established")

cursor = conn.cursor()

"""
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql',
        'NAME': 'databaseiot.postgres.database.azure.com',
        'USER': os.environ.get('DB_USER'),  # Assicurati di impostare questa variabile di ambiente con il nome utente del tuo database
        'PASSWORD': os.environ.get('DB_PASSWORD'),  # Assicurati di impostare questa variabile di ambiente con la password del tuo database
        'HOST': os.environ.get('DB_HOST'),  # Assicurati di impostare questa variabile di ambiente con l'host del tuo database
        'PORT': os.environ.get('DB_PORT', '5432'),  # Assicurati di impostare questa variabile di ambiente con la porta del tuo database, di default è 5432 per PostgreSQL
        'OPTIONS': {
            'sslmode': 'require',  # Impostazione necessaria per connettersi in modo sicuro ai database PostgreSQL su Azure
        }
    }
}
"""

# Default primary key field type
# https://docs.djangoproject.com/en/5.0/ref/settings/#default-auto-field

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'
