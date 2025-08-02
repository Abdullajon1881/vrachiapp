from django.core.management.base import BaseCommand
from authentication.models import User


class Command(BaseCommand):
    help = 'Verify existing users and set them as active'

    def handle(self, *args, **options):
        # Получаем всех пользователей
        users = User.objects.all()
        
        updated_count = 0
        
        for user in users:
            # Проверяем, нужно ли обновить пользователя
            needs_update = False
            
            # Если пользователь не верифицирован, верифицируем его
            if not user.is_verified:
                user.is_verified = True
                needs_update = True
                self.stdout.write(f"Верифицируем пользователя: {user.email}")
            
            # Если пользователь неактивен, активируем его
            if not user.is_active:
                user.is_active = True
                needs_update = True
                self.stdout.write(f"Активируем пользователя: {user.email}")
            
            # Если есть Google ID, считаем пользователя верифицированным
            if user.google_id and not user.is_verified:
                user.is_verified = True
                user.is_active = True
                needs_update = True
                self.stdout.write(f"Верифицируем Google пользователя: {user.email}")
            
            # Сохраняем изменения
            if needs_update:
                user.save()
                updated_count += 1
        
        self.stdout.write(
            self.style.SUCCESS(
                f'Успешно обновлено {updated_count} пользователей из {users.count()}'
            )
        ) 