from django.utils.deprecation import MiddlewareMixin
from django.contrib.auth.models import AnonymousUser
from django.contrib.auth import get_user_model
from channels.middleware import BaseMiddleware
from channels.db import database_sync_to_async
from django.contrib.auth.models import AnonymousUser
from django.contrib.auth import get_user_model
import json

User = get_user_model()

class DisableCSRFMiddleware(MiddlewareMixin):
    def process_request(self, request):
        if request.path.startswith('/api/'):
            setattr(request, '_dont_enforce_csrf_checks', True)

class WebSocketAuthMiddleware(BaseMiddleware):
    async def __call__(self, scope, receive, send):
        # Получаем пользователя из сессии
        user = await self.get_user(scope)
        scope['user'] = user
        return await super().__call__(scope, receive, send)

    @database_sync_to_async
    def get_user(self, scope):
        # Проверяем, есть ли сессия в scope
        if 'session' not in scope:
            return AnonymousUser()
        
        session_key = scope['session'].get('_auth_user_id')
        if session_key:
            try:
                return User.objects.get(id=session_key)
            except User.DoesNotExist:
                return AnonymousUser()
        return AnonymousUser() 