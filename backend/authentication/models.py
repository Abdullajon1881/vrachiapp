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
    
# VIDEO CALL MODELS

class VideoCall(models.Model):
    STATUS_CHOICES = [
        ('waiting', 'Waiting'),
        ('active', 'Active'),
        ('ended', 'Ended'),
        ('missed', 'Missed'),
    ]

    appointment = models.OneToOneField(
        Appointment, on_delete=models.CASCADE,
        related_name='video_call', null=True, blank=True
    )
    doctor = models.ForeignKey(
        User, on_delete=models.CASCADE,
        related_name='doctor_video_calls'
    )
    patient = models.ForeignKey(
        User, on_delete=models.CASCADE,
        related_name='patient_video_calls'
    )
    room_id = models.CharField(max_length=100, unique=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='waiting')
    started_at = models.DateTimeField(null=True, blank=True)
    ended_at = models.DateTimeField(null=True, blank=True)
    duration_seconds = models.IntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"VideoCall {self.room_id} — {self.doctor.full_name} & {self.patient.full_name}"

    @property
    def duration_minutes(self):
        return round(self.duration_seconds / 60, 1)


class VideoCallSignal(models.Model):
    SIGNAL_TYPES = [
        ('offer', 'Offer'),
        ('answer', 'Answer'),
        ('ice_candidate', 'ICE Candidate'),
        ('end_call', 'End Call'),
    ]

    call = models.ForeignKey(
        VideoCall, on_delete=models.CASCADE,
        related_name='signals'
    )
    sender = models.ForeignKey(
        User, on_delete=models.CASCADE,
        related_name='sent_signals'
    )
    signal_type = models.CharField(max_length=20, choices=SIGNAL_TYPES)
    payload = models.JSONField()
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['created_at']
        verbose_name = 'Video Call Signal'
        verbose_name_plural = 'Video Call Signals'

# ============================================
# DENTAL TOOTH HISTORY SYSTEM
# ============================================

class DentalChart(models.Model):
    """One dental chart per patient — created automatically on first visit"""
    patient = models.OneToOneField(
        User, on_delete=models.CASCADE,
        related_name='dental_chart'
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    notes = models.TextField(blank=True)

    def __str__(self):
        return f"Dental Chart — {self.patient.full_name}"


class Tooth(models.Model):
    """Represents a single tooth in a patient's dental chart (FDI numbering)"""
    CONDITION_CHOICES = [
        ('healthy', 'Healthy'),
        ('filled', 'Filled'),
        ('crowned', 'Crowned'),
        ('missing', 'Missing'),
        ('implant', 'Implant'),
        ('damaged', 'Damaged'),
        ('decayed', 'Decayed'),
        ('root_canal', 'Root Canal Treated'),
        ('bridge', 'Bridge'),
        ('veneer', 'Veneer'),
        ('extracted', 'Extracted'),
        ('impacted', 'Impacted'),
        ('under_treatment', 'Under Treatment'),
    ]

    # FDI numbering: 11-18, 21-28, 31-38, 41-48
    FDI_CHOICES = (
        [(i, f'Upper Right {i}') for i in range(11, 19)] +
        [(i, f'Upper Left {i}') for i in range(21, 29)] +
        [(i, f'Lower Left {i}') for i in range(31, 39)] +
        [(i, f'Lower Right {i}') for i in range(41, 49)]
    )

    chart = models.ForeignKey(
        DentalChart, on_delete=models.CASCADE,
        related_name='teeth'
    )
    fdi_number = models.IntegerField(choices=FDI_CHOICES)
    condition = models.CharField(
        max_length=20, choices=CONDITION_CHOICES, default='healthy'
    )
    notes = models.TextField(blank=True)
    last_updated = models.DateTimeField(auto_now=True)
    last_updated_by = models.ForeignKey(
        User, on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name='updated_teeth'
    )

    class Meta:
        unique_together = ['chart', 'fdi_number']
        ordering = ['fdi_number']

    def __str__(self):
        return f"Tooth {self.fdi_number} — {self.patient_name} ({self.condition})"

    @property
    def patient_name(self):
        return self.chart.patient.full_name

    @property
    def quadrant(self):
        first_digit = self.fdi_number // 10
        quadrant_map = {
            1: 'Upper Right', 2: 'Upper Left',
            3: 'Lower Left', 4: 'Lower Right'
        }
        return quadrant_map.get(first_digit, 'Unknown')


class ToothTreatment(models.Model):
    """A single treatment event for a specific tooth"""
    TREATMENT_CHOICES = [
        ('examination', 'Examination'),
        ('filling', 'Filling'),
        ('composite_filling', 'Composite Filling'),
        ('amalgam_filling', 'Amalgam Filling'),
        ('crown', 'Crown'),
        ('root_canal', 'Root Canal Treatment'),
        ('extraction', 'Extraction'),
        ('implant', 'Implant'),
        ('implant_crown', 'Implant Crown'),
        ('bridge', 'Bridge'),
        ('veneer', 'Veneer'),
        ('whitening', 'Whitening'),
        ('scaling', 'Scaling & Cleaning'),
        ('xray', 'X-Ray'),
        ('orthodontic', 'Orthodontic Treatment'),
        ('sealant', 'Sealant'),
        ('bonding', 'Bonding'),
        ('other', 'Other'),
    ]

    tooth = models.ForeignKey(
        Tooth, on_delete=models.CASCADE,
        related_name='treatments'
    )
    doctor = models.ForeignKey(
        User, on_delete=models.SET_NULL,
        null=True, related_name='dental_treatments'
    )
    treatment_type = models.CharField(max_length=30, choices=TREATMENT_CHOICES)
    treatment_date = models.DateField()
    description = models.TextField(blank=True)
    materials_used = models.CharField(max_length=200, blank=True)
    cost = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    next_visit_recommended = models.DateField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-treatment_date']

    def __str__(self):
        return f"{self.treatment_type} on tooth {self.tooth.fdi_number} by Dr. {self.doctor.full_name if self.doctor else 'Unknown'}"


class ToothXray(models.Model):
    """X-ray or photo attached to a specific tooth"""
    tooth = models.ForeignKey(
        Tooth, on_delete=models.CASCADE,
        related_name='xrays'
    )
    treatment = models.ForeignKey(
        ToothTreatment, on_delete=models.SET_NULL,
        null=True, blank=True, related_name='xrays'
    )
    uploaded_by = models.ForeignKey(
        User, on_delete=models.SET_NULL,
        null=True, related_name='uploaded_xrays'
    )
    file = models.FileField(upload_to='dental_xrays/')
    file_type = models.CharField(
        max_length=10,
        choices=[('xray', 'X-Ray'), ('photo', 'Photo'), ('scan', '3D Scan')],
        default='xray'
    )
    notes = models.CharField(max_length=300, blank=True)
    taken_at = models.DateField()
    uploaded_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-taken_at']

    def __str__(self):
        return f"{self.file_type} — Tooth {self.tooth.fdi_number} ({self.taken_at})"
    
# NEUROLOGY MODULE

class HeadacheDiary(models.Model):
    """Headache/migraine diary entry for a patient"""
    HEADACHE_TYPES = [
        ('tension', 'Tension Headache'),
        ('migraine', 'Migraine'),
        ('cluster', 'Cluster Headache'),
        ('sinus', 'Sinus Headache'),
        ('rebound', 'Rebound Headache'),
        ('thunderclap', 'Thunderclap Headache'),
        ('unknown', 'Unknown'),
    ]

    SEVERITY_CHOICES = [(i, str(i)) for i in range(1, 11)]  # 1-10 scale

    LOCATION_CHOICES = [
        ('front', 'Front of head'),
        ('back', 'Back of head'),
        ('left', 'Left side'),
        ('right', 'Right side'),
        ('both_sides', 'Both sides'),
        ('top', 'Top of head'),
        ('around_eye', 'Around eye'),
        ('whole_head', 'Whole head'),
    ]

    patient = models.ForeignKey(
        User, on_delete=models.CASCADE,
        related_name='headache_diary'
    )
    headache_type = models.CharField(
        max_length=20, choices=HEADACHE_TYPES, default='unknown'
    )
    severity = models.IntegerField(choices=SEVERITY_CHOICES)
    location = models.CharField(
        max_length=20, choices=LOCATION_CHOICES, default='whole_head'
    )
    started_at = models.DateTimeField()
    ended_at = models.DateTimeField(null=True, blank=True)
    duration_minutes = models.IntegerField(null=True, blank=True)

    # Symptoms
    nausea = models.BooleanField(default=False)
    vomiting = models.BooleanField(default=False)
    light_sensitivity = models.BooleanField(default=False)
    sound_sensitivity = models.BooleanField(default=False)
    aura = models.BooleanField(default=False)
    aura_description = models.TextField(blank=True)

    # Triggers
    triggers = models.JSONField(default=list, blank=True)
    # e.g. ["stress", "lack_of_sleep", "alcohol", "bright_light"]

    # Treatment
    medication_taken = models.CharField(max_length=200, blank=True)
    medication_helped = models.BooleanField(null=True, blank=True)

    notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-started_at']

    def __str__(self):
        return f"{self.headache_type} headache — {self.patient.full_name} ({self.started_at.date()})"

    def save(self, *args, **kwargs):
        if self.started_at and self.ended_at:
            delta = self.ended_at - self.started_at
            self.duration_minutes = int(delta.total_seconds() / 60)
        super().save(*args, **kwargs)


class SeizureRecord(models.Model):
    """Seizure tracking record for a patient"""
    SEIZURE_TYPES = [
        ('tonic_clonic', 'Tonic-Clonic (Grand Mal)'),
        ('absence', 'Absence (Petit Mal)'),
        ('focal', 'Focal Seizure'),
        ('myoclonic', 'Myoclonic'),
        ('atonic', 'Atonic (Drop Attack)'),
        ('tonic', 'Tonic'),
        ('clonic', 'Clonic'),
        ('unknown', 'Unknown'),
    ]

    CONSCIOUSNESS_CHOICES = [
        ('full', 'Fully Conscious'),
        ('partial', 'Partially Conscious'),
        ('lost', 'Lost Consciousness'),
    ]

    patient = models.ForeignKey(
        User, on_delete=models.CASCADE,
        related_name='seizure_records'
    )
    seizure_type = models.CharField(
        max_length=20, choices=SEIZURE_TYPES, default='unknown'
    )
    occurred_at = models.DateTimeField()
    duration_seconds = models.IntegerField()
    consciousness = models.CharField(
        max_length=10, choices=CONSCIOUSNESS_CHOICES, default='lost'
    )

    # Before seizure
    warning_signs = models.TextField(blank=True)
    potential_trigger = models.CharField(max_length=200, blank=True)

    # During seizure
    body_parts_affected = models.JSONField(default=list, blank=True)
    fell_down = models.BooleanField(default=False)
    injury_occurred = models.BooleanField(default=False)
    injury_description = models.TextField(blank=True)

    # After seizure
    recovery_time_minutes = models.IntegerField(null=True, blank=True)
    post_seizure_symptoms = models.TextField(blank=True)
    emergency_services_called = models.BooleanField(default=False)

    # Medical
    witnessed_by = models.CharField(max_length=200, blank=True)
    recorded_by = models.ForeignKey(
        User, on_delete=models.SET_NULL, null=True, blank=True,
        related_name='recorded_seizures'
    )
    notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-occurred_at']

    def __str__(self):
        return f"{self.seizure_type} — {self.patient.full_name} ({self.occurred_at.date()})"

    @property
    def duration_minutes(self):
        return round(self.duration_seconds / 60, 1)


class NeurologyVisit(models.Model):
    """Neurology clinic visit record"""
    patient = models.ForeignKey(
        User, on_delete=models.CASCADE,
        related_name='neurology_visits'
    )
    doctor = models.ForeignKey(
        User, on_delete=models.SET_NULL, null=True,
        related_name='neurology_consultations'
    )
    visit_date = models.DateField()
    diagnosis = models.CharField(max_length=300, blank=True)
    symptoms_reported = models.TextField(blank=True)
    examination_findings = models.TextField(blank=True)
    medications_prescribed = models.JSONField(default=list, blank=True)
    tests_ordered = models.JSONField(default=list, blank=True)
    # e.g. ["MRI", "EEG", "CT scan", "blood test"]
    next_visit = models.DateField(null=True, blank=True)
    notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-visit_date']

    def __str__(self):
        return f"Neurology visit — {self.patient.full_name} ({self.visit_date})"
    
# ============================================
# PHARMACY MODULE
# ============================================

class Medication(models.Model):
    """Master list of medications in the system"""
    name = models.CharField(max_length=200)
    generic_name = models.CharField(max_length=200, blank=True)
    drug_class = models.CharField(max_length=100, blank=True)
    description = models.TextField(blank=True)
    common_side_effects = models.TextField(blank=True)
    contraindications = models.TextField(blank=True)
    requires_prescription = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['name']

    def __str__(self):
        return self.name


class PatientMedication(models.Model):
    """A medication currently or previously taken by a patient"""
    STATUS_CHOICES = [
        ('active', 'Active'),
        ('completed', 'Completed'),
        ('paused', 'Paused'),
        ('cancelled', 'Cancelled'),
    ]

    FREQUENCY_CHOICES = [
        ('once_daily', 'Once Daily'),
        ('twice_daily', 'Twice Daily'),
        ('three_times_daily', 'Three Times Daily'),
        ('four_times_daily', 'Four Times Daily'),
        ('every_other_day', 'Every Other Day'),
        ('weekly', 'Weekly'),
        ('as_needed', 'As Needed'),
        ('other', 'Other'),
    ]

    patient = models.ForeignKey(
        User, on_delete=models.CASCADE,
        related_name='patient_medications'
    )
    prescribed_by = models.ForeignKey(
        User, on_delete=models.SET_NULL, null=True, blank=True,
        related_name='prescribed_medications'
    )
    medication_name = models.CharField(max_length=200)
    generic_name = models.CharField(max_length=200, blank=True)
    dosage = models.CharField(max_length=100)
    # e.g. "500mg", "10ml", "1 tablet"
    frequency = models.CharField(
        max_length=20, choices=FREQUENCY_CHOICES, default='once_daily'
    )
    frequency_custom = models.CharField(max_length=200, blank=True)
    route = models.CharField(
        max_length=50, blank=True,
        # e.g. oral, injection, topical, inhaled
    )
    start_date = models.DateField()
    end_date = models.DateField(null=True, blank=True)
    status = models.CharField(
        max_length=20, choices=STATUS_CHOICES, default='active'
    )
    purpose = models.CharField(max_length=300, blank=True)
    instructions = models.TextField(blank=True)
    side_effects_experienced = models.TextField(blank=True)
    refills_remaining = models.IntegerField(default=0)
    last_refill_date = models.DateField(null=True, blank=True)
    next_refill_date = models.DateField(null=True, blank=True)
    prescription = models.ForeignKey(
        'Prescription', on_delete=models.SET_NULL,
        null=True, blank=True, related_name='patient_medications'
    )
    notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.medication_name} — {self.patient.full_name} ({self.status})"

    @property
    def is_active(self):
        return self.status == 'active'

    @property
    def days_until_refill(self):
        if self.next_refill_date:
            delta = self.next_refill_date - date.today()
            return delta.days
        return None


class MedicationIntakeLog(models.Model):
    """Log of each time a patient takes their medication"""
    STATUS_CHOICES = [
        ('taken', 'Taken'),
        ('missed', 'Missed'),
        ('skipped', 'Skipped'),
        ('delayed', 'Delayed'),
    ]

    medication = models.ForeignKey(
        PatientMedication, on_delete=models.CASCADE,
        related_name='intake_logs'
    )
    scheduled_time = models.DateTimeField()
    taken_at = models.DateTimeField(null=True, blank=True)
    status = models.CharField(
        max_length=10, choices=STATUS_CHOICES, default='taken'
    )
    notes = models.CharField(max_length=300, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-scheduled_time']

    def __str__(self):
        return f"{self.medication.medication_name} — {self.status} at {self.scheduled_time}"


class DrugInteractionCheck(models.Model):
    """Record of drug interaction checks performed"""
    patient = models.ForeignKey(
        User, on_delete=models.CASCADE,
        related_name='interaction_checks'
    )
    medications_checked = models.JSONField()
    # List of medication names checked
    interaction_found = models.BooleanField(default=False)
    severity = models.CharField(
        max_length=20,
        choices=[
            ('none', 'No Interaction'),
            ('minor', 'Minor'),
            ('moderate', 'Moderate'),
            ('major', 'Major'),
            ('contraindicated', 'Contraindicated'),
        ],
        default='none'
    )
    ai_analysis = models.TextField(blank=True)
    checked_by = models.ForeignKey(
        User, on_delete=models.SET_NULL, null=True,
        related_name='performed_interaction_checks'
    )
    checked_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-checked_at']

    def __str__(self):
        return f"Interaction check for {self.patient.full_name} — {self.severity}"
    
# OPHTHALMOLOGY MODULE

class EyeExam(models.Model):
    """Complete eye examination record"""
    EXAM_TYPES = [
        ('routine', 'Routine Eye Exam'),
        ('emergency', 'Emergency Visit'),
        ('follow_up', 'Follow-up'),
        ('pre_surgery', 'Pre-Surgery Assessment'),
        ('post_surgery', 'Post-Surgery Check'),
        ('contact_lens', 'Contact Lens Fitting'),
        ('pediatric', 'Pediatric Eye Exam'),
    ]

    patient = models.ForeignKey(
        User, on_delete=models.CASCADE,
        related_name='eye_exams'
    )
    doctor = models.ForeignKey(
        User, on_delete=models.SET_NULL, null=True,
        related_name='performed_eye_exams'
    )
    exam_date = models.DateField()
    exam_type = models.CharField(
        max_length=20, choices=EXAM_TYPES, default='routine'
    )

    # Visual Acuity (e.g. 20/20, 6/6)
    va_right_eye = models.CharField(max_length=20, blank=True)  # e.g. "20/20"
    va_left_eye = models.CharField(max_length=20, blank=True)
    va_right_corrected = models.CharField(max_length=20, blank=True)
    va_left_corrected = models.CharField(max_length=20, blank=True)

    # Intraocular Pressure (mmHg)
    iop_right = models.FloatField(null=True, blank=True)
    iop_left = models.FloatField(null=True, blank=True)

    # Diagnosis & findings
    diagnosis = models.CharField(max_length=300, blank=True)
    findings = models.TextField(blank=True)
    recommendations = models.TextField(blank=True)
    next_exam_date = models.DateField(null=True, blank=True)
    notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-exam_date']

    def __str__(self):
        return f"Eye exam — {self.patient.full_name} ({self.exam_date})"


class VisionPrescription(models.Model):
    """Glasses or contact lens prescription"""
    PRESCRIPTION_TYPES = [
        ('glasses', 'Glasses'),
        ('contact_lens', 'Contact Lens'),
        ('both', 'Both'),
    ]

    patient = models.ForeignKey(
        User, on_delete=models.CASCADE,
        related_name='vision_prescriptions'
    )
    doctor = models.ForeignKey(
        User, on_delete=models.SET_NULL, null=True,
        related_name='issued_vision_prescriptions'
    )
    exam = models.ForeignKey(
        EyeExam, on_delete=models.SET_NULL,
        null=True, blank=True, related_name='prescriptions'
    )
    prescription_type = models.CharField(
        max_length=15, choices=PRESCRIPTION_TYPES, default='glasses'
    )
    issued_date = models.DateField()
    expiry_date = models.DateField(null=True, blank=True)

    # Right eye (OD)
    right_sphere = models.FloatField(null=True, blank=True)    # SPH
    right_cylinder = models.FloatField(null=True, blank=True)  # CYL
    right_axis = models.IntegerField(null=True, blank=True)    # AXIS (0-180)
    right_add = models.FloatField(null=True, blank=True)       # ADD (for bifocals)
    right_pd = models.FloatField(null=True, blank=True)        # Pupillary distance

    # Left eye (OS)
    left_sphere = models.FloatField(null=True, blank=True)
    left_cylinder = models.FloatField(null=True, blank=True)
    left_axis = models.IntegerField(null=True, blank=True)
    left_add = models.FloatField(null=True, blank=True)
    left_pd = models.FloatField(null=True, blank=True)

    notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-issued_date']

    def __str__(self):
        return f"{self.prescription_type} prescription — {self.patient.full_name} ({self.issued_date})"

    @property
    def is_expired(self):
        if self.expiry_date:
            return self.expiry_date < date.today()
        return False


class EyeCondition(models.Model):
    """Chronic or diagnosed eye condition for a patient"""
    CONDITION_CHOICES = [
        ('myopia', 'Myopia (Nearsightedness)'),
        ('hyperopia', 'Hyperopia (Farsightedness)'),
        ('astigmatism', 'Astigmatism'),
        ('presbyopia', 'Presbyopia'),
        ('glaucoma', 'Glaucoma'),
        ('cataract', 'Cataract'),
        ('macular_degeneration', 'Macular Degeneration'),
        ('diabetic_retinopathy', 'Diabetic Retinopathy'),
        ('dry_eye', 'Dry Eye Syndrome'),
        ('conjunctivitis', 'Conjunctivitis'),
        ('strabismus', 'Strabismus'),
        ('amblyopia', 'Amblyopia (Lazy Eye)'),
        ('retinal_detachment', 'Retinal Detachment'),
        ('keratoconus', 'Keratoconus'),
        ('other', 'Other'),
    ]

    STATUS_CHOICES = [
        ('active', 'Active'),
        ('managed', 'Managed'),
        ('resolved', 'Resolved'),
        ('monitoring', 'Monitoring'),
    ]

    patient = models.ForeignKey(
        User, on_delete=models.CASCADE,
        related_name='eye_conditions'
    )
    doctor = models.ForeignKey(
        User, on_delete=models.SET_NULL, null=True,
        related_name='diagnosed_eye_conditions'
    )
    condition = models.CharField(max_length=30, choices=CONDITION_CHOICES)
    affected_eye = models.CharField(
        max_length=10,
        choices=[('right', 'Right'), ('left', 'Left'), ('both', 'Both')],
        default='both'
    )
    status = models.CharField(
        max_length=15, choices=STATUS_CHOICES, default='active'
    )
    diagnosed_date = models.DateField(null=True, blank=True)
    notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.condition} — {self.patient.full_name} ({self.status})"
    
# CARDIOLOGY MODULE

class BloodPressureLog(models.Model):
    """Blood pressure measurement log"""
    POSITION_CHOICES = [
        ('sitting', 'Sitting'),
        ('standing', 'Standing'),
        ('lying', 'Lying Down'),
    ]

    ARM_CHOICES = [
        ('left', 'Left Arm'),
        ('right', 'Right Arm'),
        ('both', 'Both Arms'),
    ]

    patient = models.ForeignKey(
        User, on_delete=models.CASCADE,
        related_name='bp_logs'
    )
    recorded_by = models.ForeignKey(
        User, on_delete=models.SET_NULL, null=True, blank=True,
        related_name='recorded_bp_logs'
    )
    systolic = models.IntegerField()   # mmHg upper number
    diastolic = models.IntegerField()  # mmHg lower number
    pulse = models.IntegerField(null=True, blank=True)  # bpm
    position = models.CharField(
        max_length=10, choices=POSITION_CHOICES, default='sitting'
    )
    arm = models.CharField(
        max_length=10, choices=ARM_CHOICES, default='left'
    )
    measured_at = models.DateTimeField()
    notes = models.CharField(max_length=300, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-measured_at']

    def __str__(self):
        return f"BP {self.systolic}/{self.diastolic} — {self.patient.full_name} ({self.measured_at.date()})"

    @property
    def category(self):
        """Classify BP according to AHA guidelines"""
        if self.systolic < 120 and self.diastolic < 80:
            return 'normal'
        elif self.systolic < 130 and self.diastolic < 80:
            return 'elevated'
        elif self.systolic < 140 or self.diastolic < 90:
            return 'high_stage1'
        elif self.systolic >= 140 or self.diastolic >= 90:
            return 'high_stage2'
        elif self.systolic >= 180 or self.diastolic >= 120:
            return 'crisis'
        return 'unknown'

    @property
    def category_label(self):
        labels = {
            'normal': '🟢 Normal',
            'elevated': '🟡 Elevated',
            'high_stage1': '🟠 High Stage 1',
            'high_stage2': '🔴 High Stage 2',
            'crisis': '🚨 Hypertensive Crisis',
        }
        return labels.get(self.category, 'Unknown')


class ECGRecord(models.Model):
    """ECG/EKG record for a patient"""
    RHYTHM_CHOICES = [
        ('normal_sinus', 'Normal Sinus Rhythm'),
        ('sinus_tachycardia', 'Sinus Tachycardia'),
        ('sinus_bradycardia', 'Sinus Bradycardia'),
        ('atrial_fibrillation', 'Atrial Fibrillation'),
        ('atrial_flutter', 'Atrial Flutter'),
        ('svt', 'Supraventricular Tachycardia'),
        ('ventricular_tachycardia', 'Ventricular Tachycardia'),
        ('heart_block', 'Heart Block'),
        ('paced', 'Paced Rhythm'),
        ('other', 'Other'),
    ]

    patient = models.ForeignKey(
        User, on_delete=models.CASCADE,
        related_name='ecg_records'
    )
    doctor = models.ForeignKey(
        User, on_delete=models.SET_NULL, null=True,
        related_name='interpreted_ecgs'
    )
    recorded_at = models.DateTimeField()
    heart_rate = models.IntegerField(null=True, blank=True)  # bpm
    rhythm = models.CharField(
        max_length=30, choices=RHYTHM_CHOICES, default='normal_sinus'
    )
    pr_interval = models.FloatField(null=True, blank=True)   # ms
    qrs_duration = models.FloatField(null=True, blank=True)  # ms
    qt_interval = models.FloatField(null=True, blank=True)   # ms
    qtc_interval = models.FloatField(null=True, blank=True)  # ms corrected
    axis = models.CharField(max_length=50, blank=True)       # e.g. "Normal axis"
    interpretation = models.TextField(blank=True)
    is_abnormal = models.BooleanField(default=False)
    ecg_file = models.FileField(
        upload_to='ecg_files/', null=True, blank=True
    )
    notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-recorded_at']

    def __str__(self):
        return f"ECG — {self.patient.full_name} ({self.recorded_at.date()}) — {self.rhythm}"


class HeartCondition(models.Model):
    """Diagnosed heart condition for a patient"""
    CONDITION_CHOICES = [
        ('hypertension', 'Hypertension'),
        ('coronary_artery_disease', 'Coronary Artery Disease'),
        ('heart_failure', 'Heart Failure'),
        ('atrial_fibrillation', 'Atrial Fibrillation'),
        ('arrhythmia', 'Arrhythmia'),
        ('valve_disease', 'Heart Valve Disease'),
        ('cardiomyopathy', 'Cardiomyopathy'),
        ('pericarditis', 'Pericarditis'),
        ('myocarditis', 'Myocarditis'),
        ('congenital', 'Congenital Heart Defect'),
        ('angina', 'Angina'),
        ('heart_attack', 'Heart Attack (MI)'),
        ('stroke', 'Stroke'),
        ('dvt', 'Deep Vein Thrombosis'),
        ('other', 'Other'),
    ]

    STATUS_CHOICES = [
        ('active', 'Active'),
        ('managed', 'Managed'),
        ('resolved', 'Resolved'),
        ('monitoring', 'Monitoring'),
    ]

    patient = models.ForeignKey(
        User, on_delete=models.CASCADE,
        related_name='heart_conditions'
    )
    doctor = models.ForeignKey(
        User, on_delete=models.SET_NULL, null=True,
        related_name='diagnosed_heart_conditions'
    )
    condition = models.CharField(max_length=30, choices=CONDITION_CHOICES)
    status = models.CharField(
        max_length=15, choices=STATUS_CHOICES, default='active'
    )
    diagnosed_date = models.DateField(null=True, blank=True)
    notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.condition} — {self.patient.full_name} ({self.status})"


class CardiologyVisit(models.Model):
    """Cardiology clinic visit record"""
    patient = models.ForeignKey(
        User, on_delete=models.CASCADE,
        related_name='cardiology_visits'
    )
    doctor = models.ForeignKey(
        User, on_delete=models.SET_NULL, null=True,
        related_name='cardiology_consultations'
    )
    visit_date = models.DateField()
    chief_complaint = models.CharField(max_length=300, blank=True)
    diagnosis = models.CharField(max_length=300, blank=True)
    examination_findings = models.TextField(blank=True)
    medications_prescribed = models.JSONField(default=list, blank=True)
    tests_ordered = models.JSONField(default=list, blank=True)
    lifestyle_recommendations = models.TextField(blank=True)
    next_visit = models.DateField(null=True, blank=True)
    notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-visit_date']

    def __str__(self):
        return f"Cardiology visit — {self.patient.full_name} ({self.visit_date})"
    
# ORTHOPEDICS MODULE

class OrthoCondition(models.Model):
    """Orthopedic condition or diagnosis"""
    CONDITION_CHOICES = [
        ('fracture', 'Fracture'),
        ('dislocation', 'Dislocation'),
        ('sprain', 'Sprain'),
        ('strain', 'Strain/Muscle Tear'),
        ('tendinitis', 'Tendinitis'),
        ('bursitis', 'Bursitis'),
        ('arthritis', 'Arthritis'),
        ('osteoporosis', 'Osteoporosis'),
        ('herniated_disc', 'Herniated Disc'),
        ('scoliosis', 'Scoliosis'),
        ('carpal_tunnel', 'Carpal Tunnel Syndrome'),
        ('rotator_cuff', 'Rotator Cuff Injury'),
        ('acl_injury', 'ACL Injury'),
        ('meniscus_tear', 'Meniscus Tear'),
        ('plantar_fasciitis', 'Plantar Fasciitis'),
        ('osteoarthritis', 'Osteoarthritis'),
        ('rheumatoid_arthritis', 'Rheumatoid Arthritis'),
        ('back_pain', 'Back Pain'),
        ('neck_pain', 'Neck Pain'),
        ('other', 'Other'),
    ]

    BODY_PART_CHOICES = [
        ('spine', 'Spine'),
        ('neck', 'Neck'),
        ('shoulder_left', 'Left Shoulder'),
        ('shoulder_right', 'Right Shoulder'),
        ('elbow_left', 'Left Elbow'),
        ('elbow_right', 'Right Elbow'),
        ('wrist_left', 'Left Wrist'),
        ('wrist_right', 'Right Wrist'),
        ('hand_left', 'Left Hand'),
        ('hand_right', 'Right Hand'),
        ('hip_left', 'Left Hip'),
        ('hip_right', 'Right Hip'),
        ('knee_left', 'Left Knee'),
        ('knee_right', 'Right Knee'),
        ('ankle_left', 'Left Ankle'),
        ('ankle_right', 'Right Ankle'),
        ('foot_left', 'Left Foot'),
        ('foot_right', 'Right Foot'),
        ('pelvis', 'Pelvis'),
        ('ribs', 'Ribs'),
        ('other', 'Other'),
    ]

    STATUS_CHOICES = [
        ('active', 'Active'),
        ('healing', 'Healing'),
        ('chronic', 'Chronic'),
        ('resolved', 'Resolved'),
        ('post_surgery', 'Post Surgery'),
    ]

    patient = models.ForeignKey(
        User, on_delete=models.CASCADE,
        related_name='ortho_conditions'
    )
    doctor = models.ForeignKey(
        User, on_delete=models.SET_NULL, null=True,
        related_name='diagnosed_ortho_conditions'
    )
    condition = models.CharField(max_length=30, choices=CONDITION_CHOICES)
    body_part = models.CharField(max_length=20, choices=BODY_PART_CHOICES)
    status = models.CharField(
        max_length=15, choices=STATUS_CHOICES, default='active'
    )
    severity = models.IntegerField(
        null=True, blank=True,
        choices=[(i, str(i)) for i in range(1, 11)]
    )
    diagnosed_date = models.DateField(null=True, blank=True)
    injury_date = models.DateField(null=True, blank=True)
    injury_cause = models.CharField(max_length=300, blank=True)
    notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.condition} ({self.body_part}) — {self.patient.full_name}"


class OrthoImaging(models.Model):
    """MRI, X-ray, CT scan records for orthopedic conditions"""
    IMAGING_TYPES = [
        ('xray', 'X-Ray'),
        ('mri', 'MRI'),
        ('ct_scan', 'CT Scan'),
        ('ultrasound', 'Ultrasound'),
        ('bone_scan', 'Bone Scan'),
        ('dexa', 'DEXA Scan (Bone Density)'),
    ]

    patient = models.ForeignKey(
        User, on_delete=models.CASCADE,
        related_name='ortho_imaging'
    )
    doctor = models.ForeignKey(
        User, on_delete=models.SET_NULL, null=True,
        related_name='ordered_ortho_imaging'
    )
    condition = models.ForeignKey(
        OrthoCondition, on_delete=models.SET_NULL,
        null=True, blank=True, related_name='imaging'
    )
    imaging_type = models.CharField(max_length=15, choices=IMAGING_TYPES)
    body_part = models.CharField(max_length=20)
    imaging_date = models.DateField()
    findings = models.TextField(blank=True)
    impression = models.TextField(blank=True)
    file = models.FileField(upload_to='ortho_imaging/', null=True, blank=True)
    notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-imaging_date']

    def __str__(self):
        return f"{self.imaging_type} — {self.body_part} — {self.patient.full_name} ({self.imaging_date})"


class OrthoSurgery(models.Model):
    """Orthopedic surgery record"""
    SURGERY_TYPES = [
        ('arthroplasty', 'Joint Replacement (Arthroplasty)'),
        ('arthroscopy', 'Arthroscopy'),
        ('acl_reconstruction', 'ACL Reconstruction'),
        ('spinal_fusion', 'Spinal Fusion'),
        ('discectomy', 'Discectomy'),
        ('fracture_repair', 'Fracture Repair/ORIF'),
        ('tendon_repair', 'Tendon Repair'),
        ('rotator_cuff_repair', 'Rotator Cuff Repair'),
        ('meniscus_repair', 'Meniscus Repair'),
        ('carpal_tunnel_release', 'Carpal Tunnel Release'),
        ('amputation', 'Amputation'),
        ('bone_graft', 'Bone Graft'),
        ('other', 'Other'),
    ]

    OUTCOME_CHOICES = [
        ('successful', 'Successful'),
        ('partial', 'Partial Success'),
        ('complicated', 'Complicated'),
        ('revision_needed', 'Revision Needed'),
    ]

    patient = models.ForeignKey(
        User, on_delete=models.CASCADE,
        related_name='ortho_surgeries'
    )
    surgeon = models.ForeignKey(
        User, on_delete=models.SET_NULL, null=True,
        related_name='performed_ortho_surgeries'
    )
    condition = models.ForeignKey(
        OrthoCondition, on_delete=models.SET_NULL,
        null=True, blank=True, related_name='surgeries'
    )
    surgery_type = models.CharField(max_length=30, choices=SURGERY_TYPES)
    body_part = models.CharField(max_length=20)
    surgery_date = models.DateField()
    duration_minutes = models.IntegerField(null=True, blank=True)
    outcome = models.CharField(
        max_length=20, choices=OUTCOME_CHOICES, default='successful'
    )
    complications = models.TextField(blank=True)
    implants_used = models.CharField(max_length=300, blank=True)
    rehabilitation_required = models.BooleanField(default=True)
    rehabilitation_duration_weeks = models.IntegerField(null=True, blank=True)
    follow_up_date = models.DateField(null=True, blank=True)
    notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-surgery_date']

    def __str__(self):
        return f"{self.surgery_type} — {self.patient.full_name} ({self.surgery_date})"


class RehabilitationPlan(models.Model):
    """Rehabilitation/physiotherapy plan"""
    STATUS_CHOICES = [
        ('active', 'Active'),
        ('completed', 'Completed'),
        ('paused', 'Paused'),
        ('cancelled', 'Cancelled'),
    ]

    patient = models.ForeignKey(
        User, on_delete=models.CASCADE,
        related_name='rehab_plans'
    )
    doctor = models.ForeignKey(
        User, on_delete=models.SET_NULL, null=True,
        related_name='created_rehab_plans'
    )
    condition = models.ForeignKey(
        OrthoCondition, on_delete=models.SET_NULL,
        null=True, blank=True, related_name='rehab_plans'
    )
    surgery = models.ForeignKey(
        OrthoSurgery, on_delete=models.SET_NULL,
        null=True, blank=True, related_name='rehab_plans'
    )
    title = models.CharField(max_length=200)
    start_date = models.DateField()
    end_date = models.DateField(null=True, blank=True)
    status = models.CharField(
        max_length=15, choices=STATUS_CHOICES, default='active'
    )
    frequency_per_week = models.IntegerField(default=3)
    exercises = models.JSONField(default=list, blank=True)
    goals = models.TextField(blank=True)
    progress_notes = models.TextField(blank=True)
    pain_level_start = models.IntegerField(null=True, blank=True)
    pain_level_current = models.IntegerField(null=True, blank=True)
    notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"Rehab: {self.title} — {self.patient.full_name} ({self.status})"