from django.db import models
from django.contrib.auth.models import AbstractUser
from django.utils import timezone
from django.core.validators import FileExtensionValidator


class User(AbstractUser):
    """Расширенная модель пользователя"""
    ROLE_CHOICES = [
        ('patient', 'Пациент'),
        ('doctor', 'Врач'),
        ('admin', 'Администратор'),
    ]
    
    email = models.EmailField(unique=True)
    phone = models.CharField(max_length=20, blank=True, null=True)
    avatar = models.URLField(blank=True, null=True)
    google_id = models.CharField(max_length=100, blank=True, null=True, unique=True)
    is_verified = models.BooleanField(default=False)
    role = models.CharField(max_length=20, choices=ROLE_CHOICES, default='patient')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = ['username']

    def __str__(self):
        return self.email

    @property
    def full_name(self):
        return f"{self.first_name} {self.last_name}".strip() or self.username

    @property
    def initials(self):
        if self.first_name and self.last_name:
            return f"{self.first_name[0]}{self.last_name[0]}".upper()
        elif self.first_name:
            return self.first_name[0].upper()
        elif self.username:
            return self.username[0].upper()
        return "U"


class Region(models.Model):
    """Регионы Узбекистана"""
    REGION_TYPES = [
        ('region', 'Область'),
        ('city', 'Город республиканского подчинения'),
        ('republic', 'Республика'),
    ]
    
    name = models.CharField(max_length=100, unique=True)
    name_uz = models.CharField(max_length=100, blank=True, null=True)
    type = models.CharField(max_length=20, choices=REGION_TYPES, default='region')
    
    def __str__(self):
        return self.name
    
    class Meta:
        ordering = ['type', 'name']


class City(models.Model):
    """Города Узбекистана"""
    name = models.CharField(max_length=100)
    region = models.ForeignKey(Region, on_delete=models.CASCADE, related_name='cities')
    name_uz = models.CharField(max_length=100, blank=True, null=True)
    
    def __str__(self):
        return f"{self.name}, {self.region.name}"
    
    class Meta:
        ordering = ['name']
        unique_together = ['name', 'region']


class District(models.Model):
    """Районы Узбекистана"""
    name = models.CharField(max_length=100)
    region = models.ForeignKey(Region, on_delete=models.CASCADE, related_name='districts')
    name_uz = models.CharField(max_length=100, blank=True, null=True)
    
    def __str__(self):
        return f"{self.name}, {self.region.name}"
    
    class Meta:
        ordering = ['name']
        unique_together = ['name', 'region']


class UserProfile(models.Model):
    """Профиль пользователя"""
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='profile')
    date_of_birth = models.DateField(blank=True, null=True)
    gender = models.CharField(max_length=10, choices=[
        ('male', 'Мужской'),
        ('female', 'Женский'),
        ('other', 'Другой')
    ], blank=True, null=True)
    
    # Контактная информация
    phone = models.CharField(max_length=20, blank=True, null=True)
    
    # Адрес
    region = models.ForeignKey(Region, on_delete=models.SET_NULL, blank=True, null=True)
    city = models.ForeignKey(City, on_delete=models.SET_NULL, blank=True, null=True)
    district = models.ForeignKey(District, on_delete=models.SET_NULL, blank=True, null=True)
    address = models.TextField(blank=True, null=True)
    
    # Медицинская информация
    medical_info = models.TextField(blank=True, null=True, help_text="Информация о заболеваниях, аллергиях и т.д.")
    emergency_contact = models.CharField(max_length=20, blank=True, null=True)
    
    # Поля врача (заполняются автоматически при одобрении заявки)
    specialization = models.CharField(max_length=255, blank=True, null=True)
    experience = models.TextField(blank=True, null=True)
    education = models.TextField(blank=True, null=True)
    license_number = models.CharField(max_length=100, blank=True, null=True)
    languages = models.JSONField(default=list, blank=True)
    additional_info = models.TextField(blank=True, null=True)
    
    # Дополнительная информация
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    def __str__(self):
        return f"Профиль {self.user.email}"


class DoctorApplication(models.Model):
    STATUS_CHOICES = [
        ('pending', 'На рассмотрении'),
        ('approved', 'Одобрена'),
        ('rejected', 'Отклонена'),
    ]
    
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='doctor_applications')
    first_name = models.CharField(max_length=100, default='')
    last_name = models.CharField(max_length=100, default='')
    specialization = models.CharField(max_length=100)
    region = models.ForeignKey(Region, on_delete=models.CASCADE, null=True, blank=True)
    city = models.ForeignKey(City, on_delete=models.CASCADE, null=True, blank=True)
    district = models.ForeignKey(District, on_delete=models.CASCADE, null=True, blank=True)
    languages = models.JSONField(default=list)
    experience = models.TextField()
    education = models.TextField()
    license_number = models.CharField(max_length=100)
    additional_info = models.TextField(blank=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    # Поля профиля
    date_of_birth = models.DateField(null=True, blank=True)
    gender = models.CharField(max_length=10, choices=[('male', 'Мужской'), ('female', 'Женский')], null=True, blank=True)
    phone = models.CharField(max_length=20, blank=True, default='')
    address = models.TextField(blank=True, default='')
    medical_info = models.TextField(blank=True, default='')
    emergency_contact = models.CharField(max_length=100, blank=True, default='')
    
    # Файлы
    photo = models.FileField(upload_to='doctor_applications/photos/', null=True, blank=True)
    diploma = models.FileField(upload_to='doctor_applications/diplomas/', null=True, blank=True)
    license = models.FileField(upload_to='doctor_applications/licenses/', null=True, blank=True)
    
    # Статус и метаданные
    rejection_reason = models.TextField(blank=True)
    reviewed_by = models.ForeignKey(
        User, 
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True, 
        related_name='reviewed_applications'
    )
    reviewed_at = models.DateTimeField(null=True, blank=True)
    
    class Meta:
        ordering = ['-created_at']
        verbose_name = 'Заявка на роль врача'
        verbose_name_plural = 'Заявки на роль врача'
    
    def __str__(self):
        return f"Заявка от {self.first_name} {self.last_name} - {self.get_status_display()}" 