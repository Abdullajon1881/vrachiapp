"""
ASGI config for vrachiapp_backend project.

It exposes the ASGI callable as a module-level variable named ``application``.

For more information on this file, see
https://docs.djangoproject.com/en/4.2/howto/deployment/asgi/
"""

import os
from django.core.asgi import get_asgi_application
from channels.routing import ProtocolTypeRouter, URLRouter
from channels.auth import AuthMiddlewareStack
from channels.sessions import SessionMiddlewareStack
from authentication.routing import websocket_urlpatterns
from authentication.middleware import WebSocketAuthMiddleware

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'vrachiapp_backend.settings')

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
