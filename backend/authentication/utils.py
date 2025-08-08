import uuid
from datetime import timedelta
from django.utils import timezone
from django.core.mail import send_mail
from django.template.loader import render_to_string
from django.conf import settings
from .models import User


def generate_verification_token():
    """Генерирует уникальный токен для верификации email"""
    return uuid.uuid4()


def send_verification_email(user, verification_url):
    """Отправляет email с ссылкой для подтверждения"""
    subject = 'Подтверждение регистрации - VrachiApp'
    
    # Заменяем API URL на HTML URL
    html_verification_url = verification_url.replace('/api/auth/verify-email/', '/api/auth/verify-email-html/')
    
    # HTML шаблон для email
    html_message = render_to_string('authentication/email_verification.html', {
        'user': user,
        'verification_url': html_verification_url,
        'expires_in': '24 часа'
    })
    
    # Текстовый шаблон для email
    text_message = f"""
    Здравствуйте, {user.first_name or user.username}!
    
    Спасибо за регистрацию в VrachiApp!
    
    Для завершения регистрации, пожалуйста, подтвердите ваш email, перейдя по ссылке:
    {html_verification_url}
    
    Ссылка действительна в течение 10 минут.
    
    Если вы не регистрировались в VrachiApp, просто проигнорируйте это письмо.
    
    С уважением,
    Команда VrachiApp
    """
    
    try:
        send_mail(
            subject=subject,
            message=text_message,
            from_email=settings.EMAIL_FROM,
            recipient_list=[user.email],
            html_message=html_message,
            fail_silently=False,
        )
        return True
    except Exception as e:
        print(f"Ошибка отправки email: {e}")
        return False


def is_verification_token_expired(user):
    """Проверяет, истек ли токен верификации (увеличено до 24 часов)"""
    if not user.email_verification_sent_at:
        return True
    
    expiration_time = user.email_verification_sent_at + timedelta(hours=24)
    return timezone.now() > expiration_time


def verify_email_token(token):
    """Проверяет токен верификации и активирует пользователя"""
    try:
        user = User.objects.get(email_verification_token=token)
        
        # Проверяем, не истек ли токен
        if is_verification_token_expired(user):
            return None
        
        # Активируем пользователя
        user.is_verified = True
        user.is_active = True
        user.email_verification_token = None
        user.email_verification_sent_at = None
        user.save()
        
        return user
        
    except User.DoesNotExist:
        return None
    except Exception as e:
        return None


def create_user_with_verification(email, password, first_name, last_name, role='patient'):
    """Создает пользователя с отправкой email для верификации"""
    from .models import User
    
    # Проверяем, существует ли уже пользователь с таким email
    existing_user = User.objects.filter(email=email).first()
    if existing_user:
        # Если пользователь уже существует, возвращаем его
        return existing_user
    
    # Генерируем уникальный username на основе email
    base_username = email.split('@')[0]
    username = base_username
    counter = 1
    
    # Проверяем уникальность username
    while User.objects.filter(username=username).exists():
        username = f"{base_username}{counter}"
        counter += 1
    
    # Создаем пользователя (неактивного)
    user = User.objects.create_user(
        username=username,
        email=email,
        password=password,
        first_name=first_name,
        last_name=last_name,
        role=role,
        is_active=False,  # Неактивен до подтверждения
        is_verified=False
    )
    
    # Генерируем токен верификации
    user.email_verification_token = generate_verification_token()
    user.email_verification_sent_at = timezone.now()
    user.save()
    
    return user


def create_google_user(google_user_info):
    """Создает пользователя через Google OAuth (автоматически подтвержденного)"""
    from .models import User, UserProfile
    
    # Извлекаем данные из Google OAuth
    email = google_user_info.get('email')
    first_name = google_user_info.get('given_name', '')
    last_name = google_user_info.get('family_name', '')
    google_id = google_user_info.get('id')
    avatar = google_user_info.get('picture')
    
    if not email:
        raise ValueError("Email обязателен для создания пользователя через Google")
    
    # Проверяем, существует ли уже пользователь с таким email
    existing_user = User.objects.filter(email=email).first()
    if existing_user:
        # Если пользователь уже существует, обновляем Google ID и возвращаем его
        if not existing_user.google_id:
            existing_user.google_id = google_id
            existing_user.is_verified = True
            existing_user.is_active = True
            if avatar:
                existing_user.avatar = avatar
            existing_user.save()
        return existing_user
    
    # Генерируем уникальный username на основе email
    base_username = email.split('@')[0]
    username = base_username
    counter = 1
    
    # Проверяем уникальность username
    while User.objects.filter(username=username).exists():
        username = f"{base_username}{counter}"
        counter += 1
    
    # Создаем пользователя (активного и подтвержденного)
    user = User.objects.create_user(
        username=username,
        email=email,
        first_name=first_name,
        last_name=last_name,
        google_id=google_id,
        avatar=avatar,
        is_active=True,  # Активен сразу
        is_verified=True,  # Подтвержден сразу
        role='patient'
    )
    
    # Создаем профиль пользователя
    UserProfile.objects.create(user=user)
    
    return user 