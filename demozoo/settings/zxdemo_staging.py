from .staging import *

from django.conf.global_settings import TEMPLATE_CONTEXT_PROCESSORS
TEMPLATE_CONTEXT_PROCESSORS += (
	'django.core.context_processors.request',
	'zxdemo.context_processors.zxdemo_context',
)

ROOT_URLCONF = 'zxdemo.urls'

ZXDEMO_PLATFORM_IDS = [2]

ALLOWED_HOSTS = ['staging.zxdemo.org', 'localhost']
