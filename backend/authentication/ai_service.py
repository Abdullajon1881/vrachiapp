import os
import io
import json
import logging
import tempfile
import asyncio
import requests
from typing import Optional, Dict, Any, Tuple
from pathlib import Path
from datetime import datetime

import google.generativeai as genai
from django.conf import settings
from django.core.files.storage import default_storage
from django.core.files.base import ContentFile
from django.core.files import File
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
        
        # Информация о TTS сервисах
        logger.info("🎙️✨ TTS: Edge TTS - Красивые женские голоса Microsoft")
        logger.info("🔄 Fallback 1: Google Translate TTS")
        logger.info("🔄 Fallback 2: Браузерный женский TTS")
        logger.info("✅ Healzy AI готова говорить КРАСИВЫМ женским голосом!")
        
        # Системный промпт для медицинских вопросов
        self.system_prompt = """
Ты - Healzy AI, женщина-врач и медицинская помощница с естественным женским голосом.

ТВОЯ РОЛЬ:
- Медицинская консультантка и помощница
- Отвечаешь ТОЛЬКО на медицинские вопросы
- Анализируешь симптомы и даешь советы
- Говоришь на русском языке естественным женским голосом
- Ведешь диалог как опытная медсестра или женщина-врач
- Всегда говори о себе в женском роде

ПРИНЦИПЫ РАБОТЫ:
✅ Внимательно анализируй каждый симптом
✅ Давай конкретные, полезные советы  
✅ Объясняй медицинские вопросы простым языком
✅ Будь дружелюбной, эмпатичной, но профессиональной
✅ Отвечай точно на заданный вопрос
✅ Поддерживай естественный разговорный тон
✅ Используй интонации и паузы для лучшего восприятия
✅ Не начинай ответ с приветствия — сразу переходи к сути
✅ Говори "я рада помочь", "я думаю", "я рекомендую" (женский род)

ПРИ МЕДИЦИНСКИХ ВОПРОСАХ:
- Подробно анализируй ситуацию
- Давай практические рекомендации
- Объясняй возможные причины
- При серьезных симптомах рекомендуй врача
- Проявляй сочувствие и понимание
- Говори как заботливая женщина-врач

НЕ ДЕЛАЙ:
❌ Не ставь точные диагнозы
❌ Не повторяй шаблонные фразы  
❌ Не добавляй предупреждения к каждому ответу
❌ Не отвечай на немедицинские вопросы
❌ Не используй роботизированную речь
❌ Не говори о себе в мужском роде
"""
    
    async def _is_medical_question(self, text: str) -> bool:
        """Проверяет, является ли вопрос медицинским с помощью AI"""
        try:
            # Системный промпт для анализа вопросов
            analysis_prompt = f"""
Проанализируй этот текст и определи, связан ли он с медициной, здоровьем или медицинскими вопросами.

МЕДИЦИНСКИЕ ТЕМЫ (отвечай "ДА"):
- Симптомы и жалобы на здоровье
- Вопросы о болезнях и лечении
- Части тела и их функции
- Лекарства и медицинские процедуры
- Первая помощь и неотложные состояния
- Профилактика заболеваний
- Питание и диеты для здоровья
- Психическое здоровье и стресс
- Беременность и детское здоровье
- Приветствия и знакомство с медицинским помощником

НЕ МЕДИЦИНСКИЕ ТЕМЫ (отвечай "НЕТ"):
- Бизнес, финансы
- История, география, политика
- Наука, технологии (кроме медицинских)
- Развлечения, спорт, хобби
- Кулинария (кроме диет для здоровья)
- Философия, религия
- Литература, искусство

Текст для анализа: "{text}"

Ответь только одним словом: "ДА" или "НЕТ"
"""
            
            # Отправляем запрос к Gemini для анализа
            response = self.model.generate_content(analysis_prompt)
            
            if response and response.text:
                result = response.text.strip().upper()
                logger.info(f"AI анализ вопроса '{text[:50]}...': {result}")
                return result == "ДА"
            else:
                # Если AI не ответила, считаем что это медицинский вопрос (безопаснее)
                logger.warning("Не удалось получить ответ от AI для анализа вопроса")
                return True
                
        except Exception as e:
            logger.error(f"Ошибка при анализе вопроса с помощью AI: {str(e)}")
            # В случае ошибки считаем что это медицинский вопрос
            return True

    def _is_greeting(self, text: str) -> bool:
        """Простая эвристика для распознавания коротких приветствий/малого small talk"""
        text_lower = text.strip().lower()
        if len(text_lower) > 40:
            return False
        greeting_keywords = [
            'привет', 'здравствуй', 'здравствуйте', 'добрый день', 'добрый вечер', 'доброе утро',
            'как дела', 'как ты', 'как у тебя', 'hi', 'hello'
        ]
        return any(kw in text_lower for kw in greeting_keywords)
    
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

    def _strip_leading_greeting(self, text: str) -> str:
        """Удаляет вежливые вступительные приветствия в начале ответа"""
        if not text:
            return text
        cleaned = text.lstrip()
        lower = cleaned.lower()
        prefixes = [
            'здравствуйте', 'привет', 'добрый день', 'добрый вечер', 'доброе утро',
            'рад помочь', 'рада помочь', 'я healzy ai', 'я – healzy ai', 'я — healzy ai'
        ]
        for prefix in prefixes:
            if lower.startswith(prefix):
                # Найти конец первой строки/предложения
                # Обрезаем до первого переноса строки или точки с пробелом
                for sep in ['\n', '. ', '! ', '? ']:
                    idx = cleaned.find(sep)
                    if idx != -1 and idx < 80:
                        cleaned = cleaned[idx + len(sep):].lstrip()
                        lower = cleaned.lower()
                        break
                else:
                    # Если разделителей нет — просто удаляем сам префикс
                    cleaned = cleaned[len(prefix):].lstrip(' ,!.-')
                # После удаления одного префикса выходим
                break
        return cleaned

    async def _generate_speech_with_edge_tts(self, text: str) -> Optional[bytes]:
        """Генерирует речь с помощью Edge TTS (Microsoft) - КРАСИВЫЕ женские голоса"""
        try:
            import edge_tts
            import tempfile
            import asyncio
            
            # Очищаем текст  
            clean_text = text.strip()
            if len(clean_text) > 1000:
                clean_text = clean_text[:1000]
            
            # Женские голоса Microsoft Edge TTS для русского языка
            female_voices = [
                "ru-RU-SvetlanaNeural",  # Светлана - очень красивый женский голос
                "ru-RU-DariyaNeural",    # Дария - приятный женский голос  
                "ru-RU-PolarisNeural"    # Полярис - современный женский голос
            ]
            
            # Пробуем голоса по порядку качества
            for voice in female_voices:
                try:
                    # Создаем временный файл
                    with tempfile.NamedTemporaryFile(suffix='.mp3', delete=False) as tmp_file:
                        tmp_path = tmp_file.name
                    
                    # Генерируем речь
                    communicate = edge_tts.Communicate(clean_text, voice)
                    await communicate.save(tmp_path)
                    
                    # Читаем сгенерированное аудио
                    with open(tmp_path, 'rb') as f:
                        audio_content = f.read()
                    
                    # Удаляем временный файл
                    import os
                    os.unlink(tmp_path)
                    
                    if len(audio_content) > 1000:  # Проверяем что аудио сгенерировалось
                        logger.info(f"🎤✨ Edge TTS: Красивый женский голос {voice} для '{text[:50]}...'")
                        return audio_content
                        
                except Exception as voice_error:
                    logger.warning(f"Голос {voice} недоступен: {voice_error}")
                    continue
            
            logger.warning("❌ Все Edge TTS голоса недоступны")
            return None
                
        except ImportError:
            logger.warning("❌ Edge TTS библиотека не установлена")
            return None
        except Exception as e:
            logger.error(f"❌ Ошибка Edge TTS: {str(e)}")
            return None

    async def _generate_speech_with_google_tts(self, text: str) -> Optional[bytes]:
        """Fallback: Google Translate TTS"""
        try:
            clean_text = text.strip()
            if len(clean_text) > 1000:
                clean_text = clean_text[:1000]
            
            import urllib.parse
            encoded_text = urllib.parse.quote(clean_text)
            url = f"https://translate.google.com/translate_tts?ie=UTF-8&tl=ru&client=tw-ob&q={encoded_text}"
            
            headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}
            response = requests.get(url, headers=headers, timeout=15)
            
            if response.status_code == 200 and len(response.content) > 1000:
                logger.info(f"🔄 Google TTS: Fallback голос для '{text[:50]}...'")
                return response.content
            return None
                
        except Exception as e:
            logger.error(f"❌ Ошибка Google TTS: {str(e)}")
            return None


    async def _generate_speech_best_quality(self, text: str) -> Optional[bytes]:
        """Генерирует речь используя лучший доступный сервис"""
        
        # 1. Сначала пробуем Edge TTS (Microsoft) - САМЫЕ КРАСИВЫЕ голоса
        logger.info("🎤✨ Пробуем Edge TTS для красивого женского голоса...")
        audio_content = await self._generate_speech_with_edge_tts(text)
        if audio_content:
            return audio_content
        
        # 2. Fallback к Google Translate TTS
        logger.info("🔄 Edge TTS недоступен, пробуем Google TTS...")
        audio_content = await self._generate_speech_with_google_tts(text)
        if audio_content:
            return audio_content
        
        # 3. Если все не работает - браузерный TTS
        logger.info("🔄 Все серверные TTS недоступны, используется браузерный женский голос")
        return None

    async def process_text_message(self, user: User, message: str) -> Dict[str, Any]:
        """Обрабатывает текстовое сообщение"""
        try:
            # Короткое приветствие — отвечаем кратко и дружелюбно
            if self._is_greeting(message):
                response_text = 'Привет! Я Healzy - ваша медицинская помощница. Чем могу помочь со здоровьем?'
                
                # Генерируем голосовой ответ
                audio_content = await self._generate_speech_best_quality(response_text)
                
                return {
                    'success': True,
                    'response': response_text,
                    'type': 'text',
                    'audio_content': audio_content,
                    'has_voice': audio_content is not None
                }

            # Проверяем, является ли вопрос медицинским (с помощью AI)
            if not await self._is_medical_question(message):
                response_text = (
                    "Я могу помогать только с медицинскими вопросами. "
                    "Пожалуйста, опишите симптом или задайте вопрос о здоровье."
                )
                
                # Генерируем голосовой ответ
                audio_content = await self._generate_speech_best_quality(response_text)
                
                return {
                    'success': True,
                    'response': response_text,
                    'type': 'text',
                    'audio_content': audio_content,
                    'has_voice': audio_content is not None
                }
            
            # Создаем контекст с системным промптом
            full_prompt = (
                f"{self.system_prompt}\n\n"
                f"Вопрос пользователя: {message}\n\n"
                f"Ответь кратко и по делу, как заботливая женщина-врач. "
                f"Твой ответ будет озвучен женским голосом, поэтому говори естественно, "
                f"используй женские окончания и интонации. Ты - женщина-медик."
            )
            
            # Отправляем запрос к Gemini
            response = self.model.generate_content(full_prompt)
            
            if response and response.text:
                ai_body = self._strip_leading_greeting(response.text)
                ai_response = ai_body + self._create_safety_disclaimer(message)
                
                # Генерируем голосовой ответ
                audio_content = await self._generate_speech_best_quality(ai_response)
                
                return {
                    'success': True,
                    'response': ai_response,
                    'type': 'text',
                    'audio_content': audio_content,
                    'has_voice': audio_content is not None
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
        """Обрабатывает аудио сообщение с полным циклом voice-to-voice"""
        try:
            logger.info(f"Начинаю обработку аудио сообщения от пользователя {user.email}")
            
            # 1. Пока распознавание речи недоступно (STT убран для упрощения)
            transcription = None
            
            if not transcription:
                # Информативное сообщение о голосовых функциях
                response_text = "Получила ваше голосовое сообщение! Пока распознавание речи на сервере недоступно, но я отвечу качественным женским голосом. Используйте кнопку микрофона в браузере для полного голосового общения."
                audio_content = await self._generate_speech_best_quality(response_text)
                
                return {
                    'success': True,
                    'response': response_text,
                    'type': 'voice_response',
                    'transcription': None,
                    'audio_content': audio_content,
                    'has_voice': audio_content is not None
                }
            
            logger.info(f"Распознанный текст: '{transcription}'")
            
            # 2. Обрабатываем распознанный текст как обычное текстовое сообщение
            text_result = await self.process_text_message(user, transcription)
            
            if text_result['success']:
                return {
                    'success': True,
                    'response': text_result['response'],
                    'type': 'voice_response',
                    'transcription': transcription,
                    'audio_content': text_result.get('audio_content'),
                    'has_voice': text_result.get('has_voice', False)
                }
            else:
                return text_result
                
        except Exception as e:
            logger.error(f"Ошибка при обработке аудио: {str(e)}")
            return {
                'success': False,
                'error': 'Произошла ошибка при обработке аудио'
            }
    
    def save_dialogue_message(self, user: User, content: str, sender_type: str, 
                            message_type: str = 'text', audio_file=None, 
                            transcription: str = None, audio_duration: float = None) -> AIMessage:
        """Сохраняет сообщение в диалоге с поддержкой аудио"""
        try:
            # Получаем или создаем активный диалог
            dialogue, created = AIDialogue.objects.get_or_create(
                user=user,
                is_active=True,
                defaults={'title': f'Голосовой диалог с AI от {user.first_name}'}
            )
            
            # Создаем сообщение
            message = AIMessage.objects.create(
                dialogue=dialogue,
                sender_type=sender_type,
                message_type=message_type,
                content=content,
                transcription=transcription,
                audio_duration=audio_duration
            )
            
            # Если есть аудиофайл, сохраняем его
            if audio_file:
                message.audio_file.save(
                    f'ai_message_{message.id}.mp3',
                    ContentFile(audio_file),
                    save=True
                )
            
            # Обновляем время последнего обновления диалога
            dialogue.save()
            
            return message
            
        except Exception as e:
            logger.error(f"Ошибка при сохранении сообщения: {str(e)}")
            raise

    def start_new_dialogue(self, user: User, title: Optional[str] = None) -> AIDialogue:
        """Создает новый диалог и деактивирует предыдущий активный"""
        # Деактивируем текущие активные диалоги пользователя
        AIDialogue.objects.filter(user=user, is_active=True).update(is_active=False)
        # Создаем новый
        dialogue = AIDialogue.objects.create(
            user=user,
            title=title or 'Новый диалог с AI',
            is_active=True,
        )
        return dialogue

    def close_dialogue(self, user: User, dialogue_id: int) -> bool:
        """Закрывает указанный диалог пользователя"""
        try:
            dialogue = AIDialogue.objects.get(id=dialogue_id, user=user)
            dialogue.is_active = False
            dialogue.save()
            return True
        except AIDialogue.DoesNotExist:
            return False

# Создаем экземпляр сервиса
ai_service = HealzyAIService()
