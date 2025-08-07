import os
import json
import logging
from typing import Optional, Dict, Any
import google.generativeai as genai
from django.conf import settings
from django.core.files.storage import default_storage
from django.core.files.base import ContentFile
from .models import AIDialogue, AIMessage, User

# Настройка логирования
logger = logging.getLogger(__name__)

# Настройка Gemini API
GEMINI_API_KEY = "AIzaSyBGjqF-6Vs3z7NlLj8708eKmeBc1QWFi-c"
genai.configure(api_key=GEMINI_API_KEY)

class HealzyAIService:
    """Сервис для работы с Healzy AI (Gemini)"""
    
    def __init__(self):
        self.model_name = "gemini-1.5-flash"
        self.model = genai.GenerativeModel(self.model_name)
        
        # Системный промпт для точных ответов
        self.system_prompt = """
Ты - Healzy AI, медицинский помощник. 

ПРАВИЛА:
- Внимательно читай каждый вопрос пользователя
- Отвечай ТОЧНО на заданный вопрос
- Не используй шаблонные фразы
- Анализируй конкретную ситуацию
- Говори на русском языке

МЕДИЦИНСКИЕ ВОПРОСЫ:
- Анализируй симптомы подробно
- Давай практические советы
- Объясняй простым языком
- Рекомендуй врача только при серьезных симптомах

ОБЫЧНЫЕ ВОПРОСЫ:
- Отвечай дружелюбно и по делу
- Поддерживай разговор
- Будь полезной

НЕ ДЕЛАЙ:
❌ Не повторяй одни и те же фразы
❌ Не говори "Привет! Как дела?" если не спрашивают
❌ Не добавляй лишнюю информацию
❌ Не используй шаблоны

ДЕЛАЙ:
✅ Читай вопрос внимательно
✅ Отвечай конкретно на вопрос
✅ Будь полезной и точной
✅ Анализируй контекст
"""
    
    def _is_medical_question(self, text: str) -> bool:
        """Проверяет, является ли вопрос медицинским (теперь принимаем почти все)"""
        # Убрал строгие ограничения - теперь отвечаем на все вопросы!
        return True  # Всегда возвращаем True, чтобы AI отвечала на любые вопросы
    
    def _create_safety_disclaimer(self, message: str) -> str:
        """Создает предупреждение о безопасности только для серьезных случаев"""
        # Ключевые слова серьезных симптомов
        serious_keywords = [
            'боль в груди', 'сердце болит', 'не могу дышать', 'потеря сознания', 
            'кровь', 'высокая температура', 'судороги', 'обморок', 'сильная боль',
            'рвота с кровью', 'черный стул', 'сильное головокружение', 'паралич'
        ]
        
        # Проверяем, есть ли серьезные симптомы
        message_lower = message.lower()
        for keyword in serious_keywords:
            if keyword in message_lower:
                return "\n\n⚠️ При таких симптомах рекомендую срочно обратиться к врачу!"
        
        # Для обычных вопросов не добавляем предупреждение
        return ""
    
    async def process_text_message(self, user: User, message: str) -> Dict[str, Any]:
        """Обрабатывает текстовое сообщение"""
        try:
            # Проверяем, является ли вопрос медицинским
            if not self._is_medical_question(message):
                response = """Извините, я Healzy AI и специализируюсь только на медицинских вопросах. 
                
Я могу помочь вам с:
• Анализом симптомов
• Общими медицинскими рекомендациями  
• Объяснением медицинских терминов
• Советами о том, когда обратиться к врачу

Пожалуйста, задайте вопрос, связанный со здоровьем или медициной."""
                return {
                    'success': True,
                    'response': response,
                    'type': 'text'
                }
            
            # Создаем контекст с системным промптом
            full_prompt = f"{self.system_prompt}\n\nВопрос пользователя: {message}\n\nОтветь точно на этот вопрос:"
            
            # Отправляем запрос к Gemini
            response = self.model.generate_content(full_prompt)
            
            if response and response.text:
                ai_response = response.text + self._create_safety_disclaimer(message)
                
                return {
                    'success': True,
                    'response': ai_response,
                    'type': 'text'
                }
            else:
                return {
                    'success': False,
                    'error': 'Не удалось получить ответ от AI'
                }
                
        except Exception as e:
            logger.error(f"Ошибка при обработке текстового сообщения: {str(e)}")
            return {
                'success': False,
                'error': 'Произошла ошибка при обработке сообщения'
            }
    
    async def process_image_message(self, user: User, image_file) -> Dict[str, Any]:
        """Обрабатывает изображение"""
        try:
            # Сохраняем файл временно
            file_path = default_storage.save(f'temp/ai_images/{image_file.name}', image_file)
            
            # Создаем промпт для анализа изображения
            prompt = f"""{self.system_prompt}

Пользователь прислал изображение для медицинского анализа. 
Проанализируй изображение и дай медицинские рекомендации.

ВАЖНО: 
- Опиши что видишь на изображении
- Дай общие рекомендации
- Обязательно порекомендуй обратиться к врачу если видишь что-то серьезное
- Не ставь точный диагноз"""

            # Загружаем изображение для Gemini
            with default_storage.open(file_path, 'rb') as f:
                image_data = f.read()
            
            # Создаем объект изображения для Gemini
            image_part = {
                "mime_type": image_file.content_type,
                "data": image_data
            }
            
            # Отправляем запрос с изображением
            response = self.model.generate_content([prompt, image_part])
            
            # Удаляем временный файл
            default_storage.delete(file_path)
            
            if response and response.text:
                ai_response = response.text + self._create_safety_disclaimer("medical_image")
                
                return {
                    'success': True,
                    'response': ai_response,
                    'type': 'image'
                }
            else:
                return {
                    'success': False,
                    'error': 'Не удалось проанализировать изображение'
                }
                
        except Exception as e:
            logger.error(f"Ошибка при обработке изображения: {str(e)}")
            return {
                'success': False,
                'error': 'Произошла ошибка при анализе изображения'
            }
    
    async def process_audio_message(self, user: User, audio_file) -> Dict[str, Any]:
        """Обрабатывает аудио сообщение"""
        try:
            # Базовая обработка аудио - пока что отвечаем текстом на голосовые сообщения
            # TODO: В будущем добавить Speech-to-Text и Text-to-Speech
            
            ai_response = f"""Привет! 🎤 Получила ваше голосовое сообщение! 

Круто, что вы попробовали голосовую функцию! 😊 Пока я отвечаю текстом, но очень скоро научусь говорить! 

Расскажите текстом - что вас беспокоит? Или отправьте фото, если нужно что-то посмотреть. Я Healzy AI и всегда рада помочь! ✨"""
            
            return {
                'success': True,
                'response': ai_response,
                'type': 'text',  # Возвращаем текстовый ответ на голосовое сообщение
                'is_voice_response': False
            }
                
        except Exception as e:
            logger.error(f"Ошибка при обработке аудио: {str(e)}")
            return {
                'success': False,
                'error': 'Произошла ошибка при обработке аудио'
            }
    
    def save_dialogue_message(self, user: User, content: str, sender_type: str, 
                            message_type: str = 'text', file_path: str = None) -> AIMessage:
        """Сохраняет сообщение в диалоге"""
        try:
            # Получаем или создаем активный диалог
            dialogue, created = AIDialogue.objects.get_or_create(
                user=user,
                is_active=True,
                defaults={'title': f'Диалог с AI от {user.first_name}'}
            )
            
            # Создаем сообщение
            message = AIMessage.objects.create(
                dialogue=dialogue,
                sender_type=sender_type,
                message_type=message_type,
                content=content,
                file_path=file_path
            )
            
            # Обновляем время последнего обновления диалога
            dialogue.save()
            
            return message
            
        except Exception as e:
            logger.error(f"Ошибка при сохранении сообщения: {str(e)}")
            raise

# Создаем экземпляр сервиса
ai_service = HealzyAIService()
