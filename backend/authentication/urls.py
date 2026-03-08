from django.urls import path
from . import views

urlpatterns = [
    # Аутентификация
    path('register/', views.RegisterView.as_view(), name='register'),
    path('login/', views.LoginView.as_view(), name='login'),
    path('logout/', views.LogoutView.as_view(), name='logout'),
    path('google-auth/', views.GoogleAuthView.as_view(), name='google-auth'),
    
    # Email верификация
    path('verify-email/<str:token>/', views.verify_email_view, name='verify_email'),
    path('verify-email-html/<str:token>/', views.verify_email_html_view, name='verify_email_html'),
    path('resend-verification/', views.resend_verification_email, name='resend_verification_email'),
    
    # Профиль
    path('profile/', views.user_profile, name='user-profile'),
    path('check-auth/', views.check_auth, name='check-auth'),
    path('csrf/', views.get_csrf_token, name='csrf'),
    path('users/', views.list_users, name='list-users'),
    path('regions/', views.get_regions, name='regions'),
    path('cities/', views.get_cities, name='cities'),
    path('districts/', views.get_districts, name='districts'),
    path('detect-location/', views.detect_location, name='detect-location'),
    
    # Сброс пароля
    path('password-reset/', views.PasswordResetView.as_view(), name='password-reset'),
    
    # Новые маршруты для заявок врачей
    path('doctor-applications/', views.submit_doctor_application, name='submit_doctor_application'),
    path('doctor-applications/list/', views.get_doctor_applications, name='get_doctor_applications'),
    path('doctor-applications/<int:application_id>/', views.get_doctor_application_detail, name='get_doctor_application_detail'),
    path('doctor-applications/<int:application_id>/update/', views.update_doctor_application, name='update_doctor_application'),
    path('doctor-applications/<int:application_id>/update-name/', views.update_doctor_name_from_application, name='update_doctor_name_from_application'),
    path('user-applications/', views.get_user_applications, name='get_user_applications'),
    
    # Управление пользователями (только для админов)
    path('users/', views.get_all_users, name='get_all_users'),
    path('users/<int:user_id>/delete/', views.delete_user, name='delete_user'),
    
    # Врачи (только для пациентов)
    path('doctors/', views.get_doctors, name='get_doctors'),
    path('doctors/<int:doctor_id>/', views.get_doctor_profile, name='get_doctor_profile'),
    path('users/<int:user_id>/profile/', views.manage_user_profile, name='manage_user_profile'),
    path('current-user/', views.get_current_user_data, name='get_current_user_data'),
    
    # Консультации и чаты
    path('consultations/', views.get_consultations, name='get_consultations'),
    path('consultations/create/', views.create_consultation, name='create_consultation'),
    path('consultations/<int:consultation_id>/', views.get_consultation_detail, name='get_consultation_detail'),
    path('consultations/<int:consultation_id>/update/', views.update_consultation, name='update_consultation'),
    path('consultations/<int:consultation_id>/accept/', views.accept_consultation, name='accept_consultation'),
    path('consultations/<int:consultation_id>/complete/', views.complete_consultation, name='complete_consultation'),
    path('consultations/<int:consultation_id>/messages/', views.get_messages, name='get_messages'),
    path('consultations/<int:consultation_id>/messages/send/', views.send_message, name='send_message'),
    
    # AI диагностика
    path('ai/diagnosis/', views.ai_diagnosis, name='ai_diagnosis'),
    path('ai/history/', views.ai_dialogue_history, name='ai_dialogue_history'),

    # Поддержка
    path('support/send/', views.send_support_message, name='send_support_message'),

    # Защищённый доступ к медиа (только для админов)
    path('protected-media/<path:subpath>/', views.protected_media, name='protected_media'),

    # Appointment booking system
    path('appointments/', views.appointments, name='appointments'),
    path('appointments/<int:appointment_id>/', views.appointment_detail, name='appointment_detail'),
    path('appointments/<int:appointment_id>/cancel/', views.appointment_detail, name='appointment_cancel'),
    path('doctors/<int:doctor_id>/available-slots/', views.doctor_available_slots, name='doctor_available_slots'),
    path('doctor/schedule/', views.doctor_schedule, name='doctor_schedule'),
    
    # Medical records system
    path('medical-records/', views.medical_records, name='medical_records'),
    path('medical-records/<int:record_id>/', views.medical_record_detail, name='medical_record_detail'),
    path('vital-signs/', views.vital_signs, name='vital_signs'),
    path('vital-signs/<int:patient_id>/', views.vital_signs, name='vital_signs_patient'),

    # Notifications system
    path('notifications/', views.notifications, name='notifications'),
    path('notifications/<int:notification_id>/read/', views.mark_notification_read, name='mark_notification_read'),
    path('notifications/read-all/', views.mark_all_notifications_read, name='mark_all_notifications_read'),
    path('notifications/<int:notification_id>/delete/', views.delete_notification, name='delete_notification'),

    # Dashboard APIs
    path('dashboard/patient/', views.patient_dashboard, name='patient_dashboard'),
    path('dashboard/doctor/', views.doctor_dashboard, name='doctor_dashboard'),

    # Doctor search & filtering
    path('doctors/search/', views.search_doctors, name='search_doctors'),
    path('doctors/<int:doctor_id>/profile/', views.doctor_profile_detail, name='doctor_profile_detail'),
    path('specializations/', views.specializations_list, name='specializations_list'),

    # Reviews & ratings system
    path('doctors/<int:doctor_id>/reviews/', views.doctor_reviews, name='doctor_reviews'),
    path('reviews/<int:review_id>/', views.review_detail, name='review_detail'),

    # Admin panel & doctor approval
    path('admin/dashboard/', views.admin_dashboard, name='admin_dashboard'),
    path('admin/users/', views.admin_users_list, name='admin_users_list'),
    path('admin/doctors/<int:doctor_id>/approve/', views.admin_approve_doctor, name='admin_approve_doctor'),
    path('admin/users/<int:user_id>/toggle/', views.admin_toggle_user, name='admin_toggle_user'),
    path('admin/users/<int:user_id>/delete/', views.admin_delete_user, name='admin_delete_user'),
    path('admin/consultations/', views.admin_consultations_list, name='admin_consultations_list'),

    # File uploads
    path('upload/avatar/', views.upload_avatar, name='upload_avatar'),
    path('upload/medical-document/', views.upload_medical_document, name='upload_medical_document'),
    path('upload/consultation/<int:consultation_id>/', views.upload_consultation_file, name='upload_consultation_file'),
    path('upload/delete/', views.delete_file, name='delete_file'),

        # Email notifications
    path('email/test/', views.send_test_email, name='send_test_email'),

    # Additional features
    path('change-password/', views.change_password, name='change_password'),
    path('statistics/', views.user_statistics, name='user_statistics'),
    path('report-issue/', views.report_issue, name='report_issue'),
    path('search/', views.search_global, name='search_global'),

    # Calendar & reminders
    path('calendar/<int:doctor_id>/', views.doctor_calendar, name='doctor_calendar'),
    path('appointments/reminders/', views.appointment_reminders, name='appointment_reminders'),
    path('appointments/history/', views.appointment_history, name='appointment_history'),
    path('appointments/<int:appointment_id>/reschedule/', views.reschedule_appointment, name='reschedule_appointment'),

    # AI dialogue management
    path('ai/dialogue/new/', views.start_new_ai_dialogue, name='start_new_ai_dialogue'),
    path('ai/dialogue/<int:dialogue_id>/close/', views.close_ai_dialogue, name='close_ai_dialogue'),

    # Doctor availability & slots
    path('doctors/<int:doctor_id>/slots/', views.doctor_available_slots, name='doctor_available_slots'),
    path('doctors/<int:doctor_id>/available-dates/', views.doctor_available_dates, name='doctor_available_dates'),
    path('doctors/<int:doctor_id>/next-slot/', views.next_available_slot, name='next_available_slot'),

    # SMS notifications
    path('sms/test/', views.send_test_sms, name='send_test_sms'),

    # AI Medical History
    path('ai/medical-summary/', views.ai_medical_summary, name='ai_medical_summary'),
    path('ai/medical-summary/<int:patient_id>/', views.ai_medical_summary, name='ai_medical_summary_patient'),
    path('ai/risk-assessment/', views.ai_patient_risk_assessment, name='ai_patient_risk_assessment'),
    path('ai/risk-assessment/<int:patient_id>/', views.ai_patient_risk_assessment, name='ai_patient_risk_assessment_patient'),

    # Video calls / telemedicine
    path('video-calls/create/', views.create_video_call, name='create_video_call'),
    path('video-calls/my/', views.my_video_calls, name='my_video_calls'),
    path('video-calls/<str:room_id>/', views.get_video_call, name='get_video_call'),
    path('video-calls/<str:room_id>/status/', views.update_video_call_status, name='update_video_call_status'),
    path('video-calls/<str:room_id>/signal/', views.send_webrtc_signal, name='send_webrtc_signal'),
    path('video-calls/<str:room_id>/signals/', views.get_webrtc_signals, name='get_webrtc_signals'),

    # Dental tooth history system
    path('dental/chart/', views.get_dental_chart, name='get_dental_chart'),
    path('dental/chart/<int:patient_id>/', views.get_dental_chart, name='get_dental_chart_patient'),
    path('dental/chart/<int:patient_id>/summary/', views.patient_dental_summary, name='patient_dental_summary'),
    path('dental/chart/<int:patient_id>/tooth/<int:fdi_number>/', views.get_tooth_detail, name='get_tooth_detail'),
    path('dental/chart/<int:patient_id>/tooth/<int:fdi_number>/treatment/', views.add_tooth_treatment, name='add_tooth_treatment'),
    path('dental/chart/<int:patient_id>/tooth/<int:fdi_number>/condition/', views.update_tooth_condition, name='update_tooth_condition'),
    path('dental/chart/<int:patient_id>/tooth/<int:fdi_number>/xray/', views.upload_tooth_xray, name='upload_tooth_xray'),
    path('dental/treatment/<int:treatment_id>/delete/', views.delete_tooth_treatment, name='delete_tooth_treatment'),

    # Pharmacy module
    path('pharmacy/medications/', views.patient_medications, name='patient_medications'),
    path('pharmacy/medications/<int:med_id>/', views.medication_detail, name='medication_detail'),
    path('pharmacy/medications/<int:med_id>/log/', views.log_medication_intake, name='log_medication_intake'),
    path('pharmacy/interactions/', views.check_drug_interactions, name='check_drug_interactions'),
    path('pharmacy/summary/', views.pharmacy_summary, name='pharmacy_summary'),
    path('pharmacy/summary/<int:patient_id>/', views.pharmacy_summary, name='pharmacy_summary_patient'),

    # Ophthalmology module
    path('ophthalmology/exams/', views.eye_exams, name='eye_exams'),
    path('ophthalmology/prescriptions/', views.vision_prescriptions, name='vision_prescriptions'),
    path('ophthalmology/conditions/', views.eye_conditions, name='eye_conditions'),
    path('ophthalmology/summary/', views.ophthalmology_summary, name='ophthalmology_summary'),
    path('ophthalmology/summary/<int:patient_id>/', views.ophthalmology_summary, name='ophthalmology_summary_patient'),

] 