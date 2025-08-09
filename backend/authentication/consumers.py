import json
import asyncio
import logging
import os
from channels.generic.websocket import AsyncWebsocketConsumer
from channels.db import database_sync_to_async
from django.contrib.auth import get_user_model
from .models import Consultation, Message
from django.utils import timezone

logger = logging.getLogger(__name__)
User = get_user_model()

# Redis rate-limit client (async)
try:
    import redis.asyncio as aioredis  # redis-py >= 4
except Exception:
    aioredis = None

RATE_LIMIT_MSGS_PER_MINUTE = int(os.getenv('CHAT_RATE_LIMIT_PER_MIN', '60'))
RATE_LIMIT_BAN_SECONDS = int(os.getenv('CHAT_RATE_LIMIT_BAN_SECONDS', '60'))


class ChatConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        try:
            self.consultation_id = self.scope['url_route']['kwargs']['consultation_id']
            self.room_group_name = f'chat_{self.consultation_id}'
            
            logger.info(f"WebSocket connect attempt for consultation {self.consultation_id}")
            logger.info(f"User: {self.scope['user']}, authenticated: {self.scope['user'].is_authenticated}")
            
            # Проверяем, что пользователь авторизован
            if not self.scope['user'].is_authenticated:
                logger.warning(f"Unauthenticated user tried to connect to consultation {self.consultation_id}")
                await self.close(code=4001)
                return
            
            # Проверяем, что пользователь имеет доступ к этой консультации
            access_granted = await self.can_access_consultation()
            if not access_granted:
                logger.warning(f"User {self.scope['user'].id} denied access to consultation {self.consultation_id}")
                await self.close(code=4003)
                return
            
            # Присоединяемся к группе чата
            await self.channel_layer.group_add(
                self.room_group_name,
                self.channel_name
            )
            
            await self.accept()
            
            logger.info(f"User {self.scope['user'].id} connected to consultation {self.consultation_id}")
            
            # Отправляем информацию о подключении
            await self.send(text_data=json.dumps({
                'type': 'connection_established',
                'message': 'Подключение к чату установлено',
                'consultation_id': self.consultation_id
            }))
            
        except Exception as e:
            logger.error(f"Error in WebSocket connect: {e}")
            await self.close(code=4000)

    async def disconnect(self, close_code):
        # Покидаем группу чата
        await self.channel_layer.group_discard(
            self.room_group_name,
            self.channel_name
        )

    async def receive(self, text_data):
        try:
            if not self.scope['user'].is_authenticated:
                await self.send(text_data=json.dumps({
                    'type': 'error',
                    'message': 'Необходима аутентификация'
                }))
                return
                
            text_data_json = json.loads(text_data)
            message_type = text_data_json.get('type', 'chat_message')
            
            if message_type == 'chat_message':
                message_content = text_data_json.get('message', '').strip()
                
                if not message_content:
                    await self.send(text_data=json.dumps({
                        'type': 'error',
                        'message': 'Сообщение не может быть пустым'
                    }))
                    return
                
                sender_id = self.scope['user'].id

                # Rate limiting через Redis (если доступен)
                if aioredis is not None:
                    try:
                        redis = aioredis.from_url(
                            f"redis://{os.getenv('REDIS_HOST', '127.0.0.1')}:{os.getenv('REDIS_PORT', '6379')}/0",
                            encoding='utf-8', decode_responses=True
                        )
                        key = f"rate:chat:{self.consultation_id}:{sender_id}"
                        # Инкремент и установка TTL, первый инкремент возвращает 1
                        count = await redis.incr(key)
                        if count == 1:
                            await redis.expire(key, 60)
                        if count > RATE_LIMIT_MSGS_PER_MINUTE:
                            # Превышение — сообщаем и не обрабатываем
                            await self.send(text_data=json.dumps({
                                'type': 'error',
                                'message': 'Слишком много сообщений. Попробуйте позже.'
                            }))
                            return
                    except Exception as e:
                        logger.warning(f"Rate-limit Redis error: {e}")
                
                # Сохраняем сообщение в базе данных
                saved_message = await self.save_message(message_content, sender_id)
                
                if saved_message:
                    logger.info(f"Message saved: {saved_message.id} from user {sender_id}")
                    
                    # Отправляем сообщение в группу
                    await self.channel_layer.group_send(
                        self.room_group_name,
                        {
                            'type': 'chat_message',
                            'message': message_content,
                            'sender_id': sender_id,
                            'sender_name': self.scope['user'].full_name,
                            'sender_initials': self.scope['user'].initials,
                            'timestamp': saved_message.created_at.isoformat(),
                            'message_id': saved_message.id
                        }
                    )
                else:
                    # Отправляем ошибку отправителю
                    await self.send(text_data=json.dumps({
                        'type': 'error',
                        'message': 'Не удалось отправить сообщение. Проверьте права доступа.'
                    }))
                    
            elif message_type == 'ping':
                # Отвечаем на ping для поддержания соединения
                await self.send(text_data=json.dumps({
                    'type': 'pong',
                    'timestamp': timezone.now().isoformat()
                }))
                
        except json.JSONDecodeError:
            await self.send(text_data=json.dumps({
                'type': 'error',
                'message': 'Неверный формат данных'
            }))
        except Exception as e:
            logger.error(f"Error in receive: {e}")
            await self.send(text_data=json.dumps({
                'type': 'error',
                'message': 'Произошла ошибка при обработке сообщения'
            }))

    async def chat_message(self, event):
        # Отправляем сообщение в WebSocket
        await self.send(text_data=json.dumps({
            'type': 'chat_message',
            'message': event['message'],
            'sender_id': event['sender_id'],
            'sender_name': event['sender_name'],
            'sender_initials': event['sender_initials'],
            'timestamp': event['timestamp'],
            'message_id': event['message_id']
        }))

    @database_sync_to_async
    def can_access_consultation(self):
        """Проверяет, может ли пользователь получить доступ к консультации"""
        try:
            consultation = Consultation.objects.get(id=self.consultation_id)
            user = self.scope['user']
            
            # Пользователь может получить доступ, если он пациент или врач этой консультации
            return (user == consultation.patient or user == consultation.doctor)
        except Consultation.DoesNotExist:
            return False

    @database_sync_to_async
    def save_message(self, content, sender_id):
        """Сохраняет сообщение в базе данных"""
        try:
            consultation = Consultation.objects.get(id=self.consultation_id)
            sender = User.objects.get(id=sender_id)
            
            logger.info(f"Attempting to save message from user {sender_id} to consultation {self.consultation_id}")
            logger.info(f"Consultation status: {consultation.status}")
            logger.info(f"Can patient write: {consultation.can_patient_write}")
            logger.info(f"Can doctor write: {consultation.can_doctor_write}")
            
            # Проверяем, может ли пользователь писать в этой консультации
            if sender == consultation.patient and not consultation.can_patient_write:
                logger.warning(f"Patient {sender_id} cannot write to consultation {self.consultation_id}")
                return None
            elif sender == consultation.doctor and not consultation.can_doctor_write:
                logger.warning(f"Doctor {sender_id} cannot write to consultation {self.consultation_id}")
                return None
            
            # Создаем сообщение
            message = Message.objects.create(
                consultation=consultation,
                sender=sender,
                content=content
            )
            
            logger.info(f"Message created successfully: {message.id}")
            return message
            
        except Consultation.DoesNotExist:
            logger.error(f"Consultation {self.consultation_id} not found")
            return None
        except User.DoesNotExist:
            logger.error(f"User {sender_id} not found")
            return None
        except Exception as e:
            logger.error(f"Error saving message: {e}")
            return None


class NotificationConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        if not self.scope['user'].is_authenticated:
            await self.close()
            return
        
        self.user_id = self.scope['user'].id
        self.user_group_name = f'user_{self.user_id}'
        
        # Присоединяемся к группе пользователя
        await self.channel_layer.group_add(
            self.user_group_name,
            self.channel_name
        )
        
        await self.accept()
        
        await self.send(text_data=json.dumps({
            'type': 'connection_established',
            'message': 'Подключение к уведомлениям установлено'
        }))

    async def disconnect(self, close_code):
        await self.channel_layer.group_discard(
            self.user_group_name,
            self.channel_name
        )

    async def receive(self, text_data):
        # Обработка входящих сообщений (если нужно)
        pass

    async def notification_message(self, event):
        # Отправляем уведомление пользователю
        await self.send(text_data=json.dumps({
            'type': 'notification',
            'message': event['message'],
            'notification_type': event.get('notification_type', 'info'),
            'data': event.get('data', {})
        })) 