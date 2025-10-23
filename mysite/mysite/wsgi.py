"""
WSGI config for mysite project.

It exposes the WSGI callable as a module-level variable named ``application``.
"""

import os
from django.core.wsgi import get_wsgi_application

# Point to your settings.py inside the inner mysite folder
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "mysite.settings")

# This is the callable that WSGI servers use
application = get_wsgi_application()
