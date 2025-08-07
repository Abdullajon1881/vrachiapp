from django.utils.deprecation import MiddlewareMixin
from django.contrib.auth.models import AnonymousUser
from django.contrib.auth import get_user_model
from channels.middleware import BaseMiddleware
from channels.db import database_sync_to_async
from django.contrib.sessions.models import Session
from urllib.parse import parse_qs
import json
import logging

logger = logging.getLogger(__name__)
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
        logger.info(f"WebSocket user: {user}, authenticated: {user.is_authenticated}")
        return await super().__call__(scope, receive, send)

    @database_sync_to_async
    def get_user(self, scope):
        try:
            # Сначала пытаемся получить пользователя из сессии Django
            if 'session' in scope and scope['session']:
                session_key = scope['session'].get('_auth_user_id')
                if session_key:
                    try:
                        user = User.objects.get(id=session_key)
                        logger.info(f"User found in session: {user}")
                        return user
                    except User.DoesNotExist:
                        logger.warning(f"User with id {session_key} not found")
                        pass

            # Пытаемся получить sessionid из cookies
            headers = dict(scope.get('headers', []))
            cookie_header = headers.get(b'cookie', b'').decode()
            
            if cookie_header:
                cookies = {}
                for cookie in cookie_header.split(';'):
                    if '=' in cookie:
                        key, value = cookie.strip().split('=', 1)
                        cookies[key] = value
                
                sessionid = cookies.get('sessionid')
                if sessionid:
                    try:
                        session = Session.objects.get(session_key=sessionid)
                        session_data = session.get_decoded()
                        user_id = session_data.get('_auth_user_id')
                        if user_id:
                            user = User.objects.get(id=user_id)
                            logger.info(f"User found via cookie session: {user}")
                            return user
                    except (Session.DoesNotExist, User.DoesNotExist) as e:
                        logger.warning(f"Session/User not found via cookie: {e}")
                        pass

            logger.warning("No authenticated user found, returning AnonymousUser")
            return AnonymousUser()
            
        except Exception as e:
            logger.error(f"Error in WebSocket auth middleware: {e}")
            return AnonymousUser() 