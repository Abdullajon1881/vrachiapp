from django.db import migrations


def verify_existing_users(apps, schema_editor):
    """Верифицируем существующих пользователей"""
    User = apps.get_model('authentication', 'User')
    
    # Получаем всех пользователей
    users = User.objects.all()
    
    for user in users:
        # Если пользователь не верифицирован, верифицируем его
        if not user.is_verified:
            user.is_verified = True
            user.is_active = True
            user.save()
        
        # Если есть Google ID, считаем пользователя верифицированным
        if user.google_id and not user.is_verified:
            user.is_verified = True
            user.is_active = True
            user.save()


def reverse_verify_existing_users(apps, schema_editor):
    """Откат верификации (не используется)"""
    pass


class Migration(migrations.Migration):

    dependencies = [
        ('authentication', '0010_alter_user_username'),
    ]

    operations = [
        migrations.RunPython(verify_existing_users, reverse_verify_existing_users),
    ] 