"""
Django settings for app project.
"""

import os
import sys
import ldap
import platform
import builtins
from django_auth_ldap.config import LDAPSearch

# Validate Python version
if platform.python_version_tuple() < ('3', '6'):
    raise RuntimeError(
        "abcontrol requires Python 3.6 or higher (current: Python {})".format(platform.python_version())
    )

# Build paths inside the project like this: os.path.join(BASE_DIR, ...)
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# ----- Configuration file -----
CONFIG_FILE = "/etc/abcontrol/abcontrol.yaml"

if "/opt" not in sys.path:
    sys.path.insert(0, '/opt')
import ablib.utils as abutils

# Load configuration
config = abutils.load_config(CONFIG_FILE)
builtins.config = config

django_config = config.django

# ----- settings, mostly from config file -----

# SECURITY WARNING: keep the secret key used in production secret!
SECRET_KEY = django_config.secret_key

tmp = django_config.get("requests_ca_bundle", None)
if tmp:
    # Use specified CA certificates
    os.environ["REQUESTS_CA_BUNDLE"] = tmp

# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = False
DEBUG = True

# We are behind a firewall that blocks connection to gunicorn, apache2 proxies to us
ALLOWED_HOSTS = ['*']

# Application definition

INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'base.apps.BaseConfig',
    'docs.apps.DocsConfig',
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

ROOT_URLCONF = 'app.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [
            os.path.join(BASE_DIR, 'templates'),
        ],
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

WSGI_APPLICATION = 'app.wsgi.application'

# Database
# https://docs.djangoproject.com/en/2.2/ref/settings/#databases

DATABASES = {}

if "db" in django_config:
    DATABASES["default"] = {
        'ENGINE': 'django.db.backends.postgresql_psycopg2',
        'NAME': django_config.db.NAME,
        'USER': django_config.db.USER,
        'PASSWORD': django_config.db.PASSWORD,
        'HOST': django_config.db.HOST,
        'PORT': django_config.db.PORT,
    }
else:
    # Dummy database, to be able to run CLI scripts
    DATABASES['default'] = {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': "/var/lib/abcontrol/abcontrol.sqlite3",
    }

# Password validation
# https://docs.djangoproject.com/en/2.2/ref/settings/#auth-password-validators

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
# https://docs.djangoproject.com/en/2.2/topics/i18n/

LANGUAGE_CODE = django_config.language_code
TIME_ZONE = django_config.time_zone
USE_I18N = True
USE_L10N = True
USE_TZ = True

# Static files (CSS, JavaScript, Images)
# https://docs.djangoproject.com/en/2.2/howto/static-files/

STATIC_URL = '/static/'
STATIC_ROOT = os.path.join(BASE_DIR, 'static')

# Redirect to home URL after login (Default redirects to /accounts/profile/)
LOGIN_REDIRECT_URL = '/'
LOGOUT_REDIRECT_URL = '/'

# LDAP authentification
AUTHENTICATION_BACKENDS = [
    'django.contrib.auth.backends.ModelBackend',
]

try:
    if django_config.ldap.enabled:
        AUTHENTICATION_BACKENDS.append("django_auth_ldap.backend.LDAPBackend")
        AUTH_LDAP_SERVER_URI = django_config.ldap.server
        AUTH_LDAP_START_TLS = django_config.ldap.get("start_tls", False)
        AUTH_LDAP_BIND_DN = django_config.ldap.bind_dn
        AUTH_LDAP_BIND_PASSWORD = django_config.ldap.bind_password
        AUTH_LDAP_USER_SEARCH = LDAPSearch(django_config.ldap.user_search, ldap.SCOPE_SUBTREE, "(uid=%(user)s)")
except AttributeError:
    pass
