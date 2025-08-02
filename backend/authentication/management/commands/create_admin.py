from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
from authentication.models import UserProfile

User = get_user_model()

class Command(BaseCommand):
    help = 'Создает администратора с указанными данными'

    def add_arguments(self, parser):
        parser.add_argument('--email', type=str, required=True, help='Email администратора')
        parser.add_argument('--password', type=str, required=True, help='Пароль администратора')
        parser.add_argument('--first-name', type=str, default='', help='Имя администратора')
        parser.add_argument('--last-name', type=str, default='', help='Фамилия администратора')
        parser.add_argument('--username', type=str, default='', help='Имя пользователя (опционально)')

    def handle(self, *args, **options):
        email = options['email']
        password = options['password']
        first_name = options['first_name']
        last_name = options['last_name']
        username = options['username'] or email.split('@')[0]

        # Проверяем, существует ли пользователь
        if User.objects.filter(email=email).exists():
            self.stdout.write(
                self.style.WARNING(f'Пользователь с email {email} уже существует')
            )
            return

        # Создаем пользователя
        user = User.objects.create_user(
            username=username,
            email=email,
            password=password,
            first_name=first_name,
            last_name=last_name,
            role='admin',
            is_staff=True,
            is_superuser=True,
            is_verified=True,
            is_active=True
        )

        # Создаем профиль пользователя
        UserProfile.objects.create(user=user)

        self.stdout.write(
            self.style.SUCCESS(
                f'Администратор успешно создан:\n'
                f'Email: {email}\n'
                f'Имя: {first_name} {last_name}\n'
                f'Роль: {user.role}\n'
                f'Staff: {user.is_staff}\n'
                f'Superuser: {user.is_superuser}'
            )
        ) 