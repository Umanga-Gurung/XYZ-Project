from pathlib import Path
import os


BASE_DIR = Path(__file__).resolve().parent.parent
SECRET_KEY = 'django-insecure-ec65z229mhfzv8ofg4+jfwy2*bh+tdkold5&((tc7$8+5k!sh-'
DEBUG = True
ALLOWED_HOSTS = ['*']



INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'rest_framework',
    'app',
    'category',
    'store',
    'cart',
    'accounts',
    'orders',
]

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
    'whitenoise.middleware.WhiteNoiseMiddleware',
]

ROOT_URLCONF = 'project.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
                'category.context_processors.menu_links',
                'cart.context_processors.counter',
            ],
        },
    },
]

WSGI_APPLICATION = 'project.wsgi.application'
AUTH_USER_MODEL = 'app.Account'


DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': BASE_DIR / 'db.sqlite3',
    }
}


AUTH_PASSWORD_VALIDATORS = []


LANGUAGE_CODE = 'en-us'
TIME_ZONE = 'UTC'
USE_I18N = True
USE_TZ = True


BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
STATIC_ROOT = os.path.join(BASE_DIR, 'staticfiles')
STATIC_URL = '/static/'


DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

MEDIA_URL = '/media/'
MEDIA_ROOT = os.path.join(BASE_DIR, 'media')
CRISPY_TEMPLATE_PACK = 'bootstrap4'

ESEWA_PAYMENT_URL = os.environ.get('ESEWA_PAYMENT_URL', 'https://rc-epay.esewa.com.np/api/epay/main/v2/form')
ESEWA_STATUS_CHECK_URL = os.environ.get('ESEWA_STATUS_CHECK_URL', 'https://rc.esewa.com.np/api/epay/transaction/status/')
ESEWA_PRODUCT_CODE = os.environ.get('ESEWA_PRODUCT_CODE', 'EPAYTEST')
ESEWA_SECRET_KEY = os.environ.get('ESEWA_SECRET_KEY', '8gBm/:&EnhH.1/q')
ESEWA_SIGNED_FIELD_NAMES = os.environ.get(
    'ESEWA_SIGNED_FIELD_NAMES',
    'total_amount,transaction_uuid,product_code',
)

from django.contrib.messages import constants as messages
MESSAGE_TAGS = {
    messages.ERROR: 'danger',
    
}
