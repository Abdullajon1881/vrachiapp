from django.db import models
from django.contrib.auth.models import AbstractUser
from django.utils import timezone
from django.core.validators import FileExtensionValidator
import uuid
from datetime import timedelta


class User(AbstractUser):
    """Расширенная модель пользователя"""
    ROLE_CHOICES = [
        ('patient', 'Пациент'),
        ('doctor', 'Врач'),
        ('admin', 'Администратор'),
    ]
    
    # Переопределяем username для уникальности
    username = models.CharField(max_length=150, unique=True, blank=True, null=True)
    email = models.EmailField(unique=True)
    phone = models.CharField(max_length=20, blank=True, null=True)
    avatar = models.URLField(blank=True, null=True)
    google_id = models.CharField(max_length=100, blank=True, null=True, unique=True)
    is_verified = models.BooleanField(default=False)
    role = models.CharField(max_length=20, choices=ROLE_CHOICES, default='patient')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    # Поля для email верификации
    email_verification_token = models.UUIDField(blank=True, null=True)
    email_verification_sent_at = models.DateTimeField(blank=True, null=True)
    is_active = models.BooleanField(default=False)  # Пользователь неактивен до подтверждения email

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
    city = models.ForeignKey(City, on_delete=models.CASCADE, related_name='districts', null=True, blank=True)
    name_uz = models.CharField(max_length=100, blank=True, null=True)
    
    def __str__(self):
        if self.city:
            return f"{self.name}, {self.city.name}"
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


class Consultation(models.Model):
    """Модель консультации между пациентом и врачом"""
    STATUS_CHOICES = [
        ('pending', 'Ожидание'),
        ('active', 'Активна'),
        ('completed', 'Завершена'),
        ('cancelled', 'Отменена'),
    ]
    
    patient = models.ForeignKey(User, on_delete=models.CASCADE, related_name='patient_consultations')
    doctor = models.ForeignKey(User, on_delete=models.CASCADE, related_name='doctor_consultations')
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    title = models.CharField(max_length=255, blank=True, null=True)
    description = models.TextField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    started_at = models.DateTimeField(null=True, blank=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    
    class Meta:
        ordering = ['-created_at']
        verbose_name = 'Консультация'
        verbose_name_plural = 'Консультации'
    
    def __str__(self):
        return f"Консультация {self.patient.full_name} - {self.doctor.full_name} ({self.get_status_display()})"
    
    @property
    def is_active(self):
        return self.status == 'active'
    
    @property
    def can_patient_write(self):
        return self.status == 'active'
    
    @property
    def can_doctor_write(self):
        return self.status == 'active'


class Message(models.Model):
    """Модель сообщения в чате консультации"""
    consultation = models.ForeignKey(Consultation, on_delete=models.CASCADE, related_name='messages')
    sender = models.ForeignKey(User, on_delete=models.CASCADE, related_name='sent_messages')
    content = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)
    is_read = models.BooleanField(default=False)
    read_at = models.DateTimeField(null=True, blank=True)
    
    class Meta:
        ordering = ['created_at']
        verbose_name = 'Сообщение'
        verbose_name_plural = 'Сообщения'
    
    def __str__(self):
        return f"Сообщение от {self.sender.full_name} в {self.consultation}"
    
    def mark_as_read(self):
        if not self.is_read:
            self.is_read = True
            self.read_at = timezone.now()
            self.save()


class AIDialogue(models.Model):
    """Модель для хранения диалогов с AI"""
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='ai_dialogues')
    title = models.CharField(max_length=200, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ['-updated_at']
        verbose_name = 'AI диалог'
        verbose_name_plural = 'AI диалоги'

    def __str__(self):
        return f"AI Dialogue {self.id} - {self.user.full_name}"

    def save(self, *args, **kwargs):
        # Автоматически создаем заголовок из первого сообщения
        if not self.title and not self.pk:
            self.title = f"Диалог от {self.created_at.strftime('%d.%m.%Y %H:%M')}"
        super().save(*args, **kwargs)


class AIMessage(models.Model):
    """Модель для хранения сообщений в AI диалоге"""
    MESSAGE_TYPES = [
        ('text', 'Текст'),
        ('image', 'Изображение'),
        ('video', 'Видео'),
        ('audio', 'Аудио'),
        ('voice_response', 'Голосовой ответ'),
    ]
    
    SENDER_TYPES = [
        ('user', 'Пользователь'),
        ('ai', 'AI'),
    ]

    dialogue = models.ForeignKey(AIDialogue, on_delete=models.CASCADE, related_name='messages')
    sender_type = models.CharField(max_length=10, choices=SENDER_TYPES)
    message_type = models.CharField(max_length=15, choices=MESSAGE_TYPES, default='text')
    content = models.TextField()
    file_path = models.CharField(max_length=500, blank=True, null=True)  # Для медиафайлов
    audio_file = models.FileField(upload_to='ai_messages/audio/', blank=True, null=True)  # Аудиофайлы
    audio_duration = models.FloatField(blank=True, null=True)  # Длительность аудио в секундах
    transcription = models.TextField(blank=True, null=True)  # Расшифровка аудио
    metadata = models.JSONField(default=dict, blank=True)  # Дополнительные данные
    timestamp = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['timestamp']
        verbose_name = 'AI сообщение'
        verbose_name_plural = 'AI сообщения'

    def __str__(self):
        return f"{self.get_sender_type_display()} сообщение в диалоге {self.dialogue.id}"
    
class Appointment(models.Model):
    """Appointment booking between patient and doctor"""
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('confirmed', 'Confirmed'),
        ('cancelled', 'Cancelled'),
        ('completed', 'Completed'),
        ('no_show', 'No Show'),
    ]

    patient = models.ForeignKey(User, on_delete=models.CASCADE, related_name='patient_appointments')
    doctor = models.ForeignKey(User, on_delete=models.CASCADE, related_name='doctor_appointments')
    appointment_date = models.DateField()
    appointment_time = models.TimeField()
    duration_minutes = models.IntegerField(default=30)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    reason = models.TextField(blank=True, null=True)
    notes = models.TextField(blank=True, null=True)
    doctor_notes = models.TextField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    cancelled_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='cancelled_appointments')
    cancellation_reason = models.TextField(blank=True, null=True)

    class Meta:
        ordering = ['appointment_date', 'appointment_time']
        verbose_name = 'Appointment'
        verbose_name_plural = 'Appointments'
        unique_together = ['doctor', 'appointment_date', 'appointment_time']

    def __str__(self):
        return f"Appointment: {self.patient.full_name} with Dr. {self.doctor.full_name} on {self.appointment_date} at {self.appointment_time}"

    @property
    def is_upcoming(self):
        from datetime import date
        today = date.today()
        now_time = timezone.now().time()
        if self.appointment_date > today:
            return True
        if self.appointment_date == today and self.appointment_time > now_time:
            return True
        return False


class DoctorSchedule(models.Model):
    """Doctor's weekly availability schedule"""
    DAY_CHOICES = [
        (0, 'Monday'), (1, 'Tuesday'), (2, 'Wednesday'),
        (3, 'Thursday'), (4, 'Friday'), (5, 'Saturday'), (6, 'Sunday'),
    ]

    doctor = models.ForeignKey(User, on_delete=models.CASCADE, related_name='schedules')
    day_of_week = models.IntegerField(choices=DAY_CHOICES)
    start_time = models.TimeField()
    end_time = models.TimeField()
    is_available = models.BooleanField(default=True)
    slot_duration_minutes = models.IntegerField(default=30)

    class Meta:
        ordering = ['day_of_week', 'start_time']
        verbose_name = 'Doctor Schedule'
        verbose_name_plural = 'Doctor Schedules'
        unique_together = ['doctor', 'day_of_week']

    def __str__(self):
        return f"Dr. {self.doctor.full_name} - {self.get_day_of_week_display()} {self.start_time}-{self.end_time}"


class MedicalRecord(models.Model):
    """Patient medical record created by a doctor"""
    RECORD_TYPES = [
        ('diagnosis', 'Diagnosis'),
        ('prescription', 'Prescription'),
        ('lab_result', 'Lab Result'),
        ('imaging', 'Imaging / X-Ray'),
        ('vaccination', 'Vaccination'),
        ('allergy', 'Allergy'),
        ('surgery', 'Surgery'),
        ('note', 'General Note'),
    ]

    patient = models.ForeignKey(User, on_delete=models.CASCADE, related_name='medical_records')
    doctor = models.ForeignKey(User, on_delete=models.CASCADE, related_name='created_records')
    consultation = models.ForeignKey(Consultation, on_delete=models.SET_NULL, null=True, blank=True, related_name='medical_records')
    appointment = models.ForeignKey(Appointment, on_delete=models.SET_NULL, null=True, blank=True, related_name='medical_records')
    record_type = models.CharField(max_length=20, choices=RECORD_TYPES, default='note')
    title = models.CharField(max_length=255)
    description = models.TextField()
    diagnosis_code = models.CharField(max_length=20, blank=True, null=True)
    medications = models.JSONField(default=list, blank=True)
    attachments = models.JSONField(default=list, blank=True)
    is_visible_to_patient = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']
        verbose_name = 'Medical Record'
        verbose_name_plural = 'Medical Records'

    def __str__(self):
        return f"{self.get_record_type_display()} - {self.patient.full_name} by Dr. {self.doctor.full_name}"


class Prescription(models.Model):
    """Prescription linked to a medical record"""
    STATUS_CHOICES = [
        ('active', 'Active'),
        ('completed', 'Completed'),
        ('cancelled', 'Cancelled'),
    ]

    medical_record = models.ForeignKey(MedicalRecord, on_delete=models.CASCADE, related_name='prescriptions')
    patient = models.ForeignKey(User, on_delete=models.CASCADE, related_name='prescriptions')
    doctor = models.ForeignKey(User, on_delete=models.CASCADE, related_name='issued_prescriptions')
    medication_name = models.CharField(max_length=255)
    dosage = models.CharField(max_length=100)
    frequency = models.CharField(max_length=100)
    duration_days = models.IntegerField(blank=True, null=True)
    instructions = models.TextField(blank=True, null=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='active')
    prescribed_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateField(blank=True, null=True)

    class Meta:
        ordering = ['-prescribed_at']
        verbose_name = 'Prescription'
        verbose_name_plural = 'Prescriptions'

    def __str__(self):
        return f"{self.medication_name} for {self.patient.full_name}"


class VitalSigns(models.Model):
    """Patient vital signs log"""
    patient = models.ForeignKey(User, on_delete=models.CASCADE, related_name='vital_signs')
    recorded_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='recorded_vitals')
    blood_pressure_systolic = models.IntegerField(blank=True, null=True)
    blood_pressure_diastolic = models.IntegerField(blank=True, null=True)
    heart_rate = models.IntegerField(blank=True, null=True)
    temperature = models.DecimalField(max_digits=4, decimal_places=1, blank=True, null=True)
    weight_kg = models.DecimalField(max_digits=5, decimal_places=1, blank=True, null=True)
    height_cm = models.DecimalField(max_digits=5, decimal_places=1, blank=True, null=True)
    oxygen_saturation = models.IntegerField(blank=True, null=True)
    notes = models.TextField(blank=True, null=True)
    recorded_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-recorded_at']
        verbose_name = 'Vital Signs'
        verbose_name_plural = 'Vital Signs'

    def __str__(self):
        return f"Vitals for {self.patient.full_name} at {self.recorded_at}"

    @property
    def bmi(self):
        if self.weight_kg and self.height_cm and self.height_cm > 0:
            height_m = float(self.height_cm) / 100
            return round(float(self.weight_kg) / (height_m ** 2), 1)
        return None

class Notification(models.Model):
    """In-app notification system"""
    NOTIFICATION_TYPES = [
        ('appointment_booked', 'Appointment Booked'),
        ('appointment_confirmed', 'Appointment Confirmed'),
        ('appointment_cancelled', 'Appointment Cancelled'),
        ('appointment_reminder', 'Appointment Reminder'),
        ('new_message', 'New Message'),
        ('consultation_started', 'Consultation Started'),
        ('consultation_completed', 'Consultation completed'),
        ('medical_record_added', 'Medical Record Added'),
        ('prescription_issued', 'Prescription Issued'),
        ('doctor_approved', 'Doctor Application Approved'),
        ('doctor_rejected', 'Doctor Application Rejected'),
        ('general', 'General'),
    ]

    recipient = models.ForeignKey(
        User, on_delete=models.CASCADE, related_name='notifications'
    )
    sender = models.ForeignKey(
        User, on_delete=models.SET_NULL, null=True, blank=True,
        related_name='sent_notifications'
    )
    notification_type = models.CharField(max_length=40, choices=NOTIFICATION_TYPES, default='general')
    title = models.CharField(max_length=255)
    message = models.TextField()
    is_read = models.BooleanField(default=False)
    read_at = models.DateTimeField(null=True, blank=True)
    link = models.CharField(max_length=255, blank=True, null=True)
    data = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']
        verbose_name = 'Notification'
        verbose_name_plural = 'Notifications'

    def __str__(self):
        return f"Notification for {self.recipient.full_name}: {self.title}"

    def mark_as_read(self):
        if not self.is_read:
            self.is_read = True
            self.read_at = timezone.now()
            self.save()

class Review(models.Model):
    """Patient review and rating for a doctor"""
    patient = models.ForeignKey(
        User, on_delete=models.CASCADE, related_name='given_reviews'
    )
    doctor = models.ForeignKey(
        User, on_delete=models.CASCADE, related_name='received_reviews'
    )
    consultation = models.ForeignKey(
        Consultation, on_delete=models.SET_NULL, null=True, blank=True,
        related_name='reviews'
    )
    appointment = models.ForeignKey(
        Appointment, on_delete=models.SET_NULL, null=True, blank=True,
        related_name='reviews'
    )
    rating = models.IntegerField(choices=[
        (1, '1 - Poor'),
        (2, '2 - Fair'),
        (3, '3 - Good'),
        (4, '4 - Very Good'),
        (5, '5 - Excellent'),
    ])
    comment = models.TextField(blank=True, null=True)
    is_anonymous = models.BooleanField(default=False)
    is_visible = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']
        verbose_name = 'Review'
        verbose_name_plural = 'Reviews'
        unique_together = ['patient', 'doctor', 'consultation']

    def __str__(self):
        return f"Review by {self.patient.full_name} for Dr. {self.doctor.full_name} - {self.rating}/5"
