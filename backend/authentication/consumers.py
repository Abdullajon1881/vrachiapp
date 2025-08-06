import json
import asyncio
from channels.generic.websocket import AsyncWebsocketConsumer
from channels.db import database_sync_to_async
from django.contrib.auth import get_user_model
from .models import Consultation, Message
from django.utils import timezone

User = get_user_model()


class ChatConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        self.consultation_id = self.scope['url_route']['kwargs']['consultation_id']
        self.room_group_name = f'chat_{self.consultation_id}'
        
        # Проверяем, что пользователь авторизован
        if not self.scope['user'].is_authenticated:
            await self.close()
            return
        
        # Проверяем, что пользователь имеет доступ к этой консультации
        if not await self.can_access_consultation():
            await self.close()
            return
        
        # Присоединяемся к группе чата
        await self.channel_layer.group_add(
            self.room_group_name,
            self.channel_name
        )
        
        await self.accept()
        
        # Отправляем информацию о подключении
        await self.send(text_data=json.dumps({
            'type': 'connection_established',
            'message': 'Подключение к чату установлено'
        }))

    async def disconnect(self, close_code):
        # Покидаем группу чата
        await self.channel_layer.group_discard(
            self.room_group_name,
            self.channel_name
        )

    async def receive(self, text_data):
        text_data_json = json.loads(text_data)
        message_type = text_data_json.get('type', 'chat_message')
        
        if message_type == 'chat_message':
            message = text_data_json['message']
            sender_id = self.scope['user'].id
            
            # Сохраняем сообщение в базе данных
            saved_message = await self.save_message(message, sender_id)
            
            if saved_message:
                # Отправляем сообщение в группу
                await self.channel_layer.group_send(
                    self.room_group_name,
                    {
                        'type': 'chat_message',
                        'message': message,
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
                    'message': 'Не удалось отправить сообщение'
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
            
            # Проверяем, может ли пользователь писать в этой консультации
            if sender == consultation.patient and not consultation.can_patient_write:
                return None
            elif sender == consultation.doctor and not consultation.can_doctor_write:
                return None
            
            # Создаем сообщение
            message = Message.objects.create(
                consultation=consultation,
                sender=sender,
                content=content
            )
            
            return message
        except (Consultation.DoesNotExist, User.DoesNotExist):
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