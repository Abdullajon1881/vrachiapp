import os
import logging
import tempfile
import requests
from typing import Optional, Dict, Any, List

import anthropic
from django.core.files.storage import default_storage
from django.core.files.base import ContentFile
from .models import AIDialogue, AIMessage, User

logger = logging.getLogger(__name__)

ANTHROPIC_API_KEY = "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"
client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)
MODEL = "claude-sonnet-4-20250514"


class HealzyAIService:
    """Healzy AI — медицинская помощница на базе Claude Sonnet 4"""

    def __init__(self):
        self.max_history_messages = 10

        self.system_prompt = """Ты — Healzy AI, опытная женщина-врач и медицинская помощница.

ТВОЯ ЛИЧНОСТЬ:
- Тёплая, внимательная, профессиональная
- Говоришь на русском языке, о себе — в женском роде
- Не начинаешь ответ с приветствия — сразу по делу
- Никогда не говоришь "как ИИ я не могу..." — ты врач

СПЕЦИАЛИЗАЦИИ (знаешь всё):
🫀 Кардиология — сердце, давление, сосуды
🧠 Неврология — головная боль, головокружение, сон
🫁 Пульмонология — кашель, дыхание, бронхи
🦷 Стоматология — зубы, дёсны, полость рта
🍽️ Гастроэнтерология — желудок, кишечник, печень
🦴 Ортопедия — суставы, позвоночник, мышцы
🧴 Дерматология — кожа, сыпь, аллергия
👁️ Офтальмология — глаза, зрение
👂 ЛОР — уши, нос, горло
🤰 Гинекология — женское здоровье
👶 Педиатрия — здоровье детей
🧪 Общая терапия — общие симптомы, ОРВИ, грипп

КАК ОТВЕЧАТЬ:
✅ Анализируй симптомы внимательно и детально
✅ Объясняй возможные причины (дифференциальный анализ)
✅ Давай конкретные практические советы
✅ Рекомендуй домашнее лечение когда уместно
✅ Указывай когда нужно срочно к врачу
✅ Используй контекст предыдущих сообщений
✅ Задавай уточняющие вопросы если нужно больше информации
✅ Структурируй длинные ответы (причины / симптомы / лечение)

УРОВНИ СРОЧНОСТИ:
🟢 Не срочно — можно лечить дома, наблюдать
🟡 Умеренно — записаться к врачу в ближайшие дни
🔴 Срочно — нужен врач сегодня или скорая помощь

ЗАПРЕЩЕНО:
❌ Ставить точный диагноз (только вероятные причины)
❌ Назначать конкретные дозы лекарств
❌ Отвечать на немедицинские вопросы
❌ Говорить о себе в мужском роде
❌ Добавлять одинаковые предупреждения к каждому ответу"""

    def _get_conversation_history(self, user: User) -> List[Dict]:
        """Получает историю последних сообщений диалога"""
        try:
            dialogue = AIDialogue.objects.filter(
                user=user, is_active=True
            ).first()
            if not dialogue:
                return []

            messages = AIMessage.objects.filter(
                dialogue=dialogue
            ).order_by('-timestamp')[:self.max_history_messages]

            history = []
            for msg in reversed(messages):
                role = 'user' if msg.sender_type == 'user' else 'assistant'
                content = msg.transcription or msg.content
                if content:
                    history.append({'role': role, 'content': content})
            return history
        except Exception as e:
            logger.error(f"Ошибка получения истории: {e}")
            return []

    def _detect_urgency(self, message: str) -> Optional[str]:
        message_lower = message.lower()
        emergency_keywords = [
            'боль в груди', 'не могу дышать', 'потеря сознания', 'упал в обморок',
            'инсульт', 'инфаркт', 'судороги', 'рвота с кровью', 'кровотечение',
            'сильная аллергия', 'отёк горла', 'не могу говорить', 'парализовало'
        ]
        urgent_keywords = [
            'высокая температура', 'сильная боль', 'не проходит', 'ухудшается',
            'несколько дней', 'кровь в моче', 'желтуха', 'сильное головокружение'
        ]
        for kw in emergency_keywords:
            if kw in message_lower:
                return 'emergency'
        for kw in urgent_keywords:
            if kw in message_lower:
                return 'urgent'
        return None

    def _suggest_specialist(self, message: str) -> Optional[str]:
        message_lower = message.lower()
        specialists = {
            'кардиолог': ['сердце', 'давление', 'пульс', 'аритмия', 'боль в груди'],
            'невролог': ['голова болит', 'головная боль', 'мигрень', 'головокружение', 'онемение'],
            'гастроэнтеролог': ['желудок', 'живот болит', 'тошнота', 'изжога', 'понос', 'запор'],
            'дерматолог': ['сыпь', 'зуд', 'кожа', 'прыщи', 'покраснение'],
            'ортопед': ['сустав', 'колено', 'спина болит', 'позвоночник', 'перелом'],
            'пульмонолог': ['кашель', 'дыхание', 'астма', 'бронхит', 'одышка'],
            'лор': ['горло', 'нос', 'уши', 'насморк', 'ухо болит', 'гайморит'],
            'офтальмолог': ['глаза', 'зрение', 'глаз болит', 'покраснение глаз'],
            'эндокринолог': ['щитовидка', 'диабет', 'сахар', 'гормоны'],
            'уролог': ['почки', 'мочевой', 'боль при мочеиспускании', 'моча'],
        }
        for specialist, keywords in specialists.items():
            for kw in keywords:
                if kw in message_lower:
                    return specialist
        return None

    def _is_greeting(self, text: str) -> bool:
        text_lower = text.strip().lower()
        if len(text_lower) > 40:
            return False
        greeting_keywords = [
            'привет', 'здравствуй', 'здравствуйте', 'добрый день',
            'добрый вечер', 'доброе утро', 'как дела', 'hi', 'hello'
        ]
        return any(kw in text_lower for kw in greeting_keywords)

    def _is_medical_question(self, text: str) -> bool:
        """Быстрая проверка на медицинскую тему по ключевым словам"""
        non_medical_keywords = [
            'политика', 'экономика', 'бизнес', 'финансы', 'акции', 'криптовалюта',
            'спорт', 'футбол', 'кино', 'музыка', 'игры', 'программирование',
            'история', 'география', 'математика', 'физика', 'химия',
            'кулинария', 'рецепт', 'готовить', 'путешествия', 'туризм'
        ]
        text_lower = text.lower()
        for kw in non_medical_keywords:
            if kw in text_lower:
                return False
        return True

    def _add_urgency_note(self, message: str, ai_response: str) -> str:
        urgency = self._detect_urgency(message)
        if urgency == 'emergency':
            if '🔴' not in ai_response and 'скорую' not in ai_response.lower():
                return ai_response + "\n\n🔴 **Срочно вызовите скорую помощь (103)!**"
        return ai_response

    def _call_claude(self, messages: List[Dict], max_tokens: int = 1024) -> Optional[str]:
        """Вызывает Claude API синхронно"""
        try:
            response = client.messages.create(
                model=MODEL,
                max_tokens=max_tokens,
                system=self.system_prompt,
                messages=messages,
            )
            return response.content[0].text
        except Exception as e:
            logger.error(f"Ошибка Claude API: {e}")
            return None

    async def _generate_speech_with_edge_tts(self, text: str) -> Optional[bytes]:
        try:
            import edge_tts
            clean_text = text.strip()[:1000]
            female_voices = [
                "ru-RU-SvetlanaNeural",
                "ru-RU-DariyaNeural",
                "ru-RU-PolarisNeural"
            ]
            for voice in female_voices:
                try:
                    with tempfile.NamedTemporaryFile(suffix='.mp3', delete=False) as tmp:
                        tmp_path = tmp.name
                    communicate = edge_tts.Communicate(clean_text, voice)
                    await communicate.save(tmp_path)
                    with open(tmp_path, 'rb') as f:
                        audio_content = f.read()
                    os.unlink(tmp_path)
                    if len(audio_content) > 1000:
                        return audio_content
                except Exception:
                    continue
            return None
        except ImportError:
            return None
        except Exception as e:
            logger.error(f"Edge TTS error: {e}")
            return None

    async def _generate_speech_with_google_tts(self, text: str) -> Optional[bytes]:
        try:
            import urllib.parse
            clean_text = text.strip()[:1000]
            encoded = urllib.parse.quote(clean_text)
            url = f"https://translate.google.com/translate_tts?ie=UTF-8&tl=ru&client=tw-ob&q={encoded}"
            headers = {"User-Agent": "Mozilla/5.0"}
            response = requests.get(url, headers=headers, timeout=15)
            if response.status_code == 200 and len(response.content) > 1000:
                return response.content
            return None
        except Exception as e:
            logger.error(f"Google TTS error: {e}")
            return None

    async def _generate_speech_best_quality(self, text: str) -> Optional[bytes]:
        audio = await self._generate_speech_with_edge_tts(text)
        if audio:
            return audio
        audio = await self._generate_speech_with_google_tts(text)
        if audio:
            return audio
        return None

    async def process_text_message(self, user: User, message: str) -> Dict[str, Any]:
        """Обрабатывает текстовое сообщение через Claude"""
        try:
            # Handle greetings
            if self._is_greeting(message):
                history = self._get_conversation_history(user)
                if history:
                    response_text = 'Снова привет! Чем могу помочь со здоровьем?'
                else:
                    response_text = 'Привет! Я Healzy — ваша медицинская помощница на базе Claude AI. Расскажите, что вас беспокоит?'
                audio = await self._generate_speech_best_quality(response_text)
                return {
                    'success': True, 'response': response_text,
                    'type': 'text', 'audio_content': audio,
                    'has_voice': audio is not None
                }

            # Check if medical
            if not self._is_medical_question(message):
                response_text = (
                    "Я специализируюсь только на медицинских вопросах. "
                    "Расскажите о ваших симптомах или задайте вопрос о здоровье."
                )
                audio = await self._generate_speech_best_quality(response_text)
                return {
                    'success': True, 'response': response_text,
                    'type': 'text', 'audio_content': audio,
                    'has_voice': audio is not None
                }

            # Build messages with conversation history
            history = self._get_conversation_history(user)
            messages = []

            # Add history
            for h in history:
                messages.append({'role': h['role'], 'content': h['content']})

            # Add current message
            messages.append({'role': 'user', 'content': message})

            # Call Claude
            ai_response = self._call_claude(messages)

            if ai_response:
                ai_response = self._add_urgency_note(message, ai_response)

                # Add specialist suggestion if not already mentioned
                specialist = self._suggest_specialist(message)
                if specialist and specialist not in ai_response.lower():
                    ai_response += f"\n\n💡 По этим симптомам рекомендую обратиться к **{specialist}у**."

                audio = await self._generate_speech_best_quality(ai_response)
                return {
                    'success': True, 'response': ai_response,
                    'type': 'text', 'audio_content': audio,
                    'has_voice': audio is not None,
                    'specialist_suggestion': specialist,
                }
            else:
                return {'success': False, 'error': 'Не удалось получить ответ от AI'}

        except Exception as e:
            logger.error(f"Ошибка обработки текста: {e}")
            return {'success': False, 'error': 'Ошибка при обработке сообщения'}

    async def process_image_message(self, user: User, image_file) -> Dict[str, Any]:
        """Обрабатывает изображение через Claude Vision"""
        try:
            import base64
            file_path = default_storage.save(f'temp/ai_images/{image_file.name}', image_file)

            with default_storage.open(file_path, 'rb') as f:
                image_data = base64.standard_b64encode(f.read()).decode('utf-8')

            default_storage.delete(file_path)

            # Get history for context
            history = self._get_conversation_history(user)
            messages = []
            for h in history[-4:]:
                messages.append({'role': h['role'], 'content': h['content']})

            # Add image message
            messages.append({
                'role': 'user',
                'content': [
                    {
                        'type': 'image',
                        'source': {
                            'type': 'base64',
                            'media_type': image_file.content_type,
                            'data': image_data,
                        }
                    },
                    {
                        'type': 'text',
                        'text': (
                            'Пациент прислал изображение для медицинского анализа. '
                            'Опиши что видишь, дай медицинскую оценку, '
                            'укажи возможные причины и рекомендации. '
                            'Скажи нужен ли врач (🟢/🟡/🔴).'
                        )
                    }
                ]
            })

            ai_response = self._call_claude(messages, max_tokens=1500)

            if ai_response:
                return {'success': True, 'response': ai_response, 'type': 'image'}
            return {'success': False, 'error': 'Не удалось проанализировать изображение'}

        except Exception as e:
            logger.error(f"Ошибка обработки изображения: {e}")
            return {'success': False, 'error': 'Ошибка при анализе изображения'}

    async def process_audio_message(self, user: User, audio_file) -> Dict[str, Any]:
        """Обрабатывает аудио сообщение"""
        try:
            response_text = (
                "Получила ваше голосовое сообщение! "
                "Распознавание речи на сервере пока недоступно. "
                "Используйте текстовый ввод или микрофон браузера для полного голосового общения."
            )
            audio = await self._generate_speech_best_quality(response_text)
            return {
                'success': True, 'response': response_text,
                'type': 'voice_response', 'transcription': None,
                'audio_content': audio, 'has_voice': audio is not None
            }
        except Exception as e:
            logger.error(f"Ошибка обработки аудио: {e}")
            return {'success': False, 'error': 'Ошибка при обработке аудио'}

    def save_dialogue_message(self, user: User, content: str, sender_type: str,
                              message_type: str = 'text', audio_file=None,
                              transcription: str = None,
                              audio_duration: float = None) -> AIMessage:
        """Сохраняет сообщение в диалоге"""
        try:
            dialogue, created = AIDialogue.objects.get_or_create(
                user=user, is_active=True,
                defaults={'title': f'Диалог с AI — {user.first_name or user.email}'}
            )
            message = AIMessage.objects.create(
                dialogue=dialogue,
                sender_type=sender_type,
                message_type=message_type,
                content=content,
                transcription=transcription,
                audio_duration=audio_duration
            )
            if audio_file:
                message.audio_file.save(
                    f'ai_message_{message.id}.mp3',
                    ContentFile(audio_file),
                    save=True
                )
            dialogue.save()
            return message
        except Exception as e:
            logger.error(f"Ошибка сохранения сообщения: {e}")
            raise

    def start_new_dialogue(self, user: User, title: Optional[str] = None) -> AIDialogue:
        """Создает новый диалог"""
        AIDialogue.objects.filter(user=user, is_active=True).update(is_active=False)
        return AIDialogue.objects.create(
            user=user,
            title=title or 'Новый диалог с AI',
            is_active=True,
        )

    def close_dialogue(self, user: User, dialogue_id: int) -> bool:
        """Закрывает диалог"""
        try:
            dialogue = AIDialogue.objects.get(id=dialogue_id, user=user)
            dialogue.is_active = False
            dialogue.save()
            return True
        except AIDialogue.DoesNotExist:
            return False
        except Exception as e:
            logger.error(f"Ошибка закрытия диалога: {e}")
            return False


ai_service = HealzyAIService()
