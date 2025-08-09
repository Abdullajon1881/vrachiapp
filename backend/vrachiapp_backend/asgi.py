"""
ASGI config for vrachiapp_backend project.

It exposes the ASGI callable as a module-level variable named ``application``.

For more information on this file, see
https://docs.djangoproject.com/en/4.2/howto/deployment/asgi/
"""

import os

# ВАЖНО: сначала указываем настройки Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'vrachiapp_backend.settings')

# Явно инициализируем Django до импорта модулей, использующих ORM/модели
import django
django.setup()

from django.core.asgi import get_asgi_application
from channels.routing import ProtocolTypeRouter, URLRouter
from channels.sessions import SessionMiddlewareStack
from authentication.middleware import WebSocketAuthMiddleware
from authentication.routing import websocket_urlpatterns

application = ProtocolTypeRouter({
    "http": get_asgi_application(),
    "websocket": SessionMiddlewareStack(
        WebSocketAuthMiddleware(
            URLRouter(
                websocket_urlpatterns
            )
        )
    ),
})
