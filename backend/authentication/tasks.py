from celery import shared_task
from django.utils import timezone
from datetime import timedelta


@shared_task
def send_appointment_reminders():
    """Send reminders for appointments in the next 24 hours and 1 hour"""
    from django.contrib.auth import get_user_model
    from .models import Appointment, Notification

    now = timezone.now()
    reminders_sent = 0

    # 24 hour reminders
    window_24h_start = now + timedelta(hours=23, minutes=30)
    window_24h_end = now + timedelta(hours=24, minutes=30)

    # 1 hour reminders
    window_1h_start = now + timedelta(minutes=45)
    window_1h_end = now + timedelta(hours=1, minutes=15)

    upcoming_24h = Appointment.objects.filter(
        appointment_date__range=(window_24h_start, window_24h_end),
        status='confirmed'
    ).select_related('patient', 'doctor')

    upcoming_1h = Appointment.objects.filter(
        appointment_date__range=(window_1h_start, window_1h_end),
        status='confirmed'
    ).select_related('patient', 'doctor')

    for appointment in upcoming_24h:
        already_sent = Notification.objects.filter(
            user=appointment.patient,
            notification_type='appointment_reminder',
            related_id=appointment.id,
            message__icontains='24'
        ).exists()

        if not already_sent:
            Notification.objects.create(
                user=appointment.patient,
                title='Appointment Reminder - 24 Hours',
                message=f'You have an appointment with Dr. {appointment.doctor.get_full_name()} tomorrow at {appointment.appointment_date.strftime("%H:%M")}.',
                notification_type='appointment_reminder',
                related_id=appointment.id,
            )
            reminders_sent += 1

    for appointment in upcoming_1h:
        already_sent = Notification.objects.filter(
            user=appointment.patient,
            notification_type='appointment_reminder',
            related_id=appointment.id,
            message__icontains='1 hour'
        ).exists()

        if not already_sent:
            Notification.objects.create(
                user=appointment.patient,
                title='Appointment Reminder - 1 Hour',
                message=f'Your appointment with Dr. {appointment.doctor.get_full_name()} starts in 1 hour at {appointment.appointment_date.strftime("%H:%M")}.',
                notification_type='appointment_reminder',
                related_id=appointment.id,
            )
            reminders_sent += 1

    return f'Sent {reminders_sent} reminders'


@shared_task
def cleanup_old_notifications():
    """Delete notifications older than 30 days"""
    from .models import Notification
    cutoff = timezone.now() - timedelta(days=30)
    deleted, _ = Notification.objects.filter(
        created_at__lt=cutoff,
        is_read=True
    ).delete()
    return f'Deleted {deleted} old notifications'